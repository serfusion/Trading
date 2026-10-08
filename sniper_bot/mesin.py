"""Mesin bot: loop utama, ukuran posisi, batas risiko, kelola posisi (TP/SL/batas waktu), perintah Telegram.

Keselamatan uang (hasil review adversarial 8 Okt 2026):
- order dicatat 'pending' SEBELUM dikirim; status tidak pasti (TidakPasti) -> bot DIJEDA, tidak pernah beli ulang otomatis;
- setiap posisi dikelola dalam try/except sendiri (satu posisi bermasalah tidak menghentikan SL posisi lain);
- isi sebagian (TP atau jual pasar) dicatat ke posisi; sisa di bawah minimum bursa = 'debu' (ditutup di catatan);
- rugi harian = rugi tertutup hari ini + perubahan nilai posisi SEJAK awal hari UTC (bukan rugi kumulatif sejak entry).
"""
from __future__ import annotations

import math
import time
import traceback
from datetime import datetime, timezone

from .broker import Isi, TidakBisa, TidakPasti, hingga
from .telegram import esc, sensor

WIB = 7 * 3600


def jam(t: float) -> str:
    return datetime.fromtimestamp(t + WIB, timezone.utc).strftime("%d %b %H:%M WIB")


def usd(x: float) -> str:
    return f"${x:,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def px(x: float | None) -> str:
    if x is None or not hingga(x):
        return "?"
    if x >= 100:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:,.4f}"
    return f"{x:.8f}".rstrip("0")


