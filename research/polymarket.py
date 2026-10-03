"""Polymarket (pasar prediksi) untuk berita AS: unduh riwayat & uji akurasi (host dibuka pengguna 30 Sep 2026).

python -m research.polymarket unduh   # event tertutup + harga per jam -> data/research/eksternal/polymarket/<slug>.json
python -m research.polymarket uji     # akurasi tebakan kejutan vs konsensus FF & vs Kalshi -> docs/eksternal/hasil_polymarket.txt

Pertanyaan pengguna: "polling Polymarket bisa diterapkan oleh sistem kita? Setiap ada polling untuk news?"
Polymarket: satu event per rilis berisi pasar "keranjang" (mis. NFP "50k to 100k", CPI "0.3%", pengangguran "4.1%",
Fed "No change"/"25 bps increase"); harga YES = peluang. gamma-api (daftar & hasil), clob (riwayat harga per jam).
Aturan uji = research/kalshi_uji.py (ditetapkan sebelum melihat hasil): peluang pada 24/6/1 jam sebelum rilis,
P(di atas / sama / di bawah konsensus ForexFactory), tebakan bila selisih >= 10 poin.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from .eksternal import cache_path

G = "https://gamma-api.polymarket.com"
C = "https://clob.polymarket.com"
QUERIES = ["inflation us monthly", "core cpi mom", "jobs added", "unemployment rate", "fed decision"]
# judul event -> (judul ForexFactory, jenis)
KIND = [(re.compile(r"^Core CPI .*MoM", re.I), "Core CPI m/m"),
        (re.compile(r"Inflation US - Monthly", re.I), "CPI m/m"),
        (re.compile(r"^How many jobs added in", re.I), "Non-Farm Employment Change"),
        (re.compile(r"^(?:\w+ )?(?:\d{4} )?Unemployment Rate$|^\w+ Unemployment Rate(?: \d{4})?$", re.I), "Unemployment Rate"),
        (re.compile(r"^Fed (?:decision|interest rates)", re.I), "Federal Funds Rate")]


def _get(url: str):
    for k in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riset-xau"}), timeout=30) as r:
                time.sleep(0.3)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** k)
                continue
            if e.code in (400, 404):
                return None
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** k)
    return None


def kind(title: str) -> str | None:
    if any(w in title for w in ("Japan", "Mexico", "UK", "U.K.", "Canada", "Argentina", "China", "Brazil", "Euro",
                                "decisions", "Dissent", "dissent", "combo", "Combo")):
        return None
    return next((k for rx, k in KIND if rx.search(title.strip())), None)


def discover() -> dict[str, dict]:
    found = {}
    for q in QUERIES:
        for page in range(1, 15):
            d = _get(f"{G}/public-search?" + urllib.parse.urlencode(
                {"q": q, "limit_per_type": 50, "page": page, "events_status": "closed"})) or {}
            evs = d.get("events") or []
            for e in evs:
                k = kind(e.get("title") or "")
                if k:
                    found[e["slug"]] = {"slug": e["slug"], "judul": e["title"], "jenis": k}
            if len(evs) < 50:
                break
    return found


def download() -> None:
    d = cache_path("polymarket")
    d.mkdir(parents=True, exist_ok=True)
    evs = discover()
    print(f"{len(evs)} event ditemukan", flush=True)
    for slug, meta in sorted(evs.items()):
        f = d / f"{slug}.json"
        if f.exists() and any(m["harga"] for m in json.loads(f.read_text(encoding="utf-8"))["pasar"]):
            continue
        e = (_get(f"{G}/events?slug={urllib.parse.quote(slug)}") or [None])[0]
        if not e or not e.get("closed"):
            continue
        rows = []
        for m in e.get("markets") or []:
            toks = json.loads(m.get("clobTokenIds") or "[]")
            if not toks:
                continue
            h = (_get(f"{C}/prices-history?market={toks[0]}&interval=max&fidelity=60") or {}).get("history") or []
            if not h and e.get("endDate"):                       # pasar lama: interval=max kosong -> rentang <= 7 hari
                end = int(pd.Timestamp(e["endDate"]).timestamp()) + 86400
                h = (_get(f"{C}/prices-history?market={toks[0]}&startTs={end - 6 * 86400}&endTs={end}&fidelity=60")
                     or {}).get("history") or []
            rows.append({"keranjang": m.get("groupItemTitle") or m.get("question"), "pertanyaan": m.get("question"),
                         "hasil": m.get("outcomePrices"), "volume": m.get("volume"),
                         "harga": [[x["t"], x["p"]] for x in h]})
        f.write_text(json.dumps({**meta, "akhir": e.get("endDate"), "volume": e.get("volume"), "pasar": rows},
                                ensure_ascii=False), encoding="utf-8")
        print(f"  {slug}: {len(rows)} pasar, volume {float(e.get('volume') or 0):,.0f}", flush=True)


# ------------------------------------------------------------------ keranjang -> rentang angka
_NUM = r"(-?\d+(?:\.\d+)?)\s*(k|%)?"


def bucket(label: str, jenis: str) -> tuple[float, float] | None:
    """Rentang [bawah, atas] angka (NFP dalam ribu, % untuk CPI/pengangguran). Nilai diskret: bawah = atas."""
    s = label.replace("−", "-").replace("–", "-").replace(",", "").strip()
    nums = [float(x) for x, _ in re.findall(_NUM, s)]
    if not nums:
        return None
    lo_inf, hi_inf = float("-inf"), float("inf")
    if jenis == "Non-Farm Employment Change":
        if re.search(r"^<|less|below|lose more", s, re.I):
            return lo_inf, nums[0]
        if re.search(r"\+$|or more|at least|more than", s, re.I) and len(nums) == 1:
            return nums[0], hi_inf
        if len(nums) >= 2:
            return nums[0], nums[1]
        return None
    v = nums[0]
    if re.search(r"^[≤<]|or less", s):
        return lo_inf, v
    if re.search(r"^[≥>]|\+$|or more", s):
        return v, hi_inf
    return v, v


def probs(markets: list[dict], ts: float) -> list[tuple[tuple[float, float], float]]:
    """[(rentang, peluang dinormalkan)] pada waktu ts (harga per jam terakhir <= ts)."""
    out = []
    for m in markets:
        h = [p for t, p in m.get("harga") or [] if t <= ts]
        b = m.get("rentang")
        if h and b:
            out.append((b, float(h[-1])))
    tot = sum(p for _, p in out)
    return [(b, p / tot) for b, p in out] if tot > 0 else []


def split(pr: list[tuple[tuple[float, float], float]], cons: float, continuous: bool) -> dict | None:
    """P(di atas / sama / di bawah) konsensus. Diskret: per nilai; kontinu (NFP): bagian keranjang dibagi linear."""
    if not pr:
        return None
    up = down = same = 0.0
    for (lo, hi), p in pr:
        if continuous:
            if hi <= cons:
                down += p
            elif lo >= cons:
                up += p
            elif lo == float("-inf") or hi == float("inf"):
                return None
            else:
                f = (cons - lo) / (hi - lo)
                down += p * f
                up += p * (1 - f)
        else:
            if hi < cons - 1e-9:
                down += p
            elif lo > cons + 1e-9:
                up += p
            elif lo == hi:
                same += p
            else:
                return None                                   # keranjang terbuka memuat konsensus
    return {"atas": up, "sama": same, "bawah": down}


def load() -> list[dict]:
    import glob
    from pathlib import Path
    out = []
    for f in sorted(glob.glob(str(cache_path("polymarket") / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        for m in d["pasar"]:
            m["rentang"] = bucket(m["keranjang"] or "", d["jenis"])
        out.append(d)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["unduh"]:
        download()
    elif sys.argv[1:2] == ["uji"]:
        from .polymarket_uji import main
        main()
