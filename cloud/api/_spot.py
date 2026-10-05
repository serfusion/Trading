"""💎 Sinyal SPOT Binance: peluang naik lagi (research/spot_peluang.py; pindai tiap tick: research/spot_pindai.py).

Permintaan pengguna 4 Okt 2026 (sinyal & close spot) dan 5 Okt 2026 (URGENT: "dipindai beberapa menit, bukan per hari,
koinnya bukan hanya 20"). Tiap tick cloud (10 menit): ambil daftar koin USDT Binance dengan volume 24 jam terbesar
(bawaan 100 koin, tanpa stablecoin/token pembungkus), candle harian tiap koin (paralel); candle hari ini yang masih
berjalan dipakai sebagai candle terakhir (harga sekarang = close) -> fitur -> peluang "harga menyentuh +TP% dalam N hari"
dari model gradient boosting (spot_model.json: pohon diekspor, dievaluasi tanpa pustaka). Sinyal = peluang >= ambang
ATAU aturan 3 merah, dan BTC di atas SMA200 (filter teruji; BTC di bawah SMA200 -> spot dijeda). Posisi dicek tiap tick
dengan candle 15 menit SETELAH entry: high menyentuh TP -> CLOSE (limit jual terisi); N hari lewat -> CLOSE.
Hanya informasi: cloud TIDAK membuka order spot.

Data: data-api.binance.vision -> api.binance.us -> Twelve Data (hanya candle harian, maks 4 kredit per tick; Vercel di
AS, api.binance.com menolak AS 451). State: baris Supabase 'spot'. Pesan ntfy: spot_signal, spot_close (notifikasi),
spot_status (kartu 💎).
"""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _core

_PATH = Path(__file__).resolve().parent / "spot_model.json"
MODEL = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
DAY = timedelta(days=1)
M15 = timedelta(minutes=15)
KEEP_CLOSED = 30
STATUS_EVERY = timedelta(minutes=30)
COOLDOWN = timedelta(hours=1)           # setelah CLOSE: koin yang sama paling cepat 1 jam lagi (riset: jam berikutnya)
BARS = 260                              # SMA200 + RSI stabil
WORKERS = 16
UNIVERSE_EVERY = timedelta(hours=6)
BINANCE = ("https://data-api.binance.vision", "https://api.binance.us")
# bukan koin kripto bergerak bebas: stablecoin, fiat, emas tokenisasi, token pembungkus/staking
SKIP = {"USDT", "USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "USDE", "PYUSD", "RLUSD", "USD1", "BFUSD", "XUSD",
        "USDS", "FRAX", "LUSD", "GUSD", "UST", "USTC", "USDD", "SUSD", "USDJ", "EURC", "EUR", "EURI", "AEUR", "GBP",
        "TRY", "BRL", "AUD", "JPY", "ARS", "MXN", "ZAR", "PLN", "RON", "UAH", "IDRT", "BIDR", "BVND", "PAXG", "XAUT",
        "WBTC", "WBETH", "BETH", "STETH", "WSTETH", "BNSOL", "CBETH", "RETH", "WETH"}
_LOCK = threading.Lock()


# ------------------------------------------------------------------ data
def _bars(rows) -> list[_core.Bar]:
    return [_core.Bar(datetime.fromtimestamp(r[0] / 1000, timezone.utc), float(r[1]), float(r[2]), float(r[3]),
                      float(r[4])) for r in rows or []]


def _binance(base: str, coin: str, n: int, interval: str = "1d", start: datetime | None = None) -> list[_core.Bar]:
    q = {"symbol": f"{coin}USDT", "interval": interval, "limit": n}
    if start is not None:
        q["startTime"] = int(start.timestamp() * 1000)
    return _bars(_core.http("GET", f"{base}/api/v3/klines?{urllib.parse.urlencode(q)}", timeout=10))


SOURCES = (
    ("binance", lambda coin, n, key: _binance(BINANCE[0], coin, n)),
    ("binance.us", lambda coin, n, key: _binance(BINANCE[1], coin, n)),
    ("twelvedata", lambda coin, n, key: _core.TwelveData(key, f"{coin}/USD").candles(n, "1day") if key else []),
)


