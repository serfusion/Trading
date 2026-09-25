import pandas as pd
import pytest

from helpers import add_sweep_and_mss, mirror_prices, sell_setup_path
from xau_bot.backtest import XAU_SPEC, run_backtest
from xau_bot.broker.paper import PaperBroker
from xau_bot.config import AppConfig
from xau_bot.engine import Engine
from xau_bot.journal import Journal
from xau_bot.news import NewsFilter
from xau_bot.telegram import Notifier


class Capture(Notifier):
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)


def continuation(df, rows):
    idx = pd.date_range(df.index[-1] + pd.Timedelta(minutes=5), periods=len(rows), freq="5min", tz="UTC")
    return pd.concat([df, pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)])


WIN_ROWS = [
    (4328.2, 4332.2, 4328.0, 4332.0),
    (4332.0, 4337.5, 4331.8, 4336.5),   # retrace ke FVG -> sell limit 4337.25 terisi
    (4336.5, 4336.8, 4332.5, 4333.0),
    (4333.0, 4333.2, 4327.5, 4328.0),   # TP1 (4328.1 ask) tercapai
    (4328.0, 4328.4, 4323.0, 4323.5),
    (4323.5, 4323.8, 4318.0, 4318.5),
    (4318.5, 4318.7, 4314.0, 4315.0),   # TP2 ~4317.6 tercapai
    (4315.0, 4316.0, 4314.5, 4315.5),
]


def build(df, cfg=None, balance=10_000.0):
    cfg = cfg or AppConfig()
    cfg.strategy.mode = "smc" if cfg.strategy.mode == "trend" else cfg.strategy.mode
    cfg.news.enabled = False
    cfg.telegram.enabled = False
    start = df.index.get_loc(df.index[-len(WIN_ROWS) - 2])  # bar sebelum MSS
    broker = PaperBroker({cfg.broker.symbol: df}, "M5", XAU_SPEC, spread=0.2, balance=balance,
                         start_index=start)
    notes = Capture()
    engine = Engine(cfg, broker, notes, NewsFilter(cfg.news), Journal(":memory:"), clock=lambda: broker.now)
    assert engine.start()
    return engine, broker, notes


def run_all(engine, broker):
    while broker.advance():
        bar = broker.data[broker.main].iloc[broker.cursor]
        engine.step(price_range=(float(bar["low"]), float(bar["high"])))


def test_sell_setup_end_to_end_places_limit_moves_be_and_hits_tp2():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(df)
    run_all(engine, broker)
    assert any("SETUP SELL" in m and "Limit order terpasang" in m for m in notes.messages)
    assert any("BE" in m for m in notes.messages)
    assert len(broker.closed) == 2                      # TP1 & TP2
    assert all(t.pnl > 0 for t in broker.closed)
    assert broker.balance > 10_000
    risk_money = 10_000 * 0.01
    assert broker.balance - 10_000 > 2 * risk_money     # hasil > 2R


def test_buy_mirror_end_to_end():
    pivot = 8670.0
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(mirror_prices(df, pivot))
    run_all(engine, broker)
    assert any("SETUP BUY" in m for m in notes.messages)
    assert broker.closed and all(t.pnl > 0 for t in broker.closed)


def test_stop_loss_hit_loses_about_one_r():
    rows = [
        (4328.2, 4332.2, 4328.0, 4332.0),
        (4332.0, 4337.5, 4331.8, 4336.5),   # terisi
        (4336.5, 4342.5, 4336.0, 4342.2),   # tembus SL 4342.0
    ] + [(4342.2, 4342.6, 4341.8, 4342.3)] * 5
    df = continuation(add_sweep_and_mss(sell_setup_path()), rows)
    engine, broker, _ = build(df)
    run_all(engine, broker)
    loss = broker.balance - 10_000
    assert loss < 0
    assert loss == pytest.approx(-100, rel=0.1)          # ~1% saldo


def test_signals_only_mode_places_nothing():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    cfg = AppConfig()
    cfg.trade_enabled = False
    engine, broker, notes = build(df, cfg)
    run_all(engine, broker)
    assert any("Sinyal saja" in m for m in notes.messages)
    assert broker.closed == [] and broker.orders("XAUUSD", cfg.broker.magic) == []


def test_pause_blocks_new_setup():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(df)
    engine.command_handlers()["pause"]("")
    run_all(engine, broker)
    assert any("Dilewati: Bot dijeda" in m for m in notes.messages)
    assert broker.closed == []


def test_small_account_skips_when_min_lot_too_risky():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(df, balance=100.0)
    run_all(engine, broker)
    assert any("Lot minimum" in m for m in notes.messages)
    assert broker.closed == []


def test_run_backtest_summary():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    cfg = AppConfig()
    cfg.strategy.mode = "smc"
    cfg.strategy.bars = 60
    result = run_backtest(cfg, df, balance=10_000)
    assert result.end_balance > 10_000
    assert "win-rate" in result.summary()


def test_telegram_commands_processed_on_main_loop():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(df)
    queue = [("status", ""), ("pause", ""), ("tidakada", "")]
    notes.pending_commands = lambda: [queue.pop(0)] if queue else []
    for _ in range(3):
        broker.advance()
        engine.step()
    assert engine.paused
    assert any("XAUUSD" in m and "spread" in m for m in notes.messages)
    assert any("/closeall" in m for m in notes.messages)   # perintah tak dikenal -> bantuan


def test_temporarily_skipped_setup_is_retried_next_bar():
    df = continuation(add_sweep_and_mss(sell_setup_path()), WIN_ROWS)
    engine, broker, notes = build(df)
    engine.paused = True
    broker.advance()
    bar = broker.data[broker.main].iloc[broker.cursor]
    engine.step(price_range=(float(bar["low"]), float(bar["high"])))   # bar MSS: dijeda -> dilewati
    assert any("Dilewati: Bot dijeda" in m for m in notes.messages)
    engine.paused = False
    run_all(engine, broker)
    assert sum("Dilewati" in m for m in notes.messages) == 1           # tidak spam
    assert any("Limit order terpasang" in m for m in notes.messages)   # dicoba ulang & dieksekusi
    assert broker.balance > 10_000
