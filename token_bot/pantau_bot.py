"""Bot kontrol Telegram gaya screenshot (wetharb/circarb) untuk token_bot — python -m token_bot bot

Memantau pasangan pool vs harga ACUAN (harga wajar) dan, bila diizinkan, membeli saat jauh di bawah acuan / menjual
saat di atas (lihat token_bot/strategi.evaluasi: kuotasi NYATA Quoter, ukuran dikecilkan sampai slippage <= batas,
cek jual-balik honeypot). Dikendalikan lewat Telegram dengan tombol persis screenshot:
  💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART · ❓ Bantuan

Tiga mode (config `mode`):
  pantau  (bawaan) — hanya MENGABARI peluang, tidak ada transaksi (paling aman).
  kertas            — simulasi: saldo & posisi palsu diisi di harga kuotasi, tanpa menyentuh dana.
  live              — transaksi NYATA lewat token_bot/eksekusi.Dompet. BAWAAN MATI; perlu live.aktif + env TOKEN_BOT_PK.
                      Auto-beli hanya aktif setelah 🅰 BUY ON (diarmкан sekali dengan konfirmasi). Batas keras
                      (maks $/trade, total, trade/hari) tetap berlaku.

PENTING (hasil riset docs/eksternal/hasil_arb_cari.txt & hasil_arb_latensi.txt): strategi "beli diskon lalu tebus 1:1
lewat jembatan" hanya menghasilkan di JENDELA PELUNCURAN chain/jembatan BARU (pra-publik); setelah publik sisa peluang
±$20-65/HARI untuk SEMUA pelaku dan direbut bot < 1 detik. Bot ini TIDAK menebus lewat jembatan (kustodial, berisiko) —
hanya arbitrase DEX; leg tebus dilakukan manual. Jalankan di mode pantau/kertas dulu. Tidak ada janji profit.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from . import acuan
from .dex import quote
from .strategi import evaluasi
from .tele import Telegram, TelegramMati, esc, sensor

WIB = 7 * 3600
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def _usd(x) -> str:
    return "?" if not isinstance(x, (int, float)) else f"${x:,.2f}"


def _pct(x) -> str:
    return "-" if not isinstance(x, (int, float)) else f"{x * 100:+.2f}%"


def jam(t: float) -> str:
    return datetime.fromtimestamp(t + WIB, timezone.utc).strftime("%d %b %H:%M WIB")


class Store:
    KOSONG = {"mode": None, "buy_on": False, "stop": False, "posisi": {}, "kas_kertas": None, "log": [], "tx": [],
              "hari": None, "n_trade": 0, "offset": 0, "pending": None}

    def __init__(self, data_dir: Path):
        self.dir = data_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "state.json"
        self.s = self._baca()

    def _baca(self) -> dict:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                for k, v in self.KOSONG.items():
                    d.setdefault(k, json.loads(json.dumps(v)))
                return d
            except json.JSONDecodeError:
                self.path.rename(self.path.with_suffix(f".rusak.{int(time.time())}.json"))
        return json.loads(json.dumps(self.KOSONG))

    def simpan(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def kunci(self) -> None:
        self._f = open(self.dir / "bot.lock", "a+")
        try:
            import fcntl
            fcntl.flock(self._f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ImportError) as e:
            raise RuntimeError(f"bot lain memakai {self.dir} (bot.lock)") from e


class Bot:
    def __init__(self, cfg: dict, store: Store, rpcs: dict, prs: list, tg, dompet=None, sekarang=time.time):
        self.cfg, self.store, self.rpcs, self.prs, self.tg = cfg, store, rpcs, prs, tg
        self.dompet, self.now = dompet, sekarang
        self.mode = cfg.get("mode", "pantau")
        self.lv = cfg.get("live", {})
        self.jadwal: dict[str, float] = {}
        self.konfirmasi: dict[str, tuple] = {}
        self.galat_t: dict[str, float] = {}
        s = store.s
        if s["mode"] and s["mode"] != self.mode and s["posisi"]:
            raise RuntimeError(f"state berisi posisi mode {s['mode']}, sekarang {self.mode}. Pakai data_dir lain atau "
                               f"tutup posisi dulu.")
        s["mode"] = self.mode
        if self.mode == "kertas" and s["kas_kertas"] is None:
            s["kas_kertas"] = float(cfg.get("modal_kertas_usd", 500))

    @property
    def s(self) -> dict:
        return self.store.s

    # ------------------------------------------------------------------ kabar & log
    def kabar(self, teks: str, **kw) -> None:
        try:
            self.tg.kirim(teks, **kw)
        except Exception as e:  # noqa: BLE001
            print("tele gagal:", sensor(e), flush=True)

    def galat(self, kunci: str, e) -> None:
        t = self.now()
        print(f"[galat] {kunci}: {sensor(e)}", flush=True)
        if t - self.galat_t.get(kunci, 0) > 1800:
            self.galat_t[kunci] = t
            self.kabar(f"⚠️ <b>{esc(kunci)}</b>: {esc(sensor(e)[:300])}")

    def catat(self, jenis: str, teks: str, tx: str | None = None) -> None:
        row = {"t": self.now(), "jenis": jenis, "teks": teks}
        self.s["log"] = ([row] + self.s["log"])[:100]
        if tx:
            self.s["tx"] = ([{"t": self.now(), "teks": teks, "tx": tx}] + self.s["tx"])[:50]

    def _hari(self) -> None:
        hari = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%d")
        if self.s["hari"] != hari:
            self.s["hari"], self.s["n_trade"] = hari, 0

    # ------------------------------------------------------------------ evaluasi satu pasangan
    def _eval(self, net: str, p):
        ncfg = self.cfg["jaringan"][net]
        q = ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"]
        return evaluasi(self.rpcs[net], p, q, ncfg.get("state_view"), self.s["posisi"].get(p.nama))

    def putaran(self) -> None:
        for off, u, cid, teks, cbid in self.tg.ambil():
            self.s["offset"] = off
            if u is None:
                continue
            try:
                self.perintah(cid, teks, cbid)
            except Exception as e:  # noqa: BLE001
                self.galat("perintah", e)
        if self.s["stop"]:
            self.store.simpan()
            return
        if not self.jatuh_tempo("pindai", float(self.cfg.get("interval", 5))):
            self.store.simpan()
            return
        self._hari()
        for net, p in self.prs:
            try:
                r = self._eval(net, p)
            except Exception as e:  # noqa: BLE001
                self.galat(f"eval {p.nama}", e)
                continue
            self.tangani(net, p, r)
        self.store.simpan()

    def jatuh_tempo(self, kunci: str, detik: float) -> bool:
        t = self.now()
        if t - self.jadwal.get(kunci, 0) >= detik:
            self.jadwal[kunci] = t
            return True
        return False

    def tangani(self, net: str, p, r: dict) -> None:
        pos = self.s["posisi"].get(p.nama)
        if pos and r["aksi"] == "JUAL":
            self.tutup(net, p, r)
            return
        if not pos and r["aksi"] == "BELI":
            self.catat("sinyal", f"{p.nama}: {r['alasan']}")
            if self.mode == "pantau":
                self.kabar(f"🅰 <b>PELUANG BELI {esc(p.nama)}</b>\nHarga {r['harga_beli']:.6g} = {_pct(r['untung_beli'])} "
                           f"di bawah wajar {r['wajar']:.6g}, ukuran {_usd(r.get('ukuran_usd'))}, slippage "
                           f"{_pct(r.get('slippage_beli'))}. Mode pantau: tidak dibeli. (Leg tebus jembatan manual.)")
            elif self.s["buy_on"]:
                self.beli(net, p, r)
            # kertas/live tanpa BUY ON: diam (sudah dicatat di log)

    # ------------------------------------------------------------------ batas risiko
    def boleh(self, usd: float) -> str | None:
        if self.s.get("pending"):
            return "ada transaksi tidak pasti — cek dompet lalu /beres"
        self._hari()
        maks_tr = self.lv.get("maks_trade_per_hari", 5) if self.mode == "live" else 50
        if self.s["n_trade"] >= maks_tr:
            return f"batas {maks_tr} trade/hari"
        maks1 = self.lv.get("maks_usd_per_trade", 25) if self.mode == "live" else 1e9
        if usd > maks1 + 1e-9:
            return f"ukuran > batas {_usd(maks1)}/trade"
        maks_t = self.lv.get("maks_total_usd", 100) if self.mode == "live" else 1e9
        if sum(v["usd"] for v in self.s["posisi"].values()) + usd > maks_t + 1e-9:
            return f"total posisi akan > {_usd(maks_t)}"
        return None

    # ------------------------------------------------------------------ beli / tutup
    def beli(self, net: str, p, r: dict) -> None:
        usd = min(r["ukuran_usd"], self.lv.get("maks_usd_per_trade", 25) if self.mode == "live" else r["ukuran_usd"])
        alasan = self.boleh(usd)
        if alasan:
            self.catat("lewat", f"{p.nama}: {alasan}")
            return
        if self.mode == "kertas":
            if usd > (self.s["kas_kertas"] or 0):
                self.catat("lewat", f"{p.nama}: kas kertas kurang")
                return
            self.s["kas_kertas"] -= usd
            tok = usd / r["harga_beli"]
            self.s["posisi"][p.nama] = {"net": net, "token": tok, "harga": r["harga_beli"], "usd": usd,
                                        "t": self.now()}
            self.s["n_trade"] += 1
            self.catat("beli", f"{p.nama} {usd:.2f} @ {r['harga_beli']:.6g}")
            self.kabar(f"🟢 <b>BELI (kertas) {esc(p.nama)}</b> {_usd(usd)} @ {r['harga_beli']:.6g} "
                       f"({_pct(r['untung_beli'])} di bawah wajar)")
            return
        # live
        self._beli_live(net, p, r, usd)

    def _beli_live(self, net: str, p, r: dict, usd: float) -> None:
        ncfg = self.cfg["jaringan"][net]
        q = ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"]
        dq = p.pool.d0 if p.quote.lower() == p.pool.c0.lower() else p.pool.d1
        dt = p.pool.d1 if dq == p.pool.d0 else p.pool.d0
        try:
            amt = int(usd / acuan.harga(p.acuan_quote) * 10 ** dq)
            got = quote(self.rpcs[net], p.pool, p.quote, amt, q)
        except Exception as e:  # noqa: BLE001 — belum kirim transaksi
            self.galat(f"kuotasi {p.nama}", e)
            return
        self.s["pending"] = {"nama": p.nama, "usd": usd, "t": self.now()}
        self.store.simpan()                    # catat SEBELUM kirim
        try:
            h = self.dompet.swap(ncfg, p.pool, p.quote, amt, int(got * (1 - p.max_slippage)))
        except Exception as e:  # noqa: BLE001 — transaksi mungkin terkirim: JEDA, jangan ulang
            self.darurat(f"BELI {p.nama} {_usd(usd)} status tidak pasti", e)
            return
        self.s["pending"] = None
        self.s["posisi"][p.nama] = {"net": net, "token": got, "harga": (amt / 10 ** dq) / (got / 10 ** dt),
                                    "usd": usd, "t": self.now(), "tx": h}
        self.s["n_trade"] += 1
        self.catat("beli", f"{p.nama} {usd:.2f} @ {r['harga_beli']:.6g}", tx=h)
        self.store.simpan()
        self.kabar(f"🟢 <b>BELI (live) {esc(p.nama)}</b> {_usd(usd)} @ {r['harga_beli']:.6g}\ntx {esc(h)}")

    def tutup(self, net: str, p, r: dict) -> None:
        pos = self.s["posisi"][p.nama]
        if self.mode in ("pantau", "kertas"):
            keluar = r.get("harga_jual") or r.get("wajar")
            hasil = pos["token"] * keluar - pos["usd"]
            if self.mode == "kertas":
                self.s["kas_kertas"] += pos["token"] * keluar
            self.s["posisi"].pop(p.nama)
            self.catat("jual", f"{p.nama} {('%+.2f' % hasil)} ({r['alasan']})")
            self.kabar(f"💰 <b>JUAL ({self.mode}) {esc(p.nama)}</b> {_usd(hasil)} ({r['alasan']})")
            return
        ncfg = self.cfg["jaringan"][net]
        q = ncfg["v4_quoter"] if p.pool.ver == 4 else ncfg["v3_quoter"]
        dq = p.pool.d0 if p.quote.lower() == p.pool.c0.lower() else p.pool.d1
        n = int(pos["token"])
        try:
            got = quote(self.rpcs[net], p.pool, p.token, n, q)
        except Exception as e:  # noqa: BLE001
            self.galat(f"kuotasi jual {p.nama}", e)
            return
        self.s["pending"] = {"nama": p.nama, "jual": True, "t": self.now()}
        self.store.simpan()
        try:
            h = self.dompet.swap(ncfg, p.pool, p.token, n, int(got * (1 - p.max_slippage)))
        except Exception as e:  # noqa: BLE001
            self.darurat(f"JUAL {p.nama} status tidak pasti", e)
            return
        self.s["pending"] = None
        hasil = got / 10 ** dq - pos["usd"]
        self.s["posisi"].pop(p.nama)
        self.catat("jual", f"{p.nama} {('%+.2f' % hasil)} ({r['alasan']})", tx=h)
        self.store.simpan()
        self.kabar(f"💰 <b>JUAL (live) {esc(p.nama)}</b> {_usd(hasil)} ({r['alasan']})\ntx {esc(h)}")

    def darurat(self, judul: str, e) -> None:
        self.s["stop"] = True
        self.s["buy_on"] = False
        self.store.simpan()
        print(f"[darurat] {judul}: {sensor(e)}", flush=True)
        self.kabar(f"🚨 <b>{esc(judul)}</b>\n{esc(sensor(e)[:400])}\nBot DISTOP & BUY OFF. Cek dompet/explorer: apakah "
                   f"transaksi terkirim? Lalu /beres dan 🔄 RESTART.")

    # ------------------------------------------------------------------ perintah Telegram
    TOMBOL = {"💰 saldo": "/saldo", "📈 harga": "/harga", "📄 log": "/log", "🧾 tx": "/tx",
              "🅰 buy on/off": "/buy", "⏹ stop": "/stop", "🔄 restart": "/restart", "❓ bantuan": "/bantuan"}

    def perintah(self, cid: int, teks: str, cbid: str | None) -> None:
        if cbid:
            jenis, _, tok = teks.partition(":")
            t, fn, cid0 = self.konfirmasi.pop(tok, (0, None, None))
            if not fn or cid0 != cid or self.now() - t > 60:
                self.tg.jawab_tombol(cbid, "Kedaluwarsa.")
                return
            self.tg.jawab_tombol(cbid, "OK" if jenis == "ya" else "Batal")
            if jenis == "ya":
                fn()
            return
        t = teks.strip()
        t = self.TOMBOL.get(t.lower(), t)
        cmd = t.split()[0].split("@")[0].lower() if t else ""
        if cmd in ("/start", "/bantuan", "/help", "/menu"):
            self.kabar(self.bantuan(), chat_id=cid, menu=True)
        elif cmd == "/saldo":
            self.kabar(self.teks_saldo(), chat_id=cid)
        elif cmd == "/harga":
            self.kabar(self.teks_harga(), chat_id=cid)
        elif cmd == "/log":
            self.kabar(self.teks_log(), chat_id=cid)
        elif cmd == "/tx":
            self.kabar(self.teks_tx(), chat_id=cid)
        elif cmd == "/stop":
            self.s["stop"] = True
            self.s["buy_on"] = False
            self.kabar("⏹ <b>STOP</b> — pemantauan & auto-beli berhenti. 🔄 RESTART untuk mulai lagi. Posisi terbuka "
                       "TIDAK ditutup otomatis saat stop.", chat_id=cid)
        elif cmd == "/restart":
            if self.s.get("pending"):
                self.kabar("🚨 Masih ada transaksi tidak pasti. /beres dulu.", chat_id=cid)
                return
            self.s["stop"] = False
            self.jadwal.pop("pindai", None)
            self.kabar("🔄 <b>RESTART</b> — pemantauan jalan lagi.", chat_id=cid)
        elif cmd == "/buy":
            self.cmd_buy(cid)
        elif cmd == "/beres":
            if not self.s.get("pending"):
                self.kabar("Tidak ada transaksi tidak pasti.", chat_id=cid)
                return
            pend = self.s["pending"]
            self.s["pending"] = None
            self.store.simpan()
            self.kabar(f"✅ Tanda tidak pasti dihapus ({esc(pend.get('nama', ''))}). Bila transaksi ternyata terjadi, "
                       f"koin/USDC ada di dompet tetapi TIDAK tercatat bot — sesuaikan manual. Bot masih STOP: 🔄 RESTART.",
                       chat_id=cid)
        else:
            self.kabar("Perintah tidak dikenal. ❓ Bantuan", chat_id=cid)

    def cmd_buy(self, cid: int) -> None:
        if self.mode == "pantau":
            self.kabar("Mode <b>pantau</b>: bot hanya mengabari, tidak membeli. Ubah `mode: kertas` atau `live` di "
                       "config untuk mengaktifkan auto-beli.", chat_id=cid)
            return
        if self.s["buy_on"]:
            self.s["buy_on"] = False
            self.kabar("🅰 <b>BUY OFF</b> — auto-beli dimatikan (posisi terbuka tetap dikelola).", chat_id=cid)
            return
        if self.mode == "live":
            import secrets
            tok = secrets.token_hex(4)

            def arm():
                self.s["buy_on"] = True
                self.kabar("🅰 <b>BUY ON (LIVE)</b> — bot akan membeli OTOMATIS saat ada peluang, dalam batas "
                           f"{_usd(self.lv.get('maks_usd_per_trade', 25))}/trade, total {_usd(self.lv.get('maks_total_usd', 100))}, "
                           f"{self.lv.get('maks_trade_per_hari', 5)} trade/hari.")
            self.konfirmasi[tok] = (self.now(), arm, cid)
            self.kabar(f"⚠️ Aktifkan AUTO-BELI dengan <b>uang sungguhan</b> di dompet {esc(getattr(self.dompet, 'addr', '?'))}? "
                       f"Tombol berlaku 60 detik.", chat_id=cid,
                       tombol=[[{"text": "✅ Ya, BUY ON", "callback_data": f"ya:{tok}"},
                                {"text": "❌ Batal", "callback_data": f"tidak:{tok}"}]])
            return
        self.s["buy_on"] = True
        self.kabar("🅰 <b>BUY ON (kertas)</b> — simulasi auto-beli aktif.", chat_id=cid)

    # ------------------------------------------------------------------ teks
    def bantuan(self) -> str:
        return ("<b>Bot token (arbitrase token baru)</b>\n"
                f"Mode: <b>{esc(self.mode)}</b> • pasangan dipantau: {len(self.prs)}\n"
                "💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART\n"
                "BELI saat harga pool jauh di bawah acuan, JUAL saat di atas / TP / SL (kuotasi nyata, cek honeypot).\n"
                "⚠️ Teruji: menguntungkan hanya di jendela peluncuran chain/jembatan BARU (pra-publik). Setelah publik "
                "peluang receh & diperebutkan bot < 1 dtk. Bot tidak menebus lewat jembatan (manual). Bukan janji profit.")

    def teks_saldo(self) -> str:
        if self.mode == "live" and self.dompet:
            return f"Mode LIVE • dompet {esc(self.dompet.addr)}\nPosisi tercatat: {len(self.s['posisi'])}"
        kas = self.s.get("kas_kertas")
        eks = sum(v["usd"] for v in self.s["posisi"].values())
        return (f"Mode <b>{esc(self.mode)}</b>\nKas kertas {_usd(kas)} • posisi {len(self.s['posisi'])} senilai {_usd(eks)}"
                + ("".join(f"\n• {esc(k)}: {_usd(v['usd'])} @ {v['harga']:.6g}" for k, v in self.s["posisi"].items())))

    def teks_harga(self) -> str:
        out = [f"Status: {'⏹ STOP' if self.s['stop'] else '▶️ jalan'} • BUY {'ON' if self.s['buy_on'] else 'OFF'}"]
        for net, p in self.prs[:20]:
            try:
                r = self._eval(net, p)
                out.append(f"{esc(p.nama)}: spot {_pct(r.get('selisih_spot'))} vs wajar • beli {_pct(r.get('untung_beli'))}"
                           f" • {esc(r['aksi'])}")
            except Exception as e:  # noqa: BLE001
                out.append(f"{esc(p.nama)}: galat {esc(sensor(e)[:40])}")
        return "\n".join(out)

    def teks_log(self) -> str:
        if not self.s["log"]:
            return "Log kosong."
        return "\n".join(f"{jam(x['t'])} [{esc(x['jenis'])}] {esc(x['teks'])}" for x in self.s["log"][:20])

    def teks_tx(self) -> str:
        if not self.s["tx"]:
            return "Belum ada transaksi."
        return "\n".join(f"{jam(x['t'])} {esc(x['teks'])}\n{esc(x['tx'])}" for x in self.s["tx"][:15])

    # ------------------------------------------------------------------ loop
    def jalan(self, putaran: int | None = None) -> None:
        self.tg.mulai_polling(int(self.s.get("offset") or 0))
        self.kabar(f"🤖 <b>Bot token aktif</b> — mode {esc(self.mode)}, {len(self.prs)} pasangan.\n{self.bantuan()}",
                   menu=True)
        if self.s.get("pending"):
            self.kabar("🚨 Ada transaksi tidak pasti dari sesi lalu — /beres sebelum RESTART.")
        n = 0
        try:
            while putaran is None or n < putaran:
                self.putaran()
                n += 1
                time.sleep(1)
        finally:
            self.store.simpan()
            self.tg.berhenti()


# ---------------------------------------------------------------- pembuatan
def buat(cfg: dict, tg_mati: bool = False, store: Store | None = None):
    from .__main__ import _rpcs, pasangan
    mode = cfg.get("mode", "pantau")
    store = store or Store(DATA / mode)
    nets = {x["jaringan"] for x in cfg["pasangan"]}
    rpcs = _rpcs(cfg, nets)
    prs = pasangan(cfg, rpcs)
    dompet = None
    if mode == "live":
        if not cfg.get("live", {}).get("aktif"):
            raise SystemExit("mode live: set live.aktif: true di config (baca peringatan docs/ARB_BOT.md)")
        if len(nets) != 1:
            raise SystemExit("mode live: satu jaringan per proses")
        from .eksekusi import Dompet
        net = next(iter(nets))
        dompet = Dompet(rpcs[net], cfg["jaringan"][net]["chain_id"])
    if tg_mati or not cfg.get("telegram", {}).get("aktif", True):
        tg = TelegramMati()
    else:
        ids = [int(x) for x in os.environ.get("TELEGRAM_CHAT_ID", "").replace(";", ",").split(",") if x.strip()]
        if not ids:
            raise SystemExit("TELEGRAM_CHAT_ID kosong (token_bot/.env)")
        tg = Telegram(os.environ.get("TELEGRAM_TOKEN", ""), ids, int(cfg.get("telegram", {}).get("interval_poll", 25)))
    return Bot(cfg, store, rpcs, prs, tg, dompet)
