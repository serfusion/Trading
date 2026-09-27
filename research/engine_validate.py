"""Validasi modul TREND lewat Engine + PaperBroker (jalur kode yang sama dengan live).

python -m research.engine_validate <dataset> [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--balance N]
"""
import argparse
import time

import pandas as pd

from xau_bot.backtest import run_backtest
from xau_bot.config import AppConfig

from .data import resample
from .run_scan import dataset

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--from", dest="f")
    ap.add_argument("--to", dest="t")
    ap.add_argument("--balance", type=float, default=10_000)
    ap.add_argument("--risk", type=float, default=1.0)
    ap.add_argument("--spread", type=float)
    ap.add_argument("--no-bias", action="store_true", help="matikan filter bias struktur H4")
    a = ap.parse_args()
    df, tf, _, spread, _ = dataset(a.name)
    if tf == "M5":
        df, tf = resample(df, "15min"), "M15"   # trend H1 cukup dengan bar dasar M15
    if a.f:
        df = df[df.index >= pd.Timestamp(a.f, tz="UTC")]
    if a.t:
        df = df[df.index < pd.Timestamp(a.t, tz="UTC")]
    cfg = AppConfig()
    cfg.strategy.mode = "trend"
    cfg.strategy.entry_tf = tf
    cfg.strategy.bars = 60
    cfg.risk.risk_pct = a.risk
    cfg.trend.risk_pct_per_set = a.risk
    cfg.trend.bias_filter = not a.no_bias
    cfg.trend.state_dir = (f"/tmp/xau_state_{a.name}_{a.f or ''}_{a.t or ''}_r{a.risk}"
                           + ("_nb" if a.no_bias else ""))
    import shutil; shutil.rmtree(cfg.trend.state_dir, ignore_errors=True)
    cfg.risk.max_spread = 5.0
    t0 = time.time()
    res = run_backtest(cfg, df, spread=a.spread or spread, balance=a.balance)
    print(f"{a.name} {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d} | {len(df)} bar | {time.time() - t0:.0f} dtk")
    print(res.summary())
    t = res.trades
    if not t.empty:
        eq = a.balance + t.sort_values("close_time")["pnl"].cumsum()
        yearly = t.groupby(t["close_time"].dt.year)["pnl"].sum().round(0)
        print("PnL per tahun:", yearly.to_dict())
        print(f"Tahun positif: {(yearly > 0).sum()} dari {len(yearly)}")
