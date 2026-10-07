"""🎯 Satu baris prediksi per berita (cloud/api/_prediksi.py), tanpa jaringan."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _prediksi as P  # noqa: E402


class Store:
    def __init__(self, d):
        self.d = d

    def get_state(self, row):
        return self.d.get(row, {})


def test_urutan_sumber_dan_format():
    nfp = "Non-Farm Employment Change"
    m = P.untuk({"title": nfp, "prarilis": {"naik": 38, "bukti": "model"}})
    assert m["teks"] == "NFP: peluang emas turun 1 jam 62%" and m["sumber"] == "model" and m["catatan"] == "teruji, belum pasti"
    assert "<" not in m["teks"] and ">" not in m["teks"]
    # setelah rilis model tidak dipakai; rilis lalu di atas perkiraan → aturan teruji 61%
    a = P.untuk({"title": nfp, "released": True, "prarilis": {"naik": 70}}, {nfp: {"s": 1}})
    assert a["teks"] == "NFP: peluang emas naik 1 jam 61%" and a["sumber"] == "aturan" and a["kuat"]
    d = P.untuk({"title": "CPI m/m"})
    assert d["sumber"] == "dasar" and d["teks"].startswith("CPI: peluang emas ") and "1 jam" in d["teks"]
    assert P.untuk({"title": "Berita tak dikenal"}) is None


def test_attach_berita_dan_mendatang():
    prep = {"berita": [{"title": "JOLTS Job Openings", "prarilis": {"naik": 66, "bukti": "x"}}],
            "mendatang": [{"title": "Non-Farm Employment Change"}, {"title": "Federal Funds Rate"}]}
    P.attach(prep, Store({"prarilis": {"mem": {"Non-Farm Employment Change": {"s": 1, "time": "t"}}}}))
    assert prep["berita"][0]["prediksi"]["teks"] == "JOLTS: peluang emas naik 1 jam 66%"
    assert prep["mendatang"][0]["prediksi"]["sumber"] == "aturan"
    assert prep["mendatang"][1]["prediksi"]["teks"].startswith("Fed: peluang emas")


def test_peringkat_kilat():
    prep = {"mendatang": [{"title": "Non-Farm Employment Change"}, {"title": "CPI m/m"}]}
    P.attach(prep, Store({"prarilis": {"mem": {"Non-Farm Employment Change": {"s": 1, "time": "t"}}}}))
    nfp, cpi = (c["prediksi"] for c in prep["mendatang"])
    assert nfp["teks"].startswith("⚡ NFP:") and nfp["peringkat"] == 1
    assert cpi["peringkat"] == 4 and not cpi["teks"].startswith("⚡")
    m = P.untuk({"title": "JOLTS Job Openings", "prarilis": {"naik": 66, "uji": {"lama": 72, "baru": 58}}})
    assert P.peringkat(m, {"prarilis": {"uji": {"lama": 72, "baru": 58}}}) == 2


def test_kandidat_nfp_saat_pendahulu_membaik(monkeypatch):
    import _nfp_titik as N
    monkeypatch.setattr(N, "kondisi", lambda now, store, env: dict(N.ringkas(N.CFG["kondisi"]), lead=2))
    prep = {"mendatang": [{"title": "Non-Farm Employment Change"}]}
    P.attach(prep)
    assert prep["mendatang"][0]["prediksi"]["detail"][-1]["judul"].startswith("🧪 Kandidat")
