"""🦄 DEX (Robinhood Chain / Arc / EVM Uniswap v3-v4): PERINGATAN saja, memakai token_bot/ (docs/TOKEN_BARU.md).

Kenapa hanya peringatan: data on-chain 2026 menunjukkan selisih harga besar direbut bot dalam 0,1–3 detik; sesudah
pekan pertama chain, peluang >= 1% yang terbuka >= 10 detik bernilai puluhan–ratusan $/hari untuk SEMUA pelaku.
Belum ada riwayat bertahun-tahun. Eksekusi DEX tetap lewat `python -m token_bot pantau --live` (terpisah, atas risiko
pengguna) — bot Telegram ini tidak memegang kunci dompet.
"""
from __future__ import annotations

import time

from ..telegram import esc


class DexMesin:
    nama = "dex"
    label = "🦄 DEX (peringatan)"

    def __init__(self, mesin):
        self.m = mesin
        self.cfg = mesin.cfg["dex"]
        from token_bot.__main__ import _rpcs, muat_cfg, pasangan
        self.tcfg = muat_cfg(self.cfg["config"])
        nets = {x["jaringan"] for x in self.tcfg.get("pasangan", [])} | set(self.cfg.get("pool_baru") or [])
        self.rpcs = _rpcs(self.tcfg, nets)
        self.pairs = pasangan(self.tcfg, self.rpcs) if self.tcfg.get("pasangan") else []
        self.blok = {}
        self.diam: dict[str, float] = {}
        self.terakhir = None

    def tick_harga(self) -> None:
        return None

    def tick_jadwal(self) -> None:
        if not self.m.jatuh_tempo("dex", float(self.cfg["interval_dtk"])):
            return
        from token_bot.strategi import evaluasi
        for net, p in self.pairs:
            nc = self.tcfg["jaringan"][net]
            try:
                r = evaluasi(self.rpcs[net], p, nc["v4_quoter"] if p.pool.ver == 4 else nc["v3_quoter"], nc.get("state_view"))
            except Exception as e:  # noqa: BLE001
                self.m.galat(f"dex {p.nama}", e)
                continue
            self.terakhir = time.time()
            if r["aksi"] in ("BELI", "JUAL_ARBITRASE") and time.time() - self.diam.get(p.nama, 0) > 600:
                self.diam[p.nama] = time.time()
                self.m.kabar(f"🦄 <b>{esc(p.nama)}</b> {r['aksi']}: {esc(r['alasan'])}\nharga wajar {r['wajar']:.6g}, "
                             f"ukuran ${r.get('ukuran_usd', 0):,.0f}, slippage {r.get('slippage_beli', 0) * 100:.2f}%. "
                             f"Hanya peringatan — eksekusi lewat token_bot.")
        for net in self.cfg.get("pool_baru") or []:
            self._pool_baru(net)

    def _pool_baru(self, net: str) -> None:
        from token_bot import acuan
        from token_bot.dex import T_INIT, decimals, sqrtp_harga
        nc, tok = self.tcfg["jaringan"][net], self.tcfg["token"][net]
        rpc = self.rpcs[net]
        wl = {v["alamat"].lower(): (k, v) for k, v in tok.items()}
        top = rpc.block_number()
        b = self.blok.get(net, top)
        if top > b:
            for lg in rpc.get_logs(nc["pool_manager"], [T_INIT], b + 1, top, span=nc.get("span_log", 5000)):
                c0, c1 = "0x" + lg["topics"][2][-40:], "0x" + lg["topics"][3][-40:]
                if c0 not in wl or c1 not in wl:
                    continue
                (n0, t0), (n1, t1) = wl[c0], wl[c1]
                sq = int(lg["data"][2 + 64 * 3: 2 + 64 * 4], 16)
                harga = sqrtp_harga(sq, decimals(rpc, c0), decimals(rpc, c1))
                wajar = acuan.harga(t0["acuan"]) / acuan.harga(t1["acuan"])
                dev = harga / wajar - 1
                if abs(dev) >= 0.02:
                    self.m.kabar(f"🦄 <b>POOL BARU {esc(net)} {esc(n0)}/{esc(n1)}</b> harga awal {harga:.6g} vs wajar "
                                 f"{wajar:.6g} ({dev * 100:+.1f}%). Peluang seperti ini biasanya diambil bot < 3 detik; "
                                 f"cek likuiditas sebelum transaksi (token_bot cek).")
        self.blok[net] = top

    def status_teks(self) -> str:
        return f"{self.label}: {len(self.pairs)} pasangan, pool baru {', '.join(self.cfg.get('pool_baru') or []) or '-'}"
