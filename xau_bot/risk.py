"""Perhitungan lot & batas risiko harian/mingguan."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .config import RiskConfig
from .models import Account, ClosedTrade, SymbolSpec
from .sessions import trading_day, trading_week


def round_volume(volume: float, spec: SymbolSpec) -> float:
    steps = math.floor(volume / spec.volume_step + 1e-9)
    vol = round(steps * spec.volume_step, 8)
    return min(vol, spec.volume_max)


def money_per_price_unit(spec: SymbolSpec) -> float:
    """Nilai uang untuk pergerakan harga 1.00 pada 1 lot."""
    return spec.tick_value / spec.tick_size


def lot_size(balance: float, risk_pct: float, entry: float, sl: float, spec: SymbolSpec,
             allow_min_over_risk: bool = False) -> tuple[float, float, str]:
    """Return (lot, uang_yang_dirisikokan, pesan). lot 0 = jangan entry."""
    distance = abs(entry - sl)
    if distance <= 0:
        return 0.0, 0.0, "Jarak SL nol"
    risk_money = balance * risk_pct / 100.0
    per_lot = distance * money_per_price_unit(spec)
    raw = risk_money / per_lot
    vol = round_volume(raw, spec)
    if vol < spec.volume_min:
        min_risk = spec.volume_min * per_lot
        if allow_min_over_risk:
            return spec.volume_min, min_risk, f"Lot minimum dipakai (risiko {min_risk:.2f})"
        return 0.0, min_risk, (f"Lot minimum {spec.volume_min} berisiko {min_risk:.2f} "
                               f"> batas {risk_money:.2f}")
    return vol, vol * per_lot, ""


def split_volume(volume: float, ratio: float, spec: SymbolSpec) -> tuple[float, float]:
    """Bagi volume untuk TP1 (parsial) dan TP2. (0, vol) jika tidak bisa dibagi."""
    part = round_volume(volume * ratio, spec)
    rest = round(volume - part, 8)
    if part < spec.volume_min or rest < spec.volume_min:
        return 0.0, volume
    return part, rest


@dataclass
class RiskState:
    day_pnl: float
    week_pnl: float
    streak: int
    day_start_balance: float
    blocked: str | None


class RiskGuard:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg

    def evaluate(self, now: pd.Timestamp, account: Account, trades: list[ClosedTrade]) -> RiskState:
        today = trading_day(now)
        week = trading_week(now)
        todays = sorted((t for t in trades if trading_day(t.close_time) == today),
                        key=lambda t: t.close_time)
        day_pnl = sum(t.pnl for t in todays)
        week_pnl = sum(t.pnl for t in trades if trading_week(t.close_time) == week)
        # Satu setup bisa terdiri dari 2 posisi (TP1 & TP2) -> gabungkan per waktu buka.
        groups: dict[tuple, float] = {}
        for t in todays:
            opened = t.open_time.floor("1min") if t.open_time is not None else t.close_time
            key = (t.direction, opened)
            groups[key] = groups.get(key, 0.0) + t.pnl
        streak = 0
        for pnl in reversed(list(groups.values())):
            if pnl < 0:
                streak += 1
            else:
                break
        floating = account.equity - account.balance
        day_start = account.balance - day_pnl
        week_start = account.balance - week_pnl
        blocked = None
        if day_start > 0 and (day_pnl + min(floating, 0)) <= -self.cfg.daily_loss_pct / 100 * day_start:
            blocked = f"Batas rugi harian {self.cfg.daily_loss_pct}% tercapai"
        elif week_start > 0 and (week_pnl + min(floating, 0)) <= -self.cfg.weekly_loss_pct / 100 * week_start:
            blocked = f"Batas rugi mingguan {self.cfg.weekly_loss_pct}% tercapai"
        elif self.cfg.max_consecutive_losses and streak >= self.cfg.max_consecutive_losses:
            blocked = f"{streak}x SL beruntun hari ini, istirahat sampai besok"
        return RiskState(day_pnl, week_pnl, streak, day_start, blocked)
