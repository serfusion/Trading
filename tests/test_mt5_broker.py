"""Uji MT5Broker dengan modul MetaTrader5 palsu (paket asli hanya ada di Windows)."""
import sys
import types
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from xau_bot.models import Direction


def fake_mt5():
    m = types.ModuleType("MetaTrader5")
    consts = dict(
        TIMEFRAME_M1=1, TIMEFRAME_M5=5, TIMEFRAME_M10=10, TIMEFRAME_M15=15, TIMEFRAME_M30=30,
        TIMEFRAME_H1=16385, TIMEFRAME_H4=16388, TIMEFRAME_D1=16408,
        POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1,
        ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1, ORDER_TYPE_BUY_LIMIT=2, ORDER_TYPE_SELL_LIMIT=3,
        ORDER_TYPE_BUY_STOP=4, ORDER_TYPE_SELL_STOP=5,
        ORDER_FILLING_FOK=0, ORDER_FILLING_IOC=1, ORDER_FILLING_RETURN=2,
        TRADE_ACTION_DEAL=1, TRADE_ACTION_PENDING=5, TRADE_ACTION_SLTP=6, TRADE_ACTION_REMOVE=8,
        ORDER_TIME_GTC=0, TRADE_RETCODE_DONE=10009, TRADE_RETCODE_PLACED=10008,
        TRADE_RETCODE_DONE_PARTIAL=10010, TRADE_RETCODE_INVALID_FILL=10030,
        DEAL_ENTRY_IN=0, DEAL_ENTRY_OUT=1, DEAL_ENTRY_INOUT=2, DEAL_ENTRY_OUT_BY=3,
        DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
    )
    for k, v in consts.items():
        setattr(m, k, v)
    m.sent = []
    symbols = {"XAUUSDm": NS(name="XAUUSDm", digits=3, point=0.001, trade_tick_size=0.001,
                             trade_tick_value=0.1, volume_min=0.01, volume_max=200, volume_step=0.01,
                             trade_stops_level=0, trade_contract_size=100, filling_mode=2)}
    m.initialize = lambda **kw: True
    m.shutdown = lambda: None
    m.last_error = lambda: (0, "ok")
    m.account_info = lambda: NS(login=1, currency="USD", server="Exness-MT5Real", balance=1000.0,
                                equity=1010.0, margin_free=900.0)
    m.symbol_info = lambda s: symbols.get(s)
    m.symbol_select = lambda s, on: s in symbols
    m.symbols_get = lambda pattern: [v for k, v in symbols.items() if k.startswith(pattern.rstrip("*"))]
    m.symbol_info_tick = lambda s: NS(time_msc=1_790_000_000_000, bid=4300.123, ask=4300.323)
    dtype = [("time", "<i8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"), ("close", "<f8"),
             ("tick_volume", "<u8"), ("spread", "<i4"), ("real_volume", "<u8")]
    m.copy_rates_from_pos = lambda s, tf, pos, n: np.array(
        [(1_790_000_000 + i * 300, 1.0, 2.0, 0.5, 1.5, 10, 20, 0) for i in range(n)], dtype=dtype)
    m.positions_get = lambda symbol=None, ticket=None: [
        NS(ticket=11, identifier=11, magic=250925, type=1, volume=0.1, price_open=4301.0, sl=4305.0,
           tp=4290.0, profit=5.0, time=1_790_000_000, comment="SMC SELL")]
    m.orders_get = lambda symbol=None: [
        NS(ticket=21, magic=250925, type=2, volume_current=0.1, price_open=4290.0, sl=4285.0,
           tp=4310.0, time_setup=1_790_000_000, comment="SMC BUY"),
        NS(ticket=22, magic=1, type=3, volume_current=0.1, price_open=4310.0, sl=4315.0,
           tp=4300.0, time_setup=1_790_000_000, comment="lain")]

    def order_send(req):
        m.sent.append(req)
        if req.get("type_filling") == m.ORDER_FILLING_FOK:
            return NS(retcode=m.TRADE_RETCODE_INVALID_FILL, comment="fill", order=0, deal=0, price=0)
        code = m.TRADE_RETCODE_PLACED if req["action"] == m.TRADE_ACTION_PENDING else m.TRADE_RETCODE_DONE
        return NS(retcode=code, comment="ok", order=99, deal=98, price=req.get("price", 0))
    m.order_send = order_send
    m.history_deals_get = lambda a, b: [
        NS(position_id=5, symbol="XAUUSDm", magic=250925, entry=0, type=1, profit=0.0, commission=-0.5,
           swap=0.0, fee=0.0, volume=0.1, time=1_790_000_000),
        NS(position_id=5, symbol="XAUUSDm", magic=250925, entry=1, type=0, profit=-30.0, commission=-0.5,
           swap=0.0, fee=0.0, volume=0.1, time=1_790_000_600),
        NS(position_id=11, symbol="XAUUSDm", magic=250925, entry=0, type=1, profit=0.0, commission=0.0,
           swap=0.0, fee=0.0, volume=0.1, time=1_790_000_000),
    ]
    return m


