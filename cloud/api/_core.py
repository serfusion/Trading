"""Inti bot sinyal cloud (Vercel + Supabase + ntfy) — hanya library standar Python.

Skema F-ensemble, IDENTIK dengan bot (xau_bot/trend.py + trend_ensemble.py; diuji di tests/test_cloud.py):
- 3 set Donchian H1 (40/15, 55/20, 80/30). BUY bila close > high N bar sebelumnya, SELL kebalikannya.
- SL = entry -/+ 3 x ATR(20). Tiap sinyal = 5 posisi: posisi #1 TP1 = 1R, sisanya hold.
- TP1 kena -> SL posisi sisa ke entry (SL+). TUTUP saat close menembus channel exit.
- ⭐: setiap sinyal diberi tanda star=True bila searah tren D1 (close D1 kemarin vs EMA50 D1) DAN
  close H1 menembus high/low 20 candle H4 sebelumnya (research/filters.py, "tren D1 + H4 breakout").
  star_only=True -> sinyal non-⭐ tidak dikirim sama sekali (default: semua dikirim, ⭐ ditandai).
"""
from __future__ import annotations

import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CFG = {"entry": 55, "exit": 20, "atr": 20, "stop_atr": 3.0, "bars": 3000, "tf_minutes": 60,
       "sets": [(40, 15), (55, 20), (80, 30)], "legs": 5, "tp1_r": 1.0, "be_offset": 0.10,
       "leg_lot": 0.01, "star_only": False, "star_ema": 50, "star_h4": 20,
       "market_hours": True, "skip_open_bars": 3}


def new_york(t: datetime) -> datetime:
    """Waktu New York tanpa database zona waktu (aturan DST AS sejak 2007): EDT (UTC-4) dari Minggu kedua
    Maret 02:00 sampai Minggu pertama November 02:00 waktu lokal, selain itu EST (UTC-5)."""
    t = t.astimezone(timezone.utc)
    mar = datetime(t.year, 3, 8, 7, tzinfo=timezone.utc)            # 02:00 EST = 07:00 UTC
    start = mar + timedelta(days=(6 - mar.weekday()) % 7)           # Minggu kedua Maret
    nov = datetime(t.year, 11, 1, 6, tzinfo=timezone.utc)           # 02:00 EDT = 06:00 UTC
    end = nov + timedelta(days=(6 - nov.weekday()) % 7)             # Minggu pertama November
    offset = 4 if start <= t < end else 5
    return (t - timedelta(hours=offset)).replace(tzinfo=None)


def market_open(t: datetime) -> bool:
    """Candle H1 (waktu buka, UTC) jatuh di jam pasar emas: Minggu 18:00 – Jumat 17:00 New York,
    tanpa jeda harian 17:00–18:00. Feed kadang tetap mengirim candle datar saat pasar tutup; candle itu
    membuat ATR & channel palsu (sinyal Minggu 27 Sep 2026 22:02 UTC dengan SL hanya $1,23)."""
    ny = new_york(t)
    return not weekend_closed(t) and not (ny.weekday() <= 3 and ny.hour == 17)


def weekend_closed(t: datetime) -> bool:
    """Jumat 17:00 – Minggu 18:00 New York: pasar emas tutup akhir pekan."""
    ny = new_york(t)
    wd, h = ny.weekday(), ny.hour          # Senin = 0
    return wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 18)


def since_week_open(closed: list[Bar]) -> int:
    """Jumlah candle sejak candle pertama setelah pasar tutup (> 12 jam tanpa candle). 0 = candle pertama."""
    n = 0
    for k in range(len(closed) - 1, 0, -1):
        if closed[k].t - closed[k - 1].t > timedelta(hours=12):
            return n
        n += 1
    return n


def scheme_r(bars: list, v: dict, exit_price: float, tp_legs: int, be_07: bool, tp1_r: float = 1.0,
             be_offset: float = 0.10) -> float:
    """R rata-rata per posisi bila pengguna memakai skema lain: `tp_legs` posisi ditutup di TP1, sisanya ikut
    sampai TUTUP; SL+ (entry ± be_offset) setelah TP1, atau lebih awal saat profit 0,7R bila `be_07`.
    Urutan per candle sama dengan pengelolaan virtual: SL dulu, lalu TP1, lalu cek 0,7R."""
    sign = 1 if v["dir"] == "BUY" else -1
    entry, risk, legs = v["entry"], v["risk"], v["legs"]
    tp_legs = min(tp_legs, legs)
    sl, tp1 = entry - sign * risk, entry + sign * tp1_r * risk
    be = entry + sign * be_offset
    left, pnl, tp_hit = legs, 0.0, False
    start = parse_iso(v["bar_close"])
    for b in bars:
        if b.t < start:
            continue
        if (b.l <= sl) if sign > 0 else (b.h >= sl):
            return (pnl + left * (sl - entry) * sign / risk) / legs
        if not tp_hit and ((b.h >= tp1) if sign > 0 else (b.l <= tp1)):
            tp_hit, pnl, left = True, pnl + tp_legs * tp1_r, left - tp_legs
            sl = max(sl, be) if sign > 0 else min(sl, be)
            if left == 0:
                return pnl / legs
        if be_07 and ((b.h - entry) if sign > 0 else (entry - b.l)) >= 0.7 * risk:
            sl = max(sl, be) if sign > 0 else min(sl, be)
    return (pnl + left * (exit_price - entry) * sign / risk) / legs


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


