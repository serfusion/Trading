"""Data H1 pair tambahan: ejtrader (2012-11..2022-03) + Twelve Data (2022-03..sekarang) + ETH Binance. 

python -m research.pair_data      # unduh/lanjutkan, cache data/research/eksternal/pair_h1/<PAIR>.parquet
Twelve Data paket gratis: 8 kredit/menit, 5.000 candle per permintaan -> jeda 8 detik antar permintaan.
"""
from __future__ import annotations

import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile

import pandas as pd

from .eksternal import cache_path
from .multi_asset import INSTRUMENTS, load

FOREX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "EURGBP", "EURCHF"]


def _dir():
    d = cache_path("pair_h1")
    d.mkdir(parents=True, exist_ok=True)
    return d


def twelvedata(sym: str, start: str, end: str) -> pd.DataFrame:
    """Per jendela 180 hari (start_date + end_date) agar tidak terpotong batas 5.000 candle."""
    key = os.environ["TWELVEDATA_API_KEY"]
    td = f"{sym[:3]}/{sym[3:]}"
    out, cur = [], pd.Timestamp(start, tz="UTC")
    stop = pd.Timestamp(end, tz="UTC")
    while cur < stop:
        nxt = min(cur + pd.Timedelta(days=180), stop)
        q = urllib.parse.urlencode({"symbol": td, "interval": "1h", "start_date": f"{cur:%Y-%m-%d %H:%M:%S}",
                                    "end_date": f"{nxt:%Y-%m-%d %H:%M:%S}", "outputsize": 5000, "timezone": "UTC",
                                    "order": "ASC", "apikey": key})
        d = {}
        for k in range(6):
            try:
                with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as r:
                    d = json.loads(r.read())
            except Exception:  # noqa: BLE001
                time.sleep(10 * (k + 1))
                continue
            if "credits" in str(d.get("message", "")).lower():
                time.sleep(61)
                continue
            break
        time.sleep(8)
        if d.get("status") == "ok" and d.get("values"):
            df = pd.DataFrame(d["values"])
            df.index = pd.to_datetime(df.datetime, utc=True)
            out.append(df[["open", "high", "low", "close"]].astype(float))
        cur = nxt
    return pd.concat(out).sort_index() if out else pd.DataFrame()


def forex(sym: str) -> pd.DataFrame:
    f = _dir() / f"{sym}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    old = load(sym)[["open", "high", "low", "close"]]
    new = twelvedata(sym, str(old.index[-1].date() - pd.Timedelta(days=3)), "2026-10-03")
    # cek kecocokan harga di masa tumpang tindih
    ov = old.index.intersection(new.index)
    gap = float((old.loc[ov, "close"] - new.loc[ov, "close"]).abs().median() / old.close.iloc[-1]) if len(ov) else None
    df = pd.concat([old, new[new.index > old.index[-1]]]).sort_index()
    df = df[~df.index.duplicated()]
    df.attrs["overlap_gap"] = gap
    df.to_parquet(f)
    print(f"{sym}: {len(old)} + {len(new)} candle, tumpang tindih {len(ov)}, beda median {gap}")
    return df


def eth() -> pd.DataFrame:
    f = _dir() / "ETHUSD.parquet"
    if f.exists():
        return pd.read_parquet(f)
    parts = []
    for p in pd.period_range("2017-09", "2026-09", freq="M"):
        url = f"https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-{p.strftime('%Y-%m')}.zip"
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
        except Exception:  # noqa: BLE001
            continue
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4])
        raw.columns = ["t", "open", "high", "low", "close"]
        unit = "us" if raw.t.iloc[0] > 1e14 else "ms"
        raw.index = pd.to_datetime(raw.t, unit=unit, utc=True)
        parts.append(raw[["open", "high", "low", "close"]].astype(float))
    df = pd.concat(parts).sort_index()
    df.to_parquet(f)
    print(f"ETHUSD: {len(df)} candle {df.index[0]} .. {df.index[-1]}")
    return df


def spread(sym: str):
    return "0.05%" if sym == "ETHUSD" else INSTRUMENTS[sym][1]


def main() -> None:
    eth()
    for s in FOREX:
        forex(s)


if __name__ == "__main__":
    main()
