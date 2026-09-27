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
from .harness import Arrays, Period, fmt, periods, server_time, simulate, stats, to_base, trades_frame


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


# ---------------------------------------------------------------- BlamzKunG: Advanced Grid EA (Experts/XAUUSD_Advanced_Grid_EA.mq5)
def blamz_adv_grid(p: Period, balance0: float = 1000.0, leverage: float = 100.0) -> pd.DataFrame:
    """Simulasi akun (bukan R): basket BUY & SELL dibuka BERSAMAAN tanpa sinyal bila filter lolos (jam server 7-21,
    Jumat < 18, ATR H1 < $7,5, ADX H1 < 32, |harga - EMA200 H1| <= $15). Lot awal 0,01, x1,20 per level, jarak grid
    max($2,50; 0,5 ATR H1) x 1,1^level, maks 8 level & 2,5 lot. Basket ditutup bila profit >= $15, harga >= BE + $1,
    atau trailing (mulai $12, kunci $4). Level 8 tembus satu langkah lagi -> hedge lock (lot sama arah berlawanan),
    ditutup bersama basketnya. DD mengambang >= 20% -> tutup semua & EA berhenti (dianggap dinyalakan lagi besok);
    DD >= 12% / margin < 200% -> tidak menambah level; rugi harian $100 / untung $150 -> tidak buka basket baru hari itu
    (baris 86-160, 467-560, 588-700, 716-900). 1 lot = 100 oz. Harga dicek per bar (M5/M15): SL darurat dicek dulu."""
    df = p.base
    A, sp = Arrays(df), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    H = resample(df, "60min")
    hc = H["close"].to_numpy(float)
    atr_h = htf_closed_base(df, H, atr_w(H, 14))
    adx_h = htf_closed_base(df, H, adx_w(H, 14))
    ema_h = htf_closed_base(df, H, ema(hc, 200))
    srv = server_time(df.index)
    hour, dow, day = srv.hour.to_numpy(), srv.dayofweek.to_numpy(), srv.normalize().to_numpy()
    OZ = 100.0
    bal = balance0
    side = {1: [], -1: []}          # list (harga, lot)
    hedge = {1: None, -1: None}     # (harga, lot, arah)
    peak = {1: 0.0, -1: 0.0}
    opened = {1: 0, -1: 0}
    day_pl, cur_day, lock_day = 0.0, None, None
    rows, eq_curve, stops, hedges = [], [], 0, 0

    def pnl(d, px_bid):
        """Profit mengambang basket arah d + hedge-nya pada harga bid px_bid."""
        tot = 0.0
        for e, lot in side[d]:
            tot += ((px_bid - e) if d > 0 else (e - (px_bid + sp))) * lot * OZ
        if hedge[d] is not None:
            e, lot, hd = hedge[d]
            tot += ((px_bid - e) if hd > 0 else (e - (px_bid + sp))) * lot * OZ
        return tot

    def close(d, px_bid, j, why):
        nonlocal bal, day_pl
        prof = pnl(d, px_bid)
        bal += prof
        day_pl += prof
        rows.append((opened[d], j, d, prof, len(side[d]), why, hedge[d] is not None))
        side[d], hedge[d], peak[d] = [], None, 0.0

    habis = None
    for j in range(300, A.n - 1):
        if bal <= 0.05 * balance0:      # akun habis (margin call) -> simulasi berhenti
            habis = df.index[j]
            break
        if day[j] != cur_day:
            cur_day, day_pl = day[j], 0.0
        # 1. guard DD darurat: equity terburuk di dalam bar (low utk BUY, high utk SELL tidak bisa terjadi bersamaan;
        #    ambil yang lebih buruk dari dua skenario harga)
        if side[1] or side[-1]:
            worst = min(pnl(1, l[j]) + pnl(-1, l[j]), pnl(1, h[j]) + pnl(-1, h[j]))
            if (bal - (bal + worst)) / bal * 100 >= 20.0:
                px = l[j] if pnl(1, l[j]) + pnl(-1, l[j]) <= pnl(1, h[j]) + pnl(-1, h[j]) else h[j]
                for d in (1, -1):
                    if side[d]:
                        close(d, px, j, "darurat_DD20")
                stops += 1
                lock_day = cur_day
                eq_curve.append(bal)
                continue
        # 2. keluar basket
        for d in (1, -1):
            if not side[d]:
                continue
            lots = sum(x[1] for x in side[d])
            be = sum(e * x for e, x in side[d]) / lots
            tgt = be + 1.0 if d > 0 else be - 1.0
            hit_pts = (h[j] >= tgt) if d > 0 else (l[j] + sp <= tgt)
            if hit_pts:
                close(d, tgt if d > 0 else tgt - sp, j, "tp_titik")
                continue
            prof = pnl(d, c[j])
            if prof >= 15.0:
                close(d, c[j], j, "tp_usd")
                continue
            if prof >= 12.0:
                peak[d] = max(peak[d], prof)
                if prof <= peak[d] - 4.0 and peak[d] - 4.0 > 0:
                    close(d, c[j], j, "trailing")
                    continue
            else:
                peak[d] = 0.0
        # 3. hedge lock
        stepb = max(2.5, 0.5 * atr_h[j]) if not np.isnan(atr_h[j]) else 2.5
        for d in (1, -1):
            if len(side[d]) >= 8 and hedge[d] is None:
                ext = min(e for e, _ in side[d]) if d > 0 else max(e for e, _ in side[d])
                trig = ext - d * stepb * 1.1 ** len(side[d])
                if (l[j] + sp <= trig) if d > 0 else (h[j] >= trig):
                    lot = sum(x[1] for x in side[d])
                    hedge[d] = ((trig - sp) if d > 0 else trig + sp, lot, -d)
                    hedges += 1
        # 4. tambah level grid
        eq = bal + pnl(1, c[j]) + pnl(-1, c[j])
        used = sum(x[1] for d in (1, -1) for x in side[d]) * OZ * c[j] / leverage
        margin_ok = used == 0 or eq / used * 100 >= 200
        dd_ok = eq >= bal or (bal - eq) / bal * 100 < 12.0
        if margin_ok and dd_ok:
            for d in (1, -1):
                n = len(side[d])
                if 0 < n < 8:
                    ext = min(e for e, _ in side[d]) if d > 0 else max(e for e, _ in side[d])
                    nxt = ext - d * round(stepb * 1.1 ** n, 2)
                    lot = round(min(0.5, side[d][-1][1] * 1.2), 2)
                    if sum(x[1] for x in side[d]) + lot <= 2.5 and ((l[j] + sp <= nxt) if d > 0 else (h[j] >= nxt)):
                        side[d].append((nxt, lot))
        # 5. basket baru (tanpa sinyal)
        ok = (7 <= hour[j] <= 21 and not (dow[j] == 4 and hour[j] >= 18) and lock_day != cur_day
              and -100.0 < day_pl < 150.0 and not np.isnan(ema_h[j]) and atr_h[j] < 7.5 and adx_h[j] <= 32
              and abs(o[j] - ema_h[j]) <= 15.0)
        if ok:
            for d in (1, -1):
                if not side[d]:
                    side[d] = [(o[j] + (sp if d > 0 else 0.0), 0.01)]
                    opened[d] = j
        eq_curve.append(bal + pnl(1, c[j]) + pnl(-1, c[j]))
    t = pd.DataFrame(rows, columns=["j0", "j1", "dir", "usd", "levels", "why", "hedged"])
    if len(t):
        t["time"] = df.index[t.j0.to_numpy()]
        t["exit"] = df.index[np.minimum(t.j1.to_numpy(), len(df) - 1)]
        t["R"] = t.usd / balance0 * 100   # "R" di sini = % saldo awal per basket
    eq = np.array(eq_curve)
    t.attrs.update(saldo_akhir=bal, dd_maks=float((eq / np.maximum.accumulate(eq) - 1).min() * 100) if len(eq) else 0.0,
                   stop_darurat=stops, hedge=hedges, habis=habis)
    return t


