"""🔗 Keterkaitan antar berita: apakah hasil berita A (rilis sebelumnya) menebak hasil berita B & arah emas di B? (15 Okt 2026)

python -m research.keterkaitan        → docs/eksternal/hasil_keterkaitan.txt + cloud/api/keterkaitan.json

Permintaan pengguna 15 Okt (setelah PPI tertebak TURUN): "semua news tepat predict seperti ini, rangkumkan dari semua
informasi yang ada, buat secara keterkaitan". Uji SEMUA pasangan judul USD berdampak tinggi ForexFactory 2010–2026
(research/news_data, kejutan USD = tanda Act − perkiraan; pengangguran & klaim dibalik): untuk setiap rilis B, kejutan A
TERAKHIR yang terbit sebelum B (≤ 35 hari, minimal 1 menit sebelumnya — tanpa look-ahead). Aturan per pasangan dipilih
HANYA dari periode LAMA (< Okt 2021): tanda hubungan (searah / berbalik) = mayoritas LAMA. Diuji di BARU (Okt 2021–2026):
  (1) ANGKA: kejutan B searah tebakan (rilis dengan kejutan A & B ≠ 0),
  (2) EMAS di B: lonjakan terbesar menit 1 (lonjakan60) & detik 2 (pra_xau_semua_v2) searah tebakan (emas = kebalikan USD),
      PER ARAH tebakan (naik / turun) + pembanding selalu-NAIK/TURUN pada rilis B yang sama.
Lolos (ditetapkan sebelum melihat BARU): LAMA angka ≥ 60% (n ≥ 20) & BARU angka ≥ 60% (n ≥ 12) & BARU emas menit 1 ≥ 60%
dan ≥ pembanding + 5 poin & tiap arah tebakan ≥ 55% (n ≥ 5). Uji acak: kejutan A digeser melingkar di deretnya (200×) →
jumlah lolos yang diharapkan kebetulan; lolos ≤ kebetulan = tidak ada keterkaitan yang bisa dipercaya.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .news_data import load_calendar

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_keterkaitan.txt"
OUT_JSON = ROOT / "cloud" / "api" / "keterkaitan.json"                       # ringkas (dibaca cloud)
OUT_PASANGAN = ROOT / "docs" / "eksternal" / "hasil_keterkaitan_pasangan.json"  # semua pasangan (riset)
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
JENDELA = pd.Timedelta(days=35)
JUDUL = ["Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m", "Core CPI m/m", "CPI m/m",
         "CPI y/y", "Core PPI m/m", "PPI m/m", "Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m",
         "Advance GDP q/q", "Prelim GDP q/q", "Unemployment Claims", "ADP Non-Farm Employment Change",
         "ISM Manufacturing PMI", "ISM Services PMI", "JOLTS Job Openings", "CB Consumer Confidence",
         "Prelim UoM Consumer Sentiment", "Core Durable Goods Orders m/m", "Philly Fed Manufacturing Index",
         "Empire State Manufacturing Index", "Federal Funds Rate"]
TARGET = ["Non-Farm Employment Change", "Core CPI m/m", "CPI m/m", "CPI y/y", "PPI m/m", "Core PPI m/m",
          "Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m", "Advance GDP q/q", "Unemployment Claims",
          "ADP Non-Farm Employment Change", "ISM Manufacturing PMI", "ISM Services PMI", "JOLTS Job Openings",
          "CB Consumer Confidence", "Unemployment Rate", "Prelim UoM Consumer Sentiment"]


def emas() -> pd.DataFrame:
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")
    lj["t"] = pd.to_datetime(lj.t0, utc=True).dt.floor("min")
    lj = lj.groupby("t").agg(m1=("arah", "first"))
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s["t"] = pd.to_datetime(s.t0, utc=True).dt.floor("min")
    s["d2"] = np.sign(s["y2_XAU_EXNESS"].where(s["y2_XAU_EXNESS"].notna(), s["y2_XAU"]))
    s = s.groupby("t").agg(d2=("d2", "first"))
    return lj.join(s, how="outer")


def kejutan() -> pd.DataFrame:
    cal = load_calendar(ROOT / "data" / "research")
    cal = cal[cal.event.isin(JUDUL) & cal.usd_surprise.notna()].copy()
    cal["t"] = cal.time.dt.floor("min")
    return cal.drop_duplicates(["t", "event"]).sort_values("t")[["t", "event", "usd_surprise"]]


def pasangan(kj: pd.DataFrame, em: pd.DataFrame, geser: dict | None = None) -> pd.DataFrame:
    """Satu baris per (rilis B, judul A): kejutan A terakhir sebelum B (≤ 35 hari) + kejutan B + emas di B."""
    seri = {e: g[["t", "usd_surprise"]].reset_index(drop=True) for e, g in kj.groupby("event")}
    if geser:                                              # uji acak: geser melingkar deret kejutan A
        seri = {e: g.assign(usd_surprise=np.roll(g.usd_surprise.to_numpy(), geser.get(e, 0))) for e, g in seri.items()}
    rows = []
    for b in TARGET:
        if b not in seri:
            continue
        gb = seri[b].merge(em, left_on="t", right_index=True, how="left")
        for a, ga in seri.items():
            if a == b:
                continue
            ta = ga.t.to_numpy()
            idx = np.searchsorted(ta, (gb.t - pd.Timedelta(minutes=1)).to_numpy(), side="right") - 1
            ok = idx >= 0
            sa = np.where(ok, ga.usd_surprise.to_numpy()[np.clip(idx, 0, None)], np.nan)
            umur = np.where(ok, (gb.t.to_numpy() - ta[np.clip(idx, 0, None)]) / np.timedelta64(1, "D"), np.inf)
            sa = np.where(umur <= JENDELA.days, sa, np.nan)
            rows.append(pd.DataFrame({"B": b, "A": a, "t": gb.t, "sB": gb.usd_surprise, "sA": sa,
                                      "m1": gb.m1, "d2": gb.d2}))
    return pd.concat(rows, ignore_index=True)


def nilai(x: pd.DataFrame) -> list[dict]:
    out = []
    for (b, a), g in x.groupby(["B", "A"]):
        g = g[g.sA.notna() & (g.sA != 0)]
        lama, baru = g[g.t < SPLIT], g[g.t >= SPLIT]
        l2 = lama[lama.sB.notna() & (lama.sB != 0)]
        if len(l2) < 20:
            continue
        sepakat = float((l2.sA == l2.sB).mean())
        r = 1 if sepakat >= 0.5 else -1                     # hubungan dipilih dari LAMA saja
        ang_l = max(sepakat, 1 - sepakat) * 100
        b2 = baru[baru.sB.notna() & (baru.sB != 0)]
        ang_b = float((r * b2.sA == b2.sB).mean() * 100) if len(b2) else np.nan
        o = {"B": b, "A": a, "hubungan": "searah" if r > 0 else "berbalik", "angka_lama": round(ang_l, 1),
             "n_lama": int(len(l2)), "angka_baru": None if np.isnan(ang_b) else round(ang_b, 1), "n_baru": int(len(b2))}
        for h in ("m1", "d2"):
            for nm, q in (("lama", lama), ("baru", baru)):
                y = q[q[h].notna() & (q[h] != 0)]
                tebak = -r * y.sA                                  # emas = kebalikan USD tebakan B
                o[f"emas_{h}_{nm}"] = round(float((tebak == y[h]).mean() * 100), 1) if len(y) else None
                o[f"n_{h}_{nm}"] = int(len(y))
                for arah, tanda in (("naik", 1), ("turun", -1)):
                    yy = y[tebak == tanda]
                    o[f"emas_{h}_{nm}_{arah}"] = round(float((yy[h] == tanda).mean() * 100), 1) if len(yy) else None
                    o[f"n_{h}_{nm}_{arah}"] = int(len(yy))
        out.append(o)
    return out


def lolos(o: dict, dasar: dict) -> bool:
    if o["angka_lama"] < 60 or o["angka_baru"] is None or o["n_baru"] < 12 or o["angka_baru"] < 60:
        return False
    e = o.get("emas_m1_baru")
    if e is None or o["n_m1_baru"] < 12 or e < 60:
        return False
    if e < dasar.get(o["B"], 50) + 5:
        return False
    for arah in ("naik", "turun"):
        v, n = o.get(f"emas_m1_baru_{arah}"), o.get(f"n_m1_baru_{arah}", 0)
        if n >= 5 and (v is None or v < 55):
            return False
    return True


def dasar_baru(kj: pd.DataFrame, em: pd.DataFrame) -> dict:
    """Pembanding: max(selalu-NAIK, selalu-TURUN) emas menit 1 pada rilis B periode BARU."""
    out = {}
    for b, g in kj.groupby("event"):
        y = g.merge(em, left_on="t", right_index=True, how="left")
        y = y[(y.t >= SPLIT) & y.m1.notna() & (y.m1 != 0)]
        if len(y):
            p = float((y.m1 > 0).mean() * 100)
            out[b] = max(p, 100 - p)
    return out


def walk_forward(g: pd.DataFrame) -> dict:
    """Tutup kertas per tahun: hubungan (searah/berbalik) dipilih dari tahun-tahun SEBELUMNYA saja (≥ 12 rilis)."""
    g = g.assign(th=g.t.dt.year)
    a, e = [], []
    for th in sorted(g.th.unique()):
        pra = g[(g.th < th) & g.sB.notna() & (g.sB != 0)]
        if len(pra) < 12:
            continue
        rr = 1 if (pra.sA == pra.sB).mean() >= 0.5 else -1
        q = g[g.th == th]
        qa, qe = q[q.sB.notna() & (q.sB != 0)], q[q.m1.notna() & (q.m1 != 0)]
        a += list((rr * qa.sA == qa.sB).astype(int))
        e += list((-rr * qe.sA == qe.m1).astype(int))
    return {"angka_wf": round(float(np.mean(a)) * 100, 1) if a else None, "n_angka_wf": len(a),
            "emas_wf": round(float(np.mean(e)) * 100, 1) if e else None, "n_emas_wf": len(e)}


def tampil(x: pd.DataFrame, hasil: list[dict]) -> dict:
    """Keterkaitan yang ditampilkan aplikasi (info, bukan arah utama): per berita B, maks 3 berita A yang ANGKANYA berkaitan
    konsisten (LAMA ≥ 58% n ≥ 20, BARU ≥ 55% n ≥ 10, walk-forward ≥ 58%), urut ketepatan angka walk-forward. Emas = walk-
    forward menit 1 (status: ≥ 60% & LAMA/BARU ≥ 55% → "belum terbukti"; ≥ 55% → "lemah"; lainnya "≈ acak")."""
    out: dict[str, list] = {}
    for o in hasil:
        if o["angka_lama"] < 58 or o["n_baru"] < 10 or (o["angka_baru"] or 0) < 55:
            continue
        g = x[(x.A == o["A"]) & (x.B == o["B"]) & x.sA.notna() & (x.sA != 0)]
        wf = walk_forward(g)
        if (wf["angka_wf"] or 0) < 58:
            continue
        e = wf["emas_wf"] or 0
        sub = [(o.get("emas_m1_lama"), o.get("n_m1_lama", 0)), (o.get("emas_m1_baru"), o.get("n_m1_baru", 0))]
        sub = [v for v, n_ in sub if v is not None and n_ >= 5]            # sub-periode < 5 rilis tidak menentukan
        if e < 52 or any(v < 50 for v in sub):                             # aturan audit: emas tidak ikut angka
            status = "≈ acak"
        elif e >= 60 and all(v >= 55 for v in sub):
            status = "belum terbukti"
        else:
            status = "lemah" if e >= 55 else "≈ acak"
        out.setdefault(o["B"], []).append({"A": o["A"], "hubungan": o["hubungan"], **wf, "angka_lama": o["angka_lama"],
                                           "angka_baru": o["angka_baru"], "emas_lama": o.get("emas_m1_lama"),
                                           "emas_baru": o.get("emas_m1_baru"), "status_emas": status})
    return {b: sorted(v, key=lambda r: -(r["angka_wf"] or 0))[:3] for b, v in out.items()}


def main(acak: int = 200) -> None:
    kj, em = kejutan(), emas()
    x = pasangan(kj, em)
    hasil = nilai(x)
    dasar = dasar_baru(kj, em)
    tampil_ = tampil(x, hasil)
    ok = [o for o in hasil if lolos(o, dasar)]
    rng = np.random.default_rng(15)
    n_acak = []
    panjang = kj.groupby("event").size().to_dict()
    for _ in range(acak):
        geser = {e: int(rng.integers(5, max(6, n - 5))) for e, n in panjang.items()}
        n_acak.append(sum(lolos(o, dasar) for o in nilai(pasangan(kj, em, geser))))
    lama_acak = (json.loads(OUT_JSON.read_text(encoding="utf-8")).get("acak") if OUT_JSON.exists() else None) or {}
    if not n_acak and lama_acak:                                  # python -m research.keterkaitan 0: hasil uji acak lama
        n_acak = [lama_acak["rata"]]
    n_acak = np.array(n_acak or [0.0])
    p = float((n_acak >= len(ok)).mean()) if acak else lama_acak.get("p", float("nan"))
    if not acak and lama_acak:
        acak, n_acak = lama_acak.get("n", 200), np.array([lama_acak["rata"]])
    L = ["# 🔗 Keterkaitan antar berita (research/keterkaitan.py)", __doc__.split("\n\n")[1],
         f"pasangan diuji: {len(hasil)} • lolos: {len(ok)} • uji acak {acak}×: rata-rata lolos kebetulan {n_acak.mean():.1f} "
         f"(P95 {(np.percentile(n_acak, 95) if len(n_acak) > 1 else lama_acak.get('p95', 0)):.0f}) • p = {p:.2f}", "",
         "## Lolos"]
    for o in sorted(ok, key=lambda o: -o["emas_m1_baru"]):
        L.append(f"   {o['A']} → {o['B']} ({o['hubungan']}): angka lama {o['angka_lama']}% (n {o['n_lama']}) / baru "
                 f"{o['angka_baru']}% (n {o['n_baru']}) • emas menit 1 baru {o['emas_m1_baru']}% (n {o['n_m1_baru']}; naik "
                 f"{o.get('emas_m1_baru_naik')} / turun {o.get('emas_m1_baru_turun')}; pembanding {dasar.get(o['B'], 50):.0f}%) "
                 f"• detik 2 baru {o.get('emas_d2_baru')}%")
    L += ["", "## Angka berkaitan kuat di LAMA & BARU (≥ 60%) — terlepas dari emas"]
    for o in sorted(hasil, key=lambda o: -(o["angka_baru"] or 0)):
        if o["angka_lama"] >= 60 and (o["angka_baru"] or 0) >= 60 and o["n_baru"] >= 12:
            L.append(f"   {o['A']} → {o['B']} ({o['hubungan']}): angka lama {o['angka_lama']}% (n {o['n_lama']}) / baru "
                     f"{o['angka_baru']}% (n {o['n_baru']}) • emas menit 1 lama {o.get('emas_m1_lama')}% / baru "
                     f"{o.get('emas_m1_baru')}% (pembanding baru {dasar.get(o['B'], 50):.0f}%)")
    L += ["", "## Ditampilkan di aplikasi (angka berkaitan konsisten; emas walk-forward per tahun)"]
    for b, v in tampil_.items():
        for r in v:
            L.append(f"   {r['A']} → {b} ({r['hubungan']}): angka walk-forward {r['angka_wf']}% (n {r['n_angka_wf']}; lama "
                     f"{r['angka_lama']} / baru {r['angka_baru']}) • emas menit 1 walk-forward {r['emas_wf']}% (n "
                     f"{r['n_emas_wf']}; lama {r['emas_lama']} / baru {r['emas_baru']}) → {r['status_emas']}")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
                                    "sumber": "research/keterkaitan.py", "n_pasangan": len(hasil), "lolos": ok,
                                    "acak": {"rata": round(float(n_acak.mean()), 2), "n": acak,
                                             "p95": float(np.percentile(n_acak, 95)) if len(n_acak) > 1
                                             else lama_acak.get("p95"), "p": p},
                                    "tampil": tampil_, "dasar_baru": dasar},
                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_PASANGAN.write_text(json.dumps(hasil, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
