import importlib.util
import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from helpers import bars_from_path
from test_trend import trend_path
from xau_bot.config import TrendConfig
from xau_bot.models import Direction
from xau_bot.trend import TrendStrategy

API = Path(__file__).resolve().parent.parent / "cloud" / "api"
sys.path.insert(0, str(API))
import _core  # noqa: E402


def to_bars(df):
    return [_core.Bar(t.to_pydatetime(), r.open, r.high, r.low, r.close) for t, r in df.iterrows()]


def test_cloud_logic_identical_to_bot_trend_module():
    rng = np.random.default_rng(3)
    closes = 2000 + np.cumsum(rng.standard_t(4, 1500) * 3)
    df = bars_from_path(closes, freq="1h", wick=1.0)
    df["high"] += np.abs(rng.normal(0, 1.5, len(df)))
    df["low"] -= np.abs(rng.normal(0, 1.5, len(df)))
    bot = TrendStrategy(TrendConfig())
    bars = to_bars(df)
    checked = 0
    for end in range(80, len(df), 7):
        for pos, pos_c in [(None, None), (Direction.BUY, "BUY"), (Direction.SELL, "SELL")]:
            a = bot.evaluate(df.iloc[max(0, end - 150):end], pos)
            b = _core.evaluate(bars[max(0, end - 150):end], pos_c)
            assert a.action == b["action"]
            if a.action == "open":
                assert a.direction.name == b["dir"]
                assert abs(a.atr - b["atr"]) < 1e-9
            checked += 1
    assert checked > 500


class FakePrices:
    def __init__(self, bars):
        self.all = bars
        self.now = None

    def candles(self, n):
        # termasuk bar yang sedang berjalan (seperti API aslinya)
        return [b for b in self.all if b.t <= self.now][-n:]


class FakeStore:
    def __init__(self):
        self.state, self.logs = {}, []

    def get_state(self):
        return dict(self.state)

    def save_state(self, data):
        self.state = dict(data)

    def log(self, kind, payload):
        self.logs.append((kind, payload))


class FakePub:
    def __init__(self):
        self.events = []

    def publish(self, event, text=None, title="", priority=3, tags=None):
        self.events.append(event)


def run_ticks(df, every_minutes=30, double=False, cfg=None):
    cfg = cfg or {**_core.CFG, "star_only": False, "market_hours": False, "skip_open_bars": 0, "profit_only": False}
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = df.index[60].to_pydatetime()
    end = df.index[-1].to_pydatetime() + timedelta(hours=1)
    while now <= end:
        prices.now = now
        _core.tick(now, prices, store, pub, cfg)
        if double:
            _core.tick(now, prices, store, pub, cfg)   # cron terpanggil dua kali
        now += timedelta(minutes=every_minutes)
    return store, pub


ONE_SET = {**_core.CFG, "star_only": False, "market_hours": False, "skip_open_bars": 0, "profit_only": False, "sets": [(55, 20)]}


def test_tick_flow_ensemble_signal_close_and_idempotent():
    df = bars_from_path(trend_path(), start="2026-09-14 00:00", freq="1h", wick=0.5)
    store, pub = run_ticks(df)
    sig = [e for e in pub.events if e["type"] == "signal"]
    cls = [e for e in pub.events if e["type"] == "close"]
    assert sig and {e["set"] for e in sig} >= {"T40/15", "T55/20"}
    ids = {e["id"] for e in sig}
    assert all(c["id"] in ids for c in cls)                 # setiap TUTUP punya sinyal
    for name in {e["set"] for e in sig}:
        n_sig = sum(1 for e in sig if e["set"] == name)
        n_cls = sum(1 for e in cls if e["set"] == name)
        assert n_sig - n_cls in (0, 1)                      # tidak ada entry ganda per set
    first = sig[0]
    assert first["tp1"] > first["entry"] > first["sl"] and first["legs"] == 5 and first["lot"] == "5 x 0.01"
    assert any(e["type"] == "info" and "TP1" in e["text"] for e in pub.events)
    assert any(e["type"] == "heartbeat" for e in pub.events)
    _, pub2 = run_ticks(df, double=True)
    assert [e["id"] for e in pub2.events if e["type"] == "signal"] == [e["id"] for e in sig]


def test_stop_loss_before_tp1_is_minus_one_r():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4
    df = bars_from_path(flat + [top] + list(np.linspace(top, top - 60, 3)) + [top - 60] * 10,
                        start="2026-09-14 00:00", freq="1h", wick=0.5)
    _, pub = run_ticks(df, cfg=ONE_SET)
    cls = [e for e in pub.events if e["type"] == "close"]
    assert cls and cls[0]["reason"] == "Stop loss tersentuh" and cls[0]["r"] == -1.0
    assert not any(e["type"] == "info" and "TP1" in e.get("text", "") for e in pub.events)


