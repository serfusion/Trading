"""Skema F vs A lewat Engine + PaperBroker (kode yang sama dengan live), risiko 0,5% per set.

python -m research.engine_ab <dataset> <F|A> [--from YYYY-MM-DD] [--to YYYY-MM-DD]
Skema A tanpa mengubah kode: tp1_r sangat besar -> TP1/SL+ tidak pernah tersentuh, semua posisi hold
sampai sinyal TUTUP atau SL. HANYA untuk PaperBroker: di broker sungguhan TP SELL bisa negatif dan ditolak.
"""
import argparse
import shutil
import time

import pandas as pd

from xau_bot.backtest import run_backtest
from xau_bot.config import AppConfig

from .data import resample
from .run_scan import dataset

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("scheme", choices=["F", "A"])
    ap.add_argument("--from", dest="f")
    ap.add_argument("--to", dest="t")
    ap.add_argument("--risk", type=float, default=0.5)
    a = ap.parse_args()
    df, tf, _, spread, _ = dataset(a.name)
    if tf == "M5":
        df, tf = resample(df, "15min"), "M15"
    if a.f:
        df = df[df.index >= pd.Timestamp(a.f, tz="UTC")]
    if a.t:
        df = df[df.index < pd.Timestamp(a.t, tz="UTC")]
    cfg = AppConfig()
    cfg.strategy.mode, cfg.strategy.entry_tf, cfg.strategy.bars = "trend", tf, 60
    cfg.strategy.smt_symbols = []
    cfg.trend.risk_pct_per_set = a.risk
    if a.scheme == "A":
        cfg.trend.tp1_r = 1000.0
    cfg.trend.state_dir = f"/tmp/xau_ab_{a.name}_{a.scheme}_{a.f}_{a.t}_{a.risk}"
    shutil.rmtree(cfg.trend.state_dir, ignore_errors=True)
    cfg.risk.max_spread = 5.0
    t0 = time.time()
    res = run_backtest(cfg, df, spread=spread, balance=10_000)
    t = res.trades
    yearly = t.groupby(t["close_time"].dt.year)["pnl"].sum().round(0) if not t.empty else pd.Series(dtype=float)
    print(f"{a.scheme} {a.name} {df.index[0]:%Y-%m} -> {df.index[-1]:%Y-%m} ({time.time() - t0:.0f} dtk)")
    print(res.summary())
    print("PnL per tahun:", yearly.to_dict(), f"| tahun positif {(yearly > 0).sum()} dari {len(yearly)}")
