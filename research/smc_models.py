"""Perbandingan menyeluruh metode SMC/ICT populer + kombinasinya dengan trend.

python -m research.smc_models [--m5] [--csv out.csv]

Setiap model memakai aturan "buku teks" dengan parameter TETAP (pra-daftar, tidak dioptimasi) lalu
diuji di 3 periode: 2012-17 (pengembangan), 2018-22 dan 2025-26 (out-of-sample, OOS).
Aturan simulasi (konservatif, sama untuk semua model):
- sinyal hanya dari candle yang SUDAH tertutup; market order di open candle berikutnya;
  limit order terisi bila harga menyentuh entry, batal bila TP tersentuh dulu / kedaluwarsa;
- harga candle = BID, ASK = BID + spread (BUY bayar spread saat masuk, SELL saat keluar);
- SL dicek lebih dulu; di candle pengisian hanya SL yang boleh kena;
- satu posisi per model (sinyal saat posisi/order masih aktif dilewati).
Hasil dalam R (kelipatan risiko awal). LOLOS = rata-rata R > 0 di KETIGA periode dengan >= 30 trade.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from xau_bot.smc import atr, swing_mask

from .data import resample
from .run_scan import DATA, dataset
from .scalp import trend_state

NY = "America/New_York"
BIG = 10 ** 9


@dataclass
class Sig:
    i: int                        # candle sinyal (diketahui saat candle i tertutup)
    d: int                        # +1 BUY, -1 SELL
    sl: float | None = None       # harga SL absolut ...
    sl_dist: float = 0.0          # ... atau jarak SL dari harga isi
    entry: float | None = None    # None = market di open candle berikutnya, angka = limit
    tp: float | None = None       # harga TP absolut; None = tp_r x risiko
    tp_r: float | None = 2.0      # None & tp None = tanpa TP (keluar lewat exit_fn / waktu)
    expiry: int = 12              # candle maksimum menunggu limit terisi
    hold: int = BIG               # keluar paksa setelah N candle sejak isi


class Frame:
    """Array OHLC + waktu New York untuk satu timeframe."""

    def __init__(self, df: pd.DataFrame, tf_min: int):
        self.df, self.tf, self.n = df, tf_min, len(df)
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.a = atr(df, 14)
        self.a20 = atr(df, 20)
        ny = df.index.tz_convert(NY)
        self.mins = (ny.hour * 60 + ny.minute).to_numpy()
        self.day = pd.factorize((ny + pd.Timedelta(hours=7)).normalize())[0]  # hari trading (17:00 NY)

    def map_htf(self, values: np.ndarray, htf: pd.DataFrame, htf_min: int) -> np.ndarray:
        """Nilai per candle HTF (diketahui saat candle HTF tertutup) -> per candle frame ini."""
        s = pd.Series(values, index=htf.index + pd.Timedelta(minutes=htf_min))
        close_t = self.df.index + pd.Timedelta(minutes=self.tf)
        return s.reindex(close_t, method="ffill").fillna(0).to_numpy()


# ------------------------------------------------------------------ simulator
def run(fr: Frame, sigs: list[Sig], spread: float, exit_fn: Callable[[int, int], bool] | None = None,
        be_r: float | None = None, be_offset: float = 0.10, f_legs: int = 0, tp1_r: float = 1.0):
    """f_legs >= 2 = skema F bot: posisi #1 TP1 (tp1_r R), sisanya runner; TP1 kena -> SL+ (entry + be_offset).
    Hasil = R rata-rata per posisi (risiko awal total tetap 1R)."""
    o, h, l, c, n = fr.o, fr.h, fr.l, fr.c, fr.n
    if f_legs >= 2:
        be_r = tp1_r
    out, busy = [], -1
    for s in sorted(sigs, key=lambda x: x.i):
        if s.i <= busy or s.i + 1 >= n:
            continue
        d = s.d
        adj = spread if d < 0 else 0.0      # SELL keluar di ASK
        fill, j = None, s.i + 1
        if s.entry is None:
            fill = o[j] + (spread if d > 0 else 0.0)
        else:
            sl0 = s.sl if s.sl is not None else s.entry - d * s.sl_dist
            risk0 = (s.entry - sl0) * d
            tp0 = s.tp if s.tp is not None else (s.entry + d * s.tp_r * risk0 if s.tp_r else None)
            for j in range(s.i + 1, min(n, s.i + 1 + s.expiry)):
                if (l[j] + spread <= s.entry) if d > 0 else (h[j] >= s.entry):
                    fill = min(s.entry, o[j] + spread) if d > 0 else max(s.entry, o[j])
                    break
                if tp0 is not None and ((h[j] >= tp0) if d > 0 else (l[j] + adj <= tp0)):
                    break  # target tercapai sebelum entry -> setup terlewat
            if fill is None:
                busy = j
                continue
        sl = s.sl if s.sl is not None else fill - d * s.sl_dist
        risk = (fill - sl) * d
        if risk <= 0:
            busy = j
            continue
        tp = s.tp if s.tp is not None else (fill + d * s.tp_r * risk if s.tp_r else None)
        if tp is not None and (tp - fill) * d <= 0:
            busy = j
            continue
        fill_i, r, be_done = j, None, False
        end = min(n - 1, fill_i + s.hold)
        k = fill_i
        while k <= end:
            if (l[k] <= sl) if d > 0 else (h[k] + spread >= sl):
                px = sl if k == fill_i else (min(sl, o[k]) if d > 0 else max(sl, o[k] + spread))
                r = (px - fill) * d / risk
                break
            if k > fill_i:
                if tp is not None and ((h[k] >= tp) if d > 0 else (l[k] + adj <= tp)):
                    r = (tp - fill) * d / risk
                    break
                if be_r and not be_done and ((h[k] >= fill + be_r * risk) if d > 0
                                             else (l[k] + adj <= fill - be_r * risk)):
                    be_done, sl = True, fill + d * be_offset
                if exit_fn is not None and k + 1 < n and exit_fn(k, d):
                    r = (o[k + 1] + adj - fill) * d / risk
                    break
            k += 1
        if r is None:
            k = min(k, end)
            r = (c[k] + adj - fill) * d / risk
        if f_legs >= 2 and be_done:
            r = (tp1_r + (f_legs - 1) * r) / f_legs
        out.append((fr.df.index[min(k, n - 1)], r))
        busy = k
    # R per trade + waktu keluar (untuk urutan kronologis equity/drawdown)
    return np.array([x[1] for x in out]), pd.DatetimeIndex([x[0] for x in out])


def stats(r: np.ndarray) -> dict:
    if len(r) == 0:
        return {"n": 0, "win": 0.0, "avg": 0.0, "pf": 0.0, "sum": 0.0, "dd": 0.0}
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    loss = -r[r < 0].sum()
    return {"n": len(r), "win": (r > 0).mean() * 100, "avg": r.mean(),
            "pf": r[r > 0].sum() / loss if loss else float("inf"), "sum": r.sum(), "dd": dd}


# ------------------------------------------------------------- primitif SMC
def structure(fr: Frame, length: int = 3):
    """BOS per candle (tanpa look-ahead). Return (events, state) — event = (i, dir, swing_idx, leg_idx)."""
    h, l, c = fr.h, fr.l, fr.c
    hm, lm = swing_mask(h, length, "high"), swing_mask(l, length, "low")
    last_h = last_l = None
    state, s = np.zeros(fr.n), 0
    events = []
    for i in range(fr.n):
        k = i - length
        if k >= 0:
            if hm[k]:
                last_h = k
            if lm[k]:
                last_l = k
        if last_h is not None and c[i] > h[last_h]:
            events.append((i, 1, last_h, last_h + int(np.argmin(l[last_h:i + 1]))))
            s, last_h = 1, None
        elif last_l is not None and c[i] < l[last_l]:
            events.append((i, -1, last_l, last_l + int(np.argmax(h[last_l:i + 1]))))
            s, last_l = -1, None
        state[i] = s
    return events, state


def bars_until(fr: Frame, i: int, end_min: int) -> int:
    return max(1, (end_min - int(fr.mins[i])) // fr.tf)


def sweep_reclaim(fr: Frame, hi_lvl: np.ndarray, lo_lvl: np.ndarray, win: tuple[int, int], end_min: int,
                  mss: bool = False, tp_level: bool = False) -> list[Sig]:
    """Sweep level (ekor menembus) lalu close kembali di dalam, di jendela jam NY `win`.
    Satu sinyal per hari. mss=True: tunggu close menembus swing internal berlawanan (<= 8 candle)."""
    h, l, c, a, mins, day = fr.h, fr.l, fr.c, fr.a, fr.mins, fr.day
    lo_sw = swing_mask(l, 1, "low")
    hi_sw = swing_mask(h, 1, "high")
    sigs, used = [], set()
    ext_hi = ext_lo = None
    cur_day = -1
    for i in range(2, fr.n):
        if day[i] != cur_day:
            cur_day, ext_hi, ext_lo = day[i], None, None
        if day[i] in used or not (win[0] <= mins[i] < win[1]) or np.isnan(hi_lvl[i]) or np.isnan(lo_lvl[i]):
            continue
        ext_hi = h[i] if ext_hi is None else max(ext_hi, h[i])
        ext_lo = l[i] if ext_lo is None else min(ext_lo, l[i])
        for d, swept, back in ((-1, ext_hi > hi_lvl[i], c[i] < hi_lvl[i]),
                               (1, ext_lo < lo_lvl[i], c[i] > lo_lvl[i])):
            if not (swept and back and lo_lvl[i] < c[i] < hi_lvl[i]):
                continue
            k = i
            if mss:  # konfirmasi: close menembus swing internal terakhir sebelum sweep
                ref_mask = lo_sw if d < 0 else hi_sw
                refs = np.nonzero(ref_mask[max(0, i - 30):i - 1])[0]
                if not refs.size:
                    continue
                ref = (l if d < 0 else h)[max(0, i - 30) + refs[-1]]
                k = None
                ext = ext_hi if d < 0 else ext_lo
                for m in range(i, min(fr.n, i + 9)):
                    if day[m] != day[i] or mins[m] >= end_min:
                        break
                    ext = max(ext, h[m]) if d < 0 else min(ext, l[m])
                    if (c[m] < ref) if d < 0 else (c[m] > ref):
                        k = m
                        break
                if k is None:
                    continue
                sl = ext + a[k] * 0.1 if d < 0 else ext - a[k] * 0.1
            else:
                sl = ext_hi + a[i] * 0.1 if d < 0 else ext_lo - a[i] * 0.1
            tp = (lo_lvl[i] if d < 0 else hi_lvl[i]) if tp_level else None
            if tp is not None and (tp - c[k]) * d <= 0:
                continue
            sigs.append(Sig(k, d, sl=sl, tp=tp, tp_r=None if tp_level else 2.0, hold=bars_until(fr, k, end_min)))
            used.add(day[i])
            break
    return sigs


# ------------------------------------------------------------------- model
def m_turtle_soup(fr: Frame, n: int = 20, hold: int = 32) -> list[Sig]:
    """Turtle Soup (Raschke): low baru 20 candle, low lama >= 4 candle lalu, close kembali di atasnya."""
    ls, hs = pd.Series(fr.l), pd.Series(fr.h)
    old_lo = ls.rolling(n - 3).min().shift(4).to_numpy()
    rec_lo = ls.rolling(3).min().shift(1).to_numpy()
    old_hi = hs.rolling(n - 3).max().shift(4).to_numpy()
    rec_hi = hs.rolling(3).max().shift(1).to_numpy()
    sigs = []
    for i in range(n + 4, fr.n):
        if rec_lo[i] > old_lo[i] and fr.l[i] < old_lo[i] and fr.c[i] > old_lo[i]:
            sigs.append(Sig(i, 1, sl=fr.l[i] - 0.1 * fr.a[i], hold=hold))
        elif rec_hi[i] < old_hi[i] and fr.h[i] > old_hi[i] and fr.c[i] < old_hi[i]:
            sigs.append(Sig(i, -1, sl=fr.h[i] + 0.1 * fr.a[i], hold=hold))
    return sigs


def asia_levels(fr: Frame) -> tuple[np.ndarray, np.ndarray]:
    """High/low range Asia 20:00-00:00 NY hari trading yang sama (NaN sebelum range selesai)."""
    asia = fr.mins >= 20 * 60
    df = pd.DataFrame({"d": fr.day, "h": np.where(asia, fr.h, np.nan), "l": np.where(asia, fr.l, np.nan)})
    g = df.groupby("d")
    ah, al = g["h"].transform("max").to_numpy(), g["l"].transform("min").to_numpy()
    ready = fr.mins < 17 * 60  # setelah tengah malam (range Asia sudah selesai)
    return np.where(ready, ah, np.nan), np.where(ready, al, np.nan)


def prev_day_levels(fr: Frame) -> tuple[np.ndarray, np.ndarray]:
    df = pd.DataFrame({"d": fr.day, "h": fr.h, "l": fr.l})
    daily = df.groupby("d").agg(h=("h", "max"), l=("l", "min"))
    return daily["h"].shift(1).reindex(fr.day).to_numpy(), daily["l"].shift(1).reindex(fr.day).to_numpy()


def m_judas(fr: Frame, **kw) -> list[Sig]:
    """Judas swing / Power of 3: London (02-05 NY) menyapu range Asia lalu kembali -> arah berlawanan."""
    ah, al = asia_levels(fr)
    return sweep_reclaim(fr, ah, al, (120, 300), 12 * 60, **kw)


def m_pd_sweep(fr: Frame, **kw) -> list[Sig]:
    """Sweep high/low hari sebelumnya (PDH/PDL) di London-NY (02-12 NY) lalu kembali."""
    ph, pl = prev_day_levels(fr)
    return sweep_reclaim(fr, ph, pl, (120, 720), 16 * 60, **kw)


def m_silver_bullet(fr: Frame, windows=((600, 660),), raid=(10, 40)) -> list[Sig]:
    """ICT Silver Bullet: FVG terbentuk di jendela waktu setelah raid likuiditas; limit di CE, TP 2R."""
    h, l, a, mins, day = fr.h, fr.l, fr.a, fr.mins, fr.day
    sigs, used = [], set()
    for i in range(raid[1] + 2, fr.n):
        w = next((wd for wd in windows if wd[0] <= mins[i] < wd[1]), None)
        if w is None or (day[i], w) in used:
            continue
        if l[i] > h[i - 2]:
            recent, older = l[i - raid[0]:i + 1].min(), l[i - raid[1]:i - raid[0]].min()
            if recent < older:
                sigs.append(Sig(i, 1, entry=(l[i] + h[i - 2]) / 2, sl=recent - 0.1 * a[i],
                                expiry=max(1, (w[1] + 60 - mins[i]) // fr.tf), hold=bars_until(fr, i, 16 * 60)))
                used.add((day[i], w))
        elif h[i] < l[i - 2]:
            recent, older = h[i - raid[0]:i + 1].max(), h[i - raid[1]:i - raid[0]].max()
            if recent > older:
                sigs.append(Sig(i, -1, entry=(h[i] + l[i - 2]) / 2, sl=recent + 0.1 * a[i],
                                expiry=max(1, (w[1] + 60 - mins[i]) // fr.tf), hold=bars_until(fr, i, 16 * 60)))
                used.add((day[i], w))
    return sigs


def m_fvg(fr: Frame, disp: float = 1.0) -> list[Sig]:
    """FVG dengan displacement (body candle tengah >= 1 ATR): limit di CE, SL di luar candle 1, TP 2R."""
    o, h, l, c, a = fr.o, fr.h, fr.l, fr.c, fr.a
    sigs = []
    for i in range(2, fr.n):
        body = c[i - 1] - o[i - 1]
        if l[i] > h[i - 2] and body >= disp * a[i]:
            sigs.append(Sig(i, 1, entry=(l[i] + h[i - 2]) / 2, sl=l[i - 2] - 0.1 * a[i]))
        elif h[i] < l[i - 2] and -body >= disp * a[i]:
            sigs.append(Sig(i, -1, entry=(h[i] + l[i - 2]) / 2, sl=h[i - 2] + 0.1 * a[i]))
    return sigs


def m_bos_ob(fr: Frame, events) -> list[Sig]:
    """BOS lalu retest Order Block (candle berlawanan terakhir sebelum dorongan); limit di tepi OB."""
    o, h, l, c, a = fr.o, fr.h, fr.l, fr.c, fr.a
    sigs = []
    for i, d, _, leg in events:
        ob = next((j for j in range(leg, max(leg - 6, -1), -1) if (c[j] < o[j]) == (d > 0) and c[j] != o[j]), leg)
        if d > 0:
            entry, sl = h[ob], min(l[ob], l[leg]) - 0.1 * a[i]
            if entry < c[i]:
                sigs.append(Sig(i, 1, entry=entry, sl=sl, expiry=24))
        else:
            entry, sl = l[ob], max(h[ob], h[leg]) + 0.1 * a[i]
            if entry > c[i]:
                sigs.append(Sig(i, -1, entry=entry, sl=sl, expiry=24))
    return sigs


def m_ote(fr: Frame, events) -> list[Sig]:
    """OTE: setelah BOS dengan dorongan >= 2 ATR, limit di retracement 70,5%, SL di 100%, TP ekstensi -27%."""
    h, l, a = fr.h, fr.l, fr.a
    sigs = []
    for i, d, _, leg in events:
        if d > 0:
            hi, lo = h[leg:i + 1].max(), l[leg]
            rng = hi - lo
            if rng >= 2 * a[i]:
                sigs.append(Sig(i, 1, entry=hi - 0.705 * rng, sl=lo - 0.1 * a[i], tp=hi + 0.27 * rng, expiry=24))
        else:
            lo, hi = l[leg:i + 1].min(), h[leg]
            rng = hi - lo
            if rng >= 2 * a[i]:
                sigs.append(Sig(i, -1, entry=lo + 0.705 * rng, sl=hi + 0.1 * a[i], tp=lo - 0.27 * rng, expiry=24))
    return sigs


def m_cisd(fr: Frame, n: int = 20, wait: int = 6) -> list[Sig]:
    """Sweep high/low 20 candle lalu CISD: close menembus open rangkaian candle searah sebelum sweep."""
    o, h, l, c, a = fr.o, fr.h, fr.l, fr.c, fr.a
    hi_n = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    lo_n = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    sigs, i = [], n + 1
    while i < fr.n - 1:
        for d, swept in ((-1, h[i] > hi_n[i]), (1, l[i] < lo_n[i])):
            if not swept:
                continue
            p = i
            while p - 1 >= 0 and ((c[p - 1] > o[p - 1]) if d < 0 else (c[p - 1] < o[p - 1])) and i - p < 10:
                p -= 1
            level, ext = o[p], (h[i] if d < 0 else l[i])
            for k in range(i + 1, min(fr.n, i + 1 + wait)):
                if (h[k] > ext) if d < 0 else (l[k] < ext):
                    break  # ekstrem baru -> bukan reversal
                if (c[k] < level) if d < 0 else (c[k] > level):
                    sigs.append(Sig(k, d, sl=ext + d * -0.1 * a[k], hold=32))
                    break
            break
        i += 1
    return sigs


def m_breaker(fr: Frame, unicorn: bool = False, length: int = 2) -> list[Sig]:
    """Breaker block: H1 -> L1 -> H2 (> H1, sweep) -> close < L1 (MSS). OB bullish di L1 yang gagal
    menjadi zona SELL (limit di tepi bawah, SL di atas zona). Unicorn = breaker bertumpuk dengan FVG."""
    o, h, l, c, a = fr.o, fr.h, fr.l, fr.c, fr.a
    hm, lm = swing_mask(h, length, "high"), swing_mask(l, length, "low")
    sw: list[tuple[int, int]] = []  # (idx, +1 high / -1 low) urut terkonfirmasi
    sigs, used = [], set()
    for i in range(fr.n):
        k = i - length
        if k >= 0:
            if hm[k]:
                sw.append((k, 1))
            if lm[k]:
                sw.append((k, -1))
        for d in (-1, 1):  # d = arah trade; SELL butuh pola high-low-high
            top = 1 if d < 0 else -1
            seq = [s for s in sw[-8:]]
            last_top = next((s for s in reversed(seq) if s[1] == top), None)
            if last_top is None or last_top[0] in used:
                continue
            l1 = next((s for s in reversed(seq) if s[1] == -top and s[0] < last_top[0]), None)
            if l1 is None:
                continue
            h1 = next((s for s in reversed(seq) if s[1] == top and s[0] < l1[0]), None)
            if h1 is None:
                continue
            p_top = h[last_top[0]] if d < 0 else l[last_top[0]]
            p_h1 = h[h1[0]] if d < 0 else l[h1[0]]
            p_l1 = l[l1[0]] if d < 0 else h[l1[0]]
            swept = p_top > p_h1 if d < 0 else p_top < p_h1
            intact = (h[last_top[0]:i + 1].max() <= p_top) if d < 0 else (l[last_top[0]:i + 1].min() >= p_top)
            broke = c[i] < p_l1 if d < 0 else c[i] > p_l1
            if not (swept and intact and broke):
                continue
            used.add(last_top[0])
            b0 = l1[0]
            b = next((j for j in range(b0, max(b0 - 6, -1), -1) if (c[j] < o[j]) == (d < 0) and c[j] != o[j]), b0)
            z_lo, z_hi = l[b], h[b]
            if unicorn:
                gaps = [(h[j], l[j - 2]) if d < 0 else (h[j - 2], l[j])
                        for j in range(last_top[0] + 2, i + 1)
                        if (h[j] < l[j - 2] if d < 0 else l[j] > h[j - 2])]
                over = [(max(g0, z_lo), min(g1, z_hi)) for g0, g1 in gaps if min(g1, z_hi) > max(g0, z_lo)]
                if not over:
                    continue
                z_lo, z_hi = over[-1]
            if d < 0 and z_lo > c[i]:
                sigs.append(Sig(i, -1, entry=z_lo, sl=h[b] + 0.1 * a[i], expiry=24))
            elif d > 0 and z_hi < c[i]:
                sigs.append(Sig(i, 1, entry=z_hi, sl=l[b] - 0.1 * a[i], expiry=24))
    return sigs


def m_structure_follow(fr: Frame, events) -> tuple[list[Sig], Callable]:
    """Ikut struktur (BOS) seperti trend: market saat BOS, SL di swing berlawanan, keluar saat CHoCH."""
    h, l, a = fr.h, fr.l, fr.a
    _, state = structure(fr, 3)
    sigs = []
    for i, d, _, leg in events:
        sl = (l[leg] - 0.1 * a[i]) if d > 0 else (h[leg] + 0.1 * a[i])
        sigs.append(Sig(i, d, sl=sl, tp_r=None))
    return sigs, (lambda k, d: state[k] == -d)


# ----------------------------------------------------------------- trend
def donchian_sigs(fr: Frame, ne: int = 55, nx: int = 20, stop_atr: float = 3.0,
                  keep: Callable[[int, int], bool] | None = None, pullback: bool = False):
    h, l, c, o = fr.h, fr.l, fr.c, fr.o
    hi_e = pd.Series(h).rolling(ne).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(ne).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(nx).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(nx).min().shift(1).to_numpy()
    sigs = []
    for i in range(ne + 1, fr.n):
        d = 1 if c[i] > hi_e[i] else (-1 if c[i] < lo_e[i] else 0)
        if d == 0 or (keep is not None and not keep(i, d)):
            continue
        if pullback:  # entry SMC: limit di 50% body candle breakout, SL tetap dari close sinyal
            sigs.append(Sig(i, d, entry=(o[i] + c[i]) / 2, sl=c[i] - d * stop_atr * fr.a20[i], tp_r=None, expiry=6))
        else:
            sigs.append(Sig(i, d, sl_dist=stop_atr * fr.a20[i], tp_r=None))
    return sigs, (lambda k, d: (c[k] < lo_x[k]) if d > 0 else (c[k] > hi_x[k]))


# ------------------------------------------------------------------ main
def periods(tf: str) -> dict[str, tuple[pd.DataFrame, float]]:
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    if tf == "M5":
        return {"2025-26": (m5, 0.25)}
    rule = {"M15": "15min", "H1": "60min"}[tf]
    return {"2012-17": (resample(m15[m15.index < cut], rule), 0.30),
            "2018-22": (resample(m15[m15.index >= cut], rule), 0.30),
            "2025-26": (resample(m5, rule), 0.25)}


def bot_smc_signals(period: str, fr: Frame, tp2: bool) -> list[Sig]:
    """Setup SmcStrategy bot (hasil research.run_scan) -> sinyal limit, skor >= 7."""
    name = {"2012-17": "scan_m15.pkl", "2018-22": "scan_m15.pkl", "2025-26": "scan_m5.pkl"}[period]
    try:
        sc = pd.read_pickle(DATA / name)
    except OSError:
        return []
    sc = sc[sc.score >= 7]
    idx = fr.df.index
    out = []
    for r in sc.itertuples(index=False):
        # waktu candle sinyal -> index frame ini (M5 dipetakan ke candle M15 yang memuatnya)
        pos = idx.searchsorted(r.time, side="right") - 1
        if pos < 0 or pos >= len(idx) or r.time - idx[pos] >= pd.Timedelta(minutes=fr.tf):
            continue
        out.append(Sig(int(pos), int(r.dir), entry=r.entry, sl=r.sl, tp=r.tp2 if tp2 else None,
                       tp_r=None if tp2 else 2.0, expiry=8))
    return out


def build_models(tf: str, fr: Frame, period: str, htf_bias: np.ndarray, trend: np.ndarray):
    """Daftar model: nama -> (sinyal, exit_fn). Filter: '' | '+bias H1' | '+trend H1'."""
    events, _ = structure(fr, 3)
    kz = [(120, 300), (420, 660)]
    models: dict[str, tuple[list[Sig], Callable | None]] = {}
    if tf in ("M15", "M5"):
        base = {
            "SMC bot (sweep-MSS-FVG/OB, TP likuiditas)": bot_smc_signals(period, fr, True),
            "SMC bot (sweep-MSS-FVG/OB, TP 2R)": bot_smc_signals(period, fr, False),
            "Turtle Soup 20": m_turtle_soup(fr),
            "Judas swing / PO3 (sweep Asia, TP 2R)": m_judas(fr),
            "Judas swing / PO3 (TP sisi lain range)": m_judas(fr, tp_level=True),
            "Judas swing + MSS": m_judas(fr, mss=True),
            "Sweep PDH/PDL": m_pd_sweep(fr),
            "Sweep PDH/PDL + MSS": m_pd_sweep(fr, mss=True),
            "Silver Bullet 10-11 NY": m_silver_bullet(fr),
            "Silver Bullet 3 jendela": m_silver_bullet(fr, ((180, 240), (600, 660), (840, 900))),
            "FVG displacement": m_fvg(fr),
            "BOS + Order Block": m_bos_ob(fr, events),
            "OTE 70.5% setelah BOS": m_ote(fr, events),
            "CISD setelah sweep": m_cisd(fr),
            "Breaker block": m_breaker(fr),
            "Unicorn (breaker + FVG)": m_breaker(fr, unicorn=True),
        }
        for name, sigs in base.items():
            models[name] = (sigs, None)
            if not name.startswith("SMC bot"):
                models[name + " +bias H1"] = ([s for s in sigs if htf_bias[s.i] == s.d], None)
            models[name + " +trend H1"] = ([s for s in sigs if trend[s.i] == s.d], None)
    else:  # H1
        models["Ikut struktur BOS/CHoCH H1"] = m_structure_follow(fr, events)
        models["Turtle Soup 20 H1"] = (m_turtle_soup(fr, hold=48), None)
        models["Donchian 55/20 (trend bot)"] = donchian_sigs(fr)
        models["Donchian + bias struktur H4"] = donchian_sigs(fr, keep=lambda i, d: htf_bias[i] == d)
        models["Donchian + killzone"] = donchian_sigs(
            fr, keep=lambda i, d: any(a <= fr.mins[i] + 60 <= b for a, b in kz))
        models["Donchian + displacement (body >= 1 ATR)"] = donchian_sigs(
            fr, keep=lambda i, d: (fr.c[i] - fr.o[i]) * d >= fr.a20[i])
        models["Donchian + entry pullback 50% (SMC)"] = donchian_sigs(fr, pullback=True)
    return models


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m5", action="store_true", help="juga uji model intraday di M5 2025-26")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    rows = []
    for tf in (["H1", "M15"] + (["M5"] if a.m5 else [])):
        tf_min = {"M5": 5, "M15": 15, "H1": 60}[tf]
        for period, (df, sp) in periods(tf).items():
            fr = Frame(df, tf_min)
            if tf == "H1":
                h4 = resample(df, "240min")
                bias = fr.map_htf(structure(Frame(h4, 240), 3)[1], h4, 240)
                trend = np.zeros(fr.n)
            else:
                h1 = resample(df, "60min")
                bias = fr.map_htf(structure(Frame(h1, 60), 3)[1], h1, 60)
                ts = trend_state(h1)  # index = waktu close H1
                trend = ts.reindex(df.index + pd.Timedelta(minutes=tf_min), method="ffill").fillna(0).to_numpy()
            for name, (sigs, exit_fn) in build_models(tf, fr, period, bias, trend).items():
                r, _ = run(fr, sigs, sp, exit_fn)
                rows.append({"tf": tf, "model": name, "period": period, **stats(r)})
            print(f"selesai {tf} {period}", flush=True)
    res = pd.DataFrame(rows)
    if a.csv:
        res.to_csv(a.csv, index=False)
    report(res)


def report(res: pd.DataFrame) -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    for (tf, model), g in res.groupby(["tf", "model"], sort=False):
        per = {r.period: r for r in g.itertuples()}
        positive = all(r.avg > 0 and r.n >= 30 for r in per.values())
        # M5 hanya punya 1 periode (2025-26) -> tidak cukup untuk dinyatakan lolos
        tag = ("LOLOS " if positive and len(per) == 3 else ("+1 per " if positive else "gagal "))
        cells = " | ".join(f"{p}: n={r.n:4d} win={r.win:4.1f}% {r.avg:+.3f}R PF={r.pf:4.2f} {r.sum:+7.1f}R"
                           for p, r in per.items())
        print(f"{tag} {tf:3s} {model:48s} {cells}")


if __name__ == "__main__":
    main()
