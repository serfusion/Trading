"""Uji 10 strategi "Blueprint EA XAU/USD Non-Martingale" (unggahan pengguna, 3 Okt 2026) — python -m research.blueprint10

Aturan ditulis ulang dari dokumen (parameter baseline dokumen, sedikit variasi), XAU 2012 – 2 Okt 2026, bar dasar M15
(M5 2020+ di-resample), setup di H1/H4/D1 (bar yang sudah selesai). Entry di open bar berikutnya (+spread $0,20 untuk BUY,
ASK untuk SELL), SL dicek lebih dulu (research/harness.simulate), satu posisi per strategi, tahan maks 5 hari.
Cara keluar: "2R" (dokumen), "1R" & "0,5R" (win rate tinggi), "F" = separuh TP 1R + separuh TP 2R dengan SL ke impas
setelah +1R, "alami" (mean reversion ke middle band/VWAP). Hasil dalam R (risiko per trade).
Gabungan: filter "tren2" (H4 EMA50 & D1 EMA200 searah, sama dengan piramida), regime switching (#10), skor kualitas (#19).
Seleksi DITETAPKAN DULU di LAMA (< Okt 2021): n ≥ 100, rata-rata > 0, t ≥ 2, ≥ 70% tahun positif → diuji di BARU.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import resample
from .harness import Arrays, simulate
from .martingale_ea import SPLIT, load

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_blueprint10.txt"
SP = 0.20
HOLD = 5 * 96          # 5 hari bar M15
A = 1 / 14


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df):
    up, dn = df.high.diff(), -df.low.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    at = atr(df)
    pdi = 100 * pdm.ewm(alpha=A, adjust=False).mean() / at
    ndi = 100 * ndm.ewm(alpha=A, adjust=False).mean() / at
    return (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=A, adjust=False).mean()


def rsi(c):
    d = c.diff()
    rs = d.clip(lower=0).ewm(alpha=A, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=A, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def htf_on(src: pd.Series, idx: pd.DatetimeIndex, freq: str) -> np.ndarray:
    """Nilai bar timeframe besar yang SUDAH selesai untuk bar idx (yang dimulai pada idx)."""
    return src.shift(1).reindex(idx.floor(freq)).ffill().to_numpy()


class Data:
    def __init__(self):
        raw = load()
        self.b = resample(raw, "15min")
        self.a = Arrays(self.b)
        b = self.b
        h1 = resample(b, "1h")
        self.h1 = h1
        h4, d1 = resample(b, "4h"), resample(b, "1D")
        x = pd.DataFrame(index=h1.index)
        x["o"], x["h"], x["l"], x["c"] = h1.open, h1.high, h1.low, h1.close
        x["e20"], x["e50"], x["e200"] = ema(h1.close, 20), ema(h1.close, 50), ema(h1.close, 200)
        x["atr"], x["adx"], x["rsi"] = atr(h1), adx(h1), rsi(h1.close)
        mid, sd = h1.close.rolling(20).mean(), h1.close.rolling(20).std()
        x["bbm"], x["bbu"], x["bbl"] = mid, mid + 2 * sd, mid - 2 * sd
        x["bbw"] = (4 * sd / mid)
        x["bbw_pct"] = x.bbw.rolling(120).rank(pct=True)
        x["atr_pct"] = x.atr.rolling(500).rank(pct=True)
        x["dh"], x["dl"] = h1.high.rolling(20).max().shift(1), h1.low.rolling(20).min().shift(1)
        # VWAP harian ~ rata-rata harga tipikal sejak awal hari (volume tidak tersedia di semua sumber)
        tp = (h1.high + h1.low + h1.close) / 3
        x["vwap"] = tp.groupby(h1.index.floor("D")).expanding().mean().reset_index(level=0, drop=True)
        up4 = (h4.close > ema(h4.close, 50)).astype(float)
        upd = (d1.close > ema(d1.close, 200)).astype(float)
        x["up4"] = htf_on(up4, h1.index, "4h")
        x["upd"] = htf_on(upd, h1.index, "D")
        x["adx4"] = htf_on(adx(h4), h1.index, "4h")
        # struktur H4: dua swing high & dua swing low terakhir naik/turun (fraktal 2 kiri 2 kanan, dikonfirmasi)
        sh = h4.high[(h4.high == h4.high.rolling(5, center=True).max())]
        sl = h4.low[(h4.low == h4.low.rolling(5, center=True).min())]
        sh.index, sl.index = sh.index + pd.Timedelta(hours=12), sl.index + pd.Timedelta(hours=12)   # baru diketahui 2 bar kemudian
        hh = (sh > sh.shift(1)).astype(float).reindex(h1.index, method="ffill")
        hl = (sl > sl.shift(1)).astype(float).reindex(h1.index, method="ffill")
        x["bull4"] = (hh == 1) & (hl == 1)
        x["bear4"] = (hh == 0) & (hl == 0)
        self.x = x
        self.j_next_h1 = np.searchsorted(b.index.asi8, (h1.index + pd.Timedelta(hours=1)).asi8)   # bar M15 pertama setelah H1 selesai
        self.year = b.index.year.to_numpy()


def sinyal(D: Data) -> dict[str, list]:
    """Setiap strategi → daftar (j0 M15, arah, harga SL, target alami atau None)."""
    x = D.x
    o, h, l, c = x.o.to_numpy(), x.h.to_numpy(), x.l.to_numpy(), x.c.to_numpy()
    at, ad, rs = x.atr.to_numpy(), x.adx.to_numpy(), x.rsi.to_numpy()
    e20, e50, e200 = x.e20.to_numpy(), x.e50.to_numpy(), x.e200.to_numpy()
    bbu, bbl, bbm = x.bbu.to_numpy(), x.bbl.to_numpy(), x.bbm.to_numpy()
    dh, dl, vw = x.dh.to_numpy(), x.dl.to_numpy(), x.vwap.to_numpy()
    jn = D.j_next_h1
    n = len(x)
    S: dict[str, list] = {k: [] for k in ("1 tren+pullback", "2 breakout+retest", "3 sweep+MSS", "4 mean reversion BB",
                                         "5 momentum expansion", "6 sesi London", "7 VWAP reversion", "8 MTF struktur",
                                         "9 ATR breakout")}

    def add(k, i, d, sl, tgt=None):
        if i + 1 < n and jn[i] < D.a.n - 2 and np.isfinite(sl) and at[i] > 0:
            S[k].append((int(jn[i]), d, float(sl), tgt))

    brk_up = brk_dn = -99
    lvl_up = lvl_dn = np.nan
    for i in range(220, n):
        a = at[i]
        # 1 tren + pullback ke EMA20 + candle konfirmasi
        if e50[i] > e200[i] and ad[i] > 20 and l[i] <= e20[i] < c[i] and c[i] > o[i]:
            add("1 tren+pullback", i, 1, c[i] - 1.5 * a)
        elif e50[i] < e200[i] and ad[i] > 20 and h[i] >= e20[i] > c[i] and c[i] < o[i]:
            add("1 tren+pullback", i, -1, c[i] + 1.5 * a)
        # 2 breakout Donchian 20 lalu retest ≤ 10 bar dengan rejection
        if c[i] > dh[i]:
            brk_up, lvl_up = i, dh[i]
        if c[i] < dl[i]:
            brk_dn, lvl_dn = i, dl[i]
        if 0 < i - brk_up <= 10 and l[i] <= lvl_up + 0.2 * a and c[i] > lvl_up and c[i] > o[i]:
            add("2 breakout+retest", i, 1, min(l[i], lvl_up) - 0.5 * a)
            brk_up = -99
        if 0 < i - brk_dn <= 10 and h[i] >= lvl_dn - 0.2 * a and c[i] < lvl_dn and c[i] < o[i]:
            add("2 breakout+retest", i, -1, max(h[i], lvl_dn) + 0.5 * a)
            brk_dn = -99
        # 3 sweep low 20 bar + tutup kembali di atas, lalu MSS (tutup > tertinggi 5 bar sebelum sweep) ≤ 6 bar
        for back in range(1, 7):
            s = i - back
            if l[s] < dl[s] and c[s] > dl[s] and c[i] > max(h[s - 5:s]) and c[i - 1] <= max(h[s - 5:s]):
                add("3 sweep+MSS", i, 1, min(l[s:i + 1]) - 0.2 * a)
                break
            if h[s] > dh[s] and c[s] < dh[s] and c[i] < min(l[s - 5:s]) and c[i - 1] >= min(l[s - 5:s]):
                add("3 sweep+MSS", i, -1, max(h[s:i + 1]) + 0.2 * a)
                break
        # 4 mean reversion BB saat ADX rendah: bar lalu di luar band + RSI ekstrem, bar ini kembali masuk + rejection
        if ad[i] < 20 and c[i - 1] < bbl[i - 1] and rs[i - 1] < 30 and c[i] > bbl[i] and c[i] > o[i]:
            add("4 mean reversion BB", i, 1, min(l[i - 1], l[i]) - 0.5 * a, bbm[i])
        elif ad[i] < 20 and c[i - 1] > bbu[i - 1] and rs[i - 1] > 70 and c[i] < bbu[i] and c[i] < o[i]:
            add("4 mean reversion BB", i, -1, max(h[i - 1], h[i]) + 0.5 * a, bbm[i])
        # 5 momentum expansion: squeeze (lebar BB ≤ persentil 20 dalam 5 bar terakhir) lalu tembus band, range > 1,2 ATR
        if x.bbw_pct.iat[i - 1] <= 0.2 and (h[i] - l[i]) > 1.2 * a:
            if c[i] > bbu[i]:
                add("5 momentum expansion", i, 1, c[i] - 1.5 * a)
            elif c[i] < bbl[i]:
                add("5 momentum expansion", i, -1, c[i] + 1.5 * a)
        # 7 VWAP reversion: jauh dari VWAP (> 2 ATR) + structure shift (tutup lewati high/low bar lalu)
        if c[i] < vw[i] - 2 * a and c[i] > h[i - 1]:
            add("7 VWAP reversion", i, 1, min(l[i - 2:i + 1]) - 0.3 * a, vw[i])
        elif c[i] > vw[i] + 2 * a and c[i] < l[i - 1]:
            add("7 VWAP reversion", i, -1, max(h[i - 2:i + 1]) + 0.3 * a, vw[i])
        # 9 ATR volatility breakout: candle H1 bergerak > 1 ATR dari close sebelumnya
        if c[i] - c[i - 1] > 1.0 * a:
            add("9 ATR breakout", i, 1, c[i] - 1.5 * a)
        elif c[i - 1] - c[i] > 1.0 * a:
            add("9 ATR breakout", i, -1, c[i] + 1.5 * a)
    sesi_mtf(D, S)
    return S


def sesi_mtf(D: Data, S: dict) -> None:
    """#6 London breakout dari range Asia (M15) dan #8 MTF (bias H4 HH/HL, pullback H1 di bawah EMA20, MSS M15)."""
    b = D.b
    o, h, l, c = D.a.o, D.a.h, D.a.l, D.a.c
    t = b.index
    hr = t.hour.to_numpy()
    day = t.floor("D").asi8
    x = D.x
    # nilai H1 yang sudah selesai untuk tiap bar M15
    def h1v(col):
        return x[col].shift(1).reindex(t.floor("h")).ffill().to_numpy()
    atr1, e20, bull, bear = h1v("atr"), h1v("e20"), h1v("bull4"), h1v("bear4")
    asia_hi = asia_lo = np.nan
    cur_day, done = None, False
    for j in range(200, len(b) - 2):
        if day[j] != cur_day:
            cur_day, done = day[j], False
            k = j
            hi, lo = -np.inf, np.inf
            while k < len(b) and day[k] == cur_day and hr[k] < 7:
                hi, lo = max(hi, h[k]), min(lo, l[k])
                k += 1
            asia_hi, asia_lo = (hi, lo) if np.isfinite(hi) else (np.nan, np.nan)
        # 6 London (07–10 UTC): close M15 pertama di luar range Asia, SL di tengah range
        if not done and 7 <= hr[j] < 10 and np.isfinite(asia_hi) and (asia_hi - asia_lo) > 0:
            mid = (asia_hi + asia_lo) / 2
            if c[j] > asia_hi:
                S["6 sesi London"].append((j + 1, 1, mid, None))
                done = True
            elif c[j] < asia_lo:
                S["6 sesi London"].append((j + 1, -1, mid, None))
                done = True
        # 8 MTF: bias H4, harga di sisi "pullback" EMA20 H1, MSS M15 = tutup lewati tertinggi/terendah 5 bar
        a = atr1[j]
        if not np.isfinite(a) or a <= 0:
            continue
        if bull[j] == 1 and c[j] < e20[j] and c[j] > h[j - 5:j].max() and c[j - 1] <= h[j - 6:j - 1].max():
            S["8 MTF struktur"].append((j + 1, 1, c[j] - 1.5 * a, None))
        elif bear[j] == 1 and c[j] > e20[j] and c[j] < l[j - 5:j].min() and c[j - 1] >= l[j - 6:j - 1].min():
            S["8 MTF struktur"].append((j + 1, -1, c[j] + 1.5 * a, None))


