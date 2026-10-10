"""🛑 BATAL saat guncangan ekstrem (cloud/api/_core.guncangan, _arus, _pulih), tanpa jaringan."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud", "api"))

import _core  # noqa: E402

T0 = datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)


def bars(path):
    """Candle H1 dari daftar close; high/low ±1 di sekitar open/close."""
    out, prev = [], path[0]
    for i, c in enumerate(path):
        out.append(_core.Bar(T0 + timedelta(hours=i), prev, max(prev, c) + 1, min(prev, c) - 1, c))
        prev = c
    return out


def test_guncangan_buy_dan_sell_simetris():
    b = bars([100.0] * 30 + [101, 100, 98, 95, 90])            # ATR ±2 sebelum entry; jatuh 11 dalam 3 jam
    v = {"dir": "BUY", "entry": 100.0, "bar_close": _core.iso(b[30].t)}
    g = _core.guncangan(b, v, 90.0)
    assert g and g["atr_x"] >= 4 and g["dari"] == 102.0
    assert _core.guncangan(b, v, 96.0) is None                  # < 4 ATR: tidak dibatalkan (data: merugikan)
    up = bars([100.0] * 30 + [99, 100, 102, 105, 110])
    s = {"dir": "SELL", "entry": 100.0, "bar_close": _core.iso(up[30].t)}
    assert _core.guncangan(up, s, 110.0) is not None             # SELL dibatalkan saat lonjakan naik (permintaan 10 Okt)
    assert _core.guncangan(up, {**s, "dir": "BUY"}, 110.0) is None


def test_arus_dan_pulih_punya_saklar():
    import _arus
    import _pulih
    assert _arus.GUNCANG == (3.0, 3) and _arus.GUNCANG_ON is True
    assert _pulih.GUNCANG == (0.05, 60) and _pulih.GUNCANG_ON is True


def test_pulih_keranjang_anjlok_ditutup():
    import _pulih

    class Mem:
        def __init__(self, s):
            self.s = s

        def get_state(self):
            return self.s

        def save_state(self, d):
            self.s = d

    class Pub:
        def __init__(self):
            self.ev = []

        def publish(self, ev, *a, **k):
            self.ev.append(ev)
    now = T0 + timedelta(hours=5)
    pos = {"id": "PULIH-1", "entry": {"BTC": 100.0, "ETH": 10.0}, "time": _core.iso(T0),
           "deadline": _core.iso(T0 + timedelta(hours=48))}
    m, p = Mem({"open": dict(pos)}), Pub()
    _pulih.pulih_tick(now, [], m, p, prices=lambda k: {"BTC": 99.0, "ETH": 9.9})    # −1%: tetap
    assert m.s["open"] and not p.ev
    _pulih.pulih_tick(now + timedelta(minutes=10), [], m, p, prices=lambda k: {"BTC": 94.0, "ETH": 9.4})
    ev = [e for e in p.ev if e["type"] == "pulih_close"]
    assert ev and ev[0]["batal"] and ev[0]["reason"].startswith("🛑 BATAL") and m.s["open"] is None
