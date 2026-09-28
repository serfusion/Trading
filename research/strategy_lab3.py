"""Tahap 3: gabungan filter & metode dalam satu akun, jendela sama 2021 - Sep 2026 (python -m research.strategy_lab3).

Stabilitas diukur per bulan & per kuartal (risiko 0,5% per sinyal, tanpa bunga majemuk).
"""
from __future__ import annotations

import warnings

import pandas as pd

from .filters import features
from .gap_study import week_info
from .strategy_lab import Bars, markets, stats
from .strategy_lab2 import STAR, backtest_f, signals, trend_states

warnings.filterwarnings("ignore", category=UserWarning)
START = pd.Timestamp("2021-01-01", tz="UTC")


def run(b, method, filt, scheme="F"):
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))

    def conf(i, d):
        return s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d

    def allow(i, d):
        if since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        return {"-": True, "⭐": star, "konf": conf(i, d), "⭐ dan konf": star and conf(i, d),
                "⭐ atau konf": star or conf(i, d)}[filt]
    tr = []
    for li, si, lo, so in signals(b, method):
        tr += backtest_f(b, li, si, lo, so, 3.0, 5, 1.0 if scheme == "F" else None, allow)
    return sorted(x for x in tr if x[0] >= START)


def report(name, tr, risk=0.005):
    s = stats(tr)
    r = pd.Series([x[2] * risk * 100 for x in tr], index=pd.DatetimeIndex([x[1] for x in tr]).tz_localize(None))
    mon = r.resample("MS").sum()
    q = r.resample("QS").sum()
    yr = r.resample("YS").sum()
    eq = mon.cumsum()
    dd = (eq - eq.cummax()).min()
    print(f"  {name:48s} n={s['n']:4d} win={s['win']:4.1f}% rata={s['avg']:+.3f}R | total {r.sum():+6.1f}% "
          f"DD {dd:6.1f}% | bulan+ {(mon > 0).mean() * 100:3.0f}% kuartal+ {(q > 0).mean() * 100:3.0f}% "
          f"tahun+ {(yr > 0).mean() * 100:3.0f}% | bulan terburuk {mon.min():+.1f}%")


def main():
    bars = {m.name: Bars(m.h1, m.spread) for m in markets() if m.name in ("XAUUSD", "BTCUSD")}
    res = {}
    for sym, b in bars.items():
        for method in ("donchian", "supertrend", "ema"):
            for filt in ("-", "⭐", "konf", "⭐ dan konf", "⭐ atau konf"):
                res[(sym, method, filt)] = run(b, method, filt)
    print("Per instrumen (Donchian 3 set, skema F), 2021 - Sep 2026")
    for sym in bars:
        for filt in ("-", "⭐", "konf", "⭐ dan konf", "⭐ atau konf"):
            report(f"{sym} donchian filter {filt}", res[(sym, "donchian", filt)])
    print("\nSatu akun XAU + BTC")
    plans = {
        "SEKARANG: donchian ⭐ (XAU & BTC)": [("XAUUSD", "donchian", "⭐"), ("BTCUSD", "donchian", "⭐")],
        "donchian tanpa filter": [("XAUUSD", "donchian", "-"), ("BTCUSD", "donchian", "-")],
        "donchian konf (XAU) + ⭐ (BTC)": [("XAUUSD", "donchian", "konf"), ("BTCUSD", "donchian", "⭐")],
        "donchian ⭐ dan konf": [("XAUUSD", "donchian", "⭐ dan konf"), ("BTCUSD", "donchian", "⭐ dan konf")],
        "donchian ⭐ atau konf": [("XAUUSD", "donchian", "⭐ atau konf"), ("BTCUSD", "donchian", "⭐ atau konf")],
        "multi-metode: donchian ⭐ + supertrend konf + ema -": [
            ("XAUUSD", "donchian", "⭐"), ("BTCUSD", "donchian", "⭐"), ("XAUUSD", "supertrend", "konf"),
            ("BTCUSD", "supertrend", "konf"), ("XAUUSD", "ema", "-"), ("BTCUSD", "ema", "-")],
    }
    for name, keys in plans.items():
        report(name, sorted(sum((res[k] for k in keys), [])))


if __name__ == "__main__":
    main()
