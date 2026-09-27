"""Port tahap B2 tidak boleh mengintip masa depan (data dipotong = trade yang sudah selesai tetap sama)."""
import pandas as pd
import pytest

import research.github_popular4 as g
from research.harness import Period
from tests.test_github_popular3 import _period


@pytest.mark.parametrize("fn,must_trade", [
    (g.samw_macd, True),
    (g.samw_gapfill, False),
    (g.ultra_aggressive, True),
    (g.angga_rules, True),
    (lambda p: g.xaubot_v3(p, "harian", atr_filter=False), False),
])
def test_tanpa_look_ahead(fn, must_trade):
    full = _period(n=12 * 24 * 90)
    cut = full.base.index[len(full.base) * 2 // 3]
    part = Period("potong", full.base[full.base.index < cut], "M5", 0.25)
    a, b = fn(full), fn(part)
    lim = cut - pd.Timedelta(days=11)
    done_a = a[a.exit < lim][["time", "dir", "R"]].reset_index(drop=True)
    done_b = b[b.exit < lim][["time", "dir", "R"]].reset_index(drop=True)
    assert len(done_a) > 0 or not must_trade
    pd.testing.assert_frame_equal(done_a, done_b)
