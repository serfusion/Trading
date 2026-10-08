"""Klien Telegram Bot API minimal (urllib, long polling getUpdates). Hanya chat_id pemilik yang dilayani."""
from __future__ import annotations

import html
import json
import queue
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org"

MENU = [["📊 Status", "📂 Posisi"], ["🧾 Riwayat", "🆕 Listing"], ["🔎 Pindai", "⏸ Jeda", "▶️ Lanjut"], ["❓ Bantuan"]]


def esc(s) -> str:
    return html.escape(str(s), quote=False)


class Telegram:
    def __init__(self, token: str, chat_ids: list[int], timeout_poll: int = 25):
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN kosong (isi di sniper_bot/.env)")
        self.token, self.chat_ids, self.tp = token, [int(c) for c in chat_ids], timeout_poll
        self.masuk: queue.Queue = queue.Queue()
        self._stop = threading.Event()

    def _call(self, method: str, data: dict, timeout: float = 30) -> dict:
        body = json.dumps(data).encode()
        req = urllib.request.Request(f"{API}/bot{self.token}/{method}", data=body,
                                     headers={"content-type": "application/json"})
        for k in range(4):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                info = {}
                try:
                    info = json.loads(e.read())
                except Exception:  # noqa: BLE001
                    pass
                retry = (info.get("parameters") or {}).get("retry_after")
                if e.code == 429 and retry:
                    time.sleep(float(retry) + 0.5)
                    continue
                if e.code in (500, 502, 503, 504):
                    time.sleep(2 * (k + 1))
                    continue
                return {"ok": False, "error_code": e.code, "description": info.get("description", str(e))}
            except Exception as e:  # noqa: BLE001 - jaringan
                if k == 3:
                    return {"ok": False, "description": str(e)[:200]}
                time.sleep(2 * (k + 1))
        return {"ok": False}

    def kirim(self, teks: str, chat_id: int | None = None, menu: bool = False, tombol: list | None = None) -> None:
        """teks = HTML Telegram (sudah di-escape oleh pemanggil). Dipotong per 3.900 karakter."""
        for cid in ([chat_id] if chat_id else self.chat_ids):
            for i in range(0, max(len(teks), 1), 3900):
                d = {"chat_id": cid, "text": teks[i:i + 3900], "parse_mode": "HTML", "disable_web_page_preview": True}
                if menu:
                    d["reply_markup"] = {"keyboard": MENU, "resize_keyboard": True, "is_persistent": True}
                elif tombol:
                    d["reply_markup"] = {"inline_keyboard": tombol}
                self._call("sendMessage", d)

    def jawab_tombol(self, callback_id: str, teks: str = "") -> None:
        self._call("answerCallbackQuery", {"callback_query_id": callback_id, "text": teks[:180]})

    def get_updates(self, offset: int) -> list[dict]:
        r = self._call("getUpdates", {"offset": offset, "timeout": self.tp,
                                      "allowed_updates": ["message", "callback_query"]}, timeout=self.tp + 10)
        return r.get("result", []) if r.get("ok") else []

    def mulai_polling(self, offset: int) -> None:
        def loop():
            off = offset
            while not self._stop.is_set():
                for u in self.get_updates(off):
                    off = max(off, u["update_id"] + 1)
                    self.masuk.put((off, u))
                if self._stop.is_set():
                    break
        threading.Thread(target=loop, name="telegram", daemon=True).start()

    def berhenti(self) -> None:
        self._stop.set()

    def ambil(self) -> list[tuple[int, dict, int, str, str | None]]:
        """[(offset_baru, update, chat_id, teks/data, callback_id)] hanya dari chat pemilik."""
        out = []
        while True:
            try:
                off, u = self.masuk.get_nowait()
            except queue.Empty:
                return out
            if "callback_query" in u:
                cq = u["callback_query"]
                cid = (cq.get("message") or {}).get("chat", {}).get("id")
                if cid in self.chat_ids:
                    out.append((off, u, cid, cq.get("data", ""), cq["id"]))
            else:
                m = u.get("message") or {}
                cid = m.get("chat", {}).get("id")
                if cid in self.chat_ids:
                    out.append((off, u, cid, m.get("text", "") or "", None))
                elif cid:
                    # bukan pemilik: balas id-nya saja (memudahkan setelan), tanpa data apa pun
                    self._call("sendMessage", {"chat_id": cid, "text": f"Bot pribadi. chat_id kamu: {cid}"})


class TelegramMati:
    """Pengganti bila Telegram dimatikan (mis. uji lokal): pesan dicetak ke layar."""

    chat_ids: list[int] = []

    def kirim(self, teks: str, chat_id: int | None = None, menu: bool = False, tombol: list | None = None) -> None:
        import re
        print("[TG]", re.sub(r"<[^>]+>", "", html.unescape(teks)), flush=True)

    def jawab_tombol(self, *a, **k) -> None:
        return None

    def mulai_polling(self, offset: int) -> None:
        return None

    def berhenti(self) -> None:
        return None

    def ambil(self) -> list:
        return []
