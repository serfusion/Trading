"""Emas setelah NFP: naik di menit awal, lalu berbalik dalam beberapa jam? python -m research.nfp_berbalik

Pertanyaan pengguna (2 Okt 2026, NFP 29K vs perkiraan 89K, pengangguran 4,2% vs 4,1%, upah 0,1% vs 0,3%): "persentase
bullish tinggi, hasil news juga bullish, kenapa sekarang turun?" — XAU 4.182 -> +$40 dalam 2 menit -> puncak 4.226
(33 menit) -> 4.140 (3 jam kemudian). Di sini: XAU M15 (research/event_stats.xau_m15) dari open candle rilis ke
close 15 menit / 1 / 3 / 6 jam, per arah kejutan NFP (kalender ForexFactory 2012-2025), LAMA (< Okt 2021) & BARU.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .event_stats import xau_m15
from .news_detik import NEW
from .news_prediksi import calendar

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_nfp_berbalik.txt"


def table() -> pd.DataFrame:
    m = xau_m15()
    idx = m.index
    cal = calendar()
    rows = []
    for r in cal[cal.event == "Non-Farm Employment Change"].itertuples():
        t = pd.Timestamp(r.time)
        k = idx.searchsorted(t)
        if k >= len(idx) or idx[k] != t:
            continue
        o = m.open.iloc[k]

        def at(minutes: int) -> float:
            j = idx.searchsorted(t + pd.Timedelta(minutes=minutes)) - 1
            return float(m.close.iloc[j] - o) if 0 <= j < len(idx) and idx[j] >= t else np.nan
        rows.append({"time": t, "s": r.s, **{f"p{x}": at(x) for x in (15, 60, 180, 360)}})
    return pd.DataFrame(rows)


def report() -> str:
    d = table()
    L = ["# Emas setelah NFP: menit awal vs beberapa jam (research/nfp_berbalik.py)", ""]
    for s, lab in ((-1, "NFP di BAWAH perkiraan (emas diharapkan naik)"), (1, "NFP di ATAS perkiraan (emas diharapkan turun)")):
        g = d[d.s == s]
        up = 1 if s < 0 else -1
        for name, x in (("semua", g), ("LAMA < Okt 2021", g[g.time < NEW]), ("BARU", g[g.time >= NEW])):
            ok = [(np.sign(x[f"p{h}"]) == up).mean() * 100 for h in (15, 60, 180, 360)]
            first = np.sign(x.p15) == up
            back = (first & (np.sign(x.p180) == -up)).sum()
            L.append(f"{lab} | {name:15} n={len(x):3} searah: 15 mnt {ok[0]:3.0f}% • 1 jam {ok[1]:3.0f}% • 3 jam "
                     f"{ok[2]:3.0f}% • 6 jam {ok[3]:3.0f}% | searah di 15 mnt lalu melewati harga awal ke arah "
                     f"sebaliknya dalam 3 jam: {back}/{int(first.sum())}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
