"""🔎 CPI: uji SEMUA sumber yang tersisa + model gabungan + keterlambatan eksekusi → docs/eksternal/hasil_cpi_semua.txt

python -m research.cpi_semua [sinyal|model|telat|semua]

Permintaan pengguna 13 Okt 2026 "uji semua" (setelah daftar "belum diuji" di docs/CPI_ALLIN.md). Aturan ditetapkan sebelum
melihat hasil; tanda +1 = CPI diduga DI ATAS konsensus → emas TURUN. Setiap nilai hanya dipakai bila terbit SEBELUM tanggal
rilis CPI (tanpa look-ahead).
A. Kalender Nasdaq (cache data/research/eksternal/nasdaq, rilis terakhir ≤ 40 hari sebelum CPI): ISM manufaktur harga,
   ISM jasa harga, PPI, core PPI, harga impor, NFIB, Michigan 1 th, Fed NY ekspektasi 1 th, Philly harga bayar —
   masing-masing *_chg = tanda(Act − sebelumnya) dan *_sur = tanda(Act − konsensus).
B. Manheim (mobil bekas, xlsx resmi 1997–Nov 2025, terbit ±hari kerja ke-5 bulan berikut): perubahan SA 2 bulan sebelum
   bulan acuan (lag harga lelang → CPI mobil bekas), ambang ±2%.
C. Zillow ZORI nasional (sewa, terbit pertengahan bulan berikut): m/m 12 bulan sebelum bulan acuan vs rata-rata 12 bulan
   sebelumnya (sewa baru → CPI shelter ±12 bulan), ambang ±0,1 poin.
D. Cleveland Fed nowcast (cpi_cleveland), breakeven/UMich/harga bayar Fed (cpi_lain2) — ikut model gabungan.
E. Model gabungan: regresi logistik semua fitur (+ aturan aplikasi IDX, Kalshi), latih tahun < Y, tebak tahun Y (tutup
   kertas), target = arah emas detik 2.
F. Banyak-uji: berapa sinyal tunggal "lolos" (detik 2 ≥ 60% & LAMA > 50% & BARU > 50%, n ≥ 20) vs arah emas diacak 500×.
G. Telat eksekusi strategi modal kecil (tebakan kuat, tick Exness): masuk t−1,5/−1/−0,5/−0,2 dtk; keputusan lentur detik 2
   dieksekusi detik 2/2,5/3; tutup akhir detik 10/10,5/11.
Sumber yang TIDAK bisa diuji: CME (403), Bloomberg/Reuters (berbayar), Truflation (API berkunci), opsi emas (berbayar).
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_semua.txt"
NAS = {"ISMM": "ISM Manufacturing Prices", "ISMS": "ISM Non-Manufacturing Prices", "PPI": "PPI", "CPPI": "Core PPI",
       "IMP": "Import Price Index", "NFIB": "NFIB Small Business Optimism", "UM1": "Michigan 1-Year Inflation Expectations",
       "NY1": "NY Fed 1-Year Consumer Inflation Expectations", "PHPP_N": "Philly Fed Prices Paid"}


def _angka(s: str) -> float:
    from .nasdaq_kalender import angka
    return angka(s)


def nasdaq_rows() -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(EKS / "nasdaq" / "*.json")):
        tgl = pd.Timestamp(Path(f).stem)
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for r in d:
            if r.get("country") != "United States":
                continue
            for k, nama in NAS.items():
                if r["eventName"] == nama:
                    rows.append({"k": k, "tgl": tgl, "a": _angka(r["actual"]), "f": _angka(r["consensus"]),
                                 "p": _angka(r["previous"])})
    x = pd.DataFrame(rows)
    # PPI/Core PPI punya baris m/m & y/y: pakai yang |nilai| terkecil per tanggal (m/m)
    x["abs"] = x.p.abs()
    return x.sort_values(["k", "tgl", "abs"]).drop_duplicates(["k", "tgl"])


def sinyal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    nas = nasdaq_rows()
    ny = df.t0.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    for k in NAS:
        sub = nas[nas.k == k]
        chg, sur = [], []
        for t in ny:
            v = sub[(sub.tgl < t) & (sub.tgl >= t - pd.Timedelta(days=40))]
            if not len(v):
                chg.append(0.0)
                sur.append(0.0)
                continue
            r = v.sort_values("tgl").iloc[-1]
            chg.append(C.sgn(r.a - r.p))
            sur.append(C.sgn(r.a - r.f))
        df[f"{k}_chg"], df[f"{k}_sur"] = chg, sur
    if "NFIB_chg" in df:                                   # optimisme naik ≠ inflasi naik: dibiarkan apa adanya (diuji dua arah lewat tetap)
        pass
    # B. Manheim
    m = pd.read_excel(EKS / "cpi_lain" / "manheim.xlsx", sheet_name="DATA", header=None).iloc[1:, [0, 2]]
    m.columns = ["bln", "sa"]
    m = m.dropna().set_index(pd.to_datetime(m.bln)).sa.astype(float)
    out = []
    for t in ny:
        ref = (t - pd.DateOffset(months=1)).to_period("M").to_timestamp()
        a, b = ref - pd.DateOffset(months=2), ref - pd.DateOffset(months=4)
        if a in m.index and b in m.index and t >= ref + pd.DateOffset(months=1, days=7):
            ch = m[a] / m[b] - 1
            out.append(1.0 if ch > 0.02 else -1.0 if ch < -0.02 else 0.0)
        else:
            out.append(0.0)
    df["MANHEIM"] = out
    # C. Zillow ZORI nasional
    z = pd.read_csv(EKS / "cpi_lain" / "zori_us.csv")
    z = z[z.RegionName == "United States"].iloc[0, 5:].astype(float)
    z.index = pd.to_datetime(z.index).to_period("M").to_timestamp()
    zm = z.pct_change() * 100
    out = []
    for t in ny:
        ref = (t - pd.DateOffset(months=1)).to_period("M").to_timestamp()
        a = ref - pd.DateOffset(months=12)
        hist = zm[(zm.index < a) & (zm.index >= a - pd.DateOffset(months=12))]
        if a in zm.index and len(hist) >= 6 and zm[a] == zm[a]:
            d = zm[a] - hist.mean()
            out.append(C.sgn(d, 0.1))
        else:
            out.append(0.0)
    df["ZORI"] = out
    return df


def tambah_semua(df: pd.DataFrame) -> pd.DataFrame:
    from .cpi_cleveland import nowcast, pasang
    from .cpi_lain2 import tambah
    df = pasang(df, nowcast(), 0.05)
    df = tambah(df)
    return sinyal(df)


KOLOM_TUNGGAL = [f"{k}_{s}" for k in NAS for s in ("chg", "sur")] + ["MANHEIM", "ZORI", "CLV_mm", "CLV_core", "CLV",
                                                                      "BEI5", "MICH", "NYPP", "NYPR", "PHPP", "PHPR"]


def uji_sinyal(df: pd.DataFrame) -> tuple[list[str], int]:
    m = df.th >= C.MULAI
    lama, baru = m & (df.t0 < "2021-10-01"), df.t0 >= "2021-10-01"

    def acc(tb, mask, hs):
        k, n = C.tepat(df[mask], tb[mask], hs)
        return (k / n * 100 if n else np.nan), n // len(hs)
    L, lolos = ["## A–D. Sinyal tunggal (tutup kertas; emas detik 2 | detik 2–10; kejutan CPI/core)"], 0
    for k in KOLOM_TUNGGAL:
        if k not in df:
            continue
        tb = C.tetap(df, k)
        a2, n2 = acc(tb, m, (2,))
        al, _ = acc(tb, lama, (2,))
        ab, _ = acc(tb, baru, (2,))
        a210, _ = acc(tb, m, C.JAUH)
        okm = (df[k] != 0) & (df.s_mm != 0)
        okc = (df[k] != 0) & (df.s_core != 0)
        km = (df[k][okm] == df.s_mm[okm]).mean() * 100 if okm.sum() else np.nan
        kc = (df[k][okc] == df.s_core[okc]).mean() * 100 if okc.sum() else np.nan
        ok = n2 >= 20 and a2 >= 60 and al > 50 and ab > 50
        lolos += ok
        r2, rn = acc(-df[k], m, (2,))                   # mentah (tanpa saringan tutup kertas)
        if n2 == 0:
            a2 = al = ab = a210 = np.nan                # tidak pernah lolos syarat tutup kertas (ketepatan lalu ≤ 50%)
        L.append(f"   {k:11s} mentah detik 2 {r2:4.0f}% (n {rn:3}) | tutup kertas detik 2 {a2:4.0f}% (n {n2:3}) lama {al:4.0f}% "
                 f"baru {ab:4.0f}% | 2–10 {a210:4.0f}% | kejutan CPI "
                 f"{km:3.0f}% core {kc:3.0f}% (n {okm.sum()}) {'← lolos' if ok else ''}")
    return L, lolos


def acak_lolos(df: pd.DataFrame, n_acak: int = 200) -> list[int]:
    """Berapa sinyal tunggal 'lolos' bila arah emas diacak per rilis (semua detik ikut dibalik bersama)."""
    rng = np.random.default_rng(5)
    hasil = []
    gcols = [f"g{h}" for h in C.DET]
    for _ in range(n_acak):
        d = df.copy()
        flip = rng.choice([-1.0, 1.0], size=len(d))
        for c in gcols:
            d[c] = d[c] * flip
        _, n = uji_sinyal(d)
        hasil.append(n)
    return hasil


def model(df: pd.DataFrame) -> list[str]:
    from sklearn.linear_model import LogisticRegression
    fitur = [k for k in KOLOM_TUNGGAL if k in df] + ["IDX|K", "mm_K", "core_K"]
    X = df[fitur].fillna(0).to_numpy()
    y = np.sign(df.g2.fillna(0)).to_numpy()
    tebak = np.zeros(len(df))
    for th in range(C.MULAI + 3, int(df.th.max()) + 1):
        tr = (df.th < th).to_numpy() & (y != 0)
        te = (df.th == th).to_numpy()
        if tr.sum() < 30 or not te.any():
            continue
        lr = LogisticRegression(C=0.3, max_iter=500).fit(X[tr], y[tr])
        p = lr.predict_proba(X[te])[:, list(lr.classes_).index(1.0)]
        tebak[te] = np.where(p >= 0.55, 1.0, np.where(p <= 0.45, -1.0, 0.0))
    tb = pd.Series(tebak, index=df.index)          # sudah arah EMAS
    m = df.th >= C.MULAI + 3
    lama, baru = m & (df.t0 < "2021-10-01"), df.t0 >= "2021-10-01"
    ts = C.tetap(df, "IDX|K+S")

    def st(t, mask, hs=(2,)):
        k, n = C.tepat(df[mask], t[mask], hs)
        return f"{k / n * 100:3.0f}% ({n // len(hs)})" if n else "–"
    L = ["\n## E. Model gabungan (logistik, walk-forward per tahun, target emas detik 2, |p−0,5| ≥ 0,05)",
         f"   fitur: {len(fitur)}",
         f"   model     detik 2: semua {st(tb, m)} lama {st(tb, lama)} baru {st(tb, baru)} | 2–10 {st(tb, m, C.JAUH)}",
         f"   aplikasi  detik 2: semua {st(ts, m)} lama {st(ts, lama)} baru {st(ts, baru)} | 2–10 {st(ts, m, C.JAUH)}"]
    sep = ts.where((ts != 0) & (tb == ts), 0)
    lw = ts.where((ts != 0) & (tb != 0) & (tb != ts), 0)
    L.append(f"   aplikasi & model sepakat detik 2: {st(sep, m)} lama {st(sep, lama)} baru {st(sep, baru)} | berlawanan "
             f"{st(lw, m)}")
    return L


def telat() -> list[str]:
    from .cpi_allin2 import MODAL, SPLIT, arr
    from .exness import ticks_around
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    ts = C.tetap(df, "IDX|K+S")
    A = {i: arr(tk, r.t0) for i, r in df.iterrows() if ts.iloc[i] != 0 and (tk := ticks_around("XAUUSDc", r.t0)) is not None}

    def jalan(a, g, masuk, putus, eks2, akhir, lev):
        s, bid, ask = a
        i0 = np.searchsorted(s, masuk, side="right") - 1
        if i0 < 0 or masuk - s[i0] > 30:
            return None
        px0 = ask[i0] if g > 0 else bid[i0]
        oz = MODAL * lev / px0
        kp = bid if g > 0 else ask

        def pl_s(h):
            i1 = np.searchsorted(s, h, side="right") - 1
            seg = kp[i0 + 1:i1 + 1]
            return oz * (seg - px0) * g if len(seg) else None
        p_put = pl_s(putus)                                 # yang DILIHAT di detik 2
        p_eks = pl_s(eks2)                                  # yang DIDAPAT bila tutup (eksekusi telat)
        if p_put is None or p_eks is None:
            return None
        if p_eks.min() <= -MODAL:
            return -MODAL, True
        if p_put[-1] <= 0:
            return float(p_eks[-1]), False
        p_akh = pl_s(akhir)
        if p_akh is None:
            return None
        return (-MODAL, True) if p_akh.min() <= -MODAL else (float(p_akh[-1]), False)
    L = ["\n## G. Telat eksekusi (tebakan kuat, lentur, tick Exness, rata-rata per $100 sejak 2022 | LAMA)"]
    for masuk in (-1.5, -1.0, -0.5, -0.2):
        for eks2, akhir in ((2.0, 10.0), (2.5, 10.5), (3.0, 11.0)):
            for lev in (200, 500):
                rec = []
                for i, a in A.items():
                    o = jalan(a, int(np.sign(ts.iloc[i])), masuk, 2.0, eks2, akhir, lev)
                    if o:
                        rec.append((df.t0[i], *o))
                x = pd.DataFrame(rec, columns=["t0", "pl", "mc"])
                b, lm = x[x.t0 >= SPLIT], x[x.t0 < SPLIT]
                L.append(f"   masuk {masuk:+.1f} dtk • tutup rugi di {eks2:.1f} • akhir {akhir:.1f} • 1:{lev:<3} | untung "
                         f"{(b.pl > 0).mean() * 100:3.0f}% ${b.pl.mean():+6.1f} habis {int(b.mc.sum())} | lama ${lm.pl.mean():+6.1f}")
    return L


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "semua"
    L = ["# 🔎 CPI: uji semua sumber tersisa (research/cpi_semua.py)", __doc__.split("\n\n")[1], ""]
    if cmd in ("sinyal", "model", "semua"):
        df = tambah_semua(C.turunan(C.tabel()))
        if cmd in ("sinyal", "semua"):
            S, n = uji_sinyal(df)
            L += S
            ac = acak_lolos(df)
            L.append(f"\n## F. Banyak-uji: lolos {n} dari {sum(k in df for k in KOLOM_TUNGGAL)} sinyal; bila arah emas diacak "
                     f"(200×) rata-rata lolos {np.mean(ac):.1f}, ≥ {n} pada {np.mean(np.array(ac) >= n) * 100:.0f}% acakan")
        if cmd in ("model", "semua"):
            L += model(df)
    if cmd in ("telat", "semua"):
        L += telat()
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
