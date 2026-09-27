//+------------------------------------------------------------------+
//| Risk Manager Class                                                |
//| Manages risk and position sizing                                 |
//+------------------------------------------------------------------+

#ifndef __RISK_MANAGER_MQH__
#define __RISK_MANAGER_MQH__

class CRiskManager
{
private:
    double m_accountRisk;           // Risk per trade (%)
    double m_maxDrawdown;           // Maximum drawdown (%)
    double m_initialBalance;        // Initial account balance
    double m_highestBalance;        // Highest balance reached
    
public:
    CRiskManager();
    ~CRiskManager();
    
    void SetAccountRisk(double risk) { m_accountRisk = risk; }
    void SetMaxDrawdown(double drawdown) { m_maxDrawdown = drawdown; }
    
    double CalculateLotSize(double stopLossPips, double accountBalance);
    bool ValidateTrade(double lotSize, double stopLoss, double entryPrice);
    bool CheckDrawdownLimit();
    double GetCurrentDrawdown();
    
private:
    double CalculateRiskAmount(double accountBalance);
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CRiskManager::CRiskManager()
{
    m_accountRisk = 2.0;
    m_maxDrawdown = 10.0;
    m_initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    m_highestBalance = m_initialBalance;
}

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CRiskManager::~CRiskManager()
{
}

//+------------------------------------------------------------------+
//| Calculate Lot Size Based on Risk                                  |
//+------------------------------------------------------------------+
double CRiskManager::CalculateLotSize(double stopLossPips, double accountBalance)
{
    double riskAmount = CalculateRiskAmount(accountBalance);
    double pipValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    
    if (stopLossPips <= 0 || pipValue <= 0) {
        Print("Error: Invalid stop loss or pip value");
        return 0.0;
    }
    
    double lotSize = riskAmount / (stopLossPips * pipValue);
    
    // Validate lot size
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
    
    if (lotSize < minLot) lotSize = minLot;
    if (lotSize > maxLot) lotSize = maxLot;
    
    // Round to lot step
    lotSize = MathRound(lotSize / lotStep) * lotStep;
    
    return lotSize;
}

//+------------------------------------------------------------------+
//| Calculate Risk Amount                                             |
//+------------------------------------------------------------------+
double CRiskManager::CalculateRiskAmount(double accountBalance)
{
    return accountBalance * (m_accountRisk / 100.0);
}

//+------------------------------------------------------------------+
//| Validate Trade                                                    |
//+------------------------------------------------------------------+
bool CRiskManager::ValidateTrade(double lotSize, double stopLoss, double entryPrice)
{
    // Check if lot size is valid
    if (lotSize <= 0) {
        Print("Error: Invalid lot size");
        return false;
    }
    
    // Check if we're within drawdown limit
    if (!CheckDrawdownLimit()) {
        Print("Trading halted: Drawdown limit reached");
        return false;
    }
    
    // Check if stop loss is valid
    if (stopLoss <= 0) {
        Print("Error: Invalid stop loss");
        return false;
    }
    
    // Calculate potential loss
    double pipDifference = MathAbs(entryPrice - stopLoss) / _Point;
    double potentialLoss = lotSize * pipDifference * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    
    if (potentialLoss > CalculateRiskAmount(accountBalance)) {
        Print("Error: Potential loss exceeds risk limit");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Check Drawdown Limit                                              |
//+------------------------------------------------------------------+
bool CRiskManager::CheckDrawdownLimit()
{
    double currentDrawdown = GetCurrentDrawdown();
    
    if (currentDrawdown >= m_maxDrawdown) {
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get Current Drawdown                                              |
//+------------------------------------------------------------------+
double CRiskManager::GetCurrentDrawdown()
{
    double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    
    if (currentBalance > m_highestBalance) {
        m_highestBalance = currentBalance;
    }
    
    double drawdown = ((m_highestBalance - currentBalance) / m_highestBalance) * 100.0;
    
    return drawdown;
}

#endif
