"""
AI GOLD TRADER PRO — Market Structure Engine (Phase 2)

Given a DataFrame of OHLC candles for one timeframe, this module detects:
    - Swing highs / swing lows
    - HH / HL / LH / LL labeling
    - BOS (Break of Structure) — trend continuation break
    - CHoCH (Change of Character) — first break against prevailing trend
    - Supply & Demand zones
    - Support & Resistance levels

No MT5 dependency here — pure pandas/numpy, so it's easy to test standalone
with synthetic data or historical CSVs before plugging in live data.
"""

import pandas as pd
import numpy as np
import config


# ---------------------------------------------------------------------------
# Swing detection
# ---------------------------------------------------------------------------

def find_swings(df: pd.DataFrame, lookback: int = None) -> pd.DataFrame:
    """
    Marks swing highs and swing lows.
    A candle at index i is a swing high if its high is the max within
    [i-lookback, i+lookback], and similarly for swing lows.

    Adds columns: swing_high (bool), swing_low (bool)
    """
    lookback = lookback or config.SWING_LOOKBACK
    df = df.copy()
    n = len(df)
    swing_high = np.zeros(n, dtype=bool)
    swing_low = np.zeros(n, dtype=bool)

    highs = df["high"].values
    lows = df["low"].values

    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback:i + lookback + 1]
        window_low = lows[i - lookback:i + lookback + 1]

        if highs[i] == window_high.max() and np.argmax(window_high) == lookback:
            swing_high[i] = True
        if lows[i] == window_low.min() and np.argmin(window_low) == lookback:
            swing_low[i] = True

    df["swing_high"] = swing_high
    df["swing_low"] = swing_low
    return df


