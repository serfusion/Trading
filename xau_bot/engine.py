"""Engine: loop 24 jam — ambil data, cari setup, eksekusi, kelola posisi, lapor."""
from __future__ import annotations

import json
import logging
import time as _time
from collections import defaultdict, deque
from pathlib import Path
from typing import Callable

import pandas as pd

from .broker.base import Broker
from .config import AppConfig
from .journal import Journal
from .models import Direction, EngineStatus, PendingOrder, Position, Setup, Tick
from .news import NewsFilter
from .risk import RiskGuard, lot_size, split_volume
from .sessions import SessionClock, fmt_wib, trading_day
from .smc import find_swings
from .strategy import TF_MINUTES, MarketContext, SmcStrategy
from .publish import Publisher
from .telegram import Notifier
from .trend import TrendStrategy

log = logging.getLogger(__name__)


def _dir(value: str) -> Direction:
    return Direction.BUY if value == "BUY" else Direction.SELL


class Engine:
    def __init__(self, cfg: AppConfig, broker: Broker, notifier: Notifier | None = None,
                 news: NewsFilter | None = None, journal: Journal | None = None,
                 clock: Callable[[], pd.Timestamp] | None = None, publisher: Publisher | None = None):
        self.cfg = cfg
        self.publisher = publisher or Publisher()
        self.currency = "USD"
        self.cent = False
        self._last_heartbeat: pd.Timestamp | None = None
        self.virtual: dict | None = None
        self._last_trend_skip: tuple | None = None
        self.broker = broker
        self.notifier = notifier or Notifier()
        self.news = news or NewsFilter(cfg.news)
        self.journal = journal or Journal(cfg.journal_file)
        self.clock = clock or (lambda: pd.Timestamp.now(tz="UTC"))
        self.sessions = SessionClock(cfg.sessions)
        self.strategy = SmcStrategy(cfg.strategy, self.sessions)
        self.risk = RiskGuard(cfg.risk)
        self.symbol = cfg.broker.symbol
        self.magic = cfg.broker.magic
        self.trend_magic = cfg.broker.magic + cfg.trend.magic_offset
        self.trend = TrendStrategy(cfg.trend)
        self.use_smc = cfg.strategy.mode in ("smc", "both")
        self.use_trend = cfg.strategy.mode in ("trend", "both")
        self.last_trend_bar: pd.Timestamp | None = None
        self.status = EngineStatus()
        self.logs: deque[str] = deque(maxlen=14)
        self.paused = False
        self.spec = None
        self.smt_symbols: dict[str, int] = {}
        self.last_bar_time: pd.Timestamp | None = None
        self.current_day = None
        self.errors = 0
        self.stats = {"setups": 0, "placed": 0, "skipped": 0}
        self.handlers: dict[str, Callable[[str], str]] = {}
        self._closed_cache: tuple[pd.Timestamp, list] | None = None
        self._skip_notified: set[str] = set()

    # ---------------------------------------------------------------- logging
    def log(self, message: str, level: str = "INFO", notify: bool = False) -> None:
        now = self.clock()
        self.logs.append(f"[{fmt_wib(now, '%H:%M:%S')}] {message}")
        getattr(log, level.lower(), log.info)(message)
        self.journal.log(now, level, message)
        if notify:
            self.notifier.send(message)

    # ------------------------------------------------------------------ start
    def start(self) -> bool:
        if not self.broker.connect():
            self.log("Gagal terhubung ke broker", "ERROR", notify=True)
            return False
        acc = self.broker.account()
        self.currency = (acc.currency if acc else "USD") or "USD"
        kind = self.cfg.broker.account_type.lower()
        self.cent = kind == "cent" or (kind == "auto" and self.currency.upper() in ("USC", "USX", "UScent"))
        resolved = self.broker.resolve_symbol(self.symbol, cent=self.cent)
        if resolved is None:
            self.log(f"Simbol {self.symbol} tidak ditemukan di broker", "ERROR", notify=True)
            return False
        self.symbol = resolved
        self.spec = self.broker.symbol_spec(self.symbol)
        for item in self.cfg.strategy.smt_symbols:
            sym = self.broker.resolve_symbol(item.symbol, cent=self.cent)
            if sym:
                self.smt_symbols[sym] = item.correlation
            else:
                self.log(f"Simbol SMT {item.symbol} tidak tersedia, dilewati", "WARNING")
        mode = "AUTO-TRADE" if self.cfg.trade_enabled else "SINYAL SAJA"
        parts = []
        if self.use_trend:
            t = self.cfg.trend
            parts.append(f"TREND {t.timeframe} {t.entry_period}/{t.exit_period} SL {t.stop_atr}xATR")
        if self.use_smc:
            parts.append(f"SMC {self.cfg.strategy.entry_tf} (SMT: {', '.join(self.smt_symbols) or '-'})")
        acct = f"akun {'CENT ' if self.cent else ''}{self.currency}"
        self.log(f"Bot aktif {self.symbol} ({acct}) | {mode} | {' + '.join(parts)}", notify=True)
        self.handlers = self.command_handlers()
        self.notifier.start()
        self.virtual = None if self.cfg.trade_enabled else self._load_virtual()
        self.publisher.start()
        self.publisher.publish({"type": "info", "time": self.clock(),
                                "text": f"Bot aktif {self.symbol} ({acct}) | {mode}"},
                               f"Bot aktif {self.symbol} ({acct}) | {mode}", "XAU Signal", 2)
        return True

    def money(self, value: float) -> str:
        """Format uang sesuai akun; akun Cent juga menampilkan nilai USD."""
        text = f"{value:,.2f} {self.currency}"
        return text + f" (≈${value / 100:,.2f})" if self.cent else text

    def run(self, on_step: Callable[["Engine"], None] | None = None) -> None:
        """Loop utama 24/7. Error apa pun tidak menghentikan bot."""
        while True:
            try:
                self.step()
                self.errors = 0
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001
                self.errors += 1
                log.exception("Error di loop")
                if self.errors in (1, 10) or self.errors % 100 == 0:
                    self.log(f"⚠️ Error loop ({self.errors}x): {exc}", "ERROR", notify=True)
                if self.errors % 5 == 0:
                    self.broker.connect()
            if on_step:
                on_step(self)
            _time.sleep(self.cfg.poll_seconds)

    # ------------------------------------------------------------------- step
    def _process_commands(self) -> None:
        for cmd, arg in self.notifier.pending_commands():
            handler = self.handlers.get(cmd, self.handlers["help"])
            try:
                reply = handler(arg)
            except Exception as exc:  # noqa: BLE001
                reply = f"Error: {exc}"
            self.notifier.send(reply)

    def step(self, price_range: tuple[float, float] | None = None) -> None:
        self._process_commands()
        tick = self.broker.tick(self.symbol)
        if tick is None:
            self.status.block_reason = "Tidak ada harga (reconnect...)"
            self.broker.connect()
            return
        now = self.clock()
        lo, hi = price_range if price_range else (tick.bid, tick.bid)
        self.news.refresh(now)
        account = self.broker.account()
        positions = self.broker.positions(self.symbol, self.magic)
        orders = self.broker.orders(self.symbol, self.magic)
        bars = self.broker.rates(self.symbol, self.cfg.strategy.entry_tf, self.cfg.strategy.bars)

        self._manage_orders(now, tick, orders, lo, hi)
        self._manage_positions(now, tick, positions, orders, bars, lo, hi)
        self._daily_report(now)
        if self.use_trend:
            self._check_virtual_sl(now, tick, lo, hi)
            self._trend_step(now, tick, account)

        if self.use_smc and not bars.empty and bars.index[-1] != self.last_bar_time:
            self.last_bar_time = bars.index[-1]
            positions = self.broker.positions(self.symbol, self.magic)
            orders = self.broker.orders(self.symbol, self.magic)
            self._on_new_bar(now, tick, bars, account, positions, orders)

        self._update_status(now, tick, account)
        self._heartbeat(now, tick, account)

    def _heartbeat(self, now, tick: Tick, account) -> None:
        every = pd.Timedelta(minutes=self.cfg.app.heartbeat_minutes)
        if self._last_heartbeat is not None and now - self._last_heartbeat < every:
            return
        self._last_heartbeat = now
        st = self.status
        self.publisher.publish({
            "type": "heartbeat", "time": now, "symbol": self.symbol, "price": tick.bid,
            "spread": round(tick.spread, 3), "currency": self.currency, "cent": self.cent,
            "balance": account.balance if account else None, "equity": account.equity if account else None,
            "daily_pnl": st.daily_pnl, "mode": "AUTO" if self.cfg.trade_enabled else "SINYAL",
            "paused": self.paused, "trend": self.trend.state, "session": st.session,
            "block": st.block_reason, "news": st.news,
            "positions": [{"ticket": p.ticket, "dir": p.direction.label, "volume": p.volume,
                           "open": p.price_open, "sl": p.sl, "tp": p.tp, "profit": p.profit}
                          for p in st.positions],
        })

    # ------------------------------------------------------------- new setups
    def _context(self, bars: pd.DataFrame, tick: Tick) -> MarketContext:
        s = self.cfg.strategy
        htf = self.broker.rates(self.symbol, s.bias_tf, s.htf_bars)
        corr = {}
        for sym, c in self.smt_symbols.items():
            df = self.broker.rates(sym, s.entry_tf, s.bars)
            if not df.empty:
                corr[sym] = (df, c)
        return MarketContext(entry=bars, htf=htf, spread=tick.spread, correlated=corr)

    def _on_new_bar(self, now, tick, bars, account, positions, orders) -> None:
        setups = self.strategy.evaluate(self._context(bars, tick))
        self.status.last_eval = f"{fmt_wib(bars.index[-1], '%H:%M')} {self.strategy.last_note}"
        for setup in setups:
            row = self.journal.setup_row(setup.key)
            if row is not None and row["status"] != "skipped":
                continue  # sudah dieksekusi/dibatalkan; setup yang dilewati boleh dicek ulang
            self._handle_setup(now, tick, setup, account, positions, orders)
            positions = self.broker.positions(self.symbol, self.magic)
            orders = self.broker.orders(self.symbol, self.magic)

    def _active_setups(self, positions: list[Position], orders: list[PendingOrder]) -> dict[Direction, set]:
        active: dict[Direction, set] = defaultdict(set)
        for o in orders:
            row = self.journal.ticket(o.ticket)
            active[o.direction].add(row["setup_key"] if row else f"o{o.ticket}")
        for p in positions:
            row = self.journal.ticket(p.identifier)
            if row is None:
                active[p.direction].add(f"p{p.ticket}")
            elif not row["be_done"]:
                active[p.direction].add(row["setup_key"])
        return active

    def _block_reason(self, now, tick, setup, account, positions, orders) -> str | None:
        if self.paused:
            return "Bot dijeda (/pause)"
        reason = self.sessions.entry_block_reason(now)
        if reason:
            return reason
        if self.cfg.sessions.killzone_only and not self.sessions.killzone(now):
            return "Di luar killzone"
        reason = self.news.blocked(now)
        if reason:
            return reason
        if tick.spread > self.cfg.risk.max_spread:
            return f"Spread {tick.spread:.2f} > {self.cfg.risk.max_spread:.2f}"
        if account is None:
            return "Info akun tidak tersedia"
        state = self.risk.evaluate(now, account, self._closed(now - pd.Timedelta(days=8)))
        if state.blocked:
            return state.blocked
        active = self._active_setups(positions, orders)
        opposite = Direction(-int(setup.direction))
        if active.get(opposite):
            return f"Masih ada posisi {opposite.label} aktif (belum BE)"
        if len(active.get(setup.direction, ())) >= self.cfg.risk.max_setups_per_direction:
            return f"Sudah ada setup {setup.direction.label} aktif"
        return None

    def _handle_setup(self, now, tick: Tick, setup: Setup, account, positions, orders) -> None:
        self.stats["setups"] += 1
        spec = self.spec
        sign = int(setup.direction)
        reason = self._block_reason(now, tick, setup, account, positions, orders)

        # Harga sudah melewati entry -> market bila RR masih layak.
        market_price = tick.ask if setup.direction == Direction.BUY else tick.bid
        if reason is None and (market_price - setup.entry) * sign <= 0:
            risk_now = (setup.sl - market_price) * -sign
            if risk_now <= spec.min_stop_distance or risk_now <= 0:
                reason = "Harga sudah dekat SL"
            elif abs(setup.tp2 - market_price) / risk_now < self.cfg.strategy.min_rr:
                reason = "Harga sudah melewati entry, RR tidak layak"
            else:
                setup.entry = market_price
                setup.market_entry = True
        if reason is None and setup.risk < max(spec.min_stop_distance, spec.tick_size):
            reason = "Jarak SL di bawah stop level broker"

        volume, risk_money, note = 0.0, 0.0, ""
        if reason is None:
            volume, risk_money, note = lot_size(account.balance, self.cfg.risk.risk_pct, setup.entry,
                                                setup.sl, spec, self.cfg.risk.allow_min_lot_over_risk)
            if volume <= 0:
                reason = note

        if reason is not None:
            self.journal.record_setup(setup, "skipped", reason)
            if setup.key in self._skip_notified:
                return  # alasan sama/serupa sudah dilaporkan
            self._skip_notified.add(setup.key)
            self.stats["skipped"] += 1
            self.log(f"Setup {setup.direction.label} skor {setup.score} dilewati: {reason}")
            if self.cfg.signals_enabled and self.cfg.telegram.notify_skipped:
                self.notifier.send(self._format(setup, f"⛔ Dilewati: {reason}"))
            return

        if not self.cfg.trade_enabled:
            self.journal.record_setup(setup, "signal", note, volume)
            self.log(f"Sinyal {setup.direction.label} {setup.entry:.2f} (mode sinyal)")
            if self.cfg.signals_enabled:
                self.notifier.send(self._format(setup, "📡 Sinyal saja (auto-trade OFF)", volume, risk_money))
            return

        part, rest = split_volume(volume, self.cfg.risk.partial_ratio, spec)
        legs = [("tp1", part, setup.tp1), ("tp2", rest, setup.tp2)] if part > 0 else [
            ("single", volume, setup.tp2)]
        comment = f"SMC {setup.direction.label} s{setup.score}"
        placed = []
        for leg, vol, tp in legs:
            if setup.market_entry:
                res = self.broker.market_order(self.symbol, setup.direction, vol, setup.sl, tp,
                                               self.magic, f"{comment} {leg}")
            else:
                res = self.broker.place_limit(self.symbol, setup.direction, vol, setup.entry,
                                              setup.sl, tp, self.magic, f"{comment} {leg}")
            if res.ok:
                self.journal.add_ticket(res.ticket, setup.key, leg, now)
                placed.append((leg, res.ticket))
            else:
                self.log(f"Order {leg} gagal: {res.message}", "WARNING")
        if placed:
            self.stats["placed"] += 1
            kind = "Market" if setup.market_entry else "Limit"
            self.journal.record_setup(setup, "placed", note, volume)
            self.log(f"{kind} {setup.direction.label} {volume} lot @ {setup.entry:.2f} "
                     f"SL {setup.sl:.2f} TP {setup.tp2:.2f}")
            self.notifier.send(self._format(setup, f"✅ {kind} order terpasang "
                                                   f"({len(placed)} posisi)", volume, risk_money))
        else:
            self.journal.record_setup(setup, "failed", "order ditolak broker", volume)
            self.notifier.send(self._format(setup, "❌ Order ditolak broker, cek log", volume, risk_money))

    def _format(self, s: Setup, status: str, volume: float = 0.0, risk_money: float = 0.0) -> str:
        max_score = sum(self.cfg.strategy.weights.values())
        icon = "🟢" if s.direction == Direction.BUY else "🔴"
        lines = [
            f"{icon} SETUP {s.direction.label} {self.symbol} | skor {s.score}/{max_score}",
            f"Entry: {s.entry:.2f} ({'market' if s.market_entry else 'limit'})",
            f"SL: {s.sl:.2f} | TP1: {s.tp1:.2f} | TP2: {s.tp2:.2f}",
            f"RR: 1:{s.rr:.1f} (TP1 1:{s.rr_tp1:.1f})",
        ]
        if volume:
            lines.append(f"Lot: {volume} | Risiko: {risk_money:.2f} ({self.cfg.risk.risk_pct}%)")
        lines.append("Alasan:")
        lines += [f"• {r}" for r in s.reasons]
        lines.append(f"Status: {status}")
        lines.append(f"Waktu: {fmt_wib(self.clock())}")
        return "\n".join(lines)

    # ----------------------------------------------------------------- trend
    # posisi virtual: dipakai di mode SINYAL supaya sinyal keluar (exit/SL) tetap dikirim
    def _load_virtual(self) -> dict | None:
        try:
            data = json.loads(Path(self.cfg.trend.virtual_file).read_text(encoding="utf-8"))
            data["dir"] = Direction[data["dir"]]
            return data
        except (OSError, ValueError, KeyError):
            return None

    def _save_virtual(self, value: dict | None) -> None:
        self.virtual = value
        path = Path(self.cfg.trend.virtual_file)
        if value is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**value, "dir": value["dir"].name}, default=str), encoding="utf-8")

    def _close_virtual(self, now, price: float, why: str) -> None:
        v = self.virtual
        sign = int(v["dir"])
        points = (price - v["entry"]) * sign
        r = points / abs(v["entry"] - v["sl"]) if v["entry"] != v["sl"] else 0.0
        text = (f"🏁 TUTUP {v['dir'].label} {self.symbol} @ {price:.2f}\n"
                f"Entry {v['entry']:.2f} -> hasil {points:+.2f} poin ({r:+.2f}R)\nAlasan: {why}")
        self.log(text.replace("\n", " | "), notify=self.cfg.signals_enabled)
        self.publisher.publish({"type": "close", "id": v["key"], "time": now, "mode": "trend",
                                "dir": v["dir"].label, "entry": v["entry"], "price": round(price, 3),
                                "points": round(points, 3), "r": round(r, 2), "reason": why},
                               text, "Sinyal TUTUP posisi", 5, ["checkered_flag"])
        self._save_virtual(None)

    def _check_virtual_sl(self, now, tick: Tick, lo: float, hi: float) -> None:
        v = self.virtual
        if v is None or self.cfg.trade_enabled:
            return
        if v["dir"] == Direction.BUY and lo <= v["sl"]:
            self._close_virtual(now, v["sl"], "Stop loss tersentuh")
        elif v["dir"] == Direction.SELL and hi + tick.spread >= v["sl"]:
            self._close_virtual(now, v["sl"], "Stop loss tersentuh")

    def _trend_step(self, now, tick: Tick, account) -> None:
        cfg = self.cfg.trend
        bars = self.broker.rates(self.symbol, cfg.timeframe, cfg.bars)
        if bars.empty or bars.index[-1] == self.last_trend_bar:
            return
        self.last_trend_bar = bars.index[-1]
        positions = self.broker.positions(self.symbol, self.trend_magic)
        virtual = None if self.cfg.trade_enabled else self.virtual
        current = positions[0].direction if positions else (virtual["dir"] if virtual else None)
        sig = self.trend.evaluate(bars, current)
        if sig.action == "close":
            for p in positions:
                res = self.broker.close_position(self.symbol, p.ticket)
                if res.ok:
                    text = (f"🏁 TREND {p.direction.label} #{p.ticket} ditutup: {sig.note} "
                            f"(PnL {self.money(p.profit)})")
                    self.log(text, notify=True)
                    self.publisher.publish({"type": "close", "time": now, "mode": "trend",
                                            "dir": p.direction.label, "ticket": p.ticket,
                                            "price": tick.bid, "pnl": p.profit, "reason": sig.note},
                                           text, "Posisi ditutup", 4, ["checkered_flag"])
            if virtual and not positions:
                price = tick.bid if virtual["dir"] == Direction.BUY else tick.ask
                self._close_virtual(now, price, sig.note)
            return
        if sig.action != "open":
            return
        direction = sig.direction
        sign = int(direction)
        key = f"TREND-{direction.label}-{bars.index[-1]:%Y%m%d%H%M}"
        entry = tick.ask if direction == Direction.BUY else tick.bid
        sl = entry - sign * cfg.stop_atr * sig.atr
        reason = self._trend_block_reason(now, tick, account)
        volume, risk_money, lot_warn = 0.0, 0.0, ""
        if reason is None:
            volume, risk_money, note = lot_size(account.balance, self.cfg.risk.risk_pct, entry, sl,
                                                self.spec, self.cfg.risk.allow_min_lot_over_risk)
            if volume <= 0:
                if self.cfg.trade_enabled:
                    reason = note
                else:  # mode sinyal: tetap kirim, beri peringatan lot minimum
                    volume, risk_money = self.spec.volume_min, abs(entry - sl) * self.spec.volume_min * (
                        self.spec.tick_value / self.spec.tick_size)
                    pct = risk_money / account.balance * 100 if account.balance else 0
                    lot_warn = f"⚠️ Lot minimum {volume} = risiko {pct:.1f}% saldo"
        event = {"type": "signal", "id": key, "time": now, "mode": "trend", "dir": direction.label,
                 "symbol": self.symbol, "entry": round(entry, 3), "sl": round(sl, 3), "tp": None,
                 "atr": round(sig.atr, 3), "exit_rule": f"close {cfg.timeframe} menembus channel {cfg.exit_period} bar",
                 "timeframe": cfg.timeframe, "reason": sig.note}
        lines = [
            f"{'🟢' if direction == Direction.BUY else '🔴'} TREND {direction.label} {self.symbol} "
            f"({cfg.timeframe} Donchian {cfg.entry_period}/{cfg.exit_period})",
            f"Entry: {entry:.2f} (market) | SL: {sl:.2f} ({cfg.stop_atr}x ATR {sig.atr:.2f})",
            f"TP: tidak ada - tunggu sinyal TUTUP (close menembus channel {cfg.exit_period} bar)",
            f"Alasan: {sig.note}",
        ]
        if reason is not None:
            self.journal.log(now, "INFO", f"{key} dilewati: {reason}")
            if self._last_trend_skip == (direction, reason):
                return  # alasan sama dengan bar sebelumnya -> jangan spam
            self._last_trend_skip = (direction, reason)
            self.log(f"Sinyal TREND {direction.label} dilewati: {reason}")
            if self.cfg.signals_enabled and self.cfg.telegram.notify_skipped:
                self.notifier.send("\n".join(lines + [f"Status: ⛔ Dilewati: {reason}"]))
            self.publisher.publish({**event, "status": "skipped", "note": reason},
                                   "\n".join(lines + [f"⛔ Dilewati: {reason}"]), "Sinyal dilewati", 2)
            return
        lines.append(f"Lot: {volume} | Risiko: {self.money(risk_money)} ({self.cfg.risk.risk_pct}%)")
        if lot_warn:
            lines.append(lot_warn)
        event.update(lot=volume, risk=round(risk_money, 2), currency=self.currency, warning=lot_warn)
        tags = ["green_circle" if direction == Direction.BUY else "red_circle"]
        self._last_trend_skip = None
        if not self.cfg.trade_enabled:
            self.log(f"Sinyal TREND {direction.label} {entry:.2f} (mode sinyal)")
            if self.cfg.signals_enabled:
                self.notifier.send("\n".join(lines + ["Status: 📡 Sinyal (auto-trade OFF)"]))
            self.publisher.publish({**event, "status": "signal"}, "\n".join(lines),
                                   f"{direction.label} XAUUSD", 5, tags)
            self._save_virtual({"dir": direction, "entry": entry, "sl": sl, "key": key, "time": now})
            return
        res = self.broker.market_order(self.symbol, direction, volume, sl, 0.0, self.trend_magic,
                                       f"TREND {direction.label}")
        status = "✅ Market order terbuka" if res.ok else f"❌ Ditolak broker: {res.message}"
        self.log(f"TREND {direction.label} {volume} lot @ {entry:.2f} SL {sl:.2f}: {status}")
        self.notifier.send("\n".join(lines + [f"Status: {status}", f"Waktu: {fmt_wib(now)}"]))
        self.publisher.publish({**event, "status": "opened" if res.ok else "failed", "note": status},
                               "\n".join(lines + [status]), f"{direction.label} XAUUSD", 5, tags)

    def _trend_block_reason(self, now, tick: Tick, account) -> str | None:
        if self.paused:
            return "Bot dijeda (/pause)"
        reason = self.sessions.entry_block_reason(now)
        if reason is None and self.cfg.trend.respect_news:
            reason = self.news.blocked(now)
        if reason:
            return reason
        if tick.spread > self.cfg.risk.max_spread:
            return f"Spread {tick.spread:.2f} > {self.cfg.risk.max_spread:.2f}"
        if account is None:
            return "Info akun tidak tersedia"
        return self.risk.evaluate(now, account, self._closed(now - pd.Timedelta(days=8))).blocked

    # ------------------------------------------------------------ management
    def _manage_orders(self, now, tick: Tick, orders: list[PendingOrder], lo: float, hi: float) -> None:
        by_setup: dict[str, list[PendingOrder]] = defaultdict(list)
        for o in orders:
            row = self.journal.ticket(o.ticket)
            if row:
                by_setup[row["setup_key"]].append(o)
        news_block = self.news.blocked(now)
        for key, group in by_setup.items():
            s = self.journal.setup_row(key)
            if s is None:
                continue
            direction = _dir(s["direction"])
            reason = None
            if now - min(o.time for o in group) > pd.Timedelta(minutes=self.cfg.risk.pending_expiry_minutes):
                reason = "Kedaluwarsa"
            elif (direction == Direction.SELL and lo + tick.spread <= s["tp1"]) or (
                    direction == Direction.BUY and hi >= s["tp1"]):
                reason = "Harga ke TP1 sebelum entry (setup terlewat)"
            elif news_block:
                reason = news_block
            elif self.paused:
                reason = "Bot dijeda"
            if reason:
                for o in group:
                    self.broker.cancel_order(o.ticket)
                self.journal.set_status(key, "cancelled", reason)
                self.log(f"Order {direction.label} dibatalkan: {reason}", notify=True)

    def _manage_positions(self, now, tick: Tick, positions: list[Position], orders: list[PendingOrder],
                          bars: pd.DataFrame, lo: float, hi: float) -> None:
        if not positions:
            return
        open_ids = {p.identifier for p in positions}
        pending_ids = {o.ticket for o in orders}
        groups: dict[str, list[tuple[Position, dict]]] = defaultdict(list)
        for p in positions:
            row = self.journal.ticket(p.identifier)
            if row:
                groups[row["setup_key"]].append((p, row))
        news_soon = self.news.upcoming(now, self.cfg.news.protect_before_minutes) if self.cfg.news.enabled else []
        for key, items in groups.items():
            s = self.journal.setup_row(key)
            if s is None:
                continue
            direction = _dir(s["direction"])
            tp1_leg_done = any(t["leg"] == "tp1" and t["ticket"] not in open_ids
                               and t["ticket"] not in pending_ids for t in self.journal.tickets_for(key))
            reached = hi >= s["tp1"] if direction == Direction.BUY else lo + tick.spread <= s["tp1"]
            for p, row in items:
                if not row["be_done"]:
                    if tp1_leg_done or reached:
                        self._move_be(p, tick, "TP1 tercapai")
                    elif news_soon and self._in_profit(p, tick):
                        self._move_be(p, tick, f"Proteksi berita {news_soon[0].title}")
                elif self.cfg.risk.trail_after_tp1:
                    self._trail(p, tick, bars)

    def _in_profit(self, p: Position, tick: Tick) -> bool:
        price = tick.bid if p.direction == Direction.BUY else tick.ask
        return (price - p.price_open) * int(p.direction) > self.cfg.risk.be_offset * 2

    def _move_be(self, p: Position, tick: Tick, why: str) -> None:
        sign = int(p.direction)
        new_sl = p.price_open + sign * self.cfg.risk.be_offset
        price = tick.bid if p.direction == Direction.BUY else tick.ask
        min_stop = self.spec.min_stop_distance
        if (price - new_sl) * sign <= min_stop:
            return  # harga belum cukup jauh, coba lagi nanti
        if p.sl and (new_sl - p.sl) * sign <= 0:
            self.journal.mark_be(p.identifier)
            return
        res = self.broker.modify_position(self.symbol, p.ticket, new_sl, p.tp)
        if res.ok:
            self.journal.mark_be(p.identifier)
            self.log(f"🛡️ SL #{p.ticket} ke BE {new_sl:.2f} ({why})", notify=True)

    def _trail(self, p: Position, tick: Tick, bars: pd.DataFrame) -> None:
        if bars.empty:
            return
        s = self.cfg.strategy
        side = "high" if p.direction == Direction.SELL else "low"
        swings = [w for w in find_swings(bars, s.internal_swing_len, side)
                  if w.time > p.time and w.confirmed_idx < len(bars)]
        if not swings:
            return
        sign = int(p.direction)
        buf = self.cfg.risk.trail_buffer + (tick.spread if p.direction == Direction.SELL else 0.0)
        new_sl = swings[-1].price - sign * buf
        price = tick.bid if p.direction == Direction.BUY else tick.ask
        if (price - new_sl) * sign <= self.spec.min_stop_distance:
            return
        if p.sl and (new_sl - p.sl) * sign < 0.10:
            return
        res = self.broker.modify_position(self.symbol, p.ticket, new_sl, p.tp)
        if res.ok:
            self.log(f"📈 Trailing SL #{p.ticket} -> {new_sl:.2f}")

    # --------------------------------------------------------------- laporan
    def _closed(self, since: pd.Timestamp) -> list:
        trades = self.broker.closed_trades(self.symbol, self.magic, since)
        trades += self.broker.closed_trades(self.symbol, self.trend_magic, since)
        return sorted(trades, key=lambda t: t.close_time)

    def _all_positions(self) -> list[Position]:
        return (self.broker.positions(self.symbol, self.magic)
                + self.broker.positions(self.symbol, self.trend_magic))

    def _day_summary(self, day) -> str:
        trades = [t for t in self._closed(self.clock() - pd.Timedelta(days=8))
                  if trading_day(t.close_time) == day]
        pnl = sum(t.pnl for t in trades)
        wins = sum(1 for t in trades if t.pnl > 0)
        losses = sum(1 for t in trades if t.pnl < 0)
        return (f"📊 Ringkasan {day}: {len(trades)} posisi ditutup | menang {wins} | kalah {losses} | "
                f"PnL {pnl:.2f}")

    def _daily_report(self, now) -> None:
        day = trading_day(now)
        if self.current_day is None:
            self.current_day = day
            return
        if day != self.current_day:
            self.notifier.send(self._day_summary(self.current_day))
            self.current_day = day

    def _update_status(self, now, tick: Tick, account) -> None:
        st = self.status
        st.now = now
        st.price = tick.bid
        st.spread = tick.spread
        st.account = account
        st.positions = self._all_positions()
        st.orders = self.broker.orders(self.symbol, self.magic)
        bias = self.strategy.last_bias
        st.bias = {1: "BULLISH", -1: "BEARISH"}.get(bias, "NETRAL")
        st.session = self.sessions.session_name(now)
        st.paused = self.paused
        nxt = self.news.next_event(now)
        st.news = self.news.error or (f"{nxt.title} {fmt_wib(nxt.time)}" if nxt else "-")
        st.block_reason = (self.sessions.entry_block_reason(now) or self.news.blocked(now) or "")
        if account is not None:
            if self._closed_cache is None or now - self._closed_cache[0] > pd.Timedelta(seconds=30):
                self._closed_cache = (now, self._closed(now - pd.Timedelta(days=2)))
            trades = self._closed_cache[1]
            st.daily_pnl = sum(t.pnl for t in trades if trading_day(t.close_time) == trading_day(now))

    # -------------------------------------------------------------- telegram
    def command_handlers(self) -> dict[str, Callable[[str], str]]:
        def status(_: str) -> str:
            st = self.status
            acc = st.account
            lines = [
                f"🤖 {self.symbol} {st.price:.2f} | spread {st.spread:.2f}",
                f"Mode: {'AUTO' if self.cfg.trade_enabled else 'SINYAL'}"
                f"{' (DIJEDA)' if self.paused else ''}",
                f"Bias {self.cfg.strategy.bias_tf}: {st.bias} | Sesi: {st.session}",
                f"Berita: {st.news}",
                f"Evaluasi terakhir: {st.last_eval}",
                f"Trend {self.cfg.trend.timeframe}: {self.trend.state}",
            ]
            if acc:
                lines.append(f"Balance {acc.balance:.2f} | Equity {acc.equity:.2f} | PnL hari ini {st.daily_pnl:.2f}")
            if st.block_reason:
                lines.append(f"Blokir entry: {st.block_reason}")
            return "\n".join(lines)

        def positions(_: str) -> str:
            ps = self._all_positions()
            os_ = self.broker.orders(self.symbol, self.magic)
            if not ps and not os_:
                return "Tidak ada posisi/order aktif"
            lines = [f"{p.direction.label} {p.volume} @ {p.price_open:.2f} SL {p.sl:.2f} TP {p.tp:.2f} "
                     f"PnL {p.profit:.2f}" for p in ps]
            lines += [f"PENDING {o.direction.label} {o.volume} @ {o.price:.2f}" for o in os_]
            return "\n".join(lines)

        def pause(_: str) -> str:
            self.paused = True
            return "⏸️ Bot dijeda: tidak ada entry baru (posisi tetap dikelola)"

        def resume(_: str) -> str:
            self.paused = False
            return "▶️ Bot aktif kembali"

        def evaluate(_: str) -> str:
            now = self.clock()
            rows = self.journal.setups_since(now - pd.Timedelta(days=1))
            lines = [self._day_summary(trading_day(now)), f"Setup 24 jam terakhir: {len(rows)}"]
            lines += [f"{r['direction']} {r['entry']:.2f} skor {r['score']} -> {r['status']} {r['note'] or ''}"
                      for r in rows[-10:]]
            return "\n".join(lines)

        def news(_: str) -> str:
            now = self.clock()
            evs = self.news.upcoming(now, 60 * 24)
            if not evs:
                return self.news.error or "Tidak ada berita high-impact 24 jam ke depan"
            return "\n".join(f"📰 {fmt_wib(e.time)} {e.currency} {e.title}" for e in evs)

        def closeall(arg: str) -> str:
            if arg.strip().lower() != "ya":
                return "Ketik /closeall ya untuk menutup SEMUA posisi & order bot"
            for o in self.broker.orders(self.symbol, self.magic):
                self.broker.cancel_order(o.ticket)
            for p in self._all_positions():
                self.broker.close_position(self.symbol, p.ticket)
            self.paused = True
            return "Semua posisi & order ditutup. Bot dijeda (/resume untuk lanjut)"

        def help_(_: str) -> str:
            return ("/status - kondisi bot\n/posisi - posisi & order\n/pause - jeda entry baru\n"
                    "/resume - lanjut\n/eval - ringkasan hari ini\n/berita - kalender 24 jam\n"
                    "/closeall ya - tutup semua")

        return {"status": status, "posisi": positions, "positions": positions, "pause": pause,
                "resume": resume, "eval": evaluate, "berita": news, "news": news,
                "closeall": closeall, "help": help_, "start": help_}


__all__ = ["Engine", "TF_MINUTES"]
