"""🔗 Emas pulih → kripto ikut naik (research/xau_kripto.py, docs/XAU_KRIPTO.md; permintaan pengguna 9 Okt 2026:
"xau turun sangat dalam lalu pullback ke atas → BTC & koin lain ikut naik serempak").

Aturan (dipilih dari riset, diuji 2018–2026):
  XAU jatuh dari puncak ke dasar ≥ 5 × ATR24 dalam 24 candle H1 terakhir, dasar ≤ 12 jam lalu, lalu close candle
  memantul ≥ 38,2% dari jarak jatuh (transisi: candle sebelumnya belum), dan korelasi return harian XAU–BTC 60 hari
  (s.d. kemarin) ≥ 0,2 → beli keranjang koin spot di harga saat itu, tahan 48 jam.
Teruji (keranjang 19 koin, biaya 0,2%): sejak Okt 2021 111 kejadian, naik 64%, rata +1,1% per 48 jam (beli kapan saja
pada kondisi korelasi sama: naik 46%, −0,2%); per pekan p-acak < 0,001; sebelum Okt 2021 51 kejadian, naik 63%, +1,3%
(dasar +0,9% → per kejadian p 0,29, tidak signifikan); 6 dari 7 tahun positif (2025 −0,5%). Rugi terburuk keranjang
−20% (BTC −10%). Ditemukan setelah melihat data 2026 (korelasi tinggi) → tetap info, bukan jaminan. Tanpa order
otomatis. BELUM disambung ke tick.py (menunggu "pasang"). State: baris Supabase 'pulih'.
Pesan ntfy: pulih_signal, pulih_close. Hanya library standar Python.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone

import _core

H1 = timedelta(hours=1)
N, K, R, W, HOLD = 24, 5.0, 0.382, 12, 48
CORR_HARI, CORR_MIN = 60, 0.2
KOIN = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK", "AVAX"]
TERUJI = {"baru": [111, 64, 1.11], "lama": [51, 63, 1.34], "tahun": "6/7 tahun +", "terburuk": -20.0,
          "dasar_baru": [46, -0.23]}
KEEP_CLOSED = 20


def atr_ewm(bars: list[_core.Bar], n: int = 24) -> list[float]:
    """Sama dengan research.xau_kripto.atr: EWMA alpha 1/n dari true range (seed = TR pertama)."""
    out, a = [], None
    for i, b in enumerate(bars):
        pc = bars[i - 1].c if i else b.c
        tr = max(b.h - b.l, abs(b.h - pc), abs(b.l - pc))
        a = tr if a is None else a + (tr - a) / n
        out.append(a)
    return out


def pantul(bars: list[_core.Bar], atr: list[float], t: int) -> dict | None:
    """Kejadian di candle t (sama dengan research.xau_kripto.kejadian tanpa jeda antar-kejadian)."""
    if t < N + 1:
        return None
    w0 = t - N + 1
    hs = [b.h for b in bars[w0:t + 1]]
    ih = w0 + hs.index(max(hs))
    if ih >= t:
        return None
    ls = [b.l for b in bars[ih:t + 1]]
    il = ih + ls.index(min(ls))
    if t - il > W or il == t:
        return None
    top, bot = bars[ih].h, bars[il].l
    jarak = top - bot
    if jarak <= 0 or jarak / atr[ih] < K:
        return None
    lvl = bot + R * jarak
    if bars[t].c >= lvl and bars[t - 1].c < lvl:
        return {"top": top, "bot": bot, "atr_x": jarak / atr[ih], "level": lvl}
    return None


def korelasi(xau: list[_core.Bar], btc_daily: dict, hari: str) -> float | None:
    """Korelasi return harian XAU vs BTC 60 baris terakhir, persis seperti research.xau_kripto (pandas 3): return hanya
    dari dua tanggal kalender BERURUTAN yang sama-sama punya data (Senin, hari setelah libur → tidak dipakai), lalu
    nilai 'per tanggal' = korelasi baris SEBELUM baris tanggal itu (shift 1, ffill ke tanggal kejadian)."""
    xd: dict[str, float] = {}
    for b in xau:
        xd[b.t.strftime("%Y-%m-%d")] = b.c
    pairs = []
    for d in sorted(xd):
        prev = (datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if prev in xd and d in btc_daily and prev in btc_daily:
            pairs.append((d, xd[d] / xd[prev] - 1, btc_daily[d] / btc_daily[prev] - 1))
    rows = [p for p in pairs if p[0] <= hari]
    if not rows:
        return None
    upto = rows[-1][0]                                  # baris terakhir ≤ tanggal kejadian; pakai baris SEBELUMNYA
    use = [p for p in pairs if p[0] < upto][-CORR_HARI:]
    if len(use) < CORR_HARI:
        return None
    n = len(use)
    mx = sum(x for _, x, _ in use) / n
    my = sum(y for _, _, y in use) / n
    sxy = sum((x - mx) * (y - my) for _, x, y in use)
    sx = sum((x - mx) ** 2 for _, x, _ in use) ** 0.5
    sy = sum((y - my) ** 2 for _, _, y in use) ** 0.5
    return sxy / (sx * sy) if sx > 0 and sy > 0 else None


def btc_harian(n: int = 100) -> dict:
    """Close harian BTC/USDT Binance (tanggal UTC → close)."""
    u = f"https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit={n}"
    rows = _core.http("GET", u, timeout=10) or []
    return {datetime.fromtimestamp(r[0] / 1000, timezone.utc).strftime("%Y-%m-%d"): float(r[4]) for r in rows}


def harga_koin(koin: list[str]) -> dict:
    syms = json.dumps([f"{c}USDT" for c in koin], separators=(",", ":"))
    u = "https://data-api.binance.vision/api/v3/ticker/price?symbols=" + urllib.request.quote(syms)
    rows = _core.http("GET", u, timeout=10) or []
    return {r["symbol"].removesuffix("USDT"): float(r["price"]) for r in rows}


def _pct(v: float) -> str:
    return f"{v:+.1f}%".replace(".", ",")


def pulih_tick(now: datetime, xau_bars: list[_core.Bar], store, pub, btc_daily=None, prices=None) -> dict:
    """Dipanggil tiap tick cloud. Idempoten. btc_daily()/prices(koin) bisa diganti (tes/replay)."""
    btc_daily = btc_daily or btc_harian
    prices = prices or harga_koin
    state = store.get_state() or {}
    closed_log = state.get("closed") or []
    events = []
    pos = state.get("open")
    # 1) tutup setelah 48 jam
    if pos and now >= _core.parse_iso(pos["deadline"]):
        try:
            px = prices(list(pos["entry"]))
            hasil = {c: (px[c] / e - 1) * 100 - 0.2 for c, e in pos["entry"].items() if c in px and e}
            avg = sum(hasil.values()) / len(hasil) if hasil else 0.0
            naik = sum(1 for v in hasil.values() if v > 0)
            ev = {"type": "pulih_close", "id": pos["id"], "symbol": "KRIPTO", "r_pct": round(avg, 2), "win": avg > 0,
                  "per_koin": {c: round(v, 2) for c, v in hasil.items()}, "naik": naik, "n": len(hasil),
                  "time": _core.iso(now)}
            best = sorted(hasil.items(), key=lambda x: -x[1])[:3]
            pub.publish(ev, f"48 jam selesai: jual keranjang. Rata-rata {_pct(avg)} setelah biaya; {naik}/{len(hasil)} "
                            f"koin naik. Terbaik: " + ", ".join(f"{c} {_pct(v)}" for c, v in best) + ".",
                        f"🔗 TUTUP keranjang kripto • {'PROFIT' if avg > 0 else 'MINUS'} {_pct(avg)}", 4, ["link"])
            closed_log = ([ev] + closed_log)[:KEEP_CLOSED]
            state["open"] = None
            pos = None
            events.append(f"pulih tutup {_pct(avg)}")
        except Exception as exc:  # noqa: BLE001 - coba lagi tick berikutnya
            events.append(f"pulih tutup gagal: {exc}")
    # 2) kejadian baru di candle XAU yang sudah tutup
    bars = [b for b in xau_bars if b.h > b.l and _core.market_open(b.t)]
    done = [b for b in bars if b.t + H1 <= now]
    if len(done) < 200:
        store.save_state({**state, "closed": closed_log})
        return {"ok": True, "events": events, "note": "candle XAU kurang"}
    last_seen = state.get("last_bar")
    new_idx = [i for i, b in enumerate(done) if last_seen is None or _core.iso(b.t) > last_seen]
    if last_seen is None:
        new_idx = new_idx[-1:]
    atr = atr_ewm(done)
    last_ev = state.get("last_ev")
    for i in new_idx:
        b = done[i]
        k = pantul(done, atr, i)
        if not k:
            continue
        if last_ev and sum(1 for x in done if _core.parse_iso(last_ev) < x.t <= b.t) <= N:
            continue                                   # jeda ≥ N candle antar-kejadian (sama dengan riset)
        last_ev = _core.iso(b.t)
        state["last_ev"] = last_ev
        if pos:
            continue
        try:
            daily = btc_daily()
            c = korelasi(done, daily, b.t.strftime("%Y-%m-%d"))
        except Exception as exc:  # noqa: BLE001
            events.append(f"pulih korelasi gagal: {exc}")
            continue
        if c is None or c < CORR_MIN:
            events.append(f"pulih dilewati: korelasi {c if c is None else round(c, 2)}")
            continue
        try:
            px = prices(KOIN)
        except Exception as exc:  # noqa: BLE001
            events.append(f"pulih harga gagal: {exc}")
            continue
        sid = f"PULIH-{b.t:%Y%m%d%H}"
        pos = {"id": sid, "entry": px, "time": _core.iso(now), "deadline": _core.iso(now + HOLD * H1)}
        state["open"] = pos
        t1 = TERUJI
        ev = {"type": "pulih_signal", "id": sid, "symbol": "KRIPTO", "dir": "BUY", "koin": px,
              "xau_top": round(k["top"], 2), "xau_bot": round(k["bot"], 2), "atr_x": round(k["atr_x"], 1),
              "korelasi": round(c, 2), "hold_h": HOLD, "deadline": pos["deadline"], "teruji": t1, "time": _core.iso(now)}
        text = (f"Emas jatuh {k['atr_x']:.1f} ATR ({k['top']:,.2f} → {k['bot']:,.2f}) lalu memantul; emas & BTC sedang "
                f"searah (korelasi 60 hari {c:.2f}). Beli spot keranjang " + ", ".join(KOIN[:5]) + " dst. bagi rata, "
                f"tahan {HOLD} jam. Teruji sejak Okt 2021: naik {t1['baru'][1]}% kejadian, rata "
                f"{_pct(t1['baru'][2])} (dasar {_pct(t1['dasar_baru'][1])}); rugi terburuk {t1['terburuk']:.0f}%.")
        pub.publish(ev, text, "🔗 EMAS PULIH → BELI KRIPTO • tahan 48 jam", 4, ["link"])
        events.append("pulih sinyal")
    state["last_bar"] = _core.iso(done[-1].t)
    state["closed"] = closed_log
    store.save_state(state)
    return {"ok": True, "events": events}