# ---------------------------------------------------------------- shamshyder123-oss: GoldTradingEA.mq5
def shamshyder(p: Period, unit: float = 0.01) -> pd.DataFrame:
    """Versi yang DIMAKSUD penulis (kode aslinya tidak terkompilasi: tipe `ctrade`; dan `iMA()` dipakai sebagai nilai
    padahal mengembalikan handle -> sinyal tidak pernah muncul). H1: BUY bila 25<RSI14<35, SMA20>SMA50, MACD>0,
    close>SMA20; SELL kebalikannya (65<RSI<75). SL 100 x unit, TP 200 x unit, trailing 50 x unit saat profit.
    unit=0,01 (=_Point, seperti kodenya: SL $1) atau 0,10 (bila 'pips' = 10 point: SL $10)."""
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    r = rsi(c, 14)
    macd = ema(c, 12) - ema(c, 26)
    s20, s50 = pd.Series(c).rolling(20).mean().to_numpy(), pd.Series(c).rolling(50).mean().to_numpy()
    start = to_base(p.base, H.index)
    sl, tp, tr = 100 * unit, 200 * unit, 50 * unit
    rows, busy = [], -1
    for k in range(60, len(H) - 1):
        if 25 < r[k] < 35 and s20[k] > s50[k] and macd[k] > 0 and c[k] > s20[k]:
            d = 1
        elif 65 < r[k] < 75 and s20[k] < s50[k] and macd[k] < 0 and c[k] < s20[k]:
            d = -1
        else:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)

        def trail(j, d, entry, cur, tr=tr):
            if d > 0:
                return max(cur, A.h[j] - tr) if A.h[j] > entry else cur
            return min(cur, A.l[j] + sp + tr) if A.l[j] + sp < entry else cur

        j1, rr = simulate(A, sp, j0, d, entry, entry - d * sl, entry + d * tp, 5 * 24 * bph(p), trail=trail)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- thanvish21: Gold_Dominator_Pro_v3_STRATEGY.pine
