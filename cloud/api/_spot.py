"""💎 Sinyal SPOT Binance: peluang naik lagi (research/spot_peluang.py, permintaan pengguna 4 Okt 2026).

Sekali sehari setelah candle harian UTC tutup (± 07:05 WIB): hitung fitur 20 koin besar dan peluang "harga menyentuh
+TP% dalam N hari" dari model gradient boosting (spot_model.json: pohon diekspor, dievaluasi tanpa pustaka). Peluang ≥
ambang dan koin belum terbuka -> pesan BELI SPOT. Posisi dicek tiap jam: high harian menyentuh TP -> CLOSE (limit jual
terisi); N hari lewat -> CLOSE di close candle terakhir. Hanya informasi: cloud TIDAK membuka order spot.

Data harian: data-api.binance.vision -> api.binance.us -> Twelve Data (Vercel di AS; api.binance.com menolak AS, 451).
State: baris Supabase 'spot'. Pesan ntfy: spot_signal, spot_close (dengan notifikasi), spot_status (kartu 💎).
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _core

_PATH = Path(__file__).resolve().parent / "spot_model.json"
MODEL = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
DAY = timedelta(days=1)
SCAN_AFTER = timedelta(minutes=5)       # tunggu candle harian benar-benar tutup
KEEP_CLOSED = 30
STATUS_EVERY = timedelta(hours=2)


# ------------------------------------------------------------------ data
def _binance(base: str, coin: str, n: int) -> list[_core.Bar]:
    q = urllib.parse.urlencode({"symbol": f"{coin}USDT", "interval": "1d", "limit": n})
    rows = _core.http("GET", f"{base}/api/v3/klines?{q}", timeout=10) or []
    return [_core.Bar(datetime.fromtimestamp(r[0] / 1000, timezone.utc), float(r[1]), float(r[2]), float(r[3]),
                      float(r[4])) for r in rows]


SOURCES = (
    ("binance", lambda coin, n, key: _binance("https://data-api.binance.vision", coin, n)),
    ("binance.us", lambda coin, n, key: _binance("https://api.binance.us", coin, n)),
    ("twelvedata", lambda coin, n, key: _core.TwelveData(key, f"{coin}/USD").candles(n, "1day") if key else []),
)


def klines(coin: str, n: int, td_key: str | None, budget: dict) -> tuple[list[_core.Bar], str]:
    """Candle harian (termasuk candle hari ini yang masih berjalan) dari sumber pertama yang berhasil."""
    errors = []
    for name, fn in SOURCES:
        if name == "twelvedata":
            if budget.get("td", 0) <= 0:
                errors.append("twelvedata: jatah habis")
                continue
            budget["td"] -= 1
        try:
            bars = fn(coin, n, td_key)
            if len(bars) >= 2:
                return bars, name
            errors.append(f"{name}: kosong")
        except Exception as exc:  # noqa: BLE001 - coba sumber berikutnya
            errors.append(f"{name}: {str(exc)[:60]}")
    raise RuntimeError(f"{coin}: " + "; ".join(errors))


# ------------------------------------------------------------------ fitur (sama dengan research/spot_peluang.features)
def _mean(x):
    return sum(x) / len(x)


def _std(x):                       # simpangan baku sampel (ddof=1), seperti pandas
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def _rsi(closes: list[float], n: int) -> float | None:
    a = 1 / n
    up = dn = None
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        u, w = max(d, 0.0), max(-d, 0.0)
        up = u if up is None else (1 - a) * up + a * u
        dn = w if dn is None else (1 - a) * dn + a * w
    if not dn:
        return None
    return 1 - 1 / (1 + up / dn)          # RSI / 100


def features(bars: list[_core.Bar], btc: list[_core.Bar]) -> list[float] | None:
    """Fitur di close candle harian TERAKHIR yang sudah tutup. bars & btc = candle tutup, urut waktu."""
    if len(bars) < 201 or len(btc) < 201:
        return None
    c = [b.c for b in bars]
    hi = [b.h for b in bars]
    red = 0
    for b in reversed(bars):
        if b.c < b.o:
            red += 1
        else:
            break
    r14, r2 = _rsi(c, 14), _rsi(c, 2)
    if r14 is None or r2 is None:
        return None
    lr = [math.log(c[i] / c[i - 1]) for i in range(len(c) - 14, len(c))]
    s20 = _std(c[-20:])
    bmap = {b.t.date(): b.c for b in btc}
    bdates = sorted(bmap)
    last = bars[-1].t.date()
    bd = [d for d in bdates if d <= last]
    if len(bd) < 201:
        return None
    bc = [bmap[d] for d in bd]
    f = {
        "dd20": c[-1] / max(hi[-20:]) - 1,
        "dd60": c[-1] / max(hi[-60:]) - 1,
        "rsi14": r14,
        "rsi2": r2,
        "red": float(min(red, 6)),
        "r1": c[-1] / c[-2] - 1,
        "r3": c[-1] / c[-4] - 1,
        "r7": c[-1] / c[-8] - 1,
        "r30": c[-1] / c[-31] - 1,
        "z20": (c[-1] - _mean(c[-20:])) / s20 if s20 else 0.0,
        "d50": c[-1] / _mean(c[-50:]) - 1,
        "d200": c[-1] / _mean(c[-200:]) - 1,
        "vol14": _std(lr),
        "btc_up": 1.0 if bc[-1] > _mean(bc[-200:]) else 0.0,
        "btc_r7": bc[-1] / bc[-8] - 1,
    }
    return [f[k] for k in MODEL.get("fitur", list(f))]


def red_rule(x: list[float]) -> bool:
    """Aturan cadangan yang ikut teruji: 3 hari merah beruntun, turun ≥ 10% dalam 3 hari, harga di atas SMA200."""
    if not MODEL.get("aturan_merah"):
        return False
    f = dict(zip(MODEL.get("fitur", []), x))
    return f.get("red", 0) >= 3 and f.get("r3", 0) <= -0.10 and f.get("d200", -1) > 0


def prob(x: list[float], model: dict | None = None) -> float:
    """Peluang naik dari pohon gradient boosting (sama dengan research/spot_peluang.gbm_prob)."""
    model = model or MODEL
    s = model["base"]
    for nodes in model["trees"]:
        i = 0
        while not nodes[i][0]:
            _, f, thr, miss_left, left, right, _ = nodes[i]
            v = x[f]
            go_left = miss_left if v != v else v <= thr
            i = left if go_left else right
        s += nodes[i][6]
    return 1 / (1 + math.exp(-s))


# ------------------------------------------------------------------ teks
def _px(v: float) -> str:
    d = 2 if v >= 100 else 4 if v >= 1 else 6
    return f"{v:,.{d}f}"


def _wib(t: datetime) -> str:
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    w = t.astimezone(timezone(timedelta(hours=7)))
    return f"{w.day} {bulan[w.month - 1]} {w:%H:%M} WIB"


def _pct(v: float) -> str:
    return f"{v:+.1f}%".replace(".", ",")


# ------------------------------------------------------------------ putaran
def spot_tick(now: datetime, store, pub, td_key: str | None = None, max_open: int = 10, fetch=None,
              deadline_s: float = 20.0) -> dict:
    """Dipanggil tiap tick cloud (10 menit). Pindai sekali sehari, cek posisi sekali per jam. Idempoten."""
    if not MODEL:
        return {"ok": False, "error": "spot_model.json tidak ada"}
    fetch = fetch or klines
    started = time.monotonic()
    state = store.get_state() or {}
    open_ = state.get("open") or {}
    closed = state.get("closed") or []
    tp, days, thr, cost = MODEL["tp"], int(MODEL["hari"]), MODEL["ambang"], MODEL.get("biaya", 0.003)
    budget = {"td": 4}
    events, errors, changed = [], [], False
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_key = now.strftime("%Y-%m-%dT%H")
    prices = state.get("prices") or {}

    # 1) cek posisi terbuka (sekali per jam): TP tersentuh atau batas waktu habis
    if open_ and state.get("hour") != hour_key:
        for coin, pos in list(open_.items()):
            try:
                bars, _src = fetch(coin, days + 5, td_key, budget)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc)[:120])
                continue
            day0 = _core.parse_iso(pos["day"])
            dl = _core.parse_iso(pos["deadline"])
            prices[coin] = bars[-1].c
            hit = next((b for b in bars if day0 <= b.t < dl and b.h >= pos["tp"]), None)
            reason = exit_px = None
            if hit is not None:
                exit_px = max(hit.o, pos["tp"]) if hit.t > day0 else pos["tp"]
                reason = f"TP +{tp * 100:.0f}% kena"
            elif now >= dl:
                last = [b for b in bars if b.t + DAY <= dl] or [b for b in bars if b.t + DAY <= now]
                exit_px = last[-1].c if last else bars[-1].c
                reason = f"{days} hari habis"
            if reason:
                r = (exit_px / pos["entry"] - 1 - cost) * 100
                ev = {"type": "spot_close", "id": pos["id"], "symbol": f"{coin}/USDT", "coin": coin,
                      "entry": pos["entry"], "exit": round(exit_px, 8), "r": round(r, 2), "reason": reason,
                      "time_open": pos["time"], "time": _core.iso(now), "win": r > 0}
                head = "PROFIT" if r > 0 else "MINUS"
                text = (f"Limit jual terisi di {_px(exit_px)}." if hit is not None else
                        f"Belum kena TP setelah {days} hari: jual sekarang (patokan {_px(exit_px)}).") + \
                    f" Hasil {_pct(r)} setelah biaya. Beli {_px(pos['entry'])}."
                pub.publish(ev, text, f"🏁 CLOSE SPOT {coin}/USDT • {head} {_pct(r)}", 4, ["checkered_flag"])
                closed = ([{k: ev[k] for k in ("id", "coin", "entry", "exit", "r", "reason", "time_open", "time")}]
                          + closed)[:KEEP_CLOSED]
                del open_[coin]
                events.append(f"spot close {coin} {_pct(r)}")
                changed = True
            if time.monotonic() - started > deadline_s:
                break
        state["hour"] = hour_key

    # 2) pindai sekali sehari setelah candle harian tutup (bisa bertahap bila waktu/jatah habis)
    scan = state.get("scan") or {}
    day_key = today.strftime("%Y-%m-%d")
    if (now - today >= SCAN_AFTER and scan.get("day") != day_key) or (scan.get("day") == day_key and scan.get("todo")):
        if scan.get("day") != day_key:
            scan = {"day": day_key, "todo": list(MODEL["coins"]), "found": 0}
        try:
            btc_bars, src = fetch("BTC", 300, td_key, budget)
            btc_closed = [b for b in btc_bars if b.t + DAY <= now]
            state["source"] = src
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:120])
            btc_closed = None
        while btc_closed and scan["todo"] and time.monotonic() - started < deadline_s:
            coin = scan["todo"][0]
            try:
                bars = btc_bars if coin == "BTC" else fetch(coin, 300, td_key, budget)[0]
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc)[:120])
                if "jatah habis" in str(exc):
                    break                     # Binance gagal & jatah Twelve Data tick ini habis: lanjut tick berikutnya
                scan["todo"].pop(0)           # koin ini dilewati hari ini
                continue
            scan["todo"].pop(0)
            cl = [b for b in bars if b.t + DAY <= now]
            price = bars[-1].c
            prices[coin] = price
            x = features(cl, btc_closed)
            if x is None:
                continue
            p = prob(x)
            rule = red_rule(x)
            closed_today = any(x["coin"] == coin and x["time"][:10] == day_key for x in closed)
            if (p < thr and not rule) or coin in open_ or closed_today or len(open_) >= max_open:
                continue
            dl = today + days * DAY
            sid = f"SPOT-{coin}-{day_key.replace('-', '')}"
            pos = {"id": sid, "coin": coin, "entry": price, "tp": round(price * (1 + tp), 8), "p": round(p * 100, 1),
                   "time": _core.iso(now), "day": _core.iso(today), "deadline": _core.iso(dl),
                   "alasan": "model + 3 merah" if p >= thr and rule else "model" if p >= thr else "3 merah"}
            open_[coin] = pos
            st = MODEL.get("teruji", {}).get("baru", {})
            ev = {"type": "spot_signal", "id": sid, "symbol": f"{coin}/USDT", "coin": coin, "entry": price,
                  "tp": pos["tp"], "tp_pct": round(tp * 100, 1), "p": pos["p"], "days": days,
                  "deadline": pos["deadline"], "time": pos["time"], "alasan": pos["alasan"], "teruji": st,
                  "source": state.get("source")}
            text = (f"Alasan: {pos['alasan']}. Beli spot ±{_px(price)}, lalu pasang limit jual {_px(pos['tp'])} "
                    f"(+{tp * 100:.0f}%). "
                    f"Belum kena sampai {_wib(dl)} → jual. Maks {100 // max(max_open, 1)}% modal spot. "
                    + (f"Teruji sejak 2021: naik {st.get('wr', 0):.0f}% sinyal, rata {_pct(st.get('avg', 0))}, "
                       f"rugi rata {_pct(st.get('kalah', 0))}." if st else ""))
            pub.publish(ev, text, f"💎 BELI SPOT {coin}/USDT • peluang naik {p * 100:.0f}%", 4, ["gem"])
            events.append(f"spot BELI {coin} p {p * 100:.0f}%")
            scan["found"] = scan.get("found", 0) + 1
            changed = True
        if not scan["todo"]:
            changed = True                   # pindai selesai -> kirim ringkasan
        state["scan"] = scan

    # 3) ringkasan untuk kartu 💎 di aplikasi
    last_status = state.get("status_at")
    due = open_ and (not last_status or now - _core.parse_iso(last_status) >= STATUS_EVERY)
    state.update({"open": open_, "closed": closed, "prices": prices,
                  "error": "; ".join(errors)[:300] if errors else None})
    if changed or due:
        pub.publish({"type": "spot_status", "time": _core.iso(now), "open": [
            {**p, "price": prices.get(c)} for c, p in open_.items()], "closed": closed[:20],
            "scan_day": scan.get("day"), "found": scan.get("found", 0), "scan_left": len(scan.get("todo") or []), "source": state.get("source"),
            "tp_pct": round(tp * 100, 1), "days": days, "ambang": round(thr * 100), "max_open": max_open,
            "teruji": MODEL.get("teruji", {}), "error": state["error"]})
        state["status_at"] = _core.iso(now)
    store.save_state(state)
    return {"ok": not errors, "open": len(open_), "events": events, "errors": errors[:5],
            "scan_left": len(scan.get("todo") or [])}
