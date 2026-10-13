"""⚖️ CPI: tebakan aplikasi saat petunjuk lain SEPAKAT vs BERLAWANAN → cloud/api/cpi_detik.json["konflik"]

python -m research.cpi_konflik          → docs/eksternal/hasil_cpi_konflik.txt + cpi_detik.json["konflik"]

Permintaan pengguna 13 Okt 2026 (setelah konsensus CPI 14 Okt terbit): "silahkan dikalkulasikan … kedepannya selalu cek
forecast, konsensus, dll agar persentase berubah up to date". Cloud mengambil konsensus (ForexFactory/Nasdaq, cache 10–30
mnt) & Kalshi (langsung) setiap aplikasi dibuka; file ini memberi angka historis untuk SITUASI yang sedang terjadi supaya
persen di detail ikut berubah ketika petunjuk berubah. Aturan tebakan TIDAK diubah (IDX|K tutup kertas, saringan sama).

Situasi per rilis (tebakan emas = research.cpi_detik.tetap(df, "IDX|K"), termasuk tebakan ⚠️ lemah):
  YOY berlawanan   = y/y tersirat dari konsensus m/m + efek basis (indeks NSA) − konsensus y/y ≥ 0,05 menunjuk arah CPI
                     yang berlawanan dengan tebakan (tebak NAIK = CPI di bawah, tetapi y/y condong DI ATAS).
  inti berlawanan  = Kalshi core condong (|atas − bawah| ≥ 0,10) berlawanan dengan tebakan (data Kalshi 2022+).
  sepakat          = tidak ada yang berlawanan.
Kelompok yang disimpan: sepakat; yoy (SEMUA rilis dengan YOY berlawanan, termasuk yang inti juga berlawanan); inti (semua
dengan Kalshi inti berlawanan); keduanya. Cloud memakai sel paling khusus yang n ≥ 10 (keduanya → yoy → inti) supaya
tidak memamerkan persen dari 3–4 rilis.
Target: arah emas detik 2 dan detik 10 (tick, research.cpi_detik) + lonjakan terbesar menit pertama (lonjakan60).
Ini DESKRIPTIF (n kecil per situasi) — bukan aturan baru; ditampilkan sebagai "rilis serupa dulu".
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_konflik.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


def tabel() -> pd.DataFrame:
    df = C.turunan(C.tabel())
    df["t0"] = pd.to_datetime(df.t0, utc=True)
    df["tb"] = C.tetap(df, "IDX|K").to_numpy()
    df["lemah"] = (df.tb != 0) & (C.tetap(df, "IDX|K+S").to_numpy() == 0)
    from .lonjakan_uji import lonjakan
    lj = lonjakan()
    lj = lj[lj.grup == "CPI"][["t0", "L"]]
    df = df.merge(lj, on="t0", how="left")
    cpi = -df.tb                                           # arah CPI yang ditebak (+1 di atas)
    df["yoy_lawan"] = (df.tb != 0) & (df.YOY != 0) & (df.YOY != cpi)
    df["inti_lawan"] = (df.tb != 0) & (df.core_K != 0) & (df.core_K != cpi)
    df["situasi"] = np.select([df.yoy_lawan & df.inti_lawan, df.yoy_lawan, df.inti_lawan], ["keduanya", "yoy", "inti"],
                              "sepakat")
    return df[df.th >= 2016].reset_index(drop=True)


def hit(df: pd.DataFrame, m: pd.Series, kol: str) -> tuple[int, int]:
    y = np.sign(df[kol].fillna(0))
    ok = m & (df.tb != 0) & (y != 0)
    return int((y[ok] == df.tb[ok]).sum()), int(ok.sum())


def allin(df: pd.DataFrame, L: list) -> dict:
    """💥 strategi modal kecil (research/cpi_spike.jalan: masuk t−1 dtk, lentur, tick Exness) per situasi, tebakan KUAT saja."""
    from .cpi_allin2 import arr
    from .cpi_spike import jalan
    from .exness import ticks_around
    rows = []
    for _, r in df[(df.tb != 0) & ~df.lemah].iterrows():
        tk = ticks_around("XAUUSDc", r.t0)
        if tk is None:
            continue
        a, o = arr(tk, r.t0), {"t0": r.t0, "yoy": r.yoy_lawan, "inti": r.inti_lawan, "sit": r.situasi}
        for lev in (200, 500, 1000):
            j = jalan(a, int(r.tb), -1.0, lev, "lentur")
            if j is None:
                break
            o[f"pl{lev}"], o[f"h{lev}"] = j
        if "pl1000" in o:
            rows.append(o)
    x = pd.DataFrame(rows)
    x["baru"] = x.t0 >= SPLIT
    L.append("\n## 💥 Modal kecil (lentur, tebakan kuat) per situasi — per modal $100")
    hasil = {}
    for nama, m in (("semua", x.index == x.index), ("sepakat", x.sit == "sepakat"), ("yoy", x.yoy), ("inti", x.inti)):
        r = {}
        for per, mp in (("baru", x.baru), ("lama", ~x.baru)):
            z = x[m & mp]
            r[per] = {"n": len(z), **{str(lv): {"untung": round(float((z[f"pl{lv}"] > 0).mean() * 100)) if len(z) else None,
                                                 "rata": round(float(z[f"pl{lv}"].mean()), 1) if len(z) else None,
                                                 "habis": int(z[f"h{lv}"].sum())} for lv in (200, 500, 1000)}}
            if len(z):
                L.append(f"   {nama:8s} {'sejak Okt 2021' if per == 'baru' else 'sebelum Okt 2021':17s} n {len(z):2d} | " +
                         " | ".join(f"1:{lv} untung {r[per][str(lv)]['untung']}% rata {r[per][str(lv)]['rata']:+.1f} habis "
                                    f"{r[per][str(lv)]['habis']}" for lv in (200, 500, 1000)))
        hasil[nama] = r
    return hasil


def main() -> None:
    df = tabel()
    L = ["# ⚖️ CPI: tebakan saat petunjuk lain sepakat / berlawanan (research/cpi_konflik.py)", __doc__.split("\n\n")[2], ""]
    out = {}
    for arah, sg in (("naik", 1), ("turun", -1)):
        kel = {"sepakat": df.situasi == "sepakat", "yoy": df.yoy_lawan, "inti": df.inti_lawan,
               "keduanya": df.situasi == "keduanya"}
        for sit, ms in kel.items():
            m = (df.tb == sg) & ms
            r = {}
            for nama, kol in (("d2", "g2"), ("d10", "g10"), ("lonjakan", "L")):
                k, n = hit(df, m, kol)
                kb, nb = hit(df, m & (df.t0 >= SPLIT), kol)
                r[nama] = {"pct": round(k / n * 100) if n else None, "n": n,
                           "pct_baru": round(kb / nb * 100) if nb else None, "n_baru": nb}
            r["lemah"] = int((m & df.lemah).sum())
            out[f"{arah}_{sit}"] = r
            tgl = ", ".join(f"{t:%Y-%m}{'✓' if np.sign(g) == sg else '✗'}" for t, g in zip(df.t0[m], df.g2[m]) if g == g)
            L.append(f"{arah.upper():5s} {sit:9s} | detik 2 {r['d2']['pct']}% (n {r['d2']['n']}; sejak Okt 2021 "
                     f"{r['d2']['pct_baru']}% n {r['d2']['n_baru']}) | detik 10 {r['d10']['pct']}% | lonjakan "
                     f"{r['lonjakan']['pct']}% (n {r['lonjakan']['n']}) | ⚠️ lemah {r['lemah']}")
            L.append(f"      {tgl}")
    out["allin"] = allin(df, L)
    L.append("\nCatatan: n per situasi kecil → angka bisa berubah banyak dengan 1–2 rilis; aturan utama tidak diubah.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    f = ROOT / "cloud" / "api" / "cpi_detik.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["konflik"] = out
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
