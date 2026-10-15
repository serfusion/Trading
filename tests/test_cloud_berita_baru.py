"""🎲 sebaran Kalshi sebelum konsensus, 🧭 petunjuk teruji, 🗣️ pernyataan, 🎯 baris pasar CPI — tanpa jaringan."""
import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _kalshi  # noqa: E402
import _pernyataan  # noqa: E402
import _petunjuk  # noqa: E402
import _prediksi  # noqa: E402

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _cpi_lama(monkeypatch):
    """Test di file ini menguji mekanisme varian lama (pra_aset.json). Sejak 11 Okt 2026 kartu CPI memakai aturan tutup
    kertas _cpi_detik.py (diuji di test_cloud_cpi_detik.py); varian lama tetap tersedia lewat env CPI_DETIK=0."""
    monkeypatch.setenv("CPI_DETIK", "0")


T0 = "2026-10-14T12:30:00+00:00"


def mk(t, p):
    return {"ticker": f"KXCPI-26SEP-T{t}", "yes_bid_dollars": f"{p:.4f}", "yes_ask_dollars": f"{p:.4f}",
            "last_price_dollars": f"{p:.4f}", "close_time": "2026-10-14T12:25:00Z"}


def test_sebaran_kalshi_mendatang():
    ms = [mk(0.4, 0.915), mk(0.5, 0.585), mk(0.6, 0.19), mk(0.7, 0.015)]
    s = _kalshi.sebaran(ms, 0.1)
    assert s["puncak"] == 0.6 and abs(s["p"] - 0.395) < 1e-6 and s["ge"]["0.6"] == 0.585
    cards = [{"title": "CPI m/m", "time": T0}]
    _kalshi.mendatang(cards, None, NOW, get=lambda series: ms)
    k = cards[0]["kalshi_sebaran"]
    assert k["teks"] == "CPI m/m paling mungkin 0,6% (39%)" and "konsensus" in k["catatan"]


def test_baris_pasar_cpi_dan_peringkat():
    card = {"title": "CPI m/m", "time": T0, "hari_h": {"p_naik": 0.62, "teks": "EMAS 62% naik ⚪", "bukti": "x",
                                                       "geser": {"dari": 0.55, "ke": 0.62, "jam": 6.0}}}
    pr = _prediksi.untuk(card)
    assert pr["sumber"] == "pasar" and pr["teks"] == "CPI: peluang emas naik 1 menit 62%"
    assert _prediksi.peringkat(pr, card) == 2
    prep = {"berita": [card]}
    _prediksi.attach(prep)
    det = prep["berita"][0]["prediksi"]["detail"]
    assert any(d["judul"].startswith("🎲 Pasar prediksi") and "bergeser 55% → 62%" in d["catatan"] for d in det)


