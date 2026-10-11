"""📈 Target baru: ARAH LONJAKAN TERBESAR di MENIT PERTAMA setelah rilis (dihitung per detik dari tick).

python -m research.lonjakan                → data/research/eksternal/lonjakan60.parquet

Permintaan pengguna 11 Okt 2026: "hitungannya per detik, tapi hasil akhirnya beberapa detik yang diambil tinggi candle per
menit — biasanya terjadi di menit pertama, entah itu tinggi naik atau tinggi turun". Per rilis: p0 = harga tengah 1 dtk
sebelum rilis; dalam 0 < t ≤ 60 dtk: naik = maks(mid) − p0, turun = p0 − min(mid). ARAH = yang lebih jauh (naik → +1,
turun → −1); lonjakan < $0,05 = 0 (diam). Dicatat juga detik terjadinya puncak, besar lonjakan, dan arah tutup menit
pertama (mid t0+60 − p0). Feed: tick Exness (utama) dan Dukascopy (pembanding).
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
CACHE = EKS / "lonjakan60.parquet"
FEEDS = {"ex": "XAU_EXNESS", "du": "XAU"}
DETIK = 60
MIN = 0.05


def rilis() -> pd.DataFrame:
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")[["t0", "grup"]].copy()
    ny = v.t0.dt.tz_convert("America/New_York")
    v["d"], v["menit"] = ny.dt.normalize(), ny.dt.hour * 60 + ny.dt.minute
    modus = v.groupby("grup").menit.agg(lambda s: s.mode().iloc[0])
    v["_j"] = (v.menit - v.grup.map(modus)).abs()
    v = v.sort_values("_j").drop_duplicates(["grup", "d"]).sort_values("t0")
    return v[["t0", "grup"]].reset_index(drop=True)


def satu(t0: pd.Timestamp) -> dict:
    from .news_detik import prepare
    o = {"t0": t0}
    for k, feed in FEEDS.items():
        try:
            p = prepare(pd.Timestamp(t0), feed)
        except Exception:  # noqa: BLE001 - data tick tidak ada
            p = None
        if p is None:
            continue
        i0 = p.at(-1)
        if i0 < 0:
            continue
        p0 = p.mid[i0]
        w = (p.T > 0) & (p.T <= DETIK)
        if not w.any():
            continue
        m, t = p.mid[w], p.T[w]
        up, dn = float(m.max() - p0), float(p0 - m.min())
        besar = max(up, dn)
        o[f"{k}_naik"], o[f"{k}_turun"] = up, dn
        o[f"{k}_arah"] = 0.0 if besar < MIN else (1.0 if up > dn else -1.0)
        o[f"{k}_detik"] = float(t[int(m.argmax())] if up > dn else t[int(m.argmin())])
        o[f"{k}_besar"] = besar
        o[f"{k}_tutup60"] = float(np.sign(p.mid[p.at(DETIK)] - p0))
    return o


def tabel(segar: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not segar:
        return pd.read_parquet(CACHE)
    r = rilis()
    with ProcessPoolExecutor(6) as ex:
        rows = list(ex.map(satu, list(r.t0), chunksize=8))
    df = r.merge(pd.DataFrame(rows), on="t0", how="left")
    df["arah"] = df.ex_arah.fillna(df.du_arah)             # Exness utama, cadangan Dukascopy
    df["detik"] = df.ex_detik.fillna(df.du_detik)
    df["besar"] = df.ex_besar.fillna(df.du_besar)
    df.to_parquet(CACHE)
    return df


def main() -> None:
    df = tabel(segar=True)
    print(len(df), "rilis;", df.arah.notna().sum(), "punya tick")
    for g, x in df.groupby("grup"):
        a = x.arah.dropna()
        print(f"{g:9s} n {len(a):3d} lonjakan naik {(a > 0).mean() * 100:4.0f}% | puncak median detik "
              f"{x.detik.median():4.0f} | besar median ${x.besar.median():.2f} | arah Exness=Dukascopy "
              f"{(x.ex_arah == x.du_arah)[x.ex_arah.notna() & x.du_arah.notna()].mean() * 100:.0f}%")


if __name__ == "__main__":
    main()