def jalankan(D: Data, sig: list, keluar: str, sp: float = SP, saring=None) -> pd.DataFrame:
    a = D.a
    rows, busy = [], -1
    for j0, d, sl, tgt in sorted(sig, key=lambda z: z[0]):
        if j0 <= busy or j0 >= a.n - 2:
            continue
        if saring is not None and not saring(j0, d):
            continue
        entry = a.o[j0] + (sp if d > 0 else 0.0)
        risk = (entry - sl) * d
        if risk <= 0 or risk > 50:
            continue
        if keluar == "F":
            ja, ra = simulate(a, sp, j0, d, entry, sl, entry + d * risk, HOLD)
            jb, rb = simulate(a, sp, j0, d, entry, sl, entry + d * 2 * risk, HOLD, be_at=1.0)
            j1, r = max(ja, jb), (ra + rb) / 2
        else:
            if keluar == "alami":
                if tgt is None or (tgt - entry) * d <= 0:
                    continue
                tp = tgt
            else:
                tp = entry + d * {"2R": 2.0, "1R": 1.0, "0,5R": 0.5, "3R": 3.0}[keluar] * risk
            j1, r = simulate(a, sp, j0, d, entry, sl, tp, HOLD)
        rows.append((j0, j1, d, r))
        busy = j1
    t = pd.DataFrame(rows, columns=["j0", "j1", "d", "R"])
    t["time"] = D.b.index[t.j0.to_numpy()]
    return t


