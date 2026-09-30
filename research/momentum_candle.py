"""Metode "Momentum Candle" (Rizki Aditama, buku Trading Alchemist / Sekolah Trading) vs sinyal 💰 kita.

python -m research.momentum_candle

Permintaan pengguna (30 Sep 2026): telusuri buku Trading Alchemist (Rizki Aditama), bandingkan dengan strategi kita,
ambil yang baik. Isi buku (137 hlm., berbayar) tidak tersedia; aturan diambil dari materi publik penulis & komunitas
(ringkasan pencarian web 30 Sep 2026): momentum candle = candle berbadan besar & dominan dengan sumbu kecil yang
menembus supply/demand kecil; entry setelah candle TUTUP, timeframe M5/M15 dengan validasi arah H1-H4; SL di bawah/atas
candle momentum; TP ke S/R terdekat atau minimal RR 1:1,5; BE hanya setelah minor BOS (bukan karena floating kecil);
maksimal 2 momentum candle per hari.

Aturan yang ditulis ulang (ditetapkan sebelum melihat hasil), mesin research/harness.py (spread, entry di open bar
berikutnya, SL dicek lebih dulu, tanpa look-ahead):
- MC naik: close > open, badan >= k x ATR14 (k = 1,0 / 1,5), total sumbu <= 30% range, close > high tertinggi 10 bar
  sebelumnya (menembus "supply kecil"). MC turun kebalikannya.
- Validasi arah (candle HTF yang sudah tutup): tanpa / close H1 vs EMA50 H1 / close H4 vs EMA50 H4.
- Entry open bar berikutnya; SL = low MC (BUY) / high MC (SELL); TP = 1,5R / 2R; BE: tanpa / di +1R.
- Maksimal 2 entry per hari (jam server NY+7), satu posisi sekaligus, tutup paksa setelah 1 hari.
- Timeframe: M15 (2012-2026) dan M5 (2022-2026, data M5 hanya ada sejak 2022).
Laporan: per periode harness, LAMA (< Okt 2021) vs BARU, dan pembanding sinyal 💰 XAU (research/eksternal.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import resample
from .github_popular import atr_w, ema
from .harness import Arrays, Period, fmt, periods, server_time, simulate, stats

NEW = pd.Timestamp("2021-10-01", tz="UTC")
LOOKBACK = 10
WICK_MAX = 0.30
MAX_PER_DAY = 2


def htf_dir(base: pd.DataFrame, tf_min: int, rule: str, n: int = 50) -> np.ndarray:
    """Arah close vs EMA-n candle HTF terakhir yang SUDAH TUTUP saat bar dasar ditutup (+1 / -1 / 0)."""
    X = resample(base, rule)
    c = X.close.to_numpy(float)
    d = np.sign(c - ema(c, n))
    d[:n] = 0
    s = pd.Series(d, index=X.index + pd.Timedelta(rule))              # waktu tutup candle HTF
    close_base = base.index + pd.Timedelta(minutes=tf_min)
    return s.reindex(close_base, method="ffill").fillna(0).to_numpy()


def momentum_candle(base: pd.DataFrame, tf_min: int, sp: float, k: float = 1.0, htf: str | None = None,
                    rr: float = 1.5, be: float | None = None) -> pd.DataFrame:
    A = Arrays(base)
    o, h, l, c = A.o, A.h, A.l, A.c
    atr = atr_w(base, 14)
    prev_atr = np.r_[np.nan, atr[:-1]]
    body = np.abs(c - o)
    rng = h - l
    wick = rng - body
    hh = pd.Series(h).shift(1).rolling(LOOKBACK).max().to_numpy()
    ll = pd.Series(l).shift(1).rolling(LOOKBACK).min().to_numpy()
    ok = (body >= k * prev_atr) & (wick <= WICK_MAX * rng) & (rng > 0)
    bull = ok & (c > o) & (c > hh)
    bear = ok & (c < o) & (c < ll)
    if htf:
        d = htf_dir(base, tf_min, htf)
        bull &= d > 0
        bear &= d < 0
    day = server_time(base.index).normalize()
    bars_day = 24 * 60 // tf_min
    rows, busy_until, count = [], -1, {}
    for j in np.flatnonzero(bull | bear):
        j0 = j + 1
        if j0 >= A.n - 1 or j0 <= busy_until:
            continue
        dd = day[j]
        if count.get(dd, 0) >= MAX_PER_DAY:
            continue
        side = 1 if bull[j] else -1
        entry = o[j0] + (sp if side > 0 else 0.0)
        sl = l[j] if side > 0 else h[j] + sp
        risk = (entry - sl) * side
        if risk <= 0:
            continue
        j1, r = simulate(A, sp, j0, side, entry, sl, entry + side * rr * risk, bars_day, be_at=be)
        rows.append((base.index[j0], side, r))
        count[dd] = count.get(dd, 0) + 1
        busy_until = j1
    return pd.DataFrame(rows, columns=["time", "dir", "R"])


def money_signals() -> pd.DataFrame:
    """Sinyal 💰 XAU (yang dikirim cloud) dengan hasil R-nya, untuk pembanding."""
    from .eksternal import asset
    m = asset("XAUUSD").money
    return pd.DataFrame({"time": m.t.to_numpy(), "R": m.R.to_numpy()})


def summary(name: str, t: pd.DataFrame, years: float | None = None) -> str:
    if t.empty:
        return f"{name:52} n=0"
    s = stats(t.R)
    lama, baru = t[t.time < NEW].R, t[t.time >= NEW].R
    yr = t.groupby(t.time.dt.year).R.sum()
    per_year = f" | {len(t) / years:5.0f} trade/th, {t.R.sum() / years:+6.1f}R/th" if years else ""
    return (f"{name:52} {fmt(s)} | LAMA {lama.mean() if len(lama) else float('nan'):+.3f}R (n={len(lama)}) "
            f"BARU {baru.mean() if len(baru) else float('nan'):+.3f}R (n={len(baru)}) | tahun+ "
            f"{(yr > 0).mean() * 100:.0f}% dari {len(yr)}{per_year}")


def variants():
    for k in (1.0, 1.5):
        for htf in (None, "60min", "240min"):
            for rr in (1.5, 2.0):
                for be in (None, 1.0):
                    yield k, htf, rr, be


def label(k, htf, rr, be) -> str:
    v = {None: "tanpa validasi", "60min": "H1 EMA50", "240min": "H4 EMA50"}[htf]
    return f"MC {k:.1f}xATR, {v}, TP {rr}R" + (", BE +1R" if be else "")


def main() -> None:
    ps = periods()
    m15 = [(p, p.base if p.tf == "M15" else resample(p.base, "15min")) for p in ps]
    m5 = [(p, p.base) for p in ps if p.tf == "M5"]
    span = {"M15": (m15[0][1].index[0], m15[-1][1].index[-1]), "M5": (m5[0][1].index[0], m5[-1][1].index[-1])}
    rows = []
    for tf, parts, tf_min in (("M15", m15, 15), ("M5", m5, 5)):
        years = (span[tf][1] - span[tf][0]).days / 365.25
        print(f"== {tf} ({span[tf][0]:%Y-%m} .. {span[tf][1]:%Y-%m}) ==", flush=True)
        for v in variants():
            per = []
            for p, base in parts:
                per.append((p.name, momentum_candle(base, tf_min, p.spread, *v)))
            t = pd.concat([x for _, x in per if len(x)]) if any(len(x) for _, x in per) else pd.DataFrame(
                columns=["time", "dir", "R"])
            pos = sum(1 for _, x in per if len(x) and x.R.sum() > 0)
            line = summary(f"{tf} {label(*v)}", t, years) + f" | periode+ {pos}/{len(per)}"
            print(line, flush=True)
            rows.append((tf, v, t, pos, len(per)))
    print("\n== Pembanding: sinyal 💰 XAU (cloud, H1) ==")
    ms = money_signals()
    ms["time"] = pd.to_datetime(ms.time, utc=True)
    for tf in ("M15", "M5"):
        a, b = span[tf]
        mm = ms[(ms.time >= a) & (ms.time <= b)]
        print(summary(f"💰 XAU, periode yang sama dengan {tf}", mm, (b - a).days / 365.25))
    def ok(t: pd.DataFrame, pos: int, n: int) -> bool:
        lama, baru = t[t.time < NEW].R, t[t.time >= NEW].R
        return (len(t) >= 30 and (len(lama) == 0 or lama.mean() > 0) and len(baru) > 0 and baru.mean() > 0
                and pos >= 0.75 * n)
    lolos = [r for r in rows if ok(r[2], r[3], r[4])]
    print(f"\nLolos (rata > 0 di LAMA & BARU [M5: hanya BARU], >= 75% periode positif, n >= 30): {len(lolos)}")
    for tf, v, t, pos, n in lolos:
        print("  " + summary(f"{tf} {label(*v)}", t))


if __name__ == "__main__":
    main()