def star_check(closed: list[Bar], direction: str, ema_span: int = 50, h4_n: int = 20) -> tuple[bool, str]:
    """Filter ⭐: searah tren D1 DAN H1 menembus 20 candle H4 sebelumnya. Hanya data yang sudah tertutup.

    Sama dengan research/filters.py: hari & blok H4 dihitung dalam UTC (H4 mulai 00/04/08/...),
    EMA = pandas ewm(span, adjust=True) atas close harian sampai kemarin.
    """
    last = closed[-1]
    daily: dict = {}
    for b in closed:
        if b.t.date() < last.t.date():
            daily[b.t.date()] = b.c
    closes = [daily[k] for k in sorted(daily)]
    if len(closes) < 20:
        return False, "data D1 belum cukup"
    alpha, num, den = 2 / (ema_span + 1), 0.0, 0.0
    for x in closes:
        num, den = num * (1 - alpha) + x, den * (1 - alpha) + 1
    ema, prev_close = num / den, closes[-1]

    def block(t: datetime) -> datetime:
        return t.replace(hour=t.hour - t.hour % 4, minute=0, second=0, microsecond=0)

    start, blocks = block(last.t), {}
    for b in closed:
        if b.t < start:
            k = block(b.t)
            hi, lo = blocks.get(k, (float("-inf"), float("inf")))
            blocks[k] = (max(hi, b.h), min(lo, b.l))
    prev = [blocks[k] for k in sorted(blocks)][-h4_n:]
    if len(prev) < h4_n:
        return False, "data H4 belum cukup"
    buy = direction == "BUY"
    d1_ok = prev_close > ema if buy else prev_close < ema
    h4_lvl = max(h for h, _ in prev) if buy else min(lo for _, lo in prev)
    h4_ok = last.c > h4_lvl if buy else last.c < h4_lvl
    note = (f"D1 {prev_close:.2f} {'>' if prev_close > ema else '<'} EMA{ema_span} {ema:.2f} "
            f"{'✓' if d1_ok else '✗'} | H4 {'high' if buy else 'low'} {h4_n} {h4_lvl:.2f} {'✓' if h4_ok else '✗'}")
    return bool(d1_ok and h4_ok), note


def h4_ema_check(closed: list[Bar], direction: str, n: int = 50) -> tuple[bool, str]:
    """Validasi arah H4 (unsur Trading Alchemist yang lolos uji, research/alchemist.py F4): close candle H4 terakhir
    yang SUDAH TUTUP di atas EMA-n H4 untuk BUY / di bawah untuk SELL. Blok H4 UTC (00/04/08/...), EMA ewm
    adjust=False seperti riset. Data H4 kurang dari n candle -> tidak memblokir."""
    if not closed:
        return True, "data H4 belum cukup"
    decide = closed[-1].t + timedelta(hours=1)               # waktu keputusan = tutup candle sinyal
    blocks: dict = {}
    for b in closed:
        k = b.t.replace(hour=b.t.hour - b.t.hour % 4, minute=0, second=0, microsecond=0)
        if k + timedelta(hours=4) <= decide:                  # hanya blok H4 yang sudah tutup
            blocks[k] = b.c                                  # close terakhir di blok
    closes = [blocks[k] for k in sorted(blocks)]
    if len(closes) <= n:
        return True, "data H4 belum cukup"
    ema = _ema(closes, n)[-1]
    last = closes[-1]
    ok = last > ema if direction == "BUY" else last < ema
    return ok, f"H4 {last:.2f} {'>' if last > ema else '<'} EMA{n} {ema:.2f}" + ("" if ok else " (lawan arah H4)")


def trend_status(closed: list[Bar], systems: dict, cfg: dict, tf: timedelta) -> dict:
    """Kartu "Status tren & hitung mundur" (aplikasi, tab Sinyal; permintaan 3 Okt 2026). Hanya keterangan:
    arah D1 (close kemarin vs EMA50 harian) & H4 (close H4 tutup vs EMA50 H4), level breakout tiap set untuk candle H1
    berikutnya (BUY bila close > high N candle terakhir, SELL bila < low N), dan waktu cek sinyal berikutnya."""
    if len(closed) < 90:
        return {}
    daily: dict = {}
    for b in closed:
        if b.t.date() < closed[-1].t.date():
            daily[b.t.date()] = b.c                           # close harian s.d. kemarin (sama dengan star_check)
    dc = [daily[k] for k in sorted(daily)]
    d1 = None if len(dc) < 20 else ("BUY" if dc[-1] > _ema(dc, cfg.get("star_ema", 50))[-1] else "SELL")
    h4 = "BUY" if h4_ema_check(closed, "BUY")[0] else "SELL"
    levels = []
    for entry_p, exit_p in cfg["sets"]:
        name = f"T{entry_p}/{exit_p}"
        win = closed[-entry_p:]
        sysd = systems.get(name) or {}
        open_ = [x["dir"] for x in [sysd.get("virtual")] + list(sysd.get("layers") or []) if x]
        levels.append({"set": name, "buy": round(max(b.h for b in win), 3), "sell": round(min(b.l for b in win), 3),
                       "open": open_[0] if open_ else None, "n_open": len(open_)})
    return {"d1": d1, "h4": h4, "levels": levels, "next_check": iso(closed[-1].t + 2 * tf),
            "last_close": round(closed[-1].c, 3)}


