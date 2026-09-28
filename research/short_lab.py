"""31 metode di timeframe pendek M5/M15 (python -m research.short_lab).

XAU M15 2012-2026 & M5 2020-2026, BTC M5 2016-2026, EURUSD/GBPUSD/USDJPY/EURJPY M15 2012-2022.
Aturan & seleksi sama dengan world_lab (latih -> uji). Rating: ★ untung di latih & uji (uji t>1),
★★ t>2 di latih & uji, ★★★ plus >=70% tahun untung di kedua periode.
"""
from multiprocessing import Pool

import numpy as np
import pandas as pd

from .data import resample
from .gap_trade import m15_ej, xau
from .multi_asset import INSTRUMENTS
from .run_scan import DATA, dataset
from .world_lab import METHODS, Ctx, backtest, summarize


def btc_m5():
    root = DATA / "ff137_bitstamp-btcusd-minute-data" / "data"
    df = pd.concat([pd.read_csv(root / "historical" / "btcusd_bitstamp_1min_2012-2025.csv.gz"),
                    pd.read_csv(root / "updates" / "btcusd_bitstamp_1min_latest.csv")])
    df.index = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df[(df["volume"] > 0) & (df.index >= "2016-01-01")]
    return resample(df[["open", "high", "low", "close"]].astype(float), "5min")


def load(name):
    if name == "XAU M15":
        return xau(), 0.30, "2018-01-01"
    if name == "XAU M5":
        a = dataset("m5_2020")[0]
        b = dataset("m5_2025")[0]
        return pd.concat([a, b[b.index > a.index[-1]]]), 0.25, "2023-07-01"
    if name == "BTC M5":
        return btc_m5(), "0.03%", "2021-01-01"
    sym = name.split()[0]
    return m15_ej(sym), INSTRUMENTS[sym][1], "2018-01-01"


def stars(sd, st):
    if sd["avg"] > 0 and st["avg"] > 0 and sd["t"] > 2 and st["t"] > 2:
        return 3 if sd["yrs"] >= 70 and st["yrs"] >= 70 else 2
    return 1 if sd["avg"] > 0 and st["avg"] > 0 and st["t"] > 1 else 0


def run(name):
    df, spread, split = load(name)
    df = df[df["high"] > df["low"]]
    x = Ctx(df, spread)
    split = pd.Timestamp(split, tz="UTC")
    rows = []
    for meth, (fn, grid) in METHODS.items():
        best = None
        for p in grid:
            try:
                sig = fn(x, **p)
            except Exception:  # noqa: BLE001
                continue
            li, si, lo, so, sl = sig[:5]
            mh = sig[6] if len(sig) > 6 else None
            for tp in (None, 1.0, 2.0):
                tr = backtest(x.b, *(np.asarray(v, bool) for v in (li, si, lo, so)), sl, tp, mh)
                sd = summarize([t for t in tr if t[0] < split])
                if sd["n"] >= 50 and (best is None or sd["t"] > best[1]["t"]):
                    best = ({**p, "tp": tp}, sd, summarize([t for t in tr if t[0] >= split]))
        if best:
            rows.append(dict(data=name, method=meth, params=str(best[0]), bintang=stars(best[1], best[2]),
                             **{f"latih_{k}": v for k, v in best[1].items()},
                             **{f"uji_{k}": v for k, v in best[2].items()}))
    print(f"selesai {name}", flush=True)
    return rows


def main():
    names = ["XAU M15", "XAU M5", "BTC M5", "EURUSD M15", "GBPUSD M15", "USDJPY M15", "EURJPY M15"]
    with Pool(4) as p:
        rows = [r for rs in p.map(run, names) for r in rs]
    df = pd.DataFrame(rows)
    df.to_pickle(DATA / "short_lab.pkl")
    print(f"\n{len(df)} pasangan diuji. Uji t>2: {(df.uji_t > 2).sum()}, latih&uji t>2: "
          f"{((df.latih_t > 2) & (df.uji_t > 2)).sum()}")
    print(df.groupby("data").agg(untung_uji=("uji_avg", lambda v: (v > 0).sum()), metode=("method", "count"),
                                 rata_R=("uji_avg", "mean")).round(3).to_string())
    top = df[df.bintang > 0].sort_values(["bintang", "uji_t"], ascending=False)
    cols = ["data", "method", "params", "bintang", "latih_n", "latih_win", "latih_avg", "latih_t", "uji_n",
            "uji_win", "uji_avg", "uji_t", "uji_yrs"]
    print("\nBERBINTANG:")
    print(top[cols].round(3).to_string() if len(top) else "tidak ada")


if __name__ == "__main__":
    main()
