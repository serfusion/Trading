"""Primitif Smart Money Concepts tanpa look-ahead.

Setiap swing punya `confirmed_idx`: bar pertama di mana swing tersebut
sudah pasti (butuh `length` bar di kanan). Strategi hanya boleh memakai
swing yang `confirmed_idx <= t`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from .models import Level, Swing


def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    prev_c = np.concatenate(([c[0]], c[:-1])) if len(c) else c
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    return pd.Series(tr).rolling(period, min_periods=1).mean().to_numpy()


def swing_mask(values: np.ndarray, length: int, side: str) -> np.ndarray:
    """Mask swing: lebih ekstrem dari `length` bar kiri (strict) dan kanan (>=)."""
    n = len(values)
    mask = np.zeros(n, dtype=bool)
    if length < 1 or n < 2 * length + 1:
        return mask
    windows = sliding_window_view(values, length)
    idx = np.arange(length, n - length)
    if side == "high":
        agg = windows.max(axis=1)
        mask[idx] = (values[idx] > agg[idx - length]) & (values[idx] >= agg[idx + 1])
    else:
        agg = windows.min(axis=1)
        mask[idx] = (values[idx] < agg[idx - length]) & (values[idx] <= agg[idx + 1])
    return mask


def find_swings(df: pd.DataFrame, length: int, side: str) -> list[Swing]:
    col = "high" if side == "high" else "low"
    values = df[col].to_numpy(float)
    sel = np.nonzero(swing_mask(values, length, side))[0]
    return [Swing(int(i), int(i) + length, ts, float(values[i]), side)
            for i, ts in zip(sel, df.index[sel])]


def swing_levels(df: pd.DataFrame, length: int, side: str, tolerance: float) -> list[Level]:
    """Level likuiditas dari swing, termasuk equal highs/lows (strength > 1)."""
    swings = find_swings(df, length, side)
    col = df["high" if side == "high" else "low"].to_numpy(float)
    levels: list[Level] = []
    for j, sj in enumerate(swings):
        strength = 1
        price = sj.price
        for si in swings[:j]:
            if abs(si.price - sj.price) > tolerance:
                continue
            between = col[si.idx + 1:sj.idx]
            if side == "high":
                intact = between.size == 0 or between.max() <= max(si.price, sj.price)
            else:
                intact = between.size == 0 or between.min() >= min(si.price, sj.price)
            if intact:
                strength += 1
                price = max(price, si.price) if side == "high" else min(price, si.price)
        levels.append(Level(price=price, side=side, kind="equal" if strength > 1 else "swing",
                            time=sj.time, known_idx=sj.confirmed_idx, strength=strength))
    return levels


def first_break(values: np.ndarray, start: int, end: int, price: float, side: str) -> int | None:
    """Index pertama di [start, end] yang menembus level (high > price / low < price)."""
    if start > end:
        return None
    seg = values[start:end + 1]
    hits = np.nonzero(seg > price if side == "high" else seg < price)[0]
    return start + int(hits[0]) if hits.size else None


def structure_bias(df: pd.DataFrame, length: int) -> int:
    """+1 bila BOS terakhir ke atas, -1 bila ke bawah, 0 belum jelas."""
    if len(df) < 2 * length + 2:
        return 0
    highs = swing_mask(df["high"].to_numpy(float), length, "high")
    lows = swing_mask(df["low"].to_numpy(float), length, "low")
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    state = 0
    last_high = last_low = None
    for i in range(len(df)):
        k = i - length  # swing di k baru terkonfirmasi pada bar i
        if k >= 0:
            if highs[k]:
                last_high = h[k]
            if lows[k]:
                last_low = l[k]
        if last_high is not None and c[i] > last_high:
            state, last_high = 1, None
        elif last_low is not None and c[i] < last_low:
            state, last_low = -1, None
    return state


def mirror(df: pd.DataFrame) -> pd.DataFrame:
    """Balik harga (x -> -x) sehingga logika SELL bisa dipakai untuk BUY."""
    return pd.DataFrame({
        "open": -df["open"], "high": -df["low"], "low": -df["high"], "close": -df["close"],
    }, index=df.index)
