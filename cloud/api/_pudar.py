"""📉 Peringatan lonjakan memudar setelah rilis berita (XAU), permintaan pengguna 2 Okt 2026.

NFP 2 Okt: emas +$44 dalam 33 menit lalu berbalik ke bawah harga sebelum rilis. Riset `research/berita_tren.py`
(XAU M15 2012–2026, 1.035 lonjakan berita): yang memprediksi arah 3–6 jam BUKAN tren besar, tetapi SISA LONJAKAN di
menit 30/60 = (harga sekarang − harga open rilis) / puncak lonjakan. Sisa ≥ 60% di menit 60 → 88% masih searah setelah
6 jam; sisa < 30% → 56% (NFP 38%) dan 92% (NFP 97%) berbalik melewati harga awal dalam 6 jam; konsisten LAMA & BARU.
Statistik: cloud/api/pudar.json (`python -m research.berita_tren ekspor`). Harga: Twelve Data XAU/USD 5 menit
(+ 1 hari untuk ATR), cache Supabase baris "pudar" 2 menit. Informasi saja: tidak membuka order. Library standar.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "pudar.json"
STATS = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
TTL = timedelta(minutes=2)
WINDOW = timedelta(hours=6)
WIB = timedelta(hours=7)


def _usd(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}${abs(x):.2f}".replace(".", ",")


def _pct(x: float) -> int:
    return int(round(100 * x))


def measure(bars: list[tuple], t0: datetime, now: datetime, atr: float | None, min_pct: float = 0.0) -> dict | None:
    """bars = [(waktu buka, open, high, low, close)] 5 menit UTC. Sama dengan riset: lonjakan = open candle rilis ->
    close 15 menit (>= $1 dan >= 0,1 ATR harian); sisa = (close menit m - open) / puncak searah lonjakan s.d. menit m."""
    bars = sorted(b for b in bars if b[0] >= t0)
    if not bars or bars[0][0] != t0:
        return None
    o = bars[0][1]
    mins = 60 if now >= t0 + timedelta(minutes=60) else 30 if now >= t0 + timedelta(minutes=30) else 15 \
        if now >= t0 + timedelta(minutes=15) else None
    if mins is None:
        return None
    upto = [b for b in bars if b[0] + timedelta(minutes=5) <= t0 + timedelta(minutes=mins)]
    s15 = [b for b in bars if b[0] + timedelta(minutes=5) <= t0 + timedelta(minutes=15)]
    if len(s15) < 3 or len(upto) < mins // 5:
        return None
    spike = s15[-1][4] - o
    if abs(spike) < max(1.0 if not min_pct else 0.0, 0.1 * (atr or 0.0), min_pct * o):
        return {"kecil": True, "spike": spike}
    s = 1 if spike > 0 else -1
    peak_i = max(range(len(upto)), key=lambda i: (upto[i][2] - o) if s > 0 else (o - upto[i][3]))
    peak = (upto[peak_i][2] - o) if s > 0 else (o - upto[peak_i][3])
    cur = (upto[-1][4] - o) * s
    return {"kecil": False, "s": s, "open": o, "peak": peak, "peak_min": int((upto[peak_i][0] - t0).total_seconds() // 60),
            "now": cur, "keep": cur / peak if peak > 0 else 0.0, "mins": mins,
            "last": bars[-1][4], "last_move": (bars[-1][4] - o) * s}


def bucket(keep: float, mins: int, nfp: bool, btc: bool = False) -> tuple[dict | None, str]:
    keys = (("btc", "berita BTC"),) if btc else ((("nfp", "NFP") if nfp else ("semua", "berita")), ("semua", "berita"))
    for key, name in keys:
        for c in (STATS.get(key) or {}).get(str(mins)) or []:
            if c["lo"] <= keep < c["hi"] and c["n"] >= 10:
                return c, name
    return None, ""


def _amt(x: float, btc: bool) -> str:
    return f"{abs(x):,.0f}".replace(",", ".") if btc else _usd(abs(x)).lstrip("+−")


def row(m: dict, title: str, t0: datetime, now: datetime | None = None, asset: str = "XAU") -> dict | None:
    """Baris kartu 🎯. Sebelum menit 60: hitung mundur ke titik penentuan; sesudahnya: kesimpulan riwayat."""
    if m.get("kecil"):
        return None
    btc = asset == "BTC"
    nama = "BTC" if btc else "Emas"
    w = t0 + WIB
    arah = "NAIK" if m["s"] > 0 else "TURUN"
    balik_kata = "turun lagi" if m["s"] > 0 else "naik lagi"
    kembali = max(0.0, m["peak"] - m["now"])
    pct_kembali = _pct(min(max(1 - m["keep"], 0.0), 9.99))
    gerak = (f"{nama} {arah.lower()} {_amt(m['peak'], btc)} (puncak menit {m['peak_min']}), lalu {balik_kata} "
             f"{_amt(kembali, btc)} = {pct_kembali}% kembali")
    if m["mins"] < 60:
        sisa_menit = max(0, int((t0 + timedelta(minutes=60) - (now or t0)).total_seconds() // 60))
        hint = ""
        if m["mins"] == 30:
            c30, _ = bucket(m["keep"], 30, "Non-Farm" in title, btc)
            if c30:
                hint = f" • riwayat di menit 30 dengan kondisi ini: masih {arah.lower()} 6 jam {_pct(c30['h6'])}%"
        return {"label": f"⏳ Lonjakan {nama} {w:%H:%M} WIB: penentuan di menit 60", "teks": f"{sisa_menit} menit lagi",
                "kuat": False, "bukti": gerak + hint + " • bila ≥ 70% sudah kembali di menit 60 → biasanya balik "
                "melewati harga rilis", "pudar": True}
    nfp = "Non-Farm" in title
    c, grp = bucket(m["keep"], m["mins"], nfp, btc)
    if not c:
        return None
    arah = "NAIK" if m["s"] > 0 else "TURUN"
    balik = "TURUN" if m["s"] > 0 else "NAIK"
    p6 = c["h6"]
    pb = c.get("baru_h6")
    fade = c["fade"]
    if fade >= 0.8 and m["keep"] < 0.6:
        # peringatan utama: harga hampir selalu kembali melewati harga rilis (2 Okt 2026: NFP 93%, terjadi)
        sisi = "ke bawah" if m["s"] > 0 else "ke atas"
        teks, kuat = f"{_pct(fade)}% BALIK {'🔴' if m['s'] > 0 else '🟢'}", True     # pendek: muat di kanan kartu
    elif p6 >= 0.6:
        teks, kuat = f"{_pct(p6)}% tetap {arah} {'🟢' if arah == 'NAIK' else '🔴'}", pb is None or pb >= 0.55
        if not kuat:
            teks = f"{_pct(p6)}% tetap {arah.lower()} ⚪"
    elif p6 <= 0.4:
        teks, kuat = f"{_pct(1 - p6)}% BERBALIK {balik} {'🔴' if balik == 'TURUN' else '🟢'}", pb is None or pb <= 0.45
        if not kuat:
            teks = f"{_pct(1 - p6)}% berbalik {balik.lower()} ⚪"
    else:
        teks, kuat = f"≈ 50:50 ⚪ ({_pct(p6)}% tetap {arah.lower()})", False
    # 14 Okt (pengguna "intinya saja singkat jelas padat"): rincian lonjakan pindah ke bukti
    label = (f"{'📈' if m['keep'] >= 0.6 else '📉'} Setelah {nama} {w:%H:%M} WIB, 6 jam"
             + (f" (ke bawah harga rilis {m['open']:,.0f})" if m['s'] > 0 else f" (ke atas harga rilis {m['open']:,.0f})"
                ).replace(",", ".") * (fade >= 0.8 and m["keep"] < 0.6))
    kel = {"sudah berbalik": "sudah melewati harga rilis", "sisa < 30%": "≥ 70% kembali",
           "sisa 30–60%": "40–70% kembali", "sisa ≥ 60%": "< 40% kembali"}.get(c["label"], c["label"])
    per = STATS.get("btc_periode" if btc else "periode", "")
    bukti = (f"{gerak} • sekarang {_amt(m['last_move'], btc)} {'di atas' if m['last_move'] * m['s'] >= 0 else 'di bawah'} "
             f"harga rilis • riwayat {c['n']} lonjakan {grp} {per} yang {kel}: masih {arah.lower()} 3 jam "
             f"{_pct(c['h3'])}% • 6 jam {_pct(p6)}%"
             + (f" (sejak Okt 2021: {_pct(pb)}%)" if pb is not None else "")
             + f" • berbalik lewat harga rilis ≤ 6 jam {_pct(c['fade'])}% • tren besar TIDAK menentukan (diuji)")
    return {"label": label, "teks": teks, "kuat": kuat, "bukti": bukti, "pudar": True}


def _bars_cached(store, now: datetime, fetch, key: str = "pudar") -> tuple[list[tuple], float | None]:
    cached = {}
    if store is not None:
        try:
            cached = store.get_state(key) or {}
        except Exception:  # noqa: BLE001
            cached = {}
    if cached.get("t") and now - datetime.fromisoformat(cached["t"]) < TTL and cached.get("bars"):
        bars = cached["bars"]
        atr = cached.get("atr")
    else:
        bars, atr = fetch()
        if store is not None and bars:
            try:
                store.save_state({"t": now.isoformat(), "bars": bars, "atr": atr}, key)
            except Exception:  # noqa: BLE001
                pass
        if not bars:
            bars, atr = cached.get("bars") or [], cached.get("atr")
    return [(datetime.fromisoformat(b[0]), *b[1:]) for b in bars], atr


def fetch_twelvedata(api_key: str, symbol: str = "XAU/USD"):
    """() -> ([[iso, o, h, l, c]] 5 menit, ATR 14 hari) dari Twelve Data (2 kredit)."""
    import _core

    def fn():
        td = _core.TwelveData(api_key, symbol)
        b5 = td.candles(90, "5min")
        d1 = td.candles(16, "1day")
        rng = [b.h - b.l for b in d1[:-1]][-14:]
        atr = sum(rng) / len(rng) if rng else None
        return [[b.t.isoformat(), b.o, b.h, b.l, b.c] for b in b5], atr
    return fn


def attach(persiapan: dict, store, now: datetime, fetch, fetch_btc=None) -> None:
    """Tambah baris 📉/📈 ke skenario berita yang rilis 30 menit – 6 jam lalu (satu baris per waktu rilis)."""
    cards = [c for c in persiapan.get("berita") or [] if c.get("released")]
    due = {}
    for c in cards:
        try:
            t0 = datetime.fromisoformat(c["time"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        if timedelta(0) <= now - t0 <= WINDOW:
            key = c["time"]
            if key not in due or "Non-Farm" in c.get("title", ""):
                due[key] = (c, t0)
    if not due:
        return
    bars, atr = _bars_cached(store, now, fetch)
    if not bars:
        return
    for c, t0 in due.values():
        m = measure(bars, t0, now, atr)
        r = row(m, c.get("title", ""), t0, now) if m else None
        if r:
            c["pudar"] = r
            c.setdefault("skenario", []).insert(0, r)
    if fetch_btc is None or not STATS.get("btc"):
        return
    bbars, batr = _bars_cached(store, now, fetch_btc, "pudar_btc")
    for c, t0 in due.values():
        m = measure(bbars, t0, now, batr, STATS.get("btc_min_pct", 0.0015)) if bbars else None
        r = row(m, c.get("title", ""), t0, now, "BTC") if m else None
        if r:
            c["pudar_btc"] = r
            c.setdefault("skenario", []).insert(1 if c.get("pudar") else 0, r)
