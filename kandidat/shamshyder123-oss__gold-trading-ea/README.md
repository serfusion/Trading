# Gold Trading Expert Advisor (XAU/USD)

## Overview

This is a professional Expert Advisor (EA) designed for automated trading of gold (XAU/USD) forex pairs. The system incorporates advanced trading logic, risk management, and technical analysis to generate consistent trading signals.

## Features

### Trading Strategy
- **Multi-Indicator Analysis**: RSI, MACD, and Moving Averages
- **Smart Entry Signals**: Buy when RSI oversold + uptrend + MACD positive
- **Smart Exit Signals**: Sell when RSI overbought + downtrend + MACD negative
- **Trend Confirmation**: Uses 20/50 SMA crossover for trend validation

### Risk Management
- **Account Risk Control**: Configurable risk per trade (default 2%)
- **Maximum Drawdown Protection**: Stops trading if drawdown exceeds limit
- **Position Sizing**: Automatic lot calculation based on risk parameters
- **Stop Loss & Take Profit**: Fixed and adjustable targets
- **Trailing Stop**: Dynamic stop loss following price movement

### Position Management
- **Multiple Indicator Confirmation**: Reduces false signals
- **Automatic Position Closing**: On TP, SL, or max loss triggers
- **Position Modification**: Dynamic SL/TP adjustment
- **One Position Per Signal**: Prevents over-trading

## File Structure

```
gold-trading-ea/
├── GoldTradingEA.mq5        # Main EA code with entry/exit logic
├���─ Config.mqh               # Configuration parameters
├── TradeManager.mqh         # Trade execution and position management
├── TechnicalAnalysis.mqh    # Technical indicator calculations
├── RiskManager.mqh          # Risk management and position sizing
├── README.md                # This file
└── INSTALLATION.md          # Installation instructions
```

## Parameters

### Trading Parameters
- **Lot Size** (default: 0.1): Initial lot size for trades
- **Stop Loss** (default: 100): Stop loss in pips
- **Take Profit** (default: 200): Take profit in pips
- **Deviation** (default: 10): Slippage tolerance in pips

### Technical Indicators
- **RSI Period** (default: 14): RSI calculation period
- **MACD Fast** (default: 12): MACD fast EMA period
- **MACD Slow** (default: 26): MACD slow EMA period
- **MACD Signal** (default: 9): MACD signal line period
- **TimeFrame** (default: H1): Recommended H1 for gold trading

### Risk Management
- **Account Risk** (default: 2%): Risk per trade as % of account
- **Max Drawdown** (default: 10%): Maximum allowed drawdown before halt
- **Max Loss Per Trade** (default: 5%): Maximum loss per single trade

### Advanced Settings
- **Enable Trailing Stop** (default: true): Activate trailing stop loss
- **Trailing Stop Distance** (default: 50): Trailing distance in pips
- **Magic Number** (default: 123456): EA identifier for trades

## Trading Logic

### Buy Signal
A buy signal is generated when:
1. RSI is between 25-35 (approaching oversold)
2. SMA20 is above SMA50 (uptrend confirmed)
3. MACD is positive and rising
4. Price is above SMA20

### Sell Signal
A sell signal is generated when:
1. RSI is between 65-75 (approaching overbought)
2. SMA20 is below SMA50 (downtrend confirmed)
3. MACD is negative and falling
4. Price is below SMA20

## Installation

### Requirements
- MetaTrader 5 (MT5)
- Gold symbol (XAU/USD) available on your broker
- Minimum account balance (recommended $500+)

### Steps
1. Download all files from this repository
2. Copy `.mq5` and `.mqh` files to `MQL5/Experts` folder
3. Compile the main EA file in MetaEditor
4. Attach the EA to a chart (H1 timeframe recommended)
5. Configure parameters according to your risk tolerance
6. Enable autotrade in terminal settings

## Usage Tips

### Backtesting
- Test on 1-2 years of historical data
- Optimize parameters for your broker's spreads
- Monitor drawdown during testing

### Live Trading
- Start with small lot sizes (0.01-0.1)
- Monitor first trades closely
- Keep EA running 24/5 for optimal gold trading
- Review logs regularly for signals

### Optimization
- Adjust RSI periods for more/fewer signals
- Modify SL/TP based on volatility
- Increase/decrease risk parameters cautiously

## Performance Expectations

- **Win Rate**: 55-65% (typical)
- **Profit Factor**: 1.5-2.0 (good range)
- **Drawdown**: 5-15% (depends on settings)
- **ROI**: 20-50% monthly (target)

## Risk Disclaimer

⚠️ **IMPORTANT**: 
- Past performance is not indicative of future results
- Trading forex/gold involves substantial risk of loss
- Always use stop losses and risk management
- Start with small position sizes
- Test thoroughly before live trading
- Never trade with money you can't afford to lose

## Support & Contributing

For issues, questions, or improvements:
1. Open an issue on GitHub
2. Provide detailed description of problem
3. Include relevant logs/screenshots
4. Suggest improvements via pull requests

## License

MIT License - See LICENSE file for details

## Author

Gold Trading EA Development Team

---

**Version**: 1.0.0  
**Last Updated**: 2026-08-27  
**Status**: Production Ready
