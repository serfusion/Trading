import MetaTrader5 as mt5

# ==========================
# AI GOLD TRADER PRO
# SIMPLE BUY TEST
# ==========================

if not mt5.initialize():
    print("❌ MT5 Connection Failed")
    print(mt5.last_error())
    quit()

symbol = "XAUUSDm"

# Select Symbol
if not mt5.symbol_select(symbol, True):
    print("❌ Cannot Select Symbol")
    mt5.shutdown()
    quit()

symbol_info = mt5.symbol_info(symbol)

if symbol_info is None:
    print("❌ Cannot Get Symbol Info")
    mt5.shutdown()
    quit()

tick = mt5.symbol_info_tick(symbol)

if tick is None:
    print("❌ Cannot Get Current Price")
    mt5.shutdown()
    quit()

print("=" * 50)
print("AI GOLD TRADER PRO")
print("=" * 50)
print("Symbol :", symbol)
print("Bid    :", tick.bid)
print("Ask    :", tick.ask)
print("Spread :", tick.ask - tick.bid)
print("=" * 50)

request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": 0.01,
    "type": mt5.ORDER_TYPE_BUY,
    "price": tick.ask,
    "deviation": 20,
    "magic": 20260807,
    "comment": "AI GOLD TRADER PRO TEST",
    "type_time": mt5.ORDER_TIME_GTC,
}

# Try every filling mode
filling_modes = [
    ("FOK", mt5.ORDER_FILLING_FOK),
    ("IOC", mt5.ORDER_FILLING_IOC),
    ("RETURN", mt5.ORDER_FILLING_RETURN),
]

success = False

for name, mode in filling_modes:

    print(f"\nTrying Filling Mode : {name}")

    request["type_filling"] = mode

    result = mt5.order_send(request)

    print(result)

    if result is None:
        print("MT5 Error:", mt5.last_error())
        continue

    if result.retcode == mt5.TRADE_RETCODE_DONE:

        print("\n✅ TRADE OPENED SUCCESSFULLY")
        print("Ticket :", result.order)
        print("Price  :", result.price)

        success = True
        break

    else:

        print("❌ Failed")
        print("RetCode :", result.retcode)
        print("Comment :", result.comment)
        print("Last Error :", mt5.last_error())

if not success:

    print("\n❌ None of the filling modes worked.")

    print("\nBroker Execution Type")
    print(symbol_info)

mt5.shutdown()