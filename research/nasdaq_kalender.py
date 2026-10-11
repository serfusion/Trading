"""📅 Kalender ekonomi Nasdaq (api.nasdaq.com, data Investing.com): Act, konsensus, sebelumnya — termasuk konsensus
INDEKS CPI tanpa pembulatan ("CPI Index, n.s.a.", "Core CPI Index") dan rilis 2026 yang tidak ada di arsip ForexFactory.

python -m research.nasdaq_kalender unduh [CPI|SEMUA]     → data/research/eksternal/nasdaq/<tanggal>.json
python -m research.nasdaq_kalender lihat 2026-10-14

Ditemukan 11 Okt 2026 (permintaan pengguna "cari di manapun datanya"). Catatan: parameter `date` API bergeser +1 hari
(query 2024-02-14 memuat CPI 13 Feb 2024) → fungsi di sini memakai tanggal rilis lalu menambah 1 hari. Kolom `gmt` bukan
jam rilis yang andal (CPI tercatat 08:30/09:30) → jam rilis diambil dari kalender sendiri. Jeda 0,6 dtk antar permintaan.
"""
from __future__ import annotations

import html
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "nasdaq"
URL = "https://api.nasdaq.com/api/calendar/economicevents?date={}"
HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def _get(q: str) -> dict:
    req = urllib.request.Request(URL.format(q), headers=HDR)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def hari(tgl, segar: bool = False) -> list[dict]:
    """Baris kalender untuk tanggal rilis `tgl` (tanggal New York). Cache per tanggal."""
    t = pd.Timestamp(tgl).normalize()
    f = DIR / f"{t:%Y-%m-%d}.json"
    if f.exists() and not segar:
        return json.loads(f.read_text(encoding="utf-8"))
    for i in range(4):
        try:
            d = _get(f"{t + pd.Timedelta(days=1):%Y-%m-%d}")
            break
        except Exception:  # noqa: BLE001 - jaringan / batas laju
            time.sleep(2 ** (i + 1))
    else:
        return []
    rows = (d.get("data") or {}).get("rows") or []
    out = [{k: html.unescape(str(r.get(k) or "")).replace("\xa0", " ").strip() for k in
            ("gmt", "country", "eventName", "actual", "consensus", "previous")} for r in rows]
    DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    time.sleep(0.6)
    return out


def angka(s: str) -> float:
    s = (s or "").replace(",", "").replace("%", "").strip()
    mult = 1.0
    if s[-1:] in "KMB" and s:
        mult, s = {"K": 1e3, "M": 1e6, "B": 1e9}[s[-1]], s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return float("nan")


_FRED: dict = {}


def _ref(seri: str, tgl) -> tuple[float, float]:
    """(m/m, y/y) resmi FRED untuk bulan "sebelumnya" pada rilis tgl (= 2 bulan sebelum bulan rilis)."""
    if seri not in _FRED:
        from .eksternal_makro import fred
        _FRED[seri] = fred(seri).value
    v = _FRED[seri]
    b = (pd.Timestamp(tgl) - pd.DateOffset(months=2)).to_period("M").to_timestamp()
    try:
        return (float((v[b] / v[b - pd.DateOffset(months=1)] - 1) * 100),
                float((v[b] / v[b - pd.DateOffset(months=12)] - 1) * 100))
    except KeyError:
        return float("nan"), float("nan")


def cpi(tgl) -> dict:
    """Konsensus & Act CPI AS pada tanggal rilis: m/m, y/y, core m/m, core y/y, indeks NSA, indeks core."""
    rows = [r for r in hari(tgl) if r["country"] == "United States"]
    o: dict = {}
    for nama, kunci, seri in (("CPI", "mm", "CPIAUCSL"), ("Core CPI", "core", "CPILFESL")):
        g = [r for r in rows if r["eventName"] == nama]
        # dua baris m/m & y/y; urutan API kadang terbalik → pilih urutan yang "sebelumnya"-nya paling cocok dengan FRED
        if len(g) >= 2:
            g = g[:2]
            mm, yy = _ref(seri, tgl)
            if mm == mm:
                def e(a: dict, b: dict, mm: float = mm, yy: float = yy) -> float:
                    return abs(angka(a["previous"]) - mm) + abs(angka(b["previous"]) - yy)
                if e(g[1], g[0]) < e(g[0], g[1]):
                    g = [g[1], g[0]]
            o[f"{kunci}_a"], o[f"{kunci}_f"], o[f"{kunci}_p"] = (angka(g[0][k]) for k in ("actual", "consensus", "previous"))
            yk = "yy" if kunci == "mm" else "core_yy"
            o[f"{yk}_a"], o[f"{yk}_f"], o[f"{yk}_p"] = (angka(g[1][k]) for k in ("actual", "consensus", "previous"))
    for nama, kunci in (("CPI Index, n.s.a.", "nsa"), ("Core CPI Index", "cidx"), ("CPI Index, s.a", "sa")):
        g = [r for r in rows if r["eventName"] == nama]
        if g:
            o[f"{kunci}_a"], o[f"{kunci}_f"], o[f"{kunci}_p"] = (angka(g[0][k]) for k in ("actual", "consensus", "previous"))
    return o


def tanggal_cpi() -> list[pd.Timestamp]:
    g = pd.read_parquet(ROOT / "data" / "research" / "eksternal" / "pra_menit.parquet")
    t = pd.to_datetime(g[g.grup == "CPI"].t0).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    return sorted(set(t))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "unduh"
    if cmd == "unduh":
        jenis = sys.argv[2] if len(sys.argv) > 2 else "CPI"
        if jenis == "CPI":
            tg = tanggal_cpi()
        else:
            g = pd.read_parquet(ROOT / "data" / "research" / "eksternal" / "pra_menit.parquet")
            t = pd.to_datetime(g.t0).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
            tg = sorted(set(t))
        ada = 0
        for i, t in enumerate(tg):
            rows = hari(t)
            ada += bool(rows)
            if i % 20 == 0:
                print(f"{i}/{len(tg)} {t:%Y-%m-%d} baris {len(rows)}", flush=True)
        print(f"selesai: {ada}/{len(tg)} tanggal berisi")
    elif cmd == "lihat":
        print(json.dumps(cpi(sys.argv[2]), indent=1))


if __name__ == "__main__":
    main()
