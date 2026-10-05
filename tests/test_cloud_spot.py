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


def test_fitur_candle_berjalan_sama_dengan_riset_pindai():
    """Cloud memakai candle hari ini yang masih berjalan sebagai candle terakhir; riset spot_pindai.provisional
    menghitung hal yang sama dari candle 1 jam. Keduanya harus sama (yang diuji = yang dipasang)."""
    from research.spot_pindai import provisional
    rng = np.random.default_rng(11)
    n_h = 260 * 24
    idx = pd.date_range("2025-01-01", periods=n_h, freq="h", tz="UTC")

    def hourly(seed_shift):
        c = 50 * np.exp(np.cumsum(rng.normal(0, 0.006, n_h)))
        o = np.r_[c[0], c[:-1]]
        return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.002, "low": np.minimum(o, c) * 0.998,
                             "close": c}, index=idx)
    coin_h, btc_h = hourly(0), hourly(1)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    coin_d, btc_d = coin_h.resample("1D").agg(agg), btc_h.resample("1D").agg(agg)
    prov = provisional(coin_d, coin_h, btc_d, btc_h.close)
    for j in (230 * 24 + 5, 240 * 24 + 13, 259 * 24 + 20):      # jam ke-5, 13, 20 dari hari itu
        t = idx[j]
        day = t.floor("D")

        def bars(h):
            done = h[h.index < day].resample("1D").agg(agg)
            part = h[(h.index >= day) & (h.index <= t)]
            out = [_core.Bar(r.Index.to_pydatetime(), r.open, r.high, r.low, r.close) for r in done.itertuples()]
            return out + [_core.Bar(day.to_pydatetime(), part.open.iloc[0], part.high.max(), part.low.min(),
                                    part.close.iloc[-1])]
        x = _spot.features(bars(coin_h), bars(btc_h))
        want = prov.loc[t, FEATS_].to_numpy(float)
        assert np.allclose(x, want, rtol=1e-6, atol=1e-9), (t, x, want)


from research.spot_peluang import FEATS as FEATS_  # noqa: E402


def test_model_terpasang_dan_peluang_masuk_akal():
    if not _spot.MODEL:
        pytest.skip("spot_model.json belum dibuat")
    x = _spot.features(daily(seed=4), daily(seed=5))
    p = _spot.prob(x)
    assert 0 < p < 1 and _spot.MODEL["ambang"] >= 0.9 and len(_spot.MODEL["coins"]) >= 10
    assert _spot.MODEL.get("btc_filter") and "skema" in _spot.MODEL["teruji"]


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


def m15(start, prices):
    """Candle 15 menit mulai [start]: tiap harga = (open, high, low, close) sederhana."""
    return [_core.Bar(start + i * timedelta(minutes=15), p, p * 1.001, p * 0.999, p) for i, p in enumerate(prices)]


def run(store, pub, now, data, coins=("BTC", "ETH"), f15=None, **kw):
    return _spot.spot_tick(now, store, pub, fetch=make_fetch(data), coins_fn=lambda: (list(coins), "uji"),
                           fetch_15m=f15 or (lambda coin, start: []), **kw)


@pytest.fixture
def fake_model(monkeypatch):
    model = {"tp": 0.03, "hari": 10, "ambang": 0.93, "biaya": 0.003, "coins": ["BTC", "ETH"], "fitur": [],
             "teruji": {"baru": {"wr": 92, "avg": 1.2, "kalah": -15}}, "base": 0, "trees": []}
    monkeypatch.setattr(_spot, "MODEL", model)
    monkeypatch.setattr(_spot, "features", lambda bars, btc: [0.0])
    return model


