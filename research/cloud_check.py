"""Simulasi versi cloud di data asli: tick tiap 30 menit, candle H1 berjalan dibangun dari M5.

python -m research.cloud_check
"""
import bisect
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .data import resample
from .run_scan import dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402


class HistPrices:
    """Candle H1 yang sudah tutup + candle H1 berjalan (dibangun dari M5 yang sudah tutup)."""

    def __init__(self, m5: pd.DataFrame):
        self.m5 = m5
        h1 = resample(m5, "60min")
        self.h1 = [_core.Bar(t.to_pydatetime(), r.open, r.high, r.low, r.close) for t, r in h1.iterrows()]
        self.times = [b.t for b in self.h1]
        self.now = None

    def candles(self, n):
        hour = self.now.replace(minute=0, second=0, microsecond=0)
        done = self.h1[:bisect.bisect_left(self.times, hour)]
        part = self.m5[(self.m5.index >= hour) & (self.m5.index + pd.Timedelta(minutes=5) <= self.now)]
        if len(part):
            done = done + [_core.Bar(hour, part.open.iloc[0], part.high.max(), part.low.min(), part.close.iloc[-1])]
        return done[-n:]


class Store:
    def __init__(self):
        self.state = {}

    def get_state(self):
        return dict(self.state)

    def save_state(self, d):
        self.state = dict(d)

    def log(self, *a):
        pass

    def get_control(self):
        return {}


class Pub:
    def __init__(self):
        self.events = []

    def publish(self, ev, *a, **k):
        if ev["type"] in ("signal", "close"):
            self.events.append(ev)


def main():
    star = "--semua" not in sys.argv
    m5 = dataset("m5_2025")[0]
    prices, store, pub = HistPrices(m5), Store(), Pub()
    t = (m5.index[0] + pd.Timedelta(days=10)).to_pydatetime().replace(minute=2, second=0)
    end = m5.index[-1].to_pydatetime()
    while t <= end:
        prices.now = t
        _core.tick(t, prices, store, pub, {**_core.CFG, "star_only": star})
        t += timedelta(minutes=30)
    closes = [e for e in pub.events if e["type"] == "close"]
    print(f"Cloud F-ensemble {'⭐ saja' if star else 'semua sinyal'} (tick 30 menit) {m5.index[0]:%Y-%m-%d} -> {m5.index[-1]:%Y-%m-%d}")
    for name in sorted({e.get("set", "-") for e in closes}):
        r = [e["r"] for e in closes if e.get("set") == name]
        wins = sum(1 for x in r if x > 0)
        print(f"  {name}: {len(r)} sinyal | untung {wins} ({wins / len(r) * 100:.1f}%) | total {sum(r):+.1f}R")
    for tag, want in (("⭐", True), ("biasa", False)):
        r = [e["r"] for e in closes if e.get("star") is want]
        if r:
            wins = sum(1 for x in r if x > 0)
            print(f"  {tag}: {len(r)} sinyal | untung {wins} ({wins / len(r) * 100:.1f}%) | total {sum(r):+.1f}R | "
                  f"rata-rata {sum(r) / len(r):+.3f}R")
    r = [e["r"] for e in closes]
    wins = sum(1 for x in r if x > 0)
    print(f"  SEMUA: {len(r)} sinyal | untung {wins} ({wins / len(r) * 100:.1f}%) | total {sum(r):+.1f}R | "
          f"rata-rata {sum(r) / len(r):+.3f}R")


if __name__ == "__main__":
    main()
