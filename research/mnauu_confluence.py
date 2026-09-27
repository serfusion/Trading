"""Uji ulang klaim Mnauu2201/Bot-Trade-Fucking-Gold (win rate 62,3%, R:R 1:2) di data M1 asli Feb-Mei 2026.

python -m research.mnauu_confluence

Aturan disalin dari strategy/confluence.py, structure.py, price_action.py dan backtest.py penulis:
- Struktur BOS/CHoCH H4 & H1 (swing lookback 3, jendela 200 bar) -> arah (+1 bila sepakat, +0,5 bila H1 saja)
- Harga menguji Order Block H1 searah (+1) atau FVG H1 (+0,5); 5 zona terakhir, toleransi 10% tinggi zona
- Pin bar / engulfing / rejection di candle terakhir M15 & M5 (+1 bila rejection, +0,5 lainnya)
- BOS/CHoCH M1 (lookback 2, jendela 100) searah (+1); sinyal bila skor >= 3,5
- SL = tepi zona -/+ 50% tinggi zona, TP = 2R, entry = close M1; cek tiap 5 menit; sinyal searah < 60 menit
  digabung; menunggu hasil maks 800 candle M1; SL dicek sebelum TP; tanpa spread.

Dua versi:
- "seperti backtest penulis": candle H4/H1/M15/M5 diambil dengan `time <= waktu_sekarang` (waktu = jam BUKA),
  sehingga candle yang sedang berjalan ikut dipakai dengan harga PENUTUPAN FINALNYA (mengintip masa depan).
- "diperbaiki": hanya candle yang sudah tutup.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_parquet_utc
from .harness import server_time

DATA = Path(os.getenv("XAU_DATA_DIR", "data/research"))
TF_MIN = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240}


class TF:
    def __init__(self, df: pd.DataFrame, minutes: int, lookback: int, window: int):
        self.t_open = df.index.values.astype("datetime64[m]")
        self.t_close = self.t_open + np.timedelta64(minutes, "m")
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.n, self.L, self.W = len(df), lookback, window
        w = 2 * lookback + 1
        hmax = pd.Series(self.h).rolling(w, center=True).max().to_numpy()
        lmin = pd.Series(self.l).rolling(w, center=True).min().to_numpy()
        self.sh = np.flatnonzero(self.h == hmax)
        self.sl = np.flatnonzero(self.l == lmin)

    def idx(self, t_now: np.datetime64, lookahead: bool, base_min: int = 1) -> int:
        """Index candle terakhir yang dipakai pada waktu t_now (jam buka candle dasar saat ini)."""
        if lookahead:
            return int(np.searchsorted(self.t_open, t_now, side="right")) - 1
        return int(np.searchsorted(self.t_close, t_now + np.timedelta64(base_min, "m"), side="right")) - 1

    def structure(self, k: int, last_close: float | None = None) -> int:
        lo_b, hi_b = k - self.W + 1 + self.L, k - self.L
        a, b = np.searchsorted(self.sh, lo_b), np.searchsorted(self.sh, hi_b, side="right")
        c_, d_ = np.searchsorted(self.sl, lo_b), np.searchsorted(self.sl, hi_b, side="right")
        if b - a < 2 or d_ - c_ < 2:
            return 0
        close = self.c[k] if last_close is None else last_close
        if close > self.h[self.sh[b - 1]]:
            return 1
        if close < self.l[self.sl[d_ - 1]]:
            return -1
        return 0


def zones_h1(h1: TF):
    o, c, h, l = h1.o, h1.c, h1.h, h1.l
    move = np.abs(c - o) / o * 100
    ob_idx, ob = [], []
    for i in range(1, h1.n):
        if move[i] < 0.15:
            continue
        bull, pb, pbull = c[i] > o[i], c[i - 1] < o[i - 1], c[i - 1] > o[i - 1]
        if bull and pb:
            ob_idx.append(i)
            ob.append((1, o[i - 1], c[i - 1]))      # (arah, atas, bawah)
        elif not bull and pbull:
            ob_idx.append(i)
            ob.append((-1, c[i - 1], o[i - 1]))
    fvg_idx, fvg = [], []
    for i in range(2, h1.n):
        if l[i] > h[i - 2]:
            fvg_idx.append(i)
            fvg.append((1, l[i], h[i - 2]))
        elif h[i] < l[i - 2]:
            fvg_idx.append(i)
            fvg.append((-1, l[i - 2], h[i]))
    return np.array(ob_idx), ob, np.array(fvg_idx), fvg


def in_zone(p, top, bot):
    tol = (top - bot) * 0.1
    return bot - tol <= p <= top + tol


def pa_signals(tf: TF, k: int, zone) -> list[tuple[int, str]]:
    o, h, l, c = tf.o, tf.h, tf.l, tf.c
    out = []
    body = abs(c[k] - o[k])
    up, dn = h[k] - max(c[k], o[k]), min(c[k], o[k]) - l[k]
    if body > 0:
        if dn >= 2 * body and dn > up:
            out.append((1, "pin"))
        elif up >= 2 * body and up > dn:
            out.append((-1, "pin"))
    pb, cb = c[k - 1] > o[k - 1], c[k] > o[k]
    if pb and not cb and o[k] >= c[k - 1] and c[k] <= o[k - 1]:
        out.append((-1, "engulf"))
    if not pb and cb and o[k] <= c[k - 1] and c[k] >= o[k - 1]:
        out.append((1, "engulf"))
    if zone is not None:
        top, bot = zone
        if l[k] <= top and h[k] >= bot:
            if c[k] > top:
                out.append((1, "rejection"))
            elif c[k] < bot:
                out.append((-1, "rejection"))
    return out


def run(m1: pd.DataFrame, lookahead: bool, spread: float = 0.0, step: int = 5, min_score: float = 3.5,
        wait: int = 800, base_min: int = 1) -> pd.DataFrame:
    """base_min=5: pendekatan di data M5 (trigger 'M1' memakai M5, cek tiap candle M5, tunggu 160 candle)."""
    idx = server_time(m1.index)
    base = m1.set_axis(idx)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    tfs = {name: base.resample(f"{mins}min", label="left", closed="left").agg(agg).dropna()
           for name, mins in TF_MIN.items() if name != "M1"}
    M1 = TF(base, base_min, 2, 100)
    T = {k: TF(v, TF_MIN[k], 3, 200) for k, v in tfs.items()}
    ob_i, ob, fvg_i, fvg = zones_h1(T["H1"])
    rows, last_sig = [], {1: None, -1: None}
    for i in range(200, M1.n - 1, step):
        t = M1.t_open[i]
        k4, k1, k15, k5 = (T[n].idx(t, lookahead, base_min) for n in ("H4", "H1", "M15", "M5"))
        if min(k4, k1, k15, k5) < 20:
            continue
        price = M1.c[i]
        s4, s1 = T["H4"].structure(k4), T["H1"].structure(k1)
        score = 0.0
        if s4 and s4 == s1:
            d, score = s4, 1.0
        elif s1:
            d, score = s1, 0.5
        else:
            continue
        zone = None
        lo_ob = np.searchsorted(ob_i, k1 - 199 + 1)
        hi_ob = np.searchsorted(ob_i, k1 - 1, side="right")
        for j in range(max(lo_ob, hi_ob - 5), hi_ob):
            zd, top, bot = ob[j]
            if zd == d and in_zone(price, top, bot):
                zone, score = (top, bot), score + 1.0
                break
        if zone is None:
            lo_f = np.searchsorted(fvg_i, k1 - 199 + 2)
            hi_f = np.searchsorted(fvg_i, k1, side="right")
            for j in range(max(lo_f, hi_f - 5), hi_f):
                zd, top, bot = fvg[j]
                if zd == d and in_zone(price, top, bot):
                    zone, score = (top, bot), score + 0.5
                    break
        pas = [s for tf in ("M15", "M5") for s in pa_signals(T[tf], T[tf].idx(t, lookahead, base_min), zone)
               if s[0] == d]
        if pas:
            score += 1.0 if any(k == "rejection" for _, k in pas) else 0.5
        if M1.structure(i, price) == d:
            score += 1.0
        if score < min_score or zone is None:
            continue
        if last_sig[d] is not None and (t - last_sig[d]) < np.timedelta64(60, "m"):
            continue
        last_sig[d] = t
        top, bot = zone
        buf = (top - bot) * 0.5
        entry = price + (spread if d > 0 else 0.0)
        sl = bot - buf if d > 0 else top + buf
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + d * 2 * risk
        res, px = "TIMEOUT", None
        end = min(M1.n - 1, i + wait)
        for j in range(i + 1, end + 1):
            if d > 0:
                if M1.l[j] <= sl:
                    res, px = "LOSS", sl
                    break
                if M1.h[j] >= tp:
                    res, px = "WIN", tp
                    break
            else:
                if M1.h[j] + spread >= sl:
                    res, px = "LOSS", sl
                    break
                if M1.l[j] + spread <= tp:
                    res, px = "WIN", tp
                    break
        if px is None:
            px = M1.c[end] + (spread if d < 0 else 0.0)
        rows.append((m1.index[i], d, score, res, (px - entry) * d / risk, risk))
    return pd.DataFrame(rows, columns=["time", "dir", "score", "result", "R", "risk"])


def summary(t: pd.DataFrame) -> str:
    w, lo, to = (t.result == "WIN").sum(), (t.result == "LOSS").sum(), (t.result == "TIMEOUT").sum()
    dec = w + lo
    return (f"sinyal {len(t)} | menang {w} kalah {lo} timeout {to} | win rate (cara penulis, tanpa timeout) "
            f"{w / dec * 100 if dec else 0:.1f}% | win rate semua {w / len(t) * 100 if len(t) else 0:.1f}% | "
            f"rata {t.R.mean():+.3f}R | total {t.R.sum():+.1f}R | risiko median ${t.risk.median():.2f}")


def main():
    m1 = load_parquet_utc(DATA / "Sai310421_xauusd-data/parquet/XAUUSD_M1_90d_20260526.parquet")
    print(f"Data M1 {m1.index[0]:%Y-%m-%d} s/d {m1.index[-1]:%Y-%m-%d}, {len(m1)} candle")
    for label, la, sp in [("Seperti backtest penulis (look-ahead, tanpa spread)", True, 0.0),
                          ("Diperbaiki: hanya candle tertutup, tanpa spread", False, 0.0),
                          ("Diperbaiki + spread 0,25", False, 0.25)]:
        print(label)
        print("   " + summary(run(m1, la, sp)))
    from .run_scan import dataset
    m5 = dataset("m5_2025")[0]
    print(f"Pendekatan di data M5 {m5.index[0]:%Y-%m} s/d {m5.index[-1]:%Y-%m} (trigger M1 diganti M5)")
    for label, la, sp in [("Seperti backtest penulis (look-ahead, tanpa spread)", True, 0.0),
                          ("Diperbaiki + spread 0,25", False, 0.25)]:
        print(label)
        print("   " + summary(run(m5, la, sp, step=1, wait=160, base_min=5)))


if __name__ == "__main__":
    main()
