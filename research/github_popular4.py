"""Tahap B2: strategi yang belum diuji di putaran pertama (python -m research.github_popular4 [--only kata]).

Aturan dibaca dari kode asli (lihat `kandidat/<repo>/`), ditulis ulang di mesin uji yang sama (research/harness.py:
spread, entry di open bar berikutnya, SL dicek dulu, tanpa look-ahead). Kode repo TIDAK dijalankan.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .data import resample
from .github_popular import atr_w, ema, rsi
from .github_popular2 import adx_w, bph
from .github_popular3 import htf_closed, sma_tr
from .harness import Arrays, Period, fmt, periods, server_time, simulate, stats, to_base, trades_frame


def ewm_rsi(c: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(c).diff()
    g = s.where(s > 0, 0.0).ewm(alpha=1 / n, min_periods=n).mean()
    l_ = (-s.where(s < 0, 0.0)).ewm(alpha=1 / n, min_periods=n).mean()
    return (100 - 100 / (1 + g / l_)).to_numpy()


def ewm_adx(H: pd.DataFrame, n: int = 14) -> np.ndarray:
    h, l, c = (H[k] for k in ("high", "low", "close"))
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    up, dn = h - h.shift(), l.shift() - l
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    a = tr.ewm(alpha=1 / n, min_periods=n).mean()
    pdi = 100 * pdm.ewm(alpha=1 / n, min_periods=n).mean() / a
    mdi = 100 * mdm.ewm(alpha=1 / n, min_periods=n).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=1 / n, min_periods=n).mean().to_numpy()


# ================================================================ samw2591: strategi yang DINONAKTIFKAN penulis
def samw_macd(p: Period) -> pd.DataFrame:
    """strategies/signals.py check_macd_signal (config: enabled False, "11 tahun Sharpe -0,36"). H1: histogram MACD
    berbalik tanda + close di sisi EMA100 + ADX(EWM)>=18. SL = clamp(4,5 x rata-rata range 14, $10, $50), TP 8x,
    keluar saat histogram berbalik lagi, maks 20 bar."""
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    cs = pd.Series(c)
    macd = cs.ewm(span=12).mean() - cs.ewm(span=26).mean()
    hist = (macd - macd.ewm(span=9).mean()).to_numpy()
    e100 = cs.ewm(span=100).mean().to_numpy()
    atr = (H["high"] - H["low"]).rolling(14).mean().to_numpy()
    adx = ewm_adx(H)
    start = to_base(p.base, H.index)
    flip_dn = np.r_[False, (hist[1:] < 0) & (hist[:-1] >= 0)]
    flip_up = np.r_[False, (hist[1:] > 0) & (hist[:-1] <= 0)]
    rows, busy = [], -1
    for k in range(110, len(H) - 1):
        if adx[k] < 18:
            continue
        d = 1 if (flip_up[k] and c[k] > e100[k]) else (-1 if (flip_dn[k] and c[k] < e100[k]) else 0)
        if d == 0:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        sl = max(10.0, min(50.0, 4.5 * atr[k]))
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        ex = np.zeros(A.n, bool)
        opp = flip_dn if d > 0 else flip_up
        for kk in np.flatnonzero(opp[k + 1:k + 21]) + k + 1:
            if kk + 1 < len(H):
                ex[max(start[kk + 1] - 1, j0)] = True
        j1, rr = simulate(A, sp, j0, d, entry, entry - d * sl, entry + d * 8 * atr[k], 20 * bph(p), exit_mask=ex)
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


def samw_gapfill(p: Period) -> pd.DataFrame:
    """check_monday_gap_fill (config: enabled False; docstring klaim WR 79,3% Sharpe 0,92, config: "dua backtest
    Sharpe negatif"). Senin jam server <= 3: gap = close H1 - close Jumat; |gap|>=$2 -> lawan gap, SL = clamp(|gap|,
    $3, $30), TP = |gap|, 1x per Senin, maks 8 bar H1."""
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    c = H["close"].to_numpy(float)
    srv = server_time(H.index)
    dow, hr, day = srv.dayofweek.to_numpy(), srv.hour.to_numpy(), srv.normalize()
    start = to_base(p.base, H.index)
    fri_close, traded_day, rows, busy = None, None, [], -1
    for k in range(1, len(H) - 1):
        if dow[k] == 4:
            fri_close = c[k]
        if dow[k] != 0 or hr[k] > 3 or fri_close is None or traded_day == day[k]:
            continue
        gap = c[k] - fri_close
        if abs(gap) < 2:
            continue
        traded_day = day[k]
        d = -1 if gap > 0 else 1
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        sl, tp = max(3.0, min(30.0, abs(gap))), abs(gap)
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, rr = simulate(A, sp, j0, d, entry, entry - d * sl, entry + d * tp, 8 * bph(p))
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ================================================================ GifariKemal: ea-research/xaubot-mq5/Experts/XAUBot_Pro_V3.mq5
def xaubot_v3(p: Period, halt: str = "asli", atr_filter: bool = True) -> pd.DataFrame:
    """M15 + bias H1 (5 suara: EMA50/200, harga vs EMA, RSI 55/45, MACD, 2 dari 3 candle; >=3 suara). BUY: bias tidak
    bearish, EMA50>EMA200 M15, jarak close-EMA50 <= 0,3 ATR, RSI 40-70, ADX>=25, MACD>signal (SELL kebalikan, RSI
    30-60). Skor kualitas >= 60 (stabilitas ATR, jarak EMA, ADX, spread dianggap 20 point = 10, keselarasan H1),
    jeda 15 menit, maks 10 trade/hari, filter ATR M15 $5-25. Keluar (lot 0,01 -> $ = pergerakan harga): SL broker
    1 ATR, TP 2 ATR, stop keras -0,6 ATR, 'BE shield' (puncak >= 0,5 ATR lalu profit < $2), trailing (puncak >=
    0,6 ATR, mundur 0,3 ATR), EMA berbalik & profit < 0,3 ATR, 3 jam tidak untung, 5 jam mutlak, akhir pekan.
    halt='asli': canTrade=false setelah 3 kalah beruntun / rugi harian 5% / bulanan 10% dan HANYA dibuka lagi oleh
    trade menang (yang tak mungkin terjadi) -> EA berhenti permanen. halt='harian': diasumsikan reset tiap hari.
    R dihitung terhadap SL broker 1 ATR."""
    base = p.base
    A, sp = Arrays(base), p.spread
    M = resample(base, "15min")
    H = resample(base, "60min")
    mo, mh, ml, mc = (M[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ef, es = ema(mc, 50), ema(mc, 200)
    madx, mrsi = adx_w(M, 14), rsi(mc, 14)
    mm = ema(mc, 12) - ema(mc, 26)
    msig = ema(mm, 9)
    matr = sma_tr(M, 14)
    atr_avg = pd.Series(matr).rolling(96).mean().to_numpy()
    hc = H["close"].to_numpy(float)
    ho = H["open"].to_numpy(float)
    hm = ema(hc, 12) - ema(hc, 26)
    hb = {}
    hef, hes, hr_, hmm, hms = (htf_closed(M, H, v, 1, 0.25) for v in (ema(hc, 50), ema(hc, 200), rsi(hc, 14), hm,
                                                                         ema(hm, 9)))
    hclose = htf_closed(M, H, hc, 1, 0.25)
    bull3 = pd.Series((hc > ho).astype(float)).rolling(3).sum().to_numpy()
    bear3 = pd.Series((hc < ho).astype(float)).rolling(3).sum().to_numpy()
    hbull3, hbear3 = htf_closed(M, H, bull3, 1, 0.25), htf_closed(M, H, bear3, 1, 0.25)
    mstart = to_base(base, M.index)
    base_to_m = np.searchsorted(mstart, np.arange(A.n), side="right") - 1
    srv = server_time(base.index)
    b_dow, b_hr = srv.dayofweek.to_numpy(), srv.hour.to_numpy()
    mday = server_time(M.index).normalize().to_numpy()
    mmon = server_time(M.index).to_period("M").astype(str).to_numpy()
    minutes = {"M5": 5, "M15": 15}[p.tf]
    rows = []
    can_trade, consec, day_loss, mon_loss, cur_day, cur_mon, n_day = True, 0, 0.0, 0.0, None, None, 0
    k_last_trade = -10
    k = 300
    while k < len(M) - 1:
        if mday[k] != cur_day:
            cur_day, day_loss, n_day = mday[k], 0.0, 0
            if halt == "harian":
                can_trade, consec = True, 0
        if mmon[k] != cur_mon:
            cur_mon, mon_loss = mmon[k], 0.0
        a = matr[k]
        if not can_trade or np.isnan(a) or np.isnan(atr_avg[k]) or np.isnan(hes[k]) or n_day >= 10:
            k += 1
            continue
        bull = (hef[k] > hes[k]) + (hclose[k] > hef[k] and hclose[k] > hes[k]) + (hr_[k] > 55) + \
            (hmm[k] > hms[k] and hmm[k] > 0) + (hbull3[k] >= 2)
        bear = (hef[k] < hes[k]) + (hclose[k] < hef[k] and hclose[k] < hes[k]) + (hr_[k] < 45) + \
            (hmm[k] < hms[k] and hmm[k] < 0) + (hbear3[k] >= 2)
        bias = 1 if bull >= 3 else (-1 if bear >= 3 else 0)
        dev = abs(a - atr_avg[k]) / atr_avg[k]
        q = (20 if dev < 0.1 else 15 if dev < 0.2 else 10 if dev < 0.3 else 5)
        sep = abs(ef[k] - es[k]) / a
        q += 20 if sep > 2 else 15 if sep > 1.5 else 10 if sep > 1 else 5
        q += 20 if madx[k] >= 40 else 15 if madx[k] >= 30 else 10 if madx[k] >= 25 else 0
        q += 10
        q += 20 if ((bias == 1 and ef[k] > es[k]) or (bias == -1 and ef[k] < es[k])) else (10 if bias == 0 else 0)
        ok = q >= 60 and madx[k] >= 25 and k - k_last_trade >= 1 and (not atr_filter or 5.0 <= a <= 25.0)
        near = abs(mc[k] - ef[k]) / a <= 0.3
        d = 0
        if ok and near and bias >= 0 and ef[k] > es[k] and 40 <= mrsi[k] <= 70 and mm[k] > msig[k]:
            d = 1
        elif ok and near and bias <= 0 and ef[k] < es[k] and 30 <= mrsi[k] <= 60 and mm[k] < msig[k]:
            d = -1
        if d == 0:
            k += 1
            continue
        j0 = mstart[k + 1]
        if j0 >= A.n - 2:
            break
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        adj = sp if d < 0 else 0.0
        sl_px, tp_px = entry - d * a, entry + d * 2 * a
        peak, stop = 0.0, sl_px
        j, res, age = j0, None, 0
        while j < A.n - 1 and res is None:
            lo_fav = (A.l[j] - entry) if d > 0 else (entry - A.h[j] - adj)       # posisi terburuk di bar j
            hi_fav = (A.h[j] - entry) if d > 0 else (entry - A.l[j] - adj)       # posisi terbaik di bar j
            stop_fav = (stop - entry) * d
            if lo_fav <= stop_fav:                                                # stop (broker / dinamis) dulu
                px_fav = min(stop_fav, ((A.o[j] - entry) if d > 0 else (entry - A.o[j] - adj)))
                res = px_fav if j > j0 or stop == sl_px else stop_fav
                break
            if j > j0 and hi_fav >= 2 * a:
                res = 2 * a
                break
            peak = max(peak, hi_fav)
            cur = (A.c[j] - entry) if d > 0 else (entry - A.c[j] - adj)
            age = (j - j0 + 1) * minutes
            mk = base_to_m[j]
            ema_against = (ef[mk - 1] < es[mk - 1]) if d > 0 else (ef[mk - 1] > es[mk - 1])
            if ema_against and cur < 0.3 * a and j > j0:
                res = cur
            elif age >= 180 and cur <= 0:
                res = cur
            elif age >= 300:
                res = cur
            elif (b_dow[j] == 4 and b_hr[j] >= 22) and cur > -0.3 * a:
                res = cur
            else:                                                                 # stop dinamis utk bar berikut
                cand = [sl_px]
                if age >= 5:
                    cand.append(entry - d * 0.6 * a)
                if peak >= 0.5 * a:
                    cand.append(entry + d * 2.0)
                if peak >= 0.6 * a and age >= 5:
                    cand.append(entry + d * (peak - 0.3 * a))
                stop = max(cand) if d > 0 else min(cand)
            j += 1
        if res is None:
            break
        R = res / a
        rows.append((j0, j, d, R))
        n_day += 1
        k_last_trade = base_to_m[min(j, A.n - 1)]
        if R > 0:
            consec = 0
        else:
            consec += 1
            day_loss += -R * 1.0
            mon_loss += -R * 1.0
            if consec >= 3 or day_loss >= 5.0 or mon_loss >= 10.0:
                can_trade = False
        k = max(k + 1, base_to_m[min(j, A.n - 1)] + 1)
    return trades_frame(rows, base)


# ================================================================ francomascareloai/EA_SCALPER: MQL5/Experts/EA_ULTRA_AGGRESSIVE.mq5
def ultra_aggressive(p: Period) -> pd.DataFrame:
    """M15, di awal bar baru: EMA8 memotong EMA21 (RSI 30-70) -> arah potongan; kalau tidak, harga di level Fibo
    38,2/50/61,8% dari 50 bar (toleransi $0,05) searah EMA; atau RSI ekstrem di Fibo. SL = max($1,50; 1,5 ATR), TP 2R,
    1 posisi, stop harian DD 15%."""
    M = resample(p.base, "15min") if p.tf == "M5" else p.base
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (M[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    f, s, r = ema(c, 8), ema(c, 21), rsi(c, 14)
    atr = sma_tr(M, 14)
    hi50 = pd.Series(h).rolling(49).max().to_numpy()
    lo50 = pd.Series(l).rolling(49).min().to_numpy()
    mstart = to_base(p.base, M.index)
    rows, busy = [], -1
    for k in range(60, len(M) - 1):
        j0 = mstart[k]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        price = o[k]
        sh, sl_ = max(hi50[k - 1], o[k]), min(lo50[k - 1], o[k])
        rng = sh - sl_
        f382, f500, f618 = sh - 0.382 * rng, sh - 0.5 * rng, sh - 0.618 * rng
        at_fibo = min(abs(price - f382), abs(price - f500), abs(price - f618)) <= 0.05
        bull, bear = f[k - 1] > s[k - 1], f[k - 1] < s[k - 1]
        up = bull and f[k - 2] <= s[k - 2]
        dn = bear and f[k - 2] >= s[k - 2]
        rsi_ok = 30 < r[k - 1] < 70
        d = 1 if (up and rsi_ok) else (-1 if (dn and rsi_ok) else 0)
        if d == 0 and at_fibo:
            if bull and r[k - 1] <= 70 and price < f500:
                d = 1
            elif bear and r[k - 1] >= 30 and price > f500:
                d = -1
        if d == 0 and at_fibo:
            if r[k - 1] < 30 and price <= f618:
                d = 1
            elif r[k - 1] > 70 and price >= f382:
                d = -1
        if d == 0 or np.isnan(atr[k - 1]):
            continue
        risk = max(1.5, 1.5 * atr[k - 1])
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        j1, rr = simulate(A, sp, j0, d, entry, entry - d * risk, entry + d * 2 * risk, 5 * 24 * bph(p))
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


# ================================================================ AnggaKay: src/vektor_v6/direction.py + main.py (tanpa ML)
def angga_rules(p: Period) -> pd.DataFrame | None:
    """Arah berbasis aturan (filter ML tidak bisa ditiru: model tidak ada di repo). M5: candle raksasa (body > 2x
    rata-rata 5 bar, sumbu penolakan < 50% body) -> searah; ADX <= 20 -> mode sideways (sentuh BB 20/2 + Stoch 14/3
    K<25 & K>D untuk BUY); selain itu mesin tren (tembus Keltner 20/2, atau ADX>25 + DI searah + candle searah di
    atas EMA20). SL = clamp(1,5 ATR, $4, $8) (lewati bila ATR > $9). Tren/breakout = 'Kelas B' (prob ML < 0,8): TP 1x SL,
    BE di 0,5 SL, trailing $1. Sideways: lewati bila SL > $5,5; TP $4, BE $2."""
    if p.tf != "M5":
        return None
    base = p.base
    A, sp = Arrays(base), p.spread
    o, h, l, c = A.o, A.h, A.l, A.c
    cs = pd.Series(c)
    atr = sma_tr(base, 14)
    body = np.abs(c - o)
    avg5 = pd.Series(body).shift(1).rolling(5).mean().to_numpy()
    uw, lw = h - np.maximum(c, o), np.minimum(c, o) - l
    giant = body > 2 * avg5
    bull_exp = giant & (c > o) & (uw < 0.5 * body)
    bear_exp = giant & (c < o) & (lw < 0.5 * body)
    e20 = cs.ewm(span=20, adjust=False).mean().to_numpy()
    e9 = cs.ewm(span=9, adjust=False).mean().to_numpy()
    kup, klo = e20 + 2 * atr, e20 - 2 * atr
    adx = adx_w(base, 14)
    hh, ll, cc = base["high"], base["low"], base["close"]
    up, dn = hh.diff(), -ll.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = pd.Series(np.maximum(h - l, np.maximum(abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]]))))
    pdi = (pd.Series(pdm).ewm(alpha=1 / 14).mean() / trs.ewm(alpha=1 / 14).mean()).to_numpy()
    mdi = (pd.Series(mdm).ewm(alpha=1 / 14).mean() / trs.ewm(alpha=1 / 14).mean()).to_numpy()
    sma20, sd20 = cs.rolling(20).mean().to_numpy(), cs.rolling(20).std().to_numpy()
    lo14, hi14 = pd.Series(l).rolling(14).min(), pd.Series(h).rolling(14).max()
    kk = (100 * (cs - lo14) / (hi14 - lo14)).rolling(3).mean().to_numpy()
    kd = pd.Series(kk).rolling(3).mean().to_numpy()
    rows, busy = [], -1
    for k in range(80, A.n - 2):
        if k + 1 <= busy or np.isnan(atr[k]):
            continue
        side, sideways = 0, False
        if bull_exp[k] or bear_exp[k]:
            side = 1 if bull_exp[k] else -1
        elif adx[k] <= 20:
            sideways = True
            if (c[k] <= sma20[k] - 2 * sd20[k] or l[k] <= sma20[k] - 2 * sd20[k]) and kk[k] < 25 and kk[k] > kd[k]:
                side = 1
            elif (c[k] >= sma20[k] + 2 * sd20[k] or h[k] >= sma20[k] + 2 * sd20[k]) and kk[k] > 75 and kk[k] < kd[k]:
                side = -1
        else:
            if c[k] > kup[k]:
                side = 1
            elif adx[k] > 25 and pdi[k] > mdi[k] and c[k] >= e20[k] and c[k] > o[k] and (c[k - 1] < o[k - 1] or c[k] > e9[k]):
                side = 1
            elif c[k] < klo[k]:
                side = -1
            elif adx[k] > 25 and mdi[k] > pdi[k] and c[k] <= e20[k] and c[k] < o[k] and (c[k - 1] > o[k - 1] or c[k] < e9[k]):
                side = -1
        if side == 0:
            continue
        atr_pips = int(atr[k] * 10)
        if atr_pips > 90:
            continue
        sl = max(40, min(80, int(atr_pips * 1.5))) * 0.1
        j0 = k + 1
        entry = o[j0] + (sp if side > 0 else 0.0)
        if sideways:
            if sl > 5.5:
                continue
            j1, rr = simulate(A, sp, j0, side, entry, entry - side * sl, entry + side * 4.0, 2 * 24 * 12,
                              be_at=2.0 / sl)
        else:
            def trail(j, d, entry, cur):
                if (cur < entry) if d > 0 else (cur > entry):
                    return cur
                return max(cur, A.h[j] - 1.0) if d > 0 else min(cur, A.l[j] + sp + 1.0)
            j1, rr = simulate(A, sp, j0, side, entry, entry - side * sl, entry + side * sl, 2 * 24 * 12,
                              trail=trail, be_at=0.5)
        rows.append((j0, j1, side, rr))
        busy = j1
    return trades_frame(rows, base)


# ================================================================ nathanaela2002: training.py + place_order.py (MLP walk-forward)
def nathanaela_mlp(p: Period, threshold: float = 0.7) -> pd.DataFrame:
    """M30. Fitur penulis tanpa PMI & sentimen berita (datanya tidak ada): RSI14, MA20, Bollinger 20/2, engulfing,
    MACD 12/26/9, Stochastic 14/3, ATR14. Label = close berikutnya naik > 0,1%. MLP (scikit-learn) dilatih
    walk-forward: tiap 6 bulan dilatih ulang dengan SEMUA data sebelumnya (penulis: tanpa walk-forward — model dites di
    data latihnya sendiri). Sinyal: prob >= 0,7 BUY, <= 0,3 SELL. Syarat R:R >= 2 terhadap high/low 10 bar; SL di
    low/high 10 bar, TP 2R (place_order.py)."""
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    X30 = resample(p.base, "30min")
    A, sp = Arrays(p.base), p.spread
    o, h, l, c = (X30[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    cs = pd.Series(c)
    dl = cs.diff()
    rs = dl.where(dl > 0, 0).rolling(14).mean() / (-dl.where(dl < 0, 0)).rolling(14).mean()
    feat = pd.DataFrame({
        "rsi": 100 - 100 / (1 + rs), "ma": cs.rolling(20).mean(),
        "bbu": cs.rolling(20).mean() + 2 * cs.rolling(20).std(), "bbl": cs.rolling(20).mean() - 2 * cs.rolling(20).std(),
        "beng": ((np.r_[np.nan, c[:-1]] < np.r_[np.nan, o[:-1]]) & (c > o) & (o < np.r_[np.nan, c[:-1]])
                 & (c > np.r_[np.nan, o[:-1]])).astype(float),
        "seng": ((np.r_[np.nan, c[:-1]] > np.r_[np.nan, o[:-1]]) & (c < o) & (o > np.r_[np.nan, c[:-1]])
                 & (c < np.r_[np.nan, o[:-1]])).astype(float),
    })
    m = cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()
    feat["macd"], feat["macds"] = m, m.ewm(span=9, adjust=False).mean()
    lo14, hi14 = pd.Series(l).rolling(14).min(), pd.Series(h).rolling(14).max()
    feat["k"] = 100 * (cs - lo14) / (hi14 - lo14)
    feat["d"] = feat["k"].rolling(3).mean()
    feat["atr"] = sma_tr(X30, 14)
    y = ((np.r_[c[1:], np.nan] - c) / c > 0.001).astype(float)
    Xv = feat.to_numpy()
    ok = ~np.isnan(Xv).any(axis=1)
    idx = X30.index
    prob = np.full(len(c), np.nan)
    first = idx[0] + pd.DateOffset(years=1)
    edges = pd.date_range(first, idx[-1] + pd.DateOffset(months=6), freq="6MS", tz=idx.tz)
    for a_, b_ in zip(edges[:-1], edges[1:]):
        tr = ok & (idx < a_ - pd.Timedelta(hours=1))
        te = ok & (idx >= a_) & (idx < b_)
        if tr.sum() < 2000 or te.sum() == 0:
            continue
        sc = StandardScaler().fit(Xv[tr])
        mdl = MLPClassifier(hidden_layer_sizes=(64, 32), early_stopping=True, max_iter=200, random_state=0)
        mdl.fit(sc.transform(Xv[tr]), y[tr])
        prob[te] = mdl.predict_proba(sc.transform(Xv[te]))[:, 1]
    start = to_base(p.base, X30.index)
    hi10 = pd.Series(h).rolling(10).max().shift(1).to_numpy()
    lo10 = pd.Series(l).rolling(10).min().shift(1).to_numpy()
    rows, busy = [], -1
    for k in range(20, len(c) - 1):
        if np.isnan(prob[k]):
            continue
        d = 1 if prob[k] >= threshold else (-1 if prob[k] <= 1 - threshold else 0)
        if d == 0:
            continue
        pot_p = (hi10[k] - c[k]) if d > 0 else (c[k] - lo10[k])
        pot_l = (c[k] - lo10[k]) if d > 0 else (hi10[k] - c[k])
        if pot_l <= 0 or pot_p / pot_l < 2:
            continue
        j0 = start[k + 1]
        if j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        stop = lo10[k] if d > 0 else hi10[k]
        if (entry - stop) * d <= 0:
            continue
        j1, rr = simulate(A, sp, j0, d, entry, stop, entry + d * 2 * abs(entry - stop), 2 * 24 * bph(p))
        rows.append((j0, j1, d, rr))
        busy = j1
    return trades_frame(rows, p.base)


TESTS = {
    "samw_macd H1 (dinonaktifkan penulis)": samw_macd,
    "samw_gapfill Senin (dinonaktifkan penulis)": samw_gapfill,
    "xaubot_v3 asli (berhenti permanen)": xaubot_v3,
    "xaubot_v3 halt direset harian": lambda p: xaubot_v3(p, "harian"),
    "xaubot_v3 reset harian, tanpa filter ATR $5-25": lambda p: xaubot_v3(p, "harian", atr_filter=False),
    "ultra_aggressive M15 (EA_SCALPER)": ultra_aggressive,
    "angga_rules M5 tanpa ML (AnggaKay)": angga_rules,
    "nathanaela_mlp M30 walk-forward": nathanaela_mlp,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else ""
    ps = periods()
    for name, fn in TESTS.items():
        if only and only not in name:
            continue
        print(name, flush=True)
        tot = []
        for p in ps:
            t = fn(p)
            if t is None:
                print(f"   {p.name}: - (butuh data M5)")
                continue
            tot.append(t.R.to_numpy() if len(t) else np.array([]))
            print(f"   {p.name}: {fmt(stats(t.R))}", flush=True)
        if tot:
            allr = np.concatenate(tot)
            pos = sum(1 for x in tot if len(x) and x.sum() > 0)
            print(f"   TOTAL  : {fmt(stats(allr))} | periode positif {pos}/{len(tot)}", flush=True)


if __name__ == "__main__":
    main()
