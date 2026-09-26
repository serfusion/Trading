"""Skema F-ensemble: 3 set parameter Donchian H1, masing-masing dengan manajemen posisi F.

Per sinyal (per set): posisi dipecah jadi `legs` bagian (default 5).
- Leg #1 memakai TP1 = entry +/- tp1_r x R (default 1R); leg lain tanpa TP (runner).
- Setelah TP1 tersentuh -> SL semua leg sisa dipindah ke entry +/- be_offset (SL+).
- Semua leg ditutup saat close H1 menembus channel exit (sinyal TUTUP) atau SL.

Pengaman: magic number per set, kunci sinyal dicatat SEBELUM order dikirim (anti dobel
walau restart), tidak buka bila masih ada posisi di set tsb, batas order per menit,
state disimpan ke file (tahan restart) dan posisi "yatim" diadopsi kembali.
"""
from __future__ import annotations

import json
import time as _time
from collections import deque
from dataclasses import replace
from pathlib import Path

import pandas as pd

from .models import Direction, Tick
from .risk import lot_size, round_volume
from .sessions import fmt_wib
from .trend import TrendStrategy


def leg_plan(total: float, legs: int, vol_min: float, step: float) -> tuple[int, float]:
    """Bagi volume total ke beberapa leg dengan lot minimum. Return (jumlah_leg, lot_per_leg)."""
    n = max(1, min(legs, int(total / vol_min + 1e-9)))
    per = max(vol_min, round(int(total / n / step + 1e-9) * step, 8))
    return n, per


def f_result(legs: int, entry: float, risk: float, sign: int, tp1_hit: bool, exit_price: float,
             tp1_r: float) -> float:
    """R rata-rata per leg untuk skema F."""
    exit_r = (exit_price - entry) * sign / risk if risk else 0.0
    if legs >= 2 and tp1_hit:
        return (tp1_r + (legs - 1) * exit_r) / legs
    return exit_r


class OrderThrottle:
    """Batas jumlah order per menit (hindari spam order ke broker)."""

    def __init__(self, per_minute: int, clock=None):
        self.per_minute = per_minute
        self.clock = clock or (lambda: _time.monotonic())
        self.sent: deque = deque()

    def _now(self) -> float:
        t = self.clock()
        return t.timestamp() if hasattr(t, "timestamp") else float(t)

    def allow(self, count: int = 1) -> bool:
        now = self._now()
        while self.sent and now - self.sent[0] > 60:
            self.sent.popleft()
        return len(self.sent) + count <= self.per_minute

    def record(self) -> None:
        self.sent.append(self._now())


