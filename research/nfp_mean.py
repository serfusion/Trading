"""NFP mean reversion vs deterioration lanjutan — python -m research.nfp_mean

Mengikuti "NFP Mean Reversion Validation Framework" unggahan pengguna (6 Okt 2026). Semua angka NFP adalah VINTAGE
(ALFRED/FRED API, output_type=1): perubahan bulan m = level bulan m − level bulan m−1 menurut data yang berlaku pada hari
rilis m (tanpa revisi yang baru diketahui kemudian). Indikator pendahulu memakai nilai yang sudah terbit sebelum rilis:
  * Klaim pengangguran awal (ICSA, mingguan, terbit Kamis = minggu berakhir Sabtu + 5 hari): rata 4 minggu terakhir vs 4
    minggu sebelumnya (vintage terpakai sejak 2009; sebelum itu nilai sekarang — revisi klaim kecil).
  * ADP (NPPTTL, terbit ±2 hari sebelum NFP; vintage sejak 2011): perubahan bulan yang sama vs bulan sebelumnya.
  * Tingkat pengangguran (UNRATE vintage): bulan m vs m−3 (naik = memburuk).
  * JOLTS lowongan (JTSJOL, terbit ±5 minggu sesudah bulannya; vintage sejak 2010): nilai terakhir yang terbit vs 3 bulan
    sebelumnya. ISM Employment TIDAK tersedia di FRED → tidak diuji.
  * Revisi: perubahan bulan m−1 menurut rilis m dikurangi angka pertama m−1.
Uji (urutan framework bagian 32): (1) peluang rebound setelah pelemahan vs 50% & baseline (binomial, beda proporsi,
bootstrap 10.000, Mann-Whitney); (2) kelompok skor pendahulu; (3) revisi; (4) regresi logistik walk-forward (latih
s.d. tahun Y−1, uji tahun Y); (5) regime; (6) apakah sinyal memprediksi KEJUTAN vs konsensus (ForexFactory 2010–2025)
dan reaksi emas (XAU M15 15 mnt–6 jam); (7) whipsaw 15 mnt vs 1 jam.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_nfp_mean.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


def fred(sid: str, **q) -> pd.DataFrame:
    f = cache_path(f"alfred_{sid}.json")
    if f.exists():
        obs = json.loads(f.read_text())
    else:
        q = {"series_id": sid, "api_key": os.environ["FRED_API_KEY"], "file_type": "json", "observation_start": "1997-01-01",
             "realtime_start": "1999-01-01", "realtime_end": "9999-12-31", "output_type": 1, "limit": 100000, **q}
        u = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(q)
        obs = json.load(urllib.request.urlopen(u, timeout=120))["observations"]
        f.write_text(json.dumps(obs))
    d = pd.DataFrame(obs)
    d = d[d.value != "."]
    d["value"] = d.value.astype(float)
    d["date"] = pd.to_datetime(d.date)
    d["rs"] = pd.to_datetime(d.realtime_start)
    d["re"] = pd.to_datetime(d.realtime_end.replace("9999-12-31", "2262-01-01"))
    return d


def asof_value(d: pd.DataFrame, date: pd.Timestamp, when: pd.Timestamp) -> float:
    """Nilai observasi `date` menurut vintage yang berlaku pada `when` (NaN bila belum terbit)."""
    x = d[(d.date == date) & (d.rs <= when) & (d.re > when)]
    if len(x):
        return float(x.value.iloc[0])
    y = d[(d.date == date)]
    if len(y) and y.rs.min() > when and y.rs.min() <= pd.Timestamp("2011-06-01"):
        return float(y.sort_values("rs").value.iloc[0])          # vintage belum ada (sebelum 2010/2011): pakai terawal
    return np.nan


def nfp_table() -> pd.DataFrame:
    p = fred("PAYEMS")
    first = p.groupby("date").rs.min()
    rows = []
    for m, v in first.items():
        if m < pd.Timestamp("1999-03-01"):
            continue
        lv = asof_value(p, m, v)
        lv1 = asof_value(p, m - pd.DateOffset(months=1), v)
        lv2 = asof_value(p, m - pd.DateOffset(months=2), v)
        rows.append({"month": m, "release": v, "chg": lv - lv1, "prev_rev": lv1 - lv2})
    t = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)
    t["prev_first"] = t.chg.shift(1)
    t["revision"] = t.prev_rev - t.prev_first                # revisi bulan sebelumnya yang diumumkan di rilis m
    return t


def leading(t: pd.DataFrame) -> pd.DataFrame:
    icsa, adp, ur, jol = fred("ICSA"), fred("NPPTTL"), fred("UNRATE"), fred("JTSJOL")
    icsa_now = icsa.sort_values("rs").groupby("date").value.last()
    out = []
    for r in t.itertuples():
        v = r.release
        # klaim: minggu yang sudah terbit sebelum hari rilis (minggu berakhir Sabtu, terbit +5 hari)
        wk = icsa_now[icsa_now.index + pd.Timedelta(days=5) < v]
        cl = (wk.iloc[-4:].mean() / wk.iloc[-8:-4].mean() - 1) if len(wk) >= 8 else np.nan
        # ADP bulan yang sama (terbit 2 hari sebelum NFP) vs bulan sebelumnya, vintage
        m = r.month
        a0 = asof_value(adp, m, v - pd.Timedelta(days=1))
        a1 = asof_value(adp, m - pd.DateOffset(months=1), v - pd.Timedelta(days=1))
        a2 = asof_value(adp, m - pd.DateOffset(months=2), v - pd.Timedelta(days=1))
        adp_chg, adp_prev = a0 - a1, a1 - a2
        u0 = asof_value(ur, m - pd.DateOffset(months=1), v - pd.Timedelta(days=1))
        u3 = asof_value(ur, m - pd.DateOffset(months=4), v - pd.Timedelta(days=1))
        # JOLTS: observasi terakhir yang sudah terbit
        jv = jol[(jol.rs < v) & (jol.re > v)]
        if len(jv) == 0:
            jv = jol[jol.rs == jol.rs.min()]
            jv = jv[jv.date + pd.DateOffset(months=2) < v]
        jv = jv.sort_values("date")
        jo = (jv.value.iloc[-1] / jv.value.iloc[-4] - 1) if len(jv) >= 4 else np.nan
        out.append({"claims": cl, "adp_chg": adp_chg, "adp_prev": adp_prev, "ur_d3": u0 - u3, "jolts3": jo})
    return pd.concat([t, pd.DataFrame(out)], axis=1)


def score(df: pd.DataFrame) -> pd.Series:
    s = pd.Series(0.0, index=df.index)
    s += np.where(df.claims <= -0.03, 2, np.where(df.claims >= 0.03, -2, 0))
    s += np.where(df.adp_chg > df.adp_prev + 25, 1, np.where(df.adp_chg < df.adp_prev - 25, -1, 0))
    s += np.where(df.ur_d3 <= -0.1, 1, np.where(df.ur_d3 >= 0.1, -1, 0))
    s += np.where(df.jolts3 >= 0.03, 1, np.where(df.jolts3 <= -0.03, -1, 0))
    return s


def prop_test(k: int, n: int, p0: float) -> float:
    from scipy.stats import binomtest
    return binomtest(k, n, p0, alternative="greater").pvalue if n else np.nan


def boot_ci(x: np.ndarray, rng, b: int = 10000) -> tuple[float, float]:
    if len(x) == 0:
        return (np.nan, np.nan)
    s = rng.choice(x, size=(b, len(x)), replace=True).mean(1)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def main() -> None:
    from scipy.stats import mannwhitneyu
    rng = np.random.default_rng(3)
    t = leading(nfp_table())
    # target: rilis berikutnya (angka pertama m+1) vs angka pertama m (yang diketahui pasar)
    t["next"] = t.chg.shift(-1)
    t["next_rel"] = t.release.shift(-1)
    t["up"] = (t.next > t.chg).astype(float).where(t.next.notna())
    t["d_next"] = t.next - t.chg
    for w in (12, 24, 36):
        mu, sd = t.chg.shift(1).rolling(w).mean(), t.chg.shift(1).rolling(w).std()
        t[f"z{w}"] = (t.chg - mu) / sd
    t["mean24"] = t.chg.shift(1).rolling(24).mean()
    t["d1"] = t.chg.diff()
    t["d2"] = t.chg - t.chg.shift(2)
    t["p20"] = t.d2.shift(1).expanding(36).quantile(0.2)
    # skor pendahulu untuk rilis BERIKUTNYA (informasi yang tersedia sebelum rilis m+1)
    lead_next = leading(t[["month", "release"]].assign(month=t.month + pd.DateOffset(months=1),
                                                       release=t.next_rel.fillna(t.release + pd.Timedelta(days=30))))
    for c in ("claims", "adp_chg", "adp_prev", "ur_d3", "jolts3"):
        t[f"n_{c}"] = lead_next[c].to_numpy()
    nx = t[[f"n_{c}" for c in ("claims", "adp_chg", "adp_prev", "ur_d3", "jolts3")]]
    nx.columns = ["claims", "adp_chg", "adp_prev", "ur_d3", "jolts3"]
    t["lead"] = score(nx).to_numpy()
    t = t[t.next.notna() & t.z24.notna()].reset_index(drop=True)
    t.to_csv(cache_path("nfp_mean.csv"), index=False)
    base = t.up.mean()
    L = ["# NFP mean reversion vs deterioration lanjutan (research/nfp_mean.py)",
         f"Data vintage ALFRED, bulan {t.month.min():%Y-%m} s.d. {t.month.max():%Y-%m} ({len(t)} rilis).",
         f"Baseline: NFP pertama bulan berikutnya > bulan ini di {base * 100:.1f}% rilis.", ""]
    models = {
        "A z24 ≤ −1,0": t.z24 <= -1.0, "A z24 ≤ −1,25": t.z24 <= -1.25, "A z24 ≤ −1,5": t.z24 <= -1.5,
        "A z24 ≤ −1,75": t.z24 <= -1.75, "A z24 ≤ −2,0": t.z24 <= -2.0,
        "A z12 ≤ −1,5": t.z12 <= -1.5, "A z36 ≤ −1,5": t.z36 <= -1.5,
        "B turun 2 bulan": (t.d1 < 0) & (t.d1.shift(1) < 0),
        "C turun 3 bulan & < rata-rata": (t.d1 < 0) & (t.d1.shift(1) < 0) & (t.chg < t.mean24),
        "D Δ2 ≤ persentil 20": t.d2 <= t.p20,
        "Normal (tidak satu pun)": ~((t.z24 <= -1.0) | ((t.d1 < 0) & (t.d1.shift(1) < 0)) | (t.d2 <= t.p20)),
    }
    L.append("## Uji 1–2: peluang rebound (NFP m+1 > m) setelah pelemahan")
    L.append("model | n | naik | +25K | +50K | +75K | uplift vs baseline | p binomial>50% | CI95 bootstrap | p Mann-Whitney")
    for name, m in models.items():
        x = t[m.fillna(False)]
        if len(x) < 5:
            continue
        k = int(x.up.sum())
        ci = boot_ci(x.up.to_numpy(), rng)
        rest = t[~m.fillna(False)]
        mw = mannwhitneyu(x.d_next, rest.d_next, alternative="greater").pvalue if len(rest) > 5 else np.nan
        L.append(f"{name} | {len(x)} | {k / len(x) * 100:.0f}% | {(x.d_next >= 25).mean() * 100:.0f}% | "
                 f"{(x.d_next >= 50).mean() * 100:.0f}% | {(x.d_next >= 75).mean() * 100:.0f}% | "
                 f"{(k / len(x) - base) * 100:+.0f} pp | {prop_test(k, len(x), 0.5):.3f} | "
                 f"{ci[0] * 100:.0f}–{ci[1] * 100:.0f}% | {mw:.3f}")
    det = (t.z24 <= -1.0) | ((t.d1 < 0) & (t.d1.shift(1) < 0)) | (t.d2 <= t.p20)
    L += ["", "## Uji 3: pelemahan + skor indikator pendahulu (klaim, ADP, pengangguran, JOLTS) sebelum rilis berikutnya"]
    for lab, m in (("membaik (skor ≥ +2)", t.lead >= 2), ("netral (−1..+1)", t.lead.between(-1, 1)),
                   ("memburuk (≤ −2)", t.lead <= -2)):
        for gname, g in (("pelemahan", det), ("normal", ~det)):
            x = t[g & m]
            if len(x):
                L.append(f"   {gname:9} + pendahulu {lab:18}: n {len(x):3} | naik {x.up.mean() * 100:.0f}% | "
                         f"+50K {(x.d_next >= 50).mean() * 100:.0f}% | rata perubahan {x.d_next.mean():+.0f}K")
    L += ["", "## Uji 4: revisi bulan sebelumnya"]
    for lab, m in (("revisi turun ≤ −20K", t.revision <= -20), ("revisi kecil", t.revision.abs() < 20),
                   ("revisi naik ≥ +20K", t.revision >= 20)):
        x = t[m]
        L.append(f"   {lab:20}: n {len(x):3} | NFP berikutnya naik {x.up.mean() * 100:.0f}% | rata {x.d_next.mean():+.0f}K")
    # Uji 5: logistik walk-forward
    from sklearn.linear_model import LogisticRegression
    feats = ["z24", "d1", "n_claims", "n_ur_d3", "revision", "lead"]
    t["n_adp_d"] = t.n_adp_chg - t.n_adp_prev
    feats2 = feats + ["n_adp_d", "n_jolts3"]
    L += ["", "## Uji 5: regresi logistik walk-forward (latih s.d. tahun sebelumnya, uji tiap tahun)"]
    for fs, lab in ((["z24", "d1"], "hanya NFP"), (feats, "NFP + klaim + pengangguran + revisi + skor"),
                    (feats2, "+ ADP + JOLTS (2011+)")):
        preds = []
        for y in range(2006 if lab != "+ ADP + JOLTS (2011+)" else 2013, 2027):
            tr = t[(t.month.dt.year < y)].dropna(subset=fs + ["up"])
            te = t[(t.month.dt.year == y)].dropna(subset=fs + ["up"])
            if len(tr) < 40 or te.empty:
                continue
            mu, sd = tr[fs].mean(), tr[fs].std().replace(0, 1)
            m = LogisticRegression(C=1.0, max_iter=1000).fit((tr[fs] - mu) / sd, tr.up)
            preds.append(te.assign(p=m.predict_proba((te[fs] - mu) / sd)[:, 1]))
        pr = pd.concat(preds)
        hit = ((pr.p >= 0.5) == (pr.up == 1)).mean()
        hi = pr[pr.p >= 0.65]
        L.append(f"   {lab}: n {len(pr)} akurasi {hit * 100:.0f}% (baseline selalu 'naik' {pr.up.mean() * 100:.0f}%) | "
                 f"p ≥ 0,65: n {len(hi)} naik {hi.up.mean() * 100 if len(hi) else float('nan'):.0f}%")
    L += ["", "## Regime (model A z24 ≤ −1,0 dan C)"]
    for lab, a, b in (("2003–2007", 2003, 2007), ("2008–2009", 2008, 2009), ("2010–2019", 2010, 2019),
                      ("2020–2021", 2020, 2021), ("2022–2024", 2022, 2024), ("2025–2026", 2025, 2026)):
        y = t[(t.month.dt.year >= a) & (t.month.dt.year <= b)]
        xa = y[y.z24 <= -1.0]
        xc = y[models["C turun 3 bulan & < rata-rata"].reindex(y.index).fillna(False)]
        L.append(f"   {lab}: baseline {y.up.mean() * 100:.0f}% (n {len(y)}) | A n {len(xa)} naik "
                 f"{xa.up.mean() * 100 if len(xa) else float('nan'):.0f}% | C n {len(xc)} naik "
                 f"{xc.up.mean() * 100 if len(xc) else float('nan'):.0f}%")
    # Uji 6–8: konsensus & emas
    from .news_prediksi import calendar
    from .nfp_berbalik import table
    cal = calendar()
    cal = cal[cal.event == "Non-Farm Employment Change"].copy()
    cal["rel_day"] = cal.time.dt.tz_convert(None).dt.normalize()
    t["rel_day"] = pd.to_datetime(t.next_rel).dt.normalize()
    j = t.merge(cal[["rel_day", "a", "f", "time"]], on="rel_day", how="inner")
    j["surp_up"] = (j.a > j.f).astype(float)
    j["cons_up"] = (j.f > j.chg * 1000).astype(float)                 # konsensus memperkirakan naik dari angka m
    L += ["", f"## Uji 6: apakah pelemahan + pendahulu memprediksi KEJUTAN vs konsensus? (ForexFactory, n {len(j)})",
          f"   Konsensus sendiri memperkirakan rebound (f > NFP bulan ini) di {j.cons_up.mean() * 100:.0f}% rilis; "
          f"kenyataan naik {j.up.mean() * 100:.0f}%.",
          f"   Semua rilis: aktual > konsensus {j.surp_up.mean() * 100:.0f}%."]
    jd = j[(j.z24 <= -1.0) | ((j.d1 < 0) & (j.d1.shift(1) < 0)) | (j.d2 <= j.p20)]
    for lab, m in (("pelemahan", None), ("pelemahan + pendahulu membaik", jd.lead >= 2),
                   ("pelemahan + pendahulu memburuk", jd.lead <= -2)):
        x = jd if m is None else jd[m]
        if len(x):
            L.append(f"   {lab}: n {len(x)} | NFP naik {x.up.mean() * 100:.0f}% | konsensus sudah memperkirakan naik "
                     f"{x.cons_up.mean() * 100:.0f}% | aktual > konsensus {x.surp_up.mean() * 100:.0f}%")
    g = table()
    g["rel_day"] = g.time.dt.tz_convert(None).dt.normalize()
    jg = j.merge(g[["rel_day", "p15", "p60", "p180", "p360"]], on="rel_day")
    if len(jg):
        L += ["", f"## Uji 6b: emas setelah NFP (XAU M15, n {len(jg)}) — naik % per kelompok"]
        for lab, m in (("aktual > konsensus", jg.a > jg.f), ("aktual < konsensus", jg.a < jg.f)):
            x = jg[m]
            L.append(f"   {lab}: n {len(x)} | naik 15 mnt {(x.p15 > 0).mean() * 100:.0f}% | 1 jam {(x.p60 > 0).mean() * 100:.0f}% "
                     f"| 6 jam {(x.p360 > 0).mean() * 100:.0f}% | rata 1 jam {x.p60.mean():+.1f}$")
        dd = jg[(jg.z24 <= -1.0) | ((jg.d1 < 0) & (jg.d1.shift(1) < 0)) | (jg.d2 <= jg.p20)]
        for lab, x in (("setelah pelemahan (semua)", dd), ("pelemahan + pendahulu membaik", dd[dd.lead >= 2]),
                       ("pelemahan + pendahulu memburuk", dd[dd.lead <= -2])):
            if len(x):
                L.append(f"   {lab}: n {len(x)} | emas naik 1 jam {(x.p60 > 0).mean() * 100:.0f}% | 6 jam "
                         f"{(x.p360 > 0).mean() * 100:.0f}% | rata 1 jam {x.p60.mean():+.1f}$")
        ws = (np.sign(jg.p15) != np.sign(jg.p60))
        big = (jg.a - jg.f).abs() >= (jg.a - jg.f).abs().median()
        L += ["", "## Uji 8: whipsaw (arah 15 mnt ≠ arah 1 jam)",
              f"   semua {ws.mean() * 100:.0f}% | kejutan kecil {ws[~big].mean() * 100:.0f}% | kejutan besar {ws[big].mean() * 100:.0f}%"]
    # rilis terbaru
    last = t.iloc[-1]
    L += ["", "## Kondisi terbaru (data ALFRED)",
          f"   NFP {last.month:%b %Y} = {last.chg:+.0f}K (z24 {last.z24:+.2f}); berikutnya (bulan {last.month + pd.DateOffset(months=1):%b %Y}) "
          f"sudah rilis {last.next:+.0f}K"]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
