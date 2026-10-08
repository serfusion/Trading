"""Pool Uniswap v4 / v3: harga spot, kuotasi beli/jual (Quoter resmi), cari PoolKey dari event Initialize."""
from __future__ import annotations

from dataclasses import dataclass, field

from eth_abi import decode, encode
from eth_utils import keccak, to_checksum_address

from .rpc import Rpc, RpcError

T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
NOL = "0x0000000000000000000000000000000000000000"


def sel(sig: str) -> bytes:
    return keccak(text=sig)[:4]


S_V4_QUOTE = sel("quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))")
S_V3_QUOTE = sel("quoteExactInputSingle((address,address,uint256,uint24,uint160))")
S_SLOT0_V4 = sel("getSlot0(bytes32)")
S_LIQ_V4 = sel("getLiquidity(bytes32)")
S_SLOT0_V3 = sel("slot0()")
S_LIQ_V3 = sel("liquidity()")
S_DEC = sel("decimals()")
S_SYM = sel("symbol()")


@dataclass
class Pool:
    ver: int                      # 4 = Uniswap v4 (PoolManager), 3 = Uniswap v3 (kontrak pool)
    id: str                       # v4: poolId bytes32; v3: alamat pool
    c0: str
    c1: str
    fee: int
    tick_spacing: int = 0
    hooks: str = NOL
    d0: int = 18
    d1: int = 18
    nama: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> tuple:
        return (to_checksum_address(self.c0), to_checksum_address(self.c1), self.fee, self.tick_spacing,
                to_checksum_address(self.hooks))

    def pool_id(self) -> str:
        """Hitung ulang poolId v4 = keccak(abi.encode(PoolKey)) -> cek konfigurasi."""
        return "0x" + keccak(encode(["address", "address", "uint24", "int24", "address"], list(self.key))).hex()


def decimals(rpc: Rpc, token: str) -> int:
    if int(token, 16) == 0:
        return 18
    return decode(["uint8"], rpc.eth_call(token, S_DEC))[0]


def symbol(rpc: Rpc, token: str) -> str:
    if int(token, 16) == 0:
        return "NATIVE"
    try:
        return decode(["string"], rpc.eth_call(token, S_SYM))[0]
    except Exception:  # noqa: BLE001
        return "?"


def cari_v4(rpc: Rpc, pool_manager: str, pool_id: str, b0: int, b1: int | None = None, span: int = 5_000) -> Pool:
    """PoolKey dari event Initialize (topic1 = poolId)."""
    b1 = b1 or rpc.block_number()
    lg = rpc.get_logs(pool_manager, [T_INIT, pool_id.lower()], b0, b1, span=span)
    if not lg:
        raise RpcError(f"Initialize {pool_id} tidak ditemukan di blok {b0}-{b1}")
    t, d = lg[0]["topics"], bytes.fromhex(lg[0]["data"][2:])
    fee, ts, hooks, _sqrtp, _tick = decode(["uint24", "int24", "address", "uint160", "int24"], d)
    c0, c1 = "0x" + t[2][-40:], "0x" + t[3][-40:]
    p = Pool(4, pool_id.lower(), c0, c1, fee, ts, hooks)
    p.d0, p.d1 = decimals(rpc, c0), decimals(rpc, c1)
    p.extra["blok"] = int(lg[0]["blockNumber"], 16)
    if p.pool_id() != pool_id.lower():
        raise RpcError("poolId hasil hitung tidak sama -> data event aneh")
    return p


def sqrtp_harga(sqrtp: int, d0: int, d1: int) -> float:
    """Harga token0 dalam token1 (satuan manusia)."""
    return (sqrtp / 2 ** 96) ** 2 * 10 ** (d0 - d1)


def spot(rpc: Rpc, pool: Pool, state_view: str | None = None) -> tuple[float, int]:
    """(harga token0 dalam token1, likuiditas aktif)."""
    if pool.ver == 4:
        sq, _tick, _pf, _lf = decode(["uint160", "int24", "uint24", "uint24"],
                                     rpc.eth_call(state_view, S_SLOT0_V4 + bytes.fromhex(pool.id[2:])))
        liq = decode(["uint128"], rpc.eth_call(state_view, S_LIQ_V4 + bytes.fromhex(pool.id[2:])))[0]
    else:
        sq = decode(["uint160"], rpc.eth_call(pool.id, S_SLOT0_V3)[:32])[0]
        liq = decode(["uint128"], rpc.eth_call(pool.id, S_LIQ_V3))[0]
    return sqrtp_harga(sq, pool.d0, pool.d1), liq


def quote(rpc: Rpc, pool: Pool, token_in: str, amount_in: int, quoter: str) -> int:
    """Jumlah keluar (satuan terkecil) untuk menukar `amount_in` token_in -> token lain lewat Quoter resmi.
    Sudah termasuk fee pool, dampak harga (slippage karena likuiditas) dan efek hook v4."""
    zero_for_one = token_in.lower() == pool.c0.lower()
    if pool.ver == 4:
        data = S_V4_QUOTE + encode(["((address,address,uint24,int24,address),bool,uint128,bytes)"],
                                   [(pool.key, zero_for_one, amount_in, b"")])
        out = rpc.eth_call(quoter, data)
        return decode(["uint256", "uint256"], out)[0]
    t_out = pool.c1 if zero_for_one else pool.c0
    data = S_V3_QUOTE + encode(["(address,address,uint256,uint24,uint160)"],
                               [(to_checksum_address(token_in), to_checksum_address(t_out), amount_in, pool.fee, 0)])
    out = rpc.eth_call(quoter, data)
    return decode(["uint256", "uint160", "uint32", "uint256"], out)[0]


def cari_v3(rpc: Rpc, address: str) -> Pool:
    """Pool v3: token0/token1/fee dibaca dari kontrak pool."""
    t0 = "0x" + rpc.eth_call(address, sel("token0()")).hex()[-40:]
    t1 = "0x" + rpc.eth_call(address, sel("token1()")).hex()[-40:]
    fee = decode(["uint24"], rpc.eth_call(address, sel("fee()")))[0]
    p = Pool(3, address.lower(), t0, t1, fee)
    p.d0, p.d1 = decimals(rpc, t0), decimals(rpc, t1)
    return p
