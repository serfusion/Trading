"""Backtest memakai jalur kode yang SAMA dengan live (Engine + PaperBroker).

Keterbatasan: kalender berita historis tidak tersedia (filter berita dimatikan),
spread dibuat tetap, dan urutan harga di dalam satu bar diasumsikan konservatif.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .broker.paper import PaperBroker
from .config import AppConfig
from .engine import Engine
from .journal import Journal
from .models import SymbolSpec
from .news import NewsFilter
from .telegram import Notifier

XAU_SPEC = SymbolSpec(name="XAUUSD", digits=2, point=0.01, tick_size=0.01, tick_value=1.0,
                      volume_min=0.01, volume_max=200.0, volume_step=0.01, stops_level=0,
                      contract_size=100.0)


class _Silent(Notifier):
    def send(self, text: str) -> None:
        return None


def load_csv(path: str) -> pd.DataFrame:
    """CSV umum (time,open,high,low,close) atau ekspor MT5 (<DATE> <TIME> <OPEN>...)."""
    with open(path, encoding="utf-8-sig") as fh:
        first = fh.readline()
    sep = "\t" if "\t" in first else ","
    df = pd.read_csv(path, sep=sep)
    df.columns = [c.strip("<>").strip().lower() for c in df.columns]
    if "date" in df.columns and "time" in df.columns:
        stamp = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    else:
        col = "time" if "time" in df.columns else df.columns[0]
        stamp = pd.to_datetime(df[col])
    stamp = pd.DatetimeIndex(stamp)
    stamp = stamp.tz_localize("UTC") if stamp.tz is None else stamp.tz_convert("UTC")
    out = df[["open", "high", "low", "close"]].astype(float)
    out.index = stamp
    return out[~out.index.duplicated()].sort_index()


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    setups: pd.DataFrame
    start_balance: float
    end_balance: float

    def summary(self) -> str:
        t = self.trades
        lines = [f"Saldo: {self.start_balance:.2f} -> {self.end_balance:.2f} "
                 f"({(self.end_balance / self.start_balance - 1) * 100:+.2f}%)"]
        if t.empty:
            lines.append("Tidak ada trade.")
        else:
            grp = t.groupby(["direction", t["open_time"].dt.floor("1min")])["pnl"].sum()
            wins, losses = grp[grp > 0], grp[grp < 0]
            pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
            equity = self.start_balance + t.sort_values("close_time")["pnl"].cumsum()
            peak = np.maximum.accumulate(np.r_[self.start_balance, equity.to_numpy()])
            dd = ((np.r_[self.start_balance, equity.to_numpy()] - peak) / peak).min() * 100
            lines += [
                f"Setup dieksekusi: {len(grp)} | menang {len(wins)} | kalah {len(losses)} | "
                f"win-rate {len(wins) / len(grp) * 100:.1f}%",
                f"Profit factor: {pf:.2f} | rata-rata menang {wins.mean() if len(wins) else 0:.2f} | "
                f"rata-rata kalah {losses.mean() if len(losses) else 0:.2f}",
                f"Max drawdown: {dd:.2f}%",
            ]
        if not self.setups.empty:
            counts = self.setups["status"].value_counts().to_dict()
            lines.append(f"Status setup: {counts}")
            skipped = self.setups[self.setups["status"] == "skipped"]["note"].value_counts().head(5)
            for note, n in skipped.items():
                lines.append(f"  dilewati {n}x: {note}")
        return "\n".join(lines)


def run_backtest(cfg: AppConfig, entry: pd.DataFrame, correlated: dict[str, pd.DataFrame] | None = None,
                 spread: float = 0.20, balance: float = 1000.0, spec: SymbolSpec = XAU_SPEC,
                 progress: bool = False) -> BacktestResult:
    cfg = copy.deepcopy(cfg)
    cfg.news.enabled = False
    cfg.telegram.enabled = False
    cfg.poll_seconds = 0
    logging.getLogger("xau_bot").setLevel(logging.WARNING)
    data = {cfg.broker.symbol: entry}
    for sym, df in (correlated or {}).items():
        data[sym] = df
    warmup = min(cfg.strategy.bars, len(entry) - 1)
    broker = PaperBroker(data, cfg.strategy.entry_tf, spec, spread, balance, start_index=warmup)
    journal = Journal(":memory:")
    engine = Engine(cfg, broker, _Silent(), NewsFilter(cfg.news), journal, clock=lambda: broker.now)
    engine.start()
    total = len(entry)
    while broker.advance():
        bar = broker.data[broker.main].iloc[broker.cursor]
        engine.step(price_range=(float(bar["low"]), float(bar["high"])))
        if progress and broker.cursor % 2000 == 0:
            print(f"  ... {broker.cursor}/{total} bar, saldo {broker.balance:.2f}")
    trades = pd.DataFrame([{**t.__dict__, "direction": t.direction.label if t.direction else "-"}
                           for t in broker.closed])
    setups = pd.read_sql_query("SELECT * FROM setups ORDER BY created", journal.db)
    return BacktestResult(trades, setups, balance, broker.balance)
