"""🔎 Sumber lain selain Kalshi untuk menebak kejutan berita USD (Act vs konsensus) — dan apakah menambah ketepatan.

python -m research.sumber_lain            → docs/eksternal/hasil_sumber_lain.txt

Permintaan pengguna 10 Okt 2026: "cari informasi, kumpulkan, riset dan uji validitas di manapun selain Kalshi, siapa tahu
ada sumber lain". Sumber yang bisa diunduh lengkap dengan riwayat (FRED dengan tanggal terbit vintage = tanpa look-ahead;
nilai revisi terakhir dipakai — revisi survei kecil, dicatat sebagai keterbatasan) + lowongan Indeed (GitHub Hiring Lab).
Aturan tanda DITETAPKAN SEBELUM melihat hasil (naik = angka di atas konsensus, kecuali disebut terbalik):
  INFLASI (CPI, core CPI, CPI y/y, PPI, core PPI, core PCE):
    BE5   breakeven inflasi 5 th (T5YIE) naik 5 hari bursa sebelum rilis
    Y2    yield 2 th (DGS2) naik 5 hari sebelum rilis (pasar sudah menebak data panas)
    WTI   rata-rata minyak WTI bulan acuan > bulan sebelumnya (headline CPI/PPI saja)
    PP    survei Fed daerah "harga yang dibayar" (Philly, Empire, Dallas) naik dari bulan sebelumnya (rata tanda)
    MICH  ekspektasi inflasi UMich naik
  TENAGA KERJA (NFP; pengangguran terbalik):
    Y2    yield 2 th naik 5 hari    EMP  survei Fed daerah jumlah karyawan (Empire, Philly) naik
    CC    klaim berlanjut (CCSA) 4 pekan terakhir naik → NFP DI BAWAH (pengangguran DI ATAS)
    IND   lowongan Indeed bulan acuan naik (2020+)   WEI  indeks ekonomi mingguan (WEI) naik 4 pekan
  AKTIVITAS (ISM manufaktur & jasa, Retail Sales, core retail, GDP):
    GA    survei Fed daerah aktivitas umum (Philly, Empire) naik     WEI, Y2 seperti di atas
  JOLTS: IND (2020+), EMP, CC (terbalik).
Diuji sendiri-sendiri lalu digabung dengan petunjuk terbaik yang sudah ada (berita_gabung: Kalshi/kejutan lalu/GDPNow/
berbalik): "sepakat" dan "cadangan", dan model logistik walk-forward per tahun (latih hanya tahun sebelumnya).
Lolos = > 50% di LAMA (< Okt 2021) & BARU, p binomial < 0,05 (n ≥ 8 per periode; bila hanya BARU n ≥ 15).
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .berita_gabung import emas, emas_hit, nilai, tabel, teks

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_sumber_lain.txt"
INDEED = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/aggregate_job_postings_US.csv"
INFLASI = ["CPI m/m", "Core CPI m/m", "CPI y/y", "PPI m/m", "Core PPI m/m", "Core PCE Price Index m/m"]
KERJA = ["Non-Farm Employment Change", "Unemployment Rate", "ADP Non-Farm Employment Change"]
AKTIF = ["ISM Manufacturing PMI", "ISM Services PMI", "Retail Sales m/m", "Core Retail Sales m/m", "Advance GDP q/q"]
TERBALIK = ("Unemployment Rate",)
FITUR = {j: ["BE5", "Y2", "WTI", "PP", "MICH"] for j in INFLASI}
FITUR.update({j: ["Y2", "EMP", "CC", "IND", "WEI"] for j in KERJA})
FITUR.update({j: ["GA", "WEI", "Y2"] for j in AKTIF})
FITUR["JOLTS Job Openings"] = ["IND", "EMP", "CC"]


def seri(nama: str) -> pd.DataFrame:
    from .eksternal_makro import fred
    return fred(nama)


def terbit(df: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    """Nilai yang SUDAH terbit sebelum waktu t (index = tanggal data)."""
    return df.value[df.available < t]


def ubah(df: pd.DataFrame, t: pd.Timestamp, lag: int) -> float:
    s = terbit(df, t)
    return float(s.iloc[-1] - s.iloc[-1 - lag]) if len(s) > lag else np.nan


def ubah_bulan(df: pd.DataFrame, t: pd.Timestamp) -> float:
    """Rata-rata bulan acuan (bulan sebelum rilis) − bulan sebelumnya, hanya data terbit."""
    s = terbit(df, t)
    ref = (t - pd.DateOffset(months=1)).to_period("M")
    per = pd.DatetimeIndex(s.index).to_period("M")
    a, b = s[per == ref], s[per == ref - 1]
    return float(a.mean() - b.mean()) if len(a) and len(b) else np.nan


def indeed() -> pd.DataFrame:
    p = ROOT / "data" / "research" / "eksternal" / "indeed_postings_us.csv"
    if not p.exists():
        with urllib.request.urlopen(INDEED, timeout=60) as r:
            p.write_bytes(r.read())
    d = pd.read_csv(p, parse_dates=["date"])
    d = d[d.variable == "total postings"].set_index("date").indeed_job_postings_index_SA
    # Indeed memperbarui ± tiap pekan dengan jeda ±7 hari → anggap terbit 7 hari setelah tanggal data
    return pd.DataFrame({"value": d.to_numpy(), "available": (d.index + pd.Timedelta(days=7)).tz_localize("UTC")},
                        index=d.index)


def fitur(df: pd.DataFrame) -> pd.DataFrame:
    S = {k: seri(k) for k in ("T5YIE", "DGS2", "DCOILWTICO", "PPCDFSA066MSFRBPHI", "PPCDISA066MSFRBNY",
                              "PRMSAMFRBDAL", "MICH", "NECDISA066MSFRBNY", "NFBNDIF066MSFRBPHI", "CCSA", "WEI",
                              "GACDFSA066MSFRBPHI", "GACDISA066MSFRBNY")}
    ind = indeed()
    rows = []
    for r in df.itertuples():
        t, f = r.t0, {}
        sg = lambda v: 0.0 if v != v or v == 0 else float(np.sign(v))  # noqa: E731
        f["BE5"] = sg(ubah(S["T5YIE"], t, 5))
        f["Y2"] = sg(ubah(S["DGS2"], t, 5))
        f["WTI"] = sg(ubah_bulan(S["DCOILWTICO"], t)) if r.event in ("CPI m/m", "CPI y/y", "PPI m/m") else 0.0
        f["PP"] = sg(sum(sg(ubah(S[k], t, 1)) for k in ("PPCDFSA066MSFRBPHI", "PPCDISA066MSFRBNY", "PRMSAMFRBDAL")))
        f["MICH"] = sg(ubah(S["MICH"], t, 1))
        f["EMP"] = sg(sum(sg(ubah(S[k], t, 1)) for k in ("NECDISA066MSFRBNY", "NFBNDIF066MSFRBPHI")))
        f["CC"] = -sg(ubah(S["CCSA"], t, 4))
        f["WEI"] = sg(ubah(S["WEI"], t, 4))
        f["GA"] = sg(sum(sg(ubah(S[k], t, 1)) for k in ("GACDFSA066MSFRBPHI", "GACDISA066MSFRBNY")))
        f["IND"] = sg(ubah_bulan(ind, t)) if t >= pd.Timestamp("2020-04-01", tz="UTC") else np.nan
        if r.event in TERBALIK:                       # pengangguran: data kerja kuat → angka DI BAWAH
            f = {k: -v if v == v else v for k, v in f.items()}
        rows.append(f)
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def logit_wf(x: pd.DataFrame, cols: list[str]) -> pd.Series:
    """Model logistik walk-forward per tahun (dilatih rilis tahun-tahun sebelumnya, minimal 40). Tanda tebakan."""
    from sklearn.linear_model import LogisticRegression
    y = x[x.s != 0]
    out = pd.Series(0.0, index=x.index)
    for th in range(2013, 2027):
        tr = y[y.t0.dt.year < th]
        te = x[x.t0.dt.year == th]
        if len(tr) < 40 or te.empty or tr.s.nunique() < 2:
            continue
        m = LogisticRegression(C=0.5, max_iter=1000).fit(tr[cols].fillna(0), (tr.s > 0).astype(int))
        p = m.predict_proba(te[cols].fillna(0))[:, 1]
        out.loc[te.index] = np.where(p >= 0.55, 1.0, np.where(p <= 0.45, -1.0, 0.0))
    return out


def main() -> None:
    df = emas(tabel())
    df["-P"] = -df.P
    df["K|P"] = np.where(df.K.fillna(0) != 0, df.K, df.P)
    terbaik = {"CPI m/m": "K|P", "Core CPI m/m": "K|P", "CPI y/y": "P", "Unemployment Rate": "K|P",
               "Core PPI m/m": "-P", "ISM Services PMI": "-P", "JOLTS Job Openings": "-P", "Advance GDP q/q": "G"}
    judul = [j for j in FITUR if j in set(df.event)]
    df = fitur(df[df.event.isin(judul)].copy())
    L = ["# 🔎 Sumber lain selain Kalshi: tebakan kejutan berita (Act vs konsensus)", __doc__.split("\n\n")[1], ""]
    ringkas, simpan, sepakat = [], {}, {}
    for ev in judul:
        x = df[df.event == ev].copy()
        cols = FITUR[ev]
        base = terbaik.get(ev)
        L += ["", f"## {ev} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})"
                  + (f" — petunjuk terbaik lama: {base}" if base else "")]
        lolos = []
        for c in cols + ["SUARA", "MODEL"]:
            if c == "SUARA":
                x[c] = np.sign(x[cols].fillna(0).sum(axis=1))
            elif c == "MODEL":
                x[c] = logit_wf(x, cols)
            v = nilai(x, c)
            t, ok = teks(v)
            ek, en = emas_hit(x, c)
            L.append(f"   {'✅' if ok else '  '} {c:6s} {t} | emas 1 mnt cocok {ek}/{en}"
                     + (f"={ek / en * 100:.0f}%" if en else ""))
            if ok:
                lolos.append((c, v["semua"][0] / max(v["semua"][1], 1)))
                if c in ("WTI", "IND", "EMP", "GA"):          # sumber hidup yang bisa dibaca cloud (_petunjuk.py)
                    tahun = x.t0[x[c].notna() & (x[c] != 0)]
                    simpan.setdefault(ev, {})[c] = {"benar": v["semua"][0], "n": v["semua"][1], "lama": list(v["LAMA"]),
                                                    "baru": list(v["BARU"]), "emas": [ek, en],
                                                    "tahun": f"{tahun.min():%Y}–{tahun.max():%Y}"}
            if base and c in cols + ["SUARA"] and base in x:
                x["_s"] = np.where((x[base].fillna(0) != 0) & (x[base] == x[c]), x[base], 0.0)
                v2 = nilai(x, "_s")
                (k2, n2), (kb, nb) = v2["semua"], nilai(x, base)["semua"]
                if n2 >= 8:
                    L.append(f"         {base} & {c} sepakat: {k2}/{n2}={k2 / n2 * 100:.0f}% "
                             f"(vs {base} saja {kb}/{nb}={kb / max(nb, 1) * 100:.0f}%)")
                    sepakat.setdefault(ev, {})[f"{base}&{c}"] = [k2, n2]
        ringkas.append(f"{ev:32s} sumber lain lolos: " + (", ".join(f"{c} {p * 100:.0f}%" for c, p in lolos)
                                                         if lolos else "TIDAK ADA"))
    L += ["", "## Ringkasan"] + ringkas
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    import json                                         # gabung ke cloud/api/petunjuk.json (dibaca _petunjuk.py)
    pj = ROOT / "cloud" / "api" / "petunjuk.json"
    d = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {"aturan": {}}
    for ev, r in simpan.items():
        d["aturan"].setdefault(ev, {}).update(r)
    d["sepakat"] = {ev: {k: v for k, v in r.items() if k.split("&")[1] in simpan.get(ev, {})}
                    for ev, r in sepakat.items() if ev in simpan}
    d["sumber_lain"] = "research/sumber_lain.py"
    pj.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
