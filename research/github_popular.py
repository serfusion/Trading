"""Uji ulang strategi dari repo GitHub XAUUSD paling populer (python -m research.github_popular).

Setiap strategi ditulis ulang sedekat mungkin dengan kode aslinya, lalu dijalankan di 4 periode
data asli (2012-17, 2018-22, 2022-25, 2025-26) dengan spread, entry di open bar berikutnya,
SL dicek lebih dulu, dan tanpa look-ahead. Hasil dalam R (kelipatan risiko awal).

| Repo (bintang, per 26 Sep 2026)                        | Klaim penulis                         |
|--------------------------------------------------------|---------------------------------------|
| yulz008/GOLD_ORB (297)                                 | Opening Range Breakout H1             |
| 3aLaee/xauusd-trading-bot (175)                        | MACD M1, SL 1,5 / TP 1,0              |
| ilahuerta-IA/backtrader-pullback-window-xauusd (75)    | WR 55%, PF 1,64, 2020-25              |
| a1shmuk/xauusd-algo-trader (10)                        | WR 61,4%, PF 2,48, 2024-26            |
| foeed/FvgGold-EA (36)                                  | FVG M15 RR 1,5, +48,7% 6 bulan        |
| GifariKemal/xaubot-ai (83), triqbit (148), dst.        | ML/XGBoost: WR 64%, PF 2,64           |
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from xau_bot.smc import swing_mask

from .data import load_parquet_utc, resample
from .harness import (Arrays, Period, fmt, last_base_of, periods, server_time, simulate, stats,
                      to_base, trades_frame)

DATA = Path(os.getenv("XAU_DATA_DIR", "data/research"))


# ---------------------------------------------------------------- indikator
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def wilder(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up, dn = wilder(np.clip(d, 0, None), n), wilder(np.clip(-d, 0, None), n)
    return 100 - 100 / (1 + up / np.where(dn == 0, np.nan, dn))


def atr_w(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return wilder(tr, n)


def cross_up(a, b):
    return (a > b) & np.r_[False, a[:-1] <= b[:-1]]


def cross_dn(a, b):
    return (a < b) & np.r_[False, a[:-1] >= b[:-1]]


def bars_per_hour(p: Period) -> int:
    return 12 if p.tf == "M5" else 4


# ---------------------------------------------------------------- 1. GOLD_ORB
def gold_orb(p: Period, scaled: bool = False) -> pd.DataFrame:
    """yulz008/GOLD_ORB: range dari candle H1 pertama hari (01:00 server), diperbarui sampai 3 candle
    tidak membuat high/low baru; BUY bila candle naik close di atas range (SELL sebaliknya),
    maks 1 BUY + 1 SELL per hari, SL 400 point ($4), TP 1200 ($12), trailing 700/100/10.
    `scaled`: jarak dikali harga/1800 (EA dibuat saat emas ±$1.800)."""
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hour = server_time(H.index).hour.to_numpy()
    start = to_base(p.base, H.index)
    rows, busy, active = [], -1, False
    rh = rl = rbh = rbl = 0.0
    cr = cs = 0
    long_ok = short_ok = False
    for k in range(len(H) - 1):
        f = c[k] / 1800 if scaled else 1.0
        wl = 5.0 * f
        bh, bl = max(o[k], c[k]), min(o[k], c[k])
        if hour[k] == 1:
            rh, rbh = (bh if h[k] - bh > wl else h[k]), bh
            rl, rbl = (bl if bl - l[k] > wl else l[k]), bl
            cr = cs = 1
            long_ok = short_ok = active = True
            continue
        if not active:
            continue
        rr = rs = False
        if 1 <= cr <= 3 and h[k] > rh + 0.1 and bh > rbh + 0.1:
            rh, rbh, rr = (bh if h[k] - bh > wl else h[k]), bh, True
        if 1 <= cs <= 3 and l[k] < rl - 0.1 and bl < rbl - 0.1:
            rl, rbl, rs = (bl if bl - l[k] > wl else l[k]), bl, True
        cr = 1 if rr else cr + 1
        cs = 1 if rs else cs + 1
        d = 0
        if cr > 3 and c[k] > o[k] and bh > rh and long_ok:
            d, long_ok = 1, False
        elif cs > 3 and c[k] < o[k] and bl < rl and short_ok:
            d, short_ok = -1, False
        if d == 0:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)

        def trail(j, d, entry, cur, f=f):
            if d > 0:
                new = A.h[j] - 7 * f
                return new if A.h[j] - entry >= f and new > cur + 0.1 * f else cur
            ask_low = A.l[j] + sp
            new = ask_low + 7 * f
            return new if entry - ask_low >= f and new < cur - 0.1 * f else cur

        j1, r = simulate(A, sp, j0, d, entry, entry - d * 4 * f, entry + d * 12 * f,
                         5 * 24 * bars_per_hour(p), trail=trail)
        rows.append((j0, j1, d, r))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- 2. MACD scalper
def macd_scalper(df: pd.DataFrame, sp: float, sl: float = 1.5, tp: float = 1.0,
                 tp_first: bool = False) -> pd.DataFrame:
    """3aLaee/xauusd-trading-bot: MACD(12,26,9) cross + histogram searah + close di dalam S/R 10 bar,
    SL 15 pip x 0,10 = $1,50, TP 10 pip = $1,00 (SL > TP). `tp_first`: batas atas optimistis."""
    A = Arrays(df)
    c = A.c
    m = ema(c, 12) - ema(c, 26)
    s = ema(m, 9)
    hist = m - s
    lo10 = pd.Series(A.l).rolling(10).min().to_numpy()
    hi10 = pd.Series(A.h).rolling(10).max().to_numpy()
    buy = cross_up(m, s) & (hist > 0) & (c > lo10)
    sell = cross_dn(m, s) & (hist < 0) & (c < hi10)
    rows, busy = [], -1
    for k in np.flatnonzero(buy | sell):
        j0 = k + 1
        if j0 <= busy or j0 >= A.n - 2:
            continue
        d = 1 if buy[k] else -1
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, r = simulate(A, sp, j0, d, entry, entry - d * sl, entry + d * tp, 2000, tp_first=tp_first)
        rows.append((j0, j1, d, r))
        busy = j1
    return trades_frame(rows, df)


# ---------------------------------------------------------------- 3. a1shmuk EMA/RSI/H4
A1 = dict(ema_fast=9, ema_slow=21, rsi_ob=70, rsi_os=30, sl=1.5, tp=3.0, lb=5, s0=8, s1=17)


def _a1_indicators(H: pd.DataFrame, lookahead: bool):
    c = H["close"].to_numpy(float)
    e9, e21 = ema(c, A1["ema_fast"]), ema(c, A1["ema_slow"])
    pos = np.where(e9 > e21, 1, -1)
    bull = (pos == 1) & (np.r_[0, pos[:-1]] == -1)
    bear = (pos == -1) & (np.r_[0, pos[:-1]] == 1)
    r = rsi(c)
    a = atr_w(H, 14)
    h4 = resample(H, "240min")
    h4_bull = pd.Series(h4["close"].to_numpy() > ema(h4["close"].to_numpy(float), 50), index=h4.index)
    if not lookahead:  # hanya bar H4 yang sudah tertutup
        h4_bull = pd.Series(h4_bull.to_numpy(), index=h4.index + pd.Timedelta(hours=4))
    h4b = h4_bull.reindex(H.index, method="ffill").fillna(False).to_numpy(bool)
    srv = server_time(H.index)
    sess = (srv.hour >= A1["s0"]) & (srv.hour < A1["s1"]) & (srv.dayofweek < 5)
    lb = A1["lb"]
    hi, lo = H["high"].to_numpy(float), H["low"].to_numpy(float)
    sl_mask, sh_mask = swing_mask(lo, lb, "low"), swing_mask(hi, lb, "high")
    sl_s, sh_s = np.full(len(H), np.nan), np.full(len(H), np.nan)
    shift = 0 if lookahead else lb  # swing baru pasti setelah lb bar di kanannya
    idx = np.flatnonzero(sl_mask) + shift
    sl_s[idx[idx < len(H)]] = lo[np.flatnonzero(sl_mask)][idx < len(H)]
    idx = np.flatnonzero(sh_mask) + shift
    sh_s[idx[idx < len(H)]] = hi[np.flatnonzero(sh_mask)][idx < len(H)]
    return (c, bull, bear, r, a, h4b, np.asarray(sess), pd.Series(sl_s).ffill().to_numpy(),
            pd.Series(sh_s).ffill().to_numpy())


def _a1_entry(k, c, bull, bear, r, a, h4b, sess, swl, swh, entry):
    sig = 1 if bull[k] else -1
    rsi_ok = (50 < r[k] < 70) if sig > 0 else (30 < r[k] < 50)
    mtf_ok = h4b[k] if sig > 0 else not h4b[k]
    if int(rsi_ok) + int(mtf_ok) + int(sess[k]) < 2:
        return None
    atr_sl = entry - sig * A1["sl"] * a[k]
    tp = entry + sig * A1["tp"] * a[k]
    st = swl[k] - 0.5 if sig > 0 else swh[k] + 0.5
    sl = atr_sl if np.isnan(st) else (max(st, atr_sl) if sig > 0 else min(st, atr_sl))
    if abs(entry - sl) < 0.1:
        return None
    return sig, sl, tp


def a1shmuk_published(p: Period) -> pd.DataFrame:
    """Port apa adanya dari backtest_engine.py penulis: swing memakai bar masa depan, H4 memakai
    close H4 yang belum terjadi, TP diperiksa sebelum SL, semua di bar H1 (tanpa resolusi intrabar)."""
    H = resample(p.base, "60min")
    c, bull, bear, r, a, h4b, sess, swl, swh = _a1_indicators(H, lookahead=True)
    hi, lo = H["high"].to_numpy(float), H["low"].to_numpy(float)
    rows, tr = [], None
    for i in range(50, len(H)):
        if tr:
            d, e, sl, tp, i0 = tr
            hit_sl = lo[i] <= sl if d > 0 else hi[i] >= sl
            hit_tp = hi[i] >= tp if d > 0 else lo[i] <= tp
            rx = (d < 0 and r[i] <= 30) or (d > 0 and r[i] >= 70)
            ex = (d < 0 and bull[i]) or (d > 0 and bear[i])
            if hit_tp or hit_sl or rx or ex:
                px = tp if hit_tp else (sl if hit_sl else c[i])
                rows.append((i0, i, d, (px - e) * d / abs(e - sl)))
                tr = None
            continue
        if not (bull[i] or bear[i]):
            continue
        sig = 1 if bull[i] else -1
        e = c[i] + (p.spread if sig > 0 else -p.spread)
        got = _a1_entry(i, c, bull, bear, r, a, h4b, sess, swl, swh, e)
        if got:
            tr = (got[0], e, got[1], got[2], i)
    t = pd.DataFrame(rows, columns=["j0", "j1", "dir", "R"])
    t["time"] = H.index[t.j0.to_numpy()] if len(t) else []
    return t


def a1shmuk_fixed(p: Period) -> pd.DataFrame:
    """Aturan sama, tanpa look-ahead: swing & H4 hanya yang sudah pasti, entry di open H1 berikutnya
    (+spread), SL/TP dicek di candle dasar dengan SL lebih dulu, keluar RSI/EMA di open berikutnya."""
    H = resample(p.base, "60min")
    c, bull, bear, r, a, h4b, sess, swl, swh = _a1_indicators(H, lookahead=False)
    A, sp = Arrays(p.base), p.spread
    start, last = to_base(p.base, H.index), last_base_of(p.base, H)
    ex_long = np.zeros(A.n, bool)
    ex_short = np.zeros(A.n, bool)
    ex_long[last[(r >= 70) | bear]] = True
    ex_short[last[(r <= 30) | bull]] = True
    rows, busy = [], -1
    for k in np.flatnonzero(bull | bear):
        if k < 50 or k + 1 >= len(H):
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        sig = 1 if bull[k] else -1
        entry = A.o[j0] + (sp if sig > 0 else 0.0)
        got = _a1_entry(k, c, bull, bear, r, a, h4b, sess, swl, swh, entry)
        if not got:
            continue
        d, sl, tp = got
        j1, rr = simulate(A, sp, j0, d, entry, sl, tp, 30 * 24 * bars_per_hour(p),
                          exit_mask=ex_long if d > 0 else ex_short)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- 4. Pullback window
def pullback_window(p: Period, scaled: bool = False) -> pd.DataFrame:
    """ilahuerta-IA/backtrader-pullback-window-xauusd (M5, LONG saja, parameter default repo):
    close memotong ke atas EMA14/EMA24, close > EMA100, ATR(10) <= 2,00 -> ARMED; tepat 3 candle
    merah berturut-turut -> jendela 1 bar: high >= high candle pullback terakhir -> entry di open
    berikutnya bila kenaikan ATR sejak sinyal 0,2-1,6; SL 4,5xATR, TP 6,5xATR.
    `scaled`: ambang ATR dikali harga/2000 (median harga data 2020-25 milik penulis)."""
    df = p.base
    A, sp = Arrays(df), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    e14, e24, e100 = ema(c, 14), ema(c, 24), ema(c, 100)
    a = atr_w(df, 10)
    cross = cross_up(c, e14) | cross_up(c, e24)
    rows, busy = [], -1
    state, pb, sig_atr, top, bottom, wexp = "scan", 0, 0.0, 0.0, 0.0, 0
    for k in range(101, A.n - 2):
        f = c[k] / 2000 if scaled else 1.0
        if state == "window":
            if k > wexp:
                state, pb = "armed", 0
            elif h[k] >= top:
                inc = a[k] - sig_atr
                j0 = k + 1
                if 0.2 * f <= inc <= 1.6 * f and j0 > busy:
                    entry = o[j0] + sp
                    j1, r = simulate(A, sp, j0, 1, entry, entry - 4.5 * a[k], entry + 6.5 * a[k], 20000)
                    rows.append((j0, j1, 1, r))
                    busy = j1
                state = "scan"
                continue
            elif l[k] <= bottom:
                state, pb = "armed", 0
            continue
        if state == "armed":
            if c[k] < o[k]:
                pb += 1
                if pb >= 3:
                    rng = h[k] - l[k]
                    top, bottom, wexp, state = h[k] + rng * 0.001, l[k] - rng * 0.001, k + 1, "window"
                continue
            state = "scan"
        if state == "scan" and cross[k] and c[k] > e100[k] and a[k] <= 2.0 * f:
            state, pb, sig_atr = "armed", 0, a[k]
    return trades_frame(rows, df)


# ---------------------------------------------------------------- 5. FVG RR 1,5
def fvg_gold(p: Period, ref_price: float) -> pd.DataFrame:
    """foeed/FvgGold-EA (M15): FVG 3 candle, skor 0-100 (ukuran gap/ATR, displacement, searah EMA50/200
    H1, premium/discount terhadap EMA50 H1) >= 50, hanya killzone 07-10 & 12-16 GMT, limit di tepi FVG
    + buffer/2, SL di balik tepi + buffer 3,0, TP 1,5R, BE saat profit 0,5xATR, 1 posisi.
    Buffer diskalakan harga / `ref_price` (median harga periode optimasi penulis, Jan-Jul 2026)."""
    df = resample(p.base, "15min") if p.tf == "M5" else p.base
    A, sp = Arrays(df), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    a = atr_w(df, 14)
    H = resample(df, "60min")
    hc = H["close"].to_numpy(float)
    e50 = pd.Series(ema(hc, 50), index=H.index + pd.Timedelta(hours=1)).reindex(df.index, method="ffill").to_numpy()
    e200 = pd.Series(ema(hc, 200), index=H.index + pd.Timedelta(hours=1)).reindex(df.index, method="ffill").to_numpy()
    hr = df.index.hour
    kz = ((hr >= 7) & (hr < 10)) | ((hr >= 12) & (hr < 16))
    rows, busy = [], -1
    for k in range(250, A.n - 2):
        if not kz[k] or k < busy or np.isnan(e200[k]):
            continue
        d = 1 if l[k] > h[k - 2] else (-1 if h[k] < l[k - 2] else 0)
        if d == 0:
            continue
        gap = (l[k] - h[k - 2]) if d > 0 else (l[k - 2] - h[k])
        rng = h[k - 1] - l[k - 1]
        disp = abs(c[k - 1] - o[k - 1]) / rng if rng > 0 else 0.0
        buf = 3.0 * c[k] / ref_price
        edge = h[k - 2] if d > 0 else l[k - 2]
        entry = edge + d * buf / 2
        score = min(30.0, 30 * gap / a[k]) + 30 * disp
        score += 20 if (e50[k] > e200[k]) == (d > 0) else 0
        score += 10  # FVG baru terbentuk
        score += 10 if (entry < e50[k]) == (d > 0) else 0
        if score < 50:
            continue
        sl = edge - d * buf
        tp = entry + d * 1.5 * abs(entry - sl)
        for j in range(k + 1, min(k + 17, A.n - 2)):  # limit berlaku 4 jam
            if (h[j] >= tp) if d > 0 else (l[j] + sp <= tp):
                break  # target tercapai sebelum terisi -> batal
            if (l[j] + sp <= entry) if d > 0 else (h[j] >= entry):
                fill = min(entry, o[j] + sp) if d > 0 else max(entry, o[j])
                j1, r = simulate(A, sp, j, d, fill, sl, tp, 96 * 5, be_at=0.5 * a[k] / abs(fill - sl),
                                 fill_mid_bar=True)
                rows.append((j, j1, d, r))
                busy = j1 + 1
                break
    return trades_frame(rows, df)


# ---------------------------------------------------------------- 6. ML walk-forward
def ml_features(H: pd.DataFrame) -> pd.DataFrame:
    c = H["close"].to_numpy(float)
    a = atr_w(H, 14)
    na = a / c
    f = {f"ret{n}": np.log(c / np.r_[np.full(n, np.nan), c[:-n]]) / na for n in (1, 3, 6, 12, 24, 48, 120)}
    f["rsi"] = rsi(c)
    for n in (20, 50, 200):
        f[f"ema{n}"] = (c - ema(c, n)) / a
    f["vol"] = a / wilder(np.r_[a], 100)
    f["hour"] = H.index.hour
    f["dow"] = H.index.dayofweek
    return pd.DataFrame(f, index=H.index)


def ml_prob(H: pd.DataFrame, horizon: int = 12, train_years: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Model gradient boosting (setara XGBoost di xaubot-ai / triqbit) memprediksi arah `horizon` jam ke
    depan. Dilatih ulang tiap kuartal hanya dengan data sebelum kuartal itu (label yang sudah diketahui).
    Return (prob_naik, label) per bar H1; NaN = belum ada model."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    X = ml_features(H)
    c = H["close"].to_numpy(float)
    fwd = np.r_[c[horizon:], np.full(horizon, np.nan)] - c
    y = (fwd > 0).astype(float)
    y[np.isnan(fwd)] = np.nan
    prob = np.full(len(H), np.nan)
    quarters = pd.date_range(H.index[0] + pd.DateOffset(years=train_years), H.index[-1], freq="QS", tz="UTC")
    for q0, q1 in zip(quarters, list(quarters[1:]) + [H.index[-1] + pd.Timedelta(hours=1)]):
        tr = (H.index >= q0 - pd.DateOffset(years=train_years)) & (H.index < q0 - pd.Timedelta(hours=horizon))
        tr &= ~np.isnan(y) & X.notna().all(axis=1).to_numpy()
        te = (H.index >= q0) & (H.index < q1)
        if tr.sum() < 2000 or te.sum() == 0:
            continue
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=31,
                                           l2_regularization=1.0, random_state=0)
        m.fit(X[tr], y[tr])
        prob[te] = m.predict_proba(X[te])[:, 1]
    return prob, y


def ml_walkforward(H: pd.DataFrame, sp_of, horizon: int = 12, thr: float = 0.55) -> tuple[pd.DataFrame, dict]:
    """Trade bila prob > thr (BUY) / < 1-thr (SELL), SL 2xATR, keluar setelah `horizon` jam."""
    prob, y = ml_prob(H, horizon)
    A = Arrays(H)
    a = atr_w(H, 14)
    rows, busy = [], -1
    for k in np.flatnonzero(~np.isnan(prob)):
        if k + 1 <= busy or k + horizon + 2 >= A.n:
            continue
        d = 1 if prob[k] > thr else (-1 if prob[k] < 1 - thr else 0)
        if d == 0:
            continue
        sp = sp_of(H.index[k])
        j0 = k + 1
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, r = simulate(A, sp, j0, d, entry, entry - d * 2 * a[k], None, horizon - 1)
        rows.append((j0, j1, d, r))
        busy = j1
    t = trades_frame(rows, H)
    ok = ~np.isnan(prob) & ~np.isnan(y)
    acc = {"akurasi": float(((prob[ok] > 0.5) == (y[ok] > 0.5)).mean()), "n_prediksi": int(ok.sum())}
    return t, acc


# ---------------------------------------------------------------- pembanding
def donchian_f_ensemble(p: Period) -> np.ndarray:
    """Skema bot sekarang, trade diurutkan menurut waktu (drawdown kronologis)."""
    from .combine import ensemble
    return ensemble(resample(p.base, "60min"), p.spread, f_legs=5).R.to_numpy()


def buy_hold(p: Period) -> str:
    c = p.base["close"]
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    tot = c.iloc[-1] / c.iloc[0] - 1
    dd = (c / c.cummax() - 1).min()
    return f"{c.iloc[0]:7.0f} -> {c.iloc[-1]:7.0f}  {tot * 100:+6.1f}% ({((1 + tot) ** (1 / yrs) - 1) * 100:+.1f}%/th), DD {dd * 100:.0f}%"


# ---------------------------------------------------------------- main
def main():
    ps = periods()
    ref = float(ps[3].base.loc["2026-01":"2026-07", "close"].median())
    out: dict[str, dict[str, pd.DataFrame]] = {}

    def show(name, fn, only=None):
        print(name)
        out[name] = {}
        for p in ps:
            if only and p.tf not in only:
                print(f"   {p.name}: - (butuh data {'/'.join(only)})")
                continue
            t = fn(p)
            out[name][p.name] = t
            print(f"   {p.name}: {fmt(stats(t.R))}")

    print("Beli & tahan emas fisik (tanpa leverage)")
    for p in ps:
        print(f"   {p.name}: {buy_hold(p)}")
    print("PEMBANDING - bot ini: F-ensemble Donchian H1 (3 set)")
    for p in ps:
        print(f"   {p.name}: {fmt(stats(donchian_f_ensemble(p)))}")

    show("1. GOLD_ORB asli (SL $4 / TP $12, trailing)", gold_orb)
    show("1b. GOLD_ORB diskalakan harga", lambda p: gold_orb(p, scaled=True))
    show("3a. a1shmuk seperti diterbitkan (ada look-ahead)", a1shmuk_published)
    show("3b. a1shmuk tanpa look-ahead", a1shmuk_fixed)
    show("4. Pullback window asli (ATR <= 2,00)", pullback_window, only=["M5"])
    show("4b. Pullback window diskalakan harga", lambda p: pullback_window(p, scaled=True), only=["M5"])
    show(f"5. FVG RR 1,5 killzone (buffer 3,0 @ ${ref:.0f})", lambda p: fvg_gold(p, ref))
    show("2b. MACD scalper di M5 (SL $1,5 / TP $1)", lambda p: macd_scalper(p.base, p.spread), only=["M5"])

    print("2. MACD scalper M1 asli, data M1 Feb-Mei 2026")
    m1 = load_parquet_utc(DATA / "Sai310421_xauusd-data/parquet/XAUUSD_M1_90d_20260526.parquet")
    for sp in (0.0, 0.15, 0.25):
        print(f"   spread {sp:.2f}: {fmt(stats(macd_scalper(m1, sp).R))}")
        print(f"      TP dulu (optimistis): {fmt(stats(macd_scalper(m1, sp, tp_first=True).R))}")

    print("6. ML gradient boosting walk-forward (arah 12 jam, prob > 0,55)")
    H = pd.concat([resample(p.base, "60min") for p in ps])
    H = H[~H.index.duplicated()]
    spread_of = lambda t: 0.30 if t < ps[2].base.index[0] else 0.25  # noqa: E731
    t, acc = ml_walkforward(H, spread_of)
    print(f"   akurasi arah: {acc['akurasi'] * 100:.1f}% dari {acc['n_prediksi']} prediksi")
    out["6. ML"] = {}
    for p in ps:
        tt = t[(t.time >= p.base.index[0]) & (t.time <= p.base.index[-1])]
        out["6. ML"][p.name] = tt
        print(f"   {p.name}: {fmt(stats(tt.R))}")

    if len(sys.argv) > 1:
        with open(sys.argv[1], "wb") as fh:
            pickle.dump(out, fh)


if __name__ == "__main__":
    main()
