"""Endpoint tab Tanya untuk aplikasi Android — penjawab berbasis DATA, tanpa AI (lihat _chat.py).

POST /api/chat   {"messages": [{"role": "user", "content": "NFP Act: 45K Cons: 98K Prev: 162K"}, ...]}
GET  /api/chat   (dengan header kunci) -> {"ok": true, "calendar": [...], "tren": {...}, "persiapan": {...},
                 "arsip": {...}}: berita USD high-impact minggu ini (Act otomatis dari FRED setelah rilis), status tren
                 per indikator, kartu 🎯 (perkiraan hari H dari Kalshi+Polymarket / hasil setelah Act, _hari_h.py; Fed
                 berikutnya), Act berlapis (_aktual.py), dan status arsip berita ke GitHub (_arsip.py)
Header wajib: X-Chat-Key: <CHAT_KEY>, atau (bila CHAT_KEY kosong) topik ntfy yang sama dengan aplikasi.
Balasan: {"ok": true, "reply": "...", "sources": [], "model": "data (tanpa AI)"}
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

import _aktual  # noqa: E402
import _arsip  # noqa: E402
import _chat  # noqa: E402
import _core  # noqa: E402
import _hari_h  # noqa: E402
import _kalshi  # noqa: E402
import _polymarket  # noqa: E402
import _persiapan  # noqa: E402
import _tren  # noqa: E402

TREN_TTL = timedelta(hours=3)


def _states() -> tuple[dict, dict]:
    """(state XAU/BTC, cache funding) dari Supabase; kosong bila belum diatur / gagal (konteks opsional)."""
    env = os.environ
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY")):
        return {}, {}
    store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    out, funding = {}, {}
    for key, row in (("XAU/USD", "main"), ("BTC/USD", "btc"), ("funding", "funding")):
        try:
            data = store.get_state(row)
        except Exception:  # noqa: BLE001
            data = {}
        if key == "funding":
            funding = data or {}
        else:
            out[key] = data
    return out, funding


def _store():
    env = os.environ
    if env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY"):
        return _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    return None


def _calendar(store, now: datetime) -> list | None:
    """Kalender ForexFactory, cache Supabase 10 menit (hemat & tidak kena limit saat banyak aplikasi dibuka)."""
    try:
        return _arsip.calendar_cached(store, now, _chat.fetch_calendar)
    except Exception:  # noqa: BLE001 - cache opsional
        return _chat.fetch_calendar()


def _tren_status(now: datetime) -> dict:
    """Status tren per indikator (tab News), cache 3 jam di baris Supabase 'tren' (hemat kuota Twelve Data)."""
    env = os.environ
    if not env.get("TWELVEDATA_API_KEY"):
        return {}
    store = None
    if env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY"):
        store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        try:
            cached = store.get_state("tren") or {}
            if cached.get("dihitung") and now - datetime.fromisoformat(cached["dihitung"]) < TREN_TTL:
                return cached
        except Exception:  # noqa: BLE001 - cache opsional
            pass
    data = _tren.compute(env["TWELVEDATA_API_KEY"], now)
    if store is not None:
        try:
            store.save_state(data, "tren")
        except Exception:  # noqa: BLE001
            pass
    return data


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        key = os.environ.get("CHAT_KEY") or os.environ.get("NTFY_TOPIC", "")
        return bool(key) and self.headers.get("X-Chat-Key", "") == key

    def do_POST(self):
        if not self._authorized():
            self._send(401, {"ok": False, "error": "Kunci chat salah (pakai topik ntfy yang sama dengan cloud)"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(length, 200_000)) or b"{}")
            states, funding = _states()
            now = datetime.now(timezone.utc)
            self._send(200, _chat.answer(body.get("messages") or [], now, _calendar(_store(), now), states, funding))
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})

    def do_GET(self):
        if not self._authorized():
            self._send(200, {"ok": True, "info": "POST {messages: [...]} dengan header X-Chat-Key"})
            return
        try:
            now = datetime.now(timezone.utc)
            try:
                tren = _tren_status(now)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim walau status tren gagal
                tren = {"error": _arsip.redact(f"{type(exc).__name__}: {exc}")}
            store = _store()
            rows = _calendar(store, now)
            try:
                persiapan = _persiapan.cards(rows, now)     # 🎯 kartu persiapan berita (pengganti contoh pertanyaan)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim walau kartu gagal
                persiapan = {"error": _arsip.redact(f"{type(exc).__name__}: {exc}")}
            if isinstance(persiapan, dict) and persiapan.get("berita"):
                try:                                          # 🎲 peluang Kalshi per berita (cache 15 menit)
                    _kalshi.attach(persiapan, store, now)
                except Exception:  # noqa: BLE001 - Kalshi opsional
                    pass
            calendar = _chat.calendar_json(rows, now, fetch=lambda s: [])
            try:                                              # Act berlapis: BLS -> FRED API -> FRED CSV (_aktual.py)
                aktual = _aktual.fill(calendar, store, now, os.environ)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim
                aktual = {"status": _arsip.redact(f"gagal: {type(exc).__name__}: {exc}"[:200])}
            for c in calendar:                                # Act sudah keluar -> kesimpulan arah otomatis
                if c.get("actual"):
                    try:
                        c["arah"] = _persiapan.kesimpulan(c["title"], c["actual"], c.get("forecast", ""))
                    except Exception:  # noqa: BLE001
                        pass
            if isinstance(persiapan, dict) and persiapan.get("berita") is not None:
                try:                                          # 🎯 perkiraan hari H / ✅ hasil + 🏦 Fed (Polymarket)
                    berita = persiapan["berita"]
                    ks = _kalshi.cached_snapshot(berita, store, now)[0] if berita else {}
                    ps = _polymarket.cached_snapshot(berita, store, now)[0] if berita else {}
                    _hari_h.attach(persiapan, calendar, store, now, ks, ps, _polymarket.cached_fed(store, now))
                except Exception:  # noqa: BLE001 - opsional
                    pass
            try:                                              # arsip berita ke GitHub (tiap aplikasi dibuka)
                arsip = _arsip.save(rows, calendar, now, store, os.environ)
            except Exception as exc:  # noqa: BLE001 - arsip tidak boleh mengganggu kalender
                arsip = {"status": _arsip.redact(f"gagal: {type(exc).__name__}: {str(exc)[:160]}")}
            if isinstance(persiapan, dict):
                persiapan["arsip"] = arsip                    # ditampilkan di kartu 🎯 (cek token tanpa curl)
            self._send(200, {"ok": True, "calendar": calendar, "tren": tren, "persiapan": persiapan,
                             "arsip": arsip, "aktual": aktual})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})
