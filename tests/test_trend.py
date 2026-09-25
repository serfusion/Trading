import numpy as np

from helpers import bars_from_path
from xau_bot.backtest import XAU_SPEC
from xau_bot.broker.paper import PaperBroker
from xau_bot.config import AppConfig, TrendConfig
from xau_bot.engine import Engine
from xau_bot.journal import Journal
from xau_bot.models import Direction
from xau_bot.news import NewsFilter
from xau_bot.telegram import Notifier
from xau_bot.trend import TrendStrategy


class Capture(Notifier):
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)


def trend_path(n_flat=80, n_up=40, n_down=60):
    flat = [4300 + 2 * np.sin(i / 2) for i in range(n_flat)]
    up = list(np.linspace(flat[-1], flat[-1] + 60, n_up))
    down = list(np.linspace(up[-1], up[-1] - 45, n_down))
    return flat + up + down


def test_breakout_signal_and_exit():
    strat = TrendStrategy(TrendConfig(entry_period=55, exit_period=20))
    bars = bars_from_path(trend_path(), freq="1h", wick=0.5)
    signals = [strat.evaluate(bars.iloc[:i], None).action for i in range(60, 85)]
    assert "open" in signals
    first = 60 + signals.index("open")
    sig = strat.evaluate(bars.iloc[:first], None)
    assert sig.direction == Direction.BUY and sig.atr > 0
    exits = [strat.evaluate(bars.iloc[:i], Direction.BUY).action for i in range(125, len(bars))]
    assert "close" in exits


def test_no_lookahead_uses_previous_bars_only():
    strat = TrendStrategy(TrendConfig(entry_period=5, exit_period=3, atr_period=3))
    bars = bars_from_path([100, 101, 102, 101, 100, 99, 103.0], freq="1h", wick=0.1)
    assert strat.evaluate(bars, None).action == "open"          # 103 > high 5 bar sebelumnya
    assert strat.evaluate(bars.iloc[:-1], None).action == "none"


def test_engine_trend_trade_end_to_end():
    m15 = bars_from_path(np.repeat(trend_path(), 4), start="2026-09-14 00:00", freq="15min", wick=0.3)
    cfg = AppConfig()
    cfg.news.enabled = False
    cfg.telegram.enabled = False
    broker = PaperBroker({cfg.broker.symbol: m15}, "M15", XAU_SPEC, spread=0.2, balance=100_000,
                         start_index=60 * 4)
    notes = Capture()
    engine = Engine(cfg, broker, notes, NewsFilter(cfg.news), Journal(":memory:"), clock=lambda: broker.now)
    assert engine.start()
    while broker.advance():
        bar = broker.data[broker.main].iloc[broker.cursor]
        engine.step(price_range=(float(bar["low"]), float(bar["high"])))
    assert any("TREND BUY" in m and "Market order terbuka" in m for m in notes.messages)
    assert any("ditutup" in m for m in notes.messages)
    assert broker.closed and broker.closed[0].pnl > 0
    lost = [t for t in broker.closed if t.pnl < 0]
    assert all(t.pnl > -0.011 * 100_000 for t in lost)      # risiko <= ~1%


def test_trend_mode_default():
    assert AppConfig().strategy.mode == "trend"
