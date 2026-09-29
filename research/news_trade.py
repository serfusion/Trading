"""Aturan entry/SL/TP setelah berita AS (NFP, CPI, PPI, …) untuk XAU/USD — adakah yang untung konsisten?

python -m research.news_trade

Pertanyaan pengguna (29 Sep 2026): tab News berisi kalender; setelah Act/Cons/Prev diisi, aplikasi menyarankan
entry, TP, SL. Sebelum menyarankan apa pun, aturannya diuji di sini (kalender ForexFactory historis + XAU M15
2012–2026, research/event_stats.py).

Mesin: rilis di candle M15 ke-i. Entry di open candle i+1 (15 menit setelah rilis, lonjakan pertama sudah lewat) +
spread 0,60 (2x normal, saat berita). SL dicek lebih dulu tiap candle; TP sesudahnya; tutup paksa di close candle
i+16 (4 jam). R = hasil / jarak SL.

Varian (ditetapkan sebelum melihat hasil):
- arah: IKUT kejutan (data lemah -> BUY emas) / LAWAN kejutan (fade lonjakan)
- SL: di ekstrem candle rilis (BUY: low candle i) / 3x ATR M15
- TP: 1R / 2R / tanpa TP (tutup 4 jam)
- filter: semua kejutan / kejutan BESAR (>= 2x median) / candle rilis sudah searah kejutan
Kriteria "layak disarankan": rata R > 0 di latih (< 2019) DAN uji, >= 60% tahun positif, t > 2 (seluruh data).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .event_stats import PRIORITY, releases, xau_m15
from .news_data import load_calendar
from .run_scan import DATA

SPREAD = 0.60
HOLD = 16
SPLIT = pd.Timestamp("2019-01-01", tz="UTC")
GROUPS = [g for g in PRIORITY if g != "FOMC"]


def simulate(px: pd.DataFrame, ev: pd.DataFrame, follow: bool, sl_mode: str, tp_r: float | None,
             filt: str) -> pd.DataFrame:
    o, h, l, c = (px[k].to_numpy() for k in ("open", "high", "low", "close"))
    tr = np.maximum(h - l, np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]]))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    idx = px.index
    out = []
    for e in ev.itertuples():
        if not e.bias or e.bias != e.bias:
            continue
        i = idx.searchsorted(e.time, side="right") - 1
        if i < 20 or not (idx[i] <= e.time < idx[i] + pd.Timedelta(minutes=15)) or i + HOLD + 1 >= len(px):
            continue
        if filt == "besar" and not e.besar:
            continue
        first = np.sign(c[i] - o[i])
        if filt == "candle searah" and first != e.bias:
            continue
        d = int(e.bias if follow else -e.bias)
        entry = o[i + 1] + (SPREAD if d > 0 else 0.0)
        if sl_mode == "candle rilis":
            sl = l[i] if d > 0 else h[i] + SPREAD
        else:
            sl = entry - d * 3 * atr[i - 1]
        risk = (entry - sl) * d
        if not risk > 0.5:
            continue
        tp = entry + d * tp_r * risk if tp_r else None
        r = None
        for k in range(i + 1, i + 1 + HOLD):
            lo, hi = l[k], h[k] + (SPREAD if d < 0 else 0.0)
            if (lo <= sl) if d > 0 else (hi >= sl):
                r = -1.0
                break
            if tp is not None and ((hi >= tp) if d > 0 else (lo <= tp)):
                r = tp_r
                break
        if r is None:
            r = ((c[i + HOLD] - entry) * d - (SPREAD if d < 0 else 0.0)) / risk
        out.append((e.time, e.group, r))
    return pd.DataFrame(out, columns=["time", "group", "R"])


def verdict(df: pd.DataFrame) -> dict:
    r = df.R.to_numpy()
    if len(r) < 20:
        return {"n": len(r), "ok": False}
    tr, te = df[df.time < SPLIT].R, df[df.time >= SPLIT].R
    yrs = df.groupby(df.time.dt.year).R.sum()
    t = r.mean() / (r.std() or 1e-9) * math.sqrt(len(r))
    ok = tr.mean() > 0 and te.mean() > 0 and (yrs > 0).mean() >= 0.6 and t > 2
    return {"n": len(r), "wr": 100 * (r > 0).mean(), "avg": r.mean(), "latih": tr.mean(), "uji": te.mean(),
            "tahun": f"{(yrs > 0).sum()}/{len(yrs)}", "t": t, "ok": ok}


def main() -> None:
    ev = releases(load_calendar(DATA))
    ev = ev[ev.group.isin(GROUPS)]
    px = xau_m15()
    print(f"Rilis {len(ev)} ({ev.time.min():%Y-%m}–{ev.time.max():%Y-%m}), XAU M15 {px.index[0]:%Y-%m}–{px.index[-1]:%Y-%m}")
    found = []
    for follow in (True, False):
        for sl_mode in ("candle rilis", "3 ATR"):
            for tp_r in (1.0, 2.0, None):
                for filt in ("semua", "besar", "candle searah"):
                    df = simulate(px, ev, follow, sl_mode, tp_r, filt)
                    name = (f"{'IKUT' if follow else 'LAWAN'} kejutan | SL {sl_mode} | "
                            f"{'TP ' + str(tp_r) + 'R' if tp_r else 'tutup 4 jam'} | {filt}")
                    v = verdict(df)
                    if v["n"] < 20:
                        print(f"{name:62s} n={v['n']} (terlalu sedikit)")
                        continue
                    print(f"{name:62s} n={v['n']:4d} WR={v['wr']:4.0f}% rata={v['avg']:+.3f}R latih={v['latih']:+.3f} "
                          f"uji={v['uji']:+.3f} tahun+={v['tahun']} t={v['t']:+.1f}{'  ✅' if v['ok'] else ''}")
                    if v["ok"]:
                        found.append(name)
                    for grp in ("NFP", "CPI", "PPI"):
                        g = verdict(df[df.group == grp])
                        if g.get("ok"):
                            print(f"    -> {grp}: n={g['n']} rata={g['avg']:+.3f}R latih={g['latih']:+.3f} "
                                  f"uji={g['uji']:+.3f} tahun+={g['tahun']} t={g['t']:+.1f} ✅")
                            found.append(f"{name} [{grp}]")
    print(f"\nLolos kriteria: {len(found)} dari {2 * 2 * 3 * 3} varian gabungan (+ per grup NFP/CPI/PPI)")
    for f in found:
        print("  ", f)


if __name__ == "__main__":
    main()
