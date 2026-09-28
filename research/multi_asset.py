"""Sistem yang sama (F-ensemble + ⭐ + lewati 3 candle setelah gap) di banyak instrumen.

python -m research.multi_asset
Data H1 2012-11 s/d 2022-03 (ejtraderLabs/historical-data, jam server NY+7). Spread = rata-rata akun
Standard (perkiraan), swap belum dihitung. Hasil R: 1R = rugi penuh satu sinyal (5 posisi kena SL).
"""
from collections import defaultdict

import numpy as np
import pandas as pd

from .data import _clean, server_ny7_to_utc
from .filters import SETS, features
from .gap_study import week_info
from .risk_compare import F, equity, trades
from .run_scan import DATA

ROOT = DATA / "ejtraderLabs_historical-data"
# simbol: (pembagi harga di file, spread dalam harga)
INSTRUMENTS = {
    "XAUUSD": (100, 0.30), "EURUSD": (1e5, 0.00010), "GBPUSD": (1e5, 0.00012), "AUDUSD": (1e5, 0.00010),
    "USDCAD": (1e5, 0.00015), "USDCHF": (1e5, 0.00015), "EURGBP": (1e5, 0.00015), "EURCHF": (1e5, 0.00020),
    "USDJPY": (1e3, 0.012), "EURJPY": (1e3, 0.018), "GBPJPY": (1e3, 0.025), "AUDJPY": (1e3, 0.018),
}


def load(sym):
    div, _ = INSTRUMENTS[sym]
    df = pd.read_csv(ROOT / sym / f"{sym}h1.csv", parse_dates=["Date"], index_col="Date")
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]] / div
    df.index = server_ny7_to_utc(df.index)
    return _clean(df)


def run(sym):
    h1 = load(sym)
    f = features(h1)
    since, _ = week_info(h1)
    out = []
    for ne, nx in SETS:
        out += trades(h1, INSTRUMENTS[sym][1], f, F, ne, nx, allow=lambda i: since[i] >= 3)
    return sorted(out)


def summary(tr):
    r = np.array([x[2] for x in tr])
    if len(r) == 0:
        return "n=0"
    pf = r[r > 0].sum() / max(-r[r < 0].sum(), 1e-9)
    return f"n={len(r):4d} win={np.mean(r > 0) * 100:4.1f}% rata={r.mean():+.3f}R total={r.sum():+6.1f}R PF={pf:.2f}"


def yearly(tr, w_star=1.0, w_norm=0.5):
    by = defaultdict(float)
    for _, tx, r, star in tr:
        by[tx.year] += r * (w_star if star else w_norm)
    return dict(sorted(by.items()))


def main():
    results = {}
    for sym in INSTRUMENTS:
        tr = run(sym)
        results[sym] = tr
        star = [x for x in tr if x[3]]
        norm = [x for x in tr if not x[3]]
        yr = yearly(tr)
        pos = sum(1 for v in yr.values() if v > 0)
        ret, dd, _ = equity(tr, 0.005, 0.0025)
        print(f"{sym}  saldo ⭐0,5%/biasa0,25%: {ret:+6.1f}% DD {dd:5.1f}% | tahun positif {pos}/{len(yr)}")
        print(f"   ⭐    {summary(star)}")
        print(f"   biasa {summary(norm)}")
        print("   per tahun (R, ⭐ penuh + biasa ½): " + " ".join(f"{y % 100:02d}:{v:+.1f}" for y, v in yr.items()))
    print("\nPORTOFOLIO (semua sinyal dari beberapa instrumen, saldo bersama, ⭐0,5%/biasa0,25% per sinyal)")
    groups = {
        "XAU saja": ["XAUUSD"],
        "XAU + JPY (USDJPY, GBPJPY, EURJPY, AUDJPY)": ["XAUUSD", "USDJPY", "GBPJPY", "EURJPY", "AUDJPY"],
        "Semua 12 instrumen": list(INSTRUMENTS),
    }
    for name, syms in groups.items():
        tr = sorted(sum((results[s] for s in syms), []))
        ret, dd, streak = equity(tr, 0.005, 0.0025)
        yr = yearly(tr)
        print(f"   {name:45s} {ret:+7.1f}% DD {dd:6.1f}% | tahun positif {sum(v > 0 for v in yr.values())}/{len(yr)}")


if __name__ == "__main__":
    main()
