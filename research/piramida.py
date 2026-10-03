"""Kebalikan martingale: grid PIRAMIDA searah tren (3 Okt 2026) — python -m research.piramida

Setelah 936 pengaturan grid/martingale (research/grid_cari.py) tanpa keunggulan berarti, diuji kebalikannya: layer
ditambah saat harga bergerak SEARAH posisi (setiap step_k x ATR H1), stop keranjang = layer terakhir − sl_k x ATR (ikut
naik), keluar saat stop kena atau tren berbalik (dicek di harga buka bar). Arah = tren H4 EMA50 / D1 EMA200 (bar yang
sudah selesai). Lot layer k = lot0 x mult^k; lot0 diatur supaya rugi di stop awal = R = $20 (5% modal $400). Spread
$0,20 per layer, tutup sebelum akhir pekan (Jumat ≥ 20:00 UTC). maks = 1 → trend following biasa tanpa piramida.
Seleksi sama dengan grid_cari: dipilih di LAMA (< Okt 2021), diuji di BARU.
"""
from __future__ import annotations

import itertools
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from .grid_cari import R_USD, fitur
from .martingale_ea import SPLIT, SPREAD, arrays, load

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_piramida.txt"
_G: dict = {}


def _init(df_, f_):
    _G["df"], _G["f"] = df_, f_


def arah(f: dict, nama: str) -> np.ndarray:
    ok = ~np.isnan(f["atr"]) & ~np.isnan(f["up4"]) & ~np.isnan(f["upd"])
    if nama == "trenH4":
        z = np.where(f["up4"] == 1, 1, -1)
    elif nama == "trenH4_buy":
        z = np.where(f["up4"] == 1, 1, 0)
    elif nama == "trenD1":
        z = np.where(f["upd"] == 1, 1, -1)
    else:
        z = np.where((f["upd"] == 1) & (f["up4"] == 1), 1, np.where((f["upd"] == 0) & (f["up4"] == 0), -1, 0))
    return np.where(ok, z, 0).astype(int)


def jalankan(cfg: tuple, spread: float = SPREAD, detail: bool = False):
    nama, sk, slk, maks, mult = cfg
    df, f = _G["df"], _G["f"]
    o, h, l, c = arrays(df)
    t = df.index
    z = arah(f, nama).tolist()
    atr = np.nan_to_num(f["atr"], nan=np.nanmedian(f["atr"])).tolist()
    wd, hr = t.dayofweek.tolist(), t.hour.tolist()
    res_t, res_r, res_o = [], [], []
    SPREAD_ = spread
    st = dict(n=0)

    def tutup(i: int, px: float) -> None:
        g = sum(lot * (px - e) for lot, e in zip(st["lots"], st["ent"]))
        res_t.append(i)
        res_r.append(g / R_USD)
        res_o.append(st["i0"])
        st["n"] = 0

    for i in range(1, len(o)):
        blk = wd[i] == 5 or wd[i] == 6 or (wd[i] == 4 and hr[i] >= 20)
        if st["n"]:
            d = st["d"]
            if blk or z[i] != d or d * o[i] <= st["stop"]:   # akhir pekan / tren berbalik / gap lewat stop
                tutup(i, d * o[i])
        if not st["n"] and not blk and z[i]:
            d = z[i]
            a = atr[i]
            lot0 = R_USD / (slk * a + SPREAD_)
            x = d * o[i]
            st.update(n=1, d=d, step=sk * a, sld=slk * a, lots=[lot0], ent=[x + SPREAD_], last=x, stop=x - slk * a, i0=i)
        if not st["n"]:
            continue
        d = st["d"]
        pts = (o[i], l[i], h[i], c[i]) if c[i] >= o[i] else (o[i], h[i], l[i], c[i])
        for k in range(3):
            if not st["n"]:
                break
            xa, xb = d * pts[k], d * pts[k + 1]
            if xb > xa:                                   # searah: tambah layer, stop ikut naik
                while st["n"] < maks and st["last"] + st["step"] <= xb:
                    lvl = st["last"] + st["step"]
                    st["lots"].append(st["lots"][0] * mult ** st["n"])
                    st["ent"].append(lvl + SPREAD_)
                    st["n"] += 1
                    st["last"] = lvl
                    st["stop"] = max(st["stop"], lvl - st["sld"])
            elif xb <= st["stop"]:
                tutup(i, min(st["stop"], xa))
    tt = t[res_t]
    rr = np.array(res_r)
    if detail:
        return pd.DataFrame(dict(buka=t[res_o], tutup=tt, r=rr))
    out = dict(arah=nama, step_k=sk, sl_k=slk, maks=maks, mult=mult)
    for lab, sel in (("L", tt < SPLIT), ("B", tt >= SPLIT)):
        x = rr[sel]
        n = len(x)
        out[f"{lab}_n"] = n
        out[f"{lab}_mean"] = float(x.mean()) if n else 0.0
        out[f"{lab}_t"] = float(x.mean() / x.std(ddof=1) * np.sqrt(n)) if n > 2 else 0.0
        out[f"{lab}_tot"] = float(x.sum())
        yrs = pd.Series(x, index=tt[sel].year).groupby(level=0).sum()
        out[f"{lab}_th_pos"] = float((yrs > 0).mean()) if len(yrs) else 0.0
        cum = np.r_[0, np.cumsum(x)]
        out[f"{lab}_dd"] = float((np.maximum.accumulate(cum) - cum).max())
        out[f"{lab}_th"] = " ".join(f"{y}:{v:+.0f}" for y, v in yrs.items())
    return out


def main() -> None:
    df = load()
    f = fitur(df)
    cfgs = [(a, s, sl, 1, 1.0) for a, s, sl in itertools.product(("trenH4", "trenH4_buy", "trenD1", "tren2"), (1.0,), (2.0, 4.0))]
    cfgs += list(itertools.product(("trenH4", "trenH4_buy", "trenD1", "tren2"), (1.0, 2.0, 3.0), (2.0, 4.0), (3, 6), (1.0, 0.7)))
    with Pool(os.cpu_count() or 2, initializer=_init, initargs=(df, f)) as pool:
        res = pd.DataFrame(pool.map(jalankan, cfgs, chunksize=2))
    res.to_csv(OUT.with_suffix(".csv"), index=False, float_format="%.4f")
    cols = ["arah", "step_k", "sl_k", "maks", "mult", "L_n", "L_mean", "L_t", "L_th_pos", "L_dd", "B_n", "B_mean", "B_t",
            "B_th_pos", "B_tot", "B_dd"]
    lolos = res[(res.L_n >= 200) & (res.L_mean > 0) & (res.L_t >= 2) & (res.L_th_pos >= 0.7)].sort_values("L_t", ascending=False)
    fmt = lambda v: f"{v:.3f}"  # noqa: E731
    out = [f"{len(res)} pengaturan piramida; R = ${R_USD:.0f} per keranjang (stop awal). Spread ${SPREAD}.",
           f"Lolos seleksi LAMA (n ≥ 200, rata-rata > 0, t ≥ 2, ≥ 70% tahun +): {len(lolos)}"]
    if len(lolos):
        out.append(lolos[cols + ["B_th"]].to_string(index=False, float_format=fmt))
        ok_b = lolos[(lolos.B_mean > 0) & (lolos.B_t >= 1.5)]
        out.append(f"\nDari yang lolos LAMA, juga positif di BARU (t ≥ 1,5): {len(ok_b)}")
    out.append("\nSemua, urut t LAMA:")
    out.append(res.sort_values("L_t", ascending=False)[cols].to_string(index=False, float_format=fmt))
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[:60]))
    print("->", OUT)


TERPILIH = [("tren2", 1.0, 2.0, 6, 1.0), ("tren2", 2.0, 2.0, 6, 1.0), ("tren2", 3.0, 2.0, 6, 1.0)]


def cek() -> None:
    """Tiga pengaturan yang lolos: risiko per keranjang yang masuk akal untuk $400, per tahun, spread x2, lama tahan."""
    df = load()
    _init(df, fitur(df))
    out = ["Cek 3 pengaturan piramida yang lolos (python -m research.piramida cek):"]
    for cfg in TERPILIH:
        d = jalankan(cfg, detail=True)
        d2 = jalankan(cfg, spread=2 * SPREAD, detail=True)
        jam = (d.tutup - d.buka).dt.total_seconds() / 3600
        out.append(f"{cfg}: n {len(d)}, tahan median {jam.median():.1f} jam, ≥ 1 malam {100 * (d.tutup.dt.date != d.buka.dt.date).mean():.0f}%"
                   f", menang {100 * (d.r > 0).mean():.0f}%, spread x2: LAMA {d2[d2.tutup < SPLIT].r.mean():+.3f}R BARU "
                   f"{d2[d2.tutup >= SPLIT].r.mean():+.3f}R")
        th = d.groupby(d.tutup.dt.year).r.sum()
        out.append("  R per tahun: " + " ".join(f"{y}:{v:+.0f}" for y, v in th.items()))
        for pct in (0.5, 1.0):
            r_usd = 400 * pct / 100
            for lab, sel in (("LAMA", d.tutup < SPLIT), ("BARU", d.tutup >= SPLIT)):
                x = d[sel]
                cum = np.r_[0, np.cumsum(x.r.to_numpy())] * r_usd
                dd = (np.maximum.accumulate(cum) - cum).max()
                bln = (x.tutup.max() - x.tutup.min()).days / 30.44
                out.append(f"  risiko {pct}%/keranjang (${r_usd:.0f}) {lab}: total ${cum[-1]:+,.0f} = ${cum[-1] / bln:+.1f}/bulan, "
                           f"DD terdalam ${dd:,.0f} ({100 * dd / 400:.0f}% modal)")
    txt = "\n".join(out)
    OUT.with_name("hasil_piramida_cek.txt").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    import sys
    cek() if "cek" in sys.argv[1:] else main()
