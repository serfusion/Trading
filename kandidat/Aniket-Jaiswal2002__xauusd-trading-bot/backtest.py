"""
XAUUSD Backtester
Runs the EMA+RSI strategy on historical data without MT5 connection.
Usage: python backtest.py
"""

import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5
from datetime import datetime
from config import *


def backtest(symbol=SYMBOL, timeframe=TIMEFRAME, bars=5000):
    # ── Connect and fetch data ──────────────────
    mt5.initialize()
    mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)

    tf = {
        "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1,
    }.get(timeframe, mt5.TIMEFRAME_H1)

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)

    # ── Indicators ──────────────────────────────
    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=EMA_FAST)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=EMA_SLOW)
    df["rsi"]      = ta.momentum.rsi(df["close"], window=RSI_PERIOD)
    df["atr"]      = ta.volatility.average_true_range(
                         df["high"], df["low"], df["close"], window=ATR_PERIOD)

    # ── Signals ──────────────────────────────────
    df["signal"] = 0
    for i in range(1, len(df)):
        fast_up   = (df["ema_fast"].iloc[i-1] <= df["ema_slow"].iloc[i-1] and
                     df["ema_fast"].iloc[i]   >  df["ema_slow"].iloc[i])
        fast_down = (df["ema_fast"].iloc[i-1] >= df["ema_slow"].iloc[i-1] and
                     df["ema_fast"].iloc[i]   <  df["ema_slow"].iloc[i])
        rsi_val   = df["rsi"].iloc[i]

        if fast_up and rsi_val < RSI_OB:
            df.loc[df.index[i], "signal"] = 1     # BUY
        elif fast_down and rsi_val > RSI_OS:
            df.loc[df.index[i], "signal"] = -1    # SELL

    # ── Simulate trades ─────────────────────────
    trades    = []
    balance   = 10000.0
    pip_value = 1.0          # $1 per pip per 0.01 lot (simplified)
    lot       = 0.01

    for i in range(len(df)):
        sig = df["signal"].iloc[i]
        if sig == 0:
            continue

        entry  = df["close"].iloc[i]
        atr    = df["atr"].iloc[i]
        sl_pts = ATR_SL_MULT * atr
        tp_pts = ATR_TP_MULT * atr

        # Simulate outcome on remaining bars
        direction = 1 if sig == 1 else -1
        result    = "OPEN"
        pnl       = 0.0

        for j in range(i + 1, min(i + 200, len(df))):
            hi = df["high"].iloc[j]
            lo = df["low"].iloc[j]

            if sig == 1:   # BUY
                if lo <= entry - sl_pts:
                    pnl    = -sl_pts * lot * 100
                    result = "SL"
                    break
                if hi >= entry + tp_pts:
                    pnl    = tp_pts * lot * 100
                    result = "TP"
                    break
            else:          # SELL
                if hi >= entry + sl_pts:
                    pnl    = -sl_pts * lot * 100
                    result = "SL"
                    break
                if lo <= entry - tp_pts:
                    pnl    = tp_pts * lot * 100
                    result = "TP"
                    break

        if result != "OPEN":
            balance += pnl
            trades.append({
                "time": df.index[i],
                "type": "BUY" if sig == 1 else "SELL",
                "entry": entry,
                "result": result,
                "pnl": round(pnl, 2),
                "balance": round(balance, 2),
            })

    # ── Results ──────────────────────────────────
    if not trades:
        print("No trades generated.")
        return

    results = pd.DataFrame(trades)
    wins    = results[results["pnl"] > 0]
    losses  = results[results["pnl"] < 0]

    win_rate    = len(wins) / len(results) * 100
    profit_factor = wins["pnl"].sum() / abs(losses["pnl"].sum()) if len(losses) > 0 else float("inf")
    max_dd      = (results["balance"].cummax() - results["balance"]).max()
    net_profit  = results["pnl"].sum()
    sharpe      = results["pnl"].mean() / results["pnl"].std() * np.sqrt(252) if results["pnl"].std() > 0 else 0

    print("=" * 50)
    print(f"  XAUUSD Backtest — {timeframe} | {bars} bars")
    print("=" * 50)
    print(f"  Total Trades   : {len(results)}")
    print(f"  Win Rate       : {win_rate:.1f}%")
    print(f"  Profit Factor  : {profit_factor:.2f}")
    print(f"  Net Profit     : ${net_profit:.2f}")
    print(f"  Max Drawdown   : ${max_dd:.2f}")
    print(f"  Sharpe Ratio   : {sharpe:.2f}")
    print(f"  Final Balance  : ${balance:.2f}")
    print("=" * 50)

    results.to_csv("backtest_results.csv", index=False)
    print("  Saved → backtest_results.csv")

    return results


if __name__ == "__main__":
    backtest()
