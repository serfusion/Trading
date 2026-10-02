"""Uji pola Mars–Pluto (tanda hijau pengguna) pada NFP & semua rilis: python -m research.astrologi_nfp

Pertanyaan pengguna (2 Okt 2026): chart Astro-Seek NFP 2 Okt 2026 08:30 ET — Mars 2°34' Leo dekat MC (29°32' Cancer)
dan Pluto R 3°06' Aquarius dekat IC, oposisi ±0,5° → "NFP nanti akan turun seturun-turunnya".

Hipotesis (ditetapkan sebelum melihat hasil), posisi PyEphem (tropis, Washington D.C.):
  H1 Mars–Pluto aspek keras (0/90/180°, orb 5°)      H3 Mars dekat MC/IC (<= 10°)
  H2 Mars–Pluto oposisi (orb 5°)                     H4 H1 dan H3 bersamaan (pola chart pengguna)
Target: (a) NFP di BAWAH konsensus ("turun"), (b) |kejutan| NFP besar (>= 2x median |kejutan| sebelumnya),
(c) emas naik 1 menit, (d) |gerak emas 1 menit| (median, $) — semua rilis USD bintang 3 untuk (c)–(d).
Dibandingkan dengan rilis tanpa pola; uji Fisher (proporsi) & Mann-Whitney (besar gerak); banyak uji → Bonferroni.
"""
from __future__ import annotations

import math
from pathlib import Path

import ephem
import numpy as np
import pandas as pd

from .astrologi import LAT, LON, ZODIAK, hard, lon
from .news_detik import NEW, events, prepare
from .news_prediksi import calendar

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_astrologi_nfp.txt"


def midheaven(t: ephem.Date) -> float:
    o = ephem.Observer()
    o.lat, o.lon, o.date, o.epoch = LAT, LON, t, t
    ramc = float(o.sidereal_time())
    eps = math.radians(23.4393 - 0.0000004 * (t - ephem.Date("2000/1/1")))
    return math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))) % 360


