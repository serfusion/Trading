"""Scan setup di seluruh histori memakai SmcStrategy yang sama dengan bot live.

Setiap bar t hanya melihat bar <= t (tanpa look-ahead). Diparalelkan per potongan.
"""
from __future__ import annotations

import copy
from multiprocessing import get_context

import numpy as np
import pandas as pd

from xau_bot.config import AppConfig
from xau_bot.sessions import SessionClock
from xau_bot.strategy import TF_MINUTES, MarketContext, SmcStrategy

from .data import resample

_G: dict = {}


def _worker(args):
    start, end = args
    cfg: AppConfig = _G["cfg"]
    df: pd.DataFrame = _G["df"]
    htf: pd.DataFrame = _G["htf"]
    corr: dict = _G["corr"]
    spread: float = _G["spread"]
    s = cfg.strategy
    strat = SmcStrategy(s, SessionClock(cfg.sessions))
    tf_delta = pd.Timedelta(minutes=TF_MINUTES[s.entry_tf])
    htf_delta = pd.Timedelta(minutes=TF_MINUTES[s.bias_tf])
    htf_open = htf.index
    out = []
    for t in range(start, end):
        close_time = df.index[t] + tf_delta
        window = df.iloc[max(0, t - s.bars + 1):t + 1]
        h_end = htf_open.searchsorted(close_time - htf_delta, side="right")
        h = htf.iloc[max(0, h_end - s.htf_bars):h_end]
        cctx = {}
        for sym, (cdf, c) in corr.items():
            c_end = cdf.index.searchsorted(close_time - tf_delta, side="right")
            cctx[sym] = (cdf.iloc[max(0, c_end - s.bars):c_end], c)
        for st in strat.evaluate(MarketContext(entry=window, htf=h, spread=spread, correlated=cctx)):
            row = {
                "t": t, "time": df.index[t], "key": st.key, "dir": int(st.direction),
                "entry": st.entry, "sl": st.sl, "tp1": st.tp1, "tp2": st.tp2, "score": st.score,
                "poi": st.poi_kind, "level": st.swept_level.kind, "rr": st.rr,
                "risk": st.risk, "kz": strat.sessions.killzone(df.index[t]) or "-",
            }
            row.update({f"c_{k}": v for k, v in st.components.items()})
            out.append(row)
    return out


def scan(df: pd.DataFrame, cfg: AppConfig, spread: float,
         correlated: dict[str, tuple[pd.DataFrame, int]] | None = None,
         workers: int = 4, chunks: int = 64) -> pd.DataFrame:
    cfg = copy.deepcopy(cfg)
    cfg.strategy.score_threshold = 0  # simpan semua kandidat; filter skor dilakukan saat analisis
    htf = resample(df, f"{TF_MINUTES[cfg.strategy.bias_tf]}min")
    _G.update(cfg=cfg, df=df, htf=htf, corr=correlated or {}, spread=spread)
    start = min(cfg.strategy.bars, len(df) - 1)
    edges = np.linspace(start, len(df), chunks + 1).astype(int)
    tasks = [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]
    with get_context("fork").Pool(workers) as pool:
        parts = pool.map(_worker, tasks)
    rows = [r for p in parts for r in p]
    res = pd.DataFrame(rows)
    if res.empty:
        return res
    return res.sort_values("t").drop_duplicates("key", keep="first").reset_index(drop=True)
