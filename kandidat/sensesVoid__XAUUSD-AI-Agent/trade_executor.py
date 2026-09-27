import MetaTrader5 as mt5


class TradeExecutionError(Exception):
    pass


class TradeExecutor:
    MAGIC_NUMBER = 574839201  # unique tag so you can identify this pipeline's trades in MT5 history

    def __init__(self, symbol: str = "XAUUSD", max_deviation_points: int = 20):
        self.symbol = symbol
        self.max_deviation_points = max_deviation_points

    def execute_market_order(
        self, direction: str, lot_size: float, stop_loss: float, take_profit: float,
        comment: str = "ai_pipeline",
    ) -> dict:
        if direction not in ("LONG", "SHORT"):
            raise TradeExecutionError(f"Invalid direction: {direction}")

        tick = mt5.symbol_info_tick(self.symbol)
        info = mt5.symbol_info(self.symbol)
        if tick is None or info is None:
            raise TradeExecutionError(f"Could not fetch tick/symbol info for {self.symbol}")

        order_type = mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == "LONG" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": self.max_deviation_points,
            "magic": self.MAGIC_NUMBER,
            "comment": comment[:31],  # MT5 truncates comments beyond 31 chars anyway
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._resolve_filling_mode(info),
        }

        result = mt5.order_send(request)
        if result is None:
            raise TradeExecutionError(f"order_send returned None: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise TradeExecutionError(
                f"Order rejected: retcode={result.retcode}, comment={result.comment}"
            )

        return {
            "ticket": result.order,
            "volume": result.volume,
            "price": result.price,
            "retcode": result.retcode,
            "comment": result.comment,
        }

    @staticmethod
    def _resolve_filling_mode(info) -> int:
        """Not every broker/symbol supports every fill mode — check what's actually
        allowed rather than hardcoding one, or order_send silently rejects the trade."""
        if info.filling_mode & mt5.SYMBOL_FILLING_IOC:
            return mt5.ORDER_FILLING_IOC
        if info.filling_mode & mt5.SYMBOL_FILLING_FOK:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN