"""Sinyal 💰 lebih sering (XAU, BTC, XAU lagi, ...) tanpa menurunkan mutu? python -m research.sinyal_lapis

Permintaan pengguna (2 Okt 2026): "sinyal jangan hanya 1x — beberapa menit lalu XAU, lalu BTC, lalu XAU lagi dan XAU
lagi; sinyal muncul bila WR dan profit tinggi; uji dan perbaiki". Saat ini tiap set Donchian (40/15, 55/20, 80/30)
hanya memegang SATU sinyal; sinyal baru di set itu baru muncul setelah sinyal lama ditutup (TUTUP/SL/SL+).

Varian (mesin = research/sl_tangga.backtest seperti cloud: H1, SL 3xATR, 5 posisi, TP1 1R, SL+ 0,1R, kategori 💰):
  bawaan                      satu sinyal per set
  lapis setelah TP1           sinyal baru di set yang sama boleh setelah TP1 sinyal sebelumnya kena (sisa posisi
                              sudah SL+, risiko lama ±0)
  lapis setelah TP1 (baru)    idem, tetapi hanya pada breakout BARU (candle sebelumnya belum di luar channel)
  lapis kapan saja (baru)     breakout baru boleh walau sinyal lama masih rugi/belum TP1
  tambah set 20/10 & 30/15    5 set (lebih banyak breakout), satu sinyal per set
  kategori + ⭐ / + biasa      XAU: juga kirim kategori ⭐ / semua kategori (BTC sudah termasuk ⭐)
Ukuran: sinyal/bulan, WR, R per sinyal, total R, DD (urut waktu keluar), rata LAMA/BARU, tahun positif, sinyal
terbuka bersamaan (maks & rata-rata, risiko awal per sinyal = 1R x lot). LOLOS (ditetapkan sebelum melihat hasil):
total R lebih besar dari bawaan, R/sinyal >= 80% bawaan dan > 0 di LAMA & BARU, lebih baik di >= 60% tahun,
DD tidak lebih buruk dari 1,5x bawaan. Tambahan (setelah putaran 1: lapis setelah TP1 menambah sinyal tetapi DD 2x):
batas lapisan per set & lot ½ untuk lapisan; dibandingkan juga total/DD (hasil per satuan risiko) di semua data & BARU.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import MONEY, SPLIT, asset
from .filters import features
from .gap_study import week_info
from .sl_tangga import backtest
from .strategy_lab import rolling_max, rolling_min
from .strategy_lab2 import STAR, trend_states

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_sinyal_lapis.txt"
BASE_SETS = ((40, 15), (55, 20), (80, 30))
VARIANTS = {
    "bawaan (1 sinyal per set)": {},
    "lapis setelah TP1": {"overlap": "tp1"},
    "lapis setelah TP1 (breakout baru)": {"overlap": "tp1", "fresh": True},
    "lapis kapan saja (breakout baru)": {"overlap": "any", "fresh": True},
    "tambah set 20/10 & 30/15": {"sets": BASE_SETS + ((20, 10), (30, 15))},
    "kategori + ⭐": {"extra_cat": ("⭐",)},
    "kategori semua (+ biasa)": {"extra_cat": ("⭐", "biasa")},
    "lapis setelah TP1 + tambah set": {"overlap": "tp1", "sets": BASE_SETS + ((20, 10), (30, 15))},
    "lapis setelah TP1, maks 2 per set": {"overlap": "tp1", "max_layers": 2},
    "lapis setelah TP1, lapisan lot ½": {"overlap": "tp1", "half": True},
    "lapis setelah TP1, maks 2, lot ½": {"overlap": "tp1", "max_layers": 2, "half": True},
}


def run(name: str, v: dict) -> pd.DataFrame:
    a = asset(name)
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    money = tuple(MONEY[name]) + tuple(v.get("extra_cat", ()))

    def allow(i, d):
        if name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return cat in money
    tr = []
    for n_in, n_out in v.get("sets", BASE_SETS):
        hi, lo = rolling_max(b.h, n_in), rolling_min(b.l, n_in)
        hx, lx = rolling_max(b.h, n_out), rolling_min(b.l, n_out)
        one = backtest(b, b.c > hi, b.c < lo, b.c < lx, b.c > hx, allow, tps=[1.0, None, None, None, None],
                       overlap=v.get("overlap"), fresh=v.get("fresh", False), max_layers=v.get("max_layers"))
        last_out = None
        for t, t_out, r, d, mr in one:             # lapisan = dibuka saat sinyal sebelumnya di set ini masih terbuka
            lay = last_out is not None and t < last_out
            tr.append((t, t_out, r * (0.5 if lay and v.get("half") else 1.0), d, mr, lay))
            last_out = t_out if last_out is None else max(last_out, t_out)
    return pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r", "lapis"])


def concurrent(df: pd.DataFrame) -> tuple[int, float]:
    ev = sorted([(t, 1) for t in df.t] + [(t, -1) for t in df.t_out], key=lambda x: (x[0], x[1]))
    cur, mx, area, last = 0, 0, 0.0, None
    for t, s in ev:
        if last is not None:
            area += cur * (t - last).total_seconds()
        cur += s
        mx = max(mx, cur)
        last = t
    span = (df.t_out.max() - df.t.min()).total_seconds()
    return mx, area / span if span > 0 else 0.0


def summary(df: pd.DataFrame, split: pd.Timestamp) -> dict:
    r = df.sort_values("t_out").R.to_numpy()
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    yr = df.groupby(df.t.dt.year).R.sum()
    months = max((df.t.max() - df.t.min()).days / 30.44, 1)
    mx, avg_c = concurrent(df)
    base_new = df[df.t >= split].sort_values("t_out").R.to_numpy()
    eqn = np.cumsum(base_new)
    dd_new = float((eqn - np.maximum.accumulate(np.r_[0, eqn])[1:]).min()) if len(eqn) else 0.0
    return {"rasio": df.R.sum() / -dd if dd < 0 else np.nan, "dd_baru": dd_new,
            "tot_baru": df.R[df.t >= split].sum(), "n_lapis": int(df.lapis.sum()),
            "avg_lapis": df.R[df.lapis].mean() if df.lapis.any() else np.nan,
            "n": len(df), "bln": len(df) / months, "wr": 100 * (df.R > 0).mean(), "avg": df.R.mean(),
            "tot": df.R.sum(), "dd": dd, "lama": df.R[df.t < split].mean(), "baru": df.R[df.t >= split].mean(),
            "yr": yr, "tahun": f"{(yr > 0).sum()}/{len(yr)}", "maxc": mx, "avgc": avg_c}


def report() -> str:
    L = ["# Sinyal 💰 lebih sering: berlapis / tambah set / kategori (research/sinyal_lapis.py)", "",
         "R = rata-rata 5 posisi per sinyal (1R = jarak SL awal). DD dalam R (urut waktu keluar). 'terbuka' = sinyal",
         "yang terbuka bersamaan dalam satu aset (maks / rata-rata).", ""]
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        L.append(f"== {name} (LAMA < {split:%Y}) ==")
        L.append(f"  {'varian':36} {'sinyal':>6} {'/bln':>5} {'WR':>6} {'R/sin':>7} {'total':>7} {'DD':>6} "
                 f"{'LAMA':>7} {'BARU':>7} {'tahun+':>6} {'terbuka':>9} | vs bawaan")
        base = None
        for vname, v in VARIANTS.items():
            s = summary(run(name, v), split)
            if base is None:
                base = s
                verdict = ""
            else:
                better = (s["yr"] - base["yr"]).reindex(base["yr"].index).fillna(0)
                nb = int((better > 0).sum())
                lolos = (s["tot"] > base["tot"] and s["avg"] >= 0.8 * base["avg"] and s["lama"] > 0 and s["baru"] > 0
                         and nb >= 0.6 * len(better) and s["dd"] >= 1.5 * base["dd"])
                verdict = f"lebih baik {nb}/{len(better)} th → {'LOLOS' if lolos else 'tidak'}"
            L.append(f"  {vname:36} {s['n']:6d} {s['bln']:5.1f} {s['wr']:5.1f}% {s['avg']:+7.3f} {s['tot']:+7.1f} "
                     f"{s['dd']:+6.1f} {s['lama']:+7.3f} {s['baru']:+7.3f} {s['tahun']:>6} {s['maxc']:3d} / {s['avgc']:.1f}"
                     f" | {verdict}")
        L.append(f"  {'risiko vs hasil':36} {'total/DD':>9} {'BARU: total':>12} {'DD BARU':>8} {'total/DD BARU':>14} "
                 f"{'lapisan n':>9} {'R/lapisan':>9}")
        for vname, v in VARIANTS.items():
            s = summary(run(name, v), split)
            r_new = s["tot_baru"] / -s["dd_baru"] if s["dd_baru"] < 0 else float("nan")
            L.append(f"  {vname:36} {s['rasio']:9.1f} {s['tot_baru']:+12.1f} {s['dd_baru']:+8.1f} {r_new:14.1f} "
                     f"{s['n_lapis']:9d} {s['avg_lapis']:+9.3f}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
