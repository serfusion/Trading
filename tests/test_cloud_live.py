"""Uji auto order cloud (MetaApi disimulasikan): tanpa dobel, SL/TP benar, SL+, tutup, kontrol."""
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest

from helpers import bars_from_path
from test_cloud import FakePrices, FakePub, to_bars
from test_trend import trend_path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402

ONE_SET = {**_core.CFG, "sets": [(55, 20)], "max_leg_lot": 0.10}


class Store:
    def __init__(self, control=None):
        self.state, self.control, self.logs, self.saves = {}, dict(control or {}), [], 0

    def get_state(self):
        return dict(self.state)

    def save_state(self, data):
        self.saves += 1
        self.state = dict(data)

    def get_control(self):
        return dict(self.control)

    def save_control(self, data):
        self.control = dict(data)

    def log(self, kind, payload):
        self.logs.append((kind, payload))


class FakeMetaApi:
    """Meniru MetaApi + server broker: SL/TP dieksekusi saat harga menyentuh (pakai bar terakhir)."""

    def __init__(self, fail_on_leg=None):
        self.positions_ = []
        self.calls = []
        self.fail_on_leg = fail_on_leg
        self.next_id = 1
        self.closed = []

    def account(self):
        return {"balance": 30000.0, "equity": 30000.0, "currency": "USC"}

    def positions(self, magic=None):
        return [dict(p) for p in self.positions_ if magic is None or p["magic"] == magic]

    def market(self, direction, volume, sl, tp, magic, comment, client_id):
        self.calls.append(("market", direction, volume, sl, tp, magic, comment, client_id))
        if self.fail_on_leg and len([c for c in self.calls if c[0] == "market"]) == self.fail_on_leg:
            return {"ok": False, "message": "TRADE_RETCODE_REJECT"}
        self.positions_.append({"id": str(self.next_id), "type": "POSITION_TYPE_BUY" if direction == "BUY"
                                else "POSITION_TYPE_SELL", "symbol": "XAUUSDc", "magic": magic,
                                "openPrice": self.price + 0.05, "stopLoss": sl, "takeProfit": tp, "volume": volume})
        self.next_id += 1
        return {"ok": True, "stringCode": "TRADE_RETCODE_DONE"}

    def modify(self, position_id, sl, tp):
        self.calls.append(("modify", position_id, sl, tp))
        for p in self.positions_:
            if p["id"] == position_id:
                p["stopLoss"], p["takeProfit"] = sl, tp
        return {"ok": True}

    def close(self, position_id):
        self.calls.append(("close", position_id))
        self.closed += [p for p in self.positions_ if p["id"] == position_id]
        self.positions_ = [p for p in self.positions_ if p["id"] != position_id]
        return {"ok": True}

    def broker_step(self, bar):
        """SL/TP di server broker."""
        keep = []
        for p in self.positions_:
            buy = p["type"] == "POSITION_TYPE_BUY"
            sl_hit = p["stopLoss"] and ((bar.l <= p["stopLoss"]) if buy else (bar.h >= p["stopLoss"]))
            tp_hit = p["takeProfit"] and ((bar.h >= p["takeProfit"]) if buy else (bar.l <= p["takeProfit"]))
            if sl_hit or tp_hit:
                self.closed.append({**p, "by": "sl" if sl_hit else "tp"})
            else:
                keep.append(p)
        self.positions_ = keep


def run(df, control, executor, twice=False, cfg=ONE_SET, every=30):
    prices, store, pub = FakePrices(to_bars(df)), Store(control), FakePub()
    now = df.index[60].to_pydatetime()
    end = df.index[-1].to_pydatetime() + timedelta(hours=1)
    while now <= end:
        prices.now = now
        bars = prices.candles(5)
        executor.price = bars[-1].c
        executor.broker_step(bars[-1])
        _core.tick(now, prices, store, pub, cfg, executor=executor)
        if twice:
            _core.tick(now, prices, store, pub, cfg, executor=executor)
        now += timedelta(minutes=every)
    return store, pub


def market_calls(ex):
    return [c for c in ex.calls if c[0] == "market"]


def df_trend():
    return bars_from_path(trend_path(), start="2026-09-14 00:00", freq="1h", wick=0.5)


def test_auto_off_by_default_sends_no_orders():
    ex = FakeMetaApi()
    _, pub = run(df_trend(), {}, ex)
    assert market_calls(ex) == []
    assert any(e["type"] == "signal" for e in pub.events)        # sinyal tetap dikirim


def test_auto_on_opens_five_legs_correctly():
    ex = FakeMetaApi()
    run(df_trend(), {"auto": True, "leg_lot": 0.01}, ex)
    buys = [c for c in market_calls(ex) if c[1] == "BUY"]
    assert len(buys) == 5
    assert len({c[3] for c in buys}) == 1                          # SL sama
    assert sum(1 for c in buys if c[4]) == 1                        # hanya posisi #1 punya TP1
    assert all(c[2] == 0.01 and c[5] == _core.BASE_MAGIC + 0 for c in buys)
    assert all(len(c[6]) <= 12 and len(c[7]) <= 12 for c in buys)  # batas comment + clientId MetaApi
    assert buys[0][4] > buys[0][3]                                  # TP di atas, SL di bawah (BUY)


def test_no_duplicate_orders_when_cron_runs_twice():
    ex1, ex2 = FakeMetaApi(), FakeMetaApi()
    run(df_trend(), {"auto": True}, ex1)
    run(df_trend(), {"auto": True}, ex2, twice=True)
    assert len(market_calls(ex2)) == len(market_calls(ex1))


