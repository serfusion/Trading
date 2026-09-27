# Installation & Setup Guide

## Prerequisites

- **MetaTrader 5** installed on your computer
- **Code Editor** (MetaEditor bundled with MT5)
- **Administrator access** to your MT5 installation folder
- **Stable internet connection**

## Step-by-Step Installation

### 1. Download Files

```bash
# Clone the repository
git clone https://github.com/shamshyder123-oss/gold-trading-ea.git
```

Or download the ZIP file directly from GitHub.

### 2. Locate MetaTrader 5 Folder

Find your MT5 installation directory:
- **Windows**: Usually `C:\Program Files\MetaTrader 5` or `C:\Users\[Username]\AppData\Roaming\MetaTrader 5`
- **macOS**: `/Applications/MetaTrader 5`
- **Linux**: Varies by installation method

### 3. Copy Files

1. Navigate to: `[MT5 Folder]\MQL5\Experts`
2. Create a subfolder: `GoldTradingEA`
3. Copy all `.mq5` and `.mqh` files into this folder

```
MQL5/
├── Experts/
│   └── GoldTradingEA/
│       ├── GoldTradingEA.mq5
│       ├── Config.mqh
│       ├── TradeManager.mqh
│       ├── TechnicalAnalysis.mqh
│       └── RiskManager.mqh
```

### 4. Compile the EA

1. Open **MetaEditor** (Tools → MetaEditor in MT5)
2. Navigate to the EA folder
3. Open `GoldTradingEA.mq5`
4. Click **Compile** (or press F7)
5. Check for errors in the output window

**Expected Output**:
```
0 errors, 0 warnings
'GoldTradingEA' compiled successfully
```

### 5. Configure Your Broker

1. Open **MetaTrader 5**
2. Add the symbol **XAU/USD** if not available:
   - Right-click on Market Watch
   - Select "Symbols"
   - Find and enable XAU/USD
3. Ensure your broker supports gold trading (XAU/USD)

### 6. Attach EA to Chart

1. Open a **1-hour chart** (H1) for XAU/USD
2. Go to **Insert → Expert Advisors → GoldTradingEA**
3. Or drag the EA from Navigator to the chart
4. Click **OK** when the settings dialog appears

### 7. Configure Settings

In the EA settings dialog, adjust:

**Trading Tab**:
```
Lot Size: 0.1 (start small)
Stop Loss: 100 (pips)
Take Profit: 200 (pips)
Deviation: 10 (pips)
TimeFrame: H1
```

**Risk Management Tab**:
```
Account Risk: 2% (per trade)
Max Drawdown: 10%
Max Loss Per Trade: 5%
Enable Trailing Stop: true
Trailing Stop Distance: 50 (pips)
```

### 8. Enable Autotrade

1. In MetaTerminal, go to **Tools → Options**
2. **Advisors** tab:
   - ✅ Enable "Allow automated trading"
   - ✅ Enable "Allow WebRequest"
   - Adjust "Expert Advisors max. optimization passes" if needed
3. Click **OK**

### 9. Start Trading

1. Click the green **play button** on the chart to activate the EA
2. EA status shows in the top-right corner (green = running)
3. Monitor the EA's actions in the **Experts** tab

## Backtesting (Highly Recommended)

### Setup Backtest

1. Open **Strategy Tester** (View → Tester or Ctrl+R)
2. Configure:
   - **Expert Advisor**: GoldTradingEA
   - **Symbol**: XAUUSD
   - **Timeframe**: H1
   - **Model**: Open prices only or Every tick (more accurate)
   - **Period**: 2 years (minimum)
   - **Initial Deposit**: 1000

### Run Backtest

1. Click **Start** to begin testing
2. Wait for completion (may take 5-30 minutes)
3. Review results in **Results** tab

### Analyze Results

Check key metrics:
- **Total Net Profit**: Should be positive
- **Profit Factor**: > 1.5 is good
- **Max Drawdown**: < 15% is acceptable
- **Win Rate**: > 50% is target
- **Trade Count**: > 20 trades for reliability

## Troubleshooting

### "Expert Advisor has been stopped" message

**Solution**:
1. Check if autotrade is enabled
2. Verify internet connection
3. Check EA for runtime errors
4. Restart MetaTrader 5

### No trades are being placed

**Possible causes**:
1. Symbol not available - enable XAU/USD in Market Watch
2. Wrong timeframe - EA is set to H1 only
3. Market closed - gold trades 24/5, check schedule
4. Lot size too small - increase Lot parameter
5. Spread too high - wait for better conditions

### "Connection error" or "Cannot connect"

**Solution**:
1. Check internet connection
2. Verify MT5 connection (check server status)
3. Reconnect to account
4. Contact your broker

### Compilation errors

**Common issues**:
- **#include file not found**: Ensure all `.mqh` files are in same folder
- **Undefined symbol**: Check file structure and paths
- **Syntax error**: Review recent changes, use matching brackets

**Solution**:
1. Copy all files to `Experts\GoldTradingEA` folder
2. Close MetaEditor completely
3. Reopen and compile

## First Trade Checklist

- [ ] EA compiles without errors
- [ ] Symbol XAU/USD is available
- [ ] Chart timeframe is H1
- [ ] Autotrade is enabled
- [ ] Account has minimum balance ($500+)
- [ ] Lot size is set to 0.01-0.1
- [ ] Stop Loss and Take Profit are set
- [ ] Risk management parameters are reviewed
- [ ] Backtesting shows positive results
- [ ] EA shows green status on chart

## Initial Trade Monitoring

**First Week**:
1. Monitor trades closely
2. Check win rate and drawdown
3. Verify order execution is clean
4. Look for any unusual behavior
5. Keep detailed logs

**If issues arise**:
1. Disable the EA
2. Close open positions
3. Review logs in Experts tab
4. Adjust parameters and retry

## Optimization Tips

### For More Trades:
- Decrease RSI thresholds (20-80 instead of 25-75)
- Decrease SL/TP sizes (50/100 instead of 100/200)

### For Safer Trades:
- Increase RSI thresholds (15-85 instead of 25-75)
- Increase SL/TP sizes (150/300 instead of 100/200)
- Decrease lot size

### For Better Results:
1. Backtest with your broker's spreads
2. Optimize on 2+ years of data
3. Test on different market conditions
4. Paper trade before going live

## Support

For installation help:
- Open an issue on GitHub
- Include:
  - Your operating system
  - MT5 version
  - Error messages (screenshots)
  - Steps you've taken

---

**Happy Trading!** 🎯📈
