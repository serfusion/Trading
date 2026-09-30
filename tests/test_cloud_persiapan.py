"""🎯 Persiapan berita (cloud/api/_persiapan.py) — pengganti contoh pertanyaan di tab Tanya."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _persiapan  # noqa: E402

NOW = datetime(2026, 9, 30, 10, tzinfo=timezone.utc)
ROWS = [
    {"country": "USD", "impact": "High", "title": "Non-Farm Employment Change", "date": "2026-10-02T08:30:00-04:00",
     "forecast": "90K", "previous": "162K"},
    {"country": "USD", "impact": "High", "title": "Core PCE Price Index m/m", "date": "2026-09-30T08:30:00-04:00",
     "forecast": "0.3%", "previous": "0.2%"},
    {"country": "USD", "impact": "Medium", "title": "JOLTS Job Openings", "date": "2026-09-29T10:00:00-04:00"},
    {"country": "EUR", "impact": "High", "title": "CPI m/m", "date": "2026-10-01T09:00:00+02:00"},
    {"country": "USD", "impact": "Low", "title": "Unemployment Claims", "date": "2026-10-01T08:30:00-04:00"},
    {"country": "USD", "impact": "High", "title": "President Trump Speaks", "date": "2026-10-01T08:30:00-04:00"},
    {"country": "USD", "impact": "High", "title": "CPI m/m", "date": "bukan tanggal"},
]


def test_kartu_hanya_berita_usd_yang_punya_statistik():
    d = _persiapan.cards(ROWS, NOW)
    assert [c["title"] for c in d["berita"]] == ["Core PCE Price Index m/m", "Non-Farm Employment Change"]
    nfp = d["berita"][1]
    assert nfp["when"] == "Jum 02 Okt 19:30 WIB" and not nfp["released"] and nfp["forecast"] == "90K"
    assert abs(sum(nfp["hasil"].values()) - 100) <= 2 and nfp["n"] >= 100
    assert set(nfp["emas_jika"]) >= {"bawah", "atas"} and nfp["arah"] in ("≈ lempar koin", "condong naik",
                                                                            "condong turun")
    assert any("ADP" in p for p in nfp["petunjuk"]) and "Polymarket" in d["kesimpulan"]


def test_berita_lewat_lebih_dari_6_jam_dibuang():
    later = datetime(2026, 9, 30, 19, tzinfo=timezone.utc)              # PCE 12:30 UTC -> 6,5 jam lalu
    assert [c["title"] for c in _persiapan.cards(ROWS, later)["berita"]] == ["Non-Farm Employment Change"]
    assert _persiapan.cards(ROWS, datetime(2026, 9, 30, 13, tzinfo=timezone.utc))["berita"][0]["released"]
    assert _persiapan.cards(None, NOW)["berita"] == []


def test_label_arah():
    assert _persiapan.lean(57, 51) == "≈ lempar koin"
    assert _persiapan.lean(62, 65) == "condong naik"
    assert _persiapan.lean(38, 35) == "condong turun"
    assert _persiapan.lean(65, 52) == "≈ lempar koin"                  # harus kuat di semua data DAN 5 tahun
    assert _persiapan.lean(None, 60) == "data kurang"


def test_statistik_konsisten():
    for ev, st in _persiapan.STATS["dasar"].items():
        for per in ("semua", "lama", "baru"):
            assert abs(sum(st[per][k] for k in ("bawah", "sesuai", "atas")) - 100) <= 2, (ev, per)
        assert 0 <= st["emas_sebelum"]["naik1j"] <= 100


def test_detik_pertama_per_grup(monkeypatch):
    fake = {"XAU": {"NFP": {"teks": "Detik pertama (XAU): NFP", "alarm": "XAU NFP"},
                    "SEMUA": {"teks": "Detik pertama (XAU): semua", "alarm": "XAU semua"}},
            "BTC": {"SEMUA": {"teks": "BTC semua", "alarm": "BTC semua"}}}
    monkeypatch.setattr(_persiapan, "DETIK", fake)
    d = _persiapan.cards(ROWS, NOW)
    by = {c["title"]: c for c in d["berita"]}
    assert by["Non-Farm Employment Change"]["detik"] == "Detik pertama (XAU): NFP BTC semua"
    assert by["Core PCE Price Index m/m"]["detik"] == "Detik pertama (XAU): semua BTC semua"   # PCE -> SEMUA
    assert d["detik"]["NFP"]["alarm"] == "XAU NFP BTC semua" and d["detik"]["SEMUA"]["alarm"] == "XAU semua BTC semua"
    assert _persiapan.group_of("Federal Funds Rate") == "FOMC" and _persiapan.group_of("Pidato") is None


def test_detik_json_kosong_tidak_merusak_kartu(monkeypatch):
    monkeypatch.setattr(_persiapan, "DETIK", {})
    d = _persiapan.cards(ROWS, NOW)
    assert all(c["detik"] == "" for c in d["berita"]) and d["detik"] == {}