def test_tp1_then_slplus_uses_fill_price_and_exit_closes_all():
    ex = FakeMetaApi()
    run(df_trend(), {"auto": True}, ex)
    tp_closed = [p for p in ex.closed if p.get("by") == "tp"]
    assert tp_closed                                                # TP1 kena di server
    mods = [c for c in ex.calls if c[0] == "modify"]
    assert len(mods) == 4 * len(tp_closed)                          # SL+ untuk 4 posisi sisa per sinyal
    assert len({m[1] for m in mods}) == len(mods)                   # tiap posisi hanya sekali dimodifikasi
    assert not {m[1] for m in mods} & {p["id"] for p in tp_closed}  # posisi TP1 tidak disentuh
    pos = {p["id"]: p for p in ex.closed + ex.positions_}
    for m in mods:                                                  # SL+ = harga isi asli + 0.10 (BUY) / - 0.10 (SELL)
        sign = 1 if pos[m[1]]["type"] == "POSITION_TYPE_BUY" else -1
        assert m[2] == pytest.approx(pos[m[1]]["openPrice"] + sign * _core.CFG["be_offset"])
    buys = [p for p in ex.closed if p["type"] == "POSITION_TYPE_BUY"]
    assert len(buys) == 5                                           # BUY selesai: TP1 + 4 runner ditutup
    assert not [p for p in ex.positions_ if p["type"] == "POSITION_TYPE_BUY"]


def test_paused_blocks_new_orders():
    ex = FakeMetaApi()
    _, pub = run(df_trend(), {"auto": True, "paused": True}, ex)
    assert market_calls(ex) == []
    hb = [e for e in pub.events if e["type"] == "heartbeat"]
    assert hb[-1]["mode"] == "SINYAL (auto dijeda)" and hb[-1]["balance"] == 30000.0


def test_lot_is_capped():
    ex = FakeMetaApi()
    run(df_trend(), {"auto": True, "leg_lot": 5.0}, ex)
    assert market_calls(ex) and all(c[2] == 0.10 for c in market_calls(ex))


def test_rejected_leg_stops_and_never_duplicates():
    ex = FakeMetaApi(fail_on_leg=3)
    run(df_trend(), {"auto": True}, ex)
    first_signal = [c for c in market_calls(ex) if c[1] == "BUY"]
    assert len(first_signal) == 3                                   # 2 sukses, leg 3 ditolak -> berhenti


def test_metaapi_down_still_sends_signals():
    class Down(FakeMetaApi):
        def positions(self, magic=None):
            raise OSError("timeout")

        def account(self):
            raise OSError("timeout")

    ex = Down()
    _, pub = run(df_trend(), {"auto": True}, ex)
    assert market_calls(ex) == []
    assert any(e["type"] == "signal" for e in pub.events)
    assert any(e["type"] == "info" and "dilewati" in e["text"] for e in pub.events)
    assert "MetaApi" in [e for e in pub.events if e["type"] == "heartbeat"][-1]["block"]


def test_stop_loss_on_server_limits_loss():
    flat = [4300 + 2 * np.sin(i / 2) for i in range(80)]
    top = flat[-1] + 4
    df = bars_from_path(flat + [top] + list(np.linspace(top, top - 60, 3)) + [top - 60] * 10,
                        start="2026-09-14 00:00", freq="1h", wick=0.5)
    ex = FakeMetaApi()
    run(df, {"auto": True}, ex)
    buys = [p for p in ex.closed if p["type"] == "POSITION_TYPE_BUY"]
    assert len(buys) == 5 and all(p["by"] == "sl" for p in buys)
    assert not [c for c in ex.calls if c[0] == "modify"]           # tidak ada SL+ karena TP1 tak kena


def test_control_validation_and_close_all():
    ex = FakeMetaApi()
    ex.price = 4300
    ex.market("BUY", 0.01, 4250, None, _core.BASE_MAGIC, "x", "y")
    ex.positions_.append({"id": "99", "type": "POSITION_TYPE_BUY", "symbol": "XAUUSDc", "magic": 12345,
                          "openPrice": 1, "stopLoss": 0, "takeProfit": 0, "volume": 1})   # posisi manual
    store, pub = Store(), FakePub()
    st = _core.apply_control(store, ex, pub, {"auto": True, "leg_lot": 0.02, "legs": 5})
    assert st["control"] == {"auto": True, "paused": False, "leg_lot": 0.02, "legs": 5}
    with pytest.raises(ValueError):
        _core.apply_control(store, ex, pub, {"leg_lot": 1.0})
    with pytest.raises(ValueError):
        _core.apply_control(store, ex, pub, {"legs": 50})
    st = _core.apply_control(store, ex, pub, {"close_all": True})
    assert st["control"]["paused"] is True
    assert [p["id"] for p in ex.positions_] == ["99"]              # posisi manual TIDAK disentuh
    assert any(e["type"] == "info" and "Tutup semua" in e["text"] for e in pub.events)


def test_control_endpoint_requires_key(monkeypatch):
    import importlib.util
    import io
    api = Path(__file__).resolve().parent.parent / "cloud" / "api"
    spec = importlib.util.spec_from_file_location("cloud_control", api / "control.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setenv("CONTROL_KEY", "kunci")

    class Req(mod.handler):
        def __init__(self, headers):
            self.headers, self.wfile, self.code = headers, io.BytesIO(), None

        def send_response(self, code, message=None):
            self.code = code

        def send_header(self, *a):
            pass

        def end_headers(self):
            pass

    r = Req({"X-Control-Key": "salah"})
    r.do_GET()
    assert r.code == 401
    r = Req({"X-Control-Key": "salah"})
    r.do_POST()
    assert r.code == 401
