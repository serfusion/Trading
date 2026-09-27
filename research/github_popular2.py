"""Uji ulang strategi dari daftar 63 repo kiriman pengguna (python -m research.github_popular2 [out.pkl]).

Hanya repo yang aturannya jelas & bisa ditulis ulang. Kode repo TIDAK dijalankan; aturannya ditulis ulang di
mesin uji yang sama (research/harness.py: spread, entry di open berikutnya, SL dicek dulu, tanpa look-ahead).

| Port                     | Repo                                   | Inti aturan (default repo)                              |
|--------------------------|----------------------------------------|---------------------------------------------------------|
| ema_rsi_h4               | Aniket-Jaiswal2002/xauusd-trading-bot  | H4 EMA13/34 cross, RSI<65/>35, SL 2 ATR, TP 3,5, trail 1 |
| breakout_adx             | Turnipnator/Oanda_Gold                 | H1 tembus high/low 10 bar + ADX>=35, SL $3 = TP $3       |
| pdh_retest               | phatnomenal/blackXAU_AUTOMATED-BOT     | tembus high kemarin (M5) -> retest -> BUY, SL 1,5 / TP 3 ATR H1 |
| sma_pullback             | sagarmeravi/XAUUSD-Pullback-Strategy   | LONG bila close>SMA200 & <SMA10, keluar close>SMA10       |
| keltner_live / _simple   | samw2591/gold-quant-trading (+jlvalaty)| H1 Keltner EMA25+-1,2ATR, ADX>=18, EMA100; SL 4,5 ATR     |
| orb_ny                   | samw2591/gold-quant-trading            | range 15 menit NY open, SL 0,75x range, TP 3x, 1x/hari    |
| rsi2_m15                 | samw2591/gold-quant-trading            | M15 RSI(2)<15 / >85 searah SMA50 & EMA100, keluar RSI 55/45 |
| mr_grid                  | BlamzKunG/XAUUSD-Grid-EA               | M15 RSI35/65 + BB, ADX H1<28, grid 5 level, SL darurat   |
"""
from __future__ import annotations

import pickle
import sys

import numpy as np
import pandas as pd

from .data import resample
from .github_popular import atr_w, ema, rsi, wilder
from .harness import Arrays, Period, fmt, periods, server_time, simulate, stats, to_base, trades_frame


def sma_range_atr(df, n=14):
    return (df["high"] - df["low"]).rolling(n).mean().to_numpy()


