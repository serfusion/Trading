import importlib.util
import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

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


def run_ticks(df, every_minutes=30, double=False):
    prices, store, pub = FakePrices(to_bars(df)), FakeStore(), FakePub()
    now = df.index[60].to_pydatetime()
    end = df.index[-1].to_pydatetime() + timedelta(hours=1)
    while now <= end:
        prices.now = now
        _core.tick(now, prices, store, pub)
        if double:
            _core.tick(now, prices, store, pub)   # cron terpanggil dua kali
        now += timedelta(minutes=every_minutes)
    return store, pub


def test_tick_flow_signal_then_close_and_idempotent():
    df = bars_from_path(trend_path(), start="2026-09-14 00:00", freq="1h", wick=0.5)
    store, pub = run_ticks(df)
    sig = [e for e in pub.events if e["type"] == "signal"]
    cls = [e for e in pub.events if e["type"] == "close"]
    assert sig and sig[0]["dir"] == "BUY"
    assert cls and cls[0]["id"] == sig[0]["id"] and cls[0]["points"] > 0
    assert len(sig) - len(cls) in (0, 1)
    assert any(e["type"] == "heartbeat" for e in pub.events)
    _, pub2 = run_ticks(df, double=True)
    sig2 = [e for e in pub2.events if e["type"] == "signal"]
    assert [e["id"] for e in sig2] == [e["id"] for e in sig]    # tidak ada sinyal ganda


def test_stop_loss_closes_virtual_position():
    path = trend_path(n_flat=80, n_up=30, n_down=0)
    crash = list(np.linspace(path[-1], path[-1] - 80, 6))
    df = bars_from_path(path + crash + [path[-1] - 80] * 10, start="2026-09-14 00:00", freq="1h", wick=0.5)
    _, pub = run_ticks(df)
    cls = [e for e in pub.events if e["type"] == "close"]
    assert cls and cls[0]["reason"] == "Stop loss tersentuh" and cls[0]["r"] == -1.0


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
