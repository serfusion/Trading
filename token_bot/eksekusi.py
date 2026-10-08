"""Eksekusi swap NYATA (hanya bila --live + konfigurasi live.aktif + env TOKEN_BOT_PK). Belum pernah dijalankan dengan
dana nyata dari sesi riset (tidak ada dompet) -> wajib uji nominal kecil dulu.

Pengaman: (1) simulasi eth_call transaksi persis sebelum dikirim, batal bila revert; (2) amountOutMinimum = kuotasi x
(1 - max_slippage) -> kalau harga bergerak lebih jauh transaksi gagal (bukan rugi besar); (3) batas $/trade, total,
jumlah trade per hari; (4) hanya token di daftar putih konfigurasi.
v4: Universal Router perintah V4_SWAP (0x10) + aksi SWAP_EXACT_IN_SINGLE/SETTLE_ALL/TAKE_ALL, izin lewat Permit2.
v3: SwapRouter02.exactInputSingle.
"""
from __future__ import annotations

import os
import time

from eth_abi import encode
from eth_utils import to_checksum_address

from .dex import NOL, Pool, sel
from .rpc import Rpc, RpcError

MAX256 = (1 << 256) - 1
MAX160 = (1 << 160) - 1
S_APPROVE = sel("approve(address,uint256)")
S_ALLOW = sel("allowance(address,address)")
S_P2_APPROVE = sel("approve(address,address,uint160,uint48)")
S_P2_ALLOW = sel("allowance(address,address,address)")
S_UR_EXEC = sel("execute(bytes,bytes[],uint256)")
S_V3_SWAP = sel("exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))")
V4_SWAP = 0x10
A_SWAP_EXACT_IN_SINGLE, A_SETTLE_ALL, A_TAKE_ALL = 0x06, 0x0C, 0x0F


class Dompet:
    def __init__(self, rpc: Rpc, chain_id: int):
        from eth_account import Account  # hanya diperlukan untuk mode live

        pk = os.environ.get("TOKEN_BOT_PK", "")
        if not pk:
            raise RuntimeError("mode live butuh env TOKEN_BOT_PK (private key dompet KHUSUS bot, isi saldo kecil)")
        self.acct = Account.from_key(pk)
        self.addr = self.acct.address
        self.rpc, self.chain_id = rpc, chain_id

    def _fees(self) -> tuple[int, int]:
        blk = self.rpc.call("eth_getBlockByNumber", ["latest", False])
        base = int(blk.get("baseFeePerGas", "0x0"), 16)
        try:
            tip = int(self.rpc.call("eth_maxPriorityFeePerGas", []), 16)
        except RpcError:
            tip = 0
        return base * 2 + tip, tip

    def kirim(self, to: str, data: bytes, value: int = 0, simulasi: bool = True) -> str:
        tx = {"from": self.addr, "to": to, "data": "0x" + data.hex(), "value": hex(value)}
        if simulasi:
            try:
                self.rpc.call("eth_call", [tx, "latest"])
            except RpcError as e:
                raise RpcError(f"simulasi gagal (transaksi TIDAK dikirim): {e}") from e
        gas = int(int(self.rpc.call("eth_estimateGas", [tx]), 16) * 1.3)
        mf, tip = self._fees()
        nonce = int(self.rpc.call("eth_getTransactionCount", [self.addr, "pending"]), 16)
        signed = self.acct.sign_transaction({"chainId": self.chain_id, "nonce": nonce, "to": to_checksum_address(to),
                                             "value": value, "data": data, "gas": gas, "maxFeePerGas": mf,
                                             "maxPriorityFeePerGas": tip, "type": 2})
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        h = self.rpc.call("eth_sendRawTransaction", ["0x" + raw.hex()])
        for _ in range(120):
            rc = self.rpc.call("eth_getTransactionReceipt", [h])
            if rc:
                if int(rc["status"], 16) != 1:
                    raise RpcError(f"transaksi {h} GAGAL (revert)")
                return h
            time.sleep(0.5)
        raise RpcError(f"transaksi {h} belum masuk blok dalam 60 dtk")

    def _izin(self, token: str, spender: str, amount: int) -> None:
        cur = int.from_bytes(self.rpc.eth_call(token, S_ALLOW + encode(["address", "address"], [self.addr, spender])), "big")
        if cur < amount:
            self.kirim(token, S_APPROVE + encode(["address", "uint256"], [to_checksum_address(spender), MAX256]))

    def swap_v4(self, cfg: dict, pool: Pool, token_in: str, amount_in: int, min_out: int) -> str:
        zero_for_one = token_in.lower() == pool.c0.lower()
        c_in, c_out = (pool.c0, pool.c1) if zero_for_one else (pool.c1, pool.c0)
        ur, p2 = cfg["universal_router"], cfg["permit2"]
        value = 0
        if int(c_in, 16) == 0:
            value = amount_in
        else:
            self._izin(c_in, p2, amount_in)
            out = self.rpc.eth_call(p2, S_P2_ALLOW + encode(["address", "address", "address"],
                                                            [self.addr, to_checksum_address(c_in), to_checksum_address(ur)]))
            amt, exp = int.from_bytes(out[:32], "big"), int.from_bytes(out[32:64], "big")
            if amt < amount_in or exp < time.time() + 3600:
                self.kirim(p2, S_P2_APPROVE + encode(["address", "address", "uint160", "uint48"],
                                                     [to_checksum_address(c_in), to_checksum_address(ur), MAX160,
                                                      int(time.time()) + 30 * 86400]))
        actions = bytes([A_SWAP_EXACT_IN_SINGLE, A_SETTLE_ALL, A_TAKE_ALL])
        params = [
            encode(["((address,address,uint24,int24,address),bool,uint128,uint128,bytes)"],
                   [(pool.key, zero_for_one, amount_in, min_out, b"")]),
            encode(["address", "uint256"], [to_checksum_address(c_in), amount_in]),
            encode(["address", "uint256"], [to_checksum_address(c_out), min_out]),
        ]
        inp = encode(["bytes", "bytes[]"], [actions, params])
        data = S_UR_EXEC + encode(["bytes", "bytes[]", "uint256"], [bytes([V4_SWAP]), [inp], int(time.time()) + 120])
        return self.kirim(ur, data, value=value)

    def swap_v3(self, cfg: dict, pool: Pool, token_in: str, amount_in: int, min_out: int) -> str:
        router = cfg["swap_router02"]
        t_out = pool.c1 if token_in.lower() == pool.c0.lower() else pool.c0
        if int(token_in, 16) == 0 or int(t_out, 16) == 0:
            raise RpcError("v3 tidak memakai ETH native — pakai WETH")
        self._izin(token_in, router, amount_in)
        data = S_V3_SWAP + encode(["(address,address,uint24,address,uint256,uint256,uint160)"],
                                  [(to_checksum_address(token_in), to_checksum_address(t_out), pool.fee, self.addr,
                                    amount_in, min_out, 0)])
        return self.kirim(router, data)

    def swap(self, cfg: dict, pool: Pool, token_in: str, amount_in: int, min_out: int) -> str:
        if pool.ver == 4:
            return self.swap_v4(cfg, pool, token_in, amount_in, min_out)
        return self.swap_v3(cfg, pool, token_in, amount_in, min_out)


__all__ = ["Dompet", "NOL"]
