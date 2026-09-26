"""Endpoint kontrol auto order untuk aplikasi Android.

GET  /api/control            -> status (auto/jeda/lot, saldo & posisi dari MetaApi)
POST /api/control  {"auto": true, "paused": false, "leg_lot": 0.01, "legs": 5, "close_all": false}
Header wajib: X-Control-Key: <CONTROL_KEY>
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

import _core  # noqa: E402
from tick import executor_from_env  # noqa: E402


def _store():
    env = os.environ
    return _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])


def _pub():
    env = os.environ
    return _core.Ntfy(env.get("NTFY_TOPIC", ""), env.get("NTFY_SERVER", "https://ntfy.sh"))


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        key = os.environ.get("CONTROL_KEY", "")
        return bool(key) and self.headers.get("X-Control-Key", "") == key

    def do_GET(self):
        if not self._authorized():
            self._send(401, {"ok": False, "error": "Kunci kontrol salah atau CONTROL_KEY belum diisi"})
            return
        try:
            self._send(200, _core.status(_store(), executor_from_env()))
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": str(exc)})

    def do_POST(self):
        if not self._authorized():
            self._send(401, {"ok": False, "error": "Kunci kontrol salah atau CONTROL_KEY belum diisi"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            changes = json.loads(self.rfile.read(length) or b"{}")
            max_lot = float(os.environ.get("MAX_LEG_LOT", 0.10))
            self._send(200, _core.apply_control(_store(), executor_from_env(), _pub(), changes, max_lot))
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": str(exc)})
