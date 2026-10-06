"""Perbaikan sinyal 💎 spot: lebih banyak koin & volatilitas — python -m research.spot_vol

Permintaan pengguna (5 Okt 2026): "perbaiki sinyal koin WR & profit tinggi, cari informasi koin sebanyak-banyaknya,
jika volatilitas tinggi skip atau manfaatkan alur supaya profit". Dasar = sinyal terpasang (spot_peluang.final:
peluang gradient boosting ≥ 0,93 ATAU 3 merah ≥10% +SMA200; TP +3%/10 hari; walk-forward per tahun).
Varian (semua dinilai LAMA < Okt 2021 & BARU, per trade + portofolio 10 slot):
  A. semesta: 20 koin live vs SEMUA koin yang masih diperdagangkan (data s.d. 2026)
  B. lewati volatilitas tinggi: vol14 koin di atas persentil 70/80/90 dari 365 hari terakhir koin itu sendiri;
     atau volatilitas BTC tinggi (pasar panik)
  C. manfaatkan alur saat volatil: TP lebih lebar (+5%) bila vol tinggi; atau beli ikut tren (harga di atas SMA50,
     return 7 hari > 0) saat volatil
"""
from __future__ import annotations

import pandas as pd

from .pair_data import _dir
from .spot_dip import SPLIT
from .spot_dip2 import portfolio
from .spot_peluang import LIVE, dataset, labels, line, take, walk_forward

OUT = __import__("pathlib").Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_spot_vol.txt"
FIAT = {"AUD", "EUR", "GBP", "USD", "JPY", "CHF", "CAD", "NZD"}


def all_coins() -> tuple[list[str], list[str]]:
    coins, alive = [], []
    for f in sorted(_dir().glob("*USD.parquet")):
        c = f.name[:-11]
        if c in FIAT or len(c) < 2:
            continue
        coins.append(c)
        last = pd.read_parquet(f, columns=["close"]).index.max()
        if last >= pd.Timestamp("2026-07-01", tz="UTC"):
            alive.append(c)
    return ["BTC"] + coins, ["BTC"] + alive


def main() -> None:
    coins, alive = all_coins()
    df, data = dataset(coins, 0.03, 10)
    df = df.sort_index(kind="stable")
    df["pg"] = walk_forward(df, 10, "gbm")
    ok = df.pg.notna()
    df["vrank"] = df.groupby("coin").vol14.transform(lambda s: s.rolling(365, min_periods=120).rank(pct=True))
    btcv = df[df.coin == "BTC"].vrank
    df["bvrank"] = btcv[~btcv.index.duplicated()].reindex(df.index).to_numpy()
    base = ((df.pg >= 0.93) | ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0))) & ok
    live = df.base.isin(LIVE)
    allv = df.base.isin(alive)
    L = ["# Perbaikan sinyal 💎 spot: semesta koin & volatilitas (research/spot_vol.py)",
         f"Semua koin data: {len(coins)}; masih diperdagangkan: {len(alive)} ({', '.join(alive)})",
         "TP +3%/10 hari kecuali disebut. Biaya 0,30%. Portofolio 10 slot. LAMA 2019–Sep 2021, BARU Okt 2021–2026.", ""]
    s0, s1, s2 = pd.Timestamp("2019-01-01", tz="UTC"), SPLIT, pd.Timestamp("2026-10-01", tz="UTC")

    def rep(name, mask, frame=df):
        tr = take(frame, mask.to_numpy() if hasattr(mask, "to_numpy") else mask)
        pl = portfolio(tr, data, 10, s0, s1) if len(tr) else {}
        pb = portfolio(tr, data, 10, s1, s2) if len(tr) else {}
        L.append(f"{name}\n   {line(tr)}")
        if pl and pb:
            L.append(f"   portofolio: LAMA {pl['cagr'] * 100:+.1f}%/th DD {pl['dd'] * 100:.0f}% | BARU {pb['cagr'] * 100:+.1f}%/th "
                     f"DD {pb['dd'] * 100:.0f}% | " + " ".join(f"{t.year}:{v * 100:+.0f}%" for t, v in pb["tahun"].items()))

    rep("0. TERPASANG: 20 koin live", base & live)
    rep("A. semua koin yang masih diperdagangkan", base & allv)
    rep("A2. koin tambahan saja (di luar 20)", base & allv & ~live)
    for q in (0.7, 0.8, 0.9):
        rep(f"B. 20 koin, lewati vol koin > P{int(q * 100)}", base & live & ~(df.vrank > q))
        rep(f"B. semua koin, lewati vol koin > P{int(q * 100)}", base & allv & ~(df.vrank > q))
    rep("B. 20 koin, lewati vol BTC > P80", base & live & ~(df.bvrank > 0.8))
    rep("B. 20 koin, HANYA vol koin > P80 (kebalikan)", base & live & (df.vrank > 0.8))
    # C: TP +5% saat volatil -> label ulang
    lab5 = []
    for coin, segs in data.items():
        for si, d in enumerate(segs):
            name = f"{coin}#{si}" if len(segs) > 1 else coin
            x = labels(d, 0.05, 10)
            x["coin"] = name
            lab5.append(x)
    l5 = pd.concat(lab5).reset_index(names="t").set_index(["t", "coin"])
    key = pd.MultiIndex.from_arrays([df.index, df.coin])
    alt = df.copy()
    hi = (df.vrank > 0.8).to_numpy()
    r5 = l5.r.reindex(key).to_numpy()
    k5 = l5.k.reindex(key).to_numpy()
    alt.loc[hi, "r"] = r5[hi]
    idx_map = {(f"{c}#{i}" if len(s) > 1 else c): d.index for c, s in data.items() for i, d in enumerate(s)}
    alt["t_out"] = [idx_map[c][int(k)] if h and k == k and k >= 0 else t
                    for c, k, h, t in zip(df.coin, k5, hi, df.t_out)]
    rep("C1. 20 koin, TP +5% saat vol koin > P80", base & live, alt)
    trend = (df.vrank > 0.8) & (df.d50 > 0) & (df.r7 > 0) & ok
    rep("C2. ikut tren saat volatil (vol>P80, di atas SMA50, naik 7 hari) — sinyal sendiri, 20 koin", trend & live)
    rep("C3. terpasang + C2", (base | trend) & live)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
