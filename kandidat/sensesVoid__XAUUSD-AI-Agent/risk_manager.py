import MetaTrader5 as mt5
from pydantic import BaseModel

class ExecutionPlan(BaseModel):
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    sl_distance_price: float
    risk_amount: float
    reward_amount: float

class RiskManager:
    def __init__(self, symbol: str = "XAUUSD", risk_pct: float = 0.01, reward_risk_ratio: float = 2.0):
        self.symbol = symbol
        self.risk_pct = risk_pct
        self.reward_risk_ratio = reward_risk_ratio

    def build_plan(
        self, direction: str, ai_invalidation_price: float | None, atr_14: float
    ) -> ExecutionPlan | None:
        if direction not in ("LONG", "SHORT"):
            return None

        tick = mt5.symbol_info_tick(self.symbol)
        info = mt5.symbol_info(self.symbol)
        account = mt5.account_info()
        if tick is None or info is None or account is None:
            raise RuntimeError("Could not fetch tick/symbol/account info for risk calculation")

        entry_price = tick.ask if direction == "LONG" else tick.bid
        stop_loss = self._resolve_stop_loss(direction, entry_price, ai_invalidation_price, atr_14, info)
        sl_distance = abs(entry_price - stop_loss)

        take_profit = (
            entry_price + sl_distance * self.reward_risk_ratio
            if direction == "LONG"
            else entry_price - sl_distance * self.reward_risk_ratio
        )

        lot_size = self._position_size(account.balance, sl_distance, info)

        return ExecutionPlan(
            direction=direction,
            entry_price=round(entry_price, info.digits),
            stop_loss=round(stop_loss, info.digits),
            take_profit=round(take_profit, info.digits),
            lot_size=lot_size,
            sl_distance_price=round(sl_distance, info.digits),
            risk_amount=round(account.balance * self.risk_pct, 2),
            reward_amount=round(account.balance * self.risk_pct * self.reward_risk_ratio, 2),
        )

    def _resolve_stop_loss(
        self, direction: str, entry_price: float, ai_invalidation_price: float | None,
        atr_14: float, info,
    ) -> float:
        min_stop_distance = info.trade_stops_level * info.point
        atr_fallback_distance = max(atr_14 * 1.2, min_stop_distance * 1.5)

        if ai_invalidation_price is not None:
            distance = abs(entry_price - ai_invalidation_price)
            on_correct_side = (
                (direction == "LONG" and ai_invalidation_price < entry_price)
                or (direction == "SHORT" and ai_invalidation_price > entry_price)
            )
            # Trust the AI's invalidation level only if it's structurally valid —
            # right side of price, and not tighter than the broker allows
            if on_correct_side and distance >= min_stop_distance:
                return ai_invalidation_price

        # AI gave no invalidation, or it was invalid/too tight — fall back to ATR
        return (
            entry_price - atr_fallback_distance
            if direction == "LONG"
            else entry_price + atr_fallback_distance
        )

    def _position_size(self, balance: float, sl_distance_price: float, info) -> float:
        risk_amount = balance * self.risk_pct
        money_per_unit_move = info.trade_tick_value / info.trade_tick_size
        raw_lots = risk_amount / (sl_distance_price * money_per_unit_move)

        step = info.volume_step
        lots = round(raw_lots / step) * step
        lots = max(info.volume_min, min(lots, info.volume_max))
        return round(lots, 2)