"""Pasar prediksi Kalshi -> peluang hasil berita AS SEBELUM rilis (host dibuka pengguna 30 Sep 2026).

python -m research.kalshi unduh      # event, pasar, candlestick 1 jam (48 jam terakhir) -> data/research/eksternal/kalshi
python -m research.kalshi uji        # akurasi tebakan kejutan & uji entry t0-1 -> docs/eksternal/hasil_kalshi.txt

Permintaan pengguna: "kumpulkan info untuk prediksi arah news beberapa jam kemudian, berapa persentase akan kemana,
jadi saya bisa bersiap untuk 1 detik sebelum news".

Kalshi (api.elections.kalshi.com, tanpa login) punya pasar biner per rilis: "CPI m/m di atas X%?", "NFP di atas X?",
"pengangguran di atas X%?", "core PCE di atas X%?". Pasar ditutup 5 menit (CPI/PCE) / 1 menit (NFP) sebelum rilis.
Harga YES = peluang menurut pasar. Pasar yang sudah lama selesai ada di endpoint /historical/... (cutoff Agu 2026).

Aturan uji (ditetapkan sebelum melihat hasil):
- Peluang pada jam h sebelum pasar tutup (h = 24, 6, 2, 1 jam, dan saat tutup) = mid (bid+ask)/2 candle 1 jam
  terakhir yang selesai sebelum saat itu; bila bid/ask kosong dipakai harga transaksi terakhir.
- Konsensus (Cons) & Act dari kalender ForexFactory (research/news_data.load_calendar, s.d. Jan 2026).
  P(di atas Cons) = P(Act > Cons) = harga pasar "Above Cons"; P(di bawah Cons) = 1 - P("Above Cons - 1 langkah")
  (langkah 0,1 poin persen; NFP: interpolasi linear antar strike, P(bawah) = 1 - P(atas)). Sisa = P(sama).
- Tebakan kejutan = arah yang peluangnya lebih besar bila selisih >= 10 poin (juga diuji >= 0 dan >= 20).
- Arah emas = kebalikan kejutan untuk USD (pengangguran terbalik), sama dengan riset lain.
- Uji entry t0-1 dengan mesin research/news_pra2.py (tick Exness & Dukascopy, CEPAT/REALISTIS/STRES, 28 cara keluar).
Semua data unduhan disimpan di data/research/eksternal/kalshi (di-commit, permintaan pengguna).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .eksternal import cache_path

API = "https://api.elections.kalshi.com/trade-api/v2"
# seri Kalshi -> (nama event ForexFactory, langkah strike, pengangguran = terbalik untuk emas)
SERIES = {"KXCPI": ("CPI m/m", 0.1), "KXCPICORE": ("Core CPI m/m", 0.1),
          "KXPAYROLLS": ("Non-Farm Employment Change", None), "KXU3": ("Unemployment Rate", 0.1),
          "KXPCECORE": ("Core PCE Price Index m/m", 0.1), "KXFEDDECISION": ("Federal Funds Rate", None)}
HOURS = 48
PAUSE = 0.35


def _get(path: str, **q) -> dict | None:
    url = API + path + ("?" + urllib.parse.urlencode(q) if q else "")
    for k in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riset-xau"}),
                                        timeout=30) as r:
                time.sleep(PAUSE)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(min(2 ** k, 30))
                continue
            if e.code == 404:
                return None
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** k)
    raise RuntimeError(f"gagal {url}")


def events(series: str) -> list[dict]:
    out, cur = [], None
    while True:
        q = {"series_ticker": series, "limit": 200}
        if cur:
            q["cursor"] = cur
        d = _get("/events", **q) or {}
        out += d.get("events", [])
        cur = d.get("cursor")
        if not cur or not d.get("events"):
            return out


def markets(event: str) -> tuple[list[dict], bool]:
    """(pasar, arsip?) satu event; pasar lama ada di /historical/markets."""
    d = _get("/markets", event_ticker=event, limit=100) or {}
    if d.get("markets"):
        return d["markets"], False
    d = _get("/historical/markets", event_ticker=event, limit=100) or {}
    return d.get("markets", []), True


def _num(x) -> float | None:
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def candles(series: str, m: dict, archived: bool) -> list[list]:
    """[[akhir candle (unix), bid, ask, harga terakhir, volume]] 1 jam, HOURS jam terakhir sebelum pasar tutup."""
    close = datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
    q = {"start_ts": int((close - timedelta(hours=HOURS)).timestamp()), "end_ts": int(close.timestamp()) + 3600,
         "period_interval": 60}
    path = (f"/historical/markets/{m['ticker']}/candlesticks" if archived
            else f"/series/{series}/markets/{m['ticker']}/candlesticks")
    d = _get(path, **q) or {}
    out = []
    for c in d.get("candlesticks", []):
        out.append([c["end_period_ts"], _num((c.get("yes_bid") or {}).get("close")),
                    _num((c.get("yes_ask") or {}).get("close")),
                    _num((c.get("price") or {}).get("close")) or _num((c.get("price") or {}).get("previous")),
                    _num(c.get("volume"))])
    return out


def download(series_list: list[str] | None = None) -> None:
    for s in series_list or list(SERIES):
        d = cache_path(f"kalshi/{s}")
        d.mkdir(parents=True, exist_ok=True)
        evs = events(s)
        print(f"{s}: {len(evs)} event", flush=True)
        for e in sorted(evs, key=lambda x: x["event_ticker"]):
            f = d / f"{e['event_ticker']}.json"
            if f.exists():
                continue
            ms, archived = markets(e["event_ticker"])
            if not ms:
                continue
            if not all(m.get("result") in ("yes", "no") for m in ms):
                continue                                     # belum selesai: jangan disimpan (akan diulang nanti)
            rows = []
            for m in ms:
                rows.append({"ticker": m["ticker"], "judul": m.get("yes_sub_title") or m.get("subtitle"),
                             "strike": m.get("floor_strike"), "hasil": m.get("result"),
                             "nilai": m.get("expiration_value"), "tutup": m["close_time"],
                             "volume": m.get("volume_fp", m.get("volume")),
                             "candle": candles(s, m, archived)})
            f.write_text(json.dumps({"event": e["event_ticker"], "judul": e.get("title"), "sub": e.get("sub_title"),
                                     "pasar": rows}, ensure_ascii=False), encoding="utf-8")
            print(f"  {e['event_ticker']}: {len(rows)} pasar", flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["unduh"]:
        download(sys.argv[2:] or None)
    elif sys.argv[1:2] == ["uji"]:
        from .kalshi_uji import main
        main()