def sep(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def pattern(ts: pd.Timestamp) -> dict:
    t = ephem.Date(ts.tz_convert("UTC").tz_localize(None).to_pydatetime())
    mars, pluto, mc = lon(ephem.Mars(), t), lon(ephem.Pluto(), t), midheaven(t)
    h1 = hard(mars, pluto, 5.0)
    h2 = abs(sep(mars, pluto) - 180) <= 5.0
    h3 = min(sep(mars, mc), sep(mars, (mc + 180) % 360)) <= 10.0
    return {"H1": h1, "H2": h2, "H3": h3, "H4": h1 and h3, "_mars": mars, "_pluto": pluto, "_mc": mc}


def fisher(a: int, b: int, c: int, d: int) -> float:
    try:
        from scipy.stats import fisher_exact
        return float(fisher_exact([[a, b], [c, d]])[1])
    except Exception:  # noqa: BLE001
        return float("nan")


def mwu(x, y) -> float:
    try:
        from scipy.stats import mannwhitneyu
        return float(mannwhitneyu(x, y).pvalue) if len(x) and len(y) else float("nan")
    except Exception:  # noqa: BLE001
        return float("nan")


def report() -> str:
    t0 = pd.Timestamp("2026-10-02 12:30", tz="UTC")
    p0 = pattern(t0)
    L = ["# Pola Mars–Pluto vs NFP & emas (research/astrologi_nfp.py)", "",
         f"Cek chart pengguna: Mars {ZODIAK[int(p0['_mars'] // 30)]} {p0['_mars'] % 30:.2f}°, Pluto "
         f"{ZODIAK[int(p0['_pluto'] // 30)]} {p0['_pluto'] % 30:.2f}°, MC {ZODIAK[int(p0['_mc'] // 30)]} "
         f"{p0['_mc'] % 30:.2f}° → " + ", ".join(f"{k}={'ya' if p0[k] else 'tidak'}" for k in ("H1", "H2", "H3", "H4")),
         ""]
    cal = calendar()
    nfp = cal[cal.event == "Non-Farm Employment Change"].copy().sort_values("time")
    nfp["surp"] = nfp.a - nfp.f
    med = nfp.surp.abs().replace(0, np.nan).expanding().median().shift(1)
    nfp["besar"] = nfp.surp.abs() >= 2 * med
    pats = pd.DataFrame([pattern(t) for t in nfp.time], index=nfp.index)
    nfp = pd.concat([nfp, pats[["H1", "H2", "H3", "H4"]]], axis=1)
    k = nfp[nfp.s != 0]
    L.append(f"== NFP {k.time.min():%Y}–{k.time.max():%Y}: {len(k)} rilis dengan kejutan; dasar di bawah konsensus "
             f"{(k.s < 0).mean() * 100:.0f}% ==")
    tests = 0
    for h in ("H1", "H2", "H3", "H4"):
        a, b = k[k[h]], k[~k[h]]
        if not len(a):
            L.append(f"  {h}: tidak pernah terjadi saat NFP")
            continue
        p_t = fisher(int((a.s < 0).sum()), int((a.s > 0).sum()), int((b.s < 0).sum()), int((b.s > 0).sum()))
        p_b = fisher(int(a.besar.sum()), int((~a.besar).sum()), int(b.besar.sum()), int((~b.besar).sum()))
        tests += 2
        L.append(f"  {h}: n={len(a):3} | NFP di bawah konsensus {(a.s < 0).mean() * 100:4.0f}% (tanpa pola "
                 f"{(b.s < 0).mean() * 100:4.0f}%, p={p_t:.2f}) | kejutan besar {a.besar.mean() * 100:4.0f}% (tanpa "
                 f"{b.besar.mean() * 100:4.0f}%, p={p_b:.2f}) | tanggal: "
                 + ", ".join(f"{t:%Y-%m} {'↓' if s < 0 else '↑'}" for t, s in zip(a.time, a.s)))
    rows = []
    for e in events().itertuples():
        for aset in ("XAU", "XAU_EXNESS"):
            p = prepare(e.time, aset)
            if p is not None and p.at(-1) >= 0:
                mv = float(p.mid[p.at(60)] - p.mid[p.at(-1)])
                rows.append({"time": e.time, "group": e.group, "mv": mv, **{x: v for x, v in pattern(e.time).items()
                                                                            if not x.startswith("_")}})
                break
    g = pd.DataFrame(rows)
    g = g[g.mv != 0]
    L.append(f"\n== Emas 1 menit, semua rilis bintang 3 ({len(g)} rilis; dasar naik {(g.mv > 0).mean() * 100:.0f}%, "
             f"|gerak| median ${g.mv.abs().median():.2f}) ==")
    for h in ("H1", "H2", "H3", "H4"):
        a, b = g[g[h]], g[~g[h]]
        if not len(a):
            continue
        p_d = fisher(int((a.mv > 0).sum()), int((a.mv < 0).sum()), int((b.mv > 0).sum()), int((b.mv < 0).sum()))
        old, new = a[a.time < NEW], a[a.time >= NEW]
        # gerak dinormalkan per tahun (harga emas 2010 vs 2026 berbeda jauh): |gerak| / median |gerak| tahun itu
        yr_med = g.groupby(g.time.dt.year).mv.apply(lambda v: v.abs().median())
        rel = lambda x: (x.mv.abs() / x.time.dt.year.map(yr_med)).to_numpy()  # noqa: E731
        p_m = mwu(rel(a), rel(b))
        tests += 2
        L.append(f"  {h}: n={len(a):4} | naik {(a.mv > 0).mean() * 100:4.0f}% (tanpa pola {(b.mv > 0).mean() * 100:4.0f}%, "
                 f"p={p_d:.2f}; LAMA {(old.mv > 0).mean() * 100:.0f}% BARU {(new.mv > 0).mean() * 100:.0f}%) | "
                 f"|gerak| relatif median {np.median(rel(a)):.2f}x (tanpa {np.median(rel(b)):.2f}x, p={p_m:.2f})")
    L.append(f"\nJumlah uji: {tests} → p di bawah 0,05/{tests} = {0.05 / tests:.4f} baru dianggap bermakna (Bonferroni).")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
