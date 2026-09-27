"""Kajian filter entry & manajemen untuk skema F (python -m research.filters).

Setiap filter hanya memakai data yang sudah tertutup sebelum entry (tanpa bocoran masa depan).
Filter dianggap bagus hanya bila memperbaiki hasil di KETIGA periode.
"""
import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .data import resample
from .multi_tp import fmt
from .run_scan import dataset

SETS = [(40, 15), (55, 20), (80, 30)]


def features(h1: pd.DataFrame) -> dict:
    c = h1["close"]
    d1 = c.resample("1D").last().dropna()
    ema50d = d1.ewm(span=50).mean().shift(1).reindex(c.index, method="ffill")   # D1 kemarin
    d1_close = d1.shift(1).reindex(c.index, method="ffill")
    h4 = resample(h1, "240min")
    h4_hi = h4["high"].rolling(20).max().shift(1).reindex(c.index, method="ffill")
    h4_lo = h4["low"].rolling(20).min().shift(1).reindex(c.index, method="ffill")
    ema200 = c.ewm(span=200).mean()
    a = pd.Series(np.asarray(atr(h1, 20), float), index=c.index)
    a_rank = a.rolling(24 * 60).rank(pct=True)
    hi, lo = h1["high"], h1["low"]
    up = hi.diff()
    dn = -lo.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14).mean()
    pdi = 100 * pd.Series(pdm, index=c.index).ewm(alpha=1 / 14).mean() / atr14
    ndi = 100 * pd.Series(ndm, index=c.index).ewm(alpha=1 / 14).mean() / atr14
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1 / 14).mean()
    body = (c - h1["open"]).abs() / a
    return {k: np.asarray(v, float) if not isinstance(v, np.ndarray) else v for k, v in dict(
        c=c.to_numpy(), ema50d=ema50d, d1_close=d1_close, h4_hi=h4_hi, h4_lo=h4_lo, ema200=ema200,
        a_rank=a_rank, adx=adx, body=body, hour=c.index.hour, dow=c.index.dayofweek).items()}


FILTERS = {
    "tanpa filter (sekarang)": lambda f, i, d: True,
    "searah tren D1 (close D1 vs EMA50 D1)": lambda f, i, d: d * (f["d1_close"][i] - f["ema50d"][i]) > 0,
    "searah EMA200 H1": lambda f, i, d: d * (f["c"][i] - f["ema200"][i]) > 0,
    "H4 juga breakout 20 bar": lambda f, i, d: (f["c"][i] > f["h4_hi"][i]) if d > 0 else (f["c"][i] < f["h4_lo"][i]),
    "ADX H1 > 25": lambda f, i, d: f["adx"][i] > 25,
    "ADX H1 < 25 (kebalikan)": lambda f, i, d: f["adx"][i] < 25,
    "volatilitas normal (ATR pct 20-80)": lambda f, i, d: 0.2 <= f["a_rank"][i] <= 0.8,
    "volatilitas rendah (ATR pct < 50)": lambda f, i, d: f["a_rank"][i] < 0.5,
    "candle breakout tidak terlalu besar (<1.5 ATR)": lambda f, i, d: f["body"][i] < 1.5,
    "jam London-NY (07-20 UTC)": lambda f, i, d: 7 <= f["hour"][i] < 20,
    "bukan Jumat": lambda f, i, d: f["dow"][i] != 4,
    "KOMBINASI: tren D1 + H4 breakout": lambda f, i, d: (d * (f["d1_close"][i] - f["ema50d"][i]) > 0) and
        ((f["c"][i] > f["h4_hi"][i]) if d > 0 else (f["c"][i] < f["h4_lo"][i])),
}


