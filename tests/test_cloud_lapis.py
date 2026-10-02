"""Sinyal berlapis (cfg["layer"]) & tanda 📰 sinyal setelah berita di _core.tick / _berita_sinyal. Tanpa jaringan."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from helpers import bars_from_path
from test_cloud import ONE_SET, run_ticks

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _berita_sinyal  # noqa: E402
import _core  # noqa: E402

TP1_MODE = {**ONE_SET, "layer": {"mode": "tp1", "max": 10, "lot": 0.5,
                                 "stats": {"teks": "Riwayat lapisan: WR 51% • +0,28R/lapisan"}}}


def trend_df():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    rise = list(np.linspace(flat[-1] + 4, flat[-1] + 160, 40))
    drop = list(np.linspace(rise[-1], rise[-1] - 120, 8))
    return bars_from_path(flat + rise + drop + [drop[-1]] * 10, start="2026-09-14 00:00", freq="1h", wick=0.5)


def test_tanpa_setelan_lapisan_satu_sinyal_per_set():
    _, pub = run_ticks(trend_df(), cfg=ONE_SET)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert len(sig) == 1 and not sig[0].get("lapis")


def test_lapisan_setelah_tp1_lot_setengah_dan_tutup_bersama():
    store, pub = run_ticks(trend_df(), cfg=TP1_MODE)
    sig = [e for e in pub.events if e["type"] == "signal"]
    base, layers = sig[0], sig[1:]
    assert layers and all(e["lapis"] and e["lot_mult"] == 0.5 and e["id"].endswith("L") for e in layers)
    assert not base.get("lapis") and "lapis_stats" in layers[0]
    # lapisan hanya dibuka setelah sinyal TERAKHIR di set itu kena TP1
    tp1_ids = {e["id"] for e in pub.events if e["type"] == "info" and e.get("kind") == "tp1"}
    for prev, nxt in zip(sig, sig[1:]):
        assert prev["id"] in tp1_ids or any(c["id"] == prev["id"] for c in pub.events if c["type"] == "close")
        assert nxt["time"] > prev["time"]
    # heartbeat memuat level TUTUP untuk lapisan juga (aplikasi tidak menganggapnya sudah tutup)
    hb_ids = {x["id"] for e in pub.events if e["type"] == "heartbeat" for x in e.get("exits", [])}
    assert {e["id"] for e in layers} & hb_ids
    # TUTUP berlaku untuk semua sinyal di set itu
    cls = [e for e in pub.events if e["type"] == "close"]
    assert {e["id"] for e in sig} == {e["id"] for e in cls}
    assert any(c.get("lapis") for c in cls) and not store.state["systems"]["T55/20"].get("layers")


def pullback_df():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    up1 = list(np.linspace(flat[-1] + 4, flat[-1] + 60, 20))
    back = list(np.linspace(up1[-1], up1[-1] - 12, 5))
    up2 = list(np.linspace(back[-1], back[-1] + 80, 20))
    drop = list(np.linspace(up2[-1], up2[-1] - 120, 8))
    return bars_from_path(flat + up1 + back + up2 + drop + [drop[-1]] * 10, start="2026-09-14 00:00", freq="1h",
                          wick=0.5)


def test_lapisan_mode_any_maks_2_hanya_breakout_baru():
    cfg = {**ONE_SET, "layer": {"mode": "any", "max": 2, "lot": 0.5}}
    _, pub = run_ticks(pullback_df(), cfg=cfg)
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert len(sig) == 2 and sig[1]["lapis"]                # breakout baru setelah koreksi -> 1 lapisan
    _, pub_tp1 = run_ticks(trend_df(), cfg=cfg)
    assert len([e for e in pub_tp1.events if e["type"] == "signal"]) == 1   # tren tanpa koreksi: tidak ada breakout baru
    ev = [e for e in pub.events if e["type"] in ("signal", "close")]
    open_ids, peak = set(), 0
    for e in ev:
        if e["type"] == "signal":
            open_ids.add(e["id"])
        else:
            open_ids.discard(e["id"])
        peak = max(peak, len(open_ids))
    assert peak <= 2


NOW = datetime(2026, 10, 2, 14, 30, tzinfo=timezone.utc)
ROWS = [{"country": "USD", "impact": "High", "title": "Non-Farm Employment Change",
         "date": "2026-10-02T08:30:00-04:00", "forecast": "89K"},
        {"country": "USD", "impact": "High", "title": "Unemployment Rate", "date": "2026-10-02T08:30:00-04:00",
         "forecast": "4.3%"},
        {"country": "USD", "impact": "Low", "title": "CPI m/m", "date": "2026-10-02T13:30:00-04:00"}]


def test_tanda_berita_dan_searah_kejutan():
    acts = {"Non-Farm Employment Change|2026-10-02T12:30:00+00:00": "45K"}     # NFP lemah -> emas naik
    t = _berita_sinyal.tag("BTC", "BUY", NOW, ROWS, acts)
    assert t["judul"].startswith("📰 SINYAL SETELAH BERITA: NFP 19:30 WIB (2 jam 0 mnt lalu)")
    assert t["searah"] is True and "Searah kejutan NFP" in t["teks"] and "WR" in t["teks"]
    assert _berita_sinyal.tag("BTC", "SELL", NOW, ROWS, acts)["searah"] is False
    assert _berita_sinyal.tag("XAU", "BUY", NOW, ROWS, {})["searah"] is None            # Act belum ada
    assert _berita_sinyal.tag("XAU", "BUY", NOW + timedelta(hours=3), ROWS, acts) is None  # > 4 jam
    assert _berita_sinyal.tag("XAU", "BUY", NOW - timedelta(hours=3), ROWS, acts) is None  # sebelum rilis


def test_sinyal_tick_memuat_tanda_berita():
    calls = []

    def fn(direction, now):
        calls.append(direction)
        return {"judul": "📰 SINYAL SETELAH BERITA: NFP", "teks": "riwayat", "berita": "NFP"}
    _, pub = run_ticks(trend_df(), cfg={**ONE_SET, "news_fn": fn})
    sig = [e for e in pub.events if e["type"] == "signal"]
    assert sig[0]["news"]["berita"] == "NFP" and calls == ["BUY"]


def test_setelan_tick_xau_tp1_btc_breakout_baru(monkeypatch):
    import tick
    monkeypatch.delenv("LAYER_SIGNALS", raising=False)
    monkeypatch.setenv("NEWS_TAG", "0")
    x, b = tick.signal_extras("XAU", None), tick.signal_extras("BTC", None)
    assert x["layer"]["mode"] == "tp1" and x["layer"]["lot"] == 0.5 and "news_fn" not in x
    assert b["layer"]["mode"] == "any" and b["layer"]["max"] == 2 and "WR" in b["layer"]["stats"]["teks"]
    monkeypatch.setenv("LAYER_SIGNALS", "0")
    assert "layer" not in tick.signal_extras("XAU", None)