def gold_dominator(p: Period, volume_ok: bool = False, eq_filter: bool = True) -> pd.DataFrame:
    """Grafik H1. Skor 10 komponen x 10 (tren H4 EMA21/55/200, close>EMA200 H4, RSI 45-72, histogram MACD>0,
    StochRSI naik, ADX>20, close>lowest20, volume>1,2xSMA20, sesi UTC 8-11/13-17, ATR>0). BUY bila skor>=80 DAN
    StochRSI cross up, filter kurva ekuitas (ekuitas >= EMA20-nya) & DD < 10%. SL 1,5 ATR, TP 1,2/2,0/3,0 ATR
    (50/30/20%). Bug asli dipertahankan: StochRSI berskala 0-1 tapi dibandingkan dengan 20/80 -> syarat 'sk[1]<20' selalu
    benar dan SELL tidak pernah terjadi. Data tanpa volume: volume_ok=False (komponen volume selalu 0) / True (selalu 10).
    Ukuran posisi 100% ekuitas tanpa leverage (default strategi) -> dipakai untuk filter ekuitas & DD."""
    H = resample(p.base, "60min")
    H4 = resample(p.base, "240min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    c4 = H4["close"].to_numpy(float)
    ef, em, es = (htf_closed(H, H4, ema(c4, n), 4) for n in (21, 55, 200))
    r = rsi(c, 14)
    macd = ema(c, 12) - ema(c, 26)
    hist = macd - ema(macd, 9)
    rs = pd.Series(r)
    raw = ((rs - rs.rolling(14).min()) / (rs.rolling(14).max() - rs.rolling(14).min())).to_numpy()
    sk = pd.Series(raw).rolling(3).mean().to_numpy()
    sd = pd.Series(sk).rolling(3).mean().to_numpy()
    stoch_up = (sk > sd) & (np.r_[np.nan, sk[:-1]] <= np.r_[np.nan, sd[:-1]]) & (np.r_[np.nan, sk[:-1]] < 20)
    at, ad = atr_w(H, 14), adx_w(H, 14)
    low20 = pd.Series(c).rolling(20).min().to_numpy()
    hr = H.index.hour.to_numpy()
    sess = ((hr >= 8) & (hr < 11)) | ((hr >= 13) & (hr < 17))
    score = (10 * ((c > es) & (ef > em)) + 10 * (c > es) + 10 * ((r > 45) & (r < 72)) + 10 * (hist > 0) + 10 * stoch_up
             + 10 * (ad > 20) + 10 * (c > low20) + (10 if volume_ok else 0) + 10 * sess + 10 * (at > 0))
    start = to_base(p.base, H.index)
    exit_h = np.searchsorted(start, np.arange(A.n), side="right") - 1   # bar H1 tempat bar dasar j berada
    eq, eq_ema, peak = 1.0, 1.0, 1.0
    pending: list[tuple[int, float]] = []      # (bar H1 selesai, faktor ekuitas)
    rows, busy_k = [], -1
    for k in range(250, len(H) - 1):
        for item in [x for x in pending if x[0] <= k]:
            eq *= item[1]
            pending.remove(item)
        eq_ema = eq_ema + 2.0 / 21 * (eq - eq_ema)
        peak = max(peak, eq)
        if k <= busy_k or not (score[k] >= 80 and stoch_up[k] and (eq >= eq_ema or not eq_filter)
                               and ((peak - eq) / peak < 0.10 or not eq_filter)):
            continue
        j0 = start[k + 1]
        if j0 >= A.n - 2:
            break
        entry = A.o[j0] + sp
        a = at[k - 1]
        sl = c[k] - 1.5 * a
        if entry - sl <= 0:
            continue
        legs = []
        for mult, w in ((1.2, 0.5), (2.0, 0.3), (3.0, 0.2)):
            j1, rr = simulate(A, sp, j0, 1, entry, sl, c[k] + mult * a, 10 * 24 * bph(p))
            legs.append((j1, rr, w))
        j_end = max(x[0] for x in legs)
        R = sum(rr * w for _, rr, w in legs)
        rows.append((j0, j_end, 1, R))
        pending.append((exit_h[min(j_end, A.n - 1)] + 1, 1 + R * (entry - sl) / entry))
        busy_k = exit_h[min(j_end, A.n - 1)]
    return trades_frame(rows, p.base)


# ---------------------------------------------------------------- P1Piyush: pdhl_bot.py (PDH/PDL breakout-retest)
def piyush_pdhl(p: Period, partial: bool = False) -> pd.DataFrame | None:
    """M5 (hanya periode M5). PDH/PDL = high/low hari sebelumnya. Sesi UTC 6-20 kecuali jam 1, 9, 10. RSI(SMA14)
    22-78. BREAKOUT: close > PDH + 0,15% dan close sebelumnya < PDH, dan 2-3 bar sebelumnya sempat retest (low dalam
    +-0,15% & close > PDH), bias H1 EMA50>EMA200 -> BUY (kebalikannya untuk PDL). Sweep-reversal DINONAKTIFKAN di kode
    (hanya menandai level terpakai). 1 trade per level per hari, 1 posisi. SL = ATR(SMA14, M5), TP 3R (TP2, sama
    dengan laporan backtest penulis) atau partial: 50% di 1,5R + 50% di 3R (pdhl_bot.py baris 150-270)."""
    if p.tf != "M5":
        return None
    base = p.base
    A, sp = Arrays(base), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    srv = server_time(base.index)
    sday = srv.normalize()
    daily = pd.DataFrame({"h": h, "l": l}, index=sday).groupby(level=0).agg({"h": "max", "l": "min"})
    pdh = pd.Series(daily["h"].shift(1).to_numpy(), index=daily.index).reindex(sday).to_numpy()
    pdl = pd.Series(daily["l"].shift(1).to_numpy(), index=daily.index).reindex(sday).to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr_s = pd.Series(tr).rolling(14).mean().to_numpy()
    dlt = pd.Series(c).diff()
    g, ls = dlt.clip(lower=0).rolling(14).mean(), (-dlt.clip(upper=0)).rolling(14).mean()
    rsi_s = (100 - 100 / (1 + g / ls.replace(0, np.nan))).to_numpy()
    H = resample(base, "60min")
    hc = H["close"].to_numpy(float)
    bias = np.sign(htf_closed_base(base, H, ema(hc, 50)) - htf_closed_base(base, H, ema(hc, 200)))
    hr = base.index.hour.to_numpy()
    uday = base.index.normalize().to_numpy()
    rows, busy, tapped, cur_day = [], -1, {"PDH": False, "PDL": False}, None
    for k in range(300, A.n - 2):
        if uday[k] != cur_day:
            cur_day, tapped = uday[k], {"PDH": False, "PDL": False}
        if k <= busy or np.isnan(pdh[k]) or np.isnan(atr_s[k]):
            continue
        if hr[k] in (1, 9, 10) or not 6 <= hr[k] < 20:
            continue
        if rsi_s[k] > 78 or rsi_s[k] < 22:
            continue
        cur, prox = c[k], c[k] * 0.0015
        d = 0
        for lvl, sgn in (("PDH", 1), ("PDL", -1)):
            L = pdh[k] if sgn > 0 else pdl[k]
            if tapped[lvl] or abs(cur - L) >= 2 * prox:
                continue
            wick = (h[k] > L + 0.3 * prox) if sgn > 0 else (l[k] < L - 0.3 * prox)
            back = (c[k] < L) if sgn > 0 else (c[k] > L)
            mss = (c[k - 1] > o[k - 1] and c[k] < o[k]) if sgn > 0 else (c[k - 1] < o[k - 1] and c[k] > o[k])
            if wick and back and mss and (bias[k] == -sgn or np.isnan(bias[k])):
                tapped[lvl] = True          # sweep-reversal dinonaktifkan penulis: level dipakai, tanpa trade
                break
            brk = (c[k] > L + prox and c[k - 1] < L) if sgn > 0 else (c[k] < L - prox and c[k - 1] > L)
            if not brk:
                continue
            ret = any((L - prox <= (l[k - i] if sgn > 0 else h[k - i]) <= L + prox)
                      and ((c[k - i] > L) if sgn > 0 else (c[k - i] < L)) for i in range(1, 4))
            if ret and (bias[k] == sgn or np.isnan(bias[k])):
                tapped[lvl] = True
                d = sgn
                break
        if d == 0:
            continue
        j0 = k + 1
        entry = o[j0] + (sp if d > 0 else 0.0)
        risk = atr_s[k]
        if partial:
            j1a, ra = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 1.5 * risk, 5 * 24 * 12)
            j1b, rb = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 3.0 * risk, 5 * 24 * 12)
            j1, rr = max(j1a, j1b), 0.5 * ra + 0.5 * rb
        else:
            j1, rr = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 3.0 * risk, 5 * 24 * 12)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, base)


