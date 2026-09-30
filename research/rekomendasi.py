"""Rekomendasi lanjutan: hal yang BELUM pernah diuji di riset sebelumnya (python -m research.rekomendasi).

Sinyal 💰 = mesin cloud yang sama (research/eksternal.py: F-ensemble 3 set Donchian H1, SL 3×ATR, 5 posisi, TP1 1R
+ SL+, kategori konf+⭐/konf/⭐/biasa, XAU lewati 3 candle setelah buka pekan). Kategori non-💰 ditolak di allow()
seperti cloud. Sinyal kembar (beberapa set di candle & arah sama) = 1 entry, hasil = set paling lambat (seperti
aplikasi, research/kembar_tutup.py).

1. Biaya swap (selama ini "spread dihitung, swap belum"). BTCUSDc: swap long −1855,5 poin (spesifikasi Exness dari
   pengguna, 27 Sep 2026; poin 0,01 → $18,56 per BTC per hari pada harga ±$84.500 → 0,022%/hari), dihitung sebagai
   persen harga supaya adil untuk tahun-tahun lampau. XAU: nilai swap belum diketahui → skenario 5% & 10%/tahun.
   Posisi: 5 sampai TP1, 4 sesudahnya. Rollover 22:00 UTC; XAU Senin–Jumat dengan Rabu ×3, BTC setiap hari.
2. Risiko per badge: statistik kategori dari periode LATIH saja, dipakai di periode UJI (XAU uji 2019+, BTC 2021+).
3. Portofolio XAU + BTC per tahun dalam % modal (risiko per sinyal = rugi saat SL, tanpa bunga majemuk),
   sesudah swap BTC, dengan filter September BTC yang sudah terpasang di cloud.
4. Entry limit di harga pullback (x × ATR lebih baik, berlaku n candle; tidak terisi = tidak entry).

Tidak ada perubahan pada bot live / cloud. Semua simulasi historis, bukan jaminan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import MONEY, SPLIT, asset
from .filters import features
from .gap_study import week_info
from .strategy_lab2 import STAR, signals, trend_states

LEGS = 5
BTC_SWAP_LONG_DAY = 1855.5 * 0.01 / 84503.21      # fraksi harga per hari (spesifikasi pengguna / harga saat itu)


def _category(a, f, s, i, d) -> str:
    star = bool(STAR(f, i, d))
    konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
    return "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"


def trades(name: str, pull: tuple[float, int] | None = None, cats: tuple | None = None,
           be_at: float | None = None, skip=None) -> pd.DataFrame:
    """Semua trade sinyal 💰 (per set). pull=(x_atr, n_candle) -> entry limit pullback; be_at=0,7 -> SL semua posisi
    ke entry+0,1R begitu profit mencapai 0,7R (skema "SL+ 0,7R"); skip(t_keputusan, arah) -> True = sinyal ditolak
    seperti filter di allow() cloud (set tetap kosong, candle berikutnya boleh masuk lagi). Kolom: t, t_out, t_tp1, dir, set, cat, R, entry,
    risk, i (candle sinyal)."""
    a = asset(name)
    b = a.b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    ok = cats or MONEY[name]
    o, h, l, sp, atr, n, t = b.o, b.h, b.l, b.sp, b.atr, b.n, b.t
    rows = []
    for setk, (li, si, lo, so) in enumerate(signals(b, "donchian")):
        i = 0
        while i < n - 2:
            d = 1 if li[i] else (-1 if si[i] else 0)
            if d == 0 or not atr[i] > 0 or (name == "XAUUSD" and since[i] < 3):
                i += 1
                continue
            cat = _category(a, f, s, i, d)
            if cat not in ok or (skip is not None and skip(t[i + 1], d)):
                i += 1
                continue
            out = lo if d > 0 else so
            j = i + 1
            if pull is None:
                fk, entry = j, o[j] + (sp[j] if d > 0 else 0.0)
            else:
                x, nb = pull
                lim = o[j] + (sp[j] if d > 0 else 0.0) - d * x * atr[i]
                fk = entry = None
                for k in range(j, min(j + nb, n - 1)):
                    if d > 0 and l[k] + sp[k] <= lim:
                        fk, entry = k, min(lim, o[k] + sp[k])
                        break
                    if d < 0 and h[k] >= lim:
                        fk, entry = k, max(lim, o[k])
                        break
                    if out[k]:
                        break                      # tren sudah selesai sebelum harga kembali -> batal
                if fk is None:
                    i += 1
                    continue
            risk = 3.0 * atr[i]
            sl, tp1 = entry - d * risk, entry + d * risk
            left, pnl, k, done, ktp = LEGS, 0.0, fk, False, None
            while k < n - 1:
                adj = sp[k] if d < 0 else 0.0
                if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):
                    px = sl if k == fk else (min(sl, o[k] + adj) if d > 0 else max(sl, o[k] + adj))
                    pnl += (px - entry) * d * left
                    done = True
                    break
                if left == LEGS and k > fk and ((h[k] + adj >= tp1) if d > 0 else (l[k] + adj <= tp1)):
                    pnl += risk
                    left -= 1
                    sl = entry + d * 0.1 * risk
                    ktp = k
                if be_at is not None and k > fk:
                    fav = (h[k] + adj - entry) if d > 0 else (entry - l[k] - adj)
                    if fav >= be_at * risk and (sl - entry) * d < 0.1 * risk:
                        sl = entry + d * 0.1 * risk
                if out[k]:
                    pnl += (o[k + 1] + (sp[k + 1] if d < 0 else 0.0) - entry) * d * left
                    k += 1
                    done = True
                    break
                k += 1
            if not done:
                break
            rows.append((t[fk], t[min(k, n - 1)], t[ktp] if ktp is not None else pd.NaT, d, setk, cat,
                         pnl / risk / LEGS, entry, risk, i))
            i = k + 1
    df = pd.DataFrame(rows, columns=["t", "t_out", "t_tp1", "dir", "set", "cat", "R", "entry", "risk", "i"])
    return df.sort_values(["t", "set"]).reset_index(drop=True)


def entries(df: pd.DataFrame) -> pd.DataFrame:
    """Sinyal kembar (t & arah sama) = 1 entry; hasil set paling lambat (set terbesar), seperti aplikasi."""
    return df.sort_values("set").groupby(["t", "dir"], as_index=False).last().sort_values("t").reset_index(drop=True)


def swap_r(df: pd.DataFrame, name: str, long_day: float, short_day: float) -> np.ndarray:
    """Biaya swap per trade dalam R (positif = biaya). long_day/short_day = fraksi harga per hari (biaya)."""
    out = np.zeros(len(df))
    for n, r in enumerate(df.itertuples()):
        days = pd.date_range(r.t.normalize(), r.t_out.normalize(), freq="D") + pd.Timedelta(hours=22)
        roll = days[(days > r.t) & (days <= r.t_out)]
        if name == "XAUUSD":
            w = np.where(roll.dayofweek == 2, 3, np.where(roll.dayofweek <= 4, 1, 0))
        else:
            w = np.ones(len(roll))
        legs = np.where(pd.notna(r.t_tp1) & (roll > r.t_tp1), LEGS - 1, LEGS) if len(roll) else np.array([])
        rate = long_day if r.dir > 0 else short_day
        out[n] = float((w * legs).sum()) * rate * r.entry / (r.risk * LEGS)
    return out


def nights(df: pd.DataFrame) -> pd.Series:
    return (df.t_out - df.t).dt.total_seconds() / 86400


def summary(r: pd.Series) -> str:
    return f"n={len(r):4d} WR={100 * (r > 0).mean():4.1f}% rata={r.mean():+.3f}R total={r.sum():+7.1f}R"


def curve_stats(pct: pd.Series) -> tuple[float, float, float]:
    """pct = % modal per trade diurutkan waktu tutup -> (total %, rata-rata %/tahun, max drawdown %)."""
    eq = pct.cumsum()
    dd = (eq.cummax().clip(lower=0) - eq).max()
    years = max((pct.index.max() - pct.index.min()).days / 365.25, 1e-9)
    return eq.iloc[-1], eq.iloc[-1] / years, dd


def main():
    print("# Rekomendasi lanjutan (research/rekomendasi.py)\n")
    base = {n: trades(n) for n in ("XAUUSD", "BTCUSD")}
    ent = {n: entries(df) for n, df in base.items()}

    # --- cek: per set identik dengan realistic() di research/eksternal.py ---
    from .eksternal import realistic
    for n in base:
        ref = realistic(asset(n), None)
        print(f"cek {n}: per set {len(base[n])} trade {base[n].R.sum():+.1f}R vs realistic() {len(ref)} "
              f"{sum(x[2] for x in ref):+.1f}R")

    print("\n## 1. Biaya swap\n")
    for n, e in ent.items():
        nt = nights(e)
        print(f"{n}: {summary(e.R)} | lama pegang median {nt.median():.1f} hari, rata {nt.mean():.1f}, "
              f"P90 {nt.quantile(0.9):.1f}")
    e = ent["BTCUSD"]
    for tag, sh in (("swap SELL = 0", 0.0), ("swap SELL = sama dengan BUY", BTC_SWAP_LONG_DAY)):
        c = swap_r(e, "BTCUSD", BTC_SWAP_LONG_DAY, sh)
        r = e.R - c
        print(f"BTC {tag}: biaya rata {c.mean():.3f}R/entry (BUY {c[e.dir > 0].mean():.3f}R) -> {summary(r)} "
              f"| BUY {e.R[e.dir > 0].mean():+.3f} -> {r[e.dir > 0].mean():+.3f}R")
    e = ent["XAUUSD"]
    for yr in (0.05, 0.10):
        day = yr / 365
        for tag, sh in (("hanya BUY", 0.0), ("BUY & SELL", day)):
            c = swap_r(e, "XAUUSD", day, sh)
            print(f"XAU swap {yr:.0%}/th ({tag}): biaya rata {c.mean():.3f}R/entry -> {summary(e.R - c)}")

    print("\n## 2. Risiko per badge (statistik LATIH dipakai di UJI)\n")
    pf = {}
    for n, e in ent.items():
        e = e.copy()
        if n == "BTCUSD":
            e = e[e.t.dt.month != 9]                           # filter September (terpasang di cloud)
            e["R"] = e.R - swap_r(e, n, BTC_SWAP_LONG_DAY, 0.0)
        tr, te = e[e.t < SPLIT[n]], e[e.t >= SPLIT[n]]
        avg = tr.groupby("cat").R.mean()
        print(f"{n} latih per kategori: " + ", ".join(f"{k} {v:+.3f}R ({(tr.cat == k).sum()})" for k, v in avg.items()))
        print(f"{n} uji   per kategori: " + ", ".join(
            f"{k} {v:+.3f}R ({(te.cat == k).sum()})" for k, v in te.groupby("cat").R.mean().items()))
        e["tier"] = e.cat.map(lambda c: avg.get(c, 0) >= 0.2)
        pf[n] = e
    for n, e in pf.items():
        te = e[e.t >= SPLIT[n]]
        for tag, risk in (("rata 0,5%", np.full(len(te), 0.5)),
                          ("rata 0,375%", np.full(len(te), 0.375)),
                          ("badge: 0,5% / 0,25%", np.where(te.tier, 0.5, 0.25))):
            pct = pd.Series(risk * te.R.to_numpy(), index=te.t_out).sort_index()
            tot, per_yr, dd = curve_stats(pct)
            print(f"{n} UJI {tag:20s}: {per_yr:+6.1f}%/tahun, max DD {dd:5.1f}%, rasio {per_yr / dd:4.2f}")

    print("\n## 3. Portofolio XAU + BTC (UJI 2021–2026, % modal, tanpa bunga majemuk)\n")
    for tag, fn in (("rata 0,5%", lambda e: np.full(len(e), 0.5)),
                    ("badge: 0,5% / 0,25%", lambda e: np.where(e.tier, 0.5, 0.25))):
        parts = []
        for n, e in pf.items():
            e = e[e.t >= pd.Timestamp("2021-01-01", tz="UTC")]
            parts.append(pd.Series(fn(e) * e.R.to_numpy(), index=e.t_out))
        pct = pd.concat(parts).sort_index()
        tot, per_yr, dd = curve_stats(pct)
        yearly = pct.groupby(pct.index.year).sum()
        monthly = pct.groupby([pct.index.year, pct.index.month]).sum()
        print(f"{tag}: {per_yr:+.1f}%/tahun, max DD {dd:.1f}%, bulan untung {100 * (monthly > 0).mean():.0f}%, "
              f"bulan terburuk {monthly.min():+.1f}%")
        print("   per tahun: " + ", ".join(f"{y} {v:+.1f}%" for y, v in yearly.items()))

    print("\n## 4. Entry limit di harga pullback (vs market di open berikutnya)\n")
    for n in ("XAUUSD", "BTCUSD"):
        e0 = ent[n]
        print(f"{n} market      : {summary(e0.R)}")
        for pull in ((0.25, 3), (0.5, 3), (0.5, 6), (1.0, 6)):
            e = entries(trades(n, pull))
            tr, te = e[e.t < SPLIT[n]], e[e.t >= SPLIT[n]]
            print(f"{n} pullback {pull[0]:.2f}×ATR {pull[1]} candle: {summary(e.R)} | "
                  f"latih {tr.R.mean():+.3f}R uji {te.R.mean():+.3f}R")


if __name__ == "__main__":
    main()
