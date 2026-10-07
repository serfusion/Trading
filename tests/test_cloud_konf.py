"""Konfluensi di cloud harus identik dengan research/strategy_lab2.trend_states."""
import sys
from pathlib import Path

import numpy as np

from research.strategy_lab import Bars
from test_cloud import to_bars
from test_cloud_star import market

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
from research.strategy_lab2 import trend_states  # noqa: E402


def test_konf_matches_research():
    df = market(days=240, seed=7)
    s = trend_states(Bars(df, 0.3))
    bars = to_bars(df)
    checked = hits = 0
    for i in range(24 * 70, len(df), 13):
        for d, name in ((1, "BUY"), (-1, "SELL")):
            want = bool(s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d)
            assert _core.konf_check(bars[:i + 1], name) == want, (df.index[i], name)
            checked += 1
            hits += want
    assert checked > 300 and hits > 20


def test_badges():
    b = _core.badges("GAP USD/JPY")
    assert b["stars"] == 3 and b["money"] == 3 and b["badge"] == "💰💰💰⭐⭐⭐" and b["star"]
    b = _core.badges("XAU biasa")
    assert b["stars"] == 0 and b["money"] == 0 and not b["star"]
    # angka teruji Okt 2021–2026 (replay kode cloud, TP1 0,7R, sejak 7 Okt + jeda 60 jam): konf+⭐ +0,261R → 💰💰💰
    assert _core.badges("XAU konf+⭐")["badge"] == "💰💰💰⭐⭐" and _core.badges("XAU konf+⭐")["star"]
    assert np.isclose(_core.badges("XAU konf")["avg_r"], _core.STATS["XAU konf"][1])
    assert _core.badges("XAU konf")["money"] > 0 and _core.badges("BTC konf")["money"] == 0


def test_btc_runs_24_7_with_prefix_and_point_value():
    import pandas as pd
    from datetime import timedelta
    from test_cloud import FakePrices, FakePub, FakeStore
    rng = np.random.default_rng(4)
    idx = pd.date_range("2026-01-01", periods=24 * 200, freq="1h", tz="UTC")     # termasuk akhir pekan
    c = 60000 + np.cumsum(rng.standard_t(4, len(idx)) * 150 + 20)
    o = np.r_[c[0], c[:-1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 80, "low": np.minimum(o, c) - 80, "close": c}, index=idx)
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = idx[24 * 80].to_pydatetime() + timedelta(minutes=2)
    while now <= idx[-1].to_pydatetime():
        prices.now = now
        _core.tick(now, prices, store, pub, _core.BTC_CFG, symbol="BTC/USD")
        now += timedelta(hours=1)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig and all(e["id"].startswith("BTC-") and e["point_value"] == 0.01 and e["symbol"] == "BTC/USD"
                       and e["cat"].startswith("BTC") and e["star"] for e in sig)
    assert any(pd.Timestamp(e["time"]).dayofweek >= 5 for e in sig) or len(sig) < 5
