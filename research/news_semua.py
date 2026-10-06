"""Prediksi arah emas SEBELUM rilis untuk semua berita USD besar — python -m research.news_semua

Permintaan pengguna (6 Okt 2026): "bagaimana news lain selain NFP? prediksi sebelum news keluar sekian persen naik/turun".
Per judul (ForexFactory 2012–2025, XAU M15): fitur yang SUDAH diketahui sebelum rilis — kejutan rilis sebelumnya
(arah & besar relatif), konsensus vs angka sebelumnya (pasar mengharapkan naik/turun), tren 3 rilis, gerak emas 4 jam &
24 jam sebelum rilis, emas vs EMA 20 hari. Target: emas naik 1 jam setelah rilis (dan 15 mnt). Uji: aturan sederhana per
fitur + regresi logistik walk-forward per tahun (latih tahun < Y). Dilaporkan LAMA (< Okt 2021) & BARU.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression

from .event_stats import xau_m15
from .news_prediksi import EVENTS, calendar

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_semua.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
FEATS = ["prev_s", "prev_z", "exp_up", "trend3", "g4", "g24", "gema"]


def build() -> pd.DataFrame:
    m = xau_m15()
    idx, c = m.index, m.close.to_numpy()
    ema = m.close.ewm(span=20 * 96, adjust=False).mean().to_numpy()
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS)].sort_values("time")
    rows = []
    for ev, g in cal.groupby("event"):
        g = g.reset_index(drop=True)
        sd = (g.a - g.f).abs().expanding().median().shift(1)
        for i, r in g.iterrows():
            t = pd.Timestamp(r.time)
            k = idx.searchsorted(t)
            if k < 100 or k + 4 >= len(idx) or abs((idx[k] - t).total_seconds()) > 60:
                continue
            p0 = c[k - 1]                             # close candle sebelum rilis
            row = {"event": ev, "time": t, "up15": float(c[k] > p0), "up60": float(c[k + 3] > p0),
                   "r60": c[k + 3] - p0, "g4": p0 - c[k - 17], "g24": p0 - c[max(0, k - 97)],
                   "gema": float(p0 > ema[k - 1])}
            if i >= 3:
                pr = g.iloc[i - 1]
                row["prev_s"] = float(np.sign(pr.a - pr.f))
                row["prev_z"] = (pr.a - pr.f) / sd.iloc[i] if sd.iloc[i] and sd.iloc[i] > 0 else 0.0
                row["exp_up"] = float(np.sign(r.f - pr.a))   # konsensus vs angka terakhir
                row["trend3"] = float(np.sign(pr.a - g.iloc[i - 3].a))
            rows.append(row)
    return pd.DataFrame(rows).dropna(subset=FEATS)


def main() -> None:
    df = build()
    L = ["# Prediksi arah emas SEBELUM rilis — semua berita USD besar (research/news_semua.py)",
         "Target: emas naik 1 jam setelah rilis (close M15 sebelum rilis → +60 mnt). LAMA < Okt 2021, BARU ≥ Okt 2021.",
         "Aturan dianggap berguna bila searah & ≥ 58% di LAMA DAN BARU dengan n ≥ 30 masing-masing.", ""]
    keep = []
    for ev, g in df.groupby("event"):
        lama, baru = g[g.time < SPLIT], g[g.time >= SPLIT]
        L.append(f"## {ev} (n {len(g)}; dasar naik 1 jam LAMA {lama.up60.mean() * 100:.0f}% / BARU {baru.up60.mean() * 100:.0f}%)")
        best = []
        for f in ("prev_s", "exp_up", "trend3", "gema"):
            for v in (1.0, -1.0) if f != "gema" else (1.0, 0.0):
                a, b = lama[lama[f] == v], baru[baru[f] == v]
                if len(a) < 30 or len(b) < 30:
                    continue
                pa, pb = a.up60.mean(), b.up60.mean()
                if (pa >= .58 and pb >= .58) or (pa <= .42 and pb <= .42):
                    best.append(f"   ✔ {f}={v:+.0f}: naik LAMA {pa * 100:.0f}% (n {len(a)}) | BARU {pb * 100:.0f}% (n {len(b)})")
                    keep.append((ev, f, v, pa, pb, len(a), len(b)))
        for f in ("g4", "g24"):
            for lab, sel in (("emas turun sebelum rilis", lambda x, f=f: x[f] < 0), ("emas naik sebelum rilis", lambda x, f=f: x[f] > 0)):
                a, b = lama[sel(lama)], baru[sel(baru)]
                if len(a) >= 30 and len(b) >= 30:
                    pa, pb = a.up60.mean(), b.up60.mean()
                    if (pa >= .58 and pb >= .58) or (pa <= .42 and pb <= .42):
                        best.append(f"   ✔ {lab} ({f}): naik LAMA {pa * 100:.0f}% | BARU {pb * 100:.0f}%")
                        keep.append((ev, f + lab, 0, pa, pb, len(a), len(b)))
        # logistik walk-forward
        preds = []
        for y in range(2015, 2026):
            tr, te = g[g.time.dt.year < y], g[g.time.dt.year == y]
            if len(tr) < 30 or te.empty or tr.up60.nunique() < 2:
                continue
            mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
            mdl = LogisticRegression(C=0.3, max_iter=500).fit((tr[FEATS] - mu) / sd, tr.up60)
            preds.append(te.assign(p=mdl.predict_proba((te[FEATS] - mu) / sd)[:, 1]))
        if preds:
            pr = pd.concat(preds)
            conf = pr[(pr.p >= .6) | (pr.p <= .4)]
            hit = ((conf.p >= .5) == (conf.up60 == 1)).mean() if len(conf) else np.nan
            allhit = ((pr.p >= .5) == (pr.up60 == 1)).mean()
            pv = binomtest(int(((pr.p >= .5) == (pr.up60 == 1)).sum()), len(pr), 0.5, alternative="greater").pvalue
            L.append(f"   model walk-forward 2015–2025: tebakan benar {allhit * 100:.0f}% (n {len(pr)}, p {pv:.2f}) | "
                     f"saat yakin (p≥60%/≤40%): {hit * 100 if len(conf) else float('nan'):.0f}% (n {len(conf)})")
        L += best or ["   tidak ada aturan yang konsisten di dua periode"]
    L += ["", f"## Ringkasan: {len(keep)} aturan konsisten dari ±{df.event.nunique() * 12} yang dicoba "
          f"(≈ {df.event.nunique() * 12 * 0.05:.0f} diharapkan muncul karena kebetulan)."]
    for k in keep:
        L.append(f"   {k[0]} | {k[1]} {k[2]:+.0f} | LAMA {k[3] * 100:.0f}% (n {k[5]}) | BARU {k[4] * 100:.0f}% (n {k[6]})")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