def test_petunjuk_sepakat_dan_berbalik():
    mem = {"Core CPI m/m": {"s": 1, "time": "2026-09-11T12:30:00+00:00"},
           "ISM Services PMI": {"s": 1, "time": "2026-09-03T14:00:00+00:00"}}
    core = {"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00", "hari_h": {"pasar": {"atas": 0.365, "bawah": 0.215}}}
    b = _petunjuk.blok(core, mem)
    assert "SEPAKAT" in b["teks"] and b["arah_emas"] == "turun"
    basi = _petunjuk.blok({**core, "time": "2026-11-10T13:30:00+00:00"}, mem)       # memori 2 bulan lalu: tidak dipakai
    assert "SEPAKAT" not in basi["teks"]
    ism = _petunjuk.blok({"title": "ISM Services PMI", "time": "2026-10-05T14:00:00+00:00"}, mem)
    assert "DI BAWAH" in ism["teks"] and "berbalik" in ism["catatan"]
    assert _petunjuk.blok({"title": "Retail Sales m/m"}, mem) is None        # tidak ada aturan teruji


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Trump vows new tariffs on China imports - Reuters</title><link>https://x/1</link>
<pubDate>Sat, 10 Oct 2026 08:00:00 GMT</pubDate></item>
<item><title>Trump says tariffs on China imports coming soon - AP</title><link>https://x/2</link>
<pubDate>Sat, 10 Oct 2026 07:50:00 GMT</pubDate></item>
<item><title>Celebrity news without market topic Trump</title><link>https://x/3</link>
<pubDate>Sat, 10 Oct 2026 07:00:00 GMT</pubDate></item>
<item><title>Old story Fed hike</title><link>https://x/4</link><pubDate>Mon, 05 Oct 2026 07:00:00 GMT</pubDate></item>
</channel></rss>"""
FED = b"""<?xml version="1.0"?><rss><channel><item><title>Waller, The economic outlook</title><link>https://f/1</link>
<pubDate>Thu, 08 Oct 2026 12:30:00 GMT</pubDate></item></channel></rss>"""


def test_pernyataan_saring_dan_cache():
    get = lambda url, *a, **k: FED if "federalreserve" in url else RSS   # noqa: E731
    items, st = _pernyataan.kumpulkan(NOW, get)
    judul = [r["judul"] for r in items]
    assert judul[0].startswith("Trump vows") and len([j for j in judul if "tariff" in j]) == 1   # cerita sama 1x
    assert not any("Celebrity" in j or "Old story" in j for j in judul)
    assert any(j.startswith("Waller") for j in judul)                                          # pidato Fed 3 hari

    class St:
        d = {}

        def get_state(self, row):
            return self.d.get(row, {})

        def save_state(self, data, row):
            self.d[row] = json.loads(json.dumps(data))
    prep, st_ = {}, St()
    _pernyataan.attach(prep, st_, NOW, {}, get)
    assert prep["pernyataan"]["penting"] and "Google News ✓" in prep["pernyataan"]["status"]
    prep2 = {}
    _pernyataan.attach(prep2, st_, NOW, {}, lambda *a, **k: (_ for _ in ()).throw(OSError("x")))   # cache 10 mnt
    assert prep2["pernyataan"]["penting"] == prep["pernyataan"]["penting"]


def test_pra_xau_arah_1_10_detik(monkeypatch):
    """⏱️ khusus XAU: arah 1–10 dtk dari petunjuk teruji + persen searah per detik (bukan untung/rugi)."""
    import _pra_aset as A
    h = lambda b, k=False: {"exness": {"n": 20, "benar": b, "lama": None, "baru": b}, "konsisten": k}  # noqa: E731
    monkeypatch.setattr(A, "DATA", {"xau_arah": {
        "CPI • Kalshi & kejutan lalu sepakat": {"h": {"1|0": h(45.0), "2|0": h(65.0), "3|0": h(65.0), "5|0": h(65.0),
                                                       "10|0": h(70.0)}},
        "ISM Jasa • berbalik": {"h": {f"{x}|0": h(64.0, True) for x in (1, 2, 3, 5, 10)}}}})
    b = {"arah_emas": "turun", "tebak": {"K": 1.0, "P": 1.0}, "kalshi_sepakat": True, "sepakat_lain": []}
    prep = {"mendatang": [{"title": "CPI m/m", "time": T0, "when": "Rab 14 Okt 19:30 WIB", "petunjuk_teruji": b}]}
    A.attach(prep, NOW)
    p = prep["pra"]
    assert p["teks"] == "XAU TURUN ▼ • benar 65–70% (2–10 dtk) ⚠️" and p["status"] == "belum terbukti"
    assert p["kecil"].startswith("1 dtk 45% • 2 dtk 65%")
    ism = {"mendatang": [{"title": "ISM Services PMI", "time": T0, "petunjuk_teruji": {"arah_emas": "naik", "tebak": {"-P": -1.0}}}]}
    A.attach(ism, NOW)
    assert ism["pra"]["teks"] == "XAU NAIK ▲ • benar 64% (2–10 dtk) ✅"
    kosong = {"mendatang": [{"title": "Retail Sales m/m", "time": T0}]}
    A.attach(kosong, NOW)
    assert kosong["pra"]["status"] == "acak"


def test_ppi_dari_cpi_dan_kepastian_detik2(monkeypatch):
    """PPI: kejutan CPI ≤ 10 hari sebelumnya memberi arah; 📌 kepastian detik 2 tampil untuk setiap berita."""
    import _pra_aset as A
    monkeypatch.setattr(_petunjuk, "ATURAN", {"PPI m/m": {"CPI": {"benar": 21, "n": 29, "tahun": "2010–2025",
                                                                  "emas": [18, 32], "jenis": "xau 3 dtk"}}})
    mem = {"CPI m/m": {"s": 1, "time": "2026-10-14T12:30:00+00:00"}}
    ppi = {"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00"}
    b = _petunjuk.blok(ppi, mem)
    assert b["arah_emas"] == "turun" and "Kejutan CPI pekan ini" in b["catatan"] and "arah XAU 3 dtk" in b["catatan"]
    lama = _petunjuk.blok(ppi, {"CPI m/m": {"s": 1, "time": "2026-09-11T12:30:00+00:00"}})
    assert lama is None or not (lama.get("tebak") or {})                      # CPI > 10 hari: tidak dipakai
    h = {"exness": {"n": 23, "benar": 65.2, "lama": 80.0, "baru": 61.5}, "konsisten": False}
    monkeypatch.setattr(A, "DATA", {"xau_arah": {"PPI • kejutan CPI pekan ini": {"h": {f"{x}|0": h for x in (1, 2, 3, 5, 10)}}},
                                    "lanjut": {"PPI|2|0.5|10": {"tetap": 86.6, "n": 67}, "PPI|1|0.5|10": {"tetap": 71.4, "n": 21},
                                               "SEMUA|2|0.5|10": {"tetap": 93.0, "n": 900}}})
    ppi["petunjuk_teruji"] = b
    prep = {"mendatang": [ppi]}
    A.attach(prep, NOW)
    assert prep["pra"]["teks"].startswith("XAU TURUN ▼ • benar 65%")
    assert "detik 10 pada 87% rilis (n 67)" in prep["pra"]["kepastian"]
    retail = {"mendatang": [{"title": "Retail Sales m/m", "time": T0}]}
    A.attach(retail, NOW)
    assert "93% rilis (n 900)" in retail["pra"]["kepastian"]                  # tanpa data grup → SEMUA


def test_tren_emas_4_jam_searah_berlawanan(monkeypatch):
    """➕ tren emas 4 jam: searah petunjuk → % gabungan; berlawanan → ≈ lempar koin; tanpa petunjuk → tren saja."""
    from datetime import timedelta

    import _core
    import _pra_aset as A
    now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    bars = [_core.Bar(now - timedelta(minutes=15 * i), 4000 + i * 0.5, 4002 + i * 0.5, 3999 + i * 0.5, 4000.5 + i * 0.5)
            for i in range(24, -1, -1)]                           # harga turun ±$8 dalam 4 jam
    t = A.hitung_tren(bars, now)
    assert t["g4"] == round(bars[-1].c - 4008.0, 2) and t["g4"] < 0
    assert A.hitung_tren(bars[:-6], now) is None                  # data basi (> 45 mnt) → tanpa tren

    class St:
        d = {}

        def get_state(self, row):
            return self.d.get(row, {})

        def save_state(self, data, row):
            self.d[row] = data
    st = St()
    assert A.tren_emas(st, now, lambda: bars, timedelta(minutes=30))["g4"] == t["g4"]
    later = now + timedelta(minutes=3)
    assert A.tren_emas(st, later, lambda: (_ for _ in ()).throw(OSError("x")), timedelta(minutes=27)) == st.d["pra_tren"]

    x = lambda b, n=142: {str(h): {"exness": {"n": n, "benar": b, "lama": 62.2, "baru": 66.2}} for h in (1, 2, 3, 5, 10)}  # noqa: E731
    h = {"exness": {"n": 107, "benar": 65.4, "lama": 65.0, "baru": 66.0}, "konsisten": True}
    monkeypatch.setattr(A, "DATA", {"xau_arah": {"ISM Jasa • berbalik": {"h": {f"{k}|0": h for k in (1, 2, 3, 5, 10)}}},
                                    "tren": {"sepakat": {"SEMUA": x(64.0), "ISM": x(76.0, 46)},
                                             "berlawanan": {"SEMUA": x(54.0, 124), "ISM": x(57.0, 42)},
                                             "tanpa": {"SEMUA": x(55.0, 1410)}}})
    T = "2026-10-14T14:00:00+00:00"
    ism = {"mendatang": [{"title": "ISM Services PMI", "time": T, "petunjuk_teruji": {"arah_emas": "turun", "tebak": {"-P": 1.0}}}]}
    A.attach(ism, now, lambda sisa: t)
    tr = ism["pra"]["tren"]
    assert tr["hubungan"] == "sepakat" and "SEARAH → benar 76%" in tr["teks"] and tr["putusan"] == "Tebakan terbaik: XAU TURUN ▼ (petunjuk berita & tren searah)"
    naik = {"mendatang": [{"title": "ISM Services PMI", "time": T, "petunjuk_teruji": {"arah_emas": "naik", "tebak": {"-P": -1.0}}}]}
    A.attach(naik, now, lambda sisa: t)
    assert naik["pra"]["tren"]["hubungan"] == "berlawanan" and "57%" in naik["pra"]["tren"]["teks"]
    retail = {"mendatang": [{"title": "Retail Sales m/m", "time": T}]}
    A.attach(retail, now, lambda sisa: t)
    assert retail["pra"]["tren"]["hubungan"] == "tanpa" and "lemah" in retail["pra"]["tren"]["teks"]
    jauh = {"mendatang": [{"title": "Retail Sales m/m", "time": "2026-10-15T14:00:00+00:00"}]}
    A.attach(jauh, now, lambda sisa: t)
    assert "tren" not in jauh["pra"] and "≤ 6 jam" in jauh["pra"]["tren_nanti"]


def test_daftar_berita_mendatang_di_bawah_xau(monkeypatch):
    """🎯 baris per berita mendatang: "CPI • peluang emas turun 66% ⚠️ • 4 hari lagi"; NFP = kalender survei BLS;
    tanpa petunjuk → ≈ 50:50; tren 4 jam hanya untuk berita terdekat ≤ 6 jam."""
    from datetime import timedelta

    import _pra_aset as A
    h = lambda b: {"exness": {"n": 20, "benar": b, "lama": None, "baru": b}, "konsisten": False}  # noqa: E731
    monkeypatch.setattr(A, "DATA", {
        "xau_arah": {"CPI • Kalshi & kejutan lalu sepakat": {"h": {"1|0": h(45.0), "2|0": h(65.0), "3|0": h(65.0),
                                                                   "5|0": h(65.0), "10|0": h(70.0)}}},
        "per_berita": {"Unemployment Rate|PK5": {"arah": 1.0, "benar": 57.3, "lama": 57.5, "baru": 57.0, "n": 164,
                                                  "kejutan": 55.0,
                                                  "tren_searah": {"benar": 61.7, "lama": 60.6, "baru": 64.1, "n": 75},
                                                  "tren_lawan": {"benar": 53.0, "lama": 54.3, "baru": 50.9, "n": 74}}},
        "tren": {"tanpa": {"SEMUA": {str(k): {"exness": {"n": 1400, "benar": 55.0}} for k in (2, 3, 5, 10)}}}})
    now = datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)
    b = {"arah_emas": "turun", "tebak": {"K": 1.0, "P": 1.0}, "kalshi_sepakat": True, "sepakat_lain": []}
    prep = {"mendatang": [{"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00", "petunjuk_teruji": b},
                          {"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00"},
                          {"title": "Retail Sales m/m", "time": "2026-10-16T12:30:00+00:00"},
                          {"title": "Building Permits", "time": "2026-10-17T12:30:00+00:00"},
                          {"title": "Non-Farm Employment Change", "time": "2026-11-06T13:30:00+00:00"}]}
    d = A.daftar(prep, now)
    assert [r["nama"] for r in d] == ["CPI", "Retail Sales", "NFP"]
    assert d[0]["teks"] == "CPI • peluang emas turun 66% ⚠️ • 4 hari lagi"
    assert d[1]["teks"].startswith("Retail Sales • ≈ 50:50") and d[1]["status"] == "acak"
    assert d[2]["teks"] == "NFP • peluang emas naik 57% ⚠️ • 27 hari lagi" and "5 pekan" in d[2]["bukti"]
    assert A.pekan5(datetime(2026, 11, 6)) and not A.pekan5(datetime(2026, 10, 2))
    dekat = now + timedelta(days=27, hours=1)                       # NFP 1,5 jam lagi + tren searah / berlawanan
    for g4, harap in ((5.0, "NFP • peluang emas naik 62% (+ tren searah) ⚠️ • 1 jam lagi"),
                      (-5.0, "NFP • peluang emas naik 53% (tren berlawanan) ⚠️ • 1 jam lagi")):
        t = {"g4": g4, "harga": 1.0, "acuan": 1.0, "at": "2026-11-06T12:00:00+00:00"}
        r = A.daftar(prep, dekat, lambda s: t)[0]
        assert r["teks"] == harap and r["tren"]["hubungan"] in ("sepakat", "berlawanan")
    assert A.sisa_teks(timedelta(minutes=12)) == "12 mnt lagi" and A.sisa_teks(timedelta(hours=5)) == "5 jam lagi"


def test_satu_baris_berita_berikutnya_dan_arah_sama_di_semua_kartu(monkeypatch):
    """4.31: SATU baris "CPI ▼ TURUN 66% ⚠️ • 4 hari lagi"; arah yang sama dipasang di kartu (arah_detik) agar tidak
    bertentangan dengan angka 1 jam; tanpa petunjuk ≤ 6 jam → arah tren 4 jam; > 6 jam → kapan arah muncul."""
    from datetime import timedelta

    import _pra_aset as A
    h = lambda b: {"exness": {"n": 20, "benar": b, "lama": None, "baru": b}, "konsisten": False}  # noqa: E731
    monkeypatch.setattr(A, "DATA", {
        "xau_arah": {"CPI • Kalshi & kejutan lalu sepakat": {"h": {f"{k}|0": h(66.0) for k in (1, 2, 3, 5, 10)}}},
        "tren": {"tanpa": {"SEMUA": {str(k): {"exness": {"n": 1400, "benar": 55.0}} for k in (2, 3, 5, 10)}}}})
    now = datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)
    b = {"arah_emas": "turun", "tebak": {"K": 1.0, "P": 1.0}, "kalshi_sepakat": True, "sepakat_lain": []}
    cpi = {"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00", "petunjuk_teruji": b,
           "prediksi": {"teks": "CPI: peluang emas naik 1 jam 54%"}}
    prep = {"mendatang": [cpi, {"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00"}]}
    A.attach(prep, now)
    assert prep["pra_satu"]["teks"] == "CPI ▼ TURUN 66% (1–10 dtk) ⚠️ • 4 hari lagi"
    assert cpi["arah_detik"]["teks"] == "CPI: emas turun 66% (1–10 dtk)"
    ppi = {"mendatang": [{"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00"}]}
    A.attach(ppi, now)
    assert ppi["pra_satu"]["teks"] == "PPI ⚪ ≈50% (arah muncul ≤ 6 jam sebelum rilis) • 5 hari lagi"   # selalu ada %
    dekat = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
    t = {"g4": 4.0, "harga": 1.0, "acuan": 1.0, "at": "2026-10-15T09:00:00+00:00"}
    ppi2 = {"mendatang": [{"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00"}]}
    A.attach(ppi2, dekat, lambda s: t)
    assert ppi2["pra_satu"]["teks"] == "PPI ▲ NAIK 55% (1–10 dtk) ⚠️ • 3 jam lagi"
    assert ppi2["mendatang"][0]["arah_detik"]["arah"] == "naik"
    assert A.sisa_teks(timedelta(days=4, hours=1)) == "4 hari lagi"



def test_cpi_pakai_petunjuk_terkuat_di_waktu_rilis(monkeypatch):
    """Headline CPI hanya "minyak WTI" (56%) tetapi core CPI "Kalshi & kejutan lalu sepakat" (66%) → yang tampil 66%."""
    import _pra_aset as A
    h = lambda b: {"exness": {"n": 20, "benar": b, "lama": None, "baru": b}, "konsisten": False}  # noqa: E731
    monkeypatch.setattr(A, "DATA", {"xau_arah": {
        "CPI • minyak WTI saja": {"h": {f"{k}|0": h(56.0) for k in (1, 2, 3, 5, 10)}},
        "CPI • Kalshi & kejutan lalu sepakat": {"h": {f"{k}|0": h(66.0) for k in (1, 2, 3, 5, 10)}}}})
    now = datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc)
    T = "2026-10-14T12:30:00+00:00"
    head = {"title": "CPI m/m", "time": T, "petunjuk_teruji": {"arah_emas": "turun", "tebak": {"WTI": 1.0},
                                                               "sepakat_lain": []}}
    core = {"title": "Core CPI m/m", "time": T, "petunjuk_teruji": {"arah_emas": "turun", "tebak": {"K": 1.0, "P": 1.0},
                                                                    "kalshi_sepakat": True, "sepakat_lain": []}}
    prep = {"mendatang": [head, core]}
    A.attach(prep, now)
    assert prep["pra_satu"]["teks"] == "CPI ▼ TURUN 66% (1–10 dtk) ⚠️ • 2 hari lagi"
    assert prep["pra"]["teks"].startswith("XAU TURUN ▼ • benar 66%")
    assert head["arah_detik"]["persen"] == 66 and core["arah_detik"]["persen"] == 66


def test_jangka_berlaku_sampai_dan_setelahnya(monkeypatch):
    """Keterangan jangka: 'CPI ▼ TURUN 66% (s/d 1 mnt) ⚠️ • setelah 3 mnt ≈ 50:50' dari profil 1 dtk–1 jam."""
    import _pra_aset as A
    prof = {"2": {"benar": 65.0}, "10": {"benar": 70.0}, "30": {"benar": 65.0}, "60": {"benar": 60.0},
            "180": {"benar": 50.0}, "3600": {"benar": 55.0}}
    monkeypatch.setattr(A, "DATA", {"jangka": {"X": prof, "Y": {"10": {"benar": 54.0}, "30": {"benar": 40.0}}}})
    j = A.jangka("X", "turun")
    assert j["teks_sampai"] == "s/d 1 mnt" and j["teks_setelah"] == "setelah 3 mnt ≈ 50:50"
    y = A.jangka("Y", "turun")
    assert y["teks_sampai"] == "1–10 dtk" and y["teks_setelah"] == "setelah 30 dtk ▲ NAIK 60%"
    r = A.satu({"nama": "CPI", "arah": "turun", "persen": 66, "status": "belum terbukti", "sisa": "4 hari lagi",
                "dasar": "X", "bukti": "b"})
    assert r["teks"] == "CPI ▼ TURUN 66% (s/d 1 mnt) ⚠️ • 4 hari lagi"            # 10 Okt: singkat, tanpa "setelah"


def test_jangka_data_asli_cpi():
    """Profil asli (research/pra_jangka.py): CPI Kalshi & kejutan lalu sepakat berlaku s/d 1 mnt."""
    import _pra_aset as A
    j = A.jangka("CPI • Kalshi & kejutan lalu sepakat", "turun")
    assert j and j["teks_sampai"] == "s/d 1 mnt" and "setelah 3 mnt" in j["teks_setelah"]



def test_semua_kartu_satu_kerangka_tanpa_dobel(monkeypatch):
    """Screenshot 4.32: CPI tampil 2× dan PPI/Retail/Fed/PCE/JOLTS masih "peluang emas naik 1 jam" → kini setiap kartu
    yang belum rilis punya arah_detik (arah 1–10 dtk atau kapan arah muncul) dan kartu kembar ditandai ganda."""
    import _pra_aset as A
    h = lambda b: {"exness": {"n": 20, "benar": b, "lama": None, "baru": b}, "konsisten": False}  # noqa: E731
    monkeypatch.setattr(A, "DATA", {"xau_arah": {"CPI • minyak WTI saja": {"h": {f"{k}|0": h(56.0)
                                                                              for k in (1, 2, 3, 5, 10)}}}})
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    T = "2026-10-14T12:30:00+00:00"
    b = {"arah_emas": "turun", "tebak": {"WTI": 1.0}, "sepakat_lain": []}
    kartu = [{"title": "CPI m/m", "time": T, "petunjuk_teruji": b},
             {"title": "Core CPI m/m", "time": T, "prediksi": {"teks": "Core CPI: peluang emas naik 1 jam 54%"}},
             {"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00"},
             {"title": "Retail Sales m/m", "time": "2026-10-15T12:30:00+00:00"},
             {"title": "Federal Funds Rate", "time": "2026-10-28T18:00:00+00:00"},
             {"title": "Core PCE Price Index m/m", "time": "2026-10-29T12:30:00+00:00"},
             {"title": "JOLTS Job Openings", "time": "2026-11-03T15:00:00+00:00"}]
    prep = {"mendatang": kartu}
    A.attach(prep, now)
    ad = [k["arah_detik"] for k in kartu]
    assert ad[0]["teks"] == "CPI: emas turun 56% (1–10 dtk)" and not ad[0]["ganda"]
    assert ad[1]["ganda"] and ad[1]["teks"] == ad[0]["teks"]                       # core CPI: sama, tidak dobel
    assert ad[2]["teks"] == "PPI & Retail Sales: arah 1–10 dtk muncul ≤ 6 jam sebelum rilis" and not ad[2]["ganda"]
    assert ad[3]["ganda"]                                                          # Retail rilis bersamaan dengan PPI
    assert ad[4]["teks"] == "Fed: arah 1–10 dtk muncul ≤ 6 jam sebelum rilis"
    assert all("1 jam" not in a["teks"] for a in ad)


def test_arah_setelah_beberapa_menit_ikuti_detik2():
    """Data asli research/pra_menit.py: setelah rilis, arah detik 2 (≥ $0,50) masih sama di menit 5 pada ±76–79%."""
    import _pra_aset as A
    mi = A.menit_info("CPI m/m")
    assert mi and mi["grup"] == "CPI" and mi["teks"].startswith("1–5 mnt: ikuti arah detik 2 (")
    assert mi["singkat"].startswith("Setelah rilis: ikuti arah emas detik 2 (≥ $0,50) s/d 5 mnt (")
    fed = A.menit_info("Federal Funds Rate")
    assert fed and fed["grup"] == "FOMC"


def test_satu_singkat_langsung_ke_inti():
    """Screenshot 10 Okt ("singkat jelas padat, langsung ke intinya"): baris utama hanya arah + jangka + kapan; detail
    2 baris (status, LAMA/BARU, dasar; aturan setelah rilis) tanpa daftar angka per detik/per jangka. Data asli."""
    import _pra_aset as A
    c = {"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00",
         "petunjuk_teruji": {"arah_emas": "turun", "tebak": {"WTI": 1.0}, "sepakat_lain": []}}
    g = A.tebak_kartu(c)
    # 15 Okt: angka PER ARAH tebakan (research/audit_arah.py) — TURUN minyak WTI saja 53% (dulu campuran 56%)
    assert g["persen"] == 53 and (g["lama"], g["baru"]) == (55, 50) and g["status"] == "lemah"
    r = A.satu({"title": "CPI m/m", "nama": "CPI", "sisa": "3 hari lagi", **g})
    assert r["teks"] == "CPI ▼ TURUN 53% (1–10 dtk) ⚠️ • 3 hari lagi"
    baris = r["bukti"].split("\n")                     # 14 Okt: detail = poin "• …" (tutup kertas, konsensus, orang)
    assert baris[0] == "• ⚠️ Lemah: 53% (1–10 dtk) • dulu 55% • sejak Okt 2021 50% • dasar: minyak WTI"
    assert baris[1].startswith("• Setelah rilis: ikuti arah emas detik 2 (≥ $0,50) s/d 5 mnt (")
    assert len(baris) == 2 and "per jangka" not in r["bukti"] and "lama/baru" not in r["bukti"]
    assert r["poin"][0].startswith("⚠️ Lemah: 53%")
    kosong = A.satu({"title": "PPI m/m", "nama": "PPI", "sisa": "5 hari lagi", "kons": {"f": "0.3%", "p": "0.4%"}})
    assert kosong["teks"] == "PPI ⚪ ≈50% (arah muncul ≤ 6 jam sebelum rilis) • 5 hari lagi"
    assert kosong["poin"][0].startswith("⚪ Belum ada petunjuk teruji → ≈ 50:50")
    assert kosong["poin"][1] == "📊 Perkiraan 0.3% (turun dari 0.4%): keluar di atas → emas TURUN • di bawah → emas NAIK" and kosong["bukti"].count("\n") == 3   # PPI: BARU < 85% → tanpa poin ✅
    assert kosong["poin"][-1].startswith("⚠️ Tapi masuk SETELAH detik 2")      # 15 Okt: kejar setelah detik 2 rata-rata rugi
    A.tambah_orang(kosong, {"poin": "👥 Orang: ritel 8 broker BUY 70% → info"})
    assert kosong["poin"][2] == "👥 Orang: ritel 8 broker BUY 70% → info" and kosong["poin"][3].startswith("Setelah rilis")
    assert kosong["bukti"].split("\n")[2] == "• 👥 Orang: ritel 8 broker BUY 70% → info"


def test_per_arah_aturan_lemah_satu_arah_tidak_ditampilkan(monkeypatch):
    """15 Okt (pengguna "curiga salah semua"): aturan dinilai PER ARAH tebakan. Core PPI berbalik tebakan TURUN dulu 37% →
    tidak ditampilkan (≈ 50:50); ISM Jasa berbalik TURUN 68% (lama & baru > 60%) tetap tampil."""
    import _pra_aset as A
    monkeypatch.setenv("CPI_DETIK", "0")
    st = A.per_arah("Core PPI • berbalik", "turun")
    assert st["benar"] < 40 and A.status_arah(st) == "acak"
    assert A.ringkas("Core PPI • berbalik", "turun")["status"] == "acak"
    ism = A.ringkas("ISM Jasa • berbalik", "turun")
    assert ism["status"] == "teruji" and "pembanding selalu-TURUN" in ism["bukti"]
    assert A.status_arah(A.per_arah("JOLTS • berbalik", "naik")) == "acak"
    assert A.per_arah("tren|berlawanan", "turun")["benar"] < 50
