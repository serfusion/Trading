"""Endpoint tab Tanya untuk aplikasi Android — penjawab berbasis DATA, tanpa AI (lihat _chat.py).

POST /api/chat   {"messages": [{"role": "user", "content": "NFP Act: 45K Cons: 98K Prev: 162K"}, ...]}
GET  /api/chat   (dengan header kunci) -> {"ok": true, "calendar": [...], "tren": {...}, "persiapan": {...},
                 "arsip": {...}}: berita USD high-impact minggu ini (Act otomatis dari FRED setelah rilis), status tren
                 per indikator, kartu 🎯 (perkiraan hari H dari Kalshi+Polymarket / hasil setelah Act, _hari_h.py; Fed
                 berikutnya), Act berlapis (_aktual.py), dan status arsip berita ke GitHub (_arsip.py)
GET  /api/chat?riwayat=1 / ?copytrader=1 -> isi riwayat.json (📜) / copytrader.json (👥 copy trader teruji) saja
GET  /api/chat?copyposisi=<situs>|<id> -> rangkuman posisi terbuka & 10 trade terakhir trader itu (_copyposisi.py)
GET  /api/chat?ikuti=1 -> trader yang diikuti + posisi terbuka + kejadian BUKA/TUTUP terbaru (_ikuti.py)
POST /api/chat {"ikuti": {"platform", "id", "name", "url", "on": true|false}} -> follow / unfollow (maks 20)
Header wajib: X-Chat-Key: <CHAT_KEY>, atau (bila CHAT_KEY kosong) topik ntfy yang sama dengan aplikasi.
Balasan: {"ok": true, "reply": "...", "sources": [], "model": "data (tanpa AI)"}
"""
import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

import _aktual  # noqa: E402
import _arsip  # noqa: E402
import _chat  # noqa: E402
import _core  # noqa: E402
import _hari_h  # noqa: E402
import _kalshi  # noqa: E402
import _polymarket  # noqa: E402
import _pudar  # noqa: E402
import _persiapan  # noqa: E402
import _tren  # noqa: E402

TREN_TTL = timedelta(hours=3)
# 15 Okt 2026 (pengguna: "news di bawah XAU lama muncul, terkadang tidak muncul, saya mau langsung muncul"): GET membaca ±20
# baris Supabase SATU PER SATU (tiap baca = 1 perjalanan Vercel ↔ Supabase) → kini dibaca sekaligus dalam 1 permintaan.
BARIS_GET = ("kalender", "aktual", "arsip", "tren", "kalshi", "kalshi_sebaran", "polymarket", "polymarket_fed", "hari_h",
             "pernyataan", "prarilis", "petunjuk", "petunjuk_sumber", "nfp_titik", "cpi_detik", "cpi_tren", "ppi_wti",
             "ppi_cpi", "pra_tren", "sentimen", "hasil_rilis", "pudar", "pudar_btc", "perang")
# langkah INFO yang boleh dilewati bila GET sudah lama (aplikasi menunggu maks 40 dtk; isi lain tetap terkirim)
ANGGARAN_DTK = 20.0


class MemoStore:
    """Supabase dengan baca sekaligus di awal permintaan; get_state melayani dari memori (salinan), save_state menulis ke
    Supabase + memori. Gagal baca sekaligus → kembali ke baca per baris (perilaku lama)."""

    def __init__(self, store, rows=BARIS_GET):
        self.store, self.memo, self.ada = store, {}, set()
        try:
            self.memo = store.get_many(rows)
            self.ada = set(rows)
        except Exception:  # noqa: BLE001 - opsional, baca per baris
            self.memo, self.ada = {}, set()

    def get_state(self, row: str = "main") -> dict:
        if row not in self.ada:
            self.memo[row] = self.store.get_state(row) or {}
            self.ada.add(row)
        return copy.deepcopy(self.memo.get(row) or {})

    def save_state(self, data: dict, row: str = "main") -> None:
        self.store.save_state(data, row)
        self.memo[row] = copy.deepcopy(data)
        self.ada.add(row)

    def __getattr__(self, name):          # log, get_control, … diteruskan
        return getattr(self.store, name)


