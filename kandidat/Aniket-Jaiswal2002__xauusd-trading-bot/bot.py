"""
XAUUSD MT5 Trading Bot
Strategy : EMA Crossover + RSI Filter + ATR-based SL/TP
Author   : Your Name
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import ta
import time
import logging
import schedule
from datetime import datetime, timezone
from config import *


# ─────────────────────────────────────────────
#  Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  MT5 Connection
# ─────────────────────────────────────────────
def connect():
    """Initialize and login to MT5."""
    if not mt5.initialize():
        log.error(f"MT5 initialize() failed: {mt5.last_error()}")
        return False

    ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not ok:
        log.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False

    info = mt5.account_info()
    log.info(f"Connected ▸ {info.name} | Balance: {info.balance:.2f} {info.currency}")
    return True


def disconnect():
    mt5.shutdown()
    log.info("MT5 disconnected.")


# ─────────────────────────────────────────────
#  Data
# ─────────────────────────────────────────────
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,  "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,  "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

def get_ohlcv(symbol=SYMBOL, timeframe=TIMEFRAME, bars=200):
    """Fetch OHLCV data from MT5 as a DataFrame."""
    tf = TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None or len(rates) == 0:
        log.error(f"No data for {symbol} {timeframe}")
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df.set_index("time", inplace=True)
    return df


# ─────────────────────────────────────────────
#  Indicators
# ─────────────────────────────────────────────
def add_indicators(df):
    """Add EMA, RSI, ATR columns to the dataframe."""
    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=EMA_FAST)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=EMA_SLOW)
    df["rsi"]      = ta.momentum.rsi(df["close"], window=RSI_PERIOD)
    df["atr"]      = ta.volatility.average_true_range(
                         df["high"], df["low"], df["close"], window=ATR_PERIOD)
    return df


# ─────────────────────────────────────────────
#  Signal Generation
# ─────────────────────────────────────────────
def get_signal(df):
    """
    Returns: 'BUY', 'SELL', or None
    Rules:
      BUY  — EMA fast crosses above EMA slow AND RSI < RSI_OB (not overbought)
      SELL — EMA fast crosses below EMA slow AND RSI > RSI_OS (not oversold)
    """
    last  = df.iloc[-1]
    prev  = df.iloc[-2]

    fast_cross_up   = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]
    fast_cross_down = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]

    if fast_cross_up and last["rsi"] < RSI_OB:
        return "BUY"
    if fast_cross_down and last["rsi"] > RSI_OS:
        return "SELL"
    return None


# ─────────────────────────────────────────────
#  Filters
# ─────────────────────────────────────────────
def session_ok():
    """Only trade during active hours (UTC)."""
    hour = datetime.now(timezone.utc).hour
    return TRADE_HOUR_START <= hour < TRADE_HOUR_END


def spread_ok(symbol=SYMBOL):
    """Check if current spread is within acceptable range."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False
    spread = (tick.ask - tick.bid) / mt5.symbol_info(symbol).point
    if spread > MAX_SPREAD_POINTS:
        log.warning(f"Spread too wide: {spread:.1f} pts — skipping")
        return False
    return True


def daily_loss_ok():
    """Stop trading if daily drawdown exceeds the limit."""
    history = mt5.history_deals_get(
        datetime.now().replace(hour=0, minute=0, second=0),
        datetime.now()
    )
    if not history:
        return True
    today_pnl = sum(d.profit for d in history)
    balance   = mt5.account_info().balance
    if today_pnl < -(balance * DAILY_LOSS_LIMIT):
        log.warning(f"Daily loss limit hit: {today_pnl:.2f} — no new trades today")
        return False
    return True


