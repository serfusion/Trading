"""research/smc_dashboard.py: fitur di candle i tidak boleh berubah bila candle sesudahnya diubah (tanpa look-ahead)."""
import numpy as np
import pandas as pd

from research import smc_dashboard as S


def _bars(n=900, seed=3):
    rng = np.random.default_rng(seed)
    c = 2000 + np.cumsum(rng.normal(0, 2, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.random(n) * 3
    l = np.minimum(o, c) - rng.random(n) * 3
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def test_tanpa_look_ahead():
    df = _bars()
    cut = 700
    a = S.features(df)
    df2 = df.copy()
    df2.iloc[cut + 1:, :] = df2.iloc[cut + 1:, :] * 1.1 + 50      # ubah masa depan
    b = S.features(df2)
    for k in a:
        x, y = np.asarray(a[k][:cut + 1], float), np.asarray(b[k][:cut + 1], float)
        assert np.allclose(x, y, equal_nan=True), k


def test_varian_bentuk():
    df = _bars()
    f = S.features(df)
    times = pd.DatetimeIndex(df.index).as_unit("ns")
    t = pd.Series(df.index[[300, 500, 800]])
    v = S.variants(t, np.array([1, -1, 1]), f, times)
    assert len(v) == 10 and all(len(x) == 3 for x in v.values())
