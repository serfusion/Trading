"""🎯 Persiapan berita (cloud/api/_persiapan.py) — pengganti contoh pertanyaan di tab Tanya."""
import json
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
    assert _persiapan.group_of("Unemployment Rate") == "NFP" and _persiapan.group_of("Average Hourly Earnings m/m") == "NFP"
    assert _persiapan.group_of("ADP Non-Farm Employment Change") is None
    assert _persiapan.group_of("Unemployment Claims") == "CLAIMS"


def test_detik_json_kosong_tidak_merusak_kartu(monkeypatch):
    monkeypatch.setattr(_persiapan, "DETIK", {})
    d = _persiapan.cards(ROWS, NOW)
    assert all(c["detik"] == "" for c in d["berita"]) and d["detik"] == {}


def test_detik_utamakan_exness(monkeypatch):
    fake = {"XAU": {"SEMUA": {"teks": "duka", "alarm": "duka"}},
            "XAU_EXNESS": {"SEMUA": {"teks": "exness", "alarm": "exness"}}}
    monkeypatch.setattr(_persiapan, "DETIK", fake)
    assert _persiapan.detik("NFP") == "exness" and _persiapan.alarm_texts()["NFP"]["alarm"] == "exness"


def test_kesimpulan_otomatis_setelah_act_keluar():
    k = _persiapan.kesimpulan("CPI m/m", "0.2%", "0.3%")
    assert k["arah"] == "naik" and k["persen"] >= 60 and k["kuat"] and k["teks"] == f"{k['persen']}% NAIK 🟢"
    assert k["catatan"].startswith("Act < perkiraan → emas 1 dtk ") and "1 mnt" in k["catatan"] and "rilis)" in k["catatan"]
    assert _persiapan.kesimpulan("CPI m/m", "", "0.3%") is None
    assert _persiapan.kesimpulan("Tidak dikenal", "1", "2") is None
    assert _persiapan.kesimpulan("Non-Farm Employment Change", "250K", "98K")["hasil"] == "atas"


def test_skenario_angka_besar_dan_bukti_tahun():
    sk = {x["hasil"]: x for x in _persiapan.skenario("CPI m/m")}
    assert set(sk) == {"bawah", "atas"} and sk["bawah"]["label"] == "Data < perkiraan"
    assert sk["bawah"]["teks"].endswith("% NAIK 🟢") and sk["bawah"]["bukti"].startswith("teruji 2010–")
    assert "menang" not in json.dumps(sk, ensure_ascii=False)
    # lemah / tidak konsisten: persen tetap tampil, abu-abu, diberi label
    assert _persiapan.arah_emas({"naik1j": 51, "baru_naik1j": 45, "n": 70, "tahun": "2012–2025"})["teks"] == "51% naik ⚪"
    tk = _persiapan.arah_emas({"naik1j": 34, "baru_naik1j": 55, "n": 82, "tahun": "2012–2025"})
    assert not tk["kuat"] and tk["bukti"].startswith("tidak konsisten")
    assert [x["hasil"] for x in _persiapan.skenario("Federal Funds Rate")] == ["sesuai"]


def test_detik_ringkas_tanpa_kata_menang(monkeypatch):
    def row(avg, wr=77.0, x=-1.87):
        return {"tahun": "2015–2026", "pending1": {"n": 130, "wr": wr, "avg": avg, "x": x, "x_feed": "Dukascopy"}}
    monkeypatch.setattr(_persiapan, "DETIK", {"XAU_EXNESS": {"NFP": row(3.18), "PPI": row(-0.13), "FOMC": row(-1.56)}})
    d = _persiapan.detik_ringkas("NFP")
    assert d["teks"] == "77% untung ⚠️" and "teruji 2015–2026 (130 rilis" in d["bukti"] and "belum terbukti" in d["bukti"]
    assert _persiapan.detik_ringkas("PPI")["teks"] == "≈ impas ⚪"
    assert _persiapan.detik_ringkas("FOMC")["teks"] == "RUGI 🔴" and _persiapan.detik_ringkas("GDP") is None
    assert "menang" not in _persiapan.detik_singkat("NFP") and _persiapan.detik_singkat("NFP").startswith("Pending ±$1: 77%")


def test_reaksi_1_menit_diutamakan_cadangan_1_jam(monkeypatch):
    monkeypatch.setattr(_persiapan, "REAKSI", {})
    k = _persiapan.kesimpulan("CPI m/m", "0.2%", "0.3%")
    assert "emas 1 jam" in k["catatan"] and k["catatan"].count("teruji 2012–") == 1
    monkeypatch.setattr(_persiapan, "REAKSI", {"CPI m/m": {"bawah": {"naik60": 0.9, "n": 50, "baru_naik60": 0.95},
                                                           "tahun": "2010–2025"}})
    k = _persiapan.kesimpulan("CPI m/m", "0.2%", "0.3%")
    assert k["teks"] == "90% NAIK 🟢" and "emas 1 menit" in k["catatan"] and "sejak Okt 2021: 95% naik" in k["catatan"]


CEPAT = {"Non-Farm Employment Change": {
    "bawah": {"naik60": 0.81, "n": 67, "baru_naik60": 0.87,
              "cepat": {"1": {"naik": 0.57, "n": 65, "gerak": 0.17, "ex": 0.59, "baru": 0.47},
                        "2": {"naik": 0.85, "n": 67, "gerak": 2.68, "ex": 0.82, "baru": 0.87},
                        "3": {"naik": 0.58, "n": 67, "gerak": 3.1, "ex": 0.4, "baru": 0.6}}},
    "atas": {"naik60": 0.19, "n": 94, "baru_naik60": 0.32,
             "cepat": {"2": {"naik": 0.26, "n": 94, "gerak": 2.26, "ex": 0.22, "baru": 0.26}}},
    "tahun": "2010–2025"}}