def klines(coin: str, n: int, td_key: str | None, budget: dict) -> tuple[list[_core.Bar], str]:
    """Candle harian (termasuk candle hari ini yang masih berjalan) dari sumber pertama yang berhasil."""
    errors = []
    for name, fn in SOURCES:
        if name == "twelvedata":
            with _LOCK:                       # dipanggil paralel: jatah Twelve Data dibagi aman antar-thread
                ok = budget.get("td", 0) > 0
                if ok:
                    budget["td"] -= 1
            if not ok:
                errors.append("twelvedata: jatah habis")
                continue
        try:
            bars = fn(coin, n, td_key)
            if len(bars) >= 2:
                return bars, name
            errors.append(f"{name}: kosong")
        except Exception as exc:  # noqa: BLE001 - coba sumber berikutnya
            errors.append(f"{name}: {str(exc)[:60]}")
    raise RuntimeError(f"{coin}: " + "; ".join(errors))


def klines_15m(coin: str, start: datetime) -> list[_core.Bar]:
    """Candle 15 menit sejak [start] (maks 1000 = 10,4 hari) untuk cek TP setelah entry."""
    errors = []
    for base in BINANCE:
        try:
            bars = _binance(base, coin, 1000, "15m", start)
            if bars:
                return bars
            errors.append(f"{base[8:]}: kosong")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{base[8:]}: {str(exc)[:60]}")
    raise RuntimeError(f"{coin} 15m: " + "; ".join(errors))


def pick_coins(rows: list[dict], top: int, min_vol: float) -> list[str]:
    """Pair USDT dengan volume 24 jam (USDT) terbesar, tanpa stablecoin/fiat/token pembungkus/token leverage."""
    vol = {}
    for r in rows:
        sym = str(r.get("symbol", ""))
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        try:
            v = float(r.get("quoteVolume") or 0)
        except (TypeError, ValueError):
            continue
        if base and base not in SKIP and v >= min_vol:
            vol[base] = v
    for base in list(vol):                   # token leverage lama: BTCUP, ETHDOWN, ... (JUP tetap: J bukan koin)
        for suf in ("UP", "DOWN", "BULL", "BEAR"):
            if base.endswith(suf) and base[:-len(suf)] in vol:
                vol.pop(base, None)
    out = sorted(vol, key=lambda b: -vol[b])[:top]
    return (["BTC"] if "BTC" not in out else []) + out


def universe(top: int, min_vol: float) -> tuple[list[str], str]:
    """Daftar koin dari ticker 24 jam Binance (sekali panggil untuk semua pair)."""
    errors = []
    for base in BINANCE:
        for q in ("?type=MINI", ""):
            try:
                rows = _core.http("GET", f"{base}/api/v3/ticker/24hr{q}", timeout=15) or []
                coins = pick_coins(rows, top, min_vol)
                if len(coins) >= 5:
                    return coins, base[8:]
                errors.append(f"{base[8:]}: hanya {len(coins)} koin")
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{base[8:]}{q}: {str(exc)[:60]}")
    raise RuntimeError("daftar koin: " + "; ".join(errors))


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
    """Fitur di close candle harian TERAKHIR. bars & btc urut waktu; candle terakhir boleh candle hari ini yang masih
    berjalan (close = harga sekarang) — diuji di research/spot_pindai.py."""
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
def _check(pos: dict, now: datetime, bars15: list[_core.Bar] | None, daily: list[_core.Bar] | None,
           price: float | None) -> tuple[str | None, float | None]:
    """(alasan, harga keluar) bila posisi selesai: TP tersentuh SETELAH entry atau batas waktu habis."""
    tp_px, entry_t, dl = pos["tp"], _core.parse_iso(pos["time"]), _core.parse_iso(pos["deadline"])
    tp_pct = MODEL["tp"] * 100
    if bars15:
        after = [b for b in bars15 if b.t >= entry_t and b.t < dl]   # candle yang mulai setelah entry
        hit = next((b for b in after if b.h >= tp_px), None)
        if hit is not None:
            return f"TP +{tp_pct:.0f}% kena", max(hit.o, tp_px)
        if now >= dl:
            last = [b for b in bars15 if b.t + M15 <= dl] or bars15
            return f"{int(MODEL['hari'])} hari habis", last[-1].c
        return None, None
    # cadangan tanpa candle 15 menit: high harian SETELAH hari entry, atau harga sekarang
    later = [b for b in daily or [] if b.t.date() > entry_t.date() and b.t < dl]
    if any(b.h >= tp_px for b in later) or (price is not None and price >= tp_px):
        return f"TP +{tp_pct:.0f}% kena", tp_px
    if now >= dl and price is not None:
        return f"{int(MODEL['hari'])} hari habis", price
    return None, None


