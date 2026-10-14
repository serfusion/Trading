"""⛽ PPI-WTI (cloud/api/_ppi_wti.py) — tanpa jaringan."""
import io
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _ppi_wti  # noqa: E402
import _pra_aset  # noqa: E402

NOW = datetime(2026, 10, 14, 14, 0, tzinfo=timezone.utc)          # CPI sudah lewat → berikutnya PPI
T0 = "2026-10-15T12:30:00+00:00"


def deret(agu: float, sep: float) -> list[tuple[date, float]]:
    out, d = [], date(2026, 7, 20)
    while d <= date(2026, 10, 10):
        if d.weekday() < 5:
            out.append((d, agu if d < date(2026, 9, 1) else sep))
        d += timedelta(days=1)
    return out


class Toko:
    def __init__(self):
        self.d = {}

    def get_state(self, row):
        return self.d.get(row, {})

    def save_state(self, data, row):
        self.d[row] = data


def kartu():
    return {"mendatang": [{"title": "PPI m/m", "time": T0, "when": "Kam 19:30 WIB"},
                          {"title": "Retail Sales m/m", "time": T0}], "berita": []}


def test_minyak_naik_tebak_turun():
    # 14 Okt: angka AUDIT per arah — tebakan TURUN (minyak naik) hanya 55% → ⚠️ lemah, kurva per detik lama tidak dipakai
    g = _ppi_wti.tebak(datetime.fromisoformat(T0), deret(80.0, 90.0))
    pa = _ppi_wti.DATA["cpi_ppi"]["per_arah"]["turun"]
    assert g["arah"] == "turun" and g["status"] == "lemah" and g["teks_sampai"] == "lonjakan menit 1"
    assert g["persen"] == round(pa["semua"]["persen"]) and g["n"] == pa["semua"]["n"] and g["minyak"]["ubah"] == 12.5
    assert "DI ATAS" in g["bukti"] and "TURUN saja" in g["bukti"] and g["per_detik"] == {} and "55%" in g["peringatan"]
    n = _ppi_wti.tebak(datetime.fromisoformat(T0), deret(90.0, 80.0))
    assert n["status"] == "tutup kertas" and n["persen"] == round(_ppi_wti.DATA["cpi_ppi"]["per_arah"]["naik"]["semua"]["persen"])


def test_minyak_turun_tebak_naik_dan_kecil_tidak_menebak():
    assert _ppi_wti.tebak(datetime.fromisoformat(T0), deret(90.0, 80.0))["arah"] == "naik"
    assert _ppi_wti.tebak(datetime.fromisoformat(T0), deret(80.0, 82.0)) is None           # +2,5% < 5%
    assert _ppi_wti.tebak(datetime.fromisoformat(T0), deret(80.0, 90.0)[:20]) is None      # data Sep tidak ada


def test_attach_fred_cache_dan_tampil_di_aplikasi():
    obs = [{"date": d.isoformat(), "value": f"{v:.2f}"} for d, v in deret(80.0, 90.0)]
    dipanggil = []

    def opener(req, timeout=None):
        dipanggil.append(req.full_url)
        return io.BytesIO(json.dumps({"observations": obs}).encode())
    prep, toko = kartu(), Toko()
    _ppi_wti.attach(prep, toko, NOW, opener, env={"FRED_API_KEY": "k"})
    g = prep["mendatang"][0]["ppi_wti"]
    assert g["arah"] == "turun" and toko.d["ppi_wti"]["src"] == "FRED" and len(dipanggil) == 1
    _ppi_wti.attach(kartu(), toko, NOW + timedelta(hours=1), opener, env={"FRED_API_KEY": "k"})
    assert len(dipanggil) == 1                                                             # dari cache
    assert "ppi_wti" not in prep["mendatang"][1]                                           # Retail tidak disentuh
    _pra_aset.attach(prep, NOW, None)
    s = prep["pra_satu"]
    assert s["teks"].startswith(f"PPI ▼ TURUN {g['persen']}% (lonjakan menit 1)") and "⚠️" in s["teks"]
    assert "minyak WTI" in s["bukti"] and "Lemah karena tebakan TURUN" in s["bukti"]
    assert "allin" not in s                                    # tebakan lemah → tanpa 💥 modal kecil PPI
    assert "⚠️ Lemah: 55% dari 51 rilis • sejak 2021 59%" in s["bukti"]    # 14 Okt: uji sebelum rilis, per arah


def test_cadangan_uso_bila_fred_gagal(monkeypatch):
    import _perang
    monkeypatch.setattr(_perang, "fred_rows", lambda days=100: (_ for _ in ()).throw(RuntimeError("x")))
    vals = [{"datetime": d.isoformat(), "close": str(v)} for d, v in deret(70.0, 77.0)]

    def opener(req, timeout=None):
        if "stlouisfed" in req.full_url:
            raise OSError("fred mati")
        return io.BytesIO(json.dumps({"values": vals}).encode())
    obs, src = _ppi_wti.minyak(Toko(), NOW, opener, env={"FRED_API_KEY": "k", "TWELVEDATA_API_KEY": "t"})
    assert src == "USO" and len(obs) > 40
    g = _ppi_wti.tebak(datetime.fromisoformat(T0), obs, src)
    assert g["arah"] == "turun" and "USO (cadangan)" in g["bukti"]


