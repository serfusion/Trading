"""🎯 CPI: apakah MENGGABUNGKAN petunjuk menaikkan ketepatan tebakan kejutan (Act vs konsensus)?

python -m research.cpi_gabung            → docs/eksternal/hasil_cpi_gabung.txt

Permintaan pengguna 10 Okt 2026: "jika lempar koin bisa menambah persentase, gabungkan saja". Menggabungkan sumber yang
hanya lempar koin TIDAK menaikkan ketepatan — hanya membuat angka tampak yakin. Jadi tiap sumber diuji sendiri lalu
gabungannya, pada rilis yang sama, tanpa look-ahead (semua petunjuk sudah terbit SEBELUM rilis):
  N  nowcast Cleveland Fed (vintage harian, hari sebelum rilis) vs konsensus ForexFactory: |selisih| ≥ 0,05 poin
  K  pasar Kalshi 1 jam sebelum rilis: P(di atas) − P(di bawah) konsensus (research/kalshi_uji.rows, 2022–2025)
  P  kejutan rilis sebelumnya, judul sama (research/news_prediksi P1)
  B  bensin rata-rata bulan acuan vs bulan sebelumnya (FRED GASREGW, headline saja; news_prediksi P7)
Gabungan: suara (jumlah tanda), dan "sepakat" (dua sumber searah). Benar = tanda tebakan = tanda kejutan (rilis tanpa
kejutan tidak dihitung). LAMA < Okt 2021, BARU ≥ Okt 2021. p = binomial satu sisi.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NOWCAST = ROOT / "data" / "research" / "eksternal" / "cleveland" / "nowcast_month.json"
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_gabung.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
JUDUL = {"CPI Inflation": "CPI m/m", "Core CPI Inflation": "Core CPI m/m"}
SERI = {"CPI m/m": "KXCPI", "Core CPI m/m": "KXCPICORE"}


def nowcast_table(path: Path = NOWCAST) -> pd.DataFrame:
    """Baris (event, ref "YYYY-MM", tanggal vintage, nilai nowcast m/m)."""
    rows = []
    for ch in json.loads(path.read_text(encoding="utf-8")):
        y, m = map(int, ch["chart"]["subcaption"].split("-"))
        labels = [c["label"] for c in ch["categories"][0]["category"] if not c.get("vline")]
        for ds in ch["dataset"]:
            ev = JUDUL.get(ds["seriesname"])
            if not ev:
                continue
            for lab, v in zip(labels, ds["data"]):
                val = v.get("value")
                if not val or "/" not in lab:
                    continue
                mm, dd = map(int, lab.split("/"))
                rows.append({"event": ev, "ref": f"{y}-{m:02d}",
                             "date": pd.Timestamp(y + (1 if mm < m else 0), mm, dd, tz="UTC"), "now": float(val)})
    return pd.DataFrame(rows)


def nowcast_at(nc: pd.DataFrame, ev: str, t: pd.Timestamp) -> float:
    """Nowcast bulan acuan (bulan sebelum rilis) per hari SEBELUM tanggal rilis."""
    ref = (t - pd.DateOffset(months=1)).strftime("%Y-%m")
    g = nc[(nc.event == ev) & (nc.ref == ref) & (nc.date < t.normalize())]
    return float(g.sort_values("date").now.iloc[-1]) if len(g) else np.nan


def binom_p(k: int, n: int) -> float:
    from math import comb
    return float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else 1.0


def nilai(df: pd.DataFrame, col: str) -> str:
    out = []
    for per, m in (("semua", df.t0.notna()), ("LAMA", df.t0 < SPLIT), ("BARU", df.t0 >= SPLIT)):
        x = df[m & (df[col] != 0) & df[col].notna() & (df.s != 0)]
        k, n = int((np.sign(x[col]) == x.s).sum()), len(x)
        out.append(f"{per} {k}/{n} = {k / n * 100:.0f}%" + (f" (p {binom_p(k, n):.3f})" if per == "semua" else "")
                   if n else f"{per} n 0")
    return " | ".join(out)


def tabel() -> pd.DataFrame:
    from .news_prediksi import calendar, gas_signal, last_before
    cal = calendar()
    nc = nowcast_table()
    gas = gas_signal(cal)
    try:
        from .kalshi_uji import rows as kalshi_rows
        kr = kalshi_rows()
        kr = kr[kr.seri.isin(SERI.values())]
    except Exception:  # noqa: BLE001 - data Kalshi tidak ada
        kr = pd.DataFrame(columns=["seri", "t0", "lean 1 jam"])
    out = []
    for ev in SERI:
        for i, r in cal[cal.event == ev].iterrows():
            n = nowcast_at(nc, ev, r.time)
            d = n - r.f if n == n else np.nan
            k = kr[(kr.seri == SERI[ev]) & ((kr.t0 - r.time).abs() <= pd.Timedelta(minutes=20))]
            out.append({"event": ev, "t0": r.time, "cons": r.f, "act": r.a, "s": r.s, "nowcast": n,
                        "N": 0.0 if d != d or abs(d) < 0.05 else float(np.sign(d)),
                        "K": float(np.sign(k["lean 1 jam"].iloc[0])) if len(k) and k["lean 1 jam"].iloc[0] == k[
                            "lean 1 jam"].iloc[0] and abs(k["lean 1 jam"].iloc[0]) >= 0.10 else 0.0,
                        "P": last_before(cal, ev, r.time, 45),
                        "B": gas.get(i, np.nan) if ev == "CPI m/m" else np.nan})
    df = pd.DataFrame(out)
    df["P"] = df.P.fillna(0.0)
    return df


def main() -> None:
    df = tabel()
    L = ["# 🎯 CPI: petunjuk sendiri-sendiri vs digabung (tebakan arah kejutan Act vs konsensus)",
         __doc__.split("\n\n")[1], ""]
    df["NP"] = df.N + df.P
    df["NK"] = np.where((df.N != 0) & (df.N == df.K), df.N, 0.0)
    df["NKP"] = df.N + df.K + df.P
    df["N_K_lain"] = np.where(df.K != 0, df.K, df.N)          # Kalshi bila ada, selain itu nowcast
    df["NB"] = df.N + df.B.fillna(0)
    df["K_P_lain"] = np.where(df.K != 0, df.K, df.P)          # Kalshi bila ada, selain itu kejutan bulan lalu
    df["KP"] = np.where((df.K != 0) & (df.K == df.P), df.K, 0.0)
    for ev in list(SERI) + ["gabungan"]:
        x = df if ev == "gabungan" else df[df.event == ev]
        L += ["", f"## {ev} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m}; nowcast tersedia {x.nowcast.notna().sum()})"]
        for col, nama in (("N", "N nowcast Cleveland Fed"), ("K", "K Kalshi (2022–2025)"), ("P", "P kejutan bulan lalu"),
                          ("B", "B bensin"), ("NP", "N+P suara"), ("NB", "N+B suara"), ("NK", "N & K sepakat"),
                          ("NKP", "N+K+P suara"), ("N_K_lain", "Kalshi, cadangan nowcast"),
                          ("K_P_lain", "Kalshi, cadangan kejutan lalu"), ("KP", "K & P sepakat")):
            if x[col].notna().any():
                L.append(f"   {nama:28s} {nilai(x, col)}")
    # September 2026 (rilis 14 Okt): nilai petunjuk saat ini
    nc = nowcast_table()
    for ev in SERI:
        g = nc[(nc.event == ev) & (nc.ref == "2026-09")].sort_values("date")
        if len(g):
            L.append(f"\nNowcast {ev} September 2026 per {g.date.iloc[-1]:%d %b %Y}: {g.now.iloc[-1]:.2f}%")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
