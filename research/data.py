"""Loader dataset XAUUSD historis -> DataFrame OHLC dengan index UTC.

Sumber (publik, GitHub):
- ejtraderLabs/historical-data  XAUUSD M15 2012-2022 (harga x100, jam server = New York + 7 jam)
- dineshelumalai007/xauusd-5m   XAUUSD M5 2025-2026 (ekspor MT5, jam server = New York + 7 jam)
- Sai310421/xauusd-data         XAUUSD M1 & XAGUSD M5 Feb-Mei 2026 (UTC)
- ilahuerta-IA/backtrader-pullback-window-xauusd  XAUUSD M5 Agu 2020 - Agu 2025 (UTC; buka mingguan
  Minggu 22:00/23:00 UTC, selisih median 0,22 dengan data dineshelumalai007 di periode yang sama)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

NY = "America/New_York"


def server_ny7_to_utc(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Jam server MT5 'NY+7' (buka mingguan Senin 01:00) -> UTC, mengikuti DST AS."""
    ny = (index - pd.Timedelta(hours=7)).tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    return ny.tz_convert("UTC")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[["open", "high", "low", "close"]].astype(float)
    df = df[df.index.notna()]
    df = df[~df.index.duplicated()].sort_index()
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    return df[~bad]


def load_m15_2012(root: Path) -> pd.DataFrame:
    df = pd.read_csv(root / "XAUUSDm15.csv", parse_dates=["Date"], index_col="Date")
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]] / 100.0
    df.index = server_ny7_to_utc(df.index)
    return _clean(df)


def load_m5_2025(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"], index_col="time")
    df.index = server_ny7_to_utc(df.index)
    return _clean(df)


def load_m5_2020(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"Date": str, "Time": str})
    df.index = pd.DatetimeIndex(pd.to_datetime(df["Date"] + " " + df["Time"])).tz_localize("UTC")
    df.columns = [c.lower() for c in df.columns]
    return _clean(df)


def load_parquet_utc(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return _clean(df)


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample(rule, label="left", closed="left").agg(agg).dropna()