# ---------------------------------------------------------------- nazhmi12: mesinBot.py (FVG + OB + EMA200 M5)
def nazhmi_fvg_ob(p: Period, daily_limit: bool = True) -> pd.DataFrame | None:
    """CATATAN: mesinBot.py aslinya men-trade EURUSD/GBPUSD/USDJPY/AUDUSD, BUKAN emas; botXauusd.py hanya dashboard.
    Aturannya diterapkan ke XAUUSD M5: BUY bila close > EMA200, FVG (low[-1] > high[-3]) DAN order block (close[-1] >
    open[-2] & bar[-2] merah); SELL kebalikannya. SL 1,5 ATR(14), TP 2R. 1 posisi. Batas harian lot 0,01: berhenti
    setelah +$5 atau -$3 (hari = jam PC WIB). Keputusan diambil di awal bar (bar sinyal sudah tertutup)."""
    if p.tf != "M5":
        return None
    base = p.base
    A, sp = Arrays(base), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    e200 = ema(c, 200)
    at = atr_w(base, 14)
    wib_day = (base.index + pd.Timedelta(hours=7)).normalize().to_numpy()
    rows, busy, cur_day, pnl_day = [], -1, None, 0.0
    for k in range(210, A.n - 2):
        if wib_day[k] != cur_day:
            cur_day, pnl_day = wib_day[k], 0.0
        if k <= busy:
            continue
        if daily_limit and not -3.0 < pnl_day < 5.0:
            continue
        m = k - 1
        if c[m] > e200[m] and l[m] > h[m - 2] and c[m] > o[m - 1] and c[m - 1] < o[m - 1]:
            d = 1
        elif c[m] < e200[m] and h[m] < l[m - 2] and c[m] < o[m - 1] and c[m - 1] > o[m - 1]:
            d = -1
        else:
            continue
        entry = o[k] + (sp if d > 0 else 0.0)
        risk = 1.5 * at[m]
        j1, rr = simulate(A, sp, k, d, entry, entry - d * risk, entry + d * 2 * risk, 5 * 24 * 12)
        rows.append((k, j1, d, rr))
        pnl_day += rr * risk          # 0,01 lot emas = $1 per $1 pergerakan
        busy = j1
    return trades_frame(rows, base)


