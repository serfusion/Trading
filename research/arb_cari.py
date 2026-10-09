"""Cari bot arbitrase screenshot "wetharb" & "circarb" di data on-chain — python -m research.arb_cari <tahap> [net]

Permintaan pengguna 8 Okt 2026: dua screenshot bot Telegram (jam WIB, tanggal tidak diketahui):
  wetharb : "BUY 3.0000 USDC -> 0.00321553 WETH @932.97$" ... (pecahan 3 USDC, harga naik ±4,5% per 3 USDC, berhenti
            di ±$1.000, berulang saat harga turun lagi)
  circarb : "CRCL[B] BUY 25.0000 USDC -> 1.250481 CRCL @19.99$" / "CRCL[B] SELL 0.399409 -> 23.8194 USDC @59.64$" ...
Riset lama (docs/TOKEN_BARU.md) hanya memuat pool yang KEDUA tokennya ada di daftar putih. Modul ini:

  pabrik [net]    semua event pembuatan pool (Uniswap v4 Initialize dari PoolManager MANA PUN, v3 PoolCreated, v2
                  PairCreated, Algebra Pool, Solidly/Aerodrome, Slipstream, iZiSwap, LB) TANPA filter daftar putih
  token  [net]    symbol()/name()/decimals() tiap token lewat eth_call
  kandidat        pool yang simbolnya WETH/ETH/CRCL dengan pasangan USD apa pun (USDC/USDG/USDT/...) + semua pool
                  WETH/CRCL lain
  swap   [net]    unduh swap pool kandidat (v4 per id, v3/v2/Algebra per alamat)
  cari            cocokkan jumlah PERSIS screenshot (USDC 6 desimal, WETH 8 digit tampil, CRCL 6 digit tampil)
  lacak           bila ketemu: tx.from, seluruh aktivitas alamat bot, untung per putaran, pihak lawan
  potret          selisih harga mid antar pool saat ini (StateView getSlot0/getLiquidity v4, slot0/liquidity v3,
                  getReserves v2) + perkiraan untung $3/$25/$100 setelah fee kedua pool & gas
  semua           semua tahap

HANYA MEMBACA (eth_getLogs, eth_call, eth_blockNumber, eth_getBlockByNumber, eth_getTransactionByHash,
eth_getTransactionReceipt). Tanpa transaksi, tanpa kunci pribadi.
Data: data/research/eksternal/arb/ (tiap file < 50 MB). Laporan: docs/eksternal/hasil_arb_cari.txt
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .chain_onchain import NET, OUT as ONCHAIN, PM, T_INIT, T3_CREATE, T3_SWAP, T_SWAP, _addr, _s, _w, rpc

ROOT = Path(__file__).resolve().parent.parent
ARB = ROOT / "data" / "research" / "eksternal" / "arb"
LAP = ROOT / "docs" / "eksternal" / "hasil_arb_cari.txt"

# ---------------------------------------------------------------- topik event pembuatan pool
T_V2_PAIR = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"   # PairCreated(addr,addr,addr,uint)
T_ALG_POOL = "0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db"  # Pool(addr,addr,addr) Algebra v1
T_SOLID = "0xc4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9"     # PairCreated(addr,addr,bool,addr,uint)
T_AERO = "0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e"      # PoolCreated(addr,addr,bool,addr,uint)
T_SLIP = "0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2"      # PoolCreated(addr,addr,int24,addr)
T_ALG_CUSTOM = "0x8a5f030f5fc13b04a1e4ef7c47177e3d76b0e80e1d9be9843db37caa5b7b9b8f"  # CustomPool(addr,addr,addr,addr)
T_IZI = None  # diisi di bawah (keccak)
T_LB = None
PEMBUAT = {T_INIT: "v4", T3_CREATE: "v3", T_V2_PAIR: "v2", T_ALG_POOL: "alg", T_SOLID: "solid", T_AERO: "aero",
           T_SLIP: "slip", T_ALG_CUSTOM: "algc"}

# swap event per jenis
T_V2_SWAP = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"   # Swap(addr,uint,uint,uint,uint,addr)
T_SOLID_SWAP = None  # Swap(address,address,uint256,uint256,uint256,uint256) — diisi di bawah
T_ALG_SWAP = T3_SWAP  # Algebra v1/Integral: tanda tangan sama dengan v3
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _keccak(s: str) -> str:
    try:
        from eth_utils import keccak
        return "0x" + keccak(text=s).hex()
    except ImportError:  # pragma: no cover
        from Crypto.Hash import keccak as k  # type: ignore
        h = k.new(digest_bits=256)
        h.update(s.encode())
        return "0x" + h.hexdigest()


T_IZI = _keccak("NewPool(address,address,uint24,uint24,address)")
T_LB = _keccak("LBPairCreated(address,address,uint256,address,uint256)")
T_SOLID_SWAP = _keccak("Swap(address,address,uint256,uint256,uint256,uint256)")
PEMBUAT[T_IZI] = "izi"
PEMBUAT[T_LB] = "lb"

# TESTNET (hipotesis: screenshot bisa dari testnet — token tanpa nilai). RPC publik resmi, hanya baca.
NET.setdefault("arc_testnet", {"rpc": "https://rpc.testnet.arc.network", "span": 9_999, "v3": None, "mulai": 1})
NET.setdefault("rh_testnet", {"rpc": "https://rpc.testnet.chain.robinhood.com", "span": 30_000, "v3": None, "mulai": 1})
SPAN_TOPIK = {"robinhood": 30_000, "arc": 9_999, "arc_testnet": 9_999, "rh_testnet": 30_000}   # getLogs tanpa alamat
SPAN_ALAMAT = {"robinhood": 100_000, "arc": 9_999, "arc_testnet": 9_999, "rh_testnet": 30_000}  # dengan filter alamat
PAR = {"robinhood": 6, "arc": 8, "arc_testnet": 8, "rh_testnet": 6}
ADDR_PER_REQ = {"robinhood": 200, "arc": 20, "arc_testnet": 20, "rh_testnet": 200}
STATE_VIEW = "0xf3334192d15450cdd385c8b70e03f9a6bd9e673b"   # sama di kedua chain (developers.uniswap.org)


def _dir() -> Path:
    ARB.mkdir(parents=True, exist_ok=True)
    return ARB


def head(net: str) -> int:
    return int(rpc(net, "eth_blockNumber", []), 16)


def _logs_satu(net: str, flt: dict, b0: int, b1: int) -> list[dict]:
    """Satu rentang; dibelah dua bila RPC menolak (terlalu banyak hasil / rentang)."""
    try:
        return rpc(net, "eth_getLogs", [dict(flt, fromBlock=hex(b0), toBlock=hex(b1))])
    except (ValueError, RuntimeError) as e:
        msg = str(e).lower()
        if b1 > b0 and any(x in msg for x in ("range", "limit", "exceed", "too many", "size", "spans", "narrow",
                                               "10000", "response", "timed out", "timeout")):
            mid = (b0 + b1) // 2
            return _logs_satu(net, flt, b0, mid) + _logs_satu(net, flt, mid + 1, b1)
        raise


def scan(net: str, flt: dict, b0: int, b1: int, span: int, par: int | None = None, label: str = "",
         fn=None) -> list:
    """getLogs berpotongan paralel; fn (opsional) mengubah log tiap jendela langsung (hemat memori)."""
    wins = [(c, min(c + span - 1, b1)) for c in range(b0, b1 + 1, span)]
    out: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(par or PAR[net]) as ex:
        for k, r in enumerate(ex.map(lambda w: _logs_satu(net, flt, w[0], w[1]), wins)):
            out += [y for y in map(fn, r) if y] if fn else r
            if (k + 1) % 500 == 0:
                print(f"    {label} {net}: {k + 1:,}/{len(wins):,} jendela, {len(out):,} log, {time.time() - t0:.0f} dtk",
                      flush=True)
    return out


# ---------------------------------------------------------------- tahap 1: pabrik
def _dekode_pembuatan(lg: dict) -> dict | None:
    t = lg["topics"]
    jenis = PEMBUAT.get(t[0])
    d = lg["data"]
    em = lg["address"].lower()
    base = {"jenis": jenis, "emitter": em, "blok": int(lg["blockNumber"], 16), "tx": lg["transactionHash"]}
    try:
        if jenis == "v4":
            return dict(base, pool=t[1], c0=_addr(t[2]), c1=_addr(t[3]), fee=_w(d, 0), ts=_s(_w(d, 1)),
                        hooks="0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], sqrtp0=str(_w(d, 3)))
        if jenis == "v3":
            return dict(base, pool="0x" + d[2 + 64 + 24: 2 + 128], c0=_addr(t[1]), c1=_addr(t[2]), fee=int(t[3], 16),
                        ts=_s(_w(d, 0)), hooks="", sqrtp0="")
        if jenis in ("v2", "alg", "solid", "aero", "slip", "lb"):
            fee = int(t[3], 16) if len(t) > 3 else -1
            return dict(base, pool="0x" + d[2 + 24: 2 + 64], c0=_addr(t[1]), c1=_addr(t[2]), fee=fee, ts=0, hooks="",
                        sqrtp0="")
        if jenis == "algc":
            return dict(base, pool="0x" + d[2 + 24: 2 + 64], c0=_addr(t[2]), c1=_addr(t[3]), fee=-1, ts=0,
                        hooks=_addr(t[1]), sqrtp0="")
        if jenis == "izi":
            return dict(base, pool="0x" + d[2 + 64 + 24: 2 + 128], c0=_addr(t[1]), c1=_addr(t[2]), fee=int(t[3], 16),
                        ts=_w(d, 0), hooks="", sqrtp0="")
    except (IndexError, ValueError):
        return None
    return None


def pabrik(net: str) -> pd.DataFrame:
    """Semua event pembuatan pool; disimpan per bagian 200 jendela (hemat memori, bisa dilanjutkan)."""
    f = _dir() / f"{net}_semua_pool.parquet"
    if f.exists():
        return pd.read_parquet(f)
    import pyarrow as pa
    import pyarrow.parquet as pq
    top = head(net)
    span = SPAN_TOPIK[net]
    parts = _dir() / f"{net}_pabrik_parts"
    parts.mkdir(exist_ok=True)
    meta = parts / "top.json"
    if meta.exists():
        top = json.loads(meta.read_text())["top"]
    else:
        meta.write_text(json.dumps({"top": top}))
    B = 200 * span
    for k, c in enumerate(range(1, top + 1, B)):
        fp = parts / f"p_{k:04d}.parquet"
        if fp.exists():
            continue
        rows = scan(net, {"topics": [list(PEMBUAT)]}, c, min(c + B - 1, top), span, label=f"pabrik bag {k}",
                    fn=_dekode_pembuatan)
        cols = ["jenis", "emitter", "blok", "tx", "pool", "c0", "c1", "fee", "ts", "hooks", "sqrtp0"]
        d = pd.DataFrame(rows, columns=cols)
        for c_ in ("fee", "ts"):
            d[c_] = [int(v) if isinstance(v, int) and abs(v) < 2 ** 62 else -1 for v in d[c_]]
        d.astype({"fee": "int64", "ts": "int64"}).to_parquet(fp, compression="zstd")
        print(f"  pabrik {net}: bagian {k} blok {c:,}-{min(c + B - 1, top):,}: {len(rows):,} pool", flush=True)
    t = pa.concat_tables([pq.read_table(p) for p in sorted(parts.glob("p_*.parquet"))])
    df = t.to_pandas(types_mapper=pd.ArrowDtype) if False else t.to_pandas()
    df = df.drop_duplicates(["jenis", "emitter", "pool"]).sort_values("blok").reset_index(drop=True)
    df.to_parquet(f, compression="zstd")
    print(f"{net}: {len(df):,} pool; per jenis/emitter:")
    print(df.groupby(["jenis", "emitter"]).size().sort_values(ascending=False).head(20).to_string())
    return df


# ---------------------------------------------------------------- tahap 2: token
def _str_abi(h: str) -> str:
    if not h or h == "0x":
        return ""
    b = bytes.fromhex(h[2:])
    try:
        if len(b) >= 64:
            off = int.from_bytes(b[:32], "big")
            n = int.from_bytes(b[off:off + 32], "big")
            if n < 200:
                return b[off + 32: off + 32 + n].decode("utf-8", "replace")
        return b[:32].rstrip(b"\0").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _call(net: str, to: str, data: str, blok: str = "latest") -> str:
    try:
        return rpc(net, "eth_call", [{"to": to, "data": data}, blok], tries=3)
    except Exception:  # noqa: BLE001
        return ""


MC3 = "0xca11bde05977b3631167028862be2a173976ca11"   # Multicall3 (kode ada di kedua chain, dicek 8 Okt 2026)


def multicall(net: str, calls: list[tuple[str, str]], blok: str = "latest") -> list[str | None]:
    """aggregate3 (allowFailure) -> hex hasil tiap panggilan (None bila gagal). Hanya eth_call."""
    from eth_abi import decode, encode
    if not calls:
        return []
    arg = [(to, True, bytes.fromhex(data[2:])) for to, data in calls]
    data = "0x82ad56cb" + encode(["(address,bool,bytes)[]"], [arg]).hex()
    r = rpc(net, "eth_call", [{"to": MC3, "data": data}, blok], tries=6)
    out = decode(["(bool,bytes)[]"], bytes.fromhex(r[2:]))[0]
    return ["0x" + b.hex() if ok else None for ok, b in out]


def multicall_banyak(net: str, calls: list[tuple[str, str]], chunk: int = 300, blok: str = "latest") -> list:
    parts = [calls[i:i + chunk] for i in range(0, len(calls), chunk)]

    def satu(p):
        try:
            return multicall(net, p, blok)
        except Exception:  # noqa: BLE001 — satu token jahat bisa membuat batch gagal -> belah
            if len(p) == 1:
                return [None]
            h = len(p) // 2
            return satu(p[:h]) + satu(p[h:])

    with ThreadPoolExecutor(PAR[net]) as ex:
        res = list(ex.map(satu, parts))
    return [x for r in res for x in r]


def token(net: str, addrs: list[str] | None = None) -> pd.DataFrame:
    f = _dir() / f"{net}_token.parquet"
    if addrs is None:
        pools = pabrik(net)
        addrs = sorted(set(pools.c0) | set(pools.c1))
    old = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=["alamat", "symbol", "name", "decimals"])
    have = set(old.alamat)
    todo = [a for a in addrs if a not in have]
    new = []
    for a in [a for a in todo if int(a, 16) == 0]:
        new.append({"alamat": a, "symbol": "ETH" if net == "robinhood" else "USDC(native)", "name": "native",
                    "decimals": 18})
    todo = [a for a in todo if int(a, 16) != 0]
    t0 = time.time()
    B = 20_000
    for i in range(0, len(todo), B):
        part = todo[i:i + B]
        calls = [(a, s) for a in part for s in ("0x95d89b41", "0x06fdde03", "0x313ce567")]
        res = multicall_banyak(net, calls)
        for j, a in enumerate(part):
            sym, name, dec = res[3 * j: 3 * j + 3]
            try:
                d = int(dec, 16) if dec and dec != "0x" and len(dec) <= 66 else -1
            except ValueError:
                d = -1
            new.append({"alamat": a, "symbol": _str_abi(sym or "").strip()[:40], "name": _str_abi(name or "").strip()[:60],
                        "decimals": d})
        print(f"    token {net}: {min(i + B, len(todo)):,}/{len(todo):,} {time.time() - t0:.0f} dtk", flush=True)
    df = pd.concat([old, pd.DataFrame(new)], ignore_index=True).drop_duplicates("alamat")
    df.to_parquet(f)
    print(f"{net}: {len(df):,} token ({len(new):,} baru)")
    return df


# ---------------------------------------------------------------- tahap 3: kandidat
def _isusd(sym: str) -> bool:
    s = sym.upper()
    return "USD" in s or s in ("USDC", "USDT", "DAI", "USDG", "PYUSD", "USDE")


def _isweth(sym: str) -> bool:
    s = sym.upper()
    return s in ("WETH", "ETH", "WETH.E") or "WETH" in s or (s.endswith("ETH") and len(s) <= 6)


def _iscrcl(sym: str, name: str = "") -> bool:
    return "CRCL" in sym.upper() or "CIRCLE INTERNET" in name.upper()


def kandidat(net: str) -> pd.DataFrame:
    pools = pabrik(net)
    tok = token(net).set_index("alamat")
    for k in ("0", "1"):
        pools["s" + k] = pools["c" + k].map(tok.symbol).fillna("")
        pools["n" + k] = pools["c" + k].map(tok.name).fillna("")
        pools["d" + k] = pools["c" + k].map(tok.decimals).fillna(-1).astype(int)
    u0, u1 = pools.s0.map(_isusd), pools.s1.map(_isusd)
    w0, w1 = pools.s0.map(_isweth), pools.s1.map(_isweth)
    c0 = [_iscrcl(s, n) for s, n in zip(pools.s0, pools.n0)]
    c1 = [_iscrcl(s, n) for s, n in zip(pools.s1, pools.n1)]
    c0, c1 = np.array(c0), np.array(c1)
    pools["kelas"] = ""
    pools.loc[(w0 & u1) | (w1 & u0), "kelas"] = "WETH/USD"
    pools.loc[(c0 & u1) | (c1 & u0), "kelas"] = "CRCL/USD"
    pools.loc[(pools.kelas == "") & ((c0 | c1)), "kelas"] = "CRCL/lain"
    pools.loc[(pools.kelas == "") & (w0 | w1), "kelas"] = "WETH/lain"
    pools["net"] = net
    pools.to_parquet(_dir() / f"{net}_semua_pool.parquet")
    k = pools[pools.kelas != ""].copy()
    k.to_parquet(_dir() / f"{net}_kandidat.parquet")
    print(f"{net}: kandidat {len(k):,} pool:")
    print(k.groupby(["kelas", "jenis"]).size().to_string())
    return k


# ---------------------------------------------------------------- tahap 4: swap pool kandidat
SWAP_COLS = ["id", "jenis", "blok", "li", "tx", "sender", "recipient", "a0", "a1", "sqrtp", "L"]


def _dec_swap(lg: dict, jenis_alamat: dict) -> dict | None:
    t, d = lg["topics"], lg["data"]
    try:
        if t[0] == T_SWAP:   # v4: delta sisi pemanggil (negatif = dibayar ke pool)
            return {"id": t[1], "jenis": "v4", "blok": int(lg["blockNumber"], 16), "li": int(lg["logIndex"], 16),
                    "tx": lg["transactionHash"], "sender": _addr(t[2]), "recipient": "", "a0": float(_s(_w(d, 0))),
                    "a1": float(_s(_w(d, 1))), "sqrtp": float(_w(d, 2)), "L": float(_w(d, 3))}
        a = lg["address"].lower()
        if t[0] == T3_SWAP:  # v3/Algebra/Slipstream: sisi pool -> dibalik ke sisi penukar
            return {"id": a, "jenis": jenis_alamat.get(a, "v3"), "blok": int(lg["blockNumber"], 16),
                    "li": int(lg["logIndex"], 16), "tx": lg["transactionHash"], "sender": _addr(t[1]),
                    "recipient": _addr(t[2]), "a0": -float(_s(_w(d, 0))), "a1": -float(_s(_w(d, 1))),
                    "sqrtp": float(_w(d, 2)), "L": float(_w(d, 3))}
        if t[0] in (T_V2_SWAP, T_SOLID_SWAP):
            if t[0] == T_V2_SWAP:
                i0, i1, o0, o1 = (_w(d, k) for k in range(4))
            else:
                i0, i1, o0, o1 = (_w(d, k) for k in range(4))
            return {"id": a, "jenis": jenis_alamat.get(a, "v2"), "blok": int(lg["blockNumber"], 16),
                    "li": int(lg["logIndex"], 16), "tx": lg["transactionHash"], "sender": _addr(t[1]),
                    "recipient": _addr(t[2]), "a0": float(o0) - float(i0), "a1": float(o1) - float(i1),
                    "sqrtp": np.nan, "L": np.nan}
    except (IndexError, ValueError):
        return None
    return None


def swap_kandidat(net: str, kelas: tuple = ("WETH/USD", "CRCL/USD", "CRCL/lain", "WETH/lain")) -> pd.DataFrame:
    """Swap semua pool kandidat yang BELUM ada di data riset lama (pool resmi-resmi). Disimpan per bagian."""
    f = _dir() / f"{net}_swap_kandidat.parquet"
    if f.exists():
        return pd.read_parquet(f)
    k = pd.read_parquet(_dir() / f"{net}_kandidat.parquet")
    k = k[k.kelas.isin(kelas)]
    lama = set(pd.read_parquet(ONCHAIN / f"{net}_pools.parquet").id)
    if net == "arc":   # pool resmi Arc: seluruh riwayat sudah ada
        k = k[~k.pool.isin(lama)]
    else:              # Robinhood: pool resmi-resmi sudah diteliti (saham seluruh riwayat, ETH/WETH/USDG 3 hari
        k = k[~k.pool.isin(lama)]   # pertama; pool besar itu diarbitrase bot tiap blok) -> hanya pool non-daftar-putih
    # Robinhood: pool ETH/WETH/USDG lama hanya 3 hari pertama -> ikut diunduh ulang seluruhnya
    top = head(net)
    span = SPAN_ALAMAT[net]
    jenis_alamat = dict(zip(k.pool, k.jenis))
    parts = _dir() / f"{net}_swap_parts"
    parts.mkdir(exist_ok=True)
    tugas = []
    v4 = k[k.jenis == "v4"]
    for em, g in v4.groupby("emitter"):
        ids = list(g.pool)
        for i in range(0, len(ids), 500):
            tugas.append(("v4", em, ids[i:i + 500], int(g.blok.min())))
    lain = k[k.jenis.isin(["v3", "alg", "slip", "algc", "v2", "solid", "aero"])]
    lain = lain.sort_values("blok")
    adr = list(lain.pool)
    na = ADDR_PER_REQ[net]   # RPC Arc menolak ("requested range too large") bila alamat x blok terlalu besar
    for i in range(0, len(adr), na):
        tugas.append(("addr", None, adr[i:i + na], int(lain.blok.iloc[i:i + na].min())))
    print(f"{net}: {len(k):,} pool kandidat (v4 {len(v4):,}, lain {len(lain):,}) -> {len(tugas)} tugas", flush=True)
    for j, (tp, em, part, b0) in enumerate(tugas):
        fp = parts / f"swap_{j:04d}.parquet"
        if fp.exists():
            continue
        if tp == "v4":
            flt = {"address": em, "topics": [T_SWAP, part]}
        else:
            flt = {"address": part, "topics": [[T3_SWAP, T_V2_SWAP, T_SOLID_SWAP]]}
        rows = scan(net, flt, b0, top, span, label=f"swap {j + 1}/{len(tugas)}",
                    fn=lambda x: _dec_swap(x, jenis_alamat))
        pd.DataFrame(rows, columns=SWAP_COLS).to_parquet(fp, compression="zstd")
        print(f"  {net} tugas {j + 1}/{len(tugas)}: {len(rows):,} swap", flush=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(parts.glob("swap_*.parquet"))], ignore_index=True)
    df = df.sort_values(["blok", "li"]).reset_index(drop=True)
    df.to_parquet(f, compression="zstd")
    print(f"{net}: {len(df):,} swap kandidat -> {f} ({f.stat().st_size / 1e6:.1f} MB)")
    return df


# ---------------------------------------------------------------- tahap 5: cocokkan jumlah screenshot
# (bot, arah, USDC tampil 4 desimal, aset tampil 8/6 digit, jam WIB tampil)
SS = [
    ("wetharb", "BUY", 3.0, 0.00321553, "19:08"), ("wetharb", "BUY", 3.0, 0.00307713, "19:08"),
    ("wetharb", "BUY", 0.375, 0.00037535, "19:08"), ("wetharb", "BUY", 3.0, 0.00335627, "19:09"),
    ("wetharb", "BUY", 3.0, 0.00320879, "19:09"), ("wetharb", "BUY", 3.0, 0.00307082, "19:09"),
    ("wetharb", "BUY", 3.0, 0.00323409, "19:15"), ("wetharb", "BUY", 3.0, 0.00309451, "19:15"),
    ("wetharb", "BUY", 0.75, 0.00075287, "19:15"),
    ("circarb", "SELL", 23.8194, 0.399409, "19:17"), ("circarb", "BUY", 25.0, 1.250481, "19:20"),
    ("circarb", "SELL", 38.6142, 0.648057, "19:21"), ("circarb", "BUY", 25.0, 0.806017, "19:21"),
    ("circarb", "BUY", 12.5, 0.313612, "19:21"), ("circarb", "SELL", 39.3559, 0.368462, "19:21"),
    ("circarb", "SELL", 38.4092, 0.570559, "19:22"), ("circarb", "BUY", 25.0, 0.865127, "19:22"),
    ("circarb", "SELL", 42.7415, 0.712878, "19:22"), ("circarb", "SELL", 38.5639, 0.590954, "19:22"),
    ("circarb", "SELL", 23.3361, 0.344325, "19:23"), ("circarb", "SELL", 39.4181, 0.573879, "19:17"),
]


def _muat_swap_semua(net: str) -> pd.DataFrame:
    """Swap kandidat (baru) + swap riset lama (pool resmi) dengan kolom seragam: usd, aset, simbol."""
    kp = pd.read_parquet(_dir() / f"{net}_semua_pool.parquet",
                         columns=["pool", "jenis", "emitter", "c0", "c1", "s0", "s1", "d0", "d1", "fee", "hooks"])
    kp = kp.drop_duplicates("pool").set_index("pool")
    parts = sorted((_dir() / f"{net}_swap_parts").glob("swap_*.parquet"))
    sw = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True) if parts else pd.DataFrame(columns=SWAP_COLS)
    return sw.join(kp[["c0", "c1", "s0", "s1", "d0", "d1"]], on="id")


def cari(net: str, sw: pd.DataFrame | None = None) -> pd.DataFrame:
    sw = _muat_swap_semua(net) if sw is None else sw
    v0 = sw.a0.abs() / 10.0 ** sw.d0
    v1 = sw.a1.abs() / 10.0 ** sw.d1
    hits = []
    for bot, arah, u, w, jam in SS:
        tol_w = 1.01e-8 if bot == "wetharb" else 1.01e-6
        m_pair = (((v0 - u).abs() < 1.01e-4) & ((v1 - w).abs() <= tol_w)) | (((v1 - u).abs() < 1.01e-4) & ((v0 - w).abs() <= tol_w))
        m_aset = ((v0 - w).abs() <= tol_w) | ((v1 - w).abs() <= tol_w)
        for nama, m in (("pasangan", m_pair), ("aset_saja", m_aset & ~m_pair)):
            for _, r in sw[m].iterrows():
                hits.append(dict(bot=bot, arah=arah, usd=u, aset=w, jam_wib=jam, cocok=nama, **r.to_dict()))
    return pd.DataFrame(hits)


# ---------------------------------------------------------------- tahap 6: lacak alamat bot
def _pad(a: str) -> str:
    return "0x" + "0" * 24 + a[2:].lower()


def transfer_alamat(net: str, alamat: list[str], b0: int, b1: int | None = None, nama: str = "") -> pd.DataFrame:
    """Semua Transfer ERC-20 (token apa pun) dari/ke alamat-alamat ini (filter topik, tanpa filter kontrak)."""
    b1 = b1 or head(net)
    lst = [_pad(a) for a in alamat]

    def dek(x):
        t = x["topics"]
        if len(t) < 3 or len(x["data"]) < 66:
            return None
        return {"token": x["address"].lower(), "blok": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                "tx": x["transactionHash"], "dari": _addr(t[1]), "ke": _addr(t[2]), "nilai": float(int(x["data"][2:66], 16))}

    out = []
    for topics in ([T_TRANSFER, lst], [T_TRANSFER, None, lst]):
        out += scan(net, {"topics": topics}, b0, b1, SPAN_TOPIK[net], label=f"transfer {nama}", fn=dek)
    df = pd.DataFrame(out).drop_duplicates(["tx", "li"]).sort_values(["blok", "li"]).reset_index(drop=True)
    if nama:
        df.to_parquet(_dir() / f"{net}_transfer_{nama}.parquet", compression="zstd")
    return df


def tx_dari_blok(net: str, blok: int, txh: str) -> dict:
    """RPC Arc tidak melayani eth_getTransactionByHash untuk tx lama -> ambil dari blok (full tx)."""
    try:
        r = rpc(net, "eth_getTransactionByHash", [txh], tries=2)
        if r:
            return r
    except Exception:  # noqa: BLE001
        pass
    b = rpc(net, "eth_getBlockByNumber", [hex(blok), True])
    for t in b["transactions"]:
        if t["hash"].lower() == txh.lower():
            return t
    return {}


# ---------------------------------------------------------------- tahap 6b: analisa grup bot screenshot (Arc)
NATIVE_ARC = "0xfffffffffffffffffffffffffffffffffffffffe"   # log Transfer USDC native Arc (18 desimal)
USDC_ARC = "0x3600000000000000000000000000000000000000"     # antarmuka ERC-20 (6 desimal) — duplikat 0xfff..fe
E1 = "0x673250c66d8debe10bcbdd0261a3c51065026886"            # pemilik bot "wetharb" (+4 bot lain)
E2 = "0x7cff8a2b32b28ab52794c8365ae3d7423dbc87db"            # pemilik bot "circarb" (+2 bot lain), didanai E1
BOT = {
    "0xa25790ec97bf6be57c0f7e41b3bb858d13b262b1": ("wetharb", E1),
    "0xcdfe8dabe88e625ed23819066be85d36c2558551": ("circarb CRCL[B]", E2),
    "0xd410b19adea79ac2d8bbe4f8607a12f1b7329529": ("bot NVDA E2", E2),
    "0xc18f971dd86652e4d8f8f1b2695884bf8d7574fe": ("bot E2 #3", E2),
    "0x9b92efd6d50103696b60a08413c74fd4d3476bdb": ("bot NVDA E1", E1),
    "0xa807c38887f6c94efea5ac02f8a6c74c6897eb13": ("bot NVDA E1 awal", E1),
    "0x76e5c0b9b31acb9fcbe6730fa9ebd790bf3c56e2": ("bot CRCL E1", E1),
    "0x186603715be592ea531e1db3f979cba903f3d3f5": ("bot CRCL E1 awal", E1),
}
GRUP = {E1: "E1", E2: "E2", **{a: v[0] for a, v in BOT.items()}}
ARC_TOKEN_PENERBIT = "0xb053c334d151374fc19f784ebd543b73701ddfd8"   # pemilik WETH/CRCL/NVDA "• Arc Token"
TOK_ARC = {"0xd02d2b38d9ccf08044f0a493350a2339fe8d708b": ("WETH•Arc", "ETH"),
           "0x2ba0f44bdfc17fba30eda9cdbecb908ca45b043b": ("CRCL•Arc", "CRCL"),
           "0x6505506540dc99f7366316b10e9cf1a584cbd42a": ("NVDA•Arc", "NVDA")}


def _transfer_grup() -> pd.DataFrame:
    fs = [_dir() / f"arc_transfer_{n}.parquet" for n in ("grup", "grup2", "circarb")]
    t = pd.concat([pd.read_parquet(f) for f in fs if f.exists()], ignore_index=True).drop_duplicates(["tx", "li"])
    t = t[t.token != USDC_ARC].copy()   # USDC dicatat sekali lewat log native 0xfff..fe
    tok = pd.read_parquet(_dir() / "arc_token.parquet").set_index("alamat")
    dec = t.token.map(tok.decimals).where(t.token != NATIVE_ARC, 18).fillna(18).clip(lower=0)
    t["v"] = t.nilai / 10.0 ** dec
    t["sym"] = t.token.map(lambda a: "USDC" if a == NATIVE_ARC else TOK_ARC.get(a, (tok.symbol.get(a, "?"),))[0])
    return t.sort_values(["blok", "li"]).reset_index(drop=True)


def perdagangan_grup() -> pd.DataFrame:
    """Satu baris per (tx, bot/EOA grup, token non-USDC): perubahan USDC & token antara grup dan POOL."""
    from .chain_onchain import ke_waktu
    t = _transfer_grup()
    pools = set(pd.read_parquet(_dir() / "arc_semua_pool.parquet", columns=["pool"]).pool) | {PM}
    g_in, g_out = t.ke.isin(GRUP), t.dari.isin(GRUP)
    lawan = np.where(g_in & ~g_out, t.dari, np.where(g_out & ~g_in, t.ke, ""))
    t["lawan"] = lawan
    t["pelaku"] = np.where(g_in & ~g_out, t.ke, np.where(g_out & ~g_in, t.dari, ""))
    t["d"] = np.where(g_in, t.v, -t.v)
    tp = t[(t.lawan != "") & t.lawan.isin(pools)]
    rows = []
    for (tx, pel), g in tp.groupby(["tx", "pelaku"], sort=False):
        u = g[g.sym == "USDC"].d.sum()
        for (tok, sym), h in g[g.sym != "USDC"].groupby(["token", "sym"]):
            q = h.d.sum()
            if q == 0 or u == 0:
                continue
            rows.append({"tx": tx, "blok": int(g.blok.iloc[0]), "pelaku": pel, "nama": GRUP.get(pel, pel),
                         "pool": h.lawan.iloc[0], "token": tok, "sym": sym, "usdc": u, "qty": q, "harga": abs(u / q)})
    df = pd.DataFrame(rows)
    blk = pd.read_parquet(ONCHAIN / "arc_blok.parquet")["ts"]
    df["t"] = ke_waktu(df.blok.to_numpy(), blk)
    return df.sort_values("blok").reset_index(drop=True)


def fifo(tr: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    """Pasangkan jual dengan beli terdahulu (FIFO) per token -> untung per putaran (USDC)."""
    from collections import deque
    q: deque = deque()
    out = []
    for r in tr.itertuples():
        if r.qty > 0:
            q.append([r.qty, r.harga, r.t])
            continue
        amt = -r.qty
        while amt > 1e-12 and q:
            lot = q[0]
            m = min(lot[0], amt)
            out.append({"t_beli": lot[2], "t_jual": r.t, "qty": m, "beli": lot[1], "jual": r.harga,
                        "untung": m * (r.harga - lot[1])})
            lot[0] -= m
            amt -= m
            if lot[0] <= 1e-12:
                q.popleft()
        if amt > 1e-12:   # jual token yang tidak dibeli lewat pool (mis. hasil transfer masuk)
            out.append({"t_beli": pd.NaT, "t_jual": r.t, "qty": amt, "beli": np.nan, "jual": r.harga, "untung": np.nan})
    sisa = sum(x[0] for x in q)
    biaya = sum(x[0] * x[1] for x in q)
    return pd.DataFrame(out), sisa, biaya


# ---------------------------------------------------------------- tahap 7: potret sekarang
S_SLOT0_V4, S_LIQ_V4 = "0xc815641c", "0xfa6793d5"
S_SLOT0, S_LIQ, S_GLOBAL, S_RES = "0x3850c7bd", "0x1a686502", "0xe76c01e4", "0x0902f1ac"
Q96 = 2.0 ** 96
USD_SAMA = {"arc": {"0x3600000000000000000000000000000000000000", "0x0000000000000000000000000000000000000000"}}


def harga_eth() -> float:
    import urllib.request
    try:
        with urllib.request.urlopen("https://data-api.binance.vision/api/v3/ticker/price?symbol=ETHUSDT", timeout=20) as r:
            return float(json.loads(r.read())["price"])
    except Exception:  # noqa: BLE001
        return float("nan")


def _status_pool(net: str, pools: pd.DataFrame) -> pd.DataFrame:
    """sqrtP / L (v3, v4, Algebra) atau cadangan (v2) tiap pool lewat Multicall3 (eth_call saja)."""
    calls, idx = [], []
    for i, r in enumerate(pools.itertuples()):
        if r.jenis == "v4":
            if r.emitter != PM:
                continue
            pid = r.pool[2:].rjust(64, "0")
            calls += [(STATE_VIEW, S_SLOT0_V4 + pid), (STATE_VIEW, S_LIQ_V4 + pid)]
        elif r.jenis in ("v3", "slip"):
            calls += [(r.pool, S_SLOT0), (r.pool, S_LIQ)]
        elif r.jenis in ("alg", "algc"):
            calls += [(r.pool, S_GLOBAL), (r.pool, S_LIQ)]
        elif r.jenis in ("v2", "solid", "aero"):
            calls += [(r.pool, S_RES), (r.pool, S_RES)]
        else:
            continue
        idx.append(i)
    res = multicall_banyak(net, calls, chunk=400)
    out = pools.copy()
    for c in ("sqrtp", "L", "r0", "r1", "lpfee"):
        out[c] = np.nan
    sq, L, r0, r1, lf = (np.full(len(out), np.nan) for _ in range(5))
    jen = out.jenis.to_numpy()
    for k, i in enumerate(idx):
        a, b = res[2 * k], res[2 * k + 1]
        if not a or len(a) < 66:
            continue
        try:
            if jen[i] in ("v2", "solid", "aero"):
                r0[i], r1[i] = float(int(a[2:66], 16)), float(int(a[66:130], 16))
            else:
                sq[i] = float(int(a[2:66], 16))
                if jen[i] == "v4" and len(a) >= 2 + 64 * 4:
                    lf[i] = float(int(a[2 + 64 * 3: 2 + 64 * 4], 16))
                if b and len(b) >= 66:
                    L[i] = float(int(b[2:66], 16))
        except ValueError:
            continue
    out["sqrtp"], out["L"], out["r0"], out["r1"], out["lpfee"] = sq, L, r0, r1, lf
    return out


QUOTER_V4 = "0x8dc178efb8111bb0973dd9d722ebeff267c98f94"   # V4Quoter resmi (sama di kedua chain)
S_QUOTE_V4 = "0xaa9d21cb"
S_TICKBMP, S_TICKS, S_BAL = "0x5339c296", "0xf30dba93", "0x70a08231"   # tickBitmap(int16), ticks(int24), balanceOf


def _q_v4(net: str, legs: list[tuple]) -> list[float]:
    """V4Quoter.quoteExactInputSingle lewat Multicall3 (eth_call). leg = (c0, c1, fee, ts, hooks, zeroForOne, amt)."""
    from eth_abi import decode, encode
    calls = []
    for c0, c1, fee, ts, hooks, z, amt in legs:
        key = (c0, c1, int(fee), int(ts), hooks or "0x" + "0" * 40)
        calls.append((QUOTER_V4, S_QUOTE_V4 + encode(["((address,address,uint24,int24,address),bool,uint128,bytes)"],
                                                     [(key, bool(z), int(amt), b"")]).hex()))
    res = multicall_banyak(net, calls, chunk=60)
    out = []
    for r in res:
        try:
            out.append(float(decode(["uint256", "uint256"], bytes.fromhex(r[2:]))[0]) if r else 0.0)
        except Exception:  # noqa: BLE001
            out.append(0.0)
    return out


def _v3_ticks(net: str, pools: pd.DataFrame) -> dict:
    """liquidityNet tiap tick terinisialisasi di sekitar harga sekarang (±4 kata bitmap) untuk simulasi swap v3."""
    from eth_abi import decode, encode
    calls, meta = [], []
    for r in pools.itertuples():
        comp = int(np.floor(r.tick / r.ts))
        w0 = comp >> 8
        for w in range(w0 - 4, w0 + 5):
            calls.append((r.pool, S_TICKBMP + encode(["int16"], [max(min(w, 32767), -32768)]).hex()))
            meta.append((r.pool, w, r.ts))
    res = multicall_banyak(net, calls, chunk=300)
    want = []
    for (pool, w, ts), x in zip(meta, res):
        if not x or len(x) < 66:
            continue
        bm = int(x[2:66], 16)
        while bm:
            bit = (bm & -bm).bit_length() - 1
            want.append((pool, ((w << 8) + bit) * ts))
            bm &= bm - 1
    calls = [(pool, S_TICKS + encode(["int24"], [t]).hex()) for pool, t in want]
    res = multicall_banyak(net, calls, chunk=300)
    out: dict = {}
    for (pool, t), x in zip(want, res):
        if x and len(x) >= 130:
            out.setdefault(pool, {})[t] = float(decode(["int128"], bytes.fromhex(x[66:130]))[0])
    return out


def _v3_sim(amt: float, z: bool, sq: float, L: float, tick: int, fee: float, net_ticks: dict) -> float:
    """Simulasi swap exact-input Uniswap v3 (satuan mentah, float): lintas tick memakai liquidityNet."""
    out = 0.0
    rem = amt
    ticks = sorted(net_ticks)
    sqp = sq / Q96
    for _ in range(200):
        if rem <= 0 or L <= 0:
            break
        if z:   # token0 masuk, harga turun -> tick terinisialisasi berikutnya <= tick
            nxt = [t for t in ticks if t <= tick]
            tn = nxt[-1] if nxt else None
        else:
            nxt = [t for t in ticks if t > tick]
            tn = nxt[0] if nxt else None
        sq_t = 1.0001 ** (tn / 2) if tn is not None else (1e-30 if z else 1e30)
        a_eff = rem * (1 - fee)
        if z:
            need = L * (1 / sq_t - 1 / sqp)          # token0 untuk sampai batas
            if a_eff < need:
                sq_new = 1 / (1 / sqp + a_eff / L)
                out += L * (sqp - sq_new)
                rem = 0
                break
            out += L * (sqp - sq_t)
            rem -= need / (1 - fee)
            sqp = sq_t
            L -= net_ticks.get(tn, 0.0)
            tick = tn - 1
        else:
            need = L * (sq_t - sqp)                  # token1 untuk sampai batas
            if a_eff < need:
                sq_new = sqp + a_eff / L
                out += L * (1 / sqp - 1 / sq_new)
                rem = 0
                break
            out += L * (1 / sqp - 1 / sq_t)
            rem -= need / (1 - fee)
            sqp = sq_t
            L += net_ticks.get(tn, 0.0)
            tick = tn
        if tn is None:
            break
    return max(out, 0.0)


def _v2_out(amt: float, rin: float, rout: float, fee: float = 0.003) -> float:
    a = amt * (1 - fee)
    return rout * a / (rin + a) if rin > 0 and rout > 0 else 0.0


def potret(net: str, gas_usd: float | None = None, maks_grup: int = 400) -> pd.DataFrame:
    """Selisih harga antar pool untuk aset yang punya >= 2 pool dengan quote USD yang sama (Arc: USDC native &
    ERC-20 dianggap satu — saldonya sama) + untung bersih pulang-pergi $3/$25/$100 (beli di pool termurah, jual di
    termahal) dengan kuotasi PERSIS: v4 = V4Quoter resmi (termasuk hook), v3 = simulasi lintas tick dari tickBitmap,
    v2 = rumus produk-konstan cadangan nyata (fee 0,3% diasumsikan). Gas 2 swap ikut dikurangkan."""
    pools = pd.read_parquet(_dir() / f"{net}_semua_pool.parquet",
                            columns=["jenis", "emitter", "blok", "pool", "c0", "c1", "fee", "ts", "hooks"])
    pools = pools.drop_duplicates("pool")
    tok = pd.read_parquet(_dir() / f"{net}_token.parquet").set_index("alamat")
    resmi_usd = {"arc": {USDC_ARC, "0x" + "0" * 40}, "robinhood": {"0x5fc5360d0400a0fd4f2af552add042d716f1d168"}}[net]
    q0, q1 = pools.c0.isin(resmi_usd), pools.c1.isin(resmi_usd)
    pools = pools[q0 ^ q1].copy()
    pools["aset"] = np.where(pools.c0.isin(resmi_usd), pools.c1, pools.c0)
    pools["quote"] = np.where(pools.c0.isin(resmi_usd), pools.c0, pools.c1)
    n = pools.groupby("aset").pool.transform("size")
    pools = pools[(n >= 2) & pools.jenis.isin(["v4", "v3", "slip", "v2", "solid", "aero"])]
    pools = pools[(pools.jenis != "v4") | (pools.emitter == PM)]
    print(f"{net}: {len(pools):,} pool dalam {pools.aset.nunique():,} aset (>= 2 pool, quote USD resmi)", flush=True)
    st = _status_pool(net, pools)
    st["d0"] = st.c0.map(tok.decimals).where(st.c0 != "0x" + "0" * 40, 18).fillna(18).clip(lower=0).astype(int)
    st["d1"] = st.c1.map(tok.decimals).where(st.c1 != "0x" + "0" * 40, 18).fillna(18).clip(lower=0).astype(int)
    v2 = st.jenis.isin(["v2", "solid", "aero"]).to_numpy()
    sq = st.sqrtp.to_numpy() / Q96
    p01 = np.where(v2, (st.r1 / 10.0 ** st.d1) / (st.r0 / 10.0 ** st.d0), sq ** 2 * 10.0 ** (st.d0 - st.d1))
    usd0 = st.c0.isin(resmi_usd).to_numpy()
    st["harga"] = np.where(usd0, 1 / p01, p01)        # USD per aset (mid)
    st["tick"] = np.where(v2, 0, np.floor(np.log(np.where(sq > 0, sq, 1.0) ** 2) / np.log(1.0001))).astype(int)
    # kedalaman: USD untuk menggeser harga 2% (v3/v4: likuiditas aktif; v2: cadangan)
    usd_dec = np.where(usd0, st.d0, st.d1)
    vres_usd = np.where(v2, np.where(usd0, st.r0, st.r1), np.where(usd0, st.L / np.where(sq > 0, sq, np.nan), st.L * sq))
    st["dalam2"] = vres_usd / 10.0 ** usd_dec * (np.sqrt(1.02) - 1)
    st = st[np.isfinite(st.harga) & (st.harga > 0) & (st.dalam2 > 0.2)].copy()
    g = gas_usd if gas_usd is not None else gas_swap_usd(net)
    # kandidat: aset dengan >= 2 pool hidup, urut selisih max/min
    agg = st.groupby("aset").harga.agg(["min", "max", "size"])
    agg = agg[agg["size"] >= 2]
    agg["sel"] = agg["max"] / agg["min"] - 1
    calon = agg.sort_values("sel", ascending=False)
    calon = calon[calon.sel > 0.003].head(maks_grup)
    st = st[st.aset.isin(calon.index)].copy()
    v3p = st[st.jenis.isin(["v3", "slip"])].assign(ts=lambda d: d.ts.clip(lower=1))
    ticks = _v3_ticks(net, v3p) if len(v3p) else {}
    rows, legs4, idx4 = [], [], []
    SIZES = (3, 25, 100)

    def leg(r, z, amt):
        """Hasil keluar (mentah) satu leg; v4 ditunda ke Quoter (dikumpulkan)."""
        f = (r.lpfee if np.isfinite(r.lpfee) else r.fee) / 1e6 if r.jenis == "v4" else r.fee / 1e6
        if r.jenis in ("v3", "slip"):
            return _v3_sim(amt, z, r.sqrtp, r.L, int(r.tick), f, ticks.get(r.pool, {}))
        if r.jenis in ("v2", "solid", "aero"):
            return _v2_out(amt, r.r0 if z else r.r1, r.r1 if z else r.r0)
        return None

    plan = []
    for aset, grp in st.groupby("aset"):
        grp = grp.sort_values("harga")
        a, b = grp.iloc[0], grp.iloc[-1]
        plan.append((aset, a, b, len(grp)))
    # tahap 1: leg beli (USD -> aset) di pool termurah
    beli = {}
    for aset, a, b, n_ in plan:
        z_a = a.c0 in resmi_usd           # bayar token0 (USD) -> zeroForOne
        dq = a.d0 if z_a else a.d1
        for usd in SIZES:
            amt = usd * 10.0 ** dq
            o = leg(a, z_a, amt)
            if o is None:
                legs4.append((a.c0, a.c1, a.fee, a.ts, a.hooks, z_a, amt))
                idx4.append(("beli", aset, usd))
            else:
                beli[(aset, usd)] = o
    for k, o in zip(idx4, _q_v4(net, legs4)):
        beli[(k[1], k[2])] = o
    legs4, idx4 = [], []
    jual = {}
    for aset, a, b, n_ in plan:
        z_b = b.c0 not in resmi_usd       # jual aset: aset token0 -> zeroForOne
        for usd in SIZES:
            amt = beli.get((aset, usd), 0.0)
            if amt <= 0:
                jual[(aset, usd)] = 0.0
                continue
            o = leg(b, z_b, amt)
            if o is None:
                legs4.append((b.c0, b.c1, b.fee, b.ts, b.hooks, z_b, amt))
                idx4.append(("jual", aset, usd))
            else:
                jual[(aset, usd)] = o
    for k, o in zip(idx4, _q_v4(net, legs4)):
        jual[(k[1], k[2])] = o
    for aset, a, b, n_ in plan:
        dq_b = b.d0 if b.c0 in resmi_usd else b.d1
        r = {"net": net, "aset": aset, "simbol": tok.symbol.get(aset, "?"), "nama": tok.name.get(aset, ""),
             "n_pool": n_, "pool_beli": a.pool, "jenis_beli": a.jenis, "fee_beli": a.fee, "hooks_beli": a.hooks,
             "harga_beli": a.harga, "dalam2_beli": a.dalam2, "pool_jual": b.pool, "jenis_jual": b.jenis,
             "fee_jual": b.fee, "hooks_jual": b.hooks, "harga_jual": b.harga, "dalam2_jual": b.dalam2,
             "selisih_mid": b.harga / a.harga - 1, "gas_2swap": 2 * g}
        for usd in SIZES:
            r[f"untung_{usd}"] = jual.get((aset, usd), 0.0) / 10.0 ** dq_b - usd - 2 * g
        rows.append(r)
    df = pd.DataFrame(rows)
    df["untung_terbaik"] = df[[f"untung_{u}" for u in SIZES]].max(axis=1)
    df = df.sort_values("untung_terbaik", ascending=False)
    df.to_parquet(_dir() / f"{net}_potret.parquet")
    keep = ["jenis", "pool", "c0", "c1", "fee", "ts", "hooks", "aset", "quote", "sqrtp", "L", "r0", "r1", "lpfee",
            "harga", "dalam2"]
    st[keep].to_parquet(_dir() / f"{net}_potret_pool.parquet")
    return df


def potret_weth(net: str) -> pd.DataFrame:
    """Semua pool token bersimbol WETH/ETH ber-quote USD (resmi atau bukan): harga mid vs ETH Binance saat ini."""
    k = pd.read_parquet(_dir() / f"{net}_kandidat.parquet")
    k = k[k.kelas == "WETH/USD"].drop_duplicates("pool")
    k = k[(k.jenis != "v4") | (k.emitter == PM)]
    st = _status_pool(net, k)
    v2 = st.jenis.isin(["v2", "solid", "aero"]).to_numpy()
    sq = st.sqrtp.to_numpy() / Q96
    d0, d1 = st.d0.clip(lower=0).astype(float), st.d1.clip(lower=0).astype(float)
    p01 = np.where(v2, (st.r1 / 10.0 ** d1) / (st.r0 / 10.0 ** d0), sq ** 2 * 10.0 ** (d0 - d1))
    usd0 = st.s0.map(_isusd).to_numpy()
    st["harga"] = np.where(usd0, 1 / p01, p01)
    usd_dec = np.where(usd0, d0, d1)
    vres = np.where(v2, np.where(usd0, st.r0, st.r1), np.where(usd0, st.L / np.where(sq > 0, sq, np.nan), st.L * sq))
    st["dalam2"] = vres / 10.0 ** usd_dec * (np.sqrt(1.02) - 1)
    eth = harga_eth()
    st["eth_binance"] = eth
    st["selisih"] = st.harga / eth - 1
    st["weth"] = np.where(usd0, st.c1, st.c0)
    st["usd"] = np.where(usd0, st.c0, st.c1)
    st = st[np.isfinite(st.harga) & (st.harga > 0)]
    st.drop(columns=[c for c in ("n0", "n1", "sqrtp0", "tx") if c in st]).to_parquet(_dir() / f"{net}_potret_weth.parquet")
    return st


def _usd_resmi_tambahan(net: str) -> set:
    return set()


def gas_swap_usd(net: str, n: int = 20) -> float:
    """Biaya gas satu swap sekarang = median gasUsed (receipt swap terbaru) x eth_gasPrice (x harga ETH di Robinhood)."""
    top = head(net)
    lg = _logs_satu(net, {"address": PM, "topics": [T_SWAP]}, top - (2000 if net == "arc" else 20000), top)
    txs = list(dict.fromkeys(x["transactionHash"] for x in lg))[-n:]
    gu = []
    for h in txs:
        try:
            rc = rpc(net, "eth_getTransactionReceipt", [h])
            gu.append(int(rc["gasUsed"], 16))
        except Exception:  # noqa: BLE001
            pass
    gp = int(rpc(net, "eth_gasPrice", []), 16)
    med = float(np.median(gu)) if gu else 150_000.0
    unit = 1.0 if net == "arc" else harga_eth()
    usd = med * gp / 1e18 * unit
    print(f"{net}: gas swap median {med:,.0f} unit (n {len(gu)}), gasPrice {gp / 1e9:.4f} gwei -> ${usd:.5f}/swap")
    GAS_INFO[net] = {"gas_used_median": med, "gas_price_wei": gp, "usd_per_swap": usd, "n": len(gu)}
    return usd


GAS_INFO: dict = {}


if __name__ == "__main__":
    tahap = sys.argv[1] if len(sys.argv) > 1 else "semua"
    nets = [sys.argv[2]] if len(sys.argv) > 2 else ["arc", "robinhood"]
    for n in nets:
        if tahap in ("pabrik", "semua"):
            pabrik(n)
        if tahap in ("token", "semua"):
            token(n)
        if tahap in ("kandidat", "semua"):
            kandidat(n)
        if tahap in ("swap", "semua"):
            # Robinhood: ratusan ribu pool meme berpasangan WETH -> hanya pool ber-quote USD & semua pool CRCL
            swap_kandidat(n, ("WETH/USD", "CRCL/USD", "CRCL/lain") if n == "robinhood" else
                          ("WETH/USD", "CRCL/USD", "CRCL/lain", "WETH/lain"))
