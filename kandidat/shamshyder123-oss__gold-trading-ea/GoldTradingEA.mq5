//+------------------------------------------------------------------+
//| Gold Trading Expert Advisor (XAU/USD)                            |
//| Advanced automated trading system for gold forex pairs             |
//+------------------------------------------------------------------+
#property copyright "Gold Trading EA"
#property link      "https://github.com/shamshyder123-oss/gold-trading-ea"
#property version   "1.00"
#property strict

// Include configuration and utility files
#include "Config.mqh"
#include "TradeManager.mqh"
#include "TechnicalAnalysis.mqh"
#include "RiskManager.mqh"

// Global variables
ctrade Trade;
CRiskManager RiskManager;
CTechnicalAnalysis TechAnalysis;

int OnInit()
{
    // Validate settings
    if (Lot <= 0) {
        Print("Error: Invalid lot size");
        return INIT_PARAMETERS_INCORRECT;
    }
    
    if (TakeProfit <= 0 || StopLoss <= 0) {
        Print("Error: Invalid TP or SL values");
        return INIT_PARAMETERS_INCORRECT;
    }
    
    // Initialize trade object
    Trade.SetExpertMagicNumber(MAGIC_NUMBER);
    Trade.SetDeviationInPoints(Deviation);
    Trade.LogLevel(LOG_LEVEL_ERRORS);
    
    // Initialize risk manager
    RiskManager.SetAccountRisk(AccountRisk);
    RiskManager.SetMaxDrawdown(MaxDrawdown);
    
    Print("Gold Trading EA initialized successfully");
    Print("Magic Number: ", MAGIC_NUMBER);
    Print("Lot Size: ", Lot);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("Gold Trading EA deinitialized. Reason: ", reason);
}

void OnTick()
{
    // Check if market is open
    if (!IsMarketOpen()) {
        return;
    }
    
    // Get current market data
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    
    // Calculate technical indicators
    double rsi = TechAnalysis.CalculateRSI(_Symbol, RSI_Period);
    double macd = TechAnalysis.CalculateMACD(_Symbol);
    double sma20 = iMA(_Symbol, TimeFrame, 20, 0, MODE_SMA, PRICE_CLOSE);
    double sma50 = iMA(_Symbol, TimeFrame, 50, 0, MODE_SMA, PRICE_CLOSE);
    
    // Get current price
    double currentPrice = iClose(_Symbol, TimeFrame, 0);
    
    // Check for trading signals
    if (CheckBuySignal(rsi, macd, sma20, sma50, currentPrice)) {
        if (!HasOpenPosition(ORDER_TYPE_BUY)) {
            ExecuteBuyTrade(ask);
        }
    }
    else if (CheckSellSignal(rsi, macd, sma20, sma50, currentPrice)) {
        if (!HasOpenPosition(ORDER_TYPE_SELL)) {
            ExecuteSellTrade(bid);
        }
    }
    
    // Manage open positions
    ManageOpenPositions();
}

// ---- Trading Signal Functions ----
bool CheckBuySignal(double rsi, double macd, double sma20, double sma50, double price)
{
    // Buy conditions:
    // 1. RSI below oversold (30) and moving above
    // 2. SMA20 above SMA50 (uptrend)
    // 3. MACD positive and above signal line
    // 4. Price above SMA20
    
    bool rsiOversold = (rsi > 25 && rsi < 35);
    bool trendUp = (sma20 > sma50);
    bool macdPositive = (macd > 0);
    bool priceAboveSMA = (price > sma20);
    
    return (rsiOversold && trendUp && macdPositive && priceAboveSMA);
}

bool CheckSellSignal(double rsi, double macd, double sma20, double sma50, double price)
{
    // Sell conditions:
    // 1. RSI above overbought (70) and moving below
    // 2. SMA20 below SMA50 (downtrend)
    // 3. MACD negative and below signal line
    // 4. Price below SMA20
    
    bool rsiOverbought = (rsi > 65 && rsi < 75);
    bool trendDown = (sma20 < sma50);
    bool macdNegative = (macd < 0);
    bool priceBelowSMA = (price < sma20);
    
    return (rsiOverbought && trendDown && macdNegative && priceBelowSMA);
}

// ---- Trade Execution ----
void ExecuteBuyTrade(double ask)
{
    double stopLoss = ask - (StopLoss * _Point);
    double takeProfit = ask + (TakeProfit * _Point);
    
    if (RiskManager.ValidateTrade(Lot, stopLoss, ask)) {
        Trade.Buy(Lot, _Symbol, ask, stopLoss, takeProfit, "Gold EA Buy");
        Print("BUY Order Placed at ", ask);
    }
}

void ExecuteSellTrade(double bid)
{
    double stopLoss = bid + (StopLoss * _Point);
    double takeProfit = bid - (TakeProfit * _Point);
    
    if (RiskManager.ValidateTrade(Lot, stopLoss, bid)) {
        Trade.Sell(Lot, _Symbol, bid, stopLoss, takeProfit, "Gold EA Sell");
        Print("SELL Order Placed at ", bid);
    }
}

// ---- Position Management ----
bool HasOpenPosition(ENUM_ORDER_TYPE orderType)
{
    for (int i = PositionsTotal() - 1; i >= 0; i--) {
        if (PositionGetSymbol(i) == _Symbol) {
            if (PositionGetInteger(POSITION_TYPE) == orderType) {
                return true;
            }
        }
    }
    return false;
}

void ManageOpenPositions()
{
    for (int i = PositionsTotal() - 1; i >= 0; i--) {
        if (PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER) {
            double profit = PositionGetDouble(POSITION_PROFIT);
            
            // Trailing stop logic
            if (EnableTrailingStop && profit > 0) {
                UpdateTrailingStop();
            }
            
            // Close if max loss reached
            if (profit < -MaxLossPerTrade * AccountBalance() / 100) {
                Trade.PositionClose(PositionGetInteger(POSITION_TICKET));
                Print("Position closed due to max loss limit");
            }
        }
    }
}

void UpdateTrailingStop()
{
    for (int i = PositionsTotal() - 1; i >= 0; i--) {
        if (PositionGetSymbol(i) == _Symbol) {
            double currentSL = PositionGetDouble(POSITION_SL);
            double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            
            if (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) {
                double newSL = currentPrice - (TrailingStopDistance * _Point);
                if (newSL > currentSL) {
                    Trade.PositionModify(PositionGetInteger(POSITION_TICKET), newSL, PositionGetDouble(POSITION_TP));
                }
            }
            else if (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL) {
                double newSL = currentPrice + (TrailingStopDistance * _Point);
                if (newSL < currentSL) {
                    Trade.PositionModify(PositionGetInteger(POSITION_TICKET), newSL, PositionGetDouble(POSITION_TP));
                }
            }
        }
    }
}

// ---- Market Check ----
bool IsMarketOpen()
{
    MqlDateTime time;
    TimeToStruct(TimeCurrent(), time);
    
    // Gold (XAU/USD) trades 24/5
    // Only avoid Friday close and Sunday open
    if (time.day_of_week == 5 && time.hour >= 22) return false; // Friday night
    if (time.day_of_week == 0 && time.hour < 17) return false;  // Sunday before open
    
    return true;
}

double AccountBalance()
{
    return AccountInfoDouble(ACCOUNT_BALANCE);
}
