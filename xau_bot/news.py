"""Filter kalender ekonomi (feed ForexFactory / faireconomy)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

from .config import NewsConfig

log = logging.getLogger(__name__)


@dataclass
class NewsEvent:
    time: pd.Timestamp
    title: str
    currency: str
    impact: str


def parse_events(payload: list[dict]) -> list[NewsEvent]:
    events = []
    for row in payload or []:
        try:
            ts = pd.Timestamp(row["date"])
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
            events.append(NewsEvent(ts, str(row.get("title", "")), str(row.get("country", "")),
                                    str(row.get("impact", ""))))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(events, key=lambda e: e.time)


class NewsFilter:
    def __init__(self, cfg: NewsConfig, fetch: Callable[[str], list[dict]] | None = None):
        self.cfg = cfg
        self._fetch = fetch or self._http_fetch
        self.events: list[NewsEvent] = []
        self.last_refresh: pd.Timestamp | None = None
        self.error: str | None = None

    @staticmethod
    def _http_fetch(url: str) -> list[dict]:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "xau-bot/1.0"})
        resp.raise_for_status()
        return resp.json()

    def _load_cache(self) -> list[dict] | None:
        path = Path(self.cfg.cache_file)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
        return None

    def refresh(self, now: pd.Timestamp, force: bool = False) -> None:
        if not self.cfg.enabled:
            return
        due = self.last_refresh is None or (now - self.last_refresh) >= pd.Timedelta(
            minutes=self.cfg.refresh_minutes)
        if not (due or force):
            return
        self.last_refresh = now
        try:
            payload = self._fetch(self.cfg.url)
            self.events = self._filter(parse_events(payload))
            self.error = None
            try:
                path = Path(self.cfg.cache_file)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload), encoding="utf-8")
            except OSError:
                pass
        except Exception as exc:  # noqa: BLE001 - jaringan apa pun
            cached = self._load_cache()
            if cached and not self.events:
                self.events = self._filter(parse_events(cached))
            self.error = f"Gagal ambil kalender: {exc}"
            # coba lagi lebih cepat
            self.last_refresh = now - pd.Timedelta(minutes=max(self.cfg.refresh_minutes - 5, 0))
            log.warning(self.error)

    def _filter(self, events: list[NewsEvent]) -> list[NewsEvent]:
        cur = {c.upper() for c in self.cfg.currencies}
        imp = {i.lower() for i in self.cfg.impacts}
        return [e for e in events if e.currency.upper() in cur and e.impact.lower() in imp]

    def blocked(self, now: pd.Timestamp) -> str | None:
        if not self.cfg.enabled:
            return None
        if self.error and not self.events and self.cfg.block_on_error:
            return "Kalender berita tidak tersedia"
        before = pd.Timedelta(minutes=self.cfg.block_before_minutes)
        after = pd.Timedelta(minutes=self.cfg.block_after_minutes)
        for ev in self.events:
            if ev.time - before <= now <= ev.time + after:
                return f"Berita {ev.currency} {ev.title} ({ev.time:%H:%M} UTC)"
        return None

    def upcoming(self, now: pd.Timestamp, minutes: int) -> list[NewsEvent]:
        end = now + pd.Timedelta(minutes=minutes)
        return [e for e in self.events if now <= e.time <= end]

    def next_event(self, now: pd.Timestamp) -> NewsEvent | None:
        return next((e for e in self.events if e.time >= now), None)