def test_pindai_tiap_tick_lalu_close_tp_setelah_entry(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.95)
    store, pub = Store(), Pub()
    btc, eth = daily(seed=6), daily(seed=7)
    now = btc[-1].t + timedelta(hours=13, minutes=2)     # siang hari: candle harian masih berjalan
    r = run(store, pub, now, {"BTC": btc, "ETH": eth})
    sig = [e for e in pub.events if e["type"] == "spot_signal"]
    assert r["open"] == 2 and {e["coin"] for e in sig} == {"BTC", "ETH"} and r["scanned"] == 2
    assert sig[0]["tp"] == pytest.approx(sig[0]["entry"] * 1.03)
    assert sig[0]["deadline"] == _core.iso(now + 10 * DAY)
    assert any(e["type"] == "spot_status" and e["every_min"] == 10 for e in pub.events)
    # tick berikutnya: tidak ada sinyal ganda
    run(store, pub, now + timedelta(minutes=10), {"BTC": btc, "ETH": eth})
    assert len([e for e in pub.events if e["type"] == "spot_signal"]) == 2
    # BTC: candle 15 menit setelah entry menyentuh TP -> CLOSE di harga TP; ETH belum
    pos = store.s["open"]["BTC"]
    entry_t = _core.parse_iso(pos["time"])

    def f15(coin, start):
        assert start == entry_t or coin == "ETH"
        e = store.s["open"][coin]["entry"]
        bars = m15(start, [e, e * 1.01, e * 1.01, e])
        if coin == "BTC":                                  # candle ke-3: buka di bawah TP, high menembus TP
            bars[2] = _core.Bar(bars[2].t, e * 1.01, e * 1.035, e, e * 1.02)
        return bars
    monkeypatch.setattr(_spot, "prob", lambda x: 0.5)
    run(store, pub, now + timedelta(hours=1), {"BTC": btc, "ETH": eth}, f15=f15)
    cl = [e for e in pub.events if e["type"] == "spot_close"]
    assert [e["coin"] for e in cl] == ["BTC"] and cl[0]["win"] and cl[0]["exit"] == pytest.approx(pos["tp"])
    assert cl[0]["r"] == pytest.approx(2.7, abs=0.01)
    assert "BTC" not in store.s["open"] and store.s["closed"][0]["coin"] == "BTC"


def test_jeda_1_jam_setelah_close(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=12)
    now = btc[-1].t + timedelta(hours=3)
    run(store, pub, now, {"BTC": btc}, coins=("BTC",))
    e = store.s["open"]["BTC"]["entry"]
    hit = lambda coin, start: m15(start, [e, e * 1.04])   # noqa: E731
    run(store, pub, now + timedelta(minutes=10), {"BTC": btc}, coins=("BTC",), f15=hit)
    assert "BTC" not in store.s["open"]                    # close TP, koin sama belum boleh dibeli lagi
    run(store, pub, now + timedelta(minutes=20), {"BTC": btc}, coins=("BTC",))
    assert "BTC" not in store.s["open"]
    run(store, pub, now + timedelta(minutes=80), {"BTC": btc}, coins=("BTC",))
    assert "BTC" in store.s["open"]                        # lewat 1 jam: boleh lagi


def test_close_batas_waktu_dan_maks_posisi(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=8)
    now = btc[-1].t + timedelta(hours=6)
    run(store, pub, now, {"BTC": btc, "ETH": btc}, max_open=1)
    assert len(store.s["open"]) == 1                      # maks 1 posisi
    entry = store.s["open"]["BTC"]["entry"]
    flat = lambda coin, start: m15(start, [entry * 0.97] * 960 + [entry * 0.90] * 40)   # noqa: E731
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)
    run(store, pub, now + 10 * DAY + timedelta(hours=1), {"BTC": btc, "ETH": btc}, f15=flat)
    cl = [e for e in pub.events if e["type"] == "spot_close"]
    assert len(cl) == 1 and not cl[0]["win"] and "hari habis" in cl[0]["reason"]
    assert cl[0]["exit"] == pytest.approx(entry * 0.97)     # close candle terakhir sebelum batas waktu


def test_tp_sebelum_entry_di_hari_yang_sama_tidak_dihitung(fake_model, monkeypatch):
    """Cadangan tanpa candle 15 menit: high harian hari entry (bisa terjadi SEBELUM entry) tidak dipakai."""
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=13)
    now = btc[-1].t + timedelta(hours=15)
    run(store, pub, now, {"BTC": btc}, coins=("BTC",))
    pos = store.s["open"]["BTC"]
    today = _core.Bar(btc[-1].t, btc[-1].o, pos["entry"] * 1.10, btc[-1].l, pos["entry"])   # high pagi > TP
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)

    def boom(coin, start):
        raise RuntimeError("15m gagal")
    run(store, pub, now + timedelta(minutes=10), {"BTC": btc[:-1] + [today]}, coins=("BTC",), f15=boom)
    assert "BTC" in store.s["open"] and not [e for e in pub.events if e["type"] == "spot_close"]
    tomorrow = _core.Bar(btc[-1].t + DAY, pos["entry"], pos["entry"] * 1.031, pos["entry"] * 0.99, pos["entry"])
    run(store, pub, now + DAY, {"BTC": btc[:-1] + [today, tomorrow]}, coins=("BTC",), f15=boom)
    cl = [e for e in pub.events if e["type"] == "spot_close"]
    assert len(cl) == 1 and cl[0]["win"]


