"""🥇 Semua berita USD: petunjuk sebelum rilis → peluang EMAS naik per jangka (2 dtk … 1 jam), dibanding dasar.

python -m research.news_emas              → docs/eksternal/hasil_news_emas.txt

Lanjutan research/cpi_emas (permintaan pengguna 11 Okt 2026: "fokus CPI dulu baru news lain"). Untuk tiap jenis berita:
  KEJ    petunjuk kejutan teruji yang dipakai aplikasi (research/pra_xau_semua.kejutan_arah: Kalshi, kejutan lalu, GDPNow,
         ISM berbalik, minyak, Fed daerah …) sudah dikonversi ke arah emas (+1 = petunjuk bagus untuk emas)
  P      kejutan rilis SEBELUMNYA jenis yang sama (≤ 45 hari; klaim ≤ 10 hari) diulang → arah emas (aturan umum, ditetapkan
         sebelum melihat hasil; kejutan inflasi/tenaga kerja cenderung searah bulan ke bulan)
  PLAFON tanda kejutan SEBENARNYA → arah emas (research/news_detik.events "bias") = batas atas bila Act sudah diketahui
Gerak emas: harga tengah t0−1 dtk → t0+h (research/pra_menit cache). Laporan: P(naik | petunjuk naik), P(naik | petunjuk
turun), dasar semua rilis jenis itu, beda + p permutasi 5.000×, LAMA < Okt 2021 / BARU. Lolos = beda > 0 di LAMA & BARU
(n ≥ 8 tiap sisi bila dua periode) dan p < 0,05.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_news_emas.txt"
EKS = ROOT / "data" / "research" / "eksternal"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
H = {"2 dtk": "m2", "10 dtk": "m10", "1 mnt": "m60", "5 mnt": "m300", "15 mnt": "m900", "1 jam": "m3600"}


def pct(a: np.ndarray) -> str:
    return f"{a.mean() * 100:.0f}%" if len(a) else "–"


def uji(up: np.ndarray, c: np.ndarray, t: pd.Series, rng) -> tuple[str, bool]:
    pos, neg = up[c > 0], up[c < 0]
    if not len(pos) or not len(neg):
        return f"naik bila petunjuk NAIK {pct(pos)} (n{len(pos)}) | TURUN {pct(neg)} (n{len(neg)})", False
    beda = pos.mean() - neg.mean()
    sel = c != 0
    u, cc = up[sel], c[sel]
    pv = float(np.mean([u[p > 0].mean() - u[p < 0].mean() >= beda for p in (rng.permutation(cc) for _ in range(5000))]))
    per, ok = [], pv < 0.05
    lama = (t < SPLIT).to_numpy()
    for nama, w in (("LAMA", lama), ("BARU", ~lama)):
        a, b = up[w & (c > 0)], up[w & (c < 0)]
        per.append(f"{nama} {pct(a)}/{pct(b)} (n{len(a)}/{len(b)})")
        if len(a) >= 8 and len(b) >= 8:
            ok &= a.mean() > b.mean()
        elif len(a) + len(b) >= 4:
            ok = False
    return (f"naik bila petunjuk NAIK {pct(pos)} (n{len(pos)}) | bila TURUN {pct(neg)} (n{len(neg)}) | dasar {pct(up)} | "
            f"beda {beda * 100:+.0f} p {pv:.3f} | " + " ".join(per)), ok


def main() -> None:
    from .news_detik import events
    g = pd.read_parquet(EKS / "pra_menit.parquet")
    k = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")[["t0", "KEJ"]]
    ev = events()[["time", "bias"]].rename(columns={"time": "t0"})
    df = g.merge(k, on="t0", how="left").merge(ev, on="t0", how="left")
    df["KEJ"] = df.KEJ.fillna(0.0)
    df["PLAFON"] = np.sign(df.bias.fillna(0.0))
    df = df.sort_values("t0").reset_index(drop=True)
    df["P"] = 0.0
    for grup, x in df.groupby("grup"):
        batas = pd.Timedelta(days=10 if grup == "CLAIMS" else 45)
        prev_t, prev_b = x.t0.shift(1), x.PLAFON.shift(1).fillna(0.0)
        df.loc[x.index, "P"] = np.where((x.t0 - prev_t) <= batas, prev_b, 0.0)
    rng = np.random.default_rng(1)
    L = ["# 🥇 Semua berita USD: petunjuk → peluang emas naik", __doc__.split("\n\n")[1], ""]
    lolos = []
    for grup in sorted(df.grup.unique(), key=lambda x: -(df.grup == x).sum()):
        x = df[df.grup == grup]
        L.append(f"\n## {grup} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m}; petunjuk ada {(x.KEJ != 0).sum()})")
        for hn, h in H.items():
            m = x[h].notna() & (x[h] != 0)
            y = x[m]
            up = (y[h] > 0).to_numpy()
            for col in ("PLAFON", "KEJ", "P"):
                c = y[col].to_numpy()
                if (c != 0).sum() < 8:
                    continue
                s, ok = uji(up, c, y.t0, rng)
                L.append(f"   {hn:6s} {col:6s} {s}{'  ✅' if ok else ''}")
                if ok and col != "PLAFON":
                    lolos.append(f"{grup} {col} [{hn}]")
    L.append("\nPetunjuk lolos (tanpa plafon): " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
