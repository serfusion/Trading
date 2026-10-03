"""Validasi arah H4 EMA50 untuk 💰 XAU (cloud/api/_core.h4_ema_check, research/alchemist.py F4)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from test_cloud import FakePrices, FakePub, FakeStore, to_bars

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402

from research.github_popular import ema  # noqa: E402


def bars(closes, start="2026-01-05"):
    t0 = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    return [_core.Bar(t0 + timedelta(hours=i), c, c + 1, c - 1, c) for i, c in enumerate(closes)]


def test_arah_h4_naik_turun_dan_data_kurang():
    up = bars(np.linspace(2000, 2600, 400))
    assert _core.h4_ema_check(up, "BUY")[0] and not _core.h4_ema_check(up, "SELL")[0]
    assert "lawan arah H4" in _core.h4_ema_check(up, "SELL")[1]
    down = bars(np.linspace(2600, 2000, 400))
    assert _core.h4_ema_check(down, "SELL")[0] and not _core.h4_ema_check(down, "BUY")[0]
    assert _core.h4_ema_check(up[:150], "SELL") == (True, "data H4 belum cukup")      # < 50 blok H4


def test_hanya_blok_h4_yang_sudah_tutup_dan_sama_dengan_riset():
    rng = np.random.default_rng(3)
    closes = 2000 + np.cumsum(rng.normal(0, 3, 24 * 60))
    b = bars(closes)
    # riset: resample 240min (UTC), EMA ewm adjust=False, nilai blok terakhir yang tutup saat keputusan
    idx = pd.date_range("2026-01-05", periods=len(closes), freq="1h", tz="UTC")
    h4 = pd.Series(closes, index=idx).resample("240min").last()
    for end in (400, 401, 402, 403, 1000):                  # candle sinyal terakhir = end-1
        decide = idx[end - 1] + pd.Timedelta(hours=1)
        done = h4[h4.index + pd.Timedelta(hours=4) <= decide].to_numpy()
        want = done[-1] > ema(done, 50)[-1]
        assert _core.h4_ema_check(b[:end], "BUY")[0] == want


def test_tick_xau_melewati_sinyal_lawan_h4(monkeypatch):
    rng = np.random.default_rng(11)
    idx = pd.date_range("2026-01-05", periods=24 * 200, freq="1h", tz="UTC")
    c = 2000 + np.cumsum(rng.standard_t(4, len(idx)) * 4)
    o = np.r_[c[0], c[:-1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 2, "low": np.minimum(o, c) - 2, "close": c}, index=idx)
    df = df[df.index.dayofweek < 5]
    calls, real, force = [], _core.h4_ema_check, {"tolak": False}

    def spy(closed, direction, n=50):
        out = (False, "H4 (tes) (lawan arah H4)") if force["tolak"] else real(closed, direction, n)
        calls.append(out[0])
        return out
    monkeypatch.setattr(_core, "h4_ema_check", spy)
    # kartu status tren (heartbeat, 3.24) juga membaca arah H4 untuk tampilan; yang diuji di sini hanya filter sinyal
    monkeypatch.setattr(_core, "trend_status", lambda *a, **k: {})

    def run(h4):
        prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
        now, events = df.index[24 * 60].to_pydatetime() + timedelta(minutes=2), []
        while now <= df.index[-1].to_pydatetime():
            prices.now = now
            events += _core.tick(now, prices, store, pub, {**_core.CFG, "h4_filter": h4})["events"]
            now += timedelta(hours=1)
        return [e for e in pub.events if e["type"] == "signal"], events
    base, _ = run(False)
    assert calls == []                                               # saklar mati -> tidak diperiksa
    filt, ev = run(True)
    skipped = [e for e in ev if "lawan arah H4" in e]
    assert calls.count(False) == len(skipped) and calls.count(True) == len(filt) and len(filt) <= len(base) > 0
    calls.clear()
    force["tolak"] = True
    none, ev = run(True)
    assert none == [] and len(calls) > 0 and sum("dilewati: H4 (tes)" in e for e in ev) == len(calls)
