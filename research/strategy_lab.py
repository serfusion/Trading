"""Laboratorium strategi: banyak keluarga metode di XAU/USD, BTC/USD, EUR/JPY (python -m research.strategy_lab).

Aturan uji (sama untuk semua metode): sinyal di close candle H1 -> entry di open candle berikutnya (BUY + spread),
SL dicek lebih dulu, TP tidak dihitung di candle entry, satu posisi per strategi, tanpa data masa depan.
Anti-overfitting: parameter terbaik dipilih HANYA dari periode latih, lalu diuji di periode uji yang belum dilihat.
Hasil dalam R (1R = rugi bila kena SL awal). Swap belum dihitung.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import resample
from .multi_asset import load as load_ejtrader
from .run_scan import DATA, dataset


# ------------------------------------------------------------------ data
@dataclass
class Market:
    name: str
    h1: pd.DataFrame
    spread: object          # harga atau "x%" dari harga
    split: pd.Timestamp     # awal periode uji
    start: pd.Timestamp     # awal periode latih


def _clip(df, a):
    return df[df.index >= pd.Timestamp(a, tz="UTC")]


def markets() -> list[Market]:
    xau_a = load_ejtrader("XAUUSD")
    m20 = resample(dataset("m5_2020")[0], "60min")
    m25 = resample(dataset("m5_2025")[0], "60min")
    xau = pd.concat([xau_a, m20[m20.index > xau_a.index[-1]]])
    xau = pd.concat([xau, m25[m25.index > xau.index[-1]]])
    btc = pd.read_parquet(DATA / "h1" / "BTC_USD_full.parquet")
    ej_o = pd.read_parquet(DATA / "h1" / "EUR_JPY.parquet")
    ej_e = load_ejtrader("EURJPY")
    ej = pd.concat([ej_o, ej_e[ej_e.index > ej_o.index[-1]]])
    out = []
    for name, df, sp, start, split in [("XAUUSD", xau, 0.30, "2012-11-15", "2019-01-01"),
                                        ("BTCUSD", btc, "0.03%", "2016-01-01", "2021-01-01"),
                                        ("EURJPY", ej, 0.018, "2008-01-01", "2016-01-01")]:
        df = _clip(df, start)
        df = df[df["high"] > df["low"]]
        out.append(Market(name, df, sp, pd.Timestamp(split, tz="UTC"), pd.Timestamp(start, tz="UTC")))
    return out


# ------------------------------------------------------------------ indikator
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


def rolling_max(x, n):
    return pd.Series(x).rolling(n).max().shift(1).to_numpy()


def rolling_min(x, n):
    return pd.Series(x).rolling(n).min().shift(1).to_numpy()


class Bars:
    def __init__(self, df: pd.DataFrame, spread):
        self.df = df
        self.t = df.index
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.n = len(df)
        self.sp = self.c * float(spread.rstrip("%")) / 100 if isinstance(spread, str) else np.full(self.n, spread)
        self.atr = atr(self.h, self.l, self.c, 14)
        self._cache = {}

    def cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def daily(self):
        """Nilai D1 yang sudah tertutup, dipetakan ke tiap candle H1 (kemarin)."""
        def make():
            d = self.df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
            prev = d.shift(1).reindex(self.t.normalize()).set_axis(self.t)
            return d, prev
        return self.cached("daily", make)


# ------------------------------------------------------------------ simulasi
def backtest(b: Bars, long_in, short_in, long_out, short_out, sl_atr, tp_r=None, max_hold=None, be_r=None):
    """Satu posisi. *_in/*_out: array bool sinyal di close candle i. Return list (t_in, t_out, R, dir)."""
    trades, i, n = [], 0, b.n
    o, h, l, sp, a = b.o, b.h, b.l, b.sp, b.atr
    while i < n - 2:
        d = 1 if long_in[i] else (-1 if short_in[i] else 0)
        if d == 0 or not a[i] > 0:
            i += 1
            continue
        j = i + 1
        entry = o[j] + (sp[j] if d > 0 else 0.0)
        risk = sl_atr * a[i]
        sl = entry - d * risk
        tp = entry + d * tp_r * risk if tp_r else None
        out_mask = long_out if d > 0 else short_out
        exit_px, k = None, j
        while k < n - 1:
            adj = sp[k] if d < 0 else 0.0
            lo, hi = l[k] + adj, h[k] + adj
            if (lo <= sl) if d > 0 else (hi >= sl):                    # SL lebih dulu
                exit_px = sl if k == j else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                break
            if tp is not None and k > j and ((hi >= tp) if d > 0 else (lo <= tp)):
                exit_px = tp
                break
            if be_r and ((hi - entry) if d > 0 else (entry - lo)) >= be_r * risk:
                sl = entry + d * 0.1 * risk if d > 0 else entry - 0.1 * risk
            if out_mask[k] or (max_hold and k - j + 1 >= max_hold):
                exit_px = o[k + 1] + (sp[k + 1] if d < 0 else 0.0)
                k += 1
                break
            k += 1
        if exit_px is None:
            break
        trades.append((b.t[j], b.t[min(k, n - 1)], (exit_px - entry) * d / risk, d))
        i = k + 1 if k > i else i + 1
    return trades


# ------------------------------------------------------------------ keluarga metode
def fam_donchian(b, n_in, n_out, sl, tp):
    hi_i, lo_i = rolling_max(b.h, n_in), rolling_min(b.l, n_in)
    hi_o, lo_o = rolling_max(b.h, n_out), rolling_min(b.l, n_out)
    return backtest(b, b.c > hi_i, b.c < lo_i, b.c < lo_o, b.c > hi_o, sl, tp)


def fam_ema_cross(b, fast, slow, sl, tp):
    f, s = ema(b.c, fast), ema(b.c, slow)
    up = (f > s) & (np.r_[False, (f <= s)[:-1]])
    dn = (f < s) & (np.r_[False, (f >= s)[:-1]])
    return backtest(b, up, dn, f < s, f > s, sl, tp)


def fam_supertrend(b, mult, sl, tp):
    key = ("st", mult)

    def make():
        hl2 = (b.h + b.l) / 2
        up, dn = hl2 - mult * b.atr, hl2 + mult * b.atr
        trend = np.ones(b.n, int)
        fu, fd = up.copy(), dn.copy()
        for i in range(1, b.n):
            fu[i] = max(up[i], fu[i - 1]) if b.c[i - 1] > fu[i - 1] else up[i]
            fd[i] = min(dn[i], fd[i - 1]) if b.c[i - 1] < fd[i - 1] else dn[i]
            trend[i] = 1 if b.c[i] > fd[i - 1] else (-1 if b.c[i] < fu[i - 1] else trend[i - 1])
        return trend
    tr = b.cached(key, make)
    prev = np.r_[tr[0], tr[:-1]]
    return backtest(b, (tr == 1) & (prev == -1), (tr == -1) & (prev == 1), tr == -1, tr == 1, sl, tp)


def fam_tsmom_d1(b, days, sl, tp):
    d, _ = b.daily()
    mom = np.sign(d["close"] - d["close"].shift(days))
    sig = mom.shift(0).reindex(b.t.normalize(), method=None).to_numpy()    # arah hari ini (baru valid di akhir hari)
    last_of_day = np.r_[b.t.normalize()[1:] != b.t.normalize()[:-1], True]   # candle terakhir tiap hari
    s = np.where(last_of_day, sig, np.nan)
    s = pd.Series(s).ffill().to_numpy()
    prev = np.r_[np.nan, s[:-1]]
    return backtest(b, (s == 1) & (prev != 1) & last_of_day, (s == -1) & (prev != -1) & last_of_day,
                    (s == -1), (s == 1), sl, tp)


def fam_pullback_rsi(b, lvl, sl, tp):
    trend = b.cached("ema200", lambda: ema(b.c, 200))
    r = b.cached("rsi14", lambda: rsi(b.c, 14))
    return backtest(b, (b.c > trend) & (r < lvl), (b.c < trend) & (r > 100 - lvl), r > 55, r < 45, sl, tp, max_hold=48)


def fam_rsi2(b, lvl, sl, tp):
    trend = b.cached("sma200", lambda: sma(b.c, 200))
    r = b.cached("rsi2", lambda: rsi(b.c, 2))
    s5 = b.cached("sma5", lambda: sma(b.c, 5))
    return backtest(b, (b.c > trend) & (r < lvl), (b.c < trend) & (r > 100 - lvl), b.c > s5, b.c < s5, sl, tp,
                    max_hold=24)


def fam_bb_fade(b, k, trend_filter, sl, tp):
    m = b.cached("sma20", lambda: sma(b.c, 20))
    sd = b.cached("sd20", lambda: pd.Series(b.c).rolling(20).std().to_numpy())
    trend = b.cached("ema200", lambda: ema(b.c, 200))
    lo_ok = (b.c > trend) if trend_filter else np.ones(b.n, bool)
    hi_ok = (b.c < trend) if trend_filter else np.ones(b.n, bool)
    return backtest(b, lo_ok & (b.c < m - k * sd), hi_ok & (b.c > m + k * sd), b.c > m, b.c < m, sl, tp, max_hold=48)


def fam_vol_breakout(b, k, sl, tp):
    _, prev = b.daily()
    rng = (prev["high"] - prev["low"]).to_numpy()
    day = b.t.normalize()
    first = np.r_[True, day[1:] != day[:-1]]
    day_open = pd.Series(np.where(first, b.o, np.nan)).ffill().to_numpy()
    up, dn = day_open + k * rng, day_open - k * rng
    last = np.r_[day[1:] != day[:-1], True]
    return backtest(b, b.c > up, b.c < dn, last, last, sl, tp)


def fam_macd(b, sl, tp, trend_filter=True):
    m = ema(b.c, 12) - ema(b.c, 26)
    hist = m - ema(m, 9)
    trend = b.cached("ema200", lambda: ema(b.c, 200))
    prev = np.r_[0, hist[:-1]]
    up = (hist > 0) & (prev <= 0) & ((b.c > trend) if trend_filter else True)
    dn = (hist < 0) & (prev >= 0) & ((b.c < trend) if trend_filter else True)
    return backtest(b, up, dn, hist < 0, hist > 0, sl, tp)


TPS_TREND = [None, 1.0]
TPS_MR = [None, 0.5, 1.0]
FAMILIES = {
    "Donchian breakout": (fam_donchian, [dict(n_in=n, n_out=max(5, n // q), sl=s, tp=t)
                                         for n in (20, 40, 55, 80, 120) for q in (2, 4) for s in (2, 3)
                                         for t in TPS_TREND]),
    "EMA cross": (fam_ema_cross, [dict(fast=f, slow=s_, sl=s, tp=t) for f, s_ in ((10, 30), (20, 50), (20, 100), (50, 200))
                                  for s in (2, 3, 4) for t in TPS_TREND]),
    "Supertrend": (fam_supertrend, [dict(mult=m, sl=s, tp=t) for m in (2, 3, 4, 5) for s in (2, 3) for t in TPS_TREND]),
    "Momentum D1 (TSMOM)": (fam_tsmom_d1, [dict(days=d, sl=s, tp=t) for d in (20, 60, 120) for s in (4, 8)
                                           for t in TPS_TREND]),
    "MACD + tren": (fam_macd, [dict(sl=s, tp=t) for s in (2, 3) for t in TPS_TREND]),
    "Pullback RSI dalam tren": (fam_pullback_rsi, [dict(lvl=v, sl=s, tp=t) for v in (30, 35, 40) for s in (1.5, 2.5)
                                                    for t in TPS_MR]),
    "RSI(2) Connors": (fam_rsi2, [dict(lvl=v, sl=s, tp=t) for v in (5, 10, 15) for s in (2, 3) for t in TPS_MR]),
    "Bollinger fade": (fam_bb_fade, [dict(k=k, trend_filter=f, sl=s, tp=t) for k in (2.0, 2.5) for f in (True, False)
                                     for s in (1.5, 2.5) for t in TPS_MR]),
    "Volatility breakout harian": (fam_vol_breakout, [dict(k=k, sl=s, tp=t) for k in (0.3, 0.5, 0.7) for s in (2, 3)
                                                      for t in TPS_TREND]),
}


# ------------------------------------------------------------------ statistik
def stats(tr):
    if not tr:
        return dict(n=0, win=0.0, avg=0.0, total=0.0, pf=0.0, dd=0.0, tstat=0.0, years=0.0)
    r = np.array([x[2] for x in tr])
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    yrs = pd.Series(r, index=[x[1].year for x in tr]).groupby(level=0).sum()
    sd = r.std() or 1e-9
    return dict(n=len(r), win=float((r > 0).mean() * 100), avg=float(r.mean()), total=float(r.sum()),
                pf=float(r[r > 0].sum() / max(-r[r < 0].sum(), 1e-9)), dd=dd,
                tstat=float(r.mean() / sd * math.sqrt(len(r))), years=float((yrs > 0).mean() * 100))


def fmt(s):
    return (f"n={s['n']:4d} win={s['win']:4.1f}% rata={s['avg']:+.3f}R total={s['total']:+7.1f}R "
            f"PF={s['pf']:.2f} DD={s['dd']:+6.1f}R thn+={s['years']:3.0f}%")


def split(tr, m: Market):
    return [x for x in tr if x[0] < m.split], [x for x in tr if x[0] >= m.split]


def main():
    rows = []
    for m in markets():
        b = Bars(m.h1, m.spread)
        print(f"\n######## {m.name}  latih {m.start:%Y}-{m.split.year - 1}  uji {m.split:%Y}-{m.h1.index[-1]:%Y}")
        for fam, (fn, grid) in FAMILIES.items():
            res = []
            for p in grid:
                dev, test = split(fn(b, **p), m)
                sd, st = stats(dev), stats(test)
                res.append((p, sd, st))
            ok = [r for r in res if r[1]["n"] >= 60]
            if not ok:
                continue
            best = max(ok, key=lambda r: r[1]["tstat"])
            pos_test = np.mean([r[2]["total"] > 0 for r in res]) * 100
            print(f"  {fam:28s} {best[0]}")
            print(f"      LATIH {fmt(best[1])}")
            print(f"      UJI   {fmt(best[2])}   | variasi untung di uji: {pos_test:.0f}%")
            rows.append((m.name, fam, best[0], best[1], best[2], pos_test))
    pd.to_pickle(rows, DATA / "strategy_lab.pkl")


if __name__ == "__main__":
    main()
