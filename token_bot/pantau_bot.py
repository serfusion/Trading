"""Bot kontrol Telegram gaya screenshot (wetharb/circarb) untuk token_bot — python -m token_bot bot

Memantau pasangan pool vs harga ACUAN (harga wajar) dan, bila diizinkan, membeli saat jauh di bawah acuan / menjual
saat di atas (lihat token_bot/strategi.evaluasi: kuotasi NYATA Quoter, ukuran dikecilkan sampai slippage <= batas,
cek jual-balik honeypot). Dikendalikan lewat Telegram dengan tombol persis screenshot:
  💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART · ❓ Bantuan

Dua mode (config `mode`) — bot TIDAK pernah mengirim transaksi (tidak memakai private key):
  pantau  (bawaan) — hanya MENGABARI peluang. Eksekusi kamu lakukan sendiri di dompetmu.
  kertas            — simulasi: saldo & posisi palsu diisi di harga kuotasi, tanpa menyentuh dana (🅰 BUY ON).
                      Pasangan `tebus_manual` (token jembatan) disimulasikan keluar lewat tebus 1:1 - biaya_tebus.

PENTING (hasil riset docs/eksternal/hasil_arb_cari.txt & hasil_arb_latensi.txt): strategi "beli diskon lalu tebus 1:1
lewat jembatan" hanya menghasilkan di JENDELA PELUNCURAN chain/jembatan BARU (pra-publik); setelah publik sisa peluang
±$20-65/HARI untuk SEMUA pelaku dan direbut bot < 1 detik. Bot ini TIDAK menebus lewat jembatan (kustodial, berisiko) —
leg tebus dilakukan manual. Tidak ada janji profit.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

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
              "hari": None, "n_trade": 0, "offset": 0}

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
    MODE = ("pantau", "kertas")

    def __init__(self, cfg: dict, store: Store, rpcs: dict, prs: list, tg, sekarang=time.time):
        self.cfg, self.store, self.rpcs, self.prs, self.tg = cfg, store, rpcs, prs, tg
        self.now = sekarang
        self.mode = cfg.get("mode", "pantau")
        if self.mode not in self.MODE:
            raise SystemExit(f"mode {self.mode!r} tidak ada. Pilih pantau atau kertas — bot ini tidak mengirim "
                             f"transaksi nyata (eksekusi manual di dompetmu, docs/ARB_BOT.md).")
        self.jadwal: dict[str, float] = {}
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
                if self.jatuh_tempo(f"kabar {p.nama}", float(self.cfg.get("jeda_kabar", 60))):
                    self.kabar(self.teks_peluang(p, r))
            elif self.s["buy_on"]:
                self.beli(net, p, r)
            # kertas tanpa BUY ON: diam (sudah dicatat di log)

    def teks_peluang(self, p, r: dict) -> str:
        keluar = (f"tebus manual ≈ {r['nilai_tebus']:.6g}/token (setelah biaya jembatan)" if r.get("tebus_manual")
                  else "jual balik di DEX")
        return (f"🅰 <b>PELUANG BELI {esc(p.nama)}</b>\nHarga beli {r['harga_beli']:.6g} vs wajar {r['wajar']:.6g}: "
                f"diskon {_pct(r['untung_beli'])}, perkiraan bersih {_pct(r.get('untung_bersih'))} bila keluar lewat "
                f"{keluar}. Ukuran {_usd(r.get('ukuran_usd'))}, slippage {_pct(r.get('slippage_beli'))}.\n"
                f"Bot tidak membeli — eksekusi manual di dompetmu bila setuju (peluang biasanya hilang < 1 detik).")

    # ------------------------------------------------------------------ batas simulasi
    def boleh(self, usd: float) -> str | None:
        self._hari()
        maks_tr = int(self.cfg.get("maks_trade_per_hari", 50))
        if self.s["n_trade"] >= maks_tr:
            return f"batas {maks_tr} trade/hari"
        if usd > (self.s["kas_kertas"] or 0) + 1e-9:
            return "kas kertas kurang"
        return None

    # ------------------------------------------------------------------ beli / tutup
    def beli(self, net: str, p, r: dict) -> None:
        usd = r["ukuran_usd"]
        alasan = self.boleh(usd)
        if alasan:
            self.catat("lewat", f"{p.nama}: {alasan}")
            return
        self.s["kas_kertas"] -= usd
        qusd = float(r.get("quote_usd") or 1.0)          # harga 1 quote (USDG/USDC/WETH) dalam USD
        tok = usd / (r["harga_beli"] * qusd)
        self.s["n_trade"] += 1
        self.catat("beli", f"{p.nama} {usd:.2f} @ {r['harga_beli']:.6g}", tx="kertas")
        if r.get("tebus_manual"):
            # token jembatan: keluar = tebus 1:1 - biaya (manual, ±2 mnt). Simulasi menganggap tebus BERHASIL penuh —
            # kenyataannya bergantung satu operator kustodian (bisa pause/berhenti membayar).
            nilai = tok * r["nilai_tebus"] * qusd
            self.s["kas_kertas"] += nilai
            self.catat("tebus", f"{p.nama} {nilai - usd:+.2f} (simulasi tebus)", tx="kertas")
            self.kabar(f"🟢 <b>BELI + TEBUS (kertas) {esc(p.nama)}</b> {_usd(usd)} @ {r['harga_beli']:.6g} → tebus "
                       f"{_usd(nilai)} ({_usd(nilai - usd)}). Simulasi menganggap jembatan membayar penuh.")
            return
        self.s["posisi"][p.nama] = {"net": net, "token": tok, "harga": r["harga_beli"], "usd": usd, "t": self.now(),
                                    "quote_usd": qusd}
        self.kabar(f"🟢 <b>BELI (kertas) {esc(p.nama)}</b> {_usd(usd)} @ {r['harga_beli']:.6g} "
                   f"(diskon {_pct(r['untung_beli'])}, perkiraan bersih {_pct(r.get('untung_bersih'))})")

    def tutup(self, net: str, p, r: dict) -> None:
        pos = self.s["posisi"][p.nama]
        keluar = r.get("harga_jual") or r.get("wajar")
        nilai = pos["token"] * keluar * float(r.get("quote_usd") or pos.get("quote_usd") or 1.0)
        hasil = nilai - pos["usd"]
        self.s["kas_kertas"] += nilai
        self.s["posisi"].pop(p.nama)
        self.catat("jual", f"{p.nama} {hasil:+.2f} ({r['alasan']})", tx="kertas")
        self.kabar(f"💰 <b>JUAL (kertas) {esc(p.nama)}</b> {_usd(hasil)} ({esc(r['alasan'])})")

    # ------------------------------------------------------------------ perintah Telegram
    TOMBOL = {"💰 saldo": "/saldo", "📈 harga": "/harga", "📄 log": "/log", "🧾 tx": "/tx",
              "🅰 buy on/off": "/buy", "⏹ stop": "/stop", "🔄 restart": "/restart", "❓ bantuan": "/bantuan"}

    def perintah(self, cid: int, teks: str, cbid: str | None) -> None:
        if cbid:                                   # tidak ada tombol inline di bot ini
            self.tg.jawab_tombol(cbid, "Tidak dipakai.")
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
            self.s["stop"] = False
            self.jadwal.pop("pindai", None)
            self.kabar("🔄 <b>RESTART</b> — pemantauan jalan lagi.", chat_id=cid)
        elif cmd == "/buy":
            self.cmd_buy(cid)
        else:
            self.kabar("Perintah tidak dikenal. ❓ Bantuan", chat_id=cid)

    def cmd_buy(self, cid: int) -> None:
        if self.mode == "pantau":
            self.kabar("Mode <b>pantau</b>: bot hanya mengabari, tidak membeli. Ubah `mode: kertas` di config untuk "
                       "simulasi auto-beli. Transaksi nyata tidak didukung (eksekusi manual di dompetmu).", chat_id=cid)
            return
        self.s["buy_on"] = not self.s["buy_on"]
        if self.s["buy_on"]:
            self.kabar("🅰 <b>BUY ON (kertas)</b> — simulasi auto-beli aktif (uang palsu).", chat_id=cid)
        else:
            self.kabar("🅰 <b>BUY OFF</b> — simulasi auto-beli dimatikan (posisi kertas tetap dikelola).", chat_id=cid)

    # ------------------------------------------------------------------ teks
    def bantuan(self) -> str:
        return ("<b>Bot token (arbitrase token baru)</b>\n"
                f"Mode: <b>{esc(self.mode)}</b> • pasangan dipantau: {len(self.prs)}\n"
                "💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART\n"
                "Mengabari bila harga pool jauh di bawah acuan (kuotasi nyata, cek honeypot, untung BERSIH setelah "
                "biaya keluar). Bot TIDAK mengirim transaksi: mode pantau = kabar, kertas = simulasi uang palsu. "
                "Token jembatan (tebus_manual): keluar lewat tebus manual, bukan jual DEX.\n"
                "⚠️ Teruji: menguntungkan hanya di jendela peluncuran chain/jembatan BARU (pra-publik). Setelah publik "
                "peluang receh & diperebutkan bot < 1 dtk. Bukan janji profit.")

    def teks_saldo(self) -> str:
        if self.mode == "pantau":
            return "Mode <b>pantau</b> — tidak ada saldo (bot hanya mengabari). Cek saldo dompetmu sendiri."
        kas = self.s.get("kas_kertas")
        eks = sum(v["usd"] for v in self.s["posisi"].values())
        return (f"Mode <b>{esc(self.mode)}</b>\nKas kertas {_usd(kas)} • posisi {len(self.s['posisi'])} senilai {_usd(eks)}"
                + ("".join(f"\n• {esc(k)}: {_usd(v['usd'])} @ {v['harga']:.6g}" for k, v in self.s["posisi"].items())))

    def teks_harga(self) -> str:
        out = [f"Status: {'⏹ STOP' if self.s['stop'] else '▶️ jalan'} • BUY {'ON' if self.s['buy_on'] else 'OFF'}"]
        for net, p in self.prs[:20]:
            try:
                r = self._eval(net, p)
                out.append(f"{esc(p.nama)}: spot {_pct(r.get('selisih_spot'))} vs wajar • diskon {_pct(r.get('untung_beli'))}"
                           f" • bersih {_pct(r.get('untung_bersih'))} • {esc(r['aksi'])}")
            except Exception as e:  # noqa: BLE001
                out.append(f"{esc(p.nama)}: galat {esc(sensor(e)[:40])}")
        return "\n".join(out)

    def teks_log(self) -> str:
        if not self.s["log"]:
            return "Log kosong."
        return "\n".join(f"{jam(x['t'])} [{esc(x['jenis'])}] {esc(x['teks'])}" for x in self.s["log"][:20])

    def teks_tx(self) -> str:
        if not self.s["tx"]:
            return "Belum ada transaksi (kertas). Bot tidak mengirim transaksi nyata."
        return "\n".join(f"{jam(x['t'])} {esc(x['teks'])}\n{esc(x['tx'])}" for x in self.s["tx"][:15])

    # ------------------------------------------------------------------ loop
    def jalan(self, putaran: int | None = None) -> None:
        self.tg.mulai_polling(int(self.s.get("offset") or 0))
        self.kabar(f"🤖 <b>Bot token aktif</b> — mode {esc(self.mode)}, {len(self.prs)} pasangan.\n{self.bantuan()}",
                   menu=True)
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
    if mode not in Bot.MODE:
        raise SystemExit(f"mode {mode!r} tidak ada (pantau | kertas). Bot ini tidak mengirim transaksi nyata.")
    store = store or Store(DATA / mode)
    nets = {x["jaringan"] for x in cfg["pasangan"]}
    rpcs = _rpcs(cfg, nets)
    prs = pasangan(cfg, rpcs)
    if tg_mati or not cfg.get("telegram", {}).get("aktif", True):
        tg = TelegramMati()
    else:
        ids = [int(x) for x in os.environ.get("TELEGRAM_CHAT_ID", "").replace(";", ",").split(",") if x.strip()]
        if not ids:
            raise SystemExit("TELEGRAM_CHAT_ID kosong (token_bot/.env)")
        tg = Telegram(os.environ.get("TELEGRAM_TOKEN", ""), ids, int(cfg.get("telegram", {}).get("interval_poll", 25)))
    return Bot(cfg, store, rpcs, prs, tg)
