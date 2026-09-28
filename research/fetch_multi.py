"""Unduh M1 OANDA / Bitstamp (FutureSharks/financial-data) per instrumen -> H1 parquet, lalu hapus M1.

python -m research.fetch_multi NAS100_USD SPX500_USD ... BTC_USD
Hasil: data/research/h1/<SIMBOL>.parquet (index UTC). Data OANDA memakai jam UTC.
"""
import subprocess
import sys

import pandas as pd

from .run_scan import DATA

REPO = DATA / "FutureSharks_financial-data"
OUT = DATA / "h1"


def sparse(paths):
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone", *paths], cwd=REPO, check=True)
    subprocess.run(["git", "checkout", "-q", "HEAD"], cwd=REPO, check=True)


def to_h1(frames):
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample("60min", label="left", closed="left").agg(agg).dropna()


def fetch(sym):
    OUT.mkdir(exist_ok=True)
    if sym == "BTC_USD":
        base = "pyfinancialdata/data/cryptocurrencies/bitstamp/BTC_USD/"
        sparse([base])
        files = sorted((REPO / base).glob("*.csv"))
        frames = [pd.read_csv(f, parse_dates=["date"], index_col="date") for f in files]
    else:
        base = f"pyfinancialdata/data/currencies/oanda/{sym}/"
        sparse([base])
        files = sorted((REPO / base).rglob("*.csv"))
        frames = [pd.read_csv(f, parse_dates=["time"], index_col="time") for f in files]
    frames = [f[["open", "high", "low", "close"]].astype(float) for f in frames if len(f)]
    h1 = to_h1(frames)
    h1.index = h1.index.tz_localize("UTC")
    h1.to_parquet(OUT / f"{sym}.parquet")
    sparse(["README.md"])                     # hapus M1 dari disk
    print(f"{sym}: {h1.index[0]:%Y-%m-%d} .. {h1.index[-1]:%Y-%m-%d}, {len(h1)} candle H1")




def fetch_btc_full():
    """Bitstamp BTC/USD M1 2012 s/d terbaru (ff137/bitstamp-btcusd-minute-data) -> h1/BTC_USD_full.parquet."""
    root = DATA / "ff137_bitstamp-btcusd-minute-data" / "data"
    parts = [pd.read_csv(root / "historical" / "btcusd_bitstamp_1min_2012-2025.csv.gz"),
             pd.read_csv(root / "updates" / "btcusd_bitstamp_1min_latest.csv")]
    df = pd.concat(parts)
    df.index = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df[df["volume"] > 0]                                  # menit tanpa transaksi = harga salinan
    h1 = to_h1([df[["open", "high", "low", "close"]].astype(float)])
    OUT.mkdir(exist_ok=True)
    h1.to_parquet(OUT / "BTC_USD_full.parquet")
    print(f"BTC_USD_full: {h1.index[0]:%Y-%m-%d} .. {h1.index[-1]:%Y-%m-%d}, {len(h1)} candle H1")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        fetch_btc_full() if s == "BTC_USD_full" else fetch(s)
