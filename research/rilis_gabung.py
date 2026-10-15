"""🔗 Rilis BERSAMAAN: judul mana yang menentukan arah emas bila angkanya berlawanan? (15 Okt 2026)

python -m research.rilis_gabung        → cloud/api/rilis_gabung.json + docs/eksternal/hasil_rilis_gabung.txt

Pemicu (simulasi menyeluruh 15 Okt): setelah CPI 14 Okt tab News menampilkan "CPI m/m 60% NAIK 🟢" sekaligus "Core CPI 69%
TURUN 🔴" (emas turun). Satu waktu rilis harus punya satu arah. Data: kalender ForexFactory 2010–2026 (research/news_data,
kejutan USD = tanda Act − perkiraan, pengangguran/klaim dibalik) × arah emas tick Exness (cadangan Dukascopy): lonjakan
terbesar menit pertama (research/lonjakan.py → lonjakan60.parquet, = patokan "emas 1 menit" kesimpulan aplikasi) & detik 2
(research/pra_xau_semua.py). Per judul: plafon (emas searah kejutan judul itu); per PASANGAN judul yang rilis bersamaan dengan
kejutan BERLAWANAN: seberapa sering emas mengikuti masing-masing, LAMA (< Okt 2021) / BARU. Aplikasi: _persiapan.satukan.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .news_data import load_calendar

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT_JSON = ROOT / "cloud" / "api" / "rilis_gabung.json"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_rilis_gabung.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
JUDUL = ["Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m", "Core CPI m/m", "CPI m/m",
         "CPI y/y", "Core PPI m/m", "PPI m/m", "Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m",
         "Advance GDP q/q", "Prelim GDP q/q", "Final GDP q/q", "Unemployment Claims", "ADP Non-Farm Employment Change",
         "ISM Manufacturing PMI", "ISM Services PMI", "JOLTS Job Openings", "CB Consumer Confidence",
         "Prelim UoM Consumer Sentiment", "Philly Fed Manufacturing Index", "Empire State Manufacturing Index",
         "Core Durable Goods Orders m/m"]


def tabel() -> pd.DataFrame:
    cal = load_calendar(ROOT / "data" / "research")
    cal = cal[cal.usd_surprise.notna() & cal.event.isin(JUDUL)].copy()
    cal["t"] = cal.time.dt.floor("min")
    piv = cal.pivot_table(index="t", columns="event", values="usd_surprise", aggfunc="first")
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")
    lj["t"] = pd.to_datetime(lj.t0, utc=True).dt.floor("min")
    lj = lj.groupby("t").agg(m1=("arah", "first"))
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s["t"] = pd.to_datetime(s.t0, utc=True).dt.floor("min")
    s["d2"] = np.sign(s["y2_XAU_EXNESS"].where(s["y2_XAU_EXNESS"].notna(), s["y2_XAU"]))
    s = s.groupby("t").agg(d2=("d2", "first"))
    g = piv.join(lj, how="left").join(s, how="left")
    return g[g[["m1", "d2"]].notna().any(axis=1)]


def ikut(x: pd.DataFrame, col: str, h: str) -> tuple[float | None, int]:
    """% rilis di x yang arah emasnya (h) = kebalikan kejutan USD judul col."""
    y = x[h]
    ok = y.notna() & (y != 0) & x[col].notna() & (x[col] != 0)
    n = int(ok.sum())
    return (round(float((-x.loc[ok, col] == y[ok]).mean() * 100), 1), n) if n else (None, 0)


def main() -> None:
    g = tabel()
    L = ["# 🔗 Rilis bersamaan: judul penentu arah emas (research/rilis_gabung.py)", __doc__.split("\n\n")[1],
         f"rilis bertick: {len(g)} ({g.index.min():%Y-%m-%d} … {g.index.max():%Y-%m-%d})", "", "## Plafon per judul"]
    plafon = {}
    for j in JUDUL:
        if j not in g:
            continue
        m1, n1 = ikut(g, j, "m1")
        d2, n2 = ikut(g, j, "d2")
        if n1 >= 10:
            plafon[j] = {"m1": m1, "n": n1, "d2": d2, "n_d2": n2}
            L.append(f"   {j:34s} menit 1 {m1:.0f}% (n {n1}) • detik 2 {d2:.0f}% (n {n2})")
    L += ["", "## Pasangan berlawanan (rilis bersamaan, kejutan USD berlawanan): emas mengikuti …"]
    konflik = {}
    for a, b in itertools.combinations([j for j in JUDUL if j in g], 2):
        m = g[a].notna() & g[b].notna() & (g[a] != 0) & (g[b] != 0) & (g[a] != g[b])
        x = g[m]
        if len(x) < 3:
            continue
        m1, n1 = ikut(x, a, "m1")
        d2, n2 = ikut(x, b, "d2")
        d2a = None if d2 is None else round(100 - d2, 1)
        if n1 == 0:
            continue
        menang, kalah = (a, b) if m1 >= 50 else (b, a)
        pm = m1 if menang == a else round(100 - m1, 1)
        pd2 = d2a if menang == a else d2
        lama, baru = x[x.index < SPLIT], x[x.index >= SPLIT]
        pl, nl = ikut(lama, menang, "m1")
        pb, nb = ikut(baru, menang, "m1")
        konflik[f"{menang}|{kalah}"] = {"m1": pm, "n": n1, "d2": pd2, "n_d2": n2, "lama": pl, "n_lama": nl,
                                       "baru": pb, "n_baru": nb}
        L.append(f"   {menang} > {kalah}: menit 1 {pm:.0f}% (n {n1}; lama {pl} n {nl} / baru {pb} n {nb}) • detik 2 "
                 f"{pd2}% (n {n2})")
    OUT_JSON.write_text(json.dumps({"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
                                    "sumber": "research/rilis_gabung.py", "plafon": plafon, "konflik": konflik},
                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
