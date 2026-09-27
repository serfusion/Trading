import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class MT5Bridge:
    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        self.connected = False

    def connect(self) -> bool:
        initialized = mt5.initialize(
            path=os.getenv("MT5_PATH"),
            login=int(os.getenv("MT5_LOGIN")),
            password=os.getenv("MT5_PASSWORD"),
            server=os.getenv("MT5_SERVER"),
            timeout=10000,
    )
        if not initialized:
            raise RuntimeError(f"MT5 initialize/login failed: {mt5.last_error()}")

        if not mt5.symbol_select(self.symbol, True):
            raise RuntimeError(f"Could not select symbol {self.symbol}: {mt5.last_error()}")

        self.connected = True
        return True

    def get_ohlc(self, timeframe=mt5.TIMEFRAME_M15, bars: int = 200) -> pd.DataFrame:
        if not self.connected:
            self.connect()
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No rates returned for {self.symbol}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_tick(self) -> dict:
        if not self.connected:
            self.connect()
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {self.symbol}: {mt5.last_error()}")
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread_points": (tick.ask - tick.bid) / mt5.symbol_info(self.symbol).point,
            "time": datetime.fromtimestamp(tick.time),
        }

    def shutdown(self):
        mt5.shutdown()
        self.connected = False