def _states() -> tuple[dict, dict]:
    """(state XAU/BTC, cache funding) dari Supabase; kosong bila belum diatur / gagal (konteks opsional)."""
    env = os.environ
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY")):
        return {}, {}
    store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    out, funding = {}, {}
    for key, row in (("XAU/USD", "main"), ("BTC/USD", "btc"), ("funding", "funding")):
        try:
            data = store.get_state(row)
        except Exception:  # noqa: BLE001
            data = {}
        if key == "funding":
            funding = data or {}
        else:
            out[key] = data
    return out, funding


def _store():
    env = os.environ
    if env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY"):
        return _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    return None


def _calendar(store, now: datetime) -> list | None:
    """Kalender ForexFactory, cache Supabase 10 menit (hemat & tidak kena limit saat banyak aplikasi dibuka)."""
    try:
        return _arsip.calendar_cached(store, now, _chat.fetch_calendar)
    except Exception:  # noqa: BLE001 - cache opsional
        return _chat.fetch_calendar()


def _tren_status(now: datetime, store=None) -> dict:
    """Status tren per indikator (tab News), cache 3 jam di baris Supabase 'tren' (hemat kuota Twelve Data)."""
    env = os.environ
    if not env.get("TWELVEDATA_API_KEY"):
        return {}
    if store is None and env.get("SUPABASE_URL") and env.get("SUPABASE_SERVICE_KEY"):
        store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    if store is not None:
        try:
            cached = store.get_state("tren") or {}
            if cached.get("dihitung") and now - datetime.fromisoformat(cached["dihitung"]) < TREN_TTL:
                return cached
        except Exception:  # noqa: BLE001 - cache opsional
            pass
    data = _tren.compute(env["TWELVEDATA_API_KEY"], now)
    if store is not None:
        try:
            store.save_state(data, "tren")
        except Exception:  # noqa: BLE001
            pass
    return data


