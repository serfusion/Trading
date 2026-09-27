from scalpdaily.bridge import (
    read_market_data as _read_market_data,
    read_positions as _read_positions,
    read_daily_tracker as _read_tracker,
    write_daily_tracker as _write_tracker,
    write_signal as _write_signal,
    write_order_request as _write_order_request,
)
from scalpdaily.bridge import BRIDGE_PATH, SIGNALS_FILE


def read_market_data():
    return _read_market_data()


def read_positions():
    return _read_positions()


def read_tracker():
    return _read_tracker()


def write_tracker(data):
    _write_tracker(data)


def write_signal(side, reason, lot_buy, lot_sell, sl_pips, tp_pips, be, trail,
                 bar_time="", session="", spike_score=0.0, conf=0.0):
    _write_signal(
        side, conf, reason, lot_buy, lot_sell,
        sl_pips, tp_pips, be, trail,
        bar_time=bar_time, session=session,
        spike_score=spike_score,
    )

def write_order_request(action, symbol, sl=0.0, tp=0.0):
    _write_order_request(action, symbol, sl, tp)
