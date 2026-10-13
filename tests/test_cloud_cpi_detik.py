"""⏱️ CPI detik 2–10 (aturan tutup kertas IDX|K, cloud/api/_cpi_detik.py) — tanpa jaringan."""
import io
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _cpi_detik  # noqa: E402
import _pra_aset  # noqa: E402

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
T0 = "2026-10-14T12:30:00+00:00"


def baris(nama, a, f, p):
    return {"country": "United States", "eventName": nama, "actual": a, "consensus": f, "previous": p}


def opener(rows):
    def buka(req, timeout=None):
        assert "date=2026-10-15" in req.full_url                    # API Nasdaq: tanggal rilis + 1 hari
        return io.BytesIO(json.dumps({"data": {"rows": rows}}).encode())
    return buka


def mk(t, p):
    return {"ticker": f"KXCPI-26SEP-T{t}", "yes_bid_dollars": f"{p:.4f}", "yes_ask_dollars": f"{p:.4f}"}


KALSHI = [mk(0.4, 0.91), mk(0.5, 0.65), mk(0.6, 0.18), mk(0.7, 0.01)]


def kartu():
    return {"mendatang": [{"title": "CPI m/m", "time": T0, "when": "Rab 19:30 WIB"},
                          {"title": "Core CPI m/m", "time": T0}, {"title": "CPI y/y", "time": T0}], "berita": []}


def test_nasdaq_urutan_terbalik_dikenali():
    rows = [baris("CPI", "&nbsp;", "3.6%", "3.4%"), baris("CPI", "&nbsp;", "0.6%", "0.4%"),   # y/y lebih dulu
            baris("Core CPI", "&nbsp;", "0.2%", "0.3%"), baris("Core CPI", "&nbsp;", "2.5%", "2.4%"),
            baris("CPI Index, n.s.a.", "&nbsp;", " ", "334.98")]
    n = _cpi_detik.nasdaq(datetime.fromisoformat(T0), opener(rows))
    assert (n["mm_f"], n["yy_f"], n["core_f"], n["core_yy_f"], n["nsa_p"]) == (0.6, 3.6, 0.2, 2.5, 334.98)
    assert n["nsa_f"] is None


def test_kalshi_cadangan_bila_indeks_kosong():
    prep = kartu()
    rows = [baris("CPI", "", "0.6%", "0.4%"), baris("CPI", "", "3.6%", "3.4%"),
            baris("Core CPI", "", "0.2%", "0.3%"), baris("Core CPI", "", "2.5%", "2.4%")]
    _cpi_detik.attach(prep, None, NOW, opener(rows), get=lambda s: KALSHI)
    g = prep["mendatang"][0]["cpi_detik"]
    assert g["jalur"] == "kalshi" and g["arah"] == "naik" and g["status"] == "tutup kertas"
    sr = _cpi_detik.DATA["uji"]["saring"]                 # patokan utama sejak 13 Okt: DETIK 2 aturan tersaring
    assert g["persen"] == round(sr["semua"]) and g["teks_sampai"] == "detik 2" and "di bawah 35%" in g["bukti"]
    assert "detik 2–10" in g["bukti"] and "sejak 2024" in g["bukti"] and "peringatan" not in g
    _pra_aset.attach(prep, NOW, None)
    s = prep["pra_satu"]
    assert s["teks"].startswith(f"CPI ▲ NAIK {g['persen']}% (detik 2)") and "⚠️" not in s["teks"]
    assert "✅ Teruji tutup kertas" in s["bukti"] and "Kalshi" in s["bukti"]
    assert prep["pra"]["status"] == "tutup kertas" and prep["pra"]["arah"] == "naik"


def test_indeks_tanpa_pembulatan_menang_atas_kalshi():
    # konsensus indeks NSA 337,20 → y/y tersirat 3,82% > 3,6% & m/m tersirat di atas 0,6% → CPI DI ATAS → emas TURUN
    # (Kalshi yang condong di bawah diabaikan karena indeks didahulukan)
    n = {"mm_f": 0.6, "yy_f": 3.6, "core_f": 0.2, "nsa_f": 337.20, "nsa_p": 334.98}
    cards = kartu()["mendatang"]
    g = _cpi_detik.tebak(datetime.fromisoformat(T0), cards, n, get=lambda s: KALSHI)
    assert g["jalur"] == "indeks" and g["arah"] == "turun" and g["indeks"]["tanda"] == {"c": 0, "y": 1, "m": 1}
    n["nsa_f"] = 335.90                                     # tersirat 3,42% < 3,6% → DI BAWAH → emas NAIK
    assert _cpi_detik.tebak(datetime.fromisoformat(T0), cards, n, get=lambda s: KALSHI)["arah"] == "naik"


def test_tanpa_petunjuk_tidak_menebak_dan_wti_lama_tidak_dipakai():
    prep = kartu()
    prep["mendatang"][0]["petunjuk_teruji"] = {"arah_emas": "turun", "tebak": {"WTI": 1.0}}   # aturan lama
    _cpi_detik.attach(prep, None, NOW, opener([]), get=lambda s: [])
    assert prep["mendatang"][0]["cpi_detik"] is None
    _pra_aset.attach(prep, NOW, None)
    assert prep["pra_satu"].get("arah") is None and "TURUN" not in prep["pra_satu"]["teks"]
    assert prep["pra"]["status"] == "acak"


