"""Inti bot sinyal cloud (Vercel + Supabase + ntfy) — hanya library standar Python.

Logika trend IDENTIK dengan xau_bot/trend.py (diuji di tests/test_cloud.py):
- BUY  bila close H1 > high tertinggi 55 bar sebelumnya; SELL bila close < low terendah 55 bar.
- SL = entry -/+ 3 x ATR(20); keluar saat close menembus channel 20 bar berlawanan.
"""
from __future__ import annotations

import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CFG = {"entry": 55, "exit": 20, "atr": 20, "stop_atr": 3.0, "bars": 150, "tf_minutes": 60}


@dataclass
class Bar:
    t: datetime  # waktu buka (UTC)
    o: float
    h: float
    l: float  # noqa: E741
    c: float


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def new_topic() -> str:
    return "xau-" + secrets.token_urlsafe(18).replace("-", "a").replace("_", "b")


def http(method: str, url: str, headers: dict | None = None, body=None, timeout: int = 15):
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else None


# ------------------------------------------------------------------ strategi
def atr_last(bars: list[Bar], n: int) -> float:
    trs = []
    for i, b in enumerate(bars):
        prev = bars[i - 1].c if i else b.c
        trs.append(max(b.h - b.l, abs(b.h - prev), abs(b.l - prev)))
    window = trs[-n:]
    return sum(window) / len(window)


def evaluate(closed: list[Bar], position: str | None, cfg: dict = CFG) -> dict:
    """position: 'BUY' | 'SELL' | None. Hanya memakai bar yang SUDAH tertutup."""
    need = max(cfg["entry"], cfg["exit"], cfg["atr"]) + 2
    if len(closed) < need:
        return {"action": "none", "dir": None, "atr": 0.0, "note": "Data belum cukup", "state": "Data belum cukup"}
    a = atr_last(closed, cfg["atr"])
    prev_e = closed[-cfg["entry"] - 1:-1]
    prev_x = closed[-cfg["exit"] - 1:-1]
    hi_e, lo_e = max(b.h for b in prev_e), min(b.l for b in prev_e)
    hi_x, lo_x = max(b.h for b in prev_x), min(b.l for b in prev_x)
    last = closed[-1].c
    state = (f"close {last:.2f} | channel {cfg['entry']}: {lo_e:.2f}-{hi_e:.2f} | "
             f"exit {cfg['exit']}: {lo_x:.2f}-{hi_x:.2f} | ATR {a:.2f}")
    out = {"action": "none", "dir": position, "atr": a, "note": "Tidak ada sinyal", "state": state}
    if position == "BUY" and last < lo_x:
        out.update(action="close", note=f"Close {last:.2f} < low {cfg['exit']} bar {lo_x:.2f}")
    elif position == "SELL" and last > hi_x:
        out.update(action="close", note=f"Close {last:.2f} > high {cfg['exit']} bar {hi_x:.2f}")
    elif position is None and last > hi_e:
        out.update(action="open", dir="BUY", note=f"Breakout H1: close {last:.2f} > high {cfg['entry']} bar {hi_e:.2f}")
    elif position is None and last < lo_e:
        out.update(action="open", dir="SELL", note=f"Breakdown H1: close {last:.2f} < low {cfg['entry']} bar {lo_e:.2f}")
    return out


