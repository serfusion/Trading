"""Strategi pembanding (pra-didaftarkan sebelum melihat hasil OOS).

1. Donchian / time-series momentum (Turtle): breakout N bar, stop ATR, exit channel M bar.
2. Asia range breakout saat London: stop order di high/low range Asia, SL sisi lain.
Semua entry di open bar berikutnya setelah sinyal (tanpa look-ahead), BUY bayar spread.
Hasil dalam R (kelipatan risiko awal).
"""
from __future__ import annotations

import pandas as pd

from xau_bot.smc import atr


def donchian(df: pd.DataFrame, spread: float, n_entry: int = 55, n_exit: int = 20,
             atr_n: int = 20, stop_atr: float = 2.0, long_only: bool = False) -> pd.DataFrame:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, atr_n)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    trades = []
    pos, entry, stop, risk, t0 = 0, 0.0, 0.0, 0.0, 0
    for i in range(max(n_entry, atr_n) + 1, len(df) - 1):
        if pos != 0:
            # stop (konservatif: dicek dulu), lalu exit channel pada close
            if pos > 0 and l[i] <= stop:
                px = min(stop, o[i])
                trades.append((t0, i, pos, (px - entry) / risk))
                pos = 0
            elif pos < 0 and h[i] + spread >= stop:
                px = max(stop, o[i] + spread)
                trades.append((t0, i, pos, (entry - px) / risk))
                pos = 0
            elif pos > 0 and c[i] < lo_x[i]:
                px = o[i + 1]
                trades.append((t0, i + 1, pos, (px - entry) / risk))
                pos = 0
                continue
            elif pos < 0 and c[i] > hi_x[i]:
                px = o[i + 1] + spread
                trades.append((t0, i + 1, pos, (entry - px) / risk))
                pos = 0
                continue
        if pos == 0:
            if c[i] > hi_e[i]:
                entry = o[i + 1] + spread
                stop = entry - stop_atr * a[i]
                pos, risk, t0 = 1, stop_atr * a[i], i + 1
            elif c[i] < lo_e[i] and not long_only:
                entry = o[i + 1]
                stop = entry + stop_atr * a[i]
                pos, risk, t0 = -1, stop_atr * a[i], i + 1
    return pd.DataFrame(trades, columns=["i0", "i1", "dir", "R"]).assign(time=lambda x: df.index[x.i0])


def asia_breakout(df: pd.DataFrame, spread: float, tp_mult: float = 1.0, sl_mode: str = "opposite",
                  min_range_atr: float = 0.0) -> pd.DataFrame:
    """Range Asia 20:00-00:00 NY; order stop aktif 02:00-08:00 NY; tutup paksa 12:00 NY."""
    ny = df.index.tz_convert("America/New_York")
    day = (ny + pd.Timedelta(hours=7)).date
    minutes = ny.hour * 60 + ny.minute
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    trades = []
    frame = pd.DataFrame({"day": day, "m": minutes})
    for d, g in frame.groupby("day", sort=True):
        pos_idx = g.index.to_numpy()
        asia = [i for i, m in zip(pos_idx, g.m) if m >= 20 * 60]
        if len(asia) < 8:
            continue
        rh, rl = h[asia].max(), l[asia].min()
        rng = rh - rl
        if rng <= 0:
            continue
        window = [i for i, m in zip(pos_idx, g.m) if 2 * 60 <= m < 8 * 60]
        close_i = [i for i, m in zip(pos_idx, g.m) if 12 * 60 <= m < 12 * 60 + 15]
        if not window:
            continue
        end_i = close_i[0] if close_i else window[-1]
        for i in window:
            up = h[i] >= rh  # buy stop di rh (+spread) terpicu saat bid >= rh
            dn = l[i] <= rl
            if up and dn:
                break  # dua sisi tersentuh di bar yang sama -> lewati (ambigu)
            if up or dn:
                d_ = 1 if up else -1
                entry = (max(rh, o[i]) + spread) if up else min(rl, o[i])
                sl = (rl if sl_mode == "opposite" else (rh + rl) / 2) if up else (
                    rh + spread if sl_mode == "opposite" else (rh + rl) / 2 + spread)
                risk = abs(entry - sl)
                tp = entry + d_ * tp_mult * risk
                r = None
                for j in range(i + 1, end_i + 1):
                    if (l[j] <= sl) if d_ > 0 else (h[j] + spread >= sl):
                        r = -1.0
                        break
                    if (h[j] >= tp) if d_ > 0 else (l[j] + spread <= tp):
                        r = tp_mult
                        break
                if r is None:
                    px = c[end_i] + (0 if d_ > 0 else spread)
                    r = (px - entry) * d_ / risk
                # SL di bar entry (konservatif)
                if ((l[i] <= sl) if d_ > 0 else (h[i] + spread >= sl)):
                    r = -1.0
                trades.append((i, end_i, d_, r))
                break
    return pd.DataFrame(trades, columns=["i0", "i1", "dir", "R"]).assign(time=lambda x: df.index[x.i0])