def test_btc_di_bawah_sma200_menjeda_spot(fake_model, monkeypatch):
    fake_model["fitur"] = ["btc_up"]
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    monkeypatch.setattr(_spot, "features", lambda bars, b: [0.0])          # BTC < SMA200
    store, pub = Store(), Pub()
    btc = daily(seed=14)
    r = run(store, pub, btc[-1].t + timedelta(hours=2), {"BTC": btc, "ETH": btc})
    assert r["btc_up"] is False and not [e for e in pub.events if e["type"] == "spot_signal"]
    st = [e for e in pub.events if e["type"] == "spot_status"][-1]
    assert st["btc_up"] is False and st["btc_filter"]
    # filter dimatikan (env SPOT_BTC_FILTER=0) -> sinyal tetap keluar
    store2, pub2 = Store(), Pub()
    run(store2, pub2, btc[-1].t + timedelta(hours=2), {"BTC": btc, "ETH": btc}, btc_filter=False)
    assert len([e for e in pub2.events if e["type"] == "spot_signal"]) == 2


def test_daftar_koin_volume_terbesar_tanpa_stablecoin():
    rows = [{"symbol": s, "quoteVolume": str(v)} for s, v in [
        ("BTCUSDT", 9e9), ("ETHUSDT", 5e9), ("USDCUSDT", 8e9), ("FDUSDUSDT", 7e9), ("SOLUSDT", 2e9),
        ("JUPUSDT", 1e8), ("BTCUPUSDT", 9e8), ("PEPEUSDT", 6e8), ("WBTCUSDT", 5e8), ("TINYUSDT", 1e6),
        ("ETHBTC", 9e9), ("PAXGUSDT", 3e8), ("XRPUSDT", 7e8)]]
    assert _spot.pick_coins(rows, 100, 5e6) == ["BTC", "ETH", "SOL", "XRP", "PEPE", "JUP"]
    assert _spot.pick_coins(rows, 3, 5e6) == ["BTC", "ETH", "SOL"]
    assert _spot.pick_coins([r for r in rows if r["symbol"] != "BTCUSDT"], 2, 5e6) == ["BTC", "ETH", "SOL"]


def test_daftar_koin_gagal_pakai_koin_model(fake_model, monkeypatch):
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)
    store, pub = Store(), Pub()
    btc = daily(seed=15)

    def bad():
        raise RuntimeError("ticker 403")
    r = _spot.spot_tick(btc[-1].t + timedelta(hours=1), store, pub, fetch=make_fetch({"BTC": btc, "ETH": btc}),
                        coins_fn=bad, fetch_15m=lambda c, s: [])
    assert r["scanned"] == 2 and "ticker 403" in r["errors"][0]


def test_waktu_habis_koin_sisa_didahulukan_tick_berikutnya(fake_model, monkeypatch):
    import time as _t
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)
    monkeypatch.setattr(_spot, "WORKERS", 1)
    coins = ["BTC", "A", "B", "C", "D"]
    btc = daily(seed=16, n=230)
    seen = []

    def slow(coin, n, key, budget):
        seen.append(coin)
        _t.sleep(0.3)
        return btc, "uji"
    store, pub = Store(), Pub()
    r = _spot.spot_tick(btc[-1].t + timedelta(hours=1), store, pub, fetch=slow, coins_fn=lambda: (coins, "uji"),
                        fetch_15m=lambda c, s: [], deadline_s=1.0)
    assert 1 <= r["scanned"] < len(coins)
    first = len(seen)
    seen.clear()
    _t.sleep(0.4 * (len(coins) - first + 1))                 # thread lama selesai
    seen.clear()
    _spot.spot_tick(btc[-1].t + timedelta(hours=1, minutes=10), store, pub, fetch=slow,
                    coins_fn=lambda: (coins, "uji"), fetch_15m=lambda c, s: [], deadline_s=5.0)
    assert seen[1] == coins[r["scanned"]]                    # setelah BTC: koin pertama yang tadi terlewat


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
    run(store, pub, btc[-1].t + timedelta(minutes=6), {"BTC": btc, "ETH": btc})
    sig = [e for e in pub.events if e["type"] == "spot_signal"]
    assert len(sig) == 2 and sig[0]["alasan"] == "3 merah"
    monkeypatch.setattr(_spot, "features", lambda bars, b: [2.0, -0.12, 0.05])     # hanya 2 merah: tidak
    store2, pub2 = Store(), Pub()
    run(store2, pub2, btc[-1].t + timedelta(minutes=6), {"BTC": btc, "ETH": btc})
    assert not [e for e in pub2.events if e["type"] == "spot_signal"]


