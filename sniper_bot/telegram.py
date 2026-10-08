"""Klien Telegram Bot API minimal (urllib, long polling getUpdates).

Keamanan: perintah hanya diterima dari CHAT PRIBADI dengan pengirim (from.id) yang ada di TELEGRAM_CHAT_ID. Pesan dari
orang lain atau dari grup dibuang di thread polling tanpa dibalas (tidak bisa dipakai membanjiri/menahan loop utama).
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

MENU = [["📊 Status", "📂 Posisi"], ["🧾 Riwayat", "🆕 Listing"], ["🔎 Pindai", "⏸ Jeda", "▶️ Lanjut"], ["❓ Bantuan"]]

RAHASIA_ENV = ("TELEGRAM_TOKEN", "BURSA_API_KEY", "BURSA_API_SECRET", "BURSA_API_PASSWORD", "TOKEN_BOT_PK")


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def sensor(teks) -> str:
    """Buang rahasia dari teks galat sebelum dicetak/dikirim: query string URL (tanda tangan ccxt), token bot di URL,
    kunci RPC di path, dan nilai literal variabel rahasia dari .env."""
    s = str(teks)
    s = re.sub(r"(https?://[^\s?'\"]+)\?[^\s'\"]*", r"\1?…", s)
    s = re.sub(r"(?i)\b(signature|apikey|api_key|api-key|accesskeyid|secret|token|passphrase)([=:]\s*)[^&\s'\",}]+",
               r"\1\2…", s)
    s = re.sub(r"/bot\d+:[A-Za-z0-9_-]+", "/bot…", s)
    s = re.sub(r"(/v[1-3]/)[A-Za-z0-9_-]{16,}", r"\1…", s)
    for k in RAHASIA_ENV:
        v = os.environ.get(k, "").strip()
        if len(v) >= 6:
            s = s.replace(v, "…")
    return s


def _polos(teks: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", teks))


def potong(teks: str, n: int = 3900) -> list[str]:
    """Potong per baris (tag HTML tidak terbelah); baris > n dipotong kasar."""
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
            raise RuntimeError("TELEGRAM_TOKEN kosong (isi di sniper_bot/.env)")
        self.token, self.chat_ids, self.tp = token, [int(c) for c in chat_ids], timeout_poll
        self.masuk: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self.ditolak = 0

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
            except Exception as e:  # noqa: BLE001 - jaringan
                if k == 3:
                    return {"ok": False, "description": sensor(e)[:200]}
                time.sleep(2 * (k + 1))
        return {"ok": False, "description": "gagal setelah 4 percobaan"}

    def kirim(self, teks: str, chat_id: int | None = None, menu: bool = False, tombol: list | None = None) -> None:
        """teks = HTML Telegram (nilai dari luar sudah di-escape pemanggil). Bila HTML ditolak, dikirim ulang polos."""
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

    def get_updates(self, offset: int) -> tuple[bool, list[dict], dict]:
        r = self._call("getUpdates", {"offset": offset, "timeout": self.tp,
                                      "allowed_updates": ["message", "callback_query"]}, timeout=self.tp + 10)
        return bool(r.get("ok")), r.get("result", []) if r.get("ok") else [], r

    def _milik(self, u: dict) -> bool:
        """Hanya chat pribadi pemilik: chat.type private DAN from.id terdaftar."""
        if "callback_query" in u:
            cq = u["callback_query"]
            chat = (cq.get("message") or {}).get("chat") or {}
            dari = (cq.get("from") or {}).get("id")
        else:
            m = u.get("message") or {}
            chat, dari = m.get("chat") or {}, (m.get("from") or {}).get("id")
        return chat.get("type") == "private" and dari in self.chat_ids and chat.get("id") in self.chat_ids

    def mulai_polling(self, offset: int) -> None:
        def loop():
            off, jeda = offset, 5.0
            while not self._stop.is_set():
                ok, hasil, r = self.get_updates(off)
                if not ok:
                    kode = r.get("error_code")
                    if kode == 401:
                        print("[telegram] TELEGRAM_TOKEN ditolak (401). Periksa .env.", flush=True)
                    elif kode == 409:
                        print("[telegram] 409: bot dipakai proses lain / webhook aktif. Matikan instance lain.",
                              flush=True)
                    self._stop.wait(jeda)
                    jeda = min(jeda * 2, 120.0)
                    continue
                jeda = 5.0
                for u in hasil:
                    off = max(off, u["update_id"] + 1)
                    if self._milik(u):
                        self.masuk.put((off, u))
                    else:
                        self.ditolak += 1
                        self.masuk.put((off, None))       # tetap majukan offset tersimpan
        threading.Thread(target=loop, name="telegram", daemon=True).start()

    def berhenti(self) -> None:
        self._stop.set()

    def ambil(self) -> list[tuple[int, dict | None, int | None, str, str | None]]:
        """[(offset_baru, update, chat_id, teks/data, callback_id)] — hanya dari pemilik (lainnya update None)."""
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
    """Pengganti bila Telegram dimatikan (mis. uji lokal): pesan dicetak ke layar."""

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
