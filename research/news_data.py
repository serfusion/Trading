"""Kalender ekonomi historis ForexFactory -> DataFrame UTC.

Sumber:
- spoluan/forex-factory-scraper   2010-2023, jam kalender = UTC+8 (NFP 08:30 ET tercatat 21:30)
- ehsanrs2/forexfactory-scraper   2020-Jan 2026, high impact, sudah UTC
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd

TIER1 = {
    "NFP": ["Non-Farm Employment Change"],
    "CPI": ["CPI m/m", "Core CPI m/m", "CPI y/y"],
    "PPI": ["PPI m/m", "Core PPI m/m"],
    "FOMC": ["Federal Funds Rate", "FOMC Statement"],
    "RETAIL": ["Retail Sales m/m", "Core Retail Sales m/m"],
    "PCE": ["Core PCE Price Index m/m"],
    "GDP": ["Advance GDP q/q"],
    "ISM": ["ISM Manufacturing PMI", "ISM Services PMI"],
    "CLAIMS": ["Unemployment Claims"],
}
# indikator yang bila LEBIH TINGGI dari forecast justru negatif untuk USD
INVERSE = {"Unemployment Rate", "Unemployment Claims"}


def _num(value) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).strip().replace(",", "")
    m = re.match(r"^([<>]?)(-?\d+(?:\.\d+)?)([KMBT%]?)", s)
    if not m:
        return np.nan
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(m.group(3), 1.0)
    return float(m.group(2)) * mult


def _group(event: str) -> str | None:
    for g, names in TIER1.items():
        if event in names:
            return g
    return None


def load_calendar(root: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(root / "spoluan_forex-factory-scraper/datasets/*.csv"))):
        d = pd.read_csv(f)
        d = d[(d["Currency"] == "USD") & (d["Impact"] == "High")]
        t = pd.to_datetime(d["Combined DateTime"], errors="coerce") - pd.Timedelta(hours=8)
        frames.append(pd.DataFrame({"time": t.dt.tz_localize("UTC"), "event": d["Event"],
                                    "actual": d["Actual"], "forecast": d["Forecast"], "previous": d["Previous"]}))
    old = pd.concat(frames)
    old = old[old["time"] < pd.Timestamp("2020-01-01", tz="UTC")]
    e = pd.read_csv(root / "ehsanrs2_forexfactory-scraper/high_impact_events_calendar.csv")
    e = e[e["Currency"] == "USD"]
    new = pd.DataFrame({"time": pd.to_datetime(e["DateTime"], utc=True), "event": e["Event"],
                        "actual": e["Actual"], "forecast": e["Forecast"], "previous": e["Previous"]})
    cal = pd.concat([old, new]).dropna(subset=["time"]).sort_values("time")
    cal = cal.drop_duplicates(["time", "event"])
    cal["group"] = cal["event"].map(_group)
    a = cal["actual"].map(_num)
    f = cal["forecast"].map(_num)
    usd = np.sign(a - f) * np.where(cal["event"].isin(INVERSE), -1, 1)
    cal["usd_surprise"] = usd            # +1 = data lebih kuat untuk USD dari perkiraan
    cal["gold_bias"] = -usd              # emas umumnya berlawanan dengan USD
    return cal.reset_index(drop=True)
