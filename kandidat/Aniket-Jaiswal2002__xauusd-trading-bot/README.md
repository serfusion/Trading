# XAUUSD Algorithmic Trading Bot

An automated trading bot for Gold (XAUUSD) built on MetaTrader 5. Uses an EMA crossover + RSI filter strategy with dynamic ATR-based stop loss and take profit. Includes a full backtester, risk management system, and real-time Telegram alerts.

## Features

- **EMA Crossover + RSI Filter** — enters trades on EMA crossovers, filtered by RSI to avoid overbought/oversold conditions
- **ATR-based SL/TP** — dynamic stop loss and take profit calculated from market volatility
- **Trailing Stop** — automatically moves stop loss to lock in profit as price moves
- **Risk Management** — configurable risk per trade (default 1%), daily loss limit, max open trades, spread filter
- **Backtester** — test the strategy on historical data with full performance metrics
- **Telegram Alerts** — real-time notifications to your phone for every trade event
- **Session Filter** — only trades during high-liquidity hours

## Strategy

```
BUY  signal: EMA(13) crosses above EMA(34) AND RSI < 65
SELL signal: EMA(13) crosses below EMA(34) AND RSI > 35

Stop Loss  = 2.0 × ATR
Take Profit = 3.5 × ATR  (R:R ~1:1.75)
```

## Backtest Metrics

Metrics calculated and printed after every backtest run:

| Metric | Description |
|--------|-------------|
| Win Rate | % of trades that hit TP |
| Profit Factor | Gross profit / Gross loss |
| Net Profit | Total P&L in USD |
| Max Drawdown | Largest peak-to-trough drop |
| Sharpe Ratio | Risk-adjusted return |

Results are saved to `backtest_results.csv` for further analysis.

## Installation

```bash
# Clone the repo
git clone https://github.com/Aniket-Jaiswal2002/xauusd-trading-bot.git
cd xauusd-trading-bot

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to set your credentials and strategy parameters:

```python
MT5_LOGIN    = YOUR_ACCOUNT_NUMBER
MT5_PASSWORD = "YOUR_MT5_PASSWORD"
MT5_SERVER   = "YOUR_BROKER_SERVER"

TELEGRAM_TOKEN   = "YOUR_TELEGRAM_BOT_TOKEN"   # from @BotFather
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"     # from @userinfobot
```

Key strategy parameters you can tune:

```python
EMA_FAST    = 13       # Fast EMA period
EMA_SLOW    = 34       # Slow EMA period
RSI_PERIOD  = 14       # RSI period
ATR_SL_MULT = 2.0      # Stop loss multiplier
ATR_TP_MULT = 3.5      # Take profit multiplier
RISK_PCT    = 0.01     # Risk 1% of balance per trade
```

## Usage

```bash
# Run the live bot
python bot.py

# Run backtest on historical data
python backtest.py
```

## Project Structure

```
xauusd-trading-bot/
  bot.py              # main trading bot
  backtest.py         # historical backtester
  config.py           # strategy + credentials config
  telegram_notify.py  # Telegram alert system
  backtest_results.csv
  xauusd_bot.log
```

## Tech Stack

- Python 3.10+
- MetaTrader 5 API (`MetaTrader5`)
- `pandas` + `numpy` for data processing
- `ta` (Technical Analysis library) for indicators
- `schedule` for the main bot loop
- `requests` for Telegram notifications

## Disclaimer

This bot is for educational purposes only. Trading financial instruments involves significant risk. Never trade with money you cannot afford to lose.