def isi_act(persiapan: dict, calendar: list) -> None:
    """Salin Act resmi kalender (_aktual.fill) ke kartu persiapan yang sama (judul + waktu) bila kartu belum punya Act."""
    act = {(c.get("title"), c.get("time")): c for c in calendar or [] if isinstance(c, dict) and c.get("actual")}
    for k in ("berita", "mendatang"):
        for c in persiapan.get(k) or []:
            if isinstance(c, dict) and not c.get("actual") and (c.get("title"), c.get("time")) in act:
                src = act[(c["title"], c["time"])]
                c["actual"], c["actual_src"] = src["actual"], src.get("actual_src")


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        key = os.environ.get("CHAT_KEY") or os.environ.get("NTFY_TOPIC", "")
        return bool(key) and self.headers.get("X-Chat-Key", "") == key

    def do_POST(self):
        if not self._authorized():
            self._send(401, {"ok": False, "error": "Kunci chat salah (pakai topik ntfy yang sama dengan cloud)"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(length, 200_000)) or b"{}")
            if isinstance(body.get("ikuti"), dict):           # 👥 follow / unfollow copy trader (7 Okt 2026)
                import _ikuti
                store = _store()
                self._send(200, _ikuti.atur(store, body["ikuti"]) if store is not None
                           else {"ok": False, "error": "Supabase belum diatur"})
                return
            if isinstance(body.get("manual"), dict):          # Act isian manual dari kartu 🎯 (2 Okt 2026)
                m, store = body["manual"], _store()
                if store is None:
                    self._send(200, {"ok": False, "error": "Supabase belum diatur"})
                    return
                self._send(200, _aktual.save_manual(store, str(m.get("title", "")), str(m.get("time", "")),
                                                    str(m.get("actual", ""))[:300], datetime.now(timezone.utc)))
                return
            states, funding = _states()
            now = datetime.now(timezone.utc)
            self._send(200, _chat.answer(body.get("messages") or [], now, _calendar(_store(), now), states, funding))
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})

    def do_GET(self):
        if not self._authorized():
            self._send(200, {"ok": True, "info": "POST {messages: [...]} dengan header X-Chat-Key"})
            return
        if "ikuti=1" in (self.path or ""):              # 👥 status follow copy trader (_ikuti.py)
            import _ikuti
            store = _store()
            try:
                self._send(200, _ikuti.status(store) if store is not None
                           else {"ok": False, "error": "Supabase belum diatur"})
            except Exception as exc:  # noqa: BLE001
                self._send(200, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})
            return
        if "copyposisi=" in (self.path or ""):          # 👥 rangkuman posisi & riwayat 1 copy trader (_copyposisi.py)
            from urllib.parse import parse_qs, urlparse
            import _copyposisi
            v = (parse_qs(urlparse(self.path).query).get("copyposisi") or [""])[0]
            platform, _, id_ = v.partition("|")
            if not platform or not id_ or len(v) > 120:
                self._send(200, {"ok": False, "catatan": "parameter copyposisi=<situs>|<id>"})
                return
            self._send(200, _copyposisi.copyposisi(platform, id_))
            return
        for q, name in (("riwayat=1", "riwayat"), ("copytrader=1", "copytrader")):
            if q not in (self.path or ""):              # 📜 riwayat 💰 (tab Statistik) / 👥 copy trader teruji (tab Sinyal,
                continue                                # research/copy_pilih.py, diperbarui GitHub Actions mingguan) — ringan
            path = os.path.join(os.path.dirname(__file__), f"{name}.json")
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if name == "riwayat":                   # 📊 peringkat semua sinyal & label (research/peringkat.py)
                    try:
                        with open(os.path.join(os.path.dirname(__file__), "peringkat.json"), encoding="utf-8") as f:
                            data["peringkat"] = json.load(f)
                    except (OSError, ValueError):
                        pass
                self._send(200, {"ok": True, name: data})
            except Exception as exc:  # noqa: BLE001
                self._send(200, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})
            return
        try:
            now = datetime.now(timezone.utc)
            mulai = time.monotonic()
            dilewati: list[str] = []

            def sempat(nama: str) -> bool:
                """Langkah INFO dijalankan hanya bila GET belum melewati anggaran (baris XAU harus cepat sampai)."""
                if time.monotonic() - mulai <= ANGGARAN_DTK:
                    return True
                dilewati.append(nama)
                return False

            store = _store()
            if store is not None:
                store = MemoStore(store)
            try:
                tren = _tren_status(now, store)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim walau status tren gagal
                tren = {"error": _arsip.redact(f"{type(exc).__name__}: {exc}")}
            rows = _calendar(store, now)
            try:
                persiapan = _persiapan.cards(rows, now)     # 🎯 kartu persiapan berita (pengganti contoh pertanyaan)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim walau kartu gagal
                persiapan = {"error": _arsip.redact(f"{type(exc).__name__}: {exc}")}
            if isinstance(persiapan, dict) and persiapan.get("berita"):
                try:                                          # 🎲 peluang Kalshi per berita (cache 15 menit)
                    _kalshi.attach(persiapan, store, now)
                except Exception:  # noqa: BLE001 - Kalshi opsional
                    pass
            calendar = _chat.calendar_json(rows, now, fetch=lambda s: [])
            # 15 Okt: kartu 🎯 juga memuat berita berdampak SEDANG (mis. klaim pengangguran) yang tidak ada di kalender tab News
            # (High saja) → dulu Act-nya tidak pernah diambil ("menunggu Act…"). Diisi bersama, tetapi tidak dikirim ke daftar.
            kartu_judul = {(c.get("title"), c.get("time")) for c in (persiapan.get("berita") or [])
                           if isinstance(c, dict)} if isinstance(persiapan, dict) else set()
            sedang = [c for c in _chat.calendar_json(rows, now, fetch=lambda s: [], dampak=("Medium",))
                      if (c["title"], c["time"]) in kartu_judul]
            try:                                              # Act berlapis: BLS -> FRED API -> FRED CSV (_aktual.py)
                aktual = _aktual.fill(calendar + sedang, store, now, os.environ)
            except Exception as exc:  # noqa: BLE001 - kalender tetap dikirim
                aktual = {"status": _arsip.redact(f"gagal: {type(exc).__name__}: {exc}"[:200])}
            for c in calendar:                                # Act sudah keluar -> kesimpulan arah otomatis
                if c.get("actual"):
                    try:
                        c["arah"] = _persiapan.kesimpulan(c["title"], c["actual"], c.get("forecast", ""))
                    except Exception:  # noqa: BLE001
                        pass
            try:                                              # 15 Okt: rilis bersamaan → satu arah emas (judul utama)
                _persiapan.satukan(calendar, "arah")
            except Exception:  # noqa: BLE001
                pass
            if isinstance(persiapan, dict):                   # 14 Okt: Act juga ke kartu (dulu kartu dibuat sebelum Act
                isi_act(persiapan, calendar + sedang)         # diisi → PPI tidak pernah diperbarui oleh hasil CPI)
            if isinstance(persiapan, dict) and persiapan.get("berita") is not None:
                try:                                          # 🎯 perkiraan hari H / ✅ hasil + 🏦 Fed (Polymarket)
                    berita = persiapan["berita"]
                    ks = _kalshi.cached_snapshot(berita, store, now)[0] if berita else {}
                    ps = _polymarket.cached_snapshot(berita, store, now)[0] if berita else {}
                    _hari_h.attach(persiapan, calendar + sedang, store, now, ks, ps, _polymarket.cached_fed(store, now))
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict):
                try:                                          # 📅 NFP/CPI/Fed dst. setelah pekan ini (_jadwal.py)
                    import _jadwal
                    _jadwal.attach(persiapan, now)
                except Exception:  # noqa: BLE001 - opsional
                    pass
                try:                                          # 🎲 CPI dst. sebelum konsensus terbit: sebaran pasar Kalshi
                    if sempat("kalshi_mendatang"):
                        _kalshi.mendatang(persiapan.get("mendatang") or [], store, now)
                except Exception:  # noqa: BLE001 - opsional
                    pass
                try:                                          # 🗣️ pernyataan Fed/Trump/pemerintah terbaru (_pernyataan.py)
                    import _pernyataan
                    if sempat("pernyataan"):
                        _pernyataan.attach(persiapan, store, now, os.environ)
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict) and os.environ.get("PRARILIS", "1") == "1":
                try:                                          # 📊 peluang emas sebelum NFP/JOLTS/Fed (_prarilis.py)
                    import _prarilis
                    key = os.environ.get("TWELVEDATA_API_KEY", "")
                    _prarilis.attach(persiapan, calendar, store, now,
                                     lambda: _core.TwelveData(key, "XAU/USD").candles(600, "1h"))
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict):
                try:                                          # 🧭 petunjuk teruji semua berita (_petunjuk.py, petunjuk.json)
                    import _petunjuk
                    _petunjuk.attach(persiapan, calendar, store, now, os.environ)
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict):
                try:                                          # 🎯 satu baris "NFP: peluang emas naik 1 jam 61%" (_prediksi.py)
                    import _prediksi
                    _prediksi.attach(persiapan, store, now, os.environ)
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict):
                try:                                          # ⏱️ CPI detik 2–10: aturan tutup kertas (_cpi_detik.py)
                    import _cpi_detik
                    _cpi_detik.attach(persiapan, store, now)
                except Exception:  # noqa: BLE001 - opsional
                    pass
                try:                                          # ⛽ PPI: minyak WTI bulan acuan (_ppi_wti.py, 13 Okt 2026)
                    import _ppi_wti
                    _ppi_wti.attach(persiapan, store, now, calendar=calendar)
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if isinstance(persiapan, dict):
                try:                                          # 👥 sentimen orang (_sentimen.py, info saja, 14 Okt 2026)
                    import _sentimen
                    if sempat("sentimen"):
                        _sentimen.attach(persiapan, store, now)
                except Exception:  # noqa: BLE001 - opsional
                    pass
                try:                                          # ⏱️ entry 1 dtk sebelum berita: % per aset (_pra_aset.py)
                    import _pra_aset
                    key = os.environ.get("TWELVEDATA_API_KEY", "")
                    # nama terpisah: dulu memakai "tren" sehingga status tren (dikirim ke aplikasi) tertimpa lambda
                    tren_fn = (lambda sisa: _pra_aset.tren_emas(
                        store, now, lambda: _core.TwelveData(key, "XAU/USD").candles(24, "15min"), sisa)) \
                        if key and os.environ.get("PRA_TREN", "1") == "1" else None
                    _pra_aset.attach(persiapan, now, tren_fn)
                except Exception as exc:  # noqa: BLE001 - opsional (alasan dicatat untuk diagnosa)
                    persiapan["pra_galat"] = _arsip.redact(f"{type(exc).__name__}: {exc}")[:200]
                try:                                          # 🔗 keterkaitan berita sebelumnya (_keterkaitan.py, 15 Okt)
                    import _keterkaitan
                    _keterkaitan.attach(persiapan, calendar, store, now)
                except Exception:  # noqa: BLE001 - info opsional
                    pass
                try:                                          # 15 Okt: baris di bawah XAU SELALU ada (cadangan ≈ 50%)
                    import _pra_aset
                    _pra_aset.cadangan(persiapan, now)
                except Exception:  # noqa: BLE001
                    pass
                try:                                          # 📍 gaya masuk t−1 dtk + ⚡LIVE tahan/tutup (_masuk_pra.py)
                    import _masuk_pra
                    _masuk_pra.attach(persiapan)
                except Exception:  # noqa: BLE001 - info opsional
                    pass
                try:                                          # 🎯 persen sebelum rilis berita tanpa arah (_pra_peluang.py)
                    import _pra_peluang
                    _pra_peluang.attach(persiapan, now)
                except Exception:  # noqa: BLE001 - info opsional
                    pass
            if isinstance(persiapan, dict) and persiapan.get("berita") and os.environ.get("TWELVEDATA_API_KEY") \
                    and os.environ.get("FADE_WARNING", "1") == "1" and sempat("pudar"):
                try:                                          # 📉 lonjakan memudar? (sisa lonjakan menit 30/60)
                    key = os.environ["TWELVEDATA_API_KEY"]
                    _pudar.attach(persiapan, store, now, _pudar.fetch_twelvedata(key),
                                  _pudar.fetch_twelvedata(key, "BTC/USD"))
                except Exception:  # noqa: BLE001 - opsional
                    pass
            if sempat("arsip"):
                try:                                          # arsip berita ke GitHub (tiap aplikasi dibuka)
                    arsip = _arsip.save(rows, calendar, now, store, os.environ)
                except Exception as exc:  # noqa: BLE001 - arsip tidak boleh mengganggu kalender
                    arsip = {"status": _arsip.redact(f"gagal: {type(exc).__name__}: {str(exc)[:160]}")}
            else:
                arsip = {"status": "dilewati (GET lama; dicoba lagi saat aplikasi memuat ulang)"}
            if isinstance(persiapan, dict):
                persiapan["arsip"] = arsip                    # ditampilkan di kartu 🎯 (cek token tanpa curl)
                persiapan["waktu_dtk"] = round(time.monotonic() - mulai, 1)
                if dilewati:
                    persiapan["dilewati"] = dilewati
            self._send(200, {"ok": True, "calendar": calendar, "tren": tren, "persiapan": persiapan,
                             "arsip": arsip, "aktual": aktual})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": _arsip.redact(f"{type(exc).__name__}: {exc}")})
