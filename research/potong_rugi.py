"""Apakah sinyal 💰 hanya berlaku beberapa jam, dan setelah turun separuh jalan ke SL tidak akan naik lagi?

python -m research.potong_rugi      # -> docs/eksternal/hasil_potong_rugi.txt

Pertanyaan pengguna (2 Okt 2026, BTC BUY 86.628 → 85.796 ≈ −0,54R): "apakah sinyal simbol uang hanyalah sementara,
hanya berlaku beberapa jam? Setelah turun setengahnya dia tidak akan ke atas lagi, alhasil ke bawah."

Mesin = cloud (research/sl_tangga.backtest: 3 set Donchian H1, SL 3xATR, kategori 💰, skema F: 5 posisi, #1 TP1 1R,
4 jalan sampai TUTUP, SL+ entry+0,1R setelah TP1). Aturan uji (ditetapkan sebelum melihat hasil):
A. Kondisional pada skema bawaan: dari sinyal yang SEMPAT rugi >= x R sebelum TP1 (x = 0,3 / 0,5 / 0,7), berapa %
   yang akhirnya kena TP1, kena SL, dan rata-rata R akhirnya — dibanding langsung potong di −x R (yang = −x R
   sebelum biaya keluar). Bila rata-rata R akhir > −x, menahan LEBIH BAIK daripada memotong.
B. Waktu: kapan TP1 kena (jam setelah entry); sinyal yang belum TP1 setelah N jam (N = 4, 8, 12, 24, 48, 96) — sisa
   rata-rata R bila ditahan (dibanding tutup di harga saat itu tidak bisa dihitung tanpa close; dipakai varian C).
C. Uji nyata (mesin penuh, set bisa masuk lagi lebih cepat): potong −0,5R / −0,7R sebelum TP1; batas waktu 12 / 24 /
   48 jam bila TP1 belum kena (semua, atau hanya bila sedang rugi). Lebih baik bila rata-rata R > bawaan di latih DAN
   uji dan >= 60% tahun lebih baik.
LAMA/BARU = latih/uji research/eksternal.SPLIT (XAU 2019, BTC 2021). Hasil dalam R (1R = jarak SL awal).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import MONEY, SPLIT, asset
from .filters import features
from .gap_study import week_info
from .sl_tangga import backtest, summary
from .strategy_lab2 import STAR, signals, trend_states

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_potong_rugi.txt"
BASE = dict(tps=[1.0, None, None, None, None])
VARIANTS = {"bawaan (TP1 + 4 jalan sampai TUTUP)": {},
            "potong semua di −0,5R sebelum TP1": {"cut_at": 0.5},
            "potong semua di −0,7R sebelum TP1": {"cut_at": 0.7},
            "batas 12 jam bila TP1 belum kena": {"time_stop": 12},
            "batas 24 jam bila TP1 belum kena": {"time_stop": 24},
            "batas 48 jam bila TP1 belum kena": {"time_stop": 48},
            "batas 24 jam, hanya bila sedang rugi": {"time_stop": 24, "time_stop_loss": True},
            "batas 48 jam, hanya bila sedang rugi": {"time_stop": 48, "time_stop_loss": True}}


def run(name: str, extra: dict, rec: list | None = None) -> pd.DataFrame:
    a = asset(name)
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    money = MONEY[name]

    def allow(i, d):
        if name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return cat in money
    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest(b, li, si, lo, so, allow, **BASE, **extra, rec=rec)
    return pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "max_r"])


def conditional(rec: pd.DataFrame, split: pd.Timestamp) -> list[str]:
    L = []
    for x in (0.3, 0.5, 0.7, 0.9):
        g = rec[rec.mae >= x]
        if not len(g):
            continue
        cells = []
        for lab, k in (("semua", g), ("LAMA", g[g.t < split]), ("BARU", g[g.t >= split])):
            if len(k):
                cells.append(f"{lab} n={len(k):4} TP1 {k.tp1.mean() * 100:4.1f}% | SL {(k.why == 'SL').mean() * 100:4.1f}% | "
                             f"rata R akhir {k.R.mean():+.3f}")
        L.append(f"  sempat rugi >= {x:.1f}R ({len(g) / len(rec) * 100:4.1f}% sinyal): " + " || ".join(cells)
                 + f"  → potong di −{x:.1f}R = {-x:+.2f}R: {'MENAHAN lebih baik' if g.R.mean() > -x else 'MEMOTONG lebih baik'}")
    return L


def timing(rec: pd.DataFrame) -> list[str]:
    L = []
    tp = rec[rec.tp1]
    q = tp.k_tp1 + 1
    L.append(f"  TP1 kena di {len(tp)}/{len(rec)} sinyal ({len(tp) / len(rec) * 100:.1f}%); jam sampai TP1: median "
             f"{q.median():.0f}, 75% dalam {q.quantile(.75):.0f} jam, 90% dalam {q.quantile(.9):.0f} jam")
    for hrs in (4, 8, 12, 24, 48, 96):
        alive = rec[(rec.bars + 1 > hrs) & ~((rec.k_tp1.notna()) & (rec.k_tp1 + 1 <= hrs))]
        if not len(alive):
            continue
        L.append(f"  belum TP1 & masih terbuka setelah {hrs:3d} jam: n={len(alive):4} → akhirnya TP1 "
                 f"{alive.tp1.mean() * 100:4.1f}%, rata R akhir {alive.R.mean():+.3f}")
    h = rec[rec.k_half.notna()]
    if len(h):
        L.append(f"  −0,5R pertama tersentuh: median {h.k_half.median() + 1:.0f} jam setelah entry (n={len(h)})")
    return L


def report() -> str:
    L = ["# Sinyal 💰: potong rugi & batas waktu (research/potong_rugi.py)", ""]
    for name in ("BTCUSD", "XAUUSD"):
        split = SPLIT[name]
        rec: list = []
        base = run(name, {}, rec)
        r = pd.DataFrame(rec)
        L.append(f"== {name}: {len(base)} sinyal 💰 ({base.t.min():%Y-%m}..{base.t.max():%Y-%m}); LAMA < {split:%Y} ==")
        L.append("A. Setelah sempat rugi (sebelum TP1), apa yang terjadi bila ditahan:")
        L += conditional(r, split)
        L.append("B. Waktu:")
        L += timing(r)
        L.append("C. Uji nyata (R per sinyal = rata-rata 5 posisi):")
        L.append(f"  {'skema':40} {'n':>5} {'WR':>6} {'R/sinyal':>9} {'total':>8} {'DD':>7} {'LAMA':>7} {'BARU':>7} tahun+ | vs bawaan")
        b = summary(base, split)
        for vname, v in VARIANTS.items():
            df = base if not v else run(name, v)
            s = summary(df, split)
            better = (s["yr"] - b["yr"]).reindex(b["yr"].index).fillna(0)
            cmp = "" if not v else f"lebih baik {int((better > 0).sum())}/{len(better)} th"
            L.append(f"  {vname:40} {s['n']:5d} {s['wr']:5.1f}% {s['avg']:+9.3f} {s['tot']:+8.1f} {s['dd']:+7.1f} "
                     f"{s['latih']:+7.3f} {s['uji']:+7.3f} {s['tahun']:>6} | {cmp}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
