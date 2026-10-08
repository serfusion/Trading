"""Status bot di satu file JSON (ditulis atomik: file sementara lalu os.replace) — tahan mati listrik/restart."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

KOSONG = {
    "versi": 1,
    "posisi": {},          # id -> posisi terbuka
    "riwayat": [],         # posisi tertutup (maks 500 terakhir)
    "listing": {},         # SIMBOL -> {t_listing, p0, limit, status}
    "simbol_dikenal": [],  # simbol USDT yang sudah dilihat
    "spot": {"terakhir": {}, "pindai": None},
    "kas_kertas": None,    # saldo USD mode kertas
    "jeda": False,         # True = tidak membuka posisi baru
    "strategi_mati": [],   # nama strategi yang dimatikan lewat Telegram
    "hari": {"tgl": None, "pnl": 0.0, "trade": 0, "jeda_rugi": False},
    "telegram_offset": 0,
    "id_berikut": 1,
}


class Store:
    def __init__(self, data_dir: str):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "state.json"
        self.lock = threading.RLock()
        self.s = self._baca()

    def _baca(self) -> dict:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                for k, v in KOSONG.items():
                    d.setdefault(k, json.loads(json.dumps(v)))
                return d
            except json.JSONDecodeError:
                bak = self.path.with_suffix(f".rusak.{int(time.time())}.json")
                self.path.rename(bak)
        return json.loads(json.dumps(KOSONG))

    def simpan(self) -> None:
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.s, indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)

    def id_baru(self, awalan: str) -> str:
        with self.lock:
            n = self.s["id_berikut"]
            self.s["id_berikut"] = n + 1
            return f"{awalan}{n}"

    def tutup(self, pid: str, data: dict) -> dict:
        with self.lock:
            pos = self.s["posisi"].pop(pid)
            pos.update(data)
            self.s["riwayat"] = ([pos] + self.s["riwayat"])[:500]
            return pos
