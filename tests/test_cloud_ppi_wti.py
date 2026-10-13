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
    g = _ppi_wti.tebak(datetime.fromisoformat(T0), deret(80.0, 90.0))
    assert g["arah"] == "turun" and g["status"] == "tutup kertas" and g["teks_sampai"] == "lonjakan menit 1"
    assert g["persen"] == round(_ppi_wti.DATA["lonjakan"]["semua"]["persen"]) and g["minyak"]["ubah"] == 12.5
    assert "DI ATAS" in g["bukti"] and "≈ acak" in g["bukti"] and g["per_detik"]["1"] < 50


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
    assert s["teks"].startswith(f"PPI ▼ TURUN {g['persen']}% (lonjakan menit 1)") and "⚠️" not in s["teks"]
    assert "minyak WTI" in s["bukti"] and s["per_detik"]["1"] == round(_ppi_wti.DATA["per_detik"]["1"])
    a = s["allin"]
    assert not a["kuat"] and "lemah" in a["teks"] and "utamakan CPI" in a["teks"] and "menang" not in a["bukti"]


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
