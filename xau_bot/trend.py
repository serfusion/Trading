"""Modul trend-following (Donchian / time-series momentum) yang tervalidasi di data historis.

Aturan (dievaluasi setiap bar `timeframe` tertutup):
- BUY  bila close > high tertinggi `entry_period` bar sebelumnya.
- SELL bila close < low terendah `entry_period` bar sebelumnya.
- SL awal = entry -/+ `stop_atr` x ATR(`atr_period`), tanpa TP.
- Keluar bila close menembus channel `exit_period` bar berlawanan (trailing alami).

Riset (docs/BACKTEST.md): H1 55/20/3xATR positif di 2012-2017, 2018-2022 dan
2025-2026; 75 dari 76 varian parameter di sekitarnya juga positif.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import TrendConfig
from .models import Direction
from .smc import atr


@dataclass
class TrendSignal:
    action: str                  # "open" | "close" | "none"
    direction: Direction | None
    atr: float
    level: float
    note: str


class TrendStrategy:
    def __init__(self, cfg: TrendConfig):
        self.cfg = cfg
        self.state = "-"

    def evaluate(self, bars: pd.DataFrame, position: Direction | None) -> TrendSignal:
        cfg = self.cfg
        need = max(cfg.entry_period, cfg.exit_period, cfg.atr_period) + 2
        if len(bars) < need:
            self.state = "Data belum cukup"
            return TrendSignal("none", None, 0.0, 0.0, self.state)
        h = bars["high"].to_numpy(float)
        l = bars["low"].to_numpy(float)
        c = bars["close"].to_numpy(float)
        a = float(atr(bars, cfg.atr_period)[-1])
        hi_e = h[-cfg.entry_period - 1:-1].max()
        lo_e = l[-cfg.entry_period - 1:-1].min()
        hi_x = h[-cfg.exit_period - 1:-1].max()
        lo_x = l[-cfg.exit_period - 1:-1].min()
        last = c[-1]
        self.state = (f"close {last:.2f} | channel {cfg.entry_period}: {lo_e:.2f}-{hi_e:.2f} | "
                      f"exit {cfg.exit_period}: {lo_x:.2f}-{hi_x:.2f} | ATR {a:.2f}")
        if position == Direction.BUY and last < lo_x:
            return TrendSignal("close", Direction.BUY, a, lo_x,
                               f"Close {last:.2f} < low {cfg.exit_period} bar {lo_x:.2f}")
        if position == Direction.SELL and last > hi_x:
            return TrendSignal("close", Direction.SELL, a, hi_x,
                               f"Close {last:.2f} > high {cfg.exit_period} bar {hi_x:.2f}")
        if position is None:
            if last > hi_e:
                return TrendSignal("open", Direction.BUY, a, hi_e,
                                   f"Breakout {cfg.timeframe}: close {last:.2f} > high {cfg.entry_period} bar {hi_e:.2f}")
            if last < lo_e:
                return TrendSignal("open", Direction.SELL, a, lo_e,
                                   f"Breakdown {cfg.timeframe}: close {last:.2f} < low {cfg.entry_period} bar {lo_e:.2f}")
        return TrendSignal("none", position, a, 0.0, "Tidak ada sinyal")
