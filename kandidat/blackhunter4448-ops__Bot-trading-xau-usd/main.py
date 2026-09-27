#!/usr/bin/env python3
"""
XAU/USD Trading Bot with MetaTrader 5 and Technical Analysis
A bot for automated trading of gold (XAU/USD) using MT5 connection and technical indicators
"""

import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import MetaTrader5 as mt5
import pandas as pd

from mt5_connection import MT5Connection
from technical_analysis import TechnicalAnalysis, SignalGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self):
        """Initialize the trading bot"""
        logger.info("Initializing XAU/USD Trading Bot with MT5 and Technical Analysis...")
        self.mt5 = None
        self.is_running = False
        self.symbol = 'XAUUSD'
        self.timeframe = mt5.TIMEFRAME_H1
        self.last_signal = None
        self.trade_count = 0
        
    def connect(self) -> bool:
        """Connect to MT5"""
        try:
            self.mt5 = MT5Connection()
            if not self.mt5.connect():
                logger.error("Failed to connect to MT5")
                return False
            
            # Get and display account info
            account_info = self.mt5.get_account_info()
            if account_info:
                logger.info(f"Account: {account_info['name']}")
                logger.info(f"Balance: {account_info['balance']} {account_info['currency']}")
                logger.info(f"Free Margin: {account_info['free_margin']}")
            
            # Get and display symbol info
            symbol_info = self.mt5.get_symbol_info(self.symbol)
            if symbol_info:
                logger.info(f"Symbol: {symbol_info['symbol']}")
                logger.info(f"Bid: {symbol_info['bid']}, Ask: {symbol_info['ask']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def fetch_market_data(self, bars: int = 100) -> pd.DataFrame:
        """Fetch current market data"""
        try:
            logger.debug("Fetching market data...")
            
            # Get current price
            bid, ask = self.mt5.get_current_price(self.symbol)
            logger.debug(f"{self.symbol} - Bid: {bid}, Ask: {ask}")
            
            # Fetch recent bars
            df = self.mt5.fetch_rates(self.symbol, self.timeframe, bars=bars)
            if df is None:
                logger.warning("Failed to fetch rates")
                return None
            
            logger.debug(f"Fetched {len(df)} bars")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return None
    
    def analyze_signals(self, df: pd.DataFrame) -> dict:
        """Analyze technical indicators and generate signals"""
        try:
            if df is None or df.empty:
                logger.warning("No data available for analysis")
                return None
            
            logger.debug("Analyzing technical signals...")
            
            # Calculate all technical indicators
            df = TechnicalAnalysis.calculate_all_indicators(df)
            
            # Log current indicator values
            last_row = df.iloc[-1]
            logger.debug(f"Close: {last_row['close']:.2f}")
            logger.debug(f"RSI: {last_row['rsi']:.2f}")
            logger.debug(f"SMA9: {last_row['sma_9']:.2f}, SMA21: {last_row['sma_21']:.2f}")
            logger.debug(f"BB Upper: {last_row['upper']:.2f}, Middle: {last_row['middle']:.2f}, Lower: {last_row['lower']:.2f}")
            
            if pd.notna(last_row['%K']):
                logger.debug(f"Stochastic %K: {last_row['%K']:.2f}, %D: {last_row['%D']:.2f}")
            
            logger.debug(f"ATR: {last_row['atr']:.2f}")
            
            # Generate combined signal
            signal = SignalGenerator.combined_signal(df)
            
            # Fallback to individual signals if no combined signal
            if signal is None:
                signal = SignalGenerator.rsi_signal(df)
                if signal is None:
                    signal = SignalGenerator.bollinger_bands_signal(df)
                if signal is None:
                    signal = SignalGenerator.stochastic_signal(df)
                if signal is None:
                    signal = SignalGenerator.alligator_signal(df)
            
            if signal:
                logger.info(f"Signal Generated: {signal}")
                
                # Add stop loss and take profit based on ATR
                if 'entry' not in signal:
                    signal['entry'] = last_row['close']
                
                sl, tp = SignalGenerator.atr_based_stops(df, signal['entry'], atr_multiplier=2.0)
                if sl and tp:
                    signal['stop_loss'] = sl
                    signal['take_profit'] = tp
                    logger.info(f"SL: {sl:.2f}, TP: {tp:.2f}")
            else:
                logger.debug("No clear signal at this moment")
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to analyze signals: {e}")
            return None
    
    def execute_trade(self, signal: dict) -> bool:
        """Execute trade based on signal"""
        try:
            indicator_name = signal.get('indicators', [signal.get('indicator', 'Unknown')])[0] if isinstance(signal.get('indicators'), list) else signal.get('indicator', 'Unknown')
            
            if signal['type'] == 'BUY':
                result = self.mt5.send_order(
                    symbol=self.symbol,
                    order_type=mt5.ORDER_TYPE_BUY,
                    volume=0.1,
                    stop_loss=signal.get('stop_loss'),
                    take_profit=signal.get('take_profit'),
                    comment=f"Bot BUY - {indicator_name}"
                )
            elif signal['type'] == 'SELL':
                result = self.mt5.send_order(
                    symbol=self.symbol,
                    order_type=mt5.ORDER_TYPE_SELL,
                    volume=0.1,
                    stop_loss=signal.get('stop_loss'),
                    take_profit=signal.get('take_profit'),
                    comment=f"Bot SELL - {indicator_name}"
                )
            else:
                return False
            
            if result:
                self.trade_count += 1
                logger.info(f"Trade #{self.trade_count} executed: {result}")
                self.last_signal = signal
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return False
    
    def monitor_positions(self) -> None:
        """Monitor open positions"""
        try:
            positions_df = self.mt5.get_positions(self.symbol)
            if positions_df is not None and len(positions_df) > 0:
                logger.info(f"Open Positions: {len(positions_df)}")
                for _, pos in positions_df.iterrows():
                    logger.info(
                        f"Ticket: {pos['ticket']}, {pos['type']}, "
                        f"Volume: {pos['volume']}, Profit: {pos['profit']:.2f} USD "
                        f"({pos['profit_pct']:.2f}%)"
                    )
            else:
                logger.debug("No open positions")
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def print_indicators_report(self, df: pd.DataFrame) -> None:
        """Print detailed indicators report"""
        if df is None or df.empty:
            return
        
        last_row = df.iloc[-1]
        
        logger.info("=" * 60)
        logger.info("TECHNICAL ANALYSIS REPORT")
        logger.info("=" * 60)
        
        # Price Action
        logger.info(f"\n📊 PRICE ACTION:")
        logger.info(f"  Close: {last_row['close']:.4f}")
        logger.info(f"  High: {last_row['high']:.4f} | Low: {last_row['low']:.4f}")
        
        # Moving Averages
        logger.info(f"\n📈 MOVING AVERAGES:")
        logger.info(f"  SMA(9): {last_row['sma_9']:.4f}")
        logger.info(f"  SMA(21): {last_row['sma_21']:.4f}")
        logger.info(f"  EMA(12): {last_row['ema_12']:.4f}")
        
        # Bollinger Bands
        logger.info(f"\n📦 BOLLINGER BANDS:")
        logger.info(f"  Upper: {last_row['upper']:.4f}")
        logger.info(f"  Middle: {last_row['middle']:.4f}")
        logger.info(f"  Lower: {last_row['lower']:.4f}")
        logger.info(f"  BB Width: {last_row['bb_width']:.4f}")
        logger.info(f"  BB Position: {last_row['bb_position']:.2f}%")
        
        # RSI
        logger.info(f"\n⚡ RSI (14):")
        logger.info(f"  Value: {last_row['rsi']:.2f}")
        if last_row['rsi'] < 30:
            logger.info(f"  Status: OVERSOLD ⬇️")
        elif last_row['rsi'] > 70:
            logger.info(f"  Status: OVERBOUGHT ⬆️")
        else:
            logger.info(f"  Status: NEUTRAL")
        
        # Stochastic
        if pd.notna(last_row['%K']):
            logger.info(f"\n🔄 STOCHASTIC:")
            logger.info(f"  %K: {last_row['%K']:.2f}")
            logger.info(f"  %D: {last_row['%D']:.2f}")
        
        # ATR
        logger.info(f"\n📏 ATR (14):")
        logger.info(f"  Value: {last_row['atr']:.4f}")
        
        # MACD
        if pd.notna(last_row['macd']):
            logger.info(f"\n📊 MACD:")
            logger.info(f"  MACD: {last_row['macd']:.4f}")
            logger.info(f"  Signal: {last_row['signal']:.4f}")
            logger.info(f"  Histogram: {last_row['histogram']:.4f}")
        
        # Alligator
        if pd.notna(last_row['jaw']):
            logger.info(f"\n🐊 ALLIGATOR:")
            logger.info(f"  Jaw: {last_row['jaw']:.4f}")
            logger.info(f"  Teeth: {last_row['teeth']:.4f}")
            logger.info(f"  Lips: {last_row['lips']:.4f}")
        
        logger.info("=" * 60 + "\n")
    
    def run(self):
        """Main trading loop"""
        try:
            self.is_running = True
            logger.info("Starting trading bot main loop...")
            logger.info(f"Timeframe: {self.timeframe}, Symbol: {self.symbol}")
            
            while self.is_running:
                try:
                    # Fetch market data
                    df = self.fetch_market_data(bars=100)
                    if df is None:
                        logger.warning("Failed to fetch market data, retrying...")
                        time.sleep(30)
                        continue
                    
                    # Print indicators report
                    self.print_indicators_report(df)
                    
                    # Monitor positions
                    self.monitor_positions()
                    
                    # Analyze signals
                    signal = self.analyze_signals(df)
                    
                    # Execute trade if signal exists (and no recent signal of same type)
                    if signal and (self.last_signal is None or self.last_signal['type'] != signal['type']):
                        indicators = signal.get('indicators', [signal.get('indicator', 'Unknown')])
                        logger.info(f"Executing trade based on {indicators}")
                        self.execute_trade(signal)
                    
                    # Wait before next iteration (adjust based on timeframe)
                    logger.info("Waiting 60 seconds for next analysis...")
                    time.sleep(60)
                    
                except KeyboardInterrupt:
                    logger.info("Trading bot stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}")
                    time.sleep(30)
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        if self.mt5:
            self.mt5.disconnect()
        logger.info(f"Trading bot stopped. Total trades executed: {self.trade_count}")


def main():
    """Main entry point"""
    try:
        logger.info("\n" + "=" * 70)
        logger.info("XAU/USD TRADING BOT - LIVE TRADING MODE")
        logger.info("=" * 70 + "\n")
        
        bot = TradingBot()
        if not bot.connect():
            logger.error("Failed to connect to MT5. Check your credentials and try again.")
            logger.error("Instructions:")
            logger.error("1. Copy .env.mt5.example to .env")
            logger.error("2. Fill in your MT5 credentials")
            logger.error("3. Ensure MetaTrader 5 is running")
            exit(1)
        
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)


if __name__ == '__main__':
    main()