# ---------------------------------------------------------------- Kiran-Kumbar: bot.py (sinyal SMC ke Telegram)
def _swings(h, l, lb=3):
    """Indeks swing high/low (lookback 3 kiri-kanan, >=/<=), dipakai bila sudah terkonfirmasi 3 bar kemudian."""
    n = len(h)
    sh, sl_ = np.ones(n, bool), np.ones(n, bool)
    for j in range(1, lb + 1):
        sh[j:] &= h[j:] >= h[:-j]
        sh[:-j] &= h[:-j] >= h[j:]
        sl_[j:] &= l[j:] <= l[:-j]
        sl_[:-j] &= l[:-j] <= l[j:]
    sh[:lb] = sh[-lb:] = False
    sl_[:lb] = sl_[-lb:] = False
    return np.flatnonzero(sh), np.flatnonzero(sl_)


def _structure(k, c, h, l, shi, sli, win=60, lb=3):
    """analyze_structure_bos() pada bar k (jendela 60 bar terakhir)."""
    lo, hi = k - win + 1 + lb, k - lb
    a = shi[np.searchsorted(shi, lo):np.searchsorted(shi, hi, side="right")]
    b = sli[np.searchsorted(sli, lo):np.searchsorted(sli, hi, side="right")]
    if len(a) < 2 or len(b) < 2:
        return 0, False, False
    last_sh, prev_sh, last_sl, prev_sl = h[a[-1]], h[a[-2]], l[b[-1]], l[b[-2]]
    cur = c[k]
    ema_bull = c[k - 9:k + 1].mean() > c[k - 29:k + 1].mean()
    bull_bos, bear_bos = cur > last_sh, cur < last_sl
    was_bear = last_sh < prev_sh and last_sl < prev_sl
    was_bull = last_sh > prev_sh and last_sl > prev_sl
    if was_bear and bull_bos:
        return 1, True, True
    if was_bull and bear_bos:
        return -1, True, True
    if bull_bos and ema_bull and last_sh > prev_sh:
        return 1, True, False
    if bear_bos and not ema_bull and last_sl < prev_sl:
        return -1, True, False
    if ema_bull and last_sh > prev_sh and last_sl > prev_sl:
        return 1, False, False
    if not ema_bull and last_sh < prev_sh and last_sl < prev_sl:
        return -1, False, False
    return 0, False, False


