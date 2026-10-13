"""💥 Strategi modal kecil (masuk t−1 dtk, lot maks) untuk SEMUA berita sesuai urutan rilis → hasil_berita_allin.txt

python -m research.berita_allin

Permintaan pengguna 13 Okt 2026: "lanjutkan setelahnya yaitu PPI kemudian FOMC, NFP, dll sesuai urutan release". Cara SAMA
dengan CPI (research/cpi_allin2.py): tick ASLI Exness XAUUSDc, modal $100/rilis (rugi maks = modal), masuk tick terakhir
≤ t0 − 1 dtk, tutup detik 2 atau LENTUR (detik 2 rugi → tutup, untung → tahan s/d detik 10), leverage 1:200 & 1:500,
pembanding ARAH ACAK (lempar koin per rilis, 5.000×) pada rilis yang sama, LAMA (< Okt 2021) & BARU.

Petunjuk (semua sudah ada di riset lama, terbit sebelum rilis):
  research/berita_detik.tabel  NFP/ADP/PPI/RETAIL/PCE/ISM/GDP/JOLTS/CLAIMS/KONSUMEN: P, P3, KON, + khusus (ADP, KLAIM, ISME,
                               KAL, KALUR, CPI, MOBIL, CPIC, PPIC, KALPCE, CHI, FED, SPG, NOW, IND, KONT, SPX, BENSIN), SUARA
  research/pra_lain.fitur      FOMC: Y2, AKSI, DOT, PRA2, T24, LALU • PPI: PP, DXY, WTI • PCE: NOW, CPIC • JOLTS: NFP, ADP, IND
  NAIK                         selalu BUY (pembanding)
TUTUP KERTAS + ARAH DIPELAJARI: di tahun Y aturan dipakai bila ketepatan detik 2–10 tahun-tahun sebelumnya (≥ 10 rilis)
> 55% (searah) atau < 45% (dibalik); selain itu tidak menebak. Lolos "seperti CPI" = BARU rata-rata > 0 dan > acak (p < 0,05),
n BARU ≥ 15; lolos PENUH = juga LAMA > 0.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_allin2 import SPLIT, arr, sim_keluar
from .exness import ticks_around

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_berita_allin.txt"
URUT = ["PPI", "RETAIL", "FOMC", "PCE", "JOLTS", "NFP", "ADP", "ISM", "GDP", "CLAIMS", "KONSUMEN"]
H = (2, 3, 5, 10)


def gerak() -> pd.DataFrame:
    v = pd.read_parquet(ROOT / "data" / "research" / "eksternal" / "pra_xau_semua_v2.parquet")
    out = v[["t0", "grup"]].copy()
    for h in (1, 2, 3, 5, 10):
        out[f"g{h}"] = v[f"y{h}_XAU_EXNESS"].fillna(v[f"y{h}_XAU"])
    return out


def aturan() -> pd.DataFrame:
    """Baris per rilis: t0, grup, kolom petunjuk dalam ARAH EMAS (+1 naik)."""
    from .berita_detik import ATURAN, tabel
    from .pra_lain import FITUR, fitur
    bd = tabel()
    rows = []
    for g, cols in ATURAN.items():
        x = bd[bd.grup == g].copy()
        for c in cols:
            if c not in x:
                x[c] = 0.0
        khusus = [c for c in cols if c not in ("P", "P3", "KON")]
        x["SUARA"] = np.sign(x[khusus + ["P"]].fillna(0).sum(axis=1))
        keep = {c: -x[c].fillna(0.0) for c in cols + ["SUARA"]}             # arah USD → emas kebalikannya
        rows.append(pd.DataFrame({"t0": x.t0, "grup": g, **{f"bd_{c}": v for c, v in keep.items()}}))
    a = pd.concat(rows, ignore_index=True)
    pl = fitur()
    pl = pl[["t0", "grup"] + sorted({c for cs in FITUR.values() for c in cs})]
    pl = pl.rename(columns={c: f"pl_{c}" for c in pl.columns if c not in ("t0", "grup")})
    a = a.merge(pl, on=["t0", "grup"], how="outer")
    a["NAIK"] = 1.0
    return a


def tetap_arah(x: pd.DataFrame, col: str) -> pd.Series:
    out = pd.Series(0.0, index=x.index)
    th = x.t0.dt.year
    for y in sorted(th.unique()):
        lalu = x[th < y]
        k = n = 0
        for h in H:
            g = np.sign(lalu[f"g{h}"].fillna(0))
            m = (lalu[col] != 0) & (g != 0)
            k += int((np.sign(lalu[col][m]) == g[m]).sum())
            n += int(m.sum())
        if n >= 10 * len(H):
            r = k / n
            if r > 0.55:
                out[th == y] = np.sign(x[col][th == y])
            elif r < 0.45:
                out[th == y] = -np.sign(x[col][th == y])
    return out


def akurasi(x: pd.DataFrame, tb: pd.Series, hs) -> tuple[float, int]:
    k = n = 0
    for h in hs:
        g = np.sign(x[f"g{h}"].fillna(0))
        m = (tb != 0) & (g != 0)
        k += int((tb[m] == g[m]).sum())
        n += int(m.sum())
    return (k / n * 100 if n else np.nan), n // len(hs)


def main() -> None:
    a = aturan().merge(gerak(), on=["t0", "grup"], how="left")
    a = a[a.t0 >= "2013-01-01"].sort_values("t0").reset_index(drop=True)
    A = {}
    for i, r in a.iterrows():
        tk = ticks_around("XAUUSDc", r.t0)
        if tk is not None:
            A[i] = arr(tk, r.t0)
    rng = np.random.default_rng(11)
    L = ["# 💥 Strategi modal kecil untuk semua berita (research/berita_allin.py)", __doc__.split("\n\n")[1], "",
         f"Rilis: {len(a)} (tick Exness {len(A)})"]
    lolos = []
    for g in URUT:
        x = a[a.grup == g]
        if x.empty:
            continue
        cols = [c for c in x.columns if c.startswith(("bd_", "pl_")) and x[c].fillna(0).abs().sum() > 0] + ["NAIK"]
        L.append(f"\n## {g} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m}; tick Exness {sum(i in A for i in x.index)})")
        for c in cols:
            x = x.copy()
            x[c] = x[c].fillna(0.0)
            tb = x[c] if c == "NAIK" else tetap_arah(x, c)
            d2, n2 = akurasi(x, tb, (2,))
            d1, _ = akurasi(x, tb, (1,))
            if n2 < 10:
                continue
            baris = [f"   {c:10s} arah detik 1 {d1:3.0f}% detik 2 {d2:3.0f}% (n {n2})"]
            for kel, lev in ((2, 200), (("lentur", 10), 200), (("lentur", 10), 500)):
                rec = []
                for i in x.index:
                    gg = int(np.sign(tb[i]))
                    if not gg or i not in A:
                        continue
                    o, ob, os_ = sim_keluar(A[i], gg, kel, lev), sim_keluar(A[i], 1, kel, lev), sim_keluar(A[i], -1, kel, lev)
                    if o and ob and os_:
                        rec.append((a.t0[i], o[0], o[1], ob[0], os_[0]))
                if not rec:
                    continue
                y = pd.DataFrame(rec, columns=["t0", "pl", "mc", "buy", "sell"])
                b, lm = y[y.t0 >= SPLIT], y[y.t0 < SPLIT]
                if len(b) >= 5:
                    koin = rng.integers(0, 2, size=(5000, len(b)))
                    ac = np.where(koin == 1, b.buy.to_numpy(), b.sell.to_numpy()).mean(axis=1)
                    p = float((ac >= b.pl.mean()).mean())
                else:
                    ac, p = np.array([np.nan]), np.nan
                nama = "d2" if kel == 2 else "lentur"
                lm_txt = f"lama n{len(lm)} ${lm.pl.mean():+6.1f}" if len(lm) else "lama –"
                baris.append(f"      {nama:6s} 1:{lev} | baru n{len(b)} untung {(b.pl > 0).mean() * 100 if len(b) else 0:3.0f}% "
                             f"${b.pl.mean() if len(b) else 0:+6.1f} (acak ${np.mean(ac):+6.1f}, p {p:.2f}) habis "
                             f"{int(b.mc.sum())} | {lm_txt}")
                if c != "NAIK" and len(b) >= 15 and b.pl.mean() > 0 and p < 0.05:
                    tag = "PENUH" if len(lm) >= 10 and lm.pl.mean() > 0 else "seperti CPI"
                    lolos.append(f"{g} {c} {nama} 1:{lev} ({tag}; baru ${b.pl.mean():+.1f} vs acak ${np.mean(ac):+.1f}, "
                                 f"p {p:.2f}; lama {lm_txt})")
            L += baris
    L.append("\n## LOLOS (BARU > 0, > acak p < 0,05, n ≥ 15)")
    L += [f"   {s}" for s in lolos] or ["   TIDAK ADA"]
    L.append(f"   (jumlah uji ±{sum(1 for s in L if s.startswith('      '))}; bila semua acak, ±5% lolos karena kebetulan)")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
