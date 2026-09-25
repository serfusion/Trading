"""Notifikasi & perintah Telegram (Bot API langsung, tanpa library tambahan)."""
from __future__ import annotations

import logging
import queue
import threading
import requests

from .config import TelegramConfig

log = logging.getLogger(__name__)


class Notifier:
    """Antarmuka minimal; dipakai juga sebagai no-op saat Telegram nonaktif."""

    def send(self, text: str) -> None:
        log.info("NOTIF: %s", text.replace("\n", " | "))

    def start(self) -> None:
        return None

    def pending_commands(self) -> list[tuple[str, str]]:
        """Perintah masuk (cmd, argumen); diproses di thread utama oleh engine."""
        return []

    def stop(self) -> None:
        return None


class TelegramNotifier(Notifier):
    def __init__(self, cfg: TelegramConfig):
        self.cfg = cfg
        self.base = f"https://api.telegram.org/bot{cfg.token}"
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._commands: queue.Queue[tuple[str, str]] = queue.Queue()
        self._threads: list[threading.Thread] = []

    def send(self, text: str) -> None:
        super().send(text)
        self._queue.put(text)

    def _sender(self) -> None:
        while not self._stop.is_set():
            text = self._queue.get()
            if text is None:
                break
            for chunk in [text[i:i + 3900] for i in range(0, len(text), 3900)]:
                try:
                    requests.post(f"{self.base}/sendMessage", timeout=15, data={
                        "chat_id": self.cfg.chat_id, "text": chunk,
                        "disable_web_page_preview": "true"})
                except requests.RequestException as exc:
                    log.warning("Telegram gagal kirim: %s", exc)

    def _poller(self) -> None:
        offset = None
        while not self._stop.is_set():
            try:
                resp = requests.get(f"{self.base}/getUpdates", timeout=35,
                                    params={"timeout": 25, "offset": offset})
                updates = resp.json().get("result", [])
            except (requests.RequestException, ValueError):
                self._stop.wait(5)
                continue
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                if str(msg.get("chat", {}).get("id")) != str(self.cfg.chat_id):
                    continue  # hanya pemilik bot
                text = (msg.get("text") or "").strip()
                if not text.startswith("/"):
                    continue
                cmd, _, arg = text[1:].partition(" ")
                self._commands.put((cmd.split("@")[0].lower(), arg))

    def pending_commands(self) -> list[tuple[str, str]]:
        out = []
        while not self._commands.empty():
            out.append(self._commands.get_nowait())
        return out

    def start(self) -> None:
        for target in (self._sender, self._poller):
            th = threading.Thread(target=target, daemon=True)
            th.start()
            self._threads.append(th)

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(None)
