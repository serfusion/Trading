"""🎯 SEMUA berita besar USD: petunjuk sebelum rilis sendiri-sendiri vs digabung (tebakan arah kejutan Act vs konsensus).

python -m research.berita_gabung          → docs/eksternal/hasil_berita_gabung.txt

Permintaan pengguna 10 Okt 2026: "telusuri news yang lain juga, jangan hanya CPI; jika ada keakuratan selain Kalshi
gabungkan; riset dan uji validitas". Lanjutan research/cpi_gabung.py. Sumber (semua sudah terbit SEBELUM rilis):
  P  kejutan rilis sebelumnya, judul sama (≤ 45 hari; klaim ≤ 10 hari)            — semua judul
  K  pasar Kalshi 1 jam sebelum rilis (|P(atas) − P(bawah)| ≥ 0,10)                — CPI, core CPI, NFP, pengangguran,
                                                                                      core PCE (2022–2025)
  N  nowcast Cleveland Fed (hari sebelum rilis) − konsensus, |selisih| ≥ 0,05       — CPI, core CPI, core PCE
  G  GDPNow Atlanta Fed terakhir sebelum rilis − konsensus, |selisih| ≥ 0,2          — GDP advance
  A  ADP → NFP searah; klaim 4 pekan → NFP terbalik; PPI → CPI (research/news_prediksi P2–P4)
Gabungan: X&Y sepakat (dua tanda sama), X cadangan Y. Benar = tanda tebakan = tanda kejutan (rilis tanpa kejutan tidak
dihitung). LAMA < Okt 2021, BARU ≥ Okt 2021. "LOLOS" bila > 50% di LAMA & BARU (n ≥ 8 masing-masing; bila sumber
hanya ada di BARU: n ≥ 15) dan p binomial semua data < 0,05.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_gabung import SPLIT, binom_p, nowcast_table

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_berita_gabung.txt"
GDPNOW = ROOT / "data" / "research" / "eksternal" / "gdpnow" / "GDPTrackingModelDataAndForecasts.xlsx"
JUDUL = ["Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m", "CPI m/m", "Core CPI m/m",
         "CPI y/y", "PPI m/m", "Core PPI m/m", "Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m",
         "Advance GDP q/q", "ISM Manufacturing PMI", "ISM Services PMI", "JOLTS Job Openings", "Unemployment Claims",
         "ADP Non-Farm Employment Change"]
KALSHI = {"CPI m/m": "KXCPI", "Core CPI m/m": "KXCPICORE", "Non-Farm Employment Change": "KXPAYROLLS",
          "Unemployment Rate": "KXU3", "Core PCE Price Index m/m": "KXPCECORE"}


def gdpnow() -> pd.DataFrame:
    import openpyxl
    wb = openpyxl.load_workbook(GDPNOW, read_only=True, data_only=True)
    rows = []
    for r in list(wb["TrackRecord"].iter_rows(values_only=True))[1:]:
        if r[0] is None or r[1] is None or r[3] is None:
            continue
        rows.append({"q": pd.Timestamp(r[0]), "now": float(r[1]), "rilis": pd.Timestamp(r[3]).tz_localize("UTC")})
    return pd.DataFrame(rows)


def nilai(x: pd.DataFrame, col: str) -> dict:
    out = {}
    for per, m in (("semua", x.t0.notna()), ("LAMA", x.t0 < SPLIT), ("BARU", x.t0 >= SPLIT)):
        y = x[m & x[col].notna() & (x[col] != 0) & (x.s != 0)]
        k, n = int((np.sign(y[col]) == y.s).sum()), len(y)
        out[per] = (k, n)
    return out


def teks(v: dict) -> tuple[str, bool]:
    (ks, ns), (kl, nl), (kb, nb) = v["semua"], v["LAMA"], v["BARU"]
    if ns == 0:
        return "n 0", False
    p = binom_p(ks, ns)
    hanya_baru = nl == 0
    ok = p < 0.05 and ((hanya_baru and nb >= 15 and kb / nb > 0.5) or
                       (nl >= 8 and nb >= 8 and kl / nl > 0.5 and kb / nb > 0.5))
    f = lambda k, n: f"{k}/{n}={k / n * 100:.0f}%" if n else "n 0"  # noqa: E731
    return f"semua {f(ks, ns)} (p {p:.3f}) | LAMA {f(kl, nl)} | BARU {f(kb, nb)}", ok


def tabel() -> pd.DataFrame:
    from .news_prediksi import calendar, last_before, predictors
    cal = calendar()
    nc = nowcast_table()
    try:
        from .kalshi_uji import rows as kalshi_rows
        kr = kalshi_rows()
    except Exception:  # noqa: BLE001
        kr = pd.DataFrame(columns=["seri", "t0", "lean 1 jam"])
    gn = gdpnow()
    pred = predictors(cal)
    lain = {}
    for nama, (ev, ser) in pred.items():
        if nama.startswith(("P2", "P3", "P4")):
            for i, v in ser.items():
                if v == v and v != 0:
                    lain.setdefault(i, []).append(v)
    out = []
    for ev in JUDUL:
        days = 10 if ev == "Unemployment Claims" else 45
        for i, r in cal[cal.event == ev].iterrows():
            row = {"event": ev, "t0": r.time, "s": r.s, "P": last_before(cal, ev, r.time, days)}
            if ev in KALSHI:
                k = kr[(kr.seri == KALSHI[ev]) & ((kr.t0 - r.time).abs() <= pd.Timedelta(minutes=20))]
                v = k["lean 1 jam"].iloc[0] if len(k) else np.nan
                row["K"] = float(np.sign(v)) if v == v and abs(v) >= 0.10 else (0.0 if v == v else np.nan)
            nce = {"CPI m/m": "CPI m/m", "Core CPI m/m": "Core CPI m/m"}.get(ev)
            if nce:
                ref = (r.time - pd.DateOffset(months=1)).strftime("%Y-%m")
                g = nc[(nc.event == nce) & (nc.ref == ref) & (nc.date < r.time.normalize())]
                if len(g):
                    d = g.sort_values("date").now.iloc[-1] - r.f
                    row["N"] = 0.0 if abs(d) < 0.05 else float(np.sign(d))
            if ev == "Advance GDP q/q":
                g = gn[(gn.rilis - r.time.normalize()).abs() <= pd.Timedelta(days=3)]
                if len(g):
                    d = g.now.iloc[0] - r.f
                    row["G"] = 0.0 if abs(d) < 0.2 else float(np.sign(d))
            a = lain.get(i)
            if a:
                row["A"] = float(np.sign(sum(a)))
            out.append(row)
    df = pd.DataFrame(out)
    df["P"] = df.P.fillna(0.0)
    return df


def emas(df: pd.DataFrame) -> pd.DataFrame:
    """Gerak emas 1 menit (Dukascopy, research/reaksi_menit.csv) per rilis + arah emas per hasil (naik|bawah, naik|atas
    dari cloud/api/reaksi.json): uji ujung-ke-ujung "tebakan → arah emas"."""
    import json
    rm = pd.read_csv(ROOT / "data" / "research" / "eksternal" / "reaksi_menit.csv", parse_dates=["time"])
    rm = rm[["time", "event", "duka_60"]].rename(columns={"time": "t0"})
    rx = json.loads((ROOT / "cloud" / "api" / "reaksi.json").read_text(encoding="utf-8")).get("judul") or {}
    out = df.merge(rm, on=["t0", "event"], how="left")
    arah = {}
    for ev, r in rx.items():
        if "bawah" in r and "atas" in r:
            arah[ev] = (1.0 if r["bawah"]["naik60"] >= 0.5 else -1.0, 1.0 if r["atas"]["naik60"] >= 0.5 else -1.0)
    out["arah_bawah"] = out.event.map(lambda e: arah.get(e, (np.nan, np.nan))[0])
    out["arah_atas"] = out.event.map(lambda e: arah.get(e, (np.nan, np.nan))[1])
    return out


def emas_hit(x: pd.DataFrame, col: str) -> tuple[int, int]:
    y = x[x[col].notna() & (x[col] != 0) & x.duka_60.notna() & (x.duka_60 != 0) & x.arah_bawah.notna()]
    tebak = np.where(y[col] < 0, y.arah_bawah, y.arah_atas)
    return int((np.sign(y.duka_60.to_numpy()) == tebak).sum()), len(y)


def emas_teks(x: pd.DataFrame, col: str) -> str:
    """% rilis saat emas 1 menit bergerak ke arah yang ditebak (tebakan kejutan → arah emas menurut reaksi.json)."""
    y = x[x[col].notna() & (x[col] != 0) & x.duka_60.notna() & (x.duka_60 != 0) & x.arah_bawah.notna()]
    if y.empty:
        return "emas: data reaksi tidak ada"
    tebak = np.where(y[col] < 0, y.arah_bawah, y.arah_atas)
    hit = np.sign(y.duka_60.to_numpy()) == tebak
    k, n = int(hit.sum()), len(y)
    lama, baru = y.t0 < SPLIT, y.t0 >= SPLIT
    f = lambda m: f"{hit[m.to_numpy()].sum()}/{m.sum()}" if m.sum() else "n 0"  # noqa: E731
    return f"emas 1 mnt searah {k}/{n}={k / n * 100:.0f}% (p {binom_p(k, n):.3f}; LAMA {f(lama)}, BARU {f(baru)})"


def main() -> None:
    df = emas(tabel())
    df["-P"] = -df.P                                   # kejutan cenderung BERBALIK dari bulan lalu
    L = ["# 🎯 Semua berita besar USD: petunjuk sebelum rilis sendiri-sendiri vs digabung", __doc__.split("\n\n")[1], ""]
    ringkas, simpan = [], {}
    for ev in JUDUL:
        x = df[df.event == ev].copy()
        if x.empty:
            continue
        cols = {"P": "P kejutan bulan lalu", "-P": "-P berbalik dari bulan lalu"}
        for c, nama in (("K", "K Kalshi"), ("N", "N nowcast Cleveland"), ("G", "G GDPNow"), ("A", "A ADP/klaim/PPI")):
            if c in x and x[c].notna().any():
                cols[c] = nama
        srcs = [c for c in cols if c != "P"]
        for c in srcs:
            x[f"{c}&P"] = np.where((x[c].fillna(0) != 0) & (x[c] == x.P), x[c], 0.0)
            x[f"{c}|P"] = np.where(x[c].fillna(0) != 0, x[c], x.P)
            cols[f"{c}&P"], cols[f"{c}|P"] = f"{c} & P sepakat", f"{c}, cadangan P"
        if len(srcs) >= 2:
            x["suara"] = sum(x[c].fillna(0) for c in srcs) + x.P
            cols["suara"] = "suara semua"
        L += ["", f"## {ev} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})"]
        terbaik = None
        for c, nama in cols.items():
            v = nilai(x, c)
            t, ok = teks(v)
            L.append(f"   {'✅' if ok else '  '} {nama:24s} {t}" + (f"\n        → {emas_teks(x, c)}" if ok else ""))
            if ok and c in ("P", "-P", "K", "G", "K&P", "K|P"):
                ek, en = emas_hit(x, c)
                simpan.setdefault(ev, {})[c] = {"benar": v["semua"][0], "n": v["semua"][1], "lama": list(v["LAMA"]),
                                                "baru": list(v["BARU"]), "emas": [ek, en],
                                                "tahun": (lambda z: f"{z.min():%Y}–{z.max():%Y}")(
                                                    x.t0[x[c].notna() & (x[c] != 0)])}
            k, n = v["semua"]
            if ok and n and (terbaik is None or k / n > terbaik[1]):
                terbaik = (nama, k / n, n)
        ringkas.append(f"{ev:32s} terbaik lolos: " + (f"{terbaik[0]} {terbaik[1] * 100:.0f}% (n {terbaik[2]})"
                                                       if terbaik else "TIDAK ADA (≈ lempar koin)"))
    L += ["", "## Ringkasan per berita"] + ringkas
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    import json
    (ROOT / "cloud" / "api" / "petunjuk.json").write_text(json.dumps(
        {"dibuat": "research/berita_gabung.py", "aturan": simpan}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
