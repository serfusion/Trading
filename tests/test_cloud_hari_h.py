"""🎯 Perkiraan hari H / ✅ hasil (cloud/api/_hari_h.py) & 🗳️ Polymarket (_polymarket.py). Tanpa jaringan."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _hari_h  # noqa: E402
import _polymarket  # noqa: E402

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
T0 = "2026-10-02T12:30:00+00:00"
NFP = {"title": "Non-Farm Employment Change", "time": T0, "forecast": "89K", "released": False}
REAKSI = {"Non-Farm Employment Change": {"bawah": {"naik60": 0.8, "n": 67}, "atas": {"naik60": 0.2, "n": 94},
                                         "tahun": "2010–2025"}}


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row):
        return self.rows.get(row, {})

    def save_state(self, data, row):
        self.rows[row] = json.loads(json.dumps(data))


def test_perkiraan_gabungan_sumber_dan_riwayat(monkeypatch):
    monkeypatch.setattr(_hari_h, "REAKSI", REAKSI)
    monkeypatch.setattr(_hari_h, "VALID", {"Non-Farm Employment Change": {
        "gabungan": {"n": 20, "benar": 70.0, "tahun": "2024–2025"}}})
    key = f"{NFP['title']}|{T0}"
    store = Store()
    # pasar condong DI BAWAH perkiraan -> emas cenderung naik
    k, p = {key: {"atas": 0.25, "bawah": 0.75}}, {key: {"atas": 0.35, "bawah": 0.65}}
    pers = {"berita": [dict(NFP)]}
    _hari_h.attach(pers, [], store, NOW, k, p)
    h = pers["berita"][0]["hari_h"]
    # rata-rata: atas 0,30 bawah 0,70 -> 0,7x0,8 + 0,3x0,2 = 0,62
    assert h["teks"] == "EMAS 62% NAIK 🟢" and h["kuat"] and abs(h["p_naik"] - 0.62) < 1e-9
    assert "Kalshi: angka di atas perkiraan 25% / di bawah 75%" in h["bukti"] and "benar 70%" in h["bukti"]
    assert h["bukti"].startswith("KUNCI: Act di bawah 89K → emas NAIK 80% • Act di atas 89K → emas TURUN 80%")
    # 6 jam kemudian pasar berubah -> angka & riwayat berubah
    later = NOW + timedelta(hours=6)
    pers2 = {"berita": [dict(NFP)]}
    _hari_h.attach(pers2, [], store, later, {key: {"atas": 0.5, "bawah": 0.5}}, {})
    h2 = pers2["berita"][0]["hari_h"]
    assert h2["teks"] == "EMAS ≈ 50:50 ⚪" and not h2["kuat"] and "6 jam lalu 62%" in h2["bukti"]
    assert h2["riwayat"] == [0.62, 0.5]


def test_tanpa_uji_abu_abu_dan_hasil_setelah_act(monkeypatch):
    monkeypatch.setattr(_hari_h, "REAKSI", REAKSI)
    monkeypatch.setattr(_hari_h, "VALID", {})
    key = f"{NFP['title']}|{T0}"
    pers = {"berita": [dict(NFP)]}
    _hari_h.attach(pers, [], None, NOW, {key: {"atas": 0.1, "bawah": 0.9}}, {})
    assert pers["berita"][0]["hari_h"]["teks"].endswith("⚪") and "belum ada uji" in pers["berita"][0]["hari_h"]["bukti"]
    rel = dict(NFP, released=True)
    pers = {"berita": [rel]}
    _hari_h.attach(pers, [{"title": NFP["title"], "time": T0, "actual": "45K"}], None, NOW + timedelta(days=1), {}, {})
    r = pers["berita"][0]["hasil_rilis"]
    assert r["teks"].endswith("NAIK 🟢") and r["bukti"].startswith("Act 45K vs perkiraan 89K") and "hari_h" not in rel
    # detik 1-3 (reaksi.json asli): judul & deretan untuk aplikasi 3.18, ringkasan di bukti untuk aplikasi lama
    assert r["judul_tahap"].startswith("✅ Act 45K di bawah perkiraan 89K → arah emas • kejutan kecil") and [x["dtk"] for x in r["tahap"]][:3] == \
        ["1 dtk", "2 dtk", "3 dtk"] and "1 dtk " in r["bukti"] and "RIWAYAT" in r["bukti_tahap"]
    pers = {"berita": [dict(rel)]}
    _hari_h.attach(pers, [], None, NOW + timedelta(days=1), {}, {})
    assert pers["berita"][0]["hasil_rilis"]["teks"] == "menunggu Act…"


def test_polymarket_keranjang_nfp_dan_pengangguran():
    nfp = [{"groupItemTitle": "<-50k", "outcomePrices": '["0.05","0.95"]'},
           {"groupItemTitle": "0 to 50k", "outcomePrices": '["0.15","0.85"]'},
           {"groupItemTitle": "50k to 100k", "outcomePrices": '["0.40","0.60"]'},
           {"groupItemTitle": "100k to 150k", "outcomePrices": '["0.30","0.70"]'},
           {"groupItemTitle": "150k+", "outcomePrices": '["0.10","0.90"]'}]
    s = _polymarket.split(nfp, 89, True)
    # di bawah 89k: 0,05 + 0,15 + 0,40 x 39/50 = 0,512
    assert abs(s["bawah"] - 0.512) < 1e-9 and abs(s["atas"] - 0.488) < 1e-9
    ur = [{"groupItemTitle": "≤4.0%", "bestBid": "0.24", "bestAsk": "0.26"},
          {"groupItemTitle": "4.1%", "outcomePrices": '["0.40","0.60"]'},
          {"groupItemTitle": "≥4.2%", "outcomePrices": '["0.35","0.65"]'}]
    s = _polymarket.split(ur, 4.1, False)
    assert abs(s["bawah"] - 0.25) < 1e-9 and abs(s["sama"] - 0.40) < 1e-9 and abs(s["atas"] - 0.35) < 1e-9
    assert _polymarket.split(ur, 4.0, False) is None                      # konsensus di keranjang terbuka


def test_polymarket_fed_berikutnya_dan_baris_kartu():
    ev = [{"title": "Fed Decision in December?", "endDate": "2026-12-10T04:59:00Z", "volume": "2000000",
           "markets": [{"groupItemTitle": "No change", "outcomePrices": '["0.6","0.4"]'}]},
          {"title": "Fed Decision in October?", "endDate": "2026-10-29T03:59:00Z", "volume": "21800000",
           "markets": [{"groupItemTitle": "No change", "outcomePrices": '["0.74","0.26"]'},
                       {"groupItemTitle": "25 bps increase", "outcomePrices": '["0.26","0.74"]'}]}]
    f = _polymarket.fed_next(NOW, lambda title: ev)
    assert f["judul"] == "Fed Decision in October?" and list(f["pilihan"]) == ["No change", "25 bps increase"]
    line = _hari_h.fed_line(f, NOW)
    assert line["teks"] == "74% TETAP" and line["label"] == "🏦 Keputusan Fed 28 Okt"
    assert "naik 25 bps 26%" in line["bukti"] and "21.8 jt" in line["bukti"]


def test_uji_sampel_kecil_dan_buruk_tetap_abu_abu(monkeypatch):
    monkeypatch.setattr(_hari_h, "REAKSI", REAKSI)
    key = f"{NFP['title']}|{T0}"
    for v, kata in (({"n": 7, "benar": 86.0, "tahun": "2023–2025"}, "sampel kecil"),
                    ({"n": 14, "benar": 50.0, "tahun": "2024–2025"}, "tidak lebih baik")):
        monkeypatch.setattr(_hari_h, "VALID", {NFP["title"]: {"Kalshi": v}})
        pers = {"berita": [dict(NFP)]}
        _hari_h.attach(pers, [], None, NOW, {key: {"atas": 0.1, "bawah": 0.9}}, {})
        h = pers["berita"][0]["hari_h"]
        assert h["teks"].endswith("⚪") and not h["kuat"] and kata in h["bukti"]
