# XAUUSD Backtesting Python Notebook

A Python notebook for backtesting a gold (XAUUSD) trading strategy, inspired by an Instagram post and collaboratively developed by:
- [Shivkeerth Laj](https://www.linkedin.com/in/shivkeerth-laj-ecba-6567b41b6)
- [Sritej Koduri](https://www.linkedin.com/in/sritej-koduri-895467283)
- [Muhammad Babar Khan](https://www.linkedin.com/in/muhammad-babar-khan)

---

## Project Overview

This repo contains code for backtesting a rules-based strategy on XAUUSD (spot gold) using 5-minute data exported from MetaTrader 5 and processed in Python with pandas and mplfinance. The notebook is designed for traders and data analysts curious about algorithmic strategy evaluation, with exportable results and full trade logs for further study.

---

## Motivation

The trading strategy originated from a short Instagram clip and was selected for its mechanical entry/exit logic and clear pip-based risk/reward calculations. This project aims to objectively evaluate its performance on recent data and provide detailed transparency behind actual trade results, win/loss rates, equity curves, and entry/exit placement.

---

## Features

- Automated Data Collection: Downloads up to 50,000 bars of XAUUSD 5-minute historical data from MetaTrader 5.
- Customizable Risk Settings: Parameterized starting balance, risk per trade in dollars, and lot sizing.
- Rules-Based Trade Execution: Strategy logic based on candle patterns for bullish/bearish setups with dynamic stop loss and take-profit calculation.
- Detailed Trade Logging: Full summary of each trade’s entry, SL, TP, result, PnL in dollars, and account balance tracked for every bar.
- Excel Export: Automated export of trade logs and summary metrics to `.xlsx` for further sharing and review.
- Visualization: Plots entry/exit points on the full gold chart using mplfinance, with clear markers for buys/sells.

---

## Usage

### Prerequisites

- Python 3.7+
- MetaTrader5, pandas, matplotlib, mplfinance, xlsxwriter libraries

### Steps

```bash
git clone https://github.com/your-username/XAUUSD-BACKTEST-V2
cd XAUUSD-BACKTEST-V2
```
2. Launch and run `XAUUSD-BACKTEST-V2.ipynb` in Jupyter Notebook or VSCode.
3. Customize risk parameters, balance, or trade logic as needed.
4. View logs and visualizations. Check the generated `.xlsx` file for detailed results.
5. Replace sample LinkedIn URLs with real profile links for contributors.

---

## Strategy Description

- Detects 4-candle bullish or bearish runs for potential entries.
- Calculates dynamic entry, stop, and take-profit based on last candle group.
- Sizes positions to fixed dollar risk per trade.
- Tracks each outcome (win/lose), updates P&L, and saves everything for review.
- Backtests on up to 50,000 bars from Feb 2025 to Oct 2025, offering a substantive test window for recent market conditions.

---

## Results and Output

After running, the notebook outputs:
- Starting and final balance
- Total trades taken
- Win/loss counts and win %
- Cumulative profit/loss
- All trade logs and summary exported to `.xlsx`
- Chart with marked entry/exit points

---

## Collaboration

This project was built by Shivkeerth Laj, Sritej Koduri, and Muhammad Babar Khan.
Open to feedback, forks, and further strategy ideas via GitHub Issues or Pull Requests.

---

## License

Open-source under MIT License—use, modify, or share as you wish with attribution.

---

## Contact

For collaboration or questions, reach out via LinkedIn or open a GitHub Issue.

---
