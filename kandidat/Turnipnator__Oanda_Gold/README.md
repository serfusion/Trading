# 🏆 Gold Trading Bot - XAU/USD Automated Trading System

Professional-grade automated trading bot for Gold (XAU/USD) using the **Triple Confirmation Trend Follower** strategy on Oanda.

Built with proven, battle-tested strategies. No fancy indicators. Just what works in real markets.

---

## 🎯 Core Philosophy

> "Trade with the trend, manage risk ruthlessly, and let winners run while cutting losers fast."

This bot implements a systematic approach to gold trading:
- ✅ **Trend Following**: Ride strong trends using EMA alignment
- ✅ **Momentum Confirmation**: Enter only with healthy momentum (RSI)
- ✅ **Smart Entries**: Wait for pullbacks to support/resistance
- ✅ **Risk Management**: Never risk more than 1.5% per trade
- ✅ **Automated**: Runs 24/7, emotions-free

---

## 📊 The Strategy: Triple Confirmation

### Required Confirmations (All 3 Must Align):

**1️⃣ Trend Filter** (EMA 20/50)
- BULLISH: Price > EMA20 AND EMA20 > EMA50
- BEARISH: Price < EMA20 AND EMA20 < EMA50
- NEUTRAL: Don't trade when EMAs are tangled

**2️⃣ Momentum** (RSI 14)
- BULLISH: RSI between 40-70 (uptrend momentum)
- BEARISH: RSI between 30-60 (downtrend momentum)
- AVOID: RSI > 75 (overbought) or < 25 (oversold)

**3️⃣ Entry Trigger** (Pattern + Level)
- Wait for pullback to support (uptrend) or bounce to resistance (downtrend)
- Confirm with bullish/bearish engulfing candle or hammer/shooting star
- Enter on close of confirmation candle

### Risk/Reward:
- **Stop Loss**: 20-40 pips below entry
- **Take Profit 1**: 1.5R (60% position)
- **Take Profit 2**: 2.5R (40% position)
- **Breakeven**: Stop moves to entry after TP1 hit

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ installed
- Oanda account (practice or live)
- Telegram bot (optional but recommended)

### 1. Clone and Install
```bash
cd Oanda_Gold
npm install
```

### 2. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

**Required settings:**
```bash
OANDA_API_KEY=your_practice_api_token_here
OANDA_ACCOUNT_ID=your_account_id_here
TRADING_MODE=practice  # ALWAYS start with practice!
```

**Optional but recommended:**
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_user_id
ENABLE_TELEGRAM=true
```

### 3. Test Connection
```bash
npm test
```

This will verify:
- ✅ Oanda API credentials work
- ✅ Market data access
- ✅ Account balance retrieval
- ✅ Telegram bot (if configured)

### 4. Start Trading
```bash
npm start
```

---

## 🐳 Docker Deployment (Recommended for VPS)

### Build and Run
```bash
# Build image
docker-compose build

# Start bot in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop bot
docker-compose down
```

### VPS Deployment
```bash
# On your VPS (Ubuntu/Debian)
git clone <your-repo>
cd Oanda_Gold

# Copy and configure .env
cp .env.example .env
nano .env

# Start with Docker Compose
docker-compose up -d

# Monitor
docker-compose logs -f gold-bot
```

---

## 📱 Telegram Commands

Control your bot remotely via Telegram:

### Monitoring
- `/status` - Bot status, balance, P&L, performance
- `/positions` - View all open positions
- `/pnl` - Profit & Loss reports (daily/all-time)
- `/balance` - Account balance and margin

### Control
- `/stop` - Gracefully stop trading (keeps positions open)
- `/resume` - Resume trading
- `/emergency` - **Emergency stop** (close all positions immediately)

### Other
- `/help` - Show all commands

**Automatic Notifications:**
- 🟢 Trade opened
- 🎉 Trade closed (with P&L)
- 🎯 Daily target reached
- 🛑 Daily loss limit hit
- ⚠️ Errors and alerts

---

## ⚙️ Configuration

### Risk Management (`.env`)
```bash
MAX_RISK_PER_TRADE=0.015      # 1.5% per trade
MAX_PORTFOLIO_RISK=0.05       # 5% total heat
INITIAL_BALANCE=10000         # Starting balance

TARGET_DAILY_PROFIT=100       # $100/day target
MAX_DAILY_LOSS=150            # $150/day max loss
```

### Strategy Parameters
```bash
EMA_FAST=20                   # Fast EMA period
EMA_SLOW=50                   # Slow EMA period
RSI_PERIOD=14                 # RSI period

RSI_BULLISH_MIN=40            # Min RSI for longs
RSI_BULLISH_MAX=70            # Max RSI for longs
RSI_BEARISH_MIN=30            # Min RSI for shorts
RSI_BEARISH_MAX=60            # Max RSI for shorts
```

### Entry/Exit Rules
```bash
STOP_LOSS_PIPS=20             # Initial stop loss
TAKE_PROFIT_1_RR=1.5          # First target (1.5R)
TAKE_PROFIT_2_RR=2.5          # Second target (2.5R)
MOVE_STOP_TO_BE=true          # Move to breakeven after TP1
```

---

## 📈 Performance Tracking

### What "Good" Looks Like (After 6 Months)
- **Win Rate**: 55-65% (quality over quantity)
- **Profit Factor**: >1.5 ($1.50+ per $1 lost)
- **Max Drawdown**: <15% (stop if hitting 20%)
- **Average R:R**: >1.5:1 (winners bigger than losers)
- **Monthly Return**: 3-8% (steady beats spectacular)
- **Trades Per Week**: 2-5 (patient trading)

### Realistic Expectations
- ❌ NOT get-rich-quick
- ✅ Get-rich-slow-and-keep-it
- ❌ NOT 50%+ monthly returns
- ✅ Consistent 3-8% monthly
- ❌ NOT 100% win rate
- ✅ Profitable over time with discipline

---

## 🛡️ Risk Management Rules

### Position Sizing
```javascript
// Never risk more than 1.5% per trade
Position Size = (Balance × 1.5%) / Distance to Stop Loss

