# ⚡ Quick Start Guide - Gold Trading Bot

Get your bot running in 5 minutes!

---

## 🎯 Prerequisites

1. **Oanda Account** (practice recommended)
   - Sign up: https://www.oanda.com/demo-account/
   - Get API credentials from account dashboard

2. **Telegram Bot** (optional but recommended)
   - Talk to @BotFather on Telegram
   - Create new bot and get token
   - Talk to @userinfobot to get your chat ID

3. **Node.js 18+** installed on your system

---

## 🚀 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd Oanda_Gold
npm install
```

### Step 2: Configure Bot
```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or use any text editor
```

**Minimum required settings:**
```bash
# Oanda Practice Account
OANDA_API_KEY=abc123your-practice-api-key-here
OANDA_ACCOUNT_ID=101-004-1234567-001
TRADING_MODE=practice

# Telegram (optional)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=987654321
ENABLE_TELEGRAM=true
```

### Step 3: Test Connection
```bash
npm test
```

You should see:
```
✅ Connection successful!
✅ Account balance retrieved
✅ Market data accessible
✅ ALL TESTS PASSED!
```

### Step 4: Start Bot
```bash
npm start
```

**That's it!** 🎉 Your bot is now running and scanning for trades.

---

## 📱 Telegram Setup (5 Minutes)

### 1. Create Your Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the **token** (looks like `123456:ABC-DEF...`)

### 2. Get Your Chat ID
1. Search for **@userinfobot** on Telegram
2. Send `/start`
3. Copy your **user ID** (looks like `987654321`)

### 3. Add to .env
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=987654321
ENABLE_TELEGRAM=true
```

### 4. Test It
1. Restart bot: `npm start`
2. Open Telegram and search for your bot
3. Send `/start`
4. You should get a welcome message!

**Available Commands:**
- `/status` - See bot status and P&L
- `/positions` - View open trades
- `/pnl` - Profit & loss reports
- `/balance` - Account balance
- `/help` - All commands

---

## 🐳 Docker Quick Start

### Option 1: Docker Compose (Easiest)
```bash
# Build and start in one command
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Manual Docker
```bash
# Build image
docker build -t gold-bot .

# Run container
docker run -d \
  --name gold-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  gold-bot

# View logs
docker logs -f gold-bot

# Stop
docker stop gold-bot
docker rm gold-bot
```

---

## 🖥️ VPS Deployment (10 Minutes)

### Step 1: Connect to VPS
```bash
ssh root@your-vps-ip
```

### Step 2: Install Docker
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Verify
docker --version
docker-compose --version
```

### Step 3: Clone and Configure
```bash
# Clone your repo (or upload files via SFTP)
git clone <your-repo-url>
cd Oanda_Gold

# Configure
cp .env.example .env
nano .env  # Edit with your credentials
```

### Step 4: Start Bot
```bash
# Build and run
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f gold-bot
```

### Step 5: Enable Auto-Restart
Bot will automatically restart if it crashes or VPS reboots (already configured in `docker-compose.yml`).

**Monitor remotely via Telegram!** 📱

---

## ✅ Post-Setup Checklist

After starting your bot, verify:

- [ ] Bot connects to Oanda successfully
- [ ] Market data is being fetched
- [ ] Telegram bot responds to `/start`
- [ ] `/status` shows current balance
- [ ] Logs are being written to `logs/gold_bot.log`
- [ ] Bot is in **PRACTICE** mode (verify in `/status`)

---

## 🎯 First Day Checklist

**Monitor these things on day 1:**

1. **Check Telegram**
   - Send `/status` every few hours
   - Verify bot is scanning market
   - Look for "No setup" messages (normal)

2. **Review Logs**
   ```bash
   tail -f logs/gold_bot.log
   ```
   - Should see market scans every 15 minutes
   - Look for "Scanning market for setups..."
   - Pattern: Scanning → Analysis → No setup (or Trade signal)

3. **Wait for First Trade**
   - Bot only trades when **all 3 confirmations** align
   - May take hours or days for perfect setup
   - **This is normal!** Quality over quantity

