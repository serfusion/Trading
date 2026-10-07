"""🔄 Ekspor model titik balik NFP (mean reversion + pendahulu) → cloud/api/nfp_titik.json — python -m research.nfp_titik

Memakai tabel vintage dari research/nfp_mean.py (data/research/eksternal/nfp_mean.csv; jalankan `python -m
research.nfp_mean` dulu bila belum ada). Model = logistik "NFP + klaim + pengangguran + revisi + skor" (walk-forward
61%, docs/NFP_MEAN.md uji 5) dilatih ulang di SEMUA data untuk dipakai ke depan. Potret kondisi sekarang dihitung
dengan fungsi cloud yang sama (cloud/api/_nfp_titik.fitur, FRED API, butuh FRED_API_KEY) dan dicek terhadap
perhitungan pandas riset (nfp_mean.nfp_table) untuk bulan terakhir.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .eksternal import cache_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloud" / "api" / "nfp_titik.json"
FEATS = ["z24", "d1", "n_claims", "n_ur_d3", "revision", "lead"]


def walk_forward(t: pd.DataFrame) -> tuple[float, int]:
    from sklearn.linear_model import LogisticRegression
    preds = []
    for y in range(2006, 2027):
        tr = t[t.month.dt.year < y].dropna(subset=FEATS + ["up"])
        te = t[t.month.dt.year == y].dropna(subset=FEATS + ["up"])
        if len(tr) < 40 or te.empty:
            continue
        mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
        m = LogisticRegression(C=1.0, max_iter=1000).fit((tr[FEATS] - mu) / sd, tr.up)
        preds.append(te.assign(p=m.predict_proba((te[FEATS] - mu) / sd)[:, 1]))
    pr = pd.concat(preds)
    return float(((pr.p >= 0.5) == (pr.up == 1)).mean() * 100), len(pr)


def main() -> None:
    from sklearn.linear_model import LogisticRegression
    t = pd.read_csv(cache_path("nfp_mean.csv"), parse_dates=["month"])
    d = t.dropna(subset=FEATS + ["up"])
    mu, sd = d[FEATS].mean(), d[FEATS].std().replace(0, 1)
    m = LogisticRegression(C=1.0, max_iter=1000).fit((d[FEATS] - mu) / sd, d.up)
    wf, n_wf = walk_forward(t)
    det = (t.z24 <= -1.0) | ((t.d1 < 0) & (t.d1.shift(1) < 0)) | (t.d2 <= t.p20)
    grp = {}
    for lab, g in (("membaik", t.lead >= 2), ("netral", t.lead.between(-1, 1)), ("memburuk", t.lead <= -2)):
        x = t[det & g]
        grp[lab] = {"n": int(len(x)), "naik": round(float(x.up.mean() * 100))}
    obj = {"dibuat": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "model": {"fitur": FEATS, "mean": [round(float(v), 6) for v in mu], "std": [round(float(v), 6) for v in sd],
                     "coef": [round(float(v), 6) for v in m.coef_[0]], "intercept": round(float(m.intercept_[0]), 6)},
           "p20": round(float(t.d2.quantile(0.2)), 1),
           "uji": {"periode": f"{t.month.min():%Y}–{t.month.max():%Y}", "n": int(len(t)),
                   "dasar": round(float(t.up.mean() * 100)), "walk_forward": round(wf), "n_walk_forward": n_wf,
                   "kelompok": grp}}
    sys.path.insert(0, str(ROOT / "cloud" / "api"))
    OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")   # model dulu (dipakai _nfp_titik)
    import importlib

    import _nfp_titik
    importlib.reload(_nfp_titik)
    now = datetime.now(timezone.utc)
    f = _nfp_titik.fitur(os.environ["FRED_API_KEY"], now)
    f["sumber"] = "potret riset"
    obj["kondisi"] = f
    # cek: fitur NFP cloud vs riset pandas (bulan terakhir)
    from .nfp_mean import nfp_table
    rt = nfp_table()
    last = rt.iloc[-1]
    mu24, sd24 = rt.chg.iloc[-25:-1].mean(), rt.chg.iloc[-25:-1].std()
    cek = {"bulan": f"{last.month:%Y-%m}", "chg": float(last.chg), "z24": float((last.chg - mu24) / sd24),
           "revision": float(last.revision)}
    print("cloud :", {k: f[k] for k in ("bulan", "chg", "z24", "revision", "n_claims", "n_ur_d3", "n_jolts3", "lead")})
    print("riset :", cek)
    if abs(cek["chg"] - f["chg"]) > 0.5 or abs(cek["z24"] - f["z24"]) > 0.05:
        print("PERINGATAN: fitur cloud ≠ riset (cache alfred_PAYEMS mungkin lama)")
    OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    r = _nfp_titik.ringkas(f)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"walk-forward {wf:.1f}% (n {n_wf}); kelompok {grp}; dasar {obj['uji']['dasar']}%")


if __name__ == "__main__":
    main()
