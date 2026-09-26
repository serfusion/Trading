"""Simulasi versi cloud di data asli: tick tiap 30 menit, candle H1 berjalan dibangun dari M5.

python -m research.cloud_check
"""
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .data import resample
from .run_scan import dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402


class HistPrices:
    def __init__(self, m5: pd.DataFrame):
        self.m5 = m5
        self.now = None

    def candles(self, n):
        part = self.m5[self.m5.index + pd.Timedelta(minutes=5) <= self.now]   # hanya M5 yang sudah tutup
        h1 = resample(part.iloc[-(n + 2) * 12:], "60min")
        return [_core.Bar(t.to_pydatetime(), r.open, r.high, r.low, r.close) for t, r in h1.iloc[-n:].iterrows()]


class Store:
    def __init__(self):
        self.state = {}

    def get_state(self):
        return dict(self.state)

    def save_state(self, d):
        self.state = dict(d)

    def log(self, *a):
        pass


class Pub:
    def __init__(self):
        self.events = []

    def publish(self, ev, *a, **k):
        if ev["type"] in ("signal", "close"):
            self.events.append(ev)


def main():
    m5 = dataset("m5_2025")[0]
    prices, store, pub = HistPrices(m5), Store(), Pub()
    t = (m5.index[0] + pd.Timedelta(days=10)).to_pydatetime().replace(minute=2, second=0)
    end = m5.index[-1].to_pydatetime()
    while t <= end:
        prices.now = t
        _core.tick(t, prices, store, pub)
        t += timedelta(minutes=30)
    closes = [e for e in pub.events if e["type"] == "close"]
    r = [e["r"] for e in closes]
    wins = sum(1 for x in r if x > 0)
    print(f"Cloud (tick 30 menit) {m5.index[0]:%Y-%m-%d} -> {m5.index[-1]:%Y-%m-%d}: "
          f"{len(r)} sinyal selesai | benar {wins} ({wins / len(r) * 100:.1f}%) | total {sum(r):+.1f}R | "
          f"rata-rata {sum(r) / len(r):+.3f}R")


if __name__ == "__main__":
    main()
