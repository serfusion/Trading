# ─────────────────────────────────────────────
#  XAUUSD MT5 Bot — Configuration
# ─────────────────────────────────────────────

MT5_LOGIN    = 5050740103          # Your MT5 account number
MT5_PASSWORD = "YOUR_MT5_PASSWORD"   # Your MT5 password
MT5_SERVER   = "MetaQuotes-Demo" # e.g. "ICMarkets-Live", "Exness-Real"

# Symbol
SYMBOL    = "XAUUSD"
TIMEFRAME = "H4"                 # M5, M15, M30, H1, H4, D1

# ── Strategy Parameters ──────────────────────
EMA_FAST    = 13
EMA_SLOW    = 34
RSI_PERIOD  = 14
RSI_OB      = 65                 # Overbought — avoid BUY above this
RSI_OS      = 35                 # Oversold   — avoid SELL below this
ATR_PERIOD  = 14
ATR_SL_MULT = 2.0                # Stop loss  = 1.5 × ATR
ATR_TP_MULT = 3.5                # Take profit = 2.5 × ATR  (R:R ~1.67)

# ── Risk Management ───────────────────────────
RISK_PCT          = 0.01         # Risk 1% of balance per trade
MAX_OPEN_TRADES   = 2            # Max concurrent positions
DAILY_LOSS_LIMIT  = 0.03         # Stop trading if down 3% today
MAX_SPREAD_POINTS = 30           # Skip trade if spread > 30 pts (3 pips)

# ── Session Filter (UTC) ──────────────────────
# London + NY overlap = best liquidity for Gold
TRADE_HOUR_START = 0             # 8:00 UTC
TRADE_HOUR_END   = 24            # 20:00 UTC

# ── Magic Number ─────────────────────────────
MAGIC = 20240101                 # Unique ID for this bot's trades

# ── Logging ──────────────────────────────────
LOG_FILE = "xauusd_bot.log"
13
