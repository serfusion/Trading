"""Bisakah arah tren ke depan (bullish / bearish / pindah tren) diperkirakan? (python -m research.tren_kedepan)

Pertanyaan pengguna (29 Sep 2026): tab News tidak perlu saran entry, tetapi bisakah memberi saran tren ke depan —
bullish, bearish, atau akan berbalik? Diuji menyeluruh untuk XAU/USD (2012–2026) dan BTC/USD (2016–2026).

Setiap penduga memberi arah +1 (bullish) / −1 (bearish) / 0 (tidak ada pendapat) di close harian (UTC), hanya dari
data yang sudah terbit saat itu (makro & COT memakai waktu terbit, research/eksternal.asof). Target: arah harga
1 hari, 1 minggu, 1 bulan ke depan (XAU 1/5/21 hari bursa, BTC 1/7/30 hari).

Penduga (ditetapkan sebelum melihat hasil):
- momentum: return 20 / 60 / 120 / 250 hari
- rata-rata: close vs SMA50, close vs SMA200, SMA50 vs SMA200 (golden/death cross)
- channel: Donchian harian 55/20 (turtle), Donchian H1 55/20 (set tengah sinyal kita), Supertrend D1 (10, 3)
- pembalikan: RSI14 D1 > 70 -> bearish, < 30 -> bullish; jarak > 3 ATR dari SMA50 -> berbalik
- pindah tren: Donchian D1 baru berbalik (≤ 5 hari) -> arah baru; harga baru menembus SMA50 (≤ 5 hari)
- berita AS: jumlah kejutan (data lemah = bullish emas) 5 / 20 hari terakhir
- makro: yield riil 10 th (DFII10) & dolar (DTWEXBGS) 20 hari — naik -> bearish emas (hanya XAU)
- posisi spekulan COT: ekstrem (indeks 3 th ≥ 90% -> bearish, ≤ 10% -> bullish), perubahan 4 pekan
- konsensus tren: ≥ 4 dari 5 (MOM60, MA50, MA200, Donchian D1, Supertrend) searah

Kriteria "bisa dipakai" (sama ketatnya dengan riset lain): hasil searah prediksi > 0 di latih DAN uji, tebakan
benar lebih sering dari tebakan naif (selalu naik / selalu turun, mana yang lebih sering di periode itu) di latih
DAN uji, ≥ 60% tahun positif, dan t > 2 (dikoreksi tumpang tindih: t / √h).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .eksternal import SPLIT, asof, asset
from .event_stats import releases
from .news_data import load_calendar
from .run_scan import DATA

HORIZONS = {"XAUUSD": {"1 hari": 1, "1 minggu": 5, "1 bulan": 21}, "BTCUSD": {"1 hari": 1, "1 minggu": 7, "1 bulan": 30}}


def daily(h1: pd.DataFrame) -> pd.DataFrame:
    d = h1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return d[d.high > d.low]


def donchian_state(c: np.ndarray, h: np.ndarray, l: np.ndarray, n_in: int, n_out: int) -> np.ndarray:
    hi = pd.Series(h).rolling(n_in).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(n_in).min().shift(1).to_numpy()
    xhi = pd.Series(h).rolling(n_out).max().shift(1).to_numpy()
    xlo = pd.Series(l).rolling(n_out).min().shift(1).to_numpy()
    st = np.zeros(len(c))
    s = 0
    for i in range(len(c)):
        if c[i] > hi[i]:
            s = 1
        elif c[i] < lo[i]:
            s = -1
        elif s > 0 and c[i] < xlo[i]:
            s = 0
        elif s < 0 and c[i] > xhi[i]:
            s = 0
        st[i] = s
    return st


def supertrend(d: pd.DataFrame, n: int = 10, mult: float = 3.0) -> np.ndarray:
    h, l, c = d.high.to_numpy(), d.low.to_numpy(), d.close.to_numpy()
    pc = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).rolling(n).mean().to_numpy()
    mid = (h + l) / 2
    up, dn = mid - mult * atr, mid + mult * atr
    out = np.zeros(len(c))
    trend, fu, fd = 1, up[0], dn[0]
    for i in range(1, len(c)):
        if np.isnan(atr[i]):
            continue
        fu = max(up[i], fu) if c[i - 1] > fu else up[i]
        fd = min(dn[i], fd) if c[i - 1] < fd else dn[i]
        if trend > 0 and c[i] < fu:
            trend = -1
        elif trend < 0 and c[i] > fd:
            trend = 1
        out[i] = trend
    return out


def rsi(c: pd.Series, n: int = 14) -> np.ndarray:
    ch = c.diff()
    up = ch.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-ch.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()


def predictors(name: str, h1: pd.DataFrame, d: pd.DataFrame, ev: pd.DataFrame, macro: dict, cot) -> dict:
    c, h, l = d.close, d.high.to_numpy(), d.low.to_numpy()
    cv = c.to_numpy()
    t_avail = pd.DatetimeIndex(d.index + pd.Timedelta(days=1))          # close harian terbit akhir hari (UTC)
    P = {}
    for n in (20, 60, 120, 250):
        P[f"momentum {n} hari"] = np.sign(c / c.shift(n) - 1).to_numpy()
    sma50, sma200 = c.rolling(50).mean(), c.rolling(200).mean()
    P["close vs SMA50"] = np.sign(c - sma50).to_numpy()
    P["close vs SMA200"] = np.sign(c - sma200).to_numpy()
    P["SMA50 vs SMA200"] = np.sign(sma50 - sma200).to_numpy()
    don = donchian_state(cv, h, l, 55, 20)
    P["Donchian D1 55/20"] = don
    # Donchian H1 55/20 (set tengah sinyal kita) dibaca di candle H1 terakhir tiap hari
    hc, hh, hl = h1.close.to_numpy(), h1.high.to_numpy(), h1.low.to_numpy()
    s_h1 = pd.Series(donchian_state(hc, hh, hl, 55, 20), index=h1.index).resample("1D").last()
    P["Donchian H1 55/20 (sinyal kita)"] = s_h1.reindex(d.index).fillna(0).to_numpy()
    st = supertrend(d)
    P["Supertrend D1"] = st
    r = rsi(c)
    P["RSI14 ekstrem (berbalik)"] = np.where(r > 70, -1, np.where(r < 30, 1, 0))
    tr = pd.Series(np.maximum(h - l, np.abs(h - np.r_[cv[0], cv[:-1]]))).rolling(14).mean().to_numpy()
    dist = (cv - sma50.to_numpy()) / tr
    P["> 3 ATR dari SMA50 (berbalik)"] = np.where(dist > 3, -1, np.where(dist < -3, 1, 0))
    flip = np.zeros(len(cv))
    last_change, prev = -999, 0
    for i in range(len(cv)):
        if don[i] != 0 and don[i] != prev:
            last_change, prev = i, don[i]
        flip[i] = prev if (i - last_change) <= 5 and prev != 0 else 0
    P["pindah tren: Donchian D1 baru berbalik"] = flip
    cross = np.sign(cv - sma50.to_numpy())
    xs = np.zeros(len(cv))
    for i in range(6, len(cv)):
        if np.any(cross[i - 5:i + 1] != cross[i - 6]) and cross[i] != 0:
            xs[i] = cross[i]
    P["pindah tren: baru menembus SMA50"] = xs
    trend5 = np.vstack([P["momentum 60 hari"], P["close vs SMA50"], P["close vs SMA200"], don, st])
    s = np.nansum(trend5, axis=0)
    P["konsensus tren (≥4 dari 5)"] = np.where(s >= 3, 1, np.where(s <= -3, -1, 0))
    # berita AS (bias emas: +1 data lemah / dovish)
    e = ev.dropna(subset=["bias"]).set_index("time").bias.sort_index()
    cs = e.cumsum()
    for n in (5, 20):
        now = asof(t_avail, cs, cs.index)
        past = asof(t_avail - pd.Timedelta(days=n), cs, cs.index)
        P[f"kejutan berita AS {n} hari"] = np.sign(np.nan_to_num(now) - np.nan_to_num(past))
    if name == "XAUUSD":
        for key, label in (("DFII10", "yield riil 10 th"), ("DTWEXBGS", "dolar (DTWEXBGS)")):
            df = macro[key]
            ch = asof(t_avail, df.value - df.value.shift(20), pd.DatetimeIndex(df.available))
            P[f"{label} 20 hari (naik = bearish)"] = -np.sign(np.nan_to_num(ch))
    if cot is not None:
        idx = asof(t_avail, cot.idx, pd.DatetimeIndex(cot.available))
        d4 = asof(t_avail, cot.d4, pd.DatetimeIndex(cot.available))
        P["COT spekulan ekstrem (berbalik)"] = np.where(idx >= 0.9, -1, np.where(idx <= 0.1, 1, 0))
        P["COT perubahan 4 pekan (ikut)"] = np.sign(np.nan_to_num(d4))
    return {k: np.nan_to_num(np.asarray(v, float)) for k, v in P.items()}


def evaluate(pred: np.ndarray, fwd: np.ndarray, t: pd.DatetimeIndex, split: pd.Timestamp, hz: int) -> dict:
    m = (pred != 0) & ~np.isnan(fwd)
    p, f, tt = pred[m], fwd[m], t[m]
    if len(p) < 50:
        return {"n": len(p), "ok": False}
    dirret = p * f
    hit = (np.sign(f) == p)
    out = {"n": len(p), "hit": 100 * hit.mean(), "ret": 100 * dirret.mean()}
    ok = True
    for tag, sel in (("latih", tt < split), ("uji", tt >= split)):
        if sel.sum() < 20:
            return {"n": len(p), "ok": False}
        up = (f[sel] > 0).mean()
        naive = max(up, 1 - up)
        out[f"{tag}_hit"], out[f"{tag}_naif"], out[f"{tag}_ret"] = 100 * hit[sel].mean(), 100 * naive, 100 * dirret[sel].mean()
        ok &= dirret[sel].mean() > 0 and hit[sel].mean() > naive
    yrs = pd.Series(dirret, index=tt.year).groupby(level=0).mean()
    out["tahun"] = f"{(yrs > 0).sum()}/{len(yrs)}"
    tstat = dirret.mean() / (dirret.std() or 1e-12) * math.sqrt(len(dirret)) / math.sqrt(hz)
    out["t"] = tstat
    out["ok"] = bool(ok and (yrs > 0).mean() >= 0.6 and tstat > 2)
    return out


def main() -> None:
    from .eksternal_cot import fetch as cot_fetch
    from .eksternal_makro import fred
    ev = releases(load_calendar(DATA))
    macro = {k: fred(k) for k in ("DFII10", "DTWEXBGS")}
    summary = []
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        h1 = a.b.df
        d = daily(h1)
        try:
            cot = cot_fetch(name)
        except Exception as exc:  # noqa: BLE001
            print(f"COT {name} tidak tersedia: {exc}")
            cot = None
        P = predictors(name, h1, d, ev, macro, cot)
        c = d.close.to_numpy()
        t = pd.DatetimeIndex(d.index)
        print(f"\n=== {name}: harian {t[0]:%Y-%m-%d} .. {t[-1]:%Y-%m-%d} ({len(t)} hari), latih < {SPLIT[name]:%Y} ===")
        for hz_name, hz in HORIZONS[name].items():
            fwd = np.r_[c[hz:] / c[:-hz] - 1, np.full(hz, np.nan)]
            up_all = np.nanmean(fwd > 0) * 100
            print(f"\n-- {hz_name} ke depan (naik {up_all:.0f}% dari semua periode; tebakan naif = arah yang lebih sering) --")
            print(f"{'Penduga':42s} {'n':>5s} {'benar':>6s} {'latih benar/naif':>17s} {'uji benar/naif':>15s} "
                  f"{'ret%':>6s} tahun+   t")
            for k, pred in P.items():
                v = evaluate(pred, fwd, t, SPLIT[name], hz)
                if v["n"] < 50 or "latih_hit" not in v:
                    print(f"{k:42s} {v['n']:5d} (terlalu sedikit)")
                    continue
                print(f"{k:42s} {v['n']:5d} {v['hit']:5.1f}% {v['latih_hit']:7.1f}/{v['latih_naif']:4.1f}% "
                      f"{v['uji_hit']:7.1f}/{v['uji_naif']:4.1f}% {v['ret']:+6.2f} {v['tahun']:>6s} {v['t']:+5.1f}"
                      f"{'  ✅' if v['ok'] else ''}")
                if v["ok"]:
                    summary.append(f"{name} {hz_name}: {k} (benar {v['hit']:.1f}%, uji {v['uji_hit']:.1f}% vs naif "
                                   f"{v['uji_naif']:.1f}%, t {v['t']:+.1f})")
        # kondisi terkini (untuk ditampilkan bila ada yang lolos)
        print(f"\nKondisi terakhir {t[-1]:%Y-%m-%d}: " + ", ".join(f"{k}={int(v[-1]):+d}" for k, v in P.items()))
    print("\nLolos semua kriteria:")
    print("\n".join("  " + s for s in summary) or "  tidak ada")


if __name__ == "__main__":
    main()