@pytest.fixture
def broker(monkeypatch):
    m = fake_mt5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", m)
    from xau_bot.broker.mt5 import MT5Broker
    b = MT5Broker(123, "pw", "Exness-MT5Real", server_utc_offset_hours=0)
    assert b.connect()
    return b, m


def test_resolve_exness_suffix(broker):
    b, _ = broker
    assert b.resolve_symbol("XAUUSD") == "XAUUSDm"
    assert b.resolve_symbol("XAGUSD") is None


def test_rates_and_tick(broker):
    b, _ = broker
    df = b.rates("XAUUSDm", "M5", 5)
    assert list(df.columns)[:4] == ["open", "high", "low", "close"]
    assert str(df.index.tz) == "UTC" and len(df) == 5
    tick = b.tick("XAUUSDm")
    assert tick.spread == pytest.approx(0.2)


def test_spec_positions_orders(broker):
    b, _ = broker
    spec = b.symbol_spec("XAUUSDm")
    assert spec.round_price(4300.12345) == pytest.approx(4300.123)
    pos = b.positions("XAUUSDm", 250925)
    assert pos[0].direction == Direction.SELL
    orders = b.orders("XAUUSDm", 250925)
    assert len(orders) == 1 and orders[0].direction == Direction.BUY


def test_order_requests(broker):
    b, m = broker
    b.symbol_spec("XAUUSDm")
    r = b.place_limit("XAUUSDm", Direction.SELL, 0.1, 4310.1234, 4315.0, 4290.0, 250925, "x" * 40)
    assert r.ok and m.sent[-1]["type"] == m.ORDER_TYPE_SELL_LIMIT and len(m.sent[-1]["comment"]) <= 31
    r = b.market_order("XAUUSDm", Direction.BUY, 0.1, 4295.0, 4320.0, 250925, "c")
    assert r.ok and m.sent[-1]["type"] == m.ORDER_TYPE_BUY and m.sent[-1]["price"] == pytest.approx(4300.323)
    assert m.sent[-1]["type_filling"] == m.ORDER_FILLING_IOC
    assert b.modify_position("XAUUSDm", 11, 4301.1, 4290.0).ok
    r = b.close_position("XAUUSDm", 11, 0.05)
    assert r.ok and m.sent[-1]["type"] == m.ORDER_TYPE_BUY and m.sent[-1]["volume"] == 0.05
    assert b.cancel_order(21).ok


def test_closed_trades_groups_by_position(broker):
    b, _ = broker
    trades = b.closed_trades("XAUUSDm", 250925, pd.Timestamp("2026-01-01", tz="UTC"))
    assert len(trades) == 1  # posisi 11 masih terbuka
    assert trades[0].pnl == pytest.approx(-31.0)
    assert trades[0].direction == Direction.SELL
