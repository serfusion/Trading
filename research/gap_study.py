"""Sinyal di sekitar gap pembukaan pekan (python -m research.gap_study).

Apakah sinyal yang muncul di candle-candle pertama setelah pasar buka (Senin pagi WIB) perlu dilewati?
"""
import numpy as np

from xau_bot.smc import atr

from .filters import FILTERS, ensemble, features, periods
from .multi_tp import fmt

STAR = FILTERS["KOMBINASI: tren D1 + H4 breakout"]


def week_info(h1):
    t = h1.index
    gap_h = np.r_[99.0, (t[1:] - t[:-1]).total_seconds() / 3600.0]    # jam sejak candle sebelumnya
    since = np.zeros(len(t), int)
    gap_atr = np.zeros(len(t))
    a = np.asarray(atr(h1, 20), float)
    o, c = h1["open"].to_numpy(), h1["close"].to_numpy()
    last_open, g = -10**9, 0.0
    for i in range(len(t)):
        if gap_h[i] > 12:                                           # candle pertama setelah pasar tutup
            last_open = i
            g = abs(o[i] - c[i - 1]) / a[i - 1] if i else 0.0
        since[i] = i - last_open
        gap_atr[i] = g
    return since, gap_atr


def main():
    for k, (d, sp) in periods().items():
        f = features(d)
        since, gap = week_info(d)
        tests = {
            "semua sinyal": lambda f, i, dd: True,
            "lewati 1 candle pertama pekan": lambda f, i, dd: since[i] >= 1,
            "lewati 3 candle pertama pekan": lambda f, i, dd: since[i] >= 3,
            "lewati 6 jam pertama bila gap > 0.5 ATR": lambda f, i, dd: not (since[i] < 6 and gap[i] > 0.5),
            "⭐": STAR,
            "⭐ + lewati 3 candle pertama pekan": lambda f, i, dd: STAR(f, i, dd) and since[i] >= 3,
        }
        print(k)
        for name, fn in tests.items():
            print(f"   {name:42s} {fmt(ensemble(d, sp, f, fn))}")


if __name__ == "__main__":
    main()
