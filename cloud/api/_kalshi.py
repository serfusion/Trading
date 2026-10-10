"""🎲 Kalshi (pasar prediksi) untuk berita pekan ini -> ikut di kartu 🎯 (GET /api/chat -> persiapan.berita[].kalshi).

Permintaan pengguna 30 Sep 2026: "kumpulkan info untuk prediksi arah news beberapa jam kemudian, berapa persentase
akan kemana, jadi saya bisa bersiap untuk 1 detik sebelum news".

Per berita (CPI, core CPI, NFP, pengangguran, core PCE): peluang pasar Kalshi bahwa angka keluar DI ATAS / SAMA / DI
BAWAH konsensus ForexFactory (harga pasar biner "Above X" saat ini). Khusus CPI: peluang emas NAIK 1 menit setelah
rilis = P(bawah) x naik|bawah + P(atas) x naik|atas + P(sama) x naik|sama, tingkat reaksi dari cloud/api/kalshi.json
(research/kalshi_uji.py, rilis CPI 2010-2026). Bukti uji (2022-2025) ikut ditampilkan; statusnya BELUM TERBUKTI.
Pasar Kalshi dibaca paling sering tiap 15 menit untuk semua pengguna (cache Supabase baris "kalshi").
INFORMASI saja: tidak membuka order dan tidak mengubah sinyal. Hanya library standar Python.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.elections.kalshi.com/trade-api/v2"
# judul ForexFactory -> (seri Kalshi, langkah angka, pengangguran = terbalik untuk emas)
SERIES = {"CPI m/m": ("KXCPI", 0.1, False), "Core CPI m/m": ("KXCPICORE", 0.1, False),
          "Non-Farm Employment Change": ("KXPAYROLLS", None, False), "Unemployment Rate": ("KXU3", 0.1, True),
          "Core PCE Price Index m/m": ("KXPCECORE", 0.1, False)}
CPI = ("CPI m/m", "Core CPI m/m")
TTL = timedelta(minutes=15)
AHEAD = timedelta(days=8)
_PATH = Path(__file__).resolve().parent / "kalshi.json"
STATS = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
WIB = timedelta(hours=7)


def _num(text) -> float | None:
    m = re.match(r"^\s*([<>]?)(-?\d+(?:[.,]\d+)?)\s*([kKmMbB%]?)", str(text or ""))
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(3).lower(), 1.0)
    return float(m.group(2).replace(",", ".")) * mult


def fetch(series: str, opener=None) -> list[dict]:
    """Pasar terbuka satu seri (semua event terbuka), [] bila gagal."""
    url = f"{API}/events?" + urllib.parse.urlencode({"series_ticker": series, "status": "open",
                                                      "with_nested_markets": "true", "limit": 20})
    try:
        with (opener or urllib.request.urlopen)(urllib.request.Request(url, headers={"User-Agent": "xau-signal"}),
                                                timeout=6) as r:
            events = json.load(r).get("events", [])
    except Exception:  # noqa: BLE001 - Kalshi opsional
        return []
    return [m for e in events for m in e.get("markets") or []]


def strike(ticker: str) -> float | None:
    t = ticker.rsplit("-T", 1)
    try:
        return float(t[1]) if len(t) == 2 else None
    except ValueError:
        return None


def prob(m: dict) -> float | None:
    """Peluang YES: mid bid/ask bila keduanya ada, selain itu harga transaksi terakhir."""
    bid, ask, last = (_num(m.get(k)) for k in ("yes_bid_dollars", "yes_ask_dollars", "last_price_dollars"))
    if bid is not None and ask is not None and 0 < ask <= 1 and ask >= bid:
        return (bid + ask) / 2
    return last


def p_above(pts: list[tuple[float, float]], x: float) -> float | None:
    for k, p in pts:
        if abs(k - x) < 1e-9:
            return p
    lo = [(k, p) for k, p in pts if k < x]
    hi = [(k, p) for k, p in pts if k > x]
    if not lo or not hi:
        return None
    (k0, p0), (k1, p1) = lo[-1], hi[0]
    return p0 + (p1 - p0) * (x - k0) / (k1 - k0)


def split(markets: list[dict], cons: float, step: float | None) -> dict | None:
    """{"atas", "sama", "bawah"} (0..1) terhadap konsensus; None bila konsensus di luar strike pasar."""
    pts = sorted((k, p) for m in markets if (k := strike(m["ticker"])) is not None and (p := prob(m)) is not None)
    up = p_above(pts, cons)
    if up is None:
        return None
    if step is None:
        down = 1 - up
    else:
        ref = p_above(pts, round(cons - step, 6))
        if ref is None:
            return None
        down = 1 - ref
    up, down = min(max(up, 0.0), 1.0), min(max(down, 0.0), 1.0)
    return {"atas": up, "bawah": down, "sama": max(0.0, 1 - up - down)}


def snapshot(cards: list[dict], now: datetime, get=fetch) -> dict:
    """{"judul|waktu": {"atas","sama","bawah"}} untuk berita pekan ini yang punya pasar Kalshi."""
    want = [c for c in cards if c.get("title") in SERIES and c.get("forecast")]
    out, cache = {}, {}
    for c in want:
        t0 = datetime.fromisoformat(c["time"])
        if not now - timedelta(hours=6) <= t0 <= now + AHEAD:
            continue
        series, step, _ = SERIES[c["title"]]
        if series not in cache:
            cache[series] = get(series)
        ms = [m for m in cache[series] if m.get("close_time") and
              timedelta(0) <= t0 - datetime.fromisoformat(m["close_time"].replace("Z", "+00:00")) <= timedelta(minutes=20)]
        cons = _num(c["forecast"])
        if ms and cons is not None:
            s = split(ms, cons, step)
            if s:
                out[f"{c['title']}|{c['time']}"] = {k: round(v, 3) for k, v in s.items()}
    return out


def cached_snapshot(cards: list[dict], store, now: datetime, get=fetch) -> tuple[dict, str | None]:
    """(snapshot, waktu ambil ISO) dengan cache Supabase TTL menit (satu pembacaan Kalshi untuk semua pengguna)."""
    old = {}
    if store is not None:
        try:
            old = store.get_state("kalshi") or {}
        except Exception:  # noqa: BLE001
            old = {}
    if old.get("t") and now - datetime.fromisoformat(old["t"]) < TTL:
        return old.get("data") or {}, old["t"]
    data = snapshot(cards, now, get)
    if not data and old.get("data"):
        return old["data"], old.get("t")                    # Kalshi gagal -> pakai data lama
    if store is not None:
        try:
            store.save_state({"t": now.isoformat(), "data": data}, "kalshi")
        except Exception:  # noqa: BLE001
            pass
    return data, now.isoformat()


def _pct(x: float) -> int:
    return int(round(x * 100))


def gold_up(parts: list[dict]) -> float | None:
    """Peluang emas NAIK 1 menit setelah CPI (rata-rata headline & core)."""
    r = STATS.get("reaksi_cpi") or {}
    if not parts or not all(k in r for k in ("bawah", "atas", "sama")):
        return None
    vals = [p["bawah"] * r["bawah"]["naik"] + p["atas"] * r["atas"]["naik"] + p["sama"] * r["sama"]["naik"]
            for p in parts]
    return sum(vals) / len(vals)


def info(card: dict, snap: dict) -> dict | None:
    """Teks kartu: angka besar + bukti singkat (format sama dengan skenario lain di kartu 🎯)."""
    s = snap.get(f"{card['title']}|{card['time']}")
    if not s:
        return None
    series, step, _ = SERIES[card["title"]]
    peluang = (f"Kalshi: di atas perkiraan {_pct(s['atas'])}%" + (f" • sama {_pct(s['sama'])}%" if step else "")
               + f" • di bawah {_pct(s['bawah'])}%")
    if card["title"] in CPI:
        parts = [v for k, v in snap.items() if k.split("|")[0] in CPI and k.split("|")[1] == card["time"]]
        up = gold_up(parts)
        sig = (STATS.get("sinyal") or {}).get("Exness") or {}
        th = STATS.get("ambang", 0.6)
        if up is None:
            return None
        if up >= th:
            teks, kuat = f"{_pct(up)}% NAIK 🟢", True
        elif up <= 1 - th:
            teks, kuat = f"{_pct(1 - up)}% TURUN 🔴", True
        else:
            teks, kuat = f"{_pct(max(up, 1 - up))}% {'naik' if up >= 0.5 else 'turun'} ⚪", False
        bukti = peluang
        if sig:
            bukti += (f" • teruji {sig['tahun']}: {sig['n']} sinyal ≥ {_pct(th)}%, benar {sig['benar']:.0f}%, "
                      f"BUY t0−1 tutup 1 mnt rata {'+' if sig['rata60'] >= 0 else '−'}${abs(sig['rata60']):.2f}"
                      f"/0,01 lot • ⚠️ belum terbukti (sampel kecil)").replace(".", ",")
        return {"label": "🎲 Kalshi → emas 1 menit", "teks": teks, "bukti": bukti, "kuat": kuat,
                "atas": s["atas"], "sama": s["sama"], "bawah": s["bawah"]}
    acc = (STATS.get("akurasi") or {}).get(series) or {}
    arah = "DI ATAS" if s["atas"] >= s["bawah"] else "DI BAWAH"
    top = max(s["atas"], s["bawah"])
    bukti = peluang + (f" • tebakan kejutan teruji {acc['tahun']}: benar {acc['benar']:.0f}% ({acc['n']} rilis)"
                       .replace(".", ",") if acc.get("n", 0) >= 10 else " • data uji belum cukup") \
        + " • arah emas tidak terbukti"
    return {"label": "🎲 Kalshi → angka vs perkiraan", "teks": f"{_pct(top)}% {arah} ⚪", "bukti": bukti,
            "kuat": False, "atas": s["atas"], "sama": s["sama"], "bawah": s["bawah"]}


def _angka(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}%".replace(".", ",")


def sebaran(markets: list[dict], step: float) -> dict | None:
    """Sebaran pasar untuk angka berlangkah 0,1 (CPI, core CPI, core PCE, pengangguran): nilai paling mungkin, peluangnya,
    dan peluang "≥ nilai" di sekitar puncak. Dipakai SEBELUM konsensus ForexFactory terbit (permintaan 10 Okt 2026)."""
    pts = sorted((k, p) for m in markets if (k := strike(m["ticker"])) is not None and (p := prob(m)) is not None)
    if len(pts) < 3:
        return None
    # P(angka = k + step) = P(> k) - P(> k + step); ujung bawah/atas = sisa peluang
    vals = {}
    for (k0, p0), (k1, p1) in zip(pts, pts[1:]):
        vals[round(k0 + step, 6)] = max(0.0, p0 - p1)
    vals[round(pts[0][0], 6)] = max(0.0, 1 - pts[0][1])            # ≤ strike terendah
    vals[round(pts[-1][0] + step, 6)] = max(0.0, pts[-1][1])        # ≥ strike tertinggi + langkah
    tot = sum(vals.values()) or 1.0
    vals = {k: v / tot for k, v in vals.items()}
    top = max(vals, key=vals.get)
    ge = {k: sum(v for x, v in vals.items() if x >= k - 1e-9) for k in vals}
    near = [k for k in sorted(vals) if abs(k - top) <= step + 1e-9 and 0.02 <= ge[k] <= 0.98]
    return {"puncak": top, "p": vals[top], "ge": {f"{k:.1f}": round(ge[k], 3) for k in near},
            "rata": round(sum(k * v for k, v in vals.items()), 3)}


def mendatang(cards: list[dict], store, now: datetime, get=fetch) -> None:
    """Kartu 📅 berita berikutnya yang belum punya konsensus (di luar kalender pekan ini): tambahkan card["kalshi_sebaran"]
    — angka paling mungkin menurut pasar Kalshi. Cache Supabase baris "kalshi_sebaran" (TTL 15 menit)."""
    want = [c for c in cards if c.get("title") in SERIES and SERIES[c["title"]][1] and not c.get("forecast")]
    want = [c for c in want if timedelta(0) < datetime.fromisoformat(c["time"]) - now <= AHEAD]
    if not want:
        return
    old = {}
    if store is not None:
        try:
            old = store.get_state("kalshi_sebaran") or {}
        except Exception:  # noqa: BLE001
            old = {}
    data = old.get("data") or {}
    if not old.get("t") or now - datetime.fromisoformat(old["t"]) >= TTL:
        fresh, cache = {}, {}
        for c in want:
            series, step, _ = SERIES[c["title"]]
            if series not in cache:
                cache[series] = get(series)
            t0 = datetime.fromisoformat(c["time"])
            ms = [m for m in cache[series] if m.get("close_time") and timedelta(0) <= t0 - datetime.fromisoformat(
                m["close_time"].replace("Z", "+00:00")) <= timedelta(minutes=20)]
            s = sebaran(ms, step) if ms else None
            if s:
                fresh[f"{c['title']}|{c['time']}"] = s
        if fresh:
            hist = old.get("riwayat") or {}
            for k, s in fresh.items():          # riwayat peluang angka puncak → terlihat bila pasar bergeser
                h = list(hist.get(k) or [])
                if not h or now - datetime.fromisoformat(h[-1][0]) >= timedelta(minutes=14):
                    h.append([now.isoformat(), s["puncak"], round(s["p"], 3), s["rata"]])
                hist[k] = h[-200:]
            data = fresh
            old = {"t": now.isoformat(), "data": data, "riwayat": {k: v for k, v in hist.items() if k in fresh}}
            if store is not None:
                try:
                    store.save_state(old, "kalshi_sebaran")
                except Exception:  # noqa: BLE001
                    pass
    w = datetime.fromisoformat(old["t"]) + WIB if old.get("t") else None
    for c in want:
        key = f"{c['title']}|{c['time']}"
        s = data.get(key)
        if not s:
            continue
        nama = {"CPI m/m": "CPI m/m", "Core CPI m/m": "Core CPI m/m", "Core PCE Price Index m/m": "Core PCE m/m",
                "Unemployment Rate": "Pengangguran"}.get(c["title"], c["title"])
        ge = " • ".join(f"≥ {_angka(float(k))}: {_pct(v)}%" for k, v in s["ge"].items())
        geser = ""
        h = (old.get("riwayat") or {}).get(key) or []
        lama = [x for x in h if datetime.fromisoformat(x[0]) <= now - timedelta(hours=23)]
        if lama and abs(lama[-1][3] - s["rata"]) >= 0.02:
            geser = (f" • 24 jam lalu rata-rata {_angka(lama[-1][3], 2)} → sekarang {_angka(s['rata'], 2)} "
                     "(pasar bergeser: ada data/pernyataan baru)")
        c["kalshi_sebaran"] = {
            "judul": "🎲 Pasar Kalshi (sebelum konsensus terbit)",
            "teks": f"{nama} paling mungkin {_angka(s['puncak'])} ({_pct(s['p'])}%)",
            "catatan": (f"{ge} • rata-rata pasar {_angka(s['rata'], 2)}{geser}"
                        + (f" • diperbarui {w:%H:%M} WIB" if w else "")
                        + " • peluang arah emas dihitung otomatis setelah konsensus ForexFactory terbit (biasanya Minggu)"),
            "sebaran": s}


def attach(persiapan: dict, store, now: datetime | None = None, get=fetch) -> None:
    """Tambahkan persiapan.berita[].kalshi dan persiapan.kalshi_waktu (WIB)."""
    now = now or datetime.now(timezone.utc)
    cards = persiapan.get("berita") or []
    if not any(c.get("title") in SERIES for c in cards):
        return
    snap, t = cached_snapshot(cards, store, now, get)
    for c in cards:
        if c.get("title") in SERIES:
            k = info(c, snap)
            if k:
                c["kalshi"] = k
    if t:
        w = datetime.fromisoformat(t) + WIB
        persiapan["kalshi_waktu"] = f"{w:%H:%M} WIB"
