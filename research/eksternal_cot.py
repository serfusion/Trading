"""(3) COT ekstrem (CFTC) sebagai filter sinyal 💰 (python -m research.eksternal_cot).

Data: publicreporting.cftc.gov (Socrata)
- emas COMEX 088691, Disaggregated Futures Only (72hh-3qpy), 2006 ->: Managed Money long/short, open interest.
- bitcoin CME 133741, Traders in Financial Futures (gpe5-46if), 2018 ->: Leveraged Funds long/short.
Posisi per Selasa, terbit Jumat 15:30 ET. Tanpa look-ahead: dianggap terbit SENIN berikutnya 21:00 UTC (+6 hari,
menutup keterlambatan libur). Shutdown pemerintah AS menunda rilis berminggu-minggu -> laporan di jendela itu
dianggap baru terbit sesudah antrean selesai (perkiraan dibuat lebih lambat dari kenyataan).

Ukuran: net = (long - short) / open interest; indeks COT = persentil net di 156 laporan terakhir (3 tahun, min 52).
Varian (ditetapkan sebelum melihat hasil):
- hindari ramai Pxx : lewati BUY bila indeks >= xx% (spekulan sudah sangat long), SELL bila <= 100-xx%
- ikut ramai Pxx    : lewati BUY bila indeks <= 100-xx% (spekulan sangat short), SELL bila >= xx%
- tren posisi 4m searah/lawan: lewati BUY bila net turun (searah) / naik (lawan) dalam 4 laporan terakhir
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import asof, asset, bar_filter, cache_path, fmt_judge, judge, per_year, realistic_summary

SOURCES = {
    "XAUUSD": ("72hh-3qpy", "088691", "m_money_positions_long_all", "m_money_positions_short_all"),
    "BTCUSD": ("gpe5-46if", "133741", "lev_money_positions_long", "lev_money_positions_short"),
}
# (laporan dari, laporan s/d, dianggap terbit) — shutdown 2013, 2018-19, 2025
SHUTDOWN = [("2013-09-30", "2013-10-22", "2013-11-30"), ("2018-12-24", "2019-02-26", "2019-03-09"),
            ("2025-09-29", "2025-12-31", "2026-01-31")]


def fetch(name: str) -> pd.DataFrame:
    ds, code, lo, sh = SOURCES[name]
    path = cache_path(f"cot_{name}.json")
    if not path.exists():
        q = urllib.parse.urlencode({"cftc_contract_market_code": code, "$limit": 5000,
                                    "$order": "report_date_as_yyyy_mm_dd"})
        with urllib.request.urlopen(f"https://publicreporting.cftc.gov/resource/{ds}.json?{q}", timeout=60) as r:
            path.write_bytes(r.read())
    rows = json.loads(path.read_text())
    cols = {k for r in rows for k in r}
    lo = lo if lo in cols else lo + "_all"
    sh = sh if sh in cols else sh + "_all"
    df = pd.DataFrame({"date": pd.to_datetime([r["report_date_as_yyyy_mm_dd"][:10] for r in rows]),
                       "long": [float(r[lo]) for r in rows], "short": [float(r[sh]) for r in rows],
                       "oi": [float(r["open_interest_all"]) for r in rows]})
    df = df.drop_duplicates("date").sort_values("date").set_index("date")
    df["net"] = (df.long - df.short) / df.oi
    df["idx"] = df.net.rolling(156, min_periods=52).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    df["d4"] = df.net - df.net.shift(4)
    avail = df.index + pd.Timedelta(days=6, hours=21)
    for a, b, rel in SHUTDOWN:
        m = (df.index >= a) & (df.index <= b)
        avail = avail.where(~m, pd.Timestamp(rel) + pd.Timedelta(hours=21))
    df["available"] = avail.tz_localize("UTC")
    return df


def variants(sig: pd.DataFrame, cot: pd.DataFrame) -> dict[str, np.ndarray]:
    d = sig.dir.to_numpy()
    idx = asof(pd.DatetimeIndex(sig.t), cot.idx, pd.DatetimeIndex(cot.available))
    d4 = asof(pd.DatetimeIndex(sig.t), cot.d4, pd.DatetimeIndex(cot.available))
    out = {}
    na = np.isnan(idx)
    for p in (0.8, 0.9):
        crowded = ((d > 0) & (idx >= p)) | ((d < 0) & (idx <= 1 - p))
        against = ((d > 0) & (idx <= 1 - p)) | ((d < 0) & (idx >= p))
        out[f"hindari ramai P{p * 100:.0f}"] = na | ~crowded
        out[f"ikut ramai P{p * 100:.0f}"] = na | ~against
    out["tren posisi 4m searah"] = np.isnan(d4) | (np.sign(d4) != -d)
    out["tren posisi 4m lawan"] = np.isnan(d4) | (np.sign(d4) != d)
    return out


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        cot = fetch(name)
        lag = (cot.available - cot.index.tz_localize("UTC")).dt.days
        print(f"\nCOT {name}: {len(cot)} laporan {cot.index[0]:%Y-%m-%d} .. {cot.index[-1]:%Y-%m-%d}; net terakhir "
              f"{cot.net.iloc[-1]:+.1%} OI, indeks 3 th {cot.idx.iloc[-1]:.0%}; jeda terbit dipakai median {lag.median():.0f} hari")
        a = asset(name)
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            print(f"=== {name} — {label}: {len(sig)} sinyal (latih < {a.split:%Y}) — lolos/dibuang [dasar] ===")
            vs = variants(sig, cot)
            res = {k: judge(sig, v, a.split) for k, v in vs.items()}
            for k, j in res.items():
                print(fmt_judge(k, j))
            for k in (k for k in res if res[k]["konsisten"] and label == "semua sinyal"):
                print(f"-> {k} konsisten (semua sinyal); uji nyata semua kategori:")
                print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g, cot)[k]), only_money=False))
            if label == "💰 dikirim":
                best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
                print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")
                for k in (k for k in res if res[k]["konsisten"]):
                    print(f"-> {k} konsisten; uji nyata (filter di allow seperti cloud):")
                    print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g, cot)[k])))


if __name__ == "__main__":
    main()
