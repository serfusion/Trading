from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ..models import (Account, ClosedTrade, Direction, OrderResult, PendingOrder, Position,
                      SymbolSpec, Tick)


def symbol_candidates(symbol: str, cent: bool) -> list[str]:
    suffixes = ["c", "", "m"] if cent else ["", "m", "c"]
    out = [symbol + s for s in suffixes]
    if symbol[-1:] in ("c", "m") and len(symbol) > 6:
        out.insert(0, symbol)  # nama lengkap diberikan pengguna
    return list(dict.fromkeys(out))


class Broker(ABC):
    """Antarmuka broker. `rates` hanya mengembalikan bar yang SUDAH tertutup (index UTC)."""

    @abstractmethod
    def connect(self) -> bool: ...

    def shutdown(self) -> None:
        return None

    @abstractmethod
    def has_symbol(self, symbol: str) -> bool: ...

    def resolve_symbol(self, symbol: str, cent: bool = False) -> str | None:
        """Nama simbol yang benar di broker (Exness: XAUUSDc = Cent, XAUUSDm = Standard)."""
        for name in symbol_candidates(symbol, cent):
            if self.has_symbol(name):
                return name
        return None

    @abstractmethod
    def symbol_spec(self, symbol: str) -> SymbolSpec: ...

    @abstractmethod
    def rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame: ...

    @abstractmethod
    def tick(self, symbol: str) -> Tick | None: ...

    @abstractmethod
    def account(self) -> Account | None: ...

    @abstractmethod
    def positions(self, symbol: str, magic: int) -> list[Position]: ...

    @abstractmethod
    def orders(self, symbol: str, magic: int) -> list[PendingOrder]: ...

    @abstractmethod
    def place_limit(self, symbol: str, direction: Direction, volume: float, price: float,
                    sl: float, tp: float, magic: int, comment: str) -> OrderResult: ...

    @abstractmethod
    def market_order(self, symbol: str, direction: Direction, volume: float, sl: float,
                     tp: float, magic: int, comment: str) -> OrderResult: ...

    @abstractmethod
    def modify_position(self, symbol: str, ticket: int, sl: float, tp: float) -> OrderResult: ...

    @abstractmethod
    def close_position(self, symbol: str, ticket: int, volume: float | None = None) -> OrderResult: ...

    @abstractmethod
    def cancel_order(self, ticket: int) -> OrderResult: ...

    @abstractmethod
    def closed_trades(self, symbol: str, magic: int, since: pd.Timestamp) -> list[ClosedTrade]: ...
