"""📈 Uji maju otomatis prediksi berita (research/validasi_maju.py) & kenaikan kandidat NFP (cloud/api/_prediksi.py)."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from research import validasi_maju as V

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))
import _prediksi as P  # noqa: E402


def test_nilai_prediksi_dari_arsip(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "OUT", tmp_path / "out.json")
    rilis = datetime(2026, 10, 8, 12, 30, tzinfo=timezone.utc)
    (tmp_path / "candle").mkdir()
    rows = ["time_utc,open,high,low,close"]
    for i in range(30):
        t = rilis - timedelta(minutes=60) + timedelta(minutes=5 * i)
        rows.append(f"{t:%Y-%m-%d %H:%M},1,1,1,{4000 + (5 if t >= rilis else 0)}")
    (tmp_path / "candle" / "XAUUSD_5min.csv").write_text("\n".join(rows))
    (tmp_path / "prediksi").mkdir()
    (tmp_path / "prediksi" / "2026-10-05.json").write_text(json.dumps({
        "a": {"title": "Unemployment Claims", "time": rilis.isoformat(), "teks": "Klaim: peluang emas turun 1 jam 52%",
              "naik": 48, "peringkat": 4, "kandidat": False},
        "b": {"title": "X", "time": rilis.isoformat(), "teks": "⚡ X: peluang emas naik 1 jam 61%", "naik": 61,
              "peringkat": 1, "kandidat": True}}))
    o = V.main(tmp_path, now=rilis + timedelta(hours=2))
    assert o["semua"] == {"benar": 1, "n": 2}
    assert o["per_peringkat"]["1"]["benar"] == 1 and o["per_peringkat"]["4"]["benar"] == 0
    assert o["kandidat_nfp"] == {"naik": 1, "n": 1} and o["terakhir"][0]["gerak"] == 5.0


def test_kandidat_naik_ke_perak_bila_lolos(monkeypatch):
    assert P.kandidat_lolos({"kandidat_nfp": {"naik": 5, "n": 10}})[0] is False          # n 20
    assert P.kandidat_lolos({"kandidat_nfp": {"naik": 12, "n": 20}})[0] is True          # 20/30 = 67%
    assert P.kandidat_lolos({"kandidat_nfp": {"naik": 6, "n": 20}})[0] is False          # 14/30 = 47%
    import _nfp_titik as N
    monkeypatch.setattr(N, "kondisi", lambda now, store, env: dict(N.ringkas(N.CFG["kondisi"]), lead=2))
    monkeypatch.setattr(P, "maju", lambda: {"kandidat_nfp": {"naik": 12, "n": 20}, "mulai": "2026-10-07"})
    prep = {"mendatang": [{"title": "Non-Farm Employment Change"}]}
    P.attach(prep)
    pr = prep["mendatang"][0]["prediksi"]
    assert pr["teks"] == "NFP: peluang emas naik 1 jam 66%" and pr["peringkat"] == 2
    assert any(d["judul"].startswith("📈 Uji maju") for d in pr["detail"])
