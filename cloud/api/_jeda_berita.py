"""⏸️ Jeda sinyal 💰 XAU baru ≤ 60 jam sebelum NFP / CPI / keputusan Fed. Dipasang 7 Okt 2026 dengan 36 jam (izin
pengguna "terapkan apabila dapat menambah wr dan profit" — sistem Muse/trading-alert), diperpanjang ke 60 jam hari yang
sama (izin "pasang keduanya").

Riset research/muse_uji.py (docs/MUSE.md), replay PENUH kode cloud XAU 2012–2026 (konfigurasi live, R bersih spread asli
Exness, utama + lapisan), tanpa jeda → 36 jam → 60 jam:
  LAMA (< Okt 2021)    +504R → +625R → +674R, WR 59,6 → 60,8 → 61,6%, PF 1,35 → 1,52 → 1,62, DD −264 → −195 → −145R
  BARU (Okt 2021–2026) +567R → +708R → +711R, WR 62,4 → 65,0 → 65,1%, PF 1,56 → 1,86 → 1,96, DD −230 → −180 → −169R
  60 jam: 11 dari 14 tahun membaik (2013, 2015, 2021 memburuk); sinyal sebelum NFP, CPI, Fed masing-masing rugi.
BTC justru memburuk → hanya XAU. Posisi yang sudah terbuka tetap dikelola seperti biasa (SL/TP/TUTUP).
Jadwal: kalender ForexFactory pekan ini (cache Supabase 'kalender') + cloud/api/jadwal.json (FRED + FOMC).
Tanpa jadwal sama sekali → tidak ada jeda (sinyal tetap jalan). Env XAU_NEWS_SKIP=0 mematikan, XAU_NEWS_SKIP_JAM=60.
Hanya library standar Python.
"""
from __future__ import annotations

import bisect
import json
import os
from datetime import datetime, timedelta, timezone

JAM = 60.0
NAMA = {"Non-Farm Employment Change": "NFP", "CPI m/m": "CPI", "Core CPI m/m": "CPI", "Federal Funds Rate": "Fed"}
_PATH = os.path.join(os.path.dirname(__file__), "jadwal.json")
WIB = timedelta(hours=7)
HARI = ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")
BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def _t(x) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(x))
    except (TypeError, ValueError):
        return None
    return t.astimezone(timezone.utc) if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _jadwal() -> list:
    try:
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f).get("berita") or []
    except (OSError, ValueError):
        return []


def waktu(rows: list | None, berita: list | None = None) -> list[tuple[datetime, str]]:
    """Rilis NFP/CPI/Fed terurut (UTC, nama): baris ForexFactory (USD) + jadwal.json, waktu kembar digabung."""
    out = {}
    for r in list(rows or []) + list(berita or []):
        if r.get("title") not in NAMA or r.get("country") not in (None, "USD"):
            continue
        t = _t(r.get("date") or r.get("time"))
        if t is not None:
            out.setdefault(t, NAMA[r["title"]])
    return sorted(out.items())


def berikut(now: datetime, times: list[tuple[datetime, str]], jam: float = JAM) -> tuple[datetime, str] | None:
    """Rilis besar berikutnya bila jaraknya ≤ `jam` jam dari sekarang (sama dengan riset: rilis SETELAH now)."""
    k = bisect.bisect_right([t for t, _ in times], now)
    if k < len(times) and times[k][0] - now <= timedelta(hours=jam):
        return times[k]
    return None


def jam_wib(t: datetime) -> str:
    w = t + WIB
    return f"{HARI[w.weekday()]} {w.day} {BULAN[w.month - 1]} {w:%H.%M} WIB"


def skip_fn(times: list[tuple[datetime, str]], jam: float = JAM):
    """Fungsi cfg['skip_fn'] untuk _core.try_open: alasan dilewati, atau None."""
    def f(direction: str, now: datetime) -> str | None:
        nx = berikut(now, times, jam)
        return f"jeda {jam:.0f} jam sebelum {nx[1]} {jam_wib(nx[0])}" if nx else None
    return f


def label(now: datetime, times: list[tuple[datetime, str]], jam: float = JAM) -> dict:
    """Info heartbeat XAU untuk aplikasi (field 'jeda'): on = sinyal baru sedang dijeda."""
    nx = berikut(now, times, jam)
    if not nx:
        return {"on": False}
    return {"on": True, "berita": nx[1], "sampai": nx[0].isoformat(),
            "text": f"⏸️ Sinyal XAU baru dijeda s.d. {nx[1]} {jam_wib(nx[0])} — {jam:.0f} jam sebelum NFP/CPI/Fed "
                    f"sinyal lebih sering gagal (teruji 2012–2026)"}


def siapkan(rows_fn, now: datetime, env=None):
    """(skip_fn, label) untuk tick XAU. rows_fn() = baris kalender ForexFactory (boleh gagal → jadwal.json saja)."""
    env = os.environ if env is None else env
    jam = float(env.get("XAU_NEWS_SKIP_JAM", JAM))
    try:
        rows = rows_fn() or []
    except Exception:  # noqa: BLE001 - kalender opsional, jadwal.json tetap dipakai
        rows = []
    times = waktu(rows, _jadwal())
    return skip_fn(times, jam), label(now, times, jam)
