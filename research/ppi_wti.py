"""⛽ PPI-WTI → cloud/api/ppi_wti.json (angka uji untuk kartu PPI di aplikasi) — python -m research.ppi_wti

Aturan pra-registrasi (research/riset_inflasi.py, 11 Okt; lolos semua kriteria 13 Okt; verifikasi research/ppi_wti_cek.py):
rata-rata WTI (FRED DCOILWTICO) 5 observasi s/d tgl 13 bulan acuan vs bulan sebelumnya naik ≥ 5% → PPI di atas konsensus →
emas TURUN; turun ≥ 5% → emas NAIK. Angka yang disimpan = aturan MENTAH (tetap sejak pra-registrasi) 2016–2026: lonjakan
menit 1, kurva detik 1–10 + 15 dtk…5 mnt (cara sama dengan research/cpi_detik_penuh), strategi modal kecil (lentur).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_allin2 import SPLIT, arr, sim_keluar
from .cpi_detik_penuh import DETIK, gerak_semua
from .exness import ticks_around
from .ppi_wti_cek import tabel

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloud" / "api" / "ppi_wti.json"


def main() -> dict:
    p = tabel()
    p = p[p.t0 >= "2016-01-01"].reset_index(drop=True)
    tb = -p.WTI
    lama, baru, b24 = p.t0 < SPLIT, p.t0 >= SPLIT, p.th >= 2024

    def pct(y, m):
        y = np.sign(pd.Series(y).fillna(0))
        k = m & (tb != 0) & (y != 0)
        return (round(float((tb[k] == y[k]).mean() * 100), 1), int(k.sum())) if k.sum() else (None, 0)
    allm = pd.Series(True, index=p.index)
    lj = {nama: pct(p.L, m) for nama, m in (("semua", allm), ("lama", lama), ("baru", baru), ("s2024", b24))}
    g = gerak_semua(p.t0).set_index("t0").reindex(p.t0).reset_index(drop=True)
    kurva = {str(h): pct(g[f"y{h}"], allm)[0] for h in DETIK}
    A = {i: arr(tk, r.t0) for i, r in p.iterrows() if tb[i] != 0 and (tk := ticks_around("XAUUSDc", r.t0)) is not None}
    allin = {}
    for lev in (100, 200, 500):
        rec = [(p.t0[i], *o) for i, a in A.items() if (o := sim_keluar(a, int(tb[i]), ("lentur", 10), lev))]
        x = pd.DataFrame(rec, columns=["t0", "pl", "mc"])
        b, lm = x[x.t0 >= SPLIT], x[x.t0 < SPLIT]
        allin[str(lev)] = {"rata": round(float(b.pl.mean()), 1), "mc": int(b.mc.sum()), "lama_rata": round(float(lm.pl.mean()), 1),
                           "untung_baru": round(float((b.pl > 0).mean() * 100)), "n_baru": len(b)}
    out = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
           "aturan": "WTI 5 hari s/d tgl 13 bulan acuan vs bulan sebelumnya ≥ +5% → PPI di atas → emas TURUN; ≤ −5% → NAIK",
           "ambang": 5.0, "lonjakan": {k: {"persen": v[0], "n": v[1]} for k, v in lj.items()},
           "per_detik": kurva, "allin_lentur": allin,
           "verifikasi": "ambang 3–10% 66–71%; rata sebulan 66%; Dukascopy 66%; p keluarga 0,004/0,009; tanpa look-ahead"}
    lama_isi = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out.update({k: lama_isi[k] for k in ("cpi_ppi",) if k in lama_isi})     # dari research/ppi_dasar.py simpan
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
