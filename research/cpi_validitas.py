"""🔬 Uji validitas temuan CPI 1–10 detik (research/cpi_detik): apakah 64% / 71% bisa dipercaya atau kebetulan?

python -m research.cpi_validitas          → docs/eksternal/hasil_cpi_validitas.txt

Permintaan pengguna 11 Okt 2026: "setelah menemukan persentase tinggi yang dapat dipercaya validitasnya, uji juga news
lainnya". Uji di sini (target sama: arah emas detik 2/3/5/10, tutup kertas):
  1  PERMUTASI KELUARGA: hasil emas diacak antar rilis (petunjuk tetap) 2.000×; tiap acakan dihitung ketepatan TERBAIK dari
     SEMUA aturan yang diuji di cpi_detik (bukan hanya pemenang) → p = peluang kebetulan menghasilkan "pemenang" setinggi
     yang ditemukan. Ini mengoreksi masalah "banyak uji".
  2  PERMUTASI DALAM TAHUN: petunjuk diacak hanya di dalam tahun yang sama (menjaga kecenderungan emas naik per tahun).
  3  KEPEKAAN AMBANG indeks (0,01 / 0,02 / 0,03 / 0,05) — temuan rapuh bila hanya bagus di satu ambang.
  4  FEED terpisah: tick Exness saja vs Dukascopy saja.
  5  SETENGAH-SETENGAH: rilis ganjil vs genap (bukan pemilihan tahun).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .cpi_detik import DET, JAUH, per_periode, tepat, tetap, turunan

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_validitas.txt"
UTAMA = ("IDX|K", "SUARA_IDX", "mm_K")
N_PERM = 2000


def hit_mentah(clue: np.ndarray, G: np.ndarray, m: np.ndarray) -> float:
    """Ketepatan tebakan −clue terhadap tanda gerak G (baris × jangka) pada baris m."""
    c = -clue[m][:, None]
    g = G[m]
    ok = (c != 0) & (g != 0)
    return float((np.sign(g)[ok] == np.broadcast_to(c, g.shape)[ok]).mean()) if ok.any() else np.nan


def main() -> None:
    from . import cpi_detik as cd
    df = turunan(cd.tabel())
    semua = cd.PETUNJUK + list(cd.TURUNAN) + ["SUARA", "SUARA_IDX", "IDX|K", "K|IDX"]
    G = df[[f"g{h}" for h in JAUH]].fillna(0).to_numpy()
    b22 = (df.th >= 2022).to_numpy()
    s16 = (df.th >= 2016).to_numpy()
    L = ["# 🔬 Validitas temuan CPI 1–10 detik", __doc__.split("\n\n")[1], ""]
    obs = {c: (hit_mentah(df[c].to_numpy(), G, s16), hit_mentah(df[c].to_numpy(), G, b22)) for c in semua}
    L.append("## Ketepatan mentah (tanpa saringan tahun lalu) 2–10 dtk: 2016–2026 | 2022+")
    for c in UTAMA:
        L.append(f"   {c:10s} {obs[c][0] * 100:5.1f}% | {obs[c][1] * 100:5.1f}%")
    # 1 permutasi keluarga
    rng = np.random.default_rng(7)
    C = {c: df[c].to_numpy() for c in semua}
    maks16, maks22 = [], []
    for _ in range(N_PERM):
        idx = rng.permutation(len(df))
        Gp = G[idx]
        h16 = [hit_mentah(C[c], Gp, s16) for c in semua]
        h22 = [hit_mentah(C[c], Gp, b22) for c in semua]
        maks16.append(np.nanmax(h16))
        maks22.append(np.nanmax(h22))
    maks16, maks22 = np.array(maks16), np.array(maks22)
    L.append(f"\n## 1 Permutasi keluarga ({len(semua)} aturan, {N_PERM}× acak hasil emas)")
    L.append(f"   acak: aturan TERBAIK rata-rata {maks16.mean() * 100:.1f}% (2016+), {maks22.mean() * 100:.1f}% (2022+); "
             f"persentil 95: {np.percentile(maks16, 95) * 100:.1f}% / {np.percentile(maks22, 95) * 100:.1f}%")
    for c in UTAMA:
        p16 = float((maks16 >= obs[c][0]).mean())
        p22 = float((maks22 >= obs[c][1]).mean())
        L.append(f"   {c:10s} {obs[c][0] * 100:.1f}% → p {p16:.3f} | 2022+ {obs[c][1] * 100:.1f}% → p {p22:.3f}")
    # 1b keluarga terbatas: hanya aturan dengan cukup rilis (≥ 40 rilis 2016+ & ≥ 20 rilis 2022+) — aturan dengan 4–15
    #    rilis memberi angka ekstrem karena kebetulan dan tidak akan dipilih untuk dipakai
    def rilis(c, m):
        return int(((df[c] != 0) & m).sum())
    cukup = [c for c in semua if rilis(c, s16) >= 40 and rilis(c, b22) >= 20]
    m16b, m22b = [], []
    rng2 = np.random.default_rng(11)
    for _ in range(N_PERM):
        Gp = G[rng2.permutation(len(df))]
        m16b.append(np.nanmax([hit_mentah(C[c], Gp, s16) for c in cukup]))
        m22b.append(np.nanmax([hit_mentah(C[c], Gp, b22) for c in cukup]))
    m16b, m22b = np.array(m16b), np.array(m22b)
    L.append(f"\n## 1b Permutasi keluarga terbatas ({len(cukup)} aturan dengan ≥ 40 rilis 2016+ & ≥ 20 rilis 2022+)")
    L.append("   aturan: " + ", ".join(cukup))
    L.append(f"   acak: terbaik rata-rata {m16b.mean() * 100:.1f}% / {m22b.mean() * 100:.1f}%; persentil 95 "
             f"{np.percentile(m16b, 95) * 100:.1f}% / {np.percentile(m22b, 95) * 100:.1f}%")
    for c in UTAMA:
        if c in cukup:
            L.append(f"   {c:10s} p 2016+ {(m16b >= obs[c][0]).mean():.3f} | p 2022+ {(m22b >= obs[c][1]).mean():.3f}")
    # 2 permutasi dalam tahun (aturan tunggal)
    L.append(f"\n## 2 Permutasi petunjuk di dalam tahun yang sama ({N_PERM}×, aturan tunggal)")
    th = df.th.to_numpy()
    for c in UTAMA:
        x = df[c].to_numpy().copy()
        hasil16, hasil22 = [], []
        for _ in range(N_PERM):
            y = x.copy()
            for t in np.unique(th):
                i = np.where(th == t)[0]
                y[i] = y[rng.permutation(i)]
            hasil16.append(hit_mentah(y, G, s16))
            hasil22.append(hit_mentah(y, G, b22))
        L.append(f"   {c:10s} p 2016+ {np.mean(np.array(hasil16) >= obs[c][0]):.3f} | p 2022+ "
                 f"{np.mean(np.array(hasil22) >= obs[c][1]):.3f} (acak rata {np.nanmean(hasil16) * 100:.1f}% / "
                 f"{np.nanmean(hasil22) * 100:.1f}%)")
    # 3 kepekaan ambang
    L.append("\n## 3 Kepekaan ambang indeks (tutup kertas, 2–10 dtk)")
    for a in (0.01, 0.02, 0.03, 0.05):
        d = df.copy()
        for k in ("IDXc", "IDXy", "IDXm"):
            d[k] = [cd.sgn(v, a) for v in d[f"d_{k}"]]
        d = turunan(d)
        for c in ("SUARA_IDX", "IDX|K"):
            L.append(f"   ambang {a:.2f} {c:10s} {per_periode(d, tetap(d, c))}")
    # 4 feed terpisah
    L.append("\n## 4 Feed terpisah (IDX|K tutup kertas, 2–10 dtk)")
    tb = tetap(df, "IDX|K")
    for feed, nama in (("ex", "Exness"), ("du", "Dukascopy")):
        d = df.copy()
        for h in DET:
            d[f"g{h}"] = d[f"{feed}{h}"]
        L.append(f"   {nama:9s} {per_periode(d, tb)}")
    # 5 ganjil/genap
    L.append("\n## 5 Rilis ganjil vs genap (IDX|K tutup kertas, 2–10 dtk)")
    for nama, m in (("ganjil", df.index % 2 == 1), ("genap", df.index % 2 == 0)):
        k, n = tepat(df[m], tb[m])
        k2, n2 = tepat(df[m & (df.th >= 2022)], tb[m & (df.th >= 2022)])
        L.append(f"   {nama:6s} semua {k}/{n} = {k / max(n, 1) * 100:.1f}% | 2022+ {k2}/{n2} = {k2 / max(n2, 1) * 100:.1f}%")
    import json
    j = cd.JSON
    if j.exists():
        d = json.loads(j.read_text(encoding="utf-8"))
        d["validitas"] = {"p_keluarga_2016": round(float((m16b >= obs["IDX|K"][0]).mean()), 3),
                          "p_keluarga_2022": round(float((m22b >= obs["IDX|K"][1]).mean()), 3),
                          "aturan_keluarga": len(cukup), "feed_dukascopy_2022": None}
        d2 = df.copy()
        for h in DET:
            d2[f"g{h}"] = d2[f"du{h}"]
        k, n = tepat(d2[d2.th >= 2022], tb[d2.th >= 2022])
        d["validitas"]["feed_dukascopy_2022"] = round(k / n * 100, 1) if n else None
        j.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
