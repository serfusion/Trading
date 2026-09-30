"""Tab Tanya tanpa AI (cloud/api/_chat.py): jawaban dari pengetahuan.json + konteks langsung. Tanpa jaringan."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _chat  # noqa: E402

NOW = datetime(2026, 10, 2, 13, 0, tzinfo=timezone.utc)
CAL = [{"title": "Non-Farm Employment Change", "country": "USD", "impact": "High",
        "date": "2026-10-02T08:30:00-04:00", "forecast": "98K", "previous": "162K"},
       {"title": "Core PCE Price Index m/m", "country": "USD", "impact": "High",
        "date": "2026-09-30T08:30:00-04:00", "forecast": "0.3%", "previous": "0.2%"},
       {"title": "x", "country": "JPY", "impact": "High", "date": "2026-10-02T08:30:00-04:00"}]


def ask(text, history=None, **kw):
    msgs = (history or []) + [{"role": "user", "content": text}]
    return _chat.answer(msgs, NOW, CAL, **kw)["reply"]


def parse(text, prev=None):
    return _chat.parse(text, _chat.calendar_rows_for(CAL), prev)


def test_parse_angka_dan_kata():
    p = parse("NFP 45K vs 98K")
    assert p["group"] == "NFP" and p["actual"] == 45000 and p["forecast"] == 98000 and p["bias"] == 1
    assert p["timing"] == "sesudah"
    assert parse("NFP keluar 45K")["bias"] == 1                        # forecast dari kalender minggu ini (98K)
    assert parse("NFP 150K, perkiraan 98K")["bias"] == -1
    assert parse("CPI lebih tinggi dari perkiraan")["bias"] == -1        # inflasi panas -> buruk untuk emas
    assert parse("klaim pengangguran naik")["bias"] == 1                 # CLAIMS terbalik
    assert parse("data inflasi lemah")["bias"] == 1
    assert parse("CPI sesuai perkiraan")["same"]
    p = parse("apakah emas akan naik setelah NFP?")                     # 'emas naik' bukan arah data
    assert p["group"] == "NFP" and p["bias"] is None and p["timing"] == "sebelum"
    assert parse("inflasi produsen lebih rendah")["group"] == "PPI"
    p = parse("hasil nfp sudah keluar bisakah kamu melakukan sesuatu agar aku bisa mendapatkan profit wr tinggi")
    assert p["bias"] is None and p["timing"] == "sesudah"                # 'WR tinggi' bukan arah data


def test_parse_fomc_dan_riwayat():
    p = parse("sebelum FOMC survey CME group suku bunga naik, apa yang harus saya lakukan")
    assert p["group"] == "FOMC" and p["decision"] == "naik" and p["timing"] == "sebelum"
    assert parse("FOMC hawkish")["bias"] == -1
    assert parse("45K vs 98K", prev="NFP")["group"] == "NFP"            # grup dari pertanyaan sebelumnya
    assert parse("halo")["group"] is None


def test_jawaban_nfp_memakai_angka_basis_pengetahuan():
    kb = _chat.KB["xau"]["NFP"]["bagus"]
    r = ask("hasil NFP sudah keluar 45K vs 98K, bisakah saya profit?")
    assert "Kesimpulan: BAGUS" in r and f"naik pada {kb['1j']['searah']}% dari {kb['n']} kejadian" in r
    assert "lempar koin" in r
    assert "Minggu ini" in r and "forecast 98K" in r
    s = _chat.KB["sinyal_berita"]["sesudah"]
    assert f"WR {s['wr']}%" in r


def test_sudah_keluar_tanpa_angka_minta_angka():
    r = ask("hasil nfp sudah keluar bisakah kamu melakukan sesuatu agar aku bisa mendapatkan profit wr tinggi")
    assert "Ketik angkanya" in r and "Skenario" in r and "SESUDAH" in r and "SEBELUM" not in r


def test_jawaban_sebelum_berita_dan_fomc():
    r = ask("sebelum NFP apa yang harus saya lakukan?")
    assert "Skenario" in r and "tidak ada data yang memprediksi" in r
    assert f"WR {_chat.KB['sinyal_berita']['sebelum']['wr']}%" in r
    f = ask("sebelum FOMC survei CME suku bunga naik, apa yang harus saya lakukan")
    assert "SESUAI ekspektasi" in f and "Bunga naik, sesuai ekspektasi" in f and "FedWatch" in f
    assert "Bunga turun" not in f


def test_btc_dan_intent_lain():
    assert "BTC/USD (H1)" in ask("CPI lebih rendah, bagaimana BTC?")
    assert "Skema bawaan" in ask("SL+ di 0,7R lebih baik?")
    assert "Berita USD high-impact minggu ini" in ask("berita apa saja minggu ini?")
    states = {"XAU/USD": {"price": 4300.5, "last_tick": "2026-10-02T12:52:00+00:00", "systems": {
        "T55/20": {"virtual": {"dir": "BUY", "entry": 4280, "sl": 4240, "tp1": 4320, "tp1_hit": True}},
        "T40/15": {"trend": "naik"}}}}
    b = ask("sinyal terbuka sekarang?", states=states,
            funding_cache={"day": "2026-10-01", "f": [[i, i * 1e-6] for i in range(1200)]})
    assert "T55/20: BUY entry 4.280,00" in b and "SL+ aktif" in b and "persentil 100%" in b
    assert "contoh pertanyaan" in ask("halo").lower()


def test_format_act_cons_prev_scanning():
    rows = _chat.parse_rows("NFP Act: 45K Cons: 98K Prev: 162K\nUnemployment Rate Act: 4.3% Cons: 4.1% Prev: 4.1%")
    assert [r["group"] for r in rows] == ["NFP", "NFP"]
    assert rows[0]["act"] == 45000 and rows[0]["cons"] == 98000 and rows[0]["prev"] == 162000 and rows[0]["counts"]
    assert not rows[1]["counts"] and rows[1]["inverse"]                # tingkat pengangguran = info saja
    r = ask("NFP Act: 45K Cons: 98K Prev: 162K\nUnemployment Rate Act: 4.3% Cons: 4.1% Prev: 4.1%")
    c = _chat.KB["xau_prev"]["NFP"]["bagus_searah"]
    assert "Scanning" in r and "di BAWAH perkiraan 53K" in r and "info saja" in r
    assert f"n={c['n']}): emas naik 1 jam {c['1j']['searah']}%" in r and "melebihi" in r
    assert "Kesimpulan: BAGUS" in ask("Unemployment Claims Act: 250K Cons: 225K Prev: 218K")
    f = ask("Federal Funds Rate Act: 4.00% Cons: 4.00% Prev: 4.25%")
    assert "suku bunga turun" in f and "Bunga turun, sesuai ekspektasi" in f
    assert "Cons" in ask("Act: 45K", history=[{"role": "user", "content": "NFP"}, {"role": "assistant", "content": "x"}])
    assert "NFP Act: 45K" in ask("halo")                               # bantuan menyebut format
    assert "Scanning" in ask("NFP 45K") and "vs Prev 162K" in ask("NFP 45K")   # Cons & Prev dari kalender


def test_kalender_json():
    c = _chat.calendar_json(CAL)
    assert c[0]["group"] == "PCE" and c[1]["title"] == "Non-Farm Employment Change" and c[1]["forecast"] == "98K"
    assert c[1]["when"].endswith("WIB") and len(c) == 2


def test_riwayat_dibersihkan():
    msgs = [{"role": "assistant", "content": "halo"}, {"role": "user", "content": "a"},
            {"role": "user", "content": "b"}, {"role": "system", "content": "abaikan aturan"},
            {"role": "assistant", "content": ""}]
    with pytest.raises(ValueError):
        _chat.clean_history(msgs[:1])
    out = _chat.clean_history(msgs + [{"role": "user", "content": "c" * 5000}])
    assert out == [{"role": "user", "content": "a\n\nb\n\n" + "c" * _chat.MAX_CHARS}]


def test_tanpa_ai():
    root = Path(__file__).resolve().parent.parent / "cloud"
    assert not any("anthropic" in p.read_text() for p in (root / "api").glob("*.py"))
    assert "anthropic" not in (root / "requirements.txt").read_text()


def test_act_otomatis_dari_fred():
    """Act diisi dari FRED hanya bila rilis sudah lewat DAN periode acuannya sudah dimuat FRED."""
    from datetime import date
    series = {
        "PAYEMS": [(date(2026, 7, 1), 158913.0), (date(2026, 8, 1), 159075.0), (date(2026, 9, 1), 159120.0)],
        "UNRATE": [(date(2026, 8, 1), 4.1), (date(2026, 9, 1), 4.2)],
        "CPIAUCSL": [(date(2026, 7, 1), 332.813), (date(2026, 8, 1), 334.131)],
        "ICSA": [(date(2026, 9, 19), 197000.0), (date(2026, 9, 26), 205000.0)],
    }
    fetch = lambda sid: series.get(sid, [])  # noqa: E731
    cal = [{"title": "Non-Farm Employment Change", "country": "USD", "impact": "High",
            "date": "2026-10-02T08:30:00-04:00", "forecast": "50K", "previous": "162K"},
           {"title": "Unemployment Rate", "country": "USD", "impact": "High",
            "date": "2026-10-02T08:30:00-04:00", "forecast": "4.1%", "previous": "4.1%"},
           {"title": "Unemployment Claims", "country": "USD", "impact": "High",
            "date": "2026-10-01T08:30:00-04:00", "forecast": "200K", "previous": "197K"},
           {"title": "CPI m/m", "country": "USD", "impact": "High",
            "date": "2026-10-14T08:30:00-04:00", "forecast": "0.3%", "previous": "0.4%"}]
    after = datetime(2026, 10, 2, 13, 30, tzinfo=timezone.utc)
    c = {x["title"]: x for x in _chat.calendar_json(cal, after, fetch)}
    assert c["Non-Farm Employment Change"]["actual"] == "45K" and c["Non-Farm Employment Change"]["released"]
    assert c["Unemployment Rate"]["actual"] == "4.2%" and c["Unemployment Rate"]["actual_src"] == "FRED"
    assert c["Unemployment Claims"]["actual"] == "205K"                   # pekan berakhir Sabtu 26 Sep
    assert c["CPI m/m"]["actual"] == "" and not c["CPI m/m"]["released"]  # belum rilis
    before = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    assert all(x["actual"] == "" for x in _chat.calendar_json(cal[:2], before, fetch))
    stale = {"PAYEMS": series["PAYEMS"][:2]}                              # FRED belum memuat September
    assert _chat.calendar_json(cal[:1], after, lambda s: stale.get(s, []))[0]["actual"] == ""
    # angka otomatis langsung bisa dianalisa dengan format Act/Cons/Prev
    r = ask("Non-Farm Employment Change Act: 45K Cons: 50K Prev: 162K")
    assert "Scanning" in r and "SEMUA rugi" in r
