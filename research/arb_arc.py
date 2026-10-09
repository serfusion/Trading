"""Bot screenshot "wetharb"/"circarb" di Arc: bukti, untung-rugi grup, jalur keluar (redeem), pihak lawan, jendela diskon.

    python -m research.arb_arc <tahap>

Lanjutan research/arb_cari.py (tahap pabrik/token/kandidat/swap_kandidat/cari/transfer_alamat/perdagangan_grup/fifo/potret).
Modul terpisah supaya tidak bentrok dengan pekerjaan Robinhood di arb_cari.py. HANYA MEMBACA: eth_getLogs, eth_call,
eth_getBlockByNumber, eth_getTransactionReceipt, eth_getCode, eth_getTransactionCount (Arc, Ethereum, Base, Arbitrum
publik) + API harga publik (data.binance.vision, Twelve Data bila kunci tersedia). Tanpa transaksi, tanpa kunci pribadi.

Tahap:
  log_token    semua event kontrak token "• Arc Token" (WETH/CRCL/NVDA, kode identik: mint(address,uint256,bytes32)
               oleh keeper, redeem(uint256,address) oleh pemegang, maxSupply, pause) -> arc_token_log.parquet
  layar        tabel pencocokan screenshot (jam UTC/WIB tepat dari stempel blok) -> arc_layar.parquet
  acuan        harga acuan menit: ETH Binance 1m, CRCL/NVDA NYSE (Twelve Data 1 mnt/harian) -> arc_acuan_*.parquet
  pnl          untung-rugi FIFO grup per bot & token + nilai sisa + nilai yang ditebus/dibakar
  lawan        pihak lawan di pool bot: siapa yang menjual murah (tx.from), rugi vs acuan
  jendela      sejak 16 Sep: swap pool aset bernilai dengan diskon >= 5% vs acuan (durasi, volume)
Data: data/research/eksternal/arb/arc_*.parquet. Laporan: bagian Arc di docs/eksternal/hasil_arb_cari.txt
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import arb_cari as A
from .chain_onchain import OUT as ONCHAIN, _addr, ke_waktu, rpc

ARB = A.ARB
SCR = Path(os.environ.get("ARB_SCRATCH", "/tmp"))
TOKEN3 = list(A.TOK_ARC)            # WETH, CRCL, NVDA "• Arc Token"
KEEPER = "0x0d8e72ec76d44aab959b4156f29a3bfe50f5671a"   # keeper() ketiga token (EOA, nonce 13.468 pada 9 Okt 2026)
OWNER = A.ARC_TOKEN_PENERBIT                             # owner() ketiga token (EOA)
DIST = "0x7821f1d95173f214f0ef23069f3a95a29de3f311"     # EOA yang mengirim USDC/NVDA/CRCL ke E1 & menerima balik
BUAT = {"0xd02d2b38d9ccf08044f0a493350a2339fe8d708b": 19_948_946,   # blok pertama kode ada (pencarian biner getCode)
        "0x2ba0f44bdfc17fba30eda9cdbecb908ca45b043b": 19_729_553,
        "0x6505506540dc99f7366316b10e9cf1a584cbd42a": 18_671_508}
POOL_BOT = {"0x7a5de3edaab5780dbcc9a84a3dd9a25a5f4b5d8c": "WETH", "0x2e8180fa3967caf9abf57bbaeab9ae9063bcd7ba": "CRCL",
            "0x4268ad801dc449b12341add14d61119d470959f0": "NVDA"}
MAINNET_PUBLIK = pd.Timestamp("2026-09-16", tz="UTC")


def _blk() -> pd.Series:
    return pd.read_parquet(ONCHAIN / "arc_blok.parquet")["ts"]


# ---------------------------------------------------------------- log token
def log_token() -> pd.DataFrame:
    """Semua log yang dipancarkan 3 kontrak token (semua topik), sejak blok pembuatan. Disimpan per bagian."""
    f = ARB / "arc_token_log.parquet"
    if f.exists():
        return pd.read_parquet(f)
    top = A.head("arc")
    parts = ARB / "arc_token_log_parts"
    parts.mkdir(exist_ok=True)
    b0 = min(BUAT.values())
    B = 400_000
    for k, c in enumerate(range(b0, top + 1, B)):
        fp = parts / f"p_{k:04d}.parquet"
        if fp.exists():
            continue
        c1 = min(c + B - 1, top)

        def dek(x):
            t = x["topics"]
            return {"token": x["address"].lower(), "blok": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                    "tx": x["transactionHash"], "t0": t[0] if t else "", "t1": t[1] if len(t) > 1 else "",
                    "t2": t[2] if len(t) > 2 else "", "t3": t[3] if len(t) > 3 else "", "data": x["data"]}

        rows = A.scan("arc", {"address": TOKEN3}, c, c1, A.SPAN_ALAMAT["arc"], label=f"log token {k}", fn=dek)
        pd.DataFrame(rows, columns=["token", "blok", "li", "tx", "t0", "t1", "t2", "t3", "data"]).to_parquet(
            fp, compression="zstd")
        print(f"  log token bagian {k}: blok {c:,}-{c1:,}: {len(rows):,} log", flush=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(parts.glob("p_*.parquet"))], ignore_index=True)
    df = df.drop_duplicates(["tx", "li"]).sort_values(["blok", "li"]).reset_index(drop=True)
    df["t"] = ke_waktu(df.blok.to_numpy(), _blk())
    df.to_parquet(f, compression="zstd")
    print(f"log token: {len(df):,} -> {f} ({f.stat().st_size / 1e6:.1f} MB)")
    print(df.groupby(["token", "t0"]).size().to_string())
    return df


if __name__ == "__main__":
    tahap = sys.argv[1] if len(sys.argv) > 1 else ""
    if tahap == "log_token":
        log_token()
