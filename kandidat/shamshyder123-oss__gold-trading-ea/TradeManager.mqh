//+------------------------------------------------------------------+
//| Trade Manager Class                                               |
//| Handles trade execution and position management                  |
//+------------------------------------------------------------------+

#ifndef __TRADE_MANAGER_MQH__
#define __TRADE_MANAGER_MQH__

#include <Trade\Trade.mqh>

class CTradeManager : public CTrade
{
private:
    int m_lastOrderTicket;
    datetime m_lastOrderTime;
    
public:
    CTradeManager();
    ~CTradeManager();
    
    bool OpenBuyOrder(string symbol, double volume, double price, double sl, double tp, string comment);
    bool OpenSellOrder(string symbol, double volume, double price, double sl, double tp, string comment);
    bool ClosePosition(ulong ticket);
    bool ModifyPosition(ulong ticket, double newSL, double newTP);
    
    int GetLastOrderTicket() { return m_lastOrderTicket; }
    datetime GetLastOrderTime() { return m_lastOrderTime; }
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CTradeManager::CTradeManager()
{
    m_lastOrderTicket = -1;
    m_lastOrderTime = 0;
}

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CTradeManager::~CTradeManager()
{
}

//+------------------------------------------------------------------+
//| Open Buy Order                                                    |
//+------------------------------------------------------------------+
bool CTradeManager::OpenBuyOrder(string symbol, double volume, double price, 
                                  double sl, double tp, string comment)
{
    if (Buy(volume, symbol, price, sl, tp, comment)) {
        m_lastOrderTicket = (int)ResultOrder();
        m_lastOrderTime = TimeCurrent();
        Print("Buy order opened successfully. Ticket: ", m_lastOrderTicket);
        return true;
    }
    else {
        Print("Buy order failed. Error: ", GetLastError());
        return false;
    }
}

//+------------------------------------------------------------------+
//| Open Sell Order                                                   |
//+------------------------------------------------------------------+
bool CTradeManager::OpenSellOrder(string symbol, double volume, double price,
                                   double sl, double tp, string comment)
{
    if (Sell(volume, symbol, price, sl, tp, comment)) {
        m_lastOrderTicket = (int)ResultOrder();
        m_lastOrderTime = TimeCurrent();
        Print("Sell order opened successfully. Ticket: ", m_lastOrderTicket);
        return true;
    }
    else {
        Print("Sell order failed. Error: ", GetLastError());
        return false;
    }
}

//+------------------------------------------------------------------+
//| Close Position                                                    |
//+------------------------------------------------------------------+
bool CTradeManager::ClosePosition(ulong ticket)
{
    if (PositionClose(ticket)) {
        Print("Position closed successfully. Ticket: ", ticket);
        return true;
    }
    else {
        Print("Failed to close position. Error: ", GetLastError());
        return false;
    }
}

//+------------------------------------------------------------------+
//| Modify Position (SL/TP)                                           |
//+------------------------------------------------------------------+
bool CTradeManager::ModifyPosition(ulong ticket, double newSL, double newTP)
{
    if (PositionModify(ticket, newSL, newTP)) {
        Print("Position modified successfully. New SL: ", newSL, " New TP: ", newTP);
        return true;
    }
    else {
        Print("Failed to modify position. Error: ", GetLastError());
        return false;
    }
}

#endif
