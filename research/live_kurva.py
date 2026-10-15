"""⚡ Kurva persentase SETIAP DETIK 1–60 setelah rilis (15 Okt 2026).

python -m research.live_kurva        → cloud/api/live_kurva.json + docs/eksternal/hasil_live_kurva.txt

Pengguna 15 Okt: "saya membutuhkan data persentase 1 detik hingga 1 menit awal minimal 70%". Sebelum rilis tidak mungkin
(detik 1 acak walau angka sudah diketahui — plafon 51–58%). Setelah rilis: bila emas sudah bergerak ≥ $X di detik 1 atau
detik 2 (dari harga tengah 1 dtk sebelum rilis), seberapa sering arahnya SAMA di setiap detik berikutnya s/d detik 60?
Data: tick Exness (cadangan Dukascopy) semua rilis 2016–2026 di research/pra_xau_semua (cache pra_xau_semua_v2.parquet),
per kelompok berita & SEMUA, LAMA (< Okt 2021) / BARU. Detik dengan harga = harga dasar dihitung TIDAK searah (konservatif).
Aplikasi 4.43 menampilkan persen detik berjalan + "✅ ≥ 70% s/d menit 1" bila kurva terendah ≥ 70% (n ≥ 10).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT_JSON = ROOT / "cloud" / "api" / "live_kurva.json"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_live_kurva.txt"
CACHE = EKS / "live_kurva_gerak.parquet"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
DETIK = range(1, 61)
PEMICU = {"1": (0.3, 0.5, 1.0, 2.0), "2": (0.5, 1.0, 2.0)}


def gerak() -> pd.DataFrame:
    """Satu baris per rilis: grup, t0, g1…g60 = harga tengah t0+s − t0−1 dtk ($)."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .news_detik import prepare
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s["t0"] = pd.to_datetime(s.t0, utc=True)
    s = s[s.t0.dt.year >= 2016].drop_duplicates(["t0", "grup"])
    rows = []
    for r in s.itertuples():
        p = None
        for feed in ("XAU_EXNESS", "XAU"):
            try:
                p = prepare(r.t0, feed)
            except Exception:  # noqa: BLE001
                p = None
            if p is not None:
                break
        if p is None:
            continue
        i0 = p.at(-1)
        if i0 < 0 or p.T[i0] < -60:
            continue
        o = {"t0": r.t0, "grup": r.grup, "feed": feed}
        for d in DETIK:
            j = p.at(d)
            o[f"g{d}"] = float(p.mid[j] - p.mid[i0]) if j >= 0 else np.nan
        rows.append(o)
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE)
    return df


def kurva(x: pd.DataFrame, d: int, amb: float) -> dict | None:
    g = x[f"g{d}"]
    m = g.abs() >= amb
    if m.sum() < 5:
        return None
    a = np.sign(g[m])
    p, pl, pb = {}, {}, {}
    for s in DETIK:
        if s <= d:
            continue
        y = np.sign(x.loc[m, f"g{s}"])
        ok = y.notna()
        p[str(s)] = round(float((y[ok] == a[ok]).mean() * 100))
        for per, q, dst in (("lama", x.t0 < SPLIT, pl), ("baru", x.t0 >= SPLIT, pb)):
            qq = ok & q[m]
            if qq.sum() >= 5:
                dst[str(s)] = round(float((y[qq] == a[qq]).mean() * 100))
    s_min = min(p, key=p.get)
    return {"n": int(m.sum()), "p": p, "min": p[s_min], "min_s": int(s_min),
            "min_lama": min(pl.values()) if pl else None, "min_baru": min(pb.values()) if pb else None,
            "n_lama": int((m & (x.t0 < SPLIT)).sum()), "n_baru": int((m & (x.t0 >= SPLIT)).sum())}


def main() -> None:
    df = gerak()
    L = ["# ⚡ Kurva setiap detik 1–60 setelah rilis (research/live_kurva.py)", __doc__.split("\n\n")[1],
         f"rilis bertick 2016–2026: {len(df)}"]
    hasil = {}
    # PPI bersamaan Retail Sales (riset_ppi3 dgn_retail) vs PPI sendiri — detik 1 PPI sendiri tidak bisa dipercaya
    f = pd.read_parquet(EKS / "riset_ppi3" / "fitur.parquet")
    f["t0"] = pd.to_datetime(f.t0, utc=True)
    khusus = {"PPI+RETAIL": set(f[f.dgn_retail].t0), "PPI sendiri": set(f[~f.dgn_retail].t0)}
    for grp in ["SEMUA"] + sorted(df.grup.unique()) + list(khusus):
        x = df if grp == "SEMUA" else (df[df.t0.isin(khusus[grp])].drop_duplicates("t0") if grp in khusus
                                       else df[df.grup == grp])
        res = {}
        for d, ambs in PEMICU.items():
            for amb in ambs:
                k = kurva(x, int(d), amb)
                if k:
                    res[f"{d}|{amb}"] = k
        if not res:
            continue
        hasil[grp] = res
        L.append(f"\n## {grp} ({len(x)} rilis)")
        for key, k in res.items():
            d, amb = key.split("|")
            ps = k["p"]
            L.append(f"   gerak detik {d} ≥ ${amb} (n {k['n']}): terendah s/d detik 60 {k['min']}% (detik {k['min_s']}; lama "
                     f"{k['min_lama']} / baru {k['min_baru']}) | detik 2 {ps.get('2', '–')} • 3 {ps.get('3')} • 5 {ps.get('5')} • "
                     f"10 {ps.get('10')} • 20 {ps.get('20')} • 30 {ps.get('30')} • 45 {ps.get('45')} • 60 {ps.get('60')}"
                     + ("  ✅ ≥ 70% sepanjang menit 1" if k["min"] >= 70 and k["n"] >= 10 else ""))
    OUT_JSON.write_text(json.dumps({"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "sumber": "research/live_kurva.py",
                                    "grup": hasil}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
