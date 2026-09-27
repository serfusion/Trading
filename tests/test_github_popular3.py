"""Port strategi tahap B tidak boleh mengintip masa depan: trade yang sudah selesai sebelum titik potong harus sama
persis walau data sesudahnya dibuang."""
import numpy as np
import pandas as pd
import pytest

import research.github_popular3 as g
from research.harness import Period


def _period(n=12 * 24 * 60, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="5min", tz="UTC")
    c = 1900 + np.cumsum(rng.normal(0, 0.8, n))
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) + rng.uniform(0, 0.8, n)
    lo = np.minimum(o, c) - rng.uniform(0, 0.8, n)
    return Period("sintetis", pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c}, index=idx), "M5", 0.25)


@pytest.mark.parametrize("fn,must_trade", [
    (g.turnip_ema_trend, True),
    (g.turnip_triple, True),
    (lambda p: g.hillary(p, "swing"), True),
    (g.nazhmi_fvg_ob, False),          # syaratnya jarang terpenuhi di data acak
    (g.blackhunter, True),
    (lambda p: g.aurum(p, "15min", learn=False), True),
    (g.kiran_smc, True),
])
def test_tanpa_look_ahead(fn, must_trade):
    full = _period()
    cut = full.base.index[len(full.base) * 2 // 3]
    part = Period("potong", full.base[full.base.index < cut], "M5", 0.25)
    a, b = fn(full), fn(part)
    done_a = a[a.exit < cut - pd.Timedelta(days=11)][["time", "dir", "R"]].reset_index(drop=True)
    done_b = b[b.exit < cut - pd.Timedelta(days=11)][["time", "dir", "R"]].reset_index(drop=True)
    assert len(done_a) > 0 or not must_trade
    pd.testing.assert_frame_equal(done_a, done_b)


def test_grid_akun_berhenti_saat_habis():
    t = g.blamz_adv_grid(_period())
    assert t.attrs["saldo_akhir"] > 0.0 or t.attrs["habis"] is not None
