"""Bot token DEX chain baru (Robinhood Chain, Arc, chain EVM lain dengan Uniswap v3/v4).

  python -m token_bot cek    [--config token_bot/config.yaml]           # satu kali: tabel harga, slippage, keputusan
  python -m token_bot pantau [--config ...] [--interval 3] [--live]     # loop; tanpa --live = hanya sinyal (BAWAAN)
  python -m token_bot baru   [--config ...] --jaringan robinhood        # pantau pool BARU token daftar putih
  python -m token_bot cari   --jaringan arc --pool <poolId|alamat v3> [--blok N]

Tidak ada janji profit: riset docs/TOKEN_BARU.md menunjukkan selisih harga besar hanya ada di hari-hari pertama chain
dan diambil bot dalam hitungan detik. Mode live hanya bila --live DAN live.aktif: true DAN env TOKEN_BOT_PK.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import acuan
from .dex import Pool, cari_v3, cari_v4, decimals, quote, sqrtp_harga, symbol, T_INIT
from .rpc import Rpc
from .strategi import Pasangan, evaluasi

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache_pool.json"
LOG = HERE / "log"
POSISI = HERE / "posisi.json"


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
                                              "sl", "biaya_gas_usd", "luar_jam") if x.get(k, d.get(k)) is not None}
        out.append((net, Pasangan(x["nama"], pool, t["alamat"], q["alamat"], t["acuan"], q["acuan"], **kw)))
    return out


def _rpcs(cfg: dict, nets: set[str]) -> dict[str, Rpc]:
    return {n: Rpc(cfg["jaringan"][n]["rpc"], cfg["jaringan"][n]["chain_id"]) for n in nets}


def _fmt(r: dict) -> str:
    def p(k, f="{:+.2%}"):
        v = r.get(k)
        return f.format(v) if isinstance(v, (int, float)) else "-"
    return (f"{r['pasangan']:<22} wajar {r['wajar']:.6g}  spot {p('selisih_spot')}  ukuran ${r.get('ukuran_usd', 0):,.0f}"
            f"  slip {p('slippage_beli', '{:.2%}')}  beli {p('untung_beli')}  jual {p('untung_jual')}"
            f"  pp {p('rugi_pulang_pergi', '{:.2%}')}  -> {r['aksi']} {r['alasan']}")


def _ntfy(cfg: dict, msg: str) -> None:
    topic = cfg.get("ntfy_topic")
    if not topic:
        return
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode()), timeout=10)
    except Exception:  # noqa: BLE001
        pass


def _log(r: dict) -> None:
    LOG.mkdir(exist_ok=True)
    f = LOG / f"{datetime.now(timezone.utc):%Y-%m-%d}.csv"
    baru = not f.exists()
    keys = ["waktu", "pasangan", "aksi", "wajar", "spot", "selisih_spot", "ukuran_usd", "harga_beli", "slippage_beli",
            "untung_beli", "harga_jual", "untung_jual", "rugi_pulang_pergi", "acuan_hidup", "alasan"]
    with f.open("a", newline="") as fh:
        w = csv.DictWriter(fh, keys, extrasaction="ignore")
        if baru:
            w.writeheader()
        w.writerow({"waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"), **r})


def cmd_cek(cfg: dict, live: bool = False, loop: float | None = None) -> None:
    nets = {x["jaringan"] for x in cfg["pasangan"]}
    rpcs = _rpcs(cfg, nets)
    prs = pasangan(cfg, rpcs)
    dompet = None
    if live:
        if not cfg.get("live", {}).get("aktif"):
            raise SystemExit("--live ditolak: set live.aktif: true di konfigurasi dulu (baca peringatan docs)")
        from .eksekusi import Dompet
        if len(nets) != 1:
            raise SystemExit("mode live: satu jaringan per proses")
        net = next(iter(nets))
        dompet = Dompet(rpcs[net], cfg["jaringan"][net]["chain_id"])
        print(f"LIVE dompet {dompet.addr} di {net}")
    pos = json.loads(POSISI.read_text()) if POSISI.exists() else {}
    hari, n_trade = None, 0
    while True:
        for net, p in prs:
            ncfg = cfg["jaringan"][net]
            try:
                r = evaluasi(rpcs[net], p, ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"],
                             ncfg.get("state_view"), pos.get(p.nama))
            except Exception as e:  # noqa: BLE001
                print(f"{p.nama}: galat {e}")
                continue
            print(_fmt(r), flush=True)
            _log(r)
            if r["aksi"] in ("BELI", "JUAL"):
                _ntfy(cfg, _fmt(r))
            if dompet and r["aksi"] in ("BELI", "JUAL"):
                today = datetime.now(timezone.utc).date()
                if today != hari:
                    hari, n_trade = today, 0
                lv = cfg["live"]
                if n_trade >= lv.get("maks_trade_per_hari", 5):
                    print("  batas trade harian tercapai")
                    continue
                n_trade += 1
                _eksekusi(rpcs[net], cfg, ncfg, dompet, p, r, pos)
                POSISI.write_text(json.dumps(pos, indent=1))
        if loop is None:
            return
        time.sleep(loop)


def _eksekusi(rpc, cfg, ncfg, dompet, p: Pasangan, r: dict, pos: dict) -> None:
    lv = cfg["live"]
    q = ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"]
    dq = p.pool.d0 if p.quote.lower() == p.pool.c0.lower() else p.pool.d1
    dt = p.pool.d1 if dq == p.pool.d0 else p.pool.d0
    if r["aksi"] == "BELI":
        usd = min(r["ukuran_usd"], lv.get("maks_usd_per_trade", 50))
        if sum(v["usd"] for v in pos.values()) + usd > lv.get("maks_total_usd", 200):
            print("  batas total posisi tercapai")
            return
        amt = int(usd / acuan.harga(p.acuan_quote) * 10 ** dq)
        got = quote(rpc, p.pool, p.quote, amt, q)
        h = dompet.swap(ncfg, p.pool, p.quote, amt, int(got * (1 - p.max_slippage)))
        pos[p.nama] = {"token": got, "harga": (amt / 10 ** dq) / (got / 10 ** dt), "usd": usd, "tx": h,
                       "waktu": datetime.now(timezone.utc).isoformat()}
        print(f"  BELI terkirim {h}")
    elif r["aksi"] == "JUAL" and p.nama in pos:
        n = int(pos[p.nama]["token"])
        got = quote(rpc, p.pool, p.token, n, q)
        h = dompet.swap(ncfg, p.pool, p.token, n, int(got * (1 - p.max_slippage)))
        print(f"  JUAL terkirim {h}: {(got / 10 ** dq):.4f} vs modal {pos[p.nama]['usd']:.2f}")
        pos.pop(p.nama)


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


def cmd_cari(cfg: dict, net: str, pid: str, blok: int | None) -> None:
    ncfg = cfg["jaringan"][net]
    rpc = Rpc(ncfg["rpc"], ncfg["chain_id"])
    p = pool_dari(rpc, net, ncfg, 4 if len(pid) == 66 else 3, pid, blok)
    print(json.dumps(p.__dict__, indent=1))
    print("token0", symbol(rpc, p.c0), "token1", symbol(rpc, p.c1))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="token_bot")
    ap.add_argument("perintah", choices=["cek", "pantau", "baru", "cari"])
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--jaringan")
    ap.add_argument("--pool")
    ap.add_argument("--blok", type=int)
    a = ap.parse_args(argv)
    cfg = muat_cfg(a.config)
    if a.perintah == "cek":
        cmd_cek(cfg)
    elif a.perintah == "pantau":
        cmd_cek(cfg, live=a.live, loop=a.interval)
    elif a.perintah == "baru":
        cmd_baru(cfg, a.jaringan or "robinhood", a.interval)
    else:
        cmd_cari(cfg, a.jaringan, a.pool, a.blok)


if __name__ == "__main__":
    main(sys.argv[1:])
