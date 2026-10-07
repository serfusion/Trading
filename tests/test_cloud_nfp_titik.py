"""🔄 Titik balik NFP (cloud/api/_nfp_titik.py), tanpa jaringan."""
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _nfp_titik as N  # noqa: E402
import _prediksi as P  # noqa: E402


def _rows(chgs, revisi_lalu=-20.0):
    """Vintage PAYEMS palsu: level naik sesuai chgs; setiap bulan dirilis tgl 5 bulan berikutnya; bulan sebelum terakhir
    direvisi saat rilis terakhir."""
    rows, lvl, months = [], 150000.0, []
    levels = {}
    m = date(2023, 1, 1)
    for c in chgs:
        lvl += c
        levels[m] = lvl
        months.append(m)
        m = N._madd(m, 1)
    rel = {mm: date(N._madd(mm, 1).year, N._madd(mm, 1).month, 5) for mm in months}
    last = months[-1]
    for mm in months:
        start = rel[mm]
        if mm == N._madd(last, -1):                      # revisi diumumkan saat rilis bulan terakhir
            rows.append({"date": mm.isoformat(), "realtime_start": start.isoformat(),
                         "realtime_end": (rel[last] - timedelta(days=1)).isoformat(), "value": str(levels[mm])})
            rows.append({"date": mm.isoformat(), "realtime_start": rel[last].isoformat(), "realtime_end": "9999-12-31",
                         "value": str(levels[mm] + revisi_lalu)})
        else:
            rows.append({"date": mm.isoformat(), "realtime_start": start.isoformat(), "realtime_end": "9999-12-31",
                         "value": str(levels[mm])})
    return rows


def test_nfp_fitur_vintage_dan_revisi():
    chgs = [150.0] * 27 + [100.0, 29.0]
    f = N.nfp_fitur(_rows(chgs))
    # level bulan lalu direvisi −20K → perubahan bulan terakhir yang diumumkan = 29 + 20 = 49K (seperti BLS)
    assert f["chg"] == 49.0 and f["prev"] == 100.0 and f["d1"] == -51.0 and f["d2"] == -101.0
    assert f["revision"] == -20.0                                  # 100K pertama → 80K setelah revisi
    assert f["z24"] < -1.0


def test_score_dan_ringkas_tanpa_simbol():
    assert N.score(-0.036, 0.0, -0.06) == 1 and N.score(0.05, 0.2, -0.05) == -4 and N.score(-0.05, -0.2, 0.05) == 4
    f = {"bulan": "2026-09-01", "chg": 29.0, "z24": -0.83, "d1": -133.0, "d1_prev": 185.0, "d2": 52.0,
         "revision": -29.0, "n_claims": -0.036, "n_ur_d3": 0.0, "n_jolts3": -0.061, "lead": 1}
    r = N.ringkas(f)
    assert r["teks"].startswith("Peluang NFP berikutnya lebih tinggi dari +29K (Sep 2026): ")
    assert "<" not in r["teks"] + r["kondisi"] + r["pendahulu"] and ">" not in r["teks"] + r["kondisi"]
    assert "pendahulu netral" in r["kondisi"] and "klaim pengangguran 4 mgg −3,6% (membaik)" in r["pendahulu"]
    lemah = dict(f, z24=-1.6, lead=-3)
    assert "deterioration lanjutan" in N.ringkas(lemah)["kondisi"]


def test_kondisi_cache_fred_gagal_dan_bawaan():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)

    class Store:
        def __init__(self, d):
            self.d = d

        def get_state(self, row):
            return self.d.get(row, {})

        def save_state(self, data, row):
            self.d[row] = data
    f = dict(N.CFG["kondisi"], chg=55.0)
    st = Store({"nfp_titik": {"at": (now - timedelta(hours=1)).isoformat(), "f": f}})
    assert "+55K" in N.kondisi(now, st, {})["teks"]                        # cache segar dipakai

    def boom(key, now):
        raise OSError("fred")
    assert N.kondisi(now, None, {"FRED_API_KEY": "x"}, fetch=boom)["teks"] == N.ringkas(N.CFG["kondisi"])["teks"]
    st2 = Store({})
    N.kondisi(now, st2, {"FRED_API_KEY": "x"}, fetch=lambda k, n: dict(N.CFG["kondisi"], chg=12.0))
    assert st2.d["nfp_titik"]["f"]["chg"] == 12.0


def test_prediksi_detail_nfp_dan_fed(monkeypatch):
    monkeypatch.setattr(N, "kondisi", lambda now, store, env: N.ringkas(N.CFG["kondisi"]))
    prep = {"berita": [], "fed": {"label": "🏦 Keputusan Fed 29 Okt", "teks": "95% TETAP", "bukti": "Polymarket"},
            "mendatang": [{"title": "Non-Farm Employment Change"}, {"title": "Federal Funds Rate"}, {"title": "CPI m/m"}]}
    P.attach(prep)
    nfp, fed, cpi = (c["prediksi"] for c in prep["mendatang"])
    assert nfp["teks"].startswith("NFP: peluang emas") and [d["judul"] for d in nfp["detail"]] == \
        ["Dasar angka", "🔄 Titik balik ekonomi (mean reversion)"]
    assert fed["detail"][-1]["teks"] == "95% TETAP" and len(cpi["detail"]) == 1