// Example:
// Balance: $10,000
// Risk: 1.5% = $150
// Entry: $2050, Stop: $2030 (distance = $20)
// Size: $150 / $20 = 7.5 units = 7,500 Oanda units
```

### Daily Limits
- **Max Daily Loss**: Trading stops for the day
- **Target Met**: Continue trading (optional: can stop)
- **Portfolio Heat**: Max 5% total risk exposure

### Safety Rules
- ✅ ALWAYS start with practice account
- ✅ Paper trade for 3+ months minimum
- ✅ Never override stop losses
- ✅ Never revenge trade after losses
- ✅ Respect daily loss limits
- ✅ Test strategy changes on paper first

---

## 📁 Project Structure

```
Oanda_Gold/
├── src/
│   ├── index.js              # Main bot entry point
│   ├── config.js             # Configuration management
│   ├── oanda_client.js       # Oanda API wrapper
│   ├── technical_analysis.js # EMA, RSI, pattern detection
│   ├── strategy.js           # Triple Confirmation logic
│   ├── risk_manager.js       # Position sizing & risk
│   ├── telegram_bot.js       # Telegram integration
│   ├── logger.js             # Winston logging
│   └── test_connection.js    # Connection test script
├── logs/                     # Log files
├── data/                     # Trade history DB
├── .env                      # Your configuration (secret!)
├── .env.example              # Configuration template
├── Dockerfile                # Docker container config
├── docker-compose.yml        # Docker Compose setup
├── package.json              # Node.js dependencies
├── CLAUDE.md                 # Detailed strategy guide
└── README.md                 # This file
```

---

## 🔧 Troubleshooting

### Connection Issues
```bash
# Test your Oanda credentials
npm test

# Check logs
tail -f logs/gold_bot.log

# Docker logs
docker-compose logs -f
```

### Common Errors

**"Invalid API key"**
- Verify OANDA_API_KEY in .env
- Ensure TRADING_MODE matches your account (practice vs live)

**"Insufficient margin"**
- Reduce position size
- Lower MAX_RISK_PER_TRADE
- Increase account balance

**"Daily loss limit reached"**
- This is working as intended!
- Bot stops trading for the day
- Will resume automatically tomorrow

**"Portfolio heat exceeded"**
- Too many open positions
- Wait for some to close
- Or increase MAX_PORTFOLIO_RISK (not recommended)

---

## 🎓 Learning Path

### Week 1-2: Setup & Paper Trading
1. Set up Oanda practice account
2. Configure bot with .env
3. Run connection test
4. Start bot in practice mode
5. Monitor via Telegram
6. **Goal**: Understand how bot works

### Week 3-8: Strategy Validation
1. Let bot run on practice account
2. Track all trades in spreadsheet
3. Calculate win rate and profit factor
4. Fine-tune parameters if needed
5. **Goal**: Prove strategy works with paper money

### Week 9-12: Pre-Live Checklist
1. Consistent profitability for 2+ months
2. Win rate 55%+
3. Profit factor >1.5
4. Max drawdown <15%
5. **Goal**: Build confidence before risking real money

### Month 4+: Live Trading (If Profitable)
1. Start with TRADING_MODE=live
2. Use small position sizes (0.5% risk)
3. Scale up slowly as confidence grows
4. Keep manual override capability
5. **Goal**: Transition to live with discipline

---

## ⚠️ Disclaimers

### Risk Warning
- Trading gold (XAU/USD) involves substantial risk
- You can lose more than your initial investment
- Past performance doesn't guarantee future results
- Only trade with money you can afford to lose
- This bot is provided "as-is" without warranties

### Not Financial Advice
- This bot is for educational purposes
- Not financial, investment, or trading advice
- Consult a licensed financial advisor
- You are responsible for your trading decisions
- The authors assume no liability for losses

### Testing Required
- **NEVER** start with live trading
- **ALWAYS** paper trade for 3+ months
- **ONLY** go live after consistent profitability
- Test all configuration changes on practice first

---

## 📞 Support & Resources

### Documentation
- `CLAUDE.md` - Comprehensive strategy guide
- `.env.example` - All configuration options
- Inline code comments - Implementation details

### Oanda Resources
- API Docs: https://developer.oanda.com/
- Practice Account: https://www.oanda.com/demo-account/
- Live Account: https://www.oanda.com/forex-trading/

### Telegram Setup
- Create bot: Talk to @BotFather on Telegram
- Get your ID: Talk to @userinfobot on Telegram

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🙏 Credits

Built with:
- [Oanda v20 API](https://developer.oanda.com/)
- [Technical Indicators](https://www.npmjs.com/package/technicalindicators)
- [Winston Logger](https://www.npmjs.com/package/winston)
- [Telegram Bot API](https://www.npmjs.com/package/node-telegram-bot-api)

Strategy based on proven trend-following principles documented in `CLAUDE.md`.

---

**Remember**: Professional traders aim for consistent, moderate returns. Anyone promising 50%+ monthly is lying or gambling.

Start small. Trade the strategy. Review performance. Adjust. Repeat.

That's how you stay in business for 20+ years. 🏆
