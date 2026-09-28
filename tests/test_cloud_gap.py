"""Sinyal gap pekan forex (cloud/api/_gap.py)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _gap  # noqa: E402

UTC = timezone.utc
OPEN = datetime(2026, 9, 20, 21, tzinfo=UTC)          # Minggu 17:00 New York (EDT)


class Feed:
    def __init__(self, bars):
        self.bars, self.now = bars, None

    def candles(self, n):
        return [b for b in self.bars if b.t <= self.now][-n:]


class Store:
    def __init__(self):
        self.gap, self.logs = {}, []

    def get_gap_state(self):
        return dict(self.gap)

    def save_gap_state(self, d):
        self.gap = dict(d)

    def log(self, k, p):
        self.logs.append((k, p))


class Pub:
    def __init__(self):
        self.events = []

    def publish(self, ev, *a, **k):
        self.events.append(ev)


def series(gap, after=0.0, seed=3):
    """USD/JPY H1: 20 hari normal, tutup akhir pekan, buka dengan `gap`, lalu bergerak `after` per jam."""
    rng = np.random.default_rng(seed)
    bars, t, px = [], OPEN - timedelta(days=22), 150.0
    while t < OPEN + timedelta(hours=30):
        if not _gap.fx_open(t):
            t += timedelta(hours=1)
            continue
        if t == OPEN:
            px += gap
        o = px
        c = px + (after if t >= OPEN + timedelta(hours=1) else rng.normal(0, 0.08))
        bars.append(_core.Bar(t, o, max(o, c) + 0.05, min(o, c) - 0.05, c))
        px = c
        t += timedelta(hours=1)
    return bars


def run(bars, ticks):
    feed, store, pub = Feed(bars), Store(), Pub()
    for now in ticks:
        feed.now = now
        _gap.gap_tick(now, {"USD/JPY": feed}, store, pub)
    return pub.events, store


def test_big_gap_down_buy_then_tp_once():
    bars = series(gap=-1.5, after=+0.25)                     # gap turun besar, lalu harga menutup gap
    ticks = [OPEN + timedelta(hours=1, minutes=2 + 30 * i) for i in range(40)]
    ev, store = run(bars, ticks)
    sig = [e for e in ev if e["type"] == "signal"]
    cls = [e for e in ev if e["type"] == "close"]
    assert len(sig) == 1 and sig[0]["dir"] == "BUY" and sig[0]["badge"] == "⭐⭐⭐💸💸💸"
    assert sig[0]["sl"] < sig[0]["entry"] < sig[0]["tp"]
    assert len(cls) == 1 and cls[0]["r"] > 0 and "TP" in cls[0]["reason"]
    assert abs(sig[0]["point_value"] - 1000 / sig[0]["entry"]) < 1e-6


def test_stop_loss_when_gap_extends():
    bars = series(gap=+1.5, after=+0.3)                      # gap naik -> SELL, harga terus naik -> SL
    ev, _ = run(bars, [OPEN + timedelta(hours=1, minutes=2 + 30 * i) for i in range(40)])
    cls = [e for e in ev if e["type"] == "close"]
    assert cls and cls[0]["dir"] == "SELL" and abs(cls[0]["r"] + 1) < 1e-6


def test_small_gap_ignored_and_no_signal_outside_window():
    ev, _ = run(series(gap=-0.05), [OPEN + timedelta(hours=1, minutes=2)])
    assert not [e for e in ev if e["type"] == "signal"]
    ev, _ = run(series(gap=-1.5), [OPEN + timedelta(hours=5, minutes=2)])       # sudah lewat candle kedua
    assert not [e for e in ev if e["type"] == "signal"]
