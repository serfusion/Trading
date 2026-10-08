"""Harga ACUAN (harga wajar) dalam USD. Spesifikasi teks di konfigurasi:

  tetap:1                 stablecoin (USDG/USDC) = $1
  binance:ETHUSDT         harga terakhir Binance (data-api.binance.vision, mirror publik data pasar)
  saham:CRCL              harga bursa AS lewat Twelve Data (env TWELVEDATA_API_KEY; paket gratis 8 permintaan/menit
                          -> cache 60 dtk). Di luar jam bursa reguler `buka()` = False (acuan basi, risiko gap).
  gt:<network>:<pool>     harga USD token base di pool GeckoTerminal (mis. pool terbesar sebagai acuan)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_cache: dict[str, tuple[float, float]] = {}
NY = ZoneInfo("America/New_York")
LIBUR_NYSE = {  # 2026 (sisa tahun) — tambah bila perlu
    "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
}


def _get(url: str, timeout: float = 15) -> dict:
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 token-bot", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def buka(spec: str, now: datetime | None = None) -> bool:
    """Apakah acuan 'hidup'. Saham: jam reguler NYSE 09:30-16:00 New York, Senin-Jumat, bukan libur."""
    if not spec.startswith("saham:"):
        return True
    t = (now or datetime.now(timezone.utc)).astimezone(NY)
    if t.weekday() >= 5 or t.strftime("%Y-%m-%d") in LIBUR_NYSE:
        return False
    m = t.hour * 60 + t.minute
    return 9 * 60 + 30 <= m < 16 * 60


def harga(spec: str, ttl: float | None = None) -> float:
    kind, _, arg = spec.partition(":")
    if kind == "tetap":
        return float(arg)
    ttl = ttl if ttl is not None else (60.0 if kind == "saham" else 3.0)
    hit = _cache.get(spec)
    if hit and time.time() - hit[1] < ttl:
        return hit[0]
    if kind == "binance":
        p = float(_get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={arg}")["price"])
    elif kind == "saham":
        key = os.environ.get("TWELVEDATA_API_KEY", "")
        if not key:
            raise RuntimeError("acuan saham butuh env TWELVEDATA_API_KEY")
        d = _get(f"https://api.twelvedata.com/price?symbol={arg}&apikey={key}")
        if "price" not in d:
            raise RuntimeError(f"Twelve Data: {d.get('message', d)}")
        p = float(d["price"])
    elif kind == "gt":
        net, pool = arg.split(":", 1)
        d = _get(f"https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pool}")
        p = float(d["data"]["attributes"]["base_token_price_usd"])
    else:
        raise ValueError(f"acuan tidak dikenal: {spec}")
    _cache[spec] = (p, time.time())
    return p
