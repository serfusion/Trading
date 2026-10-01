"""Reaksi emas 5 dtk & 1 menit setelah rilis, per judul berita dan per hasil (di bawah / sama / di atas konsensus).

python -m research.reaksi_menit     # -> data/research/eksternal/reaksi_menit.csv + cloud/api/reaksi.json

Dipakai "perkiraan hari H" di kartu 🎯 (cloud/api/_hari_h.py): peluang pasar prediksi (Kalshi/Polymarket) untuk tiap
hasil x seberapa sering emas naik 1 menit setelah hasil itu. Gerak = mid tick dari t0-1 dtk ke t0+5 / t0+60 dtk.
Konsensus & Act: kalender ForexFactory (research/news_prediksi.calendar(), s.d. Jan 2026). Tick: Dukascopy 2010-2026
(utama) dan Exness Cent 2015-2026 (cek). Periode LAMA (< Okt 2021) dan BARU dilaporkan.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path
from .news_detik import NEW, prepare
from .news_prediksi import EVENTS, calendar

OUT_CSV = cache_path("reaksi_menit.csv")
OUT_JSON = Path(__file__).resolve().parent.parent / "cloud" / "api" / "reaksi.json"
FEEDS = {"XAU": "duka", "XAU_EXNESS": "exness"}
HASIL = {-1.0: "bawah", 0.0: "sama", 1.0: "atas"}


def build() -> pd.DataFrame:
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS)]
    rows, ticks = [], {}
    for t in sorted(cal.time.unique()):
        for aset, lab in FEEDS.items():
            p = prepare(pd.Timestamp(t), aset)
            if p is None or p.at(-1) < 0:
                continue
            m1 = p.mid[p.at(-1)]
            ticks[(t, lab)] = (float(p.mid[p.at(5)] - m1), float(p.mid[p.at(60)] - m1))
    for r in cal.itertuples():
        row = {"time": r.time, "event": r.event, "s": r.s}
        for lab in FEEDS.values():
            g = ticks.get((r.time, lab))
            row[f"{lab}_5"], row[f"{lab}_60"] = g if g else (np.nan, np.nan)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df[df.duka_60.notna() | df.exness_60.notna()].reset_index(drop=True)


def rates(df: pd.DataFrame, before: pd.Timestamp | None = None, feed: str = "duka") -> dict:
    """{judul: {hasil: {"naik60", "naik5", "n"}}} dari rilis SEBELUM `before` (walk-forward) bila diberikan."""
    x = df if before is None else df[df.time < before]
    x = x[x[f"{feed}_60"].notna() & (x[f"{feed}_60"] != 0)]
    out = {}
    for ev, g in x.groupby("event"):
        cell = {}
        for s, lab in HASIL.items():
            k = g[g.s == s]
            if len(k) >= 5:
                kb = k[k.time >= NEW]
                cell[lab] = {"naik60": round(float((k[f"{feed}_60"] > 0).mean()), 3),
                             "naik5": round(float((k[f"{feed}_5"] > 0).mean()), 3), "n": int(len(k)),
                             "baru_naik60": round(float((kb[f"{feed}_60"] > 0).mean()), 3) if len(kb) >= 5 else None}
        if cell:
            cell["tahun"] = f"{g.time.min():%Y}–{g.time.max():%Y}"
            out[ev] = cell
    return out


def main() -> None:
    df = build()
    df.to_csv(OUT_CSV, index=False)
    out = rates(df)
    OUT_JSON.write_text(json.dumps({"dibuat": "research/reaksi_menit.py", "feed": "Dukascopy (mid t0-1 dtk -> +60 dtk)",
                                    "judul": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(df)} rilis; ditulis {OUT_CSV} dan {OUT_JSON}\n")
    for ev, c in out.items():
        cells = []
        for lab in ("bawah", "sama", "atas"):
            if lab in c:
                g = df[(df.event == ev) & (df.s == {"bawah": -1, "sama": 0, "atas": 1}[lab]) & df.duka_60.notna()]
                old, new = g[g.time < NEW], g[g.time >= NEW]
                ex = df[(df.event == ev) & (df.s == {"bawah": -1, "sama": 0, "atas": 1}[lab]) & df.exness_60.notna()]
                cells.append(f"{lab} naik1m {c[lab]['naik60'] * 100:3.0f}% (n={c[lab]['n']:3}; LAMA "
                             f"{(old.duka_60 > 0).mean() * 100:3.0f}% BARU {(new.duka_60 > 0).mean() * 100:3.0f}%; "
                             f"Exness {(ex.exness_60 > 0).mean() * 100:3.0f}%)")
        print(f"- {ev} ({c['tahun']}): " + " | ".join(cells))


if __name__ == "__main__":
    main()
