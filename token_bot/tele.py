"""Klien Telegram minimal untuk bot kontrol token (urllib, long polling). Perintah hanya dari CHAT PRIBADI pemilik.

Keamanan sama dengan sniper_bot/telegram.py: hanya from.id di daftar yang dilayani; grup & orang lain dibuang tanpa
balasan; rahasia disensor dari pesan galat (query string URL/kunci RPC/private key env).
"""
from __future__ import annotations

import html
import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org"
# tombol persis gaya screenshot (wetharb/circarb): Saldo · Harga · Log · BUY ON/OFF · STOP · RESTART · Tx
MENU = [["💰 Saldo", "📈 Harga"], ["📄 Log", "🧾 Tx"], ["🅰 BUY ON/OFF", "⏹ STOP", "🔄 RESTART"], ["❓ Bantuan"]]
RAHASIA_ENV = ("TELEGRAM_TOKEN", "TOKEN_BOT_PK", "TWELVEDATA_API_KEY")


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def sensor(teks) -> str:
    s = str(teks)
    s = re.sub(r"(https?://[^\s?'\"]+)\?[^\s'\"]*", r"\1?…", s)
    s = re.sub(r"/bot\d+:[A-Za-z0-9_-]+", "/bot…", s)
    s = re.sub(r"(/v[1-3]/)[A-Za-z0-9_-]{16,}", r"\1…", s)
    s = re.sub(r"\b0x[a-fA-F0-9]{64}\b", "0x…(kunci?)", s)          # jangan pernah tampilkan private key
    for k in RAHASIA_ENV:
        v = os.environ.get(k, "").strip()
        if len(v) >= 6:
            s = s.replace(v, "…")
    return s


def _polos(teks: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", teks))


def potong(teks: str, n: int = 3900) -> list[str]:
    out, cur = [], ""
    for baris in teks.split("\n"):
        while len(baris) > n:
            if cur:
                out.append(cur)
                cur = ""
            out.append(baris[:n])
            baris = baris[n:]
        if len(cur) + len(baris) + 1 > n and cur:
            out.append(cur)
            cur = baris
        else:
            cur = f"{cur}\n{baris}" if cur else baris
    if cur or not out:
        out.append(cur)
    return out


class Telegram:
    def __init__(self, token: str, chat_ids: list[int], timeout_poll: int = 25):
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN kosong (isi di token_bot/.env)")
        self.token, self.chat_ids, self.tp = token, [int(c) for c in chat_ids], timeout_poll
        self.masuk: queue.Queue = queue.Queue()
        self._stop = threading.Event()

    def _call(self, method: str, data: dict, timeout: float = 30, maks_tunggu: float = 30) -> dict:
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
                if e.code == 429 and retry and float(retry) <= maks_tunggu:
                    time.sleep(float(retry) + 0.5)
                    continue
                if e.code in (500, 502, 503, 504):
                    time.sleep(2 * (k + 1))
                    continue
                return {"ok": False, "error_code": e.code, "description": info.get("description", f"HTTP {e.code}")}
            except Exception as e:  # noqa: BLE001
                if k == 3:
                    return {"ok": False, "description": sensor(e)[:200]}
                time.sleep(2 * (k + 1))
        return {"ok": False, "description": "gagal setelah 4 percobaan"}

    def kirim(self, teks: str, chat_id: int | None = None, menu: bool = False, tombol: list | None = None) -> None:
        for cid in ([chat_id] if chat_id else self.chat_ids):
            for bagian in potong(teks):
                d = {"chat_id": cid, "text": bagian, "parse_mode": "HTML", "disable_web_page_preview": True}
                if menu:
                    d["reply_markup"] = {"keyboard": MENU, "resize_keyboard": True, "is_persistent": True}
                elif tombol:
                    d["reply_markup"] = {"inline_keyboard": tombol}
                r = self._call("sendMessage", d)
                if not r.get("ok") and r.get("error_code") == 400:
                    d.pop("parse_mode")
                    d["text"] = _polos(bagian)
                    r = self._call("sendMessage", d)
                if not r.get("ok"):
                    print("[telegram] kirim gagal:", r.get("description"), flush=True)

    def jawab_tombol(self, callback_id: str, teks: str = "") -> None:
        self._call("answerCallbackQuery", {"callback_query_id": callback_id, "text": teks[:180]}, maks_tunggu=5)

    def _milik(self, u: dict) -> bool:
        if "callback_query" in u:
            cq = u["callback_query"]
            chat, dari = (cq.get("message") or {}).get("chat") or {}, (cq.get("from") or {}).get("id")
        else:
            m = u.get("message") or {}
            chat, dari = m.get("chat") or {}, (m.get("from") or {}).get("id")
        return chat.get("type") == "private" and dari in self.chat_ids and chat.get("id") in self.chat_ids

    def mulai_polling(self, offset: int) -> None:
        def loop():
            off, jeda = offset, 5.0
            while not self._stop.is_set():
                r = self._call("getUpdates", {"offset": off, "timeout": self.tp,
                                              "allowed_updates": ["message", "callback_query"]}, timeout=self.tp + 10)
                if not r.get("ok"):
                    if r.get("error_code") == 409:
                        print("[telegram] 409: token dipakai proses lain.", flush=True)
                    self._stop.wait(jeda)
                    jeda = min(jeda * 2, 120.0)
                    continue
                jeda = 5.0
                for u in r.get("result", []):
                    off = max(off, u["update_id"] + 1)
                    self.masuk.put((off, u if self._milik(u) else None))
        threading.Thread(target=loop, name="tele", daemon=True).start()

    def berhenti(self) -> None:
        self._stop.set()

    def ambil(self) -> list[tuple[int, dict | None, int | None, str, str | None]]:
        out = []
        while True:
            try:
                off, u = self.masuk.get_nowait()
            except queue.Empty:
                return out
            if u is None:
                out.append((off, None, None, "", None))
            elif "callback_query" in u:
                cq = u["callback_query"]
                out.append((off, u, cq["message"]["chat"]["id"], cq.get("data", ""), cq["id"]))
            else:
                m = u["message"]
                out.append((off, u, m["chat"]["id"], m.get("text", "") or "", None))


class TelegramMati:
    chat_ids: list[int] = []

    def kirim(self, teks: str, chat_id: int | None = None, menu: bool = False, tombol: list | None = None) -> None:
        print("[TG]", _polos(teks), flush=True)

    def jawab_tombol(self, *a, **k) -> None:
        return None

    def mulai_polling(self, offset: int) -> None:
        return None

    def berhenti(self) -> None:
        return None

    def ambil(self) -> list:
        return []
