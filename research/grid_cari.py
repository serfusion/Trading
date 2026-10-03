"""Pencarian grid/martingale yang untung (3 Okt 2026) — python -m research.grid_cari

Permintaan pengguna: "cari sebanyak-banyaknya agar profit, bukan minus". Teknik dari praktik EA grid emas (pencarian web
3 Okt): jarak & TP berbasis ATR, filter rezim ADX H4 (grid hanya saat ranging, tutup saat tren), batas layer + stop
per keranjang, filter sesi, entri mean-reversion RSI/Bollinger, grid searah tren EMA.

Mesin: research/martingale_ea.sim dengan kait izin/step_arr/tp_arr/lot_arr/sl_lapis/tutup_arr. Semua fitur memakai
bar yang SUDAH selesai (shift 1). Setiap keranjang dibatasi: setelah `maks` layer, stop di level berikutnya; lot awal
diatur supaya rugi di stop = R = $20 (5% modal $400) → hasil dalam R, sebanding antar-tahun (lot pecahan, riset).
Spread $0,20 per layer; tutup sebelum akhir pekan; swap diabaikan.

Aturan seleksi DITETAPKAN SEBELUM melihat BARU: dari LAMA (< Okt 2021) — n ≥ 200 keranjang, rata-rata R > 0,
t ≥ 2, ≥ 70% tahun positif. Lolos LAMA lalu diuji di BARU (Okt 2021 – 2 Okt 2026).
"""
from __future__ import annotations

import itertools
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from .data import resample
from .martingale_ea import SPLIT, SPREAD, load, sim

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_grid_cari.txt"
CSV = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_grid_cari.csv"
R_USD = 20.0
MODAL = 40_000.0

MULT = (1.0, 1.3, 1.6, 2.0)
STEP_K = (0.5, 1.0, 2.0)
TP_K = (0.5, 1.0)
MAKS = (4, 7, 10)
IZIN = ("BUY", "trenH4", "trenH4_buy", "trenD1", "range_rsi", "pullback", "asia_buy", "bb_rev", "bb_rev_tren")
IZIN2 = ("vol_rendah_buy", "vol_rendah_tren", "dip_tren", "range_adx20")   # putaran 2 (filter rezim)

_G: dict = {}


def _map(s: pd.Series, idx: pd.DatetimeIndex, freq: str) -> np.ndarray:
    """Nilai bar timeframe besar yang sudah selesai (s sudah di-shift 1) untuk tiap bar dasar."""
    return s.reindex(idx.floor(freq)).ffill().to_numpy()


