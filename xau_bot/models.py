from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import pandas as pd


class Direction(IntEnum):
    BUY = 1
    SELL = -1

    @property
    def label(self) -> str:
        return self.name


@dataclass
class Swing:
    idx: int            # posisi bar swing
    confirmed_idx: int  # bar di mana swing baru bisa diketahui (idx + len)
    time: pd.Timestamp
    price: float
    side: str           # "high" | "low"


@dataclass
class Level:
    """Level likuiditas (BSL = side 'high', SSL = side 'low')."""
    price: float
    side: str
    kind: str                 # swing | equal | htf_swing | pdh | pdl | asia_high | asia_low
    time: pd.Timestamp        # waktu terbentuk
    known_idx: int            # bar entry-TF pertama di mana level sudah diketahui
    strength: int = 1

    @property
    def external(self) -> bool:
        return self.kind != "swing"


@dataclass
class Setup:
    direction: Direction
    entry: float
    sl: float
    tp1: float
    tp2: float
    score: int
    components: dict[str, bool]
    reasons: list[str]
    swept_level: Level
    sweep_time: pd.Timestamp
    sweep_extreme: float
    mss_time: pd.Timestamp
    poi_kind: str
    poi_low: float
    poi_high: float
    created_time: pd.Timestamp
    market_entry: bool = False

    @property
    def key(self) -> str:
        return f"{self.direction.label}-{self.sweep_time:%Y%m%d%H%M}-{self.swept_level.price:.2f}"

    @property
    def risk(self) -> float:
        return abs(self.entry - self.sl)

    @property
    def rr(self) -> float:
        return abs(self.tp2 - self.entry) / self.risk if self.risk else 0.0

    @property
    def rr_tp1(self) -> float:
        return abs(self.tp1 - self.entry) / self.risk if self.risk else 0.0


@dataclass
class SymbolSpec:
    name: str
    digits: int
    point: float
    tick_size: float
    tick_value: float        # nilai uang per tick untuk 1 lot
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int = 0     # dalam point
    contract_size: float = 100.0

    def round_price(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, self.digits)

    @property
    def min_stop_distance(self) -> float:
        return self.stops_level * self.point


@dataclass
class Tick:
    time: pd.Timestamp
    bid: float
    ask: float

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class Account:
    balance: float
    equity: float
    margin_free: float
    currency: str = "USD"


@dataclass
class Position:
    ticket: int
    identifier: int
    direction: Direction
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float
    time: pd.Timestamp
    comment: str = ""


@dataclass
class PendingOrder:
    ticket: int
    direction: Direction
    volume: float
    price: float
    sl: float
    tp: float
    time: pd.Timestamp
    comment: str = ""


@dataclass
class OrderResult:
    ok: bool
    ticket: int = 0
    message: str = ""
    price: float = 0.0


@dataclass
class ClosedTrade:
    position_id: int
    direction: Direction | None
    volume: float
    pnl: float
    open_time: pd.Timestamp | None
    close_time: pd.Timestamp


@dataclass
class EngineStatus:
    """Snapshot untuk dashboard & perintah Telegram."""
    now: pd.Timestamp | None = None
    price: float = 0.0
    spread: float = 0.0
    account: Account | None = None
    daily_pnl: float = 0.0
    bias: str = "-"
    session: str = "-"
    news: str = "-"
    paused: bool = False
    block_reason: str = ""
    positions: list[Position] = field(default_factory=list)
    orders: list[PendingOrder] = field(default_factory=list)
    last_eval: str = "-"
