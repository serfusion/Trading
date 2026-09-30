"""⚡ kesempatan emas, peringkat sinyal, dan label ⚠️ mode perang di cloud."""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
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


class FakeStore:
    def __init__(self, data=None):
        self.data, self.saved = dict(data or {}), 0

    def get_state(self, row):
        return self.data.get(row, {})

    def save_state(self, data, row):
        self.data[row], self.saved = data, self.saved + 1


def _uso_response(monkeypatch, closes, start=date(2026, 9, 14)):
    import io
    import json
    calls = []
    values = [{"datetime": (start + timedelta(days=k)).isoformat(), "close": str(c)} for k, c in enumerate(closes)]

    def fake(url, timeout=0):
        calls.append(url)
        return io.BytesIO(json.dumps({"status": "ok", "values": values}).encode())
    monkeypatch.setattr(_perang.urllib.request, "urlopen", fake)
    return calls


def test_perang_fred_segar_tanpa_cadangan(monkeypatch):
    from datetime import datetime, timezone
    now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    rows = [(date(2026, 9, 15) + timedelta(days=k), 60.0 + k) for k in range(12)]
    monkeypatch.setattr(_perang, "fred_rows", lambda: rows)
    st = _perang.current(now, backup=lambda: (_ for _ in ()).throw(AssertionError("cadangan dipanggil")))
    assert st["src"] == "FRED" and st["on"] and st["wti"] == 71.0 and "WTI" in st["text"]


def test_perang_cadangan_uso_saat_fred_gagal_atau_basi(monkeypatch):
    from datetime import datetime, timezone
    now = datetime(2026, 9, 26, 22, tzinfo=timezone.utc)
    calls = _uso_response(monkeypatch, [50.0 + k for k in range(13)])      # 14..26 Sep, 26 Sep sudah final (22:00)
    store = FakeStore()

    def gagal():
        raise OSError("timeout")
    monkeypatch.setattr(_perang, "fred_rows", gagal)
    st = _perang.current(now, lambda: _perang.uso_rows("k", store, now))
    assert st["src"] == "USO" and st["on"] and st["wti"] is None and "USO" in st["text"]
    assert "FRED" in st["fred_error"] and st["date"] == "2026-09-26" and len(calls) == 1 and store.saved == 1

    basi = [(date(2026, 9, 1) + timedelta(days=k), 60.0) for k in range(12)]  # terakhir 12 Sep = 14 hari lalu
    monkeypatch.setattr(_perang, "fred_rows", lambda: basi)
    st = _perang.current(now + timedelta(hours=1), lambda: _perang.uso_rows("k", store, now + timedelta(hours=1)))
    assert st["src"] == "USO" and len(calls) == 1                          # dari cache (< 6 jam), tanpa kredit baru

    with pytest.raises(RuntimeError):
        _perang.current(now, backup=None)                                    # WAR_BACKUP=0 -> perilaku lama


def test_uso_candle_hari_ini_belum_final_dan_refresh(monkeypatch):
    from datetime import datetime, timezone
    calls = _uso_response(monkeypatch, [50.0] * 13)
    store = FakeStore()
    siang = datetime(2026, 9, 26, 15, tzinfo=timezone.utc)                  # NYSE masih buka
    assert _perang.uso_rows("k", store, siang)[-1][0] == date(2026, 9, 25)
    assert _perang.uso_rows("k", store, siang + timedelta(hours=7))[-1][0] == date(2026, 9, 26)
    assert len(calls) == 2                                                   # >= 6 jam -> unduh ulang
