"""📊 Peringkat semua sinyal & label (cloud/api/peringkat.json dari research/peringkat.py) + endpoint riwayat."""
import io
import json
import sys
from pathlib import Path

API = Path(__file__).resolve().parent.parent / "cloud" / "api"
sys.path.insert(0, str(API))


def data():
    return json.loads((API / "peringkat.json").read_text(encoding="utf-8"))


def test_struktur_dan_urutan():
    d = data()
    rows = d["daftar"]
    assert rows and d["keterangan"]
    for r in rows:
        assert r["grup"] in ("sinyal", "spot", "info", "filter") and r["label"] and r["status"]
    nomor = [r["peringkat"] for r in rows if "peringkat" in r]
    assert nomor == list(range(1, len(nomor) + 1))              # nomor urut tanpa loncat
    sig = [r for r in rows if r["grup"] == "sinyal"]
    assert [r["avg"] for r in sig] == sorted((r["avg"] for r in sig), reverse=True)   # profit dulu
    assert all(r["satuan"] == "akurasi" for r in rows if r["grup"] == "info" and "Sinyal trader" not in r["label"])
    grup = [r["grup"] for r in rows]
    assert grup == sorted(grup, key=["sinyal", "spot", "info", "filter"].index)       # grup tidak bercampur


def test_memuat_label_utama():
    teks = " ".join(r["label"] for r in data()["daftar"])
    for emo in ("⚡", "🥈", "🥉", "🔁", "🎯", "🌊", "💎", "🔄", "🧪", "⏸️", "XAU", "BTC", "ETH"):
        assert emo in teks, emo


def test_endpoint_riwayat_menyertakan_peringkat(monkeypatch):
    import chat

    out = {}

    class H(chat.handler):
        def __init__(self):
            self.path = "/api/chat?riwayat=1"

        def _authorized(self):                         # kunci chat diperiksa terpisah (test_cloud_chat)
            return True

        def _send(self, code, body):
            out["code"], out["body"] = code, body
    H().do_GET()
    assert out["code"] == 200 and out["body"]["ok"]
    assert out["body"]["riwayat"]["peringkat"]["daftar"] == data()["daftar"]
    assert "XAU" in out["body"]["riwayat"]
