"""🏦 FOMC: petunjuk SEBELUM pengumuman → arah LONJAKAN TERBESAR emas di MENIT PERTAMA (kelompok "fomc_konsumen" workflow
11 Okt yang terputus; permintaan 13 Okt "lanjutkan PPI kemudian FOMC, NFP, dll sesuai urutan release").

python -m research.riset_fomc          → docs/eksternal/hasil_riset_fomc.txt

PRA-REGISTRASI (ditulis SEBELUM evaluasi; tanda = arah "baik untuk USD" → tebakan emas = kebalikannya; info hanya yang
terbit sebelum t0 − 1 dtk):
  Y2_BALIK  yield 2 th (FRED DGS2) naik ≥ 5 bp dalam 5 hari bursa sebelum rapat → nada keras sudah terhitung → saat pengumuman
            "jual berita": USD turun → emas NAIK (usd = −tanda). Turun ≥ 5 bp → kebalikannya.
  Y2_IKUT   kebalikan Y2_BALIK (momentum: pasar benar mengantisipasi).
  DXY_BALIK dolar luas Fed (FRED DTWEXBGS) naik ≥ 0,5% dalam 5 observasi sebelum rapat → emas NAIK saat pengumuman.
  H24_BALIK emas naik dalam 24 jam sebelum (pra_xau_semua H24, ketat) → emas TURUN saat pengumuman (drift pra-FOMC berbalik,
            Lucca & Moench 2015).
  M60_BALIK sama untuk 60 menit sebelum (M60).
  LALU_IKUT arah emas pada pengumuman FOMC sebelumnya (pra_xau_semua LALU) → searah (rezim Fed bertahan).
  DOT       rapat dengan proyeksi ekonomi/dot plot (Mar, Jun, Sep, Des) → risiko nada keras → USD naik → emas TURUN; rapat lain
            → emas NAIK.
  AKSI_JUAL aksi yang diharapkan (Nasdaq "Fed Interest Rate Decision": konsensus vs sebelumnya): pemotongan diharapkan →
            "jual berita" → emas TURUN; kenaikan diharapkan → emas NAIK; tahan → tidak menebak.
  AKSI_IKUT kebalikan AKSI_JUAL.
Tidak dipakai: Kalshi/Polymarket keputusan (riset 1 Okt: keputusan selalu sesuai konsensus 90–99% → tanpa kejutan).
Evaluasi = research/lonjakan_uji (tutup, keluarga 2.000×, baris); LOLOS sama dengan CPI/PPI: tutup kertas ≥ 60% 2016–2026,
> 50% LAMA & BARU (n ≥ 8), p keluarga < 0,05, ≥ 40 rilis ditebak sejak 2016, bisa dihitung live. Sekunder: detik 2–10.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import baris, keluarga, tutup

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_fomc.txt"
ATURAN = ["Y2_BALIK", "Y2_IKUT", "DXY_BALIK", "H24_BALIK", "M60_BALIK", "LALU_IKUT", "DOT", "AKSI_JUAL", "AKSI_IKUT"]


def tabel() -> pd.DataFrame:
    from .eksternal_makro import fred
    from .nasdaq_kalender import angka, hari
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")
    x = lj[lj.grup == "FOMC"][["t0", "arah"]].rename(columns={"arah": "L"})
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    v = v[v.grup == "FOMC"]
    for h in (1, 2, 3, 5, 10):
        v[f"g{h}"] = v[f"y{h}_XAU_EXNESS"].fillna(v[f"y{h}_XAU"])
    x = x.merge(v[["t0", "H24", "M60", "LALU"] + [f"g{h}" for h in (1, 2, 3, 5, 10)]], on="t0", how="left")
    y2, dx = fred("DGS2"), fred("DTWEXBGS")
    rows = []
    for _, r in x.iterrows():
        t = r.t0
        a = y2[y2.available < t].value
        b = dx[dx.available < t].value
        d2 = (a.iloc[-1] - a.iloc[-6]) * 100 if len(a) > 6 else np.nan
        db = (b.iloc[-1] / b.iloc[-6] - 1) * 100 if len(b) > 6 else np.nan
        ny = t.tz_convert("America/New_York").tz_localize(None).normalize()
        aksi = 0.0
        for rr in hari(ny, ambil=False):
            if rr.get("country") == "United States" and rr["eventName"] == "Fed Interest Rate Decision":
                f, p = angka(rr["consensus"]), angka(rr["previous"])
                if f == f and p == p and f != p:
                    aksi = float(np.sign(f - p))
        rows.append({"t0": t, "d2": d2, "db": db, "aksi": aksi})
    x = x.merge(pd.DataFrame(rows), on="t0", how="left")
    s2 = np.where(x.d2 >= 5, 1.0, np.where(x.d2 <= -5, -1.0, 0.0))
    sb = np.where(x.db >= 0.5, 1.0, np.where(x.db <= -0.5, -1.0, 0.0))
    x["Y2_BALIK"], x["Y2_IKUT"] = -s2, s2
    x["DXY_BALIK"] = -sb
    x["H24_BALIK"] = x.H24.fillna(0)              # emas naik sebelum → USD +1 (emas turun saat pengumuman)
    x["M60_BALIK"] = x.M60.fillna(0)
    x["LALU_IKUT"] = -x.LALU.fillna(0)
    x["DOT"] = np.where(x.t0.dt.month.isin([3, 6, 9, 12]), 1.0, -1.0)
    x["AKSI_JUAL"] = -x.aksi                      # pemotongan diharapkan (aksi −1) → USD +1 → emas turun
    x["AKSI_IKUT"] = x.aksi
    x["th"] = x.t0.dt.year
    return x.sort_values("t0").reset_index(drop=True)


def main() -> None:
    x = tabel()
    x = x[x.th >= 2013].reset_index(drop=True)
    y, th = x.L.fillna(0).to_numpy(), x.th.to_numpy()
    rng = np.random.default_rng(13)
    L = ["# 🏦 FOMC → arah lonjakan emas menit pertama (research/riset_fomc.py)", __doc__.split("\n\n")[1], "",
         f"{len(x)} pengumuman {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m}; lonjakan naik {(y > 0).sum()}/{(y != 0).sum()}; "
         f"aksi diharapkan: potong {int((x.aksi < 0).sum())}, naik {int((x.aksi > 0).sum())}, tahan {int((x.aksi == 0).sum())}",
         "   selalu NAIK  " + baris(np.ones(len(x)), y, x.t0, th)[0]]
    C = {c: x[c].fillna(0).to_numpy() for c in ATURAN}
    kel = keluarga(C, y, th, rng)
    lolos = []
    for c in ATURAN:
        tb = tutup(C[c], y, th)
        teks, r = baris(tb, y, x.t0, th)
        g2 = np.sign(x.g2.fillna(0).to_numpy())
        ok = (tb != 0) & (g2 != 0) & (th >= 2016)
        d2 = f"{(tb[ok] == g2[ok]).mean() * 100:4.0f}% ({ok.sum()})" if ok.sum() else "–"
        p = kel.get(c)
        ptxt = f"p {p[0]:.3f}/{p[1]:.3f}" if p else "p –"
        (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
        ok_all = n and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5 and p and min(p[:2]) < 0.05 \
            and n >= 40
        L.append(f"   {c:10s} {teks} | {ptxt} | detik 2 {d2}{'  ✅ LOLOS' if ok_all else ''}")
        if ok_all:
            lolos.append(c)
    L.append("\nLOLOS: " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
