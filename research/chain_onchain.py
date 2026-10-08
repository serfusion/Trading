"""Event Uniswap v4/v3 langsung dari RPC chain baru — python -m research.chain_onchain <net> [init|swap|semua]

Melengkapi research/chain_baru.py (GeckoTerminal, candle menit). Di sini setiap swap terlihat: blok, waktu, jumlah
token, harga (sqrtPriceX96) dan likuiditas aktif -> untung/rugi tiap swap terhadap harga ACUAN bisa dihitung persis
(research/chain_baru_uji.py). Hanya membaca (eth_getLogs / eth_call), tanpa transaksi.

Alamat kontrak dari halaman resmi Uniswap (developers.uniswap.org v3/v4 deployments, dicek 8 Okt 2026):
  Robinhood Chain 4663: v4 PoolManager 0x8366a39c..., v3 Factory 0x1f7d7550...
  Arc 5042:             v4 PoolManager 0x8366a39c... (v3 Arc tidak ada di halaman resmi -> hanya v4)
RPC publik: rpc.mainnet.chain.robinhood.com (rentang getLogs besar OK), rpc.mainnet.arc.io (maks < 10.000 blok).
Data: data/research/eksternal/chain_baru/onchain/<net>_{init,swap,liq,blok}.parquet
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .chain_baru import ARC_STABLE, ARC_TOKEN, DIR, RH_ETH, RH_SAHAM, RH_STABLE

OUT = DIR / "onchain"
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
T_LIQ = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
T3_CREATE = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
T3_SWAP = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
T3_INIT = "0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95"  # Initialize(uint160,int24)

NET = {
    "robinhood": {"rpc": "https://rpc.mainnet.chain.robinhood.com", "span": 100_000, "v3": "0x1f7d7550b1b028f7571e69a784071f0205fd2efa",
                  "mulai": 1, "paralel": 4, "muda_hari": 1},
    "arc": {"rpc": "https://rpc.mainnet.arc.io", "span": 5_000, "v3": None, "mulai": 1_948_056,
            "paralel": 8, "muda_hari": 60},  # blok pertama PoolManager punya kode
}


def resmi(net: str) -> dict[str, tuple[str, str]]:
    """alamat -> (nama, acuan) untuk token resmi (acuan: 'USD', 'ETH', 'BTC', 'EUR', ticker saham)."""
    if net == "robinhood":
        d = {a: (n, "USD") for a, n in RH_STABLE.items()}
        d.update({a: (n, "ETH") for a, n in RH_ETH.items()})
        d.update({a: (s, s) for s, a in RH_SAHAM.items()})
        return d
    d = {a: (n, "USD") for a, n in ARC_STABLE.items()}
    d.update({a: (n, ref) for n, (a, ref) in ARC_TOKEN.items()})
    return d


# ---------------------------------------------------------------- RPC
def rpc(net: str, method: str, params: list, tries: int = 8):
    url = NET[net]["rpc"]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers={"content-type": "application/json",
                                                                   "user-agent": "Mozilla/5.0 riset-token"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read())
            if "error" in d:
                msg = str(d["error"].get("message", ""))
                if any(x in msg.lower() for x in ("range", "too many", "limit", "exceed", "size")):
                    raise ValueError(msg)
                if "rate" in msg.lower():
                    time.sleep(2 * (k + 1))
                    continue
                raise RuntimeError(msg)
            return d["result"]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:  # noqa: PERF203
            if isinstance(e, urllib.error.HTTPError) and e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"gagal {method}")


def logs(net: str, address: str | list, topics: list, b0: int, b1: int, span: int | None = None) -> list[dict]:
    """eth_getLogs berpotongan; rentang diperkecil otomatis bila ditolak (dan tidak dinaikkan lagi)."""
    span = span or NET[net]["span"]
    out, cur, n, t0 = [], b0, 0, time.time()
    while cur <= b1:
        hi = min(cur + span - 1, b1)
        try:
            r = rpc(net, "eth_getLogs", [{"address": address, "topics": topics, "fromBlock": hex(cur), "toBlock": hex(hi)}])
        except ValueError:
            span = max(span // 2, 100)
            continue
        out += r
        cur = hi + 1
        n += 1
        if n % 200 == 0:
            print(f"    logs {net}: blok {cur:,}/{b1:,} ({(cur - b0) / max(b1 - b0, 1):.0%}), {len(out)} log, "
                  f"{time.time() - t0:.0f} dtk", flush=True)
    return out


def logs_par(net: str, address, topics: list, b0: int, b1: int, n: int = 6) -> list[dict]:
    """logs() dibagi n potongan rentang blok, dijalankan paralel (RPC Arc membatasi < 10.000 blok/permintaan)."""
    from concurrent.futures import ThreadPoolExecutor
    edges = np.linspace(b0, b1 + 1, n + 1).astype(int)
    with ThreadPoolExecutor(n) as ex:
        parts = list(ex.map(lambda i: logs(net, address, topics, int(edges[i]), int(edges[i + 1]) - 1), range(n)))
    return [x for p in parts for x in p]


def head(net: str) -> int:
    return int(rpc(net, "eth_blockNumber", []), 16)


def blok_waktu(net: str, upto: int) -> pd.Series:
    """Sampel stempel waktu tiap ~1/400 rantai -> interpolasi linear blok->detik (blok stabil 0,1 / 0,5 dtk)."""
    f = OUT / f"{net}_blok.parquet"
    old = pd.read_parquet(f)["ts"] if f.exists() else pd.Series(dtype="int64")
    step = max(upto // 400, 1000)
    want = [b for b in range(1, upto + 1, step)] + [upto]
    have = set(old.index)
    new = {}
    for b in want:
        if b in have:
            continue
        blk = rpc(net, "eth_getBlockByNumber", [hex(b), False])
        new[b] = int(blk["timestamp"], 16)
    s = pd.concat([old, pd.Series(new, dtype="int64")]).sort_index()
    s = s[~s.index.duplicated()]
    s.to_frame("ts").to_parquet(f)
    return s


def ke_waktu(blocks: np.ndarray, s: pd.Series) -> pd.DatetimeIndex:
    ts = np.interp(blocks.astype(float), s.index.values.astype(float), s.values.astype(float))
    return pd.to_datetime(ts, unit="s", utc=True)


def _w(data: str, i: int) -> int:
    return int(data[2 + 64 * i: 2 + 64 * (i + 1)], 16)


def _s(x: int, bits: int = 256) -> int:
    return x - (1 << 256) if x >= 1 << 255 else x


def decimals(net: str, addr: str) -> int:
    if int(addr, 16) == 0:
        return 18
    r = rpc(net, "eth_call", [{"to": addr, "data": "0x313ce567"}, "latest"])
    return int(r, 16)


def _addr(topic: str) -> str:
    return "0x" + topic[-40:].lower()


# ---------------------------------------------------------------- v4
def init_v4(net: str) -> pd.DataFrame:
    """Semua pool v4 yang KEDUA tokennya resmi (pool tiruan/meme dibuang)."""
    f = OUT / f"{net}_init.parquet"
    if f.exists():
        return pd.read_parquet(f)
    OUT.mkdir(parents=True, exist_ok=True)
    R = resmi(net)
    lst = [("0x" + "0" * 24 + a[2:]) for a in R if int(a, 16) != 0]
    top = head(net)
    b0 = NET[net]["mulai"]
    par = NET[net].get("paralel", 1)
    raw = logs_par(net, PM, [T_INIT, None, lst], b0, top, par) + logs_par(net, PM, [T_INIT, None, None, lst], b0, top, par)
    rows = {}
    for lg in raw:
        c0, c1 = _addr(lg["topics"][2]), _addr(lg["topics"][3])
        if c0 not in R or c1 not in R:
            continue
        d = lg["data"]
        rows[lg["topics"][1]] = {"id": lg["topics"][1], "ver": 4, "blok": int(lg["blockNumber"], 16), "c0": c0, "c1": c1,
                                 "fee": _w(d, 0), "tick_spacing": _s(_w(d, 1)), "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3],
                                 "sqrtp0": str(_w(d, 3)), "tx": lg["transactionHash"]}
    df = pd.DataFrame(rows.values())
    df.to_parquet(f)
    print(f"{net}: {len(raw)} Initialize token resmi, {len(df)} pool resmi-resmi")
    return df


def init_v3(net: str) -> pd.DataFrame:
    f = OUT / f"{net}_init3.parquet"
    if f.exists() or not NET[net]["v3"]:
        return pd.read_parquet(f) if f.exists() else pd.DataFrame()
    R = resmi(net)
    lst = [("0x" + "0" * 24 + a[2:]) for a in R if int(a, 16) != 0]
    top = head(net)
    fac = NET[net]["v3"]
    raw = logs(net, fac, [T3_CREATE, lst], 1, top) + logs(net, fac, [T3_CREATE, None, lst], 1, top)
    rows = {}
    for lg in raw:
        c0, c1 = _addr(lg["topics"][1]), _addr(lg["topics"][2])
        if c0 not in R or c1 not in R:
            continue
        pool = "0x" + lg["data"][2 + 64 + 24: 2 + 128]
        rows[pool] = {"id": pool, "ver": 3, "blok": int(lg["blockNumber"], 16), "c0": c0, "c1": c1,
                      "fee": int(lg["topics"][3], 16), "tick_spacing": _s(_w(lg["data"], 0)), "hooks": "", "sqrtp0": "",
                      "tx": lg["transactionHash"]}
    df = pd.DataFrame(rows.values())
    df.to_parquet(f)
    print(f"{net}: v3 {len(df)} pool resmi-resmi")
    return df


def _dec_swap_v4(lg: dict) -> dict:
    d = lg["data"]
    # v4: BalanceDelta pemanggil -> negatif = dibayar ke pool, positif = diterima
    return {"id": lg["topics"][1], "blok": int(lg["blockNumber"], 16), "li": int(lg["logIndex"], 16),
            "tx": lg["transactionHash"], "sender": _addr(lg["topics"][2]), "a0": float(_s(_w(d, 0))),
            "a1": float(_s(_w(d, 1))), "sqrtp": float(_w(d, 2)), "L": float(_w(d, 3)), "fee": _w(d, 5)}


def _dec_swap_v3(lg: dict) -> dict:
    d = lg["data"]
    # v3: jumlah dari sisi POOL -> dibalik agar sama dengan v4 (sisi penukar)
    return {"id": lg["address"].lower(), "blok": int(lg["blockNumber"], 16), "li": int(lg["logIndex"], 16),
            "tx": lg["transactionHash"], "sender": _addr(lg["topics"][1]), "a0": -float(_s(_w(d, 0))),
            "a1": -float(_s(_w(d, 1))), "sqrtp": float(_w(d, 2)), "L": float(_w(d, 3)), "fee": -1}


MUDA_HARI = 3   # pool tanpa token saham: swap hanya diambil 3 hari pertama sejak pool dibuat (saat salah harga)
MAX_ID = 900    # batas jumlah nilai topik per permintaan RPC


def swaps(net: str, pools: pd.DataFrame) -> pd.DataFrame:
    """Swap (v4 & v3) + tambah/kurang likuiditas v4 per jendela blok. Pool berisi token SAHAM: seluruh riwayat;
    pool lain (ETH/WETH/stablecoin): hanya MUDA_HARI pertama (pool besar ETH/USDG diarbitrase bot tiap blok; yang
    dicari = pool baru yang salah harga)."""
    f = OUT / f"{net}_swap.parquet"
    if f.exists():
        return pd.read_parquet(f)
    R = resmi(net)
    saham = {a for a, (_, ref) in R.items() if ref not in ("USD", "ETH", "BTC", "EUR")}
    pools = pools.copy()
    pools["saham"] = pools.c0.isin(saham) | pools.c1.isin(saham)
    bt = NET[net].get("blok_dtk", 0.1 if net == "robinhood" else 0.5)
    muda = int(NET[net].get("muda_hari", MUDA_HARI) * 86400 / bt)
    top = head(net)
    span = NET[net]["span"] - 1
    b0 = int(pools.blok.min())
    blk = pools.blok.to_numpy()
    wins = [(c, min(c + span - 1, top)) for c in range(b0, top + 1, span)]

    def satu(w):
        cur, hi = w
        rows, liq = [], []
        aktif = pools[(blk <= hi) & (pools.saham | (blk + muda >= cur))]
        for ver, dec, tp in ((4, _dec_swap_v4, T_SWAP), (3, _dec_swap_v3, T3_SWAP)):
            a = aktif[aktif.ver == ver]
            for i in range(0, len(a), MAX_ID):
                part = list(a.id.iloc[i:i + MAX_ID])
                if ver == 4:
                    lg = logs(net, PM, [tp, part], cur, hi, span=span)
                    for x in logs(net, PM, [T_LIQ, part], cur, hi, span=span):
                        d = x["data"]
                        liq.append({"id": x["topics"][1], "blok": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                                    "tickL": _s(_w(d, 0)), "tickU": _s(_w(d, 1)), "dL": float(_s(_w(d, 2)))})
                else:
                    lg = logs(net, part, [tp], cur, hi, span=span)
                rows += [dec(x) for x in lg]
        return rows, liq, len(aktif)

    from concurrent.futures import ThreadPoolExecutor
    parts = OUT / f"{net}_swap_parts"
    parts.mkdir(exist_ok=True)
    BATCH = 50
    t0 = time.time()
    for k in range(0, len(wins), BATCH):
        fp, fl = parts / f"swap_{k // BATCH:05d}.parquet", parts / f"liq_{k // BATCH:05d}.parquet"
        if fp.exists() and fl.exists():
            continue
        rows, liq = [], []
        with ThreadPoolExecutor(NET[net].get("paralel", 1)) as ex:
            for r_, l_, na in ex.map(satu, wins[k:k + BATCH]):
                rows += r_
                liq += l_
        d = pd.DataFrame(rows, columns=["id", "blok", "li", "tx", "sender", "a0", "a1", "sqrtp", "L", "fee"])
        d.to_parquet(fp, compression="zstd")
        pd.DataFrame(liq, columns=["id", "blok", "li", "tickL", "tickU", "dL"]).to_parquet(fl, compression="zstd")
        print(f"  swap {net}: jendela {min(k + BATCH, len(wins)):,}/{len(wins):,} (+{len(d):,} swap) aktif {na} "
              f"{time.time() - t0:.0f} dtk", flush=True)
    fee3 = pools.set_index("id").fee
    cols = ["id", "blok", "li", "sender", "a0", "a1", "sqrtp", "L", "fee"]
    df = pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(parts.glob("swap_*.parquet"))], ignore_index=True)
    df["id"] = df.id.astype("category")
    df["sender"] = df.sender.astype("category")
    df = df.sort_values(["blok", "li"]).reset_index(drop=True)
    m3 = df.fee < 0
    df.loc[m3, "fee"] = df.loc[m3, "id"].astype(str).map(fee3).fillna(0).astype(int)
    df.to_parquet(f, compression="zstd")
    lq = pd.concat([pd.read_parquet(f) for f in sorted(parts.glob("liq_*.parquet"))], ignore_index=True)
    lq.to_parquet(OUT / f"{net}_liq.parquet")
    return df


def semua(net: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p4 = init_v4(net)
    p3 = init_v3(net)
    pools = pd.concat([p4, p3], ignore_index=True)
    dec = {a: decimals(net, a) for a in set(pools.c0) | set(pools.c1)}
    pools["d0"] = pools.c0.map(dec)
    pools["d1"] = pools.c1.map(dec)
    print(f"{net}: {len(pools)} pool (v4 {len(p4)}, v3 {len(p3)})", flush=True)
    pools.to_parquet(OUT / f"{net}_pools.parquet")
    sw = swaps(net, pools)
    s = blok_waktu(net, head(net))
    print(f"{net}: {len(sw)} swap, blok->waktu {len(s)} sampel", flush=True)


if __name__ == "__main__":
    semua(sys.argv[1])
