"""🗳️ Polymarket (pasar prediksi) untuk berita pekan ini -> dipakai perkiraan hari H (_hari_h.py) & kartu 🎯.

Permintaan pengguna 1 Okt 2026: "polling Polymarket bisa diterapkan oleh sistem kita? Setiap ada polling untuk news?"
Per berita (CPI, core CPI, NFP, pengangguran): peluang angka DI ATAS / SAMA / DI BAWAH konsensus ForexFactory dari
pasar "keranjang" Polymarket (mis. NFP "50k to 100k", pengangguran "4.1%"). Keputusan Fed: peluang tiap pilihan
("No change", "25 bps increase", ...). Event aktif dicari lewat gamma-api public-search (tanpa kunci); dibaca paling
sering tiap 15 menit untuk semua pengguna (cache Supabase baris "polymarket"). INFORMASI saja, tanpa order.
Hanya library standar Python. Aturan keranjang sama dengan research/polymarket.py.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

G = "https://gamma-api.polymarket.com"
# judul ForexFactory -> (kata cari, pola judul event Polymarket)
SEARCH = {"CPI m/m": ("inflation us monthly", re.compile(r"Inflation US - Monthly", re.I)),
          "Core CPI m/m": ("core cpi mom", re.compile(r"^Core CPI .*MoM", re.I)),
          "Non-Farm Employment Change": ("jobs added", re.compile(r"^How many jobs added in", re.I)),
          "Unemployment Rate": ("unemployment rate", re.compile(r"^\w+ Unemployment Rate(?: \d{4})?$", re.I)),
          "Federal Funds Rate": ("fed decision", re.compile(r"^Fed decision in \w+\?$", re.I))}
TTL = timedelta(minutes=15)
NEAR = timedelta(days=3)
_NUM = r"(-?\d+(?:\.\d+)?)\s*(k|%)?"


def _num(text) -> float | None:
    m = re.match(r"^\s*([<>]?)(-?\d+(?:[.,]\d+)?)\s*([kKmMbB%]?)", str(text or ""))
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(3).lower(), 1.0)
    return float(m.group(2).replace(",", ".")) * mult


def bucket(label: str, continuous: bool) -> tuple[float, float] | None:
    s = (label or "").replace("−", "-").replace("–", "-").replace(",", "").strip()
    nums = [float(x) for x, _ in re.findall(_NUM, s)]
    if not nums:
        return None
    inf = float("inf")
    if continuous:
        if re.search(r"^<|less|below|lose more", s, re.I):
            return -inf, nums[0]
        if re.search(r"\+$|or more|at least|more than", s, re.I) and len(nums) == 1:
            return nums[0], inf
        return (nums[0], nums[1]) if len(nums) >= 2 else None
    if re.search(r"^[≤<]|or less", s):
        return -inf, nums[0]
    if re.search(r"^[≥>]|\+$|or more", s):
        return nums[0], inf
    return nums[0], nums[0]


def price(m: dict) -> float | None:
    bid, ask = _num(m.get("bestBid")), _num(m.get("bestAsk"))
    if bid is not None and ask is not None and 0 < ask <= 1 and ask >= bid and ask - bid <= 0.2:
        return (bid + ask) / 2
    try:
        return float(json.loads(m.get("outcomePrices") or "[]")[0])
    except (ValueError, IndexError, TypeError):
        return None


def split(markets: list[dict], cons: float, continuous: bool) -> dict | None:
    pr = [(b, p) for m in markets if (b := bucket(m.get("groupItemTitle") or "", continuous)) and
          (p := price(m)) is not None]
    tot = sum(p for _, p in pr)
    if not pr or tot <= 0:
        return None
    up = down = same = 0.0
    for (lo, hi), p in pr:
        p /= tot
        if continuous:
            if hi <= cons:
                down += p
            elif lo >= cons:
                up += p
            elif abs(lo) == float("inf") or abs(hi) == float("inf"):
                return None
            else:
                f = (cons - lo) / (hi - lo)
                down, up = down + p * f, up + p * (1 - f)
        elif hi < cons - 1e-9:
            down += p
        elif lo > cons + 1e-9:
            up += p
        elif lo == hi:
            same += p
        else:
            return None
    return {"atas": up, "sama": same, "bawah": down}


def search(title: str, opener=None) -> list[dict]:
    q, rx = SEARCH[title]
    url = f"{G}/public-search?" + urllib.parse.urlencode({"q": q, "limit_per_type": 10, "events_status": "active"})
    try:
        with (opener or urllib.request.urlopen)(urllib.request.Request(url, headers={"User-Agent": "xau-signal"}),
                                                timeout=6) as r:
            evs = json.load(r).get("events") or []
    except Exception:  # noqa: BLE001 - Polymarket opsional
        return []
    return [e for e in evs if rx.search((e.get("title") or "").strip())]


def snapshot(cards: list[dict], now: datetime, get=search) -> dict:
    out, cache = {}, {}
    for c in cards:
        title = c.get("title")
        if title not in SEARCH:
            continue
        t0 = datetime.fromisoformat(c["time"])
        if not now - timedelta(hours=6) <= t0 <= now + timedelta(days=8):
            continue
        if title not in cache:
            cache[title] = get(title)
        evs = []
        for e in cache[title]:
            try:
                end = datetime.fromisoformat(str(e.get("endDate")).replace("Z", "+00:00"))
            except ValueError:
                continue
            if abs(end - t0) <= NEAR:
                evs.append(e)
        if not evs:
            continue
        e = evs[0]
        vol = float(e.get("volume") or 0)
        ms = e.get("markets") or []
        key = f"{title}|{c['time']}"
        if title == "Federal Funds Rate":
            pil = {m.get("groupItemTitle"): round(p, 3) for m in ms if (p := price(m)) is not None}
            if pil:
                out[key] = {"pilihan": pil, "volume": vol}
            continue
        cons = _num(c.get("forecast"))
        if cons is None:
            continue
        cont = title == "Non-Farm Employment Change"
        s = split(ms, cons / 1000 if cont else cons, cont)
        if s:
            out[key] = {**{k: round(v, 3) for k, v in s.items()}, "volume": vol}
    return out


def cached_snapshot(cards: list[dict], store, now: datetime, get=search) -> tuple[dict, str | None]:
    old = {}
    if store is not None:
        try:
            old = store.get_state("polymarket") or {}
        except Exception:  # noqa: BLE001
            old = {}
    if old.get("t") and now - datetime.fromisoformat(old["t"]) < TTL:
        return old.get("data") or {}, old["t"]
    data = snapshot(cards, now, get)
    if not data and old.get("data"):
        return old["data"], old.get("t")
    if store is not None:
        try:
            store.save_state({"t": now.isoformat(), "data": data}, "polymarket")
        except Exception:  # noqa: BLE001
            pass
    return data, now.isoformat()


def fed_next(now: datetime, get=search) -> dict | None:
    """Keputusan Fed terdekat (tidak harus pekan ini): {"judul", "akhir", "pilihan" {nama: peluang}, "volume"}."""
    best = None
    for e in get("Federal Funds Rate"):
        try:
            end = datetime.fromisoformat(str(e.get("endDate")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if end > now - timedelta(hours=12) and (best is None or end < best[0]):
            best = (end, e)
    if not best:
        return None
    end, e = best
    pil = {m.get("groupItemTitle"): round(p, 3) for m in e.get("markets") or [] if (p := price(m)) is not None}
    pil = dict(sorted(pil.items(), key=lambda kv: -kv[1]))
    return {"judul": e.get("title"), "akhir": end.isoformat(), "pilihan": pil, "volume": float(e.get("volume") or 0)}


def cached_fed(store, now: datetime, get=search) -> dict | None:
    old = {}
    if store is not None:
        try:
            old = store.get_state("polymarket_fed") or {}
        except Exception:  # noqa: BLE001
            old = {}
    if old.get("t") and now - datetime.fromisoformat(old["t"]) < TTL:
        return old.get("data")
    data = fed_next(now, get) or old.get("data")
    hist = (old.get("riwayat") or [])
    if data:
        top = next(iter(data["pilihan"].items()), (None, None))
        hist = (hist + [[now.isoformat(), top[0], top[1]]])[-96:]
    if store is not None:
        try:
            store.save_state({"t": now.isoformat(), "data": data, "riwayat": hist}, "polymarket_fed")
        except Exception:  # noqa: BLE001
            pass
    if data:
        data = {**data, "riwayat": hist}
    return data
