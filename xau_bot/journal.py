"""Jurnal SQLite: setup, tiket order, dan status manajemen posisi (tahan restart)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from .models import Setup

SCHEMA = """
CREATE TABLE IF NOT EXISTS setups (
    key TEXT PRIMARY KEY,
    created TEXT, direction TEXT, entry REAL, sl REAL, tp1 REAL, tp2 REAL,
    score INTEGER, reasons TEXT, status TEXT, note TEXT, volume REAL
);
CREATE TABLE IF NOT EXISTS tickets (
    ticket INTEGER PRIMARY KEY,
    setup_key TEXT, leg TEXT, placed TEXT, be_done INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    time TEXT, level TEXT, message TEXT
);
"""


class Journal:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def has_setup(self, key: str) -> bool:
        return self.db.execute("SELECT 1 FROM setups WHERE key=?", (key,)).fetchone() is not None

    def record_setup(self, setup: Setup, status: str, note: str = "", volume: float = 0.0) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO setups VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (setup.key, str(setup.created_time), setup.direction.label, setup.entry, setup.sl,
             setup.tp1, setup.tp2, setup.score, json.dumps(setup.reasons), status, note, volume))
        self.db.commit()

    def setup_row(self, key: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM setups WHERE key=?", (key,)).fetchone()

    def set_status(self, key: str, status: str, note: str = "") -> None:
        self.db.execute("UPDATE setups SET status=?, note=? WHERE key=?", (status, note, key))
        self.db.commit()

    def add_ticket(self, ticket: int, setup_key: str, leg: str, placed: pd.Timestamp) -> None:
        self.db.execute("INSERT OR REPLACE INTO tickets (ticket, setup_key, leg, placed) VALUES (?,?,?,?)",
                        (int(ticket), setup_key, leg, str(placed)))
        self.db.commit()

    def ticket(self, ticket: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM tickets WHERE ticket=?", (int(ticket),)).fetchone()

    def tickets_for(self, setup_key: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM tickets WHERE setup_key=?", (setup_key,)).fetchall()

    def mark_be(self, ticket: int) -> None:
        self.db.execute("UPDATE tickets SET be_done=1 WHERE ticket=?", (int(ticket),))
        self.db.commit()

    def log(self, time: pd.Timestamp, level: str, message: str) -> None:
        self.db.execute("INSERT INTO events VALUES (?,?,?)", (str(time), level, message))
        self.db.commit()

    def setups_since(self, since: pd.Timestamp) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM setups WHERE created >= ? ORDER BY created",
                               (str(since),)).fetchall()
