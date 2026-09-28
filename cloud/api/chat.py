"""Endpoint chat untuk aplikasi Android.

POST /api/chat   {"messages": [{"role": "user", "content": "hasil NFP sudah keluar, ..."}, ...]}
Header wajib: X-Chat-Key: <CHAT_KEY>, atau (bila CHAT_KEY kosong) topik ntfy yang sama dengan aplikasi.
Environment: ANTHROPIC_API_KEY (wajib), CHAT_MODEL (opsional, bawaan claude-opus-5).
Balasan: {"ok": true, "reply": "...", "sources": [{"title", "url"}], "model": "..."}
"""
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

import _chat  # noqa: E402
import _core  # noqa: E402


def _states() -> dict:
    env = os.environ
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY")):
        return {}
    store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    out = {}
    for asset, row in (("XAU/USD", "main"), ("BTC/USD", "btc")):
        try:
            out[asset] = store.get_state(row)
        except Exception:  # noqa: BLE001 - konteks opsional
            out[asset] = {}
    return out


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
        if not os.environ.get("ANTHROPIC_API_KEY"):
            self._send(500, {"ok": False, "error": "ANTHROPIC_API_KEY belum diisi di Vercel"})
            return
        import anthropic
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(length, 200_000)) or b"{}")
            client = anthropic.Anthropic(timeout=50.0, max_retries=1)   # batas fungsi Vercel 60 detik
            context = _chat.live_context(datetime.now(timezone.utc), _chat.fetch_calendar(), _states())
            self._send(200, _chat.ask(client, body.get("messages") or [], context,
                                      os.environ.get("CHAT_MODEL", _chat.MODEL)))
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
        except anthropic.AuthenticationError:
            self._send(500, {"ok": False, "error": "ANTHROPIC_API_KEY ditolak Anthropic — cek kuncinya di Vercel"})
        except anthropic.RateLimitError:
            self._send(429, {"ok": False, "error": "Terlalu banyak pertanyaan, coba lagi sebentar"})
        except anthropic.APITimeoutError:
            self._send(504, {"ok": False, "error": "Jawaban terlalu lama, coba pertanyaan yang lebih singkat"})
        except anthropic.APIStatusError as exc:
            self._send(502, {"ok": False, "error": f"Claude API {exc.status_code}: {exc.message}"})
        except anthropic.APIConnectionError:
            self._send(502, {"ok": False, "error": "Tidak bisa menghubungi Claude API"})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def do_GET(self):
        self._send(200, {"ok": True, "info": "POST {messages: [...]} dengan header X-Chat-Key"})
