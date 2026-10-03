"""Filter "MARKET CRASH DETECTED" bot trader (3 Okt 2026) — python -m research.krisis_filter

Bukti baru: notifikasi bot "MARKET CRASH DETECTED, Drop: $30.0 dalam 1 jam, Bot SKIP entry baru sampai volatilitas
turun, cooldown aktif sampai 21:05" pukul 20:13 & 21:30 WIB. Detektor tulis-ulang (tertinggi 60 mnt − low ≥ $30) menyala
2 Okt 2026 13:15 & 14:30 UTC (= 20:15 & 21:30 WIB) → cocok dengan hari NFP. Diuji tiga tafsiran (sejak bar berikutnya,
jeda 60 mnt yang diperpanjang selama penurunan berlanjut): "baru" = tanpa keranjang baru; "beku" = juga tanpa layer
baru; "tutup" = keranjang berjalan ditutup. Aturan grid = rekonstruksi Signal Strike (research/tiru_150.BASIS, jeda 45
mnt) dan versi modal $400 (research/ea_400).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .klaim_6bulan import mulai_apr, peluang_182
from .martingale_ea import SPLIT, load
from .signal_strike import MODAL_TG
from .tiru_150 import bulanan, ringkas

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_krisis_filter.txt"
K = (30.0, 60.0, 60.0)
M4 = 40_000.0


def cfg(nama, lot0, mult, step, modal, rek, mode=None, akhir_pekan=False, turun=30.0):
    kr = (turun, K[1], K[2], mode) if mode else None
    return (nama, 1, lot0, mult, step, 1.9, 40, modal, rek, 45, 0.0, akhir_pekan, kr)


KONFIG = [
    cfg("T0 trader 0,07/$524 x1,2 jarak $2,25, tanpa filter", 0.07, 1.2, 2.25, MODAL_TG, True),
    cfg("T1 + filter krisis 'baru' (tanpa keranjang baru)", 0.07, 1.2, 2.25, MODAL_TG, True, "baru"),
    cfg("T2 + filter krisis 'beku' (juga tanpa layer baru)", 0.07, 1.2, 2.25, MODAL_TG, True, "beku"),
    cfg("T3 + filter krisis 'tutup' (keranjang ditutup)", 0.07, 1.2, 2.25, MODAL_TG, True, "tutup"),
    cfg("T4 + filter 'beku' + tutup akhir pekan", 0.07, 1.2, 2.25, MODAL_TG, True, "beku", True),
    cfg("T5 + filter 'beku' $20 (lebih peka) + tutup akhir pekan", 0.07, 1.2, 2.25, MODAL_TG, True, "beku", True, 20.0),
    cfg("Q1 $400 x1,2 0,05 + filter 'beku' + akhir pekan", 0.05, 1.2, 2.25, M4, True, "beku", True),
    cfg("Q2 $400 x2 0,01 jarak $2,25 + filter 'beku' + akhir pekan", 0.01, 2.0, 2.25, M4, False, "beku", True),
    cfg("Q3 $400 x2 0,01 jarak $2,25 + filter 'baru'", 0.01, 2.0, 2.25, M4, False, "baru"),
    ("Q4 BAWAAN EA v1.10: $400 x2 0,01 jarak $5 maks 15 + batas rugi 30% + akhir pekan + filter 'beku'", 1, 0.01, 2.0, 5.0,
     1.9, 15, M4, False, 45, 0.3, True, (30.0, 60.0, 60.0, "beku")),
]


def main() -> None:
    df = load()
    out = [f"Data {df.index[0]:%Y-%m-%d} s/d {df.index[-1]:%Y-%m-%d}. Detektor: tertinggi 60 mnt − low ≥ $30 (T5: $20), "
           "jeda 60 mnt sejak bar berikutnya. BUY, TP rata-rata +$1,9, jeda antar keranjang 45 mnt.", ""]
    rows = []
    for v in KONFIG:
        m = bulanan(df, v)
        modal = v[7] / 100
        out.append(v[0])
        for lab, sel in (("LAMA <Okt21", m.t < SPLIT), ("BARU Okt21+", m.t >= SPLIT),
                         ("12 bln akhir", m.t >= pd.Timestamp("2025-10-01", tz="UTC"))):
            out.append(ringkas(m[sel], modal, lab))
        th = m.groupby(m.t.dt.year).agg(habis=("habis", "sum"), usd=("usd", "sum"))
        out.append("  per tahun (bulan habis / bersih $): " + " ".join(f"{y}:{int(r.habis)}/{r.usd:+,.0f}" for y, r in th.iterrows()))
        mulai_apr(df, v, out)
        peluang_182(df, v, out)
        out.append("")
        b = m[m.t >= SPLIT]
        rows.append((v[0][:2], modal, b.usd.mean(), b.habis.mean(), (b.usd >= 150).mean(), m[m.t < SPLIT].usd.mean(),
                     m[m.t < SPLIT].habis.mean(), m.usd.sum()))
        print("\n".join(out[-9:]), flush=True)
    out.append("Ringkas: kode | modal | BARU $/bln | BARU bulan habis | BARU bulan ≥ $150 | LAMA $/bln | LAMA bulan habis | total")
    out += [f"  {r[0]} | ${r[1]:.0f} | {r[2]:+6.0f} | {100 * r[3]:3.0f}% | {100 * r[4]:3.0f}% | {r[5]:+5.0f} | {100 * r[6]:3.0f}% | "
            f"{r[7]:+8,.0f}" for r in rows]
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[-len(rows) - 1:]))
    print("->", OUT)


if __name__ == "__main__":
    main()
