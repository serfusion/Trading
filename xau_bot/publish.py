"""Kirim sinyal ke aplikasi Android lewat ntfy (https://ntfy.sh, open-source, bisa self-host).

Dua topik:
- `<topic>`      : pesan teks rapi (bisa dibaca juga oleh aplikasi resmi "ntfy")
- `<topic>-data` : JSON terstruktur untuk aplikasi "XAU Signal" di folder android/

Topik dibuat acak sekali lalu disimpan di data/app_topic.txt, jadi tidak perlu .env/config.
Siapa pun yang tahu nama topik bisa membaca sinyal, jadi jangan dibagikan.
"""
from __future__ import annotations

import json
import logging
import queue
import secrets
import threading
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def _json(value):
    """Timestamp -> ISO 8601, angka numpy -> angka Python."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def load_or_create_topic(path: str) -> str:
    p = Path(path)
    if p.exists():
        topic = p.read_text(encoding="utf-8").strip()
        if topic:
            return topic
    topic = "xau-" + secrets.token_urlsafe(18).replace("-", "a").replace("_", "b")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(topic, encoding="utf-8")
    return topic


class Publisher:
    """No-op; dipakai bila aplikasi dimatikan dan di backtest."""

    topic = ""
    server = ""

    def publish(self, event: dict, text: str | None = None, title: str | None = None,
                priority: int = 3, tags: list[str] | None = None) -> None:
        return None

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class NtfyPublisher(Publisher):
    def __init__(self, server: str, topic: str):
        self.server = server.rstrip("/")
        self.topic = topic
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def publish(self, event: dict, text: str | None = None, title: str | None = None,
                priority: int = 3, tags: list[str] | None = None) -> None:
        self._q.put((event, text, title, priority, tags or []))

    def _post(self, payload: dict) -> None:
        try:
            requests.post(self.server + "/", data=json.dumps(payload).encode("utf-8"), timeout=15,
                          headers={"Content-Type": "application/json"})
        except requests.RequestException as exc:
            log.warning("Gagal kirim ke aplikasi (ntfy): %s", exc)

    def _run(self) -> None:
        while not self._stop.is_set():
            item = self._q.get()
            if item is None:
                break
            event, text, title, priority, tags = item
            self._post({"topic": self.topic + "-data", "message": json.dumps(event, default=_json),
                        "priority": 1})
            if text:
                self._post({"topic": self.topic, "message": text, "title": title or "XAU Signal",
                            "priority": priority, "tags": tags})

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._q.put(None)