4. **When First Trade Happens**
   - You'll get Telegram notification
   - Check `/positions` to see trade details
   - Monitor via `/status` for P&L updates

---

## 🚨 Common Issues

### "Connection test failed"
**Solution**: Check your .env file
```bash
# Verify these are correct
OANDA_API_KEY=<your-actual-key>
OANDA_ACCOUNT_ID=<your-actual-account-id>
TRADING_MODE=practice  # Must match account type!
```

### "Telegram bot not responding"
**Solution**: Verify token and chat ID
```bash
# Test token format (should be like: 123456789:ABC...)
echo $TELEGRAM_BOT_TOKEN

# Test chat ID (should be numeric)
echo $TELEGRAM_CHAT_ID

# Restart bot after fixing
docker-compose restart  # or npm start
```

### "No trades happening"
**Solution**: This is normal!
- Bot waits for **perfect setups** (all 3 confirmations)
- May trade 2-5 times per week
- Check logs for "No setup: <reason>"
- Be patient - quality over quantity

### "Bot stopped after daily loss"
**Solution**: Working as intended!
- Bot stops trading after hitting MAX_DAILY_LOSS
- Protects your account from revenge trading
- Will resume automatically tomorrow
- Check `/status` to see current daily P&L

---

## 📊 Monitoring Your Bot

### Via Telegram (Recommended)
```
/status    - Every few hours
/positions - When you see trade notification
/pnl       - End of day
/balance   - Weekly
```

### Via Logs
```bash
# Real-time logs
tail -f logs/gold_bot.log

# Docker logs
docker-compose logs -f gold-bot

# Search for trades
grep "TRADE" logs/gold_bot.log
```

### Via Docker
```bash
# Check if running
docker ps

# Resource usage
docker stats gold-bot

# Restart if needed
docker-compose restart
```

---

## 🎓 Next Steps

### Week 1: Learn & Monitor
- Watch how bot identifies setups
- Review each trade in logs
- Understand the Triple Confirmation logic
- Use Telegram to stay updated

### Week 2-8: Track Performance
- Create spreadsheet of all trades
- Calculate your win rate
- Monitor drawdowns
- Adjust settings if needed (on practice!)

### After 3 Months: Decision Point
**If profitable on practice:**
- Win rate >55%
- Profit factor >1.5
- Max drawdown <15%
- **Consider** switching to live with small sizes

**If not profitable:**
- Review trades to find issues
- Adjust parameters
- Continue on practice
- **DO NOT** go live yet

---

## 💡 Pro Tips

1. **Start Conservative**
   - Use default settings for first month
   - Don't tweak parameters too soon
   - Let strategy prove itself

2. **Keep a Journal**
   - Screenshot each trade notification
   - Note market conditions
   - Record your emotions (FOMO? Fear?)
   - Learn what works

3. **Use Telegram Actively**
   - Check `/status` daily
   - Review `/positions` when trading
   - Monitor `/pnl` weekly
   - Stay connected remotely

4. **Be Patient**
   - Strategy trades 2-5 times per week
   - Some weeks may have zero trades
   - This is GOOD - quality over quantity
   - Trust the process

5. **Paper Trade Longer Than You Think**
   - 3 months minimum
   - 6 months better
   - 12 months ideal
   - Never risk money you can't afford to lose

---

## 🆘 Get Help

### Check Logs First
```bash
# Recent errors
tail -100 logs/gold_bot.log | grep ERROR

# Recent trades
tail -100 logs/gold_bot.log | grep TRADE
```

### Restart Bot
```bash
# Docker
docker-compose restart

# NPM
# Press Ctrl+C, then:
npm start
```

### Full Reset
```bash
# Stop bot
docker-compose down

# Clear logs (optional)
rm -rf logs/*

# Restart fresh
docker-compose up -d
```

---

**You're all set!** 🚀

The bot is now running 24/7, scanning for high-probability gold trades.

**Remember**: This is a marathon, not a sprint. Start on practice, be patient, and let the strategy prove itself over time.

Good luck! 🏆
