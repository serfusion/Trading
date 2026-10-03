"""Lonjakan emas setelah berita: memudar bila MELAWAN tren besar? python -m research.berita_tren [ekspor]

Pertanyaan pengguna (2 Okt 2026): NFP lemah (29K vs 89K) -> emas +$44 dalam 30 menit, lalu turun $85 dan berakhir di
bawah harga sebelum rilis. Konteks: emas sedang turun ±2% sepekan (yield AS 10 th tertinggi sejak 2002, Fed menaikkan
bunga). Hipotesis (ditetapkan sebelum melihat hasil): lonjakan berita yang MELAWAN tren besar lebih sering memudar
daripada lonjakan yang SEARAH tren.

Data: XAU M15 (research/event_stats.xau_m15, 2012-2026), rilis berita AS utama (research/news_prediksi.calendar(),
judul di research/news_prediksi.EVENTS, satu baris per waktu rilis). Tanpa look-ahead:
- lonjakan = arah gerak open candle rilis -> close 15 menit (|gerak| >= $1, dan >= 0,1 x ATR harian);
- tren besar diukur SEBELUM rilis: (a) D1 = close kemarin vs EMA50 harian s.d. kemarin; (b) 20 hari = close candle
  sebelum rilis vs close 20 hari bursa sebelumnya; (c) keduanya searah.
- hasil: apakah harga 1 / 3 / 6 jam dan akhir hari (21:00 UTC) masih di sisi lonjakan dari harga open rilis, dan
  "memudar habis" = berbalik melewati harga open rilis dalam 6 jam. LAMA (< Okt 2021) & BARU dilaporkan.
Hipotesis 2 (setelah hipotesis 1 GAGAL): bagian lonjakan yang sudah dikembalikan di menit 30 / 60 (diketahui saat itu)
memprediksi arah 3-6 jam. 2 Okt 2026: puncak +$44 (menit 33), menit 60 sisa +$12 (= 27%).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .event_stats import xau_m15
from .news_detik import NEW
from .news_prediksi import EVENTS, calendar

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_berita_tren.txt"
HOURS = (1, 3, 6)


def build() -> pd.DataFrame:
    m = xau_m15()
    idx = m.index
    d1 = m.close.resample("1D").last().dropna()
    ema = d1.ewm(span=50, adjust=True).mean()
    rng = (m.high.resample("1D").max() - m.low.resample("1D").min()).dropna()
    atr = rng.rolling(14).mean()
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS)]
    times = sorted(cal.time.unique())
    groups = cal.groupby("time").event.apply(lambda v: "/".join(sorted(set(v))))
    rows = []
    for t in times:
        t = pd.Timestamp(t)
        k = idx.searchsorted(t)
        if k >= len(idx) or idx[k] != t or k < 1:
            continue
        day = t.normalize()
        prev = d1[d1.index < day]
        if len(prev) < 60:
            continue
        o = m.open.iloc[k]
        j15 = idx.searchsorted(t + pd.Timedelta(minutes=15)) - 1
        spike = m.close.iloc[j15] - o
        a = atr[atr.index < day].iloc[-1]
        if abs(spike) < max(1.0, 0.1 * a):
            continue
        s = np.sign(spike)
        tr_d1 = np.sign(prev.iloc[-1] - ema[ema.index < day].iloc[-1])
        tr_20 = np.sign(m.close.iloc[k - 1] - prev.iloc[-20])
        row = {"time": t, "events": groups.get(t, ""), "spike": float(spike), "tr_d1": tr_d1, "tr_20": tr_20}
        win = m.iloc[k:idx.searchsorted(t + pd.Timedelta(hours=6))]
        for h in HOURS:
            j = idx.searchsorted(t + pd.Timedelta(hours=h)) - 1
            row[f"h{h}"] = float((m.close.iloc[j] - o) * s)
        eod = t.normalize() + pd.Timedelta(hours=21)
        j = idx.searchsorted(eod) - 1
        row["eod"] = float((m.close.iloc[j] - o) * s) if idx[j] > t else np.nan
        # petunjuk dini (diketahui saat itu): bagian lonjakan yang SUDAH dikembalikan di menit 30 / 60
        for mins in (30, 60):
            jm = idx.searchsorted(t + pd.Timedelta(minutes=mins)) - 1
            w = m.iloc[k:jm + 1]
            peak = float(((w.high - o) if s > 0 else (o - w.low)).max())
            now_ = float((m.close.iloc[jm] - o) * s)
            row[f"keep{mins}"] = now_ / peak if peak > 0 else np.nan
            row[f"peak{mins}"] = peak
        # memudar habis: setelah lonjakan, harga melewati open rilis ke arah sebaliknya dalam 6 jam
        row["fade"] = bool(((win.low <= o) if s > 0 else (win.high >= o)).iloc[2:].any()) if len(win) > 2 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def line(name: str, x: pd.DataFrame) -> str:
    if len(x) < 5:
        return f"  {name:48} n={len(x)}"
    cells = " • ".join(f"{h} jam {(x[f'h{h}'] > 0).mean() * 100:3.0f}%" for h in HOURS)
    return (f"  {name:48} n={len(x):4} masih searah lonjakan: {cells} • akhir hari {(x.eod > 0).mean() * 100:3.0f}% | "
            f"berbalik lewat harga awal ≤ 6 jam {x.fade.mean() * 100:3.0f}% | rata 6 jam {x.h6.mean():+5.1f}$")


def report() -> str:
    d = build()
    L = ["# Lonjakan berita searah vs melawan tren besar (research/berita_tren.py)", "",
         f"{len(d)} rilis dengan lonjakan 15 menit ≥ $1 dan ≥ 0,1 ATR harian, {d.time.min():%Y}–{d.time.max():%Y}.", ""]
    for tr in ("tr_d1", "tr_20"):
        lab = {"tr_d1": "tren D1 (close vs EMA50)", "tr_20": "tren 20 hari"}[tr]
        L.append(f"== {lab} ==")
        for name, x in (("semua", d), ("LAMA < Okt 2021", d[d.time < NEW]), ("BARU", d[d.time >= NEW])):
            L.append(f" [{name}]")
            L.append(line("lonjakan SEARAH tren", x[np.sign(x.spike) == x[tr]]))
            L.append(line("lonjakan MELAWAN tren", x[np.sign(x.spike) == -x[tr]]))
        L.append("")
    both = d[(d.tr_d1 == d.tr_20)]
    L.append("== D1 & 20 hari sepakat ==")
    for name, x in (("semua", both), ("LAMA < Okt 2021", both[both.time < NEW]), ("BARU", both[both.time >= NEW])):
        L.append(f" [{name}]")
        L.append(line("lonjakan SEARAH tren", x[np.sign(x.spike) == x.tr_d1]))
        L.append(line("lonjakan MELAWAN tren", x[np.sign(x.spike) == -x.tr_d1]))
    for mins in (30, 60):
        L.append(f"\n== Petunjuk dini: sisa lonjakan di menit ke-{mins} (harga sekarang - open) / puncak lonjakan ==")
        for name, x in (("semua", d), ("LAMA < Okt 2021", d[d.time < NEW]), ("BARU", d[d.time >= NEW])):
            L.append(f" [{name}]")
            for lo, hi, lab in ((-9, 0.0, "sudah berbalik (< 0%)"), (0.0, 0.3, "sisa 0–30% (dikembalikan ≥ 70%)"),
                                (0.3, 0.6, "sisa 30–60%"), (0.6, 9, "sisa ≥ 60% (bertahan)")):
                L.append(line(lab, x[(x[f"keep{mins}"] >= lo) & (x[f"keep{mins}"] < hi)]))
    nfp = d[d.events.str.contains("Non-Farm")]
    L.append("\n== Khusus NFP (tren D1) ==")
    L.append(line("lonjakan SEARAH tren", nfp[np.sign(nfp.spike) == nfp.tr_d1]))
    L.append(line("lonjakan MELAWAN tren", nfp[np.sign(nfp.spike) == -nfp.tr_d1]))
    L.append("\n== Khusus NFP: sisa lonjakan di menit ke-60 ==")
    for lo, hi, lab in ((-9, 0.3, "sisa < 30% (dikembalikan ≥ 70%)"), (0.3, 9, "sisa ≥ 30%")):
        L.append(line(lab, nfp[(nfp.keep60 >= lo) & (nfp.keep60 < hi)]))
    up = d[d.spike > 0]
    L.append("\n== Lonjakan NAIK saat tren D1 TURUN (kasus 2 Okt 2026) ==")
    L.append(line("semua berita", up[up.tr_d1 < 0]))
    L.append(line("bandingkan: lonjakan naik saat tren naik", up[up.tr_d1 > 0]))
    return "\n".join(L) + "\n"


BUCKETS = ((-9.0, 0.0, "sudah berbalik"), (0.0, 0.3, "sisa < 30%"), (0.3, 0.6, "sisa 30–60%"), (0.6, 9.0, "sisa ≥ 60%"))
CLOUD = Path(__file__).resolve().parent.parent / "cloud" / "api" / "pudar.json"


def export() -> dict:
    """cloud/api/pudar.json: hasil per kelompok "sisa lonjakan" di menit 30 & 60 (semua berita & NFP)."""
    import json
    d = build()

    def cells(x: pd.DataFrame, col: str) -> list[dict]:
        out = []
        for lo, hi, lab in BUCKETS:
            k = x[(x[col] >= lo) & (x[col] < hi)]
            kb = k[k.time >= NEW]
            if len(k) < 10:
                continue
            out.append({"lo": lo, "hi": hi, "label": lab, "n": int(len(k)),
                        "h3": round(float((k.h3 > 0).mean()), 3), "h6": round(float((k.h6 > 0).mean()), 3),
                        "fade": round(float(k.fade.mean()), 3),
                        "baru_h6": round(float((kb.h6 > 0).mean()), 3) if len(kb) >= 10 else None})
        return out
    nfp = d[d.events.str.contains("Non-Farm")]
    data = {"dibuat": "research/berita_tren.py ekspor", "periode": f"{d.time.min():%Y}–{d.time.max():%Y}",
            "min_lonjakan": 1.0, "semua": {str(mm): cells(d, f"keep{mm}") for mm in (30, 60)},
            "nfp": {str(mm): cells(nfp, f"keep{mm}") for mm in (30, 60)}}
    CLOUD.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return data


def main() -> None:
    import sys
    if sys.argv[1:] == ["ekspor"]:
        import json
        print(json.dumps(export(), ensure_ascii=False, indent=1))
        return
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
