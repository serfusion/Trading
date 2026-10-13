"""🧱 PPI DARI DASAR: perkiraan angka per KOMPONEN (data versi hari itu) → kejutan → arah emas (13 Okt 2026).

python -m research.ppi_dasar [simpan]   → docs/eksternal/hasil_ppi_dasar.txt (+ ppi_wti.json["cpi_ppi"])

Pasangan research/cpi_dasar.py untuk PPI final demand. Tanggal rilis = hari pertama bulan acuan muncul di ALFRED PPIFIS
(rilis pertama; 08:30 New York), Mar 2014 – Sep 2026. Konsensus & aktual bulat: ForexFactory mentah, cadangan Nasdaq.
Angka sebenarnya = versi hari rilis (rekonstruksi diuji terhadap aktual kalender). Target emas = tick Exness
(research/riset_dalam_data.satu: lonjakan menit 1, detik 1/2/5/10), 2016+.

DITETAPKAN SEBELUM MELIHAT HASIL (pra-registrasi):
 TAHAP 0  peta mekanisme: kejutan bulat (total, inti) → emas naik, LAMA/BARU/2024+.
 TAHAP 1  ANGKA (bulan acuan t, rilis R; komponen versi R−1; harga pasar s/d R−1):
   FISIK  tanpa fitting: total = 0,30 × energi tersirat + 0,10 × makanan rata 3 bln + 0,60 × inti rata 3 bln, energi
          tersirat = rata % ubah WTI/bensin Gulf/solar Gulf (5 obs s/d tgl 13) × 0,35 (elastisitas grosir → PPI energi).
          (bobot kasar final demand: energi ±6%, makanan ±5% → dibulatkan menurut korelasi, BUKAN dioptimasi)
   FIT    ridge (α 3) per tahun, hanya tahun < Y: total & inti ← komponen 1/3 bln (total, inti, energi, makanan, dagang,
          transportasi, jasa lain, barang inti), energi grosir tgl 13 & sebulan, avtur, S&P 500 rata bulan t & t−1
          (manajemen portofolio), margin BBM (eceran EIA − grosir Gulf), CPI bulan sama bila sudah rilis (total, inti,
          barang inti, tiket pesawat; selain itu rata-rata latih).
   Uji    RMSE vs konsensus, ENCOMPASSING, arah kejutan |selisih| ≥ 0,05/0,08/0,10 — DIPISAH tebakan DI ATAS vs DI BAWAH
          (pelajaran CPI: tebakan di bawah bisa benar sementara tebakan di atas tidak).
 TAHAP 2  EMAS saat perkiraan berkata DI ATAS / DI BAWAH (≥ 0,08) vs selalu-NAIK pada rilis yang sama, per periode.
LAMA < Okt 2021, BARU ≥ Okt 2021.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_dasar import SC, SPLIT, encompass, pct, ridge_wf
from .cpi_dasar_data import harian, mm, potret, rata_bulan, vintage

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_ppi_dasar.txt"
EKS = ROOT / "data" / "research" / "eksternal"
KOMP = {"head": "PPIFIS", "core": "PPIFES", "en": "PPIDES", "food": "PPIDFS", "trade": "PPITSS", "trans": "PPIAWS",
        "oth": "PPITWS", "cg": "WPSFD413", "xt": "WPSFD49116", "pm": "WPU4021"}
F_HEAD = ["head_l1", "head_l3", "core_l3", "en_l1", "food_l3", "e13", "emon", "jet_mm", "marg", "sp_mm", "cpi_head", "trade_l1"]
F_CORE = ["core_l1", "core_l3", "trade_l1", "trade_l3", "trans_l3", "oth_l3", "cg_l3", "sp_mm", "sp_mm1", "pm_l1",
          "marg", "e13", "jet_mm", "cpi_core", "cpi_cg", "cpi_air"]


def jendela13(s: pd.Series, ref: pd.Timestamp) -> float:
    batas = ref + pd.Timedelta(days=12)
    x = s[(s.index <= batas)].tail(5)
    return float(x.mean()) if len(x) == 5 and (batas - x.index[-1]).days < 7 else np.nan


def rilis() -> pd.DataFrame:
    d = vintage("PPIFIS")
    r = d.groupby("date").rs.min().reset_index()
    r = r[r.rs >= pd.Timestamp("2014-03-01")]
    r["t0"] = [pd.Timestamp(x).replace(hour=8, minute=30).tz_localize("America/New_York").tz_convert("UTC") for x in r.rs]
    r = r.drop_duplicates("rs", keep="last")         # 14 Jan 2026: Okt & Nov 2025 terbit bersama (shutdown) → bulan terakhir
    return r.rename(columns={"date": "ref", "rs": "R"})[["t0", "R", "ref"]].reset_index(drop=True)


def _n(v) -> float:
    try:
        return float(str(v).replace("%", "").strip())
    except ValueError:
        return np.nan


def konsensus(t0s: pd.Series) -> pd.DataFrame:
    from .riset_dalam_data import ff_mentah
    ff = ff_mentah()
    out = []
    for t in t0s:
        o = {"t0": t}
        for k, e in (("h", "PPI m/m"), ("c", "Core PPI m/m")):
            g = ff[(ff.event == e) & ((ff.t0 - t).abs() <= pd.Timedelta(minutes=5))]
            o[f"{k}_a"], o[f"{k}_f"] = (_n(g.actual.iloc[0]), _n(g.forecast.iloc[0])) if len(g) else (np.nan, np.nan)
            if o[f"{k}_a"] != o[f"{k}_a"] or o[f"{k}_f"] != o[f"{k}_f"]:
                f = EKS / "nasdaq" / f"{t.tz_convert('America/New_York').date()}.json"
                if f.exists():
                    nm = "PPI" if k == "h" else "Core PPI"
                    rows = [r for r in json.loads(f.read_text(encoding="utf-8")) if r.get("eventName") == nm
                            and r.get("country") == "United States"]
                    rows = sorted(rows, key=lambda r: abs(_n(r.get("previous"))) if _n(r.get("previous")) == _n(r.get("previous")) else 99)
                    if rows:
                        o[f"{k}_a"], o[f"{k}_f"] = _n(rows[0].get("actual")), _n(rows[0].get("consensus"))
        out.append(o)
    return pd.DataFrame(out)


def cpi_sama() -> pd.DataFrame:
    """CPI bulan acuan sama: tanggal rilis CPI (vintage pertama CPIAUCSL) untuk dicek terbit sebelum PPI."""
    d = vintage("CPIAUCSL")
    r = d.groupby("date").rs.min()
    return r


def fitur(R: pd.Timestamp, ref: pd.Timestamp, cpi_r: pd.Series) -> dict:
    v1 = R - pd.Timedelta(days=1)
    o: dict = {}
    for k, s in KOMP.items():
        p, a = potret(s, v1), potret(s, R)
        o[f"{k}_act"] = mm(a, ref)
        l = [mm(p, ref - pd.DateOffset(months=i)) for i in range(1, 4)]
        o[f"{k}_l1"] = l[0]
        o[f"{k}_l3"] = np.nanmean(l) if np.isfinite(l).any() else np.nan
    ch13, chm = [], []
    for s in ("DCOILWTICO", "DGASUSGULF", "DDFUELUSGULF"):
        h = harian(s)
        h = h[h.index < R]
        a, b = jendela13(h, ref), jendela13(h, ref - pd.DateOffset(months=1))
        if a == a and b == b and b > 0:
            ch13.append((a / b - 1) * 100)
        a, b = rata_bulan(s, ref, R - pd.Timedelta(days=1)), rata_bulan(s, ref - pd.DateOffset(months=1))
        if a == a and b == b and b > 0:
            chm.append((a / b - 1) * 100)
    o["e13"] = float(np.mean(ch13)) if len(ch13) >= 2 else np.nan
    o["emon"] = float(np.mean(chm)) if len(chm) >= 2 else np.nan
    a, b = rata_bulan("DJFUELUSGULF", ref, R - pd.Timedelta(days=1)), rata_bulan("DJFUELUSGULF", ref - pd.DateOffset(months=1))
    o["jet_mm"] = (a / b - 1) * 100
    r1, r0 = rata_bulan("GASREGW", ref), rata_bulan("GASREGW", ref - pd.DateOffset(months=1))
    w1, w0 = rata_bulan("DGASUSGULF", ref), rata_bulan("DGASUSGULF", ref - pd.DateOffset(months=1))
    o["marg"] = ((r1 - w1) - (r0 - w0)) if all(x == x for x in (r1, r0, w1, w0)) else np.nan    # $/galon
    for j, nm in ((0, "sp_mm"), (1, "sp_mm1")):
        m1 = ref - pd.DateOffset(months=j)
        a, b = rata_bulan("SP500", m1, R - pd.Timedelta(days=1)), rata_bulan("SP500", m1 - pd.DateOffset(months=1))
        o[nm] = (a / b - 1) * 100
    # CPI bulan acuan sama bila sudah terbit sebelum hari R
    o["cpi_head"] = o["cpi_core"] = o["cpi_cg"] = o["cpi_air"] = np.nan
    if ref in cpi_r.index and cpi_r[ref] < R:
        for k, s in (("cpi_head", "CPIAUCSL"), ("cpi_core", "CPILFESL"), ("cpi_cg", "CUSR0000SACL1E"),
                     ("cpi_air", "CUSR0000SETG01")):
            o[k] = mm(potret(s, v1), ref)
    o["cpi_dulu"] = float(o["cpi_head"] == o["cpi_head"])
    return o


def tabel(cache: bool = True) -> pd.DataFrame:
    f = SC / "ppi_dasar_tab.pkl"
    if cache and f.exists():
        return pd.read_pickle(f)
    from .riset_dalam_data import satu
    r = rilis()
    cpi_r = cpi_sama()
    rows = [{"t0": x.t0, **fitur(x.R, x.ref, cpi_r)} for x in r.itertuples()]
    df = r.merge(pd.DataFrame(rows), on="t0").merge(konsensus(r.t0), on="t0", how="left")
    tg = []
    for t in df.t0:
        if t.year < 2016:
            continue
        try:
            o = satu(t)
        except Exception:                       # noqa: BLE001 — tick tidak ada
            continue
        tg.append({"t0": t, **{k: o.get(k) for k in ("arah", "d1", "d2", "d5", "d10")}})
    df = df.merge(pd.DataFrame(tg), on="t0", how="left")
    df["th"] = df.t0.dt.year
    df["s_h"], df["s_c"] = np.sign(df.h_a - df.h_f), np.sign(df.c_a - df.c_f)
    SC.mkdir(parents=True, exist_ok=True)
    df.to_pickle(f)
    return df


def periode(df: pd.DataFrame) -> dict:
    return {"2016–26": df.th >= 2016, "LAMA": (df.th >= 2016) & (df.t0 < SPLIT), "BARU": df.t0 >= SPLIT,
            "2024+": df.th >= 2024}


def up(s: pd.Series) -> str:
    s = s[(s != 0) & s.notna()]
    return f"{(s > 0).mean() * 100:3.0f}% ({int((s > 0).sum())}/{len(s)})" if len(s) else "–"


def tahap3(df: pd.DataFrame, L: list) -> None:
    """Hubungan CPI → PPI bulan acuan sama (CPI terbit lebih dulu): kejutan searah & emas saat PPI."""
    c = pd.read_pickle(SC / "cpi_dasar_tab.pkl")[["t0", "s_mm", "s_core", "ref"]].rename(
        columns={"t0": "t_cpi", "s_mm": "cs_h", "s_core": "cs_c"})
    m = df.merge(c, on="ref", how="left")
    m = m[m.t_cpi < m.t0]
    L.append(f"\n## TAHAP 3 — CPI bulan sama terbit LEBIH DULU ({len(m)} rilis): kejutan CPI → kejutan PPI & emas saat PPI")
    for a, nm in (("cs_h", "CPI total"), ("cs_c", "CPI inti")):
        for b_, nb in (("s_h", "PPI total"), ("s_c", "PPI inti")):
            isi = []
            for per, mm_ in (("LAMA", m.t0 < SPLIT), ("BARU", m.t0 >= SPLIT)):
                z = m[mm_ & (m[a] != 0) & (m[b_] != 0) & m[b_].notna()]
                isi.append(f"{per} {pct(int((z[a] == z[b_]).sum()), len(z))}")
            L.append(f"   {nm} → {nb} searah: " + " | ".join(isi))
    for v, nm in ((-1, "di bawah"), (0, "sesuai"), (1, "di atas")):
        L.append(f"   CPI inti {nm:8s} → emas naik saat PPI: " + " | ".join(
            f"{per} d2 {up(m.d2[mm_ & (m.cs_c == v)])} lonjakan {up(m.arah[mm_ & (m.cs_c == v)])}"
            for per, mm_ in (("LAMA", m.t0 < SPLIT), ("BARU", m.t0 >= SPLIT))))


def cpi_ppi(df: pd.DataFrame, L: list) -> dict:
    """Tebakan PPI-WTI (cloud/api/_ppi_wti.py) × kejutan INTI CPI bulan acuan sama yang terbit LEBIH DULU → arah lonjakan
    menit 1 saat PPI: searah / CPI inti sesuai / berlawanan (cloud/api/ppi_wti.json["cpi_ppi"])."""
    w = harian("DCOILWTICO")
    wt = []
    for r in df.itertuples():
        h = w[w.index < r.R]
        a, b = jendela13(h, r.ref), jendela13(h, r.ref - pd.DateOffset(months=1))
        wt.append((a / b - 1) * 100 if a == a and b == b else np.nan)
    x = df.assign(wti=wt)
    x["tb"] = np.where(x.wti >= 5, -1.0, np.where(x.wti <= -5, 1.0, 0.0))
    c = pd.read_pickle(SC / "cpi_dasar_tab.pkl")[["t0", "s_core", "ref"]].rename(columns={"t0": "t_cpi", "s_core": "cs_c"})
    m = x.merge(c, on="ref", how="left")
    m = m[(m.t_cpi < m.t0) & (m.th >= 2016) & (m.tb != 0) & m.arah.notna() & (m.arah != 0)]
    rel = np.where(m.cs_c == 0, "sesuai", np.where(-m.cs_c == m.tb, "sepakat", "berlawanan"))
    out = {"n": int(len(m))}
    # angka aturan PPI-WTI final (semua rilis resmi bertick 2016+, sama dengan docs/AUDIT_DATA.md) + PER ARAH tebakan
    a = x[(x.th >= 2016) & (x.tb != 0) & x.arah.notna() & (x.arah != 0)]
    def blok(z):
        return {"persen": round(float((z.tb == z.arah).mean() * 100), 1), "n": int(len(z))}
    out["lonjakan_audit"] = {k: blok(a[mk]) for k, mk in (("semua", a.th > 0), ("lama", a.t0 < SPLIT),
                                                          ("baru", a.t0 >= SPLIT), ("s2024", a.th >= 2024))}
    out["per_arah"] = {nm: {k: blok(a[(a.tb == v) & mk]) for k, mk in (("semua", a.th > 0), ("lama", a.t0 < SPLIT),
                                                                      ("baru", a.t0 >= SPLIT), ("s2024", a.th >= 2024))}
                       for nm, v in (("turun", -1.0), ("naik", 1.0))}
    L.append(f"\n## TAHAP 4 — Tebakan PPI-WTI setelah CPI inti terbit ({len(m)} rilis bersinyal, lonjakan menit 1)")
    for k in ("sepakat", "sesuai", "berlawanan"):
        o = {}
        for per, p in (("semua", m.th > 0), ("lama", m.t0 < SPLIT), ("baru", m.t0 >= SPLIT)):
            z = m[p.to_numpy() & (rel == k)]
            o[per] = round(float((z.tb == z.arah).mean() * 100), 1) if len(z) else None
            o[f"n_{per}"] = int(len(z))
        out[k] = o
        L.append(f"   {k:10s} benar {o['semua']}% (n {o['n_semua']}) • lama {o['lama']}% (n {o['n_lama']}) • baru {o['baru']}% (n {o['n_baru']})")
    return out


def hari_ini(df: pd.DataFrame, L: list, R: str = "2026-10-15", kons: dict | None = None) -> None:
    kons = kons or {"h_f": 0.5, "c_f": 0.3}
    R_ = pd.Timestamp(R)
    ref = (R_ - pd.DateOffset(months=1)).to_period("M").to_timestamp()
    o = fitur(R_, ref, cpi_sama())
    o.update({"t0": R_.tz_localize("America/New_York").replace(hour=8, minute=30).tz_convert("UTC"), "th": 9999, **kons})
    base = pd.concat([df, pd.DataFrame([o])], ignore_index=True)
    L.append(f"\n## HARI INI — PPI {R} (bulan acuan {ref:%b %Y}); konsensus {kons}")
    L.append(f"   energi grosir tgl 13 {o['e13']:+.1f}% • sebulan {o['emon']:+.1f}% • avtur {o['jet_mm']:+.1f}% • margin BBM "
             f"{o['marg']:+.3f} $/gal • S&P bulan t {o['sp_mm']:+.1f}% / t−1 {o['sp_mm1']:+.1f}% • PPI inti 1/3 bln "
             f"{o['core_l1']:.2f}/{o['core_l3']:.2f} • makanan 3 bln {o['food_l3']:+.2f}")
    L.append(f"   perkiraan total fisik {0.105 * o['e13'] + 0.10 * o['food_l3'] + 0.60 * o['core_l3']:.2f}")
    for ch, cc in ((np.nan, np.nan), (0.4, 0.1), (0.6, 0.2), (0.6, 0.3), (0.8, 0.3)):
        b = base.copy()
        b.loc[b.index[-1], ["cpi_head", "cpi_core"]] = [ch, cc]
        hf = ridge_wf(b, F_HEAD, "head_act", mulai=9999).iloc[-1]
        cf = ridge_wf(b, F_CORE, "core_act", mulai=9999).iloc[-1]
        L.append(f"   bila CPI Sep total {ch} / inti {cc}: PPI total fit {hf:.2f} (konsensus {kons['h_f']}) • inti fit {cf:.2f} "
                 f"(konsensus {kons['c_f']})" if ch == ch else
                 f"   sebelum CPI terbit: PPI total fit {hf:.2f} (konsensus {kons['h_f']}) • inti fit {cf:.2f} (konsensus {kons['c_f']})")


def main() -> None:
    L = ["# 🧱 PPI dari dasar (research/ppi_dasar.py)", __doc__.split("\n\n")[1], __doc__.split("\n\n")[2]]
    df = tabel(cache="--ulang" not in sys.argv)
    for k in ("h", "c"):
        act = "head_act" if k == "h" else "core_act"
        m = df[f"{k}_a"].notna() & df[act].notna()
        ok = (df[act][m].round(1) - df[f"{k}_a"][m]).abs() < 0.051
        L.append(f"   rekonstruksi {act} cocok angka bulat kalender: {ok.mean() * 100:.0f}% ({int(ok.sum())}/{int(m.sum())})")
    L.append(f"   rilis {len(df)} ({df.t0.min().date()} … {df.t0.max().date()}), bertick {int(df.arah.notna().sum())}, "
             f"CPI bulan sama sudah terbit sebelum PPI: {int(df.cpi_dulu.sum())}")
    for c in ("d1", "d2", "d5", "d10", "arah"):
        df[c] = np.sign(df[c].astype(float))
    df["net"] = np.sign(2 * df.s_c.fillna(0) + df.s_h.fillna(0))

    L.append("\n## TAHAP 0 — PETA MEKANISME: kejutan bulat → emas naik (detik 2 / lonjakan menit 1)")
    lama, baru, b24 = (df.th >= 2016) & (df.t0 < SPLIT), df.t0 >= SPLIT, df.th >= 2024
    kel = {"net DI BAWAH": df.net < 0, "net SESUAI": df.net == 0, "net DI ATAS": df.net > 0, "inti di bawah": df.s_c < 0,
           "inti sesuai": df.s_c == 0, "inti di atas": df.s_c > 0, "total di bawah": df.s_h < 0, "total di atas": df.s_h > 0,
           "SEMUA": df.th > 0}
    L.append("   kelompok          LAMA d2 / lonjakan              BARU d2 / lonjakan              2024+ d2 / lonjakan")
    for nm, m in kel.items():
        L.append(f"   {nm:16s} " + "   ".join(f"{up(df.d2[m & p])} / {up(df.arah[m & p])}" for p in (lama, baru, b24)))
    L.append("   porsi net di bawah • sesuai • di atas: " + " | ".join(
        f"{nm} " + " • ".join(f"{(df.net[p & df.s_h.notna()] == v).mean() * 100:.0f}%" for v in (-1, 0, 1))
        for nm, p in (("LAMA", lama), ("BARU", baru), ("2024+", b24))))

    # TAHAP 1
    df["head_fis"] = 0.30 * 0.35 * df.e13 + 0.10 * df.food_l3 + 0.60 * df.core_l3
    df["core_fis"] = df.core_l3
    df["head_fit"] = ridge_wf(df, F_HEAD, "head_act", mulai=2016)
    df["core_fit"] = ridge_wf(df, F_CORE, "core_act", mulai=2016)
    L.append("\n## TAHAP 1 — ANGKA: perkiraan bottom-up vs konsensus")
    rm = lambda a, b: np.sqrt(np.nanmean((a - b) ** 2))
    for nama, act, cons, s, kand in (("TOTAL m/m", "head_act", "h_f", "s_h", ("head_fis", "head_fit")),
                                     ("INTI m/m", "core_act", "c_f", "s_c", ("core_fis", "core_fit"))):
        L.append(f"\n### {nama}")
        for per, m in periode(df).items():
            x = df[m & df[cons].notna() & df[act].notna() & df[kand[1]].notna()]
            if not len(x):
                continue
            L.append(f"   {per:8s} n {len(x):3d} RMSE konsensus {rm(x[act], x[cons]):.3f} • fisik {rm(x[act], x[kand[0]]):.3f}"
                     f" • fit {rm(x[act], x[kand[1]]):.3f} | encompassing fisik {encompass(x[act].to_numpy(), x[cons].to_numpy(), x[kand[0]].to_numpy())}"
                     f" • fit {encompass(x[act].to_numpy(), x[cons].to_numpy(), x[kand[1]].to_numpy())}")
        for tau in (0.05, 0.08, 0.10):
            for k in kand:
                d = df[k] - df[cons]
                isi = []
                for per, m in periode(df).items():
                    for arah, mk in (("ATAS", d >= tau), ("BAWAH", d <= -tau)):
                        z = df[m & mk & df[s].notna()]
                        v = 1 if arah == "ATAS" else -1
                        isi.append(f"{per} {arah} {pct(int((z[s] == v).sum()), int((z[s] != 0).sum()))}")
                L.append(f"   {k:9s} ≥{tau:.2f}: " + " | ".join(isi))
    L.append("\n### Komponen (korelasi petunjuk → angka komponen rilis pertama, 2014–26)")
    for a, b in (("en_act", "e13"), ("en_act", "emon"), ("trade_act", "marg"), ("trade_act", "trade_l1"), ("pm_act", "sp_mm"),
                 ("pm_act", "sp_mm1"), ("trans_act", "jet_mm"), ("core_act", "cpi_core"), ("head_act", "cpi_head"),
                 ("cg_act", "cpi_cg"), ("core_act", "core_l3")):
        m = df[a].notna() & df[b].notna()
        L.append(f"   {a:9s} ← {b:9s} r {np.corrcoef(df[a][m], df[b][m])[0, 1]:+.2f} (n {m.sum()})")

    # TAHAP 2
    L.append("\n## TAHAP 2 — EMAS saat perkiraan berkata DI ATAS / DI BAWAH (selisih ≥ 0,08) vs selalu-NAIK")
    for k, cons in (("head_fit", "h_f"), ("core_fit", "c_f"), ("head_fis", "h_f")):
        d = df[k] - df[cons]
        for arah, mk in (("ATAS (emas ↓)", d >= 0.08), ("BAWAH (emas ↑)", d <= -0.08), ("netral", d.abs() < 0.08)):
            L.append(f"   {k:9s} {arah:15s} " + " | ".join(
                f"{per} n{int((mk & m).sum())} d1 {up(df.d1[mk & m])} d2 {up(df.d2[mk & m])} lonjakan {up(df.arah[mk & m])}"
                for per, m in periode(df).items()))
    tahap3(df, L)
    cp = cpi_ppi(df, L)
    if "simpan" in sys.argv:
        f = ROOT / "cloud" / "api" / "ppi_wti.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["cpi_ppi"] = cp
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        L.append("   → cloud/api/ppi_wti.json kunci cpi_ppi ditulis")
    hari_ini(df, L)
    df.to_pickle(SC / "ppi_dasar_hasil.pkl")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
