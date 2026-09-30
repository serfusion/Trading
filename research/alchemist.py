"""Unsur metode Trading Alchemist (Rizki Aditama) yang bisa menempel ke sistem kita (python -m research.alchemist).

research/momentum_candle.py menguji metode itu sebagai strategi sendiri (hasil: rugi setelah spread). Di sini unsur-
unsurnya diuji sebagai PERBAIKAN sinyal 💰 (research/eksternal.py: kriteria konsisten (a)-(d) ditetapkan sebelum
melihat hasil; latih XAU < 2019 / BTC < 2021):
- F1 candle sinyal H1 = momentum candle searah: badan >= k x ATR14 (candle sebelumnya), sumbu total <= 30% range
  (k = 1,0 / 1,5).
- F2 (XAU) candle M15 terakhir sebelum entry = momentum candle searah (badan >= 1 x ATR14 M15, sumbu <= 30%).
- F3 maksimal 2 sinyal 💰 per hari (jam server NY+7), sinyal ke-3 dst. dibuang.
- F4 validasi arah H4: close H4 terakhir yang sudah tutup di atas (BUY) / di bawah (SELL) EMA50 H4.
- Manajemen posisi (research/sl_tangga.py, uji nyata seperti cloud): SL+ setelah minor BOS (fraktal 2 & 3 candle H1)
  menggantikan / menambah SL+ setelah TP1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import resample
from .eksternal import SPLIT, asset, bar_filter, fmt_judge, judge, per_year, realistic_summary
from .github_popular import atr_w, ema
from .harness import server_time
from .sl_tangga import run as sl_run
from .sl_tangga import summary as sl_summary

WICK = 0.30


def mc_mask(df: pd.DataFrame, k: float) -> tuple[np.ndarray, np.ndarray]:
    """(naik, turun): candle berbadan >= k x ATR14 candle sebelumnya, sumbu <= 30% range."""
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    atr = np.r_[np.nan, atr_w(df, 14)[:-1]]
    body, rng = np.abs(c - o), h - l
    ok = (body >= k * atr) & (rng - body <= WICK * rng) & (rng > 0)
    return ok & (c > o), ok & (c < o)


def f1(a, k: float):
    """Candle sinyal (indeks i = candle sebelum waktu keputusan t) adalah MC searah."""
    up, dn = mc_mask(a.b.df, k)
    pos = {t: i for i, t in enumerate(a.b.t)}

    def keep(g: pd.DataFrame) -> np.ndarray:
        i = np.array([pos.get(t, 0) for t in g.t]) - 1
        return np.where(g.dir.to_numpy() > 0, up[i], dn[i])
    return keep


def f2_xau():
    from .event_stats import xau_m15
    m = xau_m15()
    up, dn = mc_mask(m, 1.0)
    s_up = pd.Series(up, index=m.index + pd.Timedelta(minutes=15))    # diketahui saat candle M15 tutup
    s_dn = pd.Series(dn, index=m.index + pd.Timedelta(minutes=15))

    def keep(g: pd.DataFrame) -> np.ndarray:
        t = pd.DatetimeIndex(g.t)
        u = s_up.reindex(t).fillna(False).to_numpy(bool)
        d = s_dn.reindex(t).fillna(False).to_numpy(bool)
        return np.where(g.dir.to_numpy() > 0, u, d)
    return keep


def f4(a):
    H4 = resample(a.b.df, "240min")
    c = H4.close.to_numpy(float)
    st = np.sign(c - ema(c, 50))
    st[:50] = 0
    s = pd.Series(st, index=H4.index + pd.Timedelta(hours=4))

    def keep(g: pd.DataFrame) -> np.ndarray:
        v = s.reindex(pd.DatetimeIndex(g.t), method="ffill").fillna(0).to_numpy()
        return v == g.dir.to_numpy()
    return keep


def f3_keep(sig: pd.DataFrame) -> np.ndarray:
    day = server_time(pd.DatetimeIndex(sig.t)).normalize()
    order = sig.assign(day=day).sort_values("t")
    rank = order.groupby("day").cumcount()
    return (rank < 2).reindex(sig.index).to_numpy()


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        sig = a.money.copy()
        sig["t"] = pd.to_datetime(sig.t, utc=True)
        print(f"\n=== {name}: filter unsur Trading Alchemist pada {len(sig)} sinyal 💰 (latih < {a.split:%Y}) ===")
        filters = {f"F1 candle sinyal MC {k}xATR": f1(a, k) for k in (1.0, 1.5)}
        if name == "XAUUSD":
            filters["F2 MC M15 terakhir searah"] = f2_xau()
        filters["F4 validasi H4 EMA50"] = f4(a)
        for fname, fn in filters.items():
            keep = fn(sig[["t", "dir"]])
            j = judge(sig, keep, a.split)
            print(fmt_judge(fname, j))
            print("   per tahun (lolos/dibuang(n)): " + per_year(sig, keep))
            if j["konsisten"]:
                print("   uji nyata:\n   " + realistic_summary(a, bar_filter(a, fn)).replace("\n", "\n   "))
        keep = f3_keep(sig)
        print(fmt_judge("F3 maks 2 sinyal per hari", judge(sig, keep, a.split)))

        print(f"--- {name}: SL+ setelah minor BOS (uji nyata seperti cloud, R rata-rata 5 posisi) ---")
        variants = {
            "F bawaan (TP1 1R, SL+ setelah TP1)": dict(tps=[1.0, None, None, None, None]),
            "F, SL+ setelah BOS fraktal 2 (bukan TP1)": dict(tps=[1.0, None, None, None, None], be=False, bos=2),
            "F, SL+ setelah BOS fraktal 3 (bukan TP1)": dict(tps=[1.0, None, None, None, None], be=False, bos=3),
            "F + SL+ setelah BOS fraktal 2 (atau TP1)": dict(tps=[1.0, None, None, None, None], bos=2),
            "F + SL+ setelah BOS fraktal 3 (atau TP1)": dict(tps=[1.0, None, None, None, None], bos=3),
        }
        base = None
        for vname, v in variants.items():
            s = sl_summary(sl_run(name, v), SPLIT[name])
            base = base or s
            better = (s["yr"] - base["yr"]).reindex(base["yr"].index).fillna(0)
            print(f"{vname:44s} n={s['n']:4d} WR {s['wr']:5.1f}% {s['avg']:+.3f}R/sinyal total {s['tot']:+7.1f}R "
                  f"DD {s['dd']:+6.1f}R | latih {s['latih']:+.3f} uji {s['uji']:+.3f} | tahun+ {s['tahun']} | "
                  f"lebih baik dari bawaan {int((better > 0).sum())}/{len(better)} tahun")


if __name__ == "__main__":
    main()
