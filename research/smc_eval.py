"""Evaluasi hasil scan SMC: python -m research.smc_eval <dataset> <scan.pkl> [YYYY-MM-DD pemisah]"""
import sys

import numpy as np
import pandas as pd

from research.run_scan import dataset
from research.simulate import simulate, simulate_plan, stats

name, path = sys.argv[1], sys.argv[2]
df, _, _, spread, _ = dataset(name)
sc = pd.read_pickle(path)
cut = df.index.searchsorted(pd.Timestamp(sys.argv[3], tz="UTC")) if len(sys.argv) > 3 else int(len(df) * 0.6)
parts = {"sebelum": sc[sc.t < cut], "sesudah": sc[sc.t >= cut]}
plans = {
    "default bot (TP1 likuiditas + BE + TP2)": None,
    "T1 1R semua": dict(t1_r=1.0, partial=1.0),
    "T1 1R + BE + T2 3R": dict(t1_r=1.0, t2_r=3.0, partial=0.5),
    "T1 2R semua": dict(t1_r=2.0, partial=1.0),
}
print(f"{name}: {len(df)} candle, {len(sc)} setup, pemisah {df.index[min(cut, len(df) - 1)]:%Y-%m-%d}")
for label, plan in plans.items():
    out = []
    for k, sub in parts.items():
        r = simulate(sub, df, spread, "split") if plan is None else simulate_plan(sub, df, spread, **plan)
        s = stats(r)
        out.append(f"{k}: n={s['trades']} win={s['win%']}% exp={s['expR']:+.3f}R PF={s['PF']}")
    print(f"{label:42s} | " + " | ".join(out))
c = df.close.to_numpy()
for k in [1, 3, 12]:
    ok = [np.sign(c[t + k] - c[t]) == d for t, d in zip(sc.t, sc.dir) if t + k < len(c) and c[t + k] != c[t]]
    print(f"arah sinyal benar setelah {k} candle: {np.mean(ok) * 100:.1f}% (n={len(ok)})")
