"""Verifikasi menyeluruh sinyal 💰 (3 Okt 2026) — python -m research.verifikasi [--cepat]

Permintaan pengguna: "pastikan lagi ... CEK, VERIFIKASI, UJI secara MENYELURUH" sebelum apa pun dipasang.
Butuh hasil replay kode cloud: python -m research.verifikasi_cloud XAU|BTC [--mentah] [--td].

1. Kode cloud asli (replay, --mentah) vs mesin riset (sl_tangga, hanya 💰 dikirim): kecocokan sinyal (set, arah,
   candle sinyal), kategori, dan R.
2. Konfigurasi LIVE (filter H4 XAU, funding & September BTC, lapisan) setelah spread ASLI Exness per jam
   (XAUUSDc / BTCUSDm, research/exness.spread_table): LAMA (< Okt 2021) / BARU / 2026, per kategori & per tahun,
   interval kepercayaan 95% (bootstrap) dan t.
3. Look-ahead: kategori dihitung ulang dari data yang DIPOTONG di candle sinyal (--cepat: dilewati).
4. Sumber data: replay live di data Twelve Data (feed cloud) vs data riset, periode yang sama.
5. Pilihan kategori: 💰 vs bukan-💰 (semua sinyal diberi label, p-acak) per periode.
Menulis docs/eksternal/hasil_verifikasi.txt dan cloud/api/riwayat.json (kartu 📜 aplikasi: angka = replay live).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import EXT, MONEY, asset, perm_p
from .exness import spread_table
from .filters import features
from .gap_study import week_info
from .kategori_badge import go
from .sl_tangga import backtest
from .strategy_lab import Bars
from .strategy_lab2 import STAR, signals, trend_states

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_verifikasi.txt"
JSON_OUT = ROOT / "cloud" / "api" / "riwayat.json"
VER = EXT / "verifikasi"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
Y26 = pd.Timestamp("2026-01-01", tz="UTC")
KEY = {"XAU": "XAUUSD", "BTC": "BTCUSD"}
EXN = {"XAU": "XAUUSDc", "BTC": "BTCUSDm"}
SETS = ("T40/15", "T55/20", "T80/30")
# kategori yang dikirim cloud SEKARANG (BTC konf dimatikan 3 Okt 2026, tick.py BTC_SKIP_KONF)
DIKIRIM = {"XAU": ("konf+⭐", "konf"), "BTC": ("konf+⭐", "⭐")}
rng = np.random.default_rng(11)


def load(name: str, tag: str = "") -> pd.DataFrame:
    df = pd.read_csv(VER / f"cloud_{name}{tag}.csv", parse_dates=["t_signal", "t_close"])
    df["bar"] = pd.to_datetime(df.id.str.rstrip("L").str.rsplit("-", n=1).str[-1], format="%Y%m%d%H%M", utc=True)
    return df


def spread_at(name: str, times: pd.Series) -> np.ndarray:
    """Spread asli Exness (median per jam) pada jam entry; jam tanpa data -> median tahunannya (tahun sebelum data
    pertama -> tahun pertama)."""
    t = spread_table(EXN[name])
    t.index = pd.to_datetime(t.index, utc=True)
    med = t["median"]
    yearly = med.groupby(med.index.year).median()
    hour = pd.DatetimeIndex(times).floor("h")
    out = med.reindex(hour).to_numpy(float)
    years = np.clip(hour.year, yearly.index.min(), yearly.index.max())
    fill = yearly.reindex(years).to_numpy(float)
    return np.where(np.isnan(out), fill, out)


def net(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """R bersih: setiap posisi membayar spread sekali -> R rata-rata per posisi dikurangi spread/risk."""
    df = df.copy()
    df["spread"] = spread_at(name, df.t_signal)
    df["R"] = df.r - df.spread / df.risk
    return df


def cell(r: pd.Series) -> dict:
    r = pd.Series(r, dtype=float)
    return {"n": int(len(r)), "wr": round(float((r > 0).mean() * 100), 1) if len(r) else 0.0,
            "avg": round(float(r.mean()), 3) if len(r) else 0.0, "tot": round(float(r.sum()), 1)}


def st(df: pd.DataFrame, col: str = "R") -> str:
    if len(df) < 2:
        return f"n{len(df)}"
    r = df[col].to_numpy(float)
    eq = np.cumsum(df.sort_values("t_close")[col].to_numpy(float))
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    boot = r[rng.integers(0, len(r), (4000, len(r)))].mean(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if r.std(ddof=1) > 0 else 0.0
    return (f"n{len(r):5} WR {(r > 0).mean() * 100:4.1f}% {r.mean():+.3f}R/sin [CI95 {lo:+.2f}..{hi:+.2f}] "
            f"t {t:4.1f} total {r.sum():+7.1f}R DD {dd:6.1f}")


def periods(df: pd.DataFrame, L: list, label: str, col: str = "R") -> None:
    L.append(f"  {label}")
    for per, m in (("LAMA", df.t_signal < SPLIT), ("BARU", df.t_signal >= SPLIT), ("2026", df.t_signal >= Y26)):
        L.append(f"    {per}: {st(df[m], col)}")


def riset_sets(name: str) -> pd.DataFrame:
    """Mesin riset (hanya 💰 dikirim) dengan label set & candle sinyal, untuk dicocokkan dengan cloud."""
    key = KEY[name]
    b = asset(key).b
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))
    cats, rows = {}, []

    def allow(i, d):
        if key == "XAUUSD" and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        c = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        cats[i] = c
        return c in MONEY[key]
    pos = {t: k for k, t in enumerate(b.t)}
    for setname, (li, si, lo, so) in zip(SETS, signals(b, "donchian")):
        for t_in, t_out, r, d, _ in backtest(b, li, si, lo, so, allow, tps=[1.0, None, None, None, None]):
            i = pos[t_in] - 1
            rows.append({"set": setname, "dir": "BUY" if d > 0 else "SELL", "bar": b.t[i], "cat": cats[i],
                         "t_signal": t_in, "t_close": t_out, "R": r})
    return pd.DataFrame(rows)


def bagian1(name: str, L: list) -> None:
    cl = load(name, "_mentah")
    cl = cl[~cl.lapis]
    rs = riset_sets(name)
    rs = rs[rs.t_signal >= cl.t_signal.min()]
    k = ["set", "dir", "bar"]
    m = cl.merge(rs, on=k, how="outer", suffixes=("_c", "_r"), indicator=True)
    both = m[m._merge == "both"]
    L.append(f"  sinyal cloud {len(cl)} | riset {len(rs)} | sama persis (set+arah+candle) {len(both)} "
             f"({len(both) / max(len(cl), 1) * 100:.0f}% cloud, {len(both) / max(len(rs), 1) * 100:.0f}% riset)")
    L.append(f"  kategori sama pada sinyal yang cocok: {(both.cat_c == both.cat_r).mean() * 100:.1f}%")
    rc, rr = both.r, both.R
    L.append(f"  R sinyal yang cocok: korelasi {np.corrcoef(rc, rr)[0, 1]:.3f}, tanda sama "
             f"{np.mean(np.sign(rc) == np.sign(rr)) * 100:.0f}%, rata-rata cloud (tanpa spread) {rc.mean():+.3f} vs "
             f"riset (dengan spread) {rr.mean():+.3f}")
    only_c, only_r = m[m._merge == "left_only"], m[m._merge == "right_only"]
    L.append(f"  hanya di cloud: n{len(only_c)} R/sin {only_c.r.mean():+.3f} | hanya di riset: n{len(only_r)} "
             f"R/sin {only_r.R.mean():+.3f}")
    c2 = cl.rename(columns={"r": "Rc"})
    for per, a, b_ in (("LAMA", None, SPLIT), ("BARU", SPLIT, None)):
        sel_c = c2[((c2.t_signal >= a) if a is not None else True) & ((c2.t_signal < b_) if b_ is not None else True)]
        sel_r = rs[((rs.t_signal >= a) if a is not None else True) & ((rs.t_signal < b_) if b_ is not None else True)]
        L.append(f"  {per}: cloud mentah {sel_c.Rc.mean():+.3f}R/sin (n{len(sel_c)}, tanpa spread) | riset "
                 f"{sel_r.R.mean():+.3f}R/sin (n{len(sel_r)}, spread riset)")


def bagian2(name: str, L: list, js: dict) -> pd.DataFrame:
    df = net(name, load(name))
    base, lay = df[~df.lapis], df[df.lapis]
    L.append(f"  spread asli rata-rata: {df.spread.mean():.3f} (= {(df.spread / df.risk).mean():.3f}R per posisi)")
    periods(base, L, "sinyal dasar (yang Anda terima, lot penuh)")
    for c, g in base.groupby("cat"):
        periods(g, L, f"kategori {c}")
    if len(lay):
        periods(lay, L, "lapisan 🔁 (lot ½)")
    yr = base.groupby(base.t_signal.dt.year).R.agg(["count", "sum", "mean"]).round(2)
    L.append("  total R per tahun (dasar): " + ", ".join(f"{y}: {s:+.0f} ({int(n)})" for y, (n, s, _) in yr.iterrows()))
    end = base.t_signal.max()
    js[name] = {
        "sampai": f"{end:%Y-%m-%d}",
        "tahun": {str(y): cell(g.R) for y, g in base.groupby(base.t_signal.dt.year)},
        "90h": cell(base[base.t_signal > end - pd.Timedelta(days=90)].R),
        "365h": cell(base[base.t_signal > end - pd.Timedelta(days=365)].R),
        "semua": cell(base.R),
        "risk_med": round(float(base[base.t_signal > end - pd.Timedelta(days=365)].risk.median()), 2),
        "lama": cell(base[base.t_signal < SPLIT].R),
        "baru": cell(base[base.t_signal >= SPLIT].R),
        "kat": {c: {"baru": cell(g[g.t_signal >= SPLIT].R), "tahun_ini": cell(g[g.t_signal >= Y26].R),
                    "semua": cell(g.R), "dikirim": c in DIKIRIM[name]} for c, g in base.groupby("cat")},
        "lapis": {"baru": cell(lay[lay.t_signal >= SPLIT].R), "semua": cell(lay.R)} if len(lay) else None,
    }
    return base


def bagian3(L: list) -> None:
    for key in ("XAUUSD", "BTCUSD"):
        A = asset(key)
        b = A.b
        f, s = features(b.df), trend_states(b)
        sig = A.sig.sample(150, random_state=3)
        same = 0
        for r in sig.itertuples():
            i, d = int(r.i), int(r.dir)
            full = (bool(STAR(f, i, d)), s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d)
            tb = Bars(b.df.iloc[: i + 1], "0.03%" if key == "BTCUSD" else 0.30)
            ft, stt = features(tb.df), trend_states(tb)
            same += full == (bool(STAR(ft, i, d)), stt["ema"][i] == d and stt["st"][i] == d and stt["mom"][i] == d)
        L.append(f"  {key}: kategori dengan data dipotong di candle sinyal = data penuh pada {same}/150 sinyal acak")


def bagian4(name: str, L: list) -> None:
    p = VER / f"cloud_{name}_td.csv"
    if not p.exists():
        L.append(f"  {name}: replay Twelve Data belum ada")
        return
    td = net(name, load(name, "_td"))
    rs = net(name, load(name))
    start = td.t_signal.min() + pd.Timedelta(days=30)
    td, rs = td[(td.t_signal >= start) & ~td.lapis], rs[(rs.t_signal >= start) & ~rs.lapis]
    end = min(td.t_signal.max(), rs.t_signal.max())
    td, rs = td[td.t_signal <= end], rs[rs.t_signal <= end]
    k = ["set", "dir", "bar"]
    both = td.merge(rs, on=k, suffixes=("_td", "_rs"))
    L.append(f"  {name} {start:%Y-%m}..{end:%Y-%m}: Twelve Data {st(td)}")
    L.append(f"  {name} {start:%Y-%m}..{end:%Y-%m}: data riset  {st(rs)}")
    L.append(f"  sinyal sama di kedua sumber: {len(both)} ({len(both) / max(len(td), 1) * 100:.0f}% dari Twelve Data)")


def bagian5(L: list) -> None:
    for key in ("XAUUSD", "BTCUSD"):
        a = go(key, None)
        for per, m in (("LAMA", a.t < SPLIT), ("BARU", a.t >= SPLIT), ("2026", a.t >= Y26)):
            x = a[m]
            keep = x.cat.isin(MONEY[key]).to_numpy()
            r = x.R.to_numpy()
            L.append(f"  {key} {per}: 💰 {r[keep].mean():+.3f} (n{keep.sum()}) vs bukan-💰 {r[~keep].mean():+.3f} "
                     f"(n{(~keep).sum()}) p-acak {perm_p(r, keep):.3f}")


def klaim(L: list, label: str, x: pd.DataFrame, col: str, wr_k, avg_k, n_k=None) -> None:
    """Satu baris: klaim (WR, R/sinyal) vs hasil replay (semua periode & sejak Okt 2021)."""
    if len(x) == 0:
        L.append(f"  {label}: tidak ada sinyal di replay")
        return
    b = x[x.t_signal >= SPLIT]
    L.append(f"  {label}: KLAIM WR {wr_k:.0f}% {avg_k:+.2f}R" + (f" (n {n_k})" if n_k else "") +
             f" | REPLAY semua WR {(x[col] > 0).mean() * 100:.0f}% {x[col].mean():+.2f}R (n {len(x)})"
             f" | sejak Okt 2021 WR {(b[col] > 0).mean() * 100:.0f}% {b[col].mean():+.2f}R (n {len(b)})")


def bagian6(L: list, js: dict) -> None:
    from . import verifikasi_cloud as vc
    from .eksternal_berita import MAIN, calendar
    from .sinyal_berita import tag
    core = vc._core
    lap = json.loads((ROOT / "cloud" / "api" / "sinyal_lapis.json").read_text(encoding="utf-8"))
    ber = json.loads((ROOT / "cloud" / "api" / "sinyal_berita.json").read_text(encoding="utf-8"))
    cal = calendar()
    for n in ("XAU", "BTC"):
        df = net(n, load(n))
        df["R07"] = df.r07 - df.spread / df.risk
        base, lay = df[~df.lapis], df[df.lapis]
        L.append(f" {n}")
        L.append("  a) badge di teks notifikasi (_core.STATS, semua periode, 'semua sinyal diberi label'):")
        for c, g in base.groupby("cat"):
            wr, avg, nn, per = core.STATS[f"{n} {c}"]
            klaim(L, f"     {c}", g, "R", wr, avg, nn)
        zap = base[base.tier == "zap"]
        t = core.TIER_STATS[n]
        L.append("  b) ⚡ kesempatan emas (_core.TIER_STATS):")
        klaim(L, "     skema bawaan", zap, "R", t[0], t[1], t[4])
        klaim(L, "     SL+ 0,7R", zap, "R07", t[2], t[3], t[4])
        if n == "BTC":
            L.append("  c) BTC dengan skema aplikasi (SL+ otomatis 0,7R) — semua sinyal dasar:")
            klaim(L, "     SL+ 0,7R vs bawaan", base, "R07", (base.R > 0).mean() * 100, base.R.mean())
        st_ = lap[n]["stats"]
        L.append("  d) lapisan 🔁 (sinyal_lapis.json):")
        klaim(L, "     lapisan", lay, "R", st_["wr"], st_["avg_r"], st_["n"])
        sig = base.rename(columns={"t_signal": "t"}).assign(dir=np.where(base.dir == "BUY", 1, -1))
        after, _ = tag(sig, cal, MAIN, 4)
        b = ber[n]
        L.append("  e) tanda 📰 ≤ 4 jam setelah berita (sinyal_berita.json):")
        klaim(L, "     setelah berita", base[after], "R", b["setelah"]["wr"], b["setelah"]["avg"], b["setelah"]["n"])
        klaim(L, "     tanpa berita", base[~after], "R", b["dasar"]["wr"], b["dasar"]["avg"])
        js[n]["skema07"] = {"baru": cell(base[base.t_signal >= SPLIT].R07), "semua": cell(base.R07)}


def main() -> None:
    cepat = "--cepat" in sys.argv
    L = ["# Verifikasi menyeluruh sinyal 💰 (research/verifikasi.py)", ""]
    js = {"dibuat": "research/verifikasi.py — replay kode cloud asli (konfigurasi live) + spread asli Exness",
          "skema": "TP1 1R + 4 jalan, SL+ entry±0,10 setelah TP1 (seperti cloud)"}
    L.append("## 1. Kode cloud asli (replay) vs mesin riset — tanpa filter tambahan, tanpa lapisan")
    for n in ("XAU", "BTC"):
        L.append(f" {n}")
        bagian1(n, L)
    L.append("\n## 2. Konfigurasi LIVE (filter + lapisan), R bersih setelah spread asli Exness")
    for n in ("XAU", "BTC"):
        L.append(f" {n}")
        bagian2(n, L, js)
    L.append("\n## 3. Look-ahead")
    if cepat:
        L.append("  dilewati (--cepat)")
    else:
        bagian3(L)
    L.append("\n## 4. Sumber data: Twelve Data (feed cloud) vs data riset, replay live")
    for n in ("XAU", "BTC"):
        bagian4(n, L)
    L.append("\n## 5. Apakah pilihan kategori 💰 menambah nilai? (semua sinyal diberi label, spread riset)")
    bagian5(L)
    for n in ("XAU", "BTC"):                 # semua kategori (termasuk yang tidak dikirim) untuk kartu 🏆 aplikasi
        if (VER / f"cloud_{n}_semua.csv").exists():      # replay kode cloud, semua kategori dikirim, spread asli
            a = net(n, load(n, "_semua")).rename(columns={"t_signal": "t"})
        else:                                            # cadangan: mesin riset (spread riset)
            a = go(KEY[n], None)
        js[n]["kat_semua"] = {c: {"baru": cell(g[g.t >= SPLIT].R), "tahun_ini": cell(g[g.t >= Y26].R),
                                  "dikirim": c in DIKIRIM[n]} for c, g in a.groupby("cat")}
    L.append("\n## 6. Angka yang tampil di aplikasi/notifikasi vs replay kode cloud (spread asli)")
    bagian6(L, js)
    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    JSON_OUT.write_text(json.dumps(js, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT} dan {JSON_OUT}")


if __name__ == "__main__":
    main()
