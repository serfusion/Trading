"""Cloud: filter SMC (bias struktur H4) & pengaman auto order harus identik dengan bot PC."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from helpers import bars_from_path
from test_cloud import to_bars
from test_cloud_live import ONE_SET, FakeMetaApi, df_trend, market_calls, run
from xau_bot.config import SessionConfig
from xau_bot.sessions import SessionClock, trading_day
from xau_bot.smc import structure_bias

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402

UTC = timezone.utc


def random_h1(n=900, seed=5):
    rng = np.random.default_rng(seed)
    closes = 2000 + np.cumsum(rng.standard_t(4, n) * 3)
    df = bars_from_path(closes, start="2026-01-05 00:00", freq="1h", wick=1.0)
    df["high"] += np.abs(rng.normal(0, 1.5, n))
    df["low"] -= np.abs(rng.normal(0, 1.5, n))
    return df


def test_structure_bias_identical_to_bot():
    df = random_h1()
    bars = to_bars(df)
    seen = set()
    for end in range(20, len(df), 11):
        for length in (2, 3, 5):
            a = structure_bias(df.iloc[:end], length)
            assert _core.structure_bias(bars[:end], length) == a
            seen.add(a)
    assert {-1, 1} <= seen


def test_h4_bars_match_pandas_resample_of_closed_bars():
    df = random_h1(300)
    bars = to_bars(df)
    now = datetime(2026, 1, 12, 14, 30, tzinfo=UTC)            # H4 12:00-16:00 belum tertutup
    closed = [b for b in bars if b.t + timedelta(hours=1) <= now]
    h4 = _core.htf_bars(closed, now, 4)
    ref = df[df.index + pd.Timedelta(hours=1) <= now].resample("240min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    ref = ref[ref.index + pd.Timedelta(hours=4) <= now]
    assert [b.t for b in h4] == [t.to_pydatetime() for t in ref.index]
    assert np.allclose([[b.o, b.h, b.l, b.c] for b in h4], ref.to_numpy())


def test_session_blocks_and_trading_day_identical_to_bot():
    clock = SessionClock(SessionConfig())
    t = datetime(2026, 3, 1, tzinfo=UTC)
    checked = 0
    while t < datetime(2027, 1, 10, tzinfo=UTC):                # termasuk 2 pergantian DST
        ts = pd.Timestamp(t)
        assert _core.entry_block_reason(t) == clock.entry_block_reason(ts), t
        assert _core.trading_day(t) == trading_day(ts).isoformat()
        assert _core.ny_time(t) == t.astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)
        t += timedelta(minutes=35)
        checked += 1
    assert checked > 10000


def test_loss_guard_daily_weekly_and_reset():
    now = datetime(2026, 9, 15, 3, tzinfo=UTC)                  # Selasa
    g = _core.loss_guard({}, {"balance": 1000.0, "equity": 1000.0}, now, 3.0, 6.0)
    assert g["blocked"] == "" and g["day_balance"] == 1000.0
    g = _core.loss_guard(g, {"balance": 995.0, "equity": 969.0}, now + timedelta(hours=2), 3.0, 6.0)
    assert "harian 3%" in g["blocked"]
    g = _core.loss_guard(g, {"balance": 969.0, "equity": 969.0}, now + timedelta(days=1), 3.0, 6.0)
    assert g["blocked"] == "" and g["day_balance"] == 969.0      # hari baru -> reset
    g = _core.loss_guard(g, {"balance": 969.0, "equity": 939.0}, now + timedelta(days=1, hours=1), 3.0, 6.0)
    assert "harian" in g["blocked"]
    g = _core.loss_guard(g, {"balance": 939.0, "equity": 939.0}, now + timedelta(days=2), 3.0, 6.0)
    assert "mingguan 6%" in g["blocked"]                         # 939 <= 1000 x 94%


class Equity(FakeMetaApi):
    """MetaApi palsu dengan equity yang bisa turun (uji batas rugi)."""

    def __init__(self, equity=lambda n: 30000.0, **kw):
        super().__init__(**kw)
        self.equity, self.n = equity, 0

    def account(self):
        self.n += 1
        return {"balance": 30000.0, "equity": self.equity(self.n), "currency": "USC"}


def run_quoted(control, spread=0.2, offset=0.0, cfg=ONE_SET):
    ex = FakeMetaApi(spread=spread, offset=offset)
    store, pub = run(df_trend(), control, ex, cfg=cfg)
    return ex, store, pub


def test_sl_tp_follow_broker_price():
    ex, store, pub = run_quoted({"auto": True}, spread=0.3, offset=1.5)
    buys = [c for c in market_calls(ex) if c[1] == "BUY"]
    assert len(buys) == 5
    sig = next(e for e in pub.events if e["type"] == "signal" and e["status"] == "signal" and e["dir"] == "BUY")
    risk = sig["risk_points"]
    fill = sig["entry"] + 1.5 + 0.3                                  # ASK broker
    assert buys[0][3] == pytest.approx(fill - risk, abs=1e-3)         # SL dari harga broker, jarak sama
    assert buys[0][4] == pytest.approx(fill + risk, abs=1e-3)         # TP1 = 1R dari harga broker


def test_wide_spread_skips_auto_order_but_keeps_signal():
    ex, _, pub = run_quoted({"auto": True}, spread=2.0)
    assert market_calls(ex) == []
    assert any(e["type"] == "signal" and e["status"] == "signal" for e in pub.events)
    assert any(e["type"] == "info" and "spread broker" in e["text"] for e in pub.events)


def test_broker_price_far_from_feed_skips():
    ex, _, pub = run_quoted({"auto": True}, offset=100.0)
    assert market_calls(ex) == []
    assert any(e["type"] == "info" and "beda jauh" in e["text"] for e in pub.events)


def test_daily_loss_limit_blocks_new_orders():
    ex = Equity(equity=lambda n: 30000.0 if n < 3 else 29000.0)   # equity turun 3,3% setelah tick awal
    store, pub = run(df_trend(), {"auto": True}, ex)
    assert market_calls(ex) == []
    assert any(e["type"] == "signal" and e["status"] == "signal" for e in pub.events)
    assert any(e["type"] == "info" and "Batas rugi harian" in e["text"] for e in pub.events)
    assert "Batas rugi harian" in _core.status(store, ex)["guard"]


def test_status_reports_filter_bias_and_limits():
    ex, store, _ = run_quoted({"auto": True})
    st = _core.status(store, ex)
    assert st["control"]["bias_filter"] is True and st["control"]["daily_loss_pct"] == 3.0
    assert st["bias"] in ("BULLISH", "BEARISH", "NETRAL") and st["guard"] == ""


def test_filter_off_from_app_takes_counter_bias_breakout():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4
    df = bars_from_path(flat + [top] + list(np.linspace(top, top - 60, 3)) + [top - 60] * 10,
                        start="2026-09-14 00:00", freq="1h", wick=0.5)
    cfg = {**ONE_SET, "bias_filter": True}
    on, off = FakeMetaApi(), FakeMetaApi()
    run(df, {"auto": True}, on, cfg=cfg)
    run(df, {"auto": True, "bias_filter": False}, off, cfg=cfg)
    assert not [c for c in market_calls(on) if c[1] == "BUY"]
    assert len([c for c in market_calls(off) if c[1] == "BUY"]) == 5
