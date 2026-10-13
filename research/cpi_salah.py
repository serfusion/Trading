"""🔍 Kenapa tebakan CPI → emas detik 1–2 salah? Bedah rilis Jun & Sep 2026 + uji perbaikan — python -m research.cpi_salah

Permintaan pengguna 13 Okt 2026: "telusuri, uji validitas, pastikan mengapa 2 lainnya bisa salah … yang penting pasca
release detik 1–2 benar". Memakai tabel & aturan research.cpi_detik (IDX|K, tutup kertas `tetap`), target detik 1 dan 2
(juga 2–10 sebagai pembanding). Tulis docs/eksternal/hasil_cpi_salah.txt.
1) Komponen mana yang menggerakkan emas (kejutan core vs headline vs y/y, bila angka SUDAH diketahui = plafon).
2) Ketepatan petunjuk menebak kejutan core; ketersediaan petunjuk per tahun.
3) Rilis 12 bulan terakhir per detik; tebakan NAIK vs TURUN per periode.
4) Kandidat: lewati tebakan TURUN saat emas tren naik (close kemarin > rata-rata N hari, N 50/100/200, atau return 60
   hari > 0) — tutup kertas + uji "buang acak" (p) di detik 2. Ditemukan SETELAH melihat kesalahan → kandidat.
5) Kandidat lain yang diuji: Kalshi core diutamakan / suara / lewati bila Kalshi berlawanan.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_salah.txt"


def tren_emas(df: pd.DataFrame) -> pd.DataFrame:
    from .eksternal import asset
    from .xau_kripto import _ohlc
    x = _ohlc(asset("XAUUSD").b.df)
    d = x[x.high > x.low].close.resample("D").last().dropna()

    def sebelum(t):
        return d[d.index < t.normalize()]                  # hanya hari SEBELUM tanggal rilis (tanpa look-ahead)
    for n in (50, 100, 200):
        df[f"T{n}"] = [0 if len(s := sebelum(t)) < n else (1 if s.iloc[-1] > s.iloc[-n:].mean() else -1) for t in df.t0]
    df["R60"] = [0 if len(s := sebelum(t)) < 61 else float(np.sign(s.iloc[-1] / s.iloc[-61] - 1)) for t in df.t0]
    return df


PER = (("semua", lambda d: d.th >= C.MULAI), ("LAMA", lambda d: (d.th >= C.MULAI) & (d.t0 < "2021-10-01")),
       ("BARU", lambda d: d.t0 >= "2021-10-01"), ("2024+", lambda d: d.th >= 2024))
HS = (((1,), "dtk1"), ((2,), "dtk2"), (C.JAUH, "2–10"))


def baris(df: pd.DataFrame, tb: pd.Series, hs) -> str:
    out = []
    for p, f in PER:
        m = f(df)
        k, n = C.tepat(df[m], tb[m], hs)
        out.append(f"{p} {k / n * 100:4.0f}% ({k}/{n})" if n else f"{p} –")
    return " | ".join(out)


def tutup(df: pd.DataFrame, sig) -> pd.Series:
    """Sama dengan cpi_detik.tetap untuk sinyal bebas: dipakai tahun Y bila ketepatan 2–10 dtk s/d Y−1 > 50%."""
    em = -pd.Series(np.asarray(sig, dtype=float), index=df.index)
    out = pd.Series(0.0, index=df.index)
    for th in range(C.MULAI, int(df.th.max()) + 1):
        k, n = C.tepat(df[df.th < th], em[df.th < th])
        if n >= 10 * len(C.JAUH) and k / n > 0.5:
            out[df.th == th] = em[df.th == th]
    return out


def tanda(g, t) -> str:
    if t == 0:
        return "–"
    if g != g or g == 0:
        return "·"
    return "✅" if np.sign(g) == t else "❌"


def main() -> None:
    df = tren_emas(C.turunan(C.tabel()))
    df = df[df.th >= C.MULAI].copy()
    L = ["# 🔍 Bedah kesalahan CPI → emas detik 1–2 (research/cpi_salah.py)", __doc__.split("\n\n")[1], ""]

    L.append("## 1. Bila kejutan SUDAH diketahui (plafon): emas berlawanan dengan komponen mana?")
    plafon = {"core (core ≠ 0)": -df.s_core, "headline m/m": -df.s_mm, "y/y": -df.s_yy,
              "core ≠ 0 & headline sesuai": pd.Series(np.where((df.s_core != 0) & (df.s_mm == 0), -df.s_core, 0), df.index),
              "headline ≠ 0 & core sesuai": pd.Series(np.where((df.s_core == 0) & (df.s_mm != 0), -df.s_mm, 0), df.index),
              "core dulu, lalu headline": pd.Series(-np.where(df.s_core != 0, df.s_core, df.s_mm), df.index),
              "core di BAWAH → emas naik": pd.Series(np.where(df.s_core < 0, 1, 0), df.index),
              "core di ATAS → emas turun": pd.Series(np.where(df.s_core > 0, -1, 0), df.index)}
    for nama, s in plafon.items():
        for hs, hn in HS:
            L.append(f"   {nama:28s} {hn:4s}| {baris(df, s, hs)}")
    for hs, hn in HS[:2]:
        L.append(f"   {'selalu NAIK':28s} {hn:4s}| {baris(df, pd.Series(1.0, index=df.index), hs)}")
    for h in (1, 2, 3):
        L.append(f"   median |gerak emas| detik {h} (2024+): ${df[df.th >= 2024][f'g{h}'].abs().median():.2f}")

    L.append("\n## 2. Ketepatan petunjuk menebak KEJUTAN CORE (angka) & ketersediaan")
    for c in ("core_K", "mm_K", "IDXc", "SUARA_IDX", "P_core", "KON", "core_N"):
        out = []
        for p, f in PER:
            s = df[f(df)]
            m = (s[c] != 0) & (s.s_core != 0)
            out.append(f"{p} {(s[c] == s.s_core)[m].mean() * 100:4.0f}% n{int(m.sum())}" if m.sum() else f"{p} –")
        L.append(f"   {c:10s}: " + " | ".join(out))
    ada = df.groupby("th")[["IDXc", "IDXy", "IDXm", "mm_K", "core_K"]].apply(lambda g: (g != 0).sum())
    L.append("   rilis berpetunjuk per tahun:\n" + "\n".join("     " + x for x in ada.to_string().splitlines()))

    tb = C.tetap(df, "IDX|K")
    L.append("\n## 3. Aturan aplikasi sekarang (IDX|K), 12 bulan terakhir per detik")
    for i, r in df[df.t0 >= "2025-10-01"].iterrows():
        t = tb[i]
        L.append(f"   {r.t0:%Y-%m-%d} {('NAIK ' if t > 0 else 'TURUN') if t else 'diam '} | indeks {r.SUARA_IDX:+.0f} "
                 f"Kalshi m/m {r.mm_K:+.0f} core {r.core_K:+.0f} | dtk1 {tanda(r.g1, t)} {r.g1:+6.2f} dtk2 "
                 f"{tanda(r.g2, t)} {r.g2:+6.2f} dtk3 {r.g3:+6.2f} | kejutan m/m {r.s_mm:+.0f} core {r.s_core:+.0f} "
                 f"y/y {r.s_yy:+.0f} | tren200 {'naik' if r.T200 > 0 else 'turun'}")
    for arah, nm in ((1, "tebak NAIK"), (-1, "tebak TURUN")):
        s = tb.where(tb == arah, 0)
        for hs, hn in HS:
            L.append(f"   {nm:12s} {hn:4s}| {baris(df, s, hs)}")

    L.append("\n## 4. Kandidat: lewati tebakan TURUN saat emas tren naik (tutup kertas)")
    base = df["IDX|K"].astype(float)
    for hs, hn in HS:
        L.append(f"   {'IDX|K sekarang':34s} {hn:4s}| {baris(df, tutup(df, base), hs)}")
    for tr in ("T50", "T100", "T200", "R60"):
        s = tutup(df, np.where((base > 0) & (df[tr] > 0), 0, base))
        for hs, hn in HS:
            L.append(f"   {'[' + tr + '] TURUN dilewati':34s} {hn:4s}| {baris(df, s, hs)}")
    new = pd.Series(np.where((tb < 0) & (df.T200 > 0), 0, tb), index=df.index)
    rng = np.random.default_rng(1)
    for nm, f in PER[1:]:
        m = f(df)
        g, t, nv = np.sign(df.g2[m].fillna(0)), tb[m], new[m]
        ok, keep = (t != 0) & (g != 0), (nv != 0) & (g != 0)
        if not keep.sum():
            continue
        obs, kk = (g[keep] == nv[keep]).mean(), int(keep.sum())
        hit, idx = (g.values == t.values), np.where(ok)[0]
        sims = np.array([hit[rng.choice(idx, kk, replace=False)].mean() for _ in range(5000)])
        L.append(f"   [T200] {nm}: detik 2 {obs * 100:.0f}% (n {kk}) vs membuang tebakan secara acak {sims.mean() * 100:.0f}% "
                 f"→ p {(sims >= obs).mean():.3f}")
    L.append("   per tahun detik 2 (sekarang → [T200]): " + " ".join(
        f"{th}:{C.tepat(df[df.th == th], tb[df.th == th], (2,))[0]}/{C.tepat(df[df.th == th], tb[df.th == th], (2,))[1]}"
        f"→{C.tepat(df[df.th == th], new[df.th == th], (2,))[0]}/{C.tepat(df[df.th == th], new[df.th == th], (2,))[1]}"
        for th in range(2016, int(df.th.max()) + 1)))

    L.append("\n## 5. Kandidat lain (tutup kertas)")
    lain = {"Kalshi core saja": df.core_K,
            "Kalshi core → IDX|K": np.where(df.core_K != 0, df.core_K, base),
            "suara 2·Kcore + Km/m + indeks": np.sign(2 * df.core_K + df.mm_K + df.SUARA_IDX),
            "lewati bila Kalshi core berlawanan": np.where((df.core_K != 0) & (df.core_K != base), 0, base),
            "lewati bila Kalshi m/m berlawanan": np.where((df.mm_K != 0) & (df.mm_K != base), 0, base)}
    for nama, s in lain.items():
        tb2 = tutup(df, s)
        for hs, hn in HS[:2]:
            L.append(f"   {nama:34s} {hn:4s}| {baris(df, tb2, hs)}")
    m = (tb > 0) & (df.core_K > 0)
    L.append("   tebak NAIK saat Kalshi core condong di ATAS (konflik, seperti 14 Okt): " + ", ".join(
        f"detik {h} {C.tepat(df[m], tb[m], (h,))[0]}/{C.tepat(df[m], tb[m], (h,))[1]}" for h in (1, 2)))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
