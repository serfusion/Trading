"""Bot token DEX chain baru (Robinhood Chain, Arc, chain EVM lain dengan Uniswap v3/v4).

  python -m token_bot cek    [--config token_bot/config.yaml]           # satu kali: tabel harga, slippage, keputusan
  python -m token_bot pantau [--config ...] [--interval 3]              # loop; hanya sinyal (tabel + ntfy)
  python -m token_bot baru   [--config ...] --jaringan robinhood        # pantau pool BARU token daftar putih
  python -m token_bot cari   --jaringan arc --pool <poolId|alamat v3> [--blok N]
  python -m token_bot bot    [--config ...]                             # bot kontrol Telegram gaya screenshot (docs/ARB_BOT.md)
  python -m token_bot chat-id                                           # tampilkan chat_id Telegram (setelah /start)

Tidak ada janji profit: riset docs/TOKEN_BARU.md menunjukkan selisih harga besar hanya ada di hari-hari pertama chain
dan diambil bot dalam hitungan detik. token_bot TIDAK mengirim transaksi (tanpa private key): hanya sinyal & simulasi
kertas; eksekusi dilakukan pengguna sendiri di dompetnya (docs/ARB_BOT.md).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import acuan
from .dex import T_INIT, Pool, cari_v3, cari_v4, decimals, sqrtp_harga, symbol
from .rpc import Rpc
from .strategi import Pasangan, evaluasi
from .tele import sensor

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache_pool.json"


def muat_env(path: Path) -> None:
    if not path.exists():
        return
    import os
    try:
        if os.name != "nt" and path.stat().st_mode & 0o077:
            print(f"⚠️ {path} bisa dibaca pengguna lain. Jalankan: chmod 600 {path}", flush=True)
    except OSError:
        pass
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
LOG = HERE / "log"


def muat_cfg(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        p = HERE / "config.example.yaml"
        print(f"(config {path} tidak ada -> pakai {p.name})")
    return yaml.safe_load(p.read_text())


def _cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def pool_dari(rpc: Rpc, net: str, ncfg: dict, ver: int, pid: str, blok: int | None = None) -> Pool:
    c = _cache()
    k = f"{net}:{pid.lower()}"
    if k in c:
        return Pool(**c[k])
    if ver == 4:
        b0 = max((blok or ncfg.get("blok_awal", 1)) - 50, 1)
        b1 = (blok + 50) if blok else None
        p = cari_v4(rpc, ncfg["pool_manager"], pid, b0, b1, span=ncfg.get("span_log", 5000))
    else:
        p = cari_v3(rpc, pid)
    c[k] = p.__dict__
    CACHE.write_text(json.dumps(c, indent=1))
    return p


def pasangan(cfg: dict, rpcs: dict) -> list[tuple[str, Pasangan]]:
    out = []
    d = cfg.get("bawaan", {})
    for x in cfg["pasangan"]:
        net = x["jaringan"]
        ncfg, tok = cfg["jaringan"][net], cfg["token"][net]
        pool = pool_dari(rpcs[net], net, ncfg, x["ver"], x["pool"], x.get("blok"))
        t, q = tok[x["token"]], tok[x["quote"]]
        for a in (t["alamat"], q["alamat"]):  # daftar putih: pool harus berisi token resmi persis
            if a.lower() not in (pool.c0.lower(), pool.c1.lower()):
                raise SystemExit(f"{x['nama']}: token {a} tidak ada di pool {x['pool']} (alamat tiruan?)")
        kw = {k: x.get(k, d.get(k)) for k in ("ukuran_usd", "min_usd", "beli_bawah", "jual_atas", "max_slippage", "tp",
                                              "sl", "biaya_gas_usd", "luar_jam", "tebus_manual", "biaya_tebus")
              if x.get(k, d.get(k)) is not None}
        out.append((net, Pasangan(x["nama"], pool, t["alamat"], q["alamat"], t["acuan"], q["acuan"], **kw)))
    return out


def _rpcs(cfg: dict, nets: set[str]) -> dict[str, Rpc]:
    from .tele import rahasia_url
    for n in nets:
        rahasia_url(cfg["jaringan"][n]["rpc"])     # URL RPC bisa memuat kunci API -> disensor dari pesan galat
    return {n: Rpc(cfg["jaringan"][n]["rpc"], cfg["jaringan"][n]["chain_id"]) for n in nets}


def _fmt(r: dict) -> str:
    def p(k, f="{:+.2%}"):
        v = r.get(k)
        return f.format(v) if isinstance(v, (int, float)) else "-"
    return (f"{r['pasangan']:<22} wajar {r['wajar']:.6g}  spot {p('selisih_spot')}  ukuran ${r.get('ukuran_usd', 0):,.0f}"
            f"  slip {p('slippage_beli', '{:.2%}')}  diskon {p('untung_beli')}  bersih {p('untung_bersih')}"
            f"  jual {p('untung_jual')}"
            f"  pp {p('rugi_pulang_pergi', '{:.2%}')}  -> {r['aksi']} {r['alasan']}")


def _ntfy(cfg: dict, msg: str) -> None:
    topic = cfg.get("ntfy_topic")
    if not topic:
        return
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode()), timeout=10)
    except Exception as e:  # noqa: BLE001 — notifikasi opsional, jangan hentikan pemantauan
        print(f"(ntfy gagal: {e})")


def _log(r: dict) -> None:
    LOG.mkdir(exist_ok=True)
    f = LOG / f"{datetime.now(timezone.utc):%Y-%m-%d}.csv"
    baru = not f.exists()
    keys = ["waktu", "pasangan", "aksi", "wajar", "spot", "selisih_spot", "ukuran_usd", "harga_beli", "slippage_beli",
            "untung_beli", "untung_bersih", "harga_jual", "untung_jual", "rugi_pulang_pergi", "acuan_hidup", "alasan"]
    with f.open("a", newline="") as fh:
        w = csv.DictWriter(fh, keys, extrasaction="ignore")
        if baru:
            w.writeheader()
        w.writerow({"waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"), **r})


def cmd_cek(cfg: dict, loop: float | None = None) -> None:
    """Tabel keputusan (sekali / loop). Hanya sinyal: tidak ada posisi & tidak ada transaksi."""
    nets = {x["jaringan"] for x in cfg["pasangan"]}
    rpcs = _rpcs(cfg, nets)
    prs = pasangan(cfg, rpcs)
    while True:
        for net, p in prs:
            ncfg = cfg["jaringan"][net]
            try:
                r = evaluasi(rpcs[net], p, ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"],
                             ncfg.get("state_view"))
            except Exception as e:  # noqa: BLE001
                print(f"{p.nama}: galat {sensor(e)}")
                continue
            print(_fmt(r), flush=True)
            _log(r)
            if r["aksi"] == "BELI":
                _ntfy(cfg, _fmt(r))
        if loop is None:
            return
        time.sleep(loop)


def cmd_baru(cfg: dict, net: str, interval: float = 2.0) -> None:
    """Pantau event Initialize pool v4 baru yang KEDUA tokennya ada di daftar putih; laporkan harga awal vs acuan.
    (Kasus pengguna: pool WETH dibuat dengan harga salah -> 0,45 ETH seharga $6.) Hanya sinyal."""
    ncfg, tok = cfg["jaringan"][net], cfg["token"][net]
    rpc = Rpc(ncfg["rpc"], ncfg["chain_id"])
    wl = {v["alamat"].lower(): (k, v) for k, v in tok.items()}
    b = rpc.block_number()
    print(f"pantau pool baru {net} mulai blok {b}; daftar putih: {', '.join(k for k, _ in wl.values())}")
    while True:
        top = rpc.block_number()
        if top > b:
            for lg in rpc.get_logs(ncfg["pool_manager"], [T_INIT], b + 1, top, span=ncfg.get("span_log", 5000)):
                c0, c1 = "0x" + lg["topics"][2][-40:], "0x" + lg["topics"][3][-40:]
                if c0 not in wl or c1 not in wl:
                    continue
                (n0, t0), (n1, t1) = wl[c0], wl[c1]
                sq = int(lg["data"][2 + 64 * 3: 2 + 64 * 4], 16)
                px = sqrtp_harga(sq, decimals(rpc, c0), decimals(rpc, c1))  # n0 dalam n1
                wajar = acuan.harga(t0["acuan"]) / acuan.harga(t1["acuan"])
                dev = px / wajar - 1
                msg = (f"POOL BARU {net} {n0}/{n1} id {lg['topics'][1][:12]}.. harga awal {px:.6g} vs wajar {wajar:.6g} "
                       f"({dev:+.1%}); cek likuiditas dgn `cek` sebelum transaksi")
                print(msg, flush=True)
                if abs(dev) >= cfg.get("bawaan", {}).get("beli_bawah", 0.02):
                    _ntfy(cfg, msg)
            b = top
        time.sleep(interval)


def cmd_chat_id() -> None:
    import urllib.request
    tok = os.environ.get("TELEGRAM_TOKEN", "")
    if not tok:
        raise SystemExit("isi TELEGRAM_TOKEN di token_bot/.env dulu")
    with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=30) as r:
        d = json.loads(r.read())
    seen = {}
    for u in d.get("result", []):
        c = (u.get("message") or {}).get("chat") or {}
        if c.get("type") == "private":
            seen[c["id"]] = c.get("username") or c.get("first_name")
    if not seen:
        print("Kirim /start ke bot dulu, lalu jalankan lagi.")
    for cid, nama in seen.items():
        print(f"chat_id {cid} ({nama}) -> token_bot/.env: TELEGRAM_CHAT_ID={cid}")


def cmd_cari(cfg: dict, net: str, pid: str, blok: int | None) -> None:
    ncfg = cfg["jaringan"][net]
    rpc = Rpc(ncfg["rpc"], ncfg["chain_id"])
    p = pool_dari(rpc, net, ncfg, 4 if len(pid) == 66 else 3, pid, blok)
    print(json.dumps(p.__dict__, indent=1))
    print("token0", symbol(rpc, p.c0), "token1", symbol(rpc, p.c1))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="token_bot")
    ap.add_argument("perintah", choices=["cek", "pantau", "baru", "cari", "bot", "chat-id"])
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--jaringan")
    ap.add_argument("--pool")
    ap.add_argument("--blok", type=int)
    a = ap.parse_args(argv)
    muat_env(HERE / ".env")
    if a.perintah == "chat-id":
        return cmd_chat_id()
    cfg = muat_cfg(a.config)
    if a.perintah == "bot":
        from .pantau_bot import Store, buat
        store = Store((HERE / "data") / cfg.get("mode", "pantau"))
        store.kunci()
        buat(cfg, store=store).jalan()
        return
    if a.perintah == "cek":
        cmd_cek(cfg)
    elif a.perintah == "pantau":
        cmd_cek(cfg, loop=a.interval)
    elif a.perintah == "baru":
        cmd_baru(cfg, a.jaringan or "robinhood", a.interval)
    else:
        cmd_cari(cfg, a.jaringan, a.pool, a.blok)


if __name__ == "__main__":
    main(sys.argv[1:])
