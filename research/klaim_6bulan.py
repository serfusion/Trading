"""Uji klaim "EA sudah jalan 6 bulan" (3 Okt 2026) — python -m research.klaim_6bulan

Aturan rekonstruksi Signal Strike (research/tiru_150.BASIS: lot x1,2 per layer, TP rata-rata +$1,9, jarak $2,25,
jeda 30/45 mnt antar keranjang = kalibrasi September) dijalankan:
1. dari setiap hari 15 Mar – 15 Apr 2026 sampai data terakhir (2 Okt 2026): berapa yang bertahan ±6 bulan?
2. dari setiap Senin 2012–2026: peluang bertahan 182 hari (LAMA < Okt 2021, BARU Okt 2021+).
3. kejadian yang menghabiskan akun Apr–Sep 2026 (EA jalan terus, setor ulang setelah habis) + gerak emas saat itu.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .martingale_ea import SPLIT, load, sim
from .tiru_150 import BASIS, jalan

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_klaim_6bulan.txt"
KONFIG = [v for v in BASIS if v[9]] + [
    ("S5 jarak $3, 0,03 lot/$524, jeda 45 mnt (paling awet)", 1, 0.03, 1.2, 3.0, 1.9, 40, BASIS[0][7], True, 45),
]


def mulai_apr(df: pd.DataFrame, v: tuple, out: list) -> None:
    t1 = df.index[-1]
    rows = []
    for a in pd.date_range(pd.Timestamp("2026-03-15", tz="UTC"), pd.Timestamp("2026-04-15", tz="UTC"), freq="D"):
        hasil, n, tr, tarik = jalan(df, v, a, t1 + pd.Timedelta(minutes=5), stop=True)
        rows.append(dict(t=a, hidup=n == 0, tr=tr, tarik=tarik, hasil=hasil))
    m = pd.DataFrame(rows)
    ok = m[m.hidup]
    habis = m[~m.hidup]
    out.append(f"  mulai 15 Mar–15 Apr 2026 ({len(m)} tanggal): bertahan s/d {t1:%d %b} {len(ok)} ({100 * len(ok) / len(m):.0f}%)"
               + (f", profit ditarik median ${ok.tarik.median():,.0f}" if len(ok) else "")
               + (f"; habis: tanggal habis pertama median {pd.DatetimeIndex(habis.tr).sort_values()[len(habis) // 2]:%d %b}"
                  f", ditarik sebelum habis median ${habis.tarik.median():,.0f}" if len(habis) else ""))
    if len(habis):
        out.append("    tanggal habis: " + ", ".join(sorted({f"{x:%d/%m}" for x in habis.tr})))


def peluang_182(df: pd.DataFrame, v: tuple, out: list) -> None:
    t1 = df.index[-1]
    rows = []
    for a in pd.date_range(pd.Timestamp("2012-06-04", tz="UTC"), t1 - pd.Timedelta(days=182), freq="W-MON"):
        hasil, n, tr, tarik = jalan(df, v, a, a + pd.Timedelta(days=182), stop=True)
        rows.append(dict(t=a, hidup=n == 0))
    m = pd.DataFrame(rows)
    th = m.groupby(m.t.dt.year).hidup.mean()
    out.append(f"  bertahan 182 hari dari tiap Senin: LAMA {100 * m[m.t < SPLIT].hidup.mean():.0f}% (n {int((m.t < SPLIT).sum())})"
               f", BARU {100 * m[m.t >= SPLIT].hidup.mean():.0f}% (n {int((m.t >= SPLIT).sum())}); per tahun mulai: "
               + " ".join(f"{y}:{100 * p:.0f}%" for y, p in th.items()))


def kejadian(df: pd.DataFrame, v: tuple, out: list) -> None:
    t = df.index
    i0 = int(t.searchsorted(pd.Timestamp("2026-04-01", tz="UTC")))
    info: list = []
    cl, ruins, _, _ = sim(df, *v[1:9], i0=i0, info=info, jeda_menit=v[9])
    out.append(f"  jalan terus 1 Apr–2 Okt (setor ulang setelah habis): profit tertutup ${cl.usc.sum() / 100:,.0f}, akun habis "
               f"{len(ruins)}x (−${len(ruins) * v[7] / 100:,.0f})")
    h, l = df.high.to_numpy(), df.low.to_numpy()
    for r in info:
        if r[4] is None:
            j = r[0]
            k = max(int(t.searchsorted(t[j] - pd.Timedelta(hours=6))), 0)
            puncak = int(np.argmax(h[k:j + 1])) + k
            out.append(f"    {t[j]:%d %b %H:%M} UTC: {r[1]} layer; emas {h[puncak]:,.0f} ({t[puncak]:%H:%M}) → {l[j]:,.0f} "
                       f"(−${h[puncak] - l[j]:,.0f})")


def main() -> None:
    df = load()
    out = [f"Data s/d {df.index[-1]:%Y-%m-%d %H:%M} UTC. Klaim: EA sudah jalan 6 bulan (± April–September 2026).", ""]
    for v in KONFIG:
        out.append(v[0])
        mulai_apr(df, v, out)
        peluang_182(df, v, out)
        kejadian(df, v, out)
        out.append("")
        print("\n".join(out[-12:]), flush=True)
    OUT.write_text("\n".join(out) + "\n")
    print("->", OUT)


if __name__ == "__main__":
    main()
