"""🧾 AUDIT DATA CPI & PPI (13 Okt 2026) — kenapa PPI-WTI turun 69% → 63%, dan apakah CPI punya masalah yang sama.

python -m research.audit_cpi_ppi      → docs/eksternal/hasil_audit_cpi_ppi.txt

Pertanyaan pengguna: "mengapa yang awalnya 69 turun ke 63, apa ada data yang sangat bagus? saya curiga CPI juga sama —
pelajari dan cari informasi lebih dalam lagi". Temuan PPI (research/riset_ppi3.py): 8 rilis bersinyal di putaran 2 TIDAK
punya tick ("tidak ada tick") sehingga diam-diam tidak dihitung; setelah tick diunduh kedelapannya salah (54/78 → 54/86) dan
satu tanggal salah (2025-09-09, PPI resmi 2025-09-10). Audit ini memeriksa hal yang sama secara sistematis:
 A. TANGGAL: daftar rilis riset vs tanggal rilis resmi FRED (CPI release 10, PPI release 46), 2016–2026.
 B. KELENGKAPAN: rilis resmi yang tidak punya target (tick) di tabel riset — ikut dihitung setelah tick diunduh?
 C. TARGET ULANG: arah detik 2/10 & lonjakan dihitung ulang dari tick ASLI Exness (jendela berita + tambahan) untuk SETIAP
    tanggal resmi, dibandingkan dengan target di tabel riset (beda feed / beda jam?).
 D. ANGKA ATURAN APLIKASI (IDX|K + saringan, tutup kertas) dengan target lama vs target ulang yang lengkap; per JALUR yang
    benar-benar dipakai (indeks Nasdaq vs Kalshi) — konsensus indeks tidak tersedia H−1 (13 Okt), jadi jalur live 2026 =
    Kalshi; dan unsur yang ditemukan SETELAH melihat hasil (IDX|K, saringan) dipisah.
 E. KEBOCORAN KONSENSUS INDEKS: galat konsensus indeks Nasdaq vs galat konsensus m/m (poin indeks) per tahun; persen yang
    persis sama dengan Act (tanda diisi setelah rilis).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .riset_dalam_data import EKS, satu

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_audit_cpi_ppi.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


def resmi(rid: int) -> list[pd.Timestamp]:
    d = json.loads((EKS / f"fred_release_{rid}.json").read_text())["release_dates"]
    out = []
    for x in d:
        t = pd.Timestamp(f"{x['date']} 08:30").tz_localize("America/New_York").tz_convert("UTC")
        if pd.Timestamp("2016-01-01", tz="UTC") <= t <= pd.Timestamp("2026-10-01", tz="UTC"):
            out.append(t)
    return sorted(set(out))


def pct(k, n) -> str:
    return f"{k / n * 100:.1f}% ({k}/{n})" if n else "–"


def benar(tb, y) -> tuple[int, int]:
    tb, y = np.asarray(tb, float), np.asarray(y, float)
    ok = (tb != 0) & (y != 0) & ~np.isnan(y)
    return int((np.sign(tb[ok]) == np.sign(y[ok])).sum()), int(ok.sum())


def bagian_tanggal(nama: str, riset: pd.Series, rid: int, L: list) -> list[pd.Timestamp]:
    r = resmi(rid)
    rs = {t.tz_convert("America/New_York").date() for t in riset}
    of = {t.tz_convert("America/New_York").date() for t in r}
    salah = sorted(d for d in rs if d not in of and pd.Timestamp("2016-01-01").date() <= d <= pd.Timestamp("2026-10-01").date())
    hilang = sorted(d for d in of if d not in rs)
    L.append(f"\n## A/B. {nama}: tanggal riset vs FRED (2016–Sep 2026): resmi {len(r)}, di tabel riset {len(rs & of)}")
    L.append(f"   tanggal di riset yang BUKAN tanggal resmi: {[str(d) for d in salah] or 'tidak ada'}")
    L.append(f"   tanggal resmi yang TIDAK ada di tabel riset: {[str(d) for d in hilang] or 'tidak ada'}")
    return r


def main() -> None:
    from . import cpi_detik as C
    L = ["# 🧾 Audit data CPI & PPI (research/audit_cpi_ppi.py)", __doc__.split("\n\n")[1]]
    # ---------------- CPI
    df = C.turunan(C.tabel())
    df["t0"] = pd.to_datetime(df.t0, utc=True)
    r = bagian_tanggal("CPI", df.t0, 10, L)
    ulang = pd.DataFrame([satu(t) for t in r])
    ulang["d"] = ulang.t0.dt.tz_convert("America/New_York").dt.date
    df["d"] = df.t0.dt.tz_convert("America/New_York").dt.date
    tb_k = C.tetap(df, "IDX|K")
    tb_s = C.tetap(df, "IDX|K+S")
    df["tb_k"], df["tb_s"] = tb_k.to_numpy(), tb_s.to_numpy()
    x = df[df.th >= 2016].merge(ulang[["d", "d2", "d10", "arah"]], on="d", how="left")
    jalur = np.where(x.SUARA_IDX != 0, "indeks", np.where(x.mm_K != 0, "kalshi", "-"))
    x["jalur"] = jalur
    L.append("\n## C. CPI target ulang (tick Exness) vs target tabel riset (g2/g10 = Exness, cadangan Dukascopy)")
    for h in (2, 10):
        a, b = np.sign(x[f"g{h}"]), np.sign(x[f"d{h}"])
        ada = a.notna() & b.notna() & (a != 0) & (b != 0)
        L.append(f"   detik {h}: tabel ada {int(a.notna().sum())}, ulang ada {int(b.notna().sum())}, sama arah "
                 f"{(a[ada] == b[ada]).mean() * 100:.1f}% ({int(ada.sum())}); tabel kosong tapi ulang ada "
                 f"{int((a.isna() & b.notna()).sum())}")
    L.append("\n## D. Aturan aplikasi CPI (tutup kertas) — target lama vs target ulang LENGKAP, per jalur")
    for nama, kol in (("IDX|K tanpa saringan", "tb_k"), ("IDX|K + saringan (aplikasi)", "tb_s")):
        for target, lama_kol, ulang_kol in (("detik 2", "g2", "d2"), ("detik 10", "g10", "d10")):
            isi = []
            for per, m in (("2016–26", x.th >= 2016), ("LAMA", x.t0 < SPLIT), ("BARU", x.t0 >= SPLIT),
                           ("2024+", x.th >= 2024)):
                k1, n1 = benar(x[kol][m], x[lama_kol][m])
                k2, n2 = benar(x[kol][m], x[ulang_kol][m])
                isi.append(f"{per} lama {pct(k1, n1)} → ulang {pct(k2, n2)}")
            L.append(f"   {nama:28s} {target}: " + " | ".join(isi))
    for j in ("indeks", "kalshi"):
        m = x.jalur == j
        isi = []
        for per, mm in (("semua", m), ("BARU", m & (x.t0 >= SPLIT)), ("2024+", m & (x.th >= 2024))):
            k, n = benar(x.tb_s[mm], x.d2[mm])
            isi.append(f"{per} {pct(k, n)}")
        L.append(f"   jalur {j:7s} (aplikasi, detik 2, target ulang): " + " | ".join(isi))
    tahun_jalur = x[x.th >= 2022].groupby("th").jalur.value_counts().unstack(fill_value=0)
    L.append("   rilis per jalur per tahun:\n" + "\n".join("      " + s for s in tahun_jalur.to_string().splitlines()))
    # rilis tanpa target di riset lama tetapi bersinyal
    hil = x[(x.tb_s != 0) & x.g2.isna()]
    L.append(f"   rilis bersinyal yang DULU tanpa target: {len(hil)} → dengan target ulang benar "
             f"{pct(*benar(hil.tb_s, hil.d2))} {[str(d) for d in hil.d]}")
    # ---------------- PPI
    p = pd.read_pickle(EKS / "riset_inflasi" / "petunjuk.parquet")
    p = p[p.grup == "PPI"]
    rp = bagian_tanggal("PPI", p.t0, 46, L)
    # hanya tanggal FRED yang benar-benar memuat angka PPI (FF semua dampak / Nasdaq); sisanya revisi musiman Februari
    nyata = set(pd.to_datetime(pd.read_csv(EKS / "riset_ppi3" / "ppi_resmi.csv").iloc[:, 0], utc=True))
    L.append(f"   tanggal FRED tanpa angka PPI (revisi musiman, dibuang): {[str(t.date()) for t in rp if t not in nyata]}")
    rp = [t for t in rp if t in nyata]
    up = pd.DataFrame([satu(t) for t in rp])
    up["d"] = up.t0.dt.tz_convert("America/New_York").dt.date
    p = p.assign(d=p.t0.dt.tz_convert("America/New_York").dt.date)
    y = up.merge(p[["d", "WTI", "L"]], on="d", how="left")
    y["th"] = y.t0.dt.year
    L.append("\n## D'. PPI-WTI dengan tanggal RESMI & target ulang lengkap (mentah, tebakan emas = −WTI)")
    g = -y.WTI.fillna(0)
    for per, m in (("2016–26", y.th >= 2016), ("LAMA", y.t0 < SPLIT), ("BARU", y.t0 >= SPLIT), ("2024+", y.th >= 2024)):
        L.append(f"   {per:8s} lonjakan putaran 2 {pct(*benar(g[m], y.L[m]))} → resmi+lengkap {pct(*benar(g[m], y.arah[m]))} | "
                 f"detik 2 {pct(*benar(g[m], y.d2[m]))} | detik 10 {pct(*benar(g[m], y.d10[m]))}")
    ppi_lengkap(rp, up, L)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def ppi_lengkap(rp: list, up: pd.DataFrame, L: list) -> None:
    """PPI-WTI & keranjang energi dihitung untuk SETIAP tanggal rilis resmi (tidak bergantung tabel riset)."""
    from scipy.stats import beta

    from .riset_ppi3 import fred_harian, jendela13
    s = {k: fred_harian(v) for k, v in (("wti", "DCOILWTICO"), ("gas", "DGASUSGULF"), ("dsl", "DDFUELUSGULF"))}
    rows = []
    for t in rp:
        ny = t.tz_convert("America/New_York")
        ref = (pd.Timestamp(ny.year, ny.month, 1) - pd.offsets.MonthBegin(1))
        prv = ref - pd.offsets.MonthBegin(1)
        ch = {}
        for k, ser in s.items():
            a, b = jendela13(ser[ser.index < ny.tz_localize(None).normalize()], ref), jendela13(ser, prv)
            ch[k] = (a / b - 1) * 100 if a == a and b == b else np.nan
        e = np.nanmean([ch["wti"], ch["gas"], ch["dsl"]]) if sum(v == v for v in ch.values()) >= 2 else np.nan
        rows.append({"t0": t, "wti": ch["wti"], "e": e})
    z = pd.DataFrame(rows).merge(up[["t0", "arah", "d1", "d2", "d3", "d5", "d10"]], on="t0", how="left")
    z["th"] = z.t0.dt.year
    L.append(f"\n## E. PPI LENGKAP: {len(z)} tanggal resmi 2016–Sep 2026, tick ada {int(z.arah.notna().sum())} "
             f"(tanpa tick = pasar tutup/data bolong: {[str(t.date()) for t in z.t0[z.arah.isna()]]})")
    for nama, kol in (("WTI ±5%", "wti"), ("keranjang energi ±5%", "e")):
        g = -np.where(z[kol] >= 5, 1.0, np.where(z[kol] <= -5, -1.0, 0.0))
        for per, m in (("2016–26", z.th >= 2016), ("LAMA", z.t0 < SPLIT), ("BARU", z.t0 >= SPLIT), ("2024+", z.th >= 2024)):
            mm = m.to_numpy()
            isi = [f"{h} {pct(*benar(g[mm], z[c].to_numpy()[mm]))}" for h, c in
                   (("lonjakan", "arah"), ("d1", "d1"), ("d2", "d2"), ("d5", "d5"), ("d10", "d10"))]
            k, n = benar(g[mm], z.arah.to_numpy()[mm])
            isi.append(f"Bayes P>50% {1 - beta.cdf(0.5, k + 1, n - k + 1):.2f} P>60% {1 - beta.cdf(0.6, k + 1, n - k + 1):.2f}")
            L.append(f"   {nama:20s} {per:8s} " + " • ".join(isi))
    tambah = z[~z.t0.dt.date.isin(set(pd.to_datetime(pd.read_pickle(EKS / "riset_inflasi" / "petunjuk.parquet").query(
        "grup == 'PPI'").t0).dt.tz_convert("America/New_York").dt.date))]
    g = -np.where(tambah.wti >= 5, 1.0, np.where(tambah.wti <= -5, -1.0, 0.0))
    L.append(f"   rilis resmi yang dulu TIDAK ada di tabel: {len(tambah)}, WTI bersinyal {int((g != 0).sum())}, benar "
             f"{pct(*benar(g, tambah.arah.to_numpy()))}")


if __name__ == "__main__":
    main()
