"""Statistik WR & profit per kategori sinyal, per tahun (python -m research.badge_stats).

XAU: Donchian 3 set, skema F, lewati 3 candle setelah buka; kategori di candle sinyal:
  konf+⭐ (keduanya), konf (konfluensi 3/3 saja), ⭐ (tren D1 + breakout H4 saja), biasa.
BTC: sama, 2016-2026. Hasil dipakai sebagai angka WR/profit di sinyal cloud (cloud/api/_core.py STATS).
"""
import warnings

import numpy as np
import pandas as pd

from .filters import features
from .gap_study import week_info
from .strategy_lab import Bars, markets
from .strategy_lab2 import STAR, backtest_f, signals, trend_states

warnings.filterwarnings("ignore")


def categorized(b, skip_open=True):
    f = features(b.df)
    since = week_info(b.df)[0]
    s = trend_states(b)
    out = []
    for li, si, lo, so in signals(b, "donchian"):
        for t_in, t_out, r, d in backtest_f(b, li, si, lo, so, 3.0, 5, 1.0,
                                             (lambda i, d: since[i] >= 3) if skip_open else None):
            i = b.t.get_loc(t_in) - 1
            star = bool(STAR(f, i, d))
            konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
            cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
            out.append((t_in, cat, r))
    return pd.DataFrame(out, columns=["t", "cat", "R"])


def main():
    for m in markets():
        if m.name not in ("XAUUSD", "BTCUSD"):
            continue
        df = categorized(Bars(m.h1, m.spread), m.name == "XAUUSD")
        df["y"] = df.t.dt.year
        print(f"\n### {m.name} {df.y.min()}-{df.y.max()}")
        for cat, g in df.groupby("cat"):
            yrs = g.groupby("y").R.sum()
            yw = g.groupby("y").R.apply(lambda v: (v > 0).mean() * 100)
            print(f"  {cat:7s} n={len(g):4d} WR={np.mean(g.R > 0) * 100:4.1f}% rata={g.R.mean():+.3f}R "
                  f"tahun untung {(yrs > 0).sum()}/{len(yrs)} | " +
                  " ".join(f"{y % 100:02d}:{w:.0f}%/{t:+.0f}" for y, w, t in zip(yrs.index, yw, yrs)))


if __name__ == "__main__":
    main()
