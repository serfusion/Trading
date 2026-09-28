"""Uji besar: ±35 metode × 21 instrumen, latih/uji terpisah (python -m research.world_lab).

Instrumen: 11 forex (ejtrader 2012-2022, 4 pair disambung OANDA 2008-), XAU (2012-2026), 7 indeks saham +
WTI (OANDA 2008-2020), BTC (Bitstamp 2016-2026). Aturan: sinyal di close H1 -> entry open berikutnya (+spread),
SL dicek dulu, tanpa data masa depan, satu posisi per (instrumen, metode), swap belum dihitung.
Parameter terbaik dipilih di periode LATIH (t-stat), dinilai di periode UJI.
"""
from __future__ import annotations

import math
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

from .data import resample
from .multi_asset import INSTRUMENTS as EJ, load as load_ej
from .run_scan import DATA, dataset
from .strategy_lab import Bars, atr, ema, rolling_max, rolling_min, rsi, sma

# ------------------------------------------------------------------ instrumen
OANDA_SPREAD = {"NAS100_USD": 1.8, "SPX500_USD": 0.5, "US2000_USD": 0.3, "JP225_USD": 10.0, "UK100_GBP": 1.5,
                "FR40_EUR": 1.5, "AU200_AUD": 2.5, "WTICO_USD": 0.03}
JOIN = {"EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "EURJPY": "EUR_JPY", "AUDJPY": "AUD_JPY"}


def instrument(name):
    """-> (h1, spread, awal latih, awal uji)"""
    if name == "XAUUSD":
        a = load_ej("XAUUSD")
        m20 = resample(dataset("m5_2020")[0], "60min")
        m25 = resample(dataset("m5_2025")[0], "60min")
        h1 = pd.concat([a, m20[m20.index > a.index[-1]]])
        h1 = pd.concat([h1, m25[m25.index > h1.index[-1]]])
        return h1, 0.30, "2012-11-15", "2019-01-01"
    if name == "BTCUSD":
        return pd.read_parquet(DATA / "h1" / "BTC_USD_full.parquet"), "0.03%", "2016-01-01", "2021-01-01"
    if name in OANDA_SPREAD:
        return pd.read_parquet(DATA / "h1" / f"{name}.parquet"), OANDA_SPREAD[name], "2008-01-01", "2015-01-01"
    h1 = load_ej(name)
    if name in JOIN:
        o = pd.read_parquet(DATA / "h1" / f"{JOIN[name]}.parquet")
        h1 = pd.concat([o, h1[h1.index > o.index[-1]]])
        return h1, EJ[name][1], "2008-01-01", "2016-01-01"
    return h1, EJ[name][1], "2012-11-15", "2018-01-01"


NAMES = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "EURGBP", "EURCHF", "USDJPY",
         "EURJPY", "GBPJPY", "AUDJPY", "WTICO_USD", "NAS100_USD", "SPX500_USD", "US2000_USD", "JP225_USD",
         "UK100_GBP", "FR40_EUR", "AU200_AUD"]


# ------------------------------------------------------------------ backtest cepat
def backtest(b, long_in, short_in, long_out, short_out, sl_atr, tp_r=None, max_hold=None):
    trades = []
    o, h, l, sp, a, t, n = b.o, b.h, b.l, b.sp, b.atr, b.t, b.n
    cand = np.flatnonzero((long_in | short_in)[: n - 2])
    ci, i = 0, 0
    while ci < len(cand):
        i = cand[ci]
        d = 1 if long_in[i] else -1
        if not a[i] > 0:
            ci += 1
            continue
        j = i + 1
        entry = o[j] + (sp[j] if d > 0 else 0.0)
        risk = sl_atr * a[i]
        sl = entry - d * risk
        tp = entry + d * tp_r * risk if tp_r else None
        out = long_out if d > 0 else short_out
        px, k = None, j
        while k < n - 1:
            adj = sp[k] if d < 0 else 0.0
            if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):
                px = sl if k == j else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                break
            if tp is not None and k > j and ((h[k] + adj >= tp) if d > 0 else (l[k] + adj <= tp)):
                px = tp
                break
            if out[k] or (max_hold and k - j + 1 >= max_hold):
                k += 1
                px = o[k] + (sp[k] if d < 0 else 0.0)
                break
            k += 1
        if px is None:
            break
        trades.append((t[j], t[k], (px - entry) * d / risk))
        ci = np.searchsorted(cand, k, side="left")
    return trades


