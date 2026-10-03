"""Badge 💰 vs hasil sinyal yang benar-benar dikirim — python -m research.kategori_badge

Pertanyaan pengguna (3 Okt 2026): "katanya 💰/⭐ bagus dan yang minus hanya sinyal biasa, sekarang sinyal biasa malah
profit dan 💰⭐ konf tidak untung?" Dua cara hitung dibandingkan dengan mesin yang sama (sl_tangga.backtest, skema
bawaan TP1 1R + 4 jalan):

A  semua sinyal dikirim lalu diberi label kategori. Inilah dasar angka badge (`cloud/api/_core.STATS`).
B  hanya kategori 💰 yang dikirim (seperti cloud & aplikasi). Slot set yang tidak terisi sinyal biasa/⭐ bisa terisi
   sinyal 💰 tambahan, jadi hasil per kategori bisa berbeda dari A.
Varian B: bawaan, tanpa "konf", dan "semua kategori". Periode LAMA (< Okt 2021) / BARU / 2026.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import MONEY, asset
from .filters import features
from .gap_study import week_info
from .sl_tangga import backtest
from .strategy_lab2 import STAR, signals, trend_states

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_kategori_badge.txt"
SPLIT = "2021-10-01"
ALL = ("konf+⭐", "konf", "⭐", "biasa")
VARIANTS = {"XAUUSD": [MONEY["XAUUSD"], ("konf+⭐",), ALL],
            "BTCUSD": [MONEY["BTCUSD"], ("konf+⭐", "⭐"), ALL]}


def go(name: str, allowed: tuple | None) -> pd.DataFrame:
    b = asset(name).b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    cats = {}

    def allow(i, d):
        if name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        c = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        cats[b.t[i + 1]] = c
        return allowed is None or c in allowed
    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest(b, li, si, lo, so, allow, tps=[1.0, None, None, None, None])
    df = pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r"])
    df["cat"] = df.t.map(cats)
    return df


def st(g: pd.DataFrame) -> str:
    if len(g) == 0:
        return "-"
    eq = np.cumsum(g.sort_values("t_out").R.to_numpy())
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    return f"n{len(g)} WR {(g.R > 0).mean() * 100:.0f}% {g.R.mean():+.3f}R/sin total {g.R.sum():+.0f}R DD {dd:.0f}"


def periods(df: pd.DataFrame, L: list) -> None:
    for per, w in (("LAMA", df[df.t < SPLIT]), ("BARU", df[df.t >= SPLIT]), ("2026", df[df.t >= "2026-01-01"])):
        L.append(f"   {per}: semua {st(w)}")
        for c, g in w.groupby("cat"):
            L.append(f"         {c:8} {st(g)}")
    yr = df[df.t >= SPLIT].groupby(df.t.dt.year).R.sum().round(0).astype(int).to_dict()
    L.append(f"   total R per tahun BARU: {yr}")


def report() -> str:
    L = ["# Badge 💰 vs sinyal yang dikirim (research/kategori_badge.py)", ""]
    for name, vs in VARIANTS.items():
        a = go(name, None)
        L.append(f"== {name} (data s.d. {a.t.max():%Y-%m-%d}) ==")
        L.append(" A: semua sinyal diberi label (dasar badge)")
        periods(a, L)
        for v in vs:
            m = go(name, v)
            L.append(f" B: hanya {' + '.join(v)} dikirim" + (" (bawaan cloud)" if v == MONEY[name] else ""))
            periods(m, L)
            if v == MONEY[name]:
                for c in v:
                    ta = set(a[a.cat == c].t)
                    g = m[m.cat == c]
                    extra = g[~g.t.isin(ta)]
                    L.append(f"   {c}: sinyal tambahan yang hanya muncul di B: {st(extra)}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
