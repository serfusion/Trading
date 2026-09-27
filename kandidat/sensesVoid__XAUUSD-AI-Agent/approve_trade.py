import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
from dotenv import load_dotenv

from mt5_bridge import MT5Bridge
from trade_executor import TradeExecutor, TradeExecutionError

load_dotenv()

SIGNAL_FILE = Path("latest_signal.json")
HISTORY_FILE = Path("trade_history.jsonl")
STALE_AFTER_MINUTES = 5
MAX_PRICE_DRIFT_ATR_MULT = 0.3  # reject-warn if price moved more than this fraction of the SL distance


def load_pending_signal() -> dict | None:
    if not SIGNAL_FILE.exists():
        print("No signal file found. Run main.py first.")
        return None
    with open(SIGNAL_FILE) as f:
        data = json.load(f)
    if data.get("already_actioned"):
        print("This signal has already been approved or rejected. Waiting for the next pipeline cycle.")
        return None
    return data


def mark_actioned(data: dict, outcome: str, detail: dict | None = None):
    data["already_actioned"] = True
    data["outcome"] = outcome
    data["outcome_detail"] = detail
    with open(SIGNAL_FILE, "w") as f:
        json.dump(data, f, indent=2)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps({**data, "logged_at": datetime.now(timezone.utc).isoformat()}) + "\n")


def signal_age_minutes(data: dict) -> float:
    ts = datetime.fromisoformat(data["timestamp"])
    return (datetime.now(timezone.utc) - ts).total_seconds() / 60


def main():
    data = load_pending_signal()
    if data is None:
        return

    if data["direction"] not in ("LONG", "SHORT"):
        print(f"Latest signal is {data['direction']} — nothing to approve.")
        return

    plan = data.get("execution_plan")
    if plan is None:
        print("Signal has no execution plan attached (risk calc may have failed). Nothing to execute.")
        return

    age = signal_age_minutes(data)
    print("=" * 60)
    print(f"PENDING SIGNAL — generated {age:.1f} min ago")
    print(f"Direction:      {data['direction']}")
    print(f"Confidence:     {data['confidence']}")
    print(f"Strategy:       {data['matched_strategy']}")
    print(f"Reasoning:      {data['reasoning']}")
    print("-" * 60)
    print(f"Entry (at gen): {plan['entry_price']}")
    print(f"Stop Loss:      {plan['stop_loss']}")
    print(f"Take Profit:    {plan['take_profit']}")
    print(f"Lot size:       {plan['lot_size']}")
    print(f"Risk amount:    ${plan['risk_amount']}")
    print(f"Reward amount:  ${plan['reward_amount']}")
    print("=" * 60)

    if age > STALE_AFTER_MINUTES:
        print(f"\n⚠ This signal is {age:.1f} minutes old (stale threshold: {STALE_AFTER_MINUTES} min).")
        print("  Market context may have moved on. Consider rejecting and waiting for the next cycle.\n")

    bridge = MT5Bridge(symbol="XAUUSD")
    bridge.connect()

    tick = mt5.symbol_info_tick("XAUUSD")
    current_price = tick.ask if data["direction"] == "LONG" else tick.bid
    drift = abs(current_price - plan["entry_price"])
    drift_tolerance = plan["sl_distance_price"] * MAX_PRICE_DRIFT_ATR_MULT
    if drift > drift_tolerance:
        print(f"⚠ Price has moved {drift:.2f} since generation (tolerance: {drift_tolerance:.2f}).")
        print(f"  Generated entry: {plan['entry_price']}  |  Current price: {current_price}\n")

    choice = input("Approve this trade? [y/N]: ").strip().lower()
    if choice != "y":
        print("Rejected. No order sent.")
        mark_actioned(data, outcome="rejected")
        return

    executor = TradeExecutor(symbol="XAUUSD")
    try:
        result = executor.execute_market_order(
            direction=data["direction"],
            lot_size=plan["lot_size"],
            stop_loss=plan["stop_loss"],
            take_profit=plan["take_profit"],
            comment=f"ai_{data['matched_strategy'][:20]}",
        )
        print(f"\n✓ Order executed. Ticket: {result['ticket']}, Fill price: {result['price']}")
        mark_actioned(data, outcome="executed", detail=result)
    except TradeExecutionError as e:
        print(f"\n✗ Execution failed: {e}")
        mark_actioned(data, outcome="execution_failed", detail={"error": str(e)})


if __name__ == "__main__":
    main()