"""Setelah TP1 kena: tahan 4 posisi running sampai TUTUP, atau ambil profit lebih awal? Per kategori sinyal.

python -m research.runner_kategori

Pertanyaan pengguna (28 Sep 2026): sinyal SELL format lama (kategori "⭐ saja", tidak dikirim lagi sejak ada 💰)
sudah TP1 dan profit; apakah 4 posisi running lebih baik ditutup lebih awal?

Mesin = research/sl_tangga.py (sama dengan cloud: 3 set Donchian H1, SL 3xATR, 5 posisi, SL+ entry+0,1R setelah
TP1, satu posisi per set, XAU lewati 3 candle setelah buka pekan), hanya kategori yang dipilih dikirim.
Semua varian identik sampai TP1; yang berbeda hanya cara menutup 4 posisi running.

Varian (ditetapkan sebelum melihat hasil):
- bawaan: running sampai sinyal TUTUP / SL+
- semua ditutup di TP1 (5 posisi TP 1R)
- running ambil profit di 2R / di 3R
- bawaan + SL bertangga 1R (2R -> SL 1R, 3R -> SL 2R, ...)
- bawaan + trailing 3 ATR setelah TP1
"""
from __future__ import annotations

import pandas as pd

from .eksternal import SPLIT, asset
from .filters import features
from .gap_study import week_info
from .sl_tangga import backtest, summary
from .strategy_lab2 import STAR, signals, trend_states

VARIANTS = {
    "bawaan: running sampai TUTUP / SL+": dict(tps=[1.0, None, None, None, None]),
    "semua ditutup di TP1 (1R)": dict(tps=[1.0] * 5),
    "running ambil profit di 2R": dict(tps=[1.0, 2.0, 2.0, 2.0, 2.0]),
    "running ambil profit di 3R": dict(tps=[1.0, 3.0, 3.0, 3.0, 3.0]),
    "bawaan + SL bertangga 1R": dict(tps=[1.0, None, None, None, None], ladder=(1.0, 1.0)),
    "bawaan + trailing 3 ATR": dict(tps=[1.0, None, None, None, None], chand=3.0),
}
CATS = {"XAUUSD": ["konf+⭐", "konf", "⭐", "biasa"], "BTCUSD": ["konf+⭐", "konf", "⭐", "biasa"]}


def run(name: str, cat: str, variant: dict) -> pd.DataFrame:
    a = asset(name)
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))

    def allow(i, d):
        if name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        c = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return c == cat
    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest(b, li, si, lo, so, allow, **variant)
    return pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r"])


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        for cat in CATS[name]:
            print(f"\n=== {name} kategori {cat} (latih < {split:%Y}) ===")
            print(f"{'Cara menutup running':38s} {'sinyal':>6s} {'WR':>6s} {'R/sinyal':>9s} {'total':>8s} "
                  f"{'DD':>7s} {'latih':>7s} {'uji':>7s} tahun+  | sesudah TP1: n, R/sinyal")
            base = None
            for vname, v in VARIANTS.items():
                df = run(name, cat, v)
                st = summary(df, split)
                hit = df[df.max_r >= 1.0]
                if base is None:
                    base = st
                print(f"{vname:38s} {st['n']:6d} {st['wr']:5.1f}% {st['avg']:+9.3f} {st['tot']:+8.1f} "
                      f"{st['dd']:+7.1f} {st['latih']:+7.3f} {st['uji']:+7.3f} {st['tahun']:>6s}  | "
                      f"{len(hit)}, {hit.R.mean():+.3f}")
                if vname != next(iter(VARIANTS)):
                    better = (st["yr"] - base["yr"]).reindex(base["yr"].index).fillna(0)
                    print(f"{'':38s} vs bawaan per tahun: lebih baik {int((better > 0).sum())}/{len(better)}")


if __name__ == "__main__":
    main()
