"""Act berlapis (cloud/api/_aktual.py): BLS -> FRED API -> FRED CSV, simpan Supabase. Tanpa jaringan."""
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _aktual  # noqa: E402
import _chat  # noqa: E402

NOW = datetime(2026, 10, 2, 12, 31, tzinfo=timezone.utc)
CAL = [{"title": "Non-Farm Employment Change", "time": "2026-10-02T12:30:00+00:00", "released": True, "actual": ""},
       {"title": "Core PCE Price Index m/m", "time": "2026-09-30T12:30:00+00:00", "released": True, "actual": ""},
       {"title": "Unemployment Rate", "time": "2026-10-09T12:30:00+00:00", "released": False, "actual": ""}]
BLS_JSON = {"status": "REQUEST_SUCCEEDED", "Results": {"series": [
    {"seriesID": "CES0000000001", "data": [{"year": "2026", "period": "M09", "value": "159345"},
                                           {"year": "2026", "period": "M08", "value": "159300"}]}]}}
FRED_JSON = {"observations": [{"date": "2026-07-01", "value": "130.133"}, {"date": "2026-08-01", "value": "130.455"},
                              {"date": "2026-09-01", "value": "."}]}


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row):
        return self.rows.get(row, {})

    def save_state(self, data, row):
        self.rows[row] = json.loads(json.dumps(data))


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener(calls, bls_ok=True, fred_ok=True):
    def op(req, timeout=0):
        url = req.full_url
        calls.append(url.split("?")[0])
        if "bls.gov" in url:
            if not bls_ok:
                raise TimeoutError("timed out")
            return Resp(json.dumps(BLS_JSON).encode())
        if "stlouisfed" in url:
            if not fred_ok:
                raise TimeoutError("timed out")
            return Resp(json.dumps(FRED_JSON).encode())
        raise AssertionError(url)
    return op


def cal():
    return [dict(c) for c in CAL]


def test_bls_untuk_nfp_fred_api_untuk_pce_dan_disimpan():
    calls, store = [], Store()
    f = _aktual.Fetcher({"FRED_API_KEY": "kunci"}, {"PAYEMS", "PCEPILFE"}, opener(calls), csv=lambda s: [])
    c = cal()
    out = _aktual.fill(c, store, NOW, {}, f)
    assert c[0]["actual"] == "45K" and c[0]["actual_src"] == "BLS"
    assert c[1]["actual"] == "0.2%" and c[1]["actual_src"] == "FRED"
    assert c[2]["actual"] == "" and "actual_info" not in c[2]                 # belum rilis
    assert out["sumber"]["BLS"] == "ok" and calls.count(_aktual.BLS_V1) == 1   # satu permintaan BLS untuk semua
    # pembukaan berikutnya: dari Supabase, tanpa jaringan sama sekali
    c2, calls2 = cal(), []
    assert _aktual.fill(c2, store, NOW + timedelta(minutes=5), {},
                        _aktual.Fetcher({}, set(), opener(calls2)))["status"] == "lengkap"
    assert c2[0]["actual"] == "45K" and c2[1]["actual"] == "0.2%" and calls2 == []


def test_semua_sumber_gagal_alasan_tanpa_kunci_dan_ditunda():
    calls, store = [], Store()
    env = {"FRED_API_KEY": "rahasia123"}
    f = _aktual.Fetcher(env, {"PAYEMS"}, opener(calls, bls_ok=False, fred_ok=False), csv=lambda s: [])
    c = cal()[:1]
    out = _aktual.fill(c, store, NOW, env, f)
    assert c[0]["actual"] == "" and c[0]["actual_info"].startswith("sumber gagal")
    assert "rahasia123" not in json.dumps([c, out, store.rows])
    assert out["sumber"]["BLS"] == "gagal (timeout)"
    # 10 menit pertama setelah rilis: dicoba lagi paling cepat tiap 30 detik (hemat batas BLS 25/hari)
    c3 = cal()[:1]
    assert _aktual.fill(c3, store, NOW + timedelta(seconds=20), env)["status"] == "ditunda"
    assert c3[0]["actual_info"] == c[0]["actual_info"]


