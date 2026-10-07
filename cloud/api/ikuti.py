"""Endpoint Vercel: GET /api/ikuti?key=<CRON_SECRET> — 👥 pantau posisi copy trader yang diikuti (_ikuti.py).

Dipanggil Supabase pg_cron tiap ±15 detik (docs/COPY_TRADE.md bagian Follow). Ringan: hanya membaca posisi terbuka
trader yang diikuti (maks 20) lalu mengirim kejadian BUKA/TUTUP ke topik ntfy <NTFY_TOPIC>-copy. Tanpa order.
COPY_FOLLOW=0 mematikan.
"""
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

import _core  # noqa: E402
import _ikuti  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        env = os.environ
        secret = env.get("CRON_SECRET", "")
        key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
        if not secret or (key != secret and self.headers.get("Authorization", "") != f"Bearer {secret}"):
            self._send(401, {"ok": False, "error": "kunci salah atau CRON_SECRET belum diisi"})
            return
        if env.get("COPY_FOLLOW", "1") != "1":
            self._send(200, {"ok": True, "info": "COPY_FOLLOW=0 (mati)"})
            return
        try:
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            pub = _ikuti.publisher(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh"))
            self._send(200, _ikuti.putaran(store, pub))
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300],
                             "trace": traceback.format_exc()[-600:]})

    do_POST = do_GET
