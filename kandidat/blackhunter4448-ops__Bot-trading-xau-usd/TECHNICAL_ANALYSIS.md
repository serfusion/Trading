# Technical Analysis Documentation

## Implemented Indicators

### 1. **Bollinger Bands**
- **Description**: Shows volatility and potential overbought/oversold conditions
- **Parameters**: Period (20), Standard Deviations (2)
- **Signal Logic**:
  - BUY when price touches lower band (potential reversal)
  - SELL when price touches upper band (potential reversal)
- **Usage**: Identify support/resistance and volatility expansion/contraction

### 2. **Relative Strength Index (RSI)**
- **Description**: Measures momentum and price velocity
- **Parameters**: Period (14)
- **Range**: 0-100
- **Signal Logic**:
  - BUY when RSI < 30 (oversold)
  - SELL when RSI > 70 (overbought)
- **Neutral Zone**: 30-70

### 3. **Stochastic Oscillator**
- **Description**: Compares closing price to price range to identify momentum
- **Parameters**: Period (14), K-line smoothing (3), D-line smoothing (3)
- **Range**: 0-100
- **Signal Logic**:
  - BUY when %K crosses above %D with both below 20 (oversold)
  - SELL when %K crosses below %D with both above 80 (overbought)
- **Advantage**: Better at identifying divergences than RSI

### 4. **Average True Range (ATR)**
- **Description**: Measures market volatility
- **Parameters**: Period (14)
- **Usage**: 
  - Determine position sizing
  - Calculate dynamic stop-loss and take-profit levels
  - Identify quiet vs volatile market periods

### 5. **Alligator Indicator (Williams Alligator)**
- **Description**: Uses three moving averages to identify trends
- **Components**:
  - Jaw (blue): 13-period SMA shifted 8 bars
  - Teeth (red): 8-period SMA shifted 5 bars
  - Lips (green): 5-period SMA shifted 3 bars
- **Signal Logic**:
  - BUY when Lips > Teeth > Jaw (uptrend)
  - SELL when Lips < Teeth < Jaw (downtrend)
  - Quiet when lines are intertwined (consolidation)

### 6. **Fractals**
- **Description**: Identifies local highs and lows (support/resistance)
- **Parameters**: Period (2 bars on each side)
- **Signal Logic**:
  - UP Fractal: High is higher than all surrounding bars
  - DOWN Fractal: Low is lower than all surrounding bars
- **Usage**: 
  - Entry/exit points
  - Support/resistance levels
  - Breakout signals

### 7. **MACD (Moving Average Convergence Divergence)**
- **Description**: Identifies trend changes and momentum
- **Parameters**: 
  - Fast EMA (12)
  - Slow EMA (26)
  - Signal line (9)
- **Components**:
  - MACD line (Fast - Slow)
  - Signal line (EMA of MACD)
  - Histogram (MACD - Signal)

## Signal Generation Strategy

### Combined Signal (Multi-Indicator Confirmation)
The bot generates signals that require confirmation from at least 2 indicators:

1. **Bollinger Bands** - Volatility-based
2. **RSI** - Momentum-based
3. **Stochastic** - Oscillator-based
4. **Alligator** - Trend-based

**Confidence Levels**:
- Single indicator: 60-70% confidence
- Combined signal: 75-95% confidence (based on number of confirmations)

### Stop Loss & Take Profit Calculation
- Calculated using **ATR multiplier (2.0)**
- SL = Entry - (2 × ATR)
- TP = Entry + (2 × ATR)
- Adjustable based on risk tolerance

## Usage Example

```python
from technical_analysis import TechnicalAnalysis, SignalGenerator
import pandas as pd

# Fetch OHLC data
# df should have: 'open', 'high', 'low', 'close', 'volume'

# Calculate all indicators
df = TechnicalAnalysis.calculate_all_indicators(df)

# Get individual signals
bb_signal = SignalGenerator.bollinger_bands_signal(df)
rsi_signal = SignalGenerator.rsi_signal(df)
stoch_signal = SignalGenerator.stochastic_signal(df)
alligator_signal = SignalGenerator.alligator_signal(df)
fractal_signal = SignalGenerator.fractal_signal(df)

# Get combined signal (requires 2+ confirmations)
combined_signal = SignalGenerator.combined_signal(df)

# Calculate stops based on ATR
stop_loss, take_profit = SignalGenerator.atr_based_stops(df, entry_price=2000)
```

## Best Practices

1. **Use Multiple Timeframes**: Confirm signals on higher timeframes
2. **Avoid Consolidation**: Fractal indicator helps identify trading ranges
3. **Watch Volatility**: Use ATR to adjust position sizes in volatile markets
4. **Divergences**: Monitor RSI/Stochastic divergences for reversals
5. **Trend Confirmation**: Use Alligator to confirm trend direction

## Risk Management

- **Position Sizing**: Based on account equity and risk per trade
- **Risk per Trade**: 1-2% of account balance
- **Stop Loss**: Always set (calculated by ATR)
- **Take Profit**: Use dynamic levels based on ATR
- **Daily Loss Limit**: Stop trading after X% daily loss

## Limitations

- Technical indicators are **lagging** - they follow price action
- **No guarantee** of accurate signals in all market conditions
- Highly volatile/ranged markets require adjusted parameters
- **Always use proper risk management**
- Backtest strategies before live trading