def ringkas(t: pd.DataFrame) -> dict:
    out = {}
    for lab, sel in (("L", t.time < SPLIT), ("B", t.time >= SPLIT)):
        r = t.R[sel].to_numpy()
        n = len(r)
        out[f"{lab}_n"] = n
        out[f"{lab}_wr"] = 100 * (r > 0).mean() if n else 0.0
        out[f"{lab}_avg"] = r.mean() if n else 0.0
        out[f"{lab}_t"] = r.mean() / r.std(ddof=1) * np.sqrt(n) if n > 2 and r.std() > 0 else 0.0
        out[f"{lab}_pf"] = r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else 0.0
        yrs = pd.Series(r, index=t.time[sel].dt.year).groupby(level=0).sum()
        out[f"{lab}_th"] = (yrs > 0).mean() if len(yrs) else 0.0
        cum = np.r_[0, np.cumsum(r)]
        out[f"{lab}_dd"] = (np.maximum.accumulate(cum) - cum).max()
    return out


def main() -> None:
    D = Data()
    S = sinyal(D)
    x = D.x
    up4 = x.up4.shift(0).reindex(D.b.index.floor("h")).ffill().to_numpy()      # sudah bar selesai (htf_on)
    upd = x.upd.reindex(D.b.index.floor("h")).ffill().to_numpy()
    adx4 = x.adx4.reindex(D.b.index.floor("h")).ffill().to_numpy()
    atrp = x.atr_pct.shift(1).reindex(D.b.index.floor("h")).ffill().to_numpy()

    def tren2(j, d):
        return (d > 0 and up4[j] == 1 and upd[j] == 1) or (d < 0 and up4[j] == 0 and upd[j] == 0)

    rows = []
    for nama, sig in S.items():
        exits = ["2R", "1R", "0,5R", "F"] + (["alami"] if nama[0] in "47" else [])
        for ke in exits:
            for fl, fn in (("-", None), ("tren2", tren2)):
                t = jalankan(D, sig, ke, saring=fn)
                r = dict(strategi=nama, keluar=ke, filter=fl, **ringkas(t))
                t2 = jalankan(D, sig, ke, sp=2 * SP, saring=fn)
                r["L_sp2"], r["B_sp2"] = t2.R[t2.time < SPLIT].mean(), t2.R[t2.time >= SPLIT].mean()
                rows.append(r)
        print(nama, len(sig), flush=True)

    # 10 regime switching: tren (ADX H4 > 25) → #1 & #9 searah tren2; range (ADX H4 < 20) → #4; volatil (ATR > persentil 90) → tidak
    def rezim(nama):
        def f(j, d):
            if atrp[j] > 0.9:
                return False
            if nama[0] in "19":
                return adx4[j] > 25 and tren2(j, d)
            return adx4[j] < 20
        return f
    for ke in ("2R", "1R", "F"):
        rr = []
        for nama in ("1 tren+pullback", "9 ATR breakout", "4 mean reversion BB"):
            rr.append(jalankan(D, S[nama], ke, saring=rezim(nama)))
        t = pd.concat(rr).sort_values("time")
        rows.append(dict(strategi="10 regime switching (1+9 tren, 4 range)", keluar=ke, filter="rezim", **ringkas(t),
                         L_sp2=np.nan, B_sp2=np.nan))
    res = pd.DataFrame(rows)
    res.to_csv(OUT.with_suffix(".csv"), index=False, float_format="%.4f")
    fmt = lambda v: f"{v:.2f}"  # noqa: E731
    cols = ["strategi", "keluar", "filter", "L_n", "L_wr", "L_avg", "L_t", "L_th", "B_n", "B_wr", "B_avg", "B_t", "B_th",
            "B_pf", "B_dd", "L_sp2", "B_sp2"]
    lolos = res[(res.L_n >= 100) & (res.L_avg > 0) & (res.L_t >= 2) & (res.L_th >= 0.7)]
    out = [f"{len(res)} kombinasi (strategi × cara keluar × filter). Spread ${SP}; R per trade; satu posisi per strategi.",
           f"Lolos seleksi LAMA (n ≥ 100, rata-rata > 0, t ≥ 2, ≥ 70% tahun +): {len(lolos)}"]
    if len(lolos):
        out.append(lolos.sort_values("L_t", ascending=False)[cols].to_string(index=False, float_format=fmt))
        ok = lolos[(lolos.B_avg > 0) & (lolos.B_t >= 1.5)]
        out.append(f"\nLolos LAMA dan positif di BARU (t ≥ 1,5): {len(ok)}")
        if len(ok):
            out.append(ok[cols].to_string(index=False, float_format=fmt))
    out.append("\nWin rate ≥ 60% di LAMA dan BARU:")
    hw = res[(res.L_wr >= 60) & (res.B_wr >= 60)].sort_values("B_avg", ascending=False)
    out.append(hw[cols].to_string(index=False, float_format=fmt) if len(hw) else "  (tidak ada)")
    out.append("\nSemua (urut rata-rata BARU):")
    out.append(res.sort_values("B_avg", ascending=False)[cols].to_string(index=False, float_format=fmt))
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[:40]))
    print("->", OUT)


if __name__ == "__main__":
    main()
