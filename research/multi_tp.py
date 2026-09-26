"""Uji skema multi-TP + SL+ pada sinyal TREND H1 (python -m research.multi_tp).

Entry & keluar channel sama dengan modul trend. Posisi dipecah jadi beberapa bagian dengan
TP berbeda; setelah TP tertentu tercapai, SL sisa posisi dinaikkan (SL+). Konservatif: bila SL
dan TP di bar yang sama -> SL dulu; di bar entry TP tidak dihitung.
"""
import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .data import resample
from .run_scan import dataset


def simulate(h1: pd.DataFrame, spread: float, legs: list, sl_steps: dict,
             n_entry=55, n_exit=20, stop_atr=3.0):
    """legs: list TP dalam R (None = runner, keluar di channel). sl_steps: {jumlah_TP_tercapai: SL_baru_dalam_R}."""
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(h1, 20)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    results, i = [], n_entry + 2
    while i < len(c) - 2:
        d = 1 if c[i] > hi_e[i] else (-1 if c[i] < lo_e[i] else 0)
        if d == 0:
            i += 1
            continue
        entry = o[i + 1] + (spread if d > 0 else 0.0)
        risk = stop_atr * a[i]
        sl = entry - d * risk
        open_legs = list(range(len(legs)))
        pnl, hits, j = 0.0, 0, i + 1
        adj = spread if d < 0 else 0.0
        while open_legs and j < len(c) - 1:
            if (l[j] <= sl) if d > 0 else (h[j] + adj >= sl):
                px = sl if j == i + 1 else (min(sl, o[j]) if d > 0 else max(sl, o[j] + adj))
                pnl += sum((px - entry) * d for _ in open_legs)
                open_legs = []
                break
            if j > i + 1:
                for k in list(open_legs):
                    tp = legs[k]
                    if tp is not None and ((h[j] >= entry + d * tp * risk) if d > 0 else (l[j] + adj <= entry - tp * risk)):
                        pnl += tp * risk
                        open_legs.remove(k)
                        hits += 1
                        if hits in sl_steps:
                            sl = entry + d * sl_steps[hits] * risk
            runner = [k for k in open_legs if legs[k] is None]
            if runner and ((d > 0 and c[j] < lo_x[j]) or (d < 0 and c[j] > hi_x[j])):
                px = o[j + 1] + adj
                pnl += sum((px - entry) * d for _ in runner)
                open_legs = [k for k in open_legs if k not in runner]
            j += 1
        # rata-rata R per unit lot (total dibagi jumlah bagian) supaya risiko awal sama = 1R
        results.append(pnl / risk / len(legs))
        i = j + 1
    return np.array(results)


def fmt(r):
    w = (r > 0).mean() * 100
    pf = r[r > 0].sum() / -r[r < 0].sum()
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return f"n={len(r):3d} win={w:4.1f}% total={r.sum():+6.1f}R rata={r.mean():+.3f}R PF={pf:.2f} DD={dd:+.1f}R"


def main():
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    sets = {"2012-17": (resample(m15[m15.index < cut], "60min"), 0.30),
            "2018-22": (resample(m15[m15.index >= cut], "60min"), 0.30),
            "2025-26": (resample(m5, "60min"), 0.25)}
    plans = {
        "A. Sekarang: 1 posisi, keluar di channel": ([None], {}),
        "B. Usulanmu: 2xTP1 1R, 2xTP2 2R, 1xTP3 3R, SL+ bertahap": ([1, 1, 2, 2, 3], {2: 0.1, 4: 1.0}),
        "C. 2xTP1 1R, 2xTP2 2R, 1 runner channel, SL+": ([1, 1, 2, 2, None], {2: 0.1, 4: 1.0}),
        "D. 1xTP1 1R, 1xTP2 2R, 3 runner channel, SL+ setelah TP1": ([1, 2, None, None, None], {1: 0.1}),
        "E. 1xTP 2R, 4 runner channel, SL+ setelah TP": ([2, None, None, None, None], {1: 0.1}),
    }
    for name, (legs, steps) in plans.items():
        print(name)
        for k, (d, sp) in sets.items():
            print(f"   {k}: {fmt(simulate(d, sp, legs, steps))}")


if __name__ == "__main__":
    main()
