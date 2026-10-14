"""📝 Rantai hasil berita (15 Okt 2026): rekam tiap jam, memori 'kejutan lalu' harus rilis sebelumnya, Act Nasdaq ISM/Fed."""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _aktual  # noqa: E402
import _petunjuk  # noqa: E402
import _prarilis  # noqa: E402
import _prediksi  # noqa: E402
import _rekam  # noqa: E402

NOW = datetime(2026, 10, 16, 3, 0, tzinfo=timezone.utc)


class Toko(dict):
    def get_state(self, r):
        return self.get(r, {})

    def save_state(self, d, r):
        self[r] = d


def ff(title, date, forecast, previous="0.1%"):
    return {"title": title, "country": "USD", "date": date, "impact": "High", "forecast": forecast, "previous": previous}


def test_segar_hanya_rilis_sebelumnya():
    m = {"s": 1, "time": "2026-09-11T12:30:00+00:00"}
    assert _prarilis.segar(m, "2026-10-14T12:30:00+00:00", "CPI m/m")
    assert not _prarilis.segar(m, "2026-11-10T13:30:00+00:00", "CPI m/m")          # 2 bulan lalu = basi
    assert not _prarilis.segar(m, "2026-09-11T12:30:00+00:00", "CPI m/m")          # bukan sebelum kartu
    assert _prarilis.segar({"s": 1, "time": "2026-09-16T18:00:00+00:00"}, "2026-10-28T18:00:00+00:00",
                           "Federal Funds Rate")                                    # FOMC 6 pekan
    assert not _prarilis.segar(None, "2026-10-28T18:00:00+00:00", "Federal Funds Rate")


def test_petunjuk_dan_prediksi_tidak_memakai_memori_basi():
    kartu = {"title": "Non-Farm Employment Change", "time": "2026-12-04T13:30:00+00:00", "released": False}
    basi = {"Non-Farm Employment Change": {"s": 1, "time": "2026-10-02T12:30:00+00:00"}}
    segar = {"Non-Farm Employment Change": {"s": 1, "time": "2026-11-06T13:30:00+00:00"}}
    assert (_prediksi.untuk(kartu, segar) or {}).get("sumber") == "aturan"
    assert (_prediksi.untuk(kartu, basi) or {}).get("sumber") != "aturan"
    c = {"title": "JOLTS Job Openings", "time": "2026-12-08T15:00:00+00:00", "released": False}
    assert _petunjuk.blok(c, {"JOLTS Job Openings": {"s": 1, "time": "2026-11-03T15:00:00+00:00"}}) is not None
    assert _petunjuk.blok(c, {"JOLTS Job Openings": {"s": 1, "time": "2026-09-30T14:00:00+00:00"}}) is None


def test_rekam_tiap_jam_mengisi_semua_memori_tanpa_aplikasi():
    rows = [ff("Core CPI m/m", "2026-10-14T08:30:00-04:00", "0.2%"), ff("CPI m/m", "2026-10-14T08:30:00-04:00", "0.6%"),
            ff("ISM Services PMI", "2026-10-05T10:00:00-04:00", "55.1", "55.4"),
            ff("PPI m/m", "2026-10-15T08:30:00-04:00", "0.6%", "0.4%")]
    toko = Toko()
    toko["aktual"] = {"found": {"Core CPI m/m|2026-10-14T12:30:00+00:00": {"actual": "0.3%", "src": "BLS",
                                                                           "t": NOW.isoformat()},
                                "CPI m/m|2026-10-14T12:30:00+00:00": {"actual": "0.6%", "src": "BLS", "t": NOW.isoformat()},
                                "PPI m/m|2026-10-15T12:30:00+00:00": {"actual": "0.5%", "src": "BLS", "t": NOW.isoformat()}}}
    r = _rekam.jalankan(toko, NOW, {}, lambda: rows)
    assert r["status"] == "ok" and r["cpi_inti"] == "2026-10-14T12:30:00+00:00"
    assert toko["ppi_cpi"]["s"] == 1                                         # PPI berikutnya tahu CPI inti di atas
    assert toko["petunjuk"]["mem"]["CPI m/m"] == {"s": 0, "time": "2026-10-14T12:30:00+00:00"}
    assert toko["petunjuk"]["mem"]["PPI m/m"]["s"] == -1
    assert _rekam.jalankan(toko, NOW + timedelta(days=6), {}, lambda: rows)["status"] == "tidak ada rilis"
    assert _rekam.jalankan(toko, NOW, {"REKAM_HASIL": "0"}, lambda: rows)["status"] == "mati"


def test_act_nasdaq_untuk_ism_dan_fed():
    dipanggil = []

    def op(req, timeout=None):
        dipanggil.append(req.full_url)
        return io.BytesIO(json.dumps({"data": {"rows": [
            {"country": "United States", "eventName": "ISM Non-Manufacturing PMI", "actual": "54.9", "consensus": "55.1"},
            {"country": "United States", "eventName": "Fed Interest Rate Decision", "actual": "", "consensus": "4.25%"}]}}
        ).encode())
    t = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    assert _aktual.nasdaq_act("ISM Services PMI", t, op) == "54.9" and dipanggil[0].endswith("date=2026-10-06")
    assert _aktual.nasdaq_act("Federal Funds Rate", t, op) is None                     # belum diumumkan
    assert _aktual.nasdaq_act("CPI m/m", t, op) is None
    cal = [{"title": "ISM Services PMI", "time": t.isoformat(), "released": True, "forecast": "55.1", "actual": ""}]
    st = _aktual.fill(cal, Toko(), t + timedelta(minutes=5), {}, nasdaq=lambda ti, tt: _aktual.nasdaq_act(ti, tt, op))
    assert cal[0]["actual"] == "54.9" and cal[0]["actual_src"] == "Nasdaq" and st["sumber"]["Nasdaq"] == "ok"
