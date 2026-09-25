"""Sesi pasar, killzone, rollover, dan hari trading (batas 17:00 New York)."""
from __future__ import annotations

from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from .config import SessionConfig

NY = ZoneInfo("America/New_York")
WIB = ZoneInfo("Asia/Jakarta")


def _t(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh) % 24, int(mm))


def to_ny(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_convert(NY)


def fmt_wib(ts: pd.Timestamp | None, fmt: str = "%d %b %H:%M") -> str:
    if ts is None:
        return "-"
    return pd.Timestamp(ts).tz_convert(WIB).strftime(fmt) + " WIB"


def in_window(ny_time: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= ny_time < end
    return ny_time >= start or ny_time < end  # melewati tengah malam


def trading_day(ts: pd.Timestamp) -> date:
    """Hari trading forex dimulai 17:00 New York."""
    return (to_ny(ts) + timedelta(hours=7)).date()


def trading_week(ts: pd.Timestamp) -> tuple[int, int]:
    return trading_day(ts).isocalendar()[:2]


class SessionClock:
    def __init__(self, cfg: SessionConfig):
        self.cfg = cfg
        self.killzones = {k: (_t(v[0]), _t(v[1])) for k, v in cfg.killzones.items()}
        self.asia = (_t(cfg.asia_range[0]), _t(cfg.asia_range[1]))
        self.rollover = (_t(cfg.rollover_block[0]), _t(cfg.rollover_block[1]))
        self.friday_cutoff = _t(cfg.friday_cutoff)

    def killzone(self, ts: pd.Timestamp) -> str | None:
        t = to_ny(ts).time()
        for name, (start, end) in self.killzones.items():
            if in_window(t, start, end):
                return name
        return None

    def session_name(self, ts: pd.Timestamp) -> str:
        kz = self.killzone(ts)
        if kz:
            return kz
        t = to_ny(ts).time()
        if in_window(t, time(19, 0), time(2, 0)):
            return "Asia"
        if in_window(t, time(2, 0), time(8, 0)):
            return "London"
        if in_window(t, time(8, 0), time(17, 0)):
            return "NewYork"
        return "Off"

    def is_asia(self, ts: pd.Timestamp) -> bool:
        return in_window(to_ny(ts).time(), *self.asia)

    def entry_block_reason(self, ts: pd.Timestamp) -> str | None:
        ny = to_ny(ts)
        t = ny.time()
        wd = ny.weekday()  # Senin=0
        if wd == 5 or (wd == 4 and t >= time(17, 0)):
            return "Pasar tutup (akhir pekan)"
        if wd == 6:
            open_until = ny.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(
                minutes=self.cfg.sunday_open_block_minutes)
            if ny < open_until:
                return "Pembukaan pasar Minggu (gap/spread)"
        if wd == 4 and t >= self.friday_cutoff:
            return "Jumat sore (tidak entry baru)"
        if in_window(t, *self.rollover):
            return "Rollover harian (spread lebar)"
        return None
