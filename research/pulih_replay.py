"""Putar ulang kode cloud ASLI cloud/api/_pulih.py jam demi jam (XAU H1 riset + BTC harian + harga koin per jam)
lalu bandingkan dengan research.xau_kripto (kejadian sama? hasil 48 jam sama?). python -m research.pulih_replay
"""
from __future__ import annotations

import functools
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud" / "api"))
import _core  # noqa: E402
import _pulih  # noqa: E402

from . import xau_kripto as X  # noqa: E402


class Mem:
    def __init__(self):
        self.s = {}

    def get_state(self):
        return self.s

    def save_state(self, d):
        self.s = d


class Pub:
    def __init__(self):
        self.ev = []

    def publish(self, ev, *a, **k):
        self.ev.append(ev)


def main() -> None:
    xau, cr = X.muat()
    _core.market_open = functools.lru_cache(maxsize=None)(_core.market_open)
    bars = [_core.Bar(t.to_pydatetime(), o, h, lo, c) for t, o, h, lo, c in
            zip(xau.index, xau.open, xau.high, xau.low, xau.close)]
    btc_d = cr.BTC.resample("D").last().dropna()
    btc_daily = {d.strftime("%Y-%m-%d"): float(v) for d, v in btc_d.items()}
    kol = [c for c in _pulih.KOIN if c in cr.columns]
    arr = cr[kol]
    mem, pub = Mem(), Pub()
    now_ref = {"t": None}

    def prices(koin):
        row = arr.loc[now_ref["t"]] if now_ref["t"] in arr.index else arr.iloc[arr.index.get_indexer([now_ref["t"]],
                                                                                                    method="ffill")[0]]
        return {c: float(row[c]) for c in koin if c in row and not np.isnan(row[c])}

    mulai = X.MULAI.to_pydatetime()
    idx = [i for i, b in enumerate(bars) if b.t >= mulai]
    for i in idx:
        # tick setelah candle i tutup (cron :02) — keputusan di close candle i, harga koin = close jam i
        now = bars[i].t + timedelta(hours=1, minutes=2)
        now_ref["t"] = pd.Timestamp(bars[i].t)
        _pulih.pulih_tick(now, bars[max(0, i - 2400):i + 2], mem, pub, lambda: btc_daily, prices)
    sig = [e for e in pub.ev if e["type"] == "pulih_signal"]
    cl = [e for e in pub.ev if e["type"] == "pulih_close"]
    # riset: kejadian + korelasi ≥ 0,2
    xd = xau.close.resample("D").last().pct_change()
    bd = cr.BTC.resample("D").last().pct_change()
    dd = pd.DataFrame({"x": xd, "b": bd}).dropna()
    corr = dd.x.rolling(60).corr(dd.b).shift(1)
    ev = X.kejadian(xau, _pulih.N, _pulih.K, _pulih.R)
    t = xau.index[ev]
    t = t[t >= X.MULAI]
    c = corr.reindex(t.normalize(), method="ffill").to_numpy()
    rs = set(t[c >= 0.2].strftime("%Y%m%d%H"))
    cs = {e["id"].split("-")[1] for e in sig}
    L = ["# Replay kode cloud _pulih.py vs riset (2018–2026)",
         f"riset (tanpa memblokir saat posisi terbuka) {len(rs)} kejadian | cloud sinyal {len(sig)} tutup {len(cl)}",
         f"sinyal cloud yang juga ada di riset: {len(cs & rs)} / {len(cs)}; riset yang tidak dikirim cloud: {len(rs - cs)} "
         "(sebagian karena posisi 48 jam sebelumnya masih terbuka)"]
    if cl:
        r = np.array([e["r_pct"] for e in cl])
        tt = pd.to_datetime([e["time"] for e in cl], utc=True)
        for per, m in (("LAMA", tt < X.SPLIT), ("BARU", tt >= X.SPLIT)):
            L.append(f"cloud {per}: n {m.sum()} naik {(r[m] > 0).mean() * 100:.0f}% rata {r[m].mean():+.2f}% "
                     f"terburuk {r[m].min():+.1f}%")
        per_th = pd.Series(r, index=tt).groupby(tt.year).agg(["size", "mean"])
        L.append("per tahun: " + " ".join(f"{y}:{v['mean']:+.1f}%({int(v['size'])})" for y, v in per_th.iterrows()))
    out = ROOT / "docs" / "eksternal" / "hasil_pulih_replay.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
