"""Sinyal 💰 di pair tambahan (forex & ETH): layak ditambahkan? python -m research.pair_tambahan

Permintaan pengguna (3 Okt 2026): "uji juga pair tambahan" (sumber sinyal tambahan yang paling sehat = pair berbeda).
Mesin SAMA dengan cloud (research/sl_tangga.backtest): 3 set Donchian H1 (40/15, 55/20, 80/30), SL 3xATR, 5 posisi,
TP1 1R + 4 jalan, SL+ setelah TP1; forex melewati 3 candle pertama setelah buka pekan (seperti XAU). Spread akun
Standard (research/multi_asset.INSTRUMENTS), ETH 0,05%. Data: research/pair_data.py.
Tanpa look-ahead: kategori sinyal (konf+⭐ / konf / ⭐ / biasa, sama dengan cloud) yang dipakai sebagai "💰" untuk pair
itu DIPILIH HANYA dari periode LAMA (< Okt 2021): kategori dengan rata-rata > 0 dan n >= 30. Lalu diuji di BARU
(Okt 2021 – 2026) dengan mesin penuh (allow = kategori terpilih).
LOLOS (sebelum melihat hasil): BARU rata-rata > 0 dengan n >= 40, >= 60% tahun positif, total/DD >= 3.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .filters import features
from .gap_study import week_info
from .pair_data import FOREX, eth, forex, spread
from .sl_tangga import backtest
from .strategy_lab import Bars, rolling_max, rolling_min
from .strategy_lab2 import STAR, trend_states

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_pair_tambahan.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
SETS = ((40, 15), (55, 20), (80, 30))
CATS = ("konf+⭐", "konf", "⭐", "biasa")


def bars(sym: str) -> Bars:
    df = eth() if sym == "ETHUSD" else forex(sym)
    df = df[(df.high > df.low)].copy()
    return Bars(df, spread(sym))


def run(sym: str, b: Bars, allowed: tuple | None) -> pd.DataFrame:
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    cats = {}

    def cat(i, d):
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        return "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"

    def allow(i, d):
        if sym != "ETHUSD" and since[i] < 3:
            return False
        c = cat(i, d)
        cats[b.t[i + 1]] = c
        return allowed is None or c in allowed
    tr = []
    for n_in, n_out in SETS:
        hi, lo = rolling_max(b.h, n_in), rolling_min(b.l, n_in)
        hx, lx = rolling_max(b.h, n_out), rolling_min(b.l, n_out)
        tr += backtest(b, b.c > hi, b.c < lo, b.c < lx, b.c > hx, allow, tps=[1.0, None, None, None, None])
    df = pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r"])
    df["cat"] = df.t.map(cats)
    return df


def summ(x: pd.DataFrame) -> dict:
    if len(x) < 2:
        return {"n": len(x)}
    r = x.sort_values("t_out").R.to_numpy()
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    yr = x.groupby(x.t.dt.year).R.sum()
    lama, baru = x[x.t < SPLIT].R, x[x.t >= SPLIT].R
    return {"n": len(x), "wr": (x.R > 0).mean() * 100, "avg": x.R.mean(), "tot": x.R.sum(), "dd": dd,
            "lama": lama.mean() if len(lama) else np.nan, "n_lama": len(lama),
            "baru": baru.mean() if len(baru) else np.nan, "n_baru": len(baru),
            "th": (yr > 0).mean() * 100, "nth": len(yr), "ratio": x.R.sum() / -dd if dd < 0 else np.nan}


def fmt(s: dict) -> str:
    if s.get("n", 0) < 2:
        return f"n={s.get('n', 0)}"
    return (f"n={s['n']:4} WR {s['wr']:4.1f}% R/sin {s['avg']:+.3f} total {s['tot']:+6.1f}R DD {s['dd']:+6.1f} "
            f"total/DD {s['ratio']:4.1f} | LAMA {s['lama']:+.3f} (n {s['n_lama']}) BARU {s['baru']:+.3f} "
            f"(n {s['n_baru']}) | tahun+ {s['th']:.0f}% ({s['nth']} th)")


def report() -> str:
    L = ["# Sinyal 💰 di pair tambahan (research/pair_tambahan.py)", "",
         "Kategori 💰 per pair dipilih dari LAMA (< Okt 2021) saja, diuji di BARU. R = rata-rata 5 posisi (1R = SL).", ""]
    lolos = []
    for sym in ["ETHUSD"] + FOREX:
        try:
            b = bars(sym)
        except Exception as exc:  # noqa: BLE001
            L.append(f"== {sym}: data gagal ({exc}) ==\n")
            continue
        allsig = run(sym, b, None)
        L.append(f"== {sym} ({b.t[0]:%Y-%m} .. {b.t[-1]:%Y-%m}, {b.n} candle H1) ==")
        L.append(f"  semua sinyal         {fmt(summ(allsig))}")
        pick = []
        for c in CATS:
            x = allsig[allsig.cat == c]
            s = summ(x)
            L.append(f"  kategori {c:8}     {fmt(s)}")
            if s.get("n_lama", 0) >= 30 and s["lama"] > 0:
                pick.append(c)
        if not pick:
            L.append("  → tidak ada kategori positif di LAMA: TIDAK layak\n")
            continue
        sel = run(sym, b, tuple(pick))
        s = summ(sel)
        ok = (s.get("n_baru", 0) >= 40 and s["baru"] > 0 and s["th"] >= 60 and s["ratio"] >= 3)
        L.append(f"  💰 = {', '.join(pick)} (dipilih dari LAMA)")
        L.append(f"  uji nyata 💰         {fmt(s)} → {'LOLOS' if ok else 'tidak'}")
        if ok:
            lolos.append((sym, pick, s))
        L.append("")
    L.append("== Ringkasan LOLOS ==")
    for sym, pick, s in lolos:
        L.append(f"  {sym}: 💰 = {', '.join(pick)} | {fmt(s)}")
    if not lolos:
        L.append("  (tidak ada)")
    L.append("\nPembanding (mesin sama, research/kategori_badge.py, sejak Okt 2021): XAU 💰 +0,21R/sinyal, BTC 💰 +0,19R/sinyal.")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
