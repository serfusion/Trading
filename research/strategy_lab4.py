"""Cek silang: apakah filter terbaik 2021-2026 juga terbaik di periode lama? (python -m research.strategy_lab4)"""
import warnings

import pandas as pd

from . import strategy_lab3 as lab3
from .strategy_lab import Bars, markets

warnings.filterwarnings("ignore", category=UserWarning)
WINDOWS = {"XAUUSD": [("2012-11-15", "2016-01-01"), ("2016-01-01", "2019-01-01"), ("2019-01-01", "2021-01-01")],
           "BTCUSD": [("2016-01-01", "2018-07-01"), ("2018-07-01", "2021-01-01")]}


def main():
    for m in markets():
        if m.name not in WINDOWS:
            continue
        b = Bars(m.h1, m.spread)
        for filt in ("-", "⭐", "konf", "⭐ atau konf"):
            lab3.START = pd.Timestamp("2000-01-01", tz="UTC")
            tr = lab3.run(b, "donchian", filt)
            for a, z in WINDOWS[m.name]:
                a_, z_ = pd.Timestamp(a, tz="UTC"), pd.Timestamp(z, tz="UTC")
                lab3.report(f"{m.name} {a[:4]}-{z[:4]} filter {filt}", [x for x in tr if a_ <= x[0] < z_])


if __name__ == "__main__":
    main()
