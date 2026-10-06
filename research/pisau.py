"""Tangkap pisau jatuh: entry BUY (balik) atau SELL (lanjut) setelah XAU/kripto jatuh/melonjak cepat.

python -m research.pisau            # semua aset, tulis docs/eksternal/hasil_pisau.txt
Permintaan pengguna (6 Okt 2026): "saat XAU atau koin jatuh bisakah kita menangkap pisau itu untuk entry buy/sell?
Seperti sekarang XAU lagi jatuh. Uji validasi, keluarkan seluruh kemampuan."

Literatur (dipakai sebagai hipotesis, bukan bukti): Caporale & Plastun (kripto) — pada hari overreaction harga cenderung
LANJUT searah (momentum), hari berikutnya kadang berbalik; Bitcoin: overreaction sesudah guncangan negatif per jam.
Untuk emas intraday hampir tidak ada studi → diuji dua arah.

Metode (H1, tanpa look-ahead; keputusan di close candle t, entry paling cepat di open t+1):
  * Kejadian "jatuh": (high tertinggi N candle terakhir − close) ≥ k × ATR24; "melonjak": kebalikannya. Hanya
    kejadian pertama (tidak aktif di candle sebelumnya) + jeda N candle. N ∈ {3,6,12,24,48}, k ∈ {3,4,5,6,8}.
  * Arah: "balik" (BUY setelah jatuh / SELL setelah melonjak) atau "lanjut" (SELL setelah jatuh / BUY setelah melonjak).
  * Entry balik: pasar, konfirmasi (candle pertama yang close > high candle sebelumnya, ≤ 6 candle), limit lebih dalam
    0,5/1/1,5 ATR (berlaku 12 candle). Entry lanjut: pasar, pullback limit 25%/50% dari gerakan, stop order tembus
    ujung candle kejadian.
  * Keluar: SL 1/1,5/2/3 ATR, TP 0,5/1/1,5/2/3 ATR atau balik 38%/50% gerakan, batas 6/12/24/48 candle. SL dicek dulu,
    TP tidak dihitung di candle pengisian, gap melewati SL diisi di open (konservatif, sama dengan research/harness).
  * Filter tren besar: semua / searah EMA H1 1200 (±50 hari) / melawan.
  * Biaya: XAU spread $0,30 + slip $0,20 (pasar cepat); BTC/ETH CFD 0,06% pulang-pergi; koin spot (BUY saja) 0,30%.
  * Validasi: pilih HANYA dari LAMA (< Okt 2021), lihat BARU; pembanding entry acak di jam mana pun dengan arah,
    filter & aturan keluar yang sama (supaya untung karena tren emas 2024–2026 tidak dikira keunggulan); per tahun;
    tetangga parameter; spread ×2.
"""
from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .strategy_lab import atr as _atr
from .strategy_lab import ema

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pisau.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
NS, KS = (3, 6, 12, 24, 48), (3, 4, 5, 6, 8)
SLS, TPS, HS = (1.0, 1.5, 2.0, 3.0), (0.5, 1.0, 1.5, 2.0, 3.0, "r38", "r50"), (6, 12, 24, 48)
HMAX = max(HS)
COINS = ["ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "AVAX", "DOT", "LTC", "BCH", "XLM", "ATOM",
         "ETC", "UNI", "NEAR", "AAVE", "FIL"]


@dataclass
class Series:
    name: str
    t: pd.DatetimeIndex
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray  # noqa: E741
    c: np.ndarray
    atr: np.ndarray
    trend: np.ndarray          # +1 di atas EMA 1200, -1 di bawah
    cost: float                # biaya pulang-pergi dalam harga (absolut) — diterapkan saat entry
    pct: bool                  # biaya dalam persen harga
    buy_only: bool = False


def make(name: str, df: pd.DataFrame, cost: float, pct: bool, buy_only: bool = False) -> Series:
    df = df[(df.high > df.low) & (df.close > 0)]
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))  # noqa: E741
    a = _atr(h, l, c, 24)
    tr = np.where(c > ema(c, 1200), 1, -1)
    return Series(name, df.index, o, h, l, c, a, tr, cost, pct, buy_only)


def load() -> list[Series]:
    from .pair_data import _dir
    from .strategy_lab import markets
    m = {x.name: x for x in markets()}
    out = [make("XAU", m["XAUUSD"].h1, 0.50, False), make("BTC", m["BTCUSD"].h1, 0.0006, True)]
    out.append(make("ETH", pd.read_parquet(_dir() / "ETHUSD.parquet"), 0.0006, True))
    return out


