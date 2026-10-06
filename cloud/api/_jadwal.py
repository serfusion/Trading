"""📅 Berita besar USD berikutnya di luar pekan ini (kartu 🎯, aplikasi 4.14) — data cloud/api/jadwal.json
(research/jadwal_berita.py: tanggal rilis FRED + jadwal FOMC). Kalender ForexFactory hanya memuat pekan ini, jadi
NFP/CPI/Fed pekan depan dst. tidak pernah tampil (keluhan pengguna 6 Okt 2026). Per berita: kapan, dalam berapa hari,
dan skenario historis (emas 1 menit bila Act di bawah/di atas perkiraan) dari _persiapan.card. Info saja.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import _persiapan

_PATH = os.path.join(os.path.dirname(__file__), "jadwal.json")
MAX = 8
UTAMA = ("Non-Farm Employment Change", "CPI m/m", "Federal Funds Rate", "JOLTS Job Openings")   # selalu tampil


def _load() -> list:
    try:
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f).get("berita") or []
    except (OSError, ValueError):
        return []


def mendatang(persiapan: dict | None, now: datetime | None = None, jadwal: list | None = None) -> list:
    now = now or datetime.now(timezone.utc)
    sudah = {(b.get("title"), str(b.get("time", ""))[:10]) for b in (persiapan or {}).get("berita") or []}
    seen, out = set(), []
    for j in jadwal if jadwal is not None else _load():
        try:
            t = datetime.fromisoformat(j["time"]).astimezone(timezone.utc)
        except (KeyError, ValueError, TypeError):
            continue
        title = j.get("title") or ""
        if t <= now or title in seen or (title, t.isoformat()[:10]) in sudah:
            continue
        c = _persiapan.card(title, t, "", "", now)
        if not c:
            continue
        seen.add(title)
        hari = (t - now).total_seconds() / 86400
        c["dalam"] = f"{hari:.0f} hari lagi" if hari >= 1.5 else f"{hari * 24:.0f} jam lagi"
        out.append(c)
    # berita utama (NFP, CPI, Fed, JOLTS) selalu ikut; sisanya yang paling dekat, total maks MAX, urut waktu
    utama = [c for c in out if c["title"] in UTAMA]
    lain = [c for c in out if c["title"] not in UTAMA][:max(0, MAX - len(utama))]
    return sorted(utama + lain, key=lambda c: c["time"])


def attach(persiapan: dict, now: datetime | None = None) -> None:
    if isinstance(persiapan, dict):
        persiapan["mendatang"] = mendatang(persiapan, now)
