#property strict

class COrderEngine
{
private:
   string m_symbol;
   double m_lotSize;
   int    m_slPips;
   int    m_tpPips;
   int    m_breakevenTrigger;
   int    m_trailingStep;
   int    m_maxSpreadPips;
   string m_debugFolder;

   void WriteDebugLog(string msg)
   {
      if(m_debugFolder == "") return;
      string path = m_debugFolder + "\\ea_trace.log";
      int handle = FileOpen(path, FILE_WRITE | FILE_READ | FILE_TXT | FILE_COMMON);
      if(handle != INVALID_HANDLE)
      {
         FileSeek(handle, 0, SEEK_END);
         string line = "[" + TimeToString(TimeCurrent()) + "] [OE] " + msg + "\r\n";
         FileWriteString(handle, line);
         FileClose(handle);
      }
   }

public:
   COrderEngine()
   {
      m_symbol = "";
      m_lotSize = 0.01;
      m_slPips = 10;
      m_tpPips = 20;
      m_breakevenTrigger = 5;
      m_trailingStep = 2;
      m_maxSpreadPips = 3;
      m_debugFolder = "";
   }

   void SetSymbol(string symbol) { m_symbol = symbol; }
   void SetDebugFolder(string folder) { m_debugFolder = folder; }

   void Configure(double lotSize, int slPips, int tpPips)
   {
      m_lotSize = lotSize;
      m_slPips = slPips;
      m_tpPips = tpPips;
   }

   void ConfigureEx(double lotSize, int slPips, int tpPips, int breakevenTrigger, int trailingStep, int maxSpreadPips = 3)
   {
      m_lotSize = lotSize;
      m_slPips = slPips;
      m_tpPips = tpPips;
      m_breakevenTrigger = breakevenTrigger;
      m_trailingStep = trailingStep;
      m_maxSpreadPips = maxSpreadPips;
   }

   bool CheckSpread()
   {
      double spread = MarketInfo(m_symbol, MODE_SPREAD);
      double point = MarketInfo(m_symbol, MODE_POINT);
      double spreadPips = spread * point / (10 * point);
      if(spread > m_maxSpreadPips * 10)
      {
         WriteDebugLog("SPREAD_TOO_HIGH: spread=" + DoubleToString(spread, 1) + " max=" + IntegerToString(m_maxSpreadPips * 10));
         return false;
      }
      return true;
   }

   int Execute(string side)
   {
      if(m_symbol == "") { WriteDebugLog("FAIL: symbol_empty"); return -1; }
      if(!IsConnected()) { WriteDebugLog("FAIL: connection_lost (no server connection)"); return -1; }
      if(!IsTradeAllowed()) { WriteDebugLog("FAIL: trade_context_busy or trading disabled"); return -1; }
      if(!CheckSpread()) { WriteDebugLog("FAIL: spread_too_high"); return -1; }

      double point = MarketInfo(m_symbol, MODE_POINT);
      int digits = (int)MarketInfo(m_symbol, MODE_DIGITS);
      double spread = MarketInfo(m_symbol, MODE_SPREAD);
      int stopLevel = (int)MarketInfo(m_symbol, MODE_STOPLEVEL);
      int freezeLevel = (int)MarketInfo(m_symbol, MODE_FREEZELEVEL);
      double minLot = MarketInfo(m_symbol, MODE_MINLOT);
      double maxLot = MarketInfo(m_symbol, MODE_MAXLOT);
      double lotStep = MarketInfo(m_symbol, MODE_LOTSTEP);
      double bid = MarketInfo(m_symbol, MODE_BID);
      double ask = MarketInfo(m_symbol, MODE_ASK);

      double price = 0.0;
      int orderType = -1;
      color orderColor = clrNONE;

      if(side == "BUY") { price = ask; orderType = OP_BUY; orderColor = clrBlue; }
      else if(side == "SELL") { price = bid; orderType = OP_SELL; orderColor = clrRed; }
      else { WriteDebugLog("FAIL: invalid_side=" + side); return -1; }

      double slPrice = 0.0;
      double tpPrice = 0.0;
      if(m_slPips > 0)
      {
         if(orderType == OP_BUY) {
            slPrice = NormalizeDouble(price - m_slPips * point * 10, digits);
            tpPrice = NormalizeDouble(price + m_tpPips * point * 10, digits);
         } else {
            slPrice = NormalizeDouble(price + m_slPips * point * 10, digits);
            tpPrice = NormalizeDouble(price - m_tpPips * point * 10, digits);
         }
      }

      if(stopLevel > 0)
      {
         double minStopDist = stopLevel * point;
         if(orderType == OP_BUY && slPrice > 0) {
            if((price - slPrice) < minStopDist) slPrice = NormalizeDouble(price - minStopDist * 1.5, digits);
         } else if(orderType == OP_SELL && slPrice > 0) {
            if((slPrice - price) < minStopDist) slPrice = NormalizeDouble(price + minStopDist * 1.5, digits);
         }
      }

      double lot = NormalizeDouble(MathMax(minLot, MathMin(m_lotSize, maxLot)), 2);
      if(lotStep > 0) lot = MathRound(lot / lotStep) * lotStep;
      int slippage = 30;

      if(freezeLevel > 0)
      {
         double freezePrice = freezeLevel * point;
         if(MathAbs(price - bid) < freezePrice || MathAbs(price - ask) < freezePrice)
         {
            WriteDebugLog("FAIL: freeze_level");
            return -1;
         }
      }

      string debugInfo = "BEFORE_ORDER: side=" + side + " price=" + DoubleToString(price, digits) +
         " sl=" + DoubleToString(slPrice, digits) + " tp=" + DoubleToString(tpPrice, digits) +
         " lot=" + DoubleToString(lot, 2) + " spread=" + DoubleToString(spread, 1) +
         " bt=" + IntegerToString(m_breakevenTrigger) + " ts=" + IntegerToString(m_trailingStep);
      WriteDebugLog(debugInfo);

      int ticket = -1;
      int retryCount = 0;
      int maxRetries = 3;
      int finalErr = 0;
      while(ticket < 0 && retryCount < maxRetries)
      {
         ticket = OrderSend(m_symbol, orderType, lot, price, slippage, slPrice, tpPrice,
                          "ScalpDaily ML", 0, 0, orderColor);
         if(ticket < 0)
         {
            int err = GetLastError();
            finalErr = err;
            if(err == 130) { slPrice = 0; tpPrice = 0; }
            else if(err == 129 || err == 138) { RefreshRates(); bid = MarketInfo(m_symbol, MODE_BID); ask = MarketInfo(m_symbol, MODE_ASK); price = (orderType == OP_BUY) ? ask : bid; }
            else if(err == 145) Sleep(1000);
            else break;
            retryCount++;
            Sleep(300);
         }
      }

      if(ticket > 0)
         WriteDebugLog("SUCCESS: ticket=" + IntegerToString(ticket) + " side=" + side + " price=" + DoubleToString(price, digits));
      else
         WriteDebugLog("FAIL_FINAL: err=" + IntegerToString(finalErr));
      return ticket;
   }

