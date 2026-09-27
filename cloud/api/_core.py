"""Inti bot sinyal cloud (Vercel + Supabase + ntfy) — hanya library standar Python.

Skema F-ensemble, IDENTIK dengan bot (xau_bot/trend.py + trend_ensemble.py; diuji di tests/test_cloud.py):
- 3 set Donchian H1 (40/15, 55/20, 80/30). BUY bila close > high N bar sebelumnya, SELL kebalikannya.
- SL = entry -/+ 3 x ATR(20). Tiap sinyal = 5 posisi: posisi #1 TP1 = 1R, sisanya hold.
- TP1 kena -> SL posisi sisa ke entry (SL+). TUTUP saat close menembus channel exit.
- Filter SMC (default ON): breakout hanya diambil bila searah bias struktur H4 (BOS terakhir), tidak
  entry saat akhir pekan / Jumat sore / pembukaan Minggu / rollover (sama dengan xau_bot/sessions.py).
Pengaman auto order: spread & harga broker dicek, SL/TP dihitung dari harga broker, batas rugi
harian/mingguan dari equity akun (order baru dihentikan, posisi berjalan tetap dikelola).
"""
from __future__ import annotations

import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CFG = {"entry": 55, "exit": 20, "atr": 20, "stop_atr": 3.0, "bars": 1300, "tf_minutes": 60,
       "sets": [(40, 15), (55, 20), (80, 30)], "legs": 5, "tp1_r": 1.0, "be_offset": 0.10,
       "leg_lot": 0.01,
       # filter SMC tervalidasi (research/trend_filters.py): bias struktur H4, swing 3, 300 bar H4
       "bias_filter": True, "bias_hours": 4, "bias_swing": 3, "bias_bars": 300,
       # pengaman auto order
       "daily_loss_pct": 3.0, "weekly_loss_pct": 6.0, "max_spread": 0.50}
BIAS_NAMES = {1: "BULLISH", -1: "BEARISH", 0: "NETRAL"}


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


def swing_flags(vals: list[float], length: int, high: bool) -> list[bool]:
    """Sama dengan xau_bot.smc.swing_mask: lebih ekstrem dari `length` bar kiri (strict) & kanan (>=)."""
    n = len(vals)
    out = [False] * n
    for i in range(length, n - length):
        left, right = vals[i - length:i], vals[i + 1:i + length + 1]
        out[i] = (vals[i] > max(left) and vals[i] >= max(right)) if high else (
            vals[i] < min(left) and vals[i] <= min(right))
    return out


def structure_bias(bars: list[Bar], length: int = 3) -> int:
    """Sama dengan xau_bot.smc.structure_bias: +1 BOS terakhir ke atas, -1 ke bawah, 0 belum jelas."""
    if len(bars) < 2 * length + 2:
        return 0
    hs, ls, cs = [b.h for b in bars], [b.l for b in bars], [b.c for b in bars]
    hm, lm = swing_flags(hs, length, True), swing_flags(ls, length, False)
    state, last_h, last_l = 0, None, None
    for i in range(len(bars)):
        k = i - length
        if k >= 0:
            if hm[k]:
                last_h = hs[k]
            if lm[k]:
                last_l = ls[k]
        if last_h is not None and cs[i] > last_h:
            state, last_h = 1, None
        elif last_l is not None and cs[i] < last_l:
            state, last_l = -1, None
    return state


def htf_bars(closed: list[Bar], now: datetime, hours: int = 4) -> list[Bar]:
    """Gabungkan bar H1 tertutup jadi bar H4 (00/04/08.. UTC, sama dengan MT5 Exness & pandas resample);
    hanya bar H4 yang sudah tertutup."""
    out: list[Bar] = []
    for b in closed:
        start = b.t.replace(hour=b.t.hour - b.t.hour % hours, minute=0, second=0, microsecond=0)
        if start + timedelta(hours=hours) > now:
            break
        if out and out[-1].t == start:
            last = out[-1]
            out[-1] = Bar(start, last.o, max(last.h, b.h), min(last.l, b.l), b.c)
        else:
            out.append(Bar(start, b.o, b.h, b.l, b.c))
    return out


