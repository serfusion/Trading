"""Gabungan "terbaik dari yang terbaik" (python -m research.combine [out.pkl]).

Satu-satunya keluarga strategi yang lolos di keempat periode adalah trend-following Donchian H1
(research.github_popular, research.trend_grid). Di sini diuji, TANPA mengubah parameter:
1. A-ensemble: 3 set (40/15, 55/20, 80/30), hold sampai channel exit, risiko dibagi 3.
2. F-ensemble: skema bot sekarang (TP1 1R untuk 1 dari 5 posisi, lalu SL+).
3. A-ensemble + filter rezim: BUY hanya bila close harian kemarin > SMA200 harian, SELL sebaliknya.
4. A-ensemble + filter ML: hanya ambil sinyal yang searah prediksi model gradient boosting (prob > 0,5).
Semua filter pra-didaftarkan (satu varian, tanpa optimasi).
"""
from __future__ import annotations

import pickle
import sys

import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .data import resample
from .github_popular import ml_prob
from .harness import fmt, periods, stats

SETS = [(40, 15), (55, 20), (80, 30)]


def donchian_allow(df: pd.DataFrame, spread: float, n_entry: int, n_exit: int, stop_atr: float = 3.0,
                   long_ok: np.ndarray | None = None, short_ok: np.ndarray | None = None,
                   f_legs: int = 0) -> pd.DataFrame:
    """Sama dengan research.alt.donchian, ditambah izin arah per bar sinyal.

    f_legs > 1: skema F (bot sekarang) - 1 dari f_legs posisi TP 1R, setelah itu SL sisa ke entry + 0,1R;
    R = rata-rata per posisi (risiko awal total tetap 1R)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, 20)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    n = len(df)
    lok = np.ones(n, bool) if long_ok is None else long_ok
    sok = np.ones(n, bool) if short_ok is None else short_ok
    trades = []
    pos, entry, stop, risk, t0, tp1 = 0, 0.0, 0.0, 0.0, 0, False

    def res(r_exit):  # R per trade (skema F: 1 posisi sudah TP 1R)
        return (1.0 + (f_legs - 1) * r_exit) / f_legs if tp1 else r_exit

    for i in range(max(n_entry, 20) + 1, n - 1):
        if pos != 0:
            if pos > 0 and l[i] <= stop:
                trades.append((t0, i, pos, res((min(stop, o[i]) - entry) / risk)))
                pos = 0
            elif pos < 0 and h[i] + spread >= stop:
                trades.append((t0, i, pos, res((entry - max(stop, o[i] + spread)) / risk)))
                pos = 0
            else:
                if f_legs > 1 and not tp1 and i > t0 and (
                        (h[i] >= entry + risk) if pos > 0 else (l[i] + spread <= entry - risk)):
                    tp1, stop = True, entry + pos * 0.1 * risk
                if pos > 0 and c[i] < lo_x[i]:
                    trades.append((t0, i + 1, pos, res((o[i + 1] - entry) / risk)))
                    pos = 0
                    continue
                if pos < 0 and c[i] > hi_x[i]:
                    trades.append((t0, i + 1, pos, res((entry - o[i + 1] - spread) / risk)))
                    pos = 0
                    continue
        if pos == 0:
            if c[i] > hi_e[i] and lok[i]:
                entry = o[i + 1] + spread
                stop, pos, risk, t0, tp1 = entry - stop_atr * a[i], 1, stop_atr * a[i], i + 1, False
            elif c[i] < lo_e[i] and sok[i]:
                entry = o[i + 1]
                stop, pos, risk, t0, tp1 = entry + stop_atr * a[i], -1, stop_atr * a[i], i + 1, False
    t = pd.DataFrame(trades, columns=["i0", "i1", "dir", "R"])
    t["time"] = df.index[t.i0.to_numpy()] if len(t) else pd.Series(dtype="datetime64[ns, UTC]")
    t["exit"] = df.index[np.minimum(t.i1.to_numpy(), n - 1)] if len(t) else pd.Series(dtype="datetime64[ns, UTC]")
    return t


def ensemble(H, sp, **kw) -> pd.DataFrame:
    parts = [donchian_allow(H, sp, ne, nx, **kw).assign(set=f"{ne}/{nx}") for ne, nx in SETS]
    t = pd.concat(parts, ignore_index=True).sort_values("time", kind="stable")
    return t.assign(R=t.R / 3).reset_index(drop=True)


def regime_masks(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    d = H["close"].resample("1D").last().dropna()
    up = (d > d.rolling(200).mean()).astype(float)
    up[d.rolling(200).mean().isna()] = np.nan
    up.index = up.index + pd.Timedelta(days=1)  # hanya hari yang sudah selesai
    u = up.reindex(H.index, method="ffill").to_numpy()
    return np.nan_to_num(u, nan=1) == 1, np.nan_to_num(u, nan=0) == 0


def main():
    ps = periods()
    Hs = {p.name: (resample(p.base, "60min"), p.spread) for p in ps}
    full = pd.concat([h for h, _ in Hs.values()])
    full = full[~full.index.duplicated()]
    prob, _ = ml_prob(full)
    prob = pd.Series(prob, index=full.index)

    results: dict[str, dict[str, pd.DataFrame]] = {k: {} for k in ("F", "A", "Rezim", "ML")}
    for label, name in [("F", "F-ensemble (bot sekarang: TP1 1R + SL+)"), ("A", "A-ensemble (hold sampai channel exit)"), ("Rezim", "A-ensemble + filter SMA200 harian"),
                        ("ML", "A-ensemble + filter searah ML")]:
        print(name)
        tot = []
        for k, (H, sp) in Hs.items():
            kw = {"f_legs": 5} if label == "F" else {}
            if label == "Rezim":
                lo, so = regime_masks(pd.concat([full[full.index < H.index[0]].iloc[-24 * 400:], H]))
                kw = {"long_ok": lo[-len(H):], "short_ok": so[-len(H):]}
            elif label == "ML":
                p = prob.reindex(H.index).to_numpy()
                kw = {"long_ok": ~(p < 0.5), "short_ok": ~(p > 0.5)}  # tanpa model (awal data) = tidak difilter
            t = ensemble(H, sp, **kw)
            results[label][k] = t
            tot.append(t.R.sum())
            print(f"   {k}: {fmt(stats(t.R))}")
        print(f"   total 4 periode: {sum(tot):+.1f}R, periode positif {sum(x > 0 for x in tot)}/4")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "wb") as fh:
            pickle.dump(results, fh)


if __name__ == "__main__":
    main()
