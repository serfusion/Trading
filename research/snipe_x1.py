"""🎯 Snipe token baru di X1 (chain SVM, koin XNT) — python -m research.snipe_x1 unduh|tx|bar|uji|kmn

Permintaan pengguna 10 Okt 2026 (screenshot bot Telegram: token KMN dibeli 2 XNT → "Value 435 XNT, PnL 21.652%";
klaim tutorial "chain yang tidak banyak orang tahu, $1 jadi $200+, tidak ada rugger, snipe langsung dapat besar").

X1 = L1 kompatibel Solana (SVM), mainnet 6 Okt 2025, koin XNT. DEX utama XDEX = fork Raydium CP-Swap (program
sEsYH97…b4fN, pool 637 byte, biaya swap 0,28%). DexScreener TIDAK mendukung X1; GeckoTerminal ada (x1-network) tetapi
tidak semua pool terindeks (KMN 404) → sumber kebenaran = RPC on-chain (rpc.mainnet.x1.xyz, 300 permintaan/5 dtk).

Data (semua on-chain kecuali bar harga):
* pools.json      : semua pool XDEX (getProgramAccounts) — vault, mint, pembuat, lp_supply, open_time.
* cadangan.json   : saldo vault SEKARANG (getMultipleAccounts) = likuiditas nyata yang bisa dijual hari ini.
* tanda/<pool>    : SEMUA tanda tangan transaksi pool (jumlah, waktu) + daftar 24 jam pertama.
* lp/<pool>       : event tambah/tarik likuiditas (tanda tangan LP mint; swap tidak menyentuh LP mint) + saldo vault.
* swap/<pool>     : transaksi 24 jam pertama (maks N per pool) → cadangan vault SETELAH tiap transaksi (harga & likuiditas
                    persis), pembayar biaya (siapa yang snipe), arah beli/jual.
* xnt_usd.json    : harga XNT/USDC.X per jam dari chart XDEX.
Jual disimulasikan memakai rumus x·y=k pada cadangan nyata saat itu (bukan "harga × jumlah" seperti PnL bot).
"""
from __future__ import annotations

import base64
import gzip
import json
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "snipe_x1"
OUT = ROOT / "docs" / "eksternal" / "hasil_snipe_x1.txt"
RPC = "https://rpc.mainnet.x1.xyz"
CPMM = "sEsYH97wqmfnkzHedjNcw3zyJdPvUmsa9AixhS4b4fN"
WXNT = "So11111111111111111111111111111111111111112"
USDC_X = "B69chRzqzDCmdB5WYB8NRu5Yv5ZA95ABiZcdzCgGm9Tq"  # USDC jembatan di X1 (pool WXNT/USDC.X terbesar)
XDEX = "https://api.xdex.xyz"
KMN = "CzgRKzLkBP52uXAzQh8Yu8vuMk37G8YY12vYj6EthRD8"
UA = {"User-Agent": "Mozilla/5.0 (riset)", "Content-Type": "application/json", "Accept": "application/json"}

# ----------------------------------------------------------------------------------------------------------- jaringan
_lock = threading.Lock()
_stamps: list[float] = []
RATE = 45  # permintaan per detik (batas publik 300/5 dtk = 60/dtk)


def _tunggu():
    while True:
        with _lock:
            now = time.time()
            while _stamps and now - _stamps[0] > 1:
                _stamps.pop(0)
            if len(_stamps) < RATE:
                _stamps.append(now)
                return
        time.sleep(0.02)


def rpc(method: str, params: list, tries: int = 8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        _tunggu()
        try:
            with urllib.request.urlopen(urllib.request.Request(RPC, data=body, headers=UA), timeout=60) as r:
                d = json.load(r)
            if "error" in d:
                raise RuntimeError(d["error"])
            return d["result"]
        except urllib.error.HTTPError as exc:
            time.sleep(float(exc.headers.get("Retry-After") or 2 * (i + 1)) if exc.code == 429 else 2 * (i + 1))
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"rpc gagal {method}")


