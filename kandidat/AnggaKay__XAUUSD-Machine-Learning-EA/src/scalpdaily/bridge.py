"""Vektor Bot — Bridge: file-based I/O, AI Analyst → EA Executor."""
import json
import time
from pathlib import Path
from typing import Optional
import pandas as pd

BRIDGE_PATH = Path(
    r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ScalpDailyBridge"
)
MARKET_DATA_FILE = BRIDGE_PATH / "market_data.json"
SIGNALS_FILE = BRIDGE_PATH / "signals.json"
ORDERS_FILE = BRIDGE_PATH / "orders.json"
POSITIONS_FILE = BRIDGE_PATH / "positions.json"
DAILY_FILE = BRIDGE_PATH / "daily_tracker.json"
BAR_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

def _parse_bars(bars_raw: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(bars_raw)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    return df.sort_values("timestamp").reset_index(drop=True)

def read_market_data() -> Optional[dict]:
    raw = None
    for attempt in range(3):
        if not MARKET_DATA_FILE.exists():
            if attempt < 2:
                time.sleep(0.1)
                continue
            return None
        try:
            raw = json.loads(MARKET_DATA_FILE.read_text(encoding="utf-8"))
            break
        except (json.JSONDecodeError, OSError):
            if attempt < 2:
                time.sleep(0.1)
                continue
            return None
    result = {
        "timestamp": raw.get("timestamp"),
        "symbol": raw.get("symbol", "XAUUSD"),
        "primary_timeframe": raw.get("primary_timeframe", "M1"),
        "timeframes": raw.get("timeframes", ["M1", "M5", "H1"]),
        "ohlcv": raw.get("ohlcv", {}),
        "indicators": raw.get("indicators", {}),
    }
    for tf in result["timeframes"]:
        key = f"bars_{tf}"
        if key in raw:
            result[key] = _parse_bars(raw[key])
        elif tf == result["primary_timeframe"] and "bars" in raw:
            result[key] = _parse_bars(raw["bars"])
        else:
            result[key] = pd.DataFrame()
    if "bars" in raw and result["primary_timeframe"] not in raw.get("timeframes", []):
        result["bars"] = _parse_bars(raw["bars"])
    return result

class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        import numpy as np
        if isinstance(o, (np.floating, np.integer)):
            return float(o) if isinstance(o, np.floating) else int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return super().default(o)

def write_signal_vektor(
    signal: str,
    confidence: float,
    reason: str,
    lot_buy: float,
    lot_sell: float,
    sl_pips: int,
    tp_pips: int,
    breakeven_trigger: int,
    trailing_step: int,
    bar_time: str = "",
    session: str = "",
    regime: str = "",
    spike_score: float = 0.0,
    components: Optional[dict] = None,
) -> None:
    payload = {
        "signal": signal,
        "confidence": float(round(confidence, 4)),
        "reason": reason,
        "lot_buy": float(lot_buy),
        "lot_sell": float(lot_sell),
        "sl_pips": int(sl_pips),
        "tp_pips": int(tp_pips),
        "breakeven_trigger": int(breakeven_trigger),
        "trailing_step": int(trailing_step),
        "bar_time": bar_time,
        "session": session,
        "regime": regime,
        "spike_score": float(round(spike_score, 1)),
    }
    tmp_file = SIGNALS_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(payload, cls=NumpyEncoder), encoding="utf-8")
    tmp_file.replace(SIGNALS_FILE)

def write_signal(*args, **kwargs):
    write_signal_vektor(*args, **kwargs)

def read_daily_tracker() -> dict:
    if DAILY_FILE.exists():
        try:
            return json.loads(DAILY_FILE.read_text())
        except Exception:
            pass
    return {"date": "", "loss_pips": 0.0, "consecutive_losses": 0, "circuit_breaker_until": ""}

def write_daily_tracker(data: dict) -> None:
    DAILY_FILE.write_text(json.dumps(data, cls=NumpyEncoder))

def read_positions() -> dict:
    if not POSITIONS_FILE.exists():
        return {"balance": 1000.0, "equity": 1000.0, "positions": []}
    try:
        data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
        return {
            "balance": float(data.get("balance", 1000.0)),
            "equity": float(data.get("equity", 1000.0)),
            "positions": data.get("positions", []),
        }
    except (json.JSONDecodeError, OSError):
        return {"balance": 1000.0, "equity": 1000.0, "positions": []}

def write_order_request(action: str, symbol: str, sl: float = 0.0, tp: float = 0.0) -> None:
    payload = {
        "action": action,
        "symbol": symbol,
        "side": "",
        "lot": 0.0,
        "sl": float(round(sl, 5)) if sl > 0 else 0.0,
        "tp": float(round(tp, 5)) if tp > 0 else 0.0
    }
    tmp_file = ORDERS_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(payload), encoding="utf-8")
    tmp_file.replace(ORDERS_FILE)
