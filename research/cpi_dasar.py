"""🧱 CPI DARI DASAR: perkiraan angka per KOMPONEN (data versi hari itu) → kejutan → arah emas (13 Okt 2026).

python -m research.cpi_dasar            → docs/eksternal/hasil_cpi_dasar.txt

Kritik pengguna: "riset datamu hanya sebatas selalu buy, tidak mendasar". Jawaban riset ini: bangun angka CPI seperti ekonom
(bottom-up), bandingkan dengan konsensus, lalu ukur apakah tebakan kejutan menambah sesuatu DI ATAS pembanding arah emas
(selalu-NAIK & tren emas). Semua angka komponen dari ALFRED (research/cpi_dasar_data): petunjuk = versi hari sebelum rilis,
angka sebenarnya = versi hari rilis (rilis pertama, bukan revisi). Rekonstruksi cocok 100% dengan angka aktual kalender.

DITETAPKAN SEBELUM MELIHAT HASIL (pra-registrasi):
 TAHAP 0  PETA MEKANISME: arah emas (detik 1/2/5/10 & lonjakan menit 1) per pola kejutan bulat (m/m, inti, y/y), LAMA/BARU.
          Pertanyaan: dari mana datangnya "selalu NAIK" 2024+ (kejutan di bawah atau rilis sesuai perkiraan)?
 TAHAP 1  ANGKA (bulan acuan t, rilis R; komponen versi R−1):
   FISIK  tanpa fitting: inti = rata-rata inti 3 bln; makanan = rata 3 bln; energi = ½ bensin + ½ (listrik & gas pipa rata
          3 bln); bensin SA = rata EIA eceran bulan t vs t−1 − (NSA − SA bensin bulan sama tahun lalu); total = 0,79 inti +
          0,135 makanan + 0,075 energi.
   FIT    ridge (α 3, terstandar) per tahun, hanya tahun < Y: total ← inti, makanan, bensin prediksi, listrik, gas; inti ←
          inti 1/3/6 bln, shelter, OER, sewa, mobil bekas, Manheim t−1/t−2, tiket pesawat, avtur, medis, pakaian, mobil baru.
   Uji    RMSE vs konsensus; ENCOMPASSING (aktual − konsensus) = a + b (perkiraan − konsensus) di luar sampel (b > 0 &
          t > 2 = perkiraan tahu sesuatu yang konsensus tidak tahu); arah kejutan bila |perkiraan − konsensus| ≥ 0,05
          (kepekaan 0,08/0,10) vs kejutan bulat.
   y/y    y/y tersirat dari konsensus m/m + efek basis (YOY) dan dari perkiraan FIT m/m (YOYn).
 TAHAP 2  EMAS: logistik walk-forward per tahun, target arah detik 2 / lonjakan menit 1:
   B0 konstanta (≈ selalu-NAIK bila emas lebih sering naik)  B1 + rezim (T200, momentum 20 & 5 hari)
   F1 B1 + tebakan kejutan (perkiraan total/inti, YOY, Kalshi total/inti, indeks Nasdaq, kejutan lalu)  F2 F1 tanpa rezim
   Uji    log-loss & Brier di luar sampel, ketepatan PER ARAH tebakan, McNemar F1 vs B0 dan F1 vs B1, LAMA/BARU/2024+.
   SKOR   aturan transparan tanpa ML: jumlah tanda tebakan kejutan (total: Kalshi→FIT; inti: Kalshi inti→FIT; y/y: YOY);
          tebak emas = −tanda(SKOR) bila |SKOR| ≥ 2 (komponen sepakat).
LAMA < Okt 2021, BARU ≥ Okt 2021.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .cpi_dasar_data import harian, mm, potret, rata_bulan

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_dasar.txt"
EKS = ROOT / "data" / "research" / "eksternal"
SC = EKS / "cpi_dasar"                      # cache tabel (data disimpan di repo)
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
TAU = 0.05

KOMP = {"core": "CPILFESL", "head": "CPIAUCSL", "food": "CPIUFDSL", "en": "CPIENGSL", "elec": "CUSR0000SEHF01",
        "gpipe": "CUSR0000SEHF02", "shel": "CUSR0000SAH1", "oer": "CUSR0000SEHC", "rent": "CUSR0000SEHA",
        "used": "CUSR0000SETA02", "new": "CUSR0000SETA01", "air": "CUSR0000SETG01", "med": "CUSR0000SAM2",
        "app": "CPIAPPSL", "cg": "CUSR0000SACL1E", "cs": "CUSR0000SASLE", "gas": "CUSR0000SETB01"}
F_HEAD = ["core_l1", "core_l3", "food_l1", "food_l3", "gas_pred", "elec_l3", "gpipe_l3", "hh_mm"]
F_CORE = ["core_l1", "core_l3", "core_l6", "shel_l3", "oer_l1", "rent_l1", "used_l1", "used_l3", "manh_1", "manh_2",
          "air_l1", "jet_mm", "med_l3", "app_l1", "new_l1", "cg_l3", "cs_l3"]


def acuan(t0: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    R = t0.tz_convert("America/New_York").tz_localize(None).normalize()
    return R, (R - pd.DateOffset(months=1)).to_period("M").to_timestamp()


def manheim() -> pd.Series:
    m = pd.read_excel(EKS / "cpi_lain" / "manheim.xlsx", sheet_name="DATA", header=None).iloc[1:, [0, 1]]
    m.columns = ["bln", "idx"]
    return m.dropna().set_index(pd.to_datetime(m.bln)).idx.astype(float)


def fitur(R: pd.Timestamp, ref: pd.Timestamp, man: pd.Series) -> dict:
    v1 = R - pd.Timedelta(days=1)
    o: dict = {}
    for k, s in KOMP.items():
        p = potret(s, v1)
        a = potret(s, R)
        o[f"{k}_act"] = mm(a, ref)                                       # angka rilis pertama (target / diagnosis)
        l = [mm(p, ref - pd.DateOffset(months=i)) for i in range(1, 13)]
        o[f"{k}_l1"] = l[0]
        o[f"{k}_l3"] = np.nanmean(l[:3]) if np.isfinite(l[:3]).any() else np.nan
        o[f"{k}_l6"] = np.nanmean(l[:6]) if np.isfinite(l[:6]).any() else np.nan
        if k == "head":
            o["head_l12"] = l[11]                                       # bulan yang keluar dari y/y (SA)
    pn, ps = potret("CUUR0000SETB01", v1), potret("CUSR0000SETB01", v1)
    o["gas_seas"] = mm(pn, ref - pd.DateOffset(months=12)) - mm(ps, ref - pd.DateOffset(months=12))
    e1, e0 = rata_bulan("GASREGW", ref), rata_bulan("GASREGW", ref - pd.DateOffset(months=1))
    o["gas_eia"] = (e1 / e0 - 1) * 100
    o["gas_pred"] = o["gas_eia"] - o["gas_seas"]
    for k, s in (("jet_mm", "DJFUELUSGULF"), ("hh_mm", "DHHNGSP"), ("wti_mm", "DCOILWTICO")):
        a, b = rata_bulan(s, ref), rata_bulan(s, ref - pd.DateOffset(months=1))
        o[k] = (a / b - 1) * 100
    for j in (1, 2):                                                    # Manheim terbit ±hari ke-7 bulan berikutnya
        b = ref - pd.DateOffset(months=j)
        ok = b in man.index and b - pd.DateOffset(months=1) in man.index and R >= b + pd.DateOffset(months=1, days=7)
        o[f"manh_{j}"] = (man[b] / man[b - pd.DateOffset(months=1)] - 1) * 100 if ok else np.nan
    nsa = potret("CPIAUCNS", v1)
    o["nsa_p1"], o["nsa_p12"] = nsa.get(ref - pd.DateOffset(months=1), np.nan), nsa.get(ref - pd.DateOffset(months=12), np.nan)
    sa1 = potret("CPIAUCSL", v1)
    p12, p13 = ref - pd.DateOffset(months=12), ref - pd.DateOffset(months=13)
    o["sea12"] = ((nsa.get(p12, np.nan) / nsa.get(p13, np.nan) - 1) - (sa1.get(p12, np.nan) / sa1.get(p13, np.nan) - 1)) * 100
    nr = potret("CPIAUCNS", R)
    o["yy_act"] = (nr.get(ref, np.nan) / nr.get(p12, np.nan) - 1) * 100
    return o


def tabel(cache: bool = True) -> pd.DataFrame:
    f = SC / "cpi_dasar_tab.pkl"
    if cache and f.exists():
        return pd.read_pickle(f)
    from . import cpi_detik as C
    df = C.turunan(C.tabel())
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")
    df = df.merge(lj[lj.grup == "CPI"][["t0", "arah"]].drop_duplicates("t0"), on="t0", how="left")
    man = manheim()
    rows = []
    for t in df.t0:
        R, ref = acuan(t)
        rows.append({"t0": t, "R": R, "ref": ref, **fitur(R, ref, man)})
    df = df.merge(pd.DataFrame(rows), on="t0")
    df = df.merge(momentum(df.t0), on="t0", how="left")
    SC.mkdir(parents=True, exist_ok=True)
    df.to_pickle(f)
    return df


def momentum(t0s: pd.Series) -> pd.DataFrame:
    from .eksternal import asset
    x = asset("XAUUSD").b.df
    x = x[x.high > x.low]
    d = x.close.resample("D").last().dropna()
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d = d[d.index.dayofweek < 5]
    out = []
    for t in t0s:
        s = d[d.index < t.normalize()]
        out.append({"t0": t, "mom20": float(np.sign(s.iloc[-1] / s.iloc[-21] - 1)) if len(s) > 21 else 0.0,
                    "mom5": float(np.sign(s.iloc[-1] / s.iloc[-6] - 1)) if len(s) > 6 else 0.0})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- TAHAP 1: angka
def fisik(df: pd.DataFrame) -> pd.DataFrame:
    en_srv = (0.78 * df.elec_l3 + 0.22 * df.gpipe_l3)
    df["en_now"] = 0.5 * df.gas_pred + 0.5 * en_srv
    df["core_fis"] = df.core_l3
    df["head_fis"] = 0.79 * df.core_l3 + 0.135 * df.food_l3 + 0.075 * df.en_now
    return df


def ridge_wf(df: pd.DataFrame, kol: list[str], y: str, alpha: float = 3.0, mulai: int = 2013) -> pd.Series:
    out = pd.Series(np.nan, index=df.index)
    for th in sorted(df.th.unique()):
        if th < mulai:
            continue
        tr = df[(df.th < th) & df[y].notna()]
        te = df[df.th == th]
        if len(tr) < 24:
            continue
        X = tr[kol].astype(float)
        mu, sd = X.mean(), X.std().replace(0, 1).fillna(1)
        Xs = ((X - mu) / sd).fillna(0).to_numpy()
        ym = tr[y].mean()
        A = Xs.T @ Xs + alpha * np.eye(len(kol))
        b = np.linalg.solve(A, Xs.T @ (tr[y].to_numpy() - ym))
        Xt = ((te[kol].astype(float) - mu) / sd).fillna(0).to_numpy()
        out[te.index] = Xt @ b + ym
    return out


def pct(k, n) -> str:
    return f"{k / n * 100:.0f}% ({k}/{n})" if n else "–"


def periode(df: pd.DataFrame) -> dict:
    return {"2014–26": df.th >= 2014, "LAMA": (df.th >= 2014) & (df.t0 < SPLIT), "BARU": df.t0 >= SPLIT,
            "2024+": df.th >= 2024}


def encompass(a: np.ndarray, c: np.ndarray, p: np.ndarray) -> str:
    m = np.isfinite(a) & np.isfinite(c) & np.isfinite(p)
    if m.sum() < 10:
        return "–"
    y, x = a[m] - c[m], p[m] - c[m]
    X = np.c_[np.ones(m.sum()), x]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    s2 = e @ e / (len(y) - 2)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return f"b {b[1]:+.2f} (t {b[1] / se[1]:+.1f}, n {m.sum()})"


def tahap1(df: pd.DataFrame, L: list) -> None:
    L.append("\n## TAHAP 1 — ANGKA: perkiraan bottom-up vs konsensus (angka rilis pertama, versi hari itu)")
    rm = lambda a, b: np.sqrt(np.nanmean((a - b) ** 2))
    for nama, act, cons, kand in (("TOTAL m/m", "head_act", "mm_f", ("head_fis", "head_fit")),
                                  ("INTI m/m", "core_act", "core_f", ("core_fis", "core_fit"))):
        L.append(f"\n### {nama}")
        for per, m in periode(df).items():
            x = df[m & df[cons].notna() & df[act].notna() & df[kand[1]].notna()]
            if not len(x):
                continue
            L.append(f"   {per:8s} n {len(x):3d} RMSE konsensus {rm(x[act], x[cons]):.3f} • fisik {rm(x[act], x[kand[0]]):.3f}"
                     f" • fit {rm(x[act], x[kand[1]]):.3f} | encompassing fisik {encompass(x[act].to_numpy(), x[cons].to_numpy(), x[kand[0]].to_numpy())}"
                     f" • fit {encompass(x[act].to_numpy(), x[cons].to_numpy(), x[kand[1]].to_numpy())}")
        sk = "s_mm" if nama.startswith("TOTAL") else "s_core"
        for tau in (TAU, 0.08, 0.10):
            for k in kand:
                isi = []
                for per, m in periode(df).items():
                    d = (df[k] - df[cons]).where(m)
                    g = np.where(d >= tau, 1.0, np.where(d <= -tau, -1.0, 0.0))
                    s = df[sk].to_numpy()
                    ok = (g != 0) & (s != 0)
                    u = np.sign(df[act] - df[cons]).to_numpy()
                    ok2 = (g != 0) & (u != 0) & np.isfinite(u)
                    isi.append(f"{per} {pct(int((g[ok] == s[ok]).sum()), int(ok.sum()))} [tak-bulat {pct(int((g[ok2] == u[ok2]).sum()), int(ok2.sum()))}; tebak {int((g != 0).sum())}]")
                L.append(f"   arah kejutan {k:9s} |selisih| ≥ {tau:.2f}: " + " | ".join(isi))
    # komponen: seberapa baik petunjuk menebak komponen
    L.append("\n### Komponen (korelasi petunjuk → angka komponen rilis pertama, 2014–26)")
    x = df[df.th >= 2014]
    for a, b in (("gas_act", "gas_pred"), ("gas_act", "gas_eia"), ("used_act", "manh_1"), ("used_act", "manh_2"),
                 ("used_act", "used_l1"), ("air_act", "jet_mm"), ("shel_act", "shel_l3"), ("core_act", "core_l3"),
                 ("food_act", "food_l3"), ("elec_act", "elec_l3"), ("en_act", "en_now")):
        m = x[a].notna() & x[b].notna()
        L.append(f"   {a:9s} ← {b:9s} r {np.corrcoef(x[a][m], x[b][m])[0, 1]:+.2f} (n {m.sum()})")
    # y/y
    L.append("\n### y/y: tersirat konsensus m/m (YOY) vs tersirat perkiraan FIT (YOYn) → kejutan y/y bulat")
    for per, m in periode(df).items():
        isi = []
        for k in ("YOY", "YOYn"):
            g, s = df[k].where(m, 0).to_numpy(), df.s_yy.to_numpy()
            ok = (g != 0) & (s != 0)
            isi.append(f"{k} {pct(int((g[ok] == s[ok]).sum()), int(ok.sum()))}")
        L.append(f"   {per:8s} " + " • ".join(isi))


def yoyn(df: pd.DataFrame) -> pd.DataFrame:
    imp = (df.nsa_p1 * (1 + (df.head_fit + df.sea12) / 100) / df.nsa_p12 - 1) * 100
    d = imp - df.yy_f
    df["YOYn"] = np.where(d >= TAU, 1.0, np.where(d <= -TAU, -1.0, 0.0))
    df["yy_fit"] = imp
    return df


# ---------------------------------------------------------------- TAHAP 0: mekanisme
def tahap0(df: pd.DataFrame, L: list) -> None:
    L.append("\n## TAHAP 0 — PETA MEKANISME: kejutan bulat (m/m / inti / y/y; −1 di bawah, 0 sesuai, +1 di atas) → emas naik")
    x = df[df.th >= 2013].copy()
    x["pat"] = x.s_mm.astype(int).astype(str) + "/" + x.s_core.astype(int).astype(str) + "/" + x.s_yy.astype(int).astype(str)
    x["net"] = np.sign(2 * x.s_core + x.s_mm + x.s_yy)

    def up(s):
        s = s[(s != 0) & s.notna()]
        return f"{(s > 0).mean() * 100:3.0f}% n{len(s):<3d}" if len(s) else "   –     "
    lama, baru, b24 = x.t0 < SPLIT, x.t0 >= SPLIT, x.th >= 2024
    L.append("   kelompok             LAMA d2 / lonjakan        BARU d2 / lonjakan        2024+ d2 / lonjakan")
    kel = {"net DI BAWAH (−)": x.net < 0, "net SESUAI (0)": x.net == 0, "net DI ATAS (+)": x.net > 0,
           "semua 3 di bawah": x.pat == "-1/-1/-1", "semua 3 sesuai": x.pat == "0/0/0", "semua 3 di atas": x.pat == "1/1/1",
           "inti di bawah": x.s_core < 0, "inti sesuai": x.s_core == 0, "inti di atas": x.s_core > 0, "SEMUA rilis": x.th > 0}
    for nm, m in kel.items():
        L.append(f"   {nm:20s} " + "   ".join(f"{up(np.sign(x.g2[m & p]))} / {up(x.arah[m & p])}" for p in (lama, baru, b24)))
    L.append("   Porsi rilis per kelompok net:  " + " | ".join(
        f"{nm} " + " • ".join(f"{(np.sign(x.net[p]) == v).mean() * 100:.0f}%" for v in (-1, 0, 1))
        for nm, p in (("LAMA", lama), ("BARU", baru), ("2024+", b24))) + "  (urutan di bawah • sesuai • di atas)")


# ---------------------------------------------------------------- TAHAP 2: emas
def logit_wf(df: pd.DataFrame, kol: list[str], y: str, C: float = 1.0, mulai: int = 2014) -> pd.Series:
    from sklearn.linear_model import LogisticRegression
    out = pd.Series(np.nan, index=df.index)
    for th in sorted(df.th.unique()):
        if th < mulai:
            continue
        tr = df[(df.th < th) & (df[y] != 0) & df[y].notna()]
        te = df[df.th == th]
        if len(tr) < 30:
            continue
        yy = (tr[y] > 0).astype(int)
        if not kol:
            out[te.index] = yy.mean()
            continue
        X = tr[kol].astype(float).fillna(0)
        mu, sd = X.mean(), X.std().replace(0, 1).fillna(1)
        m = LogisticRegression(C=C, max_iter=2000).fit((X - mu) / sd, yy)
        out[te.index] = m.predict_proba((te[kol].astype(float).fillna(0) - mu) / sd)[:, 1]
    return out


def mcnemar(a: np.ndarray, b: np.ndarray) -> str:
    """a, b: benar/salah (bool) pada rilis yang sama. p dua sisi binomial pada pasangan tidak sama."""
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    n = n01 + n10
    p = binomtest(n10, n, 0.5).pvalue if n else 1.0
    return f"model benar & pembanding salah {n10} vs sebaliknya {n01} (p {p:.2f})"


def tahap2(df: pd.DataFrame, L: list) -> dict:
    L.append("\n## TAHAP 2 — EMAS: apakah tebakan kejutan menambah sesuatu DI ATAS selalu-NAIK & tren emas?")
    df["d2"], df["d1"], df["d5"], df["d10"] = (np.sign(df[f"g{h}"].fillna(0)) for h in (2, 1, 5, 10))
    df["lj"] = df.arah.fillna(0)
    df["kal_h"] = df.mm_K
    df["kal_c"] = df.core_K
    df["now_h"] = np.where((df.head_fit - df.mm_f) >= TAU, 1.0, np.where((df.head_fit - df.mm_f) <= -TAU, -1.0, 0.0))
    df["now_c"] = np.where((df.core_fit - df.core_f) >= TAU, 1.0, np.where((df.core_fit - df.core_f) <= -TAU, -1.0, 0.0))
    df.loc[df.mm_f.isna(), "now_h"] = 0.0
    df.loc[df.core_f.isna(), "now_c"] = 0.0
    df["dh_c"] = (df.core_fit - df.core_f).fillna(0)
    df["dh_h"] = (df.head_fit - df.mm_f).fillna(0)
    rez = ["T200", "mom20", "mom5"]
    kej = ["now_h", "now_c", "YOY", "kal_h", "kal_c", "SUARA_IDX", "P_mm", "P_core", "P_yy"]
    model = {"B0 konstanta": [], "B1 rezim": rez, "F1 rezim+kejutan": rez + kej, "F2 kejutan saja": kej}
    # SKOR transparan
    h = np.where(df.kal_h != 0, df.kal_h, df.now_h)
    c = np.where(df.kal_c != 0, df.kal_c, df.now_c)
    df["SKOR"] = h + c + df.YOY
    df["skor_tb"] = np.where(df.SKOR.abs() >= 2, -np.sign(df.SKOR), 0.0)
    hasil = {}
    for tgt in ("d2", "lj"):
        L.append(f"\n### target {'detik 2' if tgt == 'd2' else 'lonjakan menit 1'} (tutup kertas, tahun < Y untuk melatih)")
        P = {nm: logit_wf(df, k, tgt) for nm, k in model.items()}
        hasil[tgt] = P
        for per, m in periode(df).items():
            sel = m & df[tgt].ne(0) & P["B0 konstanta"].notna()
            y = (df[tgt][sel] > 0).astype(float).to_numpy()
            isi = []
            for nm, p in P.items():
                pp = p[sel].clip(0.01, 0.99).to_numpy()
                ll = -np.mean(y * np.log(pp) + (1 - y) * np.log(1 - pp))
                acc = ((pp >= 0.5) == (y > 0)).mean()
                isi.append(f"{nm.split()[0]} LL {ll:.3f} acc {acc * 100:.0f}%")
            L.append(f"   {per:8s} n {sel.sum():3d} | " + " | ".join(isi))
        # per arah & McNemar
        for per, m in periode(df).items():
            sel = (m & df[tgt].ne(0) & P["F1 rezim+kejutan"].notna()).to_numpy()
            y = (df[tgt] > 0).to_numpy()[sel]
            f1 = (P["F1 rezim+kejutan"] >= 0.5).to_numpy()[sel]
            b1 = (P["B1 rezim"] >= 0.5).to_numpy()[sel]
            up = np.ones_like(y, bool)
            L.append(f"   {per:8s} F1 tebak NAIK {pct(int((y[f1]).sum()), int(f1.sum()))} • tebak TURUN "
                     f"{pct(int((~y[~f1]).sum()), int((~f1).sum()))} | selalu-NAIK {pct(int(y.sum()), len(y))} | "
                     f"vs selalu-NAIK: {mcnemar(f1 == y, up == y)} | vs rezim: {mcnemar(f1 == y, b1 == y)}")
        # SKOR
        for per, m in periode(df).items():
            sel = (m & df[tgt].ne(0)).to_numpy() & (df.skor_tb != 0).to_numpy()
            y = np.sign(df[tgt]).to_numpy()[sel]
            g = df.skor_tb.to_numpy()[sel]
            allm = (m & df[tgt].ne(0)).to_numpy()
            L.append(f"   SKOR |≥2| {per:8s} tebak NAIK {pct(int((y[g > 0] > 0).sum()), int((g > 0).sum()))} • tebak TURUN "
                     f"{pct(int((y[g < 0] < 0).sum()), int((g < 0).sum()))} | selalu-NAIK di rilis yang sama "
                     f"{pct(int((y > 0).sum()), len(y))} (semua rilis {pct(int((np.sign(df[tgt]).to_numpy()[allm] > 0).sum()), int(allm.sum()))})")
    return hasil


SUMBER_ALL = ["kal_h", "kal_c", "SUARA_IDX", "now_c", "now_h", "YOY", "P_core", "P_mm", "P_yy", "KON", "JAN"]
SUMBER_5 = ["kal_h", "kal_c", "SUARA_IDX", "now_c", "P_core"]          # dipilih SETELAH melihat akurasi sumber (pasca-lihat)


def bayes_wf(df: pd.DataFrame, src: list[str], tgt: str, k: float = 1.0, mulai: int = 2014) -> pd.DataFrame:
    """RANTAI MENDASAR: P(kejutan NET di atas/sesuai/di bawah | sumber) (naive Bayes, rasio kemungkinan dari tahun < Y,
    dikali k untuk meredam korelasi antarsumber) × P(emas naik | kejutan NET) (peta mekanisme tahun < Y)."""
    out = pd.DataFrame(index=df.index, columns=["p_atas", "p_sesuai", "p_bawah", "p_naik"], dtype=float)
    for th in sorted(df.th.unique()):
        if th < mulai:
            continue
        tr, te = df[df.th < th], df[df.th == th]
        if len(tr) < 30:
            continue
        a, b = tr[tr.net > 0], tr[tr.net < 0]
        p0 = (tr.net == 0).mean()
        lo = np.full(len(te), np.log(len(a) / max(len(b), 1)))
        for s in src:
            for v in (-1.0, 1.0):
                la = ((a[s] == v).sum() + 1) / (len(a) + 3)
                lb = ((b[s] == v).sum() + 1) / (len(b) + 3)
                lo += k * np.where(te[s].to_numpy() == v, np.log(la / lb), 0.0)
        pa = (1 - p0) / (1 + np.exp(-lo))
        pb = (1 - p0) - pa
        t2 = tr[tr[tgt] != 0]
        u = {v: ((t2[tgt][t2.net == v] > 0).sum() + 1) / ((t2.net == v).sum() + 2) for v in (-1, 0, 1)}
        out.loc[te.index, "p_atas"], out.loc[te.index, "p_sesuai"], out.loc[te.index, "p_bawah"] = pa, p0, pb
        out.loc[te.index, "p_naik"] = pa * u[1] + p0 * u[0] + pb * u[-1]
    return out


def tahap3(df: pd.DataFrame, L: list) -> dict:
    L.append("\n## TAHAP 3 — RANTAI MENDASAR: sumber → peluang kejutan NET (inti ×2 + total + y/y) → peta mekanisme → peluang emas")
    L.append("   (naive Bayes tutup kertas; ALL = 11 sumber pra-registrasi; 5 = dipilih pasca-lihat; k = peredam korelasi)")
    hasil = {}
    for tgt in ("d2", "lj"):
        for nm, src, k in (("ALL k1", SUMBER_ALL, 1.0), ("ALL k½", SUMBER_ALL, 0.5), ("5 k1", SUMBER_5, 1.0),
                           ("5 k½", SUMBER_5, 0.5)):
            B = bayes_wf(df, src, tgt, k)
            hasil[(tgt, nm)] = B
            for per, m in periode(df).items():
                sel = (m & B.p_naik.notna()).to_numpy()
                net = df.net.to_numpy()[sel]
                pa, pb = B.p_atas.to_numpy()[sel], B.p_bawah.to_numpy()[sel]
                tn = np.where(pa > pb, 1, -1)
                okn = net != 0
                y = np.sign(df[tgt]).to_numpy()[sel]
                pn = B.p_naik.to_numpy()[sel]
                ok = y != 0
                yy, pp = y[ok], pn[ok]
                ll = -np.mean((yy > 0) * np.log(pp) + (yy < 0) * np.log(1 - pp))
                up_all = (yy > 0).mean()
                ll0 = -np.mean((yy > 0) * np.log(up_all) + (yy < 0) * np.log(1 - up_all))   # pembanding: rasio naik di periode itu (curang, tahu hasil)
                isi = [f"NET benar {pct(int((tn[okn] == net[okn]).sum()), int(okn.sum()))}",
                       f"LL {ll:.3f} (rasio periode {ll0:.3f})"]
                for lo_, hi_ in ((0.5, 1.01), (0.65, 1.01), (0.0, 0.5), (0.0, 0.35)):
                    mm_ = (pp >= lo_) & (pp < hi_)
                    arah = "NAIK" if lo_ >= 0.5 else "TURUN"
                    benar = int(((yy[mm_] > 0) if arah == "NAIK" else (yy[mm_] < 0)).sum())
                    isi.append(f"p{'≥' if lo_ >= 0.5 else '<'}{lo_ if lo_ >= 0.5 else hi_:.2f} {arah} {pct(benar, int(mm_.sum()))}")
                acc_m = ((pp >= 0.5) == (yy > 0))
                isi.append(mcnemar(acc_m, yy > 0).replace("model benar & pembanding salah", "vs selalu-NAIK"))
                L.append(f"   {('detik 2' if tgt == 'd2' else 'lonjakan'):8s} {nm:6s} {per:8s} " + " • ".join(isi))
    return hasil


def kalshi_kont(df: pd.DataFrame) -> pd.DataFrame:
    """Peluang Kalshi kontinu 1 jam sebelum tutup: ku_* = P(di atas konsensus), kd_* = P(di bawah)."""
    import glob
    import json

    from .kalshi_uji import curve, lean
    for seri, fk, pre in (("KXCPI", "mm_f", "h"), ("KXCPICORE", "core_f", "c")):
        df[f"ku_{pre}"], df[f"kd_{pre}"] = np.nan, np.nan
        for f in sorted(glob.glob(str(EKS / "kalshi" / seri / "*.json"))):
            ms = json.loads(Path(f).read_text(encoding="utf-8"))["pasar"]
            close = min(pd.Timestamp(m["tutup"]) for m in ms)
            i = df.index[(df.t0 >= close) & (df.t0 <= close + pd.Timedelta(minutes=15))]
            if not len(i) or df.at[i[0], fk] != df.at[i[0], fk]:
                continue
            lp = lean(curve(ms, (close - pd.Timedelta(hours=1)).timestamp()), df.at[i[0], fk], 0.1)
            if lp:
                df.at[i[0], f"ku_{pre}"], df.at[i[0], f"kd_{pre}"] = lp
    return df


def tren_inflasi(df: pd.DataFrame) -> pd.DataFrame:
    """Hipotesis ANCHORING (peramal lambat menyesuaikan): tren inti/total 3 bln vs 12 bln, perubahan y/y 6 bln."""
    from .cpi_dasar_data import potret as pt
    l12, h12, yyc = [], [], []
    for r in df.itertuples():
        v1 = r.R - pd.Timedelta(days=1)
        for out, seri in ((l12, "CPILFESL"), (h12, "CPIAUCSL")):
            p = pt(seri, v1)
            v = [mm(p, r.ref - pd.DateOffset(months=i)) for i in range(1, 13)]
            out.append(np.nanmean(v) if np.isfinite(v).any() else np.nan)
        pn = pt("CPIAUCNS", v1)
        yyc.append(mm(pn, r.ref - pd.DateOffset(months=1), 12) - mm(pn, r.ref - pd.DateOffset(months=7), 12))
    df["TREN_c"] = np.sign((df.core_l3 - pd.Series(l12, index=df.index)).fillna(0))
    df["TREN_h"] = np.sign((df.head_l3 - pd.Series(h12, index=df.index)).fillna(0))
    df["TREN_yy"] = np.sign(pd.Series(yyc, index=df.index).fillna(0))
    return df


def tahap4(df: pd.DataFrame, L: list) -> None:
    def up(s):
        s = s[(s != 0) & s.notna()]
        return f"{(s > 0).mean() * 100:.0f}% ({int((s > 0).sum())}/{len(s)})" if len(s) else "–"
    L.append("\n## TAHAP 4 — Pemeriksaan tambahan (setelah tahap 1–3)")
    L.append("### a. Tebakan perkiraan INTI dipisah per arah (|selisih| ≥ 0,08) → kejutan inti & emas")
    d = df.core_fit - df.core_f
    for nm, m in (("DI ATAS", d >= 0.08), ("DI BAWAH", d <= -0.08), ("netral", d.abs() < 0.05)):
        for per, p in (("LAMA", (df.th >= 2014) & (df.t0 < SPLIT)), ("BARU", df.t0 >= SPLIT), ("2024+", df.th >= 2024)):
            z = df[m & p]
            L.append(f"   {nm:9s} {per:6s} n{len(z):2d} kejutan inti atas {int((z.s_core > 0).sum())} sesuai "
                     f"{int((z.s_core == 0).sum())} bawah {int((z.s_core < 0).sum())} | emas naik d1 {up(z.d1)} d2 {up(z.d2)} "
                     f"d10 {up(z.d10)} lonjakan {up(z.lj)}")
    L.append("### b. Kalibrasi Kalshi (1 jam sebelum tutup, 2022–2026): condong = P(atas) − P(bawah) → kejutan bulat nyata")
    for pre, sk in (("h", "s_mm"), ("c", "s_core")):
        y = df[df[f"ku_{pre}"].notna()]
        ln = y[f"ku_{pre}"] - y[f"kd_{pre}"]
        for lo, hi in ((-1, -0.3), (-0.3, -0.1), (-0.1, 0.1), (0.1, 0.3), (0.3, 1.01)):
            z = y[(ln >= lo) & (ln < hi)]
            if len(z):
                L.append(f"   {'total' if pre == 'h' else 'inti '} condong {lo:+.1f}…{min(hi, 1):+.1f} n{len(z):2d}: nyata atas "
                         f"{(z[sk] > 0).mean() * 100:3.0f}% sesuai {(z[sk] == 0).mean() * 100:3.0f}% bawah {(z[sk] < 0).mean() * 100:3.0f}%"
                         f" | Kalshi P atas {z[f'ku_{pre}'].mean():.2f} P bawah {z[f'kd_{pre}'].mean():.2f}")
    L.append("### c. ANCHORING (tren inflasi naik → kejutan di atas?) — tebakan = tanda tren")
    for k in ("TREN_c", "TREN_h", "TREN_yy"):
        for tgt in ("s_core", "net"):
            g, s = df[k].to_numpy(), df[tgt].to_numpy()
            isi = []
            for per, m in periode(df).items():
                ok = (g != 0) & (s != 0) & m.to_numpy()
                isi.append(f"{per} {pct(int((g[ok] == s[ok]).sum()), int(ok.sum()))}")
            L.append(f"   {k:8s} → {tgt:6s} " + " | ".join(isi))
    L.append("### d. Musiman sisa: kejutan inti per bulan acuan (atas / sesuai / bawah), LAMA | BARU")
    x = df[df.th >= 2013]
    for b in range(1, 13):
        z = x[x.ref.dt.month == b]
        f = lambda q: f"{int((q.s_core > 0).sum())}/{int((q.s_core == 0).sum())}/{int((q.s_core < 0).sum())}"
        L.append(f"   bulan {b:2d}: {f(z[z.t0 < SPLIT])} | {f(z[z.t0 >= SPLIT])}")
    L.append("### e. Per tahun: porsi kejutan NET di bawah / di atas & emas naik (dari mana 'selalu NAIK' datang)")
    for th, g in x.groupby("th"):
        L.append(f"   {th}: bawah {(g.net < 0).mean() * 100:3.0f}% atas {(g.net > 0).mean() * 100:3.0f}% | emas naik d2 "
                 f"{up(g.d2)} lonjakan {up(g.lj)}")


def hari_ini(df: pd.DataFrame, L: list, R: str, kons: dict, sumber: dict) -> None:
    """Perkiraan untuk rilis berikutnya (dilatih semua rilis yang sudah lewat) + rantai Bayes dengan sumber yang diisi tangan."""
    R_ = pd.Timestamp(R)
    ref = (R_ - pd.DateOffset(months=1)).to_period("M").to_timestamp()
    o = fitur(R_, ref, manheim())
    o.update({"t0": R_.tz_localize("America/New_York").replace(hour=8, minute=30).tz_convert("UTC"), "th": 9999, **kons})
    b = pd.concat([df, pd.DataFrame([o])], ignore_index=True)
    b = fisik(b)
    b["head_fit"] = ridge_wf(b, F_HEAD, "head_act", mulai=9999)
    b["core_fit"] = ridge_wf(b, F_CORE, "core_act", mulai=9999)
    b = yoyn(b)
    r = b.iloc[-1]
    L.append(f"\n## HARI INI — CPI {R} (bulan acuan {ref:%b %Y}); konsensus {kons}")
    L.append(f"   bensin EIA {r.gas_eia:+.1f}% − musiman {r.gas_seas:+.1f} → bensin SA {r.gas_pred:+.1f}% | avtur {r.jet_mm:+.1f}% | "
             f"inti 1/3/6 bln {r.core_l1:.2f}/{r.core_l3:.2f}/{r.core_l6:.2f} | shelter 3 bln {r.shel_l3:.2f} | mobil bekas "
             f"{r.used_l1:+.2f} | Manheim {'tidak ada (xlsx s/d Nov 2025)' if r.manh_1 != r.manh_1 else f'{r.manh_1:+.1f}'}")
    L.append(f"   PERKIRAAN total fisik {r.head_fis:.2f} • fit {r.head_fit:.2f} | inti fit {r.core_fit:.2f} | y/y tersirat fit "
             f"{r.yy_fit:.2f}")
    for k, v in sumber.items():
        b.loc[b.index[-1], k] = v
    b.loc[b.index[-1], ["net", "d2", "lj"]] = [np.nan, 0, 0]
    L.append(f"   sumber: {sumber}")
    for tgt in ("d2", "lj"):
        for nm, src, k in (("ALL k1", SUMBER_ALL, 1.0), ("ALL k½", SUMBER_ALL, 0.5), ("5 k1", SUMBER_5, 1.0)):
            B = bayes_wf(b, src, tgt, k, mulai=9999).iloc[-1]
            L.append(f"   {('detik 2' if tgt == 'd2' else 'lonjakan'):8s} {nm:6s} P(net atas) {B.p_atas:.2f} sesuai {B.p_sesuai:.2f} "
                     f"bawah {B.p_bawah:.2f} → P(emas naik) {B.p_naik:.2f}")


# 14 Okt 2026: Kalshi langsung 13 Okt 14:20 UTC (m/m vs 0,6: atas 15% sesuai 45% bawah 41% → condong bawah; y/y vs 3,6:
# atas 52% bawah 13%; pasar inti tidak terbuka → 0), YOY +1 (3,71 > 3,6), kejutan inti Agustus di atas, KON +1 (0,2 < 0,3).
SUMBER_14OKT = {"kal_h": -1.0, "kal_c": 0.0, "SUARA_IDX": 0.0, "now_c": 1.0, "now_h": 0.0, "YOY": 1.0, "P_core": 1.0,
                "P_mm": 0.0, "P_yy": 0.0, "KON": 1.0, "JAN": 0.0}


def main() -> None:
    L = ["# 🧱 CPI dari dasar (research/cpi_dasar.py)", __doc__.split("\n\n")[1], __doc__.split("\n\n")[2]]
    df = tabel(cache="--ulang" not in sys.argv)
    df = fisik(df)
    df["head_fit"] = ridge_wf(df, F_HEAD, "head_act")
    df["core_fit"] = ridge_wf(df, F_CORE, "core_act")
    df = yoyn(df)
    tahap0(df, L)
    tahap1(df, L)
    tahap2(df, L)
    df["net"] = np.sign(2 * df.s_core + df.s_mm + df.s_yy)
    df["JAN"] = np.where(df.ref.dt.month == 1, 1.0, 0.0)
    tahap3(df, L)
    df = tren_inflasi(kalshi_kont(df))
    tahap4(df, L)
    hari_ini(df, L, "2026-10-14", {"mm_f": 0.6, "core_f": 0.2, "yy_f": 3.6}, SUMBER_14OKT)
    df.to_pickle(SC / "cpi_dasar_hasil.pkl")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
