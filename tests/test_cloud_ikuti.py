"""👥 Follow/unfollow copy trader (cloud/api/_ikuti.py), tanpa jaringan."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _copyposisi as C  # noqa: E402
import _ikuti as I  # noqa: E402


class Store:
    def __init__(self):
        self.d = {}

    def get_state(self, row):
        return self.d.get(row, {})

    def save_state(self, data, row):
        self.d[row] = json.loads(json.dumps(data))


def P(sym, buy, entry, now=None):
    return C._pos(sym, buy, entry, now, lev=10)


def test_atur_follow_unfollow_dan_batas():
    st = Store()
    assert I.atur(st, {"platform": "MQL5 MT5", "id": "1"})["ok"] is False
    assert I.atur(st, {"platform": "Lain", "id": "1"})["ok"] is False
    r = I.atur(st, {"platform": "OKX", "id": "A", "name": "a", "url": "javascript:x", "on": True}, now=0)
    assert r["ok"] and r["list"][0]["url"] == ""
    I.atur(st, {"platform": "OKX", "id": "A", "name": "a2", "on": True})       # follow ulang = tidak dobel
    assert [x["name"] for x in st.d["ikuti"]["list"]] == ["a2"]
    assert I.atur(st, {"platform": "OKX", "id": "A", "on": False})["list"] == []
    for i in range(I.MAX_FOLLOW):
        I.atur(st, {"platform": "Hyperliquid", "id": f"0x{i}", "on": True})
    assert I.atur(st, {"platform": "OKX", "id": "B", "on": True})["ok"] is False


def test_putaran_buka_tutup_dan_kosong_sesaat(monkeypatch):
    st = Store()
    I.atur(st, {"platform": "Bitget", "id": "u1", "name": "Budi", "on": True})
    cur = {"BTC|1": P("BTCUSDT", True, 100.0)}
    fetch = {"Bitget": lambda id_: (dict(cur), "")}
    monkeypatch.setattr(C, "SITUS", {"Bitget": lambda id_: ([], [
        {"symbol": "BTCUSDT", "arah": "BUY", "entry": 100.0, "tutup": 103.0}], "")})
    pubs = []
    r = I.putaran(st, pubs.append, now=1000, fetch=fetch)
    assert r["kejadian"] == 1 and pubs[0]["events"][0]["type"] == "copy_follow"
    assert pubs[0]["events"][0]["posisi"][0]["symbol"] == "BTCUSDT"
    I.putaran(st, pubs.append, now=1015, fetch=fetch)                       # tanpa perubahan = tanpa pesan
    assert len(pubs) == 1
    cur["ETH|2"] = P("ETHUSDT", False, 50.0)
    I.putaran(st, pubs.append, now=1030, fetch=fetch)
    e = pubs[-1]["events"]
    assert [(x["type"], x["symbol"], x["arah"]) for x in e] == [("copy_open", "ETHUSDT", "SELL")]
    assert e[0]["name"] == "Budi" and e[0]["platform"] == "Bitget"
    cur.clear()                                                             # semua hilang: tunggu 1 putaran
    I.putaran(st, pubs.append, now=1045, fetch=fetch)
    assert len(pubs) == 2
    I.putaran(st, pubs.append, now=1060, fetch=fetch)
    e = {x["symbol"]: x for x in pubs[-1]["events"]}
    assert set(e) == {"BTCUSDT", "ETHUSDT"} and all(x["type"] == "copy_close" for x in e.values())
    assert e["BTCUSDT"]["tutup"] == 103.0 and e["BTCUSDT"]["gerak"] == 3.0
    assert e["BTCUSDT"]["tutup_dari"] == "riwayat situs" and e["ETHUSDT"]["tutup_dari"] == "harga terakhir terlihat"
    s = I.status(st, now=1070)
    assert s["umur"] == 10 and s["list"][0]["posisi"] == [] and len(s["log"]) == 4


def test_gagal_baca_tidak_membuat_tutup_palsu():
    st = Store()
    I.atur(st, {"platform": "OKX", "id": "A", "on": True})
    ok = {"OKX": lambda id_: ({"1": P("XRP-USDT", True, 1.5)}, "")}
    I.putaran(st, lambda m: None, now=0, fetch=ok)

    def boom(id_):
        raise OSError("x")
    pubs = []
    I.putaran(st, pubs.append, now=15, fetch={"OKX": boom})
    snap = st.d["ikuti_snap"]["traders"]["OKX|A"]
    assert pubs == [] and snap["gagal"] == 1 and "1" in snap["pos"]
    assert "Gagal membaca OKX" in I.status(st, now=20)["list"][0]["status"]


def test_paket_dan_status_belum_dicek():
    ev = [{"type": "copy_open", "x": "a" * 1500} for _ in range(5)]
    b = I.paket(ev)
    assert len(b) >= 2 and sum(len(x) for x in b) == 5
    assert all(len(json.dumps(x)) < 4096 for x in b)
    assert "pg_cron" in I.status(Store())["pantau"]


def test_okx_mode_net():
    assert C.okx_side({"posSide": "net", "subPos": "11.5"}) is True
    assert C.okx_side({"posSide": "net", "subPos": "-3"}) is False
    assert C.okx_side({"posSide": "short"}) is False
