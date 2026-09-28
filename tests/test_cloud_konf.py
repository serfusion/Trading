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
    assert b["stars"] == 3 and b["money"] == 3 and b["badge"] == "⭐⭐⭐💸💸💸" and b["star"]
    b = _core.badges("XAU biasa")
    assert b["stars"] == 0 and b["money"] == 0 and not b["star"]
    assert _core.badges("XAU konf+⭐")["badge"] == "⭐💸💸💸"
    assert np.isclose(_core.badges("XAU konf")["avg_r"], 0.093)
