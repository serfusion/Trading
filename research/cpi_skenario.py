"""🎯 CPI: konsistensi inti (YOYc) + mesin SKENARIO pasar × hasil dolar historis (13 Okt 2026 sore).

python -m research.cpi_skenario [--live] [simpan]     → docs/eksternal/hasil_cpi_skenario.txt (+ cpi_detik.json["yoyc"])

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


H_MID = (1, 2, 3, 5, 10, 15, 30, 60)


def tick_tabel(df: pd.DataFrame) -> pd.DataFrame:
    """Per rilis CPI 2016+: kejutan (total, inti), gerak harga tengah di beberapa detik, hasil BUY/SELL t−1 dtk."""
    from .riset_dalam_data import ticks
    rows = []
    for r in df[df.th >= 2016].itertuples():
        tk = ticks(r.t0)
        if tk is None:
            continue
        b0, a0 = at(tk, r.t0, -1)
        o = {"t0": r.t0, "th": r.th, "sm": r.s_mm, "sc": r.s_core}
        for s in H_MID:
            b, a = at(tk, r.t0, s)
            o[f"mid{s}"] = (a + b) / 2 - (a0 + b0) / 2
        for s in (2, 10):
            b, a = at(tk, r.t0, s)
            o[f"buy{s}"], o[f"sell{s}"] = b - a0, b0 - a
        o["buyL"] = o["buy10"] if o["buy2"] > 0 else o["buy2"]
        o["sellL"] = o["sell10"] if o["sell2"] > 0 else o["sell2"]
        rows.append(o)
    return pd.DataFrame(rows).dropna(subset=["buy2"])


STRAT = ("buy2", "sell2", "buy10", "sell10", "buyL", "sellL")


def sel_tabel(x: pd.DataFrame) -> dict:
    """{"sm,sc": {n, rata per strategi, naik per detik}} + cadangan per inti saja ("*,sc")."""
    out = {}
    for sm in (-1, 0, 1, None):
        for sc in (-1, 0, 1):
            z = x[(x.sc == sc) & ((x.sm == sm) if sm is not None else True)]
            if not len(z):
                continue
            k = f"{'*' if sm is None else int(sm)},{int(sc)}"
            out[k] = {"n": int(len(z)), **{s: round(float(z[s].mean()), 3) for s in STRAT},
                      "naik": {str(h): round(float((z[f"mid{h}"] > 0).mean()), 3) for h in H_MID}}
    return out


def harapan(cells: dict, ph: dict, pc: dict, min_n: int = 3) -> dict:
    """Σ peluang skenario × hasil sel (sel n < min_n → sel inti saja). Sama persis dengan cloud/api/_cpi_skenario.py."""
    ev = {s: 0.0 for s in STRAT}
    naik = {str(h): 0.0 for h in H_MID}
    for sm in (-1, 0, 1):
        for sc in (-1, 0, 1):
            w = ph[sm] * pc[sc]
            c = cells.get(f"{sm},{sc}")
            if not c or c["n"] < min_n:
                c = cells.get(f"*,{sc}")
            if not c:
                continue
            for s in STRAT:
                ev[s] += w * c[s]
            for h in naik:
                naik[h] += w * c["naik"][h]
    return {"ev": ev, "naik": naik}


def keputusan(e: dict) -> dict:
    """Arah = sisi dengan harapan tutup detik 2 lebih besar; keluar lentur hanya bila harapannya lebih besar dari detik 2."""
    ev = e["ev"]
    sisi = "buy" if ev["buy2"] >= ev["sell2"] else "sell"
    keluar = "lentur" if ev[f"{sisi}L"] > ev[f"{sisi}2"] else "detik2"
    return {"sisi": sisi, "keluar": keluar, "ev": ev[f"{sisi}{'L' if keluar == 'lentur' else '2'}"],
            "naik2": e["naik"]["2"]}


def peluang_baris(r) -> tuple[dict, dict] | None:
    if r.ku_h != r.ku_h or r.ku_c != r.ku_c:
        return None
    ph = {1: r.ku_h, -1: r.kd_h, 0: max(0.0, 1 - r.ku_h - r.kd_h)}
    pc = {1: r.ku_c, -1: r.kd_c, 0: max(0.0, 1 - r.ku_c - r.kd_c)}
    t = sum(ph.values()), sum(pc.values())
    return {k: v / t[0] for k, v in ph.items()}, {k: v / t[1] for k, v in pc.items()}


def uji_maju(df: pd.DataFrame, x: pd.DataFrame, L: list) -> dict:
    """TUTUP KERTAS: tiap rilis 2022–2026 ber-Kalshi, sel & frekuensi YOYc hanya dari rilis SEBELUMNYA."""
    L.append("\n## D. UJI TUTUP KERTAS mesin skenario (rilis 2022–2026 dengan pasar Kalshi total & inti 1 jam sebelum tutup)")
    rows = []
    for r in df[df.ku_h.notna() & df.ku_c.notna()].sort_values("t0").itertuples():
        p = peluang_baris(r)
        hasil = x[x.t0 == r.t0]
        if p is None or not len(hasil):
            continue
        h = hasil.iloc[0]
        lalu = x[x.t0 < r.t0]
        o = {"t0": r.t0, "th": r.th, "mid2": h.mid2, "mid10": h.mid10, **{s: h[s] for s in STRAT}}
        for nm, src in (("semua", lalu), ("baru", lalu[lalu.t0 >= SPLIT] if (lalu.t0 >= SPLIT).sum() >= 15 else lalu)):
            cells = sel_tabel(src)
            for var in ("kalshi", "yoyc"):
                ph, pc = p
                if var == "yoyc" and r.YOYc < 0:
                    z = df[(df.t0 < r.t0) & (df.YOYc < 0)]
                    if len(z) >= 10:
                        fq = {v: float((z.s_core == v).mean()) for v in (-1, 0, 1)}
                        pc = {v: 0.5 * pc[v] + 0.5 * fq[v] for v in (-1, 0, 1)}
                k = keputusan(harapan(cells, ph, pc))
                o[f"{nm}_{var}_sisi"], o[f"{nm}_{var}_keluar"], o[f"{nm}_{var}_p"] = k["sisi"], k["keluar"], k["naik2"]
        o["app"] = "buy" if r._asdict().get("IDX_K", np.nan) == np.nan else None
        o["idxk"] = getattr(r, "_70", None)
        rows.append(o)
    u = pd.DataFrame(rows)
    if not len(u):
        return {}
    app = df.set_index("t0")["IDX|K"]
    u["app_sisi"] = [("buy" if app.get(t, 0) < 0 else "sell") if app.get(t, 0) != 0 else None for t in u.t0]
    hasil = {}
    for kolom, nama in (("semua_kalshi", "skenario (sel semua tahun)"), ("baru_kalshi", "skenario (sel sejak Okt 2021)"),
                        ("semua_yoyc", "skenario + YOYc (sel semua tahun)"), ("baru_yoyc", "skenario + YOYc (sel sejak Okt 2021)")):
        sisi = u[f"{kolom}_sisi"]
        benar = np.where(sisi == "buy", u.mid2 > 0, u.mid2 < 0)
        ada = u.mid2 != 0
        uang = np.where(u[f"{kolom}_keluar"] == "lentur", np.where(sisi == "buy", u.buyL, u.sellL),
                        np.where(sisi == "buy", u.buy2, u.sell2))
        uang2 = np.where(sisi == "buy", u.buy2, u.sell2)
        L.append(f"   {nama:38s} arah detik 2 benar {pct(int(benar[ada].sum()), int(ada.sum()))} • tebak BUY {int((sisi == 'buy').sum())}"
                 f" • $/oz (keluar pilihan mesin) rata {np.mean(uang):+.2f}, untung {pct(int((uang > 0).sum()), len(uang))} • "
                 f"tutup detik 2 saja rata {np.mean(uang2):+.2f} • lentur dipilih {int((u[f'{kolom}_keluar'] == 'lentur').sum())}×")
        hasil[kolom] = {"benar": round(float(benar[ada].mean() * 100), 1), "n": int(ada.sum()), "rata": round(float(np.mean(uang)), 2),
                        "untung": round(float((uang > 0).mean() * 100), 1), "rata_d2": round(float(np.mean(uang2)), 2)}
    m = u.app_sisi.notna()
    ben = np.where(u.app_sisi[m] == "buy", u.mid2[m] > 0, u.mid2[m] < 0)
    ua = np.where(u.app_sisi[m] == "buy", u.buy2[m], u.sell2[m])
    L.append(f"   {'aturan aplikasi sekarang (IDX|K, tutup d2)':38s} arah detik 2 benar {pct(int(ben[(u.mid2[m] != 0).to_numpy()].sum()), int((u.mid2[m] != 0).sum()))}"
             f" • $/oz rata {np.mean(ua):+.2f} (menebak {int(m.sum())} dari {len(u)} rilis)")
    L.append(f"   {'selalu BUY tutup detik 2':38s} arah detik 2 benar {pct(int((u.mid2 > 0).sum()), int((u.mid2 != 0).sum()))} • $/oz rata "
             f"{u.buy2.mean():+.2f} • lentur {u.buyL.mean():+.2f}")
    hasil["app"] = {"benar": round(float(ben[(u.mid2[m] != 0).to_numpy()].mean() * 100), 1), "rata": round(float(np.mean(ua)), 2)}
    hasil["selalu_buy"] = {"benar": round(float((u.mid2 > 0).sum() / (u.mid2 != 0).sum() * 100), 1), "rata": round(float(u.buy2.mean()), 2)}
    for th, g in u.groupby("th"):
        sisi = g.baru_yoyc_sisi
        b = np.where(sisi == "buy", g.mid2 > 0, g.mid2 < 0)
        L.append(f"     {th}: skenario+YOYc benar {int(b.sum())}/{len(g)} • $/oz {np.where(sisi == 'buy', g.buy2, g.sell2).mean():+.2f} "
                 f"| selalu BUY {int((g.mid2 > 0).sum())}/{len(g)} {g.buy2.mean():+.2f}")
    hasil["n"] = int(len(u))
    return hasil


def yoyc_json(df: pd.DataFrame, x: pd.DataFrame, L: list) -> dict:
    """Angka untuk cloud (cpi_detik.json["yoyc"]): tebakan NAIK aturan aplikasi (IDX|K tutup kertas) saat YOYc −1 vs biasa —
    arah detik 1…60, $/oz tutup detik 2 vs lentur, LAMA/BARU; + kejutan inti saat YOYc −1."""
    from . import cpi_detik as C
    df = df.copy()
    df["tb"] = C.tetap(df, "IDX|K").to_numpy()           # +1 = emas NAIK
    m = df.merge(x, on="t0", how="inner", suffixes=("", "_x"))

    def blok(mask) -> dict:
        z = m[mask & (m.tb > 0)]
        ok = z.mid2 != 0
        o = {"n": int(len(z)), "benar": round(float((z.mid2[ok] > 0).mean() * 100), 1) if ok.any() else None,
             "d2": round(float(z.buy2.mean()), 2), "lentur": round(float(z.buyL.mean()), 2),
             "d10": round(float(z.buy10.mean()), 2), "terburuk_lentur": round(float(z.buyL.min()), 2) if len(z) else None,
             "per_detik": {str(h): round(float((z[f"mid{h}"][z[f"mid{h}"] != 0] > 0).mean() * 100), 1)
                           for h in H_MID if (z[f"mid{h}"] != 0).any()}}
        return o
    y = m.YOYc < 0
    out = {"ambang": 0.03, "dibuat": pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes"),
           "aturan": "research/cpi_skenario.py (docs/CPI_PPI_DASAR.md bagian 8)",
           "inti_bawah": [int((df.s_core[df.YOYc < 0] < 0).sum()), int((df.YOYc < 0).sum())],
           "inti_atas": int((df.s_core[df.YOYc < 0] > 0).sum()),
           "dasar_bawah": round(float((df.s_core < 0).mean() * 100), 1),
           "p_binom": float(binomtest(int((df.s_core[df.YOYc < 0] < 0).sum()), int((df.YOYc < 0).sum()),
                                      float((df.s_core < 0).mean()), alternative="less").pvalue),
           "naik": {"semua": blok(y), "lama": blok(y & (m.t0 < SPLIT)), "baru": blok(y & (m.t0 >= SPLIT))},
           "naik_biasa": {"semua": blok(~y), "lama": blok(~y & (m.t0 < SPLIT)), "baru": blok(~y & (m.t0 >= SPLIT))}}
    L.append("\n## E. Untuk cloud: tebakan NAIK aplikasi saat YOYc −1 vs biasa (tutup kertas, $/oz BUY t−1 dtk)")
    for k in ("naik", "naik_biasa"):
        for per in ("semua", "lama", "baru"):
            b = out[k][per]
            L.append(f"   {k:10s} {per:5s} n{b['n']:3d} benar detik 2 {b['benar']}% • tutup detik 2 {b['d2']:+.2f} • lentur "
                     f"{b['lentur']:+.2f} • detik 10 {b['d10']:+.2f}")
    return out


def simpan(yo: dict) -> None:
    """Gabung ke cloud/api/cpi_detik.json kunci "yoyc" (research/cpi_detik.simpan_json menjaga kunci ini)."""
    f = ROOT / "cloud" / "api" / "cpi_detik.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["yoyc"] = yo
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    L = ["# 🎯 CPI: konsistensi inti + mesin skenario (research/cpi_skenario.py)", __doc__.split("\n\n")[1]]
    df = pd.read_pickle(SC / "cpi_dasar_hasil.pkl")
    df = tambah_cyy(df)
    bagian_a(df, L)
    bagian_b(df, L)
    bagian_c(df, L, "--live" in sys.argv)
    x = tick_tabel(df)
    uji = uji_maju(df, x, L)
    yo = yoyc_json(df, x, L)
    if "simpan" in sys.argv:
        simpan(yo)
        L.append("\n→ cloud/api/cpi_detik.json kunci yoyc ditulis")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
