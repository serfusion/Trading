"""DOGE/ADA (KRIPTO_CFG): harga kecil → 6 desimal, SL+ hampir di entry, ukuran dalam koin; XAU/BTC tidak berubah."""
import sys
from pathlib import Path

import numpy as np

from helpers import bars_from_path
from test_cloud import run_ticks

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402


def doge_df():
    flat = [0.0900 + 0.0004 * np.sin(i / 2) for i in range(80)]
    rise = list(np.linspace(flat[-1] + 0.0008, flat[-1] + 0.03, 40))
    drop = list(np.linspace(rise[-1], rise[-1] - 0.025, 8))
    return bars_from_path(flat + rise + drop + [drop[-1]] * 10, start="2026-09-14 00:00", freq="1h", wick=0.0001)


def test_doge_digit_sl_plus_dan_satuan_koin():
    cfg = {**_core.KRIPTO_CFG, "asset": "DOGE", "id_prefix": "DOGE-", "sets": [(55, 20)]}
    _, pub = run_ticks(doge_df(), cfg=cfg)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig, "harus ada sinyal breakout"
    s = sig[0]
    assert s["id"].startswith("DOGE-") and s["satuan"] == "koin" and s["tier"] == "biasa"
    assert s["entry"] != round(s["entry"], 3) or len(str(s["entry"]).split(".")[1]) <= 6   # tidak dipangkas ke 3 desimal
    assert abs(s["sl_plus"] - s["entry"]) < 0.0001                                       # SL+ hampir tepat di entry
    assert 0 < s["entry"] - s["sl"] < 0.05 and s["tp1"] > s["entry"]
    assert "posisi (ukuran koin" in s["lot"]
    cls = [e for e in pub.events if e["type"] == "close"]
    assert cls and all(len(str(c["price"]).split(".")[1]) > 3 for c in cls if "." in str(c["price"]))


def test_xau_btc_tetap_3_desimal_dan_offset_lama():
    assert _core.dg(_core.CFG) == 3 and _core.td(_core.BTC_CFG) == 2
    assert _core.CFG["be_offset"] == 0.10 and "satuan" not in _core.BTC_CFG
    assert _core.badges("DOGE biasa")["money"] >= 2 and _core.badges("ADA konf+⭐")["money"] >= 2