def test_tp1_then_break_even_is_small_profit():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4
    rise = list(np.linspace(top, top + 25, 4))
    df = bars_from_path(flat + [top] + rise + list(np.linspace(rise[-1], top - 40, 4)) + [top - 40] * 10,
                        start="2026-09-14 00:00", freq="1h", wick=0.5)
    _, pub = run_ticks(df, cfg=ONE_SET)
    info = [e for e in pub.events if e["type"] == "info" and "TP1" in e.get("text", "")]
    cls = [e for e in pub.events if e["type"] == "close"]
    assert info and cls
    assert cls[0]["reason"] == "SL+ (break-even) tersentuh" and cls[0]["tp1_hit"]
    assert 0.15 < cls[0]["r"] < 0.3                       # (1R + 4 x ~0R) / 5


def test_twelvedata_parsing(monkeypatch):
    payload = {"status": "ok", "values": [
        {"datetime": "2026-09-25 10:00:00", "open": "4300", "high": "4310", "low": "4295", "close": "4305"},
        {"datetime": "2026-09-25 09:00:00", "open": "4290", "high": "4302", "low": "4288", "close": "4300"}]}
    seen = {}

    def fake_http(method, url, headers=None, body=None, timeout=15):
        seen["url"] = url
        return payload
    monkeypatch.setattr(_core, "http", fake_http)
    bars = _core.TwelveData("KEY").candles(2)
    assert "symbol=XAU%2FUSD" in seen["url"] and "interval=1h" in seen["url"]
    assert bars[0].t == datetime(2026, 9, 25, 9, tzinfo=timezone.utc) and bars[1].c == 4305.0


def test_endpoint_requires_secret(monkeypatch):
    spec = importlib.util.spec_from_file_location("cloud_tick", API / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setenv("CRON_SECRET", "rahasia")

    class Req(mod.handler):
        def __init__(self, path):
            self.path, self.headers = path, {}
            self.wfile = io.BytesIO()
            self.code = None

        def send_response(self, code, message=None):
            self.code = code

        def send_header(self, *a):
            pass

        def end_headers(self):
            pass

    r = Req("/api/tick?key=salah")
    r.do_GET()
    assert r.code == 401
    monkeypatch.setattr(mod, "run", lambda: (200, {"ok": True}))
    r = Req("/api/tick?key=rahasia")
    r.do_GET()
    assert r.code == 200 and b'"ok": true' in r.wfile.getvalue()


def test_scheme_r_matches_standard_and_variants():
    df = bars_from_path(trend_path(), start="2026-09-14 00:00", freq="1h", wick=0.5)
    store, pub = run_ticks(df)
    closes = [e for e in pub.events if e["type"] == "close"]
    assert closes
    for c in closes:
        rb = c["r_by"]
        assert set(rb) == {"1_tp1", "1_07", "3_tp1", "3_07"}
        assert abs(rb["1_tp1"] - c["r"]) < 1e-3                  # skema standar = hasil virtual
        if c["tp1_hit"]:
            assert rb["3_tp1"] <= rb["1_tp1"] + 1e-9 or c["points"] <= c["risk_points"]
    infos = [e for e in pub.events if e["type"] == "info" and e.get("kind") == "be07"]
    tp1 = [e for e in pub.events if e["type"] == "info" and e.get("kind") == "tp1"]
    assert tp1 and infos and all("TP1" not in e["text"] for e in infos)


def test_heartbeat_level_tutup_sama_dengan_aturan_keluar():
    """exits di heartbeat = low/high N candle terakhir yang sudah tutup; TUTUP terjadi tepat saat close menembusnya."""
    df = bars_from_path(trend_path(), start="2026-09-14 00:00", freq="1h", wick=0.5)
    store, pub = run_ticks(df, every_minutes=60)
    hbs = [e for e in pub.events if e["type"] == "heartbeat"]
    with_exit = [h for h in hbs if h.get("exits")]
    assert with_exit
    closes = {e["id"]: e for e in pub.events if e["type"] == "close"}
    checked = 0
    for h in with_exit:
        for x in h["exits"]:
            assert x["set"] in ("T40/15", "T55/20", "T80/30") and x["bars"] in (15, 20, 30)
            t = pd.Timestamp(h["time"])
            done = df[df.index + pd.Timedelta(hours=1) <= t]           # candle yang sudah tutup saat tick
            window = done.iloc[-x["bars"]:]
            want = window.low.min() if x["dir"] == "BUY" else window.high.max()
            assert abs(x["level"] - round(want, 3)) < 1e-6
            checked += 1
    assert checked > 10 and closes
