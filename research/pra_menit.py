"""⏱️ Arah SETELAH beberapa menit: bila emas di detik 2 sudah bergerak ≥ $0,50 (atau ≥ $1), seberapa sering arahnya masih
sama di detik 10, 30 dan menit 1, 3, 5, 10, 15, 30, 60 setelah rilis — per jenis berita.

python -m research.pra_menit              → docs/eksternal/hasil_pra_menit.txt + cloud/api/pra_aset.json["menit"]

Permintaan pengguna 10 Okt 2026: "pasang juga setelah beberapa menit arah naik atau turun". Tebakan SEBELUM rilis kembali
≈ 50:50 setelah ±1–3 menit (research/pra_jangka.py), jadi arah menit ke depan hanya bisa dibaca SETELAH rilis: arah
detik 2 (harga tengah t0+2 dtk vs t0−1 dtk, tick Exness, cadangan Dukascopy) dibandingkan arah di jangka h.
Semua 2.051 rilis USD 2010–2026 (research/pra_xau_semua.py), dibagi LAMA (< Okt 2021) & BARU.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import NEW
from .pra_jangka import CANDLE, DETIK, gerak, label

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_menit.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
CACHE = ROOT / "data" / "research" / "eksternal" / "pra_menit.parquet"
JANGKA = [h for h in DETIK + CANDLE if h >= 10]
GRUP = ("SEMUA", "NFP", "CPI", "PPI", "RETAIL", "PCE", "GDP", "FOMC", "JOLTS", "ISM", "ADP", "CLAIMS", "KONSUMEN")


def tabel() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .pra_xau_semua import bangun
    d = bangun()[["t0", "grup"]]
    gk = gerak(list(d.t0))
    rows = []
    for t, g in zip(d.t0, d.grup):
        r = gk.get(pd.Timestamp(t))
        if r:
            rows.append({"t0": t, "grup": g, **{f"m{h}": r.get(h, np.nan) for h in [2] + JANGKA}})
    x = pd.DataFrame(rows)
    x.to_parquet(CACHE)
    return x


def main() -> None:
    x = tabel()
    L = ["# ⏱️ Arah setelah beberapa menit — ikuti arah detik 2?", __doc__.split("\n\n")[1], "",
         f"Rilis dengan data: {len(x)}"]
    hasil = {}
    for ambang in (0.5, 1.0):
        L.append(f"\n## Gerak detik 2 ≥ ${ambang:.2f} → arah sama di jangka h (LAMA / BARU)")
        for g in GRUP:
            z = x if g == "SEMUA" else x[x.grup == g]
            z = z[z.m2.abs() >= ambang]
            if len(z) < 15:
                continue
            t = pd.DatetimeIndex(z.t0)
            r = {}
            for h in JANGKA:
                y = z[f"m{h}"]
                m = y.notna() & (y != 0)
                same = np.sign(y[m]) == np.sign(z.m2[m])
                tt = t[m.to_numpy()]
                r[str(h)] = {"sama": round(float(same.mean() * 100), 1), "n": int(m.sum()),
                             "lama": round(float(same[tt < NEW].mean() * 100), 1) if (tt < NEW).any() else None,
                             "baru": round(float(same[tt >= NEW].mean() * 100), 1) if (tt >= NEW).any() else None}
            hasil.setdefault(f"{ambang:g}", {})[g] = r
            L.append(f"   {g:9s} (n {len(z)}) " + " | ".join(f"{label(int(h))} {v['sama']:.0f}%" for h, v in r.items()))
        L.append("   LAMA/BARU 5 mnt: " + ", ".join(
            f"{g} {v['300']['lama']}/{v['300']['baru']}" for g, v in hasil.get(f"{ambang:g}", {}).items() if "300" in v))
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["menit"] = hasil
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
