"""🎲 Kalshi di kartu 🎯 (cloud/api/_kalshi.py): tanpa jaringan (pasar palsu, Supabase palsu)."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _kalshi  # noqa: E402

NOW = datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)
T0 = "2026-10-14T12:30:00+00:00"
CLOSE = "2026-10-14T12:25:00Z"


def mk(ticker, bid, ask, close=CLOSE):
    return {"ticker": ticker, "yes_bid_dollars": f"{bid:.4f}", "yes_ask_dollars": f"{ask:.4f}",
            "last_price_dollars": f"{bid:.4f}", "close_time": close}


MARKETS = {
    "KXCPI": [mk("KXCPI-26SEP-T0.1", 0.95, 0.97), mk("KXCPI-26SEP-T0.2", 0.70, 0.72), mk("KXCPI-26SEP-T0.3", 0.14, 0.16),
              mk("KXCPI-26OCT-T0.2", 0.5, 0.6, "2026-11-10T13:25:00Z")],          # event bulan lain -> diabaikan
    "KXCPICORE": [mk("KXCPICORE-26SEP-T0.2", 0.80, 0.82), mk("KXCPICORE-26SEP-T0.3", 0.20, 0.22)],
    "KXPAYROLLS": [mk("KXPAYROLLS-26SEP-T100000", 0.46, 0.48, "2026-10-02T12:29:00Z"),
                   mk("KXPAYROLLS-26SEP-T50000", 0.72, 0.74, "2026-10-02T12:29:00Z")],
}
CARDS = [{"title": "CPI m/m", "time": T0, "forecast": "0.3%"}, {"title": "Core CPI m/m", "time": T0, "forecast": "0.3%"},
         {"title": "PPI m/m", "time": T0, "forecast": "0.2%"}]


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row):
        return self.rows.get(row, {})

    def save_state(self, data, row):
        self.rows[row] = json.loads(json.dumps(data))


def fake_get(calls):
    def get(series):
        calls.append(series)
        return MARKETS.get(series, [])
    return get


def test_split_atas_sama_bawah_konsensus():
    s = _kalshi.split(MARKETS["KXCPI"][:3], 0.3, 0.1)
    # di atas 0,3 = 15%; di bawah = 1 - P(> 0,2) = 29%; sama = 56%
    assert abs(s["atas"] - 0.15) < 1e-9 and abs(s["bawah"] - 0.29) < 1e-9 and abs(s["sama"] - 0.56) < 1e-9
    assert _kalshi.split(MARKETS["KXCPI"][:3], 0.9, 0.1) is None             # konsensus di luar strike


def test_nfp_interpolasi_dan_angka_k():
    s = _kalshi.split(MARKETS["KXPAYROLLS"], _kalshi._num("75K"), None)
    assert abs(s["atas"] - 0.60) < 1e-9 and abs(s["bawah"] - 0.40) < 1e-9 and s["sama"] == 0.0


def test_snapshot_hanya_event_rilis_itu_dan_cache_15_menit():
    calls, store = [], Store()
    snap, t = _kalshi.cached_snapshot(CARDS, store, NOW, fake_get(calls))
    assert set(snap) == {f"CPI m/m|{T0}", f"Core CPI m/m|{T0}"} and t == NOW.isoformat()
    assert sorted(calls) == ["KXCPI", "KXCPICORE"]                          # PPI tidak punya seri -> tidak diminta
    _kalshi.cached_snapshot(CARDS, store, NOW + timedelta(minutes=10), fake_get(calls))
    assert len(calls) == 2                                                   # masih dalam cache
    snap2, _ = _kalshi.cached_snapshot(CARDS, store, NOW + timedelta(minutes=20), lambda s: [])
    assert snap2 == snap                                                     # Kalshi gagal -> data lama


def test_info_cpi_peluang_emas_dan_bukti(monkeypatch):
    monkeypatch.setattr(_kalshi, "STATS", {
        "ambang": 0.6, "reaksi_cpi": {"bawah": {"naik": 0.85}, "atas": {"naik": 0.27}, "sama": {"naik": 0.6}},
        "sinyal": {"Exness": {"n": 18, "benar": 72.2, "rata60": 3.28, "tahun": "2023–2025"}}})
    persiapan = {"berita": [dict(c) for c in CARDS]}
    _kalshi.attach(persiapan, Store(), NOW, fake_get([]))
    k = persiapan["berita"][0]["kalshi"]
    # head: 0,29x0,85 + 0,15x0,27 + 0,56x0,6 = 0,623; core: 0,19x0,85 + 0,21x0,27 + 0,60x0,6 = 0,578 -> rata 0,601
    assert k["teks"] == "60% NAIK 🟢" and k["kuat"]
    assert abs(_kalshi.gold_up([{"bawah": 0.29, "atas": 0.15, "sama": 0.56}]) - 0.623) < 1e-9
    assert "di atas perkiraan 15% • sama 56% • di bawah 29%" in k["bukti"] and "belum terbukti" in k["bukti"]
    assert persiapan["berita"][1]["kalshi"]["teks"] == k["teks"]            # headline & core satu kesimpulan
    assert "kalshi" not in persiapan["berita"][2] and persiapan["kalshi_waktu"] == "13:00 WIB"


def test_info_nfp_hanya_peluang_angka(monkeypatch):
    monkeypatch.setattr(_kalshi, "STATS", {"akurasi": {"KXPAYROLLS": {"n": 23, "benar": 56.5, "tahun": "2023–2025"}}})
    card = {"title": "Non-Farm Employment Change", "time": "2026-10-02T12:30:00+00:00", "forecast": "75K"}
    snap = _kalshi.snapshot([card], datetime(2026, 10, 1, tzinfo=timezone.utc), fake_get([]))
    k = _kalshi.info(card, snap)
    assert k["teks"] == "60% DI ATAS ⚪" and "benar 56%" in k["bukti"] and "tidak terbukti" in k["bukti"]
    assert "sama" not in k["bukti"]                                         # NFP kontinu: tidak ada "sama"
