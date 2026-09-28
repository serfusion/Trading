"""Lawan gap pekan, per tahun, semua instrumen dengan data H1 terpanjang (python -m research.gap_years).

Entry 1 jam setelah pasar buka (sama dengan sinyal live: cron memeriksa setelah candle H1 pertama tutup).
Variasi dikunci sama untuk semua instrumen supaya tidak memilih yang kebetulan bagus.
"""
import numpy as np
import pandas as pd

from .gap_trade import events, sim, xau
from .multi_asset import INSTRUMENTS, load as load_ej
from .run_scan import DATA

JOIN = {"EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "EURJPY": "EUR_JPY", "AUDJPY": "AUD_JPY"}
OANDA_ONLY = {"NAS100_USD": 1.8, "SPX500_USD": 0.5, "US2000_USD": 0.3, "JP225_USD": 10.0, "UK100_GBP": 1.5,
              "FR40_EUR": 1.5, "AU200_AUD": 2.5, "WTICO_USD": 0.03}
VARIANTS = [(m, thr, k) for m in ("fade50", "fade100") for thr in (0.25, 0.5) for k in (1.0, 2.0)]


def data():
    out = {"XAUUSD": (xau(), 0.30)}
    for s in INSTRUMENTS:
        if s == "XAUUSD":
            continue
        h1 = load_ej(s)
        if s in JOIN:
            o = pd.read_parquet(DATA / "h1" / f"{JOIN[s]}.parquet")
            h1 = pd.concat([o, h1[h1.index > o.index[-1]]])
        out[s] = (h1, INSTRUMENTS[s][1])
    for s, sp in OANDA_ONLY.items():
        out[s] = (pd.read_parquet(DATA / "h1" / f"{s}.parquet"), sp)
    return out


def per_year(rows):
    r = pd.DataFrame(rows, columns=["t", "R"])
    r["y"] = r.t.dt.year
    return r.groupby("y").agg(n=("R", "size"), win=("R", lambda v: (v > 0).mean() * 100), total=("R", "sum"))


def main():
    d = data()
    allrows = {}
    print("RINGKAS per variasi (semua tahun):")
    for name, (df, sp) in d.items():
        df = df[df["high"] > df["low"]]
        evs = events(df)
        for v in VARIANTS:
            allrows[(name, v)] = sim(df, sp, evs, v[0], v[1], v[2], 1)
    for v in VARIANTS:
        line = []
        for name in d:
            r = np.array([x[1] for x in allrows[(name, v)]])
            if len(r) >= 20:
                line.append(f"{name}:{np.mean(r > 0) * 100:.0f}%/{r.mean():+.2f}R")
        print(f"  {v}: " + "  ".join(line))
    best = ("fade100", 0.25, 2.0)
    print(f"\nPER TAHUN untuk variasi {best} (win rate / total R / jumlah trade):")
    table = []
    for name in d:
        rows = allrows[(name, best)]
        if len(rows) < 20:
            continue
        y = per_year(rows)
        r = np.array([x[1] for x in rows])
        table.append((name, len(r), np.mean(r > 0) * 100, r.mean(), (y.total > 0).sum(), len(y)))
        print(f"  {name:11s} " + " ".join(f"{yy % 100:02d}:{w:.0f}%/{t:+.1f}R({n})" for yy, (n, w, t) in y.iterrows()))
    print("\nURUT win rate lalu profit:")
    for name, n, w, a, pos, ny in sorted(table, key=lambda x: (-x[2], -x[3])):
        print(f"  {name:11s} n={n:3d} win={w:4.1f}% rata={a:+.3f}R tahun untung {pos}/{ny}")


if __name__ == "__main__":
    main()
