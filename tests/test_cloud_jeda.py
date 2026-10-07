"""⏸️ Jeda sinyal XAU ≤ 36 jam sebelum NFP/CPI/Fed (cloud/api/_jeda_berita.py) — tanpa jaringan."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from test_cloud import FakePrices, FakePub, FakeStore, to_bars

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _jeda_berita as jb  # noqa: E402

UTC = timezone.utc
NFP = datetime(2026, 11, 6, 13, 30, tzinfo=UTC)


def test_waktu_gabung_ff_usd_dan_jadwal():
    rows = [{"title": "Non-Farm Employment Change", "country": "USD", "date": "2026-11-06T08:30:00-05:00"},
            {"title": "CPI m/m", "country": "CAD", "date": "2026-11-05T08:30:00-05:00"},      # bukan USD
            {"title": "ISM Manufacturing PMI", "country": "USD", "date": "2026-11-02T10:00:00-05:00"},
            {"title": "Federal Funds Rate", "country": "USD", "date": "rusak"}]
    berita = [{"title": "Non-Farm Employment Change", "time": "2026-11-06T13:30:00+00:00"},   # kembar FF
              {"title": "Core CPI m/m", "time": "2026-11-10T13:30:00+00:00"}]
    assert jb.waktu(rows, berita) == [(NFP, "NFP"), (datetime(2026, 11, 10, 13, 30, tzinfo=UTC), "CPI")]


def test_batas_36_jam_sama_dengan_riset():
    times = [(NFP, "NFP")]
    f = jb.skip_fn(times)
    assert f("BUY", NFP - timedelta(hours=36)) == "jeda 36 jam sebelum NFP Jum 6 Nov 20.30 WIB"
    assert f("SELL", NFP - timedelta(minutes=1)) is not None
    assert f("BUY", NFP - timedelta(hours=36, minutes=1)) is None
    assert f("BUY", NFP) is None                       # rilis sudah keluar → sinyal jalan lagi
    assert f("BUY", NFP + timedelta(hours=1)) is None
    assert jb.skip_fn(times, 6)("BUY", NFP - timedelta(hours=7)) is None
    assert jb.skip_fn([])("BUY", NFP) is None          # tanpa jadwal → tidak ada jeda


def test_label_heartbeat():
    times = [(NFP, "NFP")]
    on = jb.label(NFP - timedelta(hours=3), times)
    assert on["on"] and on["berita"] == "NFP" and on["sampai"] == NFP.isoformat()
    assert on["text"].startswith("⏸️ Sinyal XAU baru dijeda s.d. NFP Jum 6 Nov 20.30 WIB")
    assert jb.label(NFP - timedelta(days=3), times) == {"on": False}


def test_siapkan_kalender_gagal_pakai_jadwal_json(monkeypatch):
    monkeypatch.setattr(jb, "_jadwal", lambda: [{"title": "CPI m/m", "time": "2026-11-10T13:30:00+00:00"}])

    def rusak():
        raise OSError("ForexFactory mati")
    fn, lab = jb.siapkan(rusak, datetime(2026, 11, 9, 13, tzinfo=UTC), {})
    assert lab["on"] and lab["berita"] == "CPI"
    assert fn("BUY", datetime(2026, 11, 9, 13, tzinfo=UTC)).startswith("jeda 36 jam sebelum CPI")
    fn, lab = jb.siapkan(lambda: [], datetime(2026, 11, 9, 13, tzinfo=UTC), {"XAU_NEWS_SKIP_JAM": "12"})
    assert not lab["on"] and fn("BUY", datetime(2026, 11, 9, 13, tzinfo=UTC)) is None


def test_jadwal_json_memuat_fomc_2027_dan_judul_dikenal():
    berita = jb._jadwal()
    assert berita, "cloud/api/jadwal.json kosong"
    fed = [b["time"] for b in berita if b["title"] == "Federal Funds Rate"]
    assert "2027-01-27T19:00:00+00:00" in fed and "2027-12-08T19:00:00+00:00" in fed
    assert {b["title"] for b in berita} & set(jb.NAMA) == set(jb.NAMA)


def test_tick_xau_melewati_sinyal_saat_jeda_dan_heartbeat():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2026-01-05", periods=24 * 110, freq="1h", tz="UTC")
    c = 2000 + np.cumsum(rng.standard_t(4, len(idx)) * 4 + 0.3)
    o = np.r_[c[0], c[:-1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 2, "low": np.minimum(o, c) - 2, "close": c}, index=idx)
    # rilis "besar" tiap 2 hari → jeda menutup ±75% waktu
    times = [(t.to_pydatetime(), "NFP") for t in pd.date_range(idx[0], idx[-1] + pd.Timedelta(days=3), freq="48h")]

    def run(jeda):
        prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
        now = idx[24 * 80].to_pydatetime() + timedelta(minutes=2)
        events = []
        while now <= idx[-1].to_pydatetime():
            prices.now = now
            cfg = {**_core.CFG, "profit_only": False}
            if jeda:
                cfg.update(skip_fn=jb.skip_fn(times), jeda=jb.label(now, times))
            events += _core.tick(now, prices, store, pub, cfg, symbol="XAU/USD")["events"]
            now += timedelta(hours=1)
        return pub.events, events
    base, _ = run(False)
    pub, ev = run(True)
    sig = lambda xs: [e for e in xs if e["type"] == "signal"]  # noqa: E731
    assert len(sig(pub)) < len(sig(base))
    assert any("dilewati: jeda 36 jam sebelum NFP" in e for e in ev)
    for e in sig(pub):                                   # sinyal yang lolos memang di luar jendela 36 jam
        t = datetime.fromisoformat(e["time"])
        assert jb.berikut(t, times) is None
    hb = [e for e in pub if e["type"] == "heartbeat"]
    assert any((e.get("jeda") or {}).get("on") for e in hb)
    assert not any("jeda" in e for e in base if e["type"] == "heartbeat")


def test_sama_dengan_skip_riset_bila_data_ada():
    try:
        from research.muse_uji import jadwal_cloud, skip_berita
        times = jadwal_cloud()
    except Exception as exc:  # noqa: BLE001 - data kalender riset tidak ada di CI
        pytest.skip(f"data riset tidak ada: {exc}")
    f_cloud, f_res = jb.skip_fn(times), skip_berita(36)
    for t in pd.date_range("2019-01-01", "2026-09-30", freq="7h", tz="UTC") + pd.Timedelta(minutes=2):
        assert (f_cloud("BUY", t.to_pydatetime()) is None) == (f_res("BUY", t) is None), t
