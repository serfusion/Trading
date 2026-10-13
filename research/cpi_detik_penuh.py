"""⏱️ CPI: persen arah emas untuk SETIAP detik 1–10 (+ 15 dtk … 5 mnt) → cloud/api/cpi_detik.json["uji"]["saring"]

python -m research.cpi_detik_penuh

Permintaan pengguna 13 Okt 2026: "saya berharap per detik dan berubah persentase di apk, akan terus saya buka sebelum hingga
sesudah news". Dulu hanya detik 1/2/3/5/10. Cara SAMA dengan research/cpi_detik.tepat: mid emas di detik s vs tick terakhir
≤ t0 − 1 dtk (feed Exness, cadangan Dukascopy — sama dengan pra_xau_semua), rilis diam tidak dihitung, tebakan tutup kertas
IDX|K+S (kuat) dan yang kena saringan (⚠️ lemah), CPI 2013–2026.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .news_detik import prepare

DETIK = list(range(1, 11)) + [15, 20, 30, 45, 60, 90, 120, 180, 240, 300]


def gerak_semua(t0s) -> pd.DataFrame:
    rows = []
    for t in t0s:
        row = {"t0": t}
        for f in ("XAU_EXNESS", "XAU"):
            p = prepare(t, f)
            if p is None:
                continue
            i = p.at(-1)
            if i < 1 or p.T[i] < -60:
                continue
            m0 = float(p.mid[i])
            for h in DETIK:
                k = p.at(h)
                if k >= 0 and f"y{h}" not in row:
                    row[f"y{h}"] = float(p.mid[k] - m0)
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> dict:
    df = C.turunan(C.tabel())
    ts = C.tetap(df, "IDX|K+S")
    tb = C.tetap(df, "IDX|K")
    lm = pd.Series(np.where((tb != 0) & (ts == 0), tb, 0.0), index=df.index)
    g = gerak_semua(df.t0).set_index("t0").reindex(df.t0).reset_index(drop=True)
    m = df.th >= C.MULAI
    baru = df.t0 >= "2021-10-01"

    def kurva(tebak, mask):
        out = {}
        for h in DETIK:
            y = np.sign(g[f"y{h}"].fillna(0))
            ok = mask & (tebak != 0) & (y != 0)
            out[str(h)] = round(float((y[ok] == tebak[ok]).mean() * 100), 1) if ok.sum() else None
        return out
    hasil = {"kuat": kurva(ts, m), "kuat_baru": kurva(ts, m & baru), "lemah": kurva(lm, m), "lemah_baru": kurva(lm, m & baru)}
    f = C.JSON
    d = json.loads(f.read_text(encoding="utf-8"))
    s = d["uji"]["saring"]
    s["per_detik_penuh"], s["per_detik_penuh_baru"] = hasil["kuat"], hasil["kuat_baru"]
    s["lemah"]["per_detik_penuh"], s["lemah"]["per_detik_penuh_baru"] = hasil["lemah"], hasil["lemah_baru"]
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("lama (per_detik):", s["per_detik"])
    for k, v in hasil.items():
        print(k, v)
    return hasil


if __name__ == "__main__":
    main()
