"""🔁 "CPI & PPI langsung turun, FOMC langsung naik 1 detik setelah rilis" — apakah ada POLA TETAP per jenis berita?

python -m research.pola_jenis             → docs/eksternal/hasil_pola_jenis.txt

Permintaan pengguna 11 Okt 2026: "CPI, PPI langsung turun 1 detik setelah news release, FOMC langsung naik, ISM kemarin
langsung turun — SAYA MAU SEPERTI ITU SISTEMNYA". Diuji tutup kertas (setiap rilis hanya melihat rilis SEBELUMNYA), arah
harga tengah XAU t0−1 dtk → t0+1 dtk, dan detik 2/3/5/10. Aturan (ditetapkan sebelum melihat hasil):
  MAYOR  arah mayoritas jenis berita itu di SEMUA rilis sebelumnya (mulai ≥ 10 rilis)
  TAHUN  arah mayoritas rilis jenis itu di tahun berjalan (≥ 2 rilis sebelumnya di tahun itu)
  LALU1  arah rilis terakhir jenis itu       LALU3  mayoritas 3 rilis terakhir
  BALIK1 kebalikan rilis terakhir
Pembanding: selalu NAIK. Validitas: permutasi keluarga (hasil emas diacak antar rilis dalam jenis yang sama, 2.000×,
dibandingkan aturan TERBAIK acakan). LAMA < Okt 2021, BARU ≥ Okt 2021.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pola_jenis.txt"
EKS = ROOT / "data" / "research" / "eksternal"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
GRUP = ["CPI", "PPI", "FOMC", "ISM", "NFP", "RETAIL", "PCE", "GDP", "JOLTS", "ADP", "CLAIMS", "KONSUMEN"]
H = (1, 2, 3, 5, 10)


def data() -> pd.DataFrame:
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    v = v[v.grup.isin(GRUP)].copy()
    for h in H:
        v[f"g{h}"] = np.sign(v[f"y{h}_XAU_EXNESS"].fillna(v[f"y{h}_XAU"]).fillna(0))
    ny = v.t0.dt.tz_convert("America/New_York")
    v["d"], v["menit"] = ny.dt.normalize(), ny.dt.hour * 60 + ny.dt.minute
    modus = v.groupby("grup").menit.agg(lambda s: s.mode().iloc[0])
    v["_j"] = (v.menit - v.grup.map(modus)).abs()
    v = v.sort_values("_j").drop_duplicates(["grup", "d"]).sort_values("t0").reset_index(drop=True)
    v["th"] = v.t0.dt.year
    return v


def aturan(x: pd.DataFrame, h: int) -> dict[str, np.ndarray]:
    """Tebakan (+1 naik / −1 turun / 0) per rilis, hanya dari rilis sebelumnya jenis yang sama."""
    g = x[f"g{h}"].to_numpy()
    th = x.th.to_numpy()
    n = len(x)
    out = {k: np.zeros(n) for k in ("MAYOR", "TAHUN", "LALU1", "LALU3", "BALIK1")}
    for i in range(n):
        lalu = g[:i][g[:i] != 0]
        if len(lalu) >= 10:
            out["MAYOR"][i] = np.sign(lalu.sum())
        ini = g[:i][(th[:i] == th[i]) & (g[:i] != 0)]
        if len(ini) >= 2:
            out["TAHUN"][i] = np.sign(ini.sum())
        if len(lalu) >= 1:
            out["LALU1"][i], out["BALIK1"][i] = lalu[-1], -lalu[-1]
        if len(lalu) >= 3:
            out["LALU3"][i] = np.sign(lalu[-3:].sum())
    out["NAIK"] = np.ones(n)
    return out


def skor(tb: np.ndarray, g: np.ndarray, m: np.ndarray) -> tuple[int, int]:
    ok = m & (tb != 0) & (g != 0)
    return int((tb[ok] == g[ok]).sum()), int(ok.sum())


def pct(k: int, n: int) -> str:
    return f"{k / n * 100:5.1f}% ({k}/{n})" if n else "    –"


def main() -> None:
    df = data()
    L = ["# 🔁 Pola tetap per jenis berita? (tutup kertas, arah XAU detik 1 & 2–10)", __doc__.split("\n\n")[1], ""]
    rng = np.random.default_rng(3)
    lolos = []
    for gr in GRUP:
        x = df[df.grup == gr].reset_index(drop=True)
        if len(x) < 20:
            continue
        lama, baru = (x.t0 < SPLIT).to_numpy(), (x.t0 >= SPLIT).to_numpy()
        th26 = (x.th == 2026).to_numpy()
        L.append(f"\n## {gr} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})")
        naik = {h: (x[f"g{h}"] > 0).sum() / max((x[f"g{h}"] != 0).sum(), 1) * 100 for h in H}
        L.append("   emas naik (semua rilis): " + " • ".join(f"{h} dtk {naik[h]:.0f}%" for h in H))
        for nama_h, hs in (("1 dtk", (1,)), ("2–10 dtk", (2, 3, 5, 10))):
            per = {h: aturan(x, h) for h in hs}
            for k in ("NAIK", "MAYOR", "TAHUN", "LALU1", "LALU3", "BALIK1"):
                tot = [skor(per[h][k], x[f"g{h}"].to_numpy(), m) for m in
                       (np.ones(len(x), bool), lama, baru, th26) for h in hs]
                agg = [tuple(map(sum, zip(*tot[j * len(hs):(j + 1) * len(hs)]))) for j in range(4)]
                L.append(f"   {nama_h:8s} {k:6s} semua {pct(*agg[0])} | LAMA {pct(*agg[1])} | BARU {pct(*agg[2])} | "
                         f"2026 {pct(*agg[3])}")
            # permutasi keluarga 5 aturan (tanpa NAIK)
            G = np.stack([x[f"g{h}"].to_numpy() for h in hs], 1)
            obs = {}
            for k in ("MAYOR", "TAHUN", "LALU1", "LALU3", "BALIK1"):
                kk = [skor(per[h][k], x[f"g{h}"].to_numpy(), np.ones(len(x), bool)) for h in hs]
                k_, n_ = map(sum, zip(*kk))
                obs[k] = k_ / n_ if n_ else 0
            maks = []
            for _ in range(2000):
                xp = x.copy()
                idx = rng.permutation(len(x))
                for j, h in enumerate(hs):
                    xp[f"g{h}"] = G[idx, j]
                best = 0
                for k in obs:
                    kk = [skor(aturan(xp, h)[k], xp[f"g{h}"].to_numpy(), np.ones(len(x), bool)) for h in hs] \
                        if len(hs) == 1 else None
                    if kk is None:
                        break
                    k_, n_ = map(sum, zip(*kk))
                    best = max(best, k_ / n_ if n_ else 0)
                if len(hs) > 1:
                    break
                maks.append(best)
            if maks:
                maks = np.array(maks)
                k_best = max(obs, key=obs.get)
                p = float((maks >= obs[k_best]).mean())
                L.append(f"   {nama_h:8s} terbaik {k_best} {obs[k_best] * 100:.1f}% → permutasi keluarga p {p:.3f}"
                         f"{'  ✅' if p < 0.05 and obs[k_best] >= 0.6 else ''}")
                if p < 0.05 and obs[k_best] >= 0.6:
                    lolos.append(f"{gr} {k_best} 1 dtk")
    L.append("\nLolos (≥ 60% & p < 0,05, detik 1): " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
