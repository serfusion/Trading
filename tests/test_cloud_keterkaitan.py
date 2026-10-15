"""🔗 15 Okt 2026 (pengguna: "semua news … buat secara keterkaitan, betulkan bug"): satu arah per rilis bersamaan setelah
Act, tebakan < 52% tidak tampil sebagai arah, keterkaitan berita sebelumnya (info), memori hasil semua berita. Tanpa jaringan."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))

import _hari_h  # noqa: E402
import _keterkaitan  # noqa: E402
import _persiapan  # noqa: E402
import _ppi_wti  # noqa: E402
import _pra_aset  # noqa: E402
import _rekam  # noqa: E402
import _sentimen  # noqa: E402


class Toko(dict):
    def get_state(self, r):
        return self.get(r, {})

    def save_state(self, d, r):
        self[r] = d


def gabung(rows):
    cal = [{"title": t, "time": "T", "arah": _persiapan.kesimpulan(t, a, f)} for t, a, f in rows]
    _persiapan.satukan(cal, "arah")
    return {c["title"]: c["arah"] for c in cal}


def test_satu_arah_per_rilis_cpi_14okt():
    # CPI 14 Okt: m/m sama dengan perkiraan (dulu "60% NAIK 🟢"), inti & tahunan di atas → semua TURUN (emas memang turun)
    g = gabung([("CPI m/m", "0.6%", "0.6%"), ("Core CPI m/m", "0.3%", "0.2%"), ("CPI y/y", "3.7%", "3.6%")])
    assert {a["arah"] for a in g.values()} == {"turun"}
    assert g["CPI m/m"]["ikut"] == "Core CPI m/m" and "CPI inti di atas perkiraan" in g["CPI m/m"]["catatan"]
    assert "ikut" not in g["Core CPI m/m"]                                   # judul utama tidak diubah


def test_rilis_berlawanan_pakai_tabel_pasangan():
    # inti di atas, tahunan di bawah: dulu emas ikut tahunan hanya 54% (13 rilis) → ≈ 50:50, bukan dua arah
    g = gabung([("CPI m/m", "0.3%", "0.3%"), ("Core CPI m/m", "0.3%", "0.2%"), ("CPI y/y", "3.5%", "3.6%")])
    assert all(a["arah"] is None and a["teks"].startswith("≈ 50:50") for a in g.values())
    # NFP di atas, upah di bawah: dulu 82% ikut NFP tetapi sejak Okt 2021 hanya 50% → ≈ 50:50
    g = gabung([("Non-Farm Employment Change", "120K", "70K"), ("Average Hourly Earnings m/m", "0.1%", "0.3%")])
    assert all(a["arah"] is None for a in g.values()) and "sejak 50%" in g["Average Hourly Earnings m/m"]["catatan"]
    # NFP di atas, pengangguran naik: emas ikut NFP 76% (66 rilis; lama 84 / baru 59) → TURUN
    g = gabung([("Non-Farm Employment Change", "120K", "70K"), ("Unemployment Rate", "4.6%", "4.5%")])
    assert {a["arah"] for a in g.values()} == {"turun"} and all(a["teks"].startswith("76%") for a in g.values())
    # PPI di bawah, Retail di atas: emas ikut Retail 67% (12 rilis, sampel kecil) → turun ⚪ (bukan 🔴 kuat)
    g = gabung([("PPI m/m", "0.3%", "0.6%"), ("Retail Sales m/m", "0.8%", "0.3%")])
    assert {a["arah"] for a in g.values()} == {"turun"} and not any(a["kuat"] for a in g.values())


def test_hasil_rilis_kartu_juga_satu_arah():
    berita = [{"title": t, "time": "2026-10-14T12:30:00+00:00", "forecast": f, "released": True}
              for t, f in (("CPI m/m", "0.6%"), ("Core CPI m/m", "0.2%"), ("CPI y/y", "3.6%"))]
    cal = [{"title": "CPI m/m", "time": berita[0]["time"], "actual": "0.6%"},
           {"title": "Core CPI m/m", "time": berita[0]["time"], "actual": "0.3%"},
           {"title": "CPI y/y", "time": berita[0]["time"], "actual": "3.7%"}]
    prep = {"berita": berita}
    _hari_h.attach(prep, cal, Toko(), datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc), {}, {})
    hs = [c["hasil_rilis"] for c in prep["berita"]]
    assert {h["arah"] for h in hs} == {"turun"} and "TURUN" in hs[0]["teks"] and hs[0].get("label")


def test_ppi_berlawanan_tanpa_arah_dan_alasan():
    t0 = "2026-10-15T12:30:00+00:00"
    h = {"arah": None, "acak": True, "status": "acak", "alasan": "minyak → emas NAIK, CPI inti DI ATAS → emas TURUN; "
                                                                "tebakan NAIK seperti ini dulu hanya benar 43% (7 rilis)"}
    kartu = [{"title": "PPI m/m", "time": t0, "when": "Kam 15 Okt 19:30 WIB", "ppi_wti": None, "ppi_wti_acak": h,
              "forecast": "0.6%", "previous": "0.4%"},
             {"title": "Retail Sales m/m", "time": t0, "when": "Kam 15 Okt 19:30 WIB"}]
    prep = {"berita": kartu, "mendatang": []}
    now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    dl = _pra_aset.daftar(prep, now)
    assert dl[0]["arah"] is None and "petunjuk berlawanan" in dl[0]["teks"] and "43%" in dl[0]["bukti"]
    s = _pra_aset.satu(dl[0])
    assert "⚪ ≈50% (petunjuk berlawanan)" in s["teks"] and s["poin"][0].startswith("⚪ Petunjuk berlawanan")
    _pra_aset.tandai(prep, dl, now)
    assert {c["arah_detik"]["arah"] for c in kartu} == {None}
    assert "petunjuk berlawanan" in kartu[0]["arah_detik"]["teks"]


def test_kartu_ikut_keputusan_daftar_tren_berlawanan():
    """Dulu: baris XAU "NFP ≈50%" (petunjuk & tren berlawanan) tetapi kartu "NFP: emas turun 57%" (dua arah)."""
    t0 = "2026-12-04T13:30:00+00:00"
    kartu = [{"title": "Non-Farm Employment Change", "time": t0}, {"title": "Unemployment Rate", "time": t0}]
    row = {"title": "Non-Farm Employment Change", "time": t0, "arah": None, "status": "acak",
           "tren": {"hubungan": "berlawanan"}}
    _pra_aset.tandai({"berita": kartu}, [row], datetime(2026, 12, 4, 8, 0, tzinfo=timezone.utc))
    assert all(c["arah_detik"]["arah"] is None for c in kartu)


def test_status_sel_aturan_audit():
    assert _ppi_wti.status_sel(43, 7) == "acak"
    assert _ppi_wti.status_sel(90, 10, 75, 4, 100, 6) == "belum terbukti"           # 9/10: sampel kecil, bukan ✅
    assert _ppi_wti.status_sel(72.5, 40, 61.9, 21, 84.2, 19) == "tutup kertas"
    assert _ppi_wti.status_sel(71.4, 7, 0.0, 2, 100, 5) == "belum terbukti"         # LAMA 2 rilis tidak menentukan
    assert _ppi_wti.status_sel(60, 30, 45, 10, 70, 20) == "acak"                    # LAMA < 50% (≥ 5 rilis)
    assert _ppi_wti.status_sel(53, 40) == "lemah"


def test_sentimen_data_sebagian_tidak_galat():
    assert _sentimen.poin({"kitco": {"tgl": "x"}, "fxssi": {"buy": 61}}) == "👥 Orang: ritel 61% BUY (info, tidak mengubah arah)"
    assert _sentimen.poin({"kitco": "rusak"}) is None


def test_keterkaitan_memori_dan_blok(monkeypatch):
    monkeypatch.setitem(_keterkaitan.DATA, "tampil", {"Retail Sales m/m": [
        {"A": "CPI m/m", "hubungan": "searah", "angka_wf": 64.0, "n_angka_wf": 60, "emas_wf": 57.0, "status_emas": "lemah"},
        {"A": "Advance GDP q/q", "hubungan": "searah", "angka_wf": 65.0, "n_angka_wf": 46, "emas_wf": 57.0,
         "status_emas": "lemah"}]})
    toko = Toko()
    cal = [{"title": "CPI m/m", "time": "2026-11-10T13:30:00+00:00", "actual": "0.5%", "forecast": "0.3%"},
           {"title": "Advance GDP q/q", "time": "2026-10-29T12:30:00+00:00", "actual": "3.2%", "forecast": "2.8%"},
           {"title": "Retail Sales m/m", "time": "2026-10-15T12:30:00+00:00", "actual": "0.8%", "forecast": "0.3%"}]
    mem = _keterkaitan.ingat(cal, toko)
    assert toko["hasil_rilis"]["mem"]["CPI m/m"] == {"s": 1, "act": "0.5%", "f": "0.3%", "time": "2026-11-10T13:30:00+00:00"}
    kartu = {"title": "Retail Sales m/m", "time": "2026-11-17T13:30:00+00:00", "prediksi": {"detail": []}}
    prep = {"berita": [kartu], "pra_satu": {"time": kartu["time"], "poin": ["⚪ x", "Setelah rilis: y"]}}
    _keterkaitan.attach(prep, [], toko)
    b = kartu["keterkaitan"]
    assert b["teks"].startswith("2 berita terkait condong emas TURUN") and len(b["baris"]) == 2
    assert "CPI 10 Nov DI ATAS perkiraan (0,5% vs 0,3%) → Retail Sales cenderung DI ATAS" in b["baris"][0]
    assert kartu["prediksi"]["detail"][-1]["judul"].startswith("🔗") and prep["pra_satu"]["poin"][1].startswith("🔗 CPI")
    _keterkaitan.attach(prep, [], toko)                                      # tidak dobel
    assert sum(str(x).startswith("🔗") for x in prep["pra_satu"]["poin"]) == 1
    # memori basi (> 35 hari sebelum rilis) tidak dipakai
    assert _keterkaitan.baris({"title": "Retail Sales m/m", "time": "2027-01-20T13:30:00+00:00"}, mem) is None


def test_rekam_mengisi_memori_keterkaitan():
    now = datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc)
    rows = [{"title": "Retail Sales m/m", "country": "USD", "date": "2026-10-15T08:30:00-04:00", "impact": "High",
             "forecast": "0.3%", "previous": "1.2%"}]
    toko = Toko(aktual={"found": {"Retail Sales m/m|2026-10-15T12:30:00+00:00": {
        "actual": "0.8%", "src": "FRED", "t": now.isoformat()}}})
    assert _rekam.jalankan(toko, now, {}, lambda: rows)["status"] == "ok"
    assert toko["hasil_rilis"]["mem"]["Retail Sales m/m"]["s"] == 1
    assert _rekam.jalankan(toko, now + timedelta(days=6), {}, lambda: rows)["status"] == "tidak ada rilis"


def test_keterkaitan_emas_acak_tanpa_arah(monkeypatch):
    """Angka berkaitan tetapi emas tidak ikut (PPI → GDP: emas searah hanya 35%) → tidak menampilkan arah emas."""
    monkeypatch.setitem(_keterkaitan.DATA, "tampil", {"Advance GDP q/q": [
        {"A": "PPI m/m", "hubungan": "searah", "angka_wf": 58.8, "n_angka_wf": 34, "emas_wf": 35.3, "status_emas": "≈ acak"}]})
    mem = {"PPI m/m": {"s": 1, "act": "1.3%", "f": "0.6%", "time": "2026-10-15T12:30:00+00:00"}}
    b = _keterkaitan.baris({"title": "Advance GDP q/q", "time": "2026-10-29T12:30:00+00:00"}, mem)
    assert "arah emas tidak ikut (≈ 50:50)" in b["baris"][0] and "TURUN" not in b["baris"][0]
    assert b["teks"] == "berita terkait tidak memberi arah"


def test_kurva_searah_lawan_tebakan_untuk_live():
    """⚡ 4.44: gerak detik 1/2 searah tebakan sebelum rilis → kurva searah (semua berita detik 1 ≥ $0,30: ±83%), berlawanan
    → kurva berlawanan (±53% ≈ lempar koin). research/live_kurva.py → live_kurva.json searah/lawan."""
    s = _pra_aset.satu({"title": "PPI m/m", "nama": "PPI", "time": "2026-11-13T13:30:00+00:00", "arah": "turun",
                        "persen": 58, "status": "belum terbukti", "sisa": "1 hari lagi"})
    lj = s["lanjut"]
    assert lj["kurva_searah"]["2|0.5"]["min"] >= 80 and lj["kurva_searah"]["2|0.5"]["n"] >= 10
    assert lj["kurva_lawan"]["1|0.3"]["min"] < 60                       # berlawanan di detik 1 ≈ lempar koin
    assert all(x["n"] >= 10 for k in ("kurva_searah", "kurva_lawan") for x in lj[k].values())
    tanpa = _pra_aset.satu({"title": "Federal Funds Rate", "nama": "Fed", "time": "2026-10-28T18:00:00+00:00",
                            "arah": None, "sisa": "13 hari lagi"})
    assert "kurva_searah" not in tanpa.get("lanjut", {})                # tanpa tebakan → kurva biasa saja


def test_keterkaitan_menunggu_rilis_sumber_berikutnya(monkeypatch):
    """PPI 13 Nov dikaitkan dengan CPI 10 Nov (terbit 3 hari sebelumnya), bukan CPI 14 Okt yang lama."""
    monkeypatch.setitem(_keterkaitan.DATA, "tampil", {"PPI m/m": [
        {"A": "CPI m/m", "hubungan": "searah", "angka_wf": 70.7, "n_angka_wf": 41, "emas_wf": 56.6, "status_emas": "lemah"}]})
    toko = Toko()
    _keterkaitan.ingat([{"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00", "actual": "0.7%", "forecast": "0.6%"}], toko)
    prep = {"berita": [], "mendatang": [{"title": "CPI m/m", "time": "2026-11-10T13:30:00+00:00"},
                                        {"title": "PPI m/m", "time": "2026-11-13T13:30:00+00:00"}]}
    _keterkaitan.attach(prep, [], toko)
    assert "keterkaitan" not in prep["mendatang"][1]


def test_kurva_searah_tidak_untuk_arah_tren_saja():
    s = _pra_aset.satu({"title": "Retail Sales m/m", "nama": "Retail Sales", "time": "2026-11-17T13:30:00+00:00",
                        "arah": "naik", "persen": 56, "status": "lemah", "sisa": "1 jam lagi",
                        "dasar": "Tren emas 4 jam (berita tanpa petunjuk)"})
    assert "kurva_searah" not in s.get("lanjut", {}) and "kurva" in s.get("lanjut", {})
