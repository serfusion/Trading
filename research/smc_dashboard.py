"""Uji konsep dashboard "SMC ELITE PRO v9.1" (tangkapan layar pengguna 28 Sep 2026) sebagai filter sinyal 💰.

python -m research.smc_dashboard

Kode indikator itu tidak dipakai/dijalankan; setiap baris dashboard ditulis ulang sebagai aturan sederhana yang hanya
memakai candle yang sudah tutup (tanpa look-ahead). Kriteria "konsisten" sama dengan research/eksternal.py (judge):
dibuang ≤ 0 di latih & uji, lolos > dasar di latih & uji, ≥ 60% tahun membaik, permutasi p < 0,05.

Varian (ditetapkan sebelum melihat hasil):
- Higher Timeframe: searah tren mingguan (close minggu lalu vs SMA 20 minggu) / harian (close kemarin vs SMA 50 hari)
- PD Position: BUY hanya di discount (< 50% range), SELL hanya di premium (> 50%) — range 20 hari & 1 minggu;
  juga kebalikannya (BUY di premium = ikut momentum)
- Market Structure: swing H1 (fraktal 5 candle) HH/HL = naik, LH/LL = turun; "tidak berlawanan" & "searah"
- Liquidity Pools: jumlah swing high belum tersapu di atas harga (BSL) vs swing low di bawah (SSL), 200 candle;
  BUY bila BSL > SSL (likuiditas di arah sinyal lebih banyak), SELL sebaliknya
- Zone Status / FVG: FVG searah di 3 candle terakhir (displacement); tidak ada FVG lawan belum terisi di depan harga
  (100 candle)
- Session sudah diuji di research/eksternal_sesi.py (tidak konsisten), tidak diulang.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import asof, asset, bar_filter, fmt_judge, judge, per_year, realistic_summary

WIN_LIQ, WIN_FVG = 200, 100


def _htf(df: pd.DataFrame, rule: str, n: int, times: pd.DatetimeIndex) -> np.ndarray:
    """Tanda (close periode terakhir yang sudah tutup − SMA n periode) pada `times` (waktu close candle sinyal)."""
    c = df.close.resample(rule).last().dropna()
    x = np.sign(c - c.rolling(n).mean())
    avail = c.index + (pd.Timedelta(days=1) if rule.startswith("W") else pd.Timedelta(days=1))
    return asof(times, x, avail)


def features(df: pd.DataFrame) -> dict[str, np.ndarray]:
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    n = len(c)
    close_t = pd.DatetimeIndex(df.index + pd.Timedelta(hours=1))
    out = {"wk": _htf(df, "W-SUN", 20, close_t), "d1": _htf(df, "D", 50, close_t)}
    for tag, w in (("pd20", 480), ("pd5", 120)):
        hi = df.high.rolling(w, min_periods=w // 2).max().to_numpy()
        lo = df.low.rolling(w, min_periods=w // 2).min().to_numpy()
        out[tag] = (c - lo) / np.where(hi > lo, hi - lo, np.nan)
    # fraktal 5 candle: swing di k diketahui setelah candle k+2 tutup
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    sh[2:-2] = (h[2:-2] > h[1:-3]) & (h[2:-2] > h[:-4]) & (h[2:-2] > h[3:-1]) & (h[2:-2] > h[4:])
    sl[2:-2] = (l[2:-2] < l[1:-3]) & (l[2:-2] < l[:-4]) & (l[2:-2] < l[3:-1]) & (l[2:-2] < l[4:])
    struct = np.zeros(n)
    highs, lows = [], []
    for i in range(n):
        k = i - 2
        if k >= 0 and sh[k]:
            highs = (highs + [h[k]])[-2:]
        if k >= 0 and sl[k]:
            lows = (lows + [l[k]])[-2:]
        if len(highs) == 2 and len(lows) == 2:
            struct[i] = 1 if highs[1] > highs[0] and lows[1] > lows[0] else -1 if highs[1] < highs[0] and lows[1] < lows[0] else 0
    out["struct"] = struct
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    bull[2:] = l[2:] > h[:-2]
    bear[2:] = h[2:] < l[:-2]
    out["disp_up"] = np.convolve(bull, np.ones(3), "full")[:n] > 0
    out["disp_dn"] = np.convolve(bear, np.ones(3), "full")[:n] > 0
    bsl = np.zeros(n)
    ssl = np.zeros(n)
    obs_up = np.zeros(n, bool)     # FVG turun belum terisi di atas harga (penghalang BUY)
    obs_dn = np.zeros(n, bool)     # FVG naik belum terisi di bawah harga (penghalang SELL)
    for i in range(WIN_LIQ + 3, n):
        a = i - WIN_LIQ
        seg_h, seg_l = h[a:i + 1], l[a:i + 1]
        after_max = np.maximum.accumulate(seg_h[::-1])[::-1]       # max high dari k s/d i
        after_min = np.minimum.accumulate(seg_l[::-1])[::-1]
        ks = np.arange(a, i - 1)                                     # swing terkonfirmasi: k <= i-2
        later_max = np.r_[after_max[1:], -np.inf][: len(ks)]
        later_min = np.r_[after_min[1:], np.inf][: len(ks)]
        bsl[i] = np.sum(sh[ks] & (h[ks] > later_max) & (h[ks] > c[i]))
        ssl[i] = np.sum(sl[ks] & (l[ks] < later_min) & (l[ks] < c[i]))
        b = i - WIN_FVG
        kf = np.arange(b, i)                                         # FVG di k (butuh k-2), diisi candle sesudah k
        lm = np.r_[after_max[kf - a + 1]] if len(kf) else np.array([])
        ln = np.r_[after_min[kf - a + 1]] if len(kf) else np.array([])
        # bear FVG di k: celah (h[k], l[k-2]); belum terisi = belum ada high sesudahnya >= l[k-2]
        obs_up[i] = np.any(bear[kf] & (lm < l[kf - 2]) & (h[kf] > c[i]))
        obs_dn[i] = np.any(bull[kf] & (ln > h[kf - 2]) & (l[kf] < c[i]))
    out.update(bsl=bsl, ssl=ssl, obs_up=obs_up, obs_dn=obs_dn)
    return out


def variants(t: pd.Series, d: np.ndarray, f: dict, times: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """t = waktu keputusan (open candle sesudah candle sinyal); indeks candle sinyal = posisi t − 1."""
    i = np.clip(np.searchsorted(times.asi8, pd.DatetimeIndex(t).as_unit("ns").asi8) - 1, 0, len(times) - 1)
    d = np.asarray(d, float)
    g = {k: v[i] for k, v in f.items()}
    nan_ok = lambda x, cond: np.isnan(x) | cond  # noqa: E731 - data belum cukup -> sinyal tetap dikirim
    up = d > 0
    return {
        "HTF mingguan searah": nan_ok(g["wk"], g["wk"] == d),
        "HTF harian searah (SMA50)": nan_ok(g["d1"], g["d1"] == d),
        "PD: BUY discount/SELL premium 20h": nan_ok(g["pd20"], np.where(up, g["pd20"] < 0.5, g["pd20"] > 0.5)),
        "PD: BUY premium/SELL discount 20h": nan_ok(g["pd20"], np.where(up, g["pd20"] > 0.5, g["pd20"] < 0.5)),
        "PD: BUY discount/SELL premium 1mg": nan_ok(g["pd5"], np.where(up, g["pd5"] < 0.5, g["pd5"] > 0.5)),
        "Struktur H1 tidak berlawanan": g["struct"] != -d,
        "Struktur H1 searah": g["struct"] == d,
        "Likuiditas searah lebih banyak": np.where(up, g["bsl"] > g["ssl"], g["ssl"] > g["bsl"]),
        "FVG searah 3 candle (displacement)": np.where(up, g["disp_up"], g["disp_dn"]),
        "Tanpa FVG lawan di depan harga": ~np.where(up, g["obs_up"], g["obs_dn"]),
    }


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        f = features(a.b.df)
        times = pd.DatetimeIndex(a.b.df.index).as_unit("ns")
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            print(f"\n=== {name} — {label}: {len(sig)} sinyal (latih < {a.split:%Y}) — lolos/dibuang [dasar] ===")
            vs = variants(sig.t, sig.dir.to_numpy(), f, times)
            res = {k: judge(sig, v, a.split) for k, v in vs.items()}
            for k, j in res.items():
                print(fmt_judge(k, j))
            if label == "💰 dikirim":
                best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
                print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")
                for k in (k for k in res if res[k]["konsisten"]):
                    print(f"-> {k} konsisten; uji nyata (filter di allow seperti cloud):")
                    print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g.t, g.dir.to_numpy(), f,
                                                                                     times)[k])))


if __name__ == "__main__":
    main()
