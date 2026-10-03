"""Cek data + uji ulang hanya saat pasar TENANG (3 Okt 2026) — python -m research.tenang

Permintaan pengguna: "mungkin datamu salah; skip news, skip crash, pilih yang tenang saja sampai volatilitas turun".
1. Cek data: XAU H1 dari data riset vs Twelve Data H1 (sumber terpisah), 2020-06 → 2026-10.
2. Filter TENANG per bar (semua memakai info sebelum bar itu):
   - berita: tidak ada berita USD high-impact dalam 60 mnt ke depan / 120 mnt ke belakang (ForexFactory s/d Jan 2026;
     sesudahnya tanggal rilis resmi FRED: CPI, NFP, PPI, GDP, PCE, Retail 08:30 ET + jadwal FOMC 2026 14:00 ET);
   - crash: tidak ada gerak ≥ 3 × ATR H1 dalam 60 mnt selama 4 jam terakhir;
   - volatilitas: ATR H1 ≤ median ATR 20 hari ("sampai volatilitas turun").
   Grid/martingale: keranjang baru hanya saat tenang; mode "lindung" juga menutup keranjang 15 mnt sebelum berita dan
   saat crash terdeteksi.
3. Uji ulang: 10 strategi blueprint, grid/martingale (rekonstruksi Signal Strike & versi $400), piramida.
LAMA = < Okt 2021, BARU = Okt 2021+.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import piramida
from .blueprint10 import Data, jalankan as bp_jalankan, ringkas as bp_ringkas, sinyal
from .data import resample
from .grid_cari import fitur
from .martingale_ea import SPLIT, USC, arrays, load, sim
from .news_data import load_calendar
from .signal_strike import MODAL_TG

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "research"
OUT = ROOT / "docs" / "eksternal" / "hasil_tenang.txt"
FRED_RILIS = (10, 50, 46, 53, 54, 9)            # CPI, NFP, PPI, GDP, PCE, Retail (08:30 ET)
FOMC_2026 = ("2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16")   # 14:00 ET


def kalender() -> pd.DatetimeIndex:
    cal = load_calendar(DATA)
    t = list(cal.time)
    akhir = cal.time.max()
    for rid in FRED_RILIS:
        p = DATA / "eksternal" / f"fred_release_{rid}.json"
        if not p.exists():
            continue
        for r in json.loads(p.read_text())["release_dates"]:
            x = pd.Timestamp(r["date"] + " 08:30").tz_localize("America/New_York").tz_convert("UTC")
            if x > akhir:
                t.append(x)
    t += [pd.Timestamp(d + " 14:00").tz_localize("America/New_York").tz_convert("UTC") for d in FOMC_2026]
    return pd.DatetimeIndex(sorted(set(t))).as_unit("ns")


def masker(bars: pd.DataFrame, ev: pd.DatetimeIndex, k_vol: float = 1.0, crash_x: float = 3.0,
           pre: int = 60, post: int = 120, tutup_pre: int = 15) -> tuple[np.ndarray, np.ndarray, dict]:
    idx = bars.index
    tn = idx.asi8
    h1 = resample(bars, "1h")
    tr = pd.concat([h1.high - h1.low, (h1.high - h1.close.shift()).abs(), (h1.low - h1.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr_b = atr.shift(1).reindex(idx.floor("h")).ffill().to_numpy()
    med_b = atr.rolling(480).median().shift(1).reindex(idx.floor("h")).ffill().to_numpy()
    calm = atr_b <= k_vol * med_b
    hi60 = bars.high.rolling("60min").max().to_numpy()
    lo60 = bars.low.rolling("60min").min().to_numpy()
    crash = ((hi60 - bars.low.to_numpy()) >= crash_x * atr_b) | ((bars.high.to_numpy() - lo60) >= crash_x * atr_b)
    until = np.maximum.accumulate(np.where(crash, tn + 4 * 3_600_000_000_000, 0))
    crash_blk = np.r_[False, until[:-1] > tn[1:]]
    e = ev.asi8
    k = np.searchsorted(e, tn)
    nxt = np.where(k < len(e), e[np.minimum(k, len(e) - 1)], np.iinfo(np.int64).max)
    prv = np.where(k > 0, e[np.maximum(k - 1, 0)], np.iinfo(np.int64).min // 2)
    m = 60_000_000_000
    news_blk = ((nxt - tn) <= pre * m) | ((tn - prv) <= post * m)
    ok = np.isfinite(atr_b) & np.isfinite(med_b)
    tenang = ok & calm & ~crash_blk & ~news_blk
    tutup = ((nxt - tn) <= tutup_pre * m) | np.r_[False, crash[:-1]]
    info = dict(tenang=tenang.mean(), calm=np.nanmean(calm), crash=crash_blk.mean(), news=news_blk.mean())
    return tenang, tutup, info


def cek_data(df: pd.DataFrame, out: list) -> None:
    td = pd.read_parquet(DATA / "eksternal" / "twelvedata_h1" / "XAUUSD.parquet")
    td.index = pd.DatetimeIndex(td.index).tz_convert("UTC") if td.index.tz else pd.DatetimeIndex(td.index).tz_localize("UTC")
    td = td[td.index.dayofweek < 5]
    h1 = resample(df, "1h")
    j = h1[["close"]].join(td[["close"]].rename(columns={"close": "td"}), how="inner").dropna()
    j = j[(j.index >= pd.Timestamp("2020-06-01", tz="UTC")) & (j.index < df.index[-1].floor("h"))]
    d = (j.close - j.td).abs()
    r1, r2 = j.close.pct_change(), j.td.pct_change()
    arah = (np.sign(r1) == np.sign(r2))[r1.abs() > 0.0005].mean()
    out.append(f"1. Cek data XAU H1 vs Twelve Data (independen), {j.index[0]:%Y-%m} → {j.index[-1]:%Y-%m}, {len(j):,} jam: "
               f"selisih close median ${d.median():.2f}, P95 ${d.quantile(0.95):.2f}; korelasi return per jam "
               f"{r1.corr(r2):.3f}; arah candle sama {100 * arah:.1f}% (gerak > 0,05%). Per tahun selisih median: "
               + " ".join(f"{y}:${v:.2f}" for y, v in d.groupby(d.index.year).median().items()))
    rng = (df.high - df.low)
    out.append(f"   Bar janggal (range > 15× median 1 hari): {int((rng > 15 * rng.rolling('1D').median()).sum())} dari "
               f"{len(df):,}; duplikat waktu: {int(df.index.duplicated().sum())}.")


def bulan_sim(df, v, izin, tutup, akhir_pekan: bool) -> pd.DataFrame:
    t = df.index
    c = arrays(df)[3]
    awal = pd.date_range(pd.Timestamp("2012-06-01", tz="UTC"), t[-1], freq="MS")
    rows = []
    for a, b in zip(awal[:-1], awal[1:]):
        i0, i1 = max(int(t.searchsorted(a)), 1), int(t.searchsorted(b))
        cl, ruins, _, st = sim(df, *v[1:9], i0=i0, i1=i1, stop=True, jeda_menit=v[9], izin=izin, tutup_arr=tutup,
                               akhir_pekan=akhir_pekan)
        flo = 0.0
        if not len(ruins) and st["n"]:
            flo = USC * (st["sl"] * st["d"] * c[i1 - 1] - st["sc"]) + st["bal"] - v[7]
        rows.append(dict(t=a, usd=(cl.usc.sum() + flo - len(ruins) * v[7]) / 100, habis=len(ruins) > 0))
    return pd.DataFrame(rows)


def ringkas_bulan(m: pd.DataFrame) -> str:
    out = []
    for lab, sel in (("LAMA", m.t < SPLIT), ("BARU", m.t >= SPLIT), ("12bln", m.t >= pd.Timestamp("2025-10-01", tz="UTC"))):
        x = m[sel]
        out.append(f"{lab} {x.usd.mean():+5.0f}$/bln habis {100 * x.habis.mean():3.0f}% ≥$150 {100 * (x.usd >= 150).mean():3.0f}%")
    return " | ".join(out)


def main() -> None:
    out: list[str] = []
    df = load()
    cek_data(df, out)
    ev = kalender()
    out.append(f"   Kalender berita USD: {len(ev):,} rilis 2012–2026 (2026: {int((ev.year == 2026).sum())}).")
    ten, tut, info = masker(df, ev)
    out.append(f"2. Waktu 'tenang' {100 * info['tenang']:.0f}% bar (volatilitas ≤ median {100 * info['calm']:.0f}%, jeda crash "
               f"{100 * info['crash']:.0f}%, jendela berita {100 * info['news']:.0f}%).")
    out.append("")
    print("\n".join(out), flush=True)

    # 3a. blueprint
    D = Data()
    S = sinyal(D)
    ten15, _, _ = masker(D.b, ev)
    x = D.x
    up4 = x.up4.reindex(D.b.index.floor("h")).ffill().to_numpy()
    upd = x.upd.reindex(D.b.index.floor("h")).ffill().to_numpy()

    def f_ten(j, d):
        return bool(ten15[j])

    def f_ten_tren(j, d):
        return bool(ten15[j]) and ((d > 0 and up4[j] == 1 and upd[j] == 1) or (d < 0 and up4[j] == 0 and upd[j] == 0))

    out.append("3a. 10 strategi blueprint — R per trade LAMA / BARU (WR BARU); kolom: tanpa filter | tenang | tenang + tren2")
    rows = []
    for nama, sig in S.items():
        for ke in ("2R", "1R", "0,5R", "F"):
            cell = []
            for fl, fn in (("-", None), ("tenang", f_ten), ("tenang+tren2", f_ten_tren)):
                r = bp_ringkas(bp_jalankan(D, sig, ke, saring=fn))
                rows.append(dict(strategi=nama, keluar=ke, filter=fl, **r))
                cell.append(f"{r['L_avg']:+.2f}/{r['B_avg']:+.2f} ({r['B_wr']:.0f}%, n {r['L_n']}/{r['B_n']})")
            out.append(f"  {nama:22s} {ke:4s} " + " | ".join(cell))
    bp = pd.DataFrame(rows)
    bp.to_csv(OUT.with_name("hasil_tenang_blueprint.csv"), index=False, float_format="%.4f")
    lolos = bp[(bp["filter"] != "-") & (bp.L_n >= 100) & (bp.L_avg > 0) & (bp.L_t >= 2) & (bp.L_th >= 0.7)]
    out.append(f"  Lolos seleksi LAMA (n ≥ 100, > 0, t ≥ 2, ≥ 70% tahun +) dengan filter tenang: {len(lolos)}"
               + ("".join(f"\n    {r.strategi} {r.keluar} {r.filter}: LAMA {r.L_avg:+.2f} (t {r.L_t:.1f}) → BARU {r.B_avg:+.2f}"
                          f" (t {r.B_t:.1f}, WR {r.B_wr:.0f}%)" for r in lolos.itertuples())))
    hw = bp[(bp["filter"] != "-") & (bp.L_wr >= 60) & (bp.B_wr >= 60)]
    out.append(f"  WR ≥ 60% di LAMA & BARU dengan filter tenang: {len(hw)} kombinasi, rata-rata R LAMA {hw.L_avg.mean():+.3f}"
               f" / BARU {hw.B_avg.mean():+.3f}; yang positif di keduanya: {int(((hw.L_avg > 0) & (hw.B_avg > 0)).sum())}")
    out.append("")
    print("\n".join(out[-4:]), flush=True)

    # 3b. grid / martingale
    izin = np.where(ten, 1, 0).tolist()
    tutup = tut.tolist()
    G = [("G1 rekonstruksi Signal Strike 0,07/$524 x1,2", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 45),
         ("G2 $400 x2 0,01 jarak $2,25", 1, 0.01, 2.0, 2.25, 1.9, 40, 40_000.0, False, 45),
         ("G3 $400 x2 0,01 jarak $5", 1, 0.01, 2.0, 5.0, 1.9, 40, 40_000.0, False, 45),
         ("G4 $400 x1,2 0,05 jarak $2,25", 1, 0.05, 1.2, 2.25, 1.9, 40, 40_000.0, True, 45)]
    out.append("3b. Grid/martingale (akun baru tiap bulan): tanpa filter / hanya buka saat tenang / + tutup sebelum berita & saat"
               " crash / + tutup akhir pekan")
    for v in G:
        out.append(f"  {v[0]}")
        for lab, iz, tu, ap in (("tanpa filter", None, None, False), ("buka saat tenang", izin, None, False),
                                ("tenang + lindung", izin, tutup, False), ("tenang + lindung + akhir pekan", izin, tutup, True)):
            out.append(f"    {lab:30s} " + ringkas_bulan(bulan_sim(df, v, iz, tu, ap)))
        print("\n".join(out[-5:]), flush=True)
    out.append("")

    # 3c. piramida
    f = fitur(df)
    piramida._init(df, f)
    z = piramida.arah(f, "tren2")
    gate = np.where(ten, z, 0).tolist()
    out.append("3c. Piramida (tren2, stop 2 ATR, maks 6): R per keranjang LAMA / BARU, $/bln pada risiko 0,5% ($400)")
    for cfg in piramida.TERPILIH:
        for lab, g in (("biasa", None), ("hanya buka saat tenang", gate)):
            d = piramida.jalankan(cfg, detail=True, gate=g)
            s = []
            for nm, sel in (("LAMA", d.tutup < SPLIT), ("BARU", d.tutup >= SPLIT)):
                xx = d[sel]
                bln = max((xx.tutup.max() - xx.tutup.min()).days / 30.44, 1)
                tt = xx.r.mean() / xx.r.std(ddof=1) * np.sqrt(len(xx))
                s.append(f"{nm} n {len(xx)} {xx.r.mean():+.3f}R (t {tt:.1f}, WR {100 * (xx.r > 0).mean():.0f}%) ${xx.r.sum() * 2 / bln:+.1f}/bln")
            out.append(f"  jarak {cfg[1]:.0f} ATR {lab:24s} " + " | ".join(s))
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[-8:]))
    print("->", OUT)


if __name__ == "__main__":
    main()
