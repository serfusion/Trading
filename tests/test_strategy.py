import pandas as pd
import pytest

from helpers import add_sweep_and_mss, bars_from_path, mirror_prices, sell_setup_path
from xau_bot.config import AppConfig
from xau_bot.models import Direction
from xau_bot.sessions import SessionClock
from xau_bot.smc import find_swings, structure_bias, swing_mask
from xau_bot.strategy import MarketContext, SmcStrategy

EMPTY = pd.DataFrame(columns=["open", "high", "low", "close"], index=pd.DatetimeIndex([], tz="UTC"))


def make_strategy(**overrides):
    cfg = AppConfig()
    for k, v in overrides.items():
        setattr(cfg.strategy, k, v)
    return SmcStrategy(cfg.strategy, SessionClock(cfg.sessions)), cfg


def evaluate(df, spread=0.2, **overrides):
    strat, _ = make_strategy(**overrides)
    return strat.evaluate(MarketContext(entry=df, htf=EMPTY, spread=spread))


def test_swing_mask_has_no_lookahead_and_detects_peak():
    import numpy as np
    vals = np.array([1, 2, 3, 5, 3, 2, 1, 2, 3], dtype=float)
    mask = swing_mask(vals, 2, "high")
    assert mask.tolist() == [False, False, False, True, False, False, False, False, False]
    swings = find_swings(bars_from_path(vals + 4000), 2, "high")
    assert swings[0].idx == 3 and swings[0].confirmed_idx == 5


def test_sell_setup_detected_with_correct_geometry():
    df = add_sweep_and_mss(sell_setup_path())
    setups = evaluate(df)
    assert len(setups) == 1
    s = setups[0]
    assert s.direction == Direction.SELL
    assert s.sl > s.sweep_extreme > s.entry > s.tp1 > s.tp2  # SL (merah) di ATAS, profit di BAWAH
    assert s.sweep_extreme == pytest.approx(4341.5)
    assert s.sl == pytest.approx(4341.5 + 0.3 + 0.2)
    assert s.poi_kind == "FVG 50%"
    assert s.rr >= 3
    assert s.components["sweep"] and s.components["mss"] and s.components["premium_discount"]


def test_buy_setup_is_exact_mirror_of_sell():
    df = add_sweep_and_mss(sell_setup_path())
    pivot = 8670.0
    setups = evaluate(mirror_prices(df, pivot), spread=0.0)
    sells = evaluate(df, spread=0.0)
    assert len(setups) == 1 and len(sells) == 1
    b, s = setups[0], sells[0]
    assert b.direction == Direction.BUY
    assert b.sl < b.sweep_extreme < b.entry < b.tp1 < b.tp2  # SL (merah) di BAWAH, profit di ATAS
    assert b.entry == pytest.approx(pivot - s.entry)
    assert b.sl == pytest.approx(pivot - s.sl)
    assert b.tp2 == pytest.approx(pivot - s.tp2)
    assert b.score == s.score


def test_buy_limit_accounts_for_spread():
    df = mirror_prices(add_sweep_and_mss(sell_setup_path()))
    no_spread = evaluate(df, spread=0.0)[0]
    with_spread = evaluate(df, spread=0.3)[0]
    assert with_spread.entry == pytest.approx(no_spread.entry + 0.3)  # buy limit terisi di ASK
    assert with_spread.sl == pytest.approx(no_spread.sl)             # SL buy dipicu BID


def test_no_setup_before_mss():
    df = add_sweep_and_mss(sell_setup_path()).iloc[:-2]  # baru sweep, belum MSS
    assert evaluate(df) == []


def test_setup_expires_after_max_age():
    df = add_sweep_and_mss(sell_setup_path())
    last = df.iloc[-1]
    idx = pd.date_range(df.index[-1] + pd.Timedelta(minutes=5), periods=8, freq="5min", tz="UTC")
    flat = pd.DataFrame({"open": last.close, "high": last.close + 0.3, "low": last.close - 0.3,
                         "close": last.close}, index=idx)
    assert evaluate(pd.concat([df, flat])) == []


def test_setup_invalid_when_sweep_extreme_broken():
    df = add_sweep_and_mss(sell_setup_path())
    t = df.index[-1] + pd.Timedelta(minutes=5)
    spike = pd.DataFrame([(4328.2, 4342.5, 4328.0, 4330.0)], columns=["open", "high", "low", "close"],
                         index=pd.DatetimeIndex([t]))
    assert evaluate(pd.concat([df, spike])) == []


def test_threshold_blocks_low_score():
    df = add_sweep_and_mss(sell_setup_path())
    assert evaluate(df, score_threshold=13) == []


def test_max_sl_filter():
    df = add_sweep_and_mss(sell_setup_path())
    assert evaluate(df, max_sl=2.0) == []


def test_smt_divergence_adds_score():
    df = add_sweep_and_mss(sell_setup_path())
    strat, _ = make_strategy()
    base = strat.evaluate(MarketContext(entry=df, htf=EMPTY, spread=0.2))[0]
    # Perak: high kedua LEBIH RENDAH (gagal higher high) -> SMT bearish.
    silver = df.copy() / 150.0
    sweep_pos = df.index.get_loc(base.sweep_time)
    silver.iloc[sweep_pos:, :] -= 0.5
    with_smt = strat.evaluate(MarketContext(entry=df, htf=EMPTY, spread=0.2,
                                            correlated={"XAGUSD": (silver, 1)}))[0]
    assert with_smt.components["smt"]
    assert with_smt.score == base.score + 2


def test_structure_bias():
    up = bars_from_path([4000 + i + (3 if i % 6 == 3 else 0) - (3 if i % 6 == 0 else 0)
                         for i in range(80)], freq="1h")
    assert structure_bias(up, 2) == 1
    assert structure_bias(mirror_prices(up), 2) == -1
