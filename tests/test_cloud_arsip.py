"""Arsip berita ke GitHub (cloud/api/_arsip.py): tanpa jaringan (GitHub & Supabase palsu)."""
import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _arsip  # noqa: E402

NOW = datetime(2026, 10, 2, 13, 0, tzinfo=timezone.utc)
ROWS = [
    {"title": "Non-Farm Employment Change", "country": "USD", "date": "2026-10-02T08:30:00-04:00", "impact": "High",
     "forecast": "98K", "previous": "162K"},
    {"title": "Unemployment Rate", "country": "USD", "date": "2026-10-02T08:30:00-04:00", "impact": "High",
     "forecast": "4.3%", "previous": "4.3%"},
    {"title": "German Flash PMI", "country": "EUR", "date": "2026-09-28T03:30:00-04:00", "impact": "Medium",
     "forecast": "", "previous": "49.8"},
    {"title": "rusak", "country": "USD", "date": "bukan tanggal"},
]
CAL = [{"title": "Non-Farm Employment Change", "time": "2026-10-02T12:30:00+00:00", "actual": "45K",
        "actual_src": "FRED"}]


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row):
        return self.rows.get(row, {})

    def save_state(self, data, row):
        self.rows[row] = json.loads(json.dumps(data))


class FakeGH(_arsip.GitHub):
    def __init__(self):
        super().__init__("tok", "serfusion/Trading", "arsip-berita")
        self.files, self.branches, self.calls = {}, {"main"}, []

    def req(self, method, path, body=None):
        self.calls.append((method, path))
        if path.endswith("/branches/arsip-berita"):
            return (200, {}) if "arsip-berita" in self.branches else (404, None)
        if path == "/repos/serfusion/Trading":
            return 200, {"default_branch": "main"}
        if "/git/ref/heads/" in path:
            return 200, {"object": {"sha": "abc"}}
        if path.endswith("/git/refs"):
            self.branches.add(body["ref"].split("/")[-1])
            return 201, {}
        if "/contents/" in path:
            fp = path.split("/contents/")[1].split("?")[0]
            if method == "GET":
                if fp not in self.files:
                    return 404, None
                raw, sha = self.files[fp]
                return 200, {"content": base64.b64encode(raw).decode(), "sha": sha}
            if method == "PUT":
                if fp in self.files and body.get("sha") != self.files[fp][1]:
                    return 409, None
                self.files[fp] = (base64.b64decode(body["content"]), f"sha{len(self.calls)}")
                return 201, {}
        raise AssertionError(path)


def test_records_gabung_act_fred_dan_semua_negara():
    r = _arsip.records(ROWS, CAL)
    assert [x["title"] for x in r] == ["German Flash PMI", "Non-Farm Employment Change", "Unemployment Rate"]
    nfp = r[1]
    assert nfp["time_utc"] == "2026-10-02T12:30:00+00:00" and nfp["actual"] == "45K" and nfp["actual_src"] == "FRED"
    assert "actual" not in r[2] and r[0]["country"] == "EUR"
    assert _arsip.week_path(r) == "data/berita/2026/ff_2026-09-28.json"


def test_merge_tidak_menghapus_act_lama():
    old = _arsip.merge([], _arsip.records(ROWS, CAL), NOW)
    later = NOW + timedelta(hours=1)
    new = _arsip.merge(old, _arsip.records(ROWS, []), later)          # FRED sedang gagal -> Act kosong
    nfp = [x for x in new if x["title"].startswith("Non-Farm")][0]
    assert nfp["actual"] == "45K" and nfp["first_seen"] == NOW.isoformat() and nfp["actual_saved"] == NOW.isoformat()


def test_save_tanpa_token_mati():
    assert _arsip.save(ROWS, CAL, NOW, Store(), {})["status"].startswith("mati")


def test_save_buat_branch_tulis_lalu_hemat_limit():
    store, gh = Store(), FakeGH()
    first = _arsip.save(ROWS, [], NOW, store, {}, gh)
    assert first["status"] == "tersimpan" and "arsip-berita" in gh.branches
    doc = json.loads(gh.files[first["path"]][0])
    assert len(doc["berita"]) == 3 and not any(x.get("actual") for x in doc["berita"])
    n = len(gh.calls)
    assert _arsip.save(ROWS, [], NOW + timedelta(minutes=1), store, {}, gh)["status"] == "tidak berubah"
    assert len(gh.calls) == n                                            # tidak menyentuh GitHub sama sekali
    rows2 = [dict(ROWS[0], forecast="100K")] + ROWS[1:]
    assert _arsip.save(rows2, [], NOW + timedelta(minutes=5), store, {}, gh)["status"].startswith("ditunda")
    # Act baru keluar -> langsung disimpan walau < 15 menit
    out = _arsip.save(rows2, CAL, NOW + timedelta(minutes=6), store, {}, gh)
    assert out["status"] == "tersimpan"
    doc = json.loads(gh.files[out["path"]][0])
    nfp = [x for x in doc["berita"] if x["title"].startswith("Non-Farm")][0]
    assert nfp["actual"] == "45K" and nfp["forecast"] == "100K"
    assert store.rows["arsip"]["n_actual"] == 1


def test_calendar_cache_10_menit_dan_cadangan():
    store, calls = Store(), []

    def fetch():
        calls.append(1)
        return ROWS
    assert _arsip.calendar_cached(store, NOW, fetch) == ROWS
    assert _arsip.calendar_cached(store, NOW + timedelta(minutes=9), fetch) == ROWS and len(calls) == 1
    assert _arsip.calendar_cached(store, NOW + timedelta(minutes=11), fetch) == ROWS and len(calls) == 2
    assert _arsip.calendar_cached(store, NOW + timedelta(minutes=30), lambda: None) == ROWS   # gagal -> cache lama
    assert _arsip.calendar_cached(None, NOW, fetch) == ROWS                                   # tanpa Supabase