def test_tahap_detik_1_2_3_dan_1_menit(monkeypatch):
    """Permintaan 2 Okt 2026: persentase arah emas 1 detik setelah rilis (plus 2-3 detik & 1 menit)."""
    monkeypatch.setattr(_persiapan, "REAKSI", CEPAT)
    st = _persiapan.tahap("Non-Farm Employment Change", "bawah")
    assert [x["dtk"] for x in st] == ["1 dtk", "2 dtk", "3 dtk", "1 mnt"]
    assert st[0]["teks"] == "belum gerak ⚪" and not st[0]["kuat"]          # ±$0,17 ≈ spread
    assert (st[0]["angka"], st[0]["kata"], st[1]["angka"], st[1]["kata"]) == ("±$0,17", "belum gerak ⚪", "85%", "NAIK 🟢")
    assert st[1]["teks"] == "85% NAIK 🟢" and st[1]["kuat"] and st[1]["exness"] == 82
    assert st[2]["teks"] == "58% naik ⚪" and not st[2]["kuat"]             # Exness berlawanan -> abu-abu
    assert st[3]["teks"] == "81% NAIK 🟢"
    assert _persiapan.tahap_teks(st) == ("1 dtk belum gerak (±$0,17) • 2 dtk 85% NAIK (±$2,68) • 3 dtk 58% naik • "
                                         "1 mnt 81% NAIK")
    assert _persiapan.tahap("Non-Farm Employment Change", "atas")[0]["teks"] == "74% TURUN 🔴"
    sk = {x["hasil"]: x for x in _persiapan.skenario_hentakan("Non-Farm Employment Change", "89K")}
    assert sk["bawah"]["label"] == "⚡ Hentakan 1 menit bila Act < 89K" and sk["bawah"]["teks"] == "81% NAIK 🟢"
    assert sk["bawah"]["label_tahap"] == "⚡ Bila Act < 89K → arah emas" and len(sk["bawah"]["tahap"]) == 4
    assert sk["bawah"]["bukti"].startswith("1 dtk belum gerak") and "detik 1–3" not in sk["bawah"]["bukti"]
    assert "detik 1–3 dicek di tick Exness" in sk["bawah"]["bukti_tahap"]
    k = _persiapan.kesimpulan("Non-Farm Employment Change", "45K", "89K")
    assert k["catatan"].startswith("Act < perkiraan → emas 1 dtk belum gerak") and k["tahap"][1]["teks"] == "85% NAIK 🟢"
    # tanpa data detik (reaksi lama): tetap seperti sebelumnya
    monkeypatch.setattr(_persiapan, "REAKSI", {"CPI m/m": {"bawah": {"naik60": 0.9, "n": 50}, "tahun": "2010–2025"}})
    assert "tahap" not in _persiapan.skenario_hentakan("CPI m/m", "0.3%")[0]
    assert _persiapan.kesimpulan("CPI m/m", "0.2%", "0.3%")["catatan"].startswith("Act < perkiraan → emas 1 menit •")


def test_reaksi_json_berisi_detik_dari_dua_feed():
    nfp = _persiapan.REAKSI["Non-Farm Employment Change"]
    for hasil in ("bawah", "atas"):
        c = nfp[hasil]["cepat"]
        assert set(c) == {"1", "2", "3"} and all({"naik", "n", "gerak", "ex", "baru"} <= set(x) for x in c.values())


def test_kejutan_besar_kecil_mengubah_persen():
    kecil = _persiapan.kesimpulan("Non-Farm Employment Change", "60K", "89K")
    besar = _persiapan.kesimpulan("Non-Farm Employment Change", "-20K", "89K")
    assert kecil["kejutan"]["ukuran"] == "kecil" and besar["kejutan"]["ukuran"] == "besar"
    assert "kejutan BESAR (109K ≥ 84K)" in besar["catatan"] and "$" in besar["kejutan"]["bukti"]
    assert next(x for x in besar["tahap"] if x["dtk"] == "1 mnt")["persen"] == besar["persen"]   # sel 1 mnt ikut kejutan


def test_sel_3_dan_6_jam_melemah(monkeypatch):
    """2 Okt 2026: NFP naik $40 di menit awal lalu berbalik -> tampilkan juga 3 & 6 jam (XAU M15)."""
    cel = {k: dict(v) for k, v in CEPAT["Non-Farm Employment Change"].items() if isinstance(v, dict)}
    cel["bawah"]["jam"] = {"3": {"naik": 0.70, "n": 67, "baru": 0.667}, "6": {"naik": 0.687, "n": 67, "baru": 0.533}}
    monkeypatch.setattr(_persiapan, "REAKSI", {"Non-Farm Employment Change": {**cel, "tahun": "2010–2025"}})
    st = {x["dtk"]: x for x in _persiapan.tahap("Non-Farm Employment Change", "bawah")}
    assert st["3 jam"]["angka"] == "70%" and st["3 jam"]["kata"] == "NAIK 🟢"
    assert st["6 jam"]["angka"] == "53–69%" and st["6 jam"]["kata"] == "naik ⚪" and not st["6 jam"]["kuat"]
    assert _persiapan.tahap_teks(list(st.values())).endswith("3 jam 70% NAIK • 6 jam 53–69% naik")


def test_reaksi_json_berisi_3_dan_6_jam():
    j = _persiapan.REAKSI["Non-Farm Employment Change"]["bawah"]["jam"]
    assert set(j) == {"3", "6"} and j["6"]["n"] >= 30
