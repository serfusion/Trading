"""Uji menyeluruh skema F-ensemble: order, SL, TP1, SL+, exit, anti dobel, restart, adopsi."""
import numpy as np
import pandas as pd
import pytest

from helpers import bars_from_path
from test_trend import trend_path
from xau_bot.backtest import XAU_SPEC
from xau_bot.broker.paper import PaperBroker
from xau_bot.config import AppConfig
from xau_bot.engine import Engine
from xau_bot.journal import Journal
from xau_bot.models import Direction
from xau_bot.news import NewsFilter
from xau_bot.telegram import Notifier
from xau_bot.trend_ensemble import OrderThrottle, f_result, leg_plan


class Pub:
    topic = "t"

    def __init__(self):
        self.events = []

    def publish(self, event, text=None, title=None, priority=3, tags=None):
        self.events.append(event)

    def start(self):
        pass

    def stop(self):
        pass


class CountingBroker(PaperBroker):
    """Menghitung semua order market & modifikasi SL."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.market_calls, self.modify_calls = [], []

    def market_order(self, symbol, direction, volume, sl, tp, magic, comment):
        self.market_calls.append((self.now, direction, volume, sl, tp, magic, comment))
        return super().market_order(symbol, direction, volume, sl, tp, magic, comment)

    def modify_position(self, symbol, ticket, sl, tp):
        self.modify_calls.append((ticket, sl, tp))
        return super().modify_position(symbol, ticket, sl, tp)


def make(tmp_path, path=None, balance=1_000_000, trade=True, sets=((55, 20),), journal=None, broker=None,
         start=60 * 4, bias_filter=True):
    m15 = bars_from_path(np.repeat(path or trend_path(), 4), start="2026-09-14 00:00", freq="15min", wick=0.3)
    cfg = AppConfig()
    cfg.trade_enabled = trade
    cfg.news.enabled = False
    cfg.telegram.enabled = False
    cfg.trend.ensemble = [list(x) for x in sets]
    cfg.trend.state_dir = str(tmp_path / "trend")
    cfg.trend.bias_filter = bias_filter
    broker = broker or CountingBroker({cfg.broker.symbol: m15}, "M15", XAU_SPEC, spread=0.2,
                                      balance=balance, start_index=start)
    pub = Pub()
    eng = Engine(cfg, broker, Notifier(), NewsFilter(cfg.news), journal or Journal(":memory:"),
                 clock=lambda: broker.now, publisher=pub)
    assert eng.start()
    return eng, broker, pub


def step_all(eng, broker, until=None, twice=False):
    while broker.advance():
        bar = broker.data[broker.main].iloc[broker.cursor]
        rng = (float(bar["low"]), float(bar["high"]))
        eng.step(price_range=rng)
        if twice:
            eng.step(price_range=rng)
        if until and until():
            return


# ------------------------------------------------------------------- unit
def test_leg_plan():
    assert leg_plan(0.05, 5, 0.01, 0.01) == (5, 0.01)
    assert leg_plan(0.03, 5, 0.01, 0.01) == (3, 0.01)
    assert leg_plan(0.005, 5, 0.01, 0.01) == (1, 0.01)
    n, per = leg_plan(0.23, 5, 0.01, 0.01)
    assert n == 5 and per == pytest.approx(0.04) and n * per <= 0.23


def test_f_result():
    # TP1 kena lalu sisa keluar di BE (0R) -> (1 + 4*0)/5 = 0.2R
    assert f_result(5, 100, 10, 1, True, 100, 1.0) == pytest.approx(0.2)
    assert f_result(5, 100, 10, 1, False, 90, 1.0) == pytest.approx(-1.0)
    assert f_result(5, 100, 10, -1, True, 70, 1.0) == pytest.approx((1 + 4 * 3) / 5)


def test_throttle_uses_engine_clock():
    now = [pd.Timestamp("2026-09-21 10:00", tz="UTC")]
    t = OrderThrottle(3, lambda: now[0])
    assert t.allow(3)
    for _ in range(3):
        t.record()
    assert not t.allow(1)
    now[0] += pd.Timedelta(seconds=61)          # satu menit (jam pasar) kemudian -> boleh lagi
    assert t.allow(3)


# ------------------------------------------------------------ order live
def test_live_five_legs_tp1_slplus_and_exit(tmp_path):
    eng, broker, pub = make(tmp_path)
    step_all(eng, broker)
    buys = [c for c in broker.market_calls if c[1] == Direction.BUY]
    assert len(buys) == 5                                    # 5 posisi, tidak lebih
    sls = {round(c[3], 3) for c in buys}
    assert len(sls) == 1                                     # SL sama untuk semua leg
    tps = [c[4] for c in buys]
    assert sum(1 for tp in tps if tp) == 1                   # hanya leg #1 punya TP1
    entry_sl = buys[0][3]
    assert all(c[5] == eng.trend_systems[0].magic for c in buys)
    # SL+ : setiap modifikasi memindah SL di atas SL awal (ke entry + offset)
    buy_tickets = {p for p in range(1000, 1005)}             # tiket 5 leg BUY pertama
    buy_mods = [m for m in broker.modify_calls if m[0] in buy_tickets]
    assert buy_mods and all(m[1] > entry_sl for m in buy_mods)
    assert len(buy_mods) == 4 and len({m[0] for m in buy_mods}) == 4   # 4 leg sisa, masing2 sekali
    assert any(e.get("type") == "info" and "SL+" in e.get("text", "") for e in pub.events)
    # semua leg BUY tertutup (TP1 + exit channel); yang tersisa hanya sinyal SELL berikutnya
    assert all(p.direction == Direction.SELL for p in broker.positions("XAUUSD", eng.trend_systems[0].magic))
    closed = [t for t in broker.closed if t.direction == Direction.BUY]
    assert len(closed) == 5 and all(t.pnl > 0 for t in closed)


def test_no_double_orders_when_stepping_twice(tmp_path):
    eng, broker, _ = make(tmp_path)
    step_all(eng, broker, twice=True)
    per_signal = {}
    for c in broker.market_calls:
        per_signal.setdefault(c[0], 0)
        per_signal[c[0]] += 1
    assert all(n <= 5 for n in per_signal.values())
    assert len([c for c in broker.market_calls if c[1] == Direction.BUY]) == 5


def test_restart_does_not_duplicate_and_keeps_managing(tmp_path):
    journal = Journal(str(tmp_path / "j.sqlite"))
    eng, broker, _ = make(tmp_path, journal=journal)
    step_all(eng, broker, until=lambda: len(broker.market_calls) >= 5)
    assert len(broker.market_calls) == 5
    # "restart": engine baru, jurnal & state file sama, broker sama (posisi masih terbuka)
    eng2, _, pub2 = make(tmp_path, journal=Journal(str(tmp_path / "j.sqlite")), broker=broker)
    eng2.trend_systems[0].last_bar = None       # paksa evaluasi ulang bar yang sama
    step_all(eng2, broker)
    assert len([c for c in broker.market_calls if c[1] == Direction.BUY]) == 5
    assert broker.modify_calls                   # SL+ tetap dijalankan setelah restart


def test_orphan_positions_are_adopted(tmp_path):
    eng, broker, _ = make(tmp_path)
    step_all(eng, broker, until=lambda: len(broker.market_calls) >= 5)
    sys0 = eng.trend_systems[0]
    sys0.path.unlink()                          # state hilang (mis. file terhapus)
    sys0.state = None
    step_all(eng, broker)
    assert broker.modify_calls                  # tetap SL+ setelah diadopsi
    assert all(p.direction == Direction.SELL for p in broker.positions("XAUUSD", sys0.magic))
    assert len([c for c in broker.market_calls if c[1] == Direction.BUY]) == 5


def test_stop_loss_before_tp1_loses_about_risk(tmp_path):
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4                           # breakout kecil, lalu langsung jatuh
    path = flat + [top] + list(np.linspace(top, top - 60, 3)) + [top - 60] * 20
    eng, broker, _ = make(tmp_path, path=path, balance=100_000, bias_filter=False)  # uji mekanisme SL
    step_all(eng, broker)
    buys = [c for c in broker.market_calls if c[1] == Direction.BUY]
    assert len(buys) == 5
    buy_tickets = set(range(1000, 1005))
    assert not [m for m in broker.modify_calls if m[0] in buy_tickets]   # TP1 belum kena -> tanpa SL+
    loss = sum(t.pnl for t in broker.closed if t.position_id in buy_tickets)
    assert len([t for t in broker.closed if t.position_id in buy_tickets]) == 5
    assert loss < 0 and loss == pytest.approx(-500, rel=0.25)   # 0.5% risiko per set


def test_small_account_live_skips(tmp_path):
    eng, broker, pub = make(tmp_path, balance=100)
    step_all(eng, broker)
    assert broker.market_calls == []
    assert any(e.get("status") == "skipped" and "Lot minimum" in e.get("note", "") for e in pub.events)


def test_signal_mode_virtual_f(tmp_path):
    eng, broker, pub = make(tmp_path, trade=False, balance=100)
    step_all(eng, broker)
    assert broker.market_calls == []
    sig = [e for e in pub.events if e.get("type") == "signal" and e.get("status") == "signal"]
    info = [e for e in pub.events if e.get("type") == "info" and "TP1" in e.get("text", "")]
    close = [e for e in pub.events if e.get("type") == "close"]
    assert sig and sig[0]["tp1"] > sig[0]["entry"] > sig[0]["sl"]
    assert "Lot minimum" in sig[0]["warning"]
    assert info and close and close[0]["id"] == sig[0]["id"] and close[0]["r"] > 0


def test_ensemble_three_sets_independent_magics(tmp_path):
    eng, broker, _ = make(tmp_path, sets=((40, 15), (55, 20), (80, 30)), start=10 * 4)
    magics = {t.magic for t in eng.trend_systems}
    assert len(magics) == 3 and eng.magic not in magics
    step_all(eng, broker)
    per_magic = {}
    for c in broker.market_calls:
        per_magic.setdefault(c[5], 0)
        per_magic[c[5]] += 1
    assert per_magic and all(n % 5 == 0 and n <= 10 for n in per_magic.values())


def test_fixed_leg_lot_for_cent_account(tmp_path):
    m15 = bars_from_path(np.repeat(trend_path(), 4), start="2026-09-14 00:00", freq="15min", wick=0.3)
    cfg = AppConfig()
    cfg.trade_enabled = True
    cfg.news.enabled = False
    cfg.trend.ensemble = [[55, 20]]
    cfg.trend.state_dir = str(tmp_path / "trend")
    cfg.trend.fixed_leg_lot = 0.01
    broker = CountingBroker({cfg.broker.symbol: m15}, "M15", XAU_SPEC, spread=0.2, balance=30_000,
                            start_index=240)       # ~Rp5 jt di akun Cent = 30.000 USC
    eng = Engine(cfg, broker, Notifier(), NewsFilter(cfg.news), Journal(":memory:"),
                 clock=lambda: broker.now, publisher=Pub())
    assert eng.start()
    step_all(eng, broker)
    buys = [c for c in broker.market_calls if c[1] == Direction.BUY]
    assert len(buys) == 5 and all(c[2] == pytest.approx(0.01) for c in buys)


def test_fixed_leg_lot_blocked_when_too_risky(tmp_path):
    m15 = bars_from_path(np.repeat(trend_path(), 4), start="2026-09-14 00:00", freq="15min", wick=0.3)
    cfg = AppConfig()
    cfg.trade_enabled = True
    cfg.news.enabled = False
    cfg.trend.ensemble = [[55, 20]]
    cfg.trend.state_dir = str(tmp_path / "trend")
    cfg.trend.fixed_leg_lot = 0.01
    pub = Pub()
    broker = CountingBroker({cfg.broker.symbol: m15}, "M15", XAU_SPEC, spread=0.2, balance=300,
                            start_index=240)       # saldo terlalu kecil untuk 5 x 0.01
    eng = Engine(cfg, broker, Notifier(), NewsFilter(cfg.news), Journal(":memory:"),
                 clock=lambda: broker.now, publisher=pub)
    assert eng.start()
    step_all(eng, broker)
    assert broker.market_calls == []
    assert any("batas" in e.get("note", "") for e in pub.events if e.get("status") == "skipped")
