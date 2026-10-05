"""Semua pair USDT Binance (termasuk yang sudah delisting) — python -m research.spot_semua [unduh]

Permintaan pengguna (5 Okt 2026): "cek seluruhnya, supaya WR dan profit tinggi dan bisa deteksi apabila ingin turun jauh".
Data candle harian data.binance.vision (735 pair USDT, daftar dari listing S3; termasuk koin yang sudah dihapus →
tanpa bias penyintas) disimpan di data/research/eksternal/spot_1d/<KOIN>.parquet (open, high, low, close, qv = volume
USDT). Analisis: research/spot_jatuh.py.
"""
from __future__ import annotations

import io
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .eksternal import cache_path

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
SKIP = {"USDT", "USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "USDE", "PYUSD", "RLUSD", "USD1", "BFUSD", "XUSD",
        "USDS", "FRAX", "LUSD", "GUSD", "UST", "USTC", "USDD", "SUSD", "USDJ", "EURC", "EUR", "EURI", "AEUR", "GBP",
        "TRY", "BRL", "AUD", "JPY", "ARS", "MXN", "ZAR", "PLN", "RON", "UAH", "IDRT", "BIDR", "BVND", "PAXG", "XAUT",
        "WBTC", "WBETH", "BETH", "STETH", "WSTETH", "BNSOL", "CBETH", "RETH", "WETH", "PAX", "USDSB", "BKRW", "NGN",
        "RUB", "BCHSV", "BCHABC"}


def _dir():
    d = cache_path("spot_1d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get(url: str, tries: int = 5) -> bytes:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise
            err = exc
        except Exception as exc:  # noqa: BLE001 - koneksi putus: coba lagi
            err = exc
        time.sleep(2 ** i)
    raise err


def _list(prefix: str) -> tuple[list[str], list[str]]:
    """(sub-prefix, file key) di bawah prefix S3 (semua halaman)."""
    pre, keys, marker = [], [], None
    while True:
        q = f"{S3}?delimiter=/&prefix={prefix}" + (f"&marker={marker}" if marker else "")
        x = _get(q).decode()
        p = re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:]
        k = re.findall(r"<Key>([^<]+)</Key>", x)
        pre += p
        keys += k
        if "<IsTruncated>true</IsTruncated>" not in x or not (p or k):
            return pre, keys
        marker = (k or p)[-1]


def symbols() -> list[str]:
    pre, _ = _list("data/spot/monthly/klines/")
    out = []
    for p in pre:
        s = p.rstrip("/").split("/")[-1]
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if not base.isascii() or base in SKIP or re.search(r"(UP|DOWN|BULL|BEAR)$", base) and len(base) > 4:
            continue
        out.append(base)
    return sorted(set(out))


def coin(base: str) -> pd.DataFrame | None:
    f = _dir() / f"{base}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    try:
        _, keys = _list(f"data/spot/monthly/klines/{base}USDT/1d/")
    except Exception as exc:  # noqa: BLE001 - lewati sekarang, ulangi lain kali (tanpa file kosong)
        print(base, "gagal daftar:", str(exc)[:80], flush=True)
        return None

    def one(k):
        try:
            z = zipfile.ZipFile(io.BytesIO(_get(f"https://data.binance.vision/{k}")))
        except Exception:  # noqa: BLE001
            return None
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4, 7])
        raw.columns = ["t", "open", "high", "low", "close", "qv"]
        raw = raw[pd.to_numeric(raw.t, errors="coerce").notna()]
        t = raw.t.astype("int64")
        raw.index = pd.to_datetime(t.where(t < 1e14, t // 1000), unit="ms", utc=True)   # 2025+: mikrodetik
        return raw[["open", "high", "low", "close", "qv"]].astype(float)
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(one, [k for k in keys if k.endswith(".zip")]) if p is not None]
    if not parts:
        pd.DataFrame(columns=["open", "high", "low", "close", "qv"]).to_parquet(f)
        return None
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated()]
    df.index = df.index.floor("D")
    df.to_parquet(f)
    return df


def load_all(min_days: int = 120) -> dict[str, pd.DataFrame]:
    out = {}
    for f in sorted(_dir().glob("*.parquet")):
        d = pd.read_parquet(f)
        if len(d) >= min_days:
            out[f.stem] = d
    return out


def main() -> None:
    if "unduh" in sys.argv:
        syms = symbols()
        print(f"{len(syms)} koin USDT", flush=True)
        with ThreadPoolExecutor(8) as ex:
            for i, (s, d) in enumerate(zip(syms, ex.map(coin, syms))):
                if i % 50 == 0:
                    print(i, s, None if d is None else len(d), flush=True)
        return
    data = load_all()
    print(len(data), "koin dengan >= 120 hari")


if __name__ == "__main__":
    main()
