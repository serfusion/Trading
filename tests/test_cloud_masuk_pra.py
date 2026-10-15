"""📍 Gaya masuk 1 dtk sebelum rilis (_masuk_pra.py) + jalur cepat GET /api/chat (MemoStore, anggaran waktu, baris cadangan)
— 15 Okt 2026, pengguna: "entry 1 detik sebelum release, bertahan 1 detik hingga 1–3 menit" dan "news di bawah XAU lama muncul,
terkadang tidak muncul, saya mau langsung muncul"."""
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))

import _core  # noqa: E402
import _masuk_pra  # noqa: E402
import _pra_aset  # noqa: E402
import chat  # noqa: E402

UTC = timezone.utc
T0 = "2026-11-10T13:30:00+00:00"


def test_t1_status_per_arah_jujur():
    naik = _masuk_pra.t1({"title": "CPI m/m", "arah": "naik", "status": "tutup kertas", "time": T0, "nama": "CPI"})
    turun = _masuk_pra.t1({"title": "CPI m/m", "arah": "turun", "status": "lemah", "time": T0, "nama": "CPI"})
    # sebelum Okt 2021 rata-rata ≈ impas → tidak boleh "teruji"; tebakan TURUN CPI rugi rata-rata → JANGAN
    assert naik["status"] == "belum terbukti" and "BUY" in naik["teks"] and "⚠️" in naik["teks"]
    assert turun["status"] == "jangan" and "JANGAN" in turun["teks"] and "SELL" in turun["teks"]
    assert "sebelum Okt 2021" in naik["bukti"] and "selalu BUY" in naik["bukti"] and "detik 1" in naik["bukti"]
    tanpa = _masuk_pra.t1({"title": "Non-Farm Employment Change", "arah": None, "status": "acak", "time": T0})
    assert tanpa["status"] == "jangan" and "lempar koin" in tanpa["teks"] and "$0,26" in tanpa["bukti"]
    belum = _masuk_pra.t1({"title": "JOLTS Job Openings", "arah": "naik", "status": "belum terbukti", "time": T0})
    assert belum["status"] == "belum diuji"


def test_t1_tidak_lebih_tinggi_dari_tebakan_utama(monkeypatch):
    data = json.loads(json.dumps(_masuk_pra.DATA))
    data["t1"]["CPI"]["naik"] = {"n": 40, "H": {"30": [70, 1.0], "60": [72, 1.2]}, "lama": [65, 0.5, 20], "baru": [75, 1.5, 20]}
    monkeypatch.setattr(_masuk_pra, "DATA", data)
    kuat = _masuk_pra.t1({"title": "CPI m/m", "arah": "naik", "status": "tutup kertas", "time": T0})
    lemah = _masuk_pra.t1({"title": "CPI m/m", "arah": "naik", "status": "lemah", "time": T0})
    assert kuat["status"] == "teruji" and "✅" in kuat["teks"]
    assert lemah["status"] == "belum terbukti"


def test_posisi_tabel_searah_berlawanan_dan_cadangan_semua_berita():
    p = _masuk_pra.posisi("CPI m/m")
    assert p["g"] == "CPI" and {"s|0.5", "l|0.5", "kecil"} <= set(p["2"])
    s, lw = p["2"]["s|0.5"], p["2"]["l|0.5"]
    assert s["60"][0] >= 70 and lw["60"][0] <= 30 and s["g"] == "CPI"     # searah bertahan, berlawanan jarang balik
    f = _masuk_pra.posisi("Federal Funds Rate")
    assert all(v["n"] >= 20 or v["g"] == "SEMUA" for d in ("1", "2") for v in f[d].values())


