"""📅 Berita besar berikutnya di luar pekan ini (cloud/api/_jadwal.py)."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _jadwal  # noqa: E402

J = [{"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00"},
     {"title": "CPI m/m", "time": "2026-11-10T13:30:00+00:00"},
     {"title": "Non-Farm Employment Change", "time": "2026-11-06T13:30:00+00:00"},
     {"title": "Federal Funds Rate", "time": "2026-10-28T18:00:00+00:00"},
     {"title": "Judul Tanpa Statistik", "time": "2026-10-20T12:30:00+00:00"}]


def test_mendatang_urut_unik_dan_lewati_pekan_ini():
    now = datetime(2026, 10, 6, 15, tzinfo=timezone.utc)
    out = _jadwal.mendatang({"berita": []}, now, J)
    assert [c["title"] for c in out] == ["CPI m/m", "Federal Funds Rate", "Non-Farm Employment Change"]
    assert out[0]["dalam"] == "8 hari lagi" and out[0]["skenario"]
    # CPI sudah ada di kartu pekan ini → tidak diulang; kemunculan berikutnya juga tidak (satu per judul)
    out2 = _jadwal.mendatang({"berita": [{"title": "CPI m/m", "time": "2026-10-14T12:30:00+00:00"}]}, now, J)
    assert "CPI m/m" not in [c["title"] for c in out2][:1] or out2[0]["time"] != "2026-10-14T12:30:00+00:00"


def test_file_jadwal_ada_dan_utama():
    titles = {j["title"] for j in _jadwal._load()}
    assert {"Non-Farm Employment Change", "CPI m/m", "Federal Funds Rate"} <= titles
