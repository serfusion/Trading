"""🔬 PPI putaran 3 — petunjuk & metode BARU + target detik 1–5 (13 Okt 2026).

python -m research.riset_ppi3        → docs/eksternal/hasil_riset_ppi3.txt + data/research/eksternal/riset_ppi3/tabel.parquet

Permintaan pengguna 13 Okt: "untuk PPI saya masih kurang puas, cari metode lain untuk uji validitas serta riset mendalam
seluruhnya". Yang sudah ada: putaran 1 (research/berita_detik.py) 0 lolos; putaran 2 (research/riset_inflasi.py, 12 aturan)
→ hanya WTI lolos (lonjakan 68%, detik 1 48% ≈ acak, modal kecil lemah). Putaran ini menambah:
  (a) TARGET detik 1/2/3/5/10 + lonjakan dari tick ASLI Exness untuk SEMUA rilis PPI Sep 2015–2026 (jendela yang belum ada
      diunduh: research/riset_dalam_data.tambah_bulan) — patokan pengguna detik 1–5;
  (b) PLAFON per komponen: emas mengikuti kejutan headline atau CORE (seperti CPI: core penggerak utama)?
  (c) PETUNJUK BARU (PRA-REGISTRASI — ditulis sebelum evaluasi; tanda = angka PPI m/m DI ATAS konsensus = baik untuk USD →
      tebakan emas kebalikannya):
      E_KOMB   keranjang energi grosir: rata-rata % ubah (5 obs s/d tgl 13 bulan acuan vs bulan sebelumnya) WTI, bensin Gulf
               (DGASUSGULF), solar Gulf (DDFUELUSGULF); ≥ +5% → di atas, ≤ −5% → di bawah. (WTI saja = aturan putaran 2.)
      E_GAP    seperti E_KOMB tetapi HANYA bila konsensus belum memasukkan energi: selisih konsensus headline − core ≤ +0,1
               (saat energi naik) / ≥ −0,1 (saat energi turun). Alasan: peramal kurang bereaksi pada energi.
      M_BALIK  margin dagang (PPI final demand trade services PPITSS, nilai rilis pertama) bulan lalu m/m ≥ +0,8% → di bawah,
               ≤ −0,8% → di atas (margin berbalik; komponen paling liar di PPI).
      M_EN     energi naik ≥ 5% → margin SPBU/grosir tertekan → CORE di bawah (dan sebaliknya) → tanda USD = −tanda energi.
               Diuji karena emas mungkin bereaksi pada core (alasan detik 1 aturan WTI ≈ acak).
      CPIC     CPI bulan acuan yang sama sudah rilis ≤ 10 hari sebelum PPI: tanda kejutan CORE CPI searah (CPIH = headline
               CPI). Alasan: guncangan harga bersama; konsensus PPI sering dibuat sebelum CPI keluar.
      MUS      musiman: tanda rata-rata kejutan PPI headline bulan kalender yang sama di tahun-tahun SEBELUMNYA (≥ 3 tahun).
      KONC     angka core PPI bulan lalu (rilis pertama) > konsensus core → core di atas (analis menebak berbalik terlalu cepat).
      GABUNG   tanda (WTI + E_GAP + M_BALIK + CPIC) — kombinasi ditetapkan sebelum melihat hasil.
      MODEL    regresi logistik L2 walk-forward per tahun (latih hanya tahun < Y, ≥ 30 rilis) memakai SEMUA petunjuk putaran
               2 & 3 → tebak bila |p − 0,5| ≥ 0,10. Metode berbeda dari aturan tunggal.
  (d) EVALUASI sama dengan putaran 2 (tutup kertas lonjakan, LAMA/BARU/2022+, permutasi keluarga 2.000×) dengan keluarga =
      12 aturan putaran 2 + 10 aturan baru (22) — koreksi banyak-uji lintas putaran. Ditambah detik 1/2/3/5 dan subset
      bersamaan/sendiri (PPI 15 Okt 2026 bersamaan dengan Retail Sales, Empire, Philly, klaim).
Uji validitas lanjutan (bootstrap blok tahun, Bayes, mekanisme, plasebo, feed, rolling, holdout, modal kecil) di
research/riset_ppi3_cek.py.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import baris, keluarga, sk, tutup
from .riset_dalam_data import EKS, _num, ff_mentah, satu

ROOT = Path(__file__).resolve().parent.parent
DIR = EKS / "riset_ppi3"
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_ppi3.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
LAMA2 = ["P", "KONV", "YOY", "CPIX", "IMPOR", "ISMP", "WTI", "BENSIN", "SAHAM", "SUARA", "PBALIK", "KONBALIK"]
BARU3 = ["E_KOMB", "E_GAP", "M_BALIK", "M_EN", "CPIC", "CPIH", "MUS", "KONC", "GABUNG", "MODEL"]
DET = ("d1", "d2", "d3", "d5", "d10")


def sg(v, batas: float = 0.0) -> float:
    return 0.0 if v is None or v != v or abs(v) < batas or v == 0 else float(np.sign(v))


def fred_harian(seri: str) -> pd.Series:
    from .eksternal_makro import fred
    d = fred(seri)
    return pd.Series(d.value.to_numpy(), index=d.index)


def jendela13(s: pd.Series, ref: pd.Timestamp) -> float:
    batas = ref + pd.Timedelta(days=12)
    x = s[s.index <= batas].iloc[-5:]
    return float(x.mean()) if len(x) == 5 and (batas - x.index[-1]).days < 7 else np.nan


def core_ppi() -> pd.DataFrame:
    """Act & konsensus core PPI m/m per tanggal rilis (FF mentah ≤ 2023, Nasdaq 2024+; m/m = baris dengan |prev| kecil)."""
    ff = ff_mentah()
    a = ff[ff.event == "Core PPI m/m"][["t0", "actual", "forecast"]].rename(columns={"actual": "ca", "forecast": "cf"})
    a["d"] = a.t0.dt.tz_convert("America/New_York").dt.date
    rows = []
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "*.json"))):
        if Path(f).stem < "2024-01-01":
            continue
        g = [r for r in json.loads(Path(f).read_text(encoding="utf-8"))
             if r.get("eventName") == "Core PPI" and r.get("country") == "United States"]
        if len(g) >= 2:
            g = sorted(g[:2], key=lambda r: abs(_num(r.get("previous"))) if _num(r.get("previous")) == _num(
                r.get("previous")) else 99)
            rows.append({"d": pd.Timestamp(Path(f).stem).date(), "ca": g[0].get("actual"), "cf": g[0].get("consensus")})
    b = pd.DataFrame(rows)
    x = pd.concat([a[["d", "ca", "cf"]], b], ignore_index=True).drop_duplicates("d")
    x["ca"], x["cf"] = x.ca.map(_num), x.cf.map(_num)
    return x


def tabel(segar: bool = False) -> pd.DataFrame:
    f = DIR / "tabel.parquet"
    if f.exists() and not segar:
        return pd.read_parquet(f)
    DIR.mkdir(parents=True, exist_ok=True)
    p = pd.read_pickle(EKS / "riset_inflasi" / "petunjuk.parquet")
    p = p[(p.grup == "PPI") & (p.t0 >= pd.Timestamp("2015-09-01", tz="UTC"))].copy().reset_index(drop=True)
    tg = pd.DataFrame([satu(t) for t in p.t0])                      # tick Exness (jendela lama + tambahan)
    p = p.merge(tg[["t0", "arah", "besar", "d1", "d2", "d3", "d5", "d10", "d60", "spread0"]], on="t0", how="left",
                suffixes=("", "_ex"))
    p["arah"] = p.arah.fillna(p.L)                                   # cadangan target putaran 2 (Dukascopy)
    for h in (2, 3, 5, 10):
        p[f"d{h}"] = p[f"d{h}"].fillna(p[f"g{h}"])
    p["d"] = p.t0.dt.tz_convert("America/New_York").dt.date
    p = p.merge(core_ppi(), on="d", how="left")
    p["s_core"] = np.sign(p.ca - p.cf)
    p["s_head"] = np.sign(p.am - p.cm)
    # rilis bersamaan (Retail/CPI/NFP/GDP …) di menit yang sama: jadwal riset_dalam (Retail/GDP) + kolom putaran 2
    from .riset_dalam_data import jadwal
    j = jadwal()
    besar = set(j[j.grup.isin(["RETAIL", "GDP"])].t0.dt.floor("min"))
    p["dgn_retail"] = p.t0.dt.floor("min").isin(besar) | p.bersama.fillna("").str.contains("RETAIL|Retail")
    p.to_parquet(f)
    return p


def petunjuk(p: pd.DataFrame) -> pd.DataFrame:
    wti, gas, dsl = fred_harian("DCOILWTICO"), fred_harian("DGASUSGULF"), fred_harian("DDFUELUSGULF")
    from .pra_per_berita import fred_awal
    tr = fred_awal("PPITSS")
    from . import cpi_detik as C
    cpi = C.tabel()[["t0", "s_core", "s_mm"]].rename(columns={"t0": "t_cpi", "s_core": "cpi_core", "s_mm": "cpi_mm"})
    cpi["t_cpi"] = pd.to_datetime(cpi.t_cpi, utc=True)
    for c in BARU3:
        p[c] = 0.0
    p["E"] = np.nan
    for i, r in p.iterrows():
        ref = pd.Timestamp(r.ref)
        prv = (ref.to_period("M") - 1).to_timestamp()
        ch = []
        for s in (wti, gas, dsl):
            a, b = jendela13(s, ref), jendela13(s, prv)
            if a == a and b == b and b > 0:
                ch.append((a / b - 1) * 100)
        if len(ch) >= 2:
            e = float(np.mean(ch))
            p.at[i, "E"] = e
            p.at[i, "E_KOMB"] = sg(e, 5.0)
            gap = r.cm - r.cf if r.cm == r.cm and r.cf == r.cf else np.nan
            if gap == gap and ((e >= 5 and gap <= 0.1) or (e <= -5 and gap >= -0.1)):
                p.at[i, "E_GAP"] = sg(e, 5.0)
            p.at[i, "M_EN"] = -sg(e, 5.0)
        # margin dagang bulan lalu (nilai rilis pertama, terbit sebelum t0)
        ok = tr[tr.available < r.t0]
        if prv in ok.index and (prv.to_period("M") - 1).to_timestamp() in ok.index:
            m = (ok.value[prv] / ok.value[(prv.to_period("M") - 1).to_timestamp()] - 1) * 100
            p.at[i, "M_BALIK"] = -sg(m, 0.8)
        # CPI bulan acuan sama sudah rilis ≤ 10 hari sebelumnya
        c = cpi[(cpi.t_cpi < r.t0) & (cpi.t_cpi >= r.t0 - pd.Timedelta(days=10))]
        if len(c):
            p.at[i, "CPIC"] = sg(c.cpi_core.iloc[-1])
            p.at[i, "CPIH"] = sg(c.cpi_mm.iloc[-1])
        # musiman: kejutan headline bulan kalender sama, tahun-tahun lalu
        lalu = p[(p.t0 < r.t0 - pd.Timedelta(days=200)) & (p.t0.dt.month == r.t0.month) & p.s_head.notna()]
        if lalu.t0.dt.year.nunique() >= 3:
            p.at[i, "MUS"] = sg(lalu.s_head.mean())
        # core bulan lalu (Act rilis sebelumnya) vs konsensus core
        sb = p[(p.t0 < r.t0) & p.ca.notna()]
        if len(sb) and r.cf == r.cf:
            p.at[i, "KONC"] = sg(sb.ca.iloc[-1] - r.cf)
    p["GABUNG"] = np.sign(p[["WTI", "E_GAP", "M_BALIK", "CPIC"]].fillna(0).sum(axis=1))
    return p


def model(p: pd.DataFrame) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    fit = [c for c in LAMA2 + BARU3 if c not in ("MODEL", "GABUNG", "SUARA")]
    X = p[fit].fillna(0).to_numpy()
    y = p.arah.fillna(0).to_numpy()
    th = p.t0.dt.year.to_numpy()
    out = np.zeros(len(p))
    for Y in sorted(set(th)):
        m = (th < Y) & (y != 0)
        if m.sum() < 30:
            continue
        lr = LogisticRegression(C=0.5, max_iter=500).fit(X[m], (y[m] > 0).astype(int))
        pr = lr.predict_proba(X[th == Y])[:, 1]
        # disimpan sebagai tanda USD (tebakan emas = −) supaya seragam dengan aturan lain
        out[th == Y] = np.where(pr >= 0.6, -1.0, np.where(pr <= 0.4, 1.0, 0.0))
    return out


def plafon(p: pd.DataFrame, L: list) -> None:
    L.append("\n## Bila kejutan SUDAH diketahui (PLAFON): emas berlawanan dengan komponen mana? (2015-09–2026)")
    x = p[p.t0.dt.year >= 2016]
    for nama, s in (("headline m/m", x.s_head), ("core m/m", x.s_core),
                    ("core dulu, lalu headline", pd.Series(np.where(x.s_core.fillna(0) != 0, x.s_core, x.s_head), x.index)),
                    ("headline & core sepakat", pd.Series(np.where(x.s_head == x.s_core, x.s_head, 0), x.index))):
        g = -s.fillna(0)
        isi = []
        for kol in ("arah",) + DET:
            y = x[kol].fillna(0)
            ok = (g != 0) & (y != 0)
            isi.append(f"{'lonjakan' if kol == 'arah' else kol} {(g[ok] == y[ok]).mean() * 100:.0f}% ({int(ok.sum())})"
                       if ok.any() else f"{kol} –")
        L.append(f"   {nama:26s} " + " | ".join(isi))


def main() -> None:
    p = petunjuk(tabel())
    p["MODEL"] = model(p)
    p.to_parquet(DIR / "fitur.parquet")
    L = ["# 🔬 PPI putaran 3 (research/riset_ppi3.py)", __doc__.split("\n\n")[1], ""]
    L.append(f"Rilis PPI Sep 2015–2026: {len(p)}; target lonjakan ada {int(p.arah.notna().sum())}; tick Exness detik 1 ada "
             f"{int(p.d1.notna().sum())}; bersamaan Retail/GDP {int(p.dgn_retail.sum())}")
    plafon(p, L)
    aturan = LAMA2 + BARU3
    y, th, t0 = p.arah.fillna(0).to_numpy(), p.t0.dt.year.to_numpy(), p.t0
    C = {c: p[c].fillna(0).to_numpy() for c in aturan}
    rng = np.random.default_rng(15)
    kel = keluarga(C, y, th, rng)
    L.append("\n## Tutup kertas — target lonjakan (2016–2026 | LAMA | BARU | 2022+ | 2026) + p keluarga 22 aturan + detik 1–5")
    L.append("   selalu NAIK  " + baris(np.ones(len(p)), y, t0, th)[0])
    hasil = {}
    for c in aturan:
        v = C[c]
        tb = tutup(v, y, th)
        s, r = baris(tb, y, t0, th)
        pk = kel.get(c)
        (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
        n16 = int(((v != 0) & (th >= 2016)).sum())
        ok = bool(pk and n and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5
                  and min(pk[0], pk[1]) < 0.05 and n16 >= 40)
        det = []
        for kol in DET[:4]:
            yy = p[kol].fillna(0).to_numpy()
            kk, nn = sk(tutup(v, yy, th), yy, th >= 2016)
            det.append(f"{kol} {kk / nn * 100:.0f}%" if nn else f"{kol} –")
        ang = (p[c] != 0) & (p.s_head.fillna(0) != 0)
        angc = (p[c] != 0) & (p.s_core.fillna(0) != 0)
        L.append(f"   {c:9s} {s}" + (f" | p {pk[0]:.3f}/{pk[1]:.3f}" if pk else " | p –") + f" | {' '.join(det)} | angka "
                 f"head {(p[c][ang] == p.s_head[ang]).mean() * 100:.0f}% core {(p[c][angc] == p.s_core[angc]).mean() * 100:.0f}%"
                 + ("  ✅ LOLOS" if ok else ""))
        hasil[c] = {"semua": r["semua"], "lama": r["LAMA"], "baru": r["BARU"], "p": pk[:2] if pk else None, "lolos": ok}
    # PPI 15 Okt 2026: nilai petunjuk (konsensus Nasdaq 0,5% / core 0,3%)
    L.append("\n## Nilai petunjuk PPI 15 Okt 2026 dihitung di research/riset_ppi3_cek.py (bagian 'hari ini')")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR / "hasil.json").write_text(json.dumps(hasil, default=str, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
