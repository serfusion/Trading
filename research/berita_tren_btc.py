"""Lonjakan BTC setelah berita AS: bertahan atau kembali? python -m research.berita_tren_btc [ekspor]

Permintaan pengguna (2 Okt 2026): "uji juga BTC" (peringatan lonjakan memudar, research/berita_tren.py untuk XAU).
Data: kline 1 menit BTCUSDT Binance (data.binance.vision, 1 file per hari rilis, disimpan di
data/research/eksternal/binance_1m), rilis = research/news_prediksi.calendar() (EVENTS), 2018–2026.
Aturan sama dengan XAU: lonjakan = open menit rilis -> close 15 menit, minimal 0,1% harga dan 0,1 x rata range
harian 14 hari (dari kline yang sama, hari-hari rilis sebelumnya tidak dipakai -> range hari itu sendiri sebelum rilis
tidak tersedia, jadi pakai ambang 0,15% tetap). Ukuran: berapa % lonjakan yang SUDAH KEMBALI di menit 30 / 60
(1 − (harga − open)/puncak), lalu apakah 3 / 6 jam kemudian masih searah lonjakan dan apakah harga kembali melewati
harga rilis dalam 6 jam. LAMA (< Okt 2021) & BARU.
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path
from .news_detik import NEW
from .news_prediksi import EVENTS, calendar

URL = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{d}.zip"
START = pd.Timestamp("2018-01-01", tz="UTC")
MIN_PCT = 0.0015
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_berita_tren_btc.txt"
CLOUD = Path(__file__).resolve().parent.parent / "cloud" / "api" / "pudar.json"


def day_file(d: str) -> Path:
    p = cache_path("binance_1m")
    p.mkdir(parents=True, exist_ok=True)
    return p / f"BTCUSDT-1m-{d}.parquet"


def load_day(d: str) -> pd.DataFrame | None:
    f = day_file(d)
    if f.exists():
        return pd.read_parquet(f)
    for k in range(4):
        try:
            with urllib.request.urlopen(URL.format(d=d), timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            break
        except Exception:  # noqa: BLE001
            time.sleep(2 ** k)
    else:
        return None
    raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4])
    raw.columns = ["t", "open", "high", "low", "close"]
    unit = "us" if raw.t.iloc[0] > 1e14 else "ms"            # Binance memakai mikrodetik sejak 2025
    raw.index = pd.to_datetime(raw.t, unit=unit, utc=True)
    df = raw[["open", "high", "low", "close"]].astype("float32")
    df.to_parquet(f)
    return df


def build() -> pd.DataFrame:
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS) & (cal.time >= START)]
    groups = cal.groupby("time").event.apply(lambda v: "/".join(sorted(set(v))))
    rows = []
    for t in sorted(cal.time.unique()):
        t = pd.Timestamp(t)
        days = sorted({t.strftime("%Y-%m-%d"), (t + pd.Timedelta(hours=7)).strftime("%Y-%m-%d")})
        parts = [load_day(d) for d in days]
        if any(p is None for p in parts):
            continue
        m = pd.concat(parts).sort_index()
        idx = m.index
        k = idx.searchsorted(t)
        if k >= len(idx) or idx[k] != t:
            continue
        o = float(m.open.iloc[k])

        def close_at(minutes: int) -> float:
            j = idx.searchsorted(t + pd.Timedelta(minutes=minutes)) - 1
            return float(m.close.iloc[j])
        spike = close_at(15) - o
        if abs(spike) < MIN_PCT * o:
            continue
        s = np.sign(spike)
        row = {"time": t, "events": groups.get(t, ""), "spike_pct": spike / o * 100}
        for mins in (30, 60):
            w = m.iloc[k:idx.searchsorted(t + pd.Timedelta(minutes=mins))]
            peak = float(((w.high - o) if s > 0 else (o - w.low)).max())
            now_ = (close_at(mins) - o) * s
            row[f"keep{mins}"] = now_ / peak if peak > 0 else np.nan
        for h in (3, 6):
            row[f"h{h}"] = (close_at(60 * h) - o) * s
        win = m.iloc[k + 16:idx.searchsorted(t + pd.Timedelta(hours=6))]
        row["fade"] = bool(((win.low <= o) if s > 0 else (win.high >= o)).any())
        rows.append(row)
    return pd.DataFrame(rows)


BUCKETS = ((-9.0, 0.0, "sudah berbalik"), (0.0, 0.3, "sisa < 30%"), (0.3, 0.6, "sisa 30–60%"), (0.6, 9.0, "sisa ≥ 60%"))


def line(name: str, x: pd.DataFrame) -> str:
    if len(x) < 5:
        return f"  {name:34} n={len(x)}"
    return (f"  {name:34} n={len(x):4} searah 3 jam {(x.h3 > 0).mean() * 100:3.0f}% • 6 jam {(x.h6 > 0).mean() * 100:3.0f}%"
            f" | kembali lewat harga rilis ≤ 6 jam {x.fade.mean() * 100:3.0f}%")


def report(d: pd.DataFrame) -> str:
    L = ["# BTC: lonjakan setelah berita AS — bertahan atau kembali? (research/berita_tren_btc.py)", "",
         f"{len(d)} rilis dengan lonjakan 15 menit ≥ 0,15%, {d.time.min():%Y}–{d.time.max():%Y}.", ""]
    for mins in (30, 60):
        L.append(f"== bagian lonjakan yang masih ada di menit {mins} ==")
        for name, x in (("semua", d), ("LAMA < Okt 2021", d[d.time < NEW]), ("BARU", d[d.time >= NEW])):
            L.append(f" [{name}]")
            for lo, hi, lab in BUCKETS:
                L.append(line(lab, x[(x[f"keep{mins}"] >= lo) & (x[f"keep{mins}"] < hi)]))
        L.append("")
    return "\n".join(L) + "\n"


def export(d: pd.DataFrame) -> None:
    data = json.loads(CLOUD.read_text(encoding="utf-8"))
    out = {}
    for mins in (30, 60):
        cells = []
        for lo, hi, lab in BUCKETS:
            k = d[(d[f"keep{mins}"] >= lo) & (d[f"keep{mins}"] < hi)]
            kb = k[k.time >= NEW]
            if len(k) >= 10:
                cells.append({"lo": lo, "hi": hi, "label": lab, "n": int(len(k)), "h3": round(float((k.h3 > 0).mean()), 3),
                              "h6": round(float((k.h6 > 0).mean()), 3), "fade": round(float(k.fade.mean()), 3),
                              "baru_h6": round(float((kb.h6 > 0).mean()), 3) if len(kb) >= 10 else None})
        out[str(mins)] = cells
    data["btc"] = out
    data["btc_periode"] = f"{d.time.min():%Y}–{d.time.max():%Y}"
    data["btc_min_pct"] = MIN_PCT
    CLOUD.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    d = build()
    txt = report(d)
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    if sys.argv[1:] == ["ekspor"]:
        export(d)
        print(f"ditulis {CLOUD}")


if __name__ == "__main__":
    main()
