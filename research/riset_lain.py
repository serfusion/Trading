"""🔬 Retail, GDP, ADP, JOLTS, klaim, konsumen → arah LONJAKAN TERBESAR emas MENIT PERTAMA (kelompok "retail_gdp",
"kerja_lain" & konsumen dari workflow 11 Okt yang terputus; permintaan 13 Okt "lanjutkan ... sesuai urutan release").

python -m research.riset_lain          → docs/eksternal/hasil_riset_lain.txt

Dasar: research/berita_detik.tabel (petunjuk putaran 1: P, P3, KON, MOBIL, CPI, NOW, IND, KONT, KLAIM, SPX, BENSIN, SUARA —
ikut keluarga). PRA-REGISTRASI aturan BARU (ditulis SEBELUM evaluasi; tanda = angka utama DI ATAS konsensus, disimpan sebagai
arah USD → emas kebalikannya; hanya data yang terbit sebelum hari rilis):
  RETAIL  R_BENSIN  harga bensin eceran (FRED GASREGW mingguan) rata bulan acuan vs bulan sebelumnya ≥ +3% → penjualan nominal
                    di atas; ≤ −3% → di bawah.
          R_REDBOOK rata Redbook (Nasdaq, Act y/y %) bulan acuan vs bulan sebelumnya naik ≥ 0,5 poin → di atas; turun → di bawah.
  GDP     G_KAL     Kalshi KXGDP 1 jam sebelum tutup: P(atas) − P(bawah) ≥ 0,10 → searah (research/berita_detik.kalshi_lean).
          G_NOW5    GDPNow terakhir − konsensus ≥ +0,5 → di atas; ≤ −0,5 → di bawah (varian kuat aturan NOW 0,2).
  ADP     A_NFPP    kejutan NFP rilis lalu (≤ 40 hari) searah (pasar kerja bertahan).
  JOLTS   J_NFP     kejutan NFP bulan acuan JOLTS (NFP terbit 20–45 hari sebelum JOLTS) searah.
  CLAIMS  C_4W      rata 4 pekan (Nasdaq "Jobless Claims 4-Week Avg." Act pekan lalu) > konsensus → klaim di atas (konsensus
                    terlalu rendah dibanding tren) → USD turun; < → kebalikannya.
  KONSUMEN K_REVSPX hanya Michigan FINAL (prelim sudah terbit): S&P 500 naik ≥ 1% antara hari prelim dan sehari sebelum final →
                    final di atas konsensus (≈ prelim); turun ≥ 1% → di bawah.
          K_REVGAS  sama dengan harga bensin turun ≥ 2% → di atas; naik ≥ 2% → di bawah.
Evaluasi & LOLOS sama dengan CPI/PPI (research/lonjakan_uji tutup/keluarga 2.000×; ≥ 60% 2016–2026, > 50% LAMA & BARU n ≥ 8,
p keluarga < 0,05, ≥ 40 rilis ditebak sejak 2016, bisa dihitung live).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import baris, keluarga, tutup

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_lain.txt"
GRUP = ["RETAIL", "GDP", "ADP", "JOLTS", "CLAIMS", "KONSUMEN"]
BARU_ATURAN = {"RETAIL": ["R_BENSIN", "R_REDBOOK"], "GDP": ["G_KAL", "G_NOW5"], "ADP": ["A_NFPP"], "JOLTS": ["J_NFP"],
               "CLAIMS": ["C_4W"], "KONSUMEN": ["K_REVSPX", "K_REVGAS"]}


def _bulan(d: pd.Timestamp, k: int = 1) -> pd.Timestamp:
    return (d - pd.DateOffset(months=k)).to_period("M").to_timestamp()


def tambah(x: pd.DataFrame) -> pd.DataFrame:
    from .berita_detik import ambil, kalshi_lean, riwayat, sp500, us
    from .eksternal_makro import fred
    from .nasdaq_kalender import angka
    gas = fred("GASREGW")
    spx = sp500()
    gnow = __import__("research.berita_gabung", fromlist=["gdpnow"]).gdpnow()
    cache_rb: dict = {}

    def redbook(bln: pd.Timestamp) -> float:
        if bln not in cache_rb:
            v = []
            for d in pd.bdate_range(bln, bln + pd.offsets.MonthEnd(0)):
                for r in us(d):
                    if r["eventName"] == "Redbook":
                        a = angka(r["actual"])
                        if a == a:
                            v.append(a)
            cache_rb[bln] = float(np.mean(v)) if v else np.nan
        return cache_rb[bln]

    def harga_bulan(s: pd.DataFrame, bln: pd.Timestamp, t0: pd.Timestamp) -> float:
        ok = s[s.available < t0]
        a = ok.value[(ok.index >= bln) & (ok.index < bln + pd.offsets.MonthBegin(1))]
        return float(a.mean()) if len(a) else np.nan
    for c in sum(BARU_ATURAN.values(), []):
        x[c] = 0.0
    for i, r in x.iterrows():
        g, d, t0, arah = r.grup, r.d, r.t0, r.arah if r.arah == r.arah else 1.0
        num = {}
        if g == "RETAIL":
            ref = _bulan(d)
            a, b = harga_bulan(gas, ref, t0), harga_bulan(gas, _bulan(d, 2), t0)
            if a == a and b == b:
                ch = (a / b - 1) * 100
                num["R_BENSIN"] = 1.0 if ch >= 3 else -1.0 if ch <= -3 else 0.0
            a, b = redbook(ref), redbook(_bulan(d, 2))
            if a == a and b == b:
                num["R_REDBOOK"] = 1.0 if a - b >= 0.5 else -1.0 if a - b <= -0.5 else 0.0
        elif g == "GDP":
            v = ambil(d, r.nama) if isinstance(r.nama, str) else None
            f = v[1] if v else np.nan
            if f == f:
                num["G_KAL"] = kalshi_lean("KXGDP", None, t0, f)
                q = gnow[(gnow.rilis < t0) & (gnow.rilis >= t0 - pd.Timedelta(days=3))]
                if len(q):
                    dl = q.sort_values("rilis").now.iloc[-1] - f
                    num["G_NOW5"] = 1.0 if dl >= 0.5 else -1.0 if dl <= -0.5 else 0.0
        elif g == "ADP":
            nf = riwayat("Nonfarm Payrolls", d, 40)
            num["A_NFPP"] = nf[-1][1] if nf else 0.0
        elif g == "JOLTS":
            nf = [s for dd, s in riwayat("Nonfarm Payrolls", d, 45) if dd <= d - pd.Timedelta(days=20)]
            num["J_NFP"] = nf[-1] if nf else 0.0
        elif g == "CLAIMS":
            v = ambil(d, "Initial Jobless Claims")
            prev4 = None
            for dd in pd.bdate_range(d - pd.Timedelta(days=9), d - pd.Timedelta(days=1)):
                w = ambil(dd, "Jobless Claims 4-Week Avg.")
                if w and w[0] == w[0]:
                    prev4 = w[0]
            if v and prev4 is not None and v[1] == v[1] and prev4 != v[1]:
                num["C_4W"] = float(np.sign(prev4 - v[1]))
        elif g == "KONSUMEN" and r.nama == "Michigan Consumer Sentiment":
            pre = [dd for dd in pd.bdate_range(d - pd.Timedelta(days=20), d - pd.Timedelta(days=5))
                   if ambil(dd, "Michigan Consumer Sentiment")]
            if pre:
                p0 = pre[-1]
                s0 = spx[spx.available <= p0.tz_localize("UTC") + pd.Timedelta(days=1)].value
                s1 = spx[spx.available < t0].value
                if len(s0) and len(s1):
                    ch = (s1.iloc[-1] / s0.iloc[-1] - 1) * 100
                    num["K_REVSPX"] = 1.0 if ch >= 1 else -1.0 if ch <= -1 else 0.0
                g0 = gas[gas.available <= p0.tz_localize("UTC") + pd.Timedelta(days=1)].value
                g1 = gas[gas.available < t0].value
                if len(g0) and len(g1):
                    ch = (g1.iloc[-1] / g0.iloc[-1] - 1) * 100
                    num["K_REVGAS"] = -1.0 if ch >= 2 else 1.0 if ch <= -2 else 0.0
        for k, v in num.items():
            x.at[i, k] = arah * (v if v == v else 0.0)
    return x


def main() -> None:
    from .berita_detik import ATURAN, tabel
    bd = tabel()
    bd = bd[bd.grup.isin(GRUP)].copy()
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "grup", "arah"]].rename(columns={"arah": "L"})
    x = bd.merge(lj, on=["t0", "grup"], how="left")
    x = tambah(x)
    x["th"] = x.t0.dt.year
    rng = np.random.default_rng(17)
    L = ["# 🔬 Retail, GDP, ADP, JOLTS, klaim, konsumen → lonjakan menit 1 (research/riset_lain.py)",
         __doc__.split("\n\n")[1], ""]
    lolos = []
    for g in GRUP:
        z = x[(x.grup == g) & (x.th >= 2013) & x.L.notna()].sort_values("t0").reset_index(drop=True)
        if z.empty:
            continue
        aturan = ATURAN[g] + ["SUARA"] + BARU_ATURAN[g]
        for c in ATURAN[g]:
            if c not in z:
                z[c] = 0.0
        khusus = [c for c in ATURAN[g] if c not in ("P", "P3", "KON")]
        z["SUARA"] = np.sign(z[khusus + ["P"]].fillna(0).sum(axis=1))
        y, th = z.L.to_numpy(), z.th.to_numpy()
        C = {c: z[c].fillna(0).to_numpy() for c in aturan}
        kel = keluarga(C, y, th, rng)
        L.append(f"\n## {g} ({len(z)} rilis {z.t0.min():%Y-%m}–{z.t0.max():%Y-%m}; lonjakan naik {(y > 0).sum()}/{(y != 0).sum()})")
        L.append("   selalu NAIK  " + baris(np.ones(len(z)), y, z.t0, th)[0])
        for c in aturan:
            tb = tutup(C[c], y, th)
            teks, r = baris(tb, y, z.t0, th)
            p = kel.get(c)
            (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
            ok = bool(n and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5 and p
                      and min(p[:2]) < 0.05 and n >= 40)
            baru_tag = " (baru)" if c in BARU_ATURAN[g] else ""
            L.append(f"   {c:10s}{baru_tag:7s} {teks} | {'p %.3f/%.3f' % p[:2] if p else 'p –'}{'  ✅ LOLOS' if ok else ''}")
            if ok:
                lolos.append(f"{g} {c}")
    L.append("\nLOLOS: " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