# ------------------------------------------------------------------ bantuan D1
class Ctx:
    """Data + indikator bersama (dihitung sekali per instrumen)."""

    def __init__(self, h1, spread):
        self.b = Bars(h1, spread)
        b = self.b
        self.day = b.t.normalize()
        self.last = np.r_[self.day[1:] != self.day[:-1], True]            # candle terakhir tiap hari
        self.first = np.r_[True, self.day[1:] != self.day[:-1]]
        d = h1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        self.d1 = d
        # indeks hari "sudah selesai" terakhir pada close candle i
        pos = d.index.searchsorted(self.day)                               # indeks hari candle i
        self.done = np.where(self.last, pos, pos - 1)
        self.hour = b.t.hour.to_numpy()
        self.c = b.c
        self.cache = {}

    def get(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    def d1_map(self, series):
        """Nilai D1 hari yang sudah selesai pada tiap candle H1 (NaN bila belum ada)."""
        arr = np.asarray(series, float)
        idx = self.done
        out = np.full(len(idx), np.nan)
        ok = (idx >= 0) & (idx < len(arr))
        out[ok] = arr[idx[ok]]
        return out

    def d1_event(self, series_bool):
        """Kejadian D1 (mis. breakout harian) -> True hanya di candle terakhir hari itu."""
        v = self.d1_map(np.asarray(series_bool, float))
        return self.last & (v == 1)


def cross_up(x, y):
    return (x > y) & np.r_[False, (x <= y)[:-1]]


def cross_dn(x, y):
    return (x < y) & np.r_[False, (x >= y)[:-1]]


def flip(state):
    prev = np.r_[state[0], state[:-1]]
    return (state == 1) & (prev != 1), (state == -1) & (prev != -1)


# ------------------------------------------------------------------ metode
def m_donchian(x, n):
    b = x.b
    hi, lo = rolling_max(b.h, n), rolling_min(b.l, n)
    hx, lx = rolling_max(b.h, n // 4), rolling_min(b.l, n // 4)
    return b.c > hi, b.c < lo, b.c < lx, b.c > hx, 3.0


def m_turtle_d1(x, n):
    d = x.d1
    up = d["close"] > d["high"].rolling(n).max().shift(1)
    dn = d["close"] < d["low"].rolling(n).min().shift(1)
    ex_l = d["close"] < d["low"].rolling(n // 2).min().shift(1)
    ex_s = d["close"] > d["high"].rolling(n // 2).max().shift(1)
    return x.d1_event(up), x.d1_event(dn), x.d1_event(ex_l), x.d1_event(ex_s), 10.0


def m_ema_cross(x, f, s):
    c = x.c
    ef, es = ema(c, f), ema(c, s)
    return cross_up(ef, es), cross_dn(ef, es), ef < es, ef > es, 3.0


def m_triple_ma(x):
    c = x.c
    a, b_, c_ = ema(c, 20), ema(c, 50), ema(c, 100)
    st = np.where((a > b_) & (b_ > c_), 1, np.where((a < b_) & (b_ < c_), -1, 0))
    li, si = flip(st)
    return li, si, st != 1, st != -1, 3.0


def supertrend_state(x, mult):
    def make():
        b = x.b
        hl2 = (b.h + b.l) / 2
        up, dn = hl2 - mult * b.atr, hl2 + mult * b.atr
        st = np.ones(b.n, int)
        fu, fd = up.copy(), dn.copy()
        c = b.c
        for i in range(1, b.n):
            fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
            fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
            st[i] = 1 if c[i] > fd[i - 1] else (-1 if c[i] < fu[i - 1] else st[i - 1])
        return st
    return x.get(("st", mult), make)


def m_supertrend(x, mult):
    st = supertrend_state(x, mult)
    li, si = flip(st)
    return li, si, st == -1, st == 1, 3.0


def m_psar(x, step):
    def make():
        b = x.b
        h, l = b.h, b.l
        st = np.ones(b.n, int)
        sar, ep, af, up = l[0], h[0], step, True
        for i in range(1, b.n):
            sar = sar + af * (ep - sar)
            if up:
                sar = min(sar, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
                if l[i] < sar:
                    up, sar, ep, af = False, ep, l[i], step
                elif h[i] > ep:
                    ep, af = h[i], min(af + step, 0.2)
            else:
                sar = max(sar, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
                if h[i] > sar:
                    up, sar, ep, af = True, ep, h[i], step
                elif l[i] < ep:
                    ep, af = l[i], min(af + step, 0.2)
            st[i] = 1 if up else -1
        return st
    st = x.get(("psar", step), make)
    li, si = flip(st)
    return li, si, st == -1, st == 1, 3.0


def m_ichimoku(x):
    b = x.b
    tk = (pd.Series(b.h).rolling(9).max() + pd.Series(b.l).rolling(9).min()).to_numpy() / 2
    kj = (pd.Series(b.h).rolling(26).max() + pd.Series(b.l).rolling(26).min()).to_numpy() / 2
    sa = np.r_[np.full(26, np.nan), ((tk + kj) / 2)[:-26]]
    sb_ = ((pd.Series(b.h).rolling(52).max() + pd.Series(b.l).rolling(52).min()) / 2).to_numpy()
    sb = np.r_[np.full(26, np.nan), sb_[:-26]]
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    return (cross_up(tk, kj) & (b.c > top), cross_dn(tk, kj) & (b.c < bot), b.c < kj, b.c > kj, 3.0)


def dmi(x, n=14):
    def make():
        b = x.b
        up, dn = np.diff(b.h, prepend=b.h[0]), -np.diff(b.l, prepend=b.l[0])
        pdm = np.where((up > dn) & (up > 0), up, 0.0)
        ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
        a = atr(b.h, b.l, b.c, n)
        pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
        ndi = 100 * pd.Series(ndm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
        dx = 100 * abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-9)
        adx = pd.Series(dx).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
        return pdi, ndi, adx
    return x.get("dmi", make)


def m_adx(x, lvl):
    pdi, ndi, adx = dmi(x)
    return cross_up(pdi, ndi) & (adx > lvl), cross_dn(pdi, ndi) & (adx > lvl), pdi < ndi, pdi > ndi, 3.0


def m_keltner(x, mult):
    b = x.b
    m = ema(b.c, 20)
    return (cross_up(b.c, m + mult * b.atr), cross_dn(b.c, m - mult * b.atr), b.c < m, b.c > m, 3.0)


def m_bb_squeeze(x):
    b = x.b
    m = sma(b.c, 20)
    sd = pd.Series(b.c).rolling(20).std().to_numpy()
    width = 4 * sd / m
    rank = pd.Series(width).rolling(120).rank(pct=True).to_numpy()
    sq = np.r_[False, (rank < 0.2)[:-1]]
    return sq & (b.c > m + 2 * sd), sq & (b.c < m - 2 * sd), b.c < m, b.c > m, 2.0


def m_macd(x):
    c = x.c
    mm = ema(c, 12) - ema(c, 26)
    hist = mm - ema(mm, 9)
    tr = ema(c, 200)
    z = np.zeros_like(hist)
    return cross_up(hist, z) & (c > tr), cross_dn(hist, z) & (c < tr), hist < 0, hist > 0, 3.0


def m_aroon(x, n=25):
    b = x.b
    au = pd.Series(b.h).rolling(n + 1).apply(np.argmax, raw=True).to_numpy() / n * 100
    ad = pd.Series(b.l).rolling(n + 1).apply(np.argmin, raw=True).to_numpy() / n * 100
    return (cross_up(au, ad) & (au > 70), cross_dn(au, ad) & (ad > 70), au < ad, au > ad, 3.0)


def wma(v, n):
    w = np.arange(1, n + 1)
    return pd.Series(v).rolling(n).apply(lambda s: np.dot(s, w) / w.sum(), raw=True).to_numpy()


def m_hull(x, n):
    def make():
        c = x.c
        return wma(2 * wma(c, n // 2) - wma(c, n), int(math.sqrt(n)))
    hm = x.get(("hull", n), make)
    slope = np.sign(np.diff(hm, prepend=np.nan))
    li, si = flip(np.nan_to_num(slope).astype(int))
    return li, si, slope < 0, slope > 0, 3.0


def m_heikin(x):
    b = x.b
    hc = (b.o + b.h + b.l + b.c) / 4
    ho = np.empty(b.n)
    ho[0] = (b.o[0] + b.c[0]) / 2
    for i in range(1, b.n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    col = np.sign(hc - ho)
    run3 = (col == np.r_[0, col[:-1]]) & (col == np.r_[0, 0, col[:-2]])
    st = np.where(run3, col, 0)
    li = (st == 1) & np.r_[True, st[:-1] != 1]
    si = (st == -1) & np.r_[True, st[:-1] != -1]
    return li, si, col < 0, col > 0, 3.0


def m_tsmom(x, days):
    mom = np.sign(x.d1["close"] - x.d1["close"].shift(days))
    s = x.d1_map(mom)
    prev = np.r_[np.nan, s[:-1]]
    return (s == 1) & (prev != 1) & x.last, (s == -1) & (prev != -1) & x.last, s == -1, s == 1, 8.0


def m_volbreak(x, k):
    d = x.d1
    rng = x.d1_map(d["high"] - d["low"])                  # rentang hari kemarin (sudah selesai)
    rng = np.where(x.last, x.d1_map((d["high"] - d["low"]).shift(1)), rng)
    op = pd.Series(np.where(x.first, x.b.o, np.nan)).ffill().to_numpy()
    c = x.c
    return c > op + k * rng, c < op - k * rng, x.last, x.last, 2.0


def m_orb(x):
    """London breakout: rentang 00-07 UTC, tembus antara 07-12 UTC, tutup 20 UTC."""
    b = x.b
    asia = (x.hour < 7)
    grp = pd.Series(x.day)
    hi = pd.Series(np.where(asia, b.h, np.nan)).groupby(grp.values).cummax().to_numpy()
    lo = pd.Series(np.where(asia, b.l, np.nan)).groupby(grp.values).cummin().to_numpy()
    hi = pd.Series(hi).groupby(grp.values).ffill().to_numpy()
    lo = pd.Series(lo).groupby(grp.values).ffill().to_numpy()
    win = (x.hour >= 7) & (x.hour < 12)
    ex = (x.hour >= 20) | x.last
    return win & (b.c > hi), win & (b.c < lo), ex, ex, 2.0


def m_inside_bar(x):
    d = x.d1
    ib = (d["high"] < d["high"].shift(1)) & (d["low"] > d["low"].shift(1))
    hi, lo = x.d1_map(d["high"].where(ib)), x.d1_map(d["low"].where(ib))
    # hari setelah inside bar: tembus high/low inside bar
    after = ~x.last
    return after & (x.c > hi), after & (x.c < lo), x.last, x.last, 2.0


def m_rsi2(x, lvl):
    c = x.c
    r = x.get("rsi2", lambda: rsi(c, 2))
    tr = x.get("sma200", lambda: sma(c, 200))
    s5 = sma(c, 5)
    return (c > tr) & (r < lvl), (c < tr) & (r > 100 - lvl), c > s5, c < s5, 3.0, None, 24


def m_rsi14(x, trend):
    c = x.c
    r = x.get("rsi14", lambda: rsi(c, 14))
    tr = x.get("ema200", lambda: ema(c, 200))
    ok_l = (c > tr) if trend else True
    ok_s = (c < tr) if trend else True
    return cross_up(r, np.full_like(r, 30)) & ok_l, cross_dn(r, np.full_like(r, 70)) & ok_s, r > 50, r < 50, 2.0, None, 48


def m_bb_fade(x, k):
    c = x.c
    m = sma(c, 20)
    sd = pd.Series(c).rolling(20).std().to_numpy()
    tr = x.get("ema200", lambda: ema(c, 200))
    return (c > tr) & (c < m - k * sd), (c < tr) & (c > m + k * sd), c > m, c < m, 2.0, None, 48


def m_stoch(x):
    b = x.b
    ll, hh = pd.Series(b.l).rolling(14).min().to_numpy(), pd.Series(b.h).rolling(14).max().to_numpy()
    k = 100 * (b.c - ll) / np.maximum(hh - ll, 1e-9)
    ks = sma(k, 3)
    dd = sma(ks, 3)
    return (cross_up(ks, dd) & (ks < 20), cross_dn(ks, dd) & (ks > 80), ks > 50, ks < 50, 2.0, None, 48)


def m_cci(x, lvl):
    b = x.b
    tp = (b.h + b.l + b.c) / 3
    m = sma(tp, 20)
    md = pd.Series(tp).rolling(20).apply(lambda s: np.mean(abs(s - s.mean())), raw=True).to_numpy()
    cci = (tp - m) / (0.015 * np.maximum(md, 1e-9))
    return (cross_up(cci, np.full_like(cci, -lvl)), cross_dn(cci, np.full_like(cci, lvl)), cci > 0, cci < 0,
            2.0, None, 48)


def m_willr(x):
    b = x.b
    hh, ll = pd.Series(b.h).rolling(14).max().to_numpy(), pd.Series(b.l).rolling(14).min().to_numpy()
    w = -100 * (hh - b.c) / np.maximum(hh - ll, 1e-9)
    return (cross_up(w, np.full_like(w, -90)), cross_dn(w, np.full_like(w, -10)), w > -50, w < -50, 2.0, None, 48)


def m_zscore(x, z):
    c = x.c
    m = sma(c, 50)
    sd = pd.Series(c).rolling(50).std().to_numpy()
    zz = (c - m) / np.maximum(sd, 1e-12)
    return zz < -z, zz > z, zz > 0, zz < 0, 2.5, None, 72


def m_pivot(x):
    d = x.d1
    p = (d["high"] + d["low"] + d["close"]) / 3
    r1, s1 = x.d1_map(2 * p - d["low"]), x.d1_map(2 * p - d["high"])
    pp = x.d1_map(p)
    c = x.c
    return (cross_up(c, s1), cross_dn(c, r1), (c > pp) | x.last, (c < pp) | x.last, 2.0)


def m_engulf(x):
    d = x.d1
    bull = (d["close"] > d["open"]) & (d["open"].shift(1) > d["close"].shift(1)) & \
           (d["close"] > d["open"].shift(1)) & (d["open"] < d["close"].shift(1))
    bear = (d["close"] < d["open"]) & (d["open"].shift(1) < d["close"].shift(1)) & \
           (d["close"] < d["open"].shift(1)) & (d["open"] > d["close"].shift(1))
    tr = d["close"] > d["close"].rolling(50).mean()
    return x.d1_event(bull & tr), x.d1_event(bear & ~tr), np.zeros(x.b.n, bool), np.zeros(x.b.n, bool), 6.0, None, 72


def m_pinbar(x):
    d = x.d1
    body = (d["close"] - d["open"]).abs()
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    low_tail = np.minimum(d["open"], d["close"]) - d["low"]
    up_tail = d["high"] - np.maximum(d["open"], d["close"])
    bull = (low_tail > 2 * body) & (low_tail > 0.6 * rng)
    bear = (up_tail > 2 * body) & (up_tail > 0.6 * rng)
    return x.d1_event(bull), x.d1_event(bear), np.zeros(x.b.n, bool), np.zeros(x.b.n, bool), 6.0, None, 72


def m_turn_of_month(x):
    day = x.day
    month = day.month
    last_bday = pd.Series(day).groupby([day.year, month]).transform("max").to_numpy()
    is_last_day = (day.to_numpy() == last_bday) & x.last
    nothing = np.zeros(x.b.n, bool)
    return is_last_day, nothing, nothing, nothing, 8.0, None, 24 * 4


def m_overnight(x):
    """Beli di close 20:00 UTC, jual 13:00 UTC (drift di luar jam sesi AS)."""
    buy = x.hour == 20
    sell = x.hour == 13
    nothing = np.zeros(x.b.n, bool)
    return buy, nothing, sell, nothing, 3.0, None, 24


def m_gap_fade(x):
    b = x.b
    gap_h = np.r_[99.0, (b.t[1:] - b.t[:-1]).total_seconds() / 3600.0]
    first = gap_h > 12
    prev_c = np.r_[b.c[0], b.c[:-1]]
    g = (b.o - prev_c) / np.maximum(b.atr, 1e-12)
    # sinyal di close candle pertama pekan bila gap > 1 ATR H1: lawan arah gap
    li = first & (g < -1.0)
    si = first & (g > 1.0)
    fri = pd.Series(np.where(first, prev_c, np.nan)).ffill().to_numpy()      # close Jumat
    return li, si, b.c >= fri, b.c <= fri, 2.0, None, 12


METHODS = {
    # tren & breakout
    "Donchian": (m_donchian, [dict(n=n) for n in (20, 55, 120)]),
    "Turtle D1": (m_turtle_d1, [dict(n=n) for n in (20, 55)]),
    "EMA cross": (m_ema_cross, [dict(f=20, s=50), dict(f=50, s=200)]),
    "Triple MA": (m_triple_ma, [{}]),
    "Supertrend": (m_supertrend, [dict(mult=m) for m in (3, 4)]),
    "Parabolic SAR": (m_psar, [dict(step=s) for s in (0.01, 0.02)]),
    "Ichimoku": (m_ichimoku, [{}]),
    "ADX/DMI": (m_adx, [dict(lvl=v) for v in (20, 25)]),
    "Keltner breakout": (m_keltner, [dict(mult=m) for m in (2.0, 3.0)]),
    "Bollinger squeeze": (m_bb_squeeze, [{}]),
    "MACD + tren": (m_macd, [{}]),
    "Aroon": (m_aroon, [{}]),
    "Hull MA": (m_hull, [dict(n=n) for n in (55, 100)]),
    "Heikin-Ashi": (m_heikin, [{}]),
    "Momentum D1": (m_tsmom, [dict(days=d) for d in (20, 60, 120)]),
    "Volatility breakout": (m_volbreak, [dict(k=k) for k in (0.3, 0.6)]),
    "London breakout": (m_orb, [{}]),
    "Inside bar D1": (m_inside_bar, [{}]),
    # oscillator & mean-reversion
    "RSI(2) Connors": (m_rsi2, [dict(lvl=v) for v in (5, 10)]),
    "RSI(14) 30/70": (m_rsi14, [dict(trend=t) for t in (False, True)]),
    "Bollinger fade": (m_bb_fade, [dict(k=k) for k in (2.0, 2.5)]),
    "Stochastic": (m_stoch, [{}]),
    "CCI": (m_cci, [dict(lvl=v) for v in (100, 200)]),
    "Williams %R": (m_willr, [{}]),
    "Z-score": (m_zscore, [dict(z=z) for z in (2.0, 2.5)]),
    "Pivot S1/R1": (m_pivot, [{}]),
    # pola candle
    "Engulfing D1": (m_engulf, [{}]),
    "Pin bar D1": (m_pinbar, [{}]),
    # waktu & musiman
    "Turn of month": (m_turn_of_month, [{}]),
    "Overnight drift": (m_overnight, [{}]),
    "Gap fade pekan": (m_gap_fade, [{}]),
}
GROUP = {k: g for g, ks in {
    "tren": ["Donchian", "Turtle D1", "EMA cross", "Triple MA", "Supertrend", "Parabolic SAR", "Ichimoku",
             "ADX/DMI", "Keltner breakout", "Bollinger squeeze", "MACD + tren", "Aroon", "Hull MA", "Heikin-Ashi",
             "Momentum D1", "Volatility breakout", "London breakout", "Inside bar D1"],
    "mean-rev": ["RSI(2) Connors", "RSI(14) 30/70", "Bollinger fade", "Stochastic", "CCI", "Williams %R",
                 "Z-score", "Pivot S1/R1"],
    "candle": ["Engulfing D1", "Pin bar D1"],
    "waktu": ["Turn of month", "Overnight drift", "Gap fade pekan"]}.items() for k in ks}


def tstat(r):
    return float(r.mean() / (r.std() or 1e-9) * math.sqrt(len(r))) if len(r) > 1 else 0.0


def summarize(tr):
    r = np.array([x[2] for x in tr])
    if len(r) == 0:
        return dict(n=0, win=0.0, avg=0.0, total=0.0, pf=0.0, t=0.0, yrs=0.0)
    yrs = pd.Series(r, index=[x[1].year for x in tr]).groupby(level=0).sum()
    return dict(n=len(r), win=float((r > 0).mean() * 100), avg=float(r.mean()), total=float(r.sum()),
                pf=float(r[r > 0].sum() / max(-r[r < 0].sum(), 1e-9)), t=tstat(r), yrs=float((yrs > 0).mean() * 100))


def run_instrument(name):
    h1, spread, start, split = instrument(name)
    h1 = h1[(h1.index >= pd.Timestamp(start, tz="UTC")) & (h1["high"] > h1["low"])]
    x = Ctx(h1, spread)
    split = pd.Timestamp(split, tz="UTC")
    rows, trades = [], {}
    for meth, (fn, grid) in METHODS.items():
        best = None
        for p in grid:
            try:
                sig = fn(x, **p)
            except Exception as exc:  # noqa: BLE001
                print(f"{name} {meth} {p}: {exc}", file=sys.stderr)
                continue
            li, si, lo, so, sl = sig[:5]
            mh = sig[6] if len(sig) > 6 else None
            for tp in (None, 1.0, 2.0):                      # keluar sinyal / TP 1R / TP 2R
                tr = backtest(x.b, np.asarray(li, bool), np.asarray(si, bool), np.asarray(lo, bool),
                              np.asarray(so, bool), sl, tp, mh)
                dev = [t for t in tr if t[0] < split]
                tst = [t for t in tr if t[0] >= split]
                sd = summarize(dev)
                if sd["n"] >= 30 and (best is None or sd["t"] > best[1]["t"]):
                    best = ({**p, "tp": tp}, sd, summarize(tst), tst, dev)
        if best:
            rows.append(dict(inst=name, method=meth, group=GROUP[meth], params=str(best[0]),
                             **{f"latih_{k}": v for k, v in best[1].items()},
                             **{f"uji_{k}": v for k, v in best[2].items()}))
            trades[(name, meth)] = (best[4], best[3])
    print(f"selesai {name}", flush=True)
    return rows, trades


def main():
    with Pool(4) as pool:
        out = pool.map(run_instrument, NAMES)
    rows = [r for o in out for r in o[0]]
    trades = {k: v for o in out for k, v in o[1].items()}
    df = pd.DataFrame(rows)
    df.to_pickle(DATA / "world_lab.pkl")
    pd.to_pickle(trades, DATA / "world_lab_trades.pkl")
    print(f"\n{len(df)} pasangan (instrumen, metode) diuji")


if __name__ == "__main__":
    main()
