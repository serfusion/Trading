"""Metode lintas pasar (python -m research.cross_asset).

1. Rotasi momentum (cross-sectional): tiap awal bulan, beli 2 instrumen terkuat & jual 2 terlemah (return 3 bulan),
   tahan sebulan. Ukuran posisi = risiko sama (dibagi ATR harian 20). 11 forex + XAU, ejtrader 2012-2022.
2. Pairs trading EURUSD vs GBPUSD: z-score log rasio (200 candle H1); masuk |z|>2, keluar z melewati 0,
   stop |z|>4 atau 5 hari. 1R = jarak ke stop saat masuk.
Latih s/d 2017, uji 2018-2022. Spread dihitung, swap belum.
"""
import numpy as np
import pandas as pd

from .multi_asset import INSTRUMENTS, load

SPLIT = pd.Timestamp("2018-01-01", tz="UTC")


def rotation(k=2, look=63):
    names = list(INSTRUMENTS)
    d1 = {n: load(n).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
          for n in names}
    close = pd.DataFrame({n: d["close"] for n, d in d1.items()}).dropna()
    atr = pd.DataFrame({n: (d["high"] - d["low"]).rolling(20).mean() for n, d in d1.items()}).reindex(close.index)
    months = close.groupby([close.index.year, close.index.month]).head(1).index   # hari pertama tiap bulan
    rows = []
    for a, b in zip(months[:-1], months[1:]):
        i = close.index.get_loc(a)
        if i < look + 1:
            continue
        prev = close.index[i - 1]
        mom = close.loc[prev] / close.iloc[i - 1 - look] - 1
        vol = atr.loc[prev]
        ranked = mom.dropna().sort_values()
        legs = [(n, -1) for n in ranked.index[:k]] + [(n, 1) for n in ranked.index[-k:]]
        for n, d in legs:
            entry, exit_ = close.loc[a, n], close.loc[close.index[close.index.get_loc(b) - 1], n]
            spread = INSTRUMENTS[n][1]
            r = ((exit_ - entry) * d - spread) / (2 * vol[n])          # 1R = 2 x ATR harian
            rows.append((a, n, d, r))
    return pd.DataFrame(rows, columns=["t", "inst", "dir", "R"])


def pairs(a="EURUSD", b="GBPUSD", win=200, z_in=2.0, z_stop=4.0, max_bars=120):
    x, y = load(a)["close"], load(b)["close"]
    df = pd.concat([x, y], axis=1, keys=[a, b]).dropna()
    lr = np.log(df[a] / df[b])
    m, sd = lr.rolling(win).mean(), lr.rolling(win).std()
    z = ((lr - m) / sd).to_numpy()
    lrv, sdv, t = lr.to_numpy(), sd.to_numpy(), df.index
    cost = (INSTRUMENTS[a][1] / df[a] + INSTRUMENTS[b][1] / df[b]).to_numpy()   # spread 2 kaki, dalam log
    rows, i, n = [], win, len(df) - 1
    while i < n - 1:
        if np.isnan(z[i]) or not z_in <= abs(z[i]) < z_in + 1:        # masuk hanya di 2 <= |z| < 3
            i += 1
            continue
        d = -np.sign(z[i])                       # z tinggi -> jual rasio
        entry, risk = lrv[i + 1], (z_stop - abs(z[i])) * sdv[i]
        j = i + 1
        while j < n - 1 and j - i < max_bars:
            if abs(z[j]) >= z_stop or np.sign(z[j]) != np.sign(z[i]):
                break
            j += 1
        r = ((lrv[j + 1] - entry) * d - cost[i + 1]) / max(risk, 1e-9)
        rows.append((t[i + 1], r))
        i = j + 1
    return pd.DataFrame(rows, columns=["t", "R"])


def show(name, r):
    for label, part in (("LATIH", r[r.t < SPLIT]), ("UJI  ", r[r.t >= SPLIT])):
        v = part.R.to_numpy()
        if len(v) == 0:
            continue
        t = v.mean() / (v.std() or 1e-9) * np.sqrt(len(v))
        print(f"  {name:32s} {label} n={len(v):4d} win={np.mean(v > 0) * 100:4.1f}% rata={v.mean():+.3f}R "
              f"total={v.sum():+6.1f}R t={t:+.2f}")


def main():
    for k in (1, 2, 3):
        for look in (21, 63, 126):
            show(f"Rotasi momentum top/bottom {k}, {look} hari", rotation(k, look))
    for a, b in (("EURUSD", "GBPUSD"), ("AUDUSD", "USDCAD"), ("EURJPY", "GBPJPY"), ("USDCHF", "EURUSD")):
        show(f"Pairs {a}/{b}", pairs(a, b))


if __name__ == "__main__":
    main()