def ny_time(t: datetime) -> datetime:
    """UTC -> jam New York (aturan DST AS) tanpa database zona waktu."""
    t = t.astimezone(timezone.utc)
    mar1, nov1 = datetime(t.year, 3, 1, tzinfo=timezone.utc), datetime(t.year, 11, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7, hours=7)   # Minggu ke-2 Maret 02:00 NY
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=6)          # Minggu ke-1 Nov 02:00 NY
    return (t + timedelta(hours=-4 if dst_start <= t < dst_end else -5)).replace(tzinfo=None)


def trading_day(t: datetime) -> str:
    """Hari trading forex (mulai 17:00 New York), sama dengan xau_bot.sessions.trading_day."""
    return (ny_time(t) + timedelta(hours=7)).date().isoformat()


def entry_block_reason(t: datetime) -> str | None:
    """Sama dengan xau_bot.sessions.SessionClock.entry_block_reason (konfigurasi default)."""
    ny = ny_time(t)
    wd, m = ny.weekday(), ny.hour * 60 + ny.minute
    if wd == 5 or (wd == 4 and m >= 17 * 60):
        return "Pasar tutup (akhir pekan)"
    if wd == 6 and m < 18 * 60:
        return "Pembukaan pasar Minggu (gap/spread)"
    if wd == 4 and m >= 15 * 60:
        return "Jumat sore (tidak entry baru)"
    if 16 * 60 + 30 <= m < 17 * 60 + 30:
        return "Rollover harian (spread lebar)"
    return None


def loss_guard(guard: dict, acc: dict, now: datetime, daily_pct: float, weekly_pct: float) -> dict:
    """Batas rugi harian/mingguan dari equity akun (saldo dicatat di tick pertama hari/minggu trading).
    Return guard baru; guard['blocked'] berisi alasan bila order baru harus dihentikan."""
    guard = dict(guard or {})
    bal, eq = acc.get("balance"), acc.get("equity")
    if bal is None or eq is None:
        guard["blocked"] = ""
        return guard
    day = trading_day(now)
    y, w, _ = datetime.fromisoformat(day).isocalendar()
    week = f"{y}-W{w:02d}"
    if guard.get("day") != day:
        guard.update(day=day, day_balance=bal)
    if guard.get("week") != week:
        guard.update(week=week, week_balance=bal)
    blocked = ""
    if daily_pct and eq <= guard["day_balance"] * (1 - daily_pct / 100):
        blocked = f"Batas rugi harian {daily_pct:g}% tercapai (equity {eq:.2f} dari {guard['day_balance']:.2f})"
    elif weekly_pct and eq <= guard["week_balance"] * (1 - weekly_pct / 100):
        blocked = f"Batas rugi mingguan {weekly_pct:g}% tercapai (equity {eq:.2f} dari {guard['week_balance']:.2f})"
    guard["blocked"] = blocked
    return guard


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

    def get_state(self, row: str = "main") -> dict:
        rows = http("GET", f"{self.base}/xau_state?id=eq.{row}&select=data", self.headers) or []
        return rows[0]["data"] if rows else {}

    def save_state(self, data: dict, row: str = "main") -> None:
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
        http("POST", f"{self.base}/xau_state", headers,
             {"id": row, "data": data, "updated_at": iso(datetime.now(timezone.utc))})

    def get_control(self) -> dict:
        return self.get_state("control")

    def save_control(self, data: dict) -> None:
        self.save_state(data, "control")

    def log(self, kind: str, payload: dict) -> None:
        headers = {**self.headers, "Prefer": "return=minimal"}
        http("POST", f"{self.base}/xau_signals", headers, {"type": kind, "payload": payload})


OK_CODES = {"ERR_NO_ERROR", "TRADE_RETCODE_PLACED", "TRADE_RETCODE_DONE", "TRADE_RETCODE_DONE_PARTIAL",
            "TRADE_RETCODE_NO_CHANGES"}
BASE_MAGIC = 250936  # sama dengan bot desktop: 250925 + 1 + 10 + index set


def ours(p: dict) -> bool:
    """Hanya posisi milik bot ini; posisi manual / EA lain tidak pernah disentuh."""
    return BASE_MAGIC <= int(p.get("magic") or 0) < BASE_MAGIC + 10