def sma_tr_atr(df, n=14):
    """iATR MetaTrader = SMA dari true range."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()


def adx_w(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    up, dn = np.diff(h, prepend=h[0]), -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = wilder(tr, n)
    pdi = 100 * wilder(pdm, n) / np.where(atr == 0, np.nan, atr)
    mdi = 100 * wilder(mdm, n) / np.where(atr == 0, np.nan, atr)
    dx = 100 * abs(pdi - mdi) / np.where(pdi + mdi == 0, np.nan, pdi + mdi)
    return wilder(np.nan_to_num(dx), n)


def htf_on(base: pd.DataFrame, htf: pd.DataFrame, values: np.ndarray, hours: float) -> np.ndarray:
    """Nilai indikator timeframe besar yang SUDAH tertutup, dipetakan ke bar dasar."""
    s = pd.Series(values, index=htf.index + pd.Timedelta(hours=hours))
    return s.reindex(base.index, method="ffill").to_numpy()


def bph(p: Period) -> int:
    return 12 if p.tf == "M5" else 4


# ---------------------------------------------------------------- Aniket EMA/RSI H4
def ema_rsi_h4(p: Period) -> pd.DataFrame:
    H = resample(p.base, "240min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    f, s = ema(c, 13), ema(c, 34)
    r = rsi(c, 14)
    a = atr_w(H, 14)
    up = (f > s) & np.r_[False, f[:-1] <= s[:-1]]
    dn = (f < s) & np.r_[False, f[:-1] >= s[:-1]]
    start = to_base(p.base, H.index)
    rows, busy = [], -1
    for k in np.flatnonzero(up | dn):
        if k < 40 or k + 1 >= len(H):
            continue
        d = 1 if up[k] else -1
        if (d > 0 and r[k] >= 65) or (d < 0 and r[k] <= 35):
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        atr_k = a[k]

        def trail(j, d, entry, cur, atr_k=atr_k):  # SL = harga - 1 ATR bila lebih baik
            new = A.c[j] - atr_k if d > 0 else A.c[j] + sp + atr_k
            return max(cur, new) if d > 0 else min(cur, new)

        j1, rr = simulate(A, sp, j0, d, entry, entry - d * 2 * atr_k, entry + d * 3.5 * atr_k,
                          60 * 24 * bph(p), trail=trail)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- Turnipnator breakout + ADX
def breakout_adx(p: Period, scaled: bool = False) -> pd.DataFrame:
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    h, l, c = (H[k].to_numpy(float) for k in ("high", "low", "close"))
    hi = pd.Series(h).rolling(10).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(10).min().shift(1).to_numpy()
    adx = adx_w(H, 14)
    start = to_base(p.base, H.index)
    rows, busy = [], -1
    for k in range(30, len(H) - 1):
        d = 1 if c[k] > hi[k] else (-1 if c[k] < lo[k] else 0)
        if d == 0 or adx[k] < 35:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        dist = 3.0 * (c[k] / 4000 if scaled else 1.0)
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, r = simulate(A, sp, j0, d, entry, entry - d * dist, entry + d * dist, 5 * 24 * bph(p))
        rows.append((j0, j1, d, r))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- phatnomenal PDH retest (BUY saja)
def pdh_retest(p: Period) -> pd.DataFrame:
    base = p.base
    A, sp = Arrays(base), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    srv = server_time(base.index)
    day = srv.normalize()
    daily = pd.DataFrame({"h": h, "l": l}, index=day).groupby(level=0).agg({"h": "max", "l": "min"})
    pdh = pd.Series(daily["h"].shift(1).to_numpy(), index=daily.index).reindex(day).to_numpy()
    H = resample(base, "60min")
    hc = H["close"].to_numpy(float)
    e50, e200 = htf_on(base, H, ema(hc, 50), 1), htf_on(base, H, ema(hc, 200), 1)
    atr_h1 = htf_on(base, H, sma_tr_atr(H, 14), 1)
    hour = srv.hour.to_numpy()
    wait_until, busy, rows = -1, -1, []
    per_bar = 5 if p.tf == "M5" else 15
    for k in range(1, A.n - 2):
        if np.isnan(pdh[k]) or np.isnan(e200[k]):
            continue
        lvl = pdh[k]
        rng = h[k] - l[k]
        body_ok = rng > 0 and abs(c[k] - o[k]) / rng >= 0.5
        if wait_until < k and c[k] > lvl and o[k] <= lvl and (body_ok or c[k] - lvl >= 2.0):
            wait_until, level = k + 24 * 60 // per_bar, lvl
            continue
        if wait_until >= k and l[k] <= level:
            if k <= busy:  # sudah ada posisi -> batal menunggu (OnlyOnePosition)
                wait_until = -1
                continue
            if not (7 <= hour[k] < 22) or not (c[k - 1] > e50[k] and c[k - 1] > e200[k]):
                continue  # filter belum lolos -> tetap menunggu retest (seperti EA)
            wait_until = -1
            entry = min(level, o[k]) + sp
            a = atr_h1[k]

            def trail(j, d, entry, cur):  # BE di +$3, trailing $1 setelah profit > $2
                prof = A.h[j] - entry
                new = cur
                if prof >= 3.0:
                    new = max(new, entry)
                if prof > 2.0:
                    new = max(new, A.h[j] - 1.0)
                return new

            j1, r = simulate(A, sp, k, 1, entry, entry - 1.5 * a, entry + 3.0 * a, 5 * 24 * 60 // per_bar,
                             trail=trail, fill_mid_bar=True)
            rows.append((k, j1, 1, r))
            busy = j1
    return trades_frame(rows, base)


# ---------------------------------------------------------------- sagarmeravi SMA pullback (LONG)
def sma_pullback(p: Period, rule: str | None = None) -> pd.DataFrame:
    df = resample(p.base, rule) if rule else p.base
    A, sp = Arrays(df), p.spread
    c = A.c
    s200 = pd.Series(c).rolling(200).mean().to_numpy()
    s10 = pd.Series(c).rolling(10).mean().to_numpy()
    rows, k = [], 201
    while k < A.n - 2:
        if not (c[k] > s200[k] and c[k] < s10[k]):
            k += 1
            continue
        j0 = k + 1
        entry = A.o[j0] + sp
        j = j0
        while j < A.n - 2 and not (c[j] > s10[j]) and (entry - c[j]) / c[j] <= 0.10:
            j += 1
        exit_px = A.o[j + 1]
        rows.append((j0, j + 1, 1, (exit_px - entry) / (0.10 * entry)))  # 1R = stop 10%
        k = j + 1
    t = trades_frame(rows, df)
    t["pct"] = t.R * 10.0  # hasil per trade dalam % harga (tanpa leverage)
    return t


# ---------------------------------------------------------------- samw2591 Keltner H1
def keltner(p: Period, live: bool = True) -> pd.DataFrame:
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    atr = sma_range_atr(H, 14)
    mid = pd.Series(c).ewm(span=25).mean().to_numpy()
    e100 = pd.Series(c).ewm(span=100).mean().to_numpy()
    adx = adx_w(H, 14)
    start = to_base(p.base, H.index)
    rows, busy = [], -1
    for k in range(110, len(H) - 1):
        if np.isnan(atr[k]) or adx[k] < 18:
            continue
        d = 1 if (c[k] > mid[k] + 1.2 * atr[k] and c[k] > e100[k]) else (
            -1 if (c[k] < mid[k] - 1.2 * atr[k] and c[k] < e100[k]) else 0)
        if d == 0:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        a = atr[k]
        sl = entry - d * min(50.0, max(10.0, 4.5 * a))
        tp = entry + d * 8.0 * a
        if live:
            state = {"best": entry}

            def trail(j, d, entry, cur, a=a, state=state):  # aktif di +0,5 ATR, jarak 0,15 ATR
                if d > 0:
                    state["best"] = max(state["best"], A.h[j])
                    return max(cur, state["best"] - 0.15 * a) if state["best"] - entry >= 0.5 * a else cur
                state["best"] = min(state["best"], A.l[j] + sp)
                return min(cur, state["best"] + 0.15 * a) if entry - state["best"] >= 0.5 * a else cur

            j1, r = simulate(A, sp, j0, d, entry, sl, tp, 3 * bph(p) - 1, trail=trail)  # stop waktu 3 jam
        else:
            j1, r = simulate(A, sp, j0, d, entry, sl, tp, 30 * 24 * bph(p))
        rows.append((j0, j1, d, r))
        busy = j1 + (2 if live else 0)  # jeda singkat setelah keluar (cooldown 30 menit)
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- samw2591 ORB NY
def orb_ny(p: Period) -> pd.DataFrame:
    base = p.base
    A, sp = Arrays(base), p.spread
    H = resample(base, "60min")
    atr_h1 = htf_on(base, H, sma_range_atr(H, 14), 1)
    idx = base.index
    minutes = idx.hour * 60 + idx.minute
    date = idx.normalize()
    step = 5 if p.tf == "M5" else 15
    rows, busy = [], -1
    for day in pd.Series(np.arange(A.n)).groupby(date).indices.values():
        rng = day[(minutes[day] >= 14 * 60) & (minutes[day] < 14 * 60 + 15)]
        if len(rng) == 0 or rng[0] <= busy:
            continue
        hi, lo = A.h[rng].max(), A.l[rng].min()
        width = hi - lo
        a = atr_h1[rng[-1]]
        if width <= 0 or np.isnan(a):
            continue
        window = day[(minutes[day] >= 14 * 60 + 15) & (minutes[day] < 16 * 60 + 15)]
        for k in window:
            d = 1 if A.c[k] > hi else (-1 if A.c[k] < lo else 0)
            if d == 0:
                continue
            j0 = k + 1
            if j0 >= A.n - 2:
                break
            entry = A.o[j0] + (sp if d > 0 else 0.0)
            sl_d = max(0.75 * width, 1.5 * a)
            j1, r = simulate(A, sp, j0, d, entry, entry - d * sl_d, entry + d * 3.0 * width, 6 * 60 // step - 1)
            rows.append((j0, j1, d, r))
            busy = j1
            break
    return trades_frame(rows, base)


# ---------------------------------------------------------------- samw2591 RSI(2) M15
def rsi2_m15(p: Period) -> pd.DataFrame:
    df = resample(p.base, "15min") if p.tf == "M5" else p.base
    A, sp = Arrays(df), p.spread
    c = A.c
    r2 = rsi(c, 2)
    s50 = pd.Series(c).rolling(50).mean().to_numpy()
    e100 = pd.Series(c).ewm(span=100).mean().to_numpy()
    atr = sma_range_atr(df, 14)
    H = resample(df, "60min")
    adx_h1 = htf_on(df, H, adx_w(H, 14), 1)
    ex_l, ex_s = np.zeros(A.n, bool), np.zeros(A.n, bool)
    ex_l[r2 > 55] = True
    ex_s[r2 < 45] = True
    rows, busy = [], -1
    for k in range(110, A.n - 2):
        if k + 1 <= busy or np.isnan(atr[k]) or adx_h1[k] > 40:
            continue
        d = 1 if (r2[k] < 15 and c[k] > s50[k] and c[k] > e100[k]) else (
            -1 if (r2[k] > 85 and c[k] < s50[k] and c[k] < e100[k]) else 0)
        if d == 0:
            continue
        j0 = k + 1
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        sl = entry - d * min(50.0, max(10.0, 4.5 * atr[k]))
        j1, r = simulate(A, sp, j0, d, entry, sl, None, 15, exit_mask=ex_l if d > 0 else ex_s)
        rows.append((j0, j1, d, r))
        busy = j1
    return trades_frame(rows, df)


# ---------------------------------------------------------------- BlamzKunG grid mean reversion
def mr_grid(p: Period) -> pd.DataFrame:
    """Basket 0,01 lot per level. R = hasil basket / jarak SL darurat 1 posisi (1R = 1 posisi kena SL darurat)."""
    df = resample(p.base, "15min") if p.tf == "M5" else p.base
    A, sp = Arrays(df), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    r14 = rsi(c, 14)
    mid = pd.Series(c).rolling(20).mean()
    sd = pd.Series(c).rolling(20).std(ddof=0)
    bb_up, bb_lo = (mid + 2 * sd).to_numpy(), (mid - 2 * sd).to_numpy()
    atr15 = sma_tr_atr(df, 14)
    H = resample(df, "60min")
    hc = H["close"].to_numpy(float)
    adx = htf_on(df, H, adx_w(H, 14), 1)
    e50, e200 = htf_on(df, H, ema(hc, 50), 1), htf_on(df, H, ema(hc, 200), 1)
    atr_h1 = htf_on(df, H, sma_tr_atr(H, 14), 1)
    srv = server_time(df.index)
    hour, dow = srv.hour.to_numpy(), srv.dayofweek.to_numpy()
    rows, k = [], 250
    while k < A.n - 2:
        ok_time = 7 <= hour[k] < 21 and not (dow[k] == 4 and hour[k] >= 18)
        if not ok_time or np.isnan(adx[k]) or adx[k] >= 28 or abs(e50[k] - e200[k]) > 20.0:
            k += 1
            continue
        d = 1 if (r14[k] < 35 and c[k] <= bb_lo[k]) else (-1 if (r14[k] > 65 and c[k] >= bb_up[k]) else 0)
        if d == 0:
            k += 1
            continue
        j = k + 1
        first = o[j] + (sp if d > 0 else 0.0)
        pos = [first]
        esl = first - d * 3.5 * atr_h1[k]
        risk = abs(first - esl)
        peak, result = 0.0, None
        while j < A.n - 2:
            adj = sp if d < 0 else 0.0
            worst_px = l[j] if d > 0 else h[j] + adj
            # SL darurat (dicek dulu, konservatif)
            if (worst_px <= esl) if d > 0 else (worst_px >= esl):
                px = min(esl, o[j]) if d > 0 else max(esl, o[j] + adj)
                result = sum((px - e) * d for e in pos)
                break
            added = False
            step = min(12.0, max(3.5, 1.4 * atr15[j - 1]))
            while len(pos) < 5:
                nxt = pos[-1] - d * step
                if (l[j] + sp <= nxt) if d > 0 else (h[j] >= nxt):
                    pos.append(nxt)
                    added = True
                else:
                    break
            avg = sum(pos) / len(pos)
            close_px = c[j] + adj
            profit = sum((close_px - e) * d for e in pos)
            # trend escape: ADX>=32 melawan posisi & rugi >= $60 (per 0,01 lot = $60 harga x jumlah posisi)
            against = (e50[j] < e200[j] and c[j] < e200[j]) if d > 0 else (e50[j] > e200[j] and c[j] > e200[j])
            if adx[j] >= 32 and against and -profit >= 60.0:
                result = profit
                j += 1
                break
            tp_px = avg + d * 0.3 * atr15[j - 1]
            if not added and ((h[j] >= tp_px) if d > 0 else (l[j] + sp <= tp_px)):
                result = sum((tp_px - e) * d for e in pos)
                break
            if profit >= 10.0:  # trailing basket: mulai $10, kunci $3 di bawah puncak
                peak = max(peak, profit)
                if profit <= peak - 3.0:
                    result = profit
                    break
            else:
                peak = 0.0
            j += 1
        if result is None:
            break
        rows.append((k + 1, j, d, result / risk, len(pos)))
        k = j + 1 + 1  # jeda 15 menit
    t = pd.DataFrame(rows, columns=["j0", "j1", "dir", "R", "levels"])
    if len(t):
        t["time"] = df.index[t.j0.to_numpy()]
        t["exit"] = df.index[np.minimum(t.j1.to_numpy(), len(df) - 1)]
    return t


TESTS = {
    "ema_rsi_h4 (Aniket)": ema_rsi_h4,
    "breakout_adx asli $3 (Turnipnator)": breakout_adx,
    "breakout_adx diskalakan (Turnipnator)": lambda p: breakout_adx(p, scaled=True),
    "pdh_retest BUY (phatnomenal)": pdh_retest,
    "sma_pullback H1 (sagarmeravi)": lambda p: sma_pullback(p, "60min"),
    "sma_pullback M5 (sagarmeravi)": lambda p: sma_pullback(p) if p.tf == "M5" else None,
    "keltner_live 3 jam + trail (samw2591)": keltner,
    "keltner_simple SL/TP saja (samw2591)": lambda p: keltner(p, live=False),
    "orb_ny (samw2591)": orb_ny,
    "rsi2_m15 (samw2591)": rsi2_m15,
    "mr_grid (BlamzKunG)": mr_grid,
}


def main():
    ps = periods()
    out = {}
    for name, fn in TESTS.items():
        print(name)
        out[name] = {}
        for p in ps:
            t = fn(p)
            if t is None:
                print(f"   {p.name}: - (butuh data M5)")
                continue
            out[name][p.name] = t
            extra = ""
            if "pct" in t and len(t):
                extra = f" | total {t.pct.sum():+.1f}% harga, rata {t.pct.mean():+.3f}%/trade"
            if "levels" in t:
                extra = f" | level rata {t.levels.mean():.1f}, basket profit {(t.R > 0).mean() * 100:.1f}%"
            print(f"   {p.name}: {fmt(stats(t.R))}{extra}")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "wb") as fh:
            pickle.dump(out, fh)


if __name__ == "__main__":
    main()
