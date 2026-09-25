"""Scalping searah trend H1 + efek filter berita pada modul trend (python -m research.scalp).

Trend H1 (Donchian 55/20) menentukan arah: hanya BUY saat trend naik, SELL saat trend turun.
Entry scalping: breakout channel pendek di TF kecil searah trend, SL k x ATR, TP x R, keluar
paksa setelah `hold` bar. Semua keputusan di close bar (tanpa look-ahead).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .alt import donchian
from .data import resample
from .news_data import load_calendar
from .run_scan import DATA, dataset


def trend_state(h1: pd.DataFrame, n_entry=55, n_exit=20) -> pd.Series:
    """+1/-1/0 per bar H1 (diketahui di close bar tsb)."""
    h, l, c = (h1[k].to_numpy(float) for k in ("high", "low", "close"))
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    st = np.zeros(len(c))
    s = 0
    for i in range(len(c)):
        if s > 0 and c[i] < lo_x[i]:
            s = 0
        elif s < 0 and c[i] > hi_x[i]:
            s = 0
        if s == 0:
            if c[i] > hi_e[i]:
                s = 1
            elif c[i] < lo_e[i]:
                s = -1
        st[i] = s
    # berlaku mulai bar H1 berikutnya (close time)
    return pd.Series(st, index=h1.index + pd.Timedelta(hours=1))


def scalp(df: pd.DataFrame, tf_min: int, spread: float, chan: int, sl_atr: float, tp_r: float,
          hold: int, news_times: pd.DatetimeIndex | None = None, news_block_min: int = 30) -> pd.DataFrame:
    h1 = resample(df, "60min")
    state = trend_state(h1).reindex(df.index + pd.Timedelta(minutes=tf_min), method="ffill").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, 14)
    hi = pd.Series(h).rolling(chan).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(chan).min().shift(1).to_numpy()
    close_t = df.index + pd.Timedelta(minutes=tf_min)
    if news_times is not None and len(news_times):
        pos = news_times.searchsorted(close_t)
        nxt = news_times[np.minimum(pos, len(news_times) - 1)]
        prv = news_times[np.maximum(pos - 1, 0)]
        near = ((nxt - close_t) <= pd.Timedelta(minutes=news_block_min)) & (nxt >= close_t) | (
            (close_t - prv) <= pd.Timedelta(minutes=news_block_min)) & (prv <= close_t)
        near = np.asarray(near)
    else:
        near = np.zeros(len(df), bool)
    out = []
    i = chan + 20
    while i < len(df) - 1:
        d = state[i]
        if d == 0 or near[i] or np.isnan(hi[i]):
            i += 1
            continue
        if (d > 0 and c[i] > hi[i]) or (d < 0 and c[i] < lo[i]):
            entry = o[i + 1] + (spread if d > 0 else 0.0)
            risk = sl_atr * a[i]
            sl = entry - d * risk
            tp = entry + d * tp_r * risk
            r = None
            j = i + 1
            for j in range(i + 1, min(i + 1 + hold, len(df))):
                if (l[j] <= sl) if d > 0 else (h[j] + spread >= sl):
                    r = -1.0
                    break
                if j > i + 1 and ((h[j] >= tp) if d > 0 else (l[j] + spread <= tp)):
                    r = tp_r
                    break
            if r is None:
                r = ((c[j] - entry) if d > 0 else (entry - c[j] - spread)) / risk
            out.append((df.index[i], d, r))
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(out, columns=["time", "dir", "R"])


def _exp(t):
    return t["R"].mean() if len(t) else np.nan


def main() -> None:
    cal = load_calendar(DATA)
    tier = cal[cal["group"].isin(["NFP", "CPI", "PPI", "FOMC", "RETAIL", "PCE", "GDP"])]
    news_times = pd.DatetimeIndex(sorted(tier["time"].unique()))
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    sets = {"2012-17": (m15[m15.index < cut], 15, 0.30), "2018-22": (m15[m15.index >= cut], 15, 0.30),
            "2025-26 M15": (resample(m5, "15min"), 15, 0.25), "2025-26 M5": (m5, 5, 0.25)}

    print("== Efek berita pada modul TREND H1 (trade dibuka <= X jam dari rilis high-impact) ==")
    for k, (d, _, sp) in sets.items():
        if k.endswith("M5"):
            continue
        h1 = resample(d, "60min")
        t = donchian(h1, sp, 55, 20, 20, 3.0)
        ot = pd.DatetimeIndex(h1.index[t.i0])
        pos = news_times.searchsorted(ot)
        prv = news_times[np.maximum(pos - 1, 0)]
        nxt = news_times[np.minimum(pos, len(news_times) - 1)]
        dist = np.minimum(np.abs((ot - prv).total_seconds()), np.abs((nxt - ot).total_seconds())) / 3600
        near = np.asarray(dist <= 1.0)
        print(f"{k}: dekat berita (<=1 jam) n={near.sum()} exp={t.R[near].mean():+.3f}R | "
              f"jauh n={(~near).sum()} exp={t.R[~near].mean():+.3f}R | semua {t.R.mean():+.3f}R")

    print("\n== Scalping searah trend H1 (grid pra-daftar, hold 16 bar) ==")
    rows = []
    for chan, sl_atr, tp_r in itertools.product([10, 20], [1.0, 1.5, 2.0], [1.0, 1.5, 2.0]):
        row = {"chan": chan, "sl_atr": sl_atr, "tp_r": tp_r}
        for k, (d, tfm, sp) in sets.items():
            t = scalp(d, tfm, sp, chan, sl_atr, tp_r, 16)
            row[k] = _exp(t)
            row["n " + k] = len(t)
        rows.append(row)
    r = pd.DataFrame(rows)
    cols = ["2012-17", "2018-22", "2025-26 M15", "2025-26 M5"]
    print(r[["chan", "sl_atr", "tp_r", "n 2012-17"] + cols].round(3).to_string(index=False))
    allpos = (r[cols] > 0).all(axis=1)
    print(f"Varian positif di SEMUA periode: {allpos.sum()} dari {len(r)}")
    best = r.sort_values("2012-17", ascending=False).iloc[0]
    print(f"Terbaik menurut 2012-17 saja: chan {best.chan} SL {best.sl_atr}ATR TP {best.tp_r}R -> "
          + ", ".join(f"{k} {best[k]:+.3f}R" for k in cols))
    print("\nDengan filter berita (+-30 menit), varian terbaik tadi:")
    line = []
    for k, (d, tfm, sp) in sets.items():
        line.append(f"{k} {_exp(scalp(d, tfm, sp, int(best.chan), best.sl_atr, best.tp_r, 16, news_times)):+.3f}R")
    print("  " + ", ".join(line))


if __name__ == "__main__":
    main()
