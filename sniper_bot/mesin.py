"""Mesin bot: loop utama, ukuran posisi, batas risiko, kelola posisi (TP/SL/batas waktu), perintah Telegram."""
from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone

from .broker import TidakBisa
from .telegram import esc

WIB = 7 * 3600


def jam(t: float) -> str:
    return datetime.fromtimestamp(t + WIB, timezone.utc).strftime("%d %b %H:%M WIB")


def usd(x: float) -> str:
    return f"${x:,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def px(x: float) -> str:
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

    # ------------------------------------------------------------------ angka
    @property
    def s(self) -> dict:
        return self.store.s

    def nilai_posisi(self, pos: dict) -> float:
        p = self.harga.get(pos["simbol"])
        return pos["qty"] * p if p else pos["usd"]

    def eksposur(self) -> float:
        return sum(self.nilai_posisi(p) for p in self.s["posisi"].values())

    def ekuitas(self) -> float:
        try:
            kas = self.broker.saldo_usd()
        except Exception:  # noqa: BLE001
            kas = 0.0
        return kas + self.eksposur()

    def _hari(self) -> dict:
        tgl = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%d")
        h = self.s["hari"]
        if h.get("tgl") != tgl:
            h.update({"tgl": tgl, "pnl": 0.0, "trade": 0, "jeda_rugi": False})
        return h

    def rugi_hari_ini(self) -> float:
        mengambang = sum(self.nilai_posisi(p) - p["usd"] for p in self.s["posisi"].values())
        return self._hari()["pnl"] + mengambang

    def boleh_buka(self, strategi: str, usd_rencana: float) -> str | None:
        """None bila boleh; selain itu alasan menolak."""
        r = self.cfg["risiko"]
        h = self._hari()
        if self.s["jeda"]:
            return "bot dijeda (/lanjut untuk membuka posisi baru lagi)"
        if strategi in self.s["strategi_mati"]:
            return f"strategi {strategi} dimatikan"
        if h["jeda_rugi"]:
            return "batas rugi harian tercapai — entry baru dijeda sampai besok (UTC)"
        if self.rugi_hari_ini() <= -float(r["stop_rugi_harian_usd"]):
            h["jeda_rugi"] = True
            self.kabar(f"⛔ <b>Batas rugi harian</b> {usd(-float(r['stop_rugi_harian_usd']))} tercapai. Entry baru dijeda "
                       f"sampai 07:00 WIB besok. Posisi terbuka tetap dikelola (TP/SL).")
            return "batas rugi harian tercapai"
        if len(self.s["posisi"]) >= int(r["maks_posisi"]):
            return f"maks {r['maks_posisi']} posisi"
        if h["trade"] >= int(r["maks_trade_per_hari"]):
            return f"maks {r['maks_trade_per_hari']} trade/hari"
        if self.eksposur() + usd_rencana > float(r["maks_total_usd"]) + 1e-9:
            return f"total posisi akan > {usd(float(r['maks_total_usd']))}"
        return None

    def ukuran(self, persen: float, batas_volume_usd: float | None = None) -> float:
        r = self.cfg["risiko"]
        u = min(persen * self.ekuitas(), float(r["maks_usd_per_trade"]),
                float(r["maks_total_usd"]) - self.eksposur())
        if batas_volume_usd is not None:
            u = min(u, batas_volume_usd)
        return max(u, 0.0)

    # ------------------------------------------------------------------ kabar
    def kabar(self, teks: str, **kw) -> None:
        try:
            self.tg.kirim(teks, **kw)
        except Exception as e:  # noqa: BLE001
            print("telegram gagal:", e, flush=True)

    def galat(self, kunci: str, e: Exception) -> None:
        """Galat dikabarkan maks sekali per jam per kunci."""
        print(f"[galat] {kunci}: {e}", flush=True)
        t = self.now()
        if t - self.galat_terakhir.get(kunci, 0) > 3600:
            self.galat_terakhir[kunci] = t
            self.kabar(f"⚠️ <b>Galat {esc(kunci)}</b>: {esc(str(e)[:300])}")

    # ------------------------------------------------------------------ buka / tutup
    def buka(self, strategi: str, simbol: str, base: str, harga_ref: float, usd_: float, tp: float | None,
             sl: float | None, hari_maks: float | None, limit: float | None = None, info: dict | None = None,
             label: str = "") -> dict | None:
        self.gagal_terakhir = None
        alasan = self.boleh_buka(strategi, usd_)
        if alasan:
            self.gagal_terakhir = alasan
            return None
        if usd_ < 5:
            self.gagal_terakhir = "ukuran < $5"
            return None
        try:
            isi = self.broker.beli(base, usd_, harga_ref, limit=limit)
        except TidakBisa as e:
            self.gagal_terakhir = f"bursa: {e}"
            self.kabar(f"⏭ {esc(strategi)} {esc(simbol)} dilewati: {esc(e)}")
            return None
        t = self.now()
        pid = self.store.id_baru("P")
        pos = {"id": pid, "strategi": strategi, "simbol": simbol, "base": base, "qty": isi.qty, "entry": isi.harga,
               "usd": isi.usd, "biaya": isi.biaya_usd, "t_buka": t, "order_beli": isi.order_id,
               "tp_px": isi.harga * (1 + tp) if tp else None, "sl_px": isi.harga * (1 - sl) if sl else None,
               "deadline": t + hari_maks * 86400 if hari_maks else None, "tp_order": None,
               "info": info or {}, "peringatan": [], "live": self.broker.live}
        if pos["tp_px"]:
            try:
                pos["tp_order"] = self.broker.pasang_tp(base, isi.qty, pos["tp_px"])
            except Exception as e:  # noqa: BLE001 - TP tetap dipantau bot bila order limit gagal
                self.galat(f"pasang TP {simbol}", e)
        self.s["posisi"][pid] = pos
        h = self._hari()
        h["trade"] += 1
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

    def tutup(self, pos: dict, harga_ref: float, alasan: str, isi=None) -> dict | None:
        """Tutup posisi: batalkan TP, jual pasar (kecuali isi sudah diberikan, mis. TP limit terisi)."""
        from .broker import Isi
        base = pos["base"]
        if isi is None:
            terisi, avg = 0.0, None
            if pos.get("tp_order"):
                try:
                    self.broker.batal(base, pos["tp_order"])
                except Exception as e:  # noqa: BLE001
                    self.galat(f"batal TP {pos['simbol']}", e)
                    return None
                st = self._cek_tp(pos)          # TP bisa terisi (sebagian) sebelum dibatalkan
                if st and st["status"] == "closed":
                    return self._tutup_tp(pos, st)
                if st and st["filled"] > 0:
                    terisi, avg = st["filled"], st["average"] or pos["tp_px"]
                pos["tp_order"] = None
            try:
                isi = self.broker.jual(base, pos["qty"] - terisi, harga_ref)
            except TidakBisa as e:
                self.galat(f"jual {pos['simbol']}", e)
                return None
            if terisi > 0:
                fee_tp = (st.get("biaya_usd") if st else 0) or terisi * avg * 0.001
                q = terisi + isi.qty
                nilai = terisi * avg + isi.usd
                isi = Isi(q, nilai / q, nilai, isi.biaya_usd + fee_tp)
        hasil = isi.usd - isi.biaya_usd - pos["usd"]
        tutup = self.store.tutup(pos["id"], {"t_tutup": self.now(), "keluar": isi.harga, "alasan": alasan,
                                             "pnl_usd": hasil, "ret": hasil / pos["usd"] if pos["usd"] else 0.0})
        self._hari()["pnl"] += hasil
        self.store.simpan()
        ikon = {"TP": "🏁", "SL": "🔴", "WAKTU": "⌛", "MANUAL": "✋"}.get(alasan, "🏁")
        hasil_teks = "PROFIT" if hasil > 0 else "MINUS"
        self.kabar(f"{ikon} <b>TUTUP {esc(pos['simbol'])}</b> • {hasil_teks} {usd(hasil)} ({pct(tutup['ret'])})\n"
                   f"Alasan {alasan} • masuk {px(pos['entry'])} → keluar {px(isi.harga)} • "
                   f"{(self.now() - pos['t_buka']) / 86400:.1f} hari • ID {pos['id']}")
        return tutup

    def _close_jam(self, pos: dict) -> float | None:
        """Close candle 1 jam TERAKHIR yang sudah tutup (dicek sekali per jam per posisi), atau None."""
        jam_ini = int(self.now() // 3600)
        if pos.get("jam_cek") == jam_ini:
            return None
        try:
            b = self.pasar.kline(pos["simbol"], "1h", limit=2)
        except Exception as e:  # noqa: BLE001
            self.galat(f"kline 1h {pos['simbol']}", e)
            return None
        tutup = [x for x in b if x.t + 3600 <= self.now()]
        if not tutup:
            return None
        pos["jam_cek"] = jam_ini
        return tutup[-1].c if tutup[-1].t >= pos["t_buka"] - 3600 else None

    def _cek_tp(self, pos: dict) -> dict | None:
        try:
            return self.broker.cek_order(pos["base"], pos["tp_order"])
        except Exception as e:  # noqa: BLE001
            self.galat(f"cek TP {pos['simbol']}", e)
            return None

    def _tutup_tp(self, pos: dict, st: dict):
        from .broker import Isi
        qty = st["filled"] or pos["qty"]
        harga = st["average"] or pos["tp_px"]
        biaya = st.get("biaya_usd") or qty * harga * 0.001
        sisa = pos["qty"] - qty
        if sisa > pos["qty"] * 0.01:       # sebagian kecil tidak terisi -> jual pasar
            try:
                i2 = self.broker.jual(pos["base"], sisa, self.harga.get(pos["simbol"], harga))
                qty_u, nilai = qty + i2.qty, qty * harga + i2.usd
                return self.tutup(pos, harga, "TP", Isi(qty_u, nilai / qty_u, nilai, biaya + i2.biaya_usd))
            except TidakBisa:
                pass
        return self.tutup(pos, harga, "TP", Isi(qty, harga, qty * harga, biaya))

    # ------------------------------------------------------------------ kelola posisi
    def kelola(self) -> None:
        t = self.now()
        for pos in list(self.s["posisi"].values()):
            p = self.harga.get(pos["simbol"])
            if p is None:
                continue
            # 1) TP: live = order limit di bursa; kertas = harga menyentuh TP
            if pos.get("tp_px"):
                if pos.get("tp_order") and self.broker.live:
                    st = self._cek_tp(pos)
                    if st and st["status"] == "closed":
                        self._tutup_tp(pos, st)
                        continue
                    if st and st["status"] == "canceled" and st["filled"] <= 0:
                        pos["tp_order"] = None      # dibatalkan dari luar -> bot memantau sendiri
                elif p >= pos["tp_px"]:
                    if self.broker.live:
                        self.tutup(pos, p, "TP")          # order TP gagal dipasang -> jual pasar
                    else:
                        self.tutup(pos, p, "TP", self.broker.isi_tp(pos["base"], pos["qty"], pos["tp_px"]))
                    continue
            # 2) SL — harga menit, atau (listing dip) hanya di close candle 1 jam agar tidak tersapu wick flash crash
            if pos.get("sl_px"):
                if (pos.get("info") or {}).get("sl_close_jam"):
                    c = self._close_jam(pos)
                    if c is not None and c <= pos["sl_px"]:
                        self.tutup(pos, p, "SL")
                        continue
                elif p <= pos["sl_px"]:
                    self.tutup(pos, p, "SL")
                    continue
            # 3) batas waktu
            if pos.get("deadline") and t >= pos["deadline"]:
                self.tutup(pos, p, "WAKTU")
                continue
            # 4) peringatan turun (angka teruji 💎: setelah -10% 66% tetap kena TP, setelah -20% 36%)
            turun = 1 - p / pos["entry"]
            for lv in self.cfg.get("spot_dip", {}).get("peringatan_turun", []) if pos["strategi"] == "spot_dip" else []:
                if turun >= lv and lv not in pos["peringatan"]:
                    pos["peringatan"].append(lv)
                    teruji = {0.10: "66% tetap kena TP (rata akhir −4%)", 0.20: "36% tetap kena TP (rata akhir −12%)"}
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
        for off, _u, cid, teks, cbid in self.tg.ambil():
            self.s["telegram_offset"] = off
            try:
                from .perintah import tangani
                tangani(self, cid, teks, cbid)
            except Exception as e:  # noqa: BLE001
                self.galat("perintah", e)
        if self.jatuh_tempo("harga", float(j["harga_dtk"])):
            try:
                self.perbarui_harga()
                self.kelola()
                for st in self.strategi.values():
                    st.tick_harga()
            except Exception as e:  # noqa: BLE001
                self.galat("harga", e)
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
        t = self.now()
        dt = datetime.fromtimestamp(t, timezone.utc)
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
        n = 0
        try:
            while putaran is None or n < putaran:
                self.satu_putaran()
                n += 1
                time.sleep(1)
        finally:
            self.store.simpan()
            self.tg.berhenti()
