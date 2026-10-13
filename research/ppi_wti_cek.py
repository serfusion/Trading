"""✅ Verifikasi adversarial kandidat PPI-WTI (research/riset_inflasi.py, lolos semua kriteria 13 Okt 2026)

python -m research.ppi_wti_cek     → docs/eksternal/hasil_ppi_wti_cek.txt

Aturan pra-registrasi (11 Okt): rata-rata WTI (FRED DCOILWTICO) 5 observasi s/d tgl 13 bulan acuan vs bulan sebelumnya naik
≥ 5% → PPI di atas konsensus → emas TURUN; turun ≥ 5% → emas NAIK. Cek: (1) aturan MENTAH tanpa tutup kertas per periode &
per tahun, target lonjakan menit 1 & detik 1/2/2–10; (2) kepekaan ambang 3–10% & jendela (rata-rata sebulan penuh); (3) rilis
bersamaan (Retail Sales dll.) vs sendiri; (4) uang: strategi modal kecil t−1 dtk (tick Exness) vs arah acak; (5) look-ahead:
data WTI terakhir yang dipakai vs tanggal rilis; (6) nilai sinyal untuk PPI 15 Okt 2026 (FRED terbaru).
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_allin2 import SPLIT, arr, sim_keluar
from .exness import ticks_around
from .riset_inflasi import harian, jendela13, ubah_bulan, ubah_energi

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_ppi_wti_cek.txt"


def tabel() -> pd.DataFrame:
    p = pd.read_pickle(EKS / "riset_inflasi" / "petunjuk.parquet")
    p = p[p.grup == "PPI"].copy()
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")[["t0", "y1_XAU_EXNESS", "y1_XAU"]]
    v["g1"] = v.y1_XAU_EXNESS.fillna(v.y1_XAU)
    return p.merge(v[["t0", "g1"]], on="t0", how="left").sort_values("t0").reset_index(drop=True)


def akur(tb, y, mask) -> str:
    y = np.sign(pd.Series(y).fillna(0))
    m = mask & (tb != 0) & (y != 0)
    return f"{(tb[m] == y[m]).mean() * 100:4.0f}% ({m.sum():2d})" if m.sum() else "   – ( 0)"


def main() -> None:
    p = tabel()
    wti = harian("DCOILWTICO")
    tb = -p.WTI                                                      # emas = kebalikan arah PPI
    m16 = p.t0 >= "2016-01-01"
    lama, baru = m16 & (p.t0 < SPLIT), p.t0 >= SPLIT
    L = ["# ✅ Verifikasi kandidat PPI-WTI (research/ppi_wti_cek.py)", __doc__.split("\n\n")[1], ""]
    L.append("## 1. Aturan MENTAH (tanpa tutup kertas) — benar % (n)")
    L.append("   target            2016–26        LAMA          BARU        2024+")
    for nama, y in (("lonjakan menit 1", p.L), ("detik 1", p.g1), ("detik 2", p.g2), ("detik 3", p.g3), ("detik 5", p.g5),
                    ("detik 10", p.g10)):
        L.append(f"   {nama:16s} {akur(tb, y, m16)}  {akur(tb, y, lama)}  {akur(tb, y, baru)}  {akur(tb, y, p.th >= 2024)}")
    L.append("   per tahun (lonjakan): " + " ".join(
        f"{th % 100}:{int(((tb == np.sign(p.L)) & (tb != 0) & (p.th == th)).sum())}/{int(((tb != 0) & (p.th == th) & (p.L != 0)).sum())}"
        for th in range(2014, 2027)))
    L.append(f"   tebakan: NAIK {int((tb > 0).sum())} • TURUN {int((tb < 0).sum())} • tidak menebak {int((tb == 0).sum())} dari {len(p)}")
    L.append(f"   kejutan angka PPI searah aturan: {akur(p.WTI, p.s, m16)}")
    L.append("\n## 2. Kepekaan ambang & jendela (lonjakan menit 1, 2016–26 | BARU)")
    for amb in (3, 4, 5, 6, 7, 10):
        s = pd.Series([-ubah_energi(wti, r, amb) for r in p.ref], index=p.index)
        L.append(f"   jendela tgl 13, ambang {amb:2d}%: {akur(s, p.L, m16)} | {akur(s, p.L, baru)} | detik 2 {akur(s, p.g2, m16)}")
    for amb in (3, 5):
        s = pd.Series([-ubah_bulan(wti, r, amb) for r in p.ref], index=p.index)
        L.append(f"   rata sebulan penuh, ambang {amb}%: {akur(s, p.L, m16)} | {akur(s, p.L, baru)} | detik 2 {akur(s, p.g2, m16)}")
    L.append("\n## 3. Rilis bersamaan vs sendiri (lonjakan, 2016–26)")
    b = p.bersama.astype(str).str.len() > 0 if p.bersama.dtype == object else p.bersama.astype(bool)
    L.append(f"   bersamaan: {akur(tb, p.L, m16 & b)} • sendiri: {akur(tb, p.L, m16 & ~b)}")
    # 4. uang
    L.append("\n## 4. Strategi modal kecil (t−1 dtk, tick Exness, per $100) vs arah acak")
    rng = np.random.default_rng(3)
    A = {i: arr(tk, r.t0) for i, r in p.iterrows() if tb[i] != 0 and (tk := ticks_around("XAUUSDc", r.t0)) is not None}
    for kel, lev in ((2, 200), (("lentur", 10), 200), (2, 500), (("lentur", 10), 500)):
        rec = []
        for i, a in A.items():
            o, ob, os_ = sim_keluar(a, int(tb[i]), kel, lev), sim_keluar(a, 1, kel, lev), sim_keluar(a, -1, kel, lev)
            if o and ob and os_:
                rec.append((p.t0[i], o[0], o[1], ob[0], os_[0]))
        x = pd.DataFrame(rec, columns=["t0", "pl", "mc", "buy", "sell"])
        for per, y in (("LAMA", x[x.t0 < SPLIT]), ("BARU", x[x.t0 >= SPLIT])):
            if len(y) < 3:
                L.append(f"   {str(kel):15s} 1:{lev} {per}: n {len(y)}")
                continue
            koin = rng.integers(0, 2, size=(5000, len(y)))
            ac = np.where(koin == 1, y.buy.to_numpy(), y.sell.to_numpy()).mean(axis=1)
            L.append(f"   {str(kel):15s} 1:{lev} {per}: n {len(y):2d} untung {(y.pl > 0).mean() * 100:3.0f}% ${y.pl.mean():+6.1f} "
                     f"(acak ${ac.mean():+6.1f}, p {(ac >= y.pl.mean()).mean():.2f}) habis {int(y.mc.sum())}")
    # 5. look-ahead
    L.append("\n## 5. Look-ahead: jarak data WTI terakhir yang dipakai → rilis PPI (hari)")
    jar = []
    for _, r in p.iterrows():
        x = wti[wti.index <= r.ref + pd.Timedelta(days=12)]
        if len(x):
            jar.append((r.t0.tz_convert(None) - x.index[-1]).days)
    L.append(f"   minimum {min(jar)} hari, median {int(np.median(jar))} hari (data harian FRED terbit H+1) → tanpa look-ahead")
    # 6. sinyal live untuk PPI 15 Okt 2026
    key = os.environ.get("FRED_API_KEY", "")
    try:
        url = (f"https://api.stlouisfed.org/fred/series/observations?series_id=DCOILWTICO&observation_start=2026-07-01"
               f"&api_key={key}&file_type=json")
        obs = json.load(urllib.request.urlopen(url, timeout=30))["observations"]
        s = pd.Series({pd.Timestamp(o["date"]): float(o["value"]) for o in obs if o["value"] != "."}).sort_index()
        a, b_ = jendela13(s, pd.Timestamp("2026-09-01")), jendela13(s, pd.Timestamp("2026-08-01"))
        d = (a / b_ - 1) * 100
        arah = "PPI di ATAS → emas TURUN" if d >= 5 else "PPI di BAWAH → emas NAIK" if d <= -5 else "tidak menebak (< 5%)"
        L.append(f"\n## 6. PPI 15 Okt 2026 (bulan acuan Sep): WTI 5 hari s/d 13 Sep ${a:.2f} vs s/d 13 Agu ${b_:.2f} = "
                 f"{d:+.1f}% → {arah}")
    except Exception as e:  # noqa: BLE001
        L.append(f"\n## 6. FRED gagal: {type(e).__name__}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
