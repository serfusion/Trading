"""EA grid martingale modal $400, target $150/bulan (3 Okt 2026) — python -m research.ea_400

Permintaan pengguna: "modal $400 beliau bisa $150/bulan, tiru martingale x2 setiap loss". Bukti deal Signal Strike
menunjukkan pengali 1,2 per layer (docs/SIGNAL_STRIKE.md), jadi x2 dan x1,2 diuji berdampingan dengan mesin
research/martingale_ea.sim (BUY, TP rata-rata +$1,9, jeda antar keranjang 45 mnt = kalibrasi September 2026),
ditambah pengaman yang dipasang di ea/GridMartingale.mq5: batas rugi ekuitas (tutup semua bila floating ≥ X% modal)
dan tutup sebelum akhir pekan (Jumat ≥ 20:00 UTC, buka lagi Senin). Per bulan kalender, modal $400 tanpa skala.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .martingale_ea import SPLIT, load
from .tiru_150 import bulanan, ringkas, ringkas_th, setahun

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_ea_400.txt"
M = 40_000.0   # USC = $400

# nama, arah, lot0, pengali, jarak, TP, maks layer, modal, lot rekursif, jeda mnt, batas rugi, tutup akhir pekan
KONFIG = [
    ("X2a  x2 0,01 lot jarak $2,25", 1, 0.01, 2.0, 2.25, 1.9, 40, M, False, 45, 0.0, False),
    ("X2b  x2 0,01 lot jarak $5", 1, 0.01, 2.0, 5.0, 1.9, 40, M, False, 45, 0.0, False),
    ("X2c  x2 0,02 lot jarak $5", 1, 0.02, 2.0, 5.0, 1.9, 40, M, False, 45, 0.0, False),
    ("X2d  x2 0,01 lot jarak $5 + batas rugi 50% + tutup akhir pekan", 1, 0.01, 2.0, 5.0, 1.9, 40, M, False, 45, 0.5, True),
    ("X2e  x2 0,02 lot jarak $5 + batas rugi 50% + tutup akhir pekan", 1, 0.02, 2.0, 5.0, 1.9, 40, M, False, 45, 0.5, True),
    ("X2f  BAWAAN EA: x2 0,01 lot jarak $5 maks 15 + batas rugi 30% + tutup akhir pekan", 1, 0.01, 2.0, 5.0, 1.9, 15, M, False,
     45, 0.3, True),
    ("R1a  x1,2 0,05 lot (rasio trader) jarak $2,25", 1, 0.05, 1.2, 2.25, 1.9, 40, M, True, 45, 0.0, False),
    ("R1b  x1,2 0,05 lot + batas rugi 50% + tutup akhir pekan", 1, 0.05, 1.2, 2.25, 1.9, 40, M, True, 45, 0.5, True),
    ("R1c  x1,2 0,05 lot + batas rugi 30% + tutup akhir pekan", 1, 0.05, 1.2, 2.25, 1.9, 40, M, True, 45, 0.3, True),
    ("R1d  x1,2 0,03 lot + batas rugi 50% + tutup akhir pekan", 1, 0.03, 1.2, 2.25, 1.9, 40, M, True, 45, 0.5, True),
    ("R1e  x1,2 0,05 lot jarak $3 + batas rugi 50% + tutup akhir pekan", 1, 0.05, 1.2, 3.0, 1.9, 40, M, True, 45, 0.5, True),
]


def main() -> None:
    df = load()
    out = [f"Modal $400, data {df.index[0]:%Y-%m-%d} s/d {df.index[-1]:%Y-%m-%d}. BUY, TP rata-rata +$1,9, jeda 45 mnt. "
           "'Akun habis' = ekuitas 0; batas rugi dicatat sebagai bulan rugi (modal diisi lagi ke $400).", ""]
    rows = []
    for v in KONFIG:
        m = bulanan(df, v)
        y = setahun(df, v)
        out.append(v[0])
        for lab, sel in (("LAMA <Okt21", m.t < SPLIT), ("BARU Okt21+", m.t >= SPLIT),
                         ("12 bln akhir", m.t >= pd.Timestamp("2025-10-01", tz="UTC"))):
            out.append(ringkas(m[sel], 400, lab))
        th = m.groupby(m.t.dt.year).agg(habis=("habis", "sum"), usd=("usd", "sum"))
        out.append("  per tahun (bulan habis / bersih $): " + " ".join(f"{yy}:{int(r.habis)}/{r.usd:+,.0f}" for yy, r in th.iterrows()))
        out.append("  Satu akun 12 bln (berhenti di habis pertama; batas rugi = rugi sebagian, lanjut):")
        out.append(ringkas_th(y[y.t < SPLIT], 400, "LAMA <Okt21"))
        out.append(ringkas_th(y[y.t >= SPLIT], 400, "BARU Okt21+"))
        out.append("")
        b = m[m.t >= SPLIT]
        rows.append((v[0][:4], b.usd.mean(), (b.usd >= 150).mean(), b.habis.mean(), (b.usd < 0).mean(),
                     m[m.t < SPLIT].usd.mean(), m.usd.sum()))
        print("\n".join(out[-10:]), flush=True)
    out.append("Ringkas BARU (Okt 2021+): kode | rata-rata $/bln | bulan ≥ $150 | bulan akun habis | bulan rugi | LAMA $/bln | total 2012–2026")
    out += [f"  {r[0]} | {r[1]:+6.0f} | {100 * r[2]:3.0f}% | {100 * r[3]:3.0f}% | {100 * r[4]:3.0f}% | {r[5]:+5.0f} | {r[6]:+8,.0f}"
            for r in rows]
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[-len(rows) - 1:]))
    print("->", OUT)


if __name__ == "__main__":
    main()
