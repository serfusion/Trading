//+------------------------------------------------------------------+
//| Configuration Header File                                         |
//| All settings and parameters for the Gold Trading EA               |
//+------------------------------------------------------------------+

#ifndef __CONFIG_MQH__
#define __CONFIG_MQH__

// ---- EA Parameters ----
input double Lot = 0.1;                    // Lot size
input int StopLoss = 100;                  // Stop Loss in pips
input int TakeProfit = 200;                // Take Profit in pips
input int Deviation = 10;                  // Deviation in pips
input int MAGIC_NUMBER = 123456;           // Magic number for trades

// ---- TimeFrame Settings ----
input ENUM_TIMEFRAMES TimeFrame = PERIOD_H1; // Trading timeframe (H1 recommended for gold)

// ---- Technical Indicators ----
input int RSI_Period = 14;                 // RSI period
input int MACD_Fast = 12;                  // MACD fast EMA
input int MACD_Slow = 26;                  // MACD slow EMA
input int MACD_Signal = 9;                 // MACD signal line

// ---- Risk Management ----
input double AccountRisk = 2.0;            // Risk per trade (% of account)
input double MaxDrawdown = 10.0;           // Maximum drawdown allowed (%)
input double MaxLossPerTrade = 5.0;        // Max loss per trade (% of account)

// ---- Trailing Stop ----
input bool EnableTrailingStop = true;      // Enable trailing stop
input int TrailingStopDistance = 50;       // Trailing stop distance in pips

// ---- Logging Levels ----
#define LOG_LEVEL_ERRORS 1
#define LOG_LEVEL_WARNINGS 2
#define LOG_LEVEL_INFO 3

#endif
