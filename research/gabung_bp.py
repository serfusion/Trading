"""Piramida searah tren + 10 strategi blueprint & aturan risiko dokumen (3 Okt 2026) — python -m research.gabung_bp

Pertanyaan pengguna: "bagaimana jika digabungkan (dokumen 10 strategi non-martingale)? apakah ada yang WR tinggi?"
1. Sinyal blueprint (research/blueprint10.sinyal) sebagai PEMICU keranjang piramida (research/piramida, pengaturan
   terpilih tren2 / jarak 3 ATR / stop 2 ATR / maks 6): keranjang hanya dibuka saat sinyal searah tren2 muncul.
2. Aturan risiko dokumen pada risiko 0,5%/keranjang: berhenti sampai hari berikutnya bila rugi harian ≥ 2% atau 4 kalah
   beruntun, sampai pekan berikutnya bila rugi mingguan ≥ 5% (diterapkan pada urutan keranjang; pendekatan).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import piramida
from .blueprint10 import Data, sinyal
from .grid_cari import fitur
from .martingale_ea import SPLIT, load

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_gabung_bp.txt"
CFG = ("tren2", 3.0, 2.0, 6, 1.0)
PILIH = ("1 tren+pullback", "5 momentum expansion", "6 sesi London", "9 ATR breakout", "2 breakout+retest", "8 MTF struktur")


def gate_dari(D: Data, sig: list, idx: pd.DatetimeIndex) -> list:
    """Sinyal (bar M15 entry) → arah per bar df (bar df pertama di dalam bar M15 itu)."""
    t = D.b.index
    s = pd.Series({t[j0]: d for j0, d, _, _ in sig if j0 < len(t)})
    s = s[~s.index.duplicated()]
    g = s.reindex(idx.floor("15min")).fillna(0).astype(int).to_numpy()
    first = np.r_[True, idx.floor("15min")[1:] != idx.floor("15min")[:-1]]
    return np.where(first, g, 0).tolist()


def aturan_risiko(d: pd.DataFrame, risk_pct: float = 0.5) -> pd.DataFrame:
    keep, hari, pekan, rugi_h, rugi_p, beruntun, stop_sampai = [], None, None, 0.0, 0.0, 0, None
    for row in d.itertuples():
        hh, pp = row.buka.floor("D"), row.buka.tz_localize(None).to_period("W")
        if hh != hari:
            hari, rugi_h, beruntun = hh, 0.0, 0
        if pp != pekan:
            pekan, rugi_p = pp, 0.0
        if stop_sampai is not None and row.buka < stop_sampai:
            keep.append(False)
            continue
        keep.append(True)
        pct = row.r * risk_pct
        rugi_h, rugi_p = rugi_h + min(pct, 0) + max(pct, 0), rugi_p + pct
        beruntun = beruntun + 1 if row.r < 0 else 0
        if rugi_p <= -5:
            stop_sampai = (pp.end_time.tz_localize("UTC") + pd.Timedelta(seconds=1)).floor("D")
        elif rugi_h <= -2 or beruntun >= 4:
            stop_sampai = row.buka.floor("D") + pd.Timedelta(days=1)
    return d[np.array(keep)]


def ringkas(d: pd.DataFrame, lab: str) -> str:
    out = []
    for nm, sel in (("LAMA", d.tutup < SPLIT), ("BARU", d.tutup >= SPLIT)):
        x = d[sel].r.to_numpy()
        if len(x) < 3:
            out.append(f"{nm} n {len(x)}")
            continue
        t = x.mean() / x.std(ddof=1) * np.sqrt(len(x))
        th = pd.Series(x, index=d[sel].tutup.dt.year).groupby(level=0).sum()
        cum = np.r_[0, np.cumsum(x)] * 2.0
        bln = max((d[sel].tutup.max() - d[sel].tutup.min()).days / 30.44, 1)
        out.append(f"{nm} n {len(x):4d} WR {100 * (x > 0).mean():3.0f}% {x.mean():+.3f}R t {t:4.1f} th+ {100 * (th > 0).mean():3.0f}% "
                   f"${cum[-1] / bln:+5.1f}/bln DD ${(np.maximum.accumulate(cum) - cum).max():4.0f}")
    return f"  {lab:34s} " + " | ".join(out)


def main() -> None:
    df = load()
    piramida._init(df, fitur(df))
    D = Data()
    S = sinyal(D)
    out = ["Piramida tren2/3 ATR/stop 2 ATR/maks 6, risiko 0,5% ($2 per $400). $/bln & DD pada $400.", ""]
    base = piramida.jalankan(CFG, detail=True)
    out.append(ringkas(base, "piramida biasa (tanpa pemicu)"))
    out.append(ringkas(aturan_risiko(base), "  + aturan risiko dokumen"))
    semua = np.zeros(len(df), dtype=int)
    for nama in PILIH:
        g = gate_dari(D, S[nama], df.index)
        semua = np.where(semua == 0, np.array(g), semua)
        d = piramida.jalankan(CFG, detail=True, gate=g)
        out.append(ringkas(d, f"pemicu {nama}"))
    d = piramida.jalankan(CFG, detail=True, gate=semua.tolist())
    out.append(ringkas(d, "pemicu salah satu dari 6 di atas"))
    out.append(ringkas(aturan_risiko(d), "  + aturan risiko dokumen"))
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out))
    print("->", OUT)


if __name__ == "__main__":
    main()
