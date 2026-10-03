"""Riwayat sinyal 💰 per tahun & 90 / 365 hari terakhir -> cloud/api/riwayat.json (kartu 📜 tab Statistik, 3.25).

python -m research.riwayat_uang

Permintaan pengguna (3 Okt 2026): "pasang riwayat 💰" setelah bertanya apakah sinyal 💰 masih akurat. Mesin = cloud
(research/sl_tangga.run, skema bawaan TP1 1R + 4 jalan). WR = sinyal dengan hasil bersih > 0; R = rata-rata 5 posisi
(1R = rugi bila SL awal kena). Jalankan ulang bila data harga diperbarui.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .sl_tangga import run

OUT = Path(__file__).resolve().parent.parent / "cloud" / "api" / "riwayat.json"


def cell(r: pd.Series) -> dict:
    return {"n": int(len(r)), "wr": round(float((r > 0).mean() * 100), 1), "avg": round(float(r.mean()), 3),
            "tot": round(float(r.sum()), 1)}


def main() -> None:
    out = {"dibuat": "research/riwayat_uang.py", "skema": "TP1 1R + 4 jalan, SL+ setelah TP1"}
    for name, key in (("XAUUSD", "XAU"), ("BTCUSD", "BTC")):
        df = run(name, dict(tps=[1.0, None, None, None, None]))
        end = df.t.max()
        out[key] = {"sampai": f"{end:%Y-%m-%d}",
                    "tahun": {str(y): cell(g.R) for y, g in df.groupby(df.t.dt.year)},
                    "90h": cell(df[df.t > end - pd.Timedelta(days=90)].R),
                    "365h": cell(df[df.t > end - pd.Timedelta(days=365)].R),
                    "semua": cell(df.R)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if k in ("dibuat", "skema") else {x: v[x] for x in ("sampai", "90h", "365h", "semua")})
                      for k, v in out.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
