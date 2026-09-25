"""Studi reaksi emas terhadap berita USD high-impact (python -m research.news_study).

Semua keputusan dibuat di CLOSE candle rilis (M15) -> tidak ada look-ahead.
Spread saat berita dibuat lebih lebar (0.60).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .data import resample
from .news_data import load_calendar
from .run_scan import DATA, dataset

NEWS_SPREAD = 0.60
MAIN = ["NFP", "CPI", "PPI", "FOMC", "RETAIL", "PCE", "GDP"]


def event_rows(df: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per waktu rilis (event bersamaan digabung)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, 14)
    idx = df.index
    rows = []
    cal = cal[cal["group"].isin(MAIN)]
    for t, g in cal.groupby("time"):
        i = idx.searchsorted(t, side="right") - 1          # bar yang memuat waktu rilis
        if i < 20 or i + 20 >= len(df) or not (idx[i] <= t < idx[i] + pd.Timedelta(minutes=15)):
            continue
        bias = g["gold_bias"].dropna()
        rows.append({
            "time": t, "i": i, "groups": ",".join(sorted(set(g["group"]))),
            "bias": float(np.sign(bias.sum())) if len(bias) else 0.0,
            "atr": a[i - 1],
            "pre4h": c[i - 1] - c[max(0, i - 17)],
            "first": c[i] - o[i],
            "first_range": h[i] - l[i],
            "next1h": c[min(i + 4, len(c) - 1)] - c[i],
            "next4h": c[min(i + 16, len(c) - 1)] - c[i],
        })
    return pd.DataFrame(rows)


def news_trade(df: pd.DataFrame, ev: pd.DataFrame, mode: str, tp_r: float | None,
               min_first_atr: float = 0.5, hold_bars: int = 8) -> pd.DataFrame:
    """Entry di close candle rilis. mode: follow (ikut candle pertama), fade (lawan),
    surprise (ikut arah kejutan data, hanya bila candle pertama searah)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sp = NEWS_SPREAD
    out = []
    for e in ev.itertuples():
        first_dir = np.sign(e.first)
        if first_dir == 0 or abs(e.first) < min_first_atr * e.atr:
            continue
        if mode == "follow":
            d = first_dir
        elif mode == "fade":
            d = -first_dir
        else:
            if e.bias == 0 or e.bias != first_dir:
                continue
            d = e.bias
        i = e.i
        entry = c[i] + (sp if d > 0 else 0.0)
        sl = l[i] if d > 0 else h[i] + sp          # SL di ekstrem candle rilis
        if mode == "fade":
            sl = entry - d * max(e.first_range, e.atr)
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + d * tp_r * risk if tp_r else None
        r = None
        for j in range(i + 1, min(i + 1 + hold_bars, len(c))):
            if (l[j] <= sl) if d > 0 else (h[j] + sp >= sl):
                r = -1.0
                break
            if tp is not None and ((h[j] >= tp) if d > 0 else (l[j] + sp <= tp)):
                r = tp_r
                break
        if r is None:
            j = min(i + hold_bars, len(c) - 1)
            r = ((c[j] - entry) if d > 0 else (entry - c[j] - sp)) / risk
        out.append((e.time, e.groups, d, r))
    return pd.DataFrame(out, columns=["time", "groups", "dir", "R"])


def _fmt(t: pd.DataFrame) -> str:
    if t.empty:
        return "n=0"
    r = t["R"].to_numpy()
    w, L = r[r > 0], r[r < 0]
    pf = w.sum() / -L.sum() if len(L) else float("inf")
    return f"n={len(r):3d} win={100 * len(w) / len(r):4.1f}% exp={r.mean():+.3f}R PF={pf:.2f}"


def main() -> None:
    cal = load_calendar(DATA)
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    sets = {
        "2012-17": resample(m15[m15.index < cut], "15min"),
        "2018-22": resample(m15[m15.index >= cut], "15min"),
        "2025-26": resample(m5[m5.index < pd.Timestamp("2026-01-31", tz="UTC")], "15min"),
    }
    evs = {k: event_rows(d, cal) for k, d in sets.items()}
    print("== Reaksi emas terhadap berita (NFP/CPI/PPI/FOMC/Retail/PCE/GDP) ==")
    for k, ev in evs.items():
        s = ev[ev["bias"] != 0]
        agree = (np.sign(s["first"]) == s["bias"]).mean() * 100
        cont1 = (np.sign(ev["next1h"]) == np.sign(ev["first"])).mean() * 100
        cont4 = (np.sign(ev["next4h"]) == np.sign(ev["first"])).mean() * 100
        pre = (np.sign(ev["pre4h"]) == np.sign(ev["first"])).mean() * 100
        print(f"{k}: {len(ev)} rilis | candle 15m pertama searah kejutan data: {agree:.1f}% | "
              f"berlanjut 1 jam: {cont1:.1f}% | 4 jam: {cont4:.1f}% | "
              f"arah 4 jam SEBELUM berita = arah reaksi: {pre:.1f}% | "
              f"range candle rilis {(ev['first_range'] / ev['atr']).median():.1f}x ATR normal")
    print("\n== Strategi scalping berita (entry setelah candle rilis 15m tertutup, spread 0.60) ==")
    for mode in ["follow", "fade", "surprise"]:
        for tp in [1.0, 2.0, None]:
            line = [f"{k}: {_fmt(news_trade(sets[k], ev, mode, tp))}" for k, ev in evs.items()]
            print(f"{mode:8s} TP {str(tp) + 'R' if tp else 'waktu 2 jam':11s} | " + " | ".join(line))


if __name__ == "__main__":
    main()
