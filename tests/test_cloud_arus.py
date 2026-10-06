"""🌊 Ikut arus (cloud/api/_arus.py): kejadian lonjak/jatuh, sinyal, isi stop order, tutup TP/SL/batas waktu."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _arus  # noqa: E402
import _core  # noqa: E402

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def flat(n=1500, price=100.0, seed=1):
    rng = np.random.default_rng(seed)
    out, p = [], price
    for i in range(n):
        o = p
        p = p + rng.normal(0, 0.1) + 0.002
        out.append(_core.Bar(T0 + timedelta(hours=i), o, max(o, p) + 0.05, min(o, p) - 0.05, p))
    return out


class Mem:
    def __init__(self):
        self.s = {}

    def get_state(self):
        return self.s

    def save_state(self, d):
        self.s = d


class Pub:
    def __init__(self):
        self.ev = []

    def publish(self, ev, *a, **k):
        self.ev.append(ev)


def run(bars, asset, mem, pub, upto):
    for i in range(upto[0], upto[1]):
        _arus.arus_tick(bars[i].t + timedelta(minutes=2), {asset: bars[:i + 1]}, mem, pub)


def spike(bars, at, d, size, hold_after=60):
    """Gerakan cepat `size` dalam 3 candle mulai `at`, lalu lanjut searah pelan."""
    p = bars[at - 1].c
    out = bars[:at]
    for j in range(3):
        o, p = p, p + d * size / 3
        out.append(_core.Bar(out[-1].t + timedelta(hours=1), o, max(o, p) + 0.02, min(o, p) - 0.02, p))
    for j in range(hold_after):
        o, p = p, p + d * 0.15
        out.append(_core.Bar(out[-1].t + timedelta(hours=1), o, max(o, p) + 0.02, min(o, p) - 0.02, p))
    return out


def test_btc_lonjak_beri_buy_pasar_lalu_tutup_tp():
    bars = spike(flat(), 1400, +1, 6.0)
    mem, pub = Mem(), Pub()
    run(bars, "BTC", mem, pub, (1390, len(bars)))
    sig = [e for e in pub.ev if e["type"] == "arus_signal"]
    cl = [e for e in pub.ev if e["type"] == "arus_close"]
    assert sig and sig[0]["dir"] == "BUY" and sig[0]["order"] == "pasar"
    assert sig[0]["tp"] > sig[0]["entry"] > sig[0]["sl"]
    assert cl and cl[0]["id"] == sig[0]["id"] and cl[0]["reason"] == "TP" and cl[0]["win"]
    assert len(sig) <= len(cl) + 1                      # tidak ada sinyal baru selama posisi masih terbuka


def test_eth_jatuh_hanya_saat_tren_turun():
    bars = spike(flat(), 1400, -1, 6.0)            # tren naik pelan -> harga masih di atas EMA? cek tidak ada sinyal salah arah
    mem, pub = Mem(), Pub()
    run(bars, "ETH", mem, pub, (1390, len(bars)))
    for e in pub.ev:
        if e["type"] == "arus_signal":
            assert e["dir"] == "SELL"


def test_xau_stop_order_terisi_atau_batal():
    bars = spike(flat(), 1400, +1, 4.0)
    mem, pub = Mem(), Pub()
    run(bars, "XAU", mem, pub, (1390, len(bars)))
    sig = [e for e in pub.ev if e["type"] == "arus_signal"]
    if sig:
        assert sig[0]["order"] == "stop"
        kinds = {e["type"] for e in pub.ev}
        assert "arus_fill" in kinds or "arus_cancel" in kinds


def test_tanpa_gerakan_tidak_ada_sinyal_dan_idempoten():
    bars = flat()
    mem, pub = Mem(), Pub()
    run(bars, "BTC", mem, pub, (1350, 1500))
    _arus.arus_tick(bars[-1].t + timedelta(minutes=5), {"BTC": bars}, mem, pub)
    assert not [e for e in pub.ev if e["type"] == "arus_signal"]
