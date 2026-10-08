"""Token BARU listing di Binance spot: perilaku harga hari-hari pertama & ambang beli/jual — python -m research.listing_baru

Permintaan pengguna 8 Okt 2026 ("token yang baru rilis ... analisa dari tahun ke tahun ... beli di bawah XXX, jual di
atas XXX"). Data:
  - harian semua pair USDT (data/research/eksternal/spot_1d, dari research/spot_semua.py, termasuk delisting);
  - 1 jam 120 hari pertama + 1 menit 2 hari pertama tiap listing (unduh: `python -m research.listing_baru unduh`)
    -> data/research/eksternal/listing/{1h,1m}/<SYM>.parquet.
Dikecualikan: token saham Binance (akhiran B, listing >= Jun 2026), stablecoin/emas (U, KGST, XAUT, FRAX), dan pair
yang datanya < 3 hari.

Harga acuan listing = VWAP 60 menit pertama (open candle pertama Binance sering harga lelang/aneh, mis. ARB 0,5).
Biaya: 0,1% per sisi + slippage 0,1% (pasar besar) — dicek x2/x3 di laporan.
Periode: LAMA = listing < Okt 2021, BARU = >= Okt 2021 (permintaan pengguna: selalu laporkan keduanya).
"""
from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D1 = ROOT / "data" / "research" / "eksternal" / "spot_1d"
DIR = ROOT / "data" / "research" / "eksternal" / "listing"
BASE = "https://data.binance.vision/data/spot"
SKIP = {"U", "KGST", "XAUT", "FRAX", "BNCB"}
POTONG = pd.Timestamp("2021-10-01", tz="UTC")
BIAYA = 0.002  # pulang-pergi: fee 0,1% x2 ... slippage dihitung terpisah


def daftar() -> pd.DataFrame:
    rows = []
    for f in sorted(D1.glob("*.parquet")):
        df = pd.read_parquet(f)
        sym = f.stem
        if len(df) < 3 or sym in SKIP:
            continue
        t0 = df.index[0]
        if t0 >= pd.Timestamp("2026-06-01", tz="UTC") and sym.endswith("B"):
            continue  # token saham Binance (TSLAB, CRCLB, ...)
        rows.append({"sym": sym, "t0": t0, "n": len(df)})
    return pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)


def _zip(url: str) -> pd.DataFrame | None:
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
    except urllib.error.HTTPError:
        return None
    raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4, 7])
    raw.columns = ["t", "open", "high", "low", "close", "qvol"]
    raw = raw[pd.to_numeric(raw.t, errors="coerce").notna()]
    t = raw.pop("t").astype("int64")
    raw.index = pd.to_datetime(t, unit="us" if t.iloc[0] > 1e14 else "ms", utc=True)
    return raw.astype(float)


def unduh_satu(sym: str, t0: pd.Timestamp) -> str:
    s = sym + "USDT"
    (DIR / "1h").mkdir(parents=True, exist_ok=True)
    (DIR / "1m").mkdir(parents=True, exist_ok=True)
    f1h, f1m = DIR / "1h" / f"{sym}.parquet", DIR / "1m" / f"{sym}.parquet"
    msg = []
    if not f1m.exists():
        parts = [x for d in (t0, t0 + pd.Timedelta(days=1))
                 if (x := _zip(f"{BASE}/daily/klines/{s}/1m/{s}-1m-{d:%Y-%m-%d}.zip")) is not None]
        if parts:
            pd.concat(parts).sort_index().to_parquet(f1m)
        msg.append(f"1m {sum(len(p) for p in parts)}")
    if not f1h.exists():
        parts = []
        for m in pd.period_range(t0.tz_localize(None), (t0 + pd.Timedelta(days=120)).tz_localize(None), freq="M"):
            x = _zip(f"{BASE}/monthly/klines/{s}/1h/{s}-1h-{m}.zip")
            if x is None:  # bulan berjalan -> harian
                for d in pd.date_range(m.start_time, min(m.end_time, pd.Timestamp.now())):
                    y = _zip(f"{BASE}/daily/klines/{s}/1h/{s}-1h-{d:%Y-%m-%d}.zip")
                    if y is not None:
                        parts.append(y)
            else:
                parts.append(x)
        if parts:
            df = pd.concat(parts).sort_index()
            df[~df.index.duplicated()].to_parquet(f1h)
        msg.append(f"1h {sum(len(p) for p in parts)}")
    return f"{sym}: " + ", ".join(msg)


