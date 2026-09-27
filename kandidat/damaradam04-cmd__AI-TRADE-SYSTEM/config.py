"""
AI GOLD TRADER PRO — Configuration

Fill in your Exness MT5 DEMO account details below.
NEVER put live account credentials here until you've tested thoroughly on demo.
"""

# --- MT5 Connection (Exness Demo OR real) ---
MT5_LOGIN = ...           # your demo account number (int)
MT5_PASSWORD = "..."        # your demo account password
MT5_SERVER = "..."          # e.g. "Exness-MT5Trial"
MT5_PATH = "..."            # optional: path to terminal64.exe if not default install

# --- Symbol ---
SYMBOL = "XAUUSDm"        # confirm exact symbol name in your MT5 Market Watch (some brokers use "XAUUSDm" etc.)

# --- Timeframes to analyze ---
TIMEFRAMES = ["D1", "H4", "H1", "M15", "M5"]

# --- How many recent candles to keep per timeframe ---
CANDLE_HISTORY = {
    "D1": 300,
    "H4": 500,
    "H1": 500,
    "M15": 500,
    "M5": 500,
}

# --- Structure detection sensitivity ---
# Number of candles on each side required for a point to count as a swing high/low.
# Lower = more sensitive (more swings detected), Higher = smoother/fewer swings.
SWING_LOOKBACK = 3

# --- Zone detection ---
# Minimum % price move (impulse) after a candle to mark it as a supply/demand zone origin
ZONE_IMPULSE_THRESHOLD_PCT = 0.3

# --- Support/Resistance ---
SR_TOUCH_TOLERANCE_PCT = 0.15   # how close price needs to be to count as "touching" a level
SR_MIN_TOUCHES = 2               # minimum touches to consider a level valid
