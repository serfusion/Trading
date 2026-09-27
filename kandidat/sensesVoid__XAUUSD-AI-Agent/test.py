import MetaTrader5 as mt5

# Bypass .env entirely, hardcode temporarily, and pass an explicit terminal path
result = mt5.initialize(
    path=r"C:\Program Files\Fortune Prime MT5\terminal64.exe",  # match the exe you actually log into
    login=52970971,
    password="ISI_PASSWORD_SENDIRI",
    server="ICMarketsSC-Demo",
    timeout=10000,
)
print(result, mt5.last_error())