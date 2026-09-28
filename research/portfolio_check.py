"""Gabungan instrumen dalam satu akun, 2018 s/d Mar 2022 (python -m research.portfolio_check).

Sistem sama (F-ensemble + ⭐ + lewati 3 candle setelah gap). XAU & JPY: ejtraderLabs H1; BTC: Bitstamp.
"""
import pandas as pd

from .filters import SETS, features
from .gap_study import week_info
from .multi_asset import INSTRUMENTS, load, yearly
from .risk_compare import F, equity, trades
from .run_scan import DATA

START, END = pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2022-03-05", tz="UTC")


def signals(h1, spread):
    h1 = h1[(h1.index >= START - pd.Timedelta(days=90)) & (h1.index < END)]
    h1 = h1[h1["high"] > h1["low"]]
    f = features(h1)
    since, _ = week_info(h1)
    # spread tetap (harga) atau persen harga, mis. "0.03%" untuk BTC
    sp = h1["close"].to_numpy() * float(spread.rstrip("%")) / 100 if isinstance(spread, str) else spread
    tr = sorted(sum((trades(h1, sp, f, F, ne, nx, allow=lambda i: since[i] >= 3) for ne, nx in SETS), []))
    return [x for x in tr if x[0] >= START]


def main():
    res = {s: signals(load(s), INSTRUMENTS[s][1]) for s in ["XAUUSD", "EURJPY", "AUDJPY", "GBPJPY", "USDJPY"]}
    res["BTC"] = signals(pd.read_parquet(DATA / "h1" / "BTC_USD_full.parquet"), "0.03%")
    combos = [["XAUUSD"], ["BTC"], ["XAUUSD", "BTC"], ["XAUUSD", "AUDJPY", "EURJPY"],
              ["XAUUSD", "BTC", "AUDJPY", "EURJPY"], ["XAUUSD", "BTC", "AUDJPY", "EURJPY", "GBPJPY", "USDJPY"]]
    for combo in combos:
        tr = sorted(sum((res[k] for k in combo), []))
        for r in (0.005, 0.0025):
            ret, dd, _ = equity(tr, r, r / 2)
            yr = yearly(tr)
            print(f"{'+'.join(combo):40s} ⭐{r * 100:.2f}%: {ret:+7.1f}% DD {dd:6.1f}% | tahun + "
                  f"{sum(v > 0 for v in yr.values())}/{len(yr)} | " + " ".join(f"{y % 100}:{v:+.0f}" for y, v in yr.items()))


if __name__ == "__main__":
    main()
