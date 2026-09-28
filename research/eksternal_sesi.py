"""(4) Filter sesi + data Dukascopy BID/ASK (python -m research.eksternal_sesi).

Bagian A — filter sesi pada sinyal 💰 (jam keputusan UTC = open candle entry). Varian (ditetapkan sebelum melihat
hasil): lewati Asia (22-07 UTC), hanya London+NY (07-21), lewati sore NY (16-21), lewati 2 jam setelah buka harian
(22-00 UTC), hanya tumpang tindih London-NY (12-16).

Bagian B — data kedua dari Dukascopy (research/dukascopy.py, H1 BID & ASK 2012-2026):
- spread nyata per jam (ASK open - BID open) -> apakah jam tertentu terlalu mahal?
- mesin yang sama dijalankan di data Dukascopy dengan spread per candle dari ASK-BID -> apakah statistik 💰
  (konf+⭐ +0,31R, konf +0,09R) bertahan di sumber data lain dan biaya spread nyata?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import SPLIT, Asset, _categorized, asset, fmt_judge, judge, per_year
from .strategy_lab import Bars

SESSIONS = {
    "lewati Asia (22-07 UTC)": lambda h: ~((h >= 22) | (h < 7)),
    "hanya London+NY (07-21 UTC)": lambda h: (h >= 7) & (h < 21),
    "lewati sore NY (16-21 UTC)": lambda h: ~((h >= 16) & (h < 21)),
    "lewati 2 jam setelah buka harian (22-00)": lambda h: ~((h >= 22) & (h < 24)),
    "hanya tumpang tindih London-NY (12-16)": lambda h: (h >= 12) & (h < 16),
}


def variants(sig: pd.DataFrame) -> dict[str, np.ndarray]:
    h = sig.t.dt.hour.to_numpy()
    return {k: np.asarray(f(h), bool) for k, f in SESSIONS.items()}


def by_hour(sig: pd.DataFrame) -> str:
    g = sig.groupby(sig.t.dt.hour).R
    return " ".join(f"{h:02d}:{m:+.2f}({n})" for h, m, n in zip(g.mean().index, g.mean(), g.size()))


def part_a() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            print(f"\n=== {name} — {label}: {len(sig)} sinyal (latih < {a.split:%Y}) — lolos/dibuang [dasar] ===")
            print("R rata-rata per jam keputusan (UTC):", by_hour(sig))
            vs = variants(sig)
            res = {k: judge(sig, v, a.split) for k, v in vs.items()}
            for k, j in res.items():
                print(fmt_judge(k, j))
            if label == "💰 dikirim":
                best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
                print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")


def dukascopy_h1() -> tuple[pd.DataFrame, np.ndarray]:
    from .dukascopy import load
    bid, ask = load("XAUUSD", "h1")
    bid = bid[(bid.high > bid.low)]
    ask = ask.reindex(bid.index)
    sp = (ask.open - bid.open).to_numpy()
    return bid[["open", "high", "low", "close"]], np.where(sp > 0, sp, np.nan)      # NaN = ASK belum ada


def part_b() -> None:
    bid, sp = dukascopy_h1()
    keep = bid.index >= pd.Timestamp("2012-11-15", tz="UTC")
    bid, sp = bid[keep], sp[keep]
    s = pd.Series(sp, index=bid.index).dropna()                       # hanya spread nyata
    sp = np.where(np.isfinite(sp), sp, 0.30)                          # ASK tidak ada -> 0,30 (sama dgn riset lain)
    ref = asset("XAUUSD").b.df
    both = bid.index.intersection(ref.index)
    d = (bid.close.reindex(both) - ref.close.reindex(both)).abs()
    print(f"Selisih close Dukascopy vs data riset: median ${d.median():.2f}, p95 ${d.quantile(0.95):.2f} "
          f"({len(both)} candle sama)")
    print(f"\nDukascopy XAUUSD H1: {len(bid)} candle {bid.index[0]:%Y-%m-%d} .. {bid.index[-1]:%Y-%m-%d}")
    print("Spread median ASK-BID per tahun ($):", " ".join(
        f"{y % 100:02d}:{v:.2f}" for y, v in s.groupby(s.index.year).median().items()))
    hh = s[s.index.year >= 2024].groupby(s.index[s.index.year >= 2024].hour).median()
    print("Spread median per jam UTC 2024-26 ($):", " ".join(f"{h:02d}:{v:.2f}" for h, v in hh.items()))
    for label, spread in (("spread tetap 0,30", 0.30), ("spread nyata per candle", None)):
        b = Bars(bid, 0.30)
        if spread is None:
            b.sp = sp.copy()
        a = Asset("XAUUSD", b, _categorized(b, True), SPLIT["XAUUSD"])
        g = a.sig.groupby("cat").R
        print(f"\n[{label}] per kategori: " + " | ".join(
            f"{c} n={n} WR={100 * w:.0f}% rata={m:+.3f}R" for c, n, w, m in
            zip(g.size().index, g.size(), g.apply(lambda v: (v > 0).mean()), g.mean())))
        m = a.money
        lt, ut = m[m.t < a.split], m[m.t >= a.split]
        yr = m.groupby(m.t.dt.year).R.sum()
        print(f"  💰: n={len(m)} rata={m.R.mean():+.3f}R total={m.R.sum():+.1f}R | latih {lt.R.mean():+.3f}R uji "
              f"{ut.R.mean():+.3f}R | tahun untung {(yr > 0).sum()}/{len(yr)}")
        if spread is None:
            vs = variants(m)
            for k, v in vs.items():
                print(fmt_judge(k, judge(m, v, a.split)))


def main() -> None:
    part_a()
    try:
        part_b()
    except FileNotFoundError:
        print("\n(Bagian B dilewati: jalankan dulu python -m research.dukascopy h1 2012-01 2026-09)")


if __name__ == "__main__":
    main()
