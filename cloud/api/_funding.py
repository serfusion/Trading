"""Filter sinyal BTC 💰 dari riset data eksternal (docs/RISET_DATA_EKSTERNAL.md §6, research/eksternal_btc.py).

(a) Funding "ramai": BUY dilewati bila rata-rata 3 funding terakhir (24 jam) berada di persentil >= 90% dari 1.095
    funding sebelumnya (1 tahun), SELL dilewati bila <= 10%. api.binance.com diblokir dari server AS (HTTP 451) dan
    data.binance.vision hanya punya file funding BULANAN, jadi funding direkonstruksi dari file HARIAN
    premiumIndexKlines 1 jam: funding 8 jam ≈ rata-rata premium + clamp(0,01% - premium, ±0,05%) — sama dengan
    `research.eksternal_btc.funding_proxy` (diuji dengan data terlambat 36 jam: tetap konsisten).
(b) Musiman: sinyal BTC 💰 di bulan September (waktu New York) dilewati (11 dari 11 tahun rugi 2016-2026).

Cache funding disimpan di Supabase (baris 'funding'), diperbarui paling sering sekali per jam. Hanya library standar.
"""
from __future__ import annotations

import csv
import io
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

BASE = "https://data.binance.vision/data/futures/um"
KEEP = 1200            # funding 8 jam yang disimpan (> 1.095 = 1 tahun)
WINDOW, MIN_N = 1095, 365
HIGH, LOW = 0.9, 0.1
MAX_FILES = 16         # unduhan per tick (batas waktu fungsi Vercel)


def _zip_rows(url: str, timeout: int = 10) -> list[list[str]] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8")
    return [row for row in csv.reader(io.StringIO(text)) if row and row[0].strip().isdigit()]   # buang header


def premium_hours(rows: list[list[str]]) -> dict[int, float]:
    """{open_time (detik UTC): premium close}. File lama memakai mikrodetik? -> dinormalkan ke detik."""
    out = {}
    for r in rows:
        t = int(r[0])
        t = t // 1000 if t > 10**11 else t
        t = t // 1000 if t > 10**11 else t
        out[t] = float(r[4])
    return out


def funding_8h(hours: dict[int, float]) -> dict[int, float]:
    """Proxy funding per settlement (00/08/16 UTC): premium jam [T-8, T) dirata-rata, + clamp(0,01% - p, ±0,05%)."""
    groups: dict[int, list[float]] = {}
    for t, p in hours.items():
        settle = (t // 28800 + 1) * 28800
        groups.setdefault(settle, []).append(p)
    out = {}
    for t, ps in groups.items():
        m = sum(ps) / len(ps)
        out[t] = m + max(-0.0005, min(0.0005, 0.0001 - m))
    return out


def percentile_last(values: list[float]) -> float | None:
    """Persentil rata-rata 3 funding terakhir di antara rata-rata 3 funding selama 1.095 settlement terakhir."""
    if len(values) < 3:
        return None
    avg3 = [sum(values[i - 2:i + 1]) / 3 for i in range(2, len(values))][-WINDOW:]
    if len(avg3) < MIN_N:
        return None
    last = avg3[-1]
    return sum(1 for v in avg3 if v <= last) / len(avg3)


def _daily_url(d: datetime) -> str:
    return f"{BASE}/daily/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-{d:%Y-%m-%d}.zip"


def _monthly_url(d: datetime) -> str:
    return f"{BASE}/monthly/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-{d:%Y-%m}.zip"


def _month_start(d: datetime) -> datetime:
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_month(d: datetime) -> datetime:
    return _month_start(d + timedelta(days=32))


def refresh(cache: dict, now: datetime, fetch=_zip_rows) -> dict:
    """Perbarui cache {'f': [[settlement_ts, funding], ...], 'm': bulan terakhir dari file bulanan,
    'day': hari terakhir dari file harian, 'try': iso}.
    Isi awal: file bulanan sampai 2 bulan lalu, lalu file harian mulai awal bulan lalu sampai kemarin (UTC).
    Selama masih mengejar: boleh tiap tick (maks MAX_FILES unduhan); setelah mutakhir: paling sering 1x/jam."""
    cache = dict(cache or {})
    today = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    prev_month = _month_start(today - timedelta(days=today.day))            # awal bulan lalu
    day = datetime.fromisoformat(cache["day"]).replace(tzinfo=timezone.utc) if cache.get("day") else None
    if day is not None and day >= yesterday:
        return cache
    if day is not None and cache.get("try") and now - datetime.fromisoformat(cache["try"]) < timedelta(hours=1) \
            and day >= yesterday - timedelta(days=1):
        return cache                                    # hanya menunggu file kemarin terbit
    cache["try"] = now.astimezone(timezone.utc).isoformat()
    series = {int(t): v for t, v in cache.get("f") or []}
    hours: dict[int, float] = {}
    budget = MAX_FILES
    if day is None:
        m = datetime.fromisoformat(cache["m"]).replace(tzinfo=timezone.utc) if cache.get("m") else \
            _month_start(prev_month - timedelta(days=370))
        while m < prev_month and budget > 0:
            rows = fetch(_monthly_url(m))
            budget -= 1
            if rows:
                hours.update(premium_hours(rows))
            m = _add_month(m)
        cache["m"] = m.strftime("%Y-%m-%d")
        if m >= prev_month:
            day = prev_month - timedelta(days=1)
    if day is not None:
        d = day + timedelta(days=1)
        while d <= yesterday and budget > 0:
            rows = fetch(_daily_url(d))
            budget -= 1
            if rows is None:
                break                                   # belum terbit -> coba lagi nanti
            hours.update(premium_hours(rows))
            day = d
            d += timedelta(days=1)
        cache["day"] = day.strftime("%Y-%m-%d")
    series.update(funding_8h(hours))
    cache["f"] = [[t, v] for t, v in sorted(series.items())][-KEEP:]
    return cache


def skip_reason(direction: str, now: datetime, cache: dict, funding: bool = True, september: bool = True,
                new_york=None) -> str | None:
    """Alasan melewati sinyal BTC 💰, atau None bila boleh dikirim."""
    if september and new_york is not None and new_york(now).month == 9:
        return "September (11/11 tahun rugi untuk sinyal BTC 💰)"
    if funding:
        pct = percentile_last([v for _, v in cache.get("f") or []])
        if pct is not None and direction == "BUY" and pct >= HIGH:
            return f"funding Binance ramai long (persentil {pct:.0%} setahun)"
        if pct is not None and direction == "SELL" and pct <= LOW:
            return f"funding Binance ramai short (persentil {pct:.0%} setahun)"
    return None
