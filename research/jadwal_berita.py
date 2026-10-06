"""📅 Jadwal berita besar USD ke depan → cloud/api/jadwal.json — python -m research.jadwal_berita

Kalender ForexFactory (nfs.faireconomy.media) hanya memuat PEKAN INI, sehingga NFP/CPI/Fed pekan depan dst. tidak pernah
tampil di kartu 🎯 (keluhan pengguna 6 Okt 2026). Tanggal rilis resmi diambil dari FRED (release/dates, butuh
FRED_API_KEY) + jadwal FOMC 2026 (federalreserve.gov). Jam rilis ET → UTC (zona America/New_York, ikut DST).
Jalankan ulang bila jadwal habis (FRED biasanya memuat ±3 bulan ke depan).
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloud" / "api" / "jadwal.json"
ET = ZoneInfo("America/New_York")
# (release_id FRED, judul ForexFactory, jam ET)
RILIS = ((50, "Non-Farm Employment Change", "08:30"), (10, "CPI m/m", "08:30"), (10, "Core CPI m/m", "08:30"),
         (192, "JOLTS Job Openings", "10:00"), (46, "PPI m/m", "08:30"), (9, "Retail Sales m/m", "08:30"),
         (54, "Core PCE Price Index m/m", "08:30"))
FOMC = ("2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09")


def utc(d: str, hm: str) -> str:
    h, m = map(int, hm.split(":"))
    y, mo, dd = map(int, d.split("-"))
    return datetime(y, mo, dd, h, m, tzinfo=ET).astimezone(timezone.utc).isoformat()


def main() -> None:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        raise SystemExit("FRED_API_KEY kosong")
    today = date.today().isoformat()
    out, cache = [], {}
    for rid, title, hm in RILIS:
        if rid not in cache:
            u = (f"https://api.stlouisfed.org/fred/release/dates?release_id={rid}&realtime_start={today}"
                 f"&realtime_end=2099-12-31&include_release_dates_with_no_data=true&file_type=json&api_key={key}")
            with urllib.request.urlopen(u, timeout=30) as r:
                cache[rid] = [x["date"] for x in json.load(r).get("release_dates", [])]
        out += [{"title": title, "time": utc(d, hm)} for d in cache[rid] if d >= today]
    out += [{"title": "Federal Funds Rate", "time": utc(d, "14:00")} for d in FOMC if d >= today]
    out.sort(key=lambda x: x["time"])
    OUT.write_text(json.dumps({"dibuat": today, "sumber": "FRED release/dates + jadwal FOMC", "berita": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "berita s.d.", out[-1]["time"][:10] if out else "-")


if __name__ == "__main__":
    main()
