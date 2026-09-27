"""
AI GOLD TRADER PRO — Trade Executor (Phase 7, Demo Mode)

Places BUY/SELL market orders on MT5 with stop-loss and take-profit.

SAFETY: This module checks that the connected account is a DEMO account
before allowing any trade. This check is intentional — do not remove it
until you've tested extensively and are ready to trade live deliberately.

REQUIREMENTS:
    - mt5_connector.py already connected (see previous phase)
    - MetaTrader5 python package
"""

import MetaTrader5 as mt5
import config
from mt5_connector import MT5Connector


class TradeExecutor:
    def __init__(self, connector: MT5Connector, allow_live: bool = False):
        """
        connector: an already-connected MT5Connector instance
        allow_live: must be explicitly set to True to trade on a real account.
                    Defaults to False so demo is always the safe default.
        """
        self.connector = connector
        self.allow_live = allow_live

    def _check_account_safety(self):
        """Refuses to trade on a live account unless allow_live is explicitly True."""
        info = self.connector.account_info()
        # trade_mode: 0 = demo, 1 = contest, 2 = real (per MT5 docs)
        is_demo = info.get("trade_mode") == 0
        if not is_demo and not self.allow_live:
            raise RuntimeError(
                "🛑 Refusing to trade: this looks like a LIVE account and "
                "allow_live=False. Set allow_live=True explicitly in code "
                "only when you are certain you want real trades placed."
            )

    def calculate_lot_size(self, risk_percent: float, stop_loss_pips: float, symbol: str = None) -> float:
        """
        Basic position sizing: risk a fixed % of account balance per trade,
        based on the distance to your stop loss.

        This is a simplified calculation for gold (XAUUSD) where pip value
        varies by broker/lot size — verify against your broker's contract
        specs before relying on this for real trades.
        """
        symbol = symbol or config.SYMBOL
        info = self.connector.account_info()
        balance = info["balance"]

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise ValueError(f"Could not get symbol info for {symbol}")

        risk_amount = balance * (risk_percent / 100)
        # tick_value = $ per tick per 1.0 lot; tick_size = price move per tick
        pip_value_per_lot = symbol_info.trade_tick_value / symbol_info.trade_tick_size
        lot = risk_amount / (stop_loss_pips * pip_value_per_lot)

        # Round to broker's allowed lot step
        lot_step = symbol_info.volume_step
        lot = max(symbol_info.volume_min, round(lot / lot_step) * lot_step)
        lot = min(lot, symbol_info.volume_max)
        return round(lot, 2)

    def open_trade(self, direction: str, lot: float, stop_loss: float = None,
                   take_profit: float = None, symbol: str = None, comment: str = "AI Gold Trader Pro"):
        """
        Opens a market order.

        direction: 'buy' or 'sell'
        lot: position size (e.g. 0.01)
        stop_loss: absolute price level for SL (optional but strongly recommended)
        take_profit: absolute price level for TP (optional)
        """
        self._check_account_safety()

        symbol = symbol or config.SYMBOL
        self.connector.check_symbol(symbol)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Could not get current price for {symbol}")

        if direction.lower() == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif direction.lower() == "sell":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            raise ValueError("direction must be 'buy' or 'sell'")

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"Could not get symbol info for {symbol}")
        digits = symbol_info.digits

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": round(price, digits),
            "deviation": 20,
            "magic": 20260807,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if stop_loss is not None:
            request["sl"] = round(stop_loss, digits)

        if take_profit is not None:
            request["tp"] = round(take_profit, digits)

        print("\n========== ORDER REQUEST ==========")
        for key, value in request.items():
            print(f"{key}: {value}")
        print("===================================\n")

        result = mt5.order_send(request)

        print("\n========== ORDER RESULT ==========")
        print(result)
        print("==================================\n")

        if result is None:
            raise RuntimeError(f"order_send failed, no result returned: {mt5.last_error()}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(
                f"""
Order failed

Retcode : {result.retcode}
Comment : {result.comment}

SL : {request.get('sl')}
TP : {request.get('tp')}

Last Error : {mt5.last_error()}
"""
            )

        return {
            "success": True,
            "order_id": result.order,
            "price_filled": result.price,
            "volume": result.volume,
            "retcode": result.retcode,
        }

    def close_trade(self, ticket: int):
        """Closes an open position by its ticket number."""
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise ValueError(f"No open position found with ticket {ticket}")
        pos = positions[0]

        symbol = pos.symbol
        volume = pos.volume
        tick = mt5.symbol_info_tick(symbol)

        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 20260807,
            "comment": "AI Gold Trader Pro close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Close failed: {mt5.last_error() if result is None else result.comment}")
        return {"success": True, "closed_ticket": ticket}

    def get_open_positions(self, symbol: str = None):
        """Returns all currently open positions (optionally filtered by symbol)."""
        symbol = symbol or config.SYMBOL
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return []
        return [p._asdict() for p in positions]


if __name__ == "__main__":
    # Self-test: connects, checks account is demo, prints open positions.
    # Does NOT place a real order automatically — that's a deliberate choice
    # you should trigger manually once you've reviewed this code.
    conn = MT5Connector()
    conn.connect()

    executor = TradeExecutor(conn, allow_live=False)
    info = conn.account_info()
    print(f"Connected to account {info['login']} on {info['server']}")
    print(f"Balance: {info['balance']} {info['currency']}")
    print(f"Trade mode (0=demo,1=contest,2=real): {info['trade_mode']}")

    print("\nOpen positions:")
    for p in executor.get_open_positions():
        print(" ", p)

    # --- Example of how you'd place a trade (commented out on purpose) ---
    # lot = executor.calculate_lot_size(risk_percent=1, stop_loss_pips=500)
    # result = executor.open_trade(
    #     direction="buy",
    #     lot=lot,
    #     stop_loss=None,     # set an actual price level
    #     take_profit=None,   # set an actual price level
    # )
    # print(result)

    conn.disconnect()