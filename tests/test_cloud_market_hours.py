"""Candle saat pasar tutup & gap buka pekan (kasus Minggu 27 Sep 2026 22:02 UTC: BUY 4279,32 SL 4278,09)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from test_cloud import FakePrices, FakePub, FakeStore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402

UTC = timezone.utc


def test_new_york_time_matches_zoneinfo():
    from zoneinfo import ZoneInfo
    ny = ZoneInfo("America/New_York")
    t = datetime(2012, 1, 1, tzinfo=UTC)
    while t < datetime(2030, 1, 1, tzinfo=UTC):
        assert _core.new_york(t) == t.astimezone(ny).replace(tzinfo=None), t
        t += timedelta(minutes=97)


def test_market_open_summer_and_winter():
    t = lambda *a: datetime(*a, tzinfo=UTC)  # noqa: E731
    # musim panas (EDT): tutup Jumat 21:00 UTC, buka Minggu 22:00 UTC
    assert _core.market_open(t(2026, 9, 25, 20))            # Jumat 16:00 NY
    assert not _core.market_open(t(2026, 9, 25, 21))        # Jumat 17:00 NY
    assert not _core.market_open(t(2026, 9, 26, 12))        # Sabtu
    assert not _core.market_open(t(2026, 9, 27, 21))        # Minggu 17:00 NY (candle sinyal yang salah)
    assert _core.market_open(t(2026, 9, 27, 22))            # Minggu 18:00 NY
    assert not _core.market_open(t(2026, 9, 29, 21))        # Selasa 17:00 NY: jeda harian
    # musim dingin (EST): buka Minggu 23:00 UTC
    assert not _core.market_open(t(2026, 1, 4, 22))
    assert _core.market_open(t(2026, 1, 4, 23))
    assert _core.market_open(t(2026, 1, 9, 21))             # Jumat 16:00 NY


def feed(weekend_jump=True):
    """H1 feed ala Twelve Data: tren turun pelan di hari kerja, candle datar di akhir pekan,
    lalu candle 'pra-buka' Minggu 21:00 UTC melonjak, dan pasar buka gap turun."""
    bars, t, px = [], datetime(2026, 8, 3, 0, tzinfo=UTC), 4400.0
    rng = np.random.default_rng(1)
    while t < datetime(2026, 9, 28, 3, tzinfo=UTC):
        weekend = not _core.market_open(t)
        if weekend:
            o = c = px
            h, l = px + 0.2, px - 0.2                          # noqa: E741
            if weekend_jump and t == datetime(2026, 9, 27, 21, tzinfo=UTC):
                c = h = px + 1.5                               # kuotasi pra-buka
        else:
            if t == datetime(2026, 9, 27, 22, tzinfo=UTC):
                px -= 12                                       # gap turun saat buka
            o = px
            c = px + rng.normal(-0.3, 3)
            h, l = max(o, c) + abs(rng.normal(0, 2)), min(o, c) - abs(rng.normal(0, 2))  # noqa: E741
        bars.append(_core.Bar(t, o, h, l, c))
        px = c
        t += timedelta(hours=1)
    return bars


def run(cfg, bars, guard=True):
    if not guard:
        orig = _core.atr_last
        _core.atr_last = lambda b, n: orig(b, n) if n != 120 else 0.0
    prices, store, pub = FakePrices(bars), FakeStore(), FakePub()
    prices.now = datetime(2026, 9, 27, 22, 2, tzinfo=UTC)
    try:
        _core.tick(prices.now, prices, store, pub, cfg)
    finally:
        if not guard:
            _core.atr_last = orig
    return [e for e in pub.events if e["type"] == "signal"], store


def test_bug_reproduced_without_market_hours():
    signals, _ = run({**_core.CFG, "market_hours": False, "skip_open_bars": 0}, feed(), guard=False)
    assert signals and signals[0]["dir"] == "BUY"
    assert signals[0]["risk_points"] < 3                     # SL super dekat karena ATR dari candle datar


def test_no_signal_from_closed_market_bars():
    signals, _ = run(_core.CFG, feed())
    assert signals == []


def test_since_week_open_and_skip():
    bars = [b for b in feed(False) if _core.market_open(b.t)]
    first = next(i for i, b in enumerate(bars) if b.t == datetime(2026, 9, 27, 22, tzinfo=UTC))
    assert _core.since_week_open(bars[:first + 1]) == 0
    assert _core.since_week_open(bars[:first + 3]) == 2
    assert _core.since_week_open(bars[:first]) > 50


def test_stale_open_signal_is_voided():
    store, pub = FakeStore(), FakePub()
    store.state = {"systems": {"T40/15": {"last_bar": "2026-09-27T21:00:00+00:00", "virtual": {
        "id": "T40/15-BUY-202609272100", "dir": "BUY", "entry": 4279.32, "sl": 4278.09, "risk": 1.23,
        "tp1": 4280.54, "legs": 5, "be_done": False, "tp1_hit": False, "star": False,
        "bar_close": "2026-09-27T22:00:00+00:00"}}}}
    prices = FakePrices(feed(False))
    prices.now = datetime(2026, 9, 27, 22, 32, tzinfo=UTC)
    _core.tick(prices.now, prices, store, pub, _core.CFG)
    closes = [e for e in pub.events if e["type"] == "close"]
    assert len(closes) == 1 and closes[0]["void"] and closes[0]["r"] == 0.0
    assert store.state["systems"]["T40/15"].get("virtual") is None


def test_tiny_atr_guard_blocks_signal_even_without_market_filter():
    signals, _ = run({**_core.CFG, "market_hours": False, "skip_open_bars": 0}, feed())
    assert signals == []                                     # dulu: BUY dengan SL < $3