class Mesin:
    def __init__(self, cfg: dict, store, pasar, broker, tg, sekarang=time.time):
        self.cfg, self.store, self.pasar, self.broker, self.tg = cfg, store, pasar, broker, tg
        self.now = sekarang
        self.harga: dict[str, float] = {}
        self.t_harga = 0.0
        self.jadwal: dict[str, float] = {}
        self.galat_terakhir: dict[str, float] = {}
        self.strategi: dict = {}
        self.konfirmasi: dict[str, tuple[float, str]] = {}   # token tombol -> (waktu, perintah)
        self.gagal_terakhir: str | None = None
        self.gagal_sementara = False
        self.s.setdefault("pending", {})

    # ------------------------------------------------------------------ angka
    @property
    def s(self) -> dict:
        return self.store.s

    def harga_pos(self, pos: dict) -> float | None:
        p = self.harga.get(pos["simbol"])
        return p if p is not None else pos.get("harga_terakhir")

    def nilai_posisi(self, pos: dict) -> float:
        p = self.harga_pos(pos)
        return pos["qty"] * p if p else pos["usd"]

    def eksposur(self) -> float:
        return sum(self.nilai_posisi(p) for p in self.s["posisi"].values())

    def kas(self) -> float | None:
        try:
            k = self.broker.saldo_usd()
            return k if hingga(k) else None
        except Exception as e:  # noqa: BLE001
            self.galat("saldo", e)
            return None

    def ekuitas(self) -> float | None:
        k = self.kas()
        return None if k is None else k + self.eksposur()

    def _nilai_total(self, pos: dict) -> float:
        """Nilai posisi + hasil jual sebagian yang sudah diterima."""
        return self.nilai_posisi(pos) + pos.get("realisasi", 0.0)

    def _awal_hari(self) -> float:
        return math.floor(self.now() / 86400) * 86400

    def _hari(self) -> dict:
        tgl = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%d")
        h = self.s["hari"]
        if h.get("tgl") != tgl:
            h.update({"tgl": tgl, "pnl": 0.0, "trade": 0, "jeda_rugi": False})
            for p in self.s["posisi"].values():             # potret nilai awal hari (dasar rugi mengambang hari ini)
                p["awal_hari"] = {"tgl": tgl, "nilai": self._nilai_total(p)}
        return h

    def _dasar_hari(self, pos: dict) -> float:
        """Nilai acuan untung/rugi HARI INI: modal bila dibuka hari ini, selain itu nilai pada 00:00 UTC."""
        h = self._hari()
        if pos["t_buka"] >= self._awal_hari():
            return pos["usd"]
        a = pos.get("awal_hari") or {}
        if a.get("tgl") != h["tgl"]:
            a = pos["awal_hari"] = {"tgl": h["tgl"], "nilai": self._nilai_total(pos)}
        return a["nilai"]

    def rugi_hari_ini(self) -> float:
        """Untung/rugi tertutup hari ini + perubahan nilai posisi terbuka SEJAK 00:00 UTC (07:00 WIB)."""
        h = self._hari()
        return h["pnl"] + sum(self._nilai_total(p) - self._dasar_hari(p) for p in self.s["posisi"].values())

    def boleh_buka(self, strategi: str, usd_rencana: float) -> str | None:
        """None bila boleh; selain itu alasan menolak."""
        r = self.cfg["risiko"]
        h = self._hari()
        if self.s["pending"]:
            return "ada order berstatus tidak pasti — cek aplikasi bursa lalu /beres"
        if self.s["jeda"]:
            return "bot dijeda (/lanjut untuk membuka posisi baru lagi)"
        if strategi in self.s["strategi_mati"]:
            return f"strategi {strategi} dimatikan"
        if not (hingga(usd_rencana) and usd_rencana > 0):
            return "ukuran tidak valid"
        if h["jeda_rugi"]:
            return "batas rugi harian tercapai — entry baru dijeda sampai 07:00 WIB"
        if self.rugi_hari_ini() <= -float(r["stop_rugi_harian_usd"]):
            h["jeda_rugi"] = True
            self.kabar(f"⛔ <b>Batas rugi harian</b> {usd(-float(r['stop_rugi_harian_usd']))} tercapai (rugi tertutup + "
                       f"perubahan nilai posisi sejak 07:00 WIB). Entry baru dijeda sampai 07:00 WIB besok; posisi "
                       f"terbuka tetap dikelola.")
            return "batas rugi harian tercapai"
        if len(self.s["posisi"]) >= int(r["maks_posisi"]):
            return f"maks {r['maks_posisi']} posisi"
        if h["trade"] >= int(r["maks_trade_per_hari"]):
            return f"maks {r['maks_trade_per_hari']} trade/hari"
        if self.eksposur() + usd_rencana > float(r["maks_total_usd"]) + 1e-9:
            return f"total posisi akan > {usd(float(r['maks_total_usd']))}"
        return None

    def ukuran(self, persen: float, batas_volume_usd: float | None = None) -> tuple[float, float]:
        """(ukuran yang diizinkan batas risiko & kas, ukuran target teruji = persen x ekuitas)."""
        r = self.cfg["risiko"]
        kas = self.kas()
        if kas is None:
            return 0.0, 0.0
        target = persen * (kas + self.eksposur())
        u = min(target, float(r["maks_usd_per_trade"]), float(r["maks_total_usd"]) - self.eksposur(), kas * 0.99)
        if batas_volume_usd is not None:
            u = min(u, batas_volume_usd)
        return max(u, 0.0), target

    # ------------------------------------------------------------------ kabar
    def kabar(self, teks: str, **kw) -> None:
        try:
            self.tg.kirim(teks, **kw)
        except Exception as e:  # noqa: BLE001
            print("telegram gagal:", e, flush=True)

    def galat(self, kunci: str, e: Exception | str) -> None:
        """Galat dikabarkan maks sekali per jam per kunci."""
        teks = sensor(e)
        print(f"[galat] {kunci}: {teks}", flush=True)
        t = self.now()
        if t - self.galat_terakhir.get(kunci, 0) > 3600:
            self.galat_terakhir[kunci] = t
            self.kabar(f"⚠️ <b>Galat {esc(kunci)}</b>: {esc(teks[:300])}")

    def darurat(self, judul: str, e: Exception) -> None:
        """Status order tidak pasti: jeda total + kabar segera (tidak dibatasi)."""
        self.s["jeda"] = True
        self.store.simpan()
        print(f"[darurat] {judul}: {sensor(e)}", flush=True)
        self.kabar(f"🚨 <b>{esc(judul)}</b>\n{esc(sensor(e)[:400])}\nBot DIJEDA (tidak ada order baru). Buka aplikasi "
                   f"bursa: cek riwayat order & saldo koin. Lalu kirim /beres (dan /lanjut) setelah kamu yakin.")

    # ------------------------------------------------------------------ buka
    def buka(self, strategi: str, simbol: str, base: str, harga_ref: float, usd_: float, tp: float | None,
             sl: float | None, hari_maks: float | None, limit: float | None = None, info: dict | None = None,
             label: str = "") -> dict | None:
        self.gagal_terakhir, self.gagal_sementara = None, False
        alasan = self.boleh_buka(strategi, usd_)
        if alasan:
            self.gagal_terakhir = alasan
            return None
        if usd_ < 5:
            self.gagal_terakhir = "ukuran < $5"
            return None
        pid = self.store.id_baru("P")
        cid = f"sb{pid}x{int(self.now())}"
        self.s["pending"][cid] = {"strategi": strategi, "simbol": simbol, "usd": usd_, "t": self.now(), "pid": pid}
        self.store.simpan()
        try:
            isi = self.broker.beli(base, usd_, harga_ref, limit=limit, client_id=cid)
        except TidakBisa as e:
            self.s["pending"].pop(cid, None)
            self.gagal_terakhir, self.gagal_sementara = f"bursa: {e}", e.sementara
            if not e.sementara:
                self.kabar(f"⏭ {esc(strategi)} {esc(simbol)} dilewati: {esc(sensor(e))}")
            return None
        except Exception as e:  # noqa: BLE001 - TidakPasti atau galat tak terduga: order mungkin terisi
            self.s["pending"][cid]["galat"] = sensor(e)[:200]
            self.gagal_terakhir = "tidak pasti"
            self.darurat(f"Order BELI {simbol} ${usd_:.2f} berstatus tidak pasti (id {cid})", e)
            return None
        t = self.now()
        pos = {"id": pid, "strategi": strategi, "simbol": simbol, "base": base, "qty": isi.qty, "qty_awal": isi.qty,
               "entry": isi.harga, "usd": isi.usd, "biaya": isi.biaya_usd, "realisasi": 0.0, "t_buka": t,
               "order_beli": isi.order_id, "tp_px": isi.harga * (1 + tp) if tp else None,
               "sl_px": isi.harga * (1 - sl) if sl else None,
               "deadline": t + hari_maks * 86400 if hari_maks else None, "tp_order": None,
               "info": info or {}, "peringatan": [], "live": self.broker.live, "harga_terakhir": isi.harga,
               "cek_ms": (math.floor(t / 60) + 1) * 60_000, "jam_dari": math.floor(t / 3600) * 3600}
        self.s["posisi"][pid] = pos
        self.s["pending"].pop(cid, None)
        self._hari()["trade"] += 1
        self.store.simpan()                                   # catat SEBELUM memasang TP
        if pos["tp_px"]:
            try:
                pos["tp_order"] = self.broker.pasang_tp(base, isi.qty, pos["tp_px"])
            except TidakPasti as e:
                pos["tp_ragu"] = True
                self.kabar(f"⚠️ TP {esc(simbol)} mungkin terpasang/tidak ({esc(sensor(e))}). Cek order terbuka di bursa; bot "
                           f"memantau harga TP sendiri.")
            except Exception as e:  # noqa: BLE001 - TP dipantau bot bila order limit gagal
                self.galat(f"pasang TP {simbol}", e)
            self.store.simpan()
        mode = "LIVE" if self.broker.live else "KERTAS"
        self.kabar(
            f"🟢 <b>BELI {esc(simbol)}</b> ({esc(label or strategi)}, {mode})\n"
            f"Harga {px(isi.harga)} • {usd(isi.usd)} • {isi.qty:.6g} {esc(base)}\n"
            + (f"TP {px(pos['tp_px'])} ({pct(tp)})" if tp else "TP -")
            + (f" • SL {px(pos['sl_px'])} ({pct(-sl)})" if sl else " • tanpa SL")
            + (f" • batas {jam(pos['deadline'])}" if pos["deadline"] else "")
            + f"\nID {pid}")
        return pos

    # ------------------------------------------------------------------ tutup
    def _catat_jual(self, pos: dict, isi: Isi) -> None:
        pos["realisasi"] = pos.get("realisasi", 0.0) + isi.usd - isi.biaya_usd
        pos["qty"] = max(pos["qty"] - isi.qty, 0.0)

    def _habis(self, pos: dict) -> bool:
        p = self.harga_pos(pos) or pos["entry"]
        return pos["qty"] <= pos.get("qty_awal", pos["qty"]) * 0.005 or pos["qty"] * p < 0.5

    def _akhiri(self, pos: dict, alasan: str, harga_keluar: float, catatan: str = "") -> dict:
        hasil = pos.get("realisasi", 0.0) - pos["usd"]
        if pos["qty"] > 0 and catatan:          # debu tersisa: dinilai pada harga pasar di catatan saja
            hasil += pos["qty"] * (self.harga_pos(pos) or 0)
        dasar = self._dasar_hari(pos)
        tutup = self.store.tutup(pos["id"], {"t_tutup": self.now(), "keluar": harga_keluar, "alasan": alasan,
                                             "pnl_usd": hasil, "ret": hasil / pos["usd"] if pos["usd"] else 0.0,
                                             "catatan": catatan})
        self._hari()["pnl"] += pos["usd"] + hasil - dasar
        self.store.simpan()
        ikon = {"TP": "🏁", "SL": "🔴", "WAKTU": "⌛", "MANUAL": "✋", "DEBU": "🧹"}.get(alasan, "🏁")
        self.kabar(f"{ikon} <b>TUTUP {esc(pos['simbol'])}</b> • {'PROFIT' if hasil > 0 else 'MINUS'} {usd(hasil)} "
                   f"({pct(tutup['ret'])})\nAlasan {alasan} • masuk {px(pos['entry'])} → keluar {px(harga_keluar)} • "
                   f"{(self.now() - pos['t_buka']) / 86400:.1f} hari • ID {pos['id']}"
                   + (f"\n{esc(catatan)}" if catatan else ""))
        return tutup

    def _ambil_tp_terisi(self, pos: dict) -> bool:
        """Batalkan order TP & catat bagian yang sudah terisi. False bila status tidak bisa dipastikan (coba lagi)."""
        if not pos.get("tp_order"):
            return True
        try:
            self.broker.batal(pos["base"], pos["tp_order"])
            st = self.broker.cek_order(pos["base"], pos["tp_order"])
        except Exception as e:  # noqa: BLE001
            self.galat(f"batal/cek TP {pos['simbol']}", e)
            return False
        if st["filled"] > 0:
            avg = st["average"] or pos["tp_px"]
            self._catat_jual(pos, Isi(min(st["filled"], pos["qty"]), avg, st["filled"] * avg, st.get("biaya_usd") or 0.0))
        pos["tp_order"] = None
        self.store.simpan()
        return st["status"] != "open"

    def tutup(self, pos: dict, harga_ref: float, alasan: str, isi: Isi | None = None) -> dict | None:
        """Tutup posisi. isi diberikan bila TP limit terisi (kertas); selain itu batalkan TP & jual pasar."""
        if isi is not None:
            self._catat_jual(pos, isi)
            return self._akhiri(pos, alasan, isi.harga)
        if not self._ambil_tp_terisi(pos):
            return None
        if self._habis(pos):
            return self._akhiri(pos, alasan if alasan != "MANUAL" else "TP", pos.get("tp_px") or harga_ref)
        try:
            isi = self.broker.jual(pos["base"], pos["qty"], harga_ref)
        except TidakBisa as e:
            if "minimum" in str(e):
                return self._akhiri(pos, "DEBU", harga_ref, f"sisa {pos['qty']:.6g} {pos['base']} di bawah minimum "
                                                            f"bursa — jual manual / 'convert small balance'")
            self.galat(f"jual {pos['simbol']} (bila sudah dijual manual di bursa: /hapus {pos['id']})", e)
            return None
        except Exception as e:  # noqa: BLE001 - TidakPasti
            pos["tidak_pasti"] = True
            self.darurat(f"Order JUAL {pos['simbol']} ({pos['id']}) berstatus tidak pasti", e)
            return None
        self._catat_jual(pos, isi)
        if isi.diminta and isi.qty < isi.diminta * 0.99 and not self._habis(pos):
            self.store.simpan()
            self.kabar(f"◐ {esc(pos['simbol'])} terjual sebagian ({isi.qty:.6g} dari {isi.diminta:.6g}); sisa dicoba "
                       f"lagi putaran berikutnya.")
            return None
        return self._akhiri(pos, alasan, isi.harga)

    # ------------------------------------------------------------------ pemantauan
    def _tp_kertas(self, pos: dict) -> float | None:
        """Kertas: limit TP terisi bila high candle 1 menit sejak cek terakhir >= TP (wick ikut, seperti riset);
        harga isi = max(open, TP). Cadangan bila kline kosong/gagal: harga sekarang >= TP."""
        try:
            bars = self.pasar.kline(pos["simbol"], "1m", start_ms=int(pos["cek_ms"]), limit=1000)
        except Exception:  # noqa: BLE001
            bars = []
        for b in bars:
            if b.t * 1000 >= pos["cek_ms"] and b.h >= pos["tp_px"]:
                return max(b.o, pos["tp_px"])
        if bars:
            pos["cek_ms"] = max(pos["cek_ms"], int(bars[-1].t * 1000))     # candle terakhir belum tutup: cek ulang
        p = self.harga.get(pos["simbol"])
        return pos["tp_px"] if p is not None and p >= pos["tp_px"] else None

    def _sl_close_jam(self, pos: dict) -> tuple[float, bool] | None:
        """Listing dip: (close, terlambat?) candle 1 jam TUTUP pertama sejak cek terakhir dengan close <= SL."""
        if self.now() < pos["jam_dari"] + 3600:
            return None
        try:
            bars = self.pasar.kline(pos["simbol"], "1h", start_ms=int(pos["jam_dari"] * 1000), limit=1000)
        except Exception as e:  # noqa: BLE001
            self.galat(f"kline 1h {pos['simbol']}", e)
            return None
        tutup = [b for b in bars if b.t >= pos["jam_dari"] and b.t + 3600 <= self.now()]
        for i, b in enumerate(tutup):
            if b.c <= pos["sl_px"]:
                return b.c, i < len(tutup) - 1
        if tutup:
            pos["jam_dari"] = tutup[-1].t + 3600
        return None

    def kelola(self) -> None:
        for pos in list(self.s["posisi"].values()):
            try:
                self._kelola_satu(pos)
            except Exception as e:  # noqa: BLE001 - satu posisi tidak boleh menghentikan yang lain
                self.galat(f"kelola {pos.get('simbol')}", e)
                traceback.print_exc()

    def _kelola_satu(self, pos: dict) -> None:
        if pos.get("tidak_pasti"):
            return
        t = self.now()
        p = self.harga.get(pos["simbol"])
        if p is None and self.broker.live:
            p = self.broker.harga_venue(pos["base"])
        if p is None:
            p = pos.get("harga_terakhir")
            if pos.get("deadline") and t >= pos["deadline"] and not pos.get("tanpa_harga_dikabari"):
                pos["tanpa_harga_dikabari"] = True
                self.kabar(f"⚠️ {esc(pos['simbol'])} tidak punya harga (delisting/ganti simbol?). Batas waktu lewat — "
                           f"jual manual di bursa lalu /hapus {pos['id']}.")
            if p is None:
                return
        else:
            pos["harga_terakhir"] = p
        # 1) TP
        if pos.get("tp_px"):
            if pos.get("tp_order") and self.broker.live:
                st = self.broker.cek_order(pos["base"], pos["tp_order"])
                if st["status"] == "closed":
                    avg = st["average"] or pos["tp_px"]
                    self._catat_jual(pos, Isi(min(st["filled"], pos["qty"]), avg, st["filled"] * avg,
                                              st.get("biaya_usd") or 0.0))
                    pos["tp_order"] = None
                    if self._habis(pos):
                        self._akhiri(pos, "TP", avg)
                    else:
                        self.tutup(pos, p, "TP")
                    return
                if st["status"] != "open":                     # canceled/expired/rejected (dari luar bot)
                    if st["filled"] > 0:
                        avg = st["average"] or pos["tp_px"]
                        self._catat_jual(pos, Isi(min(st["filled"], pos["qty"]), avg, st["filled"] * avg,
                                                  st.get("biaya_usd") or 0.0))
                    pos["tp_order"] = None
                    if self._habis(pos):
                        self._akhiri(pos, "TP", avg if st["filled"] > 0 else p)
                        return
                    try:
                        pos["tp_order"] = self.broker.pasang_tp(pos["base"], pos["qty"], pos["tp_px"])
                        self.kabar(f"🔁 TP {esc(pos['simbol'])} berstatus {st['status']} → dipasang ulang.")
                    except Exception as e:  # noqa: BLE001
                        self.galat(f"pasang ulang TP {pos['simbol']}", e)
                    self.store.simpan()
            elif self.broker.live:
                if p >= pos["tp_px"]:
                    self.tutup(pos, p, "TP")                    # order TP tidak ada -> jual pasar
                    return
            else:
                isi_px = self._tp_kertas(pos)
                if isi_px is not None:
                    self.tutup(pos, p, "TP", self.broker.isi_tp(pos["base"], pos["qty"], isi_px))
                    return
        # 2) SL — harga menit, atau (listing dip) close candle 1 jam agar tidak tersapu wick flash crash
        if pos.get("sl_px"):
            if (pos.get("info") or {}).get("sl_close_jam"):
                hit = self._sl_close_jam(pos)
                if hit:
                    self.tutup(pos, p, "SL")
                    return
            elif p <= pos["sl_px"]:
                self.tutup(pos, p, "SL")
                return
        # 3) batas waktu
        if pos.get("deadline") and t >= pos["deadline"]:
            self.tutup(pos, p, "WAKTU")
            return
        # 4) peringatan turun 💎 (angka teruji varian jujur D, sejak Okt 2021; docs/eksternal/spek_spot_dip_bot.txt)
        if pos["strategi"] == "spot_dip":
            turun = 1 - p / pos["entry"]
            teruji = {0.10: "63% posisi seperti ini tetap kena TP (rata akhir −5%)",
                      0.20: "39% tetap kena TP (rata akhir −12%)"}
            for lv in self.cfg.get("spot_dip", {}).get("peringatan_turun", []):
                if turun >= lv and lv not in pos["peringatan"]:
                    pos["peringatan"].append(lv)
                    self.kabar(f"⚠️ {esc(pos['simbol'])} turun {pct(-turun)} dari harga beli. Teruji: "
                               f"{teruji.get(lv, '')}. Riset: menjual saat turun MEMPERBURUK hasil — bot menahan.")

    # ------------------------------------------------------------------ loop
    def perbarui_harga(self) -> None:
        self.harga = self.pasar.harga_semua()
        self.t_harga = self.now()

    def jatuh_tempo(self, kunci: str, detik: float) -> bool:
        t = self.now()
        if t - self.jadwal.get(kunci, 0) >= detik:
            self.jadwal[kunci] = t
            return True
        return False

    def satu_putaran(self) -> None:
        j = self.cfg["jadwal"]
        for off, u, cid, teks, cbid in self.tg.ambil():
            self.s["telegram_offset"] = off
            if u is None:                                     # bukan pemilik: dibuang
                continue
            try:
                from .perintah import tangani
                tangani(self, cid, teks, cbid)
            except Exception as e:  # noqa: BLE001
                self.galat("perintah", e)
        if self.jatuh_tempo("harga", float(j["harga_dtk"])):
            try:
                self.perbarui_harga()
            except Exception as e:  # noqa: BLE001
                self.galat("harga", e)
            self._hari()
            self.kelola()
            for st in self.strategi.values():
                try:
                    st.tick_harga()
                except Exception as e:  # noqa: BLE001
                    self.galat(f"{st.nama} harga", e)
                    traceback.print_exc()
        for st in self.strategi.values():
            try:
                st.tick_jadwal()
            except Exception as e:  # noqa: BLE001
                self.galat(st.nama, e)
                traceback.print_exc()
        self.ringkasan_harian()
        self.store.simpan()

    def ringkasan_harian(self) -> None:
        dt = datetime.fromtimestamp(self.now(), timezone.utc)
        kunci = dt.strftime("%Y-%m-%d")
        if dt.hour < int(self.cfg["jadwal"]["ringkasan_jam_utc"]) or self.s.get("ringkasan_tgl") == kunci:
            return
        self.s["ringkasan_tgl"] = kunci
        from .perintah import teks_status
        self.kabar("📅 <b>Ringkasan harian</b>\n" + teks_status(self))

    def jalan(self, putaran: int | None = None) -> None:
        self.tg.mulai_polling(int(self.s.get("telegram_offset") or 0))
        mode = "LIVE 💸" if self.broker.live else "KERTAS (simulasi)"
        self.kabar(f"🤖 <b>Sniper bot aktif</b> — mode {mode}, bursa {esc(self.broker.nama)}.\n"
                   f"Strategi: {', '.join(esc(n) for n in self.strategi)}. Ketik /bantuan.", menu=True)
        if self.s["pending"]:
            self.kabar("🚨 Ada order berstatus tidak pasti dari sesi sebelumnya — entry baru ditahan. Cek bursa, lalu "
                       "/beres.")
        n = 0
        try:
            while putaran is None or n < putaran:
                self.satu_putaran()
                n += 1
                time.sleep(1)
        finally:
            self.store.simpan()
            self.tg.berhenti()