class MetaApi:
    """Eksekusi order ke akun MT5 lewat MetaApi REST (https://metaapi.cloud) — tanpa PC."""

    def __init__(self, token: str, account_id: str, region: str = "new-york", symbol: str = "XAUUSDc"):
        self.base = f"https://mt-client-api-v1.{region}.agiliumtrade.ai/users/current/accounts/{account_id}"
        self.headers = {"auth-token": token, "Content-Type": "application/json"}
        self.symbol = symbol

    def account(self) -> dict:
        return http("GET", self.base + "/account-information", self.headers) or {}

    def price(self) -> dict:
        """Harga broker saat ini: {'bid': .., 'ask': ..}."""
        sym = urllib.parse.quote(self.symbol, safe="")
        return http("GET", f"{self.base}/symbols/{sym}/current-price", self.headers) or {}

    def positions(self, magic: int | None = None) -> list[dict]:
        out = http("GET", self.base + "/positions", self.headers) or []
        return [p for p in out if p.get("symbol") == self.symbol and (magic is None or p.get("magic") == magic)]

    def _trade(self, body: dict) -> dict:
        try:
            res = http("POST", self.base + "/trade", self.headers, body) or {}
        except Exception as exc:  # noqa: BLE001 - HTTP/jaringan
            return {"ok": False, "message": str(exc)}
        code = res.get("stringCode") or res.get("description") or ""
        return {**res, "ok": code in OK_CODES}

    def market(self, direction: str, volume: float, sl: float, tp: float | None, magic: int,
               comment: str, client_id: str) -> dict:
        body = {"actionType": "ORDER_TYPE_BUY" if direction == "BUY" else "ORDER_TYPE_SELL",
                "symbol": self.symbol, "volume": volume, "stopLoss": round(sl, 2),
                "comment": comment[:12], "clientId": client_id[:12], "magic": magic}
        if tp:
            body["takeProfit"] = round(tp, 2)
        return self._trade(body)

    def modify(self, position_id: str, sl: float, tp: float | None) -> dict:
        body = {"actionType": "POSITION_MODIFY", "positionId": str(position_id), "stopLoss": round(sl, 2)}
        if tp:
            body["takeProfit"] = round(tp, 2)
        return self._trade(body)

    def close(self, position_id: str) -> dict:
        return self._trade({"actionType": "POSITION_CLOSE_ID", "positionId": str(position_id)})


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
def tick(now: datetime, prices, store, pub, cfg: dict = CFG, symbol: str = "XAU/USD",
         executor: "MetaApi | None" = None) -> dict:
    """Satu putaran (dipanggil cron tiap 5-30 menit). Aman dipanggil berulang (idempoten).

    Bila `executor` (MetaApi) ada dan kontrol auto = ON (diatur dari aplikasi), order sungguhan
    dibuka/dikelola/ditutup mengikuti sinyal yang sama. Default auto = OFF.
    """
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
    control = (store.get_control() if hasattr(store, "get_control") else {}) or {}
    live = executor is not None and bool(control.get("auto")) and not control.get("paused")
    legs_n = max(1, min(int(control.get("legs") or cfg["legs"]), 10))
    leg_lot = min(float(control.get("leg_lot") or cfg["leg_lot"]), float(cfg.get("max_leg_lot", 0.10)))
    lot_text = f"{legs_n} x {leg_lot}"
    bias_on = bool(control.get("bias_filter", cfg.get("bias_filter", True)))
    bias = structure_bias(htf_bars(closed, now, cfg.get("bias_hours", 4))[-cfg.get("bias_bars", 300):],
                          cfg.get("bias_swing", 3))
    state["bias"] = bias
    acc, acc_error = None, ""
    if executor is not None:
        try:
            acc = executor.account() or {}
            state["guard"] = loss_guard(state.get("guard") or {}, acc, now,
                                        float(control.get("daily_loss_pct", cfg.get("daily_loss_pct", 3.0))),
                                        float(control.get("weekly_loss_pct", cfg.get("weekly_loss_pct", 6.0))))
        except Exception as exc:  # noqa: BLE001
            acc, acc_error = None, str(exc)
            events.append(f"MetaApi error: {exc}")
    guard_block = (state.get("guard") or {}).get("blocked", "")

    def live_close_all(name: str, magic: int, why: str) -> None:
        for p in executor.positions(magic):
            res = executor.close(p["id"])
            events.append(f"{name} LIVE tutup #{p['id']} {'ok' if res['ok'] else 'GAGAL: ' + str(res.get('message'))}")
        store.log("live_close", {"set": name, "reason": why})

    def live_positions(magic: int) -> list | None:
        """None = MetaApi tidak bisa dihubungi (sinyal tetap jalan, order tidak dikirim)."""
        if executor is None:
            return []
        try:
            return executor.positions(magic)
        except Exception as exc:  # noqa: BLE001
            events.append(f"MetaApi error: {exc}")
            return None

    def live_sync(name: str, magic: int, v: dict | None) -> dict | None:
        """Samakan posisi sungguhan dengan posisi virtual: SL+ dan penutupan.
        Tetap berjalan walau auto OFF/dijeda supaya posisi yang sudah terbuka tetap dikelola."""
        if executor is None:
            return v
        ps = live_positions(magic)
        if not ps:
            return v
        if v is None:
            live_close_all(name, magic, "sinyal TUTUP / SL")
            return v
        need_be = v.get("be_done") or (v.get("live_legs", 0) >= 2 and len(ps) < v.get("live_legs", 0))
        if need_be and not v.get("live_be"):
            sign = 1 if v["dir"] == "BUY" else -1
            ok = True
            for p in ps:
                be = float(p.get("openPrice") or v["entry"]) + sign * cfg["be_offset"]  # harga isi asli
                cur = p.get("stopLoss") or 0.0
                better = (be > cur) if v["dir"] == "BUY" else (cur == 0 or be < cur)
                if better:
                    ok = executor.modify(p["id"], be, p.get("takeProfit"))["ok"] and ok
            if ok:
                v["live_be"] = True
                events.append(f"{name} LIVE SL+ {len(ps)} posisi")
        return v

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

    def open_signal(name, idx, magic, entry_p, s, d, sign, risk, sl, tp1, key, ev, text) -> dict:
        """Sinyal lolos filter: kirim ke aplikasi, buat posisi virtual, lalu (bila auto ON) order sungguhan."""
        s.pop("last_skip", None)
        if bias_on:
            text += f"\nFilter SMC: bias struktur H4 {BIAS_NAMES[bias]} searah"
        pub.publish(ev, text, f"{d} XAUUSD", 5, ["green_circle" if d == "BUY" else "red_circle"])
        store.log("signal", ev)
        events.append(f"{name} SINYAL {d} @ {price:.2f}")
        v = {"id": key, "dir": d, "entry": price, "sl": sl, "risk": risk, "tp1": tp1,
             "legs": legs_n, "be_done": False, "tp1_hit": False,
             "bar_close": iso(closed[-1].t + tf)}
        existing = live_positions(magic) if live else []
        why = ""
        if live and existing != []:
            why = "MetaApi tidak bisa dihubungi" if existing is None else f"masih ada {len(existing)} posisi lama"
        elif live and guard_block:
            why = guard_block
        l_sl, l_tp1 = sl, tp1
        if live and not why:
            # SL/TP dari harga broker (bukan feed) + cek spread & selisih harga
            try:
                q = executor.price()
                bid, ask = float(q["bid"]), float(q["ask"])
            except Exception as exc:  # noqa: BLE001 - harga broker gagal -> pakai harga feed
                bid = ask = None
                events.append(f"{name} harga broker tidak tersedia ({exc}), SL dari harga feed")
            if bid is not None:
                fill = ask if d == "BUY" else bid
                max_spread = float(control.get("max_spread", cfg.get("max_spread", 0.50)))
                if ask - bid > max_spread:
                    why = f"spread broker {ask - bid:.2f} > {max_spread:.2f}"
                elif abs(fill - price) > 0.5 * risk:
                    why = f"harga broker {fill:.2f} beda jauh dari feed {price:.2f}"
                else:
                    l_sl, l_tp1 = fill - sign * risk, fill + sign * cfg["tp1_r"] * risk
        if live and why:
            info = f"⚠️ Auto order {name} dilewati: {why}. Sinyal tetap berlaku (manual)."
            pub.publish({"type": "info", "time": iso(now), "set": name, "id": key, "text": info},
                        info, "Auto order", 4, ["warning"])
            events.append(info)
        elif live:
            # simpan dulu SEBELUM kirim order -> tidak mungkin dobel walau fungsi terputus
            s["virtual"] = v
            systems[name] = s
            state["systems"] = systems
            store.save_state(state)
            opened = 0
            for i in range(legs_n):
                res = executor.market(d, leg_lot, l_sl, l_tp1 if (i == 0 and legs_n >= 2) else None, magic,
                                      f"F{entry_p}L{i + 1}", f"{closed[-1].t:%m%d%H}{idx}{i}")
                if not res["ok"]:
                    events.append(f"{name} LIVE leg {i + 1} GAGAL: {res.get('message') or res.get('stringCode')}")
                    break
                opened += 1
            v["live_legs"] = opened
            info = f"🤖 Auto order {name}: {opened}/{legs_n} posisi {d} {leg_lot} lot terbuka"
            pub.publish({"type": "info", "time": iso(now), "set": name, "id": key, "text": info},
                        info, "Auto order", 4, ["robot"])
            store.log("live_open", {"id": key, "opened": opened, "lot": leg_lot})
            events.append(info)
        return v

    trends = []
    for idx, (entry_p, exit_p) in enumerate(cfg["sets"]):
        name = f"T{entry_p}/{exit_p}"
        magic = BASE_MAGIC + idx
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
                      "legs": legs_n, "lot": lot_text, "timeframe": "H1", "status": "signal",
                      "exit_rule": f"close H1 menembus channel {exit_p} bar", "reason": sig["note"],
                      "warning": "Harga dari data feed; cek harga broker sebelum entry."}
                text = (f"{'🟢' if d == 'BUY' else '🔴'} TREND {d} {symbol} [{name}] skema F\n"
                        f"Entry: {price:.2f} | SL: {sl:.2f} ({cfg['stop_atr']}x ATR {sig['atr']:.2f})\n"
                        f"Lot: {lot_text} -> posisi #1 TP1 {tp1:.2f} ({cfg['tp1_r']}R), sisanya hold\n"
                        f"TP1 kena -> SL sisa ke entry (SL+). Tunggu sinyal TUTUP.\nAlasan: {sig['note']}")
                block = entry_block_reason(now)
                if block is None and bias_on and bias != sign:
                    block = f"Bias struktur H4 {BIAS_NAMES[bias]} tidak searah {d} (filter SMC)"
                if block is not None:
                    if s.get("last_skip") != f"{d}|{block}":   # satu pemberitahuan per alasan
                        s["last_skip"] = f"{d}|{block}"
                        pub.publish({**ev, "status": "skipped", "note": block}, f"{text}\n⛔ Dilewati: {block}",
                                    "Sinyal dilewati", 2)
                        store.log("skip", {"id": key, "set": name, "reason": block})
                        events.append(f"{name} {d} dilewati: {block}")
                else:
                    v = open_signal(name, idx, magic, entry_p, s, d, sign, risk, sl, tp1, key, ev, text)
            s["trend"] = sig["state"]
        try:
            v = live_sync(name, magic, v)
        except Exception as exc:  # noqa: BLE001 - kegagalan MetaApi tidak boleh menghentikan sinyal
            events.append(f"{name} LIVE sync error: {exc}")
        s["virtual"] = v
        systems[name] = s
        trends.append(f"{name}: {s.get('trend', '-')}")

    state["systems"] = systems
    state["last_tick"] = iso(now)
    state["price"] = price
    store.save_state(state)
    trend_text = " | ".join(trends)
    if bias_on:
        trend_text = f"Bias H4: {BIAS_NAMES[bias]} | {trend_text}"
    mode = "AUTO (cloud)" if live else ("SINYAL (auto dijeda)" if control.get("auto") else "SINYAL (cloud)")
    hb = {"type": "heartbeat", "time": iso(now), "symbol": symbol, "price": price, "mode": mode,
          "trend": trend_text, "session": "cloud", "block": entry_block_reason(now) or "", "news": "-",
          "currency": "", "positions": []}
    if executor is not None:
        if acc is None:
            hb["block"] = f"MetaApi: {acc_error}"
        else:
            hb.update(balance=acc.get("balance"), equity=acc.get("equity"), currency=acc.get("currency", ""))
            if guard_block and live:
                hb["block"] = guard_block
            try:
                hb["positions"] = [{"ticket": p["id"], "dir": "BUY" if p.get("type") == "POSITION_TYPE_BUY" else "SELL",
                                    "volume": p.get("volume"), "open": p.get("openPrice"), "sl": p.get("stopLoss"),
                                    "tp": p.get("takeProfit"), "profit": p.get("profit")}
                                   for p in executor.positions() if ours(p)]
            except Exception as exc:  # noqa: BLE001
                hb["block"] = f"MetaApi: {exc}"
    pub.publish(hb)
    return {"ok": True, "price": price, "auto": live, "last_closed_bar": iso(closed[-1].t) if closed else None,
            "open": {k: v["virtual"] for k, v in systems.items() if v.get("virtual")},
            "events": events, "trend": trend_text}


