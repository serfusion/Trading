"""📰 Tanda "sinyal setelah berita" untuk sinyal 💰 (permintaan pengguna 2 Okt 2026: "tandai saja jika itu sinyal news").

Aturan sinyal TIDAK berubah. Sinyal yang entry-nya <= 4 jam setelah rilis berita AS besar (NFP, CPI, PPI, FOMC,
Retail Sales, Core PCE, Advance GDP — judul sama dengan research/news_data.TIER1) diberi tanda 📰 dan statistik
riwayatnya (cloud/api/sinyal_berita.json dari `python -m research.sinyal_berita ekspor`):
XAU 186 sinyal +0,45R/sinyal (biasa +0,21R; WR 46%, tidak setiap tahun), BTC 72 sinyal +0,61R (biasa +0,37R).
Bila Act sudah ada (Supabase baris "aktual"), dicek apakah arah sinyal SEARAH kejutan (data lemah USD -> emas naik):
BTC searah 17 sinyal WR 82% (sampel kecil); XAU searah justru lemah (+0,04R) -> ditulis apa adanya.
Hanya library standar Python.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "sinyal_berita.json"
STATS = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
TITLES = {"Non-Farm Employment Change": "NFP", "CPI m/m": "CPI", "Core CPI m/m": "CPI", "CPI y/y": "CPI",
          "PPI m/m": "PPI", "Core PPI m/m": "PPI", "Federal Funds Rate": "FOMC", "FOMC Statement": "FOMC",
          "Retail Sales m/m": "Retail Sales", "Core Retail Sales m/m": "Retail Sales",
          "Core PCE Price Index m/m": "Core PCE", "Advance GDP q/q": "GDP"}
INVERSE = {"Unemployment Rate", "Unemployment Claims"}
WIB = timedelta(hours=7)


def _num(text: str) -> float | None:
    m = re.match(r"^\s*[<>]?(-?\d+(?:[.,]\d+)?)\s*([KMBT%]?)", str(text or "").upper())
    if not m:
        return None
    return float(m.group(1).replace(",", ".")) * {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(m.group(2), 1.0)


def _time(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(row.get("date") or row.get("time"))).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _usd(x: float) -> str:
    return f"{x:+.2f}".replace(".", ",")


def recent(rows: list[dict], now: datetime, hours: float = 4) -> list[dict]:
    """Rilis berita AS besar dalam `hours` jam terakhir (terbaru dulu)."""
    out = []
    for r in rows or []:
        t = _time(r)
        if (r.get("country") in (None, "USD") and r.get("impact") in (None, "High") and r.get("title") in TITLES
                and t is not None
                and now - timedelta(hours=hours) < t <= now):
            out.append({**r, "_t": t})
    return sorted(out, key=lambda r: r["_t"], reverse=True)


def gold_bias(releases: list[dict], acts: dict) -> int | None:
    """Arah emas dari kejutan rilis terakhir (+1 naik / -1 turun), None bila Act belum ada. acts: "judul|waktu" -> Act."""
    if not releases:
        return None
    t0 = releases[0]["_t"]
    total, seen = 0.0, False
    for r in releases:
        if r["_t"] != t0:
            continue
        a = _num(acts.get(f"{r['title']}|{t0.isoformat()}") or r.get("actual"))
        f = _num(r.get("forecast"))
        if a is None or f is None:
            continue
        seen = True
        usd = (1 if a > f else -1 if a < f else 0) * (-1 if r["title"] in INVERSE else 1)
        total += -usd
    if not seen or total == 0:
        return None
    return 1 if total > 0 else -1


def tag(asset: str, direction: str, now: datetime, rows: list[dict], acts: dict | None = None) -> dict | None:
    """Tanda 📰 untuk sinyal baru (None bila bukan sinyal setelah berita)."""
    st = STATS.get(asset)
    rel = recent(rows, now, (st or {}).get("jam", 4))
    if not st or not rel:
        return None
    r0 = rel[0]
    nama = TITLES[r0["title"]]
    menit = int((now - r0["_t"]).total_seconds() // 60)
    lalu = f"{menit // 60} jam {menit % 60} mnt" if menit >= 60 else f"{menit} mnt"
    a, b = st["setelah"], st["dasar"]
    teks = (f"📰 Riwayat sinyal 💰 ≤ {st['jam']} jam setelah berita besar: {a['n']} sinyal, WR {a['wr']:.0f}%, "
            f"{_usd(a['avg'])}R/sinyal (sinyal biasa {_usd(b['avg'])}R) • {st['periode']}")
    if a.get("th", 100) < 60:
        teks += f" • positif hanya {a['th']:.0f}% tahun"
    bias = gold_bias(rel, acts or {})
    searah = None
    if bias is not None:
        searah = bias == (1 if direction == "BUY" else -1)
        s = st["searah"]
        if searah:
            teks += (f"\n✅ Searah kejutan {nama}: riwayat {s['n']} sinyal WR {s['wr']:.0f}%, {_usd(s['avg'])}R/sinyal"
                     + (" (sampel kecil, belum terbukti)" if s["n"] < 30 else ""))
        else:
            teks += f"\n⚠️ Berlawanan dengan arah kejutan {nama}"
    w = r0["_t"] + WIB
    return {"judul": f"📰 SINYAL SETELAH BERITA: {nama} {w:%H:%M} WIB ({lalu} lalu)", "teks": teks,
            "berita": nama, "rilis": r0["_t"].isoformat(), "searah": searah,
            "wr": a["wr"], "avg_r": a["avg"], "n": a["n"]}


def acts_from_store(store) -> dict:
    """Act yang sudah tersimpan (_aktual: baris "aktual", kunci "judul|waktu ISO UTC")."""
    try:
        found = (store.get_state("aktual") or {}).get("found") or {}
    except Exception:  # noqa: BLE001
        return {}
    return {k: v.get("actual") for k, v in found.items() if v.get("actual")}


def news_fn(asset: str, store, fetch_rows):
    """Fungsi (arah, waktu) -> tanda 📰 untuk _core.tick (cfg["news_fn"]). Kalender & Act baru diambil saat ada
    sinyal (sekali per tick), bukan tiap putaran."""
    cache: dict = {}

    def fn(direction: str, now: datetime) -> dict | None:
        if "rows" not in cache:
            cache["rows"] = fetch_rows() or []
            cache["acts"] = acts_from_store(store) if store is not None else {}
        return tag(asset, direction, now, cache["rows"], cache["acts"])
    return fn
