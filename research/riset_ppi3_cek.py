"""🔎 PPI putaran 3 — RANGKAIAN UJI VALIDITAS lain (13 Okt 2026, permintaan "cari metode lain untuk uji validitas").

python -m research.riset_ppi3_cek     → docs/eksternal/hasil_riset_ppi3_cek.txt

Kandidat (dari research/riset_ppi3.py, ditetapkan sebelum pemeriksaan): WTI (dipasang 13 Okt), E_KOMB, BENSIN, CPIX, CPIC,
CPIH, GABUNG. Metode (masing-masing menjawab pertanyaan berbeda):
 1. MENTAH per periode & per detik — tanpa saringan tahun (apa adanya).
 2. BOOTSTRAP BLOK TAHUN 2.000× — rentang kepercayaan 90% bila tahun-tahun "beruntung" diganti tahun lain.
 3. BAYES Beta(1,1) — peluang akurasi sebenarnya > 50% dan > 60% (bukan p-value).
 4. MEKANISME — akurasi emas yang DIHARAPKAN dari (ketepatan menebak angka × PLAFON) vs yang teramati; jauh di atas harapan
    → keunggulan bukan lewat berita (curiga kebetulan / efek lain).
 5. PLASEBO — aturan yang sama (petunjuk minyak bulan acuan) dipakai pada rilis 08:30 LAIN di bulan yang sama (CPI, Retail,
    klaim, GDP…) → bila sama baiknya, ini efek pasar umum (minyak naik → emas turun pagi itu), bukan petunjuk PPI.
 6. FEED — target Exness vs Dukascopy (rilis yang punya keduanya).
 7. ROLLING 3 tahun & HOLDOUT 2024–2026 — stabil atau hanya satu periode.
 8. BERSAMAAN — rilis PPI yang bersamaan dengan Retail Sales (seperti 15 Okt 2026) vs sendiri.
 9. MODAL KECIL — masuk t−1 dtk lot penuh, lentur, tick Exness, per $100, vs arah acak; risiko lonjakan detik 1 seperti CPI.
10. HARI INI — nilai semua petunjuk untuk PPI 15 Okt 2026.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .riset_dalam_data import EKS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_ppi3_cek.txt"
DIR = EKS / "riset_ppi3"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
KAND = ["WTI", "E_KOMB", "BENSIN", "CPIX", "CPIC", "CPIH", "GABUNG"]
TARGET = [("lonjakan", "arah"), ("d1", "d1"), ("d2", "d2"), ("d3", "d3"), ("d5", "d5"), ("d10", "d10")]


def benar(g: np.ndarray, y: np.ndarray) -> tuple[int, int]:
    ok = (g != 0) & (y != 0)
    return int((g[ok] == y[ok]).sum()), int(ok.sum())


def fmt(k: int, n: int) -> str:
    return f"{k / n * 100:.0f}% ({n})" if n else "–"


def main() -> None:
    p = pd.read_parquet(DIR / "fitur.parquet")
    p = p[p.t0.dt.year >= 2016].reset_index(drop=True)
    L = ["# 🔎 PPI putaran 3 — uji validitas lain (research/riset_ppi3_cek.py)", __doc__.split("\n\n")[1]]
    rng = np.random.default_rng(17)
    th = p.t0.dt.year.to_numpy()
    lama, baru = (p.t0 < SPLIT).to_numpy(), (p.t0 >= SPLIT).to_numpy()

    L.append("\n## 1. Mentah (tebakan emas = −petunjuk), 2016–2026 | LAMA | BARU")
    for c in KAND:
        g = -p[c].fillna(0).to_numpy()
        isi = []
        for nama, kol in TARGET:
            y = p[kol].fillna(0).to_numpy()
            isi.append(f"{nama} {fmt(*benar(g, y))} [{fmt(*benar(g[lama], y[lama]))} | {fmt(*benar(g[baru], y[baru]))}]")
        L.append(f"   {c:7s} " + " • ".join(isi))

    L.append("\n## 2. Bootstrap blok TAHUN (2.000×, lonjakan) — rentang 90% | 3. Bayes P(akurasi > 50%) / P(> 60%)")
    from scipy.stats import beta
    tahun = sorted(set(th))
    for c in KAND:
        g, y = -p[c].fillna(0).to_numpy(), p.arah.fillna(0).to_numpy()
        per = {Y: benar(g[th == Y], y[th == Y]) for Y in tahun}
        bs = []
        for _ in range(2000):
            pil = rng.choice(tahun, len(tahun))
            k = sum(per[Y][0] for Y in pil)
            n = sum(per[Y][1] for Y in pil)
            if n:
                bs.append(k / n)
        k, n = benar(g, y)
        kb, nb = benar(g[baru], y[baru])
        L.append(f"   {c:7s} {fmt(k, n)} → 90%: {np.quantile(bs, 0.05) * 100:.0f}–{np.quantile(bs, 0.95) * 100:.0f}% | Bayes "
                 f"semua P>50% {1 - beta.cdf(0.5, k + 1, n - k + 1):.2f} P>60% {1 - beta.cdf(0.6, k + 1, n - k + 1):.2f} • "
                 f"BARU P>50% {1 - beta.cdf(0.5, kb + 1, nb - kb + 1):.2f} P>60% {1 - beta.cdf(0.6, kb + 1, nb - kb + 1):.2f}")

    L.append("\n## 4. Mekanisme: harapan = a·q + (1−a)(1−q), a = tebak ANGKA benar, q = PLAFON (emas ikut kejutan)")
    for c in KAND:
        for nama, s in (("headline", p.s_head), ("core", p.s_core)):
            m = (p[c].fillna(0) != 0) & (s.fillna(0) != 0) & (p.arah.fillna(0) != 0)
            if m.sum() < 8:
                continue
            a = (p[c][m] == s[m]).mean()
            q = (-s[m] == p.arah[m]).mean()
            obs = (-p[c][m] == p.arah[m]).mean()
            L.append(f"   {c:7s} via {nama:8s}: angka {a * 100:.0f}% × plafon {q * 100:.0f}% → harapan "
                     f"{(a * q + (1 - a) * (1 - q)) * 100:.0f}% vs teramati {obs * 100:.0f}% (n {int(m.sum())})")

    plasebo(p, L)

    L.append("\n## 6. Feed: target Exness vs Dukascopy (rilis yang punya keduanya, lonjakan)")
    for c in KAND:
        g = -p[c].fillna(0).to_numpy()
        m = p.ex.notna().to_numpy() & p.du.notna().to_numpy() if "ex" in p and "du" in p else np.zeros(len(p), bool)
        ke = benar(g[m], p.ex.fillna(0).to_numpy()[m]) if m.any() else (0, 0)
        kd = benar(g[m], p.du.fillna(0).to_numpy()[m]) if m.any() else (0, 0)
        L.append(f"   {c:7s} Exness {fmt(*ke)} • Dukascopy {fmt(*kd)}")

    L.append("\n## 7. Rolling 3 tahun (lonjakan) & HOLDOUT 2024–2026")
    for c in KAND:
        g, y = -p[c].fillna(0).to_numpy(), p.arah.fillna(0).to_numpy()
        roll = [f"{Y - 2}–{Y % 100:02d} {fmt(*benar(g[(th >= Y - 2) & (th <= Y)], y[(th >= Y - 2) & (th <= Y)]))}"
                for Y in range(2018, int(th.max()) + 1)]
        L.append(f"   {c:7s} " + " • ".join(roll) + f" | holdout 2024+ {fmt(*benar(g[th >= 2024], y[th >= 2024]))}")

    L.append("\n## 8. Bersamaan dengan Retail Sales vs PPI sendiri (lonjakan / detik 2 / detik 5)")
    for c in KAND:
        g = -p[c].fillna(0).to_numpy()
        isi = []
        for nama, m in (("bersama Retail", p.dgn_retail.to_numpy()), ("sendiri", ~p.dgn_retail.to_numpy())):
            isi.append(f"{nama}: " + " / ".join(fmt(*benar(g[m], p[k].fillna(0).to_numpy()[m])) for k in ("arah", "d2", "d5")))
        L.append(f"   {c:7s} " + " • ".join(isi))

    modal_kecil(p, L)
    hari_ini(p, L)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def plasebo(p: pd.DataFrame, L: list) -> None:
    """Petunjuk minyak bulan acuan PPI dipakai pada rilis 08:30 LAIN (bukan PPI) yang jatuh di bulan kalender yang sama."""
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "grup", "arah"]]
    lj2 = pd.read_parquet(EKS / "riset_dalam" / "lonjakan.parquet")[["t0", "grup", "arah"]]
    x = pd.concat([lj, lj2]).dropna(subset=["arah"]).drop_duplicates("t0")
    ny = x.t0.dt.tz_convert("America/New_York")
    x = x[(ny.dt.hour == 8) & (ny.dt.minute == 30) & (x.grup != "PPI") & (x.t0.dt.year >= 2016)]
    x = x[~x.t0.isin(p.t0)]
    x["bln"] = x.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    p2 = p.assign(bln=p.t0.dt.tz_convert("America/New_York").dt.strftime("%Y-%m"))
    L.append("\n## 5. Plasebo: petunjuk PPI bulan itu dipakai pada rilis 08:30 LAIN di bulan yang sama (lonjakan)")
    for c in ("WTI", "E_KOMB", "BENSIN"):
        m = x.merge(p2[["bln", c]], on="bln", how="inner")
        g, y = -m[c].fillna(0).to_numpy(), m.arah.to_numpy()
        gp, yp = -p[c].fillna(0).to_numpy(), p.arah.fillna(0).to_numpy()
        per_grup = " • ".join(f"{gg} {fmt(*benar(g[(m.grup == gg).to_numpy()], y[(m.grup == gg).to_numpy()]))}"
                              for gg in ("CPI", "RETAIL", "CLAIMS", "NFP", "GDP"))
        L.append(f"   {c:7s} PPI {fmt(*benar(gp, yp))} vs rilis lain {fmt(*benar(g, y))} ({per_grup})")


def modal_kecil(p: pd.DataFrame, L: list) -> None:
    from .cpi_allin2 import arr
    from .cpi_spike import jalan
    from .riset_dalam_data import ticks
    rng = np.random.default_rng(23)
    L.append("\n## 9. Modal kecil (t−1 dtk, lot penuh, lentur, tick Exness, per $100; acak = arah acak 2.000×)")
    A = {}
    for t in p.t0:
        tk = ticks(t)
        if tk is not None:
            A[t] = arr(tk, t)
    for c in ("WTI", "E_KOMB", "GABUNG", "CPIX"):
        for lev in (200, 500):
            for per, mp in (("LAMA", p.t0 < SPLIT), ("BARU", p.t0 >= SPLIT)):
                z = p[mp & (p[c].fillna(0) != 0) & p.t0.isin(A)]
                res = [jalan(A[t], int(-v), -1.0, lev, "lentur") for t, v in zip(z.t0, z[c])]
                res = [r for r in res if r is not None]
                if not res:
                    continue
                pl = np.array([r[0] for r in res])
                ac = []
                for _ in range(300):
                    rr = [jalan(A[t], int(rng.choice([-1, 1])), -1.0, lev, "lentur") for t in z.t0]
                    ac.append(np.mean([r[0] for r in rr if r is not None]))
                L.append(f"   {c:7s} 1:{lev} {per}: n {len(pl):2d} untung {(pl > 0).mean() * 100:3.0f}% rata ${pl.mean():+6.1f} "
                         f"habis {sum(r[1] for r in res)} | acak ${np.mean(ac):+6.1f} (p {(np.array(ac) >= pl.mean()).mean():.2f})")
    # lonjakan melawan detik 0–10 saat arah benar (seperti CPI): % harga
    rows = []
    for t, v in zip(p.t0, p.WTI.fillna(0)):
        if v == 0 or t not in A:
            continue
        s, bid, ask = A[t]
        g = int(-v)
        i0 = int(np.searchsorted(s, -1.0, side="right")) - 1
        j10 = int(np.searchsorted(s, 10.0, side="right")) - 1
        if i0 < 0 or j10 <= i0:
            continue
        p0 = ask[i0] if g > 0 else bid[i0]
        kp = bid if g > 0 else ask
        mae = max(0.0, -float(np.min((kp[i0 + 1:j10 + 1] - p0) * g)))
        mid10 = (bid[j10] + ask[j10]) / 2 - (bid[i0] + ask[i0]) / 2
        rows.append({"t0": t, "mae_pct": mae / p0 * 100, "benar": np.sign(mid10) == g})
    r = pd.DataFrame(rows)
    if len(r):
        b = r[r.benar]
        L.append(f"   lonjakan melawan s/d detik 10 saat arah WTI benar (n {len(b)}): median {b.mae_pct.median():.3f}% • "
                 f"P90 {b.mae_pct.quantile(0.9):.3f}% • maks {b.mae_pct.max():.3f}% harga → batas habis 1:500 = 0,200%, "
                 f"1:1000 = 0,100%")


def hari_ini(p: pd.DataFrame, L: list) -> None:
    """PPI 15 Okt 2026 (bulan acuan Sep 2026): konsensus Nasdaq headline 0,5% / core 0,3% (diambil 13 Okt)."""
    from .riset_ppi3 import fred_harian, jendela13
    ref, prv = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-08-01")
    ch = {}
    for nama, seri in (("WTI", "DCOILWTICO"), ("bensin", "DGASUSGULF"), ("solar", "DDFUELUSGULF")):
        s = fred_harian(seri)
        a, b = jendela13(s, ref), jendela13(s, prv)
        ch[nama] = (a / b - 1) * 100 if a == a and b == b else np.nan
    e = np.nanmean(list(ch.values()))
    from .pra_per_berita import fred_awal
    tr = fred_awal("PPITSS")
    m = (tr.value.get(prv) / tr.value.get(pd.Timestamp("2026-07-01")) - 1) * 100 if prv in tr.index else np.nan
    L.append("\n## 10. PPI 15 Okt 2026 (acuan Sep; konsensus headline 0,5% / core 0,3%; BERSAMAAN Retail Sales 0,3%)")
    L.append("   energi bulan acuan: " + " • ".join(f"{k} {v:+.1f}%" for k, v in ch.items()) + f" → keranjang {e:+.1f}%")
    L.append(f"   WTI ≥ +5% → PPI di ATAS → emas TURUN • E_KOMB sama • E_GAP: konsensus headline − core = +0,2 (> 0,1) → energi "
             f"dianggap SUDAH masuk konsensus → diam • margin dagang Agu m/m {m:+.2f}% → M_BALIK "
             f"{'diam' if abs(m) < 0.8 else ('di BAWAH' if m > 0 else 'di ATAS')} • CPIC/CPIH/CPIX: menunggu CPI 14 Okt")


if __name__ == "__main__":
    main()
