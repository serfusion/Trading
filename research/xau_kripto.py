"""🔗 XAU jatuh dalam lalu memantul → apakah BTC, ETH & koin lain ikut naik serempak? — python -m research.xau_kripto

Hipotesis pengguna (9 Okt 2026): "XAU/kripto akan naik apabila XAU telah turun sangat dalam; ketika XAU pullback ke atas,
mulai dari XAU, BTC, koin lainnya ikut naik serempak."

Data: XAU H1 (research.eksternal.asset XAUUSD 2012–2026), BTC H1 (BTCUSD), ETH & koin lain H1 Binance
(data/research/eksternal/pair_h1). Periode uji kripto 2018–2026; LAMA = s.d. Sep 2021, BARU = Okt 2021–2026.

1) Mekanisme: korelasi return 1 jam / 1 hari XAU vs BTC per tahun, dan lead-lag (apakah XAU bergerak lebih dulu).
2) Uji kejadian: di candle XAU t, dalam N jam terakhir XAU jatuh dari puncak ke dasar ≥ k × ATR24 (atau ≥ d%), dasar
   ≤ 12 jam lalu, dan close t baru saja memantul ≥ r dari jarak jatuh (transisi). Beli kripto di close jam t (= open jam
   berikutnya), jual H jam kemudian. Biaya spot 0,2% pulang-pergi. Pembanding: rata-rata semua jam XAU (dasar) dan
   undian acak jam XAU sejumlah sama (p-acak). Varian "serempak": BTC juga jatuh ≥ 2 ATR-nya di jendela yang sama.
3) Aturan dipilih HANYA dari LAMA (excess return terbaik dengan n ≥ 30), lalu diuji di BARU dan per tahun.
4) `python -m research.xau_kripto rezim`: jatuh dalam (≥ 5 ATR) dipisah menurut korelasi harian XAU–BTC 60 hari s.d.
   kemarin (≥ 0,2 = "emas & BTC sedang searah"); kepekaan jendela/ambang/aturan, p per pekan, serempak, TP/SL, per
   koin → docs/eksternal/hasil_xau_kripto_rezim.txt. Pemisahan korelasi ditemukan SETELAH melihat 2026 (korelasi
   tinggi) → bukan pilihan LAMA murni.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PAIR = ROOT / "data" / "research" / "eksternal" / "pair_h1"
OUT = ROOT / "docs" / "eksternal" / "hasil_xau_kripto.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
MULAI = pd.Timestamp("2018-01-01", tz="UTC")
BIAYA = 0.002
ALTS = ["ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "AVAX", "DOT", "LTC", "BCH", "XLM", "ATOM", "ETC",
        "UNI", "NEAR", "AAVE", "FIL"]
HS = (12, 24, 48, 72)


def _ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df[["open", "high", "low", "close"]].astype(float)
    df = df[(df.high > df.low) | (df.high > 0)]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df[~df.index.duplicated()].sort_index()


def muat() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(xau H1, tabel close kripto per jam penuh 24/7 [BTC, ETH, …])."""
    from .eksternal import asset
    xau = _ohlc(asset("XAUUSD").b.df)
    xau = xau[xau.high > xau.low]
    btc = _ohlc(asset("BTCUSD").b.df)
    idx = pd.date_range(MULAI, min(xau.index.max(), btc.index.max()), freq="h", tz="UTC")
    cl = {"BTC": btc.close.reindex(idx).ffill(limit=3)}
    hl = {"BTC": (btc.high.reindex(idx), btc.low.reindex(idx))}
    for c in ALTS:
        p = PAIR / f"{c}USD.parquet"
        if p.exists():
            d = _ohlc(pd.read_parquet(p))
            cl[c] = d.close.reindex(idx).ffill(limit=3)
    cr = pd.DataFrame(cl)
    cr.attrs["btc_hl"] = hl["BTC"]
    return xau[xau.index >= MULAI - pd.Timedelta(days=30)], cr


