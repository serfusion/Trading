"""₿ CPI → BTC & ETH detik 1–10 / lonjakan menit 1 / strategi modal kecil (13 Okt 2026, "setelah itu ETH dan BTC")

python -m research.kripto_cpi      → docs/eksternal/hasil_kripto_cpi.txt

Pra-registrasi: tebakan CPI KUAT aplikasi (research/cpi_detik IDX|K+S, tutup kertas) dipakai SEARAH untuk kripto (CPI di
bawah konsensus → bunga turun → emas, BTC, ETH naik). Data: BTC tick ASLI Exness BTCUSDm (bid/ask, spread asli) & Binance
1 dtk (mid); ETH Binance 1 dtk (spread asumsi research/pra_aset.ETH_SPREAD). Arah = mid detik h vs tick terakhir ≤ t0 − 1;
lonjakan menit 1 = gerak terjauh 0–60 dtk. Modal kecil = research/cpi_allin2.sim_keluar (masuk t−1, detik 2 / lentur),
1:200 (HMR Exness kripto), pembanding arah acak (5.000 lempar koin) per rilis yang sama, LAMA/BARU.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .cpi_allin2 import SPLIT, sim_keluar
from .news_detik import prepare
from .pra_aset import eth_tick

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_kripto_cpi.txt"
H = (1, 2, 3, 5, 10)


def arah_dari(p, h: float) -> float:
    i0, i1 = p.at(-1), p.at(h)
    if i0 < 0 or i1 < 0:
        return 0.0
    return float(np.sign((p.bid[i1] + p.ask[i1]) / 2 - (p.bid[i0] + p.ask[i0]) / 2))


def lonjakan(p) -> float:
    i0 = p.at(-1)
    if i0 < 0:
        return 0.0
    m0 = (p.bid[i0] + p.ask[i0]) / 2
    sel = (p.T > 0) & (p.T <= 60)
    if not sel.any():
        return 0.0
    mid = (p.bid[sel] + p.ask[sel]) / 2
    up, dn = mid.max() - m0, m0 - mid.min()
    return 1.0 if up > dn else -1.0 if dn > up else 0.0


def main() -> None:
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    ts = C.tetap(df, "IDX|K+S")
    rng = np.random.default_rng(23)
    L = ["# ₿ CPI → BTC & ETH (research/kripto_cpi.py)", __doc__.split("\n\n")[1], ""]
    def eth_exness(t):
        from .exness import ticks_around
        from .news_detik import Tick
        d = ticks_around("ETHUSDm", t)
        if d is None or not len(d):
            return None
        p = Tick(t, d, 1.0)
        return p if ((p.T >= -60) & (p.T < 0)).any() and ((p.T >= 0) & (p.T < 5)).any() else None
    for nama, ambil in (("BTC Exness (spread asli)", lambda t: prepare(t, "BTC_EXNESS")),
                        ("BTC Binance (mid)", lambda t: prepare(t, "BTC")), ("ETH Binance", eth_tick),
                        ("ETH Exness (spread asli, 2022+)", eth_exness)):
        rows = []
        for i, r in df.iterrows():
            g = int(np.sign(ts.iloc[i]))
            if not g:
                continue
            try:
                p = ambil(r.t0)
            except Exception:  # noqa: BLE001
                p = None
            if p is None:
                continue
            a = (np.asarray(p.T, float), np.asarray(p.bid, float), np.asarray(p.ask, float))
            o = {"t0": r.t0, "g": g, "L": lonjakan(p)}
            for h in H:
                o[f"d{h}"] = arah_dari(p, h)
            for kel, lev in ((2, 200), (("lentur", 10), 200)):
                k = "d2" if kel == 2 else "lt"
                res, rb, rs = sim_keluar(a, g, kel, lev), sim_keluar(a, 1, kel, lev), sim_keluar(a, -1, kel, lev)
                o[f"pl_{k}"], o[f"buy_{k}"], o[f"sell_{k}"] = (res or (np.nan,))[0], (rb or (np.nan,))[0], (rs or (np.nan,))[0]
                o[f"mc_{k}"] = bool(res and res[1])
            rows.append(o)
        x = pd.DataFrame(rows)
        if x.empty:
            L.append(f"\n## {nama}: tidak ada data")
            continue
        L.append(f"\n## {nama} — {len(x)} rilis CPI dengan tebakan kuat ({x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})")
        for per, m in (("LAMA", x.t0 < SPLIT), ("BARU", x.t0 >= SPLIT), ("2024+", x.t0 >= "2024-01-01")):
            z = x[m]
            if not len(z):
                continue

            def acc(col):
                ok = z[col] != 0
                return f"{(z[col][ok] == z.g[ok]).mean() * 100:3.0f}%" if ok.sum() else " – "
            arah = " ".join(f"d{h} {acc(f'd{h}')}" for h in H)
            L.append(f"   {per:5s} n {len(z):2d} | arah {arah} | lonjakan menit 1 {acc('L')}")
            for k, lab in (("d2", "tutup detik 2"), ("lt", "lentur")):
                w = z.dropna(subset=[f"pl_{k}", f"buy_{k}", f"sell_{k}"])
                if len(w) < 3:
                    continue
                koin = rng.integers(0, 2, size=(5000, len(w)))
                ac = np.where(koin == 1, w[f"buy_{k}"].to_numpy(), w[f"sell_{k}"].to_numpy()).mean(axis=1)
                L.append(f"         modal kecil 1:200 {lab:13s}: untung {(w[f'pl_{k}'] > 0).mean() * 100:3.0f}% "
                         f"${w[f'pl_{k}'].mean():+6.1f}/$100 (acak ${ac.mean():+6.1f}, p {(ac >= w[f'pl_{k}'].mean()).mean():.2f}) "
                         f"habis {int(w[f'mc_{k}'].sum())}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