def fitur(df: pd.DataFrame) -> dict:
    idx = df.index
    h1 = resample(df, "1h")
    tr = pd.concat([h1.high - h1.low, (h1.high - h1.close.shift()).abs(), (h1.low - h1.close.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.rolling(14).mean()
    atr = _map(atr_s.shift(1), idx, "h")
    atr_med = _map(atr_s.rolling(480).median().shift(1), idx, "h")       # median ATR ±20 hari dagang
    ema20 = _map(h1.close.ewm(span=20, adjust=False).mean().shift(1), idx, "h")
    h4 = resample(df, "4h")
    up4 = _map((h4.close > h4.close.ewm(span=50, adjust=False).mean()).astype(float).shift(1), idx, "4h")
    up_m = h4.high.diff()
    dn_m = -h4.low.diff()
    pdm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    ndm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    tr4 = pd.concat([h4.high - h4.low, (h4.high - h4.close.shift()).abs(), (h4.low - h4.close.shift()).abs()], axis=1).max(axis=1)
    a = 1 / 14
    atr4 = tr4.ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=h4.index).ewm(alpha=a, adjust=False).mean() / atr4
    ndi = 100 * pd.Series(ndm, index=h4.index).ewm(alpha=a, adjust=False).mean() / atr4
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=a, adjust=False).mean()
    adx4 = _map(adx.shift(1), idx, "4h")
    d1 = resample(df, "1D")
    upd = _map((d1.close > d1.close.ewm(span=200, adjust=False).mean()).astype(float).shift(1), idx, "D")
    m15 = resample(df, "15min")
    dlt = m15.close.diff()
    rs = dlt.clip(lower=0).ewm(alpha=a, adjust=False).mean() / (-dlt.clip(upper=0)).ewm(alpha=a, adjust=False).mean()
    rsi = _map((100 - 100 / (1 + rs)).shift(1), idx, "15min")
    mid, sd = m15.close.rolling(20).mean(), m15.close.rolling(20).std()
    bb_lo = _map((m15.close < mid - 2 * sd).astype(float).shift(1), idx, "15min")
    bb_hi = _map((m15.close > mid + 2 * sd).astype(float).shift(1), idx, "15min")
    c15 = _map(m15.close.shift(1), idx, "15min")
    return dict(atr=atr, up4=up4, adx4=adx4, upd=upd, rsi=rsi, bb_lo=bb_lo, bb_hi=bb_hi, hour=idx.hour.to_numpy(),
                atr_med=atr_med, ema20=ema20, c15=c15)


def izin_arr(f: dict, nama: str) -> tuple[list, list | None]:
    ok = (~np.isnan(f["atr"]) & ~np.isnan(f["up4"]) & ~np.isnan(f["adx4"]) & ~np.isnan(f["rsi"]) & ~np.isnan(f["upd"])
          & ~np.isnan(f["atr_med"]))
    up4, upd = f["up4"] == 1, f["upd"] == 1
    rsi, adx = f["rsi"], f["adx4"]
    tutup = None
    if nama == "BUY":
        z = np.ones(len(ok))
    elif nama == "trenH4":
        z = np.where(up4, 1, -1)
    elif nama == "trenH4_buy":
        z = np.where(up4, 1, 0)
    elif nama == "trenD1":
        z = np.where(upd, 1, -1)
    elif nama == "range_rsi":
        rng = adx < 25
        z = np.where(rng & (rsi < 35), 1, np.where(rng & (rsi > 65), -1, 0))
        tutup = (adx >= 30) & ok
    elif nama == "pullback":
        z = np.where(up4 & (rsi < 35), 1, np.where(~up4 & (rsi > 65), -1, 0))
    elif nama == "asia_buy":
        z = np.where(f["hour"] < 7, 1, 0)
    elif nama == "bb_rev":
        z = np.where(f["bb_lo"] == 1, 1, np.where(f["bb_hi"] == 1, -1, 0))
    elif nama == "bb_rev_tren":
        z = np.where(up4 & (f["bb_lo"] == 1), 1, np.where(~up4 & (f["bb_hi"] == 1), -1, 0))
    elif nama == "vol_rendah_buy":
        z = np.where(f["atr"] < 0.8 * f["atr_med"], 1, 0)
    elif nama == "vol_rendah_tren":
        z = np.where(f["atr"] < 0.8 * f["atr_med"], np.where(up4, 1, -1), 0)
    elif nama == "dip_tren":
        jauh = 1.5 * f["atr"]
        z = np.where(upd & (f["c15"] < f["ema20"] - jauh), 1, np.where(~upd & (f["c15"] > f["ema20"] + jauh), -1, 0))
    elif nama == "range_adx20":
        rng = adx < 20
        z = np.where(rng, np.where(rsi < 50, 1, -1), 0)
        tutup = (adx >= 25) & ok
    else:
        raise ValueError(nama)
    z = np.where(ok, z, 0).astype(int)
    if tutup is not None:
        z = np.where(tutup, 0, z)
        return z.tolist(), tutup.tolist()
    return z.tolist(), None


def _init(df_: pd.DataFrame, f_: dict) -> None:
    _G["df"], _G["f"] = df_, f_


def jalankan(cfg: tuple) -> dict:
    nama, mult, sk, tk, maks = cfg
    df, f = _G["df"], _G["f"]
    key = ("izin", nama)
    if key not in _G:
        _G[key] = izin_arr(f, nama)
    iz, tut = _G[key]
    atr = np.nan_to_num(f["atr"], nan=np.nanmedian(f["atr"]))
    step = np.maximum(sk * atr, 0.3)
    w = mult ** np.arange(maks)
    lot0 = R_USD / (step * float((w * (maks - np.arange(maks))).sum()) + SPREAD * float(w.sum()))
    info: list = []
    sim(df, 1, 0.01, mult, 1.0, 1.0, maks, modal=MODAL, info=info, akhir_pekan=True, izin=iz,
        step_arr=step.tolist(), tp_arr=np.maximum(tk * atr, 0.3).tolist(), lot_arr=lot0.tolist(),
        sl_lapis=True, bulat=False, tutup_arr=tut)
    t = df.index
    tt = t[[r[0] for r in info]]
    rr = np.array([r[3] / 100 / R_USD for r in info])
    lay = np.array([r[1] for r in info])
    res = dict(izin=nama, mult=mult, step_k=sk, tp_k=tk, maks=maks)
    for lab, sel in (("L", tt < SPLIT), ("B", tt >= SPLIT)):
        x = rr[sel]
        n = len(x)
        res[f"{lab}_n"] = n
        res[f"{lab}_mean"] = float(x.mean()) if n else 0.0
        res[f"{lab}_t"] = float(x.mean() / x.std(ddof=1) * np.sqrt(n)) if n > 2 and x.std() > 0 else 0.0
        res[f"{lab}_tot"] = float(x.sum())
        res[f"{lab}_wr"] = float((x > 0).mean()) if n else 0.0
        res[f"{lab}_stop"] = float((lay[sel] >= maks).mean()) if n else 0.0
        cum = np.cumsum(x)
        res[f"{lab}_dd"] = float((np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum]).max()) if n else 0.0
        yrs = pd.Series(x, index=tt[sel].year).groupby(level=0).sum()
        res[f"{lab}_th_pos"] = float((yrs > 0).mean()) if len(yrs) else 0.0
        res[f"{lab}_th"] = " ".join(f"{y}:{v:+.0f}" for y, v in yrs.items())
    return res