def label_swing_structure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Walks through detected swings in order and labels each as
    HH (higher high), LH (lower high), HL (higher low), LL (lower low)
    relative to the previous swing of the same type.

    Adds column: swing_label (string, only populated on swing rows)
    """
    df = df.copy()
    df["swing_label"] = ""

    last_high = None
    last_low = None

    for i in range(len(df)):
        if df.at[i, "swing_high"]:
            price = df.at[i, "high"]
            if last_high is None:
                label = "H"  # first swing high, no comparison yet
            else:
                label = "HH" if price > last_high else "LH"
            df.at[i, "swing_label"] = label
            last_high = price

        if df.at[i, "swing_low"]:
            price = df.at[i, "low"]
            if last_low is None:
                label = "L"  # first swing low, no comparison yet
            else:
                label = "HL" if price > last_low else "LL"
            df.at[i, "swing_label"] = label
            last_low = price

    return df


# ---------------------------------------------------------------------------
# BOS / CHoCH detection
# ---------------------------------------------------------------------------

def detect_bos_choch(df: pd.DataFrame) -> list:
    """
    Scans labeled swings in sequence and detects BOS / CHoCH events based on
    the classic swing-break logic:

    - Uptrend context (most recent confirmed pattern is HH/HL):
        price closing above the last swing high  -> BOS (trend continuation)
        price closing below the last swing low    -> CHoCH (trend may be reversing to down)
    - Downtrend context (most recent confirmed pattern is LH/LL):
        price closing below the last swing low     -> BOS (trend continuation)
        price closing above the last swing high     -> CHoCH (trend may be reversing to up)

    Returns a list of event dicts: {index, time, type ('BOS'/'CHoCH'), direction, price, reason}
    """
    events = []
    trend = None  # "up" or "down", once established

    last_swing_high = None
    last_swing_high_idx = None
    last_swing_low = None
    last_swing_low_idx = None

    broken_high_idx = None  # avoid re-triggering on the same swing repeatedly
    broken_low_idx = None

    for i in range(len(df)):
        row = df.iloc[i]

        # Update tracked swing points as we walk forward
        if row["swing_high"]:
            last_swing_high = row["high"]
            last_swing_high_idx = i
        if row["swing_low"]:
            last_swing_low = row["low"]
            last_swing_low_idx = i

        close = row["close"]

        # Check break above last swing high
        if last_swing_high is not None and close > last_swing_high and last_swing_high_idx != broken_high_idx:
            if trend in (None, "up"):
                event_type = "BOS"
                reason = "Price closed above prior swing high, continuing the uptrend."
            else:
                event_type = "CHoCH"
                reason = "Price closed above prior swing high, breaking the downtrend structure."
            events.append({
                "index": i, "time": row["time"], "type": event_type,
                "direction": "bullish", "price": close, "reason": reason,
            })
            trend = "up"
            broken_high_idx = last_swing_high_idx

        # Check break below last swing low
        if last_swing_low is not None and close < last_swing_low and last_swing_low_idx != broken_low_idx:
            if trend in (None, "down"):
                event_type = "BOS"
                reason = "Price closed below prior swing low, continuing the downtrend."
            else:
                event_type = "CHoCH"
                reason = "Price closed below prior swing low, breaking the uptrend structure."
            events.append({
                "index": i, "time": row["time"], "type": event_type,
                "direction": "bearish", "price": close, "reason": reason,
            })
            trend = "down"
            broken_low_idx = last_swing_low_idx

    return events


# ---------------------------------------------------------------------------
# Supply & Demand zones
# ---------------------------------------------------------------------------

def find_supply_demand_zones(df: pd.DataFrame, impulse_threshold_pct: float = None) -> list:
    """
    Identifies supply/demand zones using a simplified version of the common
    SMC approach: look for the last opposite-colored candle immediately
    before a strong (impulsive) directional move.

    - Demand zone: last down (bearish) candle before a strong up move
    - Supply zone: last up (bullish) candle before a strong down move

    Returns a list of zone dicts:
        {type: 'demand'/'supply', top, bottom, origin_index, origin_time, strength_pct}
    """
    threshold = impulse_threshold_pct or config.ZONE_IMPULSE_THRESHOLD_PCT
    zones = []

    for i in range(1, len(df) - 1):
        candle = df.iloc[i]
        next_candle = df.iloc[i + 1]

        move_pct = (next_candle["close"] - candle["close"]) / candle["close"] * 100

        # Bullish impulse after a down candle -> demand zone
        is_down_candle = candle["close"] < candle["open"]
        if is_down_candle and move_pct >= threshold:
            zones.append({
                "type": "demand",
                "top": candle["open"],
                "bottom": candle["low"],
                "origin_index": i,
                "origin_time": candle["time"],
                "strength_pct": round(move_pct, 3),
            })

        # Bearish impulse after an up candle -> supply zone
        is_up_candle = candle["close"] > candle["open"]
        if is_up_candle and move_pct <= -threshold:
            zones.append({
                "type": "supply",
                "top": candle["high"],
                "bottom": candle["open"],
                "origin_index": i,
                "origin_time": candle["time"],
                "strength_pct": round(abs(move_pct), 3),
            })

    return zones


def mark_zone_status(zones: list, df: pd.DataFrame) -> list:
    """
    Marks each zone as 'fresh' (never revisited) or 'mitigated' (price has
    traded back into it since it formed). Fresh zones are generally considered
    higher-probability for future reactions.
    """
    for zone in zones:
        origin_idx = zone["origin_index"]
        subsequent = df.iloc[origin_idx + 2:]  # skip the impulse candle itself
        touched = subsequent[
            (subsequent["low"] <= zone["top"]) & (subsequent["high"] >= zone["bottom"])
        ]
        zone["status"] = "mitigated" if len(touched) > 0 else "fresh"
    return zones


# ---------------------------------------------------------------------------
# Support & Resistance
# ---------------------------------------------------------------------------

def find_support_resistance(df: pd.DataFrame, tolerance_pct: float = None, min_touches: int = None) -> list:
    """
    Clusters swing highs/lows into horizontal support/resistance levels based
    on how many times price has reacted near the same price zone.

    Returns a list of level dicts: {price, type ('support'/'resistance'), touches}
    """
    tolerance_pct = tolerance_pct or config.SR_TOUCH_TOLERANCE_PCT
    min_touches = min_touches or config.SR_MIN_TOUCHES

    swing_points = []
    for i in range(len(df)):
        if df.at[i, "swing_high"]:
            swing_points.append((df.at[i, "high"], "resistance"))
        if df.at[i, "swing_low"]:
            swing_points.append((df.at[i, "low"], "support"))

    levels = []
    used = [False] * len(swing_points)

    for i, (price, kind) in enumerate(swing_points):
        if used[i]:
            continue
        cluster = [price]
        used[i] = True
        for j in range(i + 1, len(swing_points)):
            if used[j]:
                continue
            other_price, other_kind = swing_points[j]
            if other_kind != kind:
                continue
            if abs(other_price - price) / price * 100 <= tolerance_pct:
                cluster.append(other_price)
                used[j] = True

        if len(cluster) >= min_touches:
            levels.append({
                "price": round(sum(cluster) / len(cluster), 2),
                "type": kind,
                "touches": len(cluster),
            })

    levels.sort(key=lambda x: x["touches"], reverse=True)
    return levels


# ---------------------------------------------------------------------------
# Stop Loss / Take Profit calculation (based on zones & S/R)
# ---------------------------------------------------------------------------

def calculate_sl_tp(direction: str, entry_price: float, zones: list, sr_levels: list,
                     buffer_pct: float = 0.1) -> dict:
    """
    Determines a sensible Stop Loss and Take Profit based on nearby
    supply/demand zones and support/resistance levels.

    direction: 'buy' or 'sell'
    entry_price: the price you'd be entering at
    zones: output of find_supply_demand_zones() (+ mark_zone_status())
    sr_levels: output of find_support_resistance()
    buffer_pct: extra % distance added beyond the zone/level, as safety margin

    Returns: {sl, tp, risk_reward_ratio} or raises ValueError if no
    suitable zone/level is found on the required side of entry_price.
    """
    direction = direction.lower()
    if direction not in ("buy", "sell"):
        raise ValueError("direction must be 'buy' or 'sell'")

    if direction == "buy":
        # SL: nearest fresh demand zone below entry
        candidates_sl = [z for z in zones if z["type"] == "demand" and z["status"] == "fresh"
                          and z["bottom"] < entry_price]
        if not candidates_sl:
            raise ValueError("No fresh demand zone found below entry price for SL placement.")
        nearest_demand = max(candidates_sl, key=lambda z: z["bottom"])
        sl = nearest_demand["bottom"] * (1 - buffer_pct / 100)

        # TP: nearest resistance / supply zone above entry
        candidates_tp = [lvl["price"] for lvl in sr_levels
                          if lvl["type"] == "resistance" and lvl["price"] > entry_price]
        candidates_tp += [z["bottom"] for z in zones
                           if z["type"] == "supply" and z["bottom"] > entry_price]
        if not candidates_tp:
            raise ValueError("No resistance/supply zone found above entry price for TP placement.")
        tp = min(candidates_tp)

    else:  # sell
        candidates_sl = [z for z in zones if z["type"] == "supply" and z["status"] == "fresh"
                          and z["top"] > entry_price]
        if not candidates_sl:
            raise ValueError("No fresh supply zone found above entry price for SL placement.")
        nearest_supply = min(candidates_sl, key=lambda z: z["top"])
        sl = nearest_supply["top"] * (1 + buffer_pct / 100)

        candidates_tp = [lvl["price"] for lvl in sr_levels
                          if lvl["type"] == "support" and lvl["price"] < entry_price]
        candidates_tp += [z["top"] for z in zones
                           if z["type"] == "demand" and z["top"] < entry_price]
        if not candidates_tp:
            raise ValueError("No support/demand zone found below entry price for TP placement.")
        tp = max(candidates_tp)

    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    rr_ratio = round(reward / risk, 2) if risk > 0 else None

    return {
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "risk_reward_ratio": rr_ratio,
    }


# ---------------------------------------------------------------------------
# Convenience: run the full pipeline on one timeframe
# ---------------------------------------------------------------------------

def analyze_timeframe(df: pd.DataFrame) -> dict:
    """Runs the full structure analysis pipeline on a single timeframe's candles."""
    df = find_swings(df)
    df = label_swing_structure(df)

    events = detect_bos_choch(df)
    zones = find_supply_demand_zones(df)
    zones = mark_zone_status(zones, df)
    sr_levels = find_support_resistance(df)

    current_trend = None
    for e in reversed(events):
        current_trend = "up" if e["direction"] == "bullish" else "down"
        break

    return {
        "df": df,
        "events": events,
        "zones": zones,
        "sr_levels": sr_levels,
        "current_trend": current_trend,
        "last_event": events[-1] if events else None,
    }


