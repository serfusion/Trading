"""GET /api/topic -> contoh topik ntfy acak (salin ke NTFY_TOPIC di Vercel & ke aplikasi)."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

import _core  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"topik_baru": _core.new_topic(),
                           "catatan": "Salin ke NTFY_TOPIC (Vercel) dan kolom Topik di aplikasi. "
                                      "Jangan dibagikan."}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
