# 🟡 XAU/USD Price Prediction & Trading Signal Analysis

A 14-day data science project exploring the use of machine learning and technical indicators to analyze, predict, and simulate trading strategies for gold (XAU/USD) prices using GLD ETF data.

---

## 📌 Project Overview

This project focuses on applying basic **data analysis** and **machine learning** techniques to the gold market using the XAU/USD pair (proxied by GLD ETF). It simulates daily predictions and evaluates a simple trading strategy based on technical signals.

---

## 🎯 Objectives

- Visualize gold price trends using technical indicators (MA, RSI, MACD)
- Predict daily closing prices using regression models
- Predict price direction (up/down) using classification models
- Evaluate a rule-based trading strategy based on model output
- Optional bonus: Visualize results via Streamlit dashboard (if time permits)

---

## 📊 Data Source

- **Asset:** SPDR Gold Shares (GLD ETF)  
- **Date Range:** 2023 onward  
- **Source:** Manually downloaded from Yahoo Finance  
- **Columns Used:** Date, Open, High, Low, Close, Volume

---

## 🧰 Tools & Technologies

| Category | Tools |
|---------|-------|
| Language | Python |
| IDE      | Jupyter Notebook (Anaconda), VSCode |
| Data     | Pandas, Numpy |
| Viz      | Matplotlib, Seaborn, mplfinance |
| ML       | Scikit-learn |

---

## 📈 Features Extracted

- **Technical Indicators:**
  - MA5, MA10, MA20
  - RSI
  - MACD & Signal Line
- **Returns & Volatility**
- **Target Labels:**
  - Close(t+1)
  - Direction (Up/Down)

---

## 🤖 Modeling Summary

| Model Type | Algorithm | Metrics |
|------------|-----------|---------|
| Regression | Random Forest Regressor | MSE: ~5.57 |
| Classification | Random Forest Classifier | Accuracy: ~43% |

- **Note:** Class imbalance handled via manual oversampling.

---

## 💡 Trading Strategy Simulation

- Buy if signal = BUY (model predicts price will go up)
- Sell if signal = SELL
- Initial capital: $10,000
- No position stacking, no fees

### 🧾 Result:
- Final Value: ~$11,258.26
- Profit: ~$1,258.26
- Total Trades: 121 kali

## 📬 Contact / Portfolio

Feel free to connect or view more projects through my social platforms:

- 🐙 [GitHub](https://github.com/cacastudymarket)
- 📸 [Instagram](https://instagram.com/cahyaratry__)
- 💼 [LinkedIn](https://linkedin.com/in/cahyaratrilukitaputri)

