"""🎲 sebaran Kalshi sebelum konsensus, 🧭 petunjuk teruji, 🗣️ pernyataan, 🎯 baris pasar CPI — tanpa jaringan."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _kalshi  # noqa: E402
import _pernyataan  # noqa: E402
import _petunjuk  # noqa: E402
import _prediksi  # noqa: E402

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
T0 = "2026-10-14T12:30:00+00:00"


def mk(t, p):
    return {"ticker": f"KXCPI-26SEP-T{t}", "yes_bid_dollars": f"{p:.4f}", "yes_ask_dollars": f"{p:.4f}",
            "last_price_dollars": f"{p:.4f}", "close_time": "2026-10-14T12:25:00Z"}


def test_sebaran_kalshi_mendatang():
    ms = [mk(0.4, 0.915), mk(0.5, 0.585), mk(0.6, 0.19), mk(0.7, 0.015)]
    s = _kalshi.sebaran(ms, 0.1)
    assert s["puncak"] == 0.6 and abs(s["p"] - 0.395) < 1e-6 and s["ge"]["0.6"] == 0.585
    cards = [{"title": "CPI m/m", "time": T0}]
    _kalshi.mendatang(cards, None, NOW, get=lambda series: ms)
    k = cards[0]["kalshi_sebaran"]
    assert k["teks"] == "CPI m/m paling mungkin 0,6% (39%)" and "konsensus" in k["catatan"]


def test_baris_pasar_cpi_dan_peringkat():
    card = {"title": "CPI m/m", "time": T0, "hari_h": {"p_naik": 0.62, "teks": "EMAS 62% naik ⚪", "bukti": "x",
                                                       "geser": {"dari": 0.55, "ke": 0.62, "jam": 6.0}}}
    pr = _prediksi.untuk(card)
    assert pr["sumber"] == "pasar" and pr["teks"] == "CPI: peluang emas naik 1 menit 62%"
    assert _prediksi.peringkat(pr, card) == 2
    prep = {"berita": [card]}
    _prediksi.attach(prep)
    det = prep["berita"][0]["prediksi"]["detail"]
    assert any(d["judul"].startswith("🎲 Pasar prediksi") and "bergeser 55% → 62%" in d["catatan"] for d in det)


def test_petunjuk_sepakat_dan_berbalik():
    mem = {"Core CPI m/m": {"s": 1}, "ISM Services PMI": {"s": 1}}
    core = {"title": "Core CPI m/m", "hari_h": {"pasar": {"atas": 0.365, "bawah": 0.215}}}
    b = _petunjuk.blok(core, mem)
    assert "SEPAKAT" in b["teks"] and b["arah_emas"] == "turun"
    ism = _petunjuk.blok({"title": "ISM Services PMI"}, mem)
    assert "DI BAWAH" in ism["teks"] and "berbalik" in ism["catatan"]
    assert _petunjuk.blok({"title": "Retail Sales m/m"}, mem) is None        # tidak ada aturan teruji


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Trump vows new tariffs on China imports - Reuters</title><link>https://x/1</link>
<pubDate>Sat, 10 Oct 2026 08:00:00 GMT</pubDate></item>
<item><title>Trump says tariffs on China imports coming soon - AP</title><link>https://x/2</link>
<pubDate>Sat, 10 Oct 2026 07:50:00 GMT</pubDate></item>
<item><title>Celebrity news without market topic Trump</title><link>https://x/3</link>
<pubDate>Sat, 10 Oct 2026 07:00:00 GMT</pubDate></item>
<item><title>Old story Fed hike</title><link>https://x/4</link><pubDate>Mon, 05 Oct 2026 07:00:00 GMT</pubDate></item>
</channel></rss>"""
FED = b"""<?xml version="1.0"?><rss><channel><item><title>Waller, The economic outlook</title><link>https://f/1</link>
<pubDate>Thu, 08 Oct 2026 12:30:00 GMT</pubDate></item></channel></rss>"""


def test_pernyataan_saring_dan_cache():
    get = lambda url, *a, **k: FED if "federalreserve" in url else RSS   # noqa: E731
    items, st = _pernyataan.kumpulkan(NOW, get)
    judul = [r["judul"] for r in items]
    assert judul[0].startswith("Trump vows") and len([j for j in judul if "tariff" in j]) == 1   # cerita sama 1x
    assert not any("Celebrity" in j or "Old story" in j for j in judul)
    assert any(j.startswith("Waller") for j in judul)                                          # pidato Fed 3 hari

    class St:
        d = {}

        def get_state(self, row):
            return self.d.get(row, {})

        def save_state(self, data, row):
            self.d[row] = json.loads(json.dumps(data))
    prep, st_ = {}, St()
    _pernyataan.attach(prep, st_, NOW, {}, get)
    assert prep["pernyataan"]["penting"] and "Google News ✓" in prep["pernyataan"]["status"]
    prep2 = {}
    _pernyataan.attach(prep2, st_, NOW, {}, lambda *a, **k: (_ for _ in ()).throw(OSError("x")))   # cache 10 mnt
    assert prep2["pernyataan"]["penting"] == prep["pernyataan"]["penting"]
