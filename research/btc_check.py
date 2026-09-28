"""Bitcoin: sistem yang sama per periode, 2012 s/d Sep 2026 (python -m research.btc_check).

Bitstamp BTC/USD. Spread 0,03% & 0,06% harga (uji ketahanan biaya). Swap/biaya inap kripto belum dihitung.
"""
import numpy as np
import pandas as pd

from .filters import SETS, features
from .gap_study import week_info
from .multi_asset import summary, yearly
from .risk_compare import F, equity, trades
from .run_scan import DATA

PERIODS = [("2012-2017", "2012-01-01", "2018-01-01"), ("2018-2022", "2018-01-01", "2023-01-01"),
           ("2023-2026", "2023-01-01", "2027-01-01")]


def main():
    full = pd.read_parquet(DATA / "h1" / "BTC_USD_full.parquet")
    full = full[full["high"] > full["low"]]
    for cost in (0.0003, 0.0006):
        print(f"=== spread {cost * 100:.2f}% harga ===")
        for name, a, b in PERIODS:
            # data sejak 60 hari sebelum periode supaya indikator siap, trade dihitung mulai tanggal a
            h1 = full[(full.index >= pd.Timestamp(a, tz="UTC") - pd.Timedelta(days=90)) &
                      (full.index < pd.Timestamp(b, tz="UTC"))]
            f = features(h1)
            since, _ = week_info(h1)
            spread = h1["close"].to_numpy() * cost
            tr = sorted(sum((trades(h1, spread, f, F, ne, nx, allow=lambda i: since[i] >= 3) for ne, nx in SETS),
                            []))
            tr = [x for x in tr if x[0] >= pd.Timestamp(a, tz="UTC")]
            star = [x for x in tr if x[3]]
            norm = [x for x in tr if not x[3]]
            ret, dd, _ = equity(tr, 0.005, 0.0025)
            yr = yearly(tr)
            print(f"{name}: saldo ⭐0,5%/biasa0,25% {ret:+8.1f}% DD {dd:6.1f}% | tahun positif "
                  f"{sum(v > 0 for v in yr.values())}/{len(yr)}")
            print(f"   ⭐    {summary(star)}")
            print(f"   biasa {summary(norm)}")
            print("   per tahun: " + " ".join(f"{y % 100:02d}:{v:+.0f}" for y, v in yr.items()))
            if cost == 0.0003:
                r = np.array([x[2] for x in star])
                print(f"   ⭐ tanpa 5 sinyal terbaik: total {np.sort(r)[:-5].sum():+.1f}R")


if __name__ == "__main__":
    main()
