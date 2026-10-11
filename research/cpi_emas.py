"""🥇 Petunjuk CPI → arah EMAS: bila petunjuk bilang CPI di atas/di bawah konsensus, berapa persen emas naik/turun?

python -m research.cpi_emas               → docs/eksternal/hasil_cpi_emas.txt

Permintaan pengguna 11 Okt 2026: "arah news baru dikonversi XAU naik/turun berapa persentasenya, fokus CPI dulu baru news
lain". Uji LANGSUNG (tanpa peta perantara): petunjuk yang terbit SEBELUM rilis → tanda gerak harga tengah XAU dari t0−1 dtk
ke t0+2 dtk / 10 dtk / 1 / 5 / 15 menit / 1 jam (research/pra_menit cache: tick Exness, cadangan Dukascopy; 30 mnt & 1 jam
dari candle M15). Rilis yang harganya tidak bergerak tidak dihitung.
Arah emas yang ditebak DITETAPKAN SEBELUM melihat hasil: CPI di atas konsensus (inflasi panas) → emas TURUN, di bawah → NAIK.
Batas atas ("plafon"): bila kejutan sebenarnya sudah diketahui — tak ada petunjuk sebelum rilis yang bisa melampauinya.
Petunjuk (lihat research/cpi_gabung & cpi_petunjuk2): headline m/m K Kalshi, P kejutan lalu, N nowcast Cleveland, bensin,
WTI, solar; core K, P, N, KON (konsensus < bulan lalu), KON&P; y/y YOY (konsistensi y/y vs m/m), P, YOY|P. Petunjuk energi
tidak butuh konsensus → ikut diuji pada rilis 2026 (kalender ForexFactory berhenti Jan 2026).
Tambahan "apa pun infonya": searah/berlawanan dengan tren emas 4 jam sebelum rilis (H4, research/pra_xau_semua).
LAMA < Okt 2021, BARU ≥ Okt 2021. Lolos = searah > 50% di LAMA & BARU (n ≥ 8) dan p binomial semua < 0,05.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_gabung import binom_p

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_emas.txt"
EKS = ROOT / "data" / "research" / "eksternal"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
H = {"2 dtk": "m2", "10 dtk": "m10", "1 mnt": "m60", "5 mnt": "m300", "15 mnt": "m900", "1 jam": "m3600"}
EV = {"CPI m/m": "mm", "Core CPI m/m": "core", "CPI y/y": "yy"}


def sgn(v: float) -> float:
    return float(np.sign(v)) if v == v and v != 0 else 0.0


def emas() -> pd.DataFrame:
    g = pd.read_parquet(EKS / "pra_menit.parquet")
    g = g[g.grup == "CPI"].drop(columns="grup")
    t = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    t = t[t.grup == "CPI"][["t0", "H4"]]
    return g.merge(t, on="t0", how="left").sort_values("t0").reset_index(drop=True)


def tabel() -> pd.DataFrame:
    from .cpi_gabung import tabel as t1
    from .cpi_petunjuk2 import tabel as t2
    from .eksternal_makro import fred
    from .news_prediksi import calendar, last_before
    from .sumber_lain import ubah_bulan
    cal = calendar()
    a = t1()[["event", "t0", "N", "K", "P"]]
    b = t2()[["event", "t0", "s", "KON", "YOY"]]
    x = b.merge(a, on=["event", "t0"], how="left")
    yy = x.event == "CPI y/y"
    x.loc[yy, "P"] = [np.nan_to_num(last_before(cal, "CPI y/y", t, 45)) for t in x.t0[yy]]
    x["e"] = x.event.map(EV)
    x = x[x.e.notna()]
    w = x.pivot_table(index="t0", columns="e", values=["s", "N", "K", "P", "KON", "YOY"], aggfunc="first")
    w.columns = [f"{e}_{c}" for c, e in w.columns]
    df = emas().merge(w.reset_index(), on="t0", how="left")
    en = {"BENSIN": fred("GASREGW"), "WTI": fred("DCOILWTICO"), "SOLAR": fred("GASDESW")}
    for k, s in en.items():
        df[f"mm_{k}"] = [sgn(ubah_bulan(s, t)) for t in df.t0]
    df = df.fillna({c: 0.0 for c in df.columns if c[:3] in ("mm_", "cor", "yy_") and not c.endswith("_s")})
    # gabungan (ditetapkan sebelum melihat hasil)
    df["mm_K|P"] = np.where(df.mm_K != 0, df.mm_K, df.mm_P)
    df["core_K|P"] = np.where(df.core_K != 0, df.core_K, df.core_P)
    df["core_KON&P"] = np.where((df.core_KON != 0) & (df.core_KON == df.core_P), df.core_KON, 0.0)
    df["yy_YOY|P"] = np.where(df.yy_YOY != 0, df.yy_YOY, df.yy_P)
    df["CPI_suara"] = np.sign(df["mm_K|P"] + df["core_K|P"] + df["yy_YOY|P"])
    df["CPI_terbaik"] = np.sign(np.where(df.core_K != 0, df.core_K, df["core_KON&P"]) + df["yy_YOY|P"]
                                + np.where(df.mm_K != 0, df.mm_K, df.mm_SOLAR))
    df["CPI_sepakat"] = np.where((df["core_K|P"] != 0) & (df["core_K|P"] == df["yy_YOY|P"]), df["core_K|P"], 0.0)
    return df


def hit(df: pd.DataFrame, clue: pd.Series, h: str) -> dict:
    """Tebakan emas = −clue (CPI panas → emas turun)."""
    m = (clue != 0) & df[h].notna() & (df[h] != 0)
    y = df[m]
    ok = (np.sign(y[h]) == -clue[m]).to_numpy()
    lama, baru = (y.t0 < SPLIT).to_numpy(), (y.t0 >= SPLIT).to_numpy()
    atas, bawah = (clue[m] > 0).to_numpy(), (clue[m] < 0).to_numpy()
    return {"k": int(ok.sum()), "n": len(y), "kl": int(ok[lama].sum()), "nl": int(lama.sum()),
            "kb": int(ok[baru].sum()), "nb": int(baru.sum()),
            "turun|atas": (int(ok[atas].sum()), int(atas.sum())), "naik|bawah": (int(ok[bawah].sum()), int(bawah.sum()))}


def pct(k: int, n: int) -> str:
    return f"{k / n * 100:.0f}%" if n else "–"


def baris(nama: str, r: dict) -> tuple[str, bool]:
    p = binom_p(r["k"], r["n"])
    ok = p < 0.05 and r["nl"] >= 8 and r["nb"] >= 8 and r["kl"] / r["nl"] > 0.5 and r["kb"] / r["nb"] > 0.5
    ta, na = r["turun|atas"]
    tb, nb = r["naik|bawah"]
    return (f"   {nama:26s} {pct(r['k'], r['n']):>4s} n{r['n']:<3d} p {p:.3f} | LAMA {pct(r['kl'], r['nl']):>4s} "
            f"n{r['nl']:<3d} BARU {pct(r['kb'], r['nb']):>4s} n{r['nb']:<3d} | atas→TURUN {pct(ta, na)} ({na}) "
            f"bawah→NAIK {pct(tb, nb)} ({nb}){'  ✅' if ok else ''}"), ok


PETUNJUK = [
    ("PLAFON headline (kejutan asli)", "mm_s"), ("PLAFON core (kejutan asli)", "core_s"), ("PLAFON y/y (kejutan asli)", "yy_s"),
    ("headline K Kalshi", "mm_K"), ("headline P kejutan lalu", "mm_P"), ("headline N nowcast", "mm_N"),
    ("headline bensin", "mm_BENSIN"), ("headline WTI", "mm_WTI"), ("headline solar", "mm_SOLAR"), ("headline K|P", "mm_K|P"),
    ("core K Kalshi", "core_K"), ("core P kejutan lalu", "core_P"), ("core N nowcast", "core_N"), ("core KON", "core_KON"),
    ("core KON&P", "core_KON&P"), ("core K|P", "core_K|P"),
    ("y/y YOY konsistensi", "yy_YOY"), ("y/y P kejutan lalu", "yy_P"), ("y/y YOY|P", "yy_YOY|P"),
    ("GABUNG suara 3 judul", "CPI_suara"), ("GABUNG terbaik 3 judul", "CPI_terbaik"), ("GABUNG core & y/y sepakat", "CPI_sepakat"),
]


def peluang(df: pd.DataFrame, clue: pd.Series, h: str) -> str:
    """P(emas naik) bila petunjuk bilang DI BAWAH vs DI ATAS vs dasar semua rilis, + uji beda (permutasi 5.000×)."""
    m = df[h].notna() & (df[h] != 0)
    up = (df[h] > 0)[m].to_numpy()
    c = clue[m].to_numpy()
    t = df.t0[m]
    out = []
    for per, w in (("LAMA", (t < SPLIT).to_numpy()), ("BARU", (t >= SPLIT).to_numpy())):
        b, a = up[w & (c < 0)], up[w & (c > 0)]
        out.append(f"{per} bawah {pct(b.sum(), len(b))}/atas {pct(a.sum(), len(a))}")
    b, a = up[c < 0], up[c > 0]
    beda = b.mean() - a.mean() if len(a) and len(b) else np.nan
    rng = np.random.default_rng(1)
    sel = c != 0
    u, cc = up[sel], c[sel]
    perm = [u[p < 0].mean() - u[p > 0].mean() for p in (rng.permutation(cc) for _ in range(5000))]
    pv = float(np.mean(np.array(perm) >= beda)) if beda == beda else 1.0
    return (f"naik bila DI BAWAH {pct(b.sum(), len(b))} (n{len(b)}) | bila DI ATAS {pct(a.sum(), len(a))} (n{len(a)}) | "
            f"dasar {pct(up.sum(), len(up))} | beda {beda * 100:+.0f} poin p {pv:.3f} | " + " | ".join(out))


def main() -> None:
    df = tabel()
    df["mm_s"] = df.mm_s.fillna(0)
    df["core_s"] = df.core_s.fillna(0)
    df["yy_s"] = df.yy_s.fillna(0)
    L = ["# 🥇 Petunjuk CPI → arah emas (uji mundur langsung)", __doc__.split("\n\n")[1], "",
         f"{len(df)} rilis CPI {df.t0.min():%Y-%m}–{df.t0.max():%Y-%m} (konsensus FF s.d. "
         f"{df[df.mm_s != 0].t0.max():%Y-%m}). Kolom: % emas searah tebakan, n, p | LAMA | BARU | rincian per arah."]
    lolos = []
    for hn, h in H.items():
        L.append(f"\n## Emas {hn} setelah rilis")
        for nama, col in PETUNJUK:
            s, ok = baris(nama, hit(df, df[col], h))
            L.append(s)
            if ok and not nama.startswith("PLAFON"):
                lolos.append((hn, nama))
    L.append("\n## PELUANG EMAS NAIK menurut petunjuk (dibanding dasar semua rilis CPI; tidak tergantung tebakan arah)")
    for hn in ("2 dtk", "10 dtk", "1 mnt", "5 mnt", "1 jam"):
        L.append(f"  {hn}:")
        for nama, col in PETUNJUK:
            L.append(f"   {nama:26s} {peluang(df, df[col], H[hn])}")
    # tren emas 4 jam sebelum rilis: searah / berlawanan dengan tebakan
    L.append("\n## Ditambah tren emas 4 jam sebelum rilis (H4): tebakan emas searah tren vs berlawanan")
    tr = np.sign(df.H4.fillna(0))
    for nama, col in [p for p in PETUNJUK if not p[0].startswith("PLAFON")]:
        g = -df[col]                                       # arah emas yang ditebak
        for hn in ("10 dtk", "1 mnt", "1 jam"):
            sea = hit(df, df[col].where((g == tr) & (tr != 0), 0.0), H[hn])
            law = hit(df, df[col].where((g == -tr) & (tr != 0), 0.0), H[hn])
            s1, ok1 = baris(f"{nama} SEARAH {hn}", sea)
            L += [s1, baris(f"{nama} LAWAN  {hn}", law)[0]]
            if ok1:
                lolos.append((hn, f"{nama} + searah tren 4 jam"))
    L.append("\nLolos (tanpa plafon): " + ("; ".join(f"{n} [{h}]" for h, n in lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
