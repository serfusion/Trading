"""Bandingkan metode & risiko per sinyal dengan simulasi saldo (python -m research.risk_compare).

Tiap sinyal punya waktu entry & keluar; lot dihitung dari saldo saat entry × risiko%, saldo berubah saat
posisi ditutup (posisi dari 3 set bisa terbuka bersamaan). Spread dihitung, swap belum.
"""
import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .filters import FILTERS, SETS, features, periods

STAR = FILTERS["KOMBINASI: tren D1 + H4 breakout"]


def trades(h1, spread, f, legs, n_entry, n_exit, star_only=False, stop_atr=3.0, be_r=0.1):
    """List (t_entry, t_exit, R per sinyal, star). legs: TP dalam R (None = runner); SL+ setelah TP pertama."""
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = h1.index
    a = np.asarray(atr(h1, 20), float)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    out, i = [], max(n_entry + 2, 24 * 60)
    while i < len(c) - 2:
        d = 1 if c[i] > hi_e[i] else (-1 if c[i] < lo_e[i] else 0)
        if d == 0:
            i += 1
            continue
        star = bool(STAR(f, i, d))
        if star_only and not star:
            i += 1
            continue
        entry = o[i + 1] + (spread if d > 0 else 0.0)
        risk = stop_atr * a[i]
        sl = entry - d * risk
        adj = spread if d < 0 else 0.0
        open_legs, pnl, hits, j = list(range(len(legs))), 0.0, 0, i + 1
        while open_legs and j < len(c) - 1:
            if (l[j] <= sl) if d > 0 else (h[j] + adj >= sl):
                px = sl if j == i + 1 else (min(sl, o[j]) if d > 0 else max(sl, o[j] + adj))
                pnl += (px - entry) * d * len(open_legs)
                open_legs = []
                break
            if j > i + 1:
                for k in list(open_legs):
                    tp = legs[k]
                    if tp is not None and ((h[j] >= entry + tp * risk) if d > 0 else (l[j] + adj <= entry - tp * risk)):
                        pnl += tp * risk
                        open_legs.remove(k)
                        hits += 1
                        if hits == 1:
                            sl = entry + d * be_r * risk
            runner = [k for k in open_legs if legs[k] is None]
            if runner and ((d > 0 and c[j] < lo_x[j]) or (d < 0 and c[j] > hi_x[j])):
                pnl += (o[j + 1] + adj - entry) * d * len(runner)
                open_legs = [k for k in open_legs if legs[k] is not None]
                if not open_legs:
                    break
            j += 1
        out.append((t[i + 1], t[min(j, len(t) - 1)], pnl / risk / len(legs), star))
        i = j + 1
    return out


def equity(all_trades, risk_star, risk_normal):
    """Saldo awal 1.0; return (hasil %, DD terdalam %, rugi beruntun terpanjang)."""
    events = []
    for k, (te, tx, r, star) in enumerate(all_trades):
        rp = risk_star if star else risk_normal
        if rp > 0:
            events.append((te, 0, k, r, rp))
            events.append((tx, 1, k, r, rp))
    events.sort(key=lambda e: (e[0], e[1]))
    eq, peak, dd, size, streak, worst = 1.0, 1.0, 0.0, {}, 0, 0
    for _, kind, k, r, rp in events:
        if kind == 0:
            size[k] = eq * rp
        else:
            eq += size.pop(k) * r
            peak = max(peak, eq)
            dd = min(dd, eq / peak - 1)
            streak = streak + 1 if r < 0 else 0
            worst = max(worst, streak)
    return (eq - 1) * 100, dd * 100, worst


F = [1, None, None, None, None]
A = [None] * 5
METHODS = {
    "A-ensemble (5 runner)": (A, False, {"all": 1}),
    "F-ensemble (sekarang, semua sama)": (F, False, {"all": 1}),
    "F-ensemble ⭐ saja": (F, True, {"all": 1}),
    "F-ensemble ⭐ 2x, biasa 1x": (F, False, {"star": 2, "normal": 1}),
}
RISKS = [0.005, 0.01, 0.015]


def main():
    data = {k: (d, sp, features(d)) for k, (d, sp) in periods().items()}
    cache = {}
    for name, (legs, star_only, w) in METHODS.items():
        key = (tuple(x if x is not None else -1 for x in legs), star_only)
        if key not in cache:
            cache[key] = {p: sorted(sum((trades(d, sp, f, legs, ne, nx, star_only) for ne, nx in SETS), []))
                          for p, (d, sp, f) in data.items()}
        print(name)
        for base in RISKS:
            ws = w.get("star", w.get("all", 1)), w.get("normal", w.get("all", 1))
            rs, rn = base * ws[0] / max(ws), base * ws[1] / max(ws)
            cells = []
            for p, tr in cache[key].items():
                ret, dd, streak = equity(tr, rs, rn)
                cells.append(f"{p}: {ret:+7.1f}% DD {dd:6.1f}% L{streak:2d}")
            print(f"   ⭐ {rs * 100:.2f}% / biasa {rn * 100:.2f}%  |  " + "  |  ".join(cells))


if __name__ == "__main__":
    main()
