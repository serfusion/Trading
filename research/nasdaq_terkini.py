"""Nasdaq 100 (USTEC) dengan data terbaru: 31 metode populer + sistem sinyal kita (python -m research.nasdaq_terkini).

Pertanyaan pengguna (29 Sep 2026): profit 4 posisi SELL USTEC dalam 45 menit — "sepertinya mudah sekali, sudah diuji
semua pair dengan metode populer?". Uji lama (docs/UJI_DUNIA.md, docs/MULTI_ASET.md) memakai Nasdaq OANDA 2008–2020;
di sini diulang dengan data Nasdaq futures (Yahoo NQ=F, H1, ±2 tahun terakhir — batas data jam gratis).

Aturan sama dengan research/world_lab.py: sinyal di close H1 → entry open berikutnya + spread, SL dicek dulu,
parameter terbaik dipilih di tahun pertama (latih) lalu dinilai di tahun kedua (uji). Spread 2 poin (± akun Standard).
Catatan: futures ≠ CFD USTEC persis (selisih basis & jam), dan 2 tahun itu pendek — hasil hanya gambaran.
"""
from __future__ import annotations

import json
import urllib.request

import numpy as np
import pandas as pd

from .strategy_lab import Bars
from .strategy_lab2 import backtest_f, signals
from .world_lab import METHODS, Ctx, backtest, summarize

SPREAD = 2.0


def load(symbol: str = "NQ=F") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.replace('=', '%3D')}?interval=1h&range=730d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime(r["timestamp"], unit="s", utc=True)).dropna()
    df.index = df.index.floor("h")
    df = df[~df.index.duplicated(keep="last")]
    return df[df.high > df.low]


def main() -> None:
    h1 = load()
    split = h1.index[0] + (h1.index[-1] - h1.index[0]) / 2
    print(f"NQ=F H1 {h1.index[0]:%Y-%m-%d} .. {h1.index[-1]:%Y-%m-%d}, {len(h1)} candle; latih < {split:%Y-%m-%d}")
    x = Ctx(h1, SPREAD)
    rows = []
    for meth, (fn, grid) in METHODS.items():
        best = None
        for p in grid:
            try:
                sig = fn(x, **p)
            except Exception:  # noqa: BLE001 - metode yang butuh data lebih panjang dilewati
                continue
            li, si, lo, so, sl = sig[:5]
            mh = sig[6] if len(sig) > 6 else None
            for tp in (None, 1.0, 2.0):
                tr = backtest(x.b, np.asarray(li, bool), np.asarray(si, bool), np.asarray(lo, bool),
                              np.asarray(so, bool), sl, tp, mh)
                dev = [t for t in tr if t[0] < split]
                tst = [t for t in tr if t[0] >= split]
                sd = summarize(dev)
                if sd["n"] >= 15 and (best is None or sd["t"] > best[1]["t"]):
                    best = ({**p, "tp": tp}, sd, summarize(tst))
        if best:
            rows.append((meth, best[0], best[1], best[2]))
    print(f"\n{'Metode':22s} {'latih: n  win   R/trade  t':>30s} | {'uji: n  win   R/trade  t':>28s}")
    for meth, p, a, b in sorted(rows, key=lambda r: -r[3]["avg"]):
        print(f"{meth:22s} {a['n']:5d} {a['win']:5.0f}% {a['avg']:+8.3f} {a['t']:+5.1f} | "
              f"{b['n']:5d} {b['win']:5.0f}% {b['avg']:+8.3f} {b['t']:+5.1f}  {p}")
    both = [r for r in rows if r[2]["avg"] > 0 and r[3]["avg"] > 0 and r[2]["t"] > 2 and r[3]["t"] > 2]
    print(f"\nMeyakinkan (t>2) di latih DAN uji: {', '.join(r[0] for r in both) or 'tidak ada'}")
    pos = [r for r in rows if r[3]["avg"] > 0]
    print(f"Untung di periode uji: {len(pos)} dari {len(rows)} metode")

    # sistem sinyal kita: F-ensemble 3 set Donchian H1, SL 3xATR, 5 posisi, TP1 1R + SL+
    b = Bars(h1, SPREAD)
    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest_f(b, li, si, lo, so, 3.0, 5, 1.0, None)
    r = pd.Series([t[2] for t in tr], index=pd.DatetimeIndex([t[0] for t in tr]))
    for tag, m in (("semua", r), ("latih", r[r.index < split]), ("uji", r[r.index >= split])):
        print(f"Sistem kita (F-ensemble) {tag:5s}: n={len(m)} WR={100 * (m > 0).mean():.0f}% "
              f"rata={m.mean():+.3f}R total={m.sum():+.1f}R")


if __name__ == "__main__":
    main()