def rpc_batch(method: str, params: list[list], tries: int = 8) -> list:
    """Satu permintaan HTTP berisi banyak panggilan JSON-RPC (jauh lebih cepat untuk getTransaction)."""
    body = json.dumps([{"jsonrpc": "2.0", "id": i, "method": method, "params": p}
                       for i, p in enumerate(params)]).encode()
    for i in range(tries):
        _tunggu()
        try:
            with urllib.request.urlopen(urllib.request.Request(RPC, data=body, headers=UA), timeout=120) as r:
                d = json.load(r)
            res = {x["id"]: x.get("result") for x in d}
            if any("error" in x for x in d):
                raise RuntimeError([x["error"] for x in d if "error" in x][:1])
            return [res.get(j) for j in range(len(params))]
        except urllib.error.HTTPError as exc:
            time.sleep(float(exc.headers.get("Retry-After") or 2 * (i + 1)) if exc.code == 429 else 2 * (i + 1))
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"rpc batch gagal {method}")


def get(url: str, tries: int = 6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = _B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def simpan(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(obj, f, separators=(",", ":"))


def muat(path: Path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------------------- pool
def parse_pool(addr: str, raw: bytes) -> dict:
    k = lambda o: b58(raw[o:o + 32])  # noqa: E731
    q = lambda o: struct.unpack_from("<Q", raw, o)[0]  # noqa: E731
    return {"pool": addr, "config": k(8), "creator": k(40), "vault0": k(72), "vault1": k(104), "lp_mint": k(136),
            "mint0": k(168), "mint1": k(200), "status": raw[329], "lp_dec": raw[330], "dec0": raw[331],
            "dec1": raw[332], "lp_supply": q(333), "fee0": q(341) + q(357), "fee1": q(349) + q(365),
            "open_time": q(373)}


def unduh_pool() -> list[dict]:
    res = rpc("getProgramAccounts", [CPMM, {"encoding": "base64", "filters": [{"dataSize": 637}]}])
    pools = [parse_pool(a["pubkey"], base64.b64decode(a["account"]["data"][0])) for a in res]
    cfg = {}
    for c in sorted({p["config"] for p in pools}):
        raw = base64.b64decode(rpc("getAccountInfo", [c, {"encoding": "base64"}])["value"]["data"][0])
        cfg[c] = struct.unpack_from("<Q", raw, 12)[0] / 1e6
    for p in pools:
        p["fee"] = cfg[p["config"]]
    tok = get(f"{XDEX}/api/xdex/swap/tokens?network=X1%20Mainnet")["data"]["tokens"]
    sym = {t["mint"]: t.get("symbol") for t in tok}
    for p in pools:
        p["sym0"], p["sym1"] = sym.get(p["mint0"]), sym.get(p["mint1"])
    simpan(DIR / "pools.json.gz", pools)
    print(f"{len(pools)} pool, konfigurasi biaya {cfg}")
    return pools


def unduh_cadangan(pools: list[dict]) -> dict:
    akun = sorted({p[k] for p in pools for k in ("vault0", "vault1", "lp_mint")})
    out = {}
    for i in range(0, len(akun), 100):
        res = rpc("getMultipleAccounts", [akun[i:i + 100], {"encoding": "base64"}])["value"]
        for a, v in zip(akun[i:i + 100], res):
            if v is None:
                out[a] = None
                continue
            raw = base64.b64decode(v["data"][0])
            out[a] = struct.unpack_from("<Q", raw, 64 if len(raw) >= 165 else 36)[0]  # akun token: jumlah; mint: supply
    simpan(DIR / "cadangan.json.gz", {"waktu": int(time.time()), "saldo": out})
    print(f"cadangan {len(out)} akun")
    return out


def _sigs(addr: str, batas_jam: float | None = None, maks_hal: int | None = None) -> dict:
    """Semua tanda tangan (baru → lama). Simpan jumlah + yang ≤ batas_jam sejak transaksi pertama.
    maks_hal: berhenti setelah N halaman (1.000/halaman) → "awal" kosong & "terpotong" = True."""
    semua, before, hal = [], None, 0
    while True:
        hal += 1
        if maks_hal and hal > maks_hal:
            return {"n": len(semua), "terpotong": True, "awal": [], "t0": 0, "n_err": 0, "t_akhir": 0}
        p = {"limit": 1000}
        if before:
            p["before"] = before
        res = rpc("getSignaturesForAddress", [addr, p])
        semua += [(r["signature"], r.get("blockTime") or 0, 1 if r.get("err") else 0, r["slot"]) for r in res]
        if len(res) < 1000:
            break
        before = res[-1]["signature"]
    semua.reverse()
    t0 = semua[0][1] if semua else 0
    awal = [s for s in semua if batas_jam is None or s[1] - t0 <= batas_jam * 3600]
    return {"n": len(semua), "n_err": sum(s[2] for s in semua), "t0": t0, "t_akhir": semua[-1][1] if semua else 0,
            "awal": awal, "jam_hari": np.bincount(  # aktivitas per hari sejak pembuatan (maks 400 hari)
                np.clip([(s[1] - t0) // 86400 for s in semua if not s[2]], 0, 399).astype(int),
                minlength=1).tolist() if semua else []}


def _tx(sig: str):
    return rpc("getTransaction", [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0,
                                        "commitment": "confirmed"}])


def _saldo_tx(res: dict, akun: list[str]) -> dict:
    """Saldo token akun tertentu sebelum/sesudah transaksi + pembayar biaya."""
    msg = res["transaction"]["message"]
    keys = list(msg["accountKeys"])
    la = res["meta"].get("loadedAddresses") or {}
    keys += la.get("writable", []) + la.get("readonly", [])
    pre = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"]) for b in res["meta"].get("preTokenBalances") or []}
    post = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"]) for b in res["meta"].get("postTokenBalances") or []}
    out = {"payer": keys[0], "t": res.get("blockTime"), "slot": res.get("slot"), "err": bool(res["meta"].get("err"))}
    for a in akun:
        if a in keys:
            i = keys.index(a)
            out[a] = (pre.get(i), post.get(i))
    return out


def unduh_tanda_lp(pools: list[dict], pekerja: int = 10) -> None:
    def satu(p):
        f_t, f_l = DIR / "tanda" / f"{p['pool']}.json.gz", DIR / "lp" / f"{p['pool']}.json.gz"
        if not f_t.exists():
            simpan(f_t, _sigs(p["pool"], batas_jam=24))
        if not f_l.exists():
            s = _sigs(p["lp_mint"])
            ev = []
            for sig, _t, err, _slot in s["awal"]:
                if err:
                    continue
                r = _tx(sig)
                if r:
                    ev.append({"sig": sig, **_saldo_tx(r, [p["vault0"], p["vault1"]])})
            simpan(f_l, ev)
        return p["pool"]

    t = time.time()
    with ThreadPoolExecutor(pekerja) as ex:
        for i, _ in enumerate(ex.map(satu, pools)):
            if i % 100 == 0:
                print(f"  tanda+lp {i}/{len(pools)} {time.time() - t:.0f} dtk", flush=True)


def unduh_swap(pools: list[dict], maks: int = 400, pekerja: int = 12) -> None:
    """Transaksi 24 jam pertama tiap pool (maks `maks` transaksi sukses pertama)."""
    def satu(p):
        f = DIR / "swap" / f"{p['pool']}.json.gz"
        if f.exists():
            return
        s = muat(DIR / "tanda" / f"{p['pool']}.json.gz")
        sigs = [x[0] for x in s["awal"] if not x[2]][:maks]
        rows = []
        opt = {"encoding": "json", "maxSupportedTransactionVersion": 0, "commitment": "confirmed"}
        for i in range(0, len(sigs), 40):
            part = sigs[i:i + 40]
            for sig, r in zip(part, rpc_batch("getTransaction", [[g, opt] for g in part])):
                if r:
                    rows.append({"sig": sig, **_saldo_tx(r, [p["vault0"], p["vault1"]])})
        simpan(f, rows)

    t = time.time()
    with ThreadPoolExecutor(pekerja) as ex:
        for i, _ in enumerate(ex.map(satu, pools)):
            if i % 50 == 0:
                print(f"  swap {i}/{len(pools)} {time.time() - t:.0f} dtk", flush=True)


def penyandang(wallets: list[str], pekerja: int = 10) -> dict:
    """Siapa yang pertama mengirim XNT ke wallet (transaksi tertua) → deteksi wallet orang dalam yang terhubung."""
    f = DIR / "penyandang.json.gz"
    out = muat(f) if f.exists() else {}

    def satu(w):
        s = _sigs(w, maks_hal=15)
        if s.get("terpotong"):
            return w, {"dari": None, "t": None, "n": s["n"], "terpotong": True}  # wallet > 15 rb transaksi (bot besar)
        if not s["awal"]:
            return w, None
        r = _tx(s["awal"][0][0])
        if not r:
            return w, None
        keys = list(r["transaction"]["message"]["accountKeys"])
        la = r["meta"].get("loadedAddresses") or {}
        keys += la.get("writable", []) + la.get("readonly", [])
        pre, post = r["meta"]["preBalances"], r["meta"]["postBalances"]
        turun = [(post[i] - pre[i], k) for i, k in enumerate(keys[:len(pre)]) if k != w and post[i] < pre[i]]
        return w, {"dari": min(turun)[1] if turun else keys[0], "t": r.get("blockTime"), "n": s["n"]}

    baru = [w for w in dict.fromkeys(wallets) if w not in out]
    with ThreadPoolExecutor(pekerja) as ex:
        for i, (w, v) in enumerate(ex.map(satu, baru)):
            out[w] = v
            if i % 200 == 0:
                print(f"  penyandang {i}/{len(baru)}", flush=True)
                simpan(f, out)
    simpan(f, out)
    return out


def unduh_otoritas(mints: list[str]) -> dict:
    """Status mint SEKARANG: mint authority (bisa cetak token baru), freeze authority (bisa membekukan akun = tidak bisa
    jual), program Token-2022 & ekstensinya (transfer fee, permanent delegate, transfer hook)."""
    out = {}
    for i in range(0, len(mints), 100):
        res = rpc("getMultipleAccounts", [mints[i:i + 100], {"encoding": "jsonParsed"}])["value"]
        for m, v in zip(mints[i:i + 100], res):
            if not v or not isinstance(v.get("data"), dict):
                continue
            info = v["data"]["parsed"]["info"]
            ext = info.get("extensions") or []
            fee = [e["state"].get("newerTransferFee", {}).get("transferFeeBasisPoints", 0)
                   for e in ext if e["extension"] == "transferFeeConfig"]
            out[m] = {"mint_auth": bool(info.get("mintAuthority")), "freeze": bool(info.get("freezeAuthority")),
                      "t22": v["owner"] != "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                      "ext": [e["extension"] for e in ext], "fee_bp": max(fee) if fee else 0}
    simpan(DIR / "otoritas.json.gz", out)
    return out


def unduh_pasok(mints: list[str]) -> dict:
    """Total pasokan tiap token (untuk porsi pasokan yang dimasukkan ke pool saat peluncuran)."""
    out = {}
    for i in range(0, len(mints), 100):
        res = rpc("getMultipleAccounts", [mints[i:i + 100], {"encoding": "base64"}])["value"]
        for m, v in zip(mints[i:i + 100], res):
            if v:
                raw = base64.b64decode(v["data"][0])
                out[m] = struct.unpack_from("<Q", raw, 36)[0] / 10 ** raw[44]
    simpan(DIR / "pasok.json.gz", out)
    return out


def unduh_bar(mint: str, ke: str, t0: int, t1: int, res: int) -> list[dict]:
    url = (f"{XDEX}/api/xdex/chart/history?from_token={mint}&to_token={ke}&resolution={res}&time_from={t0}"
           f"&time_to={t1}&birdeye=false&network=X1%20Mainnet")
    return get(url).get("bars") or []


# ---------------------------------------------------------------------------------------------------- olah data
def muat_pools() -> list[dict]:
    return muat(DIR / "pools.json.gz")


def sisi(p: dict) -> tuple[str, str, int, int] | None:
    """(vault token, vault WXNT, desimal token, desimal WXNT) untuk pool berpasangan WXNT."""
    if p["mint1"] == WXNT:
        return p["vault0"], p["vault1"], p["dec0"], p["dec1"]
    if p["mint0"] == WXNT:
        return p["vault1"], p["vault0"], p["dec1"], p["dec0"]
    return None


def beli(x: float, y: float, xnt: float, fee: float) -> float:
    """Token didapat untuk `xnt` (x·y=k, biaya di sisi masuk)."""
    a = xnt * (1 - fee)
    return x * a / (y + a)


def jual(x: float, y: float, tok: float, fee: float) -> float:
    """XNT didapat untuk menjual `tok`."""
    a = tok * (1 - fee)
    return y * a / (x + a)


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "uji"
    if cmd == "unduh":
        pools = unduh_pool()
        unduh_cadangan(pools)
        unduh_tanda_lp(pools)
    elif cmd == "tx":  # transaksi 24 jam pertama + pasokan token + harga XNT, hanya pool peluncuran
        from research import snipe_x1_uji as U
        L = U.peluncuran()
        unduh_pasok([q["mint"] for q in L])
        unduh_otoritas([q["mint"] for q in L])
        simpan(DIR / "xnt_usd.json.gz", unduh_bar(WXNT, USDC_X, 1759276800, int(time.time()), 1440))
        unduh_swap(L, maks=int(argv[1]) if len(argv) > 1 else 3000)
    else:
        from research import snipe_x1_uji as U
        getattr(U, cmd)()


if __name__ == "__main__":
    main(sys.argv[1:])
