import pandas as pd
import numpy as np

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    d = series.diff()
    gain = d.where(d > 0, 0.0).rolling(period).mean()
    loss = -d.where(d < 0, 0.0).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))

def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def _vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, 1)
    cum_tpv = (tp * vol).cumsum()
    cum_vol = vol.cumsum()
    return cum_tpv / cum_vol

def _adx(df: pd.DataFrame, period: int = 14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = low.shift(1) - low
    
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
    
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    atr = pd.Series(tr).rolling(period).sum()
    plus_di = 100 * (pd.Series(plus_dm).rolling(period).sum() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(period).sum() / atr)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    adx = dx.rolling(period).mean()
    return adx, pd.Series(plus_di, index=df.index), pd.Series(minus_di, index=df.index)

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h = df['high']
    l = df['low']
    c = df['close']
    tr1 = h - l
    tr2 = np.abs(h - c.shift(1))
    tr3 = np.abs(l - c.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0):
    c = df['close']
    ema = _ema(c, period)
    atr = _atr(df, period)
    upper = ema + (multiplier * atr)
    lower = ema - (multiplier * atr)
    return ema, upper, lower

def _momentum_expansion(df: pd.DataFrame) -> tuple:
    if len(df) < 6:
        return False, False
    c = df['close']
    o = df['open']
    h = df['high']
    l = df['low']
    body = np.abs(c - o)
    
    # BRUTAL HONESTY LOGIC: 1 Lilin Raksasa yang besarnya 2x lipat dari rata-rata 5 lilin sebelumnya
    avg_body = body.iloc[-6:-1].mean()
    is_giant_candle = body.iloc[-1] > (avg_body * 2.0)
    
    # ANTI-FAKEOUT (Rejection Filter):
    # Jika ekor penolakan (wick) terlalu panjang (> 50% dari body), itu adalah ciri khas harga memantul (Exhaustion).
    upper_wick = h.iloc[-1] - np.maximum(c.iloc[-1], o.iloc[-1])
    lower_wick = np.minimum(c.iloc[-1], o.iloc[-1]) - l.iloc[-1]
    
    bull_exp = is_giant_candle and (c.iloc[-1] > o.iloc[-1]) and (upper_wick < body.iloc[-1] * 0.5)
    bear_exp = is_giant_candle and (c.iloc[-1] < o.iloc[-1]) and (lower_wick < body.iloc[-1] * 0.5)
    return bull_exp, bear_exp

def calculate_confluence_score(df: pd.DataFrame) -> dict:
    # Dummy function to preserve backward compatibility for imports
    return {"bull": 0.0, "bear": 0.0}

def get_direction(bars_m5) -> str:
    """Returns BUY or SELL based on Hyper-Active Trend Engine (Multi-Condition)."""
    if bars_m5 is None or len(bars_m5) < 60:
        return None
        
    c = bars_m5['close']
    o = bars_m5['open']
    
    current_price = c.iloc[-1]
    
    # 1. Keltner Channels & EMAs
    ema20, upper_k, lower_k = _keltner_channels(bars_m5, 20, 2.0)
    ema9 = _ema(c, 9)
    
    # 2. Momentum Expansion
    bull_exp, bear_exp = _momentum_expansion(bars_m5)
    
    # 3. ADX Filter & DMI
    adx_line, pdi, mdi = _adx(bars_m5, 14)
    current_adx = adx_line.iloc[-1]
    
    # === HYPER-ACTIVE TREND ENGINE ===
    if current_adx > 20:
        up_trend = pdi.iloc[-1] > mdi.iloc[-1]
        down_trend = mdi.iloc[-1] > pdi.iloc[-1]
        
        # --- BUY CONDITIONS ---
        # 1. Breakout Velocity
        if current_price > upper_k.iloc[-1] or bull_exp:
            return "BUY"
            
        # 2. Trend Continuation & Golden Reversion
        if current_adx > 25 and up_trend:
            # Pushing up from EMA 20 (Reversion to Mean)
            if current_price >= ema20.iloc[-1] and c.iloc[-1] > o.iloc[-1]:
                # Engulfing / Reversal dari koreksi merah
                if c.iloc[-2] < o.iloc[-2]: 
                    return "BUY"
                # Riding the fast momentum (Close di atas EMA 9)
                if current_price > ema9.iloc[-1]: 
                    return "BUY"
                    
        # --- SELL CONDITIONS ---
        # 1. Breakout Velocity
        if current_price < lower_k.iloc[-1] or bear_exp:
            return "SELL"
            
        # 2. Trend Continuation & Golden Reversion
        if current_adx > 25 and down_trend:
            # Pushing down from EMA 20
            if current_price <= ema20.iloc[-1] and c.iloc[-1] < o.iloc[-1]:
                # Engulfing / Reversal dari koreksi hijau
                if c.iloc[-2] > o.iloc[-2]: 
                    return "SELL"
                # Riding the fast momentum
                if current_price < ema9.iloc[-1]:
                    return "SELL"
                  
    return None

def check_h1_confluence(bars_h1: pd.DataFrame, current_price: float) -> str:
    """Check macro H1 trend confluence using EMA 10."""
    if bars_h1 is None or bars_h1.empty or len(bars_h1) < 10:
        return "BOTH"
    close = bars_h1["close"]
    ema10 = _ema(close, 10).iloc[-1]
    return "BUY" if current_price >= ema10 else "SELL"

def _stochastic_dir(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    h, l, c = df["high"], df["low"], df["close"]
    l_min = l.rolling(k_period).min()
    h_max = h.rolling(k_period).max()
    stoch_k = 100 * ((c - l_min) / (h_max - l_min + 1e-9))
    stoch_d = stoch_k.rolling(d_period).mean()
    return stoch_k, stoch_d

def get_sideways_direction(bars_m5: pd.DataFrame) -> str:
    """Returns BUY or SELL based on Mean Reversion (Bollinger Bands & Stochastic) untuk Mode Sideways."""
    if bars_m5 is None or len(bars_m5) < 30:
        return None
        
    c = bars_m5['close']
    o = bars_m5['open']
    h = bars_m5['high']
    l = bars_m5['low']
    
    current_price = c.iloc[-1]
    current_open = o.iloc[-1]
    current_high = h.iloc[-1]
    current_low = l.iloc[-1]
    
    # 1. Bollinger Bands Calculation (20, 2.0)
    sma = c.rolling(20).mean()
    std = c.rolling(20).std()
    upper_bb = (sma + (std * 2.0)).iloc[-1]
    lower_bb = (sma - (std * 2.0)).iloc[-1]
    
    # 2. Stochastic
    stoch_k, stoch_d = _stochastic_dir(bars_m5, 14, 3)
    current_k = stoch_k.iloc[-1]
    current_d = stoch_d.iloc[-1]
    
    # Sideways BUY (Lantai Bawah): Harga menjilat/menembus Lower BB, Stoch Jenuh Jual (<25) + Crossover
    if current_price <= lower_bb or current_low <= lower_bb:
        if current_k < 25 and current_k > current_d:
            return "BUY"
            
    # Sideways SELL (Atap Atas): Harga menjilat/menembus Upper BB, Stoch Jenuh Beli (>75) + Crossover
    if current_price >= upper_bb or current_high >= upper_bb:
        if current_k > 75 and current_k < current_d:
            return "SELL"
            
    return None
