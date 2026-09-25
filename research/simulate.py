"""Simulasi hasil setup dalam satuan R (risiko), harga bar = BID, ASK = BID + spread.

Aturan sama dengan PaperBroker/engine: limit order terisi bila harga menyentuh entry,
dibatalkan bila TP1 tersentuh sebelum terisi atau kedaluwarsa; bila SL & TP di bar
yang sama -> dianggap SL (konservatif).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(setups: pd.DataFrame, df: pd.DataFrame, spread: float, mode: str = "split",
             expiry_bars: int = 24, be_offset: float = 0.10, fixed_r: float = 0.0,
             max_hold: int = 2000, partial: float = 0.5) -> pd.DataFrame:
    """mode: split (TP1 parsial + BE + TP2) | tp2 | tp1 | fixed (TP = fixed_r * R)."""
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    res = []
    for s in setups.itertuples(index=False):
        d = s.dir
        e, sl, t1, t2 = s.entry, s.sl, s.tp1, s.tp2
        if mode == "fixed":
            t2 = e + d * fixed_r * abs(e - sl)
        risk = abs(e - sl)
        # harga pemicu dalam 'ruang bid': sell SL/TP dipicu ASK -> kurangi spread
        adj = spread if d < 0 else 0.0
        status, fill_i, exit_i, r = "expired", -1, -1, 0.0
        filled = False
        cur_sl = sl
        tp1_done = False
        fill_price = e
        j = s.t + 1
        end = min(n, s.t + 1 + max_hold)
        while j < end:
            if not filled:
                if j - s.t > expiry_bars:
                    break
                touched = h[j] >= e if d < 0 else lo[j] + spread <= e
                if touched:
                    filled, fill_i = True, j
                    fill_price = max(e, o[j]) if d < 0 else min(e, o[j] + spread)
                else:
                    reached_t1 = (lo[j] + adj <= t1) if d < 0 else (h[j] >= t1)
                    if reached_t1:
                        status = "missed"
                        break
                    j += 1
                    continue
            # posisi terbuka: cek SL dulu (konservatif)
            hit_sl = (h[j] + adj >= cur_sl) if d < 0 else (lo[j] <= cur_sl)
            if hit_sl:
                px = cur_sl
                if j != fill_i:
                    px = max(cur_sl, o[j] + adj) if d < 0 else min(cur_sl, o[j])
                rem = (1 - partial) if tp1_done else 1.0
                r += rem * (px - fill_price) * d / risk
                status, exit_i = ("be" if tp1_done else "sl"), j
                break
            if j == fill_i:
                j += 1  # konservatif: di bar pengisian hanya SL yang boleh kena
                continue
            if mode == "split" and not tp1_done:
                if (lo[j] + adj <= t1) if d < 0 else (h[j] >= t1):
                    r += partial * (t1 - fill_price) * d / risk
                    tp1_done = True
                    new_sl = fill_price + d * be_offset
                    # BE berlaku mulai bar berikutnya (sama seperti engine)
                    if ((lo[j] + adj <= t2) if d < 0 else (h[j] >= t2)):
                        r += (1 - partial) * (t2 - fill_price) * d / risk
                        status, exit_i = "tp2", j
                        break
                    cur_sl = new_sl
                    j += 1
                    continue
            target = t1 if mode == "tp1" else t2
            if (lo[j] + adj <= target) if d < 0 else (h[j] >= target):
                rem = (1 - partial) if (mode == "split" and tp1_done) else 1.0
                r += rem * (target - fill_price) * d / risk
                status, exit_i = ("tp2" if mode != "tp1" else "tp1"), j
                break
            j += 1
        else:
            if filled:
                px = c[end - 1] + (adj if d < 0 else 0.0)
                rem = (1 - partial) if tp1_done else 1.0
                r += rem * (px - fill_price) * d / risk
                status, exit_i = "timeout", end - 1
        res.append((status, fill_i, exit_i, r if filled else np.nan))
    out = setups.copy()
    out[["status", "fill_i", "exit_i", "R"]] = pd.DataFrame(res, index=out.index)
    return out


def stats(sim: pd.DataFrame) -> dict:
    t = sim[sim["fill_i"] >= 0]
    if t.empty:
        return {"trades": 0, "win%": 0, "expR": 0, "PF": 0, "sumR": 0, "maxDD_R": 0}
    r = t["R"].to_numpy()
    wins, losses = r[r > 0], r[r < 0]
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {
        "trades": len(r), "win%": round(100 * len(wins) / len(r), 1),
        "expR": round(r.mean(), 3), "PF": round(wins.sum() / -losses.sum(), 2) if len(losses) else float("inf"),
        "sumR": round(r.sum(), 1), "maxDD_R": round(dd, 1),
    }


def simulate_plan(setups: pd.DataFrame, df: pd.DataFrame, spread: float, t1_r: float | None = 1.0,
                  t2_r: float | None = None, partial: float = 1.0, be: bool = True,
                  sl_widen: float = 0.0, expiry_bars: int = 24, be_offset: float = 0.10,
                  max_hold: int = 2000) -> pd.DataFrame:
    """Rencana umum: SL bisa diperlebar (fraksi risiko), T1 = t1_r*R (None = TP1 setup),
    `partial` ditutup di T1 (1.0 = semua), sisa ke T2 (t2_r*R atau TP2 setup), BE setelah T1."""
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    out = []
    for s in setups.itertuples(index=False):
        d, e = s.dir, s.entry
        sl = s.sl - d * sl_widen * abs(s.entry - s.sl)
        risk = abs(e - sl)
        t1 = e + d * t1_r * risk if t1_r is not None else s.tp1
        t2 = e + d * t2_r * risk if t2_r is not None else s.tp2
        adj = spread if d < 0 else 0.0

        def reached(j, px):
            return (lo[j] + adj <= px) if d < 0 else (h[j] >= px)

        status, fill_i, r = "expired", -1, 0.0
        filled, tp1_done, cur_sl, fill_price = False, False, sl, e
        j, end = s.t + 1, min(n, s.t + 1 + max_hold)
        while j < end:
            if not filled:
                if j - s.t > expiry_bars:
                    break
                if (h[j] >= e) if d < 0 else (lo[j] + spread <= e):
                    filled, fill_i = True, j
                    fill_price = max(e, o[j]) if d < 0 else min(e, o[j] + spread)
                elif reached(j, t1):
                    status = "missed"
                    break
                else:
                    j += 1
                    continue
            rem = (1 - partial) if tp1_done else 1.0
            if (h[j] + adj >= cur_sl) if d < 0 else (lo[j] <= cur_sl):
                px = cur_sl if j == fill_i else (max(cur_sl, o[j] + adj) if d < 0 else min(cur_sl, o[j]))
                r += rem * (px - fill_price) * d / risk
                status = "be" if tp1_done else "sl"
                break
            if j == fill_i:
                j += 1  # konservatif: di bar pengisian hanya SL yang boleh kena
                continue
            if not tp1_done and reached(j, t1):
                r += partial * (t1 - fill_price) * d / risk
                if partial >= 1.0:
                    status = "tp1"
                    break
                tp1_done = True
                if reached(j, t2):
                    r += (1 - partial) * (t2 - fill_price) * d / risk
                    status = "tp2"
                    break
                if be:
                    cur_sl = fill_price + d * be_offset
                j += 1
                continue
            if tp1_done and reached(j, t2):
                r += rem * (t2 - fill_price) * d / risk
                status = "tp2"
                break
            j += 1
        else:
            if filled:
                rem = (1 - partial) if tp1_done else 1.0
                r += rem * (c[end - 1] + adj - fill_price) * d / risk
                status = "timeout"
        out.append((status, fill_i, r if filled else np.nan))
    res = setups.copy()
    res[["status", "fill_i", "R"]] = pd.DataFrame(out, index=res.index)
    return res
