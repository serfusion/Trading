"""Kebijakan uang & risiko di data asli 2012-2026 (python -m research.policy).

1. Ilusi win-rate: sinyal Donchian H1 55/20 yang sama, TP makin dekat -> win-rate naik, profit turun.
2. Money management pada trade A-ensemble (research.combine): risiko tetap 0,25-5% vs martingale.
3. EA grid + martingale (pola yang paling banyak dijual untuk emas): win-rate tinggi, lalu akun habis.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .combine import ensemble
from .data import resample
from .harness import Arrays, fmt, last_base_of, periods, simulate, stats, to_base

DATA = Path(os.getenv("XAU_DATA_DIR", "data/research"))


# ---------------------------------------------------------------- 1. ilusi win-rate
def donchian_tp(p, tp_r: float | None, n_entry=55, n_exit=20, stop_atr=3.0) -> np.ndarray:
    H = resample(p.base, "60min")
    A, sp = Arrays(p.base), p.spread
    h, l, c = (H[k].to_numpy(float) for k in ("high", "low", "close"))
    a = atr(H, 20)
    hi_e = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo_e = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    hi_x = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    lo_x = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    start, last = to_base(p.base, H.index), last_base_of(p.base, H)
    ex_l, ex_s = np.zeros(A.n, bool), np.zeros(A.n, bool)
    ex_l[last[c < lo_x]] = True
    ex_s[last[c > hi_x]] = True
    out, busy = [], -1
    for k in range(n_entry + 1, len(H) - 1):
        d = 1 if c[k] > hi_e[k] else (-1 if c[k] < lo_e[k] else 0)
        j0 = start[k + 1]
        if d == 0 or j0 <= busy or j0 >= A.n - 2:
            continue
        entry = A.o[j0] + (sp if d > 0 else 0.0)
        risk = stop_atr * a[k]
        tp = entry + d * tp_r * risk if tp_r else None
        j1, r = simulate(A, sp, j0, d, entry, entry - d * risk, tp, 60 * 24 * 12,
                         exit_mask=ex_l if d > 0 else ex_s)
        out.append(r)
        busy = j1
    return np.array(out)


# ---------------------------------------------------------------- 2. money management
def equity_path(r: np.ndarray, policy: str, pct: float, start: float = 1.0) -> tuple[float, float, bool]:
    """Return (ekuitas akhir, max drawdown, bangkrut?). Bangkrut = ekuitas < 20% modal awal."""
    eq, peak, dd, streak = start, start, 0.0, 0
    for x in r:
        risk = pct if policy == "fixed" else min(100.0, pct * 2 ** streak)  # martingale: risiko x2 tiap kalah
        eq *= max(0.0, 1 + risk / 100 * x)
        streak = streak + 1 if x < 0 else 0
        peak = max(peak, eq)
        dd = min(dd, eq / peak - 1)
        if eq < 0.2 * start:
            return eq, -1.0, True
    return eq, dd, False


def monte_carlo(r: np.ndarray, years: float, policy: str, pct: float, n: int = 3000, seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    fin, dds, ruin = [], [], 0
    for _ in range(n):
        e, d, b = equity_path(rng.choice(r, len(r), replace=True), policy, pct)
        fin.append(e)
        dds.append(d)
        ruin += b
    fin, dds = np.array(fin), np.array(dds)
    return {"cagr_median": (np.median(fin) ** (1 / years) - 1) * 100,
            "p_dd30": (dds <= -0.30).mean() * 100, "p_dd50": (dds <= -0.50).mean() * 100,
            "p_ruin": ruin / n * 100, "p_loss": (fin < 1).mean() * 100}


# ---------------------------------------------------------------- 3. EA grid martingale
def grid_martingale(H: pd.DataFrame, spread_of, balance0=1000.0, lot0=0.01, mult=1.5, step_pct=0.25,
                    max_levels=12, leverage=500) -> dict:
    """Basket BUY/SELL (arah candle terakhir), tambah posisi tiap `step_pct`% melawan arah dengan lot x
    `mult`, tutup semua saat harga kembali `step` di atas rata-rata entry. Tanpa SL. 1 lot = 100 oz.
    Level baru hanya bila margin bebas cukup; bila level ditambah di sebuah candle, TP basket tidak dihitung di
    candle itu (urutan high/low tidak diketahui). Akun dianggap habis bila ekuitas <= 0 di low/high candle
    (stop-out broker 0%), lalu diisi ulang $1.000."""
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = H.index
    bal, ruins, baskets, wins, lives = balance0, [], 0, 0, [t[0]]
    pos: list[tuple[float, float]] = []  # (harga entry, lot)
    d = 0
    peak_bal = bal
    for i in range(1, len(H)):
        sp = spread_of(t[i])
        if not pos:
            d = 1 if c[i - 1] >= o[i - 1] else -1
            pos = [(o[i] + (sp if d > 0 else 0.0), lot0)]
            step = o[i] * step_pct / 100
        # tambah level (harga terburuk bar ini) bila margin bebas cukup (leverage 1:`leverage`)
        added = False
        while len(pos) < max_levels:
            nxt = pos[-1][0] - d * step
            if not ((l[i] + sp <= nxt) if d > 0 else (h[i] >= nxt)):
                break
            lot = round(pos[-1][1] * mult, 2)
            used = sum(x for _, x in pos) * nxt * 100 / leverage
            equity = bal + sum((nxt - p_) * d * x * 100 for p_, x in pos)
            if equity - used < lot * nxt * 100 / leverage:
                break  # broker menolak order: margin tidak cukup
            pos.append((nxt, lot))
            added = True
        lots = sum(x for _, x in pos)
        avg = sum(p * x for p, x in pos) / lots
        worst = (l[i] - avg) * d * lots * 100 if d > 0 else (avg - h[i] - sp) * lots * 100
        if bal + worst <= 0:
            ruins.append(t[i])
            bal, pos, peak_bal = balance0, [], balance0
            lives.append(t[i])
            continue
        target = avg + d * step
        if not added and ((h[i] >= target) if d > 0 else (l[i] + sp <= target)):  # urutan intrabar tak diketahui
            bal += step * lots * 100
            baskets += 1
            wins += 1
            pos = []
            peak_bal = max(peak_bal, bal)
    life_days = np.diff([x.value for x in lives] + [t[-1].value]) / 86400e9
    total = baskets + len(ruins)
    return {"baskets": total, "win": 100.0 * wins / total if total else 0.0, "ruins": len(ruins),
            "deposit": balance0 * (1 + len(ruins)), "final": bal,
            "median_life_days": float(np.median(life_days)), "ruin_dates": ruins}


def main():
    ps = periods()
    print("1. Ilusi win-rate: sinyal Donchian H1 55/20 yang sama, hanya TP yang diubah")
    for tp in (0.25, 0.5, 1.0, 2.0, None):
        allr = np.concatenate([donchian_tp(p, tp) for p in ps])
        print(f"   TP {'channel exit' if tp is None else f'{tp}R':>12}: {fmt(stats(allr))}")

    pkl = DATA / "combine.pkl"
    if pkl.exists():
        with open(pkl, "rb") as fh:
            per = pickle.load(fh)["A"]
    else:
        per = {p.name: ensemble(resample(p.base, "60min"), p.spread) for p in ps}
    tr = pd.concat(per.values()).sort_values("exit")
    r = tr.R.to_numpy() * 3  # R per set (risiko per set = pct)
    years = (tr.exit.max() - tr.time.min()).days / 365.25
    w, lo = r[r > 0], r[r < 0]
    kelly = (len(w) / len(r)) - (len(lo) / len(r)) / (w.mean() / -lo.mean())
    print(f"\n2. Money management, {len(r)} trade A-ensemble {tr.time.min():%Y-%m} s/d {tr.exit.max():%Y-%m} "
          f"({years:.1f} th). Kelly penuh = {kelly * 100:.1f}% per trade")
    print("   kebijakan               | urutan asli: akhir x, maxDD | acak 3000x: CAGR median, P(DD>30%), P(DD>50%), P(bangkrut), P(rugi)")
    for policy, pct in [("fixed", 0.25), ("fixed", 0.5), ("fixed", 1.0), ("fixed", 2.0), ("fixed", 5.0),
                        ("martingale", 0.5), ("martingale", 1.0)]:
        e, d, b = equity_path(r, policy, pct)
        mc = monte_carlo(r, years, policy, pct)
        label = f"{policy} {pct}%"
        hist = "BANGKRUT" if b else f"{e:6.2f}x, {d * 100:5.1f}%"
        print(f"   {label:24s} | {hist:>18s} | {mc['cagr_median']:+6.1f}%/th {mc['p_dd30']:5.1f}% "
              f"{mc['p_dd50']:5.1f}% {mc['p_ruin']:5.1f}% {mc['p_loss']:5.1f}%")

    print("\n3. EA grid/martingale (tambah posisi tiap jarak X% melawan, TP basket, tanpa SL), akun $1.000 1:500, diisi ulang bila habis")
    H = pd.concat([p.base for p in ps])  # candle dasar M15 (2012-22) / M5 (2022-26)
    H = H[~H.index.duplicated()]
    cut = ps[2].base.index[0]
    for mult, lv, step in [(1.5, 12, 0.25), (2.0, 10, 0.25), (1.0, 20, 0.25), (1.3, 10, 1.0)]:
        g = grid_martingale(H, lambda t: 0.30 if t < cut else 0.25, mult=mult, max_levels=lv, step_pct=step)
        yrs = ", ".join(sorted({f"{x:%Y}" for x in g["ruin_dates"]}))
        print(f"   jarak {step}%, lot x{mult}, maks {lv} level: {g['baskets']} basket, {g['win']:.1f}% basket profit, "
              f"akun habis {g['ruins']}x (umur median {g['median_life_days']:.0f} hari) | setor ${g['deposit']:,.0f} "
              f"-> saldo akhir ${g['final']:,.0f} | tahun habis: {yrs}")


if __name__ == "__main__":
    main()
