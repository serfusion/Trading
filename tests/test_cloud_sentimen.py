"""👥 Sentimen orang (cloud/api/_sentimen.py) — tanpa jaringan."""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _pra_aset  # noqa: E402
import _sentimen  # noqa: E402

NOW = datetime(2026, 10, 14, 4, 0, tzinfo=timezone.utc)

# potongan teks asli survei Kitco 9 Okt 2026
ARTIKEL = ("<html><body><p>Fourteen Wall Street analysts participated in Kitco News' Gold Survey this week. Seven experts, "
           "or 50%, expect gold to rise next week, while only two, representing 14%, saw the yellow metal declining. "
           "The remaining five analysts, 36% of the total, said they couldn’t predict gold’s direction.</p><p>Meanwhile, "
           "206 votes were cast in Kitco’s online poll, with Main Street investors still failing to reclaim their bullish "
           "majority. 93 retail traders, or 45%, looked for&nbsp;gold prices to rise next week, while 77 others, or 37%, "
           "predicted the yellow metal would lose ground. The remaining 36 investors, representing 18% of the total, "
           "expected to see sideways price action.</p></body></html>")
URL = "/news/article/2026-10-09/wall-street-nears-bullish-majority-after-golds-late-week-rally-main-street"


class Toko:
    def __init__(self):
        self.d = {}

    def get_state(self, row):
        return self.d.get(row, {})

    def save_state(self, data, row):
        self.d[row] = data


def opener_ok(dipanggil):
    def op(req, timeout=None):
        u = req.full_url
        dipanggil.append(u)
        if "graphql" in u:
            body = {"data": {"nodeListByCategory": {"items": [
                {"title": "Gold weakens", "urlAlias": "/news/article/2026-10-13/metals-weaken"},
                {"title": "Wall Street nears bullish majority, Main Street…", "urlAlias": URL},
                {"title": "old", "urlAlias": "/news/article/2026-10-02/wall-street-x-main-street-y"}, {}]}}}
            return io.BytesIO(json.dumps(body).encode())
        if "kitco.com/news" in u:
            assert u.endswith(URL)                                      # survei TERBARU yang dibaca
            return io.BytesIO(ARTIKEL.encode())
        if "fxssi" in u:
            return io.BytesIO(json.dumps({"brokers": {"myfxbook": {"XAUUSD": "61.57"}, "ftroanda": {"XAUUSD": "78.07"},
                                                      "fiboforx": {"EURUSD": "50"}, "xm": {"XAUUSD": "65.35"}}}).encode())
        if "cftc" in u:
            return io.BytesIO(json.dumps([{"report_date_as_yyyy_mm_dd": "2026-10-06T00:00:00.000",
                                           "nonrept_positions_long_all": "50464",
                                           "nonrept_positions_short_all": "16272"}]).encode())
        raise AssertionError(u)
    return op


def test_parse_kitco_main_street_dan_wall_street():
    r = _sentimen.kitco_parse(ARTIKEL)
    assert r == {"ms_n": 206, "ms_up": 45.0, "ms_down": 37.0, "ms_side": 18.0, "ws_up": 50.0, "ws_down": 14.0,
                 "ws_side": 36.0}


def test_ambil_semua_sumber_lalu_cache():
    dip, toko = [], Toko()
    s = _sentimen.ambil(toko, NOW, opener_ok(dip))
    assert s["kitco"]["tgl"] == "2026-10-09" and s["kitco"]["ms_n"] == 206
    assert s["fxssi"] == {"buy": 68, "n_broker": 3} and s["cot"] == {"tgl": "2026-10-06", "long": 76}
    n = len(dip)
    s2 = _sentimen.ambil(toko, NOW + timedelta(minutes=30), opener_ok(dip))
    assert s2 == s and len(dip) == n                                     # semua dari cache
    _sentimen.ambil(toko, NOW + timedelta(hours=2), opener_ok(dip))
    assert [u for u in dip[n:] if "fxssi" in u] and not [u for u in dip[n:] if "cftc" in u]   # FXSSI 1 jam, COT 12 jam


def test_sumber_gagal_pakai_nilai_lama_dan_poin_ringkas():
    toko = Toko()
    _sentimen.ambil(toko, NOW, opener_ok([]))

    def mati(req, timeout=None):
        raise OSError("blok")
    s = _sentimen.ambil(toko, NOW + timedelta(days=2), mati)
    assert s["fxssi"]["buy"] == 68 and s["kitco"]["ms_up"] == 45.0      # nilai lama tetap tampil
    dip = []
    _sentimen.ambil(toko, NOW + timedelta(days=2, minutes=10), opener_ok(dip))
    assert dip == []                                                      # baru gagal → jeda 30 mnt, GET tidak melambat
    _sentimen.ambil(toko, NOW + timedelta(days=2, minutes=40), opener_ok(dip))
    assert dip                                                            # lewat jeda → dicoba lagi
    p = _sentimen.poin(s)
    assert p == "👥 Orang: survei 45% naik • ritel 68% BUY • COT 76% long (info, tidak mengubah arah)"
    assert _sentimen.poin({}) is None
    assert _sentimen.ambil(None, NOW, mati) == {}


def test_attach_masuk_poin_di_bawah_xau_tanpa_ubah_arah(monkeypatch):
    prep = {"mendatang": [{"title": "PPI m/m", "time": "2026-10-15T12:30:00+00:00", "forecast": "0.3%",
                           "previous": "0.2%"}], "berita": []}
    _sentimen.attach(prep, Toko(), NOW, opener_ok([]))
    assert prep["sentimen"]["poin"].startswith("👥 Orang:")
    _pra_aset.attach(prep, NOW, None)
    s = prep["pra_satu"]
    assert s["teks"].startswith("PPI ⚪ ≈50%")                        # arah/persen tidak diubah oleh sentimen
    assert any(x.startswith("👥 Orang:") for x in s["poin"]) and "• 📊 Perkiraan 0.3% (naik dari 0.2%): keluar di atas → emas TURUN • di bawah → emas NAIK" in s["bukti"]
    assert s["poin"][-1].startswith("Setelah rilis")
    monkeypatch.setenv("SENTIMEN", "0")
    p2 = {"mendatang": list(prep["mendatang"]), "berita": []}
    _sentimen.attach(p2, Toko(), NOW, opener_ok([]))
    assert "sentimen" not in p2
