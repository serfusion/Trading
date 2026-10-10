"""🛑 Batalkan / tutup sinyal saat GUNCANGAN harga (proksi pernyataan Trump, Fed, pemerintah AS, negara lain).

python -m research.batal_guncang            → docs/eksternal/hasil_batal_guncang.txt

Permintaan pengguna 10 Okt 2026: "jika ada statement Trump, pemerintah AS, the Fed, orang penting atau negara yang
membuat harga jatuh, tarik sinyal BUY (canceled/invalid) — seperti spot XLM yang dikirim sebelum jatuh lalu loss jauh".

Pernyataan baru bisa dinilai "membuat harga jatuh" setelah harga bereaksi. Arsip judul berita/pernyataan (GDELT, Truth
Social, RSS Fed/Gedung Putih) tidak bisa diunduh dari sesi riset (403), jadi yang diuji adalah GUNCANGAN HARGA yang
pasti mengikuti pernyataan penting: harga bergerak MELAWAN posisi sejauh ambang tertentu dalam ≤ m jam. Keputusan diambil
di close candle 1 jam (cloud memeriksa tiap 10 menit → di live lebih cepat; uji ini konservatif).

  A. 💰 XAU & BTC (replay kode cloud live: verifikasi/cloud_XAU.csv, cloud_BTC.csv, semua set & lapisan): SEBELUM TP1,
     harga melawan ≥ k × ATR14 H1 (dari harga terbaik sejak entry dalam m jam terakhir) → TUTUP semua posisi di close.
  B. 💎 spot (research/spot_peluang final, gabungan 20 koin, TP +3% / 10 hari, tanpa SL): koin turun ≥ x% dari high
     sejak entry dalam m jam, ATAU BTC turun ≥ y% dalam m jam → JUAL di close jam itu.
  C. 🔗 pulih (replay kode cloud _pulih.py, keranjang 9 koin 48 jam): rata-rata keranjang turun ≥ x% dari puncaknya
     dalam m jam → JUAL semua.
Pembanding = tahan seperti sekarang. Δ = hasil dengan aturan − hasil tahan (per sinyal). Δ > 0 = membatalkan menolong.
Untuk yang BELUM entry, Δ yang sama berarti: "masuk setelah guncangan lalu mengikuti TP/SL lama" rata-rata −Δ.
Kriteria lolos (ditetapkan sebelum melihat hasil): Δ rata-rata > 0 di LAMA (< Okt 2021) DAN BARU, ≥ 60% tahun Δ ≥ 0,
dan ambang tetangga (k ± 1 langkah) juga Δ > 0 di kedua periode.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_batal_guncang.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
TP1_R = 0.7
BIAYA_KELUAR = {"XAU": 0.20, "BTC": None}       # XAU $0,20 (spread Exness); BTC 0,03% harga
K_GRID = (1.5, 2.0, 3.0, 4.0)
M_GRID = (1, 2, 3, 6)


def atr14(df: pd.DataFrame) -> np.ndarray:
    h, lo, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(abs(h - pc), abs(lo - pc)))
    return pd.Series(tr).rolling(14).mean().to_numpy()


def h1(name: str) -> pd.DataFrame:
    from .eksternal import asset
    df = asset({"XAU": "XAUUSD", "BTC": "BTCUSD"}[name]).b.df[["open", "high", "low", "close"]].astype(float)
    df = df[df.high > df.low]
    return df[~df.index.duplicated()].sort_index()


# ------------------------------------------------------------------ A. 💰 XAU & BTC
def sim_sinyal(rows: pd.DataFrame, df: pd.DataFrame, name: str, k: float, m: int) -> pd.DataFrame:
    """Per sinyal: r tahan vs r dengan aturan guncangan (sebelum TP1). Kolom: t, dir, r0, r1, kena, jam."""
    t_idx = df.index
    o, h, lo, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    a = atr14(df)
    out = []
    for row in rows.itertuples():
        t0 = pd.Timestamp(row.t_signal).floor("h")
        i0 = t_idx.searchsorted(t0)
        i1 = t_idx.searchsorted(pd.Timestamp(row.t_close))
        if i0 >= len(t_idx) or i0 < 15:
            continue
        sign = 1 if row.dir == "BUY" else -1
        e, risk = float(row.entry), float(row.risk)
        sl, tp1 = e - sign * risk, e + sign * TP1_R * risk
        thr = k * a[i0 - 1]
        biaya = (BIAYA_KELUAR[name] if BIAYA_KELUAR[name] is not None else 0.0003 * e) / risk
        r1, kena, jam = float(row.r), False, None
        for j in range(i0, min(i1 + 1, len(t_idx))):
            if (lo[j] <= sl) if sign > 0 else (h[j] >= sl):
                break
            if (h[j] >= tp1) if sign > 0 else (lo[j] <= tp1):
                break
            w = slice(max(i0, j - m + 1), j + 1)
            ref = max(e, h[w].max()) if sign > 0 else min(e, lo[w].min())
            if (ref - c[j]) * sign >= thr:
                r1, kena, jam = (c[j] - e) * sign / risk - biaya, True, j - i0 + 1
                break
        out.append({"t": pd.Timestamp(row.t_signal), "dir": row.dir, "r0": float(row.r), "r1": r1, "kena": kena,
                    "jam": jam})
    return pd.DataFrame(out)


def ringkas(x: pd.DataFrame, satuan: str = "R") -> dict:
    """Δ per periode & per tahun. x: kolom t, r0, r1, kena."""
    if x.empty:
        return {}
    x = x.assign(d=x.r1 - x.r0)
    lama, baru = x[x.t < SPLIT], x[x.t >= SPLIT]
    th = x.groupby(x.t.dt.year).d.sum()
    aktif = th[x.groupby(x.t.dt.year).kena.sum() > 0]
    return {"n": len(x), "kena": int(x.kena.sum()), "d_lama": lama.d.mean() if len(lama) else np.nan,
            "d_baru": baru.d.mean() if len(baru) else np.nan, "tot0_baru": baru.r0.sum(), "tot1_baru": baru.r1.sum(),
            "tot0_lama": lama.r0.sum(), "tot1_lama": lama.r1.sum(),
            "wr0": (x.r0 > 0).mean() * 100, "wr1": (x.r1 > 0).mean() * 100,
            "tahun_ok": float((aktif >= 0).mean() * 100) if len(aktif) else np.nan, "n_tahun": len(aktif),
            "lanjut": float((x.r0 - x.r1)[x.kena].mean()) if x.kena.any() else np.nan,
            "tahun": th.round(2).to_dict(), "satuan": satuan}


def fmt(s: dict, label: str) -> str:
    if not s:
        return f"{label}: tidak ada data"
    u = s["satuan"]
    f = "{:+.3f}" if u == "R" else "{:+.2f}"
    return (f"{label}: n {s['n']} kena {s['kena']} | Δ/sinyal LAMA {f.format(s['d_lama'])}{u} BARU "
            f"{f.format(s['d_baru'])}{u} | total BARU {s['tot0_baru']:+.1f}→{s['tot1_baru']:+.1f}{u} LAMA "
            f"{s['tot0_lama']:+.1f}→{s['tot1_lama']:+.1f}{u} | WR {s['wr0']:.0f}→{s['wr1']:.0f}% | tahun Δ≥0 "
            f"{s['tahun_ok']:.0f}% ({s['n_tahun']}) | setelah guncangan (yang kena) tahan lanjut rata "
            f"{f.format(s['lanjut'])}{u}")


def lolos(grid: dict, key, tetangga: list) -> bool:
    s = grid.get(key) or {}
    if not s or not (s["d_lama"] > 0 and s["d_baru"] > 0 and s["tahun_ok"] >= 60):
        return False
    return all((grid.get(t) or {}).get("d_lama", -1) > 0 and (grid.get(t) or {}).get("d_baru", -1) > 0
               for t in tetangga if t in grid)


def uji_sinyal(L: list[str]) -> None:
    for name in ("XAU", "BTC"):
        rows = pd.read_csv(EXT / "verifikasi" / f"cloud_{name}.csv", parse_dates=["t_signal", "t_close"])
        df = h1(name)
        L += ["", f"## A. 💰 {name} (replay cloud live, {len(rows)} sinyal termasuk lapisan; aturan hanya sebelum TP1)"]
        for arah in ("BUY", "SELL", "semua"):
            sub = rows if arah == "semua" else rows[rows.dir == arah]
            grid = {}
            for k in K_GRID:
                for m in M_GRID:
                    grid[(k, m)] = ringkas(sim_sinyal(sub, df, name, k, m))
            L.append(f"### {arah}")
            for (k, m), s in grid.items():
                ki = K_GRID.index(k)
                tet = [(K_GRID[i], m) for i in (ki - 1, ki + 1) if 0 <= i < len(K_GRID)]
                L.append(("✅ " if lolos(grid, (k, m), tet) else "   ") + fmt(s, f"{k:g} ATR / {m} jam"))
            best = max(grid, key=lambda q: min(grid[q].get("d_lama", -9), grid[q].get("d_baru", -9)))
            L.append(f"   tahun (Δ total R) terbaik {best[0]:g} ATR/{best[1]} jam: {grid[best]['tahun']}")


# ------------------------------------------------------------------ B. 💎 spot
def spot_trades() -> tuple[pd.DataFrame, dict]:
    from .spot_peluang import LIVE, dataset, take, walk_forward
    from .spot_dip2 import MATI
    df, _ = dataset(LIVE + [c for c in MATI if c not in LIVE], 0.03, 10)
    df = df.sort_index(kind="stable")
    df["pg"] = walk_forward(df, 10, "gbm")
    live = df.base.isin(LIVE).to_numpy()
    ok = df.pg.notna().to_numpy()
    rule = ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)).to_numpy() & ok
    tr = take(df, (((df.pg >= 0.93).to_numpy()) | rule) & live)
    hourly = {}
    for coin in tr.coin.unique():
        base = coin.split("#")[0]
        p = EXT / "pair_h1" / f"{base}USD.parquet"
        if base == "BTC":
            hourly[coin] = h1("BTC")
        elif p.exists():
            d = pd.read_parquet(p)[["open", "high", "low", "close"]].astype(float)
            hourly[coin] = d[~d.index.duplicated()].sort_index()
    return tr, hourly


def sim_spot(tr: pd.DataFrame, hourly: dict, btc: pd.DataFrame, x: float | None, m: int, y: float | None,
             my: int = 3, tp: float = 0.03, cost: float = 0.003, murni: bool = False) -> pd.DataFrame:
    """murni=False: turun x% dari harga terbaik sejak entry (termasuk harga entry) dalam m jam; murni=True: hanya
    jatuh di dalam jendela m jam itu sendiri (guncangan mendadak, bukan turun pelan dari entry)."""
    bc = btc.close
    out = []
    for row in tr.itertuples():
        d = hourly.get(row.coin)
        if d is None:
            continue
        t0, t1 = pd.Timestamp(row.t), pd.Timestamp(row.t_out) + pd.Timedelta(days=1)
        seg = d[(d.index >= t0) & (d.index < t1)]
        if seg.empty:
            continue
        e = float(row.e)
        h, c = seg.high.to_numpy(), seg.close.to_numpy()
        r1, kena, jam = float(row.r), False, None
        for j in range(len(seg)):
            if h[j] >= e * (1 + tp):
                break
            ref = h[max(0, j - m + 1):j + 1].max() if murni else max(e, h[max(0, j - m + 1):j + 1].max())
            koin = x is not None and c[j] <= ref * (1 - x)
            pasar = False
            if y is not None:
                tj = seg.index[j]
                w = bc[(bc.index > tj - pd.Timedelta(hours=my)) & (bc.index <= tj)]
                k0 = bc.index.searchsorted(tj - pd.Timedelta(hours=my)) - 1
                if len(w) and k0 >= 0:
                    pasar = w.iloc[-1] <= max(bc.iloc[k0], w.max()) * (1 - y)
            if koin or pasar:
                r1, kena, jam = c[j] / e - 1 - cost, True, j + 1
                break
        out.append({"t": t0, "r0": float(row.r) * 100, "r1": r1 * 100, "kena": kena, "jam": jam, "coin": row.coin})
    return pd.DataFrame(out)


def uji_spot(L: list[str]) -> None:
    tr, hourly = spot_trades()
    btc = h1("BTC")
    L += ["", f"## B. 💎 spot (gabungan 20 koin, {len(tr)} trade 2019–2026, hasil dalam % per trade setelah biaya)"]
    grid = {}
    for x in (0.03, 0.05, 0.08, 0.10, 0.15):
        for m in (1, 3, 6, 24):
            grid[("koin", x, m)] = ringkas(sim_spot(tr, hourly, btc, x, m, None), "%")
    for y in (0.02, 0.03, 0.05):
        for my in (1, 3, 6):
            grid[("btc", y, my)] = ringkas(sim_spot(tr, hourly, btc, None, 1, y, my), "%")
    for x in (0.05, 0.08, 0.10):
        for m in (1, 3):
            grid[("murni", x, m)] = ringkas(sim_spot(tr, hourly, btc, x, m, None, murni=True), "%")
    xs = (0.03, 0.05, 0.08, 0.10, 0.15)
    for key, s in grid.items():
        if key[0] in ("koin", "murni"):
            xi = xs.index(key[1])
            tet = [(key[0], xs[i], key[2]) for i in (xi - 1, xi + 1) if 0 <= i < len(xs)]
            label = (f"koin −{key[1] * 100:g}% / {key[2]} jam" if key[0] == "koin"
                     else f"guncangan murni koin −{key[1] * 100:g}% dalam {key[2]} jam")
        else:
            ys = (0.02, 0.03, 0.05)
            yi = ys.index(key[1])
            tet = [("btc", ys[i], key[2]) for i in (yi - 1, yi + 1) if 0 <= i < len(ys)]
            label = f"BTC −{key[1] * 100:g}% / {key[2]} jam"
        L.append(("✅ " if lolos(grid, key, tet) else "   ") + fmt(s, label))


# ------------------------------------------------------------------ C. 🔗 pulih
def uji_pulih(L: list[str]) -> None:
    import functools
    from datetime import timedelta
    sys.path.insert(0, str(ROOT / "cloud" / "api"))
    import _core  # noqa: E402
    import _pulih  # noqa: E402
    from . import xau_kripto as X
    from .pulih_replay import Mem, Pub
    xau, cr = X.muat()
    _core.market_open = functools.lru_cache(maxsize=None)(_core.market_open)
    bars = [_core.Bar(t.to_pydatetime(), o, h, lo, c) for t, o, h, lo, c in
            zip(xau.index, xau.open, xau.high, xau.low, xau.close)]
    btc_daily = {d.strftime("%Y-%m-%d"): float(v) for d, v in cr.BTC.resample("D").last().dropna().items()}
    kol = [c for c in _pulih.KOIN if c in cr.columns]
    arr = cr[kol].copy()
    arr.attrs = {}                       # attrs berisi Series (btc_hl) → pd.concat gagal membandingkan
    mem, pub, ref = Mem(), Pub(), {"t": None}

    def prices(koin):
        k = arr.index.get_indexer([ref["t"]], method="ffill")[0]
        row = arr.iloc[k]
        return {c: float(row[c]) for c in koin if c in row and not np.isnan(row[c])}
    for i, b in enumerate(bars):
        if b.t < X.MULAI.to_pydatetime():
            continue
        ref["t"] = pd.Timestamp(b.t)
        _pulih.pulih_tick(b.t + timedelta(hours=1, minutes=2), bars[max(0, i - 2400):i + 2], mem, pub,
                          lambda: btc_daily, prices)
    sig = [e for e in pub.ev if e["type"] == "pulih_signal"]
    L += ["", f"## C. 🔗 pulih (replay kode cloud, {len(sig)} keranjang 2018–2026, % rata-rata keranjang setelah biaya)"]
    for x in (0.02, 0.03, 0.05, 0.08):
        for m in (1, 3, 6):
            rows = []
            for ev in sig:
                t0 = pd.Timestamp(ev["time"]).floor("h")
                seg = arr[(arr.index >= t0) & (arr.index <= t0 + pd.Timedelta(hours=48))]
                ent = {c: v for c, v in ev["koin"].items() if v}
                bk = pd.concat([seg[c] / v - 1 for c, v in ent.items() if c in seg], axis=1).mean(axis=1)
                if bk.empty:
                    continue
                r0 = bk.iloc[-1] - 0.002
                r1, kena = r0, False
                val = 1 + bk.to_numpy()
                for j in range(len(val)):
                    top = max(1.0, val[max(0, j - m + 1):j + 1].max())
                    if val[j] <= top * (1 - x):
                        r1, kena = val[j] - 1 - 0.002, True
                        break
                rows.append({"t": t0, "r0": r0 * 100, "r1": r1 * 100, "kena": kena})
            L.append("   " + fmt(ringkas(pd.DataFrame(rows), "%"), f"keranjang −{x * 100:g}% / {m} jam"))


# ------------------------------------------------------------------ D. 🌊 ikut arus
def uji_arus(L: list[str]) -> None:
    sys.path.insert(0, str(ROOT / "cloud" / "api"))
    import _arus  # noqa: E402
    from . import pisau as P
    from .pisau_cek import trades
    series = {x.name: x for x in P.load()}
    L += ["", "## D. 🌊 ikut arus (aturan cloud _arus.RULES, riset pisau_cek; R setelah biaya)"]
    for asset, rule in _arus.RULES.items():
        sr = series[asset]
        tr = trades(sr, rule["move"], rule["n"], rule["k"], "l_brk" if rule["mode"] == "stop" else "l_mkt", rule["tren"],
                    rule["sl"], rule["tp"], rule["h"])
        h, lo, c, tt = sr.h, sr.l, sr.c, sr.t
        a14 = atr14(pd.DataFrame({"high": h, "low": lo, "close": c}))
        for k in (2.0, 3.0, 4.0):
            for m in (1, 3):
                rows = []
                for x in tr.itertuples():
                    j0, d, e = int(x.j0), int(x.dir), float(x.e)
                    risk = abs(e - float(x.sl))
                    k_out = int(tt.searchsorted(pd.Timestamp(x.t_out)))
                    r1, kena = float(x.R), False
                    for j in range(j0, k_out):
                        w = slice(max(j0, j - m + 1), j + 1)
                        ref = max(e, h[w].max()) if d > 0 else min(e, lo[w].min())
                        if (ref - c[j]) * d >= k * a14[max(j0 - 1, 0)]:
                            r1, kena = (c[j] - e) * d / risk, True     # e sudah termasuk biaya pulang-pergi
                            break
                    rows.append({"t": pd.Timestamp(x.t), "r0": float(x.R), "r1": r1, "kena": kena})
                L.append("   " + fmt(ringkas(pd.DataFrame(rows)), f"{asset} {'BUY' if rule['move'] > 0 else 'SELL'} "
                                                                    f"{k:g} ATR / {m} jam"))


def main() -> None:
    L = ["# 🛑 Batalkan / tutup sinyal saat guncangan harga (proksi pernyataan penting)", __doc__.split("\n\n")[2], ""]
    bagian = sys.argv[1:] or ["sinyal", "spot", "pulih", "arus"]
    if "sinyal" in bagian:
        uji_sinyal(L)
    if "spot" in bagian:
        uji_spot(L)
    if "pulih" in bagian:
        uji_pulih(L)
    if "arus" in bagian:
        uji_arus(L)
    out = OUT if sys.argv[1:] in ([], ["sinyal", "spot", "pulih", "arus"]) else OUT.with_name(
        OUT.stem + "_" + "_".join(bagian) + ".txt")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
