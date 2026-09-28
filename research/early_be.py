"""SL+ sebelum TP1: pindahkan SL semua posisi ke entry+0,1R begitu profit mencapai X R (python -m research.early_be).

Donchian 3 set, skema F (TP1 1R posisi #1), XAU 2012-2026 & BTC 2016-2026, per tahun.
"""
import warnings

import numpy as np
import pandas as pd

from .strategy_lab import Bars, markets
from .strategy_lab2 import signals

warnings.filterwarnings("ignore")


def bt(b, li, si, lo, so, be_at, sl_atr=3.0, legs=5):
    o, h, l, sp, a, n = b.o, b.h, b.l, b.sp, b.atr, b.n
    out, i = [], 0
    while i < n - 2:
        d = 1 if li[i] else (-1 if si[i] else 0)
        if d == 0 or not a[i] > 0:
            i += 1
            continue
        j = i + 1
        entry = o[j] + (sp[j] if d > 0 else 0)
        risk = sl_atr * a[i]
        sl, tp1 = entry - d * risk, entry + d * risk
        left, pnl, k, done, be = legs, 0.0, j, False, False
        ex = lo if d > 0 else so
        while k < n - 1:
            adj = sp[k] if d < 0 else 0
            if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):
                px = sl if k == j else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                pnl += (px - entry) * d * left
                done = True
                break
            fav = (h[k] + adj - entry) if d > 0 else (entry - l[k] - adj)
            if k > j and left == legs and fav >= risk:
                pnl += risk
                left -= 1
                be = True
            if k > j and be_at is not None and fav >= be_at * risk:
                be = True
            if be:
                sl = entry + d * 0.1 * risk if (sl - entry) * d < 0.1 * risk else sl
            if ex[k]:
                pnl += (o[k + 1] + (sp[k + 1] if d < 0 else 0) - entry) * d * left
                k += 1
                done = True
                break
            k += 1
        if not done:
            break
        out.append((b.t[j], pnl / risk / legs))
        i = k + 1
    return out


def main():
    for m in markets():
        if m.name not in ("XAUUSD", "BTCUSD"):
            continue
        b = Bars(m.h1, m.spread)
        sig = signals(b, "donchian")
        print(f"### {m.name}")
        for be in (None, 0.3, 0.5, 0.7):
            tr = sorted(sum((bt(b, *s, be) for s in sig), []))
            r = np.array([x[1] for x in tr])
            yr = pd.Series(r, index=[x[0].year for x in tr]).groupby(level=0).sum()
            name = "SL+ setelah TP1 (sekarang)" if be is None else f"SL+ saat profit {be}R"
            print(f"  {name:28s} n={len(r)} WR={np.mean(r > 0) * 100:4.1f}% rata={r.mean():+.3f}R "
                  f"total={r.sum():+.0f}R tahun untung {(yr > 0).sum()}/{len(yr)}")


if __name__ == "__main__":
    main()
