"""🔬 Riset MENDALAM Retail+GDP, ADP+JOLTS+klaim, FOMC+konsumen → arah LONJAKAN emas menit pertama (13 Okt 2026).

python -m research.riset_dalam          → docs/eksternal/hasil_riset_dalam.txt (+ data/research/eksternal/riset_dalam/fitur.parquet)

Permintaan pengguna 13 Okt: kelompok berita sisa workflow 11 Okt (.claude/workflows/riset-berita-lonjakan.js) dikerjakan
"sedalam sesi lain". Putaran cepat sebelumnya (research/riset_lain.py) gagal karena DATA: kalender bintang 3 saja → n kecil.
Di sini: jadwal SEMUA dampak + tick Exness tambahan (research/riset_dalam_data.py) dan petunjuk baru.

PRA-REGISTRASI (ditulis SEBELUM evaluasi; semua aturan masuk uji permutasi keluarga per kelompok, tidak ada yang dibuang).
Tanda petunjuk = arah "baik untuk USD" (angka di atas konsensus; KLAIM terbalik: klaim di atas = buruk untuk USD; FOMC = hawkish)
→ tebakan emas = kebalikannya. Hanya informasi yang terbit SEBELUM t0 (nilai rilis pertama, tanggal terbit FRED).
UMUM (semua kelompok):
  P     kejutan rilis sebelumnya (kelompok yang sama) searah          P3   tanda jumlah 3 kejutan terakhir
  KON   angka rilis lalu (nilai rilis pertama, BUKAN 'previous' kalender yang sudah direvisi) > konsensus → di atas
        (analis terlalu cepat menebak berbalik)                         ANK  kebalikan KON (anchoring Campbell–Sharpe)
RETAIL (bulan acuan = bulan sebelum rilis):
  R_AUTO  penjualan mobil unit TOTALSA (rilis pertama) bulan acuan naik → di atas
  R_BBM   harga bensin GASREGW rata bulan acuan vs bulan sebelumnya ≥ +2% → di atas (penjualan nominal SPBU), ≤ −2% → di bawah
  R_RB    Redbook (Nasdaq, y/y %, terbit Selasa) rata pekan bulan acuan vs bulan sebelumnya ≥ +0,5 poin → di atas
  R_SUARA tanda jumlah tiga di atas
GDP ADVANCE (kuartal acuan): G_NOW GDPNow akhir − konsensus ≥ +0,3 → di atas (≤ −0,3 di bawah); G_STL St. Louis Fed ENI
  (STLENI, vintage ALFRED sebelum hari rilis) − konsensus ≥ ±0,3; G_SUARA jumlah keduanya.
GDP PRELIM/FINAL: hanya UMUM (KON = revisi dari estimasi sebelumnya).
ADP: A_KLM klaim awal pekan survei (pekan berisi tanggal 12) bulan acuan lebih rendah dari pekan survei bulan sebelumnya → di
  atas; A_NFP kejutan NFP terakhir (≤ 40 hari) searah.
JOLTS (bulan acuan = 2 bulan sebelum rilis): J_NFP kejutan NFP bulan acuan yang sama (terbit lebih dulu) searah; J_IND lowongan
  Indeed rata bulan acuan vs bulan sebelumnya naik → di atas (2020+); J_KLM rata klaim awal bulan acuan turun → di atas.
KLAIM (tanda USD; klaim di atas = −): C_4W konsensus − rata 4 pekan klaim terakhir ≤ −3 rb → klaim condong DI ATAS konsensus
  (USD −), ≥ +3 rb → di bawah (USD +); C_MUSIM rata kejutan pekan ISO yang sama di tahun-tahun sebelumnya (≥ 3 th) searah;
  C_KONT klaim lanjutan (CCSA FRED, terbit sebelum t0) naik dari pekan sebelumnya → klaim awal condong di atas (USD −).
UoM PRELIM: U_SPX S&P 500 20 hari bursa naik → di atas; U_BBM bensin 4 pekan ≥ +2% → di bawah (≤ −2% → di atas).
UoM FINAL (prelim sudah terbit): U_REVSPX S&P 500 dari hari prelim s/d sehari sebelum final ≥ +1% → di atas, ≤ −1% → di
  bawah; U_REVBBM bensin sejak prelim ≤ −2% → di atas, ≥ +2% → di bawah.
CB: B_UM kejutan UoM terakhir bulan yang sama (terbit lebih dulu) searah; B_SPX S&P 500 20 hari naik → di atas; B_KLM rata
  klaim 4 pekan terakhir < 4 pekan sebelumnya → di atas.
FOMC (hawkish = +): F_DGS2 yield 2 th (DGS2) 5 hari bursa terakhir naik ≥ 5 bp → hawkish, turun ≥ 5 bp → dovish;
  F_EMAS emas 5 hari sebelum (close t0−1 jam vs 5 hari sebelumnya) naik ≥ 1% → reaksi hawkish (emas turun; "beli rumor jual
  berita"), turun ≤ −1% → dovish; F_SEP rapat dengan proyeksi (Mar/Jun/Sep/Des) → hawkish; F_SUARA jumlah ketiganya.
EVALUASI: target utama = arah lonjakan terbesar 0–60 dtk (tick Exness); kedua = arah detik 2 & 10. Tutup kertas per tahun
(research/lonjakan_uji.tutup, mulai 2013), dilaporkan 2016–2026 / LAMA (< Okt 2021) / BARU / 2022+ / 2026, PLAFON (kejutan
sebenarnya), selalu NAIK, dan subset `sendiri` (tanpa rilis setingkat/lebih besar di menit yang sama). Permutasi keluarga
2.000× per kelompok (semua aturan kelompok itu). LOLOS = sama dengan CPI: ≥ 60% 2016–2026, > 50% LAMA & BARU (n ≥ 8),
p keluarga < 0,05, ≥ 40 rilis ditebak sejak 2016, dan bisa dihitung live (sumber disebut di laporan).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import baris, keluarga, sk, tutup
from .riset_dalam_data import DIR, EKS, ff_mentah, lonjakan

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_dalam.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
UMUM = ["P", "P3", "KON", "ANK"]
KHUSUS = {"RETAIL": ["R_AUTO", "R_BBM", "R_RB", "R_SUARA"], "GDP_ADV": ["G_NOW", "G_STL", "G_SUARA"], "GDP_LAIN": [],
          "ADP": ["A_KLM", "A_NFP"], "JOLTS": ["J_NFP", "J_IND", "J_KLM"], "CLAIMS": ["C_4W", "C_MUSIM", "C_KONT"],
          "UOM_PRE": ["U_SPX", "U_BBM"], "UOM_FIN": ["U_REVSPX", "U_REVBBM"], "CB": ["B_UM", "B_SPX", "B_KLM"],
          "FOMC": ["F_DGS2", "F_EMAS", "F_SEP", "F_SUARA"]}
SUMBER_LIVE = {
    "P/P3/KON/ANK": "kalender ForexFactory pekan ini / Nasdaq (konsensus) + Act rilis lalu yang tersimpan cloud",
    "R_AUTO": "FRED TOTALSA (FRED_API_KEY)", "R_BBM": "FRED GASREGW", "R_RB": "Nasdaq 'Redbook' (Selasa)",
    "G_NOW": "Atlanta Fed GDPNow (xlsx/FRED GDPNOW)", "G_STL": "FRED STLENI",
    "A_KLM/J_KLM/B_KLM/C_4W": "Act klaim mingguan (FF/Nasdaq/FRED ICSA)", "A_NFP/J_NFP": "Act & konsensus NFP (FF/Nasdaq)",
    "J_IND": "Indeed Hiring Lab CSV (GitHub)", "C_KONT": "FRED CCSA", "C_MUSIM": "riwayat kejutan klaim (tabel tetap)",
    "U_*/B_SPX": "FRED SP500 + GASREGW", "B_UM": "Act & konsensus UoM (FF/Nasdaq)", "F_DGS2": "FRED DGS2",
    "F_EMAS": "Twelve Data XAU/USD", "F_SEP": "kalender FOMC"}


def sg(v, batas: float = 0.0) -> float:
    return 0.0 if v is None or v != v or abs(v) <= batas or v == 0 else float(np.sign(v))


def fred_awal(seri: str) -> pd.DataFrame:
    from .pra_per_berita import fred_awal as f
    return f(seri)


def rata_bulan(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    s = df[df.available < t].value
    a = s[(s.index >= bulan) & (s.index < bulan + pd.offsets.MonthBegin(1))]
    return float(a.mean()) if len(a) else np.nan


def bln(t: pd.Timestamp, k: int) -> pd.Timestamp:
    return (t.tz_convert("America/New_York").tz_localize(None).to_period("M") - k).to_timestamp()


def nilai_asof(df: pd.DataFrame, t: pd.Timestamp, n: int = 1) -> list[float]:
    s = df[df.available < t].value
    return list(s.iloc[-n:]) if len(s) >= n else []


def basis() -> pd.DataFrame:
    y = lonjakan().sort_values("t0").reset_index(drop=True)
    y["inv"] = np.where(y.grup == "CLAIMS", -1.0, 1.0)
    y["s"] = np.sign(y.a - y.f) * y.inv                     # kejutan sebenarnya (arah USD) = PLAFON
    y["th"] = y.t0.dt.year
    y["kel"] = y.grup
    y.loc[(y.grup == "GDP") & (y["sub"] == "adv"), "kel"] = "GDP_ADV"
    y.loc[(y.grup == "GDP") & (y["sub"] != "adv"), "kel"] = "GDP_LAIN"
    y.loc[(y.grup == "UOM") & (y["sub"] == "prelim"), "kel"] = "UOM_PRE"
    y.loc[(y.grup == "UOM") & (y["sub"] != "prelim"), "kel"] = "UOM_FIN"
    return y


def umum(y: pd.DataFrame) -> None:
    for c in UMUM:
        y[c] = 0.0
    for _, g in y.groupby("grup"):
        idx = list(g.index)
        for j, i in enumerate(idx):
            lalu = [k for k in idx[:j] if y.at[k, "a"] == y.at[k, "a"]]
            if not lalu:
                continue
            sl = [y.at[k, "s"] for k in lalu if y.at[k, "f"] == y.at[k, "f"]]
            if sl:
                y.at[i, "P"] = sg(sl[-1])
                y.at[i, "P3"] = sg(sum(sl[-3:])) if len(sl) >= 3 else 0.0
            pa, f = y.at[lalu[-1], "a"], y.at[i, "f"]
            if f == f:
                y.at[i, "KON"] = sg(pa - f) * y.at[i, "inv"]
                y.at[i, "ANK"] = -y.at[i, "KON"]


def nfp_tabel() -> pd.DataFrame:
    ff = ff_mentah()
    n = ff[ff.event == "Non-Farm Employment Change"][["t0", "actual", "forecast"]].copy()
    rows = []
    import glob
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "2026-*.json"))):
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            if r.get("eventName") == "Nonfarm Payrolls" and r.get("country") == "United States":
                from .riset_dalam_data import _ny
                rows.append({"t0": _ny(Path(f).stem, "08:30"), "actual": r.get("actual"), "forecast": r.get("consensus")})
                break
    n = pd.concat([n, pd.DataFrame(rows)], ignore_index=True)
    from .riset_dalam_data import _num
    n["s"] = np.sign(n.actual.map(_num) - n.forecast.map(_num))
    n = n.dropna(subset=["s"]).sort_values("t0").drop_duplicates("t0")
    return n.reset_index(drop=True)


def redbook() -> pd.DataFrame:
    import glob

    from .riset_dalam_data import _num
    rows = []
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "*.json"))):
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            if r.get("eventName") == "Redbook" and r.get("country") == "United States":
                v = _num(r.get("actual"))
                if v == v:
                    d = pd.Timestamp(Path(f).stem)
                    rows.append({"tgl": d, "value": v, "available": (d + pd.Timedelta(hours=14)).tz_localize("UTC")})
                break
    return pd.DataFrame(rows).set_index("tgl")


def khusus(y: pd.DataFrame) -> None:
    from .berita_detik import sp500
    from .eksternal_makro import fred
    for c in sum(KHUSUS.values(), []):
        y[c] = 0.0
    auto, gas, spx = fred_awal("TOTALSA"), fred_awal("GASREGW"), sp500()
    rb, nfp = redbook(), nfp_tabel()
    klaim = y[(y.grup == "CLAIMS") & y.a.notna()][["t0", "a", "f", "s"]].reset_index(drop=True)
    try:
        from .berita_gabung import gdpnow
        gn = gdpnow()
    except Exception:  # noqa: BLE001
        gn = pd.DataFrame(columns=["q", "now", "rilis"])
    stl = json.loads((DIR / "fred_STLENI_semua.json").read_text())["observations"]
    stl = pd.DataFrame(stl)
    stl = stl[stl.value != "."].assign(value=lambda d: d.value.astype(float),
                                       rs=lambda d: pd.to_datetime(d.realtime_start), q=lambda d: pd.to_datetime(d.date))
    from .sumber_lain import indeed
    ind = indeed()
    ccsa, dgs2 = fred("CCSA"), fred("DGS2")
    from .event_stats import xau_m15
    xau = xau_m15().close
    xau.index = xau.index.tz_localize("UTC") if xau.index.tz is None else xau.index

    def klaim_sebelum(t: pd.Timestamp, n: int) -> list[float]:
        return list(klaim[klaim.t0 < t].a.iloc[-n:])

    def spx_ubah(t: pd.Timestamp, hari: int) -> float:
        s = spx[spx.available < t].value
        return float(s.iloc[-1] / s.iloc[-1 - hari] - 1) if len(s) > hari else np.nan

    for i, r in y.iterrows():
        t, k = r.t0, r.kel
        if k == "RETAIL":
            ref = bln(t, 1)
            a_, b_ = rata_bulan(auto, t, ref), rata_bulan(auto, t, bln(t, 2))
            y.at[i, "R_AUTO"] = sg(a_ - b_)
            a_, b_ = rata_bulan(gas, t, ref), rata_bulan(gas, t, bln(t, 2))
            y.at[i, "R_BBM"] = sg((a_ / b_ - 1) * 100, 2.0) if a_ == a_ and b_ == b_ else 0.0
            a_, b_ = rata_bulan(rb, t - pd.Timedelta(hours=12), ref), rata_bulan(rb, t - pd.Timedelta(hours=12), bln(t, 2))
            y.at[i, "R_RB"] = sg(a_ - b_, 0.5) if a_ == a_ and b_ == b_ else 0.0
            y.at[i, "R_SUARA"] = sg(y.at[i, "R_AUTO"] + y.at[i, "R_BBM"] + y.at[i, "R_RB"])
        elif k == "GDP_ADV" and r.f == r.f:
            g = gn[(gn.rilis - t).abs() <= pd.Timedelta(days=3)] if len(gn) else gn
            if len(g):
                y.at[i, "G_NOW"] = sg(g.now.iloc[-1] - r.f, 0.3 - 1e-9)
            q = bln(t, 1).to_period("Q").to_timestamp()            # kuartal acuan (advance = kuartal lalu)
            s = stl[(stl.q == q) & (stl.rs < t.tz_convert(None).normalize())]
            if len(s):
                y.at[i, "G_STL"] = sg(s.sort_values("rs").value.iloc[-1] - r.f, 0.3 - 1e-9)
            y.at[i, "G_SUARA"] = sg(y.at[i, "G_NOW"] + y.at[i, "G_STL"])
        elif k == "ADP":
            def pekan_survei(b: pd.Timestamp) -> float:
                d12 = pd.Timestamp(b) + pd.Timedelta(days=11)
                sabtu = d12 + pd.Timedelta(days=(5 - d12.weekday()) % 7)
                lo = (sabtu + pd.Timedelta(days=1)).tz_localize("America/New_York").tz_convert("UTC")
                v = klaim[(klaim.t0 > lo) & (klaim.t0 <= lo + pd.Timedelta(days=7)) & (klaim.t0 < t)]
                return float(v.a.iloc[0]) if len(v) else np.nan
            a_, b_ = pekan_survei(bln(t, 1)), pekan_survei(bln(t, 2))
            y.at[i, "A_KLM"] = -sg(a_ - b_)
            n_ = nfp[(nfp.t0 < t) & (nfp.t0 >= t - pd.Timedelta(days=40))]
            y.at[i, "A_NFP"] = sg(n_.s.iloc[-1]) if len(n_) else 0.0
        elif k == "JOLTS":
            ref = bln(t, 2)
            n_ = nfp[(nfp.t0 < t) & (nfp.t0.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("M")
                                     == (ref.to_period("M") + 1))]
            y.at[i, "J_NFP"] = sg(n_.s.iloc[-1]) if len(n_) else 0.0
            a_, b_ = rata_bulan(ind, t, ref), rata_bulan(ind, t, bln(t, 3))
            y.at[i, "J_IND"] = sg(a_ - b_) if a_ == a_ and b_ == b_ else 0.0
            ka = klaim[(klaim.t0 < t)]
            kb = ka.t0.dt.tz_convert("America/New_York").dt.tz_localize(None)
            a_ = ka.a[(kb >= ref) & (kb < ref + pd.offsets.MonthBegin(1))].mean()
            b_ = ka.a[(kb >= bln(t, 3)) & (kb < ref)].mean()
            y.at[i, "J_KLM"] = -sg(a_ - b_)
        elif k == "CLAIMS" and r.f == r.f:
            last4 = klaim_sebelum(t, 4)
            if len(last4) == 4:
                y.at[i, "C_4W"] = sg(r.f - np.mean(last4), 3000 - 1e-6)
            w = t.isocalendar().week
            lalu = klaim[(klaim.t0 < t - pd.Timedelta(days=200)) & (klaim.t0.dt.isocalendar().week == w)]
            if lalu.t0.dt.year.nunique() >= 3:
                y.at[i, "C_MUSIM"] = sg(lalu.s.mean())
            v = nilai_asof(ccsa, t, 2)
            if len(v) == 2:
                y.at[i, "C_KONT"] = -sg(v[1] - v[0])
        elif k == "UOM_PRE":
            y.at[i, "U_SPX"] = sg(spx_ubah(t, 20))
            v = gas[gas.available < t].value
            if len(v) > 4:
                y.at[i, "U_BBM"] = -sg((v.iloc[-1] / v.iloc[-5] - 1) * 100, 2.0)
        elif k == "UOM_FIN":
            pre = y[(y.kel == "UOM_PRE") & (y.t0 < t) & (y.t0 >= t - pd.Timedelta(days=25))]
            if len(pre):
                tp = pre.t0.iloc[-1]
                s = spx[(spx.available < t)].value
                s0 = spx[spx.index <= tp.tz_convert(None).normalize() - pd.Timedelta(days=1)].value
                if len(s) and len(s0):
                    y.at[i, "U_REVSPX"] = sg((s.iloc[-1] / s0.iloc[-1] - 1) * 100, 1.0)
                g1, g0 = gas[gas.available < t].value, gas[gas.available < tp].value
                if len(g1) and len(g0):
                    y.at[i, "U_REVBBM"] = -sg((g1.iloc[-1] / g0.iloc[-1] - 1) * 100, 2.0)
        elif k == "CB":
            um = y[(y.grup == "UOM") & (y.t0 < t) & (y.t0 >= t - pd.Timedelta(days=31)) & y.s.notna()]
            um = um[um.t0.dt.month == t.month]
            y.at[i, "B_UM"] = sg(um.s.iloc[-1]) if len(um) else 0.0
            y.at[i, "B_SPX"] = sg(spx_ubah(t, 20))
            k8 = klaim_sebelum(t, 8)
            if len(k8) == 8:
                y.at[i, "B_KLM"] = -sg(np.mean(k8[4:]) - np.mean(k8[:4]))
        elif k == "FOMC":
            v = nilai_asof(dgs2, t, 6)
            if len(v) == 6:
                y.at[i, "F_DGS2"] = sg(v[-1] - v[0], 0.05 - 1e-9)
            s = xau[xau.index <= t - pd.Timedelta(hours=1)]
            s5 = xau[xau.index <= t - pd.Timedelta(days=5, hours=1)]
            if len(s) and len(s5):
                y.at[i, "F_EMAS"] = sg((s.iloc[-1] / s5.iloc[-1] - 1) * 100, 1.0)
            y.at[i, "F_SEP"] = 1.0 if t.month in (3, 6, 9, 12) else 0.0
            y.at[i, "F_SUARA"] = sg(y.at[i, "F_DGS2"] + y.at[i, "F_EMAS"] + y.at[i, "F_SEP"])


def lapor(nama: str, x: pd.DataFrame, aturan: list[str], L: list, lolos: list, rng) -> dict:
    out = {}
    if len(x) < 20:
        L.append(f"\n## {nama}: hanya {len(x)} rilis bertarget — dilewati")
        return out
    yv, th, t0 = x.arah.fillna(0).to_numpy(), x.th.to_numpy(), x.t0
    L.append(f"\n## {nama} ({len(x)} rilis bertarget {t0.min():%Y-%m}–{t0.max():%Y-%m}; sendiri {int(x.sendiri.sum())}; "
             f"konsensus ada {int(x.f.notna().sum())})")
    L.append("   selalu NAIK  " + baris(np.ones(len(x)), yv, t0, th)[0])
    L.append("   PLAFON       " + baris(-x.s.fillna(0).to_numpy(), yv, t0, th)[0])
    C = {c: x[c].fillna(0).to_numpy() for c in aturan}
    kel = keluarga(C, yv, th, rng)
    for c, v in C.items():
        tb = tutup(v, yv, th)
        s, r = baris(tb, yv, t0, th)
        p = kel.get(c)
        (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
        n16 = int(((v != 0) & (th >= 2016)).sum())
        ok = bool(p and n and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5
                  and min(p[0], p[1]) < 0.05 and n16 >= 40)
        sek = []
        for kol in ("d2", "d10"):
            kk, nn = sk(tutup(v, x[kol].fillna(0).to_numpy(), th), x[kol].fillna(0).to_numpy(), th >= 2016)
            sek.append(f"{kol} {kk / nn * 100:.0f}%" if nn else f"{kol} –")
        m = x.sendiri.to_numpy() & (th >= 2016)
        ks, ns = sk(tb, yv, m)
        L.append(f"   {c:9s} {s}" + (f" | p {p[0]:.3f}/{p[1]:.3f}" if p else " | p –") +
                 f" | {' '.join(sek)}" + (f" | sendiri {ks / ns * 100:.0f}% ({ns})" if ns else "") +
                 ("  ✅ LOLOS" if ok else ""))
        out[c] = {"semua": r["semua"], "lama": r["LAMA"], "baru": r["BARU"], "p": p[:2] if p else None, "n16": n16,
                  "lolos": ok}
        if ok:
            lolos.append(f"{nama} {c}")
    return out


def main() -> None:
    y = basis()
    umum(y)
    khusus(y)
    y.to_parquet(DIR / "fitur.parquet")
    L = ["# 🔬 Riset mendalam Retail+GDP, ADP+JOLTS+klaim, FOMC+konsumen (research/riset_dalam.py)",
         __doc__.split("\n\n")[1], "", "Kolom: tutup kertas lonjakan | p keluarga 2016+/2022+ | arah detik 2/10 (tutup kertas) |"
         " subset sendiri", "Sumber live: " + json.dumps(SUMBER_LIVE, ensure_ascii=False)]
    lolos, rng, semua = [], np.random.default_rng(13), {}
    x = y[y.arah.notna()]
    for k, at in KHUSUS.items():
        semua[k] = lapor(k, x[x.kel == k].reset_index(drop=True), UMUM + at, L, lolos, rng)
    jumlah = sum(len(UMUM) + len(at) for at in KHUSUS.values())
    L.append(f"\nAturan diuji: {jumlah} (semua pra-registrasi, {len(KHUSUS)} kelompok)")
    L.append("LOLOS: " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR / "hasil.json").write_text(json.dumps({"lolos": lolos, "jumlah": jumlah, "hasil": semua}, default=str,
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
