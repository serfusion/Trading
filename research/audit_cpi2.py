"""🧾 Audit CPI putaran 2 — uji validasi yang BELUM pernah dijalankan (13 Okt 2026).

python -m research.audit_cpi2      → docs/eksternal/hasil_audit_cpi2.txt

Pertanyaan pengguna: "yakin tidak ada yang terlewat lagi, baik metode, riset, maupun uji validasi?". Ditetapkan sebelum dijalankan:
 a. PLASEBO BERITA: tebakan CPI bulan itu dipakai pada rilis 08:30 LAIN di bulan yang sama (Retail, PPI, klaim, NFP, GDP…).
    Kalau sama baiknya → bukan petunjuk CPI melainkan arah emas bulan itu.
 b. PLASEBO WAKTU: tebakan vs gerak emas SEBELUM rilis (t−100 dtk → t−1 dtk). Kalau > 50% jelas → tebakan sekadar ikut arus
    yang sudah berjalan (bukan membaca angka).
 c. BEDAH PER TAHUN: ketepatan menebak ANGKA (kejutan headline/core) vs PLAFON (emas ikut kejutan) — kenapa 2019–2021 gagal.
 d. BANYAK-UJI SELURUH RISET CPI: p binomial satu sisi tiap aturan aplikasi × jumlah aturan CPI yang pernah diuji di semua
    putaran (± 100: cpi_detik 25, cpi_petunjuk2 19, cpi_semua 29, cpi_lain2/cleveland ±12, kalshi/varian ±15) = Bonferroni.
 e. JAM RILIS: apakah lonjakan benar terjadi di t0 (|gerak 0→10 dtk| jauh > |gerak t−70→t−60 dtk|) untuk setiap rilis CPI & PPI
    — mendeteksi jam/tanggal salah yang tidak terlihat di tabel.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .riset_dalam_data import EKS, ticks

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_audit_cpi2.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
N_ATURAN_CPI = 100


def mid_at(df: pd.DataFrame, t0: pd.Timestamp, s: float) -> float:
    T = (df.index - t0).total_seconds().to_numpy()
    j = int(np.searchsorted(T, s, side="right")) - 1
    return float((df.bid.iloc[j] + df.ask.iloc[j]) / 2) if j >= 0 else np.nan


def pct(k, n) -> str:
    return f"{k / n * 100:.0f}% ({k}/{n})" if n else "–"


def main() -> None:
    from . import cpi_detik as C
    L = ["# 🧾 Audit CPI putaran 2 (research/audit_cpi2.py)", __doc__.split("\n\n")[1]]
    df = C.turunan(C.tabel())
    df["t0"] = pd.to_datetime(df.t0, utc=True)
    df["tb"] = C.tetap(df, "IDX|K+S").to_numpy()
    df["tbk"] = C.tetap(df, "IDX|K").to_numpy()
    df["kal"] = -df.mm_K
    x = df[df.th >= 2016].copy()
    aturan = {"aplikasi (IDX|K+saringan)": "tb", "IDX|K": "tbk", "Kalshi saja": "kal"}

    # a. plasebo berita
    lj = pd.concat([pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "grup", "arah"]],
                    pd.read_parquet(EKS / "riset_dalam" / "lonjakan.parquet")[["t0", "grup", "arah"]]])
    lj = lj.dropna(subset=["arah"]).drop_duplicates("t0")
    ny = lj.t0.dt.tz_convert("America/New_York")
    lain = lj[(ny.dt.hour == 8) & (ny.dt.minute == 30) & (lj.grup != "CPI") & ~lj.t0.isin(x.t0)].copy()
    lain["bln"] = lain.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    x["bln"] = x.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    lj_cpi = lj[lj.grup == "CPI"][["t0", "arah"]]
    x = x.merge(lj_cpi, on="t0", how="left")
    L.append("\n## a. Plasebo berita (lonjakan menit 1): CPI vs rilis 08:30 LAIN di bulan yang sama")
    for nama, kol in aturan.items():
        m = lain.merge(x[["bln", kol]], on="bln")
        g, y = m[kol].to_numpy(), m.arah.to_numpy()
        ok = (g != 0) & (y != 0)
        gc, yc = x[kol].to_numpy(), x.arah.fillna(0).to_numpy()
        okc = (gc != 0) & (yc != 0)
        per = " • ".join(f"{gr} {pct(int((g[ok & (m.grup == gr).to_numpy()] == y[ok & (m.grup == gr).to_numpy()]).sum()), int((ok & (m.grup == gr).to_numpy()).sum()))}"
                         for gr in ("PPI", "RETAIL", "CLAIMS", "NFP", "GDP"))
        L.append(f"   {nama:26s} CPI {pct(int((gc[okc] == yc[okc]).sum()), int(okc.sum()))} vs lain "
                 f"{pct(int((g[ok] == y[ok]).sum()), int(ok.sum()))} ({per})")

    # b & e: tick per rilis CPI (dan PPI untuk e)
    rows = []
    for t in x.t0:
        tk = ticks(t)
        if tk is None:
            continue
        a, b = mid_at(tk, t, -100), mid_at(tk, t, -1)
        c0, c1 = mid_at(tk, t, -70), mid_at(tk, t, -60)
        d10 = mid_at(tk, t, 10)
        rows.append({"t0": t, "pra": np.sign(b - a), "pra_abs": abs(b - a), "tenang": abs(c1 - c0),
                     "lonjak": abs(d10 - b)})
    tk = pd.DataFrame(rows)
    x = x.merge(tk, on="t0", how="left")
    L.append("\n## b. Plasebo waktu: tebakan vs gerak emas SEBELUM rilis (t−100 → t−1 dtk; jendela tick mulai t−120)")
    for nama, kol in aturan.items():
        g, y = x[kol].fillna(0).to_numpy(), x.pra.fillna(0).to_numpy()
        isi = []
        for per, m in (("2016–26", x.th >= 2016), ("BARU", x.t0 >= SPLIT)):
            mm = m.to_numpy() & (g != 0) & (y != 0)
            k, n = int((g[mm] == y[mm]).sum()), int(mm.sum())
            isi.append(f"{per} {pct(k, n)} (p {binomtest(k, n, 0.5).pvalue:.2f})" if n else f"{per} –")
        L.append(f"   {nama:26s} " + " | ".join(isi))

    L.append("\n## c. Per tahun: tebak ANGKA (headline / core) • PLAFON emas ikut kejutan core (detik 2) • aturan aplikasi detik 2")
    for th, g in x.groupby("th"):
        def acc(col, s):
            m = (g[col] != 0) & (g[s] != 0)
            return pct(int((np.sign(-g[col][m]) == np.sign(g[s][m])).sum()), int(m.sum()))
        d2 = np.sign(g.g2.fillna(0))
        pl = (g.s_core != 0) & (d2 != 0)
        ap = (g.tb != 0) & (d2 != 0)
        L.append(f"   {th}: angka head {acc('tb', 's_mm')} core {acc('tb', 's_core')} • plafon core "
                 f"{pct(int((-g.s_core[pl] == d2[pl]).sum()), int(pl.sum()))} • aturan detik 2 "
                 f"{pct(int((g.tb[ap] == d2[ap]).sum()), int(ap.sum()))}")

    L.append(f"\n## d. Banyak-uji seluruh riset CPI (Bonferroni × {N_ATURAN_CPI} aturan), detik 2, p binomial satu sisi")
    for nama, kol in aturan.items():
        for per, m in (("2016–26", x.th >= 2016), ("BARU", x.t0 >= SPLIT)):
            g, y = x[kol].to_numpy(), np.sign(x.g2.fillna(0)).to_numpy()
            mm = m.to_numpy() & (g != 0) & (y != 0)
            k, n = int((g[mm] == y[mm]).sum()), int(mm.sum())
            p = binomtest(k, n, 0.5, alternative="greater").pvalue if n else 1.0
            L.append(f"   {nama:26s} {per:8s} {pct(k, n)} p {p:.4f} → Bonferroni {min(1.0, p * N_ATURAN_CPI):.3f}"
                     + ("  ✅ tetap < 0,05" if p * N_ATURAN_CPI < 0.05 else ""))

    L.append("\n## e. Jam rilis: |gerak 0→10 dtk| vs |gerak t−70→t−60 dtk| (rilis tanpa lonjakan = curiga jam/tanggal salah)")
    xx = x.dropna(subset=["lonjak"])
    curiga = xx[xx.lonjak < 3 * xx.tenang.clip(lower=0.05)]
    L.append(f"   CPI: {len(xx)} rilis bertick, median lonjakan ${xx.lonjak.median():.2f} vs tenang ${xx.tenang.median():.2f}; "
             f"curiga {len(curiga)}: {[str(t.date()) for t in curiga.t0]}")
    pp = pd.read_csv(EKS / "riset_ppi3" / "ppi_resmi.csv").iloc[:, 0]
    rows = []
    for t in pd.to_datetime(pp, utc=True):
        tk2 = ticks(t)
        if tk2 is None:
            continue
        b = mid_at(tk2, t, -1)
        rows.append({"t0": t, "lonjak": abs(mid_at(tk2, t, 10) - b),
                     "tenang": abs(mid_at(tk2, t, -60) - mid_at(tk2, t, -70))})
    p2 = pd.DataFrame(rows).dropna()
    c2 = p2[p2.lonjak < 3 * p2.tenang.clip(lower=0.05)]
    L.append(f"   PPI: {len(p2)} rilis bertick, median lonjakan ${p2.lonjak.median():.2f} vs tenang ${p2.tenang.median():.2f}; "
             f"curiga {len(c2)}: {[str(t.date()) for t in c2.t0]}")
    L.append("   (dicek manual 21 rilis curiga: jumlah tick melonjak tepat di t0 & lonjakan 1 dtk terbesar umumnya T+1…+6 dtk →\n"
             "    jam BENAR; 'curiga' = rilis yang reaksinya kecil / tick Exness 2016–17 masih ±1 per detik)")
    ppi(L)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


N_ATURAN_PPI = 35          # putaran 1 (±4) + putaran 2 (12) + putaran 3 (10) + pra_per_berita/pra_xau_dalam/pra_lain (±9)


def ppi_head() -> pd.DataFrame:
    """Act & konsensus PPI headline m/m per tanggal (FF mentah ≤ 2023, Nasdaq 2024+; m/m = baris |prev| kecil)."""
    import glob
    import json

    from .riset_dalam_data import _num, ff_mentah
    ff = ff_mentah()
    a = ff[ff.event == "PPI m/m"][["t0", "actual", "forecast"]].rename(columns={"actual": "ha", "forecast": "hf"})
    a["d"] = a.t0.dt.tz_convert("America/New_York").dt.date
    rows = []
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "*.json"))):
        if Path(f).stem < "2024-01-01":
            continue
        g = [r for r in json.loads(Path(f).read_text(encoding="utf-8"))
             if r.get("eventName") == "PPI" and r.get("country") == "United States"]
        if len(g) >= 2:
            g = sorted(g[:2], key=lambda r: abs(_num(r.get("previous"))) if _num(r.get("previous")) == _num(
                r.get("previous")) else 99)
            rows.append({"d": pd.Timestamp(Path(f).stem).date(), "ha": g[0].get("actual"), "hf": g[0].get("consensus")})
    x = pd.concat([a[["d", "ha", "hf"]], pd.DataFrame(rows)], ignore_index=True).drop_duplicates("d")
    x["ha"], x["hf"] = x.ha.map(_num), x.hf.map(_num)
    return x


def ppi(L: list) -> None:
    """Uji yang sama untuk PPI-WTI pada 128 rilis RESMI dengan tick lengkap (research/audit_cpi_ppi bagian E)."""
    from .riset_dalam_data import satu
    from .riset_ppi3 import core_ppi, fred_harian, jendela13
    t = pd.to_datetime(pd.read_csv(EKS / "riset_ppi3" / "ppi_resmi.csv").iloc[:, 0], utc=True)
    wti = fred_harian("DCOILWTICO")
    rows = []
    for t0 in t:
        ny = t0.tz_convert("America/New_York")
        ref = pd.Timestamp(ny.year, ny.month, 1) - pd.offsets.MonthBegin(1)
        a = jendela13(wti[wti.index < ny.tz_localize(None).normalize()], ref)
        b = jendela13(wti, ref - pd.offsets.MonthBegin(1))
        ch = (a / b - 1) * 100 if a == a and b == b else np.nan
        o = satu(t0)
        tk = ticks(t0)
        o["pra"] = np.sign(mid_at(tk, t0, -1) - mid_at(tk, t0, -100)) if tk is not None else np.nan
        o["g"] = -1.0 if ch >= 5 else (1.0 if ch <= -5 else 0.0)          # tebakan emas
        o["d"] = ny.date()
        rows.append(o)
    x = pd.DataFrame(rows).merge(ppi_head(), on="d", how="left").merge(core_ppi(), on="d", how="left")
    x["s_head"], x["s_core"] = np.sign(x.ha - x.hf), np.sign(x.ca - x.cf)
    x["th"] = x.t0.dt.year
    x = x[x.th >= 2016]
    g = x.g.to_numpy()
    L.append(f"\n\n# PPI-WTI — uji yang sama ({len(x)} rilis resmi, tick {int(x.arah.notna().sum())})")
    # a. plasebo berita
    lj = pd.concat([pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "grup", "arah"]],
                    pd.read_parquet(EKS / "riset_dalam" / "lonjakan.parquet")[["t0", "grup", "arah"]]])
    lj = lj.dropna(subset=["arah"]).drop_duplicates("t0")
    ny = lj.t0.dt.tz_convert("America/New_York")
    lain = lj[(ny.dt.hour == 8) & (ny.dt.minute == 30) & (lj.grup != "PPI") & ~lj.t0.isin(x.t0)].copy()
    lain["bln"] = lain.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    x["bln"] = x.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    m = lain.merge(x[["bln", "g"]], on="bln")
    ok = (m.g != 0) & (m.arah != 0)
    y = x.arah.fillna(0).to_numpy()
    okp = (g != 0) & (y != 0)
    per = " • ".join(f"{gr} {pct(int((m.g[ok & (m.grup == gr)] == m.arah[ok & (m.grup == gr)]).sum()), int((ok & (m.grup == gr)).sum()))}"
                     for gr in ("CPI", "RETAIL", "CLAIMS", "NFP", "GDP"))
    L.append(f"## a. Plasebo berita (lonjakan): PPI {pct(int((g[okp] == y[okp]).sum()), int(okp.sum()))} vs rilis 08:30 lain "
             f"bulan sama {pct(int((m.g[ok] == m.arah[ok]).sum()), int(ok.sum()))} ({per})")
    # b. plasebo waktu
    pr = x.pra.fillna(0).to_numpy()
    isi = []
    for nama, mm in (("2016–26", x.th >= 2016), ("BARU", x.t0 >= SPLIT)):
        q = mm.to_numpy() & (g != 0) & (pr != 0)
        k, n = int((g[q] == pr[q]).sum()), int(q.sum())
        isi.append(f"{nama} {pct(k, n)} (p {binomtest(k, n, 0.5).pvalue:.2f})" if n else f"{nama} –")
    L.append("## b. Plasebo waktu (tebakan vs gerak emas t−100 → t−1 dtk): " + " | ".join(isi))
    # c. per tahun
    L.append("## c. Per tahun: tebak ANGKA headline / core • PLAFON emas ikut kejutan core (lonjakan) • aturan (lonjakan / detik 2)")
    for th, gg in x.groupby("th"):
        def acc(s):
            q = (gg.g != 0) & (gg[s].fillna(0) != 0)
            return pct(int((-gg.g[q] == gg[s][q]).sum()), int(q.sum()))
        q = (gg.s_core.fillna(0) != 0) & (gg.arah.fillna(0) != 0)
        a1 = (gg.g != 0) & (gg.arah.fillna(0) != 0)
        a2 = (gg.g != 0) & (gg.d2.fillna(0) != 0)
        L.append(f"   {th}: angka head {acc('s_head')} core {acc('s_core')} • plafon core "
                 f"{pct(int((-gg.s_core[q] == gg.arah[q]).sum()), int(q.sum()))} • aturan lonjakan "
                 f"{pct(int((gg.g[a1] == gg.arah[a1]).sum()), int(a1.sum()))} / detik 2 {pct(int((gg.g[a2] == gg.d2[a2]).sum()), int(a2.sum()))}")
    # d. Bonferroni
    L.append(f"## d. Banyak-uji seluruh riset PPI (Bonferroni × {N_ATURAN_PPI} aturan), p binomial satu sisi")
    for kol, lab in (("arah", "lonjakan"), ("d2", "detik 2"), ("d5", "detik 5")):
        yy = x[kol].fillna(0).to_numpy()
        for nama, mm in (("2016–26", x.th >= 2016), ("BARU", x.t0 >= SPLIT)):
            q = mm.to_numpy() & (g != 0) & (yy != 0)
            k, n = int((g[q] == yy[q]).sum()), int(q.sum())
            p = binomtest(k, n, 0.5, alternative="greater").pvalue if n else 1.0
            L.append(f"   {lab:9s} {nama:8s} {pct(k, n)} p {p:.4f} → Bonferroni {min(1.0, p * N_ATURAN_PPI):.3f}"
                     + ("  ✅ tetap < 0,05" if p * N_ATURAN_PPI < 0.05 else ""))


if __name__ == "__main__":
    main()
