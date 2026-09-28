"""Filter BTC 💰 dari riset data eksternal (cloud/api/_funding.py) — tanpa jaringan."""
import csv
import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from test_cloud import FakePrices, FakePub, FakeStore, to_bars

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _funding  # noqa: E402

UTC = timezone.utc


def rows_for(start: datetime, hours: int, premium=lambda t: 0.0002) -> list[list[str]]:
    out = []
    for h in range(hours):
        t = start + timedelta(hours=h)
        ms = int(t.timestamp() * 1000)
        out.append([str(ms), "0", "0", "0", repr(premium(t))])
    return out


def test_funding_8h_sama_dengan_rumus_riset():
    from research.eksternal_btc import funding_proxy
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rng = np.random.default_rng(1)
    vals = rng.normal(0.0001, 0.0004, 24 * 10)
    rows = rows_for(start, 24 * 10, lambda t: float(vals[int((t - start).total_seconds() // 3600)]))
    live = _funding.funding_8h(_funding.premium_hours(rows))
    idx = pd.to_datetime([int(r[0]) for r in rows], unit="ms", utc=True)
    ref = funding_proxy(pd.DataFrame({"premium": vals}, index=idx))
    assert len(live) == len(ref)
    for t, v in ref.items():
        assert abs(live[int(t.timestamp())] - v) < 1e-15


def test_clamp_dan_persentil():
    f = _funding.funding_8h({0: 0.0, 3600: 0.0})                    # premium 0 -> funding = 0,01%
    assert abs(f[28800] - 0.0001) < 1e-15
    assert _funding.percentile_last([0.0001] * 100) is None           # < 365 nilai
    vals = list(np.linspace(-0.001, 0.001, 1200))
    assert _funding.percentile_last(vals) == 1.0                       # nilai terakhir tertinggi
    assert _funding.percentile_last(vals[::-1]) < 0.01


def test_skip_reason():
    hi = {"f": [[i, v] for i, v in enumerate(np.linspace(0, 0.001, 1200))]}
    lo = {"f": [[i, v] for i, v in enumerate(np.linspace(0.001, 0, 1200))]}
    aug = datetime(2026, 8, 20, 12, tzinfo=UTC)
    assert "ramai long" in _funding.skip_reason("BUY", aug, hi, new_york=_core.new_york)
    assert _funding.skip_reason("SELL", aug, hi, new_york=_core.new_york) is None
    assert "ramai short" in _funding.skip_reason("SELL", aug, lo, new_york=_core.new_york)
    assert _funding.skip_reason("BUY", aug, lo, new_york=_core.new_york) is None
    assert _funding.skip_reason("BUY", aug, hi, funding=False, new_york=_core.new_york) is None
    sept = datetime(2026, 9, 15, 12, tzinfo=UTC)
    assert "September" in _funding.skip_reason("BUY", sept, {}, new_york=_core.new_york)
    assert _funding.skip_reason("BUY", sept, {}, september=False, new_york=_core.new_york) is None
    assert _funding.skip_reason("BUY", aug, {}, new_york=_core.new_york) is None         # cache kosong -> kirim


def test_refresh_isi_awal_lalu_harian():
    now = datetime(2026, 9, 10, 6, tzinfo=UTC)
    calls = []

    def fetch(url):
        calls.append(url)
        name = url.rsplit("-1h-", 1)[1].removesuffix(".zip")
        if "/monthly/" in url:
            start = datetime.strptime(name, "%Y-%m").replace(tzinfo=UTC)
            end = (start + timedelta(days=32)).replace(day=1)
        else:
            start = datetime.strptime(name, "%Y-%m-%d").replace(tzinfo=UTC)
            if start >= datetime(2026, 9, 9, tzinfo=UTC):
                return None                                          # file kemarin belum terbit
            end = start + timedelta(days=1)
        return rows_for(start, int((end - start).total_seconds() // 3600))
    cache = {}
    for _ in range(6):
        cache = _funding.refresh(cache, now, fetch)
    assert cache["day"] == "2026-09-08" and cache["m"] == "2026-08-01"
    assert any("/monthly/" in u and "2025-07" in u for u in calls)
    assert not any("/monthly/" in u and "2026-08" in u for u in calls)        # bulan lalu dari file harian
    assert len(cache["f"]) == _funding.KEEP and _funding.percentile_last([v for _, v in cache["f"]]) == 1.0
    n = len(calls)
    cache = _funding.refresh(cache, now + timedelta(minutes=10), fetch)      # menunggu file kemarin: 1x/jam
    assert len(calls) == n
    _funding.refresh(cache, now + timedelta(hours=2), fetch)
    assert len(calls) == n + 1


def test_tick_btc_melewati_sinyal_dengan_skip_fn():
    rng = np.random.default_rng(4)
    idx = pd.date_range("2026-01-01", periods=24 * 200, freq="1h", tz="UTC")
    c = 60000 + np.cumsum(rng.standard_t(4, len(idx)) * 150 + 20)
    o = np.r_[c[0], c[:-1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 80, "low": np.minimum(o, c) - 80, "close": c}, index=idx)

    def run(skip_fn):
        prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
        now = idx[24 * 80].to_pydatetime() + timedelta(minutes=2)
        events = []
        while now <= idx[-1].to_pydatetime():
            prices.now = now
            cfg = {**_core.BTC_CFG, "skip_fn": skip_fn} if skip_fn else _core.BTC_CFG
            events += _core.tick(now, prices, store, pub, cfg, symbol="BTC/USD")["events"]
            now += timedelta(hours=1)
        return [e for e in pub.events if e["type"] == "signal"], events
    base, _ = run(None)
    only_sell, ev = run(lambda d, t: "funding ramai long (tes)" if d == "BUY" else None)
    assert any(e["dir"] == "BUY" for e in base)
    assert all(e["dir"] == "SELL" for e in only_sell) and len(only_sell) < len(base)
    assert any("dilewati: funding ramai long (tes)" in e for e in ev)
