"""📄 Uji "tutup kertas" (walk-forward murni) untuk tebakan arah emas sebelum CPI.

python -m research.tutup_kertas           → docs/eksternal/hasil_tutup_kertas.txt

Permintaan pengguna 11 Okt 2026: "56% turun itu diuji mundur tahun ke tahun seolah belum tahu hasilnya — jawaban ditutup
kertas, tebak dulu, baru dibuka. Apakah semua tertebak, atau ada yang salah?"
Cara: untuk setiap tahun Y, hanya rilis SEBELUM tahun Y yang boleh dilihat. Dari situ dihitung (1) persen yang akan
tampil di aplikasi = ketepatan aturan s/d akhir tahun Y−1, (2) apakah aturan masih dipakai (ketepatan lalu > 50%; bila
tidak, aplikasi seharusnya "≈ 50:50, tidak menebak"). Lalu tiap rilis di tahun Y ditebak, kemudian "kertas dibuka":
arah harga tengah XAU t0−1 dtk → t0+1 / 2 / 5 / 10 dtk / +1 mnt (tick Exness, cadangan Dukascopy). Rilis yang harganya
tidak bergerak = "diam" (tidak dihitung benar/salah).
Aturan yang diuji:
  WTI   aturan yang SEKARANG tampil di aplikasi ("CPI ▼ TURUN 56% • dasar: minyak WTI"): rata-rata WTI bulan acuan naik
        → CPI di atas → emas TURUN; WTI turun → emas NAIK (berlaku juga 2026, tidak butuh konsensus)
  YOY|P aturan baru (docs/CPI_EMAS.md): konsistensi y/y vs m/m, cadangan kejutan y/y lalu (butuh konsensus FF, s.d. 2025-10)
  BUY   pembanding: selalu tebak emas NAIK
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_tutup_kertas.txt"
EKS = ROOT / "data" / "research" / "eksternal"
JANGKA = {"1 dtk": "g1", "2 dtk": "g2", "5 dtk": "g5", "10 dtk": "g10", "1 mnt": "g60"}
MULAI = 2012                                    # tahun pertama yang ditebak (butuh ≥ 2 tahun riwayat)


def data() -> pd.DataFrame:
    from .cpi_emas import tabel
    from .eksternal_makro import fred
    from .sumber_lain import ubah_bulan
    df = tabel()
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    v = v[v.grup == "CPI"][["t0"] + [f"y{h}_{f}" for h in (1, 2, 5) for f in ("XAU_EXNESS", "XAU")]]
    df = df.merge(v, on="t0", how="left")
    for h in (1, 2, 5):
        df[f"g{h}"] = df[f"y{h}_XAU_EXNESS"].fillna(df[f"y{h}_XAU"])
    df["g10"], df["g60"] = df.m10, df.m60
    wti = fred("DCOILWTICO")
    d = np.array([ubah_bulan(wti, t) for t in df.t0])
    df["wti_ubah"] = d
    df["WTI"] = -np.sign(np.nan_to_num(d))                    # arah EMAS yang ditebak
    df["YOY|P"] = -df["yy_YOY|P"]
    df["BUY"] = 1.0
    df["th"] = df.t0.dt.year
    return df


def jalan(df: pd.DataFrame, aturan: str, g: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per tahun: persen tampil (dari tahun lalu), dipakai?, benar/salah tahun itu. Per rilis: tebakan vs hasil."""
    th_rows, rilis = [], []
    for th in range(MULAI, int(df.th.max()) + 1):
        lalu = df[(df.th < th) & (df[aturan] != 0) & df[g].notna() & (df[g] != 0)]
        k_l, n_l = int((np.sign(lalu[g]) == lalu[aturan]).sum()), len(lalu)
        tampil = k_l / n_l * 100 if n_l else np.nan
        dipakai = n_l >= 10 and tampil > 50
        ini = df[(df.th == th) & (df[aturan] != 0)]
        if ini.empty:
            continue
        gerak = ini[g]
        hasil = np.sign(gerak.fillna(0))
        benar = (hasil == ini[aturan]) & (hasil != 0)
        salah = (hasil == -ini[aturan]) & (hasil != 0)
        th_rows.append({"tahun": th, "tampil": tampil, "n_lalu": n_l, "dipakai": dipakai, "tebak": len(ini),
                        "benar": int(benar.sum()), "salah": int(salah.sum()), "diam": int((hasil == 0).sum())})
        for (_, r), b, s in zip(ini.iterrows(), benar, salah):
            rilis.append({"t0": r.t0, "tebak": "NAIK" if r[aturan] > 0 else "TURUN", "gerak": r[g],
                          "hasil": "✅" if b else ("❌" if s else "· diam"), "tampil": tampil, "dipakai": dipakai,
                          "wti": r.wti_ubah})
    return pd.DataFrame(th_rows), pd.DataFrame(rilis)


def main() -> None:
    df = data()
    L = ["# 📄 Uji tutup kertas: tebakan arah emas sebelum CPI, tahun demi tahun", __doc__.split("\n\n")[1], ""]
    ringkas = []
    for aturan in ("WTI", "YOY|P", "BUY"):
        for jn, g in JANGKA.items():
            t, r = jalan(df, aturan, g)
            if t.empty:
                continue
            L.append(f"\n## Aturan {aturan} — emas {jn}")
            L.append("   tahun | persen tampil (dari data s/d tahun lalu) | tebakan | benar | salah | diam | % benar tahun itu")
            for _, x in t.iterrows():
                n = x.benar + x.salah
                L.append(f"   {x.tahun} | {x.tampil:5.1f}% (n {x.n_lalu:3d}){'' if x.dipakai else ' → TIDAK dipakai'} | "
                         f"{x.tebak:3d} | {x.benar:3d} | {x.salah:3d} | {x.diam:2d} | "
                         f"{(x.benar / n * 100 if n else float('nan')):5.1f}%")
            k, s = int(t.benar.sum()), int(t.salah.sum())
            pk = t[t.dipakai]
            kp, sp = int(pk.benar.sum()), int(pk.salah.sum())
            baru = t[t.tahun >= 2022]
            kb, sb = int(baru.benar.sum()), int(baru.salah.sum())
            L.append(f"   TOTAL {MULAI}–{t.tahun.max()}: benar {k}, salah {s} → {k / (k + s) * 100:.1f}% | hanya tahun "
                     f"'dipakai': {kp}/{kp + sp} = {kp / max(kp + sp, 1) * 100:.1f}% | 2022+: {kb}/{kb + sb} = "
                     f"{kb / max(kb + sb, 1) * 100:.1f}% | tahun ≥ 50% benar: {int(((t.benar >= t.salah)).sum())}/{len(t)}")
            ringkas.append((aturan, jn, k, s, kb, sb))
            if aturan == "WTI" and jn == "1 dtk":
                L.append("\n   Rincian per rilis 2024–2026 (aturan WTI, 1 dtk) — kertas dibuka satu per satu:")
                for _, x in r[r.t0.dt.year >= 2024].iterrows():
                    L.append(f"   {x.t0:%Y-%m-%d} WTI {x.wti:+6.2f} → tebak emas {x.tebak:5s} | gerak 1 dtk "
                             f"{x.gerak:+.2f} $ {x.hasil}")
    L.append("\n## Ringkasan (benar/salah, rilis yang harganya bergerak)")
    for a, jn, k, s, kb, sb in ringkas:
        L.append(f"   {a:6s} {jn:6s}: semua {k}/{k + s} = {k / (k + s) * 100:.1f}% | 2022+ {kb}/{kb + sb} = "
                 f"{kb / max(kb + sb, 1) * 100:.1f}%")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