def count_open_trades(symbol=SYMBOL):
    """Count open positions for this symbol opened by this bot."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return 0
    return sum(1 for p in positions if p.magic == MAGIC)


# ─────────────────────────────────────────────
#  Position Sizing
# ─────────────────────────────────────────────
def calc_lot_size(symbol, sl_distance):
    """
    Risk RISK_PCT of balance per trade.
    lot = (balance × risk%) / (sl_distance × tick_value_per_lot)
    """
    info      = mt5.account_info()
    sym_info  = mt5.symbol_info(symbol)
    balance   = info.balance
    risk_amt  = balance * RISK_PCT

    tick_size  = sym_info.trade_tick_size
    tick_value = sym_info.trade_tick_value
    ticks_in_sl = sl_distance / tick_size

    lot = risk_amt / (ticks_in_sl * tick_value)
    lot = max(sym_info.volume_min,
              min(sym_info.volume_max,
                  round(lot / sym_info.volume_step) * sym_info.volume_step))
    return round(lot, 2)


# ─────────────────────────────────────────────
#  Order Execution
# ─────────────────────────────────────────────
def place_order(signal, symbol=SYMBOL):
    """Send a market order with SL and TP based on ATR."""
    df = get_ohlcv(symbol)
    if df is None:
        return

    df = add_indicators(df)
    atr   = df["atr"].iloc[-1]
    tick  = mt5.symbol_info_tick(symbol)
    point = mt5.symbol_info(symbol).point

    if signal == "BUY":
        price = tick.ask
        sl    = round(price - ATR_SL_MULT * atr, 2)
        tp    = round(price + ATR_TP_MULT * atr, 2)
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl    = round(price + ATR_SL_MULT * atr, 2)
        tp    = round(price - ATR_TP_MULT * atr, 2)
        order_type = mt5.ORDER_TYPE_SELL

    sl_dist = abs(price - sl)
    lot     = calc_lot_size(symbol, sl_dist)

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        price,
        "sl":           sl,
        "tp":           tp,
        "deviation":    10,
        "magic":        MAGIC,
        "comment":      f"XAUUSD_BOT_{signal}",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(
            f"✅ {signal} XAUUSD | Lot: {lot} | Price: {price:.2f} "
            f"| SL: {sl:.2f} | TP: {tp:.2f} | ATR: {atr:.2f}"
        )
    else:
        log.error(f"❌ Order failed [{result.retcode}]: {result.comment}")


# ─────────────────────────────────────────────
#  Trailing Stop (call on a timer)
# ─────────────────────────────────────────────
def update_trailing_stops(symbol=SYMBOL, trail_atr_mult=1.0):
    """Move SL to lock in profit as price moves in our favor."""
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return

    df  = get_ohlcv(symbol)
    df  = add_indicators(df)
    atr = df["atr"].iloc[-1]

    for pos in positions:
        if pos.magic != MAGIC:
            continue

        tick = mt5.symbol_info_tick(symbol)
        trail_dist = trail_atr_mult * atr

        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = round(tick.bid - trail_dist, 2)
            if new_sl > pos.sl:
                _modify_sl(pos.ticket, new_sl, pos.tp)

        elif pos.type == mt5.ORDER_TYPE_SELL:
            new_sl = round(tick.ask + trail_dist, 2)
            if new_sl < pos.sl or pos.sl == 0:
                _modify_sl(pos.ticket, new_sl, pos.tp)


def _modify_sl(ticket, new_sl, tp):
    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl":       new_sl,
        "tp":       tp,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"🔒 Trailing SL updated → {new_sl:.2f} for ticket #{ticket}")


# ─────────────────────────────────────────────
#  Main Loop
# ─────────────────────────────────────────────
def run_bot():
    """Core bot logic — called on each scheduled tick."""
    log.info("─ ─ Scanning ─ ─")

    # Filters
    if not session_ok():
        log.info("Outside trading session. Waiting...")
        return
    if not daily_loss_ok():
        return
    if count_open_trades() >= MAX_OPEN_TRADES:
        log.info(f"Max open trades ({MAX_OPEN_TRADES}) reached.")
        update_trailing_stops()
        return
    if not spread_ok():
        return

    # Data + Signal
    df = get_ohlcv()
    if df is None:
        return
    df = add_indicators(df)

    signal = get_signal(df)
    log.info(
        f"EMA_fast={df['ema_fast'].iloc[-1]:.2f}  "
        f"EMA_slow={df['ema_slow'].iloc[-1]:.2f}  "
        f"RSI={df['rsi'].iloc[-1]:.1f}  "
        f"ATR={df['atr'].iloc[-1]:.2f}  "
        f"Signal={signal or 'HOLD'}"
    )

    if signal:
        place_order(signal)

    # Always update trailing stops
    update_trailing_stops()


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not connect():
        exit(1)

    log.info(" XAUUSD Bot started. Running every 60 seconds.")

    # Run immediately on start, then every minute
    run_bot()
    schedule.every(60).seconds.do(run_bot)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
    finally:
        disconnect()
