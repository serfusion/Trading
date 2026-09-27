"""Uji ketahanan fitur SMC sebagai FILTER trend Donchian H1 (python -m research.trend_filters).

Dari research.smc_models: semua model entry SMC rugi, tetapi dua konsep SMC/ICT tampak membantu
trend: (1) killzone/sesi (breakout di jam London/NY) dan (2) bias struktur H4 (BOS terakhir searah).
Supaya bukan kebetulan, filter diuji di:
- 76 varian parameter Donchian (entry 30-100, exit 10-30, SL 2-3,5 ATR) di 3 periode;
- beberapa definisi jendela waktu & panjang swing;
- skema F-ensemble yang dipakai bot (3 set, 5 posisi, TP1 1R, SL+), per periode dan per tahun.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .data import resample
from .smc_models import Frame, donchian_sigs, periods, run, stats, structure

SESSIONS = {
    "killzone London+NY (02-05, 07-11 NY)": [(120, 300), (420, 660)],
    "sesi London+NY penuh (02-12 NY)": [(120, 720)],
    "tanpa sesi Asia (bukan 18-02 NY)": [(120, 1080)],
}
ENSEMBLE = [(40, 15), (55, 20), (80, 30)]


def session_keep(fr: Frame, windows):
    close_min = (fr.mins + fr.tf) % 1440
    ok = np.zeros(fr.n, dtype=bool)
    for a, b in windows:
        ok |= (close_min > a) & (close_min <= b)
    return lambda i, d: bool(ok[i])


def bias_keep(fr: Frame, df: pd.DataFrame, rule: str, minutes: int, length: int):
    htf = resample(df, rule)
    bias = fr.map_htf(structure(Frame(htf, minutes), length)[1], htf, minutes)
    return lambda i, d: bias[i] == d


def both(*keeps):
    return lambda i, d: all(k(i, d) for k in keeps)


def main() -> None:
    frames = {p: (Frame(df, 60), df, sp) for p, (df, sp) in periods("H1").items()}
    filters = {"tanpa filter": lambda fr, df: None}
    for name, win in SESSIONS.items():
        filters[name] = lambda fr, df, win=win: session_keep(fr, win)
    for length in (2, 3, 5):
        filters[f"bias struktur H4 (swing {length})"] = lambda fr, df, n=length: bias_keep(fr, df, "240min", 240, n)
    filters["bias struktur D1 (swing 3)"] = lambda fr, df: bias_keep(fr, df, "1440min", 1440, 3)
    filters["killzone + bias H4"] = lambda fr, df: both(session_keep(fr, SESSIONS[next(iter(SESSIONS))]),
                                                        bias_keep(fr, df, "240min", 240, 3))

    keeps = {p: {f: fn(fr, df) for f, fn in filters.items()} for p, (fr, df, _) in frames.items()}

    # 1) grid 76 varian, 1 posisi, keluar channel
    grid = [(ne, nx, sa) for ne, nx, sa in itertools.product([30, 40, 55, 70, 100], [10, 15, 20, 30],
                                                             [2.0, 2.5, 3.0, 3.5]) if nx < ne]
    rows = []
    for ne, nx, sa in grid:
        for p, (fr, df, sp) in frames.items():
            for f in filters:
                sigs, ex = donchian_sigs(fr, ne, nx, sa, keep=keeps[p][f])
                r, _ = run(fr, sigs, sp, ex)
                rows.append({"var": (ne, nx, sa), "period": p, "filter": f, "avg": r.mean(), "sum": r.sum(), "n": len(r)})
    g = pd.DataFrame(rows)
    base = g[g["filter"] == "tanpa filter"].set_index(["var", "period"])
    print(f"1) {len(grid)} varian Donchian H1 (1 posisi, keluar channel)")
    print(f"{'filter':42s} | positif di 3 periode | lebih baik dari tanpa filter (rata-rata R/trade) per periode | total R rata-rata per periode")
    for f in filters:
        x = g[g["filter"] == f].set_index(["var", "period"])
        pos_all = (x["avg"].unstack() > 0).all(axis=1).mean() * 100
        better = {p: (x["avg"].xs(p, level=1) > base["avg"].xs(p, level=1)).mean() * 100 for p in frames}
        tot = {p: x["sum"].xs(p, level=1).mean() for p in frames}
        print(f"{f:42s} | {pos_all:5.0f}% | " + " ".join(f"{p} {v:4.0f}%" for p, v in better.items())
              + " | " + " ".join(f"{p} {v:+6.1f}R" for p, v in tot.items()))

    # 2) skema F-ensemble bot
    print("\n2) Skema F-ensemble bot (3 set 40/15, 55/20, 80/30; 5 posisi; TP1 1R; SL+), R per sinyal / 3 set")
    for f in filters:
        cells, yearly = [], {}
        for p, (fr, df, sp) in frames.items():
            rs, ts = [], []
            for ne, nx in ENSEMBLE:
                sigs, ex = donchian_sigs(fr, ne, nx, 3.0, keep=keeps[p][f])
                r, t = run(fr, sigs, sp, ex, f_legs=5, tp1_r=1.0)
                rs.append(r / 3)
                ts.append(t)
            r, t = np.concatenate(rs), ts[0].append(ts[1:])
            order = np.argsort(t.asi8, kind="stable")        # urut waktu keluar -> drawdown kronologis
            r, t = r[order], t[order]
            s = stats(r)
            cells.append(f"{p}: n={s['n']:4d} win={s['win']:4.1f}% {s['avg']:+.3f}R PF={s['pf']:.2f} "
                         f"total {s['sum']:+6.1f}R DD {s['dd']:+5.1f}R")
            for y, v in pd.Series(r, index=t).groupby(t.year).sum().items():
                yearly[y] = v
        yrs = pd.Series(yearly)
        print(f"{f:42s} {' | '.join(cells)}")
        print(f"{'':42s} tahun positif {int((yrs > 0).sum())}/{len(yrs)}: "
              + " ".join(f"{y}:{v:+.1f}" for y, v in yrs.items()))


if __name__ == "__main__":
    main()