if __name__ == "__main__":
    # Quick self-test with synthetic data so this module can be verified
    # without needing a live MT5 connection.
    import numpy as np
    np.random.seed(42)
    n = 200
    price = 2000
    rows = []
    t0 = pd.Timestamp("2026-01-01")
    for i in range(n):
        change = np.random.normal(0, 5)
        open_ = price
        close = price + change
        high = max(open_, close) + abs(np.random.normal(0, 2))
        low = min(open_, close) - abs(np.random.normal(0, 2))
        rows.append({
            "time": t0 + pd.Timedelta(hours=i),
            "open": open_, "high": high, "low": low, "close": close,
            "volume": np.random.randint(100, 1000), "spread": 20,
        })
        price = close

    synthetic_df = pd.DataFrame(rows)
    result = analyze_timeframe(synthetic_df)

    print(f"Detected {result['df']['swing_high'].sum()} swing highs, "
          f"{result['df']['swing_low'].sum()} swing lows")
    print(f"Detected {len(result['events'])} BOS/CHoCH events")
    if result["last_event"]:
        print(f"  Most recent: {result['last_event']['type']} "
              f"({result['last_event']['direction']}) - {result['last_event']['reason']}")
    print(f"Detected {len(result['zones'])} supply/demand zones "
          f"({sum(1 for z in result['zones'] if z['status']=='fresh')} fresh)")
    print(f"Detected {len(result['sr_levels'])} S/R levels")
    for lvl in result["sr_levels"][:5]:
        print(f"  {lvl['type']} at {lvl['price']} ({lvl['touches']} touches)")
