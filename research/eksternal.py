"""Kerangka uji DATA EKSTERNAL sebagai filter sinyal 💰 cloud (dipakai research/eksternal_*.py).

Sinyal = mesin cloud yang sama dengan badge (research/badge_stats.categorized): F-ensemble 3 set Donchian H1,
lewati 3 candle setelah buka pekan (XAU), kategori konf+⭐ / konf / ⭐ / biasa di close candle sinyal.
Sinyal 💰 yang dikirim: XAU konf+⭐ & konf; BTC konf+⭐, konf & ⭐ (cloud/api/_core.py STATS & badges).

Waktu keputusan = open candle entry (`t`, = close candle sinyal). Setiap fitur eksternal HARUS sudah terbit
sebelum `t` (lihat `asof()`: nilai dipakai mulai waktu terbitnya, bukan tanggal datanya).

Penilaian (ditetapkan SEBELUM melihat hasil):
- subset: mesin tidak berubah; filter hanya memutuskan sinyal 💰 dikirim/tidak -> kelompok 'lolos' vs 'dibuang'.
- latih/uji: XAU latih 2012-11..2018, uji 2019..2026-09; BTC latih 2016..2020, uji 2021..2026-09
  (sama dengan research/strategy_lab.py). Varian filter dipilih HANYA dari latih.
- p-acak: peluang filter acak yang membuang jumlah sinyal yang sama menghasilkan rata-rata 'lolos' >= hasil filter
  (5.000 undian, satu sisi). Banyak varian diuji -> p < 0,05 saja belum cukup.
- KONSISTEN bila: (a) rata-rata sinyal dibuang <= 0 di latih DAN uji (filter tidak membuang profit), (b) rata-rata
  'lolos' > dasar di latih DAN uji, (c) >= 60% tahun (yang punya sinyal dibuang) rata-rata dibuang < rata-rata lolos,
  (d) p-acak seluruh periode < 0,05. Hanya filter yang lolos (a)-(d) diusulkan ke cloud (perubahan live tetap
  menunggu izin pengguna).
- nyata: filter dipasang di allow() seperti cloud (sinyal ditolak -> set tetap kosong, candle berikutnya boleh masuk
  lagi bila breakout berlanjut); dilaporkan untuk filter yang konsisten.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .filters import features
from .gap_study import week_info
from .run_scan import DATA
from .strategy_lab import Bars, markets
from .strategy_lab2 import STAR, backtest_f, signals, trend_states

warnings.filterwarnings("ignore")

EXT = DATA / "eksternal"            # cache unduhan data eksternal (di-gitignore bersama data/)
SPLIT = {"XAUUSD": pd.Timestamp("2019-01-01", tz="UTC"), "BTCUSD": pd.Timestamp("2021-01-01", tz="UTC")}
MONEY = {"XAUUSD": ("konf+⭐", "konf"), "BTCUSD": ("konf+⭐", "konf", "⭐")}


@dataclass
class Asset:
    name: str
    b: Bars
    sig: pd.DataFrame      # semua sinyal: t (keputusan/entry), t_out, dir, cat, R, set, i (candle sinyal)
    split: pd.Timestamp

    @property
    def money(self) -> pd.DataFrame:
        return self.sig[self.sig.cat.isin(MONEY[self.name])].reset_index(drop=True)


def _categorized(b: Bars, skip_open: bool) -> pd.DataFrame:
    f = features(b.df)
    since = week_info(b.df)[0]
    s = trend_states(b)
    out = []
    for k, (li, si, lo, so) in enumerate(signals(b, "donchian")):
        allow = (lambda i, d: since[i] >= 3) if skip_open else None
        for t_in, t_out, r, d in backtest_f(b, li, si, lo, so, 3.0, 5, 1.0, allow):
            i = b.t.get_loc(t_in) - 1
            star = bool(STAR(f, i, d))
            konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
            cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
            out.append((t_in, t_out, d, cat, r, k, i))
    df = pd.DataFrame(out, columns=["t", "t_out", "dir", "cat", "R", "set", "i"])
    return df.sort_values("t").reset_index(drop=True)


@lru_cache(maxsize=None)
def asset(name: str) -> Asset:
    m = next(m for m in markets() if m.name == name)
    b = Bars(m.h1, m.spread)
    return Asset(name, b, _categorized(b, name == "XAUUSD"), SPLIT[name])


def asof(times: pd.DatetimeIndex, values: pd.Series, available: pd.DatetimeIndex) -> np.ndarray:
    """Nilai terakhir yang SUDAH TERBIT pada `times` (available[k] = waktu terbit values[k]). NaN bila belum ada."""
    available, times = pd.DatetimeIndex(available).as_unit("ns"), pd.DatetimeIndex(times).as_unit("ns")
    order = np.argsort(available.asi8)
    av = available.asi8[order]
    vals = np.asarray(values, float)[order]
    k = np.searchsorted(av, times.asi8, side="right") - 1
    out = np.full(len(times), np.nan)
    ok = k >= 0
    out[ok] = vals[k[ok]]
    return out


def _mean(r) -> float:
    return float(np.mean(r)) if len(r) else float("nan")


def perm_p(r: np.ndarray, keep: np.ndarray, n: int = 5000, seed: int = 7) -> float:
    """P(rata-rata subset acak berukuran sama >= rata-rata subset filter)."""
    k = int(keep.sum())
    if k == 0 or k == len(r):
        return float("nan")
    rng = np.random.default_rng(seed)
    obs = r[keep].mean()
    idx = np.argsort(rng.random((n, len(r))), axis=1)[:, :k]
    sims = r[idx].mean(axis=1)
    return float((sims >= obs - 1e-12).mean())


def judge(sig: pd.DataFrame, keep: np.ndarray, split: pd.Timestamp) -> dict:
    """Nilai filter (keep = True -> sinyal dikirim) pada daftar sinyal `sig` (kolom t, R)."""
    keep = np.asarray(keep, bool)
    r = sig.R.to_numpy(float)
    tr = (sig.t < split).to_numpy()
    out = {"n": len(r), "n_keep": int(keep.sum()), "base": _mean(r), "keep": _mean(r[keep]), "drop": _mean(r[~keep]),
           "tot_base": r.sum(), "tot_keep": r[keep].sum(), "wr_base": 100 * (r > 0).mean() if len(r) else 0.0,
           "wr_keep": 100 * (r[keep] > 0).mean() if keep.any() else 0.0}
    for tag, m in (("latih", tr), ("uji", ~tr)):
        out[f"{tag}_base"], out[f"{tag}_keep"] = _mean(r[m]), _mean(r[m & keep])
        out[f"{tag}_drop"], out[f"{tag}_ndrop"] = _mean(r[m & ~keep]), int((m & ~keep).sum())
    y = sig.t.dt.year.to_numpy()
    good = tot = 0
    for yy in np.unique(y):
        m = y == yy
        if (m & ~keep).any() and (m & keep).any():
            tot += 1
            good += r[m & ~keep].mean() < r[m & keep].mean()
    out["tahun_ok"], out["tahun_n"] = good, tot
    out["p"] = perm_p(r, keep)
    out["konsisten"] = bool(
        out["latih_drop"] <= 0 and out["uji_drop"] <= 0 and out["latih_keep"] > out["latih_base"]
        and out["uji_keep"] > out["uji_base"] and tot and good / tot >= 0.6 and out["p"] < 0.05)
    return out


def fmt_judge(name: str, j: dict) -> str:
    def f(x):
        return "  -  " if x != x else f"{x:+.2f}"
    return (f"{name:44s} kirim {j['n_keep']:4d}/{j['n']:4d} | rata lolos {f(j['keep'])} dibuang {f(j['drop'])} "
            f"(dasar {f(j['base'])}) | latih {f(j['latih_keep'])}/{f(j['latih_drop'])} [{f(j['latih_base'])}] uji "
            f"{f(j['uji_keep'])}/{f(j['uji_drop'])} [{f(j['uji_base'])}] | total {j['tot_keep']:+6.0f}R (dasar {j['tot_base']:+.0f}) | tahun "
            f"{j['tahun_ok']}/{j['tahun_n']} | p={j['p']:.3f}{'  ✅ KONSISTEN' if j['konsisten'] else ''}")


def per_year(sig: pd.DataFrame, keep: np.ndarray) -> str:
    keep = np.asarray(keep, bool)
    rows = []
    for y, g in sig.assign(k=keep).groupby(sig.t.dt.year):
        k, d = g.R[g.k], g.R[~g.k]
        rows.append(f"{y % 100:02d}:{k.mean() if len(k) else float('nan'):+.2f}/"
                    f"{d.mean() if len(d) else float('nan'):+.2f}({len(d)})")
    return " ".join(rows)


def realistic(a: Asset, filt, only_money: bool = True) -> list:
    """Filter dipasang di allow() seperti cloud. filt(t_keputusan, dir) -> bool. Return list (t, t_out, R, dir).
    only_money=False: semua kategori (seperti bot yang men-trade semua sinyal)."""
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    money = MONEY[a.name]

    def allow(i, d):
        if a.name == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        cat = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return (cat in money or not only_money) and (filt is None or filt(b.t[i + 1], d))

    tr = []
    for li, si, lo, so in signals(b, "donchian"):
        tr += backtest_f(b, li, si, lo, so, 3.0, 5, 1.0, allow)
    return sorted(tr)


def bar_filter(a: Asset, keep_fn):
    """keep_fn(DataFrame t, dir) -> array keep, dihitung sekali untuk semua candle & kedua arah -> filt(t, d)."""
    t = pd.Series(a.b.t[1:].append(a.b.t[-1:] + pd.Timedelta(hours=1)))
    grid = pd.DataFrame({"t": pd.concat([t, t], ignore_index=True), "dir": np.r_[np.ones(len(t)), -np.ones(len(t))]})
    keep = np.asarray(keep_fn(grid), bool)
    look = dict(zip(zip(grid.t, grid.dir.astype(int)), keep))
    return lambda tt, d: look.get((tt, int(d)), True)


def realistic_summary(a: Asset, filt, only_money: bool = True) -> str:
    base = realistic(a, None, only_money)
    new = realistic(a, filt, only_money)
    out = []
    for tag, tr in (("tanpa filter", base), ("dengan filter", new)):
        r = pd.Series([x[2] for x in tr], index=pd.DatetimeIndex([x[0] for x in tr]))
        lt, ut = r[r.index < a.split], r[r.index >= a.split]
        out.append(f"{tag}: n={len(r)} WR={100 * (r > 0).mean():.1f}% rata={r.mean():+.3f}R total={r.sum():+.1f}R | "
                   f"latih {lt.mean():+.3f}R ({len(lt)}) uji {ut.mean():+.3f}R ({len(ut)})")
    return "\n".join(out)


def cache_path(name: str) -> Path:
    EXT.mkdir(parents=True, exist_ok=True)
    return EXT / name