class TrendSystem:
    def __init__(self, engine, idx: int, entry: int, exit_: int):
        self.e = engine
        tc = engine.cfg.trend
        self.cfg = replace(tc, entry_period=int(entry), exit_period=int(exit_))
        self.strategy = TrendStrategy(self.cfg)
        self.name = f"T{entry}/{exit_}"
        self.magic = engine.cfg.broker.magic + tc.magic_offset + 10 + idx
        self.path = Path(tc.state_dir) / f"trend_{entry}_{exit_}.json"
        self.state: dict | None = self._load()
        self.last_bar: pd.Timestamp | None = None
        self.last_skip: tuple | None = None

    # ---------------------------------------------------------------- state
    def _load(self) -> dict | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            data["dir"] = Direction[data["dir"]]
            return data
        except (OSError, ValueError, KeyError):
            return None

    def _save(self, value: dict | None) -> None:
        self.state = value
        if value is None:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({**value, "dir": value["dir"].name}, default=str), encoding="utf-8")

    def positions(self):
        return self.e.broker.positions(self.e.symbol, self.magic)

    # ----------------------------------------------------------- manajemen
    def manage(self, now, tick: Tick, lo: float, hi: float) -> None:
        if self.e.cfg.trade_enabled:
            self._manage_live(now, tick, lo, hi)
        else:
            self._manage_virtual(now, tick, lo, hi)

    def _tp1_reached(self, st: dict, tick: Tick, lo: float, hi: float) -> bool:
        if st["dir"] == Direction.BUY:
            return max(hi, tick.bid) >= st["tp1"]
        return min(lo, tick.bid) + tick.spread <= st["tp1"]

    def _be_price(self, st: dict) -> float:
        return st["entry"] + int(st["dir"]) * self.e.cfg.risk.be_offset

    def _manage_live(self, now, tick: Tick, lo: float, hi: float) -> None:
        positions = self.positions()
        st = self.state
        if st is None and positions:
            # posisi yatim (state hilang) -> adopsi supaya tetap dikelola
            p0 = positions[0]
            tp_legs = [p for p in positions if p.tp]
            risk = abs(p0.price_open - p0.sl) if p0.sl else 0.0
            st = {"key": f"ADOPT-{self.name}-{p0.ticket}", "dir": p0.direction, "entry": p0.price_open,
                  "sl": p0.sl, "risk": risk, "tp1": tp_legs[0].tp if tp_legs else
                  p0.price_open + int(p0.direction) * self.cfg.tp1_r * risk,
                  "legs": len(positions), "be_done": bool(p0.sl) and (p0.sl - p0.price_open) * int(p0.direction) >= 0,
                  "tp1_hit": False, "time": now}
            self._save(st)
            self.e.log(f"{self.name}: {len(positions)} posisi diadopsi kembali")
        if st is None:
            return
        if not positions:
            self.e.log(f"{self.name}: semua posisi {st['dir'].label} sudah tertutup (SL/TP/manual)")
            self._save(None)
            return
        if st.get("be_done"):
            return
        leg_tp_closed = st["legs"] >= 2 and len(positions) < st["legs"]
        if leg_tp_closed or self._tp1_reached(st, tick, lo, hi):
            be = self._be_price(st)
            price = tick.bid if st["dir"] == Direction.BUY else tick.ask
            sign = int(st["dir"])
            if (price - be) * sign <= self.e.spec.min_stop_distance:
                return  # harga sudah balik ke dekat entry; coba lagi nanti
            ok = True
            for p in positions:
                if p.sl and (be - p.sl) * sign <= 0:
                    continue  # SL sudah lebih baik
                if not self.e.throttle.allow():
                    ok = False
                    break
                res = self.e.broker.modify_position(self.e.symbol, p.ticket, be, p.tp)
                self.e.throttle.record()
                ok = ok and res.ok
            if ok:
                st["be_done"], st["tp1_hit"] = True, True
                self._save(st)
                text = f"🛡️ {self.name} TP1 tercapai -> SL {len(positions)} posisi dipindah ke {be:.2f} (SL+)"
                self.e.log(text, notify=True)
                self.e.publisher.publish({"type": "info", "time": now, "id": st["key"], "set": self.name,
                                          "text": text}, text, "SL+ aktif", 4, ["shield"])

    def _manage_virtual(self, now, tick: Tick, lo: float, hi: float) -> None:
        st = self.state
        if st is None:
            return
        sign = int(st["dir"])
        sl_hit = lo <= st["sl"] if sign > 0 else hi + tick.spread >= st["sl"]
        if sl_hit:
            self._close_virtual(now, st["sl"], "Stop loss tersentuh" if not st.get("be_done")
                                else "SL+ (break-even) tersentuh")
            return
        if not st.get("be_done") and self._tp1_reached(st, tick, lo, hi):
            st["be_done"], st["tp1_hit"] = True, True
            st["sl"] = self._be_price(st)
            self._save(st)
            text = (f"🎯 {self.name} TP1 {st['tp1']:.2f} kena ({st['dir'].label})\n"
                    f"➡️ Tutup posisi #1, pindahkan SL posisi lain ke {st['sl']:.2f} (SL+)")
            self.e.log(text.replace("\n", " | "), notify=self.e.cfg.signals_enabled)
            self.e.publisher.publish({"type": "info", "time": now, "id": st["key"], "set": self.name,
                                      "text": text}, text, "TP1 + SL+", 5, ["dart"])

    def _close_virtual(self, now, price: float, why: str) -> None:
        st = self.state
        sign = int(st["dir"])
        r = f_result(st["legs"], st["entry"], st["risk"], sign, st.get("tp1_hit", False), price,
                     self.cfg.tp1_r)
        points = (price - st["entry"]) * sign
        text = (f"🏁 TUTUP {st['dir'].label} {self.e.symbol} [{self.name}] @ {price:.2f}\n"
                f"Entry {st['entry']:.2f} -> {points:+.2f} poin | hasil skema F {r:+.2f}R\nAlasan: {why}")
        self.e.log(text.replace("\n", " | "), notify=self.e.cfg.signals_enabled)
        self.e.publisher.publish({"type": "close", "id": st["key"], "time": now, "mode": "trend",
                                  "set": self.name, "dir": st["dir"].label, "entry": st["entry"],
                                  "price": round(price, 3), "points": round(points, 3), "r": round(r, 3),
                                  "risk_points": round(st["risk"], 3), "legs": st["legs"],
                                  "tp1_hit": st.get("tp1_hit", False), "reason": why},
                                 text, "Sinyal TUTUP posisi", 5, ["checkered_flag"])
        self._save(None)

    # --------------------------------------------------------------- sinyal
    def on_bar(self, now, tick: Tick, account, bars: pd.DataFrame) -> None:
        if bars.empty or bars.index[-1] == self.last_bar:
            return
        self.last_bar = bars.index[-1]
        live = self.e.cfg.trade_enabled
        positions = self.positions() if live else []
        current = self.state["dir"] if self.state else (positions[0].direction if positions else None)
        sig = self.strategy.evaluate(bars, current)
        if sig.action == "close":
            self._exit(now, tick, positions, sig.note)
        elif sig.action == "open" and current is None and not positions:
            self._open(now, tick, account, bars, sig)

    def _exit(self, now, tick: Tick, positions, why: str) -> None:
        if not self.e.cfg.trade_enabled:
            if self.state:
                price = tick.bid if self.state["dir"] == Direction.BUY else tick.ask
                self._close_virtual(now, price, why)
            return
        total = 0.0
        for p in positions:
            res = self.e.broker.close_position(self.e.symbol, p.ticket)
            self.e.throttle.record()
            if res.ok:
                total += p.profit
        if positions:
            text = f"🏁 {self.name} {positions[0].direction.label} ditutup ({len(positions)} posisi): {why} " \
                   f"(PnL {self.e.money(total)})"
            self.e.log(text, notify=True)
            st = self.state or {}
            self.e.publisher.publish({"type": "close", "id": st.get("key", self.name),
                                      "time": now, "mode": "trend", "set": self.name,
                                      "dir": positions[0].direction.label, "price": tick.bid, "pnl": total,
                                      "currency": self.e.currency, "reason": why},
                                     text, "Posisi ditutup", 4, ["checkered_flag"])
        self._save(None)

    def _open(self, now, tick: Tick, account, bars: pd.DataFrame, sig) -> None:
        e, cfg = self.e, self.cfg
        direction = sig.direction
        sign = int(direction)
        key = f"{self.name}-{direction.label}-{bars.index[-1]:%Y%m%d%H%M}"
        if e.journal.has_key(key):
            return  # sinyal ini sudah pernah diproses (mis. setelah restart)
        entry = tick.ask if direction == Direction.BUY else tick.bid
        risk = cfg.stop_atr * sig.atr
        sl = entry - sign * risk
        tp1 = entry + sign * cfg.tp1_r * risk
        spec = e.spec
        reason = e._trend_block_reason(now, tick, account)
        n_legs, per_leg, warn, risk_money = 0, 0.0, "", 0.0
        money_per_lot = abs(entry - sl) * spec.tick_value / spec.tick_size
        if reason is None and cfg.fixed_leg_lot > 0:
            n_legs, per_leg = cfg.legs, round_volume(max(cfg.fixed_leg_lot, spec.volume_min), spec)
            risk_money = n_legs * per_leg * money_per_lot
            pct = risk_money / account.balance * 100 if account.balance else 999
            if pct > cfg.max_risk_pct_per_set:
                msg = f"Lot tetap {n_legs}x{per_leg} = risiko {pct:.1f}% > batas {cfg.max_risk_pct_per_set}%"
                if e.cfg.trade_enabled:
                    reason = msg
                else:
                    warn = f"⚠️ {msg}"
            if reason is None and e.cfg.trade_enabled and not e.throttle.allow(n_legs):
                reason = "Batas order per menit tercapai"
        elif reason is None:
            total, risk_money, note = lot_size(account.balance, cfg.risk_pct_per_set, entry, sl, spec,
                                               e.cfg.risk.allow_min_lot_over_risk)
            if total <= 0:
                if e.cfg.trade_enabled:
                    reason = note
                else:
                    total = spec.volume_min
                    risk_money = abs(entry - sl) * total * spec.tick_value / spec.tick_size
                    warn = f"⚠️ Lot minimum {total} = risiko {risk_money / account.balance * 100:.1f}% saldo"
            if reason is None:
                n_legs, per_leg = leg_plan(total, cfg.legs, spec.volume_min, spec.volume_step)
                per_leg = round_volume(per_leg, spec)
                if e.cfg.trade_enabled and not e.throttle.allow(n_legs):
                    reason = "Batas order per menit tercapai"
        icon = "🟢" if direction == Direction.BUY else "🔴"
        lines = [
            f"{icon} TREND {direction.label} {e.symbol} [{self.name}] skema F",
            f"Entry: {entry:.2f} | SL: {sl:.2f} ({cfg.stop_atr}x ATR {sig.atr:.2f})",
            f"TP1: {tp1:.2f} ({cfg.tp1_r}R) untuk posisi #1; posisi lain hold sampai sinyal TUTUP",
            "Setelah TP1 kena -> SL semua posisi sisa ke entry (SL+)",
            f"Alasan: {sig.note}",
        ]
        event = {"type": "signal", "id": key, "time": now, "mode": "trend", "set": self.name,
                 "dir": direction.label, "symbol": e.symbol, "entry": round(entry, 3), "sl": round(sl, 3),
                 "tp": round(tp1, 3), "tp1": round(tp1, 3), "atr": round(sig.atr, 3), "reason": sig.note,
                 "exit_rule": f"close {cfg.timeframe} menembus channel {cfg.exit_period} bar"}
        if reason is not None:
            if self.last_skip != (direction, reason):
                self.last_skip = (direction, reason)
                e.log(f"{self.name} sinyal {direction.label} dilewati: {reason}")
                e.publisher.publish({**event, "status": "skipped", "note": reason},
                                    "\n".join(lines + [f"⛔ Dilewati: {reason}"]), "Sinyal dilewati", 2)
            return
        self.last_skip = None
        e.journal.add_key(key, now)  # dicatat SEBELUM order -> tidak mungkin dobel
        pct_text = f"{risk_money / account.balance * 100:.2f}%" if account.balance else "-"
        lines.append(f"Lot: {n_legs} x {per_leg} | risiko {e.money(risk_money)} ({pct_text} saldo)")
        if warn:
            lines.append(warn)
        event.update(lot=f"{n_legs}x{per_leg}", legs=n_legs, leg_lot=per_leg, risk=round(risk_money, 2),
                     risk_points=round(risk, 3), currency=e.currency, warning=warn)
        state = {"key": key, "dir": direction, "entry": entry, "sl": sl, "risk": risk, "tp1": tp1,
                 "legs": n_legs, "be_done": False, "tp1_hit": False, "time": now}
        tags = ["green_circle" if direction == Direction.BUY else "red_circle"]
        if not e.cfg.trade_enabled:
            e.log(f"Sinyal {self.name} {direction.label} {entry:.2f} (mode sinyal)")
            if e.cfg.signals_enabled:
                e.notifier.send("\n".join(lines + ["Status: 📡 Sinyal (auto-trade OFF)"]))
            e.publisher.publish({**event, "status": "signal"}, "\n".join(lines), f"{direction.label} XAUUSD", 5, tags)
            self._save(state)
            return
        opened = 0
        for i in range(n_legs):
            tp = tp1 if (i == 0 and n_legs >= 2) else 0.0
            res = e.broker.market_order(e.symbol, direction, per_leg, sl, tp, self.magic,
                                        f"{self.name} {direction.label} L{i + 1}")
            e.throttle.record()
            if not res.ok:
                e.log(f"{self.name} leg {i + 1} gagal: {res.message}", "WARNING")
                break
            opened += 1
        if opened:
            state["legs"] = opened
            if opened < 2:
                state["tp1_hit"] = False
            self._save(state)
        status = (f"✅ {opened}/{n_legs} posisi terbuka" if opened else "❌ Order ditolak broker, cek log")
        e.log(f"{self.name} {direction.label} {opened}x{per_leg} @ {entry:.2f} SL {sl:.2f} TP1 {tp1:.2f}: {status}")
        e.notifier.send("\n".join(lines + [f"Status: {status}", f"Waktu: {fmt_wib(now)}"]))
        e.publisher.publish({**event, "status": "opened" if opened else "failed", "note": status, "legs": opened},
                            "\n".join(lines + [status]), f"{direction.label} XAUUSD", 5, tags)
