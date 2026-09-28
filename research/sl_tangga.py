"""SL+ bertangga, TP bertingkat, dan trailing ATR untuk sinyal 💰 (python -m research.sl_tangga).

Pertanyaan pengguna (28 Sep 2026): skema bawaan = 5 posisi, posisi #1 TP1 1R, 4 posisi jalan, SL+ ke entry+0,1R
setelah TP1, sisanya keluar saat sinyal TUTUP (channel exit). Apakah lebih baik bila SL+ terus dinaikkan setiap
harga mencapai target tertentu, atau memakai TP2/TP3?

Mesin sama dengan cloud (3 set Donchian H1, SL 3xATR, hanya kategori 💰, lewati 3 candle setelah buka pekan XAU,
satu posisi per set, sinyal ditolak -> set kosong). Konservatif: SL dicek lebih dulu; TP tidak dihitung di candle
entry; SL baru (SL+, tangga, trailing) berlaku mulai candle BERIKUTNYA; gap melewati SL diisi di open.
R per sinyal = rata-rata R kelima posisi (sama dengan statistik badge).

Varian (ditetapkan sebelum melihat hasil):
- F (bawaan sekarang) dan A (tanpa TP1/SL+, semua posisi jalan) sebagai pembanding
- F + tangga (langkah s, jarak g): setiap harga mencapai k*s R, SL sisa naik ke (k*s - g) R
  (s=1,g=1: 2R->SL 1R, 3R->SL 2R, ...; s=1,g=2; s=1,g=3; s=0,5,g=1)
- TP bertingkat: posisi #1 TP 1R, #2 TP 2R, #3 TP 3R, #4-5 jalan (SL+ setelah TP1), dengan/tanpa tangga s=1,g=1
- F + trailing ATR (chandelier): setelah TP1, SL sisa = ekstrem harga sejak entry - k x ATR (k = 3, 5)
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .eksternal import MONEY, SPLIT, asset
from .filters import features
from .gap_study import week_info
from .strategy_lab2 import STAR, signals, trend_states

VARIANTS = {
    "F bawaan (TP1 1R + 4 jalan, SL+ setelah TP1)": dict(tps=[1.0, None, None, None, None]),
    "A tanpa TP1 & SL+ (5 jalan)": dict(tps=[None] * 5, be=False),
    "F + tangga 1R (2R->SL 1R, 3R->SL 2R, ...)": dict(tps=[1.0, None, None, None, None], ladder=(1.0, 1.0)),
    "F + tangga jarak 2R (3R->SL 1R, 4R->SL 2R, ...)": dict(tps=[1.0, None, None, None, None], ladder=(1.0, 2.0)),
    "F + tangga jarak 3R (4R->SL 1R, ...)": dict(tps=[1.0, None, None, None, None], ladder=(1.0, 3.0)),
    "F + tangga 0,5R (1,5R->SL 0,5R, 2R->SL 1R, ...)": dict(tps=[1.0, None, None, None, None], ladder=(0.5, 1.0)),
    "TP 1R/2R/3R + 2 jalan": dict(tps=[1.0, 2.0, 3.0, None, None]),
    "TP 1R/2R/3R + 2 jalan + tangga 1R": dict(tps=[1.0, 2.0, 3.0, None, None], ladder=(1.0, 1.0)),
    "F + trailing 3 ATR setelah TP1": dict(tps=[1.0, None, None, None, None], chand=3.0),
    "F + trailing 5 ATR setelah TP1": dict(tps=[1.0, None, None, None, None], chand=5.0),
}


def backtest(b, li, si, lo, so, allow, tps, be=True, ladder=None, chand=None, sl_atr=3.0):
    """Satu set. Return list (t_entry, t_exit, R rata-rata per posisi, dir, R maksimum yang dicapai)."""
    trades, i, n = [], 0, b.n
    o, h, l, sp, a = b.o, b.h, b.l, b.sp, b.atr
    legs = len(tps)
    while i < n - 2:
        d = 1 if li[i] else (-1 if si[i] else 0)
        if d == 0 or not a[i] > 0 or (allow is not None and not allow(i, d)):
            i += 1
            continue
        j = i + 1
        entry = o[j] + (sp[j] if d > 0 else 0.0)
        risk = sl_atr * a[i]
        sl = entry - d * risk
        open_legs = [k for k in range(legs)]
        pnl, k, tp1_hit, best, max_r = 0.0, j, False, entry, 0.0
        out = lo if d > 0 else so
        done = False
        while k < n - 1 and not done:
            adj = sp[k] if d < 0 else 0.0
            if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):          # SL/SL+ lebih dulu
                px = sl if k == j else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                pnl += (px - entry) * d * len(open_legs)
                done = True
                break
            if k > j:
                for leg in list(open_legs):
                    tp = tps[leg]
                    if tp is None:
                        continue
                    lvl = entry + d * tp * risk
                    if (h[k] + adj >= lvl) if d > 0 else (l[k] + adj <= lvl):
                        pnl += tp * risk
                        open_legs.remove(leg)
                        if tp == min(t for t in tps if t is not None):
                            tp1_hit = True
                if not open_legs:
                    done = True
                    break
            if out[k]:
                pnl += (o[k + 1] + (sp[k + 1] if d < 0 else 0.0) - entry) * d * len(open_legs)
                k += 1
                done = True
                break
            # pembaruan SL (berlaku candle berikutnya)
            fav = (h[k] - entry) if d > 0 else (entry - l[k] - adj)
            max_r = max(max_r, fav / risk)
            best = max(best, h[k]) if d > 0 else min(best, l[k] + adj)
            new = []
            if be and tp1_hit:
                new.append(0.1)
            if ladder is not None and k > j:
                s, g = ladder
                lvl = math.floor(max_r / s + 1e-9) * s
                if lvl - g > 1e-9:
                    new.append(lvl - g)
            for r in new:
                cand = entry + d * r * risk
                sl = max(sl, cand) if d > 0 else min(sl, cand)
            if chand is not None and tp1_hit:
                cand = best - d * chand * a[k]
                sl = max(sl, cand) if d > 0 else min(sl, cand)
            k += 1
        if not done:
            break
        trades.append((b.t[j], b.t[min(k, n - 1)], pnl / risk / legs, d, max_r))
        i = k + 1
    return trades


def run(name: str, variant: dict) -> pd.DataFrame:
    a = asset(name)
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    money = MONEY[name]

    def allow(i, d):
        if name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return cat in money
    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest(b, li, si, lo, so, allow, **variant)
    return pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r"])


def summary(df: pd.DataFrame, split: pd.Timestamp) -> dict:
    r = df.R.to_numpy()
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    yr = df.groupby(df.t.dt.year).R.sum()
    return {"n": len(r), "wr": 100 * (r > 0).mean(), "avg": r.mean(), "tot": r.sum(), "dd": dd,
            "latih": df.R[df.t < split].mean(), "uji": df.R[df.t >= split].mean(),
            "tahun": f"{(yr > 0).sum()}/{len(yr)}", "yr": yr}


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        print(f"\n=== {name} — sinyal 💰 (uji nyata seperti cloud; latih < {split:%Y}) ===")
        print(f"{'Skema':52s} {'sinyal':>6s} {'WR':>6s} {'R/sinyal':>9s} {'total':>8s} {'DD':>7s} "
              f"{'latih':>7s} {'uji':>7s} tahun+")
        base = None
        for vname, v in VARIANTS.items():
            df = run(name, v)
            s = summary(df, split)
            if base is None:
                base = s
            print(f"{vname:52s} {s['n']:6d} {s['wr']:5.1f}% {s['avg']:+9.3f} {s['tot']:+8.1f} {s['dd']:+7.1f} "
                  f"{s['latih']:+7.3f} {s['uji']:+7.3f} {s['tahun']}")
            better = (s["yr"] - base["yr"]).reindex(base["yr"].index).fillna(0)
            if vname != next(iter(VARIANTS)):
                print(f"{'':52s} vs bawaan per tahun: lebih baik {int((better > 0).sum())}/{len(better)} | "
                      + " ".join(f"{y % 100}:{x:+.0f}" for y, x in better.items()))


if __name__ == "__main__":
    main()