def main() -> None:
    df = load()
    f = fitur(df)
    putaran2 = "2" in sys.argv[1:]
    cfgs = list(itertools.product(IZIN2 if putaran2 else IZIN, MULT, STEP_K, TP_K, MAKS))
    out_txt, out_csv = (OUT.with_name("hasil_grid_cari2.txt"), CSV.with_name("hasil_grid_cari2.csv")) if putaran2 else (OUT, CSV)
    with Pool(max(1, (os.cpu_count() or 2)), initializer=_init, initargs=(df, f)) as pool:
        rows = []
        for k, r in enumerate(pool.imap_unordered(jalankan, cfgs, chunksize=4), 1):
            rows.append(r)
            if k % 50 == 0:
                print(f"{k}/{len(cfgs)}", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(out_csv, index=False, float_format="%.4f")
    lolos = res[(res.L_n >= 200) & (res.L_mean > 0) & (res.L_t >= 2) & (res.L_th_pos >= 0.7)].sort_values("L_t", ascending=False)
    cols = ["izin", "mult", "step_k", "tp_k", "maks", "L_n", "L_mean", "L_t", "L_th_pos", "L_dd", "B_n", "B_mean", "B_t",
            "B_th_pos", "B_tot", "B_dd"]
    out = [f"{len(res)} pengaturan; R = ${R_USD:.0f} rugi maksimum per keranjang (5% modal $400). Spread ${SPREAD}.",
           f"Lolos seleksi LAMA (n ≥ 200, rata-rata > 0, t ≥ 2, ≥ 70% tahun +): {len(lolos)}"]
    if len(lolos):
        out.append(lolos[cols].head(30).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        ok_b = lolos[(lolos.B_mean > 0) & (lolos.B_t >= 1.5)]
        out.append(f"\nDari yang lolos LAMA, juga positif di BARU (rata-rata > 0, t ≥ 1,5): {len(ok_b)}")
        if len(ok_b):
            out.append(ok_b[cols + ["B_th"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    out.append("\n10 terbaik LAMA (t) tanpa syarat:")
    out.append(res.sort_values("L_t", ascending=False)[cols].head(10).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    out.append("\n10 terbaik BARU (DIPILIH SETELAH MELIHAT BARU — bukan bukti):")
    out.append(res.sort_values("B_t", ascending=False)[cols].head(10).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    out.append("\nRata-rata per jenis izin (semua parameter): " + " | ".join(
        f"{k}: LAMA {g.L_mean.mean():+.3f}R BARU {g.B_mean.mean():+.3f}R" for k, g in res.groupby("izin")))
    out.append(f"Pengaturan positif LAMA & BARU sekaligus (tanpa syarat t): {int(((res.L_mean > 0) & (res.B_mean > 0)).sum())}"
               f" dari {len(res)}")
    out_txt.write_text("\n".join(out) + "\n")
    print("\n".join(out))
    print("->", out_txt)


if __name__ == "__main__":
    main()
