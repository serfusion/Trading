"""(1) Kalender berita NFP/CPI/FOMC sebagai filter sinyal 💰 (python -m research.eksternal_berita).

Kalender: ForexFactory historis (research/news_data.py, 2010 - Jan 2026, dengan actual/forecast) + tanggal rilis
FRED (api.stlouisfed.org release/dates: Employment Situation id 50, CPI id 10) untuk Feb-Sep 2026 pukul 08:30 ET,
dan FOMC 2026 (jadwal Fed; tiap tanggal dicek memicu lonjakan range emas 14:00 ET di data M5).
Jadwal berita diketahui jauh hari -> filter "sebelum berita" tidak memakai data masa depan. Arah kejutan
(actual vs forecast) baru dipakai SETELAH waktu rilis.

Varian (ditetapkan sebelum melihat hasil), untuk tier-1 (NFP, CPI, FOMC) dan semua berita utama
(+PPI, Retail, PCE, GDP):
- sebelum Xj : lewati sinyal bila ada rilis dalam X jam SETELAH waktu keputusan (entry tepat sebelum berita)
- sesudah Xj : lewati bila ada rilis dalam X jam SEBELUM waktu keputusan (sinyal lahir dari lonjakan berita)
- hari berita: lewati bila tanggal New York sama dengan hari rilis
- kejutan lawan: lewati bila rilis terakhir <= 24 jam sebelumnya punya arah kejutan emas berlawanan dengan sinyal
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import asset, bar_filter, cache_path, fmt_judge, judge, per_year, realistic_summary
from .news_data import load_calendar
from .run_scan import DATA

TIER1 = ["NFP", "CPI", "FOMC"]
MAIN = ["NFP", "CPI", "PPI", "FOMC", "RETAIL", "PCE", "GDP"]
FF_END = pd.Timestamp("2026-02-01", tz="UTC")
FOMC_2026 = ["2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]   # setelah FF_END
FRED_RELEASE = {"NFP": 50, "CPI": 10}


def _fred_dates(release_id: int) -> list[str]:
    path = cache_path(f"fred_release_{release_id}.json")
    if not path.exists():
        q = (f"https://api.stlouisfed.org/fred/release/dates?release_id={release_id}&api_key="
             f"{os.environ['FRED_API_KEY']}&file_type=json&realtime_start=2010-01-01&realtime_end=9999-12-31"
             f"&include_release_dates_with_no_data=true&limit=10000&sort_order=asc")
        with urllib.request.urlopen(q, timeout=30) as r:
            path.write_bytes(r.read())
    return [x["date"] for x in json.loads(path.read_text())["release_dates"]]


def _ny(date: str, hm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{date} {hm}").tz_localize("America/New_York").tz_convert("UTC")


def calendar() -> pd.DataFrame:
    """Satu baris per (waktu rilis, grup): time, group, gold_bias (+1 kejutan bagus utk emas, NaN bila tak ada)."""
    cal = load_calendar(DATA)
    cal = cal[cal.group.isin(MAIN)]
    cal = cal.groupby(["time", "group"]).gold_bias.apply(
        lambda v: np.sign(v.dropna().sum()) if v.notna().any() else np.nan).reset_index()
    extra = []
    for g, rid in FRED_RELEASE.items():
        for d in _fred_dates(rid):
            t = _ny(d, "08:30")
            if FF_END <= t <= pd.Timestamp.now(tz="UTC"):
                extra.append((t, g, np.nan))
    extra += [(_ny(d, "14:00"), "FOMC", np.nan) for d in FOMC_2026]
    cal = pd.concat([cal, pd.DataFrame(extra, columns=["time", "group", "gold_bias"])])
    return cal.sort_values("time").reset_index(drop=True)


def check_fred_vs_ff(cal: pd.DataFrame) -> str:
    """Tanggal NFP/CPI di FRED vs ForexFactory (periode tumpang tindih 2012-2025)."""
    lines = []
    for g, rid in FRED_RELEASE.items():
        fred = {d for d in _fred_dates(rid) if "2012-01-01" <= d < "2026-01-01"}
        ny = cal[(cal.group == g) & (cal.time < FF_END)].time.dt.tz_convert("America/New_York")
        ff = {t.strftime("%Y-%m-%d") for t in ny if "2012-01-01" <= t.strftime("%Y-%m-%d") < "2026-01-01"}
        lines.append(f"{g}: FRED {len(fred)} tanggal, FF {len(ff)}, sama {len(fred & ff)}, "
                     f"hanya FRED {len(fred - ff)}, hanya FF {len(ff - fred)}")
    return "; ".join(lines)


def _near(t: np.ndarray, ev: np.ndarray, lo_h: float, hi_h: float) -> np.ndarray:
    """True bila ada event di (t + lo_h jam, t + hi_h jam]."""
    lo = np.searchsorted(ev, t + int(lo_h * 3600e9), side="right")
    hi = np.searchsorted(ev, t + int(hi_h * 3600e9), side="right")
    return hi > lo


def variants(sig: pd.DataFrame, cal: pd.DataFrame) -> dict[str, np.ndarray]:
    """Nama -> keep (True = sinyal tetap dikirim)."""
    t = sig.t.to_numpy("datetime64[ns]").astype(np.int64)
    ny_day = sig.t.dt.tz_convert("America/New_York").dt.date.to_numpy()
    out = {}
    for tag, groups in (("tier1", TIER1), ("utama", MAIN)):
        c = cal[cal.group.isin(groups)]
        ev = np.unique(c.time.to_numpy("datetime64[ns]").astype(np.int64))
        for h in (2, 6, 24):
            out[f"{tag} sebelum {h}j"] = ~_near(t, ev, 0, h)
        for h in (1, 4):
            out[f"{tag} sesudah {h}j"] = ~_near(t, ev, -h, 0)
        days = set(c.time.dt.tz_convert("America/New_York").dt.date)
        out[f"{tag} hari berita"] = ~np.isin(ny_day, list(days))
        # kejutan lawan: rilis terakhir (<= 24 jam sebelum t) punya bias emas berlawanan arah sinyal
        cb = c.dropna(subset=["gold_bias"])
        cb = cb[cb.gold_bias != 0]
        if len(cb):
            et = cb.time.to_numpy("datetime64[ns]").astype(np.int64)
            k = np.searchsorted(et, t, side="right") - 1
            ok = (k >= 0) & (t - et[np.maximum(k, 0)] <= 24 * 3600e9)
            bias = np.where(ok, cb.gold_bias.to_numpy()[np.maximum(k, 0)], 0)
            out[f"{tag} kejutan lawan 24j"] = ~(bias == -sig.dir.to_numpy())
    return out


def main() -> None:
    cal = calendar()
    print(f"Kalender: {len(cal)} rilis (grup), {cal.time.min():%Y-%m-%d} .. {cal.time.max():%Y-%m-%d}; "
          f"tier-1 {cal.group.isin(TIER1).sum()}")
    print("Cek silang tanggal:", check_fred_vs_ff(cal))
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            sig = sig[sig.t >= cal.time.min() + pd.Timedelta(days=30)].reset_index(drop=True)
            print(f"\n=== {name} — {label}: {len(sig)} sinyal {sig.t.min():%Y-%m} .. {sig.t.max():%Y-%m} "
                  f"(latih < {a.split:%Y}) — lolos/dibuang dalam R rata-rata per sinyal ===")
            vs = variants(sig, cal)
            res = {k: judge(sig, v, a.split) for k, v in vs.items()}
            for k, j in res.items():
                print(fmt_judge(k, j))
            if label == "💰 dikirim":
                best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
                print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")
                for k in (k for k in res if res[k]["konsisten"]):
                    print(f"-> {k} konsisten; uji nyata (filter di allow seperti cloud):")
                    print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g, cal)[k])))


if __name__ == "__main__":
    main()
