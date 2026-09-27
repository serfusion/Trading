"""
AI GOLD TRADER PRO — MT5 Data Connector (Phase 1)

Handles connecting to Exness MT5 terminal and pulling candle data.

REQUIREMENTS:
    - Windows machine (MT5 Python API is Windows-only)
    - MetaTrader 5 terminal installed and an Exness demo account added
    - pip install MetaTrader5 pandas

USAGE:
    python mt5_connector.py
    (runs a quick self-test: connects, prints account info, fetches sample candles)
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import config

# Map our string timeframe names to MT5 constants
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Connector:
    def __init__(self):
        self.connected = False

    def connect(self):
        """Initialize connection to the MT5 terminal and log in to the account."""
        init_kwargs = {}
        if config.MT5_PATH:
            init_kwargs["path"] = config.MT5_PATH

        if not mt5.initialize(**init_kwargs):
            raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")

        if config.MT5_LOGIN:
            authorized = mt5.login(
                config.MT5_LOGIN,
                password=config.MT5_PASSWORD,
                server=config.MT5_SERVER,
            )
            if not authorized:
                mt5.shutdown()
                raise ConnectionError(f"MT5 login() failed: {mt5.last_error()}")

        self.connected = True
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def account_info(self):
        """Return a dict summary of the connected account (balance, equity, etc)."""
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"Failed to get account info: {mt5.last_error()}")
        return info._asdict()

    def check_symbol(self, symbol: str = None):
        """Verify the symbol exists and is visible in Market Watch; enable it if not."""
        symbol = symbol or config.SYMBOL
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(
                f"Symbol '{symbol}' not found. Check the exact symbol name in "
                f"your broker's Market Watch (e.g. XAUUSD, XAUUSDm, GOLD)."
            )
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not enable symbol '{symbol}' in Market Watch.")
        return True

    def get_candles(self, timeframe: str, count: int = None, symbol: str = None) -> pd.DataFrame:
        """
        Fetch the most recent `count` candles for the given timeframe.
        Returns a DataFrame: time, open, high, low, close, tick_volume, spread, real_volume
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")

        symbol = symbol or config.SYMBOL
        self.check_symbol(symbol)

        if timeframe not in TIMEFRAME_MAP:
            raise ValueError(f"Unknown timeframe '{timeframe}'. Valid: {list(TIMEFRAME_MAP)}")

        count = count or config.CANDLE_HISTORY.get(timeframe, 500)
        mt5_tf = TIMEFRAME_MAP[timeframe]

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        if rates is None or len(rates) == 0:
            raise RuntimeError(
                f"No candle data returned for {symbol} {timeframe}: {mt5.last_error()}"
            )

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"tick_volume": "volume"})
        df = df[["time", "open", "high", "low", "close", "volume", "spread"]]
        df = df.reset_index(drop=True)
        return df

    def get_all_timeframes(self, symbol: str = None) -> dict:
        """Fetch candles for every timeframe listed in config.TIMEFRAMES. Returns {tf: DataFrame}."""
        symbol = symbol or config.SYMBOL
        result = {}
        for tf in config.TIMEFRAMES:
            result[tf] = self.get_candles(tf, symbol=symbol)
        return result

    def get_current_price(self, symbol: str = None) -> dict:
        """Return current bid/ask for the symbol."""
        symbol = symbol or config.SYMBOL
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Failed to get tick for {symbol}: {mt5.last_error()}")
        return {"bid": tick.bid, "ask": tick.ask, "time": datetime.fromtimestamp(tick.time)}


if __name__ == "__main__":
    conn = MT5Connector()
    print("Connecting to MT5...")
    conn.connect()
    print("Connected ✅\n")

    print("Account info:")
    info = conn.account_info()
    for k in ("login", "server", "balance", "equity", "currency", "trade_mode"):
        print(f"  {k}: {info.get(k)}")

    print(f"\nCurrent {config.SYMBOL} price:")
    print(" ", conn.get_current_price())

    print(f"\nFetching last 5 D1 candles for {config.SYMBOL}:")
    df = conn.get_candles("D1", count=5)
    print(df)

    conn.disconnect()
    print("\nDisconnected.")
