"""Volatility Engine — rule-based spike detection, no training needed."""

import numpy as np
import pandas as pd


class VolatilityEngine:
    def compute_spike_score(
        self, df: pd.DataFrame, features_row: dict
    ) -> dict:
        if df.empty or len(df) < 20:
            return {"score": 0, "is_spike": False, "reason": "insufficient_data"}

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        vol = df["volume"].astype(float)
        last = df.iloc[-1]

        atr = features_row.get("M15_atr_5", 10.0)
        if atr <= 0:
            atr = 10.0

        range_val = last["high"] - last["low"]
        range_ratio = range_val / max(atr, 0.1)
        range_pts = min(30, max(0, range_ratio * 20))

        vol_ma = vol.rolling(20).mean()
        vol_std = vol.rolling(20).std()
        current_vol = vol.iloc[-1]
        mean_vol = vol_ma.iloc[-1]
        std_vol = vol_std.iloc[-1]
        if mean_vol > 0 and std_vol > 0.5:
            vol_z = (current_vol - mean_vol) / max(std_vol, 0.5)
            vol_pts = min(30, max(0, vol_z * 5))
        elif current_vol > 1:
            vol_ratio = current_vol / max(mean_vol, 1)
            vol_pts = min(30, max(0, (vol_ratio - 1) * 15))
        else:
            vol_pts = 0

        mom_1 = abs(close.pct_change().fillna(0).iloc[-1]) * 100
        mom_3 = abs(close.pct_change(3).fillna(0).iloc[-1]) * 100
        mom_accel = abs(close.diff(2).fillna(0).iloc[-1]) / max(close.iloc[-1], 1) * 100
        mom_pts = min(30, max(0, mom_1 * 30 + mom_3 * 10 + mom_accel * 100))

        high_20 = high.rolling(20).max()
        low_20 = low.rolling(20).min()
        prev_high_20 = high_20.iloc[-2] if len(high_20) > 1 else high_20.iloc[-1]
        prev_low_20 = low_20.iloc[-2] if len(low_20) > 1 else low_20.iloc[-1]
        cur_close = last["close"]
        if cur_close > prev_high_20:
            breakout_pts = 10
            breakout_side = "BUY"
        elif cur_close < prev_low_20:
            breakout_pts = 10
            breakout_side = "SELL"
        else:
            breakout_pts = 0
            breakout_side = None

        total = range_pts + vol_pts + mom_pts + breakout_pts
        is_spike = total >= 60

        return {
            "score": round(min(100, total), 1),
            "is_spike": is_spike,
            "is_extreme": total >= 85,
            "components": {
                "range_pts": round(range_pts, 1),
                "vol_pts": round(vol_pts, 1),
                "mom_pts": round(mom_pts, 1),
                "breakout_pts": breakout_pts,
            },
            "breakout_side": breakout_side,
        }