def test_berita_lama_dicoba_ulang_tiap_2_menit():
    store = Store()
    old = [dict(CAL[1])]                                          # Core PCE, rilis 2 hari lalu
    f = _aktual.Fetcher({}, {"PCEPILFE"}, opener([], bls_ok=False, fred_ok=False), csv=lambda s: [])
    _aktual.fill(old, store, NOW, {}, f)
    assert _aktual.fill([dict(CAL[1])], store, NOW + timedelta(minutes=1), {})["status"] == "ditunda"
    calls = []
    f2 = _aktual.Fetcher({}, {"PCEPILFE"}, opener(calls, bls_ok=False, fred_ok=False), csv=lambda s: [])
    assert _aktual.fill([dict(CAL[1])], store, NOW + timedelta(minutes=3), {}, f2)["status"] == "dicek"


def test_jolts_dua_bulan_lalu_dan_adp_dalam_orang():
    assert _chat.ref_date(datetime(2026, 10, 6, 14, tzinfo=timezone.utc), "bulan2") == date(2026, 8, 1)
    assert _chat.ref_date(datetime(2026, 1, 9, 13, tzinfo=timezone.utc), "bulan") == date(2025, 12, 1)
    vals = {"JTSJOL": [(date(2026, 7, 1), 7100.0), (date(2026, 8, 1), 7230.0)],
            "ADPMNUSNERSA": [(date(2026, 8, 1), 133_000_000.0), (date(2026, 9, 1), 133_045_000.0)]}
    t = datetime(2026, 10, 6, 14, tzinfo=timezone.utc)
    assert _chat.fred_actual("JOLTS Job Openings", t, t, lambda s: vals[s]) == "7.23M"
    t2 = datetime(2026, 10, 1, 12, 15, tzinfo=timezone.utc)
    assert _chat.fred_actual("ADP Non-Farm Employment Change", t2, t2, lambda s: vals[s]) == "45K"


def test_act_manual_investing_dan_menimpa_otomatis():
    p = _aktual.parse_manual
    assert p("08:30 USD Nonfarm Payrolls (Sep) 45K 89K 162K") == "45K"
    assert p("Unemployment Rate (Sep)\t4.4%\t4.3%\t4.3%") == "4.4%"
    assert p("Core CPI (MoM) (Sep) 0.2% 0.3% 0.3%") == "0.2%"
    assert p("-12k") == "-12K" and p("Actual: 0,2%") == "0.2%" and p("tidak ada angka") is None
    store, now = Store(), NOW
    assert _aktual.save_manual(store, CAL[0]["title"], CAL[0]["time"], "Nonfarm Payrolls (Sep) 45K 89K", now)["ok"]
    c = cal()
    c[0]["actual"] = "50K"                                       # otomatis -> manual menang
    _aktual.fill(c[:1], store, now, {}, _aktual.Fetcher({}, set(), opener([])))
    assert c[0]["actual"] == "45K" and c[0]["actual_src"] == "manual"
    assert not _aktual.save_manual(store, "x", "y", "abc", now)["ok"]
    _aktual.save_manual(store, CAL[0]["title"], CAL[0]["time"], "", now)
    assert CAL[0]["title"] + "|" + CAL[0]["time"] not in store.rows["aktual"]["found"]


def test_act_manual_salah_direvisi_otomatis_oleh_angka_resmi():
    store = Store()
    _aktual.save_manual(store, CAL[0]["title"], CAL[0]["time"], "54K", NOW)      # salah ketik (resmi 45K)
    c = cal()[:1]
    f = _aktual.Fetcher({}, {"PAYEMS"}, opener([]), csv=lambda s: [])
    _aktual.fill(c, store, NOW, {}, f)
    assert c[0]["actual"] == "45K" and c[0]["actual_src"] == "BLS" and "direvisi otomatis" in c[0]["actual_info"]
    c2 = cal()[:1]                                                                 # pembukaan berikutnya
    _aktual.fill(c2, store, NOW + timedelta(minutes=5), {}, _aktual.Fetcher({}, set(), opener([])))
    assert c2[0]["actual"] == "45K" and "54K → resmi 45K" in c2[0]["actual_info"]
    store2 = Store()
    _aktual.save_manual(store2, CAL[0]["title"], CAL[0]["time"], "45k", NOW)
    c3 = cal()[:1]
    _aktual.fill(c3, store2, NOW, {}, _aktual.Fetcher({}, {"PAYEMS"}, opener([]), csv=lambda s: []))
    assert "cocok" in c3[0]["actual_info"]
