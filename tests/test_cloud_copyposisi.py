"""👥 Rangkuman posisi copy trader di cloud (cloud/api/_copyposisi.py), tanpa jaringan."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _copyposisi as C  # noqa: E402


def test_bitget_dan_ringkas(monkeypatch):
    def fake(url, body=None, timeout=12):
        if "traderPosition" in url:
            return {"data": [{"symbolDisplayName": "BTCUSDT", "holdSide": 1, "openAvgPrice": "100", "openLevel": 10}]}
        if "ticker" in url:
            return {"data": [{"lastPr": "102"}]}
        return {"data": {"rows": [
            {"symbolDisplayName": "BTCUSDT", "position": 1, "openAvgPrice": "100", "closeAvgPrice": "105",
             "openTime": "1790000000000", "closeTime": "1790036000000", "stopProfitPrice": "106", "stopLossPrice": "-1",
             "openLevel": 10},
            {"symbolDisplayName": "ETHUSDT", "position": 2, "openAvgPrice": "50", "closeAvgPrice": "51",
             "openTime": "1790000000000", "closeTime": "1790007200000", "stopProfitPrice": "-1", "stopLossPrice": "52",
             "openLevel": 5}]}}
    monkeypatch.setattr(C, "_req", fake)
    C._CACHE.clear()
    r = C.copyposisi("Bitget", "u1", now=1.0)
    p = r["posisi"][0]
    assert (p["arah"], p["entry"], p["now"], p["lev"], p["untung"]) == ("BUY", 100.0, 102.0, 10, 20.0)
    h = r["riwayat"]
    assert h[0]["gerak"] == 5.0 and h[0]["tp"] == 106.0 and h[0]["sl"] is None
    assert h[1]["arah"] == "SELL" and h[1]["gerak"] == -2.0 and h[1]["sl"] == 52.0
    assert r["ringkas"].startswith("2 trade terakhir: untung 1/2")
    assert C.copyposisi("Bitget", "u1", now=2.0) is r                   # cache 3 menit


def test_mql5_dan_galat(monkeypatch):
    C._CACHE.clear()
    assert "pelanggan" in C.copyposisi("MQL5 MT5", "1")["catatan"]

    def boom(url, body=None, timeout=12):
        raise OSError("x")
    monkeypatch.setattr(C, "_req", boom)
    r = C.copyposisi("OKX", "z")
    assert r["ok"] is False and "OKX" in r["catatan"]
