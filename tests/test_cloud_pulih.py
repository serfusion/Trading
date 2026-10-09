"""🔗 Emas pulih → kripto ikut naik (cloud/api/_pulih.py): kejadian jatuh-pantul, korelasi XAU–BTC, buka & tutup 48 jam."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402
import _pulih  # noqa: E402

T0 = datetime(2026, 1, 4, 23, tzinfo=timezone.utc)      # Minggu malam: pasar emas buka


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


def tenang(n=2600, seed=3):
    """Candle H1 jam pasar saja, gerak kecil acak (ATR ±0,3)."""
    rng = np.random.default_rng(seed)
    out, p, t = [], 2000.0, T0
    while len(out) < n:
        if _core.market_open(t):
            o = p
            p = p + rng.normal(0, 0.2)
            out.append(_core.Bar(t, o, max(o, p) + 0.1, min(o, p) - 0.1, p))
        t += timedelta(hours=1)
    return out


def jatuh_pantul(bars, turun=12.0, naik=6.0):
    """4 candle turun `turun`, lalu 3 candle naik `naik` (memantul > 38,2%)."""
    out, p = list(bars), bars[-1].c
    t = bars[-1].t
    for d in [-turun / 4] * 4 + [naik / 3] * 3:
        t += timedelta(hours=1)
        while not _core.market_open(t):
            t += timedelta(hours=1)
        o, p = p, p + d
        out.append(_core.Bar(t, o, max(o, p) + 0.05, min(o, p) - 0.05, p))
    return out


def btc_ikut(bars, faktor=2.0, seed=4):
    """BTC harian searah emas (return = faktor × return emas + derau kecil) → korelasi tinggi; semua tanggal kalender."""
    rng = np.random.default_rng(seed)
    xd = {}
    for b in bars:
        xd[b.t.strftime("%Y-%m-%d")] = b.c
    out, v, prev = {}, 50000.0, None
    d = datetime.strptime(min(xd), "%Y-%m-%d")
    end = datetime.strptime(max(xd), "%Y-%m-%d")
    while d <= end:
        k = d.strftime("%Y-%m-%d")
        if k in xd and prev is not None:
            v *= 1 + faktor * (xd[k] / prev - 1) + rng.normal(0, 1e-5)
        if k in xd:
            prev = xd[k]
        out[k] = v
        d += timedelta(days=1)
    return out


def test_pantul_deteksi_transisi():
    bars = jatuh_pantul(tenang(400))
    atr = _pulih.atr_ewm(bars)
    hits = [i for i in range(len(bars)) if _pulih.pantul(bars, atr, i)]
    assert hits == [len(bars) - 1]                       # candle pantul ke-3 (+6 dari dasar) menembus 38,2%, sekali
    k = _pulih.pantul(bars, atr, hits[0])
    assert k["atr_x"] >= _pulih.K and k["top"] > k["level"] > k["bot"]
    # jatuh kecil (< 5 ATR) tidak dihitung
    kecil = jatuh_pantul(tenang(400), turun=1.0, naik=0.6)
    a2 = _pulih.atr_ewm(kecil)
    assert not any(_pulih.pantul(kecil, a2, i) for i in range(len(kecil)))


def test_korelasi_sama_dengan_pandas():
    bars = tenang(2600)
    rng = np.random.default_rng(9)
    btc = {}
    d = datetime(2026, 1, 1)
    while d <= bars[-1].t.replace(tzinfo=None) + timedelta(days=1):
        btc[d.strftime("%Y-%m-%d")] = 50000 * (1 + rng.normal(0, 0.03))
        d += timedelta(days=1)
    hari = bars[-1].t.strftime("%Y-%m-%d")
    got = _pulih.korelasi(bars, btc, hari)
    # rujukan: cara research.xau_kripto (pandas 3 — pct_change hanya tanggal kalender berurutan, shift 1)
    xs = pd.Series({pd.Timestamp(b.t): b.c for b in bars}).resample("D").last()
    bs = pd.Series({pd.Timestamp(k, tz="UTC"): v for k, v in btc.items()}).resample("D").last()
    xr = xs / xs.shift(1) - 1
    br = bs / bs.shift(1) - 1
    dd = pd.DataFrame({"x": xr, "b": br}).dropna()
    ref = dd.x.rolling(60).corr(dd.b).shift(1)
    want = ref.reindex([pd.Timestamp(hari, tz="UTC")], method="ffill").iloc[0]
    assert got is not None and abs(got - want) < 1e-9
    # data kurang dari 60 baris → None
    assert _pulih.korelasi(bars[:300], btc, bars[299].t.strftime("%Y-%m-%d")) is None


def test_buka_lalu_tutup_48_jam():
    base = tenang(2600)
    bars = jatuh_pantul(base)
    btc = btc_ikut(bars)
    mem, pub = Mem(), Pub()
    harga = {"v": 100.0}
    prices = lambda koin: {c: harga["v"] for c in koin}      # noqa: E731
    # tick pertama: hanya mencatat candle terakhir (tanpa memutar ulang riwayat)
    _pulih.pulih_tick(base[-1].t + timedelta(hours=1, minutes=2), base, mem, pub, lambda: btc, prices)
    assert pub.ev == [] and mem.s["last_bar"] == _core.iso(base[-1].t)
    for i in range(len(base), len(bars)):
        _pulih.pulih_tick(bars[i].t + timedelta(hours=1, minutes=2), bars[:i + 1], mem, pub, lambda: btc, prices)
    sig = [e for e in pub.ev if e["type"] == "pulih_signal"]
    assert len(sig) == 1
    ev = sig[0]
    assert ev["dir"] == "BUY" and set(ev["koin"]) == set(_pulih.KOIN) and ev["korelasi"] >= _pulih.CORR_MIN
    assert mem.s["open"]["id"] == ev["id"]
    # sebelum 48 jam: belum ditutup
    now = _core.parse_iso(ev["time"])
    harga["v"] = 110.0
    _pulih.pulih_tick(now + timedelta(hours=47), bars, mem, pub, lambda: btc, prices)
    assert not [e for e in pub.ev if e["type"] == "pulih_close"]
    _pulih.pulih_tick(now + timedelta(hours=48, minutes=1), bars, mem, pub, lambda: btc, prices)
    cl = [e for e in pub.ev if e["type"] == "pulih_close"]
    assert len(cl) == 1 and cl[0]["id"] == ev["id"]
    assert abs(cl[0]["r_pct"] - 9.8) < 1e-6 and cl[0]["win"] and cl[0]["naik"] == len(_pulih.KOIN)
    assert mem.s["open"] is None and mem.s["closed"][0]["id"] == ev["id"]


def test_korelasi_rendah_tidak_kirim():
    base = tenang(2600)
    bars = jatuh_pantul(base)
    btc = btc_ikut(bars, faktor=-2.0)                    # BTC berlawanan → korelasi negatif
    mem, pub = Mem(), Pub()
    prices = lambda koin: {c: 1.0 for c in koin}         # noqa: E731
    _pulih.pulih_tick(base[-1].t + timedelta(hours=1, minutes=2), base, mem, pub, lambda: btc, prices)
    out = None
    for i in range(len(base), len(bars)):
        out = _pulih.pulih_tick(bars[i].t + timedelta(hours=1, minutes=2), bars[:i + 1], mem, pub, lambda: btc, prices)
    assert pub.ev == [] and mem.s.get("open") is None
    assert any("dilewati" in e for e in out["events"]) or mem.s.get("last_ev")
