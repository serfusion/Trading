"""🧱 Data dasar CPI & PPI per KOMPONEN, versi yang TERSEDIA pada hari itu (ALFRED, semua vintage) — 13 Okt 2026.

python -m research.cpi_dasar_data unduh      → data/research/eksternal/cpi_dasar/alfred_<seri>.json

Dipakai research/cpi_dasar.py. `nilai(seri, bulan, hari)` = nilai observasi `bulan` seperti yang terlihat pada `hari`
(realtime_start ≤ hari ≤ realtime_end) → tanpa revisi masa depan. Rilis CPI/PPI hari R: angka bulan acuan = vintage R
(rilis pertama); petunjuk = vintage R−1 (sebelum rilis).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "cpi_dasar"

SERI_CPI = {
    "CPIAUCSL": "CPI total SA", "CPILFESL": "CPI inti SA", "CPIAUCNS": "CPI total NSA",
    "CUSR0000SETB01": "bensin SA", "CUUR0000SETB01": "bensin NSA", "CPIENGSL": "energi", "CPIUFDSL": "makanan",
    "CUSR0000SAF11": "makanan di rumah", "CUSR0000SEFV": "makanan di luar", "CUSR0000SEHF01": "listrik",
    "CUSR0000SEHF02": "gas pipa", "CUSR0000SAH1": "shelter", "CUSR0000SEHC": "OER", "CUSR0000SEHA": "sewa",
    "CUSR0000SETA02": "mobil bekas", "CUSR0000SETA01": "mobil baru", "CUSR0000SETG01": "tiket pesawat",
    "CUSR0000SAM2": "jasa medis", "CPIAPPSL": "pakaian", "CUSR0000SACL1E": "barang inti", "CUSR0000SASLE": "jasa inti",
    "CUSR0000SAS4": "jasa transportasi", "CUSR0000SETD": "servis kendaraan",
}
SERI_PPI = {
    "PPIFIS": "PPI total SA", "PPIFES": "PPI inti (ex makanan & energi) SA", "WPSFD49116": "PPI ex makanan, energi, dagang SA",
    "PPIDES": "PPI energi SA", "PPIDFS": "PPI makanan SA", "WPSFD413": "PPI barang inti SA", "PPIDSS": "PPI jasa SA",
    "PPITSS": "PPI jasa dagang (margin) SA", "PPIAWS": "PPI transportasi & gudang SA", "PPITWS": "PPI jasa lain SA",
    "WPU4021": "PPI manajemen portofolio NSA",
}
HARIAN = {"GASREGW": "bensin eceran mingguan EIA", "DGASUSGULF": "bensin grosir Gulf", "DDFUELUSGULF": "solar Gulf",
          "DJFUELUSGULF": "avtur Gulf", "DCOILWTICO": "WTI", "DHHNGSP": "gas alam Henry Hub", "SP500": "S&P 500"}


def _get(url: str) -> dict:
    for i in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:                      # noqa: BLE001 — 429/5xx FRED: tunggu lalu ulang
            if i == 5:
                raise
            time.sleep(2 * (i + 1))
            print("  ulang", e, file=sys.stderr)
    return {}


def unduh(seri: list[str] | None = None) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ["FRED_API_KEY"]
    for s in seri or [*SERI_CPI, *SERI_PPI]:
        out = DIR / f"alfred_{s}.json"
        rows, off = [], 0
        while True:
            q = urllib.parse.urlencode({"series_id": s, "api_key": key, "file_type": "json", "realtime_start": "2009-01-01",
                                        "realtime_end": "9999-12-31", "observation_start": "2007-01-01",
                                        "limit": 100000, "offset": off})
            d = _get(f"https://api.stlouisfed.org/fred/series/observations?{q}")
            obs = d.get("observations", [])
            rows += [{"date": o["date"], "rs": o["realtime_start"], "re": o["realtime_end"], "v": o["value"]} for o in obs]
            if len(obs) < 100000:
                break
            off += 100000
        out.write_text(json.dumps(rows), encoding="utf-8")
        print(s, len(rows), "baris")
        time.sleep(0.6)


@lru_cache(maxsize=None)
def vintage(seri: str) -> pd.DataFrame:
    d = pd.DataFrame(json.loads((DIR / f"alfred_{seri}.json").read_text(encoding="utf-8")))
    d = d[d.v != "."].copy()
    d["date"], d["rs"] = pd.to_datetime(d.date), pd.to_datetime(d.rs)
    d["re"] = pd.to_datetime(d.re.replace("9999-12-31", "2262-01-01"))
    d["v"] = d.v.astype(float)
    return d.sort_values(["date", "rs"]).reset_index(drop=True)


def potret(seri: str, hari: pd.Timestamp) -> pd.Series:
    """Seluruh deret seperti terlihat pada `hari` (tanggal, tanpa jam)."""
    d = vintage(seri)
    h = pd.Timestamp(hari).tz_localize(None).normalize() if pd.Timestamp(hari).tzinfo else pd.Timestamp(hari).normalize()
    m = (d.rs <= h) & (d.re >= h)
    return d[m].set_index("date").v.sort_index()


def mm(s: pd.Series, bulan: pd.Timestamp, k: int = 1) -> float:
    """Perubahan % bulan `bulan` vs k bulan sebelumnya (NaN bila tidak ada)."""
    a, b = bulan, bulan - pd.DateOffset(months=k)
    return float((s[a] / s[b] - 1) * 100) if a in s.index and b in s.index else np.nan


@lru_cache(maxsize=None)
def harian(seri: str) -> pd.Series:
    """Deret harian/mingguan FRED (cache research/eksternal_makro). SP500 = SPY Twelve Data (FRED SP500 hanya 10 tahun)."""
    if seri == "SP500":
        t = json.loads((ROOT / "data" / "research" / "eksternal" / "td_SPY_1day.json").read_text(encoding="utf-8"))
        v = pd.DataFrame(t["values"])
        return pd.Series(v.close.astype(float).to_numpy(), index=pd.to_datetime(v.datetime)).sort_index()
    from .eksternal_makro import fred
    f = fred(seri)
    return f.value


def rata_bulan(seri: str, bulan: pd.Timestamp, sampai: pd.Timestamp | None = None) -> float:
    """Rata-rata harian/mingguan dalam bulan (opsional hanya s/d tanggal `sampai`)."""
    s = harian(seri)
    a, b = bulan, bulan + pd.offsets.MonthEnd(0)
    if sampai is not None:
        b = min(b, pd.Timestamp(sampai).tz_localize(None) if pd.Timestamp(sampai).tzinfo else pd.Timestamp(sampai))
    x = s[(s.index >= a) & (s.index <= b)]
    return float(x.mean()) if len(x) else np.nan


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "unduh":
        unduh(sys.argv[2:] or None)
