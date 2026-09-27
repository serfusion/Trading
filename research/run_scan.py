"""python -m research.run_scan <dataset> <out.pkl> [key=value ...]  (override StrategyConfig)"""
import os
import sys
import time
from pathlib import Path

from xau_bot.config import AppConfig

from .data import load_m5_2020, load_m5_2025, load_m15_2012, load_parquet_utc, resample
from .scan import scan

DATA = Path(os.getenv("XAU_DATA_DIR", "data/research"))


def dataset(name):
    if name == "m5_2025":
        return load_m5_2025(DATA / "dineshelumalai007_xauusd-5m/gold_m5_historical.csv"), "M5", "H1", 0.25, {}
    if name == "m5_2020":
        return load_m5_2020(DATA / "ilahuerta-IA_backtrader-pullback-window-xauusd/data/XAUUSD_5m_5Yea.csv"), "M5", "H1", 0.25, {}
    if name == "m15_2012":
        return load_m15_2012(DATA / "ejtraderLabs_historical-data/XAUUSD"), "M15", "H4", 0.30, {}
    if name == "m5_2026_smt":
        xau = resample(load_parquet_utc(DATA / "Sai310421_xauusd-data/parquet/XAUUSD_M1_90d_20260526.parquet"), "5min")
        xag = load_parquet_utc(DATA / "Sai310421_xauusd-data/parquet/XAGUSD_M5_90d_20260526.parquet")
        return xau, "M5", "H1", 0.25, {"XAGUSD": (xag, 1)}
    raise SystemExit(f"dataset? {name}")


if __name__ == "__main__":
    name, out = sys.argv[1], sys.argv[2]
    df, tf, htf, spread, corr = dataset(name)
    cfg = AppConfig()
    cfg.strategy.entry_tf, cfg.strategy.bias_tf = tf, htf
    cfg.strategy.bars, cfg.strategy.htf_bars = 300, 200
    for kv in sys.argv[3:]:
        k, v = kv.split("=")
        cur = getattr(cfg.strategy, k)
        setattr(cfg.strategy, k, type(cur)(v))
    t0 = time.time()
    res = scan(df, cfg, spread, corr)
    res.attrs.update(dataset=name, spread=spread)
    res.to_pickle(out)
    print(f"{name}: {len(df)} bar, {len(res)} setup, {time.time() - t0:.0f} detik")
