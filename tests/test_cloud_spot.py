"""💎 Sinyal spot (cloud/api/_spot.py): fitur sama dengan riset, alur BELI → CLOSE TP / batas waktu. Tanpa jaringan."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _spot  # noqa: E402

DAY = timedelta(days=1)
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def daily(n=320, seed=1, start=T0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.005, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.01, n)))
    lo = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.01, n)))
    return [_core.Bar(start + i * DAY, float(o[i]), float(h[i]), float(lo[i]), float(c[i])) for i in range(n)]


def test_fitur_sama_dengan_riset():
    from research.spot_peluang import FEATS, features as rf
    coin, btc = daily(seed=2), daily(seed=3)
    df = pd.DataFrame([(b.t, b.o, b.h, b.l, b.c) for b in coin], columns=["t", "open", "high", "low", "close"]).set_index("t")
    bd = pd.DataFrame([(b.t, b.o, b.h, b.l, b.c) for b in btc], columns=["t", "open", "high", "low", "close"]).set_index("t")
    ref = rf(df, bd)
    for k in (250, 290, 319):
        x = _spot.features(coin[:k + 1], btc[:k + 1])
        want = ref.iloc[k][FEATS].to_numpy(float)
        assert np.allclose(x, want, rtol=1e-6, atol=1e-9), (k, x, want)


def test_model_terpasang_dan_peluang_masuk_akal():
    if not _spot.MODEL:
        pytest.skip("spot_model.json belum dibuat")
    x = _spot.features(daily(seed=4), daily(seed=5))
    p = _spot.prob(x)
    assert 0 < p < 1 and _spot.MODEL["ambang"] >= 0.9 and len(_spot.MODEL["coins"]) >= 10


class Store:
    def __init__(self):
        self.s = {}

    def get_state(self):
        return dict(self.s)

    def save_state(self, d):
        self.s = dict(d)


class Pub:
    def __init__(self):
        self.events = []

    def publish(self, ev, *a, **k):
        self.events.append(ev)


def make_fetch(data):
    def fetch(coin, n, key, budget):
        if coin not in data:
            raise RuntimeError(f"{coin}: tidak ada")
        return data[coin], "uji"
    return fetch


@pytest.fixture
def fake_model(monkeypatch):
    model = {"tp": 0.03, "hari": 10, "ambang": 0.93, "biaya": 0.003, "coins": ["BTC", "ETH"], "fitur": [],
             "teruji": {"baru": {"wr": 92, "avg": 1.2, "kalah": -15}}, "base": 0, "trees": []}
    monkeypatch.setattr(_spot, "MODEL", model)
    monkeypatch.setattr(_spot, "features", lambda bars, btc: [0.0])
    return model


def test_beli_lalu_close_tp(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.95)
    store, pub = Store(), Pub()
    btc, eth = daily(seed=6), daily(seed=7)
    day = btc[-1].t                                   # candle terakhir = hari ini (berjalan)
    now = day + timedelta(minutes=7)
    r = _spot.spot_tick(now, store, pub, fetch=make_fetch({"BTC": btc, "ETH": eth}))
    sig = [e for e in pub.events if e["type"] == "spot_signal"]
    assert r["open"] == 2 and {e["coin"] for e in sig} == {"BTC", "ETH"}
    assert sig[0]["tp"] == pytest.approx(sig[0]["entry"] * 1.03)
    assert any(e["type"] == "spot_status" for e in pub.events)
    # tick berikutnya hari yang sama: tidak ada sinyal ganda
    _spot.spot_tick(now + timedelta(minutes=10), store, pub, fetch=make_fetch({"BTC": btc, "ETH": eth}))
    assert len([e for e in pub.events if e["type"] == "spot_signal"]) == 2
    # BTC: high hari berikutnya menyentuh TP -> CLOSE profit di harga TP
    pos = store.s["open"]["BTC"]
    nxt = _core.Bar(day + DAY, pos["entry"], pos["tp"] * 1.001, pos["entry"] * 0.99, pos["entry"] * 1.01)
    btc2 = btc[:-1] + [_core.Bar(day, btc[-1].o, pos["entry"] * 1.01, btc[-1].l, btc[-1].c), nxt]
    eth2 = eth + [_core.Bar(day + DAY, eth[-1].c, eth[-1].c * 1.005, eth[-1].c * 0.99, eth[-1].c)]
    monkeypatch.setattr(_spot, "prob", lambda x: 0.5)
    _spot.spot_tick(day + DAY + timedelta(hours=3), store, pub, fetch=make_fetch({"BTC": btc2, "ETH": eth2}))
    cl = [e for e in pub.events if e["type"] == "spot_close"]
    assert [e["coin"] for e in cl] == ["BTC"] and cl[0]["win"] and cl[0]["exit"] == pytest.approx(pos["tp"])
    assert cl[0]["r"] == pytest.approx(2.7, abs=0.01)
    assert "BTC" not in store.s["open"] and store.s["closed"][0]["coin"] == "BTC"


def test_close_batas_waktu_dan_maks_posisi(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=8)
    flat = [_core.Bar(b.t, b.o, b.o * 1.001, b.o * 0.999, b.o) for b in btc]     # tidak pernah naik 3%
    day = flat[-1].t
    _spot.spot_tick(day + timedelta(minutes=6), store, pub, max_open=1,
                    fetch=make_fetch({"BTC": flat, "ETH": flat}))
    assert len(store.s["open"]) == 1                      # maks 1 posisi
    entry = store.s["open"]["BTC"]["entry"]
    later = flat + [_core.Bar(day + i * DAY, entry, entry * 1.01, entry * 0.9, entry * 0.95) for i in range(1, 12)]
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)
    _spot.spot_tick(day + 11 * DAY + timedelta(hours=1), store, pub, fetch=make_fetch({"BTC": later, "ETH": later}))
    cl = [e for e in pub.events if e["type"] == "spot_close"]
    assert len(cl) == 1 and not cl[0]["win"] and "hari habis" in cl[0]["reason"]
    assert cl[0]["exit"] == pytest.approx(entry * 0.95)


def test_sebelum_candle_tutup_tidak_memindai(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=9)
    _spot.spot_tick(btc[-1].t + timedelta(minutes=2), store, pub, fetch=make_fetch({"BTC": btc, "ETH": btc}))
    assert not [e for e in pub.events if e["type"] == "spot_signal"]


def test_sumber_gagal_lanjut_ke_cadangan(monkeypatch):
    calls = []

    def bad(coin, n, key):
        calls.append("a")
        raise RuntimeError("451")

    def good(coin, n, key):
        calls.append("b")
        return daily(n=5)
    monkeypatch.setattr(_spot, "SOURCES", (("a", bad), ("b", good)))
    bars, src = _spot.klines("BTC", 5, None, {"td": 0})
    assert src == "b" and calls == ["a", "b"] and len(bars) == 5


def test_aturan_3_merah_memberi_sinyal_walau_peluang_model_rendah(fake_model, monkeypatch):
    fake_model["aturan_merah"] = True
    fake_model["fitur"] = ["red", "r3", "d200"]
    monkeypatch.setattr(_spot, "prob", lambda x: 0.6)
    store, pub = Store(), Pub()
    btc = daily(seed=10)
    monkeypatch.setattr(_spot, "features", lambda bars, b: [3.0, -0.12, 0.05])
    _spot.spot_tick(btc[-1].t + timedelta(minutes=6), store, pub, fetch=make_fetch({"BTC": btc, "ETH": btc}))
    sig = [e for e in pub.events if e["type"] == "spot_signal"]
    assert len(sig) == 2 and sig[0]["alasan"] == "3 merah"
    monkeypatch.setattr(_spot, "features", lambda bars, b: [2.0, -0.12, 0.05])     # hanya 2 merah: tidak
    store2, pub2 = Store(), Pub()
    _spot.spot_tick(btc[-1].t + timedelta(minutes=6), store2, pub2, fetch=make_fetch({"BTC": btc, "ETH": btc}))
    assert not [e for e in pub2.events if e["type"] == "spot_signal"]


def test_vol_rank_sama_dengan_pandas():
    bars = daily(n=420, seed=11)
    c = pd.Series([b.c for b in bars])
    v = np.log(c).diff().rolling(14).std()
    want = v.rolling(365, min_periods=120).rank(pct=True).iloc[-1]
    assert _spot.vol_rank(bars) == pytest.approx(want, rel=1e-9)
