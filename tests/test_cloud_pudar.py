"""📉 Peringatan lonjakan memudar (cloud/api/_pudar.py). Tanpa jaringan."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _pudar  # noqa: E402

T0 = datetime(2026, 10, 2, 12, 30, tzinfo=timezone.utc)


def path(points: list[float], start: float = 4181.0) -> list[tuple]:
    """Candle 5 menit mulai T0 (open = start), close = titik berikutnya."""
    out, o = [], start
    for i, c in enumerate(points):
        out.append((T0 + timedelta(minutes=5 * i), o, max(o, c) + 0.5, min(o, c) - 0.5, c))
        o = c
    return out


def test_nfp_2_okt_naik_lalu_dikembalikan_peringatan_balik():
    # naik +$44 dalam 30 menit, lalu dikembalikan sampai sisa ±28% di menit 60 (seperti 2 Okt 2026)
    pts = [4199, 4212, 4220, 4222, 4223, 4224, 4220, 4210, 4200, 4196, 4195, 4193.5, 4190, 4185]
    bars = path(pts)
    m = _pudar.measure(bars, T0, T0 + timedelta(minutes=61), 58.0)
    assert m["mins"] == 60 and m["s"] == 1 and 0.2 < m["keep"] < 0.35
    r = _pudar.row(m, "Non-Farm Employment Change", T0, T0 + timedelta(minutes=61))
    assert r["teks"] == "93% BALIK 🔴" or r["teks"].endswith("% BALIK 🔴")
    assert "ke bawah harga rilis 4.181" in r["label"] and r["kuat"] and "NFP" in r["bukti"]
    assert r["label"].startswith("📉 Emas 19:30 WIB:") and "% lonjakan kembali di menit 60" in r["label"]
    assert "lalu turun lagi" in r["bukti"] and "sisa" not in r["label"]
    # sebelum menit 60: hitung mundur otomatis
    m30 = _pudar.measure(bars[:7], T0, T0 + timedelta(minutes=37), 58.0)
    r30 = _pudar.row(m30, "Non-Farm Employment Change", T0, T0 + timedelta(minutes=37))
    assert r30["teks"] == "23 menit lagi" and r30["label"].startswith("⏳ Lonjakan Emas 19:30 WIB")


def test_lonjakan_kecil_atau_terlalu_awal_tidak_ditampilkan():
    flat = path([4181.5, 4182, 4181.8, 4182.2, 4182, 4181.9, 4182, 4182.1, 4182, 4182, 4182, 4182])
    assert _pudar.measure(flat, T0, T0 + timedelta(minutes=61), 58.0)["kecil"]
    assert _pudar.measure(flat, T0, T0 + timedelta(minutes=10), 58.0) is None


class Store:
    def __init__(self):
        self.rows = {}

    def get_state(self, row):
        return self.rows.get(row, {})

    def save_state(self, data, row):
        self.rows[row] = data


def test_attach_satu_baris_per_waktu_rilis_dan_cache():
    pts = [4199, 4212, 4220, 4222, 4223, 4224, 4220, 4210, 4200, 4196, 4195, 4193.5, 4190, 4185]
    calls = []

    def fetch():
        calls.append(1)
        return [[b[0].isoformat(), *b[1:]] for b in path(pts)], 58.0
    pers = {"berita": [{"title": "Unemployment Rate", "time": T0.isoformat(), "released": True, "skenario": []},
                       {"title": "Non-Farm Employment Change", "time": T0.isoformat(), "released": True,
                        "skenario": [{"label": "x"}]}]}
    store = Store()
    _pudar.attach(pers, store, T0 + timedelta(minutes=70), fetch)
    nfp, ur = pers["berita"][1], pers["berita"][0]
    assert nfp["skenario"][0]["pudar"] and "pudar" not in ur
    _pudar.attach({"berita": [dict(nfp, skenario=[])]}, store, T0 + timedelta(minutes=71), fetch)
    assert len(calls) == 1                                  # cache 2 menit


def test_btc_memakai_statistik_btc_dan_ambang_persen():
    assert _pudar.STATS.get("btc", {}).get("60")
    base = 86616.0
    pts = [base * (1 + x) for x in (0.002, 0.004, 0.006, 0.007, 0.0072, 0.0074, 0.006, 0.004, 0.003, 0.002, 0.0015,
                                     0.0015, 0.001)]
    bars = path(pts, base)
    m = _pudar.measure(bars, T0, T0 + timedelta(minutes=61), None, 0.0015)
    r = _pudar.row(m, "Non-Farm Employment Change", T0, T0 + timedelta(minutes=61), "BTC")
    assert r["label"].startswith("📉 BTC 19:30 WIB") and "berita BTC" in r["bukti"] and r["teks"].endswith("BALIK 🔴") and "86.616" in r["label"]
    kecil = path([base * 1.0003] * 13, base)
    assert _pudar.measure(kecil, T0, T0 + timedelta(minutes=61), None, 0.0015)["kecil"]
