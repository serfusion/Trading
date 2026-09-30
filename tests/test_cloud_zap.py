"""⚡ kesempatan emas, peringkat sinyal, dan label ⚠️ mode perang di cloud."""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from research.strategy_lab import Bars
from test_cloud import run_ticks, to_bars
from test_cloud_star import market

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _perang  # noqa: E402


def test_vol_pct_sama_dengan_riset():
    df = market(days=160, seed=3)
    rank = pd.Series(Bars(df, 0.3).atr).rolling(1440, min_periods=500).rank(pct=True).to_numpy()
    bars = to_bars(df)
    for i in range(600, len(df), 97):
        assert abs(_core.vol_pct(bars[:i + 1]) - rank[i]) < 1e-9, df.index[i]
    assert _core.vol_pct(bars[:300]) is None


def test_peringkat():
    assert _core.tier("XAU", "konf+⭐", 0.2) == "zap"
    assert _core.tier("XAU", "konf+⭐", 0.5) == "bronze"
    assert _core.tier("XAU", "konf", 0.2) == "bronze"
    assert _core.tier("XAU", "konf", 0.9) == "biasa"
    assert _core.tier("XAU", "konf+⭐", None) == "bronze"
    assert _core.tier("BTC", "⭐", None) == "zap"
    assert _core.tier("BTC", "konf+⭐", None) == "silver"
    assert _core.tier("BTC", "konf", None) == "biasa"


def test_status_mode_perang():
    rows = [(date(2026, 3, 1) + timedelta(days=k), 60.0 + k * 0.8) for k in range(12)]
    st = _perang.status(rows)
    assert st["on"] and st["oil10"] >= 10 and "Mode perang" in st["text"]
    calm = [(date(2026, 3, 1) + timedelta(days=k), 60.0) for k in range(12)]
    assert not _perang.status(calm)["on"] and _perang.status(calm)["text"] == ""
    assert _perang.status(rows[:5]) is None


def test_sinyal_zap_dan_label_perang(monkeypatch):
    war = _perang.status([(date(2026, 3, 1) + timedelta(days=k), 60.0 + k * 0.8) for k in range(12)])
    monkeypatch.setattr(_core, "vol_pct", lambda closed, *a, **k: 0.1)
    monkeypatch.setattr(_core, "category", lambda closed, d, cfg: (
        {**_core.badges("XAU konf+⭐"), "star": True}, "tren D1 & H4 searah"))
    cfg = {**_core.CFG, "star_only": False, "market_hours": False, "skip_open_bars": 0, "war": war}
    store, pub = run_ticks(market(days=90, seed=11), cfg=cfg)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig and all(e["tier"] == "zap" and e["zap"] and e["badge"].startswith("⚡💰💰💰") and e["wr07"] > 60
                       and e["war"]["on"] for e in sig)
    hb = [e for e in pub.events if e["type"] == "heartbeat"]
    assert hb and hb[-1]["war"]["on"]
    closes = [e for e in pub.events if e["type"] == "close"]
    assert closes and all(e["tier"] == "zap" for e in closes)


def test_tanpa_perang_tanpa_label(monkeypatch):
    monkeypatch.setattr(_core, "vol_pct", lambda closed, *a, **k: 0.9)
    monkeypatch.setattr(_core, "category", lambda closed, d, cfg: (
        {**_core.badges("XAU konf+⭐"), "star": True}, "tren"))
    cfg = {**_core.CFG, "star_only": False, "market_hours": False, "skip_open_bars": 0}
    store, pub = run_ticks(market(days=90, seed=11), cfg=cfg)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig and all(e["tier"] == "bronze" and not e["zap"] and "war" not in e and not e["badge"].startswith("⚡")
                       for e in sig)
    assert np.isclose(sig[0]["avg_r"], 0.309)
