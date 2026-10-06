"""📊 Peluang emas sebelum NFP/JOLTS/Fed (cloud/api/_prarilis.py)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _prarilis  # noqa: E402

NOW = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row="main"):
        return self.rows.get(row, {})

    def save_state(self, data, row="main"):
        self.rows[row] = data


def bars(n=600, up=True):
    t0 = NOW - timedelta(hours=n)
    return [_core.Bar(t0 + timedelta(hours=i), 4000 + i * (0.1 if up else -0.1), 4001 + i * (0.1 if up else -0.1),
                      3999 + i * (0.1 if up else -0.1), 4000.5 + i * (0.1 if up else -0.1)) for i in range(n)
            if (t0 + timedelta(hours=i)).weekday() < 5]


def test_num():
    assert _prarilis.num("29K") == 29000 and _prarilis.num("4.25%") == 4.25 and _prarilis.num("7.23M") == 7.23e6
    assert _prarilis.num("") is None


def test_attach_nfp_jolts_fed_dan_ingat_kejutan():
    store = Store()
    pers = {"berita": [
        {"title": "Non-Farm Employment Change", "released": False, "forecast": "60K", "previous": "29K"},
        {"title": "JOLTS Job Openings", "released": False, "forecast": "7.1M", "previous": "7.2M"},
        {"title": "Federal Funds Rate", "released": False, "forecast": "4.50%", "previous": "4.25%"},
        {"title": "CPI m/m", "released": False}]}
    cal = [{"title": "JOLTS Job Openings", "actual": "7.5M", "forecast": "7.0M", "time": "2026-10-07T14:00:00+00:00"}]
    _prarilis.attach(pers, cal, store, NOW, lambda: bars())
    got = {c["title"]: c.get("prarilis") for c in pers["berita"]}
    assert got["CPI m/m"] is None
    for t in ("Non-Farm Employment Change", "JOLTS Job Openings", "Federal Funds Rate"):
        p = got[t]
        assert 0 <= p["naik"] <= 100 and p["arah"] in ("NAIK", "TURUN") and "teruji" in p["bukti"]
    mem = store.rows["prarilis"]["mem"]
    assert mem["JOLTS Job Openings"]["s"] == 1 and mem["Non-Farm Employment Change"]["s"] == -1
    assert "gold" in store.rows["prarilis"]


def test_emas_gagal_tetap_ada_peluang():
    pers = {"berita": [{"title": "Non-Farm Employment Change", "released": False, "forecast": "", "previous": ""}]}

    def boom():
        raise RuntimeError("x")
    _prarilis.attach(pers, [], Store(), NOW, boom)
    assert 0 <= pers["berita"][0]["prarilis"]["naik"] <= 100
