"""Filter ⭐ di cloud harus identik dengan research/filters.py (tren D1 + breakout H4)."""
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from research.filters import FILTERS, features
from test_cloud import FakePrices, FakePub, FakeStore, to_bars

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402

STAR = FILTERS["KOMBINASI: tren D1 + H4 breakout"]


def market(days=260, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-06", periods=days * 24, freq="1h", tz="UTC")
    idx = idx[idx.dayofweek < 5]                                # tanpa akhir pekan, seperti data asli
    close = 2600 + np.cumsum(rng.standard_t(4, len(idx)) * 2.5 + 0.15)
    open_ = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.normal(0, 1.5, (2, len(idx))))
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wick[0],
                         "low": np.minimum(open_, close) - wick[1], "close": close}, index=idx)


def test_star_check_matches_research_filter():
    df = market()
    f = features(df)
    bars = to_bars(df)
    checked = agree_true = 0
    for i in range(24 * 60, len(df), 5):
        for d, name in ((1, "BUY"), (-1, "SELL")):
            want = bool(STAR(f, i, d))
            got, _ = _core.star_check(bars[:i + 1], name)
            assert got == want, (df.index[i], name)
            checked += 1
            agree_true += got
    assert checked > 1000 and agree_true > 30


def test_star_only_skips_non_star_signals_and_marks_star():
    df = market(seed=11)
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = df.index[24 * 60].to_pydatetime() + timedelta(minutes=2)
    end = df.index[-1].to_pydatetime()
    cfg = {**_core.CFG, "star_only": True, "profit_only": False}
    while now <= end:
        prices.now = now
        _core.tick(now, prices, store, pub, cfg)
        now += timedelta(minutes=30)
    signals = [e for e in pub.events if e["type"] == "signal"]
    skipped = [p for k, p in store.logs if k == "skip"]
    assert signals and skipped
    assert all(e["cat"] in ("XAU konf+⭐", "XAU ⭐") and "✗" not in e["star_note"] for e in signals)
    closes = {e["id"] for e in pub.events if e["type"] == "close"}
    assert closes <= {e["id"] for e in signals}                  # hanya sinyal ⭐ yang dikelola & ditutup


def test_all_mode_marks_star_and_close_carries_it():
    df = market(seed=11)
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = df.index[24 * 60].to_pydatetime() + timedelta(minutes=2)
    end = df.index[-1].to_pydatetime()
    while now <= end:
        prices.now = now
        _core.tick(now, prices, store, pub, {**_core.CFG, "profit_only": False})
        now += timedelta(minutes=30)
    signals = {e["id"]: e for e in pub.events if e["type"] == "signal"}
    assert {e["cat"] for e in signals.values()} >= {"XAU biasa"} and len({e["cat"] for e in signals.values()}) >= 2
    assert all(isinstance(e["star"], bool) for e in signals.values())
    closes = [e for e in pub.events if e["type"] == "close"]
    assert closes and all(c["star"] == signals[c["id"]]["star"] for c in closes)


def test_profit_only_sends_only_money_categories():
    df = market(seed=11)
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = df.index[24 * 60].to_pydatetime() + timedelta(minutes=2)
    while now <= df.index[-1].to_pydatetime():
        prices.now = now
        _core.tick(now, prices, store, pub, _core.CFG)            # default: hanya sinyal 💰
        now += timedelta(minutes=30)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig and all(e["cat"] in ("XAU konf+⭐", "XAU konf") and e["badge"].startswith("💰") for e in sig)
    assert any(p["why"] == "XAU biasa" for k, p in store.logs if k == "skip")