def kiran_smc(p: Period) -> pd.DataFrame | None:
    """Sinyal (bukan eksekusi) tiap bar M5 tertutup: bias struktur 15 menit wajib (+30, CHoCH +10), bias M5 +15,
    harga di order block +20, equal low/high tersapu +15, liquidity grab +10, FVG >= $1,5 +10, pola +10/+5,
    RSI(SMA14) <35/>65 +8. Sinyal bila skor >= 65, searah bias 15m, dan lebih besar dari skor arah lawan. SL di
    bawah OB/swing - $0,5 (min $3, maks $20), TP 2R. Maks 3 sinyal/hari (IST), hari kerja, arah sama tidak diulang
    dalam 45 menit. Setiap sinyal dihitung sebagai trade terpisah (boleh tumpang tindih)."""
    if p.tf != "M5":
        return None
    base = p.base
    A, sp = Arrays(base), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    M = resample(base, "15min")
    mo, mh, ml, mc = (M[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    m_end = (M.index + pd.Timedelta(minutes=15)).to_numpy()
    b_end = (base.index + pd.Timedelta(minutes=5)).to_numpy()
    m_idx = np.searchsorted(m_end, b_end, side="right") - 1          # 15m terakhir yang sudah tutup
    shi15, sli15 = _swings(mh, ml)
    shi5, sli5 = _swings(h, l)
    dl = pd.Series(c).diff()
    g, ls = dl.clip(lower=0).rolling(14).mean().to_numpy(), (-dl.clip(upper=0)).rolling(14).mean().to_numpy()
    ist = base.index + pd.Timedelta(hours=5, minutes=30)
    ist_day, ist_dow = ist.normalize().to_numpy(), ist.dayofweek.to_numpy()
    rows, cur_day, n_day, last_dir, last_k = [], None, 0, 0, -10**9
    for k in range(120, A.n - 2):
        if ist_day[k] != cur_day:
            cur_day, n_day, last_dir = ist_day[k], 0, 0
        if n_day >= 3 or ist_dow[k] >= 5:
            continue
        mk = m_idx[k]
        if mk < 100:
            continue
        tf, _, choch = _structure(mk, mc, mh, ml, shi15, sli15)
        if tf == 0:
            continue
        m5, _, _ = _structure(k, c, h, l, shi5, sli5)
        cur = c[k]
        # order block searah bias 15m
        ob_h = ob_l = None
        in_ob = False
        for i in range(k - 2, max(k - 19, 3), -1):
            red = c[i] < o[i]
            if (tf > 0 and red and max(c[i + 1:min(i + 3, k + 1)]) > h[i]) or \
               (tf < 0 and c[i] > o[i] and min(c[i + 1:min(i + 3, k + 1)]) < l[i]):
                ob_h, ob_l = h[i], l[i]
                in_ob = ob_l <= cur <= ob_h
                break
        # equal highs/lows (30 bar, tanpa 2 terakhir) & sapuan
        hw, lw = np.sort(h[k - 29:k - 1]), np.sort(l[k - 29:k - 1])
        dh, dlw = np.diff(hw) <= 0.30, np.diff(lw) <= 0.30
        swept_high = bool(dh.any() and (hw[1:][dh] < h[k]).any())
        swept_low = bool(dlw.any() and (lw[:-1][dlw] > l[k]).any())
        # liquidity grab
        mx, mn = h[k - 9:k - 1].max(), l[k - 9:k - 1].min()
        grab = 0
        if h[k - 1] > mx and h[k - 1] - max(o[k - 1], c[k - 1]) >= 1.0 and c[k] < o[k]:
            grab = -1
        if l[k - 1] < mn and min(o[k - 1], c[k - 1]) - l[k - 1] >= 1.0 and c[k] > o[k]:
            grab = 1
        # FVG
        fvg = 0
        for i in range(k - 2, max(k - 9, 0), -1):
            if h[i] < l[i + 2] and l[i + 2] - h[i] >= 1.5 and cur > h[i]:
                fvg = 1
                break
            if l[i] > h[i + 2] and l[i] - h[i + 2] >= 1.5 and cur < l[i]:
                fvg = -1
                break
        # pola
        body = abs(o[k] - c[k])
        pat, pts = 0, 0
        if o[k - 1] < c[k - 1] and o[k] > c[k] and o[k] >= c[k - 1] and c[k] <= o[k - 1]:
            pat, pts = -1, 10
        elif o[k - 1] > c[k - 1] and o[k] < c[k] and o[k] <= c[k - 1] and c[k] >= o[k - 1]:
            pat, pts = 1, 10
        elif h[k] - max(o[k], c[k]) > 2 * body and body > 0:
            pat, pts = -1, 5
        elif min(o[k], c[k]) - l[k] > 2 * body and body > 0:
            pat, pts = 1, 5
        r = 100.0 if ls[k] == 0 else 100 - 100 / (1 + g[k] / ls[k])
        L = S = 0
        L += 30 if tf > 0 else 0
        S += 30 if tf < 0 else 0
        L += 10 if choch and tf > 0 else 0
        S += 10 if choch and tf < 0 else 0
        L += 15 if m5 > 0 else 0
        S += 15 if m5 < 0 else 0
        L += 20 if in_ob and tf > 0 else 0
        S += 20 if in_ob and tf < 0 else 0
        L += 15 if swept_low and tf > 0 else 0
        S += 15 if swept_high and tf < 0 else 0
        L += 10 if grab > 0 else 0
        S += 10 if grab < 0 else 0
        L += 10 if fvg > 0 else 0
        S += 10 if fvg < 0 else 0
        L += pts if pat > 0 else 0
        S += pts if pat < 0 else 0
        L += 8 if r < 35 else 0
        S += 8 if r > 65 else 0
        if L > S and L >= 65 and tf > 0:
            d = 1
        elif S > L and S >= 65 and tf < 0:
            d = -1
        else:
            continue
        if d == last_dir and k - last_k < 9:
            continue
        if d > 0:
            if ob_l is not None:
                lvl = ob_l - 0.5
            else:
                w = sli5[(sli5 >= k - 29 + 3) & (sli5 <= k - 3)]
                lvl = l[w[-1]] - 0.5 if len(w) else cur - 8.0
            risk = max(cur - lvl, 3.0)
        else:
            if ob_h is not None:
                lvl = ob_h + 0.5
            else:
                w = shi5[(shi5 >= k - 29 + 3) & (shi5 <= k - 3)]
                lvl = h[w[-1]] + 0.5 if len(w) else cur + 8.0
            risk = max(lvl - cur, 3.0)
        risk = min(risk, 20.0)
        j0 = k + 1
        entry = o[j0] + (sp if d > 0 else 0.0)
        j1, rr = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 2 * risk, 5 * 24 * 12)
        rows.append((j0, j1, d, rr))
        n_day += 1
        last_dir, last_k = d, k
    return trades_frame(rows, base)


# ---------------------------------------------------------------- HillaryMurimi: strategies/*.py (M5, SL $10 / TP $20)
def hillary(p: Period, kind: str) -> pd.DataFrame | None:
    """main.py: M5, 200 bar, SL $10, TP $20 (tetap). kind: 'scalping' = SMA5 memotong SMA20 (BUY hanya bila std10 <
    std(200 close)/2; SELL tanpa filter), 'day' = RSI(SMA14) <30 BUY / >70 SELL, 'swing' = MACD 12/26/9 cross.
    backtest_runner.py penulis mengalikan sinyal bar i dengan return bar i yang sama (look-ahead); di sini sinyal dari
    bar yang sudah tutup, masuk di open bar berikutnya, 1 posisi."""
    if p.tf != "M5":
        return None
    base = p.base
    A, sp = Arrays(base), p.spread
    c = A.c
    cs = pd.Series(c)
    if kind == "scalping":
        f, sl_ = cs.rolling(5).mean().to_numpy(), cs.rolling(20).mean().to_numpy()
        vol, allv = cs.rolling(10).std().to_numpy(), cs.rolling(200).std().to_numpy()
        up = (f > sl_) & (np.r_[np.nan, f[:-1]] <= np.r_[np.nan, sl_[:-1]]) & (vol < allv / 2)
        dn = (f < sl_) & (np.r_[np.nan, f[:-1]] >= np.r_[np.nan, sl_[:-1]])
    elif kind == "day":
        dl = cs.diff()
        g, ls = dl.where(dl > 0, 0).rolling(14).mean(), (-dl.where(dl < 0, 0)).rolling(14).mean()
        r = (100 - 100 / (1 + g / ls)).to_numpy()
        up, dn = r < 30, r > 70
    else:
        m = cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()
        sg = m.ewm(span=9, adjust=False).mean()
        m, sg = m.to_numpy(), sg.to_numpy()
        up = (m > sg) & (np.r_[np.nan, m[:-1]] <= np.r_[np.nan, sg[:-1]])
        dn = (m < sg) & (np.r_[np.nan, m[:-1]] >= np.r_[np.nan, sg[:-1]])
    rows, busy = [], -1
    for k in np.flatnonzero(up | dn):
        if k < 210 or k + 1 >= A.n - 2 or k + 1 <= busy:
            continue
        d = 1 if up[k] else -1
        j0 = k + 1
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, rr = simulate(A, sp, j0, d, entry, entry - d * 10.0, entry + d * 20.0, 5 * 24 * 12)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, base)


