"""Data harian SEMUA pair USDT Binance spot (termasuk yang sudah delisting) — python -m research.spot_semua unduh

Permintaan pengguna (5 Okt 2026): uji semua koin, bukan beberapa saja. Sumber data.binance.vision (S3, daftar file per
simbol -> hanya bulan yang ada). Candle 1d + volume quote (USDT). Disimpan data/research/eksternal/spot_1d/<SYM>.parquet.
Dikecualikan: stablecoin/fiat (USDC, FDUSD, TUSD, BUSD, DAI, EUR, ...) dan token leverage (UP/DOWN/BULL/BEAR).
"""
from __future__ import annotations

import io
import re
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "spot_1d"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
STABLE = {"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "PAX", "USDS", "UST", "SUSD", "EUR", "GBP", "AUD", "TRY",
          "BRL", "AEUR", "EURI", "USD1", "BKRW", "BIDR", "IDRT", "RUB", "UAH", "NGN", "ZAR", "XUSD", "USDE", "PAXG",
          "WBTC", "WBETH", "BFUSD", "RLUSD"}


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _list(prefix: str) -> tuple[list[str], list[str]]:
    """(sub-prefix, kunci file) di bawah prefix, semua halaman."""
    pre, keys, marker = [], [], ""
    while True:
        x = _get(f"{S3}?delimiter=/&prefix={prefix}&marker={marker}").decode()
        p = re.findall(r"<Prefix>([^<]*)</Prefix>", x)[1:]
        k = re.findall(r"<Key>([^<]*)</Key>", x)
        pre += p
        keys += k
        if "<IsTruncated>true" not in x:
            return pre, keys
        marker = (p or k)[-1]


def symbols() -> list[str]:
    pre, _ = _list("data/spot/monthly/klines/")
    out = []
    for p in pre:
        s = p.rstrip("/").split("/")[-1]
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLE or re.search(r"(UP|DOWN|BULL|BEAR)$", base) and len(base) > 4:
            continue
        out.append(s)
    return out


def one(sym: str) -> str:
    f = DIR / f"{sym[:-4]}.parquet"
    if f.exists():
        return f"{sym}: ada"
    try:
        _, keys = _list(f"data/spot/monthly/klines/{sym}/1d/")
        parts = []
        for k in keys:
            if not k.endswith(".zip"):
                continue
            z = zipfile.ZipFile(io.BytesIO(_get(DL + k)))
            raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4, 7])
            raw.columns = ["t", "open", "high", "low", "close", "qvol"]
            raw = raw[pd.to_numeric(raw.t, errors="coerce").notna()]
            t = raw.t.astype("int64")
            raw.index = pd.to_datetime(t, unit="us" if t.iloc[0] > 1e14 else "ms", utc=True)
            parts.append(raw[["open", "high", "low", "close", "qvol"]].astype(float))
        if not parts:
            return f"{sym}: kosong"
        df = pd.concat(parts).sort_index()
        df = df[~df.index.duplicated()]
        df.to_parquet(f)
        return f"{sym}: {len(df)} hari {df.index[0]:%Y-%m}..{df.index[-1]:%Y-%m}"
    except Exception as exc:  # noqa: BLE001
        return f"{sym}: gagal {exc}"


def load_all(min_days: int = 260) -> dict[str, pd.DataFrame]:
    out = {}
    for f in sorted(DIR.glob("*.parquet")):
        d = pd.read_parquet(f)
        if len(d) >= min_days:
            out[f.stem] = d
    return out


if __name__ == "__main__":
    if "unduh" in sys.argv:
        DIR.mkdir(parents=True, exist_ok=True)
        syms = symbols()
        print(len(syms), "simbol", flush=True)
        with ThreadPoolExecutor(12) as ex:
            for msg in ex.map(one, syms):
                print(msg, flush=True)
        print("SELESAI", flush=True)
