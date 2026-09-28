"""Sinyal gap besar pembukaan pekan (research/gap_years.py, variasi fade50 gap>=0,5 ATR harian, SL 1x gap).

Dicek sekali, 1 jam setelah pasar forex buka (Minggu 17:00 New York): bila gap >= 0,5 x rata-rata range harian 14
hari, lawan arah gap. TP = 50% gap tertutup, SL = 1 x gap dari entry, tutup paksa 24 jam. Satu posisi per pair.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from _core import Bar, badges, iso, new_york, parse_iso

PAIRS = {"USD/JPY": "GAP USD/JPY", "EUR/JPY": "GAP EUR/JPY", "AUD/JPY": "GAP AUD/JPY",
         "AUD/USD": "GAP AUD/USD", "EUR/CHF": "GAP EUR/CHF"}


def fx_open(t: datetime) -> bool:
    """Forex buka Minggu 17:00 – Jumat 17:00 New York."""
    ny = new_york(t)
    wd, h = ny.weekday(), ny.hour
    return not (wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 17))


def in_window(now: datetime) -> bool:
    """Minggu 17:00 – 20:00 New York: satu-satunya waktu sinyal gap bisa lahir."""
    ny = new_york(now)
    return ny.weekday() == 6 and 17 <= ny.hour < 20


def point_value(pair: str, price: float, usdjpy: float | None, usdchf: float | None) -> float:
    """Nilai 1,0 pergerakan harga untuk 0,01 lot (1.000 unit), dalam USD (atau USC di akun Cent)."""
    quote = pair.split("/")[1]
    if quote == "USD":
        return 1000.0
    if quote == "JPY":
        return 1000.0 / (usdjpy or price)
    return 1000.0 / (usdchf or 0.9)


def evaluate_open(bars: list[Bar], now: datetime) -> dict | None:
    """Return rencana entry bila sekarang = candle H1 kedua setelah buka pekan & gap cukup besar."""
    bars = [b for b in bars if fx_open(b.t) and b.h > b.l]
    closed = [b for b in bars if b.t + timedelta(hours=1) <= now]
    if len(closed) < 30:
        return None
    k = len(closed) - 1
    if closed[k].t - closed[k - 1].t <= timedelta(hours=30):
        return None                                        # candle tutup terakhir bukan candle pertama pekan
    if now >= closed[k].t + timedelta(hours=2):
        return None                                        # terlambat (lewat candle kedua)
    fri, first = closed[k - 1].c, closed[k]
    gap = first.o - fri
    day0 = first.t.date()
    days: dict = {}
    for b in closed[:k]:
        if b.t.date() < day0:
            hi, lo = days.get(b.t.date(), (float("-inf"), float("inf")))
            days[b.t.date()] = (max(hi, b.h), min(lo, b.l))
    rng = [h - l for h, l in (days[x] for x in sorted(days))][-14:]
    if len(rng) < 14:
        return None
    atr_d = sum(rng) / 14
    if abs(gap) < 0.5 * atr_d:
        return None
    d = -1 if gap > 0 else 1
    entry = bars[-1].c                                     # harga sekarang (awal candle kedua)
    tp = fri + gap / 2
    if (tp - entry) * d <= 0:
        return None                                        # separuh gap sudah tertutup sebelum entry
    sl = entry - d * abs(gap)
    return {"dir": "BUY" if d > 0 else "SELL", "entry": entry, "tp": tp, "sl": sl, "gap": gap, "atr_d": atr_d,
            "fri": fri, "week": first.t}


def manage(pos: dict, bars: list[Bar], now: datetime) -> tuple[float, str] | None:
    """Cek SL (dulu) / TP / 24 jam sejak entry. Return (harga keluar, alasan) atau None."""
    t0 = parse_iso(pos["time"])
    d = 1 if pos["dir"] == "BUY" else -1
    for b in bars:
        if b.t + timedelta(hours=1) <= t0 or b.t + timedelta(hours=1) > now:
            continue
        if (b.l <= pos["sl"]) if d > 0 else (b.h >= pos["sl"]):
            return pos["sl"], "Stop loss tersentuh"
        if b.t >= t0 and ((b.h >= pos["tp"]) if d > 0 else (b.l <= pos["tp"])):
            return pos["tp"], "TP: 50% gap tertutup"
    if now >= t0 + timedelta(hours=24):
        return bars[-1].c, "Tutup otomatis 24 jam"
    return None


def gap_tick(now: datetime, feeds: dict, store, pub, usdchf=None) -> list[str]:
    """feeds: {pair: objek dengan candles(n)}. Hanya mengambil data bila perlu (hemat kuota Twelve Data)."""
    state = store.get_gap_state() or {}
    events: list[str] = []
    cache: dict = {}

    def bars_of(pair):
        if pair not in cache:
            cache[pair] = feeds[pair].candles(400)
        return cache[pair]

    for pair, cat in PAIRS.items():
        if pair not in feeds:
            continue
        try:
            _one(pair, cat, state, now, bars_of, feeds, store, pub, usdchf, events)
        except Exception as exc:  # noqa: BLE001 - satu pair gagal tidak menghentikan pair lain
            events.append(f"{pair} error: {exc}")
    store.save_gap_state(state)
    return events


def _one(pair, cat, state, now, bars_of, feeds, store, pub, usdchf, events):
    if True:
        pos = state.get(pair)
        if pos:
            done = manage(pos, bars_of(pair), now)
            if done:
                px, why = done
                d = 1 if pos["dir"] == "BUY" else -1
                r = (px - pos["entry"]) * d / pos["risk"]
                ev = {"type": "close", "id": pos["id"], "time": iso(now), "mode": "gap", "set": "GAP",
                      "symbol": pair, "dir": pos["dir"], "entry": round(pos["entry"], 5), "price": round(px, 5),
                      "points": round((px - pos["entry"]) * d, 5), "r": round(r, 3),
                      "risk_points": round(pos["risk"], 5), "legs": 1, "tp1_hit": r > 0, "reason": why,
                      "star": pos["star"], "cat": cat, "point_value": pos["point_value"]}
                pub.publish(ev, f"🏁 TUTUP {pos['dir']} {pair} @ {px:.5g} ({r:+.2f}R) • {why}",
                            "Sinyal TUTUP posisi", 5, ["checkered_flag"])
                store.log("close", ev)
                events.append(f"{pair} TUTUP {r:+.2f}R")
                state[pair] = None
            return
        if not in_window(now):
            return
        plan = evaluate_open(bars_of(pair), now)
        if not plan:
            return
        key = f"GAP-{pair.replace('/', '')}-{plan['week']:%Y%m%d}"
        if state.get("last_" + pair) == key:
            return
        usdjpy = bars_of("USD/JPY")[-1].c if pair.endswith("JPY") and "USD/JPY" in feeds else None
        meta = badges(cat)
        pv = point_value(pair, plan["entry"], usdjpy, usdchf() if (usdchf and pair.endswith("CHF")) else None)
        risk = abs(plan["entry"] - plan["sl"])
        ev = {"type": "signal", "id": key, "time": iso(now), "mode": "gap", "set": "GAP", "symbol": pair,
              "dir": plan["dir"], "entry": round(plan["entry"], 5), "sl": round(plan["sl"], 5),
              "tp": round(plan["tp"], 5), "tp1": round(plan["tp"], 5), "risk_points": round(risk, 5),
              "legs": 1, "lot": "1 posisi", "timeframe": "H1", "status": "signal", "point_value": pv,
              "reason": f"Gap {plan['gap']:+.5g} (≥0,5× range harian {plan['atr_d']:.5g}); lawan gap, TP 50% gap",
              **meta}
        text = (f"{meta['badge']} {'🟢' if plan['dir'] == 'BUY' else '🔴'} {plan['dir']} {pair} (gap pekan)\n"
                f"WR {meta['wr']:.0f}% • rata-rata {meta['avg_r']:+.2f}R/sinyal ({meta['period']}, "
                f"{meta['n_hist']} sinyal)\nEntry {plan['entry']:.5g} | SL {plan['sl']:.5g} | TP {plan['tp']:.5g}"
                f"\nTutup otomatis 24 jam bila TP/SL belum kena.")
        pub.publish(ev, text, f"{plan['dir']} {pair}", 5, ["green_circle" if plan["dir"] == "BUY" else "red_circle"])
        store.log("signal", ev)
        state[pair] = {"id": key, "dir": plan["dir"], "entry": plan["entry"], "sl": plan["sl"], "tp": plan["tp"],
                       "risk": risk, "time": iso(now), "star": meta["star"], "point_value": pv}
        state["last_" + pair] = key
        events.append(f"{pair} SINYAL GAP {plan['dir']}")


def needs_data(now: datetime, store) -> bool:
    state = store.get_gap_state() or {}
    return in_window(now) or any(state.get(p) for p in PAIRS)
