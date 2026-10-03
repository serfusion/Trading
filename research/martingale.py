"""Martingale pendek dipadukan dengan sinyal 💰 — python -m research.martingale

Permintaan pengguna (3 Okt 2026, dengan gambar akun MT5 & video EA grid NFP 2 Okt): "auto entry 0,01 x5, kalau masih
loss 0,03 x5, kalau loss lagi 0,05 x5, dengan TP pendek; begitu seterusnya". Dua tafsiran diuji pada sinyal 💰 yang
SAMA dengan cloud (research/sl_tangga.run, skema bawaan sebagai pembanding):

M1 antar sinyal: lot sinyal berikutnya 1x / 3x / 5x setelah 0 / 1 / >=2 sinyal kalah beruntun (yang sudah tutup
   sebelum entry), kembali 1x setelah menang. Skema posisi tetap bawaan. Hasil = R sinyal x pengali.
M2 dalam satu sinyal (seperti EA di video): entry 1 bagian (0,01 x5) di harga sinyal; bila harga melawan sejauh S x R
   tambah 3 bagian (0,03 x5); melawan 2S x R tambah 5 bagian (0,05 x5). SEMUA ditutup saat harga mencapai rata-rata
   tertimbang + T x R (TP keranjang pendek), atau SL awal sinyal (3 ATR) kena, atau saat sinyal aslinya selesai (TUTUP
   /SL+ cloud) bila keduanya belum kena. Candle H1: isi level & SL dicek dulu, TP keranjang sesudahnya (konservatif).
   Spread dibayar tiap tambahan. Satuan: R dasar = rugi 1 bagian (0,01 x5) di SL awal.
Ukuran: WR (sinyal untung), hasil total, DD terdalam, rugi terbesar satu sinyal (dalam R dasar), LAMA/BARU, tahun
positif, dan "DD % modal" bila 1 R dasar = 0,5% modal (tanpa bunga berbunga).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import SPLIT, asset
from .sl_tangga import run

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_martingale.txt"
BASE = dict(tps=[1.0, None, None, None, None])
W = (1.0, 3.0, 5.0)


def m1(df: pd.DataFrame) -> pd.Series:
    """Pengali lot per sinyal dari kalah beruntun sinyal yang sudah tutup sebelum entry."""
    df = df.sort_values("t").reset_index(drop=True)
    closed = df.sort_values("t_out")
    mult = []
    for t in df.t:
        done = closed[closed.t_out <= t].R.to_numpy()
        k = 0
        for r in done[::-1]:
            if r > 0:
                break
            k += 1
        mult.append(W[min(k, 2)])
    return pd.Series(mult, index=df.index), df


def m2(name: str, step: float, tp: float) -> pd.DataFrame:
    """Grid 1/3/5 bagian dalam tiap sinyal 💰 (sinyal & waktu selesai dari mesin bawaan)."""
    rec: list = []
    base = run(name, {**BASE, "rec": rec})
    b = asset(name).b
    o, h, l, sp, a, tt = b.o, b.h, b.l, b.sp, b.atr, b.t
    idx = pd.DatetimeIndex(tt)
    rows = []
    for tr in base.itertuples():
        j = idx.get_loc(tr.t)
        k_end = idx.get_loc(tr.t_out)
        d = int(tr.dir)
        risk = 3.0 * a[j - 1]
        e0 = o[j] + (sp[j] if d > 0 else 0.0)
        sl = e0 - d * risk
        lv = [e0, e0 - d * step * risk, e0 - d * 2 * step * risk]
        filled = [(e0, W[0])]
        pnl, out = None, "tutup"
        for k in range(j, min(k_end, len(o) - 1) + 1):
            adj = sp[k] if d < 0 else 0.0
            # isi level tambahan (harga melawan), lalu SL
            for n in (1, 2):
                if len(filled) == n and ((l[k] <= lv[n]) if d > 0 else (h[k] + adj >= lv[n])):
                    px = min(lv[n], o[k]) if d > 0 else max(lv[n], o[k] + adj)     # celah: isi di harga buka
                    filled.append((px + (sp[k] if d > 0 else 0.0), W[n]))
            if (l[k] + adj <= sl) if d > 0 else (h[k] + adj >= sl):
                pnl = sum((sl - p) * d * w for p, w in filled)
                out = "SL"
                break
            wsum = sum(w for _, w in filled)
            avg = sum(p * w for p, w in filled) / wsum
            tgt = avg + d * tp * risk
            if k > j and ((h[k] + adj >= tgt) if d > 0 else (l[k] + adj <= tgt)):
                pnl = sum((tgt - p) * d * w for p, w in filled)
                out = "TP"
                break
        if pnl is None:
            k = min(k_end + 1, len(o) - 1)
            px = o[k] + (sp[k] if d < 0 else 0.0)
            pnl = sum((px - p) * d * w for p, w in filled)
        rows.append({"t": tr.t, "R": pnl / risk, "n_lv": len(filled), "out": out})
    return pd.DataFrame(rows)


def stats(r: pd.Series, t: pd.Series, split: pd.Timestamp) -> dict:
    eq = np.cumsum(r.to_numpy())
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    yr = r.groupby(t.dt.year).sum()
    return {"n": len(r), "wr": (r > 0).mean() * 100, "tot": r.sum(), "dd": dd, "worst": r.min(),
            "lama": r[t < split].sum(), "baru": r[t >= split].sum(), "th": f"{(yr > 0).sum()}/{len(yr)}"}


def fmt(name: str, s: dict) -> str:
    return (f"  {name:52} n={s['n']:4} WR {s['wr']:5.1f}% total {s['tot']:+8.1f}R DD {s['dd']:+7.1f}R "
            f"rugi terbesar 1 sinyal {s['worst']:+5.1f}R | LAMA {s['lama']:+7.1f} BARU {s['baru']:+7.1f} th+ {s['th']} | "
            f"DD {s['dd'] * 0.5:+.0f}% modal (1R = 0,5%)")


def report() -> str:
    L = ["# Martingale pendek + sinyal 💰 (research/martingale.py)", "",
         "R dasar = rugi 1 bagian (0,01 x5) bila SL awal sinyal kena. Semua angka tanpa bunga berbunga.", ""]
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        base = run(name, BASE).sort_values("t").reset_index(drop=True)
        L.append(f"== {name} ({len(base)} sinyal 💰, LAMA < {split:%Y}) ==")
        L.append(fmt("bawaan (lot tetap 1 bagian, skema TP1 + 4 jalan)", stats(base.R, base.t, split)))
        mult, srt = m1(base)
        L.append(fmt("M1 antar sinyal 1x / 3x / 5x setelah kalah", stats(srt.R * mult, srt.t, split)))
        L.append(f"    (sinyal dengan lot 5x: {(mult == 5).mean() * 100:.0f}%; rata-rata pengali {mult.mean():.2f})")
        for step in (0.2, 0.33):
            for tp in (0.1, 0.2, 0.3):
                g = m2(name, step, tp)
                s = stats(g.R, g.t, split)
                L.append(fmt(f"M2 grid 1/3/5, jarak {step}R, TP keranjang +{tp}R", s)
                         + f" | level 3 terisi {(g.n_lv == 3).mean() * 100:.0f}% | SL {(g.out == 'SL').mean() * 100:.0f}%")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