# ---------------------------------------------------------------- layanan luar
class TwelveData:
    def __init__(self, api_key: str, symbol: str = "XAU/USD"):
        self.api_key, self.symbol = api_key, symbol

    def candles(self, n: int) -> list[Bar]:
        q = urllib.parse.urlencode({"symbol": self.symbol, "interval": "1h", "outputsize": n,
                                    "timezone": "UTC", "order": "ASC", "apikey": self.api_key})
        data = http("GET", "https://api.twelvedata.com/time_series?" + q)
        if not data or data.get("status") != "ok":
            raise RuntimeError(f"Twelve Data: {(data or {}).get('message', 'tidak ada data')}")
        bars = []
        for v in data["values"]:
            t = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            bars.append(Bar(t, float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"])))
        return sorted(bars, key=lambda b: b.t)


class Supabase:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def get_state(self) -> dict:
        rows = http("GET", f"{self.base}/xau_state?id=eq.main&select=data", self.headers) or []
        return rows[0]["data"] if rows else {}

    def save_state(self, data: dict) -> None:
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
        http("POST", f"{self.base}/xau_state", headers,
             {"id": "main", "data": data, "updated_at": iso(datetime.now(timezone.utc))})

    def log(self, kind: str, payload: dict) -> None:
        headers = {**self.headers, "Prefer": "return=minimal"}
        http("POST", f"{self.base}/xau_signals", headers, {"type": kind, "payload": payload})


class Ntfy:
    """Format sama dengan xau_bot/publish.py -> kompatibel dengan APK XAU Signal."""

    def __init__(self, topic: str, server: str = "https://ntfy.sh"):
        self.topic, self.server = topic, server.rstrip("/")

    def publish(self, event: dict, text: str | None = None, title: str = "XAU Signal",
                priority: int = 3, tags: list | None = None) -> None:
        http("POST", self.server + "/", {"Content-Type": "application/json"},
             {"topic": self.topic + "-data", "message": json.dumps(event), "priority": 1})
        if text:
            http("POST", self.server + "/", {"Content-Type": "application/json"},
                 {"topic": self.topic, "message": text, "title": title, "priority": priority,
                  "tags": tags or []})


# ----------------------------------------------------------------------- tick
def tick(now: datetime, prices, store, pub, cfg: dict = CFG, symbol: str = "XAU/USD") -> dict:
    """Satu putaran (dipanggil cron tiap 5-30 menit). Aman dipanggil berulang (idempoten)."""
    tf = timedelta(minutes=cfg["tf_minutes"])
    bars = prices.candles(cfg["bars"])
    if not bars:
        return {"ok": False, "error": "tidak ada candle"}
    closed = [b for b in bars if b.t + tf <= now]
    price = bars[-1].c
    state = store.get_state() or {}
    v = state.get("virtual")
    events: list[str] = []

    def close_virtual(exit_price: float, why: str) -> None:
        nonlocal v
        sign = 1 if v["dir"] == "BUY" else -1
        points = (exit_price - v["entry"]) * sign
        risk = abs(v["entry"] - v["sl"]) or 1.0
        r = points / risk
        ev = {"type": "close", "id": v["id"], "time": iso(now), "mode": "trend", "dir": v["dir"],
              "entry": v["entry"], "price": round(exit_price, 3), "points": round(points, 3),
              "r": round(r, 2), "reason": why}
        text = (f"🏁 TUTUP {v['dir']} {symbol} @ {exit_price:.2f}\n"
                f"Entry {v['entry']:.2f} -> {points:+.2f} poin ({r:+.2f}R)\nAlasan: {why}")
        pub.publish(ev, text, "Sinyal TUTUP posisi", 5, ["checkered_flag"])
        store.log("close", ev)
        events.append(f"TUTUP {v['dir']} {r:+.2f}R")
        v = None

    # 1) SL posisi virtual (dicek terhadap semua bar sejak entry, termasuk bar berjalan)
    if v:
        since = parse_iso(v["bar_close"])
        after = [b for b in bars if b.t >= since]
        if v["dir"] == "BUY" and any(b.l <= v["sl"] for b in after):
            close_virtual(v["sl"], "Stop loss tersentuh")
        elif v["dir"] == "SELL" and any(b.h >= v["sl"] for b in after):
            close_virtual(v["sl"], "Stop loss tersentuh")

    # 2) evaluasi hanya sekali per bar H1 yang baru tertutup
    sig = {"state": "-"}
    if closed and state.get("last_bar") != iso(closed[-1].t):
        state["last_bar"] = iso(closed[-1].t)
        sig = evaluate(closed, v["dir"] if v else None, cfg)
        if sig["action"] == "close" and v:
            close_virtual(price, sig["note"])
        elif sig["action"] == "open" and v is None:
            d = sig["dir"]
            sign = 1 if d == "BUY" else -1
            sl = price - sign * cfg["stop_atr"] * sig["atr"]
            key = f"TREND-{d}-{closed[-1].t:%Y%m%d%H%M}"
            ev = {"type": "signal", "id": key, "time": iso(now), "mode": "trend", "dir": d,
                  "symbol": symbol, "entry": round(price, 3), "sl": round(sl, 3), "tp": None,
                  "atr": round(sig["atr"], 3), "timeframe": "H1", "status": "signal",
                  "exit_rule": f"close H1 menembus channel {cfg['exit']} bar", "reason": sig["note"],
                  "lot": None, "warning": "Harga dari data feed; cek harga broker sebelum entry."}
            text = (f"{'🟢' if d == 'BUY' else '🔴'} TREND {d} {symbol} (H1 Donchian {cfg['entry']}/{cfg['exit']})\n"
                    f"Entry: {price:.2f} (market) | SL: {sl:.2f} ({cfg['stop_atr']}x ATR {sig['atr']:.2f})\n"
                    f"TP: tidak ada - tunggu sinyal TUTUP\nAlasan: {sig['note']}")
            pub.publish(ev, text, f"{d} XAUUSD", 5, ["green_circle" if d == "BUY" else "red_circle"])
            store.log("signal", ev)
            events.append(f"SINYAL {d} @ {price:.2f}")
            v = {"id": key, "dir": d, "entry": price, "sl": sl, "bar_close": iso(closed[-1].t + tf)}
        state["trend"] = sig["state"]

    state["virtual"] = v
    state["last_tick"] = iso(now)
    state["price"] = price
    store.save_state(state)
    pub.publish({"type": "heartbeat", "time": iso(now), "symbol": symbol, "price": price,
                 "mode": "SINYAL (cloud)", "trend": state.get("trend", "-"), "session": "cloud",
                 "block": "", "news": "-", "currency": "", "positions": []})
    return {"ok": True, "price": price, "last_closed_bar": state.get("last_bar"),
            "virtual": v, "events": events, "trend": state.get("trend")}
