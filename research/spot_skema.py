"""💎 Skema keluar spot: cukup 1 TP (+3%) atau bertahap seperti XAU (sebagian di TP, sisanya dibiarkan)?

python -m research.spot_skema            → docs/eksternal/hasil_spot_skema.txt

Pertanyaan pengguna 10 Okt 2026: "untuk spot apakah cukup close / TP saja? Tidak seperti sinyal XAU membuka 5 entry
menutup 1 sisanya biarkan?" Sinyal sama dengan cloud (research/spot_peluang gabungan, 20 koin, walk-forward), entry di
open hari berikut, candle harian (urutan dalam hari tidak diketahui → bila TP2 dan batas waktu sama-sama mungkin, TP
yang tersentuh dihitung). Biaya 0,30% pulang-pergi per bagian. Hasil = % per sinyal (rata-rata bagian berbobot).
Skema:
  sekarang  100% jual di +3% (limit) atau close hari ke-10
  50/50 +6  50% di +3%, 50% di +6% atau close hari ke-10
  50/50 hold 50% di +3%, 50% ditahan sampai close hari ke-10 (atau +10%)
  1/5       20% di +3% (seperti 1 dari 5 posisi XAU), 80% di +6% atau close hari ke-20
  trail     50% di +3%, 50% jual saat close harian turun di bawah low 3 hari terakhir (maks 20 hari)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .spot_dip import SPLIT

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_skema.txt"
COST = 0.003


def jalur(d: pd.DataFrame, t: pd.Timestamp, hari: int) -> pd.DataFrame:
    return d[(d.index >= t)].iloc[:hari]


def bagian_tp(seg: pd.DataFrame, e: float, tp: float | None, hari: int) -> float:
    """Return satu bagian: limit di +tp (bila tersentuh dalam `hari`), selain itu close hari terakhir."""
    s = seg.iloc[:hari]
    if s.empty:
        return np.nan
    if tp is not None:
        hit = s.high.to_numpy() >= e * (1 + tp)
        if hit.any():
            k = int(np.argmax(hit))
            px = max(s.open.iloc[k], e * (1 + tp)) if k > 0 else e * (1 + tp)
            return px / e - 1 - COST
    return s.close.iloc[-1] / e - 1 - COST


def bagian_trail(seg: pd.DataFrame, e: float, hari: int = 20, n: int = 3) -> float:
    s = seg.iloc[:hari]
    c, lo = s.close.to_numpy(), s.low.to_numpy()
    for k in range(n, len(s)):
        if c[k] < lo[k - n:k].min():
            return c[k] / e - 1 - COST
    return c[-1] / e - 1 - COST if len(c) else np.nan


def main() -> None:
    from .batal_guncang import spot_trades
    from .spot_dip2 import segments
    tr, _ = spot_trades()
    harian = {}
    rows = []
    for x in tr.itertuples():
        base = x.coin.split("#")[0]
        if base not in harian:
            segs = segments(base)
            harian[base] = pd.concat(segs) if segs else None
        d = harian[base]
        if d is None:
            continue
        seg = jalur(d, pd.Timestamp(x.t), 20)
        e = float(x.e)
        if len(seg) < 2:
            continue
        a = bagian_tp(seg, e, 0.03, 10)
        rows.append({"t": pd.Timestamp(x.t), "coin": base,
                     "sekarang": a,
                     "50/50 +6": 0.5 * a + 0.5 * bagian_tp(seg, e, 0.06, 10),
                     "50/50 hold": 0.5 * a + 0.5 * bagian_tp(seg, e, 0.10, 10),
                     "1/5": 0.2 * a + 0.8 * bagian_tp(seg, e, 0.06, 20),
                     "trail": 0.5 * a + 0.5 * bagian_trail(seg, e)})
    df = pd.DataFrame(rows).dropna()
    L = ["# 💎 Skema keluar spot (sinyal cloud gabungan, % per sinyal setelah biaya)", __doc__.split("\n\n")[1], ""]
    for k in ("sekarang", "50/50 +6", "50/50 hold", "1/5", "trail"):
        parts = []
        for per, m in (("LAMA", df.t < SPLIT), ("BARU", df.t >= SPLIT)):
            x = df.loc[m, k] * 100
            parts.append(f"{per} n {len(x)} untung {(x > 0).mean() * 100:.0f}% rata {x.mean():+.2f}% "
                         f"rugi rata {x[x <= 0].mean():+.1f}% terburuk {x.min():+.0f}%")
        th = (df.groupby(df.t.dt.year)[k].mean() * 100).round(1)
        L.append(f"{k:11s} | " + " | ".join(parts) + " | per tahun " + " ".join(f"{y}:{v:+.1f}" for y, v in th.items()))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
