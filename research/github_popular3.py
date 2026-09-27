"""Tahap B: uji ulang strategi dari 63 repo yang BELUM diuji di github_popular.py / github_popular2.py.

    python -m research.github_popular3 [out.pkl] [--only kata]

Aturan dibaca dari kode asli penulis (lihat `kandidat/<repo>/`), lalu ditulis ulang di mesin uji yang sama
(research/harness.py): data 2012-2026 dalam 4 periode, spread, entry di open bar berikutnya, SL dicek dulu, tanpa
look-ahead. Kode repo TIDAK dijalankan. Setiap port mencantumkan file & baris sumber serta penyederhanaan yang
terpaksa dilakukan.
"""
from __future__ import annotations

import pickle
import sys

import numpy as np
import pandas as pd

from .data import resample
from .github_popular import atr_w, ema, rsi
from .github_popular2 import adx_w, bph
from .harness import Arrays, Period, fmt, periods, simulate, stats, to_base, trades_frame


def htf_closed(H: pd.DataFrame, X: pd.DataFrame, values: np.ndarray, x_hours: float, h_hours: float = 1.0):
    """Nilai indikator timeframe X (sudah tertutup) yang diketahui saat bar H ditutup."""
    s = pd.Series(values, index=X.index + pd.Timedelta(hours=x_hours))
    return s.reindex(H.index + pd.Timedelta(hours=h_hours), method="ffill").to_numpy()


# ---------------------------------------------------------------- Turnipnator: EMA Trend (src/ema_trend_strategy.js)
def turnip_ema_trend(p: Period, allow_short: bool = False) -> pd.DataFrame:
    """H1: EMA3>EMA8>EMA21 & close>EMA21, ADX>=25 & tidak turun >0,5, RSI 15-60 (BUY) / 35-85 (SELL),
    jarak ke EMA3 <=0,3%, H4 EMA3 vs EMA21 tidak berlawanan, filter 'leg' 6 bar (range/ATR>2 searah -> tolak).
    SL = clamp(1,5 ATR, $2, $40), TP 2R, BE di 30% TP (=0,6R), lalu trailing 1,5 ATR (config.js baris 81-105).
    ALLOW_SHORT default false di config.js -> versi asli hanya BUY."""
    H = resample(p.base, "60min")
    H4 = resample(p.base, "240min")
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    f, m, s = ema(c, 3), ema(c, 8), ema(c, 21)
    at, ad, r = atr_w(H, 14), adx_w(H, 14), rsi(c, 14)
    c4 = H4["close"].to_numpy(float)
    hf, hs = htf_closed(H, H4, ema(c4, 3), 4), htf_closed(H, H4, ema(c4, 21), 4)
    lo6 = pd.Series(l).rolling(6).min().to_numpy()
    hi6 = pd.Series(h).rolling(6).max().to_numpy()
    op6 = np.r_[np.full(5, np.nan), o[:-5]]
    start = to_base(p.base, H.index)
    rows, busy = [], -1
    for k in range(60, len(H) - 1):
        if not (ad[k] >= 25 and ad[k] >= ad[k - 1] - 0.5):
            continue
        dist = (c[k] - f[k]) / f[k]
        leg = (hi6[k] - lo6[k]) / at[k]
        leg_dir = -1 if c[k] < op6[k] else 1
        if f[k] > m[k] > s[k] and c[k] > s[k] and 15 <= r[k] <= 60 and dist <= 0.003 and not hf[k] < hs[k]:
            d = 1
        elif allow_short and f[k] < m[k] < s[k] and c[k] < s[k] and 35 <= r[k] <= 85 and dist >= -0.003 \
                and not hf[k] > hs[k]:
            d = -1
        else:
            continue
        if leg_dir == d and leg > 2.0:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        atr_k = at[k]
        risk = min(40.0, max(2.0, 1.5 * atr_k))
        entry = A.o[j0] + (sp if d > 0 else 0.0)

        def trail(j, d, entry, cur, atr_k=atr_k):  # trailing 1,5 ATR hanya setelah SL sudah di BE
            if (cur < entry) if d > 0 else (cur > entry):
                return cur
            new = A.c[j] - 1.5 * atr_k if d > 0 else A.c[j] + sp + 1.5 * atr_k
            return max(cur, new) if d > 0 else min(cur, new)

        j1, rr = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 2 * risk, 10 * 24 * bph(p),
                          trail=trail, be_at=0.6)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- Turnipnator: Triple Confirmation (src/strategy.js)
def _swing_levels(h, l, k, lookback=50):
    """identifySupportResistance(): swing 2-kiri-2-kanan dalam 50 candle terakhir (sampai bar k), cluster 0,2%,
    diurutkan menurun, ambil 3 teratas (persis seperti kode asli, termasuk urutannya)."""
    hh, ll = h[k - lookback + 1:k + 1], l[k - lookback + 1:k + 1]
    sh, sl_ = [], []
    for i in range(2, lookback - 2):
        if hh[i] > hh[i - 1] and hh[i] > hh[i - 2] and hh[i] > hh[i + 1] and hh[i] > hh[i + 2]:
            sh.append(hh[i])
        if ll[i] < ll[i - 1] and ll[i] < ll[i - 2] and ll[i] < ll[i + 1] and ll[i] < ll[i + 2]:
            sl_.append(ll[i])

    def cluster(v):
        if not v:
            return []
        v = sorted(v)
        out, cur = [], [v[0]]
        for x in v[1:]:
            if abs(x - cur[0]) / cur[0] <= 0.002:
                cur.append(x)
            else:
                out.append(sum(cur) / len(cur))
                cur = [x]
        out.append(sum(cur) / len(cur))
        return sorted(out, reverse=True)[:3]
    return cluster(sh), cluster(sl_)


