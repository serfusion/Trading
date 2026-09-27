"""Technical Indicators"""
import pandas as pd
import numpy as np
class TechnicalIndicators:
    @staticmethod
    def sma(df, period, column='close'):
        return df[column].rolling(window=period).mean()
    @staticmethod
    def rsi(df, period=14, column='close'):
        delta = df[column].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
