"""Broker simulasi untuk backtest & test. Harga bar = BID, ASK = BID + spread.

Aturan konservatif: bila SL dan TP tersentuh di bar yang sama, dianggap SL; di bar
saat order limit terisi, TP tidak dihitung (urutan harga di dalam bar tidak diketahui).
"""
from __future__ import annotations

import itertools

import pandas as pd

from ..models import (Account, ClosedTrade, Direction, OrderResult, PendingOrder, Position,
                      SymbolSpec, Tick)
from ..risk import money_per_price_unit
from ..strategy import TF_MINUTES
from .base import Broker


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    out = df[list(agg)].resample(f"{minutes}min", label="left", closed="left").agg(agg)
    return out.dropna()


class PaperBroker(Broker):
    def __init__(self, data: dict[str, pd.DataFrame], base_tf: str, spec: SymbolSpec,
                 spread: float = 0.20, balance: float = 1000.0, start_index: int = 0):
        self.base_tf = base_tf
        self.base_delta = pd.Timedelta(minutes=TF_MINUTES[base_tf])
        self.data = {s: df.sort_index() for s, df in data.items()}
        self.main = next(iter(self.data))
        self.spec = spec
        self.spread = spread
        self.balance = balance
        self.cursor = start_index
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}
        self._ids = itertools.count(1000)
        self._positions: dict[int, Position] = {}
        self._orders: dict[int, PendingOrder] = {}
        self._magic: dict[int, int] = {}
        self.closed: list[ClosedTrade] = []

    # ------------------------------------------------------------------ waktu
    @property
    def now(self) -> pd.Timestamp:
        return self.data[self.main].index[self.cursor] + self.base_delta

    def _frame(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = (symbol, timeframe)
        if key not in self._frames:
            df = self.data[symbol]
            self._frames[key] = df if timeframe == self.base_tf else resample(df, TF_MINUTES[timeframe])
        return self._frames[key]

    def connect(self) -> bool:
        return True

    def has_symbol(self, symbol: str) -> bool:
        return symbol in self.data

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        return self.spec

    def rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        df = self._frame(symbol, timeframe)
        delta = pd.Timedelta(minutes=TF_MINUTES[timeframe])
        end = df.index.searchsorted(self.now - delta, side="right")
        return df.iloc[max(0, end - count):end]

    def _bar(self) -> pd.Series:
        return self.data[self.main].iloc[self.cursor]

    def tick(self, symbol: str) -> Tick | None:
        bid = float(self.data[symbol].iloc[self.cursor]["close"])
        return Tick(self.now, bid, bid + self.spread)

    def account(self) -> Account:
        floating = sum(self._pnl(p, self._exit_price(p)) for p in self._positions.values())
        return Account(self.balance, self.balance + floating, self.balance + floating)

    def positions(self, symbol: str, magic: int) -> list[Position]:
        return [p for t, p in self._positions.items() if self._magic.get(t) == magic]

    def orders(self, symbol: str, magic: int) -> list[PendingOrder]:
        return [o for t, o in self._orders.items() if self._magic.get(t) == magic]

    # --------------------------------------------------------------- trading
    def _pnl(self, p: Position, price: float, volume: float | None = None) -> float:
        vol = p.volume if volume is None else volume
        return (price - p.price_open) * int(p.direction) * vol * money_per_price_unit(self.spec)

    def _exit_price(self, p: Position) -> float:
        bid = float(self._bar()["close"])
        return bid if p.direction == Direction.BUY else bid + self.spread

    def place_limit(self, symbol, direction, volume, price, sl, tp, magic, comment) -> OrderResult:
        ticket = next(self._ids)
        self._orders[ticket] = PendingOrder(ticket, direction, volume, price, sl, tp, self.now, comment)
        self._magic[ticket] = magic
        return OrderResult(True, ticket, "placed", price)

    def market_order(self, symbol, direction, volume, sl, tp, magic, comment) -> OrderResult:
        ticket = next(self._ids)
        bid = float(self._bar()["close"])
        price = bid + self.spread if direction == Direction.BUY else bid
        self._positions[ticket] = Position(ticket, ticket, direction, volume, price, sl, tp, 0.0,
                                           self.now, comment)
        self._magic[ticket] = magic
        return OrderResult(True, ticket, "filled", price)

    def modify_position(self, symbol, ticket, sl, tp) -> OrderResult:
        p = self._positions.get(ticket)
        if p is None:
            return OrderResult(False, message="posisi tidak ada")
        p.sl, p.tp = sl, tp
        return OrderResult(True, ticket)

    def _close(self, p: Position, price: float, volume: float | None = None) -> None:
        vol = p.volume if volume is None else min(volume, p.volume)
        pnl = self._pnl(p, price, vol)
        self.balance += pnl
        self.closed.append(ClosedTrade(p.identifier, p.direction, vol, pnl, p.time, self.now))
        p.volume = round(p.volume - vol, 8)
        if p.volume <= 0:
            self._positions.pop(p.ticket, None)

    def close_position(self, symbol, ticket, volume=None) -> OrderResult:
        p = self._positions.get(ticket)
        if p is None:
            return OrderResult(False, message="posisi tidak ada")
        price = self._exit_price(p)
        self._close(p, price, volume)
        return OrderResult(True, ticket, price=price)

    def cancel_order(self, ticket) -> OrderResult:
        return OrderResult(self._orders.pop(ticket, None) is not None, ticket)

    def closed_trades(self, symbol, magic, since) -> list[ClosedTrade]:
        return [t for t in self.closed if t.close_time >= since and self._magic.get(t.position_id) == magic]

    # -------------------------------------------------------------- simulasi
    def advance(self) -> bool:
        """Maju satu bar dan proses fill/SL/TP. False bila data habis."""
        if self.cursor + 1 >= len(self.data[self.main]):
            return False
        self.cursor += 1
        bar = self._bar()
        o, h, l = float(bar["open"]), float(bar["high"]), float(bar["low"])
        sp = self.spread
        filled_now: set[int] = set()
        for ticket, order in list(self._orders.items()):
            if order.direction == Direction.SELL and h >= order.price:
                fill = max(order.price, o)
            elif order.direction == Direction.BUY and l + sp <= order.price:
                fill = min(order.price, o + sp)
            else:
                continue
            del self._orders[ticket]
            filled_now.add(ticket)
            self._positions[ticket] = Position(ticket, ticket, order.direction, order.volume, fill,
                                               order.sl, order.tp, 0.0, self.now, order.comment)
        for p in list(self._positions.values()):
            if p.direction == Direction.SELL:
                ask_o, ask_h, ask_l = o + sp, h + sp, l + sp
                if p.sl and ask_h >= p.sl:
                    self._close(p, p.sl if p.ticket in filled_now else max(p.sl, ask_o))
                elif p.ticket in filled_now:
                    continue  # urutan di dalam bar tidak diketahui: TP tidak dihitung di bar pengisian
                elif p.tp and ask_l <= p.tp:
                    self._close(p, min(p.tp, ask_o) if ask_o < p.tp else p.tp)
            else:
                if p.sl and l <= p.sl:
                    self._close(p, p.sl if p.ticket in filled_now else min(p.sl, o))
                elif p.ticket in filled_now:
                    continue
                elif p.tp and h >= p.tp:
                    self._close(p, max(p.tp, o) if o > p.tp else p.tp)
        return True
