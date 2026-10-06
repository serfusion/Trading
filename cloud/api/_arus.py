"""🌊 Ikut arus setelah gerakan cepat (research/pisau.py, docs/PISAU.md; izin pengguna 6 Okt 2026 "ikuti arus dengan
catatan WR dan profit tinggi"). Hanya varian dengan WR ≥ 62% di LAMA & BARU dan ≥ 79% tahun positif:
  XAU  melonjak ≥ 4 ATR24 dalam 3 jam, harga di atas EMA H1 1200 → BUY STOP 0,1 ATR di atas high candle kejadian
       (berlaku 6 jam), SL 3 ATR, TP 2 ATR, maks 48 jam.
  BTC  melonjak ≥ 6 ATR24 dalam 12 jam → BUY pasar, SL 3 ATR, TP = 38% gerakan di atas close kejadian, maks 48 jam.
  ETH  jatuh ≥ 5 ATR24 dalam 6 jam, harga di bawah EMA H1 1200 → SELL pasar, SL 3 ATR, TP 2 ATR, maks 12 jam.
Candle H1 yang SUDAH tutup saja (sama dengan riset: keputusan di close, entry di open berikutnya). Info saja, tanpa
order otomatis. State: baris Supabase 'arus'. Pesan ntfy: arus_signal, arus_close, arus_cancel.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import _core

H1 = timedelta(hours=1)
RULES = {
    "XAU": {"symbol": "XAU/USD", "move": 1, "n": 3, "k": 4.0, "mode": "stop", "tren": "searah", "sl": 3.0, "tp": 2.0,
            "h": 48, "teruji": {"lama": [93, 72, 0.20], "baru": [71, 69, 0.16], "tahun": "13/14 tahun +"}},
    "BTC": {"symbol": "BTC/USD", "move": 1, "n": 12, "k": 6.0, "mode": "pasar", "tren": "semua", "sl": 3.0,
            "tp": "r38", "h": 48, "teruji": {"lama": [160, 63, 0.16], "baru": [185, 62, 0.12], "tahun": "11/11 tahun +"}},
    "ETH": {"symbol": "ETH/USD", "move": -1, "n": 6, "k": 5.0, "mode": "pasar", "tren": "searah", "sl": 3.0, "tp": 2.0,
            "h": 12, "teruji": {"lama": [50, 64, 0.18], "baru": [94, 64, 0.19], "tahun": "8/9 tahun +"}},
}
KEEP_CLOSED = 20


def _atr(bars: list[_core.Bar], n: int = 24) -> list[float]:
    """Sama dengan research.strategy_lab.atr: EWMA alpha 1/n dari true range."""
    out, a = [], None
    for i, b in enumerate(bars):
        pc = bars[i - 1].c if i else b.c
        tr = max(b.h - b.l, abs(b.h - pc), abs(b.l - pc))
        a = tr if a is None else a + (tr - a) / n
        out.append(a)
    return out


def _ema(x: list[float], span: int) -> list[float]:
    k, out, e = 2 / (span + 1), [], None
    for v in x:
        e = v if e is None else e + k * (v - e)
        out.append(e)
    return out


def _size(bars, atr, i, n, move) -> float:
    w = bars[i - n + 1:i + 1]
    if move < 0:
        return (max(b.h for b in w) - bars[i].c) / atr[i]
    return (bars[i].c - min(b.l for b in w)) / atr[i]


def _fmt(sym: str, v: float) -> str:
    return f"{v:,.2f}"


def arus_tick(now: datetime, feeds: dict, store, pub) -> dict:
    """feeds: aset -> daftar Bar H1 (boleh termasuk candle berjalan). Aman dipanggil berulang (idempoten)."""
    state = store.get_state() or {}
    closed_log = state.get("closed") or []
    events = []
    for asset, rule in RULES.items():
        bars = feeds.get(asset)
        if not bars:
            continue
        bars = [b for b in bars if b.h > b.l and (asset != "XAU" or _core.market_open(b.t))]
        done = [b for b in bars if b.t + H1 <= now]
        if len(done) < 1300:
            continue
        st = state.get(asset) or {}
        atr = _atr(done)
        ema = _ema([b.c for b in done], 1200)
        last_seen = st.get("last_bar")
        new_idx = [i for i, b in enumerate(done) if last_seen is None or _core.iso(b.t) > last_seen]
        if last_seen is None:
            new_idx = new_idx[-1:]                     # pertama kali: hanya candle terakhir, tanpa mengulang riwayat
        sym, n, move, d = rule["symbol"], rule["n"], rule["move"], rule["move"]
        for i in new_idx:
            b = done[i]
            # 1) posisi / order tertunda yang sudah ada
            pend, pos = st.get("pending"), st.get("open")
            if pend and _core.parse_iso(pend["valid_until"]) >= b.t:
                hit = b.h >= pend["level"] if d > 0 else b.l <= pend["level"]
                if hit:
                    px = max(b.o, pend["level"]) if d > 0 else min(b.o, pend["level"])
                    a = pend["atr"]
                    pos = {"id": pend["id"], "entry": px, "sl": px - d * rule["sl"] * a, "tp": px + d * rule["tp"] * a,
                           "fill": _core.iso(b.t), "deadline": _core.iso(b.t + rule["h"] * H1), "first": True}
                    st["open"], st["pending"] = pos, None
                    pub.publish({"type": "arus_fill", "id": pos["id"], "symbol": sym, "dir": "BUY" if d > 0 else "SELL",
                                 "entry": round(px, 2), "sl": round(pos["sl"], 2), "tp": round(pos["tp"], 2),
                                 "time": _core.iso(now)})
            elif pend:
                pub.publish({"type": "arus_cancel", "id": pend["id"], "symbol": sym, "time": _core.iso(now),
                             "reason": "stop order tidak tersentuh 6 jam"},
                            f"Hapus pending {'BUY' if d > 0 else 'SELL'} STOP {sym} {_fmt(sym, pend['level'])}.",
                            f"🌊 BATAL {sym}", 3, ["wave"])
                st["pending"] = None
                events.append(f"{asset} batal")
            pos = st.get("open")
            if pos and _core.iso(b.t) >= pos["fill"]:
                first = pos.get("first") and _core.iso(b.t) == pos["fill"]
                ex = why = None
                if (b.l <= pos["sl"]) if d > 0 else (b.h >= pos["sl"]):
                    ex = pos["sl"] if first else (min(b.o, pos["sl"]) if d > 0 else max(b.o, pos["sl"]))
                    why = "SL"
                elif not first and ((b.h >= pos["tp"]) if d > 0 else (b.l <= pos["tp"])):
                    ex, why = pos["tp"], "TP"
                elif b.t + H1 >= _core.parse_iso(pos["deadline"]):
                    ex, why = b.c, f"{rule['h']} jam habis"
                pos["first"] = False
                if ex is not None:
                    r = (ex - pos["entry"]) * d / abs(pos["entry"] - pos["sl"])
                    ev = {"type": "arus_close", "id": pos["id"], "symbol": sym, "dir": "BUY" if d > 0 else "SELL",
                          "entry": round(pos["entry"], 2), "exit": round(ex, 2), "r": round(r, 2), "reason": why,
                          "win": r > 0, "time": _core.iso(now)}
                    pub.publish(ev, f"Tutup {ev['dir']} {sym} @ {_fmt(sym, ex)} ({why}). Hasil {r:+.2f}R.",
                                f"🌊 TUTUP {sym} • {'PROFIT' if r > 0 else 'MINUS'}", 4, ["wave"])
                    closed_log = ([ev] + closed_log)[:KEEP_CLOSED]
                    st["open"] = None
                    events.append(f"{asset} tutup {why}")
            # 2) kejadian baru di candle i
            if i < n + 1 or st.get("open") or st.get("pending"):
                continue
            size, prev = _size(done, atr, i, n, move), _size(done, atr, i - 1, n, move)
            last_ev = st.get("last_ev")
            cool = last_ev is None or b.t - _core.parse_iso(last_ev) >= n * H1
            trend = 1 if b.c > ema[i] else -1
            if size < rule["k"] or prev >= rule["k"] or not cool:
                continue
            st["last_ev"] = _core.iso(b.t)
            if rule["tren"] == "searah" and trend != d:
                continue
            a = atr[i]
            sid = f"ARUS-{asset}-{b.t:%Y%m%d%H}"
            t1 = rule["teruji"]
            stats = (f"Teruji: WR {t1['lama'][1]}% sebelum Okt 2021, {t1['baru'][1]}% sejak itu "
                     f"(+{t1['baru'][2]:.2f}R/sinyal), {t1['tahun']}.")
            dname = "BUY" if d > 0 else "SELL"
            if rule["mode"] == "stop":
                level = b.h + 0.1 * a if d > 0 else b.l - 0.1 * a
                st["pending"] = {"id": sid, "level": level, "atr": a, "valid_until": _core.iso(b.t + 6 * H1)}
                ev = {"type": "arus_signal", "id": sid, "symbol": sym, "dir": dname, "order": "stop",
                      "entry": round(level, 2), "sl": round(level - d * rule["sl"] * a, 2),
                      "tp": round(level + d * rule["tp"] * a, 2), "valid_until": _core.iso(b.t + 7 * H1),
                      "hold_h": rule["h"], "move_atr": round(size, 1), "teruji": t1, "time": _core.iso(now)}
                text = (f"Pasang {dname} STOP {_fmt(sym, level)} (berlaku 6 jam), SL {_fmt(sym, ev['sl'])}, "
                        f"TP {_fmt(sym, ev['tp'])}, maks {rule['h']} jam. {stats}")
            else:
                # open candle berjalan (= entry riset: open candle setelah kejadian; cron jalan menit :02)
                entry = bars[-1].o if bars[-1].t > b.t else b.c
                ext = (min(x.l for x in done[i - n + 1:i + 1]) if move > 0 else max(x.h for x in done[i - n + 1:i + 1]))
                if rule["tp"] == "r38":
                    tp = b.c + (b.c - ext) * 0.382
                    if (tp - entry) * d <= 0.1 * a:
                        tp = entry + d * 0.1 * a
                else:
                    tp = entry + d * rule["tp"] * a
                sl = entry - d * rule["sl"] * a
                st["open"] = {"id": sid, "entry": entry, "sl": sl, "tp": tp, "fill": _core.iso(b.t + H1),
                              "deadline": _core.iso(b.t + H1 + rule["h"] * H1), "first": True}
                ev = {"type": "arus_signal", "id": sid, "symbol": sym, "dir": dname, "order": "pasar",
                      "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                      "deadline": st["open"]["deadline"], "hold_h": rule["h"], "move_atr": round(size, 1),
                      "teruji": t1, "time": _core.iso(now)}
                text = (f"{dname} sekarang ±{_fmt(sym, entry)}, SL {_fmt(sym, sl)}, TP {_fmt(sym, tp)}, "
                        f"tutup paling lambat {rule['h']} jam. {stats}")
            why = "melonjak" if move > 0 else "jatuh"
            pub.publish(ev, text, f"🌊 IKUT ARUS {dname} {sym} • {why} {size:.1f} ATR", 4, ["wave"])
            events.append(f"{asset} sinyal {dname}")
        st["last_bar"] = _core.iso(done[-1].t)
        state[asset] = st
    state["closed"] = closed_log
    store.save_state(state)
    return {"ok": True, "events": events}
