import MetaTrader5 as mt5

if mt5.initialize():
    symbols = mt5.symbols_get()

    print("Gold-related symbols:\n")

    for s in symbols:
        if "XAU" in s.name.upper() or "GOLD" in s.name.upper():
            print(s.name)

    mt5.shutdown()
else:
    print(mt5.last_error())