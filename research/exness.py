"""Tick asli Exness (ticks.ex2archive.com, broker pengguna) -> jendela berita & tabel spread per jam.

python -m research.exness XAUUSDc 2015-01 2026-09     # akun Cent pengguna (XAU sejak 2015)
python -m research.exness BTCUSDm 2017-01 2026-09     # BTC akun Standard (BTCUSDc baru ada sejak 2025)

Arsip Exness: satu zip per bulan (`ticks/<SIMBOL>/<th>/<bln>/Exness_<SIMBOL>_<th>_<bln>.zip`, CSV
Exness,Symbol,Timestamp(UTC ms),Bid,Ask). Satu bulan XAU ±22 MB zip / ±150 MB CSV, jadi TIDAK disimpan utuh; yang
disimpan (data/research/eksternal/exness/<SIMBOL>/):
- `<th>-<bln>.parquet`: tick (bid & spread sebagai int x1000 XAU / x100 BTC, zstd) di jendela 2 menit sebelum
  s.d. 16 menit sesudah setiap rilis berita bintang 3
  (research/news_detik.events(), semua tier) -> dipakai uji detik pertama dengan spread & slippage asli broker;
- `spread_<th>-<bln>.csv`: spread per jam UTC (median, p90, jumlah tick) seluruh bulan -> pengganti asumsi spread
  di riset lain (akun Cent pengguna).
Zip dihapus setelah diproses. Bisa dilanjutkan (bulan yang sudah ada dilewati).
"""
from __future__ import annotations

import io
import sys
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from .eksternal import cache_path

URL = "https://ticks.ex2archive.com/ticks"
SCALE = {"XAU": 1000, "BTC": 100}          # harga disimpan sebagai int (x1000 XAU, x100 BTC), parquet zstd
BEFORE, AFTER = pd.Timedelta(minutes=2), pd.Timedelta(minutes=16)


def out_dir(sym: str):
    d = cache_path(f"exness/{sym}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get(url: str, tries: int = 6) -> bytes | None:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                        timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:  # noqa: BLE001 - transfer terpotong -> ulang
            pass
        time.sleep(2 ** k)
    raise RuntimeError(f"gagal {url}")


def month(sym: str, p: pd.Period, event_times: pd.DatetimeIndex) -> str:
    d = out_dir(sym)
    f_win, f_sp = d / f"{p.strftime('%Y-%m')}.parquet", d / f"spread_{p.strftime('%Y-%m')}.csv"
    if f_win.exists() and f_sp.exists():
        return "ada"
    raw = _get(f"{URL}/{sym}/{p.year}/{p.month:02d}/Exness_{sym}_{p.year}_{p.month:02d}.zip")
    if raw is None:
        return "tidak ada"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), usecols=["Timestamp", "Bid", "Ask"])
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("Timestamp"), utc=True, format="ISO8601")).as_unit("ns")
    df.columns = ["bid", "ask"]
    df = df[~df.index.duplicated()].sort_index()
    sp = (df.ask - df.bid).groupby(df.index.floor("h"))
    pd.DataFrame({"median": sp.median(), "p90": sp.quantile(0.9), "n": sp.size()}).round(4).to_csv(f_sp)
    t = df.index.asi8
    keep = np.zeros(len(df), bool)
    for e in event_times[(event_times >= p.start_time.tz_localize("UTC") - AFTER) &
                         (event_times <= p.end_time.tz_localize("UTC") + BEFORE)]:
        a, b = np.searchsorted(t, [(e - BEFORE).value, (e + AFTER).value])
        keep[a:b] = True
    k = SCALE[sym[:3]]
    w = df[keep]
    pd.DataFrame({"bid": np.round(w.bid * k).astype("int64"), "spread": np.round((w.ask - w.bid) * k).astype("int32")},
                 index=w.index).to_parquet(f_win, compression="zstd")
    return f"{keep.sum()} tick di jendela berita, {len(df)} tick sebulan"


def run(sym: str, a: str, b: str) -> None:
    from .news_detik import events
    ev = pd.DatetimeIndex(events().time)
    for p in pd.period_range(a, b, freq="M"):
        print(f"{sym} {p}: {month(sym, p, ev)}", flush=True)


def ticks_around(sym: str, t0: pd.Timestamp) -> pd.DataFrame | None:
    """Tick Exness 2 menit sebelum s.d. 16 menit sesudah rilis (dari file jendela bulanannya)."""
    frames = []
    for p in {t0.to_period("M"), (t0 - BEFORE).to_period("M"), (t0 + AFTER).to_period("M")}:
        f = out_dir(sym) / f"{p.strftime('%Y-%m')}.parquet"
        if f.exists():
            frames.append(pd.read_parquet(f))
    if not frames:
        return None
    df = pd.concat(frames).sort_index()
    df = df[(df.index >= t0 - BEFORE) & (df.index <= t0 + AFTER)]
    if not len(df):
        return None
    k = SCALE[sym[:3]]
    return pd.DataFrame({"bid": df.bid / k, "ask": (df.bid + df.spread) / k}, index=df.index)


def spread_table(sym: str) -> pd.DataFrame:
    fs = sorted(out_dir(sym).glob("spread_*.csv"))
    return pd.concat([pd.read_csv(f, index_col=0, parse_dates=True) for f in fs]) if fs else pd.DataFrame()


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
