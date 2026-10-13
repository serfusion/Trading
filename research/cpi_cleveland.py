"""🔎 Cleveland Fed Inflation Nowcasting vs konsensus → kejutan CPI & arah emas detik 1–10 (tutup kertas)

python -m research.cpi_cleveland            → docs/eksternal/hasil_cpi_cleveland.txt

Pertanyaan pengguna 13 Okt 2026: "yakin tidak ada informasi & metode yang terlewat untuk CPI?". Cleveland Fed nowcast
(ramalan harian CPI & core CPI m/m dari harga minyak, bensin harian & data inflasi) dulu diblokir jaringan (403); kini 200.
Data: clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json (160 bulan acuan 2013-07…2026-10,
semua vintage harian) → data/research/eksternal/cleveland/nowcast_month.json.

Aturan (ditetapkan sebelum melihat hasil): nilai nowcast HARI KERJA TERAKHIR sebelum tanggal rilis (tanpa look-ahead) untuk
bulan acuan = bulan sebelum rilis. Tanda = sign(nowcast − konsensus) bila |selisih| ≥ ambang (0,05 utama; 0,03/0,10 cek).
CLV_core / CLV_mm / CLV (core dulu, cadangan headline — core paling menggerakkan emas). Emas = kebalikan tanda.
Uji = research/cpi_detik.tetap (aturan dipakai tahun Y hanya bila benar s/d Y−1 > 50%) + tepat (detik 2–10, per detik).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "research" / "eksternal" / "cleveland" / "nowcast_month.json"
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_cleveland.txt"


def nowcast() -> pd.DataFrame:
    """Baris: (bulan acuan, tanggal vintage, cpi, core)."""
    rows = []
    for e in json.loads(FILE.read_text(encoding="utf-8")):
        y, m = (int(v) for v in e["chart"]["subcaption"].split("-"))
        labs = [c.get("label", "") for c in e["categories"][0]["category"]]
        ser = {ds["seriesname"]: [d.get("value") for d in ds["data"]] for ds in e["dataset"]}
        for i, lab in enumerate(labs):
            if "/" not in lab:
                continue                                        # garis vertikal "PCE Jul" dsb.
            mm, dd = (int(v) for v in lab.split("/"))
            th = y + (1 if mm < m else 0)
            try:
                tgl = pd.Timestamp(year=th, month=mm, day=dd)
            except ValueError:
                continue

            def val(k):
                arr_ = ser.get(k) or []
                v = arr_[i] if i < len(arr_) else None           # sebagian seri lebih pendek dari label
                return float(v) if v not in (None, "") else np.nan
            rows.append({"ref": pd.Timestamp(year=y, month=m, day=1), "tgl": tgl, "cpi": val("CPI Inflation"),
                         "core": val("Core CPI Inflation")})
    return pd.DataFrame(rows).dropna(subset=["cpi"])


def pasang(df: pd.DataFrame, nc: pd.DataFrame, ambang: float = 0.05) -> pd.DataFrame:
    df = df.copy()
    for k in ("nc_mm", "nc_core"):
        df[k] = np.nan
    for i, r in df.iterrows():
        ny = r.t0.tz_convert("America/New_York").tz_localize(None).normalize()
        ref = (ny - pd.DateOffset(months=1)).to_period("M").to_timestamp()
        v = nc[(nc.ref == ref) & (nc.tgl < ny)]
        if len(v):
            last = v.sort_values("tgl").iloc[-1]
            df.at[i, "nc_mm"], df.at[i, "nc_core"] = last.cpi, last.core
    d_mm, d_core = df.nc_mm - df.mm_f, df.nc_core - df.core_f
    df["CLV_mm"] = [C.sgn(v, ambang) for v in d_mm]
    df["CLV_core"] = [C.sgn(v, ambang) for v in d_core]
    df["CLV"] = np.where(df.CLV_core != 0, df.CLV_core, df.CLV_mm)
    return df


def main() -> list[str]:
    base = C.turunan(C.tabel())
    nc = nowcast()
    L = ["# 🔎 Cleveland Fed nowcast vs konsensus (research/cpi_cleveland.py)", __doc__.split("\n\n")[2], "",
         f"Vintage nowcast: {len(nc)} baris, bulan acuan {nc.ref.min():%Y-%m} … {nc.ref.max():%Y-%m}; rilis CPI {len(base)}"]
    m = base.th >= C.MULAI
    lama, baru, b24 = m & (base.t0 < "2021-10-01"), base.t0 >= "2021-10-01", base.th >= 2024

    def st(df, tb, mask, hs=C.JAUH):
        k, n = C.tepat(df[mask], tb[mask], hs)
        return f"{k / n * 100:4.0f}% ({n // len(hs)})" if n else "  –"
    for amb in (0.03, 0.05, 0.10):
        df = pasang(base, nc, amb)
        L.append(f"\n## Ambang {amb:.2f}")
        for kol, s_ in (("CLV_mm", "s_mm"), ("CLV_core", "s_core"), ("CLV", None)):
            if s_:
                ok = (df[kol] != 0) & (df[s_] != 0)
                ok_b = ok & baru
                L.append(f"   {kol:9s} tebak kejutan angka: {(df[kol][ok] == df[s_][ok]).mean() * 100:3.0f}% (n {ok.sum()}) • "
                         f"sejak Okt 2021 {(df[kol][ok_b] == df[s_][ok_b]).mean() * 100:3.0f}% (n {ok_b.sum()})")
            raw = -df[kol]
            tb = C.tetap(df, kol)
            L.append(f"   {kol:9s} emas detik 2–10 MENTAH: semua {st(df, raw, m)} lama {st(df, raw, lama)} baru "
                     f"{st(df, raw, baru)} 2024+ {st(df, raw, b24)} | detik 2 {st(df, raw, m, (2,))}")
            L.append(f"   {kol:9s} emas TUTUP KERTAS : semua {st(df, tb, m)} lama {st(df, tb, lama)} baru {st(df, tb, baru)} "
                     f"2024+ {st(df, tb, b24)} | detik 1 {st(df, tb, m, (1,))} detik 2 {st(df, tb, m, (2,))} "
                     f"detik 10 {st(df, tb, m, (10,))}")
    df = pasang(base, nc, 0.05)
    ts = C.tetap(df, "IDX|K+S")
    clv = -df.CLV
    L.append("\n## Gabung dengan aturan aplikasi (IDX|K+S tutup kertas), ambang 0,05, detik 2 / detik 2–10")
    sep, lawan = (ts != 0) & (clv == ts), (ts != 0) & (clv != 0) & (clv != ts)
    for nama, mask in (("aplikasi semua", ts != 0), ("aplikasi + Cleveland SEPAKAT", sep),
                       ("aplikasi + Cleveland BERLAWANAN", lawan), ("aplikasi, Cleveland netral", (ts != 0) & (clv == 0))):
        t = ts.where(mask, 0)
        L.append(f"   {nama:34s} detik 2: semua {st(df, t, m, (2,))} lama {st(df, t, lama, (2,))} baru {st(df, t, baru, (2,))} "
                 f"| 2–10: semua {st(df, t, m)} baru {st(df, t, baru)}")
    isi = pd.Series(np.where(ts != 0, ts, C.tetap(df, "CLV")), index=df.index)
    L.append(f"   aplikasi, kosong diisi Cleveland     detik 2: semua {st(df, isi, m, (2,))} lama {st(df, isi, lama, (2,))} "
             f"baru {st(df, isi, baru, (2,))} | 2–10 semua {st(df, isi, m)}")
    L.append("\n## Rilis terbaru (nowcast vs konsensus)")
    for _, r in df[df.t0 >= "2025-06-01"].iterrows():
        L.append(f"   {r.t0:%Y-%m-%d} CPI nc {r.nc_mm:.2f} vs kons {r.mm_f} (aktual {r.mm_a}) • core nc {r.nc_core:.2f} vs "
                 f"{r.core_f} (aktual {r.core_a}) • CLV {int(r.CLV):+d} • emas detik 2 {r.g2:+.2f}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return L


if __name__ == "__main__":
    main()
