"""
Technical Analysis Indicators Module
Implements various technical indicators for trading signals
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TechnicalAnalysis:
    """Collection of technical analysis indicators"""
    
    @staticmethod
    def moving_average(data: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average (SMA)
        
        Args:
            data: Price data
            period: Number of periods
            
        Returns:
            pd.Series: Moving average values
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def exponential_moving_average(data: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average (EMA)
        
        Args:
            data: Price data
            period: Number of periods
            
        Returns:
            pd.Series: EMA values
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """
        Bollinger Bands
        Shows volatility and overbought/oversold conditions
        
        Args:
            data: Price data (usually close)
            period: Number of periods for SMA
            std_dev: Number of standard deviations
            
        Returns:
            pd.DataFrame: DataFrame with 'middle', 'upper', 'lower' bands
        """
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return pd.DataFrame({
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'bb_width': upper - lower,
            'bb_position': (data - lower) / (upper - lower) if len(upper) > 0 else 0
        })
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI)
        Measures momentum and overbought/oversold conditions
        
        Args:
            data: Price data
            period: Number of periods
            
        Returns:
            pd.Series: RSI values (0-100)
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def stochastic(df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
        """
        Stochastic Oscillator
        Compares closing price to price range, identifies momentum
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: Lookback period
            smooth_k: Smoothing period for %K
            smooth_d: Smoothing period for %D
            
        Returns:
            pd.DataFrame: DataFrame with '%K' and '%D' lines
        """
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()
        
        fastk = 100 * ((df['close'] - low_min) / (high_max - low_min))
        
        k_line = fastk.rolling(window=smooth_k).mean()
        d_line = k_line.rolling(window=smooth_d).mean()
        
        return pd.DataFrame({
            '%K': k_line,
            '%D': d_line
        })
    
    @staticmethod
    def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Average True Range (ATR)
        Measures market volatility
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: Number of periods
            
        Returns:
            pd.Series: ATR values
        """
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def alligator(df: pd.DataFrame) -> pd.DataFrame:
        """
        Alligator Indicator (Williams Alligator)
        Uses three moving averages (Jaw, Teeth, Lips) to identify trends
        
        Args:
            df: DataFrame with 'close' or 'hl2' (high+low)/2
            
        Returns:
            pd.DataFrame: DataFrame with 'jaw', 'teeth', 'lips'
        """
        if 'hl2' in df.columns:
            median_price = df['hl2']
        else:
            median_price = (df['high'] + df['low']) / 2
        
        jaw = median_price.rolling(window=13).mean().shift(-8)
        teeth = median_price.rolling(window=8).mean().shift(-5)
        lips = median_price.rolling(window=5).mean().shift(-3)
        
        return pd.DataFrame({
            'jaw': jaw,
            'teeth': teeth,
            'lips': lips
        })
    
    @staticmethod
    def fractals(df: pd.DataFrame, period: int = 2) -> pd.DataFrame:
        """
        Fractal Indicator
        Identifies local highs and lows
        
        Args:
            df: DataFrame with 'high' and 'low' columns
            period: Number of bars on each side
            
        Returns:
            pd.DataFrame: DataFrame with 'up_fractal', 'down_fractal'
        """
        up_fractal = pd.Series(0, index=df.index, dtype=float)
        down_fractal = pd.Series(0, index=df.index, dtype=float)
        
        for i in range(period, len(df) - period):
            if df['high'].iloc[i] == df['high'].iloc[i-period:i+period+1].max():
                if len(df['high'].iloc[i-period:i+period+1].unique()) > 1:
                    up_fractal.iloc[i] = df['high'].iloc[i]
            
            if df['low'].iloc[i] == df['low'].iloc[i-period:i+period+1].min():
                if len(df['low'].iloc[i-period:i+period+1].unique()) > 1:
                    down_fractal.iloc[i] = df['low'].iloc[i]
        
        return pd.DataFrame({
            'up_fractal': up_fractal,
            'down_fractal': down_fractal
        })
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            data: Price data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
            
        Returns:
            pd.DataFrame: DataFrame with 'macd', 'signal', 'histogram'
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators at once
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            pd.DataFrame: Original data with all indicators
        """
        result = df.copy()
        
        result['sma_9'] = TechnicalAnalysis.moving_average(df['close'], 9)
        result['sma_21'] = TechnicalAnalysis.moving_average(df['close'], 21)
        result['ema_12'] = TechnicalAnalysis.exponential_moving_average(df['close'], 12)
        
        bb = TechnicalAnalysis.bollinger_bands(df['close'], period=20, std_dev=2.0)
        result = pd.concat([result, bb], axis=1)
        
        result['rsi'] = TechnicalAnalysis.rsi(df['close'], period=14)
        
        stoch = TechnicalAnalysis.stochastic(df, period=14)
        result = pd.concat([result, stoch], axis=1)
        
        result['atr'] = TechnicalAnalysis.average_true_range(df, period=14)
        
        macd = TechnicalAnalysis.macd(df['close'])
        result = pd.concat([result, macd], axis=1)
        
        df_with_hl2 = df.copy()
        df_with_hl2['hl2'] = (df['high'] + df['low']) / 2
        alligator = TechnicalAnalysis.alligator(df_with_hl2)
        result = pd.concat([result, alligator], axis=1)
        
        fractals = TechnicalAnalysis.fractals(df, period=2)
        result = pd.concat([result, fractals], axis=1)
        
        return result


class SignalGenerator:
    """Generate trading signals based on technical indicators"""
    
    @staticmethod
    def bollinger_bands_signal(df: pd.DataFrame) -> Optional[dict]:
        """
        Generate signal based on Bollinger Bands
        """
        if df.empty or 'lower' not in df.columns:
            return None
        
        last_row = df.iloc[-1]
        
        if last_row['close'] <= last_row['lower']:
            return {
                'type': 'BUY',
                'indicator': 'Bollinger Bands',
                'confidence': 0.7,
                'entry': last_row['close'],
                'stop_loss': last_row['lower'] - (last_row['bb_width'] * 0.5),
                'take_profit': last_row['middle'] + (last_row['bb_width'] * 0.5)
            }
        
        elif last_row['close'] >= last_row['upper']:
            return {
                'type': 'SELL',
                'indicator': 'Bollinger Bands',
                'confidence': 0.7,
                'entry': last_row['close'],
                'stop_loss': last_row['upper'] + (last_row['bb_width'] * 0.5),
                'take_profit': last_row['middle'] - (last_row['bb_width'] * 0.5)
            }
        
        return None
    
    @staticmethod
    def rsi_signal(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> Optional[dict]:
        """
        Generate signal based on RSI
        """
        if df.empty or 'rsi' not in df.columns:
            return None
        
        last_row = df.iloc[-1]
        rsi = last_row['rsi']
        
        if rsi < oversold:
            return {
                'type': 'BUY',
                'indicator': 'RSI',
                'confidence': 0.6,
                'rsi_value': rsi
            }
        elif rsi > overbought:
            return {
                'type': 'SELL',
                'indicator': 'RSI',
                'confidence': 0.6,
                'rsi_value': rsi
            }
        
        return None
    
    @staticmethod
    def stochastic_signal(df: pd.DataFrame, oversold: int = 20, overbought: int = 80) -> Optional[dict]:
        """
        Generate signal based on Stochastic Oscillator
        """
        if df.empty or '%K' not in df.columns or '%D' not in df.columns:
            return None
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        k_current = current['%K']
        d_current = current['%D']
        k_previous = previous['%K']
        d_previous = previous['%D']
        
        if k_previous <= d_previous and k_current > d_current and k_current < oversold:
            return {
                'type': 'BUY',
                'indicator': 'Stochastic',
                'confidence': 0.65,
                'k_value': k_current,
                'd_value': d_current
            }
        
        elif k_previous >= d_previous and k_current < d_current and k_current > overbought:
            return {
                'type': 'SELL',
                'indicator': 'Stochastic',
                'confidence': 0.65,
                'k_value': k_current,
                'd_value': d_current
            }
        
        return None
    
    @staticmethod
    def alligator_signal(df: pd.DataFrame) -> Optional[dict]:
        """
        Generate signal based on Alligator Indicator
        """
        if df.empty or 'jaw' not in df.columns:
            return None
        
        last_row = df.iloc[-1]
        jaw = last_row['jaw']
        teeth = last_row['teeth']
        lips = last_row['lips']
        
        if pd.notna(jaw) and pd.notna(teeth) and pd.notna(lips):
            if lips > teeth > jaw:
                return {
                    'type': 'BUY',
                    'indicator': 'Alligator',
                    'confidence': 0.7,
                    'trend': 'UPTREND'
                }
            elif lips < teeth < jaw:
                return {
                    'type': 'SELL',
                    'indicator': 'Alligator',
                    'confidence': 0.7,
                    'trend': 'DOWNTREND'
                }
        
        return None
    
    @staticmethod
    def fractal_signal(df: pd.DataFrame, atr: float = None) -> Optional[dict]:
        """
        Generate signal based on Fractals
        """
        if df.empty or 'up_fractal' not in df.columns:
            return None
        
        for i in range(len(df) - 1, max(0, len(df) - 10), -1):
            if df.iloc[i]['up_fractal'] > 0:
                fractal_level = df.iloc[i]['up_fractal']
                if df.iloc[-1]['close'] > fractal_level:
                    return {
                        'type': 'BUY',
                        'indicator': 'Fractal',
                        'confidence': 0.65,
                        'fractal_level': fractal_level
                    }
            
            if df.iloc[i]['down_fractal'] > 0:
                fractal_level = df.iloc[i]['down_fractal']
                if df.iloc[-1]['close'] < fractal_level:
                    return {
                        'type': 'SELL',
                        'indicator': 'Fractal',
                        'confidence': 0.65,
                        'fractal_level': fractal_level
                    }
        
        return None
    
    @staticmethod
    def atr_based_stops(df: pd.DataFrame, entry_price: float, atr_multiplier: float = 2.0) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit based on ATR
        """
        if df.empty or 'atr' not in df.columns:
            return None, None
        
        atr = df.iloc[-1]['atr']
        if pd.isna(atr):
            return None, None
        
        stop_loss = entry_price - (atr * atr_multiplier)
        take_profit = entry_price + (atr * atr_multiplier)
        
        return stop_loss, take_profit
    
    @staticmethod
    def combined_signal(df: pd.DataFrame) -> Optional[dict]:
        """
        Generate signal combining multiple indicators
        """
        signals = []
        
        bb_signal = SignalGenerator.bollinger_bands_signal(df)
        if bb_signal:
            signals.append(bb_signal)
        
        rsi_signal = SignalGenerator.rsi_signal(df)
        if rsi_signal:
            signals.append(rsi_signal)
        
        stoch_signal = SignalGenerator.stochastic_signal(df)
        if stoch_signal:
            signals.append(stoch_signal)
        
        alligator_signal = SignalGenerator.alligator_signal(df)
        if alligator_signal:
            signals.append(alligator_signal)
        
        if len(signals) == 0:
            return None
        
        buy_count = sum(1 for s in signals if s['type'] == 'BUY')
        sell_count = sum(1 for s in signals if s['type'] == 'SELL')
        
        if buy_count >= 2:
            avg_confidence = sum(s['confidence'] for s in signals if s['type'] == 'BUY') / buy_count
            return {
                'type': 'BUY',
                'indicators': [s['indicator'] for s in signals if s['type'] == 'BUY'],
                'confidence': min(avg_confidence + 0.1, 0.95),
                'signal_count': buy_count
            }
        elif sell_count >= 2:
            avg_confidence = sum(s['confidence'] for s in signals if s['type'] == 'SELL') / sell_count
            return {
                'type': 'SELL',
                'indicators': [s['indicator'] for s in signals if s['type'] == 'SELL'],
                'confidence': min(avg_confidence + 0.1, 0.95),
                'signal_count': sell_count
            }
        
        return None
