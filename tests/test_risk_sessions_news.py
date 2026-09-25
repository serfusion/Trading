import pandas as pd
import pytest

from xau_bot.backtest import XAU_SPEC
from xau_bot.config import NewsConfig, RiskConfig, SessionConfig
from xau_bot.models import Account, ClosedTrade, Direction
from xau_bot.news import NewsFilter
from xau_bot.risk import RiskGuard, lot_size, split_volume
from xau_bot.sessions import SessionClock, trading_day


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_lot_size_one_percent():
    # Saldo 10.000, risiko 1% = 100. SL 5.00 -> 5 * 100 (nilai 1.00 per lot) = 500/lot -> 0.20 lot
    lot, risk, _ = lot_size(10_000, 1.0, 4348.23, 4343.23, XAU_SPEC)
    assert lot == pytest.approx(0.20)
    assert risk == pytest.approx(100.0)


def test_lot_rounds_down_never_over_risk():
    lot, risk, _ = lot_size(1_000, 1.0, 4348.23, 4345.18, XAU_SPEC)  # SL 3.05
    assert lot == pytest.approx(0.03)
    assert risk <= 10.0


def test_min_lot_over_risk_is_skipped_by_default():
    lot, risk, msg = lot_size(100, 1.0, 4348.23, 4343.23, XAU_SPEC)
    assert lot == 0 and "Lot minimum" in msg
    lot2, _, _ = lot_size(100, 1.0, 4348.23, 4343.23, XAU_SPEC, allow_min_over_risk=True)
    assert lot2 == pytest.approx(0.01)


def test_split_volume():
    assert split_volume(0.21, 0.5, XAU_SPEC) == (pytest.approx(0.10), pytest.approx(0.11))
    assert split_volume(0.01, 0.5, XAU_SPEC) == (0.0, 0.01)


def _trade(pnl, close, opened=None, direction=Direction.SELL):
    return ClosedTrade(1, direction, 0.1, pnl, ts(opened or close), ts(close))


def test_risk_guard_consecutive_losses_grouped_per_setup():
    guard = RiskGuard(RiskConfig(max_consecutive_losses=2))
    acc = Account(10_000, 10_000, 10_000)
    now = ts("2026-09-22 15:00")
    # Satu setup = 2 posisi yang kena SL bersamaan -> dihitung 1 kekalahan
    trades = [_trade(-20, "2026-09-22 13:00", "2026-09-22 12:00"),
              _trade(-20, "2026-09-22 13:00", "2026-09-22 12:00")]
    assert guard.evaluate(now, acc, trades).blocked is None
    trades.append(_trade(-30, "2026-09-22 14:30", "2026-09-22 14:00"))
    assert "beruntun" in guard.evaluate(now, acc, trades).blocked


def test_risk_guard_daily_loss_limit():
    guard = RiskGuard(RiskConfig(daily_loss_pct=3.0, max_consecutive_losses=0))
    acc = Account(9_700, 9_700, 9_700)
    state = guard.evaluate(ts("2026-09-22 15:00"), acc, [_trade(-300, "2026-09-22 14:00")])
    assert "harian" in state.blocked


def test_risk_guard_resets_next_trading_day():
    guard = RiskGuard(RiskConfig(max_consecutive_losses=1))
    acc = Account(10_000, 10_000, 10_000)
    trades = [_trade(-10, "2026-09-22 14:00")]
    assert guard.evaluate(ts("2026-09-22 15:00"), acc, trades).blocked
    # 17:00 New York (21:00 UTC musim panas) = hari trading baru
    assert guard.evaluate(ts("2026-09-22 21:30"), acc, trades).blocked is None


def test_trading_day_rolls_at_5pm_new_york():
    assert trading_day(ts("2026-09-22 20:59")) != trading_day(ts("2026-09-22 21:01"))


def test_sessions_killzones_follow_dst():
    clock = SessionClock(SessionConfig())
    # London open 02:00 NY = 06:00 UTC saat musim panas, 07:00 UTC saat musim dingin
    assert clock.killzone(ts("2026-09-22 06:30")) == "London"
    assert clock.killzone(ts("2026-12-15 06:30")) is None
    assert clock.killzone(ts("2026-12-15 07:30")) == "London"
    assert clock.killzone(ts("2026-09-22 14:30")) == "SilverBullet_AM"


def test_session_blocks():
    clock = SessionClock(SessionConfig())
    assert clock.entry_block_reason(ts("2026-09-26 12:00"))       # Sabtu
    assert clock.entry_block_reason(ts("2026-09-25 20:00"))       # Jumat 16:00 NY
    assert clock.entry_block_reason(ts("2026-09-22 20:45"))       # rollover 16:45 NY
    assert clock.entry_block_reason(ts("2026-09-27 21:30"))       # Minggu baru buka
    assert clock.entry_block_reason(ts("2026-09-22 13:00")) is None


def test_news_filter_blocks_window_and_filters_impact():
    payload = [
        {"title": "Non-Farm Employment Change", "country": "USD", "date": "2026-10-02T08:30:00-04:00",
         "impact": "High"},
        {"title": "Retail Sales m/m", "country": "EUR", "date": "2026-10-02T05:00:00-04:00",
         "impact": "High"},
        {"title": "Crude Oil Inventories", "country": "USD", "date": "2026-10-01T10:30:00-04:00",
         "impact": "Medium"},
    ]
    nf = NewsFilter(NewsConfig(cache_file="/tmp/xau_news_test.json"), fetch=lambda url: payload)
    nf.refresh(ts("2026-10-01 00:00"))
    assert len(nf.events) == 1
    assert nf.blocked(ts("2026-10-02 12:05"))          # 25 menit sebelum NFP (12:30 UTC)
    assert nf.blocked(ts("2026-10-02 12:55"))          # 25 menit sesudah
    assert nf.blocked(ts("2026-10-02 13:10")) is None


def test_news_filter_blocks_on_error_without_data():
    def boom(url):
        raise OSError("offline")
    nf = NewsFilter(NewsConfig(cache_file="/tmp/xau_news_missing.json"), fetch=boom)
    nf.refresh(ts("2026-10-01 00:00"))
    assert nf.blocked(ts("2026-10-01 00:00"))
