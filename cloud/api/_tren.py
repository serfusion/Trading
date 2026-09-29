"""Status tren sekarang per indikator + seberapa sering arahnya benar di masa lalu (tab News aplikasi).

DESKRIPTIF, BUKAN RAMALAN: research/tren_kedepan.py (docs/RISET_DATA_EKSTERNAL.md bagian 16) — tidak ada indikator
yang konsisten lebih baik dari tebakan dasar ("selalu naik"). Persentase dari cloud/api/tren_stats.json (dibuat
research). Rumus di sini sama persis dengan research.tren_kedepan.price_predictors (tests/test_cloud_tren.py).
Hanya library standar Python.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATS = json.loads((Path(__file__).resolve().parent / "tren_stats.json").read_text(encoding="utf-8"))
NAN = float("nan")
ASSETS = {"XAU/USD": "XAUUSD", "BTC/USD": "BTCUSD"}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
MACRO = {"DFII10": "yield riil 10 th 20 hari (naik = bearish)",
         "DTWEXBGS": "dolar (DTWEXBGS) 20 hari (naik = bearish)"}


def _sign(x: float) -> float:
    return NAN if x != x else (1.0 if x > 0 else -1.0 if x < 0 else 0.0)


def _rolling_mean(x: list, n: int) -> list:
    out, s = [NAN] * len(x), 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def donchian_state(c: list, h: list, l: list, n_in: int, n_out: int) -> list:  # noqa: E741
    out, s = [], 0
    for i in range(len(c)):
        hi = max(h[i - n_in:i]) if i >= n_in else NAN
        lo = min(l[i - n_in:i]) if i >= n_in else NAN
        xhi = max(h[i - n_out:i]) if i >= n_out else NAN
        xlo = min(l[i - n_out:i]) if i >= n_out else NAN
        if c[i] > hi:
            s = 1
        elif c[i] < lo:
            s = -1
        elif s > 0 and c[i] < xlo:
            s = 0
        elif s < 0 and c[i] > xhi:
            s = 0
        out.append(s)
    return out


def supertrend(h: list, l: list, c: list, n: int = 10, mult: float = 3.0) -> list:  # noqa: E741
    pc = [c[0]] + c[:-1]
    tr = [max(h[i] - l[i], max(abs(h[i] - pc[i]), abs(l[i] - pc[i]))) for i in range(len(c))]
    atr = _rolling_mean(tr, n)
    mid = [(h[i] + l[i]) / 2 for i in range(len(c))]
    up = [mid[i] - mult * atr[i] for i in range(len(c))]
    dn = [mid[i] + mult * atr[i] for i in range(len(c))]
    out = [0] * len(c)
    trend, fu, fd = 1, up[0], dn[0]
    for i in range(1, len(c)):
        if atr[i] != atr[i]:
            continue
        fu = max(up[i], fu) if c[i - 1] > fu else up[i]
        fd = min(dn[i], fd) if c[i - 1] < fd else dn[i]
        if trend > 0 and c[i] < fu:
            trend = -1
        elif trend < 0 and c[i] > fd:
            trend = 1
        out[i] = trend
    return out


def rsi(c: list, n: int = 14) -> list:
    a = 1 / n
    out, up, dn = [NAN], NAN, NAN
    for i in range(1, len(c)):
        ch = c[i] - c[i - 1]
        u, d = max(ch, 0.0), max(-ch, 0.0)
        up = u if up != up else (1 - a) * up + a * u
        dn = d if dn != dn else (1 - a) * dn + a * d
        out.append(100 - 100 / (1 + up / dn) if dn else NAN)
    return out


def states(bars: list) -> dict:
    """bars: [(open, high, low, close)] harian urut waktu -> {indikator: +1 bullish / -1 bearish / 0}."""
    c = [b[3] for b in bars]
    h = [b[1] for b in bars]
    l = [b[2] for b in bars]  # noqa: E741
    i = len(c) - 1
    P = {}
    for n in (20, 60, 120, 250):
        P[f"momentum {n} hari"] = _sign(c[i] / c[i - n] - 1) if i >= n else NAN
    sma50, sma200 = _rolling_mean(c, 50), _rolling_mean(c, 200)
    P["close vs SMA50"] = _sign(c[i] - sma50[i])
    P["close vs SMA200"] = _sign(c[i] - sma200[i])
    P["SMA50 vs SMA200"] = _sign(sma50[i] - sma200[i])
    don = donchian_state(c, h, l, 55, 20)
    P["Donchian D1 55/20"] = don[i]
    st = supertrend(h, l, c)
    P["Supertrend D1"] = st[i]
    r = rsi(c)[i]
    P["RSI14 ekstrem (berbalik)"] = -1 if r > 70 else 1 if r < 30 else 0
    pc = [c[0]] + c[:-1]
    tr = _rolling_mean([max(h[k] - l[k], abs(h[k] - pc[k])) for k in range(len(c))], 14)
    dist = (c[i] - sma50[i]) / tr[i] if tr[i] == tr[i] and tr[i] else NAN
    P["> 3 ATR dari SMA50 (berbalik)"] = -1 if dist > 3 else 1 if dist < -3 else 0
    last_change, prev, flip = -999, 0, 0
    for k in range(len(c)):
        if don[k] != 0 and don[k] != prev:
            last_change, prev = k, don[k]
        flip = prev if (k - last_change) <= 5 and prev != 0 else 0
    P["pindah tren: Donchian D1 baru berbalik"] = flip
    cross = [_sign(c[k] - sma50[k]) for k in range(len(c))]
    xs = 0
    if i >= 6 and any(x != cross[i - 6] for x in cross[i - 5:i + 1]) and cross[i] != 0:
        xs = cross[i]
    P["pindah tren: baru menembus SMA50"] = xs
    five = [P["momentum 60 hari"], P["close vs SMA50"], P["close vs SMA200"], don[i], st[i]]
    s = sum(v for v in five if v == v)
    P["konsensus tren (≥4 dari 5)"] = 1 if s >= 3 else -1 if s <= -3 else 0
    return {k: 0 if v != v else int(v) for k, v in P.items()}


def macro_states(fetch=None) -> dict:
    """Yield riil & dolar AS: perubahan 20 observasi terakhir (naik = bearish emas), dari CSV publik FRED."""
    fetch = fetch or _fred
    out = {}
    for sid, key in MACRO.items():
        v = fetch(sid)
        sg = _sign(v[-1] - v[-21]) if len(v) > 21 else NAN
        out[key] = 0 if sg != sg else -int(sg)
    return out


def _fred(series: str) -> list:
    since = (datetime.now(timezone.utc) - timedelta(days=200)).date().isoformat()
    try:
        req = urllib.request.Request(FRED_CSV.format(series, since), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            rows = r.read().decode("utf-8").splitlines()[1:]
    except Exception:  # noqa: BLE001
        return []
    out = []
    for ln in rows:
        try:
            out.append(float(ln.partition(",")[2]))
        except ValueError:
            continue
    return out


def daily_bars(api_key: str, symbol: str, n: int = 320) -> list:
    """Candle harian Twelve Data (UTC) -> [(tanggal, open, high, low, close)]."""
    q = urllib.parse.urlencode({"symbol": symbol, "interval": "1day", "outputsize": n, "timezone": "UTC",
                                "order": "ASC", "apikey": api_key})
    with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    if data.get("status") != "ok":
        raise RuntimeError(f"Twelve Data: {data.get('message', 'tidak ada data')}")
    return [(v["datetime"][:10], float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]))
            for v in data["values"] if float(v["high"]) > float(v["low"])]


def build(asset: str, st: dict) -> dict:
    """Baris per jangka waktu, diurutkan dari indikator yang paling sering benar di atas tebakan dasar (periode
    terbaru); indikator tanpa pendapat (0) di bawah."""
    a = STATS["aset"][ASSETS[asset]]
    out = {"periode": a["periode"], "uji_mulai": a["uji_mulai"], "jangka": {}}
    for hz, j in a["jangka"].items():
        rows = []
        for key, s in j["indikator"].items():
            d = st.get(key, 0)
            row = {"nama": key, "arah": d}
            if d:
                x = s[str(d)]
                dasar = j["naik"] if d > 0 else round(100 - j["naik"], 1)
                dasar_uji = j["naik_uji"] if d > 0 else round(100 - j["naik_uji"], 1)
                row.update(n=x["n"], benar=x["benar"], n_uji=x["n_uji"], benar_uji=x["benar_uji"], dasar=dasar,
                           dasar_uji=dasar_uji, lebih=round((x["benar_uji"] or 0) - dasar_uji, 1))
            rows.append(row)
        rows.sort(key=lambda r: (r["arah"] != 0, r.get("lebih", -99), r.get("benar_uji") or 0), reverse=True)
        out["jangka"][hz] = {"naik": j["naik"], "naik_uji": j["naik_uji"], "baris": rows,
                             "bullish": sum(r["arah"] > 0 for r in rows), "bearish": sum(r["arah"] < 0 for r in rows)}
    return out


def compute(api_key: str, now: datetime, fred=None, bars_fn=daily_bars) -> dict:
    """{aset: {tanggal, harga, periode, jangka{...}}} untuk XAU/USD & BTC/USD; aset yang gagal dilewati."""
    macro = macro_states(fred)
    out = {"dihitung": now.isoformat(), "catatan": "Status sekarang, bukan ramalan. Persentase = seberapa sering "
           "arah indikator itu benar di masa lalu; tidak ada yang konsisten lebih baik dari tebakan dasar."}
    for asset in ASSETS:
        try:
            bars = bars_fn(api_key, asset)
        except Exception as exc:  # noqa: BLE001
            out[asset] = {"error": str(exc)}
            continue
        # candle hari ini belum tutup -> pakai sampai kemarin (sama dengan riset: close harian yang sudah selesai)
        today = now.date().isoformat()
        done = [b for b in bars if b[0] < today]
        st = states([b[1:] for b in done])
        if asset == "XAU/USD":
            st.update(macro)
        out[asset] = {"tanggal": done[-1][0], "harga": done[-1][4], **build(asset, st)}
    return out
