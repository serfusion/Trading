"""Unduh candle BID & ASK Dukascopy (datafeed.dukascopy.com) -> parquet UTC di data/research/eksternal/dukascopy.

python -m research.dukascopy h1 2012-01 2026-09          # file bulanan H1 (2 x ~180 unduhan)
python -m research.dukascopy m1 2025-01-01 2026-09-25    # file harian M1 (2 x jumlah hari)

Format .bi5 = LZMA, baris 24 byte big-endian: detik sejak awal file, open, close, low, high (int, x 0,001 untuk
XAUUSD), volume (float). Bulan di URL dimulai dari 00. Candle datar tanpa volume (akhir pekan/libur) dibuang.
Server membatasi laju -> jeda antar-unduhan + ulang dengan backoff.
"""
from __future__ import annotations

import lzma
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import cache_path

URL = "https://datafeed.dukascopy.com/datafeed"
POINT = {"XAUUSD": 1e-3, "BTCUSD": 1e-1}


def _get(url: str, tries: int = 10) -> bytes:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b""
            err = e
        except Exception as e:  # noqa: BLE001 - koneksi diputus server (rate limit)
            err = e
        time.sleep(min(2 ** k, 30))
    raise RuntimeError(f"gagal {url}: {err}")


def _decode(raw: bytes, start: pd.Timestamp, point: float) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    b = lzma.decompress(raw)
    a = np.frombuffer(b, dtype=">i4").reshape(-1, 6)
    vol = np.frombuffer(b, dtype=">f4").reshape(-1, 6)[:, 5]
    idx = start + pd.to_timedelta(a[:, 0].astype(np.int64), unit="s")
    df = pd.DataFrame({"open": a[:, 1] * point, "high": a[:, 4] * point, "low": a[:, 3] * point,
                       "close": a[:, 2] * point, "volume": vol.astype(float)}, index=idx)
    return df[df.volume > 0]


def fetch(sym: str, kind: str, start: str, end: str, pause: float = 0.3) -> dict[str, pd.DataFrame]:
    """Setiap file .bi5 disimpan apa adanya (bisa dilanjutkan bila terputus), lalu digabung ke parquet."""
    point = POINT[sym]
    raw_dir = cache_path(f"dukascopy/raw_{sym}_{kind}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    steps = pd.period_range(start, end, freq="M") if kind == "h1" else pd.date_range(start, end, freq="D")
    name = "hour_1" if kind == "h1" else "min_1"
    out = {}
    for side in ("BID", "ASK"):
        frames = []
        for k, p in enumerate(steps):
            t0 = (p.to_timestamp() if kind == "h1" else p).tz_localize("UTC")
            f = raw_dir / f"{side}_{t0:%Y%m%d}.bi5"
            if not f.exists():
                url = (f"{URL}/{sym}/{t0.year}/{t0.month - 1:02d}/" +
                       (f"{side}_candles_{name}.bi5" if kind == "h1" else f"{t0.day:02d}/{side}_candles_{name}.bi5"))
                f.write_bytes(_get(url))
                time.sleep(pause)
                if k % 20 == 0:
                    print(f"{sym} {kind} {side}: {t0:%Y-%m-%d}", flush=True)
            frames.append(_decode(f.read_bytes(), t0, point))
        df = pd.concat([x for x in frames if len(x)]).sort_index()
        df = df[~df.index.duplicated()]
        df.to_parquet(cache_path(f"dukascopy/{sym}_{kind}_{side}.parquet"))
        out[side] = df
    return out


def load(sym: str, kind: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(BID, ASK) dari semua file mentah yang sudah terunduh (boleh sebagian; ASK bisa kosong di tahun tertentu)."""
    raw_dir = cache_path(f"dukascopy/raw_{sym}_{kind}")
    out = []
    for side in ("BID", "ASK"):
        files = sorted(raw_dir.glob(f"{side}_*.bi5"))
        if not files:
            raise FileNotFoundError(raw_dir)
        frames = [_decode(f.read_bytes(), pd.Timestamp(f.stem.split("_")[1], tz="UTC"), POINT[sym]) for f in files]
        df = pd.concat([x for x in frames if len(x)]).sort_index()
        out.append(df[~df.index.duplicated()])
    return out[0], out[1]


if __name__ == "__main__":
    kind, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
    sym = sys.argv[4] if len(sys.argv) > 4 else "XAUUSD"
    res = fetch(sym, kind, a, b)
    for side, df in res.items():
        print(f"{sym} {kind} {side}: {len(df)} candle {df.index[0]} .. {df.index[-1]}")