def test_attach_poin_dan_lanjut_sekali():
    ps = {"title": "CPI m/m", "nama": "CPI", "time": T0, "arah": "naik", "status": "tutup kertas",
          "poin": ["✅ Tutup kertas: 68%", "👥 Orang: survei 45% naik", "Setelah rilis: ikuti detik 2"], "lanjut": {"2": 90}}
    prep = {"pra_satu": ps}
    _masuk_pra.attach(prep)
    _masuk_pra.attach(prep)                                  # GET berulang tidak menggandakan poin
    assert [x[:1] for x in ps["poin"]].count("📍") == 1 and ps["poin"][1].startswith("📍")
    assert ps["bukti"].count("📍") == 1 and ps["t1"]["status"] == "belum terbukti"
    assert ps["lanjut"]["2"] == 90 and ps["lanjut"]["posisi"]["g"] == "CPI"


def test_mati_lewat_env(monkeypatch):
    monkeypatch.setenv("MASUK_PRA", "0")
    prep = {"pra_satu": {"title": "CPI m/m", "time": T0, "arah": "naik", "poin": []}}
    _masuk_pra.attach(prep)
    assert "t1" not in prep["pra_satu"]


class Toko(dict):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.baca, self.banyak = [], 0

    def get_state(self, r="main"):
        self.baca.append(r)
        return json.loads(json.dumps(self.get(r, {})))

    def get_many(self, rows):
        self.banyak += 1
        return {r: json.loads(json.dumps(self[r])) for r in rows if r in self}

    def save_state(self, d, r="main"):
        self[r] = json.loads(json.dumps(d))

    def log(self, kind, payload):
        self["_log"] = [kind, payload]


def test_memostore_satu_permintaan_salinan_dan_tulis():
    t = Toko(kalshi={"t": "x", "v": [1]}, aktual={"found": {}})
    m = chat.MemoStore(t)
    assert t.banyak == 1
    a = m.get_state("kalshi")
    a["v"].append(2)                                         # pemanggil mengubah hasil → memori tidak ikut berubah
    assert m.get_state("kalshi") == {"t": "x", "v": [1]} and m.get_state("hasil_rilis") == {}
    assert t.baca == []                                      # semua dari satu baca sekaligus
    m.save_state({"t": "y"}, "kalshi")
    assert t["kalshi"] == {"t": "y"} and m.get_state("kalshi") == {"t": "y"}
    assert m.get_state("lain") == {} and t.baca == ["lain"]  # baris di luar daftar dibaca sekali
    m.get_state("lain")
    assert t.baca == ["lain"]
    m.log("x", {"a": 1})
    assert t["_log"] == ["x", {"a": 1}]


def test_memostore_gagal_baca_sekaligus_kembali_per_baris():
    class Rusak(Toko):
        def get_many(self, rows):
            raise OSError("jaringan")
    t = Rusak(kalshi={"v": 1})
    m = chat.MemoStore(t)
    assert m.get_state("kalshi") == {"v": 1} and t.baca == ["kalshi"]


def test_supabase_get_many_satu_url(monkeypatch):
    urls = []

    def http(method, url, headers=None, body=None, timeout=15):
        urls.append(url)
        return [{"id": "kalshi", "data": {"v": 1}}, {"id": "aktual", "data": None}]
    monkeypatch.setattr(_core, "http", http)
    s = _core.Supabase("https://x.supabase.co", "k")
    got = s.get_many(["kalshi", "aktual", "kalshi"])
    assert got == {"kalshi": {"v": 1}, "aktual": {}}
    assert len(urls) == 1 and "xau_state?id=in.(aktual,kalshi)&select=id,data" in urls[0]


def test_cadangan_baris_xau_selalu_ada():
    now = datetime(2026, 10, 16, 6, tzinfo=UTC)
    prep = {"berita": [{"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00", "released": True}],
            "mendatang": [{"title": "Federal Funds Rate", "time": "2026-10-28T18:00:00+00:00"},
                          {"title": "Advance GDP q/q", "time": "2026-10-29T12:30:00+00:00"}]}
    _pra_aset.cadangan(prep, now)
    ps = prep["pra_satu"]
    assert ps["title"] == "Federal Funds Rate" and ps["arah"] is None and "≈50%" in ps["teks"] and "12 hari lagi" in ps["teks"]
    assert ps["cadangan"] and ps["bukti"].startswith("• ")
    lama = {"pra_satu": {"title": "X", "time": T0}}
    _pra_aset.cadangan(lama, now)
    assert lama["pra_satu"] == {"title": "X", "time": T0}    # sudah ada → tidak disentuh
    kosong = {"berita": [], "mendatang": []}
    _pra_aset.cadangan(kosong, now)
    assert "pra_satu" not in kosong


