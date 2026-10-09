"""JSON-RPC minimal (urllib, tanpa web3) + pembaca event."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class RpcError(RuntimeError):
    pass


class Rpc:
    def __init__(self, url: str, chain_id: int | None = None, timeout: float = 30):
        self.url, self.timeout = url, timeout
        self.host = urlsplit(url).hostname or "?"     # galat hanya menyebut host (URL bisa memuat kunci API)
        if chain_id is not None:
            got = int(self.call("eth_chainId", []), 16)
            if got != chain_id:
                raise RpcError(f"chain id RPC {got} != konfigurasi {chain_id} — cek URL RPC")

    def call(self, method: str, params: list, tries: int = 5):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        err = None
        for k in range(tries):
            try:
                req = urllib.request.Request(self.url, data=body, headers={
                    "content-type": "application/json", "user-agent": "Mozilla/5.0 token-bot"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    d = json.loads(r.read())
            except urllib.error.HTTPError as e:
                err = e
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(0.5 * (k + 1))
                    continue
                raise RpcError(f"HTTP {e.code} {self.host}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                err = e
                time.sleep(0.5 * (k + 1))
                continue
            if "error" in d:
                raise RpcError(str(d["error"].get("message", d["error"])))
            return d["result"]
        raise RpcError(f"gagal {method} di {self.host}: {str(err).replace(self.url, self.host)[:120]}")

    def eth_call(self, to: str, data: bytes | str, block: str = "latest", sender: str | None = None,
                 value: int = 0) -> bytes:
        tx = {"to": to, "data": data if isinstance(data, str) else "0x" + data.hex()}
        if sender:
            tx["from"] = sender
        if value:
            tx["value"] = hex(value)
        return bytes.fromhex(self.call("eth_call", [tx, block])[2:])

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def get_logs(self, address, topics: list, b0: int, b1: int, span: int = 5_000) -> list[dict]:
        out, cur = [], b0
        while cur <= b1:
            hi = min(cur + span - 1, b1)
            try:
                out += self.call("eth_getLogs", [{"address": address, "topics": topics,
                                                  "fromBlock": hex(cur), "toBlock": hex(hi)}])
            except RpcError as e:
                if span > 100 and any(x in str(e).lower() for x in ("range", "allowed", "too many", "limit")):
                    span //= 2
                    continue
                raise
            cur = hi + 1
        return out
