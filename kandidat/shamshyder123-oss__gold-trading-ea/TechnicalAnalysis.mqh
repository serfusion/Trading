//+------------------------------------------------------------------+
//| Technical Analysis Class                                          |
//| Calculates technical indicators for trading signals               |
//+------------------------------------------------------------------+

#ifndef __TECHNICAL_ANALYSIS_MQH__
#define __TECHNICAL_ANALYSIS_MQH__

class CTechnicalAnalysis
{
private:
    int m_rsiHandle;
    int m_macdHandle;
    
public:
    CTechnicalAnalysis();
    ~CTechnicalAnalysis();
    
    double CalculateRSI(string symbol, int period, int shift = 0);
    double CalculateMACD(string symbol, int shift = 0);
    double CalculateSMA(string symbol, int period, int shift = 0);
    double CalculateATR(string symbol, int period, int shift = 0);
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CTechnicalAnalysis::CTechnicalAnalysis()
{
    m_rsiHandle = -1;
    m_macdHandle = -1;
}

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CTechnicalAnalysis::~CTechnicalAnalysis()
{
    if (m_rsiHandle != -1) {
        IndicatorRelease(m_rsiHandle);
    }
    if (m_macdHandle != -1) {
        IndicatorRelease(m_macdHandle);
    }
}

//+------------------------------------------------------------------+
//| Calculate RSI (Relative Strength Index)                           |
//+------------------------------------------------------------------+
double CTechnicalAnalysis::CalculateRSI(string symbol, int period, int shift)
{
    double rsiBuffer[1];
    int handle = iRSI(symbol, PERIOD_CURRENT, period, PRICE_CLOSE);
    
    if (handle == INVALID_HANDLE) {
        Print("Error creating RSI handle");
        return -1;
    }
    
    if (CopyBuffer(handle, 0, shift, 1, rsiBuffer) <= 0) {
        Print("Error copying RSI buffer");
        return -1;
    }
    
    return rsiBuffer[0];
}

//+------------------------------------------------------------------+
//| Calculate MACD (Moving Average Convergence Divergence)            |
//+------------------------------------------------------------------+
double CTechnicalAnalysis::CalculateMACD(string symbol, int shift)
{
    double macdBuffer[1];
    int handle = iMACD(symbol, PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);
    
    if (handle == INVALID_HANDLE) {
        Print("Error creating MACD handle");
        return -1;
    }
    
    if (CopyBuffer(handle, 0, shift, 1, macdBuffer) <= 0) {
        Print("Error copying MACD buffer");
        return -1;
    }
    
    return macdBuffer[0];
}

//+------------------------------------------------------------------+
//| Calculate SMA (Simple Moving Average)                             |
//+------------------------------------------------------------------+
double CTechnicalAnalysis::CalculateSMA(string symbol, int period, int shift)
{
    double smaBuffer[1];
    int handle = iMA(symbol, PERIOD_CURRENT, period, 0, MODE_SMA, PRICE_CLOSE);
    
    if (handle == INVALID_HANDLE) {
        Print("Error creating SMA handle");
        return -1;
    }
    
    if (CopyBuffer(handle, 0, shift, 1, smaBuffer) <= 0) {
        Print("Error copying SMA buffer");
        return -1;
    }
    
    return smaBuffer[0];
}

//+------------------------------------------------------------------+
//| Calculate ATR (Average True Range)                                |
//+------------------------------------------------------------------+
double CTechnicalAnalysis::CalculateATR(string symbol, int period, int shift)
{
    double atrBuffer[1];
    int handle = iATR(symbol, PERIOD_CURRENT, period);
    
    if (handle == INVALID_HANDLE) {
        Print("Error creating ATR handle");
        return -1;
    }
    
    if (CopyBuffer(handle, 0, shift, 1, atrBuffer) <= 0) {
        Print("Error copying ATR buffer");
        return -1;
    }
    
    return atrBuffer[0];
}

#endif