   void ApplyProtection()
   {
      for(int i = OrdersTotal() - 1; i >= 0; i--)
      {
         if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderSymbol() != m_symbol) continue;

         double point = MarketInfo(m_symbol, MODE_POINT);
         int digits = (int)MarketInfo(m_symbol, MODE_DIGITS);
         double bid = MarketInfo(m_symbol, MODE_BID);
         double ask = MarketInfo(m_symbol, MODE_ASK);
         double openPrice = OrderOpenPrice();
         double currentSL = OrderStopLoss();
         double currentTP = OrderTakeProfit();
         int ticket = (int)OrderTicket();

         if(OrderType() == OP_BUY)
         {
            double profitPips = (bid - openPrice) / (point * 10);

            // Stage 2: Fast breakeven
            if(profitPips >= m_breakevenTrigger && currentSL < openPrice)
            {
               double newSL = NormalizeDouble(openPrice + 4 * point * 10, digits);
               if(OrderModify(ticket, openPrice, newSL, currentTP, 0, clrNONE))
               {
                  Print("BREAKEVEN BUY #", ticket, " pips=", DoubleToString(profitPips, 1));
                  WriteDebugLog("BREAKEVEN: ticket=" + IntegerToString(ticket) +
                     " side=BUY pips=" + DoubleToString(profitPips, 1) +
                     " oldSL=" + DoubleToString(currentSL, digits) +
                     " newSL=" + DoubleToString(newSL, digits));
               }
            }
            // Stage 3: Aggressive trailing
            else if(currentSL > openPrice && m_trailingStep > 0)
            {
               double idealSL = NormalizeDouble(bid - m_trailingStep * point * 10, digits);
               if(idealSL > currentSL + point * 5)
               {
                  if(OrderModify(ticket, openPrice, idealSL, currentTP, 0, clrNONE))
                  {
                     Print("TRAIL BUY #", ticket, " sl=", DoubleToString(idealSL, digits));
                     WriteDebugLog("TRAIL: ticket=" + IntegerToString(ticket) +
                        " side=BUY pips=" + DoubleToString(profitPips, 1) +
                        " oldSL=" + DoubleToString(currentSL, digits) +
                        " newSL=" + DoubleToString(idealSL, digits));
                  }
               }
            }
         }
         else if(OrderType() == OP_SELL)
         {
            double profitPips = (openPrice - ask) / (point * 10);
 
            if(profitPips >= m_breakevenTrigger && (currentSL > openPrice || currentSL == 0))
            {
               double newSL = NormalizeDouble(openPrice - 4 * point * 10, digits);
               if(OrderModify(ticket, openPrice, newSL, currentTP, 0, clrNONE))
               {
                  Print("BREAKEVEN SELL #", ticket, " pips=", DoubleToString(profitPips, 1));
                  WriteDebugLog("BREAKEVEN: ticket=" + IntegerToString(ticket) +
                     " side=SELL pips=" + DoubleToString(profitPips, 1) +
                     " oldSL=" + DoubleToString(currentSL, digits) +
                     " newSL=" + DoubleToString(newSL, digits));
               }
            }
            else if(currentSL < openPrice && currentSL > 0 && m_trailingStep > 0)
            {
               double idealSL = NormalizeDouble(ask + m_trailingStep * point * 10, digits);
               if(idealSL < currentSL - point * 5)
               {
                  if(OrderModify(ticket, openPrice, idealSL, currentTP, 0, clrNONE))
                  {
                     Print("TRAIL SELL #", ticket, " sl=", DoubleToString(idealSL, digits));
                     WriteDebugLog("TRAIL: ticket=" + IntegerToString(ticket) +
                        " side=SELL pips=" + DoubleToString(profitPips, 1) +
                        " oldSL=" + DoubleToString(currentSL, digits) +
                        " newSL=" + DoubleToString(idealSL, digits));
                  }
               }
            }
         }
      }
   }
};
