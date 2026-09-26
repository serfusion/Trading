"""Endpoint Vercel: GET /api/tick?key=<CRON_SECRET>  (dipanggil Supabase pg_cron)."""
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

import _core  # noqa: E402


def run() -> tuple[int, dict]:
    env = os.environ
    missing = [k for k in ("TWELVEDATA_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "NTFY_TOPIC")
               if not env.get(k)]
    if missing:
        return 500, {"ok": False, "error": f"Environment variable belum diisi: {', '.join(missing)}"}
    result = _core.tick(
        datetime.now(timezone.utc),
        _core.TwelveData(env["TWELVEDATA_API_KEY"], env.get("SYMBOL", "XAU/USD")),
        _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"]),
        _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
        symbol=env.get("SYMBOL", "XAU/USD"),
    )
    return 200, result


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        secret = os.environ.get("CRON_SECRET", "")
        key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
        auth = self.headers.get("Authorization", "")
        if not secret or (key != secret and auth != f"Bearer {secret}"):
            self._send(401, {"ok": False, "error": "kunci salah atau CRON_SECRET belum diisi"})
            return
        try:
            code, body = run()
        except Exception as exc:  # noqa: BLE001
            code, body = 500, {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]}
        self._send(code, body)

    do_POST = do_GET