def simulate(h1, spread, f, allow, legs, be_after, n_entry, n_exit, stop_atr=3.0, be_r=0.1):
    """Skema multi-posisi: legs = TP dalam R (None = runner). SL+ ke be_r setelah TP ke-be_after."""
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = np.asarray(atr(h1, 20), float)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    out, i = [], max(n_entry + 2, 24 * 60)
    while i < len(c) - 2:
        d = 1 if c[i] > hi_e[i] else (-1 if c[i] < lo_e[i] else 0)
        if d == 0 or not allow(f, i, d):
            i += 1
            continue
        entry = o[i + 1] + (spread if d > 0 else 0.0)
        risk = stop_atr * a[i]
        sl = entry - d * risk
        adj = spread if d < 0 else 0.0
        open_legs, pnl, hits, j = list(range(len(legs))), 0.0, 0, i + 1
        while open_legs and j < len(c) - 1:
            if (l[j] <= sl) if d > 0 else (h[j] + adj >= sl):
                px = sl if j == i + 1 else (min(sl, o[j]) if d > 0 else max(sl, o[j] + adj))
                pnl += (px - entry) * d * len(open_legs)
                open_legs = []
                break
            if j > i + 1:
                for k in list(open_legs):
                    tp = legs[k]
                    if tp is not None and ((h[j] >= entry + tp * risk) if d > 0 else (l[j] + adj <= entry - tp * risk)):
                        pnl += tp * risk
                        open_legs.remove(k)
                        hits += 1
                        if hits == be_after:
                            sl = entry + d * be_r * risk
            runner = [k for k in open_legs if legs[k] is None]
            if runner and ((d > 0 and c[j] < lo_x[j]) or (d < 0 and c[j] > hi_x[j])):
                pnl += (o[j + 1] + adj - entry) * d * len(runner)
                open_legs = [k for k in open_legs if legs[k] is not None]
                if not open_legs:
                    break
            j += 1
        out.append(pnl / risk / len(legs))
        i = j + 1
    return np.array(out)


def ensemble(h1, sp, f, allow, legs=(1, None, None, None, None), be_after=1, stop_atr=3.0):
    return np.concatenate([simulate(h1, sp, f, allow, list(legs), be_after, ne, nx, stop_atr)
                           for ne, nx in SETS]) / 3


def periods():
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    return {"2012-17": (resample(m15[m15.index < cut], "60min"), .30),
            "2018-22": (resample(m15[m15.index >= cut], "60min"), .30),
            "2025-26": (resample(m5, "60min"), .25)}


def main():
    data = {k: (d, sp, features(d)) for k, (d, sp) in periods().items()}
    print("=== FILTER ENTRY (skema F-ensemble) ===")
    for name, fn in FILTERS.items():
        print(name)
        for k, (d, sp, f) in data.items():
            print(f"   {k}: {fmt(ensemble(d, sp, f, fn))}")
    print("\n=== MANAJEMEN (tanpa filter) ===")
    allow = FILTERS["tanpa filter (sekarang)"]
    mgmt = {
        "F sekarang: TP1 1R x1, 4 runner, SL+ setelah TP1": ((1, None, None, None, None), 1, 3.0),
        "TP1 0.5R x1, 4 runner": ((0.5, None, None, None, None), 1, 3.0),
        "TP1 0.5R x2, 3 runner": ((0.5, 0.5, None, None, None), 1, 3.0),
        "TP1 1R x2, 3 runner": ((1, 1, None, None, None), 1, 3.0),
        "TP1 1R x1, TP2 2R x1, 3 runner": ((1, 2, None, None, None), 1, 3.0),
        "F dengan SL 2x ATR": ((1, None, None, None, None), 1, 2.0),
        "F dengan SL 4x ATR": ((1, None, None, None, None), 1, 4.0),
        "semua 5 runner, tanpa TP (A)": ((None,) * 5, 99, 3.0),
    }
    for name, (legs, be, st) in mgmt.items():
        print(name)
        for k, (d, sp, f) in data.items():
            print(f"   {k}: {fmt(ensemble(d, sp, f, allow, legs, be, st))}")


if __name__ == "__main__":
    main()
