# GOLD DOMINATOR PRO v3.0 — Quick Start Guide

## HOW TO IMPORT INTO TRADINGVIEW

### Step 1: Open Pine Script Editor
1. Go to [TradingView.com](https://tradingview.com)
2. Open any chart (search for **XAUUSD** or **GOLD**)
3. Click "Pine Editor" tab at the bottom of the screen

### Step 2: Import the Indicator
1. Click "Open" → "New blank indicator"
2. **Delete all existing code** in the editor
3. Copy the ENTIRE contents of `Gold_Dominator_Pro_v3.pine`
4. Paste it into the Pine Editor
5. Click **"Save"** (Ctrl+S) — name it "Gold Dominator Pro v3.0"
6. Click **"Add to chart"**

### Step 3: Import the Strategy (for backtesting)
1. Repeat steps above with `Gold_Dominator_Pro_v3_STRATEGY.pine`
2. This adds the **Strategy Tester** tab at the bottom
3. Click "Strategy Tester" to see backtest results

### Step 4: Configure Settings
1. Click the ⚙️ gear icon on the indicator
2. Adjust parameters to match your risk tolerance:
   - **SL ATR Multiplier:** 1.5 (default) — increase for wider stops
   - **TP1/TP2/TP3 Multipliers:** Adjust take-profit distances
   - **Session Filter:** Enable/disable London+NY filter
   - **ADX Threshold:** 20 (default) — increase for stronger trends only

### Step 5: Set Up Alerts
1. Right-click on the chart → "Add Alert"
2. Condition: "Gold Dominator Pro v3.0"
3. Select "Gold Dominator BUY" or "Gold Dominator SELL"
4. Set notification method (popup, email, webhook, mobile push)
5. Set expiration (recommend "Open-ended")

---

## FILE LIST

| File | Purpose |
|------|---------|
| `GOLD_DOMINATOR_STRATEGY.md` | Full strategy documentation (rules, risk mgmt, session playbook) |
| `Gold_Dominator_Pro_v3.pine` | **TradingView Indicator** — import this for live signals + dashboard |
| `Gold_Dominator_Pro_v3_STRATEGY.pine` | **TradingView Strategy** — import this for backtesting |
| `QUICKSTART.md` | This guide |

---

## DASHBOARD READING GUIDE

The indicator displays a real-time dashboard (top-right corner) showing:

| Field | What It Means |
|-------|--------------|
| **H4 Trend** | BULLISH / BEARISH / NEUTRAL — overall market direction |
| **RSI** | Current RSI value with color coding (green=oversold, red=overbought) |
| **MACD** | BULLISH (histogram > 0) or BEARISH (histogram < 0) |
| **ADX** | TRENDING (>20) or CHOPPY (<20) — only trade when trending |
| **StochRSI** | OVERBOUGHT / OVERSOLD / NEUTRAL — entry timing |
| **ATR(14)** | Current volatility in USD — used for SL/TP sizing |
| **Volume** | ABOVE AVG or BELOW AVG — need above average for signals |
| **Session** | Current trading session — OVERLAP is best |
| **LONG Score** | Score out of 100 — need 80+ for buy signal |
| **SHORT Score** | Score out of 100 — need 80+ for sell signal |
| **Stop Loss** | Calculated SL price for current position |
| **TP1/TP2/TP3** | Three take-profit levels |
| **SIGNAL** | Current action: BUY NOW / SELL NOW / WAITING |

---

## TRADING RULES (QUICK REFERENCE)

### When to BUY:
✅ LONG Score >= 80/100
✅ Green "BUY" label appears on chart
✅ Green background (bullish trend)
✅ Dashboard shows ">>> BUY NOW <<<"

### When to SELL:
✅ SHORT Score >= 80/100
✅ Red "SELL" label appears on chart
✅ Red background (bearish trend)
✅ Dashboard shows ">>> SELL NOW <<<"

### When to STAY OUT:
❌ Score below 80 for both directions
❌ ADX showing "CHOPPY"
❌ Session showing "OFF HOURS"
❌ Volume showing "BELOW AVG"
❌ Major news event within 30 minutes

### Position Management:
1. **At TP1 hit:** Close 50% of position, move SL to breakeven
2. **At TP2 hit:** Close 30% of position, trail SL
3. **At TP3 hit:** Close remaining 20%
4. **Max daily loss:** 3% of account → stop trading

---

## RECOMMENDED CHART SETUP

1. **Symbol:** XAUUSD (or GOLD on your broker)
2. **Timeframe:** H1 (1-hour chart) for primary monitoring
3. **Check H4:** Before each trade to confirm trend direction
4. **Chart type:** Candlestick
5. **Other indicators:** None needed — Gold Dominator includes everything

---

## OPTIMIZATION TIPS

### For Higher Win Rate (safer, fewer trades):
- Increase ADX threshold to 25
- Increase volume multiplier to 1.5
- Only trade during London/NY overlap (13:00-16:00 UTC)
- Increase score requirement to 90/100

### For More Trades (slightly lower win rate):
- Decrease ADX threshold to 18
- Decrease volume multiplier to 1.0
- Enable all session trading
- Decrease score requirement to 70/100

### Best Broker Settings for Gold:
- Spread: Under 30 pips ($0.30)
- Leverage: 1:100 or 1:200
- Execution: ECN/STP preferred
- Swap-free if holding overnight

---

## DISCLAIMER

This trading strategy is for educational and informational purposes only. It is NOT financial advice. Trading gold (XAU/USD) involves substantial risk of loss. Past performance and backtesting results do not guarantee future results. Always practice with a demo account first. Never risk money you cannot afford to lose.
