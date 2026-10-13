"""💥 Strategi "modal kecil, lot maksimal" saat rilis CPI — python -m research.cpi_allin → docs/eksternal/hasil_cpi_allin.txt

Permintaan pengguna 15 Okt 2026: modal kecil (5–10 ribu cent = $50–100), lot sebesar mungkin; bila arah emas 1–5 detik
setelah rilis benar → untung berlipat, bila salah → modal habis (margin call). "Akurasi harus benar-benar teruji, terutama
1–5 detik pertama, terutama CPI."

Simulasi (tick ASLI Exness XAUUSDc: bid & ask/spread saat rilis, research/exness.py), per rilis CPI 2016–2026:
  - Tebakan arah = aturan aplikasi (research/cpi_detik: IDX|K tutup kertas; ⚠️ lemah = kena saringan IDX|K+S).
  - Modal A = $100 per rilis (setoran baru tiap rilis; rugi maksimal = A). Lot = A × leverage / harga (margin penuh).
  - Masuk di tick terakhir ≤ t0 − 1 dtk (BUY di ask, SELL di bid). Tutup di tick pertama ≥ t0 + h dtk (BUY di bid, SELL
    di ask), h = 1/2/3/5. Equity dicek di SETIAP tick: ≤ 0 → margin call (stop out Exness 0%) → −A.
  - Leverage 1:200 (Exness memberlakukan margin tetap ±1:200 untuk posisi yang dibuka di sekitar berita besar — cek
    ketentuan akun), 1:500, 1:2000 (tanpa batas).
  - Pembanding: arah SEMPURNA (kejutan core/headline sudah diketahui) dan selalu BUY.
Belum termasuk: latensi klik/eksekusi manusia (±0,3–1 dtk), requote/penolakan order saat rilis, slippage di luar tick.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .exness import ticks_around

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_allin.txt"
MODAL = 100.0
HS = (1, 2, 3, 5)
LEV = (200, 500, 2000)


def satu(tk: pd.DataFrame, t0: pd.Timestamp, arah: int, h: int, lev: int) -> dict | None:
    """Hasil satu rilis: {"pl", "mc"} ($, margin call?) atau None bila tick tidak lengkap."""
    pre = tk[tk.index <= t0 - pd.Timedelta(seconds=1)]
    post = tk[tk.index >= t0 + pd.Timedelta(seconds=h)]
    if not len(pre) or not len(post):
        return None
    t_in = pre.index[-1]
    if t0 - t_in > pd.Timedelta(seconds=30):                     # feed beku → tidak dihitung
        return None
    masuk = pre.ask.iloc[-1] if arah > 0 else pre.bid.iloc[-1]
    oz = MODAL * lev / masuk
    jalan = tk[(tk.index > t_in) & (tk.index <= post.index[0])]
    keluar_px = (jalan.bid if arah > 0 else jalan.ask).to_numpy()
    eq = MODAL + oz * (keluar_px - masuk) * arah
    if len(eq) and eq.min() <= 0:
        return {"pl": -MODAL, "mc": True}
    akhir = post.bid.iloc[0] if arah > 0 else post.ask.iloc[0]
    return {"pl": max(-MODAL, oz * (akhir - masuk) * arah), "mc": False}


def ringkas(x: pd.DataFrame) -> str:
    if not len(x):
        return "n 0"
    menang = (x.pl > 0).mean() * 100
    return (f"n {len(x):3} | benar {menang:3.0f}% | margin call {int(x.mc.sum()):2} | rata ${x.pl.mean():+7.1f} | "
            f"total ${x.pl.sum():+8.0f} | menang rata ${x.pl[x.pl > 0].mean() if (x.pl > 0).any() else 0:6.0f} "
            f"(×{(x.pl[x.pl > 0].mean() if (x.pl > 0).any() else 0) / MODAL:.1f}) | modal habis = 1 dari "
            f"{len(x) / max(1, x.mc.sum()):.1f}")


def main() -> None:
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    tb = C.tetap(df, "IDX|K")
    ts = C.tetap(df, "IDX|K+S")
    sempurna = -np.sign(np.where(df.s_core != 0, df.s_core, df.s_mm))
    varian = {"aplikasi (semua tebakan)": tb, "hanya tebakan kuat (tanpa ⚠️)": ts,
              "hanya NAIK": tb.where(tb > 0, 0), "SEMPURNA (kejutan sudah diketahui)": pd.Series(sempurna),
              "selalu BUY": pd.Series(1.0, index=df.index)}
    tick = {i: ticks_around("XAUUSDc", r.t0) for i, r in df.iterrows()}
    ada = sum(v is not None for v in tick.values())
    L = ["# 💥 Modal kecil + lot maksimal saat CPI (research/cpi_allin.py)", __doc__.split("\n\n")[1], "",
         f"Rilis CPI 2016–2026: {len(df)}, tick Exness tersedia: {ada}", ""]
    hasil = []
    for nama, s in varian.items():
        L.append(f"## {nama}")
        for lev in LEV:
            for h in HS:
                rows = []
                for i, r in df.iterrows():
                    a = int(np.sign(s.iloc[i]))
                    if a == 0 or tick[i] is None:
                        continue
                    o = satu(tick[i], r.t0, a, h, lev)
                    if o:
                        rows.append({"t0": r.t0, **o})
                x = pd.DataFrame(rows)
                if not len(x):
                    continue
                baru = x[x.t0 >= "2021-10-01"]
                L.append(f"   1:{lev:<4} tutup detik {h}: SEMUA {ringkas(x)}")
                L.append(f"   {'':6} {'':14} sejak Okt 2021 {ringkas(baru)}")
                hasil.append((nama, lev, h, x))
        L.append("")
    # rincian per rilis 2024–2026 untuk varian aplikasi, 1:2000, detik 2
    L.append("## Rincian per rilis 2024–2026 (aplikasi, 1:2000, tutup detik 2 / detik 5)")
    for i, r in df[df.t0 >= "2024-01-01"].iterrows():
        a = int(np.sign(tb.iloc[i]))
        if a == 0 or tick[i] is None:
            L.append(f"   {r.t0:%Y-%m-%d} tidak menebak / tanpa tick")
            continue
        o2, o5 = satu(tick[i], r.t0, a, 2, 2000), satu(tick[i], r.t0, a, 5, 2000)
        sp = tick[i][(tick[i].index >= r.t0 - pd.Timedelta(seconds=1)) & (tick[i].index <= r.t0 + pd.Timedelta(seconds=5))]
        spr = (sp.ask - sp.bid).max() if len(sp) else float("nan")
        lemah = " ⚠️" if ts.iloc[i] == 0 else ""
        L.append(f"   {r.t0:%Y-%m-%d} {'BUY ' if a > 0 else 'SELL'}{lemah} | detik 2 "
                 f"{'MC ' if o2 and o2['mc'] else ''}${(o2 or {}).get('pl', float('nan')):+7.0f} | detik 5 "
                 f"{'MC ' if o5 and o5['mc'] else ''}${(o5 or {}).get('pl', float('nan')):+7.0f} | spread maks t−1..t+5 ${spr:.2f}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
