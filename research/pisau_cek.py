"""Uji ketahanan kandidat "tangkap pisau" (research/pisau.py) — python -m research.pisau_cek

Per kandidat: per tahun, biaya ×2/×3, entry terlambat 1 candle, kalah beruntun & DD (R), sinyal per bulan, tumpang
tindih dengan sinyal 💰 yang sudah dikirim (BTC/XAU), dan untuk XAU simulasi ulang di candle M15/M5 (urutan SL/TP di
dalam candle H1). Kandidat dipilih dari tabel LAMA di docs/eksternal/hasil_pisau.txt (bukan dari BARU).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import pisau as P

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pisau_cek.txt"

# (nama, aset, gerak, N, k, mode, tren, SL, TP, H)
CANDS = [
    ("X0 XAU tangkap pisau sederhana (pembanding)", "XAU", -1, 12, 5, "b_mkt", "semua", 2.0, 1.0, 24),
    ("X1 XAU jatuh → BUY limit 1,5 ATR, tren turun", "XAU", -1, 48, 5, "b_lim1.5", "melawan", 3.0, "r50", 48),
    ("X2 XAU jatuh → SELL tembus low", "XAU", -1, 6, 6, "l_brk", "semua", 3.0, 3.0, 12),
    ("X3 XAU lonjak → BUY tembus high, tren naik", "XAU", 1, 3, 4, "l_brk", "searah", 3.0, 2.0, 48),
    ("B1 BTC jatuh → SELL pasar, tren turun", "BTC", -1, 3, 3, "l_mkt", "searah", 2.0, 3.0, 24),
    ("B2 BTC lonjak → BUY pasar", "BTC", 1, 12, 6, "l_mkt", "semua", 3.0, "r50", 24),
    ("B0 BTC tangkap pisau sederhana (pembanding)", "BTC", -1, 12, 5, "b_mkt", "semua", 2.0, 1.0, 24),
    ("E1 ETH jatuh → SELL pasar", "ETH", -1, 12, 5, "l_mkt", "semua", 2.0, 3.0, 12),
    ("E2 ETH lonjak → BUY pasar, tren naik", "ETH", 1, 24, 6, "l_mkt", "searah", 3.0, 3.0, 12),
]


def trades(s: P.Series, move, n, k, mode, tren, sl, tp, hh, delay: int = 0) -> pd.DataFrame:
    ev = P.events(s, n, k, move)
    t, j0, px, d = P.entries(s, ev, n, move, mode)
    if delay:
        ok = j0 + delay + P.HMAX + 2 < len(s.c)
        t, j0, d = t[ok], j0[ok] + delay, d[ok]
        px = s.o[j0]
    if tren != "semua" and len(t):
        want = d if tren == "searah" else -d
        keep = s.trend[t] == want
        t, j0, px, d = t[keep], j0[keep], px[keep], d[keep]
    if len(t) == 0:
        return pd.DataFrame()
    res = P.outcomes(s, t, j0, px, d, move, n)
    r, k_out = res[(sl, tp, hh)]
    a = s.atr[t]
    cost = s.cost * px if s.pct else np.full(len(t), s.cost)
    return pd.DataFrame({"t": s.t[j0], "t_out": s.t[np.minimum(j0 + k_out, len(s.t) - 1)], "R": r, "dir": d,
                         "j0": j0, "px": px, "e": px + d * cost, "sl": px + d * cost - d * sl * a, "atr": a,
                         "ev": t})


def streak(r: np.ndarray) -> int:
    best = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        best = max(best, cur)
    return best


def line(x: pd.DataFrame) -> str:
    if x.empty:
        return "n 0"
    eq = x.R.cumsum().to_numpy()
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return (f"n {len(x)} WR {(x.R > 0).mean() * 100:.0f}% rata {x.R.mean():+.2f}R total {x.R.sum():+.1f}R "
            f"DD {dd:.1f}R kalah beruntun {streak(x.R.to_numpy())}")


def money_overlap(asset: str, tr: pd.DataFrame) -> float:
    """% trade yang terjadi saat sinyal 💰 searah (sistem breakout yang sudah live) sedang terbuka."""
    from .eksternal import asset as load_asset
    m = load_asset({"XAU": "XAUUSD", "BTC": "BTCUSD"}[asset]).money
    hit = 0
    for _, x in tr.iterrows():
        o = m[(m.t <= x.t) & (m.t_out > x.t) & (m.dir == x.dir)]
        hit += len(o) > 0
    return hit / len(tr) * 100 if len(tr) else np.nan


def m_base_check(tr: pd.DataFrame, sl_mult, tp, hh) -> pd.DataFrame:
    """Ulang XAU di candle M15 (2012–2022) / M5 (2022–2026): entry & SL sama, TP ATR-tetap; urutan dalam candle nyata."""
    from .harness import Arrays, periods, simulate
    rows = []
    for p in periods():
        base = p.base
        a = Arrays(base)
        per_h = 4 if p.tf == "M15" else 12
        sub = tr[(tr.t >= base.index[0]) & (tr.t <= base.index[-1])]
        for _, x in sub.iterrows():
            j = base.index.searchsorted(x.t)
            if j >= len(base) - 2:
                continue
            d = int(x.dir)
            if isinstance(tp, str):
                continue
            tpp = x.e + d * tp * x.atr
            # biaya sudah di x.e (harga efektif) -> spread simulate 0 agar tidak dihitung dua kali
            _, r = simulate(a, 0.0, j, d, x.e, x.sl, tpp, hh * per_h)
            rows.append((x.t, r))
    return pd.DataFrame(rows, columns=["t", "R"])


def main() -> None:
    series = {s.name: s for s in P.load()}
    L = ["# Uji ketahanan kandidat tangkap pisau (research/pisau_cek.py)",
         "R = kelipatan SL; biaya sudah dipotong (XAU $0,50, BTC/ETH 0,06% pulang-pergi). LAMA < Okt 2021.", ""]
    for name, asset, move, n, k, mode, tren, sl, tp, hh in CANDS:
        s = series[asset]
        tr = trades(s, move, n, k, mode, tren, sl, tp, hh)
        if tr.empty:
            L.append(f"## {name}: tidak ada trade")
            continue
        lama, baru = tr[tr.t < P.SPLIT], tr[tr.t >= P.SPLIT]
        L += [f"## {name}", f"   aturan: N{n} k{k} {mode} tren:{tren} SL {sl} ATR TP {tp} batas {hh} jam",
              f"   LAMA : {line(lama)}", f"   BARU : {line(baru)}"]
        months = (tr.t.max() - tr.t.min()).days / 30.4
        L.append(f"   sinyal/bulan {len(tr) / months:.1f} | median lama posisi "
                 f"{((tr.t_out - tr.t).dt.total_seconds() / 3600).median():.0f} jam")
        yr = tr.groupby(tr.t.dt.year).R.agg(["count", "mean", lambda x: (x > 0).mean() * 100])
        L.append("   per tahun: " + " ".join(f"{y}:{int(c)}/{m:+.2f}R/{w:.0f}%" for y, (c, m, w) in yr.iterrows()))
        for mult in (2, 3):
            s2 = replace(s, cost=s.cost * mult)
            t2 = trades(s2, move, n, k, mode, tren, sl, tp, hh)
            L.append(f"   biaya ×{mult}: LAMA {t2[t2.t < P.SPLIT].R.mean():+.2f}R | BARU {t2[t2.t >= P.SPLIT].R.mean():+.2f}R")
        td = trades(s, move, n, k, mode, tren, sl, tp, hh, delay=1)
        if not td.empty:
            L.append(f"   entry telat 1 jam: LAMA {td[td.t < P.SPLIT].R.mean():+.2f}R | BARU {td[td.t >= P.SPLIT].R.mean():+.2f}R")
        if asset in ("XAU", "BTC"):
            try:
                L.append(f"   tumpang tindih dengan sinyal 💰 searah yang terbuka: {money_overlap(asset, tr):.0f}%")
            except Exception as exc:  # noqa: BLE001
                L.append(f"   tumpang tindih 💰: gagal ({exc})")
        if asset == "XAU" and not isinstance(tp, str):
            mb = m_base_check(tr, sl, tp, hh)
            if len(mb):
                L.append(f"   cek candle M15/M5: LAMA {mb[mb.t < P.SPLIT].R.mean():+.2f}R (n {len(mb[mb.t < P.SPLIT])}) | "
                         f"BARU {mb[mb.t >= P.SPLIT].R.mean():+.2f}R (n {len(mb[mb.t >= P.SPLIT])})")
        print("\n".join(L[-10:]), flush=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
