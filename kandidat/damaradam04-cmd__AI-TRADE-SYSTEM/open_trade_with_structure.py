"""
AI GOLD TRADER PRO — Open a Trade Using Structure Analysis (manual direction)

This script:
    1. Connects to MT5
    2. Pulls recent candles for one timeframe
    3. Runs the structure engine (zones + S/R)
    4. Calculates SL/TP from the nearest zones
    5. Opens a trade with that SL/TP

IMPORTANT: You still choose direction ("buy"/"sell") yourself below —
this is not yet a fully automatic signal generator (that's the next phase).
Think of this as "structure-assisted manual trading" for now.

Run with: python open_trade_with_structure.py
"""

import config
from mt5_connector import MT5Connector
from structure_engine import analyze_timeframe, calculate_sl_tp
from trade_executor import TradeExecutor

# --- 1. Choose your settings here ---
DIRECTION = "buy" or "sell"          # "buy" or "sell" — decide this yourself for now
TIMEFRAME = "H1"           # which timeframe's zones/levels to base SL/TP on
RISK_PERCENT = 2           # % of account balance to risk on this trade

def main():
    conn = MT5Connector()
    conn.connect()

    executor = TradeExecutor(conn, allow_live=False)  # stays demo-only until you change this deliberately

    # --- 2. Confirm account is safe before doing anything else ---
    info = conn.account_info()
    print(f"Account {info['login']} | Balance: {info['balance']} {info['currency']} | "
          f"Trade mode: {info['trade_mode']} (0=demo)")
    if info["trade_mode"] != 0:
        print("🛑 This is not a demo account. Stopping.")
        conn.disconnect()
        return

    # --- 3. Pull candles and run structure analysis ---
    df = conn.get_candles(TIMEFRAME)
    result = analyze_timeframe(df)

    current_price_info = conn.get_current_price()
    entry_price = current_price_info["ask"] if DIRECTION == "buy" else current_price_info["bid"]
    print(f"\nCurrent {config.SYMBOL} price — bid: {current_price_info['bid']}, ask: {current_price_info['ask']}")
    print(f"Using entry price: {entry_price} ({DIRECTION})")

    # --- 4. Calculate SL/TP from zones & S/R ---
    try:
        sl_tp = calculate_sl_tp(DIRECTION, entry_price, result["zones"], result["sr_levels"])
    except ValueError as e:
        print(f"\n🛑 Could not calculate SL/TP: {e}")
        print("This usually means there's no clean zone/level nearby on the required side. "
              "Try a different timeframe, or wait for a clearer setup.")
        conn.disconnect()
        return

    print(f"\nCalculated SL: {sl_tp['sl']}")
    print(f"Calculated TP: {sl_tp['tp']}")
    print(f"Risk:Reward ratio: 1:{sl_tp['risk_reward_ratio']}")

    if sl_tp["risk_reward_ratio"] is None or sl_tp["risk_reward_ratio"] < 1.5:
        print("\n⚠️  Risk:Reward ratio is below 1:1.5 — this is generally considered a weak setup.")
        confirm = input("Open this trade anyway? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            conn.disconnect()
            return

    # --- 5. Calculate lot size based on your risk % and the SL distance ---
    stop_loss_pips = sl_tp["risk"]  # for gold, price-distance and "pips" are treated the same here
    lot = executor.calculate_lot_size(risk_percent=RISK_PERCENT, stop_loss_pips=stop_loss_pips)
    print(f"\nCalculated lot size for {RISK_PERCENT}% risk: {lot}")

    # --- 6. Final confirmation before sending a real order (even on demo) ---
    confirm = input(f"\nOpen {DIRECTION.upper()} {lot} lots at ~{entry_price}, "
                     f"SL={sl_tp['sl']}, TP={sl_tp['tp']}? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        conn.disconnect()
        return

    result = executor.open_trade(
        direction=DIRECTION,
        lot=lot,
        stop_loss=sl_tp["sl"],
        take_profit=sl_tp["tp"],
    )
    print("\n✅ Trade result:", result)

    conn.disconnect()


if __name__ == "__main__":
    main()