"""Data pasar Binance PUBLIK (tanpa kunci): daftar simbol, harga, kline. Dipakai untuk SINYAL (eksekusi bisa di bursa lain).

Sumber: data-api.binance.vision (mirror data pasar resmi Binance, terbuka dari AS/Indonesia) lalu api.binance.com.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASES = ("https://data-api.binance.vision", "https://api.binance.com")
STABIL = {"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "PAX", "USDS", "UST", "SUSD", "EUR", "GBP", "AUD", "TRY",
          "BRL", "AEUR", "EURI", "USD1", "BKRW", "BIDR", "IDRT", "RUB", "UAH", "NGN", "ZAR", "XUSD", "USDE", "PAXG",
          "WBTC", "WBETH", "BFUSD", "RLUSD", "U", "KGST", "XAUT", "FRAX", "BNCB"}


@dataclass
class Bar:
    t: float      # detik epoch waktu buka
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0    # volume base
    q: float = 0.0    # volume quote (USDT)


class GagalData(RuntimeError):
    pass


class Binance:
    def __init__(self, bases: tuple[str, ...] = BASES, timeout: float = 15):
        self.bases, self.timeout = bases, timeout

    def _get(self, path: str, **params):
        q = urllib.parse.urlencode(params)
        err = None
        for base in self.bases:
            for k in range(3):
                try:
                    req = urllib.request.Request(f"{base}{path}?{q}", headers={"user-agent": "sniper-bot"})
                    with urllib.request.urlopen(req, timeout=self.timeout) as r:
                        return json.loads(r.read())
                except urllib.error.HTTPError as e:
                    err = f"{base} HTTP {e.code}"
                    if e.code in (418, 429):
                        time.sleep(5 * (k + 1))
                        continue
                    break          # 451/403/400 -> sumber berikutnya
                except Exception as e:  # noqa: BLE001
                    err = f"{base} {str(e)[:80]}"
                    time.sleep(1 + k)
        raise GagalData(f"{path}: {err}")

    # ------------------------------------------------------------- simbol & harga
    def simbol_usdt(self) -> dict[str, dict]:
        """{SIMBOL: info} untuk pair spot */USDT yang TRADING atau akan dibuka (PRE_TRADING)."""
        d = self._get("/api/v3/exchangeInfo", permissions="SPOT")
        out = {}
        for s in d.get("symbols", []):
            if s.get("quoteAsset") != "USDT" or s.get("status") not in ("TRADING", "PRE_TRADING"):
                continue
            base = s["baseAsset"]
            if base in STABIL or (len(base) > 4 and re.search(r"(UP|DOWN|BULL|BEAR)$", base)):
                continue
            out[s["symbol"]] = {"base": base, "status": s["status"]}
        return out

    def harga_semua(self) -> dict[str, float]:
        return {x["symbol"]: float(x["price"]) for x in self._get("/api/v3/ticker/price")}

    def ticker24(self) -> dict[str, dict]:
        return {x["symbol"]: {"q": float(x["quoteVolume"]), "c": float(x["lastPrice"]), "low": float(x["lowPrice"])}
                for x in self._get("/api/v3/ticker/24hr")}

    def kline(self, symbol: str, interval: str, start_ms: int | None = None, limit: int = 1000,
              end_ms: int | None = None) -> list[Bar]:
        p = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_ms is not None:
            p["startTime"] = int(start_ms)
        if end_ms is not None:
            p["endTime"] = int(end_ms)
        rows = self._get("/api/v3/klines", **p)
        return [Bar(r[0] / 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[7]))
                for r in rows]

    def waktu_listing(self, symbol: str) -> float | None:
        """Detik epoch candle 1 menit PERTAMA (= saat listing); None bila belum ada perdagangan."""
        b = self.kline(symbol, "1m", start_ms=0, limit=1)
        return b[0].t if b else None
