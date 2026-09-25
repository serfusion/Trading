"""UJIAN: bot sinyal dijalankan candle demi candle, masa depan TERTUTUP.

Setiap sinyal = soal (dibuat hanya dari candle yang sudah terlihat). Saat bot mengirim sinyal
TUTUP, kunci jawaban dibuka: BENAR bila hasil > 0, SALAH bila < 0.
Memakai Engine yang sama dengan yang mengirim sinyal ke aplikasi Android (mode SINYAL).

python -m research.exam m15_2012 [--from 2018-01-01] [--to ...] [--show 10]
"""
from __future__ import annotations

import argparse
import copy
import logging
import tempfile

import pandas as pd

from xau_bot.backtest import XAU_SPEC
from xau_bot.broker.paper import PaperBroker
from xau_bot.config import AppConfig
from xau_bot.engine import Engine
from xau_bot.journal import Journal
from xau_bot.news import NewsFilter
from xau_bot.publish import Publisher
from xau_bot.telegram import Notifier

from .data import resample
from .run_scan import dataset


class Recorder(Publisher):
    def __init__(self):
        self.events: list[dict] = []

    def publish(self, event, text=None, title=None, priority=3, tags=None):
        if event.get("type") in ("signal", "close"):
            self.events.append(event)


def run_exam(df: pd.DataFrame, base_tf: str, spread: float, cfg: AppConfig | None = None) -> pd.DataFrame:
    cfg = copy.deepcopy(cfg or AppConfig())
    cfg.trade_enabled = False
    cfg.news.enabled = False
    cfg.telegram.enabled = False
    cfg.strategy.mode = "trend"
    cfg.strategy.entry_tf = base_tf
    cfg.strategy.bars = 60
    cfg.risk.max_spread = 5.0
    cfg.trend.virtual_file = tempfile.mktemp(suffix=".json")
    logging.getLogger("xau_bot").setLevel(logging.WARNING)
    broker = PaperBroker({cfg.broker.symbol: df}, base_tf, XAU_SPEC, spread=spread, balance=1e9,
                         start_index=min(60, len(df) - 1))
    rec = Recorder()
    engine = Engine(cfg, broker, Notifier(), NewsFilter(cfg.news), Journal(":memory:"),
                    clock=lambda: broker.now, publisher=rec)
    engine.log = lambda *a, **k: None  # senyap
    engine.start()
    while broker.advance():
        bar = broker.data[broker.main].iloc[broker.cursor]
        engine.step(price_range=(float(bar["low"]), float(bar["high"])))
    sig = {e["id"]: e for e in rec.events if e["type"] == "signal" and e.get("status") == "signal"}
    rows = []
    for e in rec.events:
        if e["type"] == "close" and e.get("id") in sig:
            s = sig[e["id"]]
            rows.append({"soal": s["time"], "arah": s["dir"], "entry": s["entry"], "sl": s["sl"],
                         "jawaban": e["time"], "keluar": e["price"], "poin": e["points"], "R": e["r"],
                         "alasan_tutup": e["reason"]})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--from", dest="f")
    ap.add_argument("--to", dest="t")
    ap.add_argument("--show", type=int, default=8)
    a = ap.parse_args()
    df, tf, _, spread, _ = dataset(a.name)
    if tf == "M5":
        df = resample(df, "15min")
    if a.f:
        df = df[df.index >= pd.Timestamp(a.f, tz="UTC")]
    if a.t:
        df = df[df.index < pd.Timestamp(a.t, tz="UTC")]
    ex = run_exam(df, "M15", spread)
    if ex.empty:
        print("Tidak ada soal.")
        return
    benar = (ex["R"] > 0).sum()
    print(f"UJIAN {a.name} {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d} ({len(df)} candle M15, masa depan tertutup)")
    print(f"Soal (sinyal): {len(ex)} | BENAR (profit): {benar} ({benar / len(ex) * 100:.1f}%) | "
          f"SALAH (rugi): {len(ex) - benar}")
    print(f"Nilai total: {ex['R'].sum():+.1f}R | rata-rata per soal {ex['R'].mean():+.3f}R | "
          f"rata-rata benar {ex.R[ex.R > 0].mean():+.2f}R vs salah {ex.R[ex.R <= 0].mean():+.2f}R")
    yearly = ex.groupby(ex["soal"].dt.year)["R"].sum().round(1)
    print("Nilai per tahun (R):", yearly.to_dict())
    pd.set_option("display.width", 200)
    print(f"\n{a.show} soal terakhir:")
    show = ex.tail(a.show).copy()
    show["soal"] = show["soal"].dt.tz_convert("Asia/Jakarta").dt.strftime("%d %b %Y %H:%M WIB")
    show["jawaban"] = show["jawaban"].dt.tz_convert("Asia/Jakarta").dt.strftime("%d %b %H:%M")
    show["hasil"] = ["BENAR" if r > 0 else "SALAH" for r in show["R"]]
    print(show[["soal", "arah", "entry", "sl", "jawaban", "keluar", "poin", "R", "hasil"]].to_string(index=False))


if __name__ == "__main__":
    main()