def atr(df: pd.DataFrame, n: int = 24) -> np.ndarray:
    h, lo, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(abs(h - pc), abs(lo - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def kejadian(xau: pd.DataFrame, N: int, k: float | None, r: float, d_pct: float | None = None, W: int = 12):
    """Indeks candle XAU saat pantulan terkonfirmasi. Jatuh = puncak (high) → dasar (low) sesudahnya dalam N candle."""
    h, lo, c = xau.high.to_numpy(), xau.low.to_numpy(), xau.close.to_numpy()
    a = atr(xau)
    out, terakhir = [], -10**9
    for t in range(N + 1, len(c)):
        w0 = t - N + 1
        ih = w0 + int(np.argmax(h[w0:t + 1]))
        if ih >= t:
            continue
        il = ih + int(np.argmin(lo[ih:t + 1]))
        if t - il > W or il == t:
            continue
        top, bot = h[ih], lo[il]
        jarak = top - bot
        if jarak <= 0:
            continue
        dalam = (jarak / a[ih] >= k) if k is not None else (jarak / top * 100 >= d_pct)
        if not dalam:
            continue
        lvl = bot + r * jarak
        if c[t] >= lvl and c[t - 1] < lvl and t - terakhir > N:   # transisi, tidak menghitung kejadian yang sama
            out.append(t)
            terakhir = t
    return np.array(out, dtype=int)


def maju(cr: pd.DataFrame, waktu: pd.DatetimeIndex, H: int) -> pd.DataFrame:
    """Return kripto dari close jam kejadian ke close H jam kemudian (dikurangi biaya)."""
    pos = cr.index.get_indexer(waktu)
    ok = (pos >= 0) & (pos + H < len(cr))
    p0 = cr.to_numpy()[pos[ok]]
    p1 = cr.to_numpy()[pos[ok] + H]
    r = p1 / p0 - 1 - BIAYA
    out = pd.DataFrame(r, index=waktu[ok], columns=cr.columns)
    out["ALT"] = out[[c for c in cr.columns if c != "BTC"]].mean(axis=1, skipna=True)
    return out


def btc_jatuh(cr: pd.DataFrame, waktu: pd.DatetimeIndex, N: int, m: float = 2.0) -> np.ndarray:
    """BTC juga jatuh ≥ m × ATR24-nya dari puncak ke dasar dalam N jam yang sama ('serempak')."""
    hi_, lo_ = cr.attrs["btc_hl"]
    tr = (hi_ - lo_).abs()
    a = tr.ewm(alpha=1 / 24, adjust=False).mean()
    hmax = hi_.rolling(N, min_periods=1).max()
    lmin = lo_.rolling(N, min_periods=1).min()
    jar = (hmax - lmin) / a
    return (jar.reindex(waktu).to_numpy() >= m)


def ringkas(x: pd.Series) -> str:
    x = x.dropna()
    if len(x) == 0:
        return "n 0"
    return f"n {len(x):4} | naik {(x > 0).mean() * 100:5.1f}% | rata {x.mean() * 100:+6.2f}% | median {x.median() * 100:+6.2f}%"


def mekanisme(xau: pd.DataFrame, cr: pd.DataFrame) -> list[str]:
    L = ["## 1. Mekanisme: XAU vs BTC bergerak bersama? (return 1 jam saat XAU buka & return harian)"]
    xr = xau.close.pct_change()
    br = cr.BTC.pct_change().reindex(xr.index)
    df = pd.DataFrame({"x": xr, "b": br}).dropna()
    df = df[df.index >= MULAI]
    for y, g in df.groupby(df.index.year):
        xd = xau.close[xau.index.year == y].resample("D").last().pct_change()
        bd = cr.BTC[cr.index.year == y].resample("D").last().pct_change()
        dd = pd.DataFrame({"x": xd, "b": bd}).dropna()
        L.append(f"  {y}: korelasi 1 jam {g.x.corr(g.b):+.2f} | harian {dd.x.corr(dd.b):+.2f} (n hari {len(dd)})")
    L.append("  Lead-lag (korelasi return XAU jam t dengan return BTC jam t+k, 2018–2026):")
    for k in range(0, 7):
        s = pd.DataFrame({"x": xr, "b": cr.BTC.pct_change().shift(-k).reindex(xr.index)}).dropna()
        s = s[s.index >= MULAI]
        L.append(f"    k={k}: {s.x.corr(s.b):+.3f}")
    L.append("")
    return L


def uji() -> list[str]:
    xau, cr = muat()
    L = ["# 🔗 XAU jatuh dalam lalu memantul → kripto ikut naik? (research/xau_kripto.py)", "",
         f"Data: XAU H1 {xau.index.min():%Y-%m} s.d. {xau.index.max():%Y-%m-%d}, kripto {', '.join(cr.columns)}.",
         "Return = close jam pantulan XAU → close H jam kemudian, spot, biaya 0,2% pulang-pergi. ALT = rata-rata koin selain "
         "BTC. Dasar = semua jam XAU (beli kapan saja). LAMA s.d. Sep 2021, BARU Okt 2021–2026.", ""]
    L += mekanisme(xau, cr)
    xi = xau.index
    dasar_w = xi[(xi >= MULAI)]
    base = {H: maju(cr, dasar_w, H) for H in HS}
    L.append("## 2. Dasar (beli di jam XAU mana saja)")
    for H in HS:
        b = base[H]
        for per, m in (("LAMA", b.index < SPLIT), ("BARU", b.index >= SPLIT)):
            L.append(f"  {H:2} jam {per}: BTC {ringkas(b.BTC[m])} | ALT {ringkas(b.ALT[m])}")
    L.append("")
    grid = []
    for N in (6, 12, 24, 48):
        for k in (2.0, 3.0, 4.0, 5.0):
            for r in (0.25, 0.382, 0.5):
                ev = kejadian(xau, N, k, r)
                grid.append(((N, f"k{k:g}", r), ev))
        for dp in (1.5, 2.0, 3.0):
            for r in (0.25, 0.382, 0.5):
                ev = kejadian(xau, N, None, r, dp)
                grid.append(((N, f"d{dp:g}%", r), ev))
    rows = []
    for (N, kk, r), ev in grid:
        t = xi[ev]
        t = t[t >= MULAI]
        if len(t) < 10:
            continue
        for H in HS:
            f = maju(cr, t, H)
            b = base[H]
            for per, m, mb in (("LAMA", f.index < SPLIT, b.index < SPLIT), ("BARU", f.index >= SPLIT, b.index >= SPLIT)):
                x = f[m]
                rows.append({"N": N, "dalam": kk, "r": r, "H": H, "per": per, "n": len(x),
                             "btc": x.BTC.mean(), "btc_naik": (x.BTC > 0).mean(), "alt": x.ALT.mean(),
                             "alt_naik": (x.ALT > 0).mean(), "ex_btc": x.BTC.mean() - b.BTC[mb].mean(),
                             "ex_alt": x.ALT.mean() - b.ALT[mb].mean()})
    R = pd.DataFrame(rows)
    piv = R.pivot_table(index=["N", "dalam", "r", "H"], columns="per", values=["n", "ex_btc", "ex_alt", "btc_naik",
                                                                             "alt_naik", "btc", "alt"])
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    piv = piv.dropna()
    lam = piv[piv.n_LAMA >= 30]
    L.append(f"## 3. {len(piv)} kombinasi (N jam jatuh × kedalaman × pantulan r × tahan H)")
    for nama, col in (("BTC", "ex_btc"), ("ALT", "ex_alt")):
        top = lam.sort_values(f"{col}_LAMA", ascending=False).head(8)
        nk = col.split("_")[1] + "_naik"
        L.append(f"  8 terbaik dipilih dari LAMA ({nama}, excess vs dasar), lalu BARU:")
        for i, x in top.iterrows():
            L.append(f"    N{i[0]:>2} {i[1]:>5} r{i[2]:<5} H{i[3]:>2}: LAMA n {x.n_LAMA:3.0f} excess "
                     f"{x[col + '_LAMA'] * 100:+5.2f}% naik {x[nk + '_LAMA'] * 100:4.0f}% | BARU n {x.n_BARU:3.0f} "
                     f"excess {x[col + '_BARU'] * 100:+5.2f}% naik {x[nk + '_BARU'] * 100:4.0f}%")
        konsisten = ((piv[f"{col}_LAMA"] > 0) & (piv[f"{col}_BARU"] > 0)).mean() * 100
        L.append(f"  {nama}: kombinasi dengan excess > 0 di KEDUA periode: {konsisten:.0f}% "
                 f"(kebetulan murni ≈ 25%); rata-rata excess LAMA {piv[f'{col}_LAMA'].mean() * 100:+.2f}% "
                 f"BARU {piv[f'{col}_BARU'].mean() * 100:+.2f}%")
    L.append("")
    # aturan terbaik LAMA (ALT, H 24–72) → rinci: p-acak, per tahun, serempak vs tidak
    best = lam.sort_values("ex_alt_LAMA", ascending=False).index[0]
    N, kk, r, H = best
    ev = [e for (g, e) in grid if g == (N, kk, r)][0]
    t = xi[ev]
    t = t[t >= MULAI]
    f = maju(cr, t, H)
    L.append(f"## 4. Rincian aturan terbaik LAMA: XAU jatuh {kk} dalam {N} jam, pantul {r} → tahan {H} jam")
    rng = np.random.default_rng(0)
    b = base[H]
    for per, m, mb in (("LAMA", f.index < SPLIT, b.index < SPLIT), ("BARU", f.index >= SPLIT, b.index >= SPLIT)):
        x = f[m]
        pool = b[mb]
        draws = np.array([pool.ALT.iloc[rng.choice(len(pool), len(x), replace=False)].mean() for _ in range(2000)])
        p = float((draws >= x.ALT.mean()).mean())
        L.append(f"  {per}: BTC {ringkas(x.BTC)} | ALT {ringkas(x.ALT)} | p-acak ALT {p:.3f}")
    sr = btc_jatuh(cr, f.index, N)
    for lab, m in (("BTC ikut jatuh (serempak)", sr), ("BTC tidak ikut jatuh", ~sr)):
        x = f[m]
        L.append(f"  {lab}: BTC {ringkas(x.BTC)} | ALT {ringkas(x.ALT)}")
    th = f.groupby(f.index.year).agg(n=("ALT", "size"), alt=("ALT", "mean"), btc=("BTC", "mean"))
    L.append("  per tahun (rata ALT / BTC): " + " ".join(f"{y}:{v.alt * 100:+.1f}/{v.btc * 100:+.1f}%({v.n})"
                                                      for y, v in th.iterrows()))
    per_koin = f.drop(columns=["ALT"]).mean().sort_values(ascending=False)
    L.append("  per koin (rata semua periode): " + " ".join(f"{c}:{v * 100:+.1f}%" for c, v in per_koin.items()))
    L.append("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return L


def korelasi_harian(xau: pd.DataFrame, cr: pd.DataFrame, hari: int = 60) -> pd.Series:
    """Korelasi return harian XAU–BTC `hari` baris s.d. KEMARIN (shift 1, tanpa look-ahead). Sama dengan cloud _pulih."""
    xd = xau.close.resample("D").last().pct_change()
    bd = cr.BTC.resample("D").last().pct_change()
    dd = pd.DataFrame({"x": xd, "b": bd}).dropna()
    return dd.x.rolling(hari).corr(dd.b).shift(1)


def rezim() -> list[str]:
    xau, cr = muat()
    xi = xau.index
    out = OUT.with_name("hasil_xau_kripto_rezim.txt")
    L = ["# 🔗 Rezim korelasi: jatuh dalam XAU lalu pantul, dipisah korelasi harian XAU–BTC (research/xau_kripto.py rezim)",
         "Return ALT = rata-rata 19 koin selain BTC, biaya 0,2%. Dasar = semua jam XAU pada rezim korelasi yang sama.", ""]
    corr60 = korelasi_harian(xau, cr, 60)
    cval = lambda c, t: c.reindex(t.normalize(), method="ffill").to_numpy()  # noqa: E731
    base = {H: maju(cr, xi[xi >= MULAI], H) for H in (24, 48, 72)}
    L.append("## 5a. Korelasi 60 hari ≥ 0,2 vs < 0,2 (tahan 48 jam)")
    for N, k, r in ((6, 5.0, 0.382), (12, 5.0, 0.382), (12, 5.0, 0.5), (24, 5.0, 0.382), (24, 5.0, 0.5), (24, 4.0, 0.5)):
        t = xi[kejadian(xau, N, k, r)]
        t = t[t >= MULAI]
        f = maju(cr, t, 48)
        c = cval(corr60, f.index)
        for lab, m0 in (("korelasi ≥ 0,2", c >= 0.2), ("korelasi < 0,2", c < 0.2)):
            line = f"  N{N:>2} k{k:g} r{r:<5} {lab:15}:"
            for per, mp in (("LAMA", f.index < SPLIT), ("BARU", f.index >= SPLIT)):
                x = f[m0 & mp]
                line += (f" | {per} n {len(x):3} ALT naik {(x.ALT > 0).mean() * 100 if len(x) else 0:3.0f}% rata "
                         f"{x.ALT.mean() * 100 if len(x) else 0:+5.2f}% BTC {x.BTC.mean() * 100 if len(x) else 0:+5.2f}%")
            L.append(line)
    b = base[48]
    cb = cval(corr60, b.index)
    for lab, m0 in (("dasar korelasi ≥ 0,2", cb >= 0.2), ("dasar korelasi < 0,2", cb < 0.2)):
        L.append(f"  {lab}: " + " | ".join(f"{per} ALT {b.ALT[m0 & mp].mean() * 100:+.2f}% naik "
                                           f"{(b.ALT[m0 & mp] > 0).mean() * 100:.0f}%"
                                           for per, mp in (("LAMA", b.index < SPLIT), ("BARU", b.index >= SPLIT))))
    cc = corr60.dropna()
    L.append("  porsi hari korelasi ≥ 0,2 per tahun: " + " ".join(f"{y}:{(g >= 0.2).mean() * 100:.0f}%"
                                                                  for y, g in cc.groupby(cc.index.year)))
    L.append("")
    L.append("## 5b. Kepekaan: jendela korelasi × ambang × aturan (p-acak ALT vs dasar rezim sama, 1000 undian)")
    rng = np.random.default_rng(0)
    for win in (30, 60, 90):
        corr = korelasi_harian(xau, cr, win)
        for thr in (0.1, 0.2, 0.3):
            for N, k, r, H in ((24, 5.0, 0.382, 48), (24, 5.0, 0.5, 48), (12, 5.0, 0.382, 48), (24, 4.0, 0.382, 48),
                               (24, 6.0, 0.382, 48), (24, 5.0, 0.382, 24), (24, 5.0, 0.382, 72)):
                t = xi[kejadian(xau, N, k, r)]
                t = t[t >= MULAI]
                f = maju(cr, t, H)
                bb = base[H]
                c, cb = cval(corr, f.index), cval(corr, bb.index)
                o = []
                for per, mp, mbp in (("LAMA", f.index < SPLIT, bb.index < SPLIT), ("BARU", f.index >= SPLIT,
                                                                                    bb.index >= SPLIT)):
                    x, pool = f[(c >= thr) & mp], bb[(cb >= thr) & mbp]
                    if len(x) < 5 or len(pool) < len(x):
                        o.append(f"{per} n{len(x)}")
                        continue
                    dr = np.array([pool.ALT.iloc[rng.choice(len(pool), len(x), replace=False)].mean()
                                   for _ in range(1000)])
                    th = x.groupby(x.index.year).ALT.mean()
                    o.append(f"{per} n{len(x):3} naik {(x.ALT > 0).mean() * 100:3.0f}% {x.ALT.mean() * 100:+5.2f}% "
                             f"(dasar {pool.ALT.mean() * 100:+5.2f}%) p {(dr >= x.ALT.mean()).mean():.3f} "
                             f"th+ {(th > 0).sum()}/{len(th)}")
                L.append(f"  corr{win} ≥{thr} N{N} k{k:g} r{r} H{H}: " + " || ".join(o))
    L.append("")
    N, k, r, H = 24, 5.0, 0.382, 48
    t = xi[kejadian(xau, N, k, r)]
    t = t[t >= MULAI]
    t = t[cval(corr60, t) >= 0.2]
    f = maju(cr, t, H)
    koin = list(cr.columns)
    L.append(f"## 5c. Aturan terpasang di cloud (_pulih.py): N{N} k{k:g} r{r} H{H} + korelasi 60 hari ≥ 0,2")
    L.append(f"  kejadian {len(f)} | per tahun: " + " ".join(f"{y}:{n}" for y, n in f.groupby(f.index.year).size().items()))
    for per, m in (("LAMA", f.index < SPLIT), ("BARU", f.index >= SPLIT)):
        L.append(f"  {per}: BTC {ringkas(f.BTC[m])} | ALT {ringkas(f.ALT[m])}")
    bpool = base[H][cval(corr60, base[H].index) >= 0.2]
    rng = np.random.default_rng(1)
    for per, m, mb in (("LAMA", f.index < SPLIT, bpool.index < SPLIT), ("BARU", f.index >= SPLIT, bpool.index >= SPLIT)):
        x = f[m]
        wk = x.ALT.groupby(x.index.tz_localize(None).to_period("W")).mean()
        pool = bpool[mb]
        pw = pool.ALT.groupby(pool.index.tz_localize(None).to_period("W")).mean()
        dr = np.array([pw.iloc[rng.choice(len(pw), len(wk), replace=False)].mean() for _ in range(2000)])
        L.append(f"  {per}: {len(wk)} pekan berbeda, rata per pekan {wk.mean() * 100:+.2f}% vs pekan acak "
                 f"{pw.mean() * 100:+.2f}% → p {(dr >= wk.mean()).mean():.3f}; pekan naik {(wk > 0).mean() * 100:.0f}%")
    naik = (f[koin] > 0).sum(axis=1) / f[koin].notna().sum(axis=1)
    for per, m in (("LAMA", f.index < SPLIT), ("BARU", f.index >= SPLIT)):
        L.append(f"  {per}: rata {naik[m].mean() * 100:.0f}% koin naik bersamaan; kejadian ≥ 80% koin naik: "
                 f"{(naik[m] >= 0.8).mean() * 100:.0f}%")
    x = f[f.index >= SPLIT]
    for c in ("BTC", "ALT"):
        q = x[c].quantile([0.05, 0.25, 0.5, 0.75, 0.95]) * 100
        L.append(f"  {c} BARU: P5 {q[0.05]:+.1f}% P25 {q[0.25]:+.1f}% median {q[0.5]:+.1f}% P75 {q[0.75]:+.1f}% "
                 f"P95 {q[0.95]:+.1f}% terburuk {x[c].min() * 100:+.1f}%")
    th = f.groupby(f.index.year).ALT.agg(["mean", "size"])
    L.append("  per tahun ALT: " + " ".join(f"{y}:{v['mean'] * 100:+.1f}%({int(v['size'])})" for y, v in th.iterrows()))
    pk = x.drop(columns=["ALT"]).mean().sort_values(ascending=False)
    L.append("  per koin BARU: " + " ".join(f"{c}:{v * 100:+.1f}%" for c, v in pk.items()))
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return L


if __name__ == "__main__":
    rezim() if sys.argv[1:2] == ["rezim"] else uji()
