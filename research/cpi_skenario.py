"""🎯 CPI: konsistensi inti (YOYc) + mesin SKENARIO pasar × hasil dolar historis (13 Okt 2026 sore).

python -m research.cpi_skenario [--live]     → docs/eksternal/hasil_cpi_skenario.txt

Lanjutan docs/CPI_PPI_DASAR.md setelah pengguna menolak jawaban "50:50". Tiga bagian:
 A. YOYc — inti y/y TERSIRAT dari konsensus inti m/m + indeks inti (versi hari sebelum rilis) vs konsensus inti y/y Nasdaq.
    Bila konsensus y/y LEBIH TINGGI dari tersirat (selisih ≤ −0,03), angka inti m/m konsensus yang tak dibulatkan berada di
    batas atas → inti m/m jarang keluar DI BAWAH. Uji binomial vs dasar, per periode, kepekaan ambang 0,02–0,05.
 B. Siapa yang digerakkan per detik: rilis yang kejutan total m/m ≠ kejutan inti → emas ikut yang mana di detik 1/2/3/5/10/
    lonjakan (hipotesis "total dibaca dulu" — ditolak bila inti menang sejak detik 2).
 C. MESIN SKENARIO: peluang (kejutan total, kejutan inti) dari pasar Kalshi langsung (total m/m: ≤0,5 / 0,6 / ≥0,7; inti:
    ≤0,1 / 0,2 / ≥0,3; dianggap saling bebas) × hasil dolar NYATA per sel (tick Exness 2016+, beli di ask t−1 dtk, jual di
    bid; SELL kebalikannya): BUY/SELL tutup detik 2, detik 10, "lentur" (detik 2 untung → tahan s/d 10). Sel kosong → sel inti
    saja. Varian peluang inti dari aturan YOYc (bila aktif). LAMA / BARU / 2024+.
Kalshi tervalidasi (docs/eksternal/hasil_cpi_dasar.txt tahap 4b): condong kuat akurat; peluang dipakai apa adanya.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .cpi_dasar import SC, SPLIT
from .cpi_dasar_data import potret

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_skenario.txt"
SNAP = ROOT / "data" / "research" / "eksternal" / "cpi_dasar" / "kalshi_live_20261013.json"


def pct(k, n) -> str:
    return f"{k / n * 100:.0f}% ({k}/{n})" if n else "–"


def tambah_cyy(df: pd.DataFrame) -> pd.DataFrame:
    from .nasdaq_kalender import cpi as nas
    rows = []
    for r in df.itertuples():
        n = nas(r.R)
        c = potret("CPILFESL", r.R - pd.Timedelta(days=1))
        p1, p12 = r.ref - pd.DateOffset(months=1), r.ref - pd.DateOffset(months=12)
        imp = (c[p1] * (1 + r.core_f / 100) / c[p12] - 1) * 100 if p1 in c.index and p12 in c.index and r.core_f == r.core_f else np.nan
        ca = potret("CPILFESL", r.R)
        act = (ca.get(r.ref, np.nan) / ca.get(p12, np.nan) - 1) * 100
        rows.append({"t0": r.t0, "cyy_f": n.get("core_yy_f", np.nan), "cyy_a": n.get("core_yy_a", np.nan), "cyy_imp": imp,
                     "cyy_sa": act})
    df = df.merge(pd.DataFrame(rows), on="t0")
    df["s_cyy"] = np.sign((df.cyy_a.fillna(df.cyy_sa.round(1)) - df.cyy_f).round(2))
    df["d_cyy"] = df.cyy_imp - df.cyy_f
    df["YOYc"] = np.where(df.d_cyy >= 0.03, 1.0, np.where(df.d_cyy <= -0.03, -1.0, 0.0))
    return df


def bagian_a(df: pd.DataFrame, L: list) -> None:
    L.append("\n## A. YOYc — konsensus inti y/y > tersirat dari konsensus inti m/m → inti m/m jarang DI BAWAH")
    for thr in (0.02, 0.03, 0.04, 0.05):
        m = df.d_cyy <= -thr
        z = df[m]
        k, n = int((z.s_core < 0).sum()), len(z)
        isi = []
        for per, p in (("LAMA", df.t0 < SPLIT), ("BARU", df.t0 >= SPLIT)):
            zz, base = df[m & p], (df[p].s_core < 0).mean()
            kk = int((zz.s_core < 0).sum())
            isi.append(f"{per} di bawah {kk}/{len(zz)} vs dasar {base * 100:.0f}% (p {binomtest(kk, len(zz), base, alternative='less').pvalue:.3f})"
                       if len(zz) else f"{per} –")
        base = (df.s_core < 0).mean()
        L.append(f"   ambang {thr:.2f}: n {n} inti di atas {int((z.s_core > 0).sum())} sesuai {int((z.s_core == 0).sum())} di bawah {k} "
                 f"(dasar {base * 100:.0f}%, p {binomtest(k, n, base, alternative='less').pvalue:.4f}) | " + " | ".join(isi))

    def up(s):
        s = s[(s != 0) & s.notna()]
        return pct(int((s > 0).sum()), len(s))
    for per, p in (("LAMA", df.t0 < SPLIT), ("BARU", df.t0 >= SPLIT), ("2024+", df.th >= 2024)):
        z = df[p & (df.YOYc < 0)]
        L.append(f"   emas saat YOYc −1 {per:6s} n{len(z):2d}: detik 2 naik {up(z.d2)} • detik 10 {up(z.d10)} • lonjakan {up(z.lj)}")


def bagian_b(df: pd.DataFrame, L: list) -> None:
    L.append("\n## B. Kejutan total ≠ inti: emas mengikuti yang mana? (ikut total | ikut inti)")
    df = df.copy()
    df["d3"] = np.sign(df.g3.fillna(0))
    dis = df.s_mm != df.s_core
    for h in ("d1", "d2", "d3", "d5", "d10", "lj"):
        isi = []
        for per, p in (("LAMA", df.t0 < SPLIT), ("BARU", df.t0 >= SPLIT), ("semua", df.th > 0)):
            z = df[dis & p & (df[h] != 0)]
            a, b = z[z.s_mm != 0], z[z.s_core != 0]
            isi.append(f"{per} total {pct(int((-a.s_mm == a[h]).sum()), len(a))} inti {pct(int((-b.s_core == b[h]).sum()), len(b))}")
        L.append(f"   {h:4s} " + " | ".join(isi))


def at(tk: pd.DataFrame, t0: pd.Timestamp, s: float) -> tuple[float, float]:
    T = (tk.index - t0).total_seconds().to_numpy()
    j = int(np.searchsorted(T, s, side="right")) - 1
    return (float(tk.bid.iloc[j]), float(tk.ask.iloc[j])) if j >= 0 else (np.nan, np.nan)


def hasil_tick(df: pd.DataFrame) -> pd.DataFrame:
    from .riset_dalam_data import ticks
    rows = []
    for r in df[df.th >= 2016].itertuples():
        tk = ticks(r.t0)
        if tk is None:
            continue
        b0, a0 = at(tk, r.t0, -1)
        o = {"t0": r.t0, "th": r.th, "sm": r.s_mm, "sc": r.s_core}
        for s in (2, 10):
            b, a = at(tk, r.t0, s)
            o[f"buy{s}"], o[f"sell{s}"] = b - a0, b0 - a
            o[f"mid{s}"] = (a + b) / 2 - (a0 + b0) / 2
        o["buyL"] = o["buy10"] if o["buy2"] > 0 else o["buy2"]
        o["sellL"] = o["sell10"] if o["sell2"] > 0 else o["sell2"]
        rows.append(o)
    return pd.DataFrame(rows).dropna(subset=["buy2"])


def peluang_kalshi(live: bool) -> tuple[dict, dict]:
    if live:
        sys.path.insert(0, str(ROOT / "cloud" / "api"))
        import _kalshi as K
        d = {}
        for s in ("KXCPI", "KXCPICORE"):
            ms = [m for m in K.fetch(s)]
            ev = sorted({m["event_ticker"] for m in ms})[0] if ms else None
            d[s] = {K.strike(m["ticker"]): K.prob(m) for m in ms if m["event_ticker"] == ev}
        h, c = d["KXCPI"], d["KXCPICORE"]
    else:
        snap = json.loads(SNAP.read_text(encoding="utf-8"))
        g = lambda ev: {float(t.split("-T")[-1]): p for t, _, p, _ in snap[ev]["m"] if "-T" in t}
        h, c = g("KXCPI-26SEP"), g("KXCPICORE-26SEP")
    # "Above x" = > x → angka bulat ≥ x + 0,1
    ph = {-1: 1 - h[0.5], 0: h[0.5] - h[0.6], 1: h[0.6]}            # konsensus total 0,6
    pc = {-1: 1 - c[0.1], 0: c[0.1] - c[0.2], 1: c[0.2]}            # konsensus inti 0,2
    return ph, pc


def bagian_c(df: pd.DataFrame, L: list, live: bool) -> None:
    x = hasil_tick(df)
    ph, pc_k = peluang_kalshi(live)
    z = df[df.YOYc < 0]
    pc_y = {v: float((z.s_core == v).mean()) for v in (-1, 0, 1)}
    L.append(f"\n## C. MESIN SKENARIO — Kalshi {'langsung' if live else '13 Okt 14:20 UTC'}: total m/m {({k: round(v, 3) for k, v in ph.items()})} "
             f"• inti {({k: round(v, 3) for k, v in pc_k.items()})} | inti versi YOYc {({k: round(v, 3) for k, v in pc_y.items()})}")
    L.append("   ($/oz, harga beli ask t−1 dtk, jual bid; harapan = Σ peluang skenario × rata-rata hasil nyata sel itu)")
    per = {"LAMA": x.t0 < SPLIT, "BARU": x.t0 >= SPLIT, "2024+": x.th >= 2024}
    for nm, pc in (("Kalshi", pc_k), ("Kalshi total + inti YOYc", pc_y)):
        for p, m in per.items():
            ev = {k: 0.0 for k in ("naik2", "naik10", "buy2", "buy10", "buyL", "sell2", "sell10", "sellL")}
            for sm in (-1, 0, 1):
                for sc in (-1, 0, 1):
                    w = ph[sm] * pc[sc]
                    zz = x[m & (x.sm == sm) & (x.sc == sc)]
                    if not len(zz):
                        zz = x[m & (x.sc == sc)]
                    for k in ("buy2", "buy10", "buyL", "sell2", "sell10", "sellL"):
                        ev[k] += w * zz[k].mean()
                    ev["naik2"] += w * (zz.mid2 > 0).mean()
                    ev["naik10"] += w * (zz.mid10 > 0).mean()
            L.append(f"   {nm:25s} {p:6s} peluang naik detik 2 {ev['naik2'] * 100:3.0f}% • detik 10 {ev['naik10'] * 100:3.0f}% | BUY tutup d2 "
                     f"{ev['buy2']:+.2f} • d10 {ev['buy10']:+.2f} • lentur {ev['buyL']:+.2f} | SELL d2 {ev['sell2']:+.2f} • d10 "
                     f"{ev['sell10']:+.2f} • lentur {ev['sellL']:+.2f}")
    L.append("   isi sel BARU (n • rata BUY d2 / d10):")
    for sm in (-1, 0, 1):
        L.append("     total " + {-1: "di bawah", 0: "sesuai  ", 1: "di atas "}[sm] + " | " + " | ".join(
            f"inti {({-1: 'bawah', 0: 'sesuai', 1: 'atas'})[sc]} n{len(q)} {q.buy2.mean():+.2f}/{q.buy10.mean():+.2f}"
            for sc in (-1, 0, 1) for q in [x[(x.t0 >= SPLIT) & (x.sm == sm) & (x.sc == sc)]]))
    w = x[x.t0 >= SPLIT].nsmallest(5, "buy2")[["t0", "sm", "sc", "buy2", "buy10"]]
    L.append("   5 hasil BUY detik 2 terburuk sejak Okt 2021: " + " • ".join(
        f"{r.t0.date()} (total {int(r.sm):+d}, inti {int(r.sc):+d}) {r.buy2:+.2f}" for r in w.itertuples()))


def main() -> None:
    L = ["# 🎯 CPI: konsistensi inti + mesin skenario (research/cpi_skenario.py)", __doc__.split("\n\n")[1]]
    df = pd.read_pickle(SC / "cpi_dasar_hasil.pkl")
    df = tambah_cyy(df)
    bagian_a(df, L)
    bagian_b(df, L)
    bagian_c(df, L, "--live" in sys.argv)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