# ---------------------------------------------------------------- armza332: mt5/Aurum_EA.mq5 (HAWK x5)
def aurum(p: Period, tf: str = "60min", learn: bool = True) -> pd.DataFrame:
    """Bar tertutup: wajib tembus high/low 20 bar (bar 2..21). Suara: HAWK-1 EMA20 vs EMA50 bila ADX>=22, HAWK-2 arah
    tembus, HAWK-3 fade RSI>=70/<=30, HAWK-4 fade di luar Bollinger 20/2, HAWK-5 tembus dari zona Fib 38,2-61,8% (50
    bar). Entry bila >=3 agen setuju (agen berbobot <0,5 dicadangkan; bobot +-0,08 per menang/kalah). SL 1,5 ATR,
    separuh ditutup di 1,8 ATR lalu SL ke BE, sisa TP 3,6 ATR, trailing 2 ATR setelah profit 1 ATR. Stop harian: 5 kalah
    beruntun atau rugi 3R; jeda 15 menit setelah rugi. Filter spread & berita tidak dipakai (tanpa data)."""
    H = resample(p.base, tf)
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = sma_tr(H, 14)
    f, sl_ = ema(c, 20), ema(c, 50)
    r, ad = rsi(c, 14), adx_w(H, 14)
    mid = pd.Series(c).rolling(20).mean()
    sd = pd.Series(c).rolling(20).std(ddof=0)
    up_bb, lo_bb = (mid + 2 * sd).to_numpy(), (mid - 2 * sd).to_numpy()
    hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    lo20 = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    hi50 = pd.Series(h).rolling(50).max().shift(1).to_numpy()
    lo50 = pd.Series(l).rolling(50).min().shift(1).to_numpy()
    start = to_base(p.base, H.index)
    exit_k = np.searchsorted(start, np.arange(A.n), side="right") - 1
    day = server_time(H.index).normalize().to_numpy()
    w = np.ones(5)
    rows, busy_k, cur_day, streak, day_r, last_loss_k = [], -1, None, 0, 0.0, -10**9
    bars_15m = max(1, int(round(15 / (pd.Timedelta(tf).total_seconds() / 60))))
    for k in range(60, len(H) - 1):
        if day[k] != cur_day:
            cur_day, streak, day_r = day[k], 0, 0.0
        if k <= busy_k or np.isnan(atr[k]) or atr[k] <= 0:
            continue
        bu, bd = c[k] > hi20[k], c[k] < lo20[k]
        if not (bu or bd):
            continue
        fib = (c[k] - lo50[k]) / (hi50[k] - lo50[k]) * 100 if hi50[k] > lo50[k] else 50.0
        golden = 38.2 <= fib <= 61.8
        v = [(1 if f[k] > sl_[k] else -1 if f[k] < sl_[k] else 0) if ad[k] >= 22 else 0,
             1 if bu else -1,
             -1 if r[k] >= 70 else (1 if r[k] <= 30 else 0),
             1 if c[k] < lo_bb[k] else (-1 if c[k] > up_bb[k] else 0),
             (1 if bu else -1) if golden else 0]
        act = [i for i in range(5) if w[i] >= 0.5]
        buy = sum(1 for i in act if v[i] > 0)
        sell = sum(1 for i in act if v[i] < 0)
        d = 1 if buy >= 3 else 0
        d = -1 if sell >= 3 else d
        if d == 0 or streak >= 5 or day_r <= -3.0 or k - last_loss_k < bars_15m:
            continue
        j0 = start[k + 1]
        if j0 >= A.n - 2:
            break
        a = atr[k]
        entry = A.o[j0] + (sp if d > 0 else 0.0)

        def trail(j, d, entry, cur, a=a):
            prof = (A.c[j] - entry) if d > 0 else (entry - A.c[j] - sp)
            if prof < a and ((cur < entry) if d > 0 else (cur > entry)):
                return cur
            new = A.c[j] - 2 * a if d > 0 else A.c[j] + sp + 2 * a
            if d > 0:
                return new if new > cur + 0.1 * a and new < A.c[j] else cur
            return new if new < cur - 0.1 * a and new > A.c[j] + sp else cur

        hold = 10 * 24 * bph(p)
        ja, ra = simulate(A, sp, j0, d, entry, entry - d * 1.5 * a, entry + d * 1.8 * a, hold, trail=trail)
        jb, rb = simulate(A, sp, j0, d, entry, entry - d * 1.5 * a, entry + d * 3.6 * a, hold, trail=trail, be_at=1.2)
        R = 0.5 * ra + 0.5 * rb
        j1 = max(ja, jb)
        rows.append((j0, j1, d, R))
        win = R > 0
        for i in act if learn else ():
            if v[i] == d:
                w[i] = min(1.5, max(0.1, w[i] + (0.08 if win else -0.08)))
        busy_k = exit_k[min(j1, A.n - 1)]
        if day[min(busy_k, len(H) - 1)] == cur_day:
            streak = 0 if win else streak + 1
            day_r += R
        if not win:
            last_loss_k = busy_k
    return trades_frame(rows, p.base)


