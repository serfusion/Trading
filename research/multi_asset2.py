"""Sistem yang sama di indeks saham, minyak, forex OANDA & Bitcoin (python -m research.multi_asset2).

Data H1 dari M1 OANDA 2005-2020 & Bitstamp BTC 2012-2018 (research/fetch_multi.py). Spread perkiraan akun
Standard; BTC 0,03% harga. Swap/biaya inap belum dihitung (penting untuk indeks & BTC yang ditahan berhari-hari).
"""
import numpy as np
import pandas as pd

from .filters import SETS, features
from .gap_study import week_info
from .multi_asset import summary, yearly
from .risk_compare import F, equity, trades
from .run_scan import DATA

SPREAD = {
    "NAS100_USD": 1.8, "SPX500_USD": 0.5, "US2000_USD": 0.3, "JP225_USD": 10.0, "UK100_GBP": 1.5,
    "FR40_EUR": 1.5, "AU200_AUD": 2.5, "WTICO_USD": 0.03, "XAU_USD": 0.30, "EUR_USD": 0.00010,
    "GBP_USD": 0.00012, "EUR_JPY": 0.018, "AUD_JPY": 0.018, "BTC_USD": "0.03%",
}


def run(sym, start="2008-01-01"):
    h1 = pd.read_parquet(DATA / "h1" / f"{sym}.parquet")
    h1 = h1[h1.index >= pd.Timestamp(start, tz="UTC")]
    h1 = h1[(h1["high"] > h1["low"])]                                  # buang candle tanpa transaksi
    f = features(h1)
    since, _ = week_info(h1)
    sp = SPREAD[sym]
    spread = h1["close"].to_numpy() * 0.0003 if isinstance(sp, str) else sp
    out = []
    for ne, nx in SETS:
        out += trades(h1, spread, f, F, ne, nx, allow=lambda i: since[i] >= 3)
    return sorted(out), h1


def main():
    rows = []
    for sym in SPREAD:
        path = DATA / "h1" / f"{sym}.parquet"
        if not path.exists():
            print(f"{sym}: data belum ada")
            continue
        tr, h1 = run(sym)
        star = [x for x in tr if x[3]]
        norm = [x for x in tr if not x[3]]
        yr = yearly(tr)
        pos = sum(1 for v in yr.values() if v > 0)
        ret, dd, _ = equity(tr, 0.005, 0.0025)
        rs = np.array([x[2] for x in star]) if star else np.zeros(1)
        rows.append((sym, ret, dd, pos, len(yr), rs.mean()))
        print(f"{sym} {h1.index[0]:%Y}-{h1.index[-1]:%Y}  saldo ⭐0,5%/biasa0,25%: {ret:+7.1f}% DD {dd:6.1f}% | "
              f"tahun positif {pos}/{len(yr)}")
        print(f"   ⭐    {summary(star)}")
        print(f"   biasa {summary(norm)}")
        print("   per tahun: " + " ".join(f"{y % 100:02d}:{v:+.0f}" for y, v in yr.items()))
    print("\nRINGKAS (urut rata-rata R per sinyal ⭐)")
    for sym, ret, dd, pos, n, avg in sorted(rows, key=lambda x: -x[5]):
        print(f"   {sym:11s} ⭐ {avg:+.3f}R/sinyal | saldo {ret:+7.1f}% DD {dd:6.1f}% | tahun positif {pos}/{n}")


if __name__ == "__main__":
    main()
