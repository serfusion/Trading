"""Model "peluang emas naik 1 jam" SEBELUM rilis NFP, JOLTS, Fed → cloud/api/prarilis.json — python -m research.prarilis

Izin pengguna 6 Okt 2026 ("pasang info sebelum news NFP, JOLTS & Fed"). Fitur yang bisa dihitung cloud secara live:
prev_s (rilis lalu di atas/bawah konsensus), exp_up (konsensus vs angka lalu), g4/g24 (gerak emas 4/24 jam sebelum
rilis), gema (emas di atas EMA ±20 hari). Regresi logistik; akurasi dilaporkan walk-forward per tahun 2015–2025.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression

from .news_semua import SPLIT, build

OUT = Path(__file__).resolve().parent.parent / "cloud" / "api" / "prarilis.json"
FEATS = ["prev_s", "exp_up", "g4", "g24", "gema"]
EVENTS = {"Non-Farm Employment Change": "NFP", "JOLTS Job Openings": "JOLTS", "Federal Funds Rate": "Fed"}


def main() -> None:
    df = build()
    out = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "fitur": FEATS, "model": {}}
    for ev, key in EVENTS.items():
        g = df[df.event == ev].sort_values("time")
        preds = []
        for y in range(2015, 2026):
            tr, te = g[g.time.dt.year < y], g[g.time.dt.year == y]
            if len(tr) < 30 or te.empty:
                continue
            mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
            m = LogisticRegression(C=0.3, max_iter=500).fit((tr[FEATS] - mu) / sd, tr.up60)
            preds.append(te.assign(p=m.predict_proba((te[FEATS] - mu) / sd)[:, 1]))
        pr = pd.concat(preds)
        ok = (pr.p >= .5) == (pr.up60 == 1)
        lama, baru = ok[pr.time < SPLIT], ok[pr.time >= SPLIT]
        mu, sd = g[FEATS].mean(), g[FEATS].std().replace(0, 1)
        m = LogisticRegression(C=0.3, max_iter=500).fit((g[FEATS] - mu) / sd, g.up60)
        out["model"][key] = {"judul": ev, "mean": mu.round(6).tolist(), "std": sd.round(6).tolist(),
                             "coef": m.coef_[0].round(6).tolist(), "intercept": round(float(m.intercept_[0]), 6),
                             "uji": {"n": int(len(pr)), "benar": round(float(ok.mean()) * 100, 1),
                                     "lama": round(float(lama.mean()) * 100, 1), "n_lama": int(len(lama)),
                                     "baru": round(float(baru.mean()) * 100, 1), "n_baru": int(len(baru)),
                                     "dasar_naik": round(float(g.up60.mean()) * 100, 1)}}
        print(key, out["model"][key]["uji"], dict(zip(FEATS, m.coef_[0].round(2))))
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
