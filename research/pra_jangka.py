"""⏱️ Berlaku sampai kapan? Ketepatan tiap aturan arah XAU dari 1 detik sampai 1 jam setelah rilis.

python -m research.pra_jangka              → docs/eksternal/hasil_pra_jangka.txt + cloud/api/pra_aset.json["jangka"]

Permintaan pengguna 10 Okt 2026: "tambahkan keterangan 1–X detik — setelah X detik/menit naik X%, untuk semua news".
Untuk setiap aturan yang dipakai aplikasi (pra_aset.json["xau_arah"] + kalender BLS + tren 4 jam saja), harga tengah
XAU 1 detik sebelum rilis dibandingkan dengan harga pada 1/2/3/5/10/30 detik, 1/3/5/10/15 menit (tick Exness, cadangan
Dukascopy; jendela tick s.d. 16 menit) dan 30 menit / 1 jam (open candle M15). Benar = searah tebakan.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import NEW, prepare

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_jangka.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
DETIK = [1, 2, 3, 5, 10, 30, 60, 180, 300, 600, 900]
CANDLE = [1800, 3600]
SEMUA = DETIK + CANDLE


def gerak(times) -> dict:
    """waktu → {detik: perubahan harga tengah dari t0−1}."""
    from .event_stats import xau_m15
    m15 = xau_m15()
    out = {}
    for t in times:
        t = pd.Timestamp(t)
        r = {}
        for f in ("XAU_EXNESS", "XAU"):
            p = prepare(t, f)
            if p is None:
                continue
            i = p.at(-1)
            if i < 0 or p.T[i] < -60:
                continue
            m0 = float(p.mid[i])
            for h in DETIK:
                k = p.at(h)
                if k >= 0 and p.T[k] >= h - 120:
                    r[h] = float(p.mid[k] - m0)
            for h in CANDLE:
                ts = t + pd.Timedelta(seconds=h)
                k = m15.index.searchsorted(ts)
                if k < len(m15) and m15.index[k] - ts <= pd.Timedelta(minutes=15):
                    r[h] = float(m15.open.iloc[k] - m0)
            break
        if r:
            out[t] = r
    return out


def profil(arah: pd.Series, gk: dict) -> dict:
    hasil = {}
    for h in SEMUA:
        rows = [(t, np.sign(gk[t][h]) * d) for t, d in arah.items() if t in gk and h in gk[t] and gk[t][h] != 0]
        if not rows:
            continue
        tt = pd.DatetimeIndex([r[0] for r in rows])
        ok = np.array([r[1] > 0 for r in rows])
        hasil[str(h)] = {"benar": round(float(ok.mean() * 100), 1), "n": int(len(ok)),
                         "lama": round(float(ok[tt < NEW].mean() * 100), 1) if (tt < NEW).any() else None,
                         "baru": round(float(ok[tt >= NEW].mean() * 100), 1) if (tt >= NEW).any() else None}
    return hasil


def aturan() -> dict[str, pd.Series]:
    from .pra_xau_arah import varian
    from .pra_xau_semua import bangun
    from .pra_per_berita import pekan_survei, bulan_acuan
    out = {nama: s for nama, (_, s) in varian().items()}
    d = bangun()
    nfp = d[d.grup == "NFP"]
    v = []
    for t in nfp.t0:
        m1 = bulan_acuan(pd.Timestamp(t))
        gap = (pekan_survei(m1) - pekan_survei((m1.to_period("M") - 1).to_timestamp())).days
        v.append(1.0 if gap >= 35 else -1.0)                 # 5 pekan → pengangguran di atas → emas NAIK
    out["Pengangguran • kalender survei BLS"] = pd.Series(v, index=pd.DatetimeIndex(nfp.t0))
    tanpa = d[d.KEJ.fillna(0) == 0]
    s = tanpa.H4.fillna(0)
    out["Tren emas 4 jam (berita tanpa petunjuk)"] = pd.Series(s.to_numpy(), index=pd.DatetimeIndex(tanpa.t0))[s.to_numpy() != 0]
    return out


def label(h: int) -> str:
    return f"{h} dtk" if h < 60 else f"{h // 60} mnt" if h < 3600 else "1 jam"


def main() -> None:
    A = aturan()
    times = sorted({t for s in A.values() for t in s.index})
    gk = gerak(times)
    hasil = {nama: profil(s, gk) for nama, s in A.items()}
    L = ["# ⏱️ Berlaku sampai kapan? Ketepatan arah tiap aturan 1 detik – 1 jam setelah rilis", __doc__.split("\n\n")[1], ""]
    for nama, p in hasil.items():
        L.append(f"\n## {nama}")
        L.append("   " + " | ".join(f"{label(int(h))} {v['benar']}% (n {v['n']})" for h, v in p.items()))
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["jangka"] = hasil
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