def test_get_lama_melewati_langkah_info(monkeypatch):
    """GET melewati anggaran → 🗣️/👥/arsip dilewati, baris XAU tetap ada (+ waktu_dtk & daftar dilewati untuk diagnosa)."""
    import _arsip
    import _chat
    import _pernyataan
    import _sentimen
    import urllib.error
    import urllib.request

    def no_net(*a, **k):
        raise urllib.error.URLError("offline")
    monkeypatch.setattr(urllib.request, "urlopen", no_net)
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "TWELVEDATA_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    now = datetime(2026, 10, 16, 6, tzinfo=UTC)
    rows = [{"title": "Federal Funds Rate", "country": "USD", "date": "2026-10-21T14:00:00-04:00", "impact": "High",
             "forecast": "4.25%", "previous": "4.25%"}]
    monkeypatch.setattr(_chat, "fetch_calendar", lambda: rows)
    dipanggil = []
    monkeypatch.setattr(_pernyataan, "attach", lambda *a, **k: dipanggil.append("pernyataan"))
    monkeypatch.setattr(_sentimen, "attach", lambda *a, **k: dipanggil.append("sentimen"))
    monkeypatch.setattr(_arsip, "save", lambda *a, **k: dipanggil.append("arsip") or {"status": "ok"})
    panggil = []

    def mono():                                              # mulai = 0, lalu semua cek berikutnya = 100 dtk berlalu
        panggil.append(1)
        return 0.0 if len(panggil) == 1 else 100.0
    monkeypatch.setattr(chat, "time", types.SimpleNamespace(monotonic=mono))   # hanya jam milik chat.py

    class FDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(chat, "datetime", FDT)
    out = {}
    h = chat.handler.__new__(chat.handler)
    h.path, h._authorized = "/api/chat", (lambda: True)
    h._send = lambda c, b: out.update(b, _code=c)
    h.do_GET()
    p = out["persiapan"]
    assert out["_code"] == 200 and dipanggil == []
    assert {"pernyataan", "sentimen", "arsip"} <= set(p["dilewati"]) and p["waktu_dtk"] >= 20
    assert p["pra_satu"]["time"] == "2026-10-21T18:00:00+00:00" and p["pra_satu"]["teks"]
    assert p["pra_satu"]["t1"]["status"] == "jangan" and p["pra_satu"]["lanjut"]["posisi"]["g"] == "FOMC"


def test_pra_peluang_persen_sebelum_rilis_tanpa_arah():
    import _pra_peluang
    ps = {"title": "Federal Funds Rate", "nama": "Fed", "time": "2026-10-28T18:00:00+00:00", "arah": None,
          "sisa": "13 hari lagi", "teks": "Fed ⚪ ≈50% • 13 hari lagi", "poin": ["⚪ Belum ada petunjuk teruji → ≈ 50:50"]}
    prep = {"pra_satu": ps, "fed": {"teks": "94% TETAP"}}
    _pra_peluang.attach(prep, datetime(2026, 10, 15, 16, tzinfo=UTC))
    assert "▼ TURUN 51%" in ps["teks"] and "NAIK" not in ps["teks"] and ps["teks"].endswith("13 hari lagi")
    assert ps["peluang"]["grup"] == "FOMC" and "Polymarket 94% TETAP" in ps["bukti"]
    assert not any(p.startswith("⚪ Belum ada") for p in ps["poin"])
    berarah = {"pra_satu": {"title": "CPI m/m", "time": T0, "arah": "naik", "teks": "CPI ▲ NAIK 68%"}}
    _pra_peluang.attach(berarah)
    assert berarah["pra_satu"]["teks"] == "CPI ▲ NAIK 68%"          # arah teruji tidak ditimpa
