"""Apakah memilih penyedia copy trade dengan WR / profit tertinggi berhasil? — python -m research.copy_trade

Permintaan pengguna (6 Okt 2026): "apakah kamu bisa copy trade? cari informasi, uji validitas, simpulkan; saya akan memintamu
mencari WR tertinggi atau profit tertinggi". Data platform (MQL5 Signals, Exness Social Trading, Binance, Myfxbook, ZuluTrade,
eToro) diblokir jaringan sesi → diuji dengan PASAR TIRUAN: ±300 "penyedia" di XAU H1 2012–2026 dengan gaya yang memang
ada di platform copy trade:
  tren      breakout Donchian (WR rendah, untung besar)
  balik     RSI(2) ekstrem, keluar di RSI 50 (WR tinggi)
  scalper   entry acak, TP kecil / SL besar (WR sangat tinggi, harapan negatif setelah biaya)
  grid      averaging/martingale berlapis tanpa SL sampai akun habis (WR ≈ 95–100% sampai meledak)
Tiap penyedia: modal 100, ekuitas bulanan (grid: termasuk floating; akun habis = penyedia hilang dari papan peringkat,
seperti di platform asli). Tiap bulan papan peringkat 12 bulan terakhir (hanya penyedia hidup ≥ 12 bulan) → salin 5 teratas
selama 6 bulan berikutnya, modal dibagi rata. Kriteria: WR tertinggi, profit tertinggi, profit/DD, profit dengan DD ≤ 20%,
acak. Hasil: return 6 bulan ke depan, % periode rugi, % periode dengan salah satu penyedia meledak.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from .strategy_lab import atr as _atr
from .strategy_lab import markets, rsi

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_copy_trade.txt"
SPREAD = 0.30
RISK = 0.01


def data():
    h = next(m for m in markets() if m.name == "XAUUSD").h1
    o, hi, lo, c = (h[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    return h.index, o, hi, lo, c, _atr(hi, lo, c, 24)


def run_trades(t, o, hi, lo, c, a, entries, sl_atr, tp_atr, exit_fn, max_hold):
    """entries: list (i, dir) keputusan di close i -> entry open i+1. Return list (bulan keluar, R, win)."""
    out, busy = [], -1
    n = len(c)
    for i, d in entries:
        if i <= busy or i + 2 >= n:
            continue
        j = i + 1
        e = o[j] + (SPREAD if d > 0 else 0)
        sl = e - d * sl_atr * a[i]
        tp = e + d * tp_atr * a[i] if tp_atr else None
        k, px = j, None
        end = min(n - 1, j + max_hold)
        while k <= end:
            if (lo[k] <= sl) if d > 0 else (hi[k] + SPREAD >= sl):
                px = sl if k == j else (min(o[k], sl) if d > 0 else max(o[k] + SPREAD, sl))
                break
            if tp is not None and k > j and ((hi[k] >= tp) if d > 0 else (lo[k] + SPREAD <= tp)):
                px = tp
                break
            if exit_fn is not None and k > j and exit_fn(k, d):
                px = c[k] + (0 if d > 0 else SPREAD)
                break
            k += 1
        if px is None:
            k = end
            px = c[k] + (0 if d > 0 else SPREAD)
        r = (px - e) * d / abs(e - sl)
        out.append((t[k], r))
        busy = k
    return out


def equity_from_trades(trades, months):
    """Ekuitas akhir bulan dari trade (risiko RISK × ekuitas per trade, majemuk)."""
    eq, cur = [], 100.0
    by = pd.Series([r for _, r in trades], index=pd.DatetimeIndex([t for t, _ in trades])).sort_index() if trades else pd.Series(dtype=float)
    ptr = 0
    vals = by.to_numpy()
    idx = by.index
    stats = []
    for m in months:
        w = l_ = 0
        while ptr < len(vals) and idx[ptr] < m:
            cur *= 1 + RISK * vals[ptr]
            w += vals[ptr] > 0
            l_ += vals[ptr] <= 0
            ptr += 1
        eq.append(cur)
        stats.append((w, l_))
    return np.array(eq), np.array(stats)


def grid_provider(t, o, hi, lo, c, a, step, mult, layers, months, seed, per=1000, start=1300):
    """Grid/averaging: buka searah candle sebelumnya, tambah lapis tiap `step` ATR melawan, lot × mult, tutup semua di
    rata-rata + 1 ATR. Tanpa SL; akun habis bila ekuitas ≤ 0 (penyedia hilang)."""
    rng = np.random.default_rng(seed)
    bal, pos = 100.0, []        # pos: (harga, lot, dir)
    eq_m, st_m, mi, dead = [], [], 0, False
    w = l_ = 0
    while mi < len(months) and months[mi] <= t[start]:     # sebelum penyedia lahir: belum ada di papan
        eq_m.append(np.nan)
        st_m.append((0, 0))
        mi += 1
    for k in range(start, len(c)):
        while mi < len(months) and t[k] >= months[mi]:
            fl = sum((c[k] - p if d > 0 else p - c[k] - SPREAD) * lot * 100 for p, lot, d in pos)
            eq_m.append(np.nan if dead else bal + fl)
            st_m.append((w, l_))
            w = l_ = 0
            mi += 1
        if dead:
            continue
        if not pos:
            if rng.random() < 0.25:
                d = 1 if c[k - 1] >= o[k - 1] else -1
                pos = [(o[k] + (SPREAD if d > 0 else 0), 0.01 * bal / per, d)]   # 0,01 lot per `per` modal
            continue
        d = pos[0][2]
        lots = sum(x[1] for x in pos)
        avg = sum(x[0] * x[1] for x in pos) / lots
        worst = lo[k] if d > 0 else hi[k] + SPREAD
        fl_worst = sum((worst - p) * d * lot * 100 for p, lot, _ in pos)
        if bal + fl_worst <= 0:
            dead = True
            bal = 0.0
            l_ += 1
            continue
        target = avg + d * a[k]
        if (hi[k] >= target) if d > 0 else (lo[k] + SPREAD <= target):
            bal += sum((target - p) * d * lot * 100 for p, lot, _ in pos)
            pos = []
            w += 1
            continue
        last = pos[-1][0]
        if len(pos) < layers and ((lo[k] <= last - step * a[k]) if d > 0 else (hi[k] + SPREAD >= last + step * a[k])):
            px = last - d * step * a[k]
            pos.append((px, pos[-1][1] * mult, d))
    while mi < len(months):
        eq_m.append(np.nan if dead else bal)
        st_m.append((w, l_))
        w = l_ = 0
        mi += 1
    return np.array(eq_m), np.array(st_m)


def providers():
    t, o, hi, lo, c, a = data()
    months = pd.date_range("2013-01-01", "2026-09-01", freq="MS", tz="UTC")
    r2 = rsi(c, 2)
    hh = {n: pd.Series(hi).rolling(n).max().shift(1).to_numpy() for n in (20, 40, 55, 80, 120, 10, 20, 27, 40, 60)}
    ll = {n: pd.Series(lo).rolling(n).min().shift(1).to_numpy() for n in (20, 40, 55, 80, 120, 10, 27, 40, 60)}
    P = []
    for n, sl in itertools.product((20, 40, 55, 80, 120), (2.0, 3.0)):
        ex = n // 2
        ent = [(i, 1) for i in range(1300, len(c)) if c[i] > hh[n][i]] + \
              [(i, -1) for i in range(1300, len(c)) if c[i] < ll[n][i]]
        ent.sort()
        exit_fn = (lambda k, d, ex=ex: c[k] < ll.get(ex, ll[20])[k] if d > 0 else c[k] > hh.get(ex, hh[20])[k])  # noqa: E731
        tr = run_trades(t, o, hi, lo, c, a, ent, sl, None, exit_fn, 400)
        P.append((f"tren N{n} SL{sl}", "tren", *equity_from_trades(tr, months)))
    for lo_t, sl in itertools.product((5, 10, 15), (2.0, 3.0, 5.0)):
        ent = [(i, 1) for i in range(1300, len(c)) if r2[i] < lo_t] + \
              [(i, -1) for i in range(1300, len(c)) if r2[i] > 100 - lo_t]
        ent.sort()
        exit_fn = (lambda k, d: r2[k] > 50 if d > 0 else r2[k] < 50)  # noqa: E731
        tr = run_trades(t, o, hi, lo, c, a, ent, sl, None, exit_fn, 24)
        P.append((f"balik RSI2<{lo_t} SL{sl}", "balik", *equity_from_trades(tr, months)))
    rng = np.random.default_rng(1)
    for k_, (tp, sl) in enumerate(itertools.product((0.3, 0.5, 0.8), (2.0, 3.0, 5.0))):
        for rep in range(4):
            idx = np.sort(rng.choice(np.arange(1300, len(c) - 30), size=6000, replace=False))
            ent = [(i, int(rng.choice([-1, 1]))) for i in idx]
            tr = run_trades(t, o, hi, lo, c, a, ent, sl, tp, None, 48)
            P.append((f"scalper TP{tp} SL{sl} #{rep}", "scalper", *equity_from_trades(tr, months)))
    seed = 0
    starts = [int(np.searchsorted(t, pd.Timestamp(f"{y}-01-05", tz="UTC"))) for y in range(2013, 2026)]
    for step, mult, layers, per in itertools.product((2.0, 3.0), (1.2, 1.5), (6, 10), (1000, 2000)):
        for st0 in starts:                        # penyedia grid baru muncul tiap tahun (seperti di platform)
            seed += 1
            eq, st = grid_provider(t, o, hi, lo, c, a, step, mult, layers, months, seed, per, max(st0, 1300))
            P.append((f"grid s{step} x{mult} L{layers} per{per} mulai {t[st0]:%Y}", "grid", eq, st))
    return months, P


def main() -> None:
    months, P = providers()
    fam = np.array([p[1] for p in P])
    EQ = np.vstack([p[2] for p in P])                    # penyedia × bulan
    W = np.vstack([p[3][:, 0] for p in P])
    Lc = np.vstack([p[3][:, 1] for p in P])
    T = len(months)
    L = ["# Copy trade: memilih penyedia dengan WR / profit tertinggi (research/copy_trade.py)",
         f"Pasar tiruan: {len(P)} penyedia XAU H1 ({', '.join(f'{f} {int((fam == f).sum())}' for f in np.unique(fam))}), "
         f"bulan {months[0]:%Y-%m}–{months[-1]:%Y-%m}. Papan peringkat 12 bulan, salin 5 teratas, tahan 6 bulan.", ""]
    dead_any = np.isnan(EQ[:, -1])
    L.append("Penyedia yang akun-nya habis sampai akhir: " + ", ".join(
        f"{f} {int((dead_any & (fam == f)).sum())}/{int((fam == f).sum())}" for f in np.unique(fam)))
    g = fam == "grid"
    life = (~np.isnan(EQ[g])).sum(1)
    L.append(f"Umur penyedia grid: median {np.median(life):.0f} bulan, {(life >= 12).mean() * 100:.0f}% bertahan ≥ 12 bulan, "
             f"{(life >= 36).mean() * 100:.0f}% ≥ 36 bulan")
    rng = np.random.default_rng(7)
    crit = ["WR tertinggi", "profit tertinggi", "profit/DD", "profit, DD ≤ 20%", "acak"]
    res = {c: [] for c in crit}
    for m in range(12, T - 6, 1):
        alive = ~np.isnan(EQ[:, m]) & ~np.isnan(EQ[:, m - 12])
        if alive.sum() < 20:
            continue
        past = EQ[:, m - 12:m + 1]
        ret = past[:, -1] / past[:, 0] - 1
        dd = np.nanmin(past / np.fmax.accumulate(past, axis=1), axis=1) - 1
        w, l_ = W[:, m - 11:m + 1].sum(1), Lc[:, m - 11:m + 1].sum(1)
        wr = np.where(w + l_ >= 10, w / np.maximum(w + l_, 1), np.nan)
        score = {"WR tertinggi": wr, "profit tertinggi": ret, "profit/DD": ret / np.maximum(-dd, 0.02),
                 "profit, DD ≤ 20%": np.where(dd >= -0.20, ret, np.nan), "acak": rng.random(len(P))}
        for cname, sc in score.items():
            s = np.where(alive, sc, np.nan)
            ok = np.where(~np.isnan(s))[0]
            if len(ok) < 5:
                continue
            pick = ok[np.argsort(-s[ok])[:5]]
            fut = EQ[pick, m:m + 7]
            blown = np.isnan(fut[:, -1])
            fr = np.where(blown, -1.0, fut[:, -1] / fut[:, 0] - 1)
            res[cname].append({"m": months[m], "ret": fr.mean(), "blown": blown.any(),
                               "fam": [fam[i] for i in pick], "wr_past": np.nanmean(wr[pick]) if cname != "acak" else np.nan,
                               "wr_fut": np.nansum(W[pick, m + 1:m + 7]) / max(np.nansum(W[pick, m + 1:m + 7] + Lc[pick, m + 1:m + 7]), 1)})
    L += ["", "| Cara memilih | Return 6 bln (median / rata) | % periode rugi | % periode ada penyedia meledak | WR 12 bln lalu → 6 bln ke depan | Gaya yang terpilih |",
          "|---|---|---|---|---|---|"]
    for cname in crit:
        x = pd.DataFrame(res[cname])
        if x.empty:
            continue
        fams = pd.Series([f for fs in x.fam for f in fs]).value_counts(normalize=True)
        famtxt = ", ".join(f"{k} {v * 100:.0f}%" for k, v in fams.items())
        for lab, sub in (("", x),):
            L.append(f"| {cname} | {sub.ret.median() * 100:+.1f}% / {sub.ret.mean() * 100:+.1f}% | "
                     f"{(sub.ret < 0).mean() * 100:.0f}% | {sub.blown.mean() * 100:.0f}% | "
                     f"{sub.wr_past.mean() * 100:.0f}% → {sub.wr_fut.mean() * 100:.0f}% | {famtxt} |")
    for cname in crit:
        x = pd.DataFrame(res[cname])
        if x.empty:
            continue
        lama, baru = x[x.m < pd.Timestamp("2021-10-01", tz="UTC")], x[x.m >= pd.Timestamp("2021-10-01", tz="UTC")]
        L.append(f"   {cname}: LAMA rata {lama.ret.mean() * 100:+.1f}% (meledak {lama.blown.mean() * 100:.0f}%) | "
                 f"BARU rata {baru.ret.mean() * 100:+.1f}% (meledak {baru.blown.mean() * 100:.0f}%)")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