# ------------------------------------------------------------------ kontrol
def apply_control(store, executor, pub, changes: dict, max_leg_lot: float = 0.10, cfg: dict = CFG) -> dict:
    """Ubah pengaturan auto-order dari aplikasi. Return status terbaru."""
    control = dict(store.get_control() or {})
    notes = []
    if "auto" in changes:
        control["auto"] = bool(changes["auto"])
        notes.append("Auto order " + ("ON" if control["auto"] else "OFF"))
    if "paused" in changes:
        control["paused"] = bool(changes["paused"])
        notes.append("Dijeda" if control["paused"] else "Dilanjutkan")
    if "leg_lot" in changes:
        lot = round(float(changes["leg_lot"]), 2)
        if not 0.01 <= lot <= max_leg_lot:
            raise ValueError(f"Lot per posisi harus 0.01 - {max_leg_lot}")
        control["leg_lot"] = lot
        notes.append(f"Lot {lot}")
    if "legs" in changes:
        legs = int(changes["legs"])
        if not 1 <= legs <= 10:
            raise ValueError("Jumlah posisi harus 1 - 10")
        control["legs"] = legs
        notes.append(f"{legs} posisi")
    if "bias_filter" in changes:
        control["bias_filter"] = bool(changes["bias_filter"])
        notes.append("Filter bias H4 " + ("ON" if control["bias_filter"] else "OFF"))
    for key, label in (("daily_loss_pct", "harian"), ("weekly_loss_pct", "mingguan")):
        if key in changes:
            pct = round(float(changes[key]), 1)
            if not 0.5 <= pct <= 50:
                raise ValueError(f"Batas rugi {label} harus 0.5 - 50%")
            control[key] = pct
            notes.append(f"Batas rugi {label} {pct:g}%")
    closed = 0
    if changes.get("close_all"):
        if executor is None:
            raise ValueError("MetaApi belum dikonfigurasi")
        for p in executor.positions():
            if ours(p) and executor.close(p["id"])["ok"]:
                closed += 1
        control["paused"] = True
        notes.append(f"Tutup semua ({closed} posisi) + dijeda")
    control["updated"] = iso(datetime.now(timezone.utc))
    store.save_control(control)
    if notes:
        text = "⚙️ " + ", ".join(notes) + " (dari aplikasi)"
        pub.publish({"type": "info", "time": control["updated"], "text": text}, text, "Kontrol auto order", 3,
                    ["gear"])
    return status(store, executor, control, cfg)