def vbars(n=420, seed=20, qv=1e6, last_qv=None):
    out = [_spot.VBar(b.t, b.o, b.h, b.l, b.c, qv) for b in daily(n=n, seed=seed)]
    if last_qv is not None:
        b = out[-1]
        out[-1] = _spot.VBar(b.t, b.o, b.h, b.l, b.c, last_qv)
    return out


def test_filter_kualitas_koin_berisiko_turun_jauh(monkeypatch):
    monkeypatch.setitem(_spot.MODEL, "kualitas", {"umur_min": 365, "vol_panik": 3.0, "ambruk": -0.80})
    bars = vbars()
    now = bars[-1].t + DAY                                   # candle terakhir sudah penuh
    assert _spot.quality(bars, now) in (None, "ambruk dari puncak 1 tahun")
    assert _spot.quality(bars[-300:], now) == "koin < 1 tahun"
    crash = bars[:-1] + [_core.Bar(bars[-1].t, bars[-1].o, bars[-1].o, 0.01, max(b.h for b in bars[-365:]) * 0.15)]
    assert _spot.quality(crash, now) == "ambruk dari puncak 1 tahun"
    flat = [_spot.VBar(b.t, 100, 101, 99, 100, 1e6) for b in bars]
    assert _spot.quality(flat, now) is None
    panic = flat[:-1] + [_spot.VBar(flat[-1].t, 100, 101, 99, 100, 3.5e6)]
    assert _spot.quality(panic, now) == "volume panik"
    # pagi hari (1 jam berjalan): volume 24 jam ≈ hari ini + sisa kemarin, tidak dianggap panik
    early = flat[:-1] + [_spot.VBar(flat[-1].t, 100, 101, 99, 100, 0.2e6)]
    assert _spot.quality(early, flat[-1].t + timedelta(hours=1)) is None


def test_peringatan_turun_jauh_sekali_per_level(fake_model, monkeypatch):
    fake_model["teruji"]["jatuh"] = {"10": {"tetap_tp": 66.0, "akhir": -4.3}, "20": {"tetap_tp": 35.0, "akhir": -12.4}}
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    btc = daily(seed=21)
    now = btc[-1].t + timedelta(hours=2)
    run(store, pub, now, {"BTC": btc}, coins=("BTC",))
    e = store.s["open"]["BTC"]["entry"]
    monkeypatch.setattr(_spot, "prob", lambda x: 0.1)
    for i, px in enumerate((e * 0.88, e * 0.87, e * 0.79, e * 0.78)):
        f15 = lambda coin, start, px=px: m15(start, [px])     # noqa: E731
        run(store, pub, now + timedelta(minutes=10 * (i + 1)), {"BTC": btc}, coins=("BTC",), f15=f15)
    w = [x for x in pub.events if x["type"] == "spot_warn"]
    assert [x["lvl"] for x in w] == [10, 20] and w[0]["tetap_tp"] == 66.0 and "BTC" in store.s["open"]


def test_kualitas_dipakai_saat_pindai(fake_model, monkeypatch):
    fake_model["kualitas"] = {"umur_min": 365, "vol_panik": 3.0, "ambruk": -0.80}
    monkeypatch.setattr(_spot, "prob", lambda x: 0.99)
    store, pub = Store(), Pub()
    young = daily(seed=22, n=300)                            # < 1 tahun
    r = run(store, pub, young[-1].t + timedelta(hours=1), {"BTC": young, "ETH": young})
    st = [x for x in pub.events if x["type"] == "spot_status"][-1]
    assert r["open"] == 0 and st["skipped"] == {"koin < 1 tahun": 2}
    store2, pub2 = Store(), Pub()
    run(store2, pub2, young[-1].t + timedelta(hours=1), {"BTC": young, "ETH": young}, use_quality=False)
    assert len(store2.s["open"]) == 2
