"""🎲 sebaran Kalshi sebelum konsensus, 🧭 petunjuk teruji, 🗣️ pernyataan, 🎯 baris pasar CPI — tanpa jaringan."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _kalshi  # noqa: E402
import _pernyataan  # noqa: E402
import _petunjuk  # noqa: E402
import _prediksi  # noqa: E402

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
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
    mem = {"Core CPI m/m": {"s": 1}, "ISM Services PMI": {"s": 1}}
    core = {"title": "Core CPI m/m", "hari_h": {"pasar": {"atas": 0.365, "bawah": 0.215}}}
    b = _petunjuk.blok(core, mem)
    assert "SEPAKAT" in b["teks"] and b["arah_emas"] == "turun"
    ism = _petunjuk.blok({"title": "ISM Services PMI"}, mem)
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
