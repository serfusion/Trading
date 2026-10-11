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
    assert g["persen"] == round(_cpi_detik.DATA["uji"]["semua"]) and "di bawah 35%" in g["bukti"]
    _pra_aset.attach(prep, NOW, None)
    s = prep["pra_satu"]
    assert s["teks"].startswith(f"CPI ▲ NAIK {g['persen']}% (2–10 dtk)") and "⚠️" not in s["teks"]
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


def test_nan_tidak_jadi_tanda():
    assert _cpi_detik.tanda(float("nan"), 0.02) == 0 and _cpi_detik.tanda(0.019, 0.02) == 0
    assert _cpi_detik.tanda(-0.03, 0.02) == -1


def test_env_mati(monkeypatch):
    monkeypatch.setenv("CPI_DETIK", "0")
    prep = kartu()
    _cpi_detik.attach(prep, None, NOW, opener([]), get=lambda s: KALSHI)
    assert "cpi_detik" not in prep["mendatang"][0]