def spot_tick(now: datetime, store, pub, td_key: str | None = None, max_open: int = 20, fetch=None,
              deadline_s: float = 20.0, coins_fn=None, fetch_15m=None, btc_filter: bool = True,
              top: int = 100, min_vol: float = 5e6) -> dict:
    """Dipanggil tiap tick cloud (10 menit): pindai semua koin dengan candle harian berjalan + cek posisi. Idempoten.
    coins_fn() -> (daftar koin, sumber); fetch(coin, n, key, budget) -> (candle harian, sumber);
    fetch_15m(coin, start) -> candle 15 menit (disuntik di tes)."""
    if not MODEL:
        return {"ok": False, "error": "spot_model.json tidak ada"}
    fetch = fetch or klines
    fetch_15m = fetch_15m or klines_15m
    coins_fn = coins_fn or (lambda: universe(top, min_vol))
    started = time.monotonic()
    state = store.get_state() or {}
    open_ = state.get("open") or {}
    closed = state.get("closed") or []
    tp, days, thr, cost = MODEL["tp"], int(MODEL["hari"]), MODEL["ambang"], MODEL.get("biaya", 0.003)
    use_btc = btc_filter and MODEL.get("btc_filter", True)
    budget = {"td": 4}
    events, errors, changed = [], [], False
    prices = state.get("prices") or {}

    # 1) daftar koin (volume 24 jam terbesar), diperbarui tiap 6 jam; gagal -> daftar lama / 20 koin model
    coins = state.get("coins") or []
    if not coins or not state.get("coins_at") or now - _core.parse_iso(state["coins_at"]) >= UNIVERSE_EVERY:
        try:
            coins, src = coins_fn()
            state.update({"coins": coins, "coins_at": _core.iso(now), "coins_src": src})
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:120])
            coins = coins or list(MODEL.get("coins") or [])
    coins = ["BTC"] + [c for c in coins if c != "BTC"]
    # koin yang tidak terpindai tick lalu (waktu habis) didahulukan
    rot = state.get("rot", 0) % max(len(coins) - 1, 1)
    order = ["BTC"] + coins[1:][rot:] + coins[1:][:rot] + [c for c in open_ if c not in coins]

    # 2) candle harian semua koin + candle 15 menit posisi terbuka, paralel dengan batas waktu
    daily: dict[str, list[_core.Bar]] = {}
    m15: dict[str, list[_core.Bar]] = {}
    pool = ThreadPoolExecutor(max_workers=WORKERS)
    futs = {pool.submit(fetch, c, BARS, td_key, budget): ("d", c) for c in order}
    for c, pos in open_.items():
        futs[pool.submit(fetch_15m, c, _core.parse_iso(pos["time"]))] = ("m", c)
    done, _pending = wait(futs, timeout=max(1.0, deadline_s - (time.monotonic() - started)))
    pool.shutdown(wait=False, cancel_futures=True)
    srcs = {}
    for f in done:
        kind, c = futs[f]
        try:
            res = f.result()
        except Exception as exc:  # noqa: BLE001
            if kind == "d" and len(errors) < 8:
                errors.append(str(exc)[:120])
            continue
        if kind == "d":
            daily[c], src = res
            srcs[src] = srcs.get(src, 0) + 1
            prices[c] = daily[c][-1].c
        else:
            m15[c] = res
            if res:
                prices[c] = res[-1].c
    scanned = [c for c in order if c in daily]
    state["rot"] = rot + max(len([c for c in coins[1:] if c in daily]), 1)
    if srcs:
        state["source"] = max(srcs, key=srcs.get)

    # 3) posisi terbuka: TP tersentuh setelah entry atau batas waktu habis
    for coin, pos in list(open_.items()):
        if coin not in m15 and coin not in daily:
            continue
        reason, exit_px = _check(pos, now, m15.get(coin), daily.get(coin), prices.get(coin))
        if not reason:
            continue
        r = (exit_px / pos["entry"] - 1 - cost) * 100
        ev = {"type": "spot_close", "id": pos["id"], "symbol": f"{coin}/USDT", "coin": coin, "entry": pos["entry"],
              "exit": round(exit_px, 8), "r": round(r, 2), "reason": reason, "time_open": pos["time"],
              "time": _core.iso(now), "win": r > 0}
        head = "PROFIT" if r > 0 else "MINUS"
        text = (f"Limit jual terisi di {_px(exit_px)}." if reason.startswith("TP") else
                f"Belum kena TP setelah {days} hari: jual sekarang (patokan {_px(exit_px)}).") + \
            f" Hasil {_pct(r)} setelah biaya. Beli {_px(pos['entry'])}."
        pub.publish(ev, text, f"🏁 CLOSE SPOT {coin}/USDT • {head} {_pct(r)}", 4, ["checkered_flag"])
        closed = ([{k: ev[k] for k in ("id", "coin", "entry", "exit", "r", "reason", "time_open", "time")}]
                  + closed)[:KEEP_CLOSED]
        del open_[coin]
        events.append(f"spot close {coin} {_pct(r)}")
        changed = True

    # 4) pindai: candle hari ini yang masih berjalan = candle terakhir (fitur "seandainya hari tutup sekarang")
    btc = daily.get("BTC")
    found = []
    btc_up = None
    if btc:
        xb = features(btc, btc)
        if xb is not None and "btc_up" in MODEL.get("fitur", []):
            btc_up = xb[MODEL["fitur"].index("btc_up")] >= 1.0      # harga BTC sekarang > SMA200 harian
        for coin in scanned:
            bars = daily[coin]
            x = features(bars, btc)
            if x is None:
                continue
            p = prob(x)
            rule = red_rule(x)
            if p < thr and not rule:
                continue
            if use_btc and btc_up is False:
                continue                                     # BTC di bawah SMA200: spot dijeda (teruji)
            last_close = next((c_ for c_ in closed if c_["coin"] == coin), None)
            if coin in open_ or len(open_) >= max_open or (
                    last_close and now - _core.parse_iso(last_close["time"]) < COOLDOWN):
                continue
            price = bars[-1].c
            dl = now + days * DAY
            sid = f"SPOT-{coin}-{now:%Y%m%d%H%M}"
            pos = {"id": sid, "coin": coin, "entry": price, "tp": round(price * (1 + tp), 8), "p": round(p * 100, 1),
                   "time": _core.iso(now), "deadline": _core.iso(dl),
                   "alasan": "model + 3 merah" if p >= thr and rule else "model" if p >= thr else "3 merah"}
            open_[coin] = pos
            st = MODEL.get("teruji", {}).get("baru", {})
            ev = {"type": "spot_signal", "id": sid, "symbol": f"{coin}/USDT", "coin": coin, "entry": price,
                  "tp": pos["tp"], "tp_pct": round(tp * 100, 1), "p": pos["p"], "days": days,
                  "deadline": pos["deadline"], "time": pos["time"], "alasan": pos["alasan"], "teruji": st,
                  "max_open": max_open, "source": state.get("source")}
            text = (f"Alasan: {pos['alasan']}. Beli spot ±{_px(price)}, lalu pasang limit jual {_px(pos['tp'])} "
                    f"(+{tp * 100:.0f}%). "
                    f"Belum kena sampai {_wib(dl)} → jual. Maks {100 // max(max_open, 1)}% modal spot. "
                    + (f"Teruji sejak Okt 2021: naik {st.get('wr', 0):.0f}% sinyal, rata {_pct(st.get('avg', 0))}, "
                       f"rugi rata {_pct(st.get('kalah', 0))}." if st else ""))
            pub.publish(ev, text, f"💎 BELI SPOT {coin}/USDT • peluang naik {p * 100:.0f}%", 4, ["gem"])
            events.append(f"spot BELI {coin} p {p * 100:.0f}%")
            found.append(coin)
            changed = True
    elif "BTC" not in daily:
        errors.insert(0, "BTC: candle harian gagal (fitur rezim BTC butuh BTC)")

    # 5) ringkasan untuk kartu 💎 di aplikasi (tiap 30 menit, atau segera bila ada BELI/CLOSE)
    state.update({"open": open_, "closed": closed, "prices": {c: v for c, v in prices.items() if c in open_},
                  "error": "; ".join(errors)[:300] if errors else None, "scan_at": _core.iso(now),
                  "scanned": len(scanned), "btc_up": btc_up})
    last_status = state.get("status_at")
    if changed or not last_status or now - _core.parse_iso(last_status) >= STATUS_EVERY:
        pub.publish({"type": "spot_status", "time": _core.iso(now), "open": [
            {**p, "price": prices.get(c)} for c, p in open_.items()], "closed": closed[:20],
            "scan_at": _core.iso(now), "scan_day": now.strftime("%Y-%m-%d"), "every_min": 10,
            "coins": len(coins), "scanned": len(scanned), "found": len(found), "btc_up": btc_up,
            "btc_filter": use_btc, "source": state.get("source"),
            "tp_pct": round(tp * 100, 1), "days": days, "ambang": round(thr * 100), "max_open": max_open,
            "teruji": MODEL.get("teruji", {}), "error": state["error"]})
        state["status_at"] = _core.iso(now)
    store.save_state(state)
    return {"ok": not errors, "open": len(open_), "events": events, "errors": errors[:5], "coins": len(coins),
            "scanned": len(scanned), "btc_up": btc_up, "s": round(time.monotonic() - started, 1)}
