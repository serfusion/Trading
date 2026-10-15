"""🌙 PPI 15 Okt 2026 — semua petunjuk sebelum rilis, per ARAH tebakan, + jalur setelah rilis (⚡LIVE detik 2).

python -m research.ppi_malam        → docs/eksternal/hasil_ppi_malam.txt

Permintaan pengguna 15 Okt 2026: "aplikasi stuck TURUN 74% … cari semua informasi, riset, uji validitas, semua metode untuk PPI
malam ini, saya mau angka pasti 85% ke atas". Data: research/riset_ppi3 (fitur.parquet: target tick ASLI Exness lonjakan menit 1
& detik 1–60, petunjuk pra-registrasi putaran 2–3) + research/pra_xau_semua (tren emas sebelum rilis H4/H24, gerak detik 2 $)
+ tick Exness XAUUSDc (simulasi masuk SETELAH melihat detik 2). Semua angka = rilis PPI 2016–2026, LAMA < Okt 2021.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_ppi_malam.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
TARGET = ("arah", "d2", "d5", "d10")
# malam ini (15 Okt 2026): minyak Sep +17,5% (WTI=+1, energi=+1), CPI inti 0,3 vs 0,2 (CPIC=+1), CPI m/m sesuai (CPIH=0),
# core PPI Agu 0,2 < konsensus core 0,3 (KONC=−1), sebelumnya 0,4 < konsensus 0,6 (KONV=−1), kejutan PPI Agu 0 (P=0),
# bersamaan Retail Sales, konsensus headline − core +0,3, emas 4 jam +$21 & 24 jam +$9 (OKX XAUT 09:00 UTC)
MALAM = dict(WTI=1, E_KOMB=1, CPIC=1, CPIH=0, KONC=-1, KONV=-1, M_EN=-1, P=0, dgn_retail=1, gap=0.3, H4=1, H24=1)


def data() -> pd.DataFrame:
    f = pd.read_parquet(EKS / "riset_ppi3" / "fitur.parquet")
    f["t0"] = pd.to_datetime(f.t0, utc=True)
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s = s[s.grup.astype(str).str.contains("PPI")].copy()
    s["t0"] = pd.to_datetime(s.t0, utc=True)
    x = f.merge(s.drop_duplicates("t0")[["t0", "H4", "H24", "y2_XAU_EXNESS"]], on="t0", how="left")
    x = x[x.t0.dt.year >= 2016].reset_index(drop=True)
    x["gap"] = x.cm - x.cf
    return x


def akurasi(x: pd.DataFrame, m: pd.Series, tebak: int) -> str:
    isi = []
    for t in TARGET:
        y = x[t]
        ok = m & y.notna() & (y != 0)
        if not ok.any():
            continue
        f = lambda q: f"{(y[q] == tebak).mean() * 100:.0f}%({int(q.sum())})" if q.any() else "–"  # noqa: E731
        isi.append(f"{'lonjakan' if t == 'arah' else t} {f(ok)} L{f(ok & (x.t0 < SPLIT))} B{f(ok & (x.t0 >= SPLIT))}")
    return " | ".join(isi)


def sebelum(x: pd.DataFrame, L: list) -> None:
    L.append("\n## A. Petunjuk SEBELUM rilis yang berlaku malam ini (per arah tebakan; L = LAMA, B = BARU)")
    for nm, m, tb in (
            ("selalu NAIK (pembanding)", pd.Series(True, index=x.index), 1),
            ("minyak naik ≥5% → TURUN", x.WTI == 1, -1),
            ("minyak naik & CPI inti di atas → TURUN (dulu tampil 74%)", (x.WTI == 1) & (x.CPIC == 1), -1),
            ("minyak naik & bersamaan Retail → TURUN", (x.WTI == 1) & x.dgn_retail, -1),
            ("minyak naik & konsensus sudah naik (gap ≥ 0,2) → TURUN [pasca-lihat]", (x.WTI == 1) & (x.gap >= 0.2), -1),
            ("minyak naik & tren 24 jam naik → TURUN", (x.WTI == 1) & (x.H24 > 0), -1),
            ("tren 24 jam naik → NAIK", x.H24 > 0, 1),
            ("tren 4 jam naik → NAIK", x.H4 > 0, 1),
            ("core lalu < konsensus core (KONC) → NAIK", x.KONC == -1, 1),
            ("sebelumnya < konsensus (KONV) → NAIK", x.KONV == -1, 1)):
        L.append(f"   {nm:70s} {akurasi(x, m, tb)}")


def model(x: pd.DataFrame, L: list) -> None:
    from sklearn.linear_model import LogisticRegression
    feat = list(MALAM)
    X = x[feat].astype(float).fillna(0).to_numpy()
    for c in ("H4", "H24"):
        X[:, feat.index(c)] = np.sign(X[:, feat.index(c)])
    y, th = x.arah.fillna(0).to_numpy(), x.t0.dt.year.to_numpy()
    pr = np.full(len(x), np.nan)
    for yr in sorted(set(th)):
        m = (th < yr) & (y != 0)
        if m.sum() >= 30:
            pr[th == yr] = LogisticRegression(C=0.5, max_iter=500).fit(X[m], (y[m] > 0).astype(int)).predict_proba(
                X[th == yr])[:, 1]
    ok = ~np.isnan(pr) & (y != 0)
    g = np.where(pr >= 0.5, 1, -1)
    lr = LogisticRegression(C=0.5, max_iter=500).fit(X[y != 0], (y[y != 0] > 0).astype(int))
    p = lr.predict_proba(np.array([[MALAM[f] for f in feat]], float))[0, 1]
    L.append(f"\n## B. Model gabungan {len(feat)} petunjuk (logistik, tutup kertas per tahun): benar {(g[ok] == y[ok]).mean() * 100:.0f}% "
             f"(n {int(ok.sum())}) ≈ lempar koin • malam ini P(emas naik menit 1) {p * 100:.0f}%")


def setelah(x: pd.DataFrame, L: list) -> None:
    L.append("\n## C. SETELAH rilis: arah emas detik 2 (≥ $X) masih sama di detik 5 / 10 / lonjakan menit 1")
    y2 = x.y2_XAU_EXNESS
    for amb in (0.5, 1.0, 2.0):
        isi = []
        for t in ("d5", "d10", "arah"):
            ok = (y2.abs() >= amb) & x[t].notna() & (x[t] != 0)
            b = ok & (x.t0 >= SPLIT)
            isi.append(f"{t} {(np.sign(y2[ok]) == x[t][ok]).mean() * 100:.0f}% ({int(ok.sum())}; BARU "
                       f"{(np.sign(y2[b]) == x[t][b]).mean() * 100:.0f}%)")
        L.append(f"   detik 2 ≥ ${amb}: " + " | ".join(isi))
    m = (y2.abs() >= 0.5) & (x.WTI == 1)
    for nm, q, tb in (("turun (searah tebakan minyak)", m & (y2 < 0), -1), ("naik (melawan tebakan)", m & (y2 > 0), 1)):
        ok = q & x.arah.notna()
        L.append(f"   minyak naik & detik 2 {nm}: lonjakan searah detik 2 {(x.arah[ok] == tb).mean() * 100:.0f}% "
                 f"(n {int(ok.sum())})")


def kejar(x: pd.DataFrame, L: list) -> None:
    """Masuk SETELAH melihat detik 2 (telat 0,5 / 1,5 dtk), bid/ask asli Exness, tutup detik 5–60 → untung/rugi $/oz."""
    from .exness import ticks_around
    rows = []
    for t0 in x.t0:
        tk = ticks_around("XAUUSDc", t0)
        if tk is None or not len(tk):
            continue
        s = (tk.index - t0).total_seconds().to_numpy()
        bid, ask = tk.bid.to_numpy(), tk.ask.to_numpy()
        mid = (bid + ask) / 2

        def at(sec, arr):
            i = np.searchsorted(s, sec, side="right") - 1
            return arr[i] if i >= 0 and sec - s[i] < 30 else np.nan
        m0, m2 = at(-1, mid), at(2, mid)
        if np.isnan(m0) or np.isnan(m2):
            continue
        a = np.sign(m2 - m0)
        for lat in (2.5, 3.5):
            e = at(lat, ask) if a > 0 else at(lat, bid)
            for ex in (5, 10, 30, 60):
                c = at(ex, bid) if a > 0 else at(ex, ask)
                rows.append({"t0": t0, "mv": m2 - m0, "lat": lat, "ex": ex, "pl": (c - e) * a})
    r = pd.DataFrame(rows).dropna()
    L.append(f"\n## D. KEJAR: masuk setelah melihat detik 2 (tick Exness, {r.t0.nunique()} rilis) — untung % rilis, rata-rata $/oz")
    for amb in (0.5, 1.0, 2.0):
        for lat in (2.5, 3.5):
            isi = []
            for ex in (5, 10, 30, 60):
                g = r[(r.mv.abs() >= amb) & (r.lat == lat) & (r.ex == ex)]
                isi.append(f"tutup {ex}s {100 * (g.pl > 0).mean():.0f}% ${g.pl.mean():+.2f}")
            L.append(f"   detik 2 ≥ ${amb}, masuk detik {lat} (n {int(((r.mv.abs() >= amb) & (r.lat == lat) & (r.ex == 5)).sum())}): "
                     + " | ".join(isi))


def main() -> None:
    x = data()
    L = ["# 🌙 PPI 15 Okt 2026 (research/ppi_malam.py)", __doc__.split("\n\n")[1],
         f"rilis PPI 2016–2026: {len(x)} • malam ini: {MALAM}"]
    sebelum(x, L)
    model(x, L)
    setelah(x, L)
    kejar(x, L)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