def status(store, executor, control: dict | None = None, cfg: dict = CFG) -> dict:
    control = control if control is not None else (store.get_control() or {})
    state = store.get_state() or {}
    out = {"ok": True, "control": {"auto": bool(control.get("auto")), "paused": bool(control.get("paused")),
                                   "leg_lot": control.get("leg_lot", cfg["leg_lot"]),
                                   "legs": control.get("legs", cfg["legs"]),
                                   "bias_filter": bool(control.get("bias_filter", cfg.get("bias_filter", True))),
                                   "daily_loss_pct": control.get("daily_loss_pct", cfg.get("daily_loss_pct", 3.0)),
                                   "weekly_loss_pct": control.get("weekly_loss_pct", cfg.get("weekly_loss_pct", 6.0))},
           "executor": executor is not None,
           "bias": BIAS_NAMES.get(state.get("bias", 0), "NETRAL"),
           "guard": (state.get("guard") or {}).get("blocked", ""),
           "session_block": entry_block_reason(datetime.now(timezone.utc)) or ""}
    if executor is not None:
        try:
            acc = executor.account()
            out["account"] = {k: acc.get(k) for k in ("balance", "equity", "currency", "broker", "login")}
            out["positions"] = [{"id": p["id"], "dir": "BUY" if p.get("type") == "POSITION_TYPE_BUY" else "SELL",
                                 "volume": p.get("volume"), "open": p.get("openPrice"), "sl": p.get("stopLoss"),
                                 "tp": p.get("takeProfit"), "profit": p.get("profit"), "magic": p.get("magic")}
                                for p in executor.positions() if ours(p)]
        except Exception as exc:  # noqa: BLE001
            out["error"] = f"MetaApi: {exc}"
    return out