def load_coins() -> list[Series]:
    from .pair_data import _dir
    from .strategy_lab import markets
    m = {x.name: x for x in markets()}
    out = [make("BTC", m["BTCUSD"].h1, 0.003, True, True)]
    for c in COINS:
        f = _dir() / f"{c}USD.parquet"
        if f.exists():
            out.append(make(c, pd.read_parquet(f), 0.003, True, True))
    return out


# ------------------------------------------------------------------ kejadian
def events(s: Series, n: int, k: float, move: int) -> np.ndarray:
    """Index candle t (close) kejadian pertama. move=-1 jatuh, +1 melonjak."""
    if move < 0:
        ext = pd.Series(s.h).rolling(n, min_periods=n).max().to_numpy()
        size = (ext - s.c) / s.atr
    else:
        ext = pd.Series(s.l).rolling(n, min_periods=n).min().to_numpy()
        size = (s.c - ext) / s.atr
    on = size >= k
    prev = np.r_[False, on[:-1]]
    idx = np.where(on & ~prev)[0]
    out, last = [], -10 ** 9
    for i in idx:
        if i - last >= n and i > 1300 and i + HMAX + 15 < len(s.c):
            out.append(i)
            last = i
    return np.array(out, int)


# ------------------------------------------------------------------ entry
def entries(s: Series, ev: np.ndarray, n: int, move: int, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """-> (event index t, entry bar j0, entry price, dir). Harga bar = BID; BUY membayar biaya di entry."""
    rows = []
    for t in ev:
        a = s.atr[t]
        if move < 0:
            ext = s.h[t - n + 1:t + 1].max()
        else:
            ext = s.l[t - n + 1:t + 1].min()
        size = abs(ext - s.c[t])
        fade = mode.startswith("b_")          # b_ = balik, l_ = lanjut
        d = -move if fade else move
        j0 = px = None
        if mode in ("b_mkt", "l_mkt"):
            j0, px = t + 1, s.o[t + 1]
        elif mode == "b_konf":
            for j in range(t + 1, t + 7):
                up = s.c[j] > s.h[j - 1] if d > 0 else s.c[j] < s.l[j - 1]
                if up:
                    j0, px = j + 1, s.o[j + 1]
                    break
        elif mode.startswith("b_lim"):
            m = float(mode[5:])
            lim = s.c[t] - d * m * a
            for j in range(t + 1, t + 13):
                if (s.l[j] <= lim) if d > 0 else (s.h[j] >= lim):
                    j0 = j
                    px = min(s.o[j], lim) if d > 0 else max(s.o[j], lim)
                    break
        elif mode.startswith("l_pb"):
            r = float(mode[4:])
            lim = s.c[t] - d * r * size            # lanjut: SELL setelah jatuh -> limit di atas close
            for j in range(t + 1, t + 13):
                if (s.l[j] <= lim) if d > 0 else (s.h[j] >= lim):
                    j0 = j
                    px = min(s.o[j], lim) if d > 0 else max(s.o[j], lim)
                    break
        elif mode == "l_brk":
            stop = (s.h[t] + 0.1 * a) if d > 0 else (s.l[t] - 0.1 * a)
            for j in range(t + 1, t + 7):
                if (s.h[j] >= stop) if d > 0 else (s.l[j] <= stop):
                    j0 = j
                    px = max(s.o[j], stop) if d > 0 else min(s.o[j], stop)
                    break
        if j0 is None or j0 + HMAX + 2 >= len(s.c):
            continue
        rows.append((t, j0, px, d))
    if not rows:
        return (np.array([], int),) * 2 + (np.array([]), np.array([], int))
    r = np.array(rows, dtype=object)
    return r[:, 0].astype(int), r[:, 1].astype(int), r[:, 2].astype(float), r[:, 3].astype(int)


# ------------------------------------------------------------------ keluar (vektor)
def outcomes(s: Series, t: np.ndarray, j0: np.ndarray, px: np.ndarray, d: np.ndarray, move: int, n: int) -> dict:
    """R per trade untuk setiap (SL, TP, H). Biaya pulang-pergi dibebankan di harga entry."""
    if len(t) == 0:
        return {}
    a = s.atr[t]
    cost = s.cost * px if s.pct else np.full(len(t), s.cost)
    e = px + d * cost                                     # harga efektif setelah biaya
    off = np.arange(HMAX)
    idx = j0[:, None] + off[None, :]
    H, L, O, C = s.h[idx], s.l[idx], s.o[idx], s.c[idx]  # noqa: E741
    if move < 0:
        ext = np.array([s.h[i - n + 1:i + 1].max() for i in t])
    else:
        ext = np.array([s.l[i - n + 1:i + 1].min() for i in t])
    out = {}
    for sl in SLS:
        slp = (e - d * sl * a)[:, None]                       # harga SL
        hit_sl = np.where(d[:, None] > 0, L <= slp, H >= slp)
        sl_fill = np.where(d[:, None] > 0, np.minimum(O, slp), np.maximum(O, slp))
        sl_fill[:, 0] = slp[:, 0]
        for tp in TPS:
            if isinstance(tp, str):
                frac = 0.382 if tp == "r38" else 0.5
                tpp = np.where(d == -move, s.c[t] + (ext - s.c[t]) * frac, s.c[t] - (ext - s.c[t]) * frac)
                tpp = np.where((tpp - e) * d <= 0.1 * a, e + d * 0.1 * a, tpp)   # target sudah terlewati -> 0,1 ATR
            else:
                tpp = e + d * tp * a
            tpp = tpp[:, None]
            hit_tp = np.where(d[:, None] > 0, H >= tpp, L <= tpp)
            hit_tp[:, 0] = False
            for hh in HS:
                sl_any = hit_sl[:, :hh].any(1)
                tp_any = hit_tp[:, :hh].any(1)
                fs = np.where(sl_any, hit_sl[:, :hh].argmax(1), hh)
                ft = np.where(tp_any, hit_tp[:, :hh].argmax(1), hh)
                exit_px = C[:, hh - 1].copy()
                k = np.arange(len(t))
                use_sl = fs <= ft
                use_sl &= sl_any
                use_tp = tp_any & ~use_sl
                exit_px[use_sl] = sl_fill[k[use_sl], fs[use_sl]]
                exit_px[use_tp] = tpp[use_tp, 0]
                risk = sl * a
                out[(sl, tp, hh)] = ((exit_px - e) * d / risk,
                                     np.where(use_sl, fs, np.where(use_tp, ft, hh - 1)))
    return out


def summary(r: np.ndarray, times: pd.DatetimeIndex) -> dict:
    lama, baru = r[times < SPLIT], r[times >= SPLIT]

    def st(x):
        if len(x) == 0:
            return {"n": 0, "wr": np.nan, "avg": np.nan, "t": np.nan}
        sd = x.std(ddof=1) if len(x) > 1 else np.nan
        return {"n": len(x), "wr": (x > 0).mean() * 100, "avg": x.mean(),
                "t": x.mean() / (sd / np.sqrt(len(x))) if sd and sd > 0 else np.nan}
    yrs = pd.Series(r, index=times).groupby(times.year).mean()
    return {"lama": st(lama), "baru": st(baru), "thn_pos": (yrs > 0).mean() * 100, "thn": len(yrs)}


# ------------------------------------------------------------------ pembanding acak
def baseline(s: Series, d: int, trend_f: str, rng: np.random.Generator, size: int = 6000) -> dict:
    """Entry pasar di candle acak (open t+1) dengan arah & filter sama. TP retrace diganti TP 1 ATR."""
    cand = np.arange(1300, len(s.c) - HMAX - 15)
    if trend_f != "semua":
        want = d if trend_f == "searah" else -d
        cand = cand[s.trend[cand] == want]
    t = np.sort(rng.choice(cand, size=min(size, len(cand)), replace=False))
    j0 = t + 1
    px = s.o[j0]
    dd = np.full(len(t), d)
    res = outcomes(s, t, j0, px, dd, -d, 3)
    return {k: (v[0][s.t[t] < SPLIT].mean(), v[0][s.t[t] >= SPLIT].mean()) for k, v in res.items()}


MODES = ("b_mkt", "b_konf", "b_lim0.5", "b_lim1.0", "b_lim1.5", "l_mkt", "l_pb0.25", "l_pb0.5", "l_brk")


def scan(s: Series, rng) -> pd.DataFrame:
    rows = []
    base_cache = {}
    for move, n, k in itertools.product((-1, 1), NS, KS):
        ev = events(s, n, k, move)
        if len(ev) < 20:
            continue
        for mode in MODES:
            if s.buy_only and not ((move < 0 and mode.startswith("b_")) or (move > 0 and mode.startswith("l_"))):
                continue
            t, j0, px, d = entries(s, ev, n, move, mode)
            if len(t) < 20:
                continue
            for trend_f in ("semua", "searah", "melawan"):
                dirv = d[0]
                if trend_f == "semua":
                    keep = np.ones(len(t), bool)
                else:
                    want = dirv if trend_f == "searah" else -dirv
                    keep = s.trend[t] == want
                if keep.sum() < 15:
                    continue
                res = outcomes(s, t[keep], j0[keep], px[keep], d[keep], move, n)
                times = s.t[t[keep]]
                bk = (dirv, trend_f)
                if bk not in base_cache:
                    base_cache[bk] = baseline(s, dirv, trend_f, rng)
                for key, (r, _) in res.items():
                    sm = summary(r, times)
                    bl = base_cache[bk].get((key[0], 1.0 if isinstance(key[1], str) else key[1], key[2]))
                    rows.append({"aset": s.name, "gerak": "jatuh" if move < 0 else "lonjak", "N": n, "k": k,
                                 "mode": mode, "arah": "BUY" if dirv > 0 else "SELL", "tren": trend_f,
                                 "sl": key[0], "tp": key[1], "H": key[2],
                                 **{f"L_{a}": b for a, b in sm["lama"].items()},
                                 **{f"B_{a}": b for a, b in sm["baru"].items()},
                                 "thn_pos": sm["thn_pos"], "acakL": bl[0], "acakB": bl[1]})
    return pd.DataFrame(rows)


def neighbors_ok(df: pd.DataFrame, row) -> float:
    """Persen tetangga (N±1 langkah, k±1 langkah, SL/TP/H sama) yang LAMA & BARU positif."""
    ni, ki = NS.index(row.N), KS.index(row.k)
    nb = df[(df.aset == row.aset) & (df.gerak == row.gerak) & (df["mode"] == row["mode"]) & (df.tren == row.tren) &
            (df.sl == row.sl) & (df.tp == row.tp) & (df.H == row.H) &
            df.N.isin(NS[max(0, ni - 1):ni + 2]) & df.k.isin(KS[max(0, ki - 1):ki + 2]) &
            ~((df.N == row.N) & (df.k == row.k))]
    if nb.empty:
        return np.nan
    return ((nb.L_avg > 0) & (nb.B_avg > 0)).mean() * 100


def report(df: pd.DataFrame, title: str, L: list[str]) -> pd.DataFrame:
    L += ["", f"## {title}", f"Kombinasi diuji: {len(df)}"]
    # seleksi dari LAMA saja
    sel = df[(df.L_n >= 30) & (df.L_avg >= 0.10) & (df.L_t >= 2.0) & ((df.L_avg - df.acakL) >= 0.08)]
    passed = sel[(sel.B_n >= 15) & (sel.B_avg > 0)]
    strong = sel[(sel.B_n >= 15) & (sel.B_avg >= 0.10) & ((sel.B_avg - sel.acakB) >= 0.05) & (sel.thn_pos >= 70)]
    L.append(f"Lolos LAMA (n≥30, rata ≥ +0,10R, t ≥ 2, > acak +0,08R): {len(sel)} | tetap positif BARU: {len(passed)} | "
             f"kuat di BARU (≥ +0,10R, > acak +0,05R, ≥70% tahun +): {len(strong)}")
    for gerak in ("jatuh", "lonjak"):
        for arah in ("BUY", "SELL"):
            x = df[(df.gerak == gerak) & (df.arah == arah)]
            if x.empty:
                continue
            L.append(f"   {gerak} → {arah}: rata semua kombinasi LAMA {x.L_avg.mean():+.3f}R | BARU {x.B_avg.mean():+.3f}R | "
                     f"acak LAMA {x.acakL.mean():+.3f}R BARU {x.acakB.mean():+.3f}R")
    top = sel.sort_values("L_t", ascending=False).head(15)
    if len(top):
        L.append("15 teratas LAMA (dipilih tanpa melihat BARU):")
        for _, r in top.iterrows():
            L.append(f"   {r.aset} {r.gerak} N{r.N} k{r.k} {r['mode']} {r.arah} tren:{r.tren} SL{r.sl} TP{r.tp} H{r.H} | "
                     f"LAMA n{r.L_n:.0f} WR {r.L_wr:.0f}% {r.L_avg:+.2f}R (acak {r.acakL:+.2f}) | "
                     f"BARU n{r.B_n:.0f} WR {r.B_wr:.0f}% {r.B_avg:+.2f}R (acak {r.acakB:+.2f}) | thn+ {r.thn_pos:.0f}%")
    if len(strong):
        strong = strong.assign(tetangga=[neighbors_ok(df, r) for _, r in strong.iterrows()])
        L.append("Kandidat kuat (urut BARU − acak), tetangga = % parameter sekitar yang positif di dua periode:")
        for _, r in strong.sort_values("tetangga", ascending=False).head(20).iterrows():
            L.append(f"   {r.aset} {r.gerak} N{r.N} k{r.k} {r['mode']} {r.arah} tren:{r.tren} SL{r.sl} TP{r.tp} H{r.H} | "
                     f"LAMA n{r.L_n:.0f} WR {r.L_wr:.0f}% {r.L_avg:+.2f}R | BARU n{r.B_n:.0f} WR {r.B_wr:.0f}% "
                     f"{r.B_avg:+.2f}R (acak {r.acakB:+.2f}) | thn+ {r.thn_pos:.0f}% | tetangga {r.tetangga:.0f}%")
    return strong


def main() -> None:
    rng = np.random.default_rng(11)
    L = ["# Tangkap pisau jatuh — XAU, BTC, ETH (CFD dua arah) & 20 koin spot (BUY saja) (research/pisau.py)",
         "H1, keputusan di close, entry ≥ open berikutnya. R = kelipatan SL. LAMA < Okt 2021, BARU ≥ Okt 2021.",
         "Biaya: XAU $0,50 pulang-pergi, BTC/ETH 0,06%, koin spot 0,30%."]
    allres = []
    assets = load() if "--koin" not in sys.argv else []
    for s in assets:
        df = scan(s, rng)
        allres.append(df)
        report(df, f"{s.name} ({s.t[0]:%Y}–{s.t[-1]:%Y-%m})", L)
        print("\n".join(L[-30:]), flush=True)
    if "--tanpa-koin" not in sys.argv:
        coins = load_coins()
        parts = [scan(s, rng) for s in coins]
        allc = pd.concat(parts)
        # gabungan koin: rata-rata hasil per kombinasi (tiap koin bobot sama)
        key = ["gerak", "N", "k", "mode", "arah", "tren", "sl", "tp", "H"]
        g = allc.groupby(key)
        pooled = g.agg(L_n=("L_n", "sum"), B_n=("B_n", "sum"), thn_pos=("thn_pos", "mean"), acakL=("acakL", "mean"),
                       acakB=("acakB", "mean")).reset_index()
        for p in ("L", "B"):
            w = allc[f"{p}_n"].fillna(0)
            allc[f"{p}_sum"] = allc[f"{p}_avg"].fillna(0) * w
            allc[f"{p}_wsum"] = allc[f"{p}_wr"].fillna(0) * w
            s_ = allc.groupby(key)[[f"{p}_sum", f"{p}_wsum"]].sum().reset_index()
            pooled = pooled.merge(s_, on=key)
            pooled[f"{p}_avg"] = pooled[f"{p}_sum"] / pooled[f"{p}_n"].replace(0, np.nan)
            pooled[f"{p}_wr"] = pooled[f"{p}_wsum"] / pooled[f"{p}_n"].replace(0, np.nan)
            pooled[f"{p}_t"] = np.nan
        pooled["aset"] = "KOIN20"
        # t kasar dari sebaran per-koin
        tt = allc.groupby(key).L_avg.agg(lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan)
        pooled = pooled.merge(tt.rename("L_t2").reset_index(), on=key)
        pooled["L_t"] = pooled["L_t2"]
        allres.append(pooled)
        report(pooled, f"20 koin spot BUY saja (gabungan, {len(coins)} koin)", L)
        print("\n".join(L[-30:]), flush=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    res = pd.concat(allres)
    res["tp"] = res.tp.astype(str)
    res.to_parquet(ROOT / "data" / "research" / "eksternal" / "pisau_scan.parquet")


if __name__ == "__main__":
    main()
