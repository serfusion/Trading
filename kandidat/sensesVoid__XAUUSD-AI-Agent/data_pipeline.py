import pandas as pd
import numpy as np

class MarketFeatureBuilder:
    """Turns raw OHLC into the compact feature snapshot the LLM will actually read.
    Do NOT hand the model raw candle dumps — summarize first, or it burns context
    and reasons worse. This matches the lesson from your swing-point research:
    pre-formation candle features alone carry little signal (AUC ~0.535), so the
    LLM's job here is regime/context synthesis, not pattern mining from raw OHLC."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def build_snapshot(self) -> dict:
        df = self.df
        close = df["close"]
        atr = self._atr(df, 14)
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()

        return {
            "last_close": float(close.iloc[-1]),
            "atr_14": round(float(atr.iloc[-1]), 3),
            "ema20": round(float(ema20.iloc[-1]), 3),
            "ema50": round(float(ema50.iloc[-1]), 3),
            "trend_bias": "bullish" if ema20.iloc[-1] > ema50.iloc[-1] else "bearish",
            "range_pct_of_atr": round(
                float((df["high"].iloc[-1] - df["low"].iloc[-1]) / atr.iloc[-1]), 2
            ),
            "last_5_closes": [round(float(c), 2) for c in close.tail(5)],
            "distance_from_ema20_atr": round(
                float((close.iloc[-1] - ema20.iloc[-1]) / atr.iloc[-1]), 2
            ),
        }

    @staticmethod
    def _atr(df: pd.DataFrame, period: int) -> pd.Series:
        high, low, prev_close = df["high"], df["low"], df["close"].shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        return tr.rolling(period).mean()