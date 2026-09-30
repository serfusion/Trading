"""Minyak WTI per tahun: Turtle D1 (kandidat terbaik di docs/UJI_DUNIA.md) di tiga sumber data (python -m research.wti).

Sumber (saling cek, karena tidak ada satu data WTI yang sempurna):
- Yahoo CL=F harian 2000-08 .. 2026-09 (futures bulan terdekat; ada lompatan saat ganti kontrak; April 2020 negatif).
- FRED DCOILWTICO harian 1986 .. 2026 (harga spot, HANYA close -> high = low = close).
- OANDA WTICO_USD H1 2008 .. 2020 (CFD spot, sama dengan data world_lab) -> dibuat harian.
Aturan Turtle (ditetapkan sebelum melihat hasil, sama dengan world_lab): close menembus high/low 55 hari sebelumnya ->
entry di open hari berikutnya (+spread $0,05); SL 2 × ATR20 harian; varian (a) TP 1R, (b) tanpa TP, keluar saat
close menembus low/high 27 hari. SL dicek dulu (bila SL & TP di hari yang sama dianggap SL). Satu posisi.
Periode: LAMA < 2021-10, BARU = 5 tahun terakhir. Swap belum dihitung (cek spesifikasi USOIL/XTIUSD di MT5).
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import cache_path
from .run_scan import DATA

NEW = pd.Timestamp("2021-10-01", tz="UTC")
SPREAD = 0.05


def yahoo() -> pd.DataFrame:
    """CL=F harian dari query1.finance.yahoo.com (disimpan di data/research/clf_d1.parquet)."""
    path = DATA / "clf_d1.parquet"
    if not path.exists():
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1d&period1=946684800"
               f"&period2={int(pd.Timestamp.now().timestamp())}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())["chart"]["result"][0]
        q = d["indicators"]["quote"][0]
        df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                          index=pd.to_datetime(d["timestamp"], unit="s", utc=True)).dropna()
        df.to_parquet(path)
    return pd.read_parquet(path)


def fred_spot() -> pd.DataFrame:
    path = cache_path("fred_DCOILWTICO_full.json")
    if not path.exists():
        url = ("https://api.stlouisfed.org/fred/series/observations?series_id=DCOILWTICO&observation_start=1986-01-01"
               f"&api_key={os.environ['FRED_API_KEY']}&file_type=json")
        with urllib.request.urlopen(url, timeout=60) as r:
            path.write_bytes(r.read())
    obs = pd.DataFrame(json.loads(path.read_text())["observations"])
    obs = obs[obs.value != "."]
    c = pd.Series(obs.value.astype(float).to_numpy(), index=pd.DatetimeIndex(obs.date).tz_localize("UTC"))
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c})


def oanda() -> pd.DataFrame:
    h1 = pd.read_parquet(DATA / "h1" / "WTICO_USD.parquet")
    d = h1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return d if d.index.tz is not None else d.tz_localize("UTC")


def turtle(df: pd.DataFrame, n: int = 55, tp_r: float | None = 1.0, sl_atr: float = 2.0) -> pd.DataFrame:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = df.index
    prev_c = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - prev_c), abs(l - prev_c)))
    atr = pd.Series(tr).rolling(20).mean().to_numpy()
    hi = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    xhi = pd.Series(h).rolling(n // 2).max().shift(1).to_numpy()
    xlo = pd.Series(l).rolling(n // 2).min().shift(1).to_numpy()
    out, i, N = [], 0, len(c)
    while i < N - 2:
        d = 1 if c[i] > hi[i] else (-1 if c[i] < lo[i] else 0)
        if d == 0 or not atr[i] > 0:
            i += 1
            continue
        j = i + 1
        entry = o[j] + d * SPREAD / 2
        risk = sl_atr * atr[i]
        sl = entry - d * risk
        tp = entry + d * tp_r * risk if tp_r else None
        k, px = j, None
        while k < N - 1:
            if (l[k] <= sl) if d > 0 else (h[k] >= sl):
                px = (min(sl, o[k]) if d > 0 else max(sl, o[k])) if k > j else sl
                break
            if tp is not None and ((h[k] >= tp) if d > 0 else (l[k] <= tp)):
                px = (max(tp, o[k]) if d > 0 else min(tp, o[k])) if k > j else tp
                break
            if (c[k] < xlo[k]) if d > 0 else (c[k] > xhi[k]):
                px = o[k + 1]
                k += 1
                break
            k += 1
        if px is None:
            break
        r = ((px - d * SPREAD / 2) - entry) * d / risk
        out.append((t[j], t[k], d, r, (t[k] - t[j]).days))
        i = k + 1
    return pd.DataFrame(out, columns=["t", "t_out", "dir", "R", "hari"])


def line(r: pd.Series) -> str:
    return f"n={len(r):3d} WR={100 * (r > 0).mean():4.1f}% rata={r.mean():+.3f}R total={r.sum():+6.1f}R" if len(r) \
        else "n=  0"


def report(tag: str, tr: pd.DataFrame):
    per = np.where(tr.t >= NEW, "BARU", "LAMA")
    print(f"{tag}: semua {line(tr.R)} | LAMA {line(tr.R[per == 'LAMA'])} | BARU {line(tr.R[per == 'BARU'])} | "
          f"pegang median {tr.hari.median():.0f} hari")
    y = tr.groupby(tr.t.dt.year).R.agg(["count", "sum"])
    print("   per tahun: " + ", ".join(f"{k} {int(v['count'])}×{v['sum']:+.1f}R" for k, v in y.iterrows()))
    print(f"   tahun untung {(y['sum'] > 0).sum()}/{len(y)}; 5 tahun terakhir {(y.loc[2021:, 'sum'] > 0).sum()}/"
          f"{len(y.loc[2021:])}")


def main():
    print("# WTI Turtle D1 per tahun (research/wti.py)\n")
    src = {"Yahoo CL=F 2000–2026": yahoo(), "FRED spot (close saja) 1986–2026": fred_spot(),
           "OANDA WTICO 2008–2020": oanda()}
    for name, df in src.items():
        for tag, kw in (("TP 1R", dict(tp_r=1.0)), ("tanpa TP (keluar 27 hari)", dict(tp_r=None))):
            report(f"## {name} — Turtle 55, {tag}", turtle(df, **kw))
        print()
    tr = turtle(src["Yahoo CL=F 2000–2026"], tp_r=1.0)
    print("2026 (Yahoo, TP 1R): " + ", ".join(
        f"{r.t:%d %b} {'BUY' if r.dir > 0 else 'SELL'} {r.R:+.2f}R" for r in tr[tr.t.dt.year == 2026].itertuples()))


if __name__ == "__main__":
    main()
