"""Alat riset data eksternal: tanpa look-ahead (research/eksternal*.py). Tidak butuh jaringan/data unduhan."""
import lzma

import numpy as np
import pandas as pd

from research.dukascopy import _decode
from research.eksternal import asof, judge
from research.eksternal_berita import _near
from research.eksternal_cot import SHUTDOWN


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_asof_hanya_nilai_yang_sudah_terbit():
    values = pd.Series([1.0, 2.0, 3.0])
    avail = pd.DatetimeIndex([ts("2024-01-02 21:00"), ts("2024-01-03 21:00"), ts("2024-01-04 21:00")])
    times = pd.DatetimeIndex([ts("2024-01-02 20:59"), ts("2024-01-02 21:00"), ts("2024-01-04 12:00")])
    out = asof(times, values, avail)
    assert np.isnan(out[0]) and out[1] == 1.0 and out[2] == 2.0


def test_asof_satuan_waktu_berbeda():
    """Index BTC (ms) vs waktu terbit (us) — dulu salah karena asi8 beda satuan."""
    avail = pd.DatetimeIndex([ts("2024-01-02")]).as_unit("us")
    times = pd.DatetimeIndex([ts("2024-01-03")]).as_unit("ms")
    assert asof(times, pd.Series([5.0]), avail)[0] == 5.0


def test_near_hanya_dalam_jendela():
    t = np.array([ts("2024-01-05 12:00").value])
    ev = np.array([ts("2024-01-05 13:30").value])
    assert _near(t, ev, 0, 2)[0] and not _near(t, ev, 0, 1)[0] and not _near(t, ev, -4, 0)[0]


def test_judge_konsisten_hanya_bila_membuang_rugi():
    t = pd.date_range("2013-01-01", periods=400, freq="7D", tz="UTC")
    r = np.where(np.arange(400) % 4 == 0, -1.0, 0.8)
    sig = pd.DataFrame({"t": t, "R": r})
    good = judge(sig, r > 0, ts("2019-01-01"))
    assert good["konsisten"] and good["drop"] == -1.0
    bad = judge(sig, r < 0, ts("2019-01-01"))
    assert not bad["konsisten"]


def test_shutdown_ditunda():
    for a, b, rel in SHUTDOWN:
        assert pd.Timestamp(rel) > pd.Timestamp(b)


def test_decode_bi5():
    rows = np.array([[0, 2063625, 2064295, 2063625, 2064425, 0], [60, 1, 1, 1, 1, 0]], dtype=">i4")
    rows = rows.copy()
    rows[:, 5] = np.array([0.5, 0.0], dtype=">f4").view(">i4")
    raw = lzma.compress(rows.tobytes(), format=lzma.FORMAT_ALONE)
    df = _decode(raw, ts("2024-01-02"), 1e-3)
    assert len(df) == 1                                    # volume 0 dibuang
    r = df.iloc[0]
    assert (r.open, r.close, r.low, r.high) == (2063.625, 2064.295, 2063.625, 2064.425)