def _ema(values: list[float], n: int) -> list[float]:
    a, out = 2 / (n + 1), []
    for v in values:
        out.append(v if not out else a * v + (1 - a) * out[-1])
    return out


def konf_check(closed: list[Bar], direction: str) -> bool:
    """Konfluensi 3/3 (research/strategy_lab2.trend_states): EMA50 vs EMA200 H1, Supertrend 3xATR(14) H1, dan
    momentum 60 hari (close D1 kemarin vs 60 hari sebelumnya) semuanya searah dengan sinyal."""
    d = 1 if direction == "BUY" else -1
    c = [b.c for b in closed]
    if len(c) < 210:
        return False
    if (1 if _ema(c, 50)[-1] > _ema(c, 200)[-1] else -1) != d:
        return False
    # ATR Wilder 14 (TR candle pertama memakai close sendiri) + Supertrend 3x
    atr, st, fu, fd = 0.0, 1, 0.0, 0.0
    for i, b in enumerate(closed):
        pc = closed[i - 1].c if i else b.c
        tr = max(b.h - b.l, abs(b.h - pc), abs(b.l - pc))
        atr = tr if i == 0 else atr + (tr - atr) / 14
        hl2 = (b.h + b.l) / 2
        up, dn = hl2 - 3 * atr, hl2 + 3 * atr
        if i == 0:
            fu, fd = up, dn
            continue
        pfu, pfd = fu, fd
        fu = max(up, pfu) if closed[i - 1].c > pfu else up
        fd = min(dn, pfd) if closed[i - 1].c < pfd else dn
        st = 1 if b.c > pfd else (-1 if b.c < pfu else st)
    if st != d:
        return False
    daily: dict = {}
    for b in closed:
        if b.t.date() < closed[-1].t.date():
            daily[b.t.date()] = b.c
    p = [daily[k] for k in sorted(daily)]
    if len(p) < 61:
        return False
    return (1 if p[-1] > p[-61] else -1 if p[-1] < p[-61] else 0) == d


# Statistik historis per kategori (research/badge_stats.py & research/gap_years.py): (WR %, R/sinyal, n, periode)
STATS = {
    "XAU konf+⭐": (49.2, 0.309, 850, "2012–2026"),
    "XAU konf": (48.1, 0.093, 335, "2012–2026"),
    "XAU ⭐": (42.7, -0.062, 356, "2012–2026"),
    "XAU biasa": (43.5, -0.005, 1875, "2012–2026"),
    "BTC konf+⭐": (47.8, 0.310, 811, "2016–2026"),
    "BTC konf": (48.1, 0.226, 430, "2016–2026"),
    "BTC ⭐": (49.5, 0.678, 382, "2016–2026"),
    "BTC biasa": (43.0, 0.073, 2159, "2016–2026"),
    "GAP USD/JPY": (82.4, 0.256, 34, "2012–2020"),
    "GAP EUR/JPY": (83.9, 0.137, 31, "2007–2022"),
    "GAP AUD/JPY": (85.7, 0.096, 42, "2008–2022"),
    "GAP AUD/USD": (90.5, 0.248, 21, "2013–2022"),
    "GAP EUR/CHF": (74.4, 0.134, 39, "2013–2022"),
}


# ⚡ kesempatan emas (research/momen.py, docs/MOMEN_PERANG.md): XAU konf+⭐ saat volatilitas rendah (persentil ATR14
# 60 hari < 0,331 = batas tertil bawah periode 2012–2021) dan BTC ⭐. Sinyal kembar = 1 entry. Kolom: (WR bawaan,
# R bawaan, WR SL+0,7R, R SL+0,7R, n, periode). Dua periode: XAU ⚡ +0,95R (2012–2021) / +0,53R (5 th terakhir),
# BTC ⚡ +0,97R / +0,64R.
ZAP_VOL = 0.331
TIER_STATS = {
    "XAU": (54.3, 0.799, 63.3, 0.773, 138, "2013–2026"),
    "BTC": (54.0, 0.810, 64.4, 0.747, 200, "2016–2026"),
}


def vol_pct(closed: list[Bar], n: int = 14, window: int = 1440) -> float | None:
    """Persentil ATR14 (Wilder) candle terakhir di antara `window` candle terakhir (research: rolling rank pct)."""
    if len(closed) < 500:
        return None
    a, vals = None, []
    for i, b in enumerate(closed):
        prev = closed[i - 1].c if i else b.c
        tr = max(b.h - b.l, abs(b.h - prev), abs(b.l - prev))
        a = tr if a is None else a + (tr - a) / n
        vals.append(a)
    w = vals[-window:]
    return sum(1 for v in w if v <= w[-1]) / len(w)


