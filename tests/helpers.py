import numpy as np
import pandas as pd


def bars_from_path(closes, start="2026-09-22 11:00", freq="5min", wick=0.2, start_price=None):
    """Bangun OHLC dari deret close: open = close sebelumnya."""
    closes = list(closes)
    opens = [start_price if start_price is not None else closes[0]] + closes[:-1]
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    df = pd.DataFrame({"open": opens, "close": closes}, index=idx, dtype=float)
    df["high"] = df[["open", "close"]].max(axis=1) + wick
    df["low"] = df[["open", "close"]].min(axis=1) - wick
    return df[["open", "high", "low", "close"]]


def linspace(a, b, n):
    return list(np.linspace(a, b, n + 1)[1:])


def sell_setup_path():
    """Uptrend -> swing high 4340 -> sweep 4341.5 (TS) -> MSS turun + FVG."""
    base = [4300 + i * 0.75 + 3 * np.sin(i / 1.6) for i in range(40)]
    path = base
    path += linspace(path[-1], 4340, 5)
    path += linspace(4340, 4332, 5)
    path += linspace(4332, 4338, 4)
    path += [4336.5, 4335.0, 4339.0]
    df = bars_from_path(path)
    return df


def add_sweep_and_mss(df):
    """Tambahkan bar sweep (ekor ke 4341.5, close 4338.5) lalu displacement turun."""
    t = df.index[-1]
    rows = [
        (4339.0, 4341.5, 4338.3, 4338.5),   # sweep / turtle soup
        (4338.5, 4338.6, 4335.8, 4336.0),
        (4336.0, 4336.2, 4330.8, 4331.0),   # MSS: close < swing internal
        (4331.0, 4331.3, 4327.8, 4328.2),
    ]
    idx = pd.date_range(t + pd.Timedelta(minutes=5), periods=len(rows), freq="5min", tz="UTC")
    extra = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    return pd.concat([df, extra])


def mirror_prices(df, pivot=8670.0):
    """Cerminkan harga (untuk membuat setup BUY dari setup SELL)."""
    return pd.DataFrame({
        "open": pivot - df["open"], "high": pivot - df["low"],
        "low": pivot - df["high"], "close": pivot - df["close"],
    }, index=df.index)
