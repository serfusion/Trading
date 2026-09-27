"""Filter SMC untuk trend: breakout hanya diambil bila searah bias struktur H4 (BOS terakhir)."""
import numpy as np

from test_ensemble import make, step_all
from xau_bot.models import Direction
from xau_bot.smc import structure_bias


def small_breakout_then_drop():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4
    return flat + [top] + list(np.linspace(top, top - 60, 3)) + [top - 60] * 20


def test_breakout_against_h4_structure_is_skipped(tmp_path):
    eng, broker, pub = make(tmp_path, path=small_breakout_then_drop(), balance=100_000)
    step_all(eng, broker)
    assert not [c for c in broker.market_calls if c[1] == Direction.BUY]
    notes = [e.get("note", "") for e in pub.events if e.get("status") == "skipped"]
    assert any("Bias struktur H4" in n and "BUY" in n for n in notes)


def test_breakout_with_h4_structure_is_taken_only_after_bos(tmp_path):
    eng, broker, pub = make(tmp_path)
    first = {}

    def buy_opened():
        if not first and broker.market_calls:
            h4 = broker.rates("XAUUSD", "H4", 300)
            first["bias"] = structure_bias(h4, 3)
        return False

    step_all(eng, broker, until=buy_opened)
    buys = [c for c in broker.market_calls if c[1] == Direction.BUY]
    assert len(buys) == 5
    assert first["bias"] == 1                        # order hanya dibuka saat bias H4 BULLISH
    assert "Bias H4: " in eng._trend_states()


def test_filter_can_be_disabled(tmp_path):
    eng, broker, _ = make(tmp_path, path=small_breakout_then_drop(), balance=100_000, bias_filter=False)
    step_all(eng, broker)
    assert len([c for c in broker.market_calls if c[1] == Direction.BUY]) == 5
    assert eng.trend_bias_block(Direction.BUY) is None