def tier(asset: str, cat: str, vp: float | None) -> str:
    """Peringkat sinyal: zap (⚡ emas) > silver (🥈) > bronze (🥉) > biasa. cat tanpa awalan aset (mis. 'konf+⭐')."""
    low = vp is not None and vp < ZAP_VOL
    if asset == "BTC":
        return {"⭐": "zap", "konf+⭐": "silver"}.get(cat, "biasa")
    if cat == "konf+⭐":
        return "zap" if low else "bronze"
    return "bronze" if cat == "konf" and low else "biasa"


def badges(cat: str) -> dict:
    """💰 = profit/sinyal (≥0,25R 💰💰💰, ≥0,12R 💰💰, ≥0,05R 💰), ⭐ = win rate (≥75% ⭐⭐⭐, ≥60% ⭐⭐, ≥48% ⭐).
    Profit didahulukan: badge = 💰 lalu ⭐."""
    wr, avg, n, period = STATS[cat]
    stars = 3 if wr >= 75 else 2 if wr >= 60 else 1 if wr >= 48 else 0
    money = 3 if avg >= 0.245 else 2 if avg >= 0.12 else 1 if avg >= 0.05 else 0
    return {"cat": cat, "wr": wr, "avg_r": avg, "n_hist": n, "period": period, "stars": stars, "money": money,
            "badge": "💰" * money + "⭐" * stars, "star": money > 0}


def category(closed: list[Bar], direction: str, cfg: dict) -> tuple[dict, str]:
    """Kategori sinyal (konf+⭐ / konf / ⭐ / biasa) -> badge & statistik. 'star' = punya 💰 & bukan biasa."""
    is_star, note = star_check(closed, direction, cfg.get("star_ema", 50), cfg.get("star_h4", 20))
    is_konf = konf_check(closed, direction)
    name = "konf+⭐" if is_star and is_konf else "konf" if is_konf else "⭐" if is_star else "biasa"
    meta = badges(f"{cfg.get('asset', 'XAU')} {name}")
    meta["star"] = meta["money"] > 0 and name != "biasa"
    return meta, note


# ---------------------------------------------------------------- layanan luar
class TwelveData:
    def __init__(self, api_key: str, symbol: str = "XAU/USD"):
        self.api_key, self.symbol = api_key, symbol

    def candles(self, n: int, interval: str = "1h") -> list[Bar]:
        q = urllib.parse.urlencode({"symbol": self.symbol, "interval": interval, "outputsize": n,
                                    "timezone": "UTC", "order": "ASC", "apikey": self.api_key})
        data = http("GET", "https://api.twelvedata.com/time_series?" + q)
        if not data or data.get("status") != "ok":
            raise RuntimeError(f"Twelve Data: {(data or {}).get('message', 'tidak ada data')}")
        bars = []
        for v in data["values"]:
            fmt = "%Y-%m-%d %H:%M:%S" if len(v["datetime"]) > 10 else "%Y-%m-%d"     # candle harian tanpa jam
            t = datetime.strptime(v["datetime"], fmt).replace(tzinfo=timezone.utc)
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

    def get_gap_state(self) -> dict:
        return self.get_state("gap")

    def save_gap_state(self, data: dict) -> None:
        self.save_state(data, "gap")

    def log(self, kind: str, payload: dict) -> None:
        headers = {**self.headers, "Prefer": "return=minimal"}
        http("POST", f"{self.base}/xau_signals", headers, {"type": kind, "payload": payload})


class RowStore:
    """State di baris Supabase lain (mis. 'btc'). Kontrol auto order hanya untuk XAU (baris utama)."""

    def __init__(self, store, row: str):
        self.store, self.row = store, row

    def get_state(self) -> dict:
        return self.store.get_state(self.row)

    def save_state(self, data: dict) -> None:
        self.store.save_state(data, self.row)

    def get_control(self) -> dict:
        return {}

    def log(self, kind: str, payload: dict) -> None:
        self.store.log(kind, {**payload, "asset": self.row})