class Toko:
    def __init__(self):
        self.d = {}

    def get_state(self, row):
        return self.d.get(row, {})

    def save_state(self, data, row):
        self.d[row] = data


def test_nasdaq_kosong_tidak_menimpa_cache():
    toko, t0 = Toko(), datetime.fromisoformat(T0)
    rows = [baris("CPI", "", "0.6%", "0.4%"), baris("CPI", "", "3.6%", "3.4%"),
            baris("CPI Index, n.s.a.", "", "336.10", "334.98")]
    assert _cpi_detik.konsensus_nasdaq(t0, toko, NOW, opener(rows))["nsa_f"] == 336.10
    nanti = NOW.replace(day=13)                              # TTL habis; Nasdaq kini "No record found"
    n = _cpi_detik.konsensus_nasdaq(t0, toko, nanti, opener([]))
    assert n["nsa_f"] == 336.10 and n["mm_f"] == 0.6
    assert toko.d["cpi_detik"]["nasdaq"][T0]["t"] == nanti.timestamp()


def test_nan_tidak_jadi_tanda():
    assert _cpi_detik.tanda(float("nan"), 0.02) == 0 and _cpi_detik.tanda(0.019, 0.02) == 0
    assert _cpi_detik.tanda(-0.03, 0.02) == -1


def test_cadangan_detik_2_10_bila_angka_lonjakan_tidak_ada(monkeypatch):
    monkeypatch.setattr(_cpi_detik, "DATA", {k: v for k, v in _cpi_detik.DATA.items() if k != "lonjakan"})
    n = {"mm_f": 0.6, "yy_f": 3.6, "core_f": 0.2, "nsa_f": 335.90, "nsa_p": 334.98}
    g = _cpi_detik.tebak(datetime.fromisoformat(T0), kartu()["mendatang"], n, get=lambda s: KALSHI)
    assert g["teks_sampai"] == "2–10 dtk" and g["persen"] == round(_cpi_detik.DATA["uji"]["semua"])


def test_env_mati(monkeypatch):
    monkeypatch.setenv("CPI_DETIK", "0")
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener([]), get=lambda s: KALSHI)
    assert "cpi_detik" not in prep["mendatang"][0]


ROWS_TURUN = [baris("CPI", "", "0.6%", "0.4%"), baris("CPI", "", "3.6%", "3.4%"),
              baris("Core CPI", "", "0.2%", "0.3%"), baris("Core CPI", "", "2.5%", "2.4%"),
              baris("CPI Index, n.s.a.", "", "337.20", "334.98")]           # indeks tersirat DI ATAS → emas TURUN


def mkc(t, p):
    return {"ticker": f"KXCPICORE-26SEP-T{t}", "yes_bid_dollars": f"{p:.4f}", "yes_ask_dollars": f"{p:.4f}"}


CORE_BAWAH = [mkc(0.1, 0.40), mkc(0.2, 0.10), mkc(0.3, 0.02)]               # core condong DI BAWAH 0,2%


def test_saring_turun_saat_tren_naik_tetap_tampil_lemah():
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=lambda s: KALSHI, tren=lambda: 1)
    g = prep["mendatang"][0]["cpi_detik"]
    lm = _cpi_detik.DATA["uji"]["saring"]["lemah"]
    assert g["arah"] == "turun" and g["status"] == "lemah" and "tren naik" in g["peringatan"]   # TIDAK dibuang
    assert g["persen"] == round(lm["semua"]) and g["teks_sampai"] == "detik 2" and "detik 1" in g["bukti"]
    _pra_aset.attach(prep, NOW, None)
    s = prep["pra_satu"]
    assert "▼ TURUN" in s["teks"] and "⚠️" in s["teks"] and "Lemah karena emas sedang tren naik" in s["bukti"]
    assert prep["pra"]["arah"] == "turun" and "⚠️" in prep["pra"]["teks"]


def test_saring_turun_kalshi_core_berlawanan_lemah():
    prep = kartu()
    get = lambda s: KALSHI if s == "KXCPI" else CORE_BAWAH                    # noqa: E731
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=get, tren=lambda: -1)
    g = prep["mendatang"][0]["cpi_detik"]
    assert g["arah"] == "turun" and g["status"] == "lemah" and "Kalshi core condong DI BAWAH" in g["peringatan"]


def test_saring_turun_tren_turun_tanpa_konflik_kuat():
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=lambda s: KALSHI if s == "KXCPI" else [],
                      tren=lambda: -1)
    g = prep["mendatang"][0]["cpi_detik"]
    assert g["arah"] == "turun" and g["status"] == "tutup kertas" and "peringatan" not in g
    assert g["persen"] == round(_cpi_detik.DATA["uji"]["saring"]["semua"])


