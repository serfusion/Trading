"""Gabungan kandidat terbaik dari 63 repo dengan resep bot (python -m research.combine2).

Satu-satunya strategi baru yang positif di >= 3 dari 4 periode adalah Keltner breakout H1 samw2591 versi
sederhana (SL/TP ATR, tanpa trailing ketat & stop waktu 3 jam). Diuji sebagai "set ke-4" di samping
A-ensemble Donchian (40/15, 55/20, 80/30). Tiap set memakai risiko yang sama (1 unit per trade).
Varian dipilih SEBELUM melihat hasil gabungan: parameter default repo (KC 1,2 ATR, ADX 18, SL 4,5, TP 8).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .combine import ensemble
from .data import resample
from .github_popular2 import keltner
from .harness import periods


def chrono(frames: list[pd.DataFrame]) -> pd.DataFrame:
    t = pd.concat([f[["time", "exit", "R"]] for f in frames if len(f)], ignore_index=True)
    return t.sort_values("exit", kind="stable").reset_index(drop=True)


def summary(t: pd.DataFrame) -> dict:
    r = t.R.to_numpy()
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(r) else 0.0
    return {"n": len(r), "win": (r > 0).mean() * 100 if len(r) else 0, "sum": r.sum(), "dd": dd,
            "ratio": r.sum() / -dd if dd < 0 else np.inf}


def main():
    ps = periods()
    res = {"A (3 set Donchian)": [], "Keltner saja": [], "A + Keltner (4 set)": []}
    corr = []
    for p in ps:
        H = resample(p.base, "60min")
        a = ensemble(H, p.spread).assign(R=lambda x: x.R * 3)  # kembali ke 1 unit per set
        k = keltner(p, live=False)
        res["A (3 set Donchian)"].append((p.name, chrono([a])))
        res["Keltner saja"].append((p.name, chrono([k])))
        res["A + Keltner (4 set)"].append((p.name, chrono([a, k])))
        ma = a.groupby(a.exit.dt.tz_localize(None).dt.to_period("M")).R.sum()
        mk = k.groupby(k.exit.dt.tz_localize(None).dt.to_period("M")).R.sum()
        j = pd.concat([ma, mk], axis=1).fillna(0)
        corr.append((p.name, j.corr().iloc[0, 1]))
    print("Korelasi hasil bulanan Donchian vs Keltner:", ", ".join(f"{n} {c:+.2f}" for n, c in corr))
    for name, items in res.items():
        print(name)
        tot, worst = 0.0, 0.0
        for pname, t in items:
            s = summary(t)
            tot += s["sum"]
            worst = min(worst, s["dd"])
            print(f"   {pname}: n={s['n']:4d} win={s['win']:4.1f}% total={s['sum']:+7.1f} unit DD={s['dd']:+6.1f} "
                  f"hasil/DD={s['ratio']:.2f}")
        print(f"   total {tot:+.1f} unit, DD terburuk {worst:+.1f}, hasil/DD {tot / -worst:.2f}, "
              f"periode positif {sum(summary(t)['sum'] > 0 for _, t in items)}/4")


if __name__ == "__main__":
    main()
