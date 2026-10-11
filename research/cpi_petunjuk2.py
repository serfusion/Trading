"""🎯 CPI putaran 2: petunjuk BARU untuk menebak arah kejutan CPI (Act vs konsensus), diuji mundur 2010–2025.

python -m research.cpi_petunjuk2          → docs/eksternal/hasil_cpi_petunjuk2.txt

Permintaan pengguna 11 Okt 2026: "cari lagi petunjuk yang menaikkan persentase CPI, yang terpenting akurat, cek mundur".
Sudah diuji sebelumnya (cpi_gabung, sumber_lain): nowcast Cleveland, Kalshi, kejutan bulan lalu, bensin, WTI, breakeven,
yield 2 th, harga dibayar Fed daerah, UMich. Putaran ini HANYA petunjuk baru; aturan tanda ditetapkan sebelum melihat hasil,
semua petunjuk sudah terbit SEBELUM rilis (tanpa look-ahead):
  PPI   kejutan PPI (judul sama: headline→CPI, core→core) yang rilis ≤ 10 hari SEBELUM CPI bulan yang sama
  AHE   kejutan upah per jam (NFP) bulan ini (≤ 14 hari sebelum CPI) → core/headline searah
  MUS   musiman: tanda rata-rata kejutan bulan kalender yang sama di tahun-tahun SEBELUMNYA (≥ 3 tahun)
  KON   konsensus < angka bulan lalu → kejutan NAIK (analis berlebihan menebak mean reversion), sebaliknya turun
  YOY   konsistensi aritmetika: y/y tersirat = y/y lalu + m/m konsensus − m/m bulan yang sama tahun lalu (CPIAUCSL);
        tersirat − konsensus y/y ≥ 0,05 → tebak y/y searah (untuk m/m kebalikannya: konsensus y/y − tersirat)
  DSL   solar (GASDESW) rata-rata bulan acuan naik          JET  avtur (DJFUELUSGULF) naik     NG  gas alam (DHHNGSP) naik
Benar = tanda tebakan = tanda kejutan (rilis tanpa kejutan & petunjuk 0 tidak dihitung). LAMA < Okt 2021, BARU ≥ Okt 2021.
Lolos = > 50% di LAMA dan BARU dengan n ≥ 8 masing-masing dan p binomial gabungan < 0,05.
Keterbatasan: nilai CPIAUCSL/harga energi = revisi terakhir (revisi musiman kecil); banyak uji → satu lolos bisa kebetulan.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_gabung import binom_p
from .news_prediksi import calendar, last_before

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_petunjuk2.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
EVENTS = ["CPI m/m", "Core CPI m/m", "CPI y/y"]
PPI = {"CPI m/m": "PPI m/m", "Core CPI m/m": "Core PPI m/m", "CPI y/y": "PPI m/m"}


def energi(cal_t: pd.Timestamp, df: pd.DataFrame) -> float:
    from .sumber_lain import ubah_bulan
    d = ubah_bulan(df, cal_t)
    return float(np.sign(d)) if d == d and d != 0 else 0.0


def tabel() -> pd.DataFrame:
    from .eksternal_makro import fred
    cal = calendar()
    cpi = fred("CPIAUCSL")
    mm = cpi.value.pct_change() * 100
    yy = cpi.value.pct_change(12) * 100
    en = {k: fred(s) for k, s in (("DSL", "GASDESW"), ("JET", "DJFUELUSGULF"), ("NG", "DHHNGSP"))}
    rows = []
    for ev in EVENTS:
        g = cal[cal.event == ev].sort_values("time")
        for _, r in g.iterrows():
            t = r.time
            ref = (t - pd.DateOffset(months=1)).to_period("M").to_timestamp()
            o = {"event": ev, "t0": t, "s": r.s, "cons": r.f}
            o["PPI"] = np.nan_to_num(last_before(cal, PPI[ev], t, 10))
            o["AHE"] = np.nan_to_num(last_before(cal, "Average Hourly Earnings m/m", t, 14))
            past = g[(g.time < t - pd.Timedelta(days=200)) & (g.time.dt.month == t.month)]
            o["MUS"] = float(np.sign(past.s.mean())) if len(past) >= 3 and past.s.mean() != 0 else 0.0
            prev = g[g.time < t].tail(1)
            o["KON"] = float(np.sign(prev.a.iloc[0] - r.f)) if len(prev) and prev.a.iloc[0] != r.f else 0.0
            # konsistensi y/y vs m/m (konsensus pasangannya di rilis yang sama)
            same = cal[(cal.time - t).abs() <= pd.Timedelta(minutes=5)]
            cm = same[same.event == "CPI m/m"].f
            cy = same[same.event == "CPI y/y"].f
            p1, p12 = ref - pd.DateOffset(months=1), ref - pd.DateOffset(months=12)
            o["YOY"] = 0.0
            if len(cm) and len(cy) and p1 in yy.index and p12 in mm.index and ev != "Core CPI m/m":
                tersirat = yy[p1] + cm.iloc[0] - mm[p12]
                d = tersirat - cy.iloc[0]
                if abs(d) >= 0.05:
                    o["YOY"] = float(np.sign(d)) * (1 if ev == "CPI y/y" else -1)
            for k, df in en.items():
                o[k] = energi(t, df) if ev != "Core CPI m/m" else 0.0
            rows.append(o)
    return pd.DataFrame(rows)


def nilai(x: pd.DataFrame, col: str) -> tuple[str, bool]:
    out, ok, ks, ns = [], True, 0, 0
    for per, m in (("LAMA", x.t0 < SPLIT), ("BARU", x.t0 >= SPLIT)):
        y = x[m & (x[col] != 0) & (x.s != 0)]
        k, n = int((np.sign(y[col]) == y.s).sum()), len(y)
        ks, ns = ks + k, ns + n
        out.append(f"{per} {k}/{n} = {k / n * 100:.0f}%" if n else f"{per} n 0")
        ok &= n >= 8 and k / max(n, 1) > 0.5
    p = binom_p(ks, ns)
    ok &= p < 0.05
    return f"semua {ks}/{ns} = {ks / max(ns, 1) * 100:.0f}% (p {p:.3f}) | " + " | ".join(out), ok


def main() -> None:
    df = tabel()
    L = ["# 🎯 CPI putaran 2 — petunjuk baru, uji mundur", __doc__.split("\n\n")[1], ""]
    lolos = []
    for ev in EVENTS:
        x = df[df.event == ev]
        L.append(f"\n## {ev} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})")
        for col in ("PPI", "AHE", "MUS", "KON", "YOY", "DSL", "JET", "NG"):
            if (x[col] != 0).sum() == 0:
                continue
            s, ok = nilai(x, col)
            L.append(f"   {col:4s} {s}{'  ✅ LOLOS' if ok else ''}")
            if ok:
                lolos.append((ev, col))
    L.append("\nLolos: " + (", ".join(f"{e} ← {c}" for e, c in lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
