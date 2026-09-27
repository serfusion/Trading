import MetaTrader5 as mt5

if not mt5.initialize():
    print(mt5.last_error())
    quit()

symbols = mt5.symbols_get()

print("Available Gold Symbols:\n")

for symbol in symbols:
    name = symbol.name.upper()

    if "XAU" in name or "GOLD" in name:
        print(symbol.name)

mt5.shutdown()