# GOLD DOMINATOR PRO - XAU/USD Trading Strategy
## Target: 80% Win Rate | 20% Max Loss | Professional Grade

---

## STRATEGY OVERVIEW

**Name:** Gold Dominator Pro v3.0
**Instrument:** XAU/USD (Gold vs US Dollar)
**Timeframes:** H1 (primary), H4 (trend confirmation), M15 (precision entry)
**Style:** Trend-following with mean-reversion filters
**Target Win Rate:** 80%+
**Risk per Trade:** 1-1.5% of account
**Risk:Reward:** Minimum 1:1.2 (scalable to 1:2+ with trailing)

---

## PART 1: TECHNICAL INDICATOR STACK

### Layer 1 - TREND IDENTIFICATION (H4 Timeframe)
| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| EMA 21 | Period: 21, Source: Close | Fast trend direction |
| EMA 55 | Period: 55, Source: Close | Medium trend direction |
| EMA 200 | Period: 200, Source: Close | Major trend / institutional bias |

**Rules:**
- **BULLISH BIAS:** Price > EMA 200 AND EMA 21 > EMA 55
- **BEARISH BIAS:** Price < EMA 200 AND EMA 21 < EMA 55
- **NO TRADE ZONE:** EMAs tangled (21 and 55 within 3 points of each other)

### Layer 2 - MOMENTUM CONFIRMATION (H1 Timeframe)
| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| RSI | Period: 14, OB: 72, OS: 28 | Momentum + divergence |
| MACD | Fast: 12, Slow: 26, Signal: 9 | Trend momentum crossovers |
| Stochastic RSI | K: 14, D: 3, Smooth: 3, OB: 80, OS: 20 | Precision timing |

**Rules:**
- **LONG ENTRY:** RSI > 45 AND RSI < 72 AND MACD histogram > 0 AND StochRSI K crosses above D below 30
- **SHORT ENTRY:** RSI < 55 AND RSI > 28 AND MACD histogram < 0 AND StochRSI K crosses below D above 70

### Layer 3 - VOLATILITY FILTER (H1 Timeframe)
| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| ATR | Period: 14 | Dynamic SL/TP sizing |
| Bollinger Bands | Period: 20, StdDev: 2.0 | Volatility squeeze/expansion |
| ADX | Period: 14, Threshold: 20 | Trend strength filter |

**Rules:**
- **TRADE ONLY WHEN:** ADX > 20 (confirmed trend, not chop)
- **AVOID:** When BB width < 15 points (squeeze = imminent breakout, unpredictable direction)
- **STOP LOSS:** 1.5x ATR(14) from entry
- **TAKE PROFIT 1:** 1.2x ATR(14) from entry (60% of position)
- **TAKE PROFIT 2:** 2.5x ATR(14) from entry (remaining 40%, trailing)

### Layer 4 - VOLUME & SESSION FILTER
| Filter | Parameters | Purpose |
|--------|-----------|---------|
| Volume SMA | Period: 20 | Volume confirmation |
| Session Filter | London + NY only | High-liquidity sessions |
| News Filter | Avoid 30min pre/post | Major USD events |

**Rules:**
- **VOLUME:** Current volume must be > 1.2x Volume SMA(20)
- **SESSION:** Only trade 08:00-11:00 UTC (London) and 13:00-17:00 UTC (NY)
- **LONDON/NY OVERLAP (13:00-16:00 UTC):** Best window - tighten SL by 20%

---

## PART 2: ENTRY RULES (THE COMPLETE SIGNAL)

### LONG ENTRY CHECKLIST (ALL must be TRUE):
```
[x] H4: Price > EMA 200
[x] H4: EMA 21 > EMA 55
[x] H1: RSI between 45-72
[x] H1: MACD histogram > 0 (or crossing to positive)
[x] H1: StochRSI K crosses above D below level 30
[x] H1: ADX > 20
[x] H1: Price above lower Bollinger Band
[x] H1: Volume > 1.2x SMA(20)
[x] Session: London or NY active
[x] No major USD news within 30 minutes
```
**Signal Strength Score:** Each condition = 10 points. Need >= 80 to trade.

### SHORT ENTRY CHECKLIST (ALL must be TRUE):
```
[x] H4: Price < EMA 200
[x] H4: EMA 21 < EMA 55
[x] H1: RSI between 28-55
[x] H1: MACD histogram < 0 (or crossing to negative)
[x] H1: StochRSI K crosses below D above level 70
[x] H1: ADX > 20
[x] H1: Price below upper Bollinger Band
[x] H1: Volume > 1.2x SMA(20)
[x] Session: London or NY active
[x] No major USD news within 30 minutes
```

---

## PART 3: EXIT RULES

### Stop Loss Placement
| Method | Calculation | When to Use |
|--------|------------|-------------|
| **Primary SL** | 1.5 x ATR(14) from entry | Default for all trades |
| **Structure SL** | Below/above nearest swing H/L | When swing is closer than ATR SL |
| **Maximum SL** | $15 per lot (150 pips) | Hard cap regardless of ATR |

### Take Profit Strategy (Scaled Exit)
| Level | Distance | Position % | Action |
|-------|----------|-----------|--------|
| **TP1** | 1.2 x ATR(14) | Close 50% | Move SL to breakeven |
| **TP2** | 2.0 x ATR(14) | Close 30% | Trail SL by 0.5x ATR |
| **TP3** | 3.0 x ATR(14) | Close remaining 20% | Trail SL by 0.75x ATR |

### Trailing Stop Rules
- After TP1 hit: Move SL to entry (breakeven)
- After TP2 hit: Trail SL at 0.5x ATR behind price
- If price reverses 0.75x ATR from highest point after TP2: Close all remaining

---

## PART 4: RISK MANAGEMENT

### Position Sizing Formula
```
Lot Size = (Account Balance x Risk%) / (SL in pips x Pip Value)

Example:
- Account: $10,000
- Risk: 1.5% = $150
- SL: 100 pips (10 USD on gold)
- Pip value per standard lot: $10
- Lot Size = $150 / (100 x $10) = 0.15 lots
```

### Daily Risk Rules
| Rule | Value | Action if Breached |
|------|-------|-------------------|
| Max risk per trade | 1.5% of account | Reduce lot size |
| Max daily loss | 3% of account | STOP trading for the day |
| Max weekly loss | 6% of account | STOP trading, review strategy |
| Max open trades | 2 simultaneous | Wait for exit before new entry |
| Max consecutive losses | 3 in a row | Reduce size by 50% next trade |
| Daily trade limit | 4 trades max | No more entries regardless of signals |

### Drawdown Recovery Protocol
| Drawdown Level | Action |
|---------------|--------|
| 0-3% | Normal trading |
| 3-5% | Reduce risk to 1% per trade |
| 5-8% | Reduce risk to 0.5%, only A+ setups |
| 8-10% | STOP. Review. Paper trade for 1 week |
| >10% | Full strategy audit required |

---

## PART 5: SESSION PLAYBOOK

### Asian Session (00:00-08:00 UTC)
- **DO NOT TRADE** - Low liquidity, erratic spreads on gold
- Use this time to mark key levels from D1 chart

### London Session (08:00-11:00 UTC)
- **TRADE** - Good volatility, gold tends to set daily direction
- Look for: Breakouts of Asian range, EMA retests
- Typical range: 15-25 USD

### London/NY Overlap (13:00-16:00 UTC)
- **BEST WINDOW** - Highest liquidity and cleanest moves
- Look for: Continuation of London trend, DXY-driven moves
- Typical range: 20-35 USD
- Tighten SL by 20%, increase position by 20%

### NY Close (16:00-17:00 UTC)
- **CLOSE ALL POSITIONS** - Unless running on D1 swing trade
- Do not open new positions after 16:30 UTC

---

## PART 6: FUNDAMENTAL FILTERS

### DXY Correlation Filter
- Gold has ~-0.85 correlation with DXY
- **LONG GOLD:** Only when DXY EMA(21) < DXY EMA(55) on H4
- **SHORT GOLD:** Only when DXY EMA(21) > DXY EMA(55) on H4
- If DXY and Gold moving in same direction: NO TRADE (anomaly)

### News Event Calendar
| Event | Impact on Gold | Action |
|-------|---------------|--------|
| FOMC Rate Decision | EXTREME | No trading 2hr before/after |
| NFP (Non-Farm Payrolls) | EXTREME | No trading 1hr before/after |
| CPI Data | HIGH | No trading 30min before/after |
| PPI Data | MEDIUM | Tighten SL by 30% |
| GDP Data | MEDIUM | Tighten SL by 30% |
| Jobless Claims | LOW | Normal trading |
| Fed Speakers | MEDIUM | Awareness only |
| Geopolitical Events | VARIABLE | Consider long bias |

### Gold-Specific Drivers (2024-2026 Regime)
1. **Central Bank Buying:** Record purchases by China, India, Turkey - Structural LONG bias
2. **De-dollarization:** BRICS alternatives - Supports gold above $2,000 floor
3. **Real Yields:** When US 10Y yield minus CPI < 1% - Bullish gold
4. **ETF Flows:** Monitor GLD holdings - Rising = institutional accumulation
5. **Seasonality:** Strong months: Jan, Feb, Aug, Sep, Nov. Weak: Mar, Jun

---

## PART 7: PERFORMANCE TARGETS & VALIDATION

### Minimum Backtest Requirements
- **Period:** 2 years minimum (covering different market regimes)
- **Trades:** Minimum 200 trades for statistical significance
- **Win Rate:** >= 78% (targeting 80%)
- **Profit Factor:** >= 2.0
- **Sharpe Ratio:** >= 1.5
- **Max Drawdown:** <= 12%
- **Average Win / Average Loss:** >= 0.8 (acceptable with 80% WR)
- **Expectancy per trade:** >= 0.5% of account

### Monthly Performance Targets
| Metric | Conservative | Aggressive |
|--------|-------------|-----------|
| Monthly Return | 5-8% | 10-15% |
| Win Rate | 78-82% | 80-85% |
| Trades/Month | 20-30 | 30-50 |
| Max Monthly DD | 5% | 8% |
| Profit Factor | 2.0+ | 2.5+ |

---

## PART 8: QUICK REFERENCE CARD

### BUY Signal Summary
```
H4 TREND:  Price > EMA200, EMA21 > EMA55
H1 ENTRY:  RSI 45-72, MACD+ , StochRSI cross up from <30
FILTERS:   ADX>20, Vol>1.2xSMA, London/NY session
STOP LOSS: 1.5 x ATR(14) below entry
TP1:       1.2 x ATR(14) — close 50%, move SL to BE
TP2:       2.0 x ATR(14) — close 30%, trail SL
TP3:       3.0 x ATR(14) — close 20%, trail tight
RISK:      1-1.5% per trade, max 3% daily
```

### SELL Signal Summary
```
H4 TREND:  Price < EMA200, EMA21 < EMA55
H1 ENTRY:  RSI 28-55, MACD- , StochRSI cross down from >70
FILTERS:   ADX>20, Vol>1.2xSMA, London/NY session
STOP LOSS: 1.5 x ATR(14) above entry
TP1:       1.2 x ATR(14) — close 50%, move SL to BE
TP2:       2.0 x ATR(14) — close 30%, trail SL
TP3:       3.0 x ATR(14) — close 20%, trail tight
RISK:      1-1.5% per trade, max 3% daily
```

---

---

## PART 9: PRO FEATURES (STRATEGY VERSION ONLY)

### Equity Curve Filter
The strategy version includes a built-in equity curve filter. When enabled, the system only takes new trades when the account equity is **above its own EMA** (default: 20-period). This automatically pauses trading during drawdown periods and resumes when the strategy recovers — a technique used by professional CTAs and systematic funds.

- **Enable/Disable:** Settings → Equity Curve Filter
- **EMA Length:** Default 20 (adjustable 5-100)
- **Effect:** Prevents compounding losses during negative regime shifts

### Max Drawdown Guard
Hard-caps maximum drawdown at a configurable threshold (default 10%). When breached, no new positions are opened until equity recovers. This is your circuit breaker.

### Performance Metrics Dashboard
The strategy version displays a live performance table (bottom-right corner) showing:
- Net Profit ($)
- Win Rate (%)
- Profit Factor
- Total Trades
- Average Win / Average Loss
- Current Max Drawdown (%)

### How to Backtest Properly
1. Apply the STRATEGY version to XAUUSD H1 chart
2. Set date range: minimum 2 years (e.g., Jan 2024 - Jul 2026)
3. Check "Strategy Tester" tab at the bottom
4. Review: Net Profit, Win Rate, Profit Factor, Max Drawdown
5. **Target metrics:** Win Rate ≥ 78%, Profit Factor ≥ 2.0, Max DD ≤ 12%
6. If metrics are below target, increase ADX threshold (+2) and volume multiplier (+0.1)

---

**DISCLAIMER:** This strategy is for educational purposes. Past performance does not guarantee future results. Trading gold carries significant risk. Always use proper risk management and never risk more than you can afford to lose.
