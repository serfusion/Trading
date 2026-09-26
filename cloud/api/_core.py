"""Inti bot sinyal cloud (Vercel + Supabase + ntfy) — hanya library standar Python.

Skema F-ensemble, IDENTIK dengan bot (xau_bot/trend.py + trend_ensemble.py; diuji di tests/test_cloud.py):
- 3 set Donchian H1 (40/15, 55/20, 80/30). BUY bila close > high N bar sebelumnya, SELL kebalikannya.
- SL = entry -/+ 3 x ATR(20). Tiap sinyal = 5 posisi: posisi #1 TP1 = 1R, sisanya hold.
- TP1 kena -> SL posisi sisa ke entry (SL+). TUTUP saat close menembus channel exit.
"""
from __future__ import annotations

import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CFG = {"entry": 55, "exit": 20, "atr": 20, "stop_atr": 3.0, "bars": 150, "tf_minutes": 60,
       "sets": [(40, 15), (55, 20), (80, 30)], "legs": 5, "tp1_r": 1.0, "be_offset": 0.10,
       "leg_lot": 0.01}


def f_result(legs: int, entry: float, risk: float, sign: int, tp1_hit: bool, exit_price: float,
             tp1_r: float) -> float:
    """R rata-rata per posisi untuk skema F (sama dengan xau_bot/trend_ensemble.f_result)."""
    exit_r = (exit_price - entry) * sign / risk if risk else 0.0
    if legs >= 2 and tp1_hit:
        return (tp1_r + (legs - 1) * exit_r) / legs
    return exit_r


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
    state.pop("virtual", None)  # format lama (1 set)
    systems = state.get("systems") or {}
    events: list[str] = []
    lot_text = f"{cfg['legs']} x {cfg['leg_lot']}"

    def close_virtual(name: str, v: dict, exit_price: float, why: str) -> None:
        sign = 1 if v["dir"] == "BUY" else -1
        points = (exit_price - v["entry"]) * sign
        r = f_result(v["legs"], v["entry"], v["risk"], sign, v.get("tp1_hit", False), exit_price, cfg["tp1_r"])
        ev = {"type": "close", "id": v["id"], "time": iso(now), "mode": "trend", "set": name,
              "dir": v["dir"], "entry": round(v["entry"], 3), "price": round(exit_price, 3),
              "points": round(points, 3), "r": round(r, 3), "risk_points": round(v["risk"], 3),
              "legs": v["legs"], "tp1_hit": v.get("tp1_hit", False), "reason": why}
        text = (f"🏁 TUTUP {v['dir']} {symbol} [{name}] @ {exit_price:.2f}\n"
                f"Entry {v['entry']:.2f} -> {points:+.2f} poin | hasil skema F {r:+.2f}R\nAlasan: {why}")
        pub.publish(ev, text, "Sinyal TUTUP posisi", 5, ["checkered_flag"])
        store.log("close", ev)
        events.append(f"{name} TUTUP {v['dir']} {r:+.2f}R")

    def manage(name: str, v: dict | None) -> dict | None:
        """Cek SL / TP1 / SL+ secara berurutan per bar sejak entry (konservatif: SL dulu)."""
        if not v:
            return None
        buy = v["dir"] == "BUY"
        if not v.get("be_done"):
            for b in (b for b in bars if b.t >= parse_iso(v["bar_close"])):
                if (b.l <= v["sl"]) if buy else (b.h >= v["sl"]):
                    close_virtual(name, v, v["sl"], "Stop loss tersentuh")
                    return None
                if (b.h >= v["tp1"]) if buy else (b.l <= v["tp1"]):
                    v.update(be_done=True, tp1_hit=True, be_bar=iso(b.t),
                             sl=v["entry"] + (1 if buy else -1) * cfg["be_offset"])
                    text = (f"🎯 [{name}] TP1 {v['tp1']:.2f} kena ({v['dir']})\n"
                            f"➡️ Tutup posisi #1, pindahkan SL posisi lain ke {v['sl']:.2f} (SL+)")
                    pub.publish({"type": "info", "time": iso(now), "set": name, "id": v["id"], "text": text},
                                text, "TP1 + SL+", 5, ["dart"])
                    store.log("tp1", {"id": v["id"], "set": name, "sl": v["sl"]})
                    events.append(f"{name} TP1 -> SL+")
                    break
        if v.get("be_done"):
            for b in (b for b in bars if b.t > parse_iso(v["be_bar"])):
                if (b.l <= v["sl"]) if buy else (b.h >= v["sl"]):
                    close_virtual(name, v, v["sl"], "SL+ (break-even) tersentuh")
                    return None
        return v

    trends = []
    for entry_p, exit_p in cfg["sets"]:
        name = f"T{entry_p}/{exit_p}"
        sc = {**cfg, "entry": entry_p, "exit": exit_p}
        s = dict(systems.get(name) or {})
        v = manage(name, s.get("virtual"))
        if closed and s.get("last_bar") != iso(closed[-1].t):
            s["last_bar"] = iso(closed[-1].t)
            sig = evaluate(closed, v["dir"] if v else None, sc)
            if sig["action"] == "close" and v:
                close_virtual(name, v, price, sig["note"])
                v = None
            elif sig["action"] == "open" and v is None:
                d = sig["dir"]
                sign = 1 if d == "BUY" else -1
                risk = cfg["stop_atr"] * sig["atr"]
                sl = price - sign * risk
                tp1 = price + sign * cfg["tp1_r"] * risk
                key = f"{name}-{d}-{closed[-1].t:%Y%m%d%H%M}"
                ev = {"type": "signal", "id": key, "time": iso(now), "mode": "trend", "set": name, "dir": d,
                      "symbol": symbol, "entry": round(price, 3), "sl": round(sl, 3), "tp": round(tp1, 3),
                      "tp1": round(tp1, 3), "atr": round(sig["atr"], 3), "risk_points": round(risk, 3),
                      "legs": cfg["legs"], "lot": lot_text, "timeframe": "H1", "status": "signal",
                      "exit_rule": f"close H1 menembus channel {exit_p} bar", "reason": sig["note"],
                      "warning": "Harga dari data feed; cek harga broker sebelum entry."}
                text = (f"{'🟢' if d == 'BUY' else '🔴'} TREND {d} {symbol} [{name}] skema F\n"
                        f"Entry: {price:.2f} | SL: {sl:.2f} ({cfg['stop_atr']}x ATR {sig['atr']:.2f})\n"
                        f"Lot: {lot_text} -> posisi #1 TP1 {tp1:.2f} ({cfg['tp1_r']}R), sisanya hold\n"
                        f"TP1 kena -> SL sisa ke entry (SL+). Tunggu sinyal TUTUP.\nAlasan: {sig['note']}")
                pub.publish(ev, text, f"{d} XAUUSD", 5, ["green_circle" if d == "BUY" else "red_circle"])
                store.log("signal", ev)
                events.append(f"{name} SINYAL {d} @ {price:.2f}")
                v = {"id": key, "dir": d, "entry": price, "sl": sl, "risk": risk, "tp1": tp1,
                     "legs": cfg["legs"], "be_done": False, "tp1_hit": False,
                     "bar_close": iso(closed[-1].t + tf)}
            s["trend"] = sig["state"]
        s["virtual"] = v
        systems[name] = s
        trends.append(f"{name}: {s.get('trend', '-')}")

    state["systems"] = systems
    state["last_tick"] = iso(now)
    state["price"] = price
    store.save_state(state)
    trend_text = " | ".join(trends)
    pub.publish({"type": "heartbeat", "time": iso(now), "symbol": symbol, "price": price,
                 "mode": "SINYAL (cloud)", "trend": trend_text, "session": "cloud",
                 "block": "", "news": "-", "currency": "", "positions": []})
    return {"ok": True, "price": price, "last_closed_bar": iso(closed[-1].t) if closed else None,
            "open": {k: v["virtual"] for k, v in systems.items() if v.get("virtual")},
            "events": events, "trend": trend_text}
