"""Filter "pasar tenang" pada sinyal 💰 bot (3 Okt 2026) — python -m research.sinyal_tenang

Pertanyaan pengguna: "kalau diterapkan di bot sinyal kita, bisakah naikkan WR dan profit? Terutama WR tinggi."
Sinyal = replay kode cloud ASLI (pengaturan live, TP1 0,7R, spread asli; data/research/eksternal/verifikasi/
cloud_<aset>.csv, satu baris per sinyal yang sudah tutup). Filter dihitung pada waktu sinyal dari informasi sebelum bar
sinyal (research/tenang): berita USD high-impact (60 mnt sebelum / 120 mnt sesudah), crash (gerak ≥ 3 ATR H1 dalam
60 mnt selama 4 jam terakhir), volatilitas rendah (ATR H1 ≤ median 20 hari) / tinggi (≥ 1,5 × median).
WR = sinyal dengan hasil bersih > 0. LAMA < Okt 2021, BARU Okt 2021+.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import resample
from .martingale_ea import SPLIT, load
from .tenang import kalender

ROOT = Path(__file__).resolve().parent.parent
VER = ROOT / "data" / "research" / "eksternal" / "verifikasi"
OUT = ROOT / "docs" / "eksternal" / "hasil_sinyal_tenang.txt"


def komponen(bars: pd.DataFrame, ev: pd.DatetimeIndex) -> pd.DataFrame:
    idx = bars.index
    tn = idx.asi8
    h1 = resample(bars, "1h")
    tr = pd.concat([h1.high - h1.low, (h1.high - h1.close.shift()).abs(), (h1.low - h1.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr_b = atr.shift(1).reindex(idx.floor("h")).ffill().to_numpy()
    med_b = atr.rolling(480).median().shift(1).reindex(idx.floor("h")).ffill().to_numpy()
    hi60 = bars.high.rolling("60min").max().to_numpy()
    lo60 = bars.low.rolling("60min").min().to_numpy()
    crash = ((hi60 - bars.low.to_numpy()) >= 3 * atr_b) | ((bars.high.to_numpy() - lo60) >= 3 * atr_b)
    until = np.maximum.accumulate(np.where(crash, tn + 4 * 3_600_000_000_000, 0))
    e = ev.asi8
    k = np.searchsorted(e, tn)
    nxt = np.where(k < len(e), e[np.minimum(k, len(e) - 1)], np.iinfo(np.int64).max)
    prv = np.where(k > 0, e[np.maximum(k - 1, 0)], np.iinfo(np.int64).min // 2)
    m = 60_000_000_000
    return pd.DataFrame(dict(berita=((nxt - tn) <= 60 * m) | ((tn - prv) <= 120 * m),
                             crash=np.r_[False, until[:-1] > tn[1:]],
                             vol_rel=atr_b / med_b), index=idx)


def tandai(sig: pd.DataFrame, kom: pd.DataFrame) -> pd.DataFrame:
    t = pd.to_datetime(sig.t_signal, utc=True)
    j = np.clip(kom.index.searchsorted(t, side="right") - 1, 0, len(kom) - 1)
    s = sig.assign(t=t, berita=kom.berita.to_numpy()[j], crash=kom.crash.to_numpy()[j], vol=kom.vol_rel.to_numpy()[j])
    return s[np.isfinite(s.vol)]


def baris(s: pd.DataFrame, lab: str, ref: pd.DataFrame) -> str:
    out = []
    for nm, sel, sel_ref in (("LAMA", s.t < SPLIT, ref.t < SPLIT), ("BARU", s.t >= SPLIT, ref.t >= SPLIT)):
        x = s[sel].r.to_numpy()
        n0 = int(sel_ref.sum())
        if len(x) < 5:
            out.append(f"{nm} n {len(x)}")
            continue
        out.append(f"{nm} n {len(x):4d} ({100 * len(x) / n0:3.0f}%) WR {100 * (x > 0).mean():3.0f}% {x.mean():+.3f}R total {x.sum():+6.0f}R")
    return f"  {lab:34s} " + " | ".join(out)


def main() -> None:
    ev = kalender()
    xau = load()
    btc = pd.read_parquet(ROOT / "data" / "research" / "h1" / "BTC_USD_full.parquet")
    if btc.index.tz is None:
        btc.index = btc.index.tz_localize("UTC")
    btc = btc[["open", "high", "low", "close"]].astype(float).sort_index()
    btc.index = btc.index.as_unit("ns")
    out = ["Sinyal 💰 replay kode cloud (TP1 0,7R, spread asli). Kolom: n (% dari semua), WR, R/sinyal, total R.", ""]
    for aset, bars, files in (("XAU", xau, ("cloud_XAU.csv",)), ("BTC", btc, ("cloud_BTC.csv",)), ("ETH", None, ("cloud_ETH.csv",))):
        if bars is None:
            continue
        kom = komponen(bars, ev)
        for f in files:
            raw = pd.read_csv(VER / f)
            for bagian, sub in (("dasar", raw[~raw.lapis]), ("lapisan", raw[raw.lapis])):
                if len(sub) < 50:
                    continue
                s = tandai(sub, kom)
                out.append(f"{aset} {bagian} ({f})")
                tests = [
                    ("semua (sekarang)", s),
                    ("lewati berita", s[~s.berita]),
                    ("lewati crash", s[~s.crash]),
                    ("hanya volatilitas rendah (≤ median)", s[s.vol <= 1.0]),
                    ("TENANG penuh (3 syarat)", s[~s.berita & ~s.crash & (s.vol <= 1.0)]),
                    ("kebalikan: hanya volatil (> median)", s[s.vol > 1.0]),
                    ("hanya sangat volatil (≥ 1,5× median)", s[s.vol >= 1.5]),
                    ("hanya saat/sesudah berita", s[s.berita]),
                ]
                out += [baris(x, lab, s) for lab, x in tests]
                s = s.assign(per=np.where(s.t < SPLIT, "LAMA", "BARU"),
                             vb=pd.cut(s.vol, [0, 0.75, 1.0, 1.25, 1.5, 2.0, 99],
                                       labels=["<0.75", "0.75-1", "1-1.25", "1.25-1.5", "1.5-2", ">2"]))
                g = s.groupby(["vb", "per"], observed=True).agg(n=("r", "size"), WR=("r", lambda x: (x > 0).mean()),
                                                                R=("r", "mean")).unstack("per")
                out.append("  per tingkat volatilitas (ATR H1 / median 20 hari):")
                out += ["    " + ln for ln in g.round(2).to_string().splitlines()]
                hv = s[s.vol >= 1.5]
                out.append("  volatilitas ≥ 1,5×, WR per tahun: " + " ".join(
                    f"{y}:{100 * (x.r > 0).mean():.0f}%(n{len(x)})" for y, x in hv.groupby(hv.t.dt.year)))
                out.append("")
                print("\n".join(out[-22:]), flush=True)
    OUT.write_text("\n".join(out) + "\n")
    print("->", OUT)


if __name__ == "__main__":
    main()
