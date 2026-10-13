"""🔎 Sumber CPI yang belum pernah diuji (13 Okt 2026, pertanyaan "yakin tidak ada yang terlewat?") → hasil_cpi_lain2.txt

python -m research.cpi_lain2

Semua lewat FRED (waktu terbit dari vintage ALFRED; nilai dipakai HANYA bila terbit sebelum tanggal rilis CPI):
  BEI5   breakeven inflasi 5 th (T5YIE, harian): perubahan 20 hari kerja s/d H−1 rilis (pasar obligasi)
  MICH   ekspektasi inflasi 1 th Univ. Michigan: bulan acuan − bulan sebelumnya
  NYPP   Fed New York (Empire) harga bayar, bulan acuan − sebelumnya   (PPCDISA066MSFRBNY)
  NYPR   Fed New York harga jual                                       (PRCDISA066MSFRBNY)
  PHPP   Fed Philadelphia harga bayar                                  (PPCDFSA066MSFRBPHI)
  PHPR   Fed Philadelphia harga jual                                   (PRCDFSA066MSFRBPHI)
  PP2    NYPP & PHPP sepakat
Tanda +1 = CPI diduga DI ATAS konsensus → emas TURUN. Uji = cpi_detik.tetap + tepat (sama dengan aturan aplikasi).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .eksternal_makro import fred

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_lain2.txt"
BULANAN = {"MICH": "MICH", "NYPP": "PPCDISA066MSFRBNY", "NYPR": "PRCDISA066MSFRBNY", "PHPP": "PPCDFSA066MSFRBPHI",
           "PHPR": "PRCDFSA066MSFRBPHI"}


def tambah(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rilis = df.t0.dt.tz_convert("UTC")
    for nama, seri in BULANAN.items():
        try:
            f = fred(seri)
        except Exception as e:  # noqa: BLE001
            print(nama, "gagal", e)
            df[nama] = 0.0
            continue
        out = []
        for t in rilis:
            ref = (t.tz_convert("America/New_York").tz_localize(None) - pd.DateOffset(months=1)).to_period("M").to_timestamp()
            prev = ref - pd.DateOffset(months=1)
            ok = f[f.available < t]
            out.append(float(np.sign(ok.value[ref] - ok.value[prev])) if ref in ok.index and prev in ok.index else 0.0)
        df[nama] = out
    df["PP2"] = np.where(df.NYPP == df.PHPP, df.NYPP, 0.0)
    b = fred("T5YIE")
    out = []
    for t in rilis:
        ok = b[b.available < t].value
        out.append(float(np.sign(ok.iloc[-1] - ok.iloc[-21])) if len(ok) > 21 else 0.0)
    df["BEI5"] = out
    return df


def main() -> None:
    df = tambah(C.turunan(C.tabel()))
    m = df.th >= C.MULAI
    lama, baru = m & (df.t0 < "2021-10-01"), df.t0 >= "2021-10-01"

    def st(tb, mask, hs=C.JAUH):
        k, n = C.tepat(df[mask], tb[mask], hs)
        return f"{k / n * 100:3.0f}% ({n // len(hs)})" if n else "  –"
    L = ["# 🔎 Sumber CPI baru (research/cpi_lain2.py)", __doc__.split("\n\n")[1], ""]
    ts = C.tetap(df, "IDX|K+S")
    for k in ("BEI5", "MICH", "NYPP", "NYPR", "PHPP", "PHPR", "PP2"):
        ok_m = (df[k] != 0) & (df.s_mm != 0)
        ok_c = (df[k] != 0) & (df.s_core != 0)
        tb = C.tetap(df, k)
        sep = ts.where((ts != 0) & (-df[k] == ts), 0)
        L.append(f"{k:5s} kejutan CPI {(df[k][ok_m] == df.s_mm[ok_m]).mean() * 100:3.0f}% / core "
                 f"{(df[k][ok_c] == df.s_core[ok_c]).mean() * 100:3.0f}% (n {ok_m.sum()}) | emas mentah 2–10 {st(-df[k], m)} "
                 f"lama {st(-df[k], lama)} baru {st(-df[k], baru)} | tutup kertas {st(tb, m)} detik 2 {st(tb, m, (2,))} | "
                 f"aplikasi+{k} sepakat detik 2 {st(sep, m, (2,))} lama {st(sep, lama, (2,))} baru {st(sep, baru, (2,))}")
    L.append(f"\nPembanding aplikasi (IDX|K+S) detik 2: semua {st(ts, m, (2,))} lama {st(ts, lama, (2,))} baru {st(ts, baru, (2,))}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
