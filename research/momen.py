"""Momen entry, mode perang Timur Tengah, dan skema SL+ per periode (python -m research.momen).

Aturan penilaian (ditetapkan sebelum melihat hasil):
- Periode LAMA = sebelum 2021-10-01 (XAU 2012-11.., BTC 2016..), BARU = 5 tahun terakhir 2021-10-01 .. 2026-09.
- Sinyal 💰 = mesin cloud (research/rekomendasi.trades); sinyal kembar = 1 entry, hasil set paling lambat.
- Ciri numerik dibagi 3 (tertil) dengan batas dari periode LAMA saja. "Momen terbaik" = tertil dengan rata-rata R
  tertinggi di LAMA; lalu dinilai di BARU. KONSISTEN bila: (a) tertil itu > dasar di LAMA dan BARU, (b) >= 60%
  tahun tertil itu > sisanya, (c) p-acak (5.000 undian kelompok acak berukuran sama) < 0,05 di seluruh data.
  Banyak ciri diuji -> satu dua lolos bisa kebetulan; yang lolos baru dipakai bila juga masuk akal.
- Data eksternal dipakai sejak waktu terbitnya (research/eksternal.asof): OVX (FRED OVXCLS, volatilitas minyak),
  WTI (FRED DCOILWTICO).
- Mode perang: (1) OVX >= persentil 80 setahun terakhir, (2) minyak naik >= 10% dalam 10 hari bursa,
  (3) jendela 30 hari setelah eskalasi Timur Tengah besar (daftar EPISODE; deskriptif, tanggal kejadian diketahui
  sesudahnya -> bukan aturan trading).
Tidak ada perubahan bot live / cloud. Simulasi historis, bukan jaminan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import asof, asset
from .eksternal_makro import fred
from .rekomendasi import BTC_SWAP_LONG_DAY, entries, swap_r, trades
from .strategy_lab import ema

NEW = pd.Timestamp("2021-10-01", tz="UTC")
EPISODE = {                      # eskalasi Timur Tengah besar (tanggal mulai)
    "2019-09-14": "serangan kilang Abqaiq (Saudi)",
    "2020-01-03": "Soleimani tewas, Iran balas serang pangkalan AS",
    "2023-10-07": "serangan Hamas, perang Israel–Gaza",
    "2024-04-13": "Iran serang Israel (drone & rudal)",
    "2024-10-01": "Iran serang Israel (rudal balistik)",
    "2025-06-13": "perang Israel–Iran 12 hari, AS serang situs nuklir 22 Jun",
}


def period(t: pd.Series) -> np.ndarray:
    return np.where(t >= NEW, "BARU", "LAMA")


def base_entries(name: str, be_at=None) -> pd.DataFrame:
    """Entry 💰 (kembar = 1) + ukuran kembar; BTC: tanpa September (filter cloud) dan sesudah swap."""
    per_set = trades(name, be_at=be_at)
    size = per_set.groupby(["t", "dir"]).size().rename("kembar")
    e = entries(per_set).merge(size, on=["t", "dir"])
    if name == "BTCUSD":
        e = e[e.t.dt.month != 9].copy()
        e["R"] = e.R - swap_r(e, name, BTC_SWAP_LONG_DAY, 0.0)
    e["per"] = period(e.t)
    return e.reset_index(drop=True)


def line(r: pd.Series) -> str:
    return f"n={len(r):4d} WR={100 * (r > 0).mean():4.1f}% rata={r.mean():+.3f}R total={r.sum():+7.1f}R"


# ------------------------------------------------------------------ 1. skema SL+ per periode
def schemes():
    print("## 1. Skema SL+ di sinyal 💰: LAMA vs 5 tahun terakhir\n")
    for n in ("XAUUSD", "BTCUSD"):
        for tag, be in (("TP1 lalu SL+ di entry, tahan sampai TUTUP", None), ("SL+ saat profit 0,7R", 0.7)):
            e = base_entries(n, be)
            parts = " | ".join(f"{p}: {line(e.R[e.per == p])}" for p in ("LAMA", "BARU"))
            print(f"{n} {tag:44s} {parts}")
    print()


# ------------------------------------------------------------------ 2. ciri momen entry
def features(name: str, e: pd.DataFrame, macro: dict) -> dict[str, np.ndarray]:
    b = asset(name).b
    i = e.i.to_numpy()
    d = e.dir.to_numpy()
    c, h, l, a = b.c, b.h, b.l, b.atr
    e50, e200 = ema(c, 50), ema(c, 200)
    cross = np.r_[0, np.flatnonzero(np.diff(np.sign(e50 - e200)) != 0) + 1]
    age = i - cross[np.searchsorted(cross, i, side="right") - 1]
    hi55 = pd.Series(h).rolling(55).max().shift(1).to_numpy()
    lo55 = pd.Series(l).rolling(55).min().shift(1).to_numpy()
    rank = pd.Series(a).rolling(24 * 60, min_periods=500).rank(pct=True).to_numpy()
    tr = pd.Series(np.maximum(h - l, np.maximum(abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]]))))
    up, dn = pd.Series(h).diff(), -pd.Series(l).diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0))
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0))
    at14 = tr.ewm(alpha=1 / 14).mean()
    pdi, ndi = 100 * pdm.ewm(alpha=1 / 14).mean() / at14, 100 * ndm.ewm(alpha=1 / 14).mean() / at14
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1 / 14).mean().to_numpy()
    dd, _ = b.daily()
    mom = (dd.close / dd.close.shift(60) - 1).shift(1).reindex(b.t.normalize()).to_numpy()
    # hasil entry 💰 sebelumnya yang SUDAH tutup sebelum entry ini
    prev = np.full(len(e), np.nan)
    closed = e.sort_values("t_out")
    for k, t in enumerate(e.t):
        done = closed[closed.t_out <= t]
        if len(done):
            prev[k] = done.R.iloc[-1]
    t = pd.DatetimeIndex(e.t)
    ovx, oil = macro["OVXCLS"], macro["DCOILWTICO"]
    ovx_pct = ovx.value.rolling(252, min_periods=120).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    oil10 = oil.value / oil.value.shift(10) - 1
    return {
        "kembar (jumlah set sinyal sama)": e.kembar.to_numpy(float),
        "volatilitas ATR (persentil 60 hari)": rank[i],
        "ADX H1 (kekuatan tren)": adx[i],
        "badan candle sinyal / ATR": np.abs(c[i] - b.o[i]) / a[i],
        "lebar konsolidasi 55 candle / ATR": (hi55[i] - lo55[i]) / a[i],
        "umur tren (candle sejak EMA50×200)": age.astype(float),
        "jarak dari EMA50 H1 / ATR (searah)": d * (c[i] - e50[i]) / a[i],
        "momentum D1 60 hari (searah)": d * mom[i],
        "jam UTC sinyal": b.t[i].hour.to_numpy(float),
        "hasil entry 💰 sebelumnya (R)": prev,
        "OVX volatilitas minyak (persentil 1 th)": asof(t, ovx_pct, pd.DatetimeIndex(ovx.available)),
        "minyak WTI 10 hari (%)": asof(t, oil10, pd.DatetimeIndex(oil.available)),
        "hari (0=Senin)": b.t[i].dayofweek.to_numpy(float),
    }


def perm_p(r: np.ndarray, mask: np.ndarray, n: int = 5000, seed: int = 11) -> float:
    rng = np.random.default_rng(seed)
    k = int(mask.sum())
    if k == 0 or k == len(r):
        return 1.0
    obs = r[mask].mean()
    sims = np.array([r[rng.choice(len(r), k, replace=False)].mean() for _ in range(n)])
    return float((sims >= obs).mean())


def judge_feature(e: pd.DataFrame, x: np.ndarray, name: str) -> tuple[str, bool, np.ndarray | None]:
    ok = ~np.isnan(x)
    old = ok & (e.per.to_numpy() == "LAMA")
    if old.sum() < 60:
        return f"{name}: data kurang", False, None
    uniq = np.unique(x[ok])
    if len(uniq) <= 4:                                   # kategori kecil (mis. kembar 1/2/3)
        groups = [(f"={u:g}", x == u) for u in uniq]
    else:
        q1, q2 = np.quantile(x[old], [1 / 3, 2 / 3])
        groups = [(f"<{q1:.3g}", ok & (x < q1)), (f"{q1:.3g}–{q2:.3g}", ok & (x >= q1) & (x < q2)),
                  (f">={q2:.3g}", ok & (x >= q2))]
    r = e.R.to_numpy()
    per = e.per.to_numpy()
    cells = []
    best, best_v = None, -9.0
    for lab, m in groups:
        vo, vn = r[m & (per == "LAMA")], r[m & (per == "BARU")]
        cells.append(f"{lab}: LAMA {vo.mean() if len(vo) else np.nan:+.2f}R ({len(vo)}) BARU "
                     f"{vn.mean() if len(vn) else np.nan:+.2f}R ({len(vn)})")
        if len(vo) >= 30 and vo.mean() > best_v:
            best, best_v = (lab, m), vo.mean()
    lab, m = best
    base_o, base_n = r[per == "LAMA"].mean(), r[per == "BARU"].mean()
    bo, bn = r[m & (per == "LAMA")], r[m & (per == "BARU")]
    yrs = e.t.dt.year.to_numpy()
    wins = tot = 0
    for y in np.unique(yrs):
        a_, b_ = r[m & (yrs == y)], r[~m & ok & (yrs == y)]
        if len(a_) >= 3 and len(b_) >= 3:
            tot += 1
            wins += a_.mean() > b_.mean()
    p = perm_p(r[ok], m[ok])
    good = len(bn) >= 20 and bo.mean() > base_o and bn.mean() > base_n and tot and wins / tot >= 0.6 and p < 0.05
    txt = (f"{name}\n   " + "\n   ".join(cells) +
           f"\n   -> momen terbaik (dipilih di LAMA) {lab}: BARU {bn.mean():+.3f}R vs dasar {base_n:+.3f}R, "
           f"tahun menang {wins}/{tot}, p={p:.3f} => {'KONSISTEN' if good else 'tidak konsisten'}")
    return txt, bool(good), m


def curve(pct: pd.Series) -> tuple[float, float]:
    eq = pct.sort_index().cumsum()
    yrs = max((eq.index.max() - eq.index.min()).days / 365.25, 1e-9)
    return eq.iloc[-1] / yrs, (eq.cummax().clip(lower=0) - eq).max()


def moments(macro: dict) -> dict:
    print("## 2. Momen entry (ciri di candle sinyal) — dipilih di LAMA, dinilai di 5 tahun terakhir\n")
    found = {}
    for n in ("XAUUSD", "BTCUSD"):
        e = base_entries(n)
        print(f"### {n}: dasar LAMA {line(e.R[e.per == 'LAMA'])} | BARU {line(e.R[e.per == 'BARU'])}\n")
        for fname, x in features(n, e, macro).items():
            txt, good, m = judge_feature(e, x, fname)
            print(txt)
            if good:
                found[(n, fname)] = (e, m)
        print()
    for (n, fname), (e, m) in found.items():
        print(f"Ukuran lot {n} '{fname}': 0,5% di momen terbaik, 0,25% lainnya vs rata 0,5%")
        for p in ("LAMA", "BARU"):
            s = e.per.to_numpy() == p
            flat = pd.Series(0.5 * e.R.to_numpy()[s], index=e.t_out[s])
            tier = pd.Series(np.where(m, 0.5, 0.25)[s] * e.R.to_numpy()[s], index=e.t_out[s])
            (fy, fd), (ty, td) = curve(flat), curve(tier)
            print(f"   {p}: rata {fy:+.1f}%/th DD {fd:.1f}% rasio {fy / fd:.2f} | momen {ty:+.1f}%/th DD {td:.1f}% "
                  f"rasio {ty / td:.2f}")
    return found


# ------------------------------------------------------------------ 3. mode perang
def war(macro: dict):
    print("\n## 3. Mode perang Timur Tengah\n")
    ovx, oil = macro["OVXCLS"], macro["DCOILWTICO"]
    ovx_pct = ovx.value.rolling(252, min_periods=120).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    oil10 = oil.value / oil.value.shift(10) - 1
    for n in ("XAUUSD", "BTCUSD"):
        e = base_entries(n)
        t = pd.DatetimeIndex(e.t)
        modes = {
            "OVX >= P80 setahun": asof(t, ovx_pct, pd.DatetimeIndex(ovx.available)) >= 0.8,
            "minyak naik >= 10% dalam 10 hari": asof(t, oil10, pd.DatetimeIndex(oil.available)) >= 0.10,
        }
        ep = np.zeros(len(e), bool)
        for d0 in EPISODE:
            s = pd.Timestamp(d0, tz="UTC")
            ep |= (t >= s) & (t < s + pd.Timedelta(days=30))
        modes["30 hari setelah eskalasi (deskriptif)"] = ep
        for tag, m in modes.items():
            m = np.asarray(m, bool)
            cells = []
            for p in ("LAMA", "BARU"):
                s = e.per.to_numpy() == p
                cells.append(f"{p} perang {line(e.R[m & s])} | normal rata {e.R[~m & s].mean():+.3f}R")
            print(f"{n} {tag}:\n   " + "\n   ".join(cells))
        # per episode
        for d0, what in EPISODE.items():
            s = pd.Timestamp(d0, tz="UTC")
            w = (t >= s) & (t < s + pd.Timedelta(days=30))
            print(f"   {d0} {what}: {int(w.sum())} entry, {e.R[w].sum():+.2f}R")
    # OVX & minyak per bulan 2026 (apa yang terjadi beberapa bulan ini)
    print("\nOVX & WTI per bulan 2025–2026 (rata-rata bulanan, FRED):")
    mo = pd.DataFrame({"OVX": ovx.value, "WTI": oil.value}).loc["2025-01-01":].resample("MS").mean().round(1)
    print(mo.T.to_string())


# ------------------------------------------------------------------ 4. hasil bulanan 2026
def recent():
    print("\n## 4. Sinyal 💰 per bulan 2025–2026\n")
    for n in ("XAUUSD", "BTCUSD"):
        e = base_entries(n)
        e = e[e.t >= pd.Timestamp("2025-01-01", tz="UTC")]
        g = e.groupby(e.t.dt.strftime("%Y-%m")).R.agg(["count", "sum"])
        print(f"{n}: " + ", ".join(f"{k} {int(v['count'])}×{v['sum']:+.1f}R" for k, v in g.iterrows()))


def main():
    print("# Momen entry, mode perang, skema SL+ (research/momen.py)\n")
    macro = {s: fred(s) for s in ("OVXCLS", "DCOILWTICO")}
    schemes()
    moments(macro)
    war(macro)
    recent()


if __name__ == "__main__":
    main()