def unduh() -> None:
    L = daftar()
    with ThreadPoolExecutor(8) as ex:
        for m in ex.map(lambda r: unduh_satu(r.sym, r.t0), L.itertuples()):
            print(m, flush=True)



# ---------------------------------------------------------------- analisis
def muat(sym: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    f1h, f1m = DIR / "1h" / f"{sym}.parquet", DIR / "1m" / f"{sym}.parquet"
    h = pd.read_parquet(f1h) if f1h.exists() else None
    m = pd.read_parquet(f1m) if f1m.exists() else None
    return h, m


def metrik() -> pd.DataFrame:
    """Satu baris per listing: P0 (VWAP 60 mnt), lonjakan hari 1, return N hari, naik/turun maksimum."""
    rows = []
    for r in daftar().itertuples():
        if r.t0 < pd.Timestamp("2017-09-01", tz="UTC"):
            continue  # data Binance dimulai Agu 2017 -> bukan tanggal listing
        h, m = muat(r.sym)
        if h is None or len(h) < 48:
            continue
        t_list = m.index[0] if m is not None and len(m) else h.index[0]
        if m is not None and len(m) >= 30:
            w = m.iloc[:60]
            tp = (w.high + w.low + w.close) / 3
            p0 = float((tp * w.qvol).sum() / w.qvol.sum()) if w.qvol.sum() > 0 else float(w.close.iloc[-1])
            pump1m = float(m.iloc[:5].high.max() / p0 - 1)
        else:
            p0 = float(h.close.iloc[0])
            pump1m = np.nan
        after = h[h.index >= t_list + pd.Timedelta(hours=1)]
        if len(after) < 24:
            continue

        def ret(days, after=after, t_list=t_list, p0=p0):
            x = after[after.index <= t_list + pd.Timedelta(days=days)]
            return float(x.close.iloc[-1] / p0 - 1) if len(x) and x.index[-1] >= t_list + pd.Timedelta(days=days * .9) else np.nan

        def win(days, after=after, t_list=t_list):
            return after[after.index <= t_list + pd.Timedelta(days=days)]

        d1 = h[h.index < t_list + pd.Timedelta(days=1)]
        rows.append({
            "sym": r.sym, "t": t_list, "tahun": t_list.year, "p0": p0, "pump5m": pump1m,
            "high_h1": float(d1.high.max() / p0 - 1), "low_h1": float(d1.low.min() / p0 - 1),
            "vol_h1_musd": float(d1.qvol.sum() / 1e6),
            **{f"r{d}": ret(d) for d in (1, 7, 30, 90)},
            "maxup30": float(win(30).high.max() / p0 - 1), "maxup90": float(win(90).high.max() / p0 - 1),
            "maxdn30": float(win(30).low.min() / p0 - 1), "maxdn90": float(win(90).low.min() / p0 - 1),
        })
    df = pd.DataFrame(rows)
    df["periode"] = np.where(df.t < POTONG, "LAMA", "BARU")
    return df


def _keluar(yh, yl, yc, yo, e, s, l, biaya):
    tp = e * (1 + s)
    i_tp = int(np.argmax(yh >= tp)) if (yh >= tp).any() else 10**9
    i_sl = int(np.argmax(yl <= e * (1 - l))) if l and (yl <= e * (1 - l)).any() else 10**9
    if i_sl <= i_tp and i_sl < 10**9:  # SL dulu bila satu candle (konservatif)
        return min(yo[i_sl], e * (1 - l)) / e - 1 - biaya
    if i_tp < 10**9:
        return max(yo[i_tp], tp) / e - 1 - biaya
    return yc[-1] / e - 1 - biaya


def grid(m: pd.DataFrame, biaya: float = 0.004) -> pd.DataFrame:
    """Semua kombinasi aturan beli/jual pada setiap listing. Kolom hasil per trade -> diringkas per periode."""
    B = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    S = [0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
    Ls = [0, 0.15, 0.3, 0.5]
    Ts = [7, 30, 90]
    out = []
    for r in m.itertuples():
        h, _ = muat(r.sym)
        hh = h[h.index >= r.t + pd.Timedelta(hours=1)]
        o, hi, lo, c = (hh[k].values for k in ("open", "high", "low", "close"))
        tt = hh.index.values
        d1hi = r.p0 * (1 + r.high_h1)
        i_d1 = int(np.searchsorted(tt, np.datetime64((r.t + pd.Timedelta(days=1)).tz_localize(None))))
        W = int(np.searchsorted(tt, np.datetime64((r.t + pd.Timedelta(days=30)).tz_localize(None))))
        for mode in ("pasar", "dip", "tembus"):
            for b in (B if mode != "pasar" else [0.0]):
                if mode == "pasar":
                    idx, e = 0, o[0]
                elif mode == "dip":
                    lim = r.p0 * (1 - b)
                    hit = np.nonzero(lo[:W] <= lim)[0]
                    if not len(hit):
                        continue
                    idx = int(hit[0]); e = min(o[idx], lim)
                else:
                    if b > 0.3:
                        continue
                    lim = d1hi * (1 + b)
                    hit = np.nonzero(hi[i_d1:W] >= lim)[0]
                    if not len(hit):
                        continue
                    idx = i_d1 + int(hit[0]); e = max(o[idx], lim)
                e *= 1.0
                for T in Ts:
                    j = int(np.searchsorted(tt, tt[idx] + np.timedelta64(T, "D")))
                    sl_ = slice(idx + 1, max(j, idx + 2))
                    yh, yl, yc, yo = hi[sl_], lo[sl_], c[sl_], o[sl_]
                    if not len(yc):
                        continue
                    for s_ in S:
                        for l_ in Ls:
                            out.append((r.sym, r.t, r.periode, mode, b, s_, l_, T,
                                        _keluar(yh, yl, yc, yo, e, s_, l_, biaya)))
    return pd.DataFrame(out, columns=["sym", "t", "periode", "mode", "b", "s", "l", "T", "ret"])


def ringkas(g: pd.DataFrame) -> pd.DataFrame:
    k = ["mode", "b", "s", "l", "T"]
    def f(x):
        return pd.Series({"n": len(x), "wr": (x.ret > 0).mean(), "rata": x.ret.mean(), "median": x.ret.median(),
                          "terburuk": x.ret.min()})
    r = g.groupby(k + ["periode"]).ret.agg(n="size", wr=lambda x: (x > 0).mean(), rata="mean", median="median",
                                          terburuk="min").unstack("periode")
    r.columns = [f"{a}_{b}" for a, b in r.columns]
    return r.reset_index()


AIRDROP = ["UNI", "1INCH", "DYDX", "ENS", "OP", "APT", "ARB", "TIA", "JTO", "JUP", "STRK", "ENA", "W", "ZK", "ZRO",
           "EIGEN", "ME", "BERA", "KAITO", "LINEA", "MEGA"]  # dibagikan gratis (airdrop) & listing Binance saat TGE


def acak(m: pd.DataFrame, s: float, l: float, T: int, biaya: float = 0.004, n: int = 20, seed: int = 0) -> pd.Series:
    """Pembanding: beli di jam ACAK dalam 30 hari pertama, TP/SL/batas sama -> rata-rata per listing."""
    rng = np.random.default_rng(seed)
    out = {}
    for r in m.itertuples():
        h, _ = muat(r.sym)
        hh = h[h.index >= r.t + pd.Timedelta(hours=1)]
        W = int(np.searchsorted(hh.index.values, np.datetime64((r.t + pd.Timedelta(days=30)).tz_localize(None))))
        if W < 2:
            continue
        o, hi, lo, c, tt = hh.open.values, hh.high.values, hh.low.values, hh.close.values, hh.index.values
        res = []
        for idx in rng.integers(0, W, n):
            j = int(np.searchsorted(tt, tt[idx] + np.timedelta64(T, "D")))
            sl_ = slice(idx + 1, max(j, idx + 2))
            if not len(c[sl_]):
                continue
            res.append(_keluar(hi[sl_], lo[sl_], c[sl_], o[sl_], o[idx], s, l, biaya))
        if res:
            out[r.sym] = float(np.mean(res))
    return pd.Series(out)


def laporan() -> str:
    m = pd.read_parquet(DIR / "metrik.parquet") if (DIR / "metrik.parquet").exists() else metrik()
    g = pd.read_parquet(DIR / "grid.parquet") if (DIR / "grid.parquet").exists() else grid(m)
    L = []
    p = L.append
    med = lambda x: f"{np.nanmedian(x) * 100:+.0f}%"
    p(f"=== Listing baru Binance spot (USDT), {len(m)} token 2017-09..2026-09 (termasuk yang sudah delisting)")
    p("P0 = VWAP 60 menit pertama. Angka median kecuali disebut.\n")
    t = m.groupby("tahun").agg(n=("sym", "size"), lonjak_5mnt=("pump5m", med), puncak_hari1=("high_h1", med),
                               r1=("r1", med), r7=("r7", med), r30=("r30", med), r90=("r90", med),
                               naik_90h=("r90", lambda x: f"{(x > 0).mean():.0%}"),
                               capai_2x_90h=("maxup90", lambda x: f"{(x >= 1).mean():.0%}"),
                               capai_5x_90h=("maxup90", lambda x: f"{(x >= 4).mean():.0%}"),
                               turun_maks_30h=("maxdn30", med))
    p(t.to_string())
    for per in ("LAMA", "BARU"):
        x = m[m.periode == per]
        p(f"{per} (n {len(x)}): r30 median {x.r30.median():+.0%} rata {x.r30.mean():+.0%}; r90 median {x.r90.median():+.0%}"
          f" rata {x.r90.mean():+.0%}; naik setelah 90 hari {(x.r90 > 0).mean():.0%}; sempat 2x {(x.maxup90 >= 1).mean():.0%}")

    r = ringkas(g)
    ok = r[(r.n_LAMA >= 30) & (r.n_BARU >= 30)].copy()
    cols = ["mode", "b", "s", "l", "T", "n_LAMA", "wr_LAMA", "rata_LAMA", "n_BARU", "wr_BARU", "rata_BARU", "median_BARU",
            "terburuk_BARU"]
    p(f"\n=== Aturan beli/jual ({len(ok)} kombinasi dgn n >= 30 di kedua periode; biaya 0,4% pulang-pergi)")
    p("mode pasar = beli jam ke-2 listing; dip = limit beli P0 x (1-b) dalam 30 hari; tembus = beli bila tembus puncak"
      " hari-1 x (1+b). s = TP, l = SL (0 = tanpa), T = batas hari.")
    p(f"positif di kedua periode: {((ok.rata_LAMA > 0) & (ok.rata_BARU > 0)).sum()} dari {len(ok)}")
    p("\n-- 10 terbaik menurut LAMA (dipilih TANPA melihat BARU)")
    p(ok.sort_values("rata_LAMA", ascending=False)[cols].head(10).round(3).to_string(index=False))
    p("\n-- beli saat listing (pasar) — pembanding")
    p(ok[ok["mode"] == "pasar"].sort_values("rata_LAMA", ascending=False)[cols].head(5).round(3).to_string(index=False))
    for per in ("LAMA", "BARU"):
        y = g[(g["mode"] == "dip") & (g["T"] == 90) & (g.l == 0.5) & (g.periode == per)]
        tt = y.groupby(["b", "s"]).ret.agg(lambda v: f"{v.mean() * 100:+.0f} ({(v > 0).mean() * 100:.0f})").unstack("s")
        p(f"\n-- {per}: dip, SL 50%, batas 90 hari: rata %/trade (WR %), baris b = turun dari P0, kolom s = TP")
        p(tt.to_string())

    p("\n=== Kandidat: beli setelah turun >= 60% dari P0 (30 hari pertama), TP +20%, SL -50%, maks 90 hari")
    c = g[(g["mode"] == "dip") & (g.b == 0.6) & (g.s == 0.2) & (g.l == 0.5) & (g["T"] == 90)].copy()
    c["tahun"] = c.t.dt.year
    y = c.groupby("tahun").ret.agg(n="size", rata="mean", wr=lambda v: (v > 0).mean())
    p(y.round(3).T.to_string())
    for per in ("LAMA", "BARU"):
        v = c[c.periode == per].ret.to_numpy()
        rng = np.random.default_rng(0)
        bs = np.array([rng.choice(v, len(v)).mean() for _ in range(5000)])
        p(f"{per}: n {len(v)}, WR {(v > 0).mean():.0%}, rata {v.mean():+.1%}, median {np.median(v):+.1%}, terburuk "
          f"{v.min():+.0%}, CI90 rata [{np.percentile(bs, 5):+.1%}, {np.percentile(bs, 95):+.1%}]")
    for k in (2, 3):
        p(f"biaya x{k}: rata BARU {(c[c.periode == 'BARU'].ret - 0.004 * (k - 1)).mean():+.1%}")
    ac = acak(m[m.sym.isin(c.sym)], 0.2, 0.5, 90)
    cc = c.set_index("sym").ret
    both = cc.index.intersection(ac.index)
    p(f"pembanding: token yang SAMA, beli di jam acak 30 hari pertama (TP/SL sama): rata {ac[both].mean():+.1%} vs "
      f"kandidat {cc[both].mean():+.1%} (n {len(both)})")

    p("\n=== Token AIRDROP (gratis, seperti ARB) — harga setelah listing Binance vs P0")
    rows = []
    for sym in AIRDROP:
        if sym not in set(m.sym):
            continue
        r_ = m[m.sym == sym].iloc[0]
        d = pd.read_parquet(D1 / f"{sym}.parquet")
        t0 = r_.t.normalize()

        def at(days, d=d, t0=t0, p0=r_.p0):
            x = d[d.index <= t0 + pd.Timedelta(days=days)]
            return x.close.iloc[-1] / p0 - 1 if len(x) and x.index[-1] >= t0 + pd.Timedelta(days=days - 1) else np.nan

        rows.append({"token": sym, "listing": r_.t.date(), "P0$": round(r_.p0, 4), "5mnt_pertama": r_.pump5m,
                     "7h": at(7), "30h": at(30), "90h": at(90), "180h": at(180), "365h": at(365),
                     "sekarang": d.close.iloc[-1] / r_.p0 - 1, "puncak": d.high.max() / r_.p0 - 1,
                     "hari_ke_puncak": (d.high.idxmax() - t0).days})
    a = pd.DataFrame(rows).set_index("token")
    pct = ["5mnt_pertama", "7h", "30h", "90h", "180h", "365h", "sekarang", "puncak"]
    p(a.assign(**{k: a[k].map(lambda v: "" if pd.isna(v) else f"{v:+.0%}") for k in pct}).to_string())
    p("median: " + ", ".join(f"{k} {a[k].median():+.0%}" for k in pct))
    p(f"lebih tinggi dari P0 setelah 365 hari: {(a['365h'] > 0).sum()}/{a['365h'].notna().sum()}; puncak di hari "
      f"listing (<= 1 hari): {(a.hari_ke_puncak <= 1).sum()}/{len(a)}")
    arb = a.loc["ARB"]
    p(f"ARB: alokasi airdrop 625-10.250 ARB per dompet (Mar 2023). x P0 ${arb['P0$']} = ${625 * arb['P0$']:,.0f}-"
      f"${10250 * arb['P0$']:,.0f} (kurs ±Rp15.300 -> Rp{625 * arb['P0$'] * 15300 / 1e6:,.0f}-"
      f"{10250 * arb['P0$'] * 15300 / 1e6:,.0f} juta). Nilai sekarang {arb['sekarang']:+.0%} dari P0.")
    out = "\n".join(L)
    (ROOT / "docs" / "eksternal").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "eksternal" / "hasil_listing_baru.txt").write_text(out)
    return out

if __name__ == "__main__":
    if sys.argv[1:] == ["unduh"]:
        unduh()
    elif sys.argv[1:] == ["laporan"]:
        print(laporan())
    else:
        print(daftar().assign(y=lambda d: d.t0.dt.year).y.value_counts().sort_index())
