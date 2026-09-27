"""Alat uji bersama untuk riset strategi dari repo GitHub populer.

- `periods()`  : 4 periode data asli yang tidak saling tumpang-tindih.
- `simulate()` : satu posisi pada candle resolusi dasar (M5/M15), harga bar = BID, ASK = BID + spread.
  Konservatif: SL dicek lebih dulu; di bar pengisian TP tidak dihitung; gap melewati SL diisi di open.
- `stats()`    : ringkasan dalam satuan R (kelipatan risiko awal).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import resample
from .run_scan import dataset

NY = "America/New_York"
CUTS = [pd.Timestamp(x, tz="UTC") for x in ("2018-01-01", "2022-04-01", "2025-04-07")]


@dataclass
class Period:
    name: str
    base: pd.DataFrame   # resolusi dasar (M15 untuk 2012-22, M5 untuk 2022-26)
    tf: str              # "M15" / "M5"
    spread: float


def periods() -> list[Period]:
    m15 = dataset("m15_2012")[0]
    m20 = dataset("m5_2020")[0]
    m25 = dataset("m5_2025")[0]
    a, b, c = CUTS
    return [
        Period("2012-17", m15[m15.index < a], "M15", 0.30),
        Period("2018-22", m15[(m15.index >= a) & (m15.index < b)], "M15", 0.30),
        Period("2022-25", m20[(m20.index >= b) & (m20.index < c)], "M5", 0.25),
        Period("2025-26", m25[m25.index >= c], "M5", 0.25),
    ]


def server_time(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Jam server MT5 umum (New York + 7 jam): hari trading mulai 00:00, ikut DST AS."""
    return index.tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)


def to_base(base: pd.DataFrame, times: pd.DatetimeIndex) -> np.ndarray:
    """Index bar dasar pertama yang dibuka pada/ setelah `times`."""
    return base.index.searchsorted(times, side="left")


def last_base_of(base: pd.DataFrame, htf: pd.DataFrame) -> np.ndarray:
    """Untuk tiap bar timeframe besar k: index bar dasar terakhir di dalamnya."""
    starts = to_base(base, htf.index)
    ends = np.r_[starts[1:], len(base)] - 1
    return ends


class Arrays:
    def __init__(self, df: pd.DataFrame):
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.n = len(df)


def simulate(a: Arrays, sp: float, j0: int, d: int, entry: float, sl: float, tp: float | None,
             max_hold: int, exit_mask: np.ndarray | None = None, trail=None, be_at: float | None = None,
             fill_mid_bar: bool = False, tp_first: bool = False) -> tuple[int, float]:
    """Posisi terisi di bar j0 pada harga `entry` (sudah termasuk spread untuk BUY).

    exit_mask[j] True -> keluar di open bar j+1 (sinyal keluar pada close bar j).
    trail(j, d, entry, sl) -> SL baru (berlaku mulai bar berikutnya).
    be_at: pindah SL ke entry setelah profit >= be_at x risiko (berlaku bar berikutnya).
    tp_first: batas atas OPTIMISTIS - TP diperiksa sebelum SL di setiap bar (termasuk bar pengisian).
    Return (index_bar_keluar, R).
    """
    risk = abs(entry - sl)
    if risk <= 0:
        return j0, 0.0
    adj = sp if d < 0 else 0.0
    o, h, l, c = a.o, a.h, a.l, a.c
    cur = sl
    end = min(a.n - 2, j0 + max_hold)
    for j in range(j0, end + 1):
        if tp_first and tp is not None and ((h[j] >= tp) if d > 0 else (l[j] + adj <= tp)):
            return j, (tp - entry) * d / risk
        if (l[j] <= cur) if d > 0 else (h[j] + adj >= cur):
            if j == j0 and fill_mid_bar:
                px = cur
            else:
                px = min(cur, o[j]) if d > 0 else max(cur, o[j] + adj)
            return j, (px - entry) * d / risk
        if j > j0 and tp is not None and ((h[j] >= tp) if d > 0 else (l[j] + adj <= tp)):
            return j, (tp - entry) * d / risk
        if exit_mask is not None and exit_mask[j]:
            return j + 1, (o[j + 1] + adj - entry) * d / risk
        if j > j0:
            if trail is not None:
                cur = trail(j, d, entry, cur)
            if be_at is not None:
                best = (h[j] - entry) if d > 0 else (entry - l[j] - adj)
                if best >= be_at * risk:
                    cur = max(cur, entry) if d > 0 else min(cur, entry)
    return end, (c[end] + adj - entry) * d / risk


def trades_frame(rows: list, base: pd.DataFrame) -> pd.DataFrame:
    """rows: (j_entry, j_exit, dir, R) -> DataFrame berwaktu."""
    t = pd.DataFrame(rows, columns=["j0", "j1", "dir", "R"])
    if t.empty:
        return t.assign(time=pd.Series(dtype="datetime64[ns, UTC]"), exit=pd.Series(dtype="datetime64[ns, UTC]"))
    t["time"] = base.index[t.j0.to_numpy()]
    t["exit"] = base.index[np.minimum(t.j1.to_numpy(), len(base) - 1)]
    return t


def stats(r) -> dict:
    r = np.asarray(r, float)
    if len(r) == 0:
        return {"n": 0, "win": 0.0, "avg": 0.0, "sum": 0.0, "pf": 0.0, "dd": 0.0}
    wins, losses = r[r > 0], r[r < 0]
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
    return {"n": len(r), "win": 100 * len(wins) / len(r), "avg": r.mean(), "sum": r.sum(), "pf": pf, "dd": dd}


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=  0 (tidak ada trade)"
    return (f"n={s['n']:4d} win={s['win']:4.1f}% rata={s['avg']:+.3f}R total={s['sum']:+7.1f}R "
            f"PF={s['pf']:.2f} DD={s['dd']:+.1f}R")


def h1(p: Period) -> pd.DataFrame:
    return resample(p.base, "60min")