def test_saring_tren_tidak_terbaca_lemah():
    g = {"arah": "turun", "konsensus": {"core": 0.2}}
    assert "tidak terbaca" in _cpi_detik.saring(datetime.fromisoformat(T0), g, lambda: None, get=lambda s: [])
    assert _cpi_detik.saring(datetime.fromisoformat(T0), {"arah": "naik"}, lambda: 1) is None   # NAIK tak disaring


def test_saring_env_mati_kembali_ke_angka_lama(monkeypatch):
    monkeypatch.setenv("CPI_SARING", "0")
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=lambda s: KALSHI, tren=lambda: 1)
    g = prep["mendatang"][0]["cpi_detik"]
    assert g["status"] == "tutup kertas" and g["teks_sampai"] == "lonjakan menit 1"


class Bar:
    def __init__(self, t, c):
        self.t, self.c = t, c


class Feed:
    def __init__(self, naik):
        self.naik, self.n = naik, 0

    def candles(self, n, interval="1h"):
        from datetime import timedelta
        self.n += 1
        assert interval == "1day"
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return [Bar(t0 + timedelta(days=i), 4000 + (i if self.naik else -i)) for i in range(286)]


def test_tren200_dan_cache():
    toko, t0 = Toko(), datetime.fromisoformat(T0)
    f = Feed(True)
    assert _cpi_detik.tren200(t0, toko, NOW, feed=f) == 1 and toko.d["cpi_tren"]["hari"] == "2026-10-14"
    assert _cpi_detik.tren200(t0, toko, NOW, feed=Feed(False)) == 1          # cache 6 jam: feed tidak dipanggil
    nanti = NOW.replace(hour=20)
    assert _cpi_detik.tren200(t0, toko, nanti, feed=Feed(False)) == -1


def test_allin_tebakan_kuat_masuk_tutup_detik_2():
    prep = kartu()
    rows = [baris("CPI", "", "0.6%", "0.4%"), baris("CPI", "", "3.6%", "3.4%"),
            baris("Core CPI", "", "0.2%", "0.3%"), baris("Core CPI", "", "2.5%", "2.4%")]
    _cpi_detik.attach(prep, None, NOW, opener(rows), get=lambda s: KALSHI)
    _pra_aset.attach(prep, NOW, None)
    a = prep["pra_satu"]["allin"]
    d = _cpi_detik.DATA["allin"]
    assert a["kuat"] and a["arah"] == "BUY" and a["keluar"] == "lentur"
    assert a["teks"] == "💥 Modal kecil: BUY 1 dtk sebelum rilis → detik 2 rugi TUTUP, untung tahan s/d detik 10"
    assert f"untung di {d['lentur']['untung_baru']}% rilis" in a["bukti"] and "2019–2021 GAGAL" in a["bukti"]
    assert "1:200 +$" in a["bukti"] and "HMR" in a["bukti"] and "akun terpisah" in a["bukti"] and "menang" not in a["bukti"]
    assert "₿ Kripto" in a["bukti"] and "ETH arah detik 2" in a["bukti"] and "emas tetap terbaik" in a["bukti"]
    # persen per detik: SETIAP detik 1–10 + 15 dtk…5 mnt ikut ke aplikasi
    pd_ = prep["pra_satu"]["per_detik"]
    assert all(str(h) in pd_ for h in list(range(1, 11)) + [30, 60, 300])
    assert pd_["2"] == round(_cpi_detik.DATA["uji"]["saring"]["per_detik"]["2"])
    assert "4 dtk" not in prep["pra"]["kecil"]                       # baris lama tetap ringkas (1/2/3/5/10)


def test_allin_tanpa_lentur_kembali_detik_2(monkeypatch):
    d = {k: v for k, v in _cpi_detik.DATA["allin"].items() if k != "lentur"}
    monkeypatch.setattr(_cpi_detik, "DATA", {**_cpi_detik.DATA, "allin": d})
    a = _pra_aset.allin({"title": "CPI m/m", "arah": "turun", "status": "tutup kertas"})
    assert a["keluar"] == "detik2" and a["teks"] == "💥 Modal kecil: SELL 1 dtk sebelum rilis → TUTUP detik 2"


def test_allin_lemah_jangan_dan_env_mati(monkeypatch):
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=lambda s: KALSHI, tren=lambda: 1)
    _pra_aset.attach(prep, NOW, None)
    a = prep["pra_satu"]["allin"]
    assert not a["kuat"] and "JANGAN" in a["teks"] and "modal habis" in a["bukti"]
    monkeypatch.setenv("CPI_ALLIN", "0")
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener(ROWS_TURUN), get=lambda s: KALSHI, tren=lambda: 1)
    _pra_aset.attach(prep, NOW, None)
    assert "allin" not in prep["pra_satu"]


def test_allin_bukan_cpi_tidak_ada():
    assert _pra_aset.allin({"title": "Non-Farm Employment Change", "arah": "naik", "status": "teruji"}) is None
    assert _pra_aset.allin({"title": "CPI m/m", "arah": None, "status": "acak"}) is None
