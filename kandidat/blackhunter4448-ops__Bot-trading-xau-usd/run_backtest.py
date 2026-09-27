#!/usr/bin/env python3
"""
Backtesting Script for XAU/USD Trading Bot
Run this to test your trading strategies on historical data
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from backtest import Backtest, BacktestOptimizer, save_backtest_results

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_sample_data() -> pd.DataFrame:
    """
    Load sample data (you should replace with your actual data source)
    For demonstration, we'll create synthetic data
    """
    logger.info("Loading historical data...")
    
    # Create sample data - in production, load from MT5, CSV, or API
    dates = pd.date_range(start='2024-01-01', end='2024-06-02', freq='H')
    
    # Generate realistic OHLC data
    import numpy as np
    np.random.seed(42)
    
    prices = [2000]  # Starting price for gold
    for _ in range(len(dates) - 1):
        # Random walk with upward bias
        change = np.random.normal(0.01, 2)
        prices.append(prices[-1] + change)
    
    prices = np.array(prices)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices + np.random.uniform(-1, 1, len(prices)),
        'high': prices + np.random.uniform(0, 3, len(prices)),
        'low': prices - np.random.uniform(0, 3, len(prices)),
        'close': prices,
        'tick_volume': np.random.randint(100, 1000, len(prices))
    })
    
    logger.info(f"Loaded {len(df)} bars of data")
    return df


def run_basic_backtest():
    """Run a basic backtest with default parameters"""
    logger.info("=" * 70)
    logger.info("RUNNING BASIC BACKTEST")
    logger.info("=" * 70 + "\n")
    
    # Load data
    df = load_sample_data()
    
    # Run backtest
    backtest = Backtest(
        initial_balance=10000,
        lot_size=0.1,
        slippage=0.5,
        commission=0.0005
    )
    
    results = backtest.run_backtest(df, use_combined_signals=True)
    
    # Print report
    results.print_report()
    
    # Save results
    save_backtest_results(results, 'backtest_results_basic.json')
    
    return results


def run_individual_signal_backtest():
    """Run backtest with individual signals (no multi-indicator confirmation)"""
    logger.info("=" * 70)
    logger.info("RUNNING INDIVIDUAL SIGNAL BACKTEST (RSI-ONLY)")
    logger.info("=" * 70 + "\n")
    
    # Load data
    df = load_sample_data()
    
    # Run backtest
    backtest = Backtest(
        initial_balance=10000,
        lot_size=0.1,
        slippage=0.5,
        commission=0.0005
    )
    
    results = backtest.run_backtest(df, use_combined_signals=False)
    
    # Print report
    results.print_report()
    
    # Save results
    save_backtest_results(results, 'backtest_results_individual.json')
    
    return results


def run_parameter_optimization():
    """Run parameter optimization for RSI levels"""
    logger.info("=" * 70)
    logger.info("RUNNING PARAMETER OPTIMIZATION (RSI LEVELS)")
    logger.info("=" * 70 + "\n")
    
    # Load data
    df = load_sample_data()
    
    logger.info("Testing different RSI oversold/overbought levels...")
    results = BacktestOptimizer.optimize_rsi_levels(
        df,
        initial_balance=10000,
        oversold_range=(20, 40),
        overbought_range=(60, 80)
    )
    
    # Print top results
    logger.info("\nTOP 5 PARAMETER COMBINATIONS:")
    logger.info("-" * 70)
    
    for i, result in enumerate(results[:5], 1):
        logger.info(f"\n{i}. Oversold: {result['oversold']}, Overbought: {result['overbought']}")
        logger.info(f"   Return: {result['total_return']:.2f}%")
        logger.info(f"   Win Rate: {result['win_rate']:.2f}%")
        logger.info(f"   Sharpe Ratio: {result['sharpe_ratio']:.4f}")
        logger.info(f"   Profit Factor: {result['profit_factor']:.2f}")
        logger.info(f"   Max Drawdown: {result['max_drawdown']:.2f}%")
        logger.info(f"   Total Trades: {result['total_trades']}")
    
    logger.info("\n" + "=" * 70)
    logger.info("Full optimization results saved to 'optimization_results.json'\n")
    
    # Save all results
    import json
    with open('optimization_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


def compare_strategies():
    """Compare multiple trading strategies"""
    logger.info("=" * 70)
    logger.info("COMPARING TRADING STRATEGIES")
    logger.info("=" * 70 + "\n")
    
    df = load_sample_data()
    
    strategies = [
        ("Combined Signals (2+ confirmations)", True),
        ("Individual Signals (RSI)", False)
    ]
    
    comparison_results = []
    
    for strategy_name, use_combined in strategies:
        logger.info(f"\nTesting: {strategy_name}")
        logger.info("-" * 70)
        
        backtest = Backtest(initial_balance=10000, lot_size=0.1)
        results = backtest.run_backtest(df, use_combined_signals=use_combined)
        
        comparison_results.append({
            'strategy': strategy_name,
            'metrics': results.to_dict()
        })
        
        logger.info(f"Return: {results.total_return_pct:.2f}%")
        logger.info(f"Win Rate: {results.win_rate:.2f}%")
        logger.info(f"Total Trades: {results.total_trades}")
        logger.info(f"Sharpe Ratio: {results.sharpe_ratio:.4f}")
    
    # Save comparison
    import json
    with open('strategy_comparison.json', 'w') as f:
        json.dump(comparison_results, f, indent=2)
    
    logger.info("\n" + "=" * 70)
    logger.info("Comparison results saved to 'strategy_comparison.json'\n")
    
    return comparison_results


def main():
    """Main backtesting function"""
    logger.info("\n" + "=" * 70)
    logger.info("XAU/USD TRADING BOT - BACKTESTING MODULE")
    logger.info("=" * 70 + "\n")
    
    # Run tests
    print("\nSelect backtest to run:")
    print("1. Basic Backtest (Combined Signals)")
    print("2. Individual Signal Backtest")
    print("3. Parameter Optimization")
    print("4. Strategy Comparison")
    print("5. Run All\n")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == '1':
        run_basic_backtest()
    elif choice == '2':
        run_individual_signal_backtest()
    elif choice == '3':
        run_parameter_optimization()
    elif choice == '4':
        compare_strategies()
    elif choice == '5':
        run_basic_backtest()
        run_individual_signal_backtest()
        run_parameter_optimization()
        compare_strategies()
    else:
        logger.error("Invalid choice!")
        return
    
    logger.info("\n" + "=" * 70)
    logger.info("BACKTESTING COMPLETE")
    logger.info("=" * 70 + "\n")


if __name__ == '__main__':
    main()
