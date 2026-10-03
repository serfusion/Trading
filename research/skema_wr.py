"""Skema WR tinggi: beberapa TP pendek + sisakan 1-2 posisi berjalan. python -m research.skema_wr

Permintaan pengguna (3 Okt 2026, setelah 1 sinyal 💰 BTC kena SL −1.380 USC): "ubah pola yang WR tinggi dengan TP
pendek, kemudian sisakan 1-2 yang dibiarkan sampai TUTUP". Sinyal TIDAK berubah (mesin cloud = research/sl_tangga.run:
3 set Donchian H1, SL 3xATR, kategori 💰); yang diuji hanya cara membagi 5 posisi (TP per posisi, None = berjalan sampai
TUTUP/SL+) dan kapan SL+ (entry + 0,1R) dipasang.
WR = % sinyal yang hasil bersihnya > 0 (rata-rata 5 posisi); WR TP1 = % sinyal yang TP pertamanya kena.
LOLOS (ditetapkan sebelum melihat hasil): R/sinyal >= bawaan di LAMA DAN BARU, total R >= bawaan, DD tidak lebih buruk,
>= 60% tahun lebih baik. Satuan R: 1R = jarak SL awal; hasil uang = R x risiko per sinyal (lot aplikasi).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .eksternal import SPLIT
from .sl_tangga import run, summary

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_skema_wr.txt"
N = None
VARIANTS = {
    "bawaan: 1 TP 1R + 4 jalan (SL+ setelah TP1)": dict(tps=[1.0, N, N, N, N]),
    "3 TP pendek 0,3/0,5/0,7R + 2 jalan": dict(tps=[0.3, 0.5, 0.7, N, N]),
    "3 TP 0,5/0,7/1R + 2 jalan": dict(tps=[0.5, 0.7, 1.0, N, N]),
    "3 TP 0,5/1/1,5R + 2 jalan": dict(tps=[0.5, 1.0, 1.5, N, N]),
    "4 TP 0,3/0,5/0,7/1R + 1 jalan": dict(tps=[0.3, 0.5, 0.7, 1.0, N]),
    "4 TP 0,5/0,7/1/1,5R + 1 jalan": dict(tps=[0.5, 0.7, 1.0, 1.5, N]),
    "2 TP 0,5/1R + 3 jalan": dict(tps=[0.5, 1.0, N, N, N]),
    "3 TP 0,5R semua + 2 jalan": dict(tps=[0.5, 0.5, 0.5, N, N]),
    "3 TP 1R semua + 2 jalan": dict(tps=[1.0, 1.0, 1.0, N, N]),
    "5 TP pendek 0,3/0,5/0,7/1/1,5R (tanpa jalan)": dict(tps=[0.3, 0.5, 0.7, 1.0, 1.5]),
    "5 TP 0,5R semua (WR maksimal)": dict(tps=[0.5] * 5),
    "3 TP 0,5/0,7/1R + 2 jalan, SL+ setelah TP ke-2": dict(tps=[0.5, 0.7, 1.0, N, N], be=False, be_at=0.7),
    "3 TP 0,5/1/1,5R + 2 jalan, SL+ setelah 1R": dict(tps=[0.5, 1.0, 1.5, N, N], be=False, be_at=1.0),
}


def report() -> str:
    L = ["# Skema WR tinggi: TP pendek + 1-2 posisi berjalan (research/skema_wr.py)", "",
         "WR = sinyal dengan hasil bersih > 0. R per sinyal = rata-rata 5 posisi. DD = penurunan terdalam (R).", ""]
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        L.append(f"== {name} (LAMA < {split:%Y}) ==")
        L.append(f"  {'skema':48} {'sinyal':>6} {'WR':>6} {'R/sin':>7} {'total':>7} {'DD':>6} {'LAMA':>7} {'BARU':>7} "
                 f"{'tahun+':>6} | vs bawaan")
        base = None
        for vname, v in VARIANTS.items():
            df = run(name, v)
            s = summary(df, split)
            if base is None:
                base = s
                verdict = ""
            else:
                better = (s["yr"] - base["yr"]).reindex(base["yr"].index).fillna(0)
                nb = int((better > 0).sum())
                ok = (s["latih"] >= base["latih"] and s["uji"] >= base["uji"] and s["tot"] >= base["tot"]
                      and s["dd"] >= base["dd"] and nb >= 0.6 * len(better))
                verdict = f"lebih baik {nb}/{len(better)} th → {'LOLOS' if ok else 'tidak'}"
            # rugi beruntun terpanjang (sinyal) — terasa paling menyakitkan bagi pengguna
            r = df.sort_values("t").R.to_numpy()
            streak = max((len(x) for x in "".join("L" if v <= 0 else "W" for v in r).split("W")), default=0)
            L.append(f"  {vname:48} {s['n']:6d} {s['wr']:5.1f}% {s['avg']:+7.3f} {s['tot']:+7.1f} {s['dd']:+6.1f} "
                     f"{s['latih']:+7.3f} {s['uji']:+7.3f} {s['tahun']:>6} | {verdict} | kalah beruntun maks {streak}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