def turnip_triple(p: Period) -> pd.DataFrame:
    """H1: tren = close>EMA20>EMA50 (atau kebalikannya), jarak EMA >= $10, RSI 40-70 (BUY) / 30-60 (SELL),
    pemicu = pola engulfing/hammer/shooting star atau dekat support/resistance/EMA20 (0,2%), skor >= 70.
    SL tetap $3,50 (atau di bawah support bila < $0,10), TP 1R, trailing $1,50 setelah profit $2 (config.js)."""
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    f, s, r = ema(c, 20), ema(c, 50), rsi(c, 14)
    start = to_base(p.base, H.index)
    rows, busy = [], -1
    for k in range(60, len(H) - 1):
        if c[k] > f[k] > s[k]:
            d = 1
        elif c[k] < f[k] < s[k]:
            d = -1
        else:
            continue
        if abs(f[k] - s[k]) < 10.0:
            continue
        if not ((40 <= r[k] <= 70) if d > 0 else (30 <= r[k] <= 60)):
            continue
        body, rng = abs(c[k] - o[k]), h[k] - l[k]
        lw, uw = min(o[k], c[k]) - l[k], h[k] - max(o[k], c[k])
        pat = None
        if c[k - 1] < o[k - 1] and c[k] > o[k] and o[k] < c[k - 1] and c[k] > o[k - 1]:
            pat = "BULL_ENG"
        elif c[k - 1] > o[k - 1] and c[k] < o[k] and o[k] > c[k - 1] and c[k] < o[k - 1]:
            pat = "BEAR_ENG"
        elif rng > 0 and lw > 2 * body and uw < 0.5 * body and body < 0.3 * rng:
            pat = "HAMMER"
        elif rng > 0 and uw > 2 * body and lw < 0.5 * body and body < 0.3 * rng:
            pat = "STAR"
        res, sup = _swing_levels(h, l, k)
        ns = next((x for x in sup if x < c[k]), None)
        nr = next((x for x in res if x > c[k]), None)
        at_s = ns is not None and abs(c[k] - ns) / ns <= 0.002
        at_r = nr is not None and abs(c[k] - nr) / nr <= 0.002
        near_ema = abs(c[k] - f[k]) / c[k] < 0.002
        good_pat = pat in (("BULL_ENG", "HAMMER") if d > 0 else ("BEAR_ENG", "STAR"))
        level = at_s if d > 0 else at_r
        if not (level or near_ema):
            continue
        score = 40 + ((20 if pat.endswith("ENG") else 15) if pat else 0) + (15 if (at_s or at_r) else 0)
        score += 10 if ((d > 0 and 50 <= r[k] <= 65) or (d < 0 and 35 <= r[k] <= 50)) else 0
        spread_pct = abs(f[k] - s[k]) / c[k]
        score += 10 if spread_pct > 0.01 else (5 if spread_pct > 0.005 else 0)
        if score < 70:
            continue
        _ = good_pat  # pola hanya menambah skor & alasan; pemicu tetap sah tanpa pola (strategy.js 97-127)
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        risk = 3.5
        if d > 0 and ns is not None and 0 < c[k] - ns < 0.10:
            risk = entry - (ns - 0.05)
        if d < 0 and nr is not None and 0 < nr - c[k] < 0.10:
            risk = (nr + 0.05) - entry

        def trail(j, d, entry, cur):  # trailing stop broker: aktif setelah profit $2, jarak $1,50
            if d > 0:
                return max(cur, A.h[j] - 1.5) if A.h[j] - entry >= 2.0 else cur
            return min(cur, A.l[j] + sp + 1.5) if entry - (A.l[j] + sp) >= 2.0 else cur

        j1, rr = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * risk, 5 * 24 * bph(p), trail=trail)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


TESTS = {
    "turnip_ema_trend BUY saja (asli)": turnip_ema_trend,
    "turnip_ema_trend + SELL": lambda p: turnip_ema_trend(p, allow_short=True),
    "turnip_triple (Turnipnator)": turnip_triple,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else ""
    out_path = next((a for a in argv if a.endswith(".pkl")), "")
    ps = periods()
    out = {}
    for name, fn in TESTS.items():
        if only and only not in name:
            continue
        print(name, flush=True)
        out[name] = {}
        tot = []
        for p in ps:
            t = fn(p)
            if t is None:
                print(f"   {p.name}: - (butuh data M5)")
                continue
            out[name][p.name] = t
            tot.append(t.R.to_numpy() if len(t) else np.array([]))
            print(f"   {p.name}: {fmt(stats(t.R))}", flush=True)
        if tot:
            allr = np.concatenate(tot)
            pos = sum(1 for x in tot if len(x) and x.sum() > 0)
            print(f"   TOTAL  : {fmt(stats(allr))} | periode positif {pos}/{len(tot)}", flush=True)
    if out_path:
        with open(out_path, "wb") as fh:
            pickle.dump(out, fh)


if __name__ == "__main__":
    main()
