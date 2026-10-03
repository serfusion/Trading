"""Sensitivitas grid + filter tenang & lindung & akhir pekan (36 pengaturan) — python -m research.tenang_sensitif"""
import numpy as np, pandas as pd, itertools
from .martingale_ea import load, SPLIT
from .tenang import kalender, masker, bulan_sim
df = load(); ev = kalender(); ten, tut, _ = masker(df, ev)
izin, tutup = np.where(ten, 1, 0).tolist(), tut.tolist()
rows = []
for mult, lot, step, tp in itertools.product((2.0, 1.5, 1.2), (0.01, 0.02), (4.0, 5.0, 6.0), (1.9, 3.0)):
    v = (f"x{mult} {lot} jarak {step} tp {tp}", 1, lot, mult, step, tp, 40, 40000.0, mult != 2.0, 45)
    m = bulan_sim(df, v, izin, tutup, True)
    L, B = m[m.t < SPLIT], m[m.t >= SPLIT]
    tB = B.usd.mean() / B.usd.std(ddof=1) * np.sqrt(len(B))
    yrs = m.groupby(m.t.dt.year).usd.sum()
    rows.append(dict(cfg=v[0], L=L.usd.mean(), B=B.usd.mean(), tB=tB, habis=m.habis.mean(), th_pos=(yrs > 0).mean(), r12=m[m.t >= pd.Timestamp("2025-10-01", tz="UTC")].usd.mean()))
r = pd.DataFrame(rows).sort_values("B", ascending=False)
txt = r.round(2).to_string(index=False) + f"\npositif LAMA & BARU: {int(((r.L > 0) & (r.B > 0)).sum())} dari {len(r)}"
print(txt)
from pathlib import Path
(Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_tenang_sensitif.txt").write_text(txt + "\n")
