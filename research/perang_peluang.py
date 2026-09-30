"""Studi kejadian "mode perang": setelah minyak melonjak, apa yang terjadi pada emas, minyak, dan pair terkait?
(python -m research.perang_peluang)

Pertanyaan pengguna (30 Sep 2026): saat perang Timur Tengah biasanya XAU turun & minyak naik -> bisakah diambil
sebagai peluang entry (bukan menjeda XAU)?

Aturan (ditetapkan sebelum melihat hasil):
- Pemicu: close harian minyak (Yahoo CL=F / BZ=F) naik >= X% dibanding 10 hari bursa sebelumnya. Episode baru bila
  tidak ada pemicu dalam 20 hari bursa sebelumnya. Diketahui di close hari T -> entry di OPEN hari bursa berikutnya.
- Aset (Yahoo harian): XAU (GC=F), WTI (CL=F), Brent (BZ=F), XAG, USD/CAD, USD/JPY, USD/NOK, S&P 500, BTC.
- Diukur: return dari open entry sampai close h hari (h = 1, 3, 5, 10, 20), periode LAMA (< Okt 2021) dan BARU.
  Pembanding: rata-rata return h hari pada semua hari (tanpa pemicu).
- Trade: arah dipilih dari LAMA saja (tanda rata-rata return 5 hari), SL 2 × ATR20 harian, TP 1R atau 2R, tutup
  paksa setelah 10 hari; SL dicek dulu. Dinilai di LAMA & BARU. Spread/swap belum dihitung.
- Sampel kecil (puluhan episode) -> hanya dianggap peluang bila arah sama di LAMA & BARU, t > 2 di seluruh data,
  dan trade untung di kedua periode.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .run_scan import DATA

ASSETS = ["xau", "wti", "brent", "xag", "usdcad", "usdjpy", "usdnok", "spx", "btc"]
NAMA = {"xau": "XAU/USD", "wti": "WTI", "brent": "Brent", "xag": "XAG/USD", "usdcad": "USD/CAD",
        "usdjpy": "USD/JPY", "usdnok": "USD/NOK", "spx": "S&P 500", "btc": "BTC/USD"}
NEW = pd.Timestamp("2021-10-01", tz="UTC")
H = (1, 3, 5, 10, 20)


def load(name: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"yd_{name}.parquet")
    df.index = df.index.normalize()
    return df[~df.index.duplicated(keep="last")]


def triggers(oil: pd.DataFrame, thr: float, n: int = 10, gap: int = 20) -> pd.DatetimeIndex:
    c = oil.close
    ch = c / c.shift(n) - 1
    hit = np.flatnonzero((ch >= thr).to_numpy() & (c.shift(n) > 0).to_numpy())
    out, last = [], -10 ** 9
    for k in hit:
        if k - last > gap:
            out.append(oil.index[k])
        last = k
    return pd.DatetimeIndex(out)


def forward(df: pd.DataFrame, days: pd.DatetimeIndex, h: int) -> pd.Series:
    """Return % dari open hari bursa pertama SESUDAH hari pemicu sampai close h-1 hari bursa sesudahnya."""
    idx = df.index
    out = {}
    for d in days:
        j = idx.searchsorted(d, side="right")
        if j + h - 1 < len(idx) and (idx[j] - d).days <= 5 and df.open.iloc[j] > 0:   # aset sudah punya data
            out[d] = 100 * (df.close.iloc[j + h - 1] / df.open.iloc[j] - 1)
    return pd.Series(out, dtype=float)


def baseline(df: pd.DataFrame, h: int) -> float:
    r = 100 * (df.close.shift(-(h - 1)) / df.open - 1)
    return float(r[df.open > 0].mean())


def trade(df: pd.DataFrame, days: pd.DatetimeIndex, d: int, tp_r: float, hold: int = 10) -> pd.Series:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).rolling(20).mean().to_numpy()
    out = {}
    for day in days:
        j = df.index.searchsorted(day, side="right")
        if j >= len(c) - 1 or (df.index[j] - day).days > 5 or not atr[j - 1] > 0:
            continue
        e, risk = o[j], 2 * atr[j - 1]
        sl, tp = e - d * risk, e + d * tp_r * risk
        r = None
        for k in range(j, min(j + hold, len(c))):
            if (l[k] <= sl) if d > 0 else (h[k] >= sl):
                r = ((min(sl, o[k]) if d > 0 else max(sl, o[k])) - e) * d / risk if k > j else -1.0
                break
            if (h[k] >= tp) if d > 0 else (l[k] <= tp):
                r = tp_r
                break
        if r is None:
            r = (c[min(j + hold, len(c)) - 1] - e) * d / risk
        out[day] = r
    return pd.Series(out, dtype=float)


def tstat(x: pd.Series) -> float:
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else 0.0


def main():
    print("# Studi kejadian mode perang (research/perang_peluang.py)\n")
    data = {a: load(a) for a in ASSETS}
    for oil_name in ("wti", "brent"):
        for thr in (0.10, 0.15):
            days = triggers(data[oil_name], thr)
            old, new = days[days < NEW], days[days >= NEW]
            print(f"## Pemicu {NAMA[oil_name]} naik >= {thr:.0%} dalam 10 hari: {len(days)} episode "
                  f"(LAMA {len(old)}, BARU {len(new)})")
            print("   episode BARU: " + ", ".join(f"{d:%Y-%m-%d}" for d in new))
            for a in ASSETS:
                df = data[a]
                cells = []
                for h in H:
                    f = forward(df, days, h)
                    fo, fn = f[f.index < NEW], f[f.index >= NEW]
                    cells.append(f"{h}h {fo.mean():+.2f}/{fn.mean():+.2f}% (dasar {baseline(df, h):+.2f}, "
                                 f"t {tstat(f):+.1f})")
                print(f"   {NAMA[a]:8s} LAMA/BARU: " + " | ".join(cells))
            print("   trade (arah dari LAMA, 5 hari), SL 2×ATR, tutup maks 10 hari:")
            for a in ASSETS:
                df = data[a]
                f5 = forward(df, days, 5)
                d = 1 if f5[f5.index < NEW].mean() > 0 else -1
                for tp in (1.0, 2.0):
                    r = trade(df, days, d, tp)
                    ro, rn = r[r.index < NEW], r[r.index >= NEW]
                    flag = "  <- KANDIDAT" if (len(ro) >= 8 and len(rn) >= 3 and ro.mean() > 0 and rn.mean() > 0
                                               and tstat(f5 * d) > 2) else ""
                    print(f"      {NAMA[a]:8s} {'BUY ' if d > 0 else 'SELL'} TP {tp:.0f}R: LAMA n={len(ro)} "
                          f"WR={100 * (ro > 0).mean():.0f}% {ro.mean():+.2f}R | BARU n={len(rn)} "
                          f"WR={100 * (rn > 0).mean() if len(rn) else 0:.0f}% {rn.mean() if len(rn) else 0:+.2f}R{flag}")
            print()


if __name__ == "__main__":
    main()
