"""Broker MetaTrader 5 (Exness). Hanya berjalan di Windows dengan terminal MT5 terpasang."""
from __future__ import annotations

import logging
from collections import defaultdict

import pandas as pd

from ..models import (Account, ClosedTrade, Direction, OrderResult, PendingOrder, Position,
                      SymbolSpec, Tick)
from .base import Broker

log = logging.getLogger(__name__)

_TF_NAMES = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M10": "TIMEFRAME_M10",
             "M15": "TIMEFRAME_M15", "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1",
             "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1"}


class MT5Broker(Broker):
    def __init__(self, login: int, password: str, server: str, path: str = "",
                 server_utc_offset_hours: float = 0.0, deviation: int = 30):
        try:
            import MetaTrader5 as mt5  # noqa: N813
        except ImportError as exc:  # pragma: no cover - hanya Windows
            raise RuntimeError(
                "Paket MetaTrader5 tidak tersedia. Jalankan di Windows: pip install MetaTrader5"
            ) from exc
        self.mt5 = mt5
        self.login, self.password, self.server, self.path = login, password, server, path
        self.offset = pd.Timedelta(hours=server_utc_offset_hours)
        self.deviation = deviation
        self._specs: dict[str, SymbolSpec] = {}

    # ---------------------------------------------------------------- koneksi
    def connect(self) -> bool:
        mt5 = self.mt5
        kwargs = {}
        if self.path:
            kwargs["path"] = self.path
        if self.login:
            kwargs.update(login=int(self.login), password=self.password, server=self.server)
        if not mt5.initialize(**kwargs):
            log.error("MT5 initialize gagal: %s", mt5.last_error())
            return False
        info = mt5.account_info()
        if info is None:
            log.error("Tidak bisa membaca akun MT5: %s", mt5.last_error())
            return False
        log.info("Terhubung ke MT5 akun %s (%s) server %s", info.login, info.currency, info.server)
        return True

    def shutdown(self) -> None:
        self.mt5.shutdown()

    def has_symbol(self, symbol: str) -> bool:
        return self.mt5.symbol_info(symbol) is not None and bool(self.mt5.symbol_select(symbol, True))

    def resolve_symbol(self, symbol: str) -> str | None:
        if self.has_symbol(symbol):
            return symbol
        # Exness: Standard = akhiran "m", Cent = "c", Pro/Raw/Zero tanpa akhiran.
        for suffix in ("m", "c"):
            if self.has_symbol(symbol + suffix):
                return symbol + suffix
        found = [s.name for s in (self.mt5.symbols_get(f"{symbol}*") or [])]
        found.sort(key=len)
        for name in found:
            if self.has_symbol(name):
                return name
        return None

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbol {symbol} tidak ditemukan di MT5")
        self.mt5.symbol_select(symbol, True)
        spec = SymbolSpec(
            name=symbol, digits=info.digits, point=info.point,
            tick_size=info.trade_tick_size or info.point,
            tick_value=info.trade_tick_value, volume_min=info.volume_min,
            volume_max=info.volume_max, volume_step=info.volume_step,
            stops_level=info.trade_stops_level, contract_size=info.trade_contract_size,
        )
        self._specs[symbol] = spec
        return spec

    # ------------------------------------------------------------------ data
    def _to_utc(self, seconds) -> pd.Timestamp:
        return pd.to_datetime(seconds, unit="s", utc=True) - self.offset

    def rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        tf = getattr(self.mt5, _TF_NAMES[timeframe])
        arr = self.mt5.copy_rates_from_pos(symbol, tf, 1, count)  # posisi 1 = bar tertutup
        if arr is None or len(arr) == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close"])
        df = pd.DataFrame(arr)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True) - self.offset
        return df.set_index("time")[["open", "high", "low", "close", "tick_volume"]].astype(float)

    def tick(self, symbol: str) -> Tick | None:
        t = self.mt5.symbol_info_tick(symbol)
        if t is None or not t.bid:
            return None
        ts = pd.to_datetime(t.time_msc, unit="ms", utc=True) - self.offset
        return Tick(ts, float(t.bid), float(t.ask))

    def account(self) -> Account | None:
        a = self.mt5.account_info()
        if a is None:
            return None
        return Account(a.balance, a.equity, a.margin_free, a.currency)

    def positions(self, symbol: str, magic: int) -> list[Position]:
        mt5 = self.mt5
        out = []
        for p in mt5.positions_get(symbol=symbol) or []:
            if p.magic != magic:
                continue
            out.append(Position(
                ticket=p.ticket, identifier=p.identifier,
                direction=Direction.BUY if p.type == mt5.POSITION_TYPE_BUY else Direction.SELL,
                volume=p.volume, price_open=p.price_open, sl=p.sl, tp=p.tp, profit=p.profit,
                time=self._to_utc(p.time), comment=p.comment))
        return out

    def orders(self, symbol: str, magic: int) -> list[PendingOrder]:
        mt5 = self.mt5
        buy_types = {mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP}
        out = []
        for o in mt5.orders_get(symbol=symbol) or []:
            if o.magic != magic:
                continue
            out.append(PendingOrder(
                ticket=o.ticket,
                direction=Direction.BUY if o.type in buy_types else Direction.SELL,
                volume=o.volume_current, price=o.price_open, sl=o.sl, tp=o.tp,
                time=self._to_utc(o.time_setup), comment=o.comment))
        return out

    # --------------------------------------------------------------- trading
    def _fillings(self, symbol: str) -> list[int]:
        mt5 = self.mt5
        info = mt5.symbol_info(symbol)
        modes = []
        if info is not None:
            if info.filling_mode & 1:
                modes.append(mt5.ORDER_FILLING_FOK)
            if info.filling_mode & 2:
                modes.append(mt5.ORDER_FILLING_IOC)
        modes.append(mt5.ORDER_FILLING_RETURN)
        return modes

    def _send(self, request: dict, fillings: list[int] | None = None) -> OrderResult:
        mt5 = self.mt5
        ok_codes = {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL}
        last = OrderResult(False, message="tidak terkirim")
        for filling in fillings or [None]:
            req = dict(request)
            if filling is not None:
                req["type_filling"] = filling
            res = mt5.order_send(req)
            if res is None:
                last = OrderResult(False, message=f"order_send None: {mt5.last_error()}")
                continue
            if res.retcode in ok_codes:
                return OrderResult(True, res.order or res.deal, res.comment, res.price)
            last = OrderResult(False, message=f"{res.retcode} {res.comment}")
            if res.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
                break
        log.warning("Order gagal: %s | %s", last.message, request)
        return last

    def _norm(self, symbol: str, price: float) -> float:
        spec = self._specs.get(symbol) or self.symbol_spec(symbol)
        return spec.round_price(price) if price else 0.0

    def place_limit(self, symbol, direction, volume, price, sl, tp, magic, comment) -> OrderResult:
        mt5 = self.mt5
        req = {
            "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY_LIMIT if direction == Direction.BUY else mt5.ORDER_TYPE_SELL_LIMIT,
            "price": self._norm(symbol, price), "sl": self._norm(symbol, sl),
            "tp": self._norm(symbol, tp), "magic": magic, "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req, [mt5.ORDER_FILLING_RETURN] + self._fillings(symbol))

    def market_order(self, symbol, direction, volume, sl, tp, magic, comment) -> OrderResult:
        mt5 = self.mt5
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return OrderResult(False, message="tick tidak tersedia")
        req = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY if direction == Direction.BUY else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if direction == Direction.BUY else tick.bid,
            "sl": self._norm(symbol, sl), "tp": self._norm(symbol, tp),
            "deviation": self.deviation, "magic": magic, "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req, self._fillings(symbol))

    def modify_position(self, symbol, ticket, sl, tp) -> OrderResult:
        mt5 = self.mt5
        req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol, "position": int(ticket),
               "sl": self._norm(symbol, sl), "tp": self._norm(symbol, tp)}
        return self._send(req)

    def close_position(self, symbol, ticket, volume=None) -> OrderResult:
        mt5 = self.mt5
        pos = mt5.positions_get(ticket=int(ticket))
        if not pos:
            return OrderResult(False, message="posisi tidak ditemukan")
        p = pos[0]
        tick = mt5.symbol_info_tick(symbol)
        is_buy = p.type == mt5.POSITION_TYPE_BUY
        req = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "position": int(ticket),
            "volume": float(volume or p.volume),
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "price": tick.bid if is_buy else tick.ask, "deviation": self.deviation,
            "magic": p.magic, "comment": "close", "type_time": mt5.ORDER_TIME_GTC,
        }
        return self._send(req, self._fillings(symbol))

    def cancel_order(self, ticket) -> OrderResult:
        return self._send({"action": self.mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})

    def closed_trades(self, symbol, magic, since) -> list[ClosedTrade]:
        mt5 = self.mt5
        start = int((since + self.offset).timestamp())
        end = int((pd.Timestamp.now(tz="UTC") + self.offset + pd.Timedelta(days=2)).timestamp())
        deals = mt5.history_deals_get(start, end) or []
        ours = {d.position_id for d in deals if d.symbol == symbol and d.magic == magic}
        grouped = defaultdict(list)
        for d in deals:
            if d.position_id in ours and d.symbol == symbol:
                grouped[d.position_id].append(d)
        open_ids = {p.identifier for p in (mt5.positions_get(symbol=symbol) or [])}
        out = []
        for pid, ds in grouped.items():
            if pid in open_ids:
                continue
            outs = [d for d in ds if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)]
            if not outs:
                continue
            ins = [d for d in ds if d.entry == mt5.DEAL_ENTRY_IN]
            pnl = sum(d.profit + d.commission + d.swap + getattr(d, "fee", 0.0) for d in ds)
            direction = None
            if ins:
                direction = Direction.BUY if ins[0].type == mt5.DEAL_TYPE_BUY else Direction.SELL
            out.append(ClosedTrade(
                position_id=pid, direction=direction, volume=sum(d.volume for d in ins),
                pnl=pnl, open_time=self._to_utc(ins[0].time) if ins else None,
                close_time=self._to_utc(max(d.time for d in outs))))
        return sorted(out, key=lambda t: t.close_time)