def sma_tr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    """iATR MetaTrader 5 = rata-rata sederhana true range."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()


def htf_closed_base(base: pd.DataFrame, X: pd.DataFrame, values: np.ndarray) -> np.ndarray:
    """Nilai H1 yang sudah tertutup, dipetakan ke setiap bar dasar (dipakai saat bar dasar dibuka)."""
    s = pd.Series(values, index=X.index + pd.Timedelta(hours=1))
    return s.reindex(base.index, method="ffill").to_numpy()


TESTS = {
    "turnip_ema_trend BUY saja (asli)": turnip_ema_trend,
    "turnip_ema_trend + SELL": lambda p: turnip_ema_trend(p, allow_short=True),
    "turnip_triple (Turnipnator)": turnip_triple,
    "blamz_adv_grid akun $1.000 (BlamzKunG)": blamz_adv_grid,
    "shamshyder SL $1/TP $2 seperti kode": shamshyder,
    "shamshyder SL $10/TP $20 (pips=10 point)": lambda p: shamshyder(p, 0.10),
    "gold_dominator volume=0 (thanvish21)": gold_dominator,
    "gold_dominator volume=10 (thanvish21)": lambda p: gold_dominator(p, True),
    "gold_dominator volume=10 tanpa filter ekuitas & DD": lambda p: gold_dominator(p, True, eq_filter=False),
    "piyush_pdhl TP 3R (P1Piyush)": piyush_pdhl,
    "piyush_pdhl 50% 1,5R + 50% 3R": lambda p: piyush_pdhl(p, partial=True),
    "nazhmi_fvg_ob M5 + batas harian (nazhmi12)": nazhmi_fvg_ob,
    "nazhmi_fvg_ob M5 tanpa batas harian": lambda p: nazhmi_fvg_ob(p, daily_limit=False),
    "kiran_smc sinyal M5 (Kiran-Kumbar)": kiran_smc,
    "hillary scalping SMA5/20 M5 (HillaryMurimi)": lambda p: hillary(p, "scalping"),
    "hillary day RSI 30/70 M5": lambda p: hillary(p, "day"),
    "hillary swing MACD cross M5": lambda p: hillary(p, "swing"),
    "aurum H1 (armza332)": aurum,
    "aurum M15 (armza332)": lambda p: aurum(p, "15min"),
    "aurum H1 tanpa self-learning": lambda p: aurum(p, learn=False),
    "aurum M15 tanpa self-learning": lambda p: aurum(p, "15min", learn=False),
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
            if "usd" in t:
                a = t.attrs
                print(f"   {p.name}: basket={len(t)} profit%={(t.usd > 0).mean() * 100:.1f} total=${t.usd.sum():+,.0f} "
                      f"({t.usd.sum() / 10:+.1f}% dari $1.000) saldo akhir ${a['saldo_akhir']:,.0f} "
                      f"DD maks {a['dd_maks']:.1f}% | stop darurat {a['stop_darurat']}x, hedge {a['hedge']}x, "
                      f"rata level {t.levels.mean():.1f}"
                      + (f" | AKUN HABIS {a['habis']:%Y-%m-%d}" if a.get("habis") is not None else ""), flush=True)
                continue
            print(f"   {p.name}: {fmt(stats(t.R))}", flush=True)
        if tot and any("usd" in t for t in out[name].values()):
            pct = [t.usd.sum() / 10 for t in out[name].values()]
            print(f"   TOTAL  : {sum(pct):+.1f}% (jumlah 4 akun $1.000 terpisah) | periode positif "
                  f"{sum(x > 0 for x in pct)}/{len(pct)}", flush=True)
        elif tot:
            allr = np.concatenate(tot)
            pos = sum(1 for x in tot if len(x) and x.sum() > 0)
            print(f"   TOTAL  : {fmt(stats(allr))} | periode positif {pos}/{len(tot)}", flush=True)
    if out_path:
        with open(out_path, "wb") as fh:
            pickle.dump(out, fh)


if __name__ == "__main__":
    main()
