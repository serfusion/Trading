"""Tahap 2: gabungan metode trend + penaik win rate (python -m research.strategy_lab2).

Parameter SAMA untuk semua instrumen (tidak dioptimasi per instrumen). Hasil hanya dari periode UJI
(XAU 2019-2026, BTC 2021-2026, EURJPY 2016-2022) + portofolio satu akun. Stabil = % bulan untung.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .filters import FILTERS, features
from .gap_study import week_info
from .strategy_lab import Bars, ema, markets, rolling_max, rolling_min, stats

STAR = FILTERS["KOMBINASI: tren D1 + H4 breakout"]


def backtest_f(b, long_in, short_in, long_out, short_out, sl_atr, legs=5, tp1_r=1.0, allow=None):
    """Skema F: `legs` posisi, posisi #1 TP di tp1_r, setelah TP1 SL sisa -> entry+0,1R; sisanya keluar di sinyal
    keluar. tp1_r=None -> semua posisi runner. Return list (t_in, t_out, R rata-rata per posisi, dir)."""
    trades, i, n = [], 0, b.n
    o, h, l, sp, a = b.o, b.h, b.l, b.sp, b.atr
    while i < n - 2:
        d = 1 if long_in[i] else (-1 if short_in[i] else 0)
        if d == 0 or not a[i] > 0 or (allow is not None and not allow(i, d)):
            i += 1
            continue
        j = i + 1
        entry = o[j] + (sp[j] if d > 0 else 0.0)
        risk = sl_atr * a[i]
        sl = entry - d * risk
        tp1 = entry + d * tp1_r * risk if tp1_r else None
        left, pnl, k = legs, 0.0, j
        out = long_out if d > 0 else short_out
        done = False
        while k < n - 1 and not done:
            adj = sp[k] if d < 0 else 0.0
            if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):
                px = sl if k == j else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                pnl += (px - entry) * d * left
                done = True
                break
            if tp1 is not None and left == legs and k > j and ((h[k] + adj >= tp1) if d > 0 else (l[k] + adj <= tp1)):
                pnl += tp1_r * risk
                left -= 1
                sl = entry + d * 0.1 * risk
            if out[k]:
                pnl += (o[k + 1] + (sp[k + 1] if d < 0 else 0.0) - entry) * d * left
                k += 1
                done = True
                break
            k += 1
        if not done:
            break
        trades.append((b.t[j], b.t[min(k, n - 1)], pnl / risk / legs, d))
        i = k + 1
    return trades


def trend_states(b):
    """Arah tiap metode trend (1/-1) di close candle i — dipakai untuk konfluensi."""
    c = b.c
    e50, e200 = ema(c, 50), ema(c, 200)
    ema_dir = np.where(e50 > e200, 1, -1)
    # supertrend 3x ATR
    hl2 = (b.h + b.l) / 2
    up, dn = hl2 - 3 * b.atr, hl2 + 3 * b.atr
    st = np.ones(b.n, int)
    fu, fd = up.copy(), dn.copy()
    for i in range(1, b.n):
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        st[i] = 1 if c[i] > fd[i - 1] else (-1 if c[i] < fu[i - 1] else st[i - 1])
    d, _ = b.daily()
    mom = np.sign(d["close"] - d["close"].shift(60)).shift(1)             # momentum 60 hari s/d kemarin
    mom = mom.reindex(b.t.normalize()).to_numpy()
    return {"ema": ema_dir, "st": st, "mom": np.nan_to_num(mom)}


def signals(b, method):
    c, h, l = b.c, b.h, b.l
    if method == "donchian":
        out = []
        for n_in, n_out in ((40, 15), (55, 20), (80, 30)):
            hi, lo = rolling_max(h, n_in), rolling_min(l, n_in)
            hx, lx = rolling_max(h, n_out), rolling_min(l, n_out)
            out.append((c > hi, c < lo, c < lx, c > hx))
        return out
    s = trend_states(b)
    if method == "supertrend":
        st = s["st"]
        prev = np.r_[st[0], st[:-1]]
        return [((st == 1) & (prev == -1), (st == -1) & (prev == 1), st == -1, st == 1)]
    if method == "ema":
        e = s["ema"]
        prev = np.r_[e[0], e[:-1]]
        return [((e == 1) & (prev == -1), (e == -1) & (prev == 1), e == -1, e == 1)]
    raise ValueError(method)


def run(b, m, method, scheme, filt):
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))

    def allow(i, d):
        if since[i] < 3:
            return False
        if filt == "⭐":
            return bool(STAR(f, i, d))
        if filt == "konfluensi 3/3":
            return s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        return True
    sl = 3.0
    tr = []
    for li, si, lo, so in signals(b, method):
        if scheme == "F (TP1 1R + SL+)":
            tr += backtest_f(b, li, si, lo, so, sl, 5, 1.0, allow)
        else:
            tr += backtest_f(b, li, si, lo, so, sl, 5, None, allow)
    tr.sort()
    return [x for x in tr if x[0] >= m.split]


def monthly(tr, risk=0.005):
    r = pd.Series([x[2] * risk for x in tr], index=[x[1] for x in tr])
    mon = r.groupby(r.index.to_period("M")).sum()
    return mon


def fmt(s, mon):
    return (f"n={s['n']:4d} win={s['win']:4.1f}% rata={s['avg']:+.3f}R total={s['total']:+7.1f}R PF={s['pf']:.2f} "
            f"DD={s['dd']:+6.1f}R bulan+={(mon > 0).mean() * 100:3.0f}%")


def main():
    combos = [(m, sc, fl) for m in ("donchian", "supertrend", "ema")
              for sc in ("semua runner", "F (TP1 1R + SL+)") for fl in ("-", "⭐", "konfluensi 3/3")]
    results = {}
    for mk in markets():
        b = Bars(mk.h1, mk.spread)
        print(f"\n######## {mk.name} (UJI {mk.split:%Y}-{mk.h1.index[-1]:%Y})")
        for method, scheme, filt in combos:
            tr = run(b, mk, method, scheme, filt)
            results[(mk.name, method, scheme, filt)] = tr
            print(f"  {method:10s} {scheme:17s} filter {filt:15s} {fmt(stats(tr), monthly(tr))}")
    pd.to_pickle(results, "data/research/strategy_lab2.pkl")
    print("\nPORTOFOLIO satu akun (0,5% per sinyal), periode uji masing-masing, XAU + BTC")
    for method, scheme, filt in combos:
        tr = sorted(results[("XAUUSD", method, scheme, filt)] + results[("BTCUSD", method, scheme, filt)])
        mon = monthly(tr)
        print(f"  {method:10s} {scheme:17s} filter {filt:15s} {fmt(stats(tr), mon)} "
              f"bulan terburuk {mon.min() * 100:+.1f}%")


if __name__ == "__main__":
    main()