def test_env_mati(monkeypatch):
    monkeypatch.setenv("PPI_WTI", "0")
    prep = kartu()
    _ppi_wti.attach(prep, Toko(), NOW, lambda *a, **k: None, env={})
    assert "ppi_wti" not in prep["mendatang"][0]


def cpi_kartu(actual, forecast="0.2%"):
    return {"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00", "released": True, "actual": actual,
            "forecast": forecast}


def test_setelah_cpi_inti_tebakan_ppi_diperbarui_otomatis():
    # 13 Okt (izin "Pasang! … otomatis jika sudah keluar"): minyak naik → tebakan TURUN; CPI inti kemarin menentukan persen
    cp = _ppi_wti.DATA["cpi_ppi"]
    t0 = datetime.fromisoformat(T0)
    g = _ppi_wti.tebak(t0, deret(80.0, 90.0))
    for act, rel in (("0.3%", "sepakat"), ("0.2%", "sesuai"), ("0.1%", "berlawanan")):
        prep = {"berita": [cpi_kartu(act)]}
        h = _ppi_wti.pakai_cpi(g, _ppi_wti.cpi_inti(prep, t0))
        assert h["cpi_inti"]["hubungan"] == rel and h["persen"] == round(cp[rel]["semua"]) and h["arah"] == "turun"
        assert h["bukti"].startswith("🔗 CPI inti") and (h["status"] == "lemah") == (rel == "berlawanan")
        assert ("peringatan" in h) == (rel == "berlawanan")
    assert _ppi_wti.cpi_inti({"berita": [{**cpi_kartu("0.3%"), "released": False}]}, t0) is None
    assert _ppi_wti.cpi_inti({"berita": [cpi_kartu("")]}, t0) is None


def test_setelah_cpi_env_mati(monkeypatch):
    monkeypatch.setenv("PPI_CPI", "0")
    t0 = datetime.fromisoformat(T0)
    g = _ppi_wti.tebak(t0, deret(80.0, 90.0))
    assert _ppi_wti.pakai_cpi(g, _ppi_wti.cpi_inti({"berita": [cpi_kartu("0.1%")]}, t0)) is g


def test_isi_act_kartu_dari_kalender_lalu_ppi_ikut_cpi_14okt():
    """14 Okt: kartu dibuat sebelum Act diisi → PPI tidak pernah diperbarui oleh CPI. chat.isi_act menyalin Act kalender."""
    import chat
    prep = {"berita": [{"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00", "forecast": "0.2%",
                        "released": True}], "mendatang": []}
    cal = [{"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00", "actual": "0.3%", "actual_src": "FRED"},
           {"title": "PPI m/m", "time": T0}]
    chat.isi_act(prep, cal)
    assert prep["berita"][0]["actual"] == "0.3%" and prep["berita"][0]["actual_src"] == "FRED"
    ci = _ppi_wti.cpi_inti(prep, datetime.fromisoformat(T0))
    assert ci and ci["s"] == 1
    g = _ppi_wti.pakai_cpi({"arah": "turun", "persen": 55, "status": "lemah", "bukti": "x", "peringatan": "p"}, ci)
    assert g["status"] == "tutup kertas" and g["cpi_inti"]["hubungan"] == "sepakat" and "peringatan" not in g
    row = {"title": "PPI m/m", "nama": "PPI", "sisa": "1 hari lagi", **g}
    s = _pra_aset.satu(row)
    assert s["teks"].startswith(f"PPI ▼ TURUN {g['persen']}%") and "⚖️" not in s["teks"]
    assert s["poin"][0].startswith("✅ Teruji sebelum rilis: 74% dari 19 rilis")


def test_cpi_inti_tetap_terbaca_setelah_kartu_cpi_hilang_15okt():
    """Bug 15 Okt: kartu CPI hilang 6 jam setelah rilis → PPI kembali 55%. Kini dari kalender & simpanan Supabase."""
    import _ppi_wti as P
    from datetime import datetime, timezone

    class Toko(dict):
        def get_state(self, r):
            return self.get(r, {})

        def save_state(self, d, r):
            self[r] = d
    t0 = datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc)
    kal = [{"title": "Core CPI m/m", "time": "2026-10-14T12:30:00+00:00", "actual": "0.3%", "forecast": "0.2%"}]
    toko = Toko()
    ci = P.cpi_inti({"berita": []}, t0, kal, toko)
    assert ci["s"] == 1 and toko["ppi_cpi"]["time"] == "2026-10-14T12:30:00+00:00"
    assert P.cpi_inti({"berita": []}, t0, [], toko)["actual"] == 0.3          # kalender pun hilang → simpanan
    assert P.cpi_inti({}, datetime(2026, 11, 13, 13, 30, tzinfo=timezone.utc), [], toko) is None   # basi > 4 hari