BTC_CFG = {**CFG, "asset": "BTC", "id_prefix": "BTC-", "market_hours": False, "skip_open_bars": 0,
           "point_value": 0.01}          # BTCUSD(c): kontrak 1 BTC/lot -> 0,01 lot = 0,01 per $1


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
    if cfg.get("market_hours", True):
        bars = [b for b in bars if market_open(b.t)]
    if not bars:
        return {"ok": False, "error": "tidak ada candle"}
    closed = [b for b in bars if b.t + tf <= now and (b.h > b.l or not cfg.get("market_hours", True))]
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

    def twins_open(name: str, v: dict) -> list[str]:
        """Set lain dengan sinyal kembar (arah & candle sinyal sama) yang masih punya posisi virtual. Set yang sudah
        diproses di tick ini memakai state terbarunya (systems diperbarui di akhir tiap set)."""
        if v.get("lapis"):                       # lapisan di-entry terpisah (lot ½), bukan kembar sinyal dasar
            return []
        return [n for n, s in systems.items() if n != name and s.get("virtual")
                and s["virtual"].get("bar_close") == v.get("bar_close") and s["virtual"].get("dir") == v.get("dir")]

    def exit_of(name: str) -> int:
        try:
            return int(name.split("/")[1])
        except (IndexError, ValueError):
            return 0

    def is_primary(name: str, v: dict) -> bool:
        """Sinyal kembar di-entry sekali dengan satu harga TUTUP: set paling lambat (tutup paling akhir). Teks ntfy
        (aplikasi ntfy) hanya dikirim untuk set itu supaya pengguna menerima 1 pesan per sinyal; data -data tetap
        dikirim untuk semua set."""
        return all(exit_of(n) < exit_of(name) for n in twins_open(name, v))

    def close_virtual(name: str, v: dict, exit_price: float, why: str, quiet: bool = False) -> None:
        sign = 1 if v["dir"] == "BUY" else -1
        points = (exit_price - v["entry"]) * sign
        r = f_result(v["legs"], v["entry"], v["risk"], sign, v.get("tp1_hit", False), exit_price, cfg["tp1_r"])
        ev = {"type": "close", "id": v["id"], "time": iso(now), "mode": "trend", "set": name,
              "dir": v["dir"], "entry": round(v["entry"], 3), "price": round(exit_price, 3),
              "points": round(points, 3), "r": round(r, 3), "risk_points": round(v["risk"], 3),
              "legs": v["legs"], "tp1_hit": v.get("tp1_hit", False), "star": v.get("star", False),
              "cat": v.get("cat", ""), "tier": v.get("tier", ""), "point_value": cfg.get("point_value", 1.0),
              "tp1_time": v.get("be_bar"), "reason": why, **({"lapis": True} if v.get("lapis") else {}),
              "r_by": {f"{n}_{'07' if e else 'tp1'}": round(scheme_r(bars, v, exit_price, n, e, cfg["tp1_r"],
                                                                     cfg["be_offset"]), 3)
                       for n in (1, 3) for e in (False, True)}}
        text = (f"🏁 TUTUP {v['dir']} {symbol} @ {exit_price:.2f} — tutup SEMUA posisi sinyal ini\n"
                f"Entry {v['entry']:.2f} -> {points:+.2f} poin | {'PROFIT (TP1 kena)' if v.get('tp1_hit') else 'MINUS'}"
                f"\nAlasan: {why}")
        # sinyal kembar: hanya set terakhir yang masih terbuka mengirim teks (set lebih cepat tutup diam-diam)
        if v.get("lapis"):
            text = "🔁 LAPISAN " + text
        pub.publish(ev, None if quiet or twins_open(name, v) else text, "Sinyal TUTUP posisi", 5, ["checkered_flag"])
        store.log("close", ev)
        events.append(f"{name} TUTUP {v['dir']} {r:+.2f}R")

    def manage(name: str, v: dict | None) -> dict | None:
        """Cek SL / TP1 / SL+ secara berurutan per bar sejak entry (konservatif: SL dulu)."""
        if not v:
            return None
        if cfg.get("market_hours", True) and weekend_closed(parse_iso(v["bar_close"]) - tf):
            # sinyal lama yang lahir dari candle saat pasar tutup -> batalkan, tidak dihitung menang/kalah
            ev = {"type": "close", "id": v["id"], "time": iso(now), "mode": "trend", "set": name, "dir": v["dir"],
                  "entry": round(v["entry"], 3), "price": round(price, 3), "points": 0.0, "r": 0.0,
                  "risk_points": round(v["risk"], 3), "legs": v["legs"], "tp1_hit": False,
                  "star": v.get("star", False), "void": True,
                  "reason": "Dibatalkan: sinyal dari data saat pasar tutup"}
            text = f"⚠️ BATAL {v['dir']} [{name}] @ {v['entry']:.2f}: sinyal dari data saat pasar tutup, abaikan."
            pub.publish(ev, text, "Sinyal dibatalkan", 4, ["warning"])
            store.log("void", ev)
            events.append(f"{name} BATAL {v['dir']} (data pasar tutup)")
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
                    pub.publish({"type": "info", "kind": "tp1", "time": iso(now), "set": name, "id": v["id"],
                                 "symbol": symbol, "sl_plus": round(v["sl"], 3), "text": text},
                                text if is_primary(name, v) else None, "TP1 + SL+", 5, ["dart"])
                    store.log("tp1", {"id": v["id"], "set": name, "sl": v["sl"]})
                    events.append(f"{name} TP1 -> SL+")
                    break
        if not v.get("be_done") and not v.get("n07"):
            fav = max(((b.h - v["entry"]) if buy else (v["entry"] - b.l)
                       for b in bars if b.t >= parse_iso(v["bar_close"])), default=0.0)
            if fav >= 0.7 * v["risk"]:
                v["n07"] = True
                sl_plus = v["entry"] + (1 if buy else -1) * cfg["be_offset"]
                text = (f"🛡️ [{name}] {v['dir']} {symbol}: profit 0,7R tercapai → SL+ ke {sl_plus:.2f}"
                        " (bila memakai SL+ 0,7R)")
                pub.publish({"type": "info", "kind": "be07", "time": iso(now), "set": name, "id": v["id"],
                             "symbol": symbol, "sl_plus": round(sl_plus, 3), "text": text},
                            text if is_primary(name, v) else None, "SL+ sekarang", 5, ["shield"])
                events.append(f"{name} 0,7R")
        if v.get("be_done"):
            for b in (b for b in bars if b.t > parse_iso(v["be_bar"])):
                if (b.l <= v["sl"]) if buy else (b.h >= v["sl"]):
                    close_virtual(name, v, v["sl"], "SL+ (break-even) tersentuh")
                    return None
        return v

    def try_open(name: str, idx: int, magic: int, entry_p: int, exit_p: int, s: dict, sig: dict,
                 layer: bool = False, opens_now: list | None = None) -> dict | None:
        """Filter sinyal (ATR, buka pekan, ⭐, 💰, H4, filter eksternal) lalu buat & kirim sinyal. Dipakai sinyal dasar
        dan lapisan (layer=True: sinyal baru saat sinyal lain di set ini masih berjalan, lot ½, tanpa auto order)."""
        opens_now = opens_now or []
        if sig["atr"] < 0.4 * atr_last(closed, 120):
            # ATR(20) jauh di bawah normal (mis. candle datar) -> SL terlalu sempit, sinyal tidak wajar
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": "ATR tidak wajar"})
            events.append(f"{name} {sig['dir']} dilewati: ATR {sig['atr']:.2f} terlalu kecil")
            return None
        if since_week_open(closed) < cfg.get("skip_open_bars", 0):
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": "gap buka pekan"})
            events.append(f"{name} {sig['dir']} dilewati: {since_week_open(closed) + 1} candle pertama setelah buka")
            return None
        if cfg.get("star_only") and not (
                star := star_check(closed, sig["dir"], cfg.get("star_ema", 50), cfg.get("star_h4", 20)))[0]:
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": star[1]})
            events.append(f"{name} {sig['dir']} bukan ⭐ ({star[1]})")
            return None
        if cfg.get("profit_only", True) and not (cat := category(closed, sig["dir"], cfg))[0]["star"]:
            # hanya kirim sinyal yang terbukti untung (punya 💰); sinyal biasa tidak worth it
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": cat[0]["cat"]})
            events.append(f"{name} {sig['dir']} dilewati: {cat[0]['cat']} tanpa 💰")
            return None
        if (c0 := category(closed, sig["dir"], cfg)[0]["cat"].split(" ", 1)[-1]) in (cfg.get("skip_cats") or ()):
            # kategori dimatikan (BTC konf: research/tanpa_konf.py, izin pengguna 3 Okt 2026 "matikan btc konf")
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": c0})
            events.append(f"{name} {sig['dir']} dilewati: kategori {c0} dimatikan")
            return None
        if cfg.get("h4_filter") and not (h4 := h4_ema_check(closed, sig["dir"]))[0]:
            # validasi arah H4 EMA50 (research/alchemist.py F4, XAU): sinyal 💰 lawan arah H4 tidak dikirim
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": h4[1]})
            events.append(f"{name} {sig['dir']} dilewati: {h4[1]}")
            return None
        if cfg.get("skip_fn") and (why := cfg["skip_fn"](sig["dir"], now)):
            # filter riset data eksternal (BTC: funding ramai, September) — _funding.skip_reason
            store.log("skip", {"set": name, "dir": sig["dir"], "bar": iso(closed[-1].t), "why": why})
            events.append(f"{name} {sig['dir']} dilewati: {why}")
            return None
        d = sig["dir"]
        meta, star_note = category(closed, d, cfg)
        asset = cfg.get("asset", "XAU")
        vp = vol_pct(closed) if asset == "XAU" else None
        meta["tier"] = tier(asset, meta["cat"].split(" ", 1)[-1], vp)
        meta["vol_pct"] = None if vp is None else round(vp, 3)
        meta["zap"] = meta["tier"] == "zap"
        if meta["zap"]:        # ⚡: statistik kelompok ⚡ sendiri (lebih tinggi dari kategori induknya)
            wr, ar, wr7, ar7, n_z, per_z = TIER_STATS[asset]
            meta.update(badge="⚡" + meta["badge"], wr=wr, avg_r=ar, wr07=wr7, avg_r07=ar7, n_hist=n_z,
                        period=per_z)
        war = cfg.get("war") if asset == "XAU" else None
        sign = 1 if d == "BUY" else -1
        risk = cfg["stop_atr"] * sig["atr"]
        sl = price - sign * risk
        tp1 = price + sign * cfg["tp1_r"] * risk
        key = f"{cfg.get('id_prefix', '')}{name}-{d}-{closed[-1].t:%Y%m%d%H%M}" + ("L" if layer else "")
        ev = {"type": "signal", "id": key, "time": iso(now), "mode": "trend", "set": name, "dir": d,
              "symbol": symbol, "entry": round(price, 3), "sl": round(sl, 3), "tp": round(tp1, 3),
              "tp1": round(tp1, 3), "atr": round(sig["atr"], 3), "risk_points": round(risk, 3),
              "legs": legs_n, "lot": lot_text, "timeframe": "H1", "status": "signal",
              "exit_rule": f"close H1 menembus channel {exit_p} bar", "reason": sig["note"],
              "warning": "Harga dari data feed; cek harga broker sebelum entry.",
              "star_note": star_note, "point_value": cfg.get("point_value", 1.0), **meta}
        if war and war.get("on"):
            ev["war"] = war
        text = (f"{meta['badge'] + ' ' if meta['badge'] else ''}{'🟢' if d == 'BUY' else '🔴'} {d} {symbol} [{name}]\n"
                f"WR {meta['wr']:.0f}% • rata-rata {meta['avg_r']:+.2f}R/sinyal ({meta['period']}, "
                f"{meta['n_hist']} sinyal)\n"
                f"Entry: {price:.2f} | SL: {sl:.2f} ({cfg['stop_atr']}x ATR {sig['atr']:.2f})\n"
                f"Lot: {lot_text} -> posisi #1 TP1 {tp1:.2f} ({cfg['tp1_r']}R), sisanya hold\n"
                f"TP1 kena -> SL sisa ke entry (SL+). Tunggu sinyal TUTUP.\nAlasan: {sig['note']}")
        if meta["zap"]:
            text = (f"⚡ KESEMPATAN EMAS (WR {meta['wr07']:.0f}% dengan SL+ 0,7R, +{meta['avg_r07']:.2f}R/sinyal)\n"
                    + text)
        if war and war.get("on"):
            text += "\n" + war["text"]
        news = None
        if cfg.get("news_fn"):
            try:                    # 📰 sinyal lahir <= 4 jam setelah berita AS besar (research/sinyal_berita.py)
                news = cfg["news_fn"](d, now)
            except Exception as exc:  # noqa: BLE001 - tanda berita opsional
                events.append(f"{name} tanda berita gagal: {exc}")
        if news:
            ev["news"] = news
            text = news["judul"] + "\n" + text + "\n" + news["teks"]
        if layer:
            lay = cfg.get("layer") or {}
            n_open = len(opens_now)
            ev.update(lapis=True, lot_mult=lay.get("lot", 0.5), lapis_ke=n_open)
            if lay.get("stats"):
                ev["lapis_stats"] = lay["stats"]
            text = (f"🔁 LAPISAN ke-{n_open} (lot ½) — {n_open} sinyal sebelumnya di set ini masih berjalan"
                    + (f"\n{lay['stats']['teks']}" if lay.get("stats") else "") + "\n" + text
                    + "\nPakai ½ lot dari biasanya. Auto order tidak dipakai untuk lapisan.")
        # sinyal kembar (set lain sudah membuka sinyal di candle & arah yang sama): cukup 1 teks ntfy
        first = layer or not twins_open(name, {"bar_close": iso(closed[-1].t + tf), "dir": d})
        pub.publish(ev, text if first else None, f"{d} {symbol}", 5,
                    ["green_circle" if d == "BUY" else "red_circle"])
        store.log("signal", ev)
        events.append(f"{name} SINYAL {d} @ {price:.2f}")
        v = {"id": key, "dir": d, "entry": price, "sl": sl, "risk": risk, "tp1": tp1,
             "legs": legs_n, "be_done": False, "tp1_hit": False, "star": meta["star"], "cat": meta["cat"],
             "tier": meta["tier"],
             "bar_close": iso(closed[-1].t + tf), **({"lapis": True} if layer else {})}
        existing = live_positions(magic) if live and not layer else []
        if layer:
            pass                    # lapisan: sinyal saja (posisi lama satu magic per set; auto order hanya sinyal dasar)
        elif live and existing != []:
            why = "MetaApi tidak bisa dihubungi" if existing is None else f"masih ada {len(existing)} posisi lama"
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
                res = executor.market(d, leg_lot, sl, tp1 if (i == 0 and legs_n >= 2) else None, magic,
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

    def layer_ok(opens: list, sc: dict) -> bool:
        """Boleh sinyal lapisan? (research/sinyal_lapis.py & sinyal_berita.py) cfg["layer"]:
        mode "tp1" = sinyal terakhir di set ini sudah TP1 (sisa posisi SL+); mode "any" = kapan saja, asal breakout
        BARU (candle sebelumnya belum di luar channel); "max" = batas sinyal terbuka bersamaan per set."""
        lay = cfg.get("layer")
        if not lay or len(opens) >= lay.get("max", 10):
            return False
        if lay.get("mode") == "tp1":
            last = max(opens, key=lambda x: x["bar_close"])
            # seperti backtest: keputusan lapisan di candle SESUDAH candle tempat TP1 kena
            return bool(last.get("tp1_hit")) and parse_iso(last["be_bar"]) < closed[-1].t
        if lay.get("mode") == "any":
            prev = evaluate(closed[:-1], None, sc)
            return not (prev["action"] == "open" and prev["dir"] == opens[0]["dir"])
        return False

    trends = []
    for idx, (entry_p, exit_p) in enumerate(cfg["sets"]):
        name = f"T{entry_p}/{exit_p}"
        magic = BASE_MAGIC + idx
        sc = {**cfg, "entry": entry_p, "exit": exit_p}
        s = dict(systems.get(name) or {})
        v = manage(name, s.get("virtual"))
        layers = [x for x in (manage(name, x) for x in (s.get("layers") or [])) if x]
        if closed and s.get("last_bar") != iso(closed[-1].t):
            s["last_bar"] = iso(closed[-1].t)
            opens = ([v] if v else []) + layers
            pos = opens[0]["dir"] if opens else None
            sig = evaluate(closed, pos, sc)
            if sig["action"] == "close" and opens:
                for k, x in enumerate(opens):          # TUTUP berlaku untuk semua sinyal (dasar & lapisan) di set ini
                    close_virtual(name, x, price, sig["note"], quiet=k > 0)
                v, layers = None, []
            elif sig["action"] == "open" and not opens:
                v = try_open(name, idx, magic, entry_p, exit_p, s, sig)
            elif opens and layer_ok(opens, sc):
                sig2 = evaluate(closed, None, sc)
                if sig2["action"] == "open" and sig2["dir"] == pos:
                    nv = try_open(name, idx, magic, entry_p, exit_p, s, sig2, layer=True, opens_now=opens)
                    if nv:
                        layers.append(nv)
            s["trend"] = sig["state"]
        try:
            v = live_sync(name, magic, v)
        except Exception as exc:  # noqa: BLE001 - kegagalan MetaApi tidak boleh menghentikan sinyal
            events.append(f"{name} LIVE sync error: {exc}")
        s["virtual"] = v
        s["layers"] = layers
        systems[name] = s
        trends.append(f"{name}: {s.get('trend', '-')}")

    state["systems"] = systems
    state["last_tick"] = iso(now)
    state["price"] = price
    store.save_state(state)
    trend_text = " | ".join(trends)
    mode = "AUTO (cloud)" if live else ("SINYAL (auto dijeda)" if control.get("auto") else "SINYAL (cloud)")
    # level TUTUP untuk candle H1 yang sedang berjalan: BUY ditutup bila close < low N candle terakhir yang sudah
    # tutup (SELL: close > high N candle) — sama dengan evaluate() di tick berikutnya. Ditampilkan di kartu sinyal.
    exits = []
    for entry_p, exit_p in cfg["sets"]:
        sysd = systems.get(f"T{entry_p}/{exit_p}") or {}
        for v in [x for x in [sysd.get("virtual")] + list(sysd.get("layers") or []) if x]:   # dasar + lapisan
            if len(closed) >= exit_p:
                window = closed[-exit_p:]
                level = min(b.l for b in window) if v["dir"] == "BUY" else max(b.h for b in window)
                exits.append({"id": v["id"], "set": f"T{entry_p}/{exit_p}", "dir": v["dir"],
                              "level": round(level, 3), "bars": exit_p, **({"lapis": True} if v.get("lapis") else {})})
    hb = {"type": "heartbeat", "time": iso(now), "symbol": symbol, "price": price, "mode": mode,
          "trend": trend_text, "session": "cloud", "block": "", "news": "-", "currency": "", "positions": [],
          "exits": exits, "status": trend_status(closed, systems, cfg, tf)}
    if cfg.get("asset", "XAU") == "XAU" and cfg.get("war") is not None:
        hb["war"] = cfg["war"]
    if executor is not None:
        try:
            acc = executor.account()
            hb.update(balance=acc.get("balance"), equity=acc.get("equity"), currency=acc.get("currency", ""))
            hb["positions"] = [{"ticket": p["id"], "dir": "BUY" if p.get("type") == "POSITION_TYPE_BUY" else "SELL",
                                "volume": p.get("volume"), "open": p.get("openPrice"), "sl": p.get("stopLoss"),
                                "tp": p.get("takeProfit"), "profit": p.get("profit")}
                               for p in executor.positions() if ours(p)]
        except Exception as exc:  # noqa: BLE001
            hb["block"] = f"MetaApi: {exc}"
    pub.publish(hb)
    return {"ok": True, "price": price, "auto": live, "last_closed_bar": iso(closed[-1].t) if closed else None,
            "open": {k: v["virtual"] for k, v in systems.items() if v.get("virtual")},
            "layers": {k: v["layers"] for k, v in systems.items() if v.get("layers")},
            "events": events, "trend": trend_text}


# ------------------------------------------------------------------ kontrol
def apply_control(store, executor, pub, changes: dict, max_leg_lot: float = 0.10) -> dict:
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
    return status(store, executor, control)


def status(store, executor, control: dict | None = None) -> dict:
    control = control if control is not None else (store.get_control() or {})
    out = {"ok": True, "control": {"auto": bool(control.get("auto")), "paused": bool(control.get("paused")),
                                   "leg_lot": control.get("leg_lot", CFG["leg_lot"]),
                                   "legs": control.get("legs", CFG["legs"])},
           "executor": executor is not None}
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
