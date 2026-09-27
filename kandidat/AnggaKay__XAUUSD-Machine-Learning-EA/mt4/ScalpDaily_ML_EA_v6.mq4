#property strict

#include <ScalpDaily_DataCollector.mqh>
#include <ScalpDaily_Bridge.mqh>
#include <ScalpDaily_OrderEngine.mqh>

input string BridgeFolder = "ScalpDailyBridge";
input ENUM_TIMEFRAMES PrimaryTimeframe = PERIOD_M1;
input ENUM_TIMEFRAMES ConfluenceTF1 = PERIOD_M5;
input ENUM_TIMEFRAMES ConfluenceTF2 = PERIOD_H1;
input int BarsCount = 200;
input int TickDelaySeconds = 2;

input double DefaultLot = 0.01;
input int DefaultSLPips = 7;
input int DefaultTPPips = 50;
input int DefaultBreakevenTrigger = 4;
input int DefaultTrailingStep = 15;
#define MAX_SPREAD_PIPS 25

input int MaxOpenPositions = 999;
input int SessionStartHour = 0;
input int SessionEndHour = 24;
input double MaxDailyLossPips = 100;
input int MaxConsecutiveLosses = 5;
input int CircuitBreakerPauseMinutes = 240;

CDataCollector g_collector;
CBridgeComm g_bridge;
COrderEngine g_orders;

bool g_dataDumped = false;
datetime g_lastTick = 0;
datetime g_lastTradeTime = 0;
int g_lastExportHour = -1;

double g_dailyLossPips = 0.0;
double g_dailyProfitUSD = 0.0;
int g_consecutiveLosses = 0;
datetime g_circuitBreakerUntil = 0;
string g_currentDate = "";


// ── Close tracking ─────────────────────────────────────────────────
#define MAX_TRACKED 200
int g_tickets[MAX_TRACKED];
string g_ticketSides[MAX_TRACKED];
double g_ticketPrices[MAX_TRACKED];
double g_ticketSL[MAX_TRACKED];
double g_ticketTP[MAX_TRACKED];
int g_ticketCount = 0;

void AddTicket(int ticket, string side, double price, double sl, double tp)
{
   if(g_ticketCount >= MAX_TRACKED) return;
   g_tickets[g_ticketCount] = ticket;
   g_ticketSides[g_ticketCount] = side;
   g_ticketPrices[g_ticketCount] = price;
   g_ticketSL[g_ticketCount] = sl;
   g_ticketTP[g_ticketCount] = tp;
   g_ticketCount++;
}

void TrackClosedTrades()
{
   for(int i = g_ticketCount - 1; i >= 0; i--)
   {
      bool found = false;
      for(int j = OrdersTotal() - 1; j >= 0; j--)
      {
         if(OrderSelect(j, SELECT_BY_POS, MODE_TRADES))
         {
            if((int)OrderTicket() == g_tickets[i]) { found = true; break; }
         }
      }
      if(found) continue;

      for(int h = OrdersHistoryTotal() - 1; h >= 0; h--)
      {
         if(OrderSelect(h, SELECT_BY_POS, MODE_HISTORY))
         {
            if((int)OrderTicket() != g_tickets[i]) continue;
            double closePrice = OrderClosePrice();
            double point = MarketInfo(OrderSymbol(), MODE_POINT);
            double pips = 0.0;
            if(g_ticketSides[i] == "BUY")
               pips = (closePrice - g_ticketPrices[i]) / (point * 10);
            else
               pips = (g_ticketPrices[i] - closePrice) / (point * 10);

            string reason = "OTHER";
            if(closePrice == OrderTakeProfit() && OrderTakeProfit() > 0) reason = "TP";
            else if(closePrice == OrderStopLoss() && OrderStopLoss() > 0) reason = "SL";
            else if(MathAbs(pips) < 0.5) reason = "BE";

            WriteDebugLog("CLOSE: ticket=" + IntegerToString(g_tickets[i]) +
               " side=" + g_ticketSides[i] +
               " entry=" + DoubleToString(g_ticketPrices[i], 5) +
               " close=" + DoubleToString(closePrice, 5) +
               " pips=" + DoubleToString(pips, 1) +
               " reason=" + reason);

            double tradeProfit = OrderProfit() + OrderCommission() + OrderSwap();
            g_dailyProfitUSD += tradeProfit;

            // Sync EA-side tracker: update loss_pips from this close
            if(pips <= 0)
            {
               g_dailyLossPips += MathAbs(pips);
               g_consecutiveLosses++;
            }
            else
            {
               g_consecutiveLosses = 0;
            }
            if(g_consecutiveLosses >= MaxConsecutiveLosses)
            {
               g_circuitBreakerUntil = TimeCurrent() + CircuitBreakerPauseMinutes * 60;
               g_consecutiveLosses = 0;
            }
            UpdateDailyTrackerFile();

            break;
         }
      }

      for(int k = i; k < g_ticketCount - 1; k++)
      {
         g_tickets[k] = g_tickets[k + 1];
         g_ticketSides[k] = g_ticketSides[k + 1];
         g_ticketPrices[k] = g_ticketPrices[k + 1];
         g_ticketSL[k] = g_ticketSL[k + 1];
         g_ticketTP[k] = g_ticketTP[k + 1];
      }
      g_ticketCount--;
   }
}

void WriteDebugLog(string msg)
{
   int handle = FileOpen("ScalpDailyBridge\\ea_trace.log", FILE_WRITE | FILE_READ | FILE_TXT | FILE_COMMON);
   if(handle != INVALID_HANDLE)
   {
      FileSeek(handle, 0, SEEK_END);
      string line = "[" + TimeToString(TimeCurrent()) + "] [v6] " + msg + "\r\n";
      FileWriteString(handle, line);
      FileClose(handle);
   }
}

string BuildPositionsJSON()
{
   string json = "{\"balance\":" + DoubleToString(AccountBalance(), 2) + ",";
   json += "\"equity\":" + DoubleToString(AccountEquity(), 2) + ",";
   json += "\"positions\":[";
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(count > 0) json += ",";
         json += "{\"ticket\":" + IntegerToString(OrderTicket()) + ",";
         json += "\"symbol\":\"" + OrderSymbol() + "\",";
         json += "\"type\":\"" + (OrderType() == OP_BUY ? "BUY" : "SELL") + "\",";
         json += "\"lots\":" + DoubleToString(OrderLots(), 2) + ",";
         json += "\"open_price\":" + DoubleToString(OrderOpenPrice(), 5) + ",";
         json += "\"sl\":" + DoubleToString(OrderStopLoss(), 5) + ",";
         json += "\"tp\":" + DoubleToString(OrderTakeProfit(), 5) + ",";
         json += "\"profit\":" + DoubleToString(OrderProfit(), 2);
         json += "}";
         count++;
      }
   }
   json += "]}";
   return json;
}

int CountOpenPositions()
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) count++;
   return count;
}

double GetOpenPositionProfit()
{
   double total = 0.0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         total += OrderProfit() + OrderSwap() + OrderCommission();
   return total;
}

double GetPipsForSymbol(double priceDiff)
{
   double point = MarketInfo(Symbol(), MODE_POINT);
   if(point <= 0) return 0.0;
   return priceDiff / (point * 10);
}

void RecalcDailyLoss()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   string today = IntegerToString(dt.year) + "-" +
                  StringFormat("%02d", dt.mon) + "-" +
                  StringFormat("%02d", dt.day);
   if(g_currentDate != today)
   {
      g_currentDate = today;
      g_dailyLossPips = 0.0;
      g_dailyProfitUSD = 0.0;
      g_consecutiveLosses = 0;
      g_circuitBreakerUntil = 0;
   }
    string json;
    if(g_bridge.ReadDailyTracker(json))
    {
       double fileLoss = g_bridge.ExtractNumberValue(json, "loss_pips", 0.0);
       if(fileLoss > g_dailyLossPips) g_dailyLossPips = fileLoss;
       double fileProfit = g_bridge.ExtractNumberValue(json, "profit_usd", 0.0);
       if(fileProfit > g_dailyProfitUSD) g_dailyProfitUSD = fileProfit;
    }
}

void UpdateDailyTrackerFile()
{
   // Sync EA tracker from file first (in case Python updated it)
   string jsonIn;
   if(g_bridge.ReadDailyTracker(jsonIn))
   {
      double fileLoss = g_bridge.ExtractNumberValue(jsonIn, "loss_pips", 0.0);
      if(fileLoss > g_dailyLossPips) g_dailyLossPips = fileLoss;
      double fileProfit = g_bridge.ExtractNumberValue(jsonIn, "profit_usd", 0.0);
      if(fileProfit > g_dailyProfitUSD) g_dailyProfitUSD = fileProfit;
   }

   string json = "{\"date\":\"" + g_currentDate + "\",";
   json += "\"loss_pips\":" + DoubleToString(g_dailyLossPips, 1) + ",";
   json += "\"profit_usd\":" + DoubleToString(g_dailyProfitUSD, 2) + ",";
   json += "\"consecutive_losses\":" + IntegerToString(g_consecutiveLosses) + ",";
   json += "\"circuit_breaker_until\":\"";
   if(g_circuitBreakerUntil > 0)
      json += TimeToString(g_circuitBreakerUntil);
   json += "\"}";
   g_bridge.WriteDailyTracker(json);
}

void ApplyTimeStop()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == Symbol() && (OrderComment() == "ScalpDaily ML" || OrderComment() == "ScalpDaily ML(t)"))
         {
            datetime openTime = OrderOpenTime();
            if(TimeCurrent() - openTime >= 30 * 60) // 30 minutes
            {
               double closePrice = (OrderType() == OP_BUY) ? Bid : Ask;
               bool closed = OrderClose(OrderTicket(), OrderLots(), closePrice, 30, clrOrange);
               if(closed)
               {
                  WriteDebugLog("TIMESTOP: ticket=" + IntegerToString(OrderTicket()) + " closed after 30 mins");
                  Print("VEKTOR v6 TIMESTOP: closed ticket #", OrderTicket());
               }
               else
               {
                  WriteDebugLog("TIMESTOP_FAILED: ticket=" + IntegerToString(OrderTicket()) + " err=" + IntegerToString(GetLastError()));
               }
            }
         }
      }
   }
}

void CheckActiveOrderRequests()
{
   string action = "";
   string reqSymbol = "";
   string side = "";
   double lot = 0.0;
   double newSL = 0.0;
   double newTP = 0.0;
   
   if(g_bridge.ReadOrderRequest(action, reqSymbol, side, lot, newSL, newTP))
   {
      WriteDebugLog("ORDER_REQ: action=" + action + " sym=" + reqSymbol + " sl=" + DoubleToString(newSL, 5) + " tp=" + DoubleToString(newTP, 5));
      if(reqSymbol != Symbol() && reqSymbol != "") return;
      
      for(int i = OrdersTotal() - 1; i >= 0; i--)
      {
         if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         {
            if(OrderSymbol() == Symbol())
            {
               int ticket = OrderTicket();
               if(action == "CLOSE")
               {
                  double closePrice = (OrderType() == OP_BUY) ? Bid : Ask;
                  if(OrderClose(ticket, OrderLots(), closePrice, 30, clrRed))
                  {
                     WriteDebugLog("REQ_CLOSE_SUCCESS: ticket=" + IntegerToString(ticket));
                     Print("VEKTOR v9.7 REQ_CLOSE: ticket #", ticket, " closed successfully.");
                  }
                  else
                  {
                     WriteDebugLog("REQ_CLOSE_FAILED: ticket=" + IntegerToString(ticket) + " err=" + IntegerToString(GetLastError()));
                  }
               }
               else if(action == "MODIFY")
               {
                  double currentTP = OrderTakeProfit();
                  double currentSL = OrderStopLoss();
                  double openPrice = OrderOpenPrice();
                  
                  double targetSL = currentSL;
                  double targetTP = currentTP;
                  
                  if(newSL > 0) targetSL = NormalizeDouble(newSL, Digits);
                  if(newTP > 0) targetTP = NormalizeDouble(newTP, Digits);
                  
                  if(targetSL != currentSL || targetTP != currentTP)
                  {
                     if(OrderModify(ticket, openPrice, targetSL, targetTP, 0, clrNONE))
                     {
                        WriteDebugLog("REQ_MODIFY_SUCCESS: ticket=" + IntegerToString(ticket) + " sl=" + DoubleToString(targetSL, 5));
                        Print("VEKTOR v9.7 REQ_MODIFY: ticket #", ticket, " SL updated to ", targetSL);
                     }
                     else
                     {
                        WriteDebugLog("REQ_MODIFY_FAILED: ticket=" + IntegerToString(ticket) + " err=" + IntegerToString(GetLastError()));
                     }
                  }
               }
            }
         }
      }
   }
}

bool IsBarGuardOk()
{
   return true;  // v6: no bar guard — Python controls throttling
}

bool IsDailyLossOk()
{
   return true;
}

bool IsCircuitBreakerOk()
{
   return true;
}

bool IsMarginOk(double lotNeeded)
{
   return true;
}

int OnInit()
{
   // Proteksi Arsitektur v8.1: Daftarkan ChartID aktif khusus simbol ini
   string activeVar = "VEKTOR_ACTIVE_CHART_" + Symbol();
   GlobalVariableSet(activeVar, (double)ChartID());

   g_collector.Configure(Symbol(), PrimaryTimeframe, ConfluenceTF1, ConfluenceTF2);
   g_collector.Initialize();
   g_collector.SetupTrainingExport("ScalpDailyTraining");
   if(!g_bridge.Initialize(BridgeFolder)) return INIT_FAILED;
   g_orders.SetSymbol(Symbol());
   g_orders.SetDebugFolder(BridgeFolder);
   g_orders.ConfigureEx(DefaultLot, DefaultSLPips, DefaultTPPips,
                        DefaultBreakevenTrigger, DefaultTrailingStep,
                        MAX_SPREAD_PIPS);
    g_lastTick = 0;
    g_lastTradeTime = 0;
    g_lastExportHour = -1;
    RecalcDailyLoss();
    if(!g_dataDumped)
    {
       g_collector.DumpHistoryToCSV(BridgeFolder, 1000, 6000);
       g_dataDumped = true;
    }
    EventSetMillisecondTimer(10000);
    Print("VEKTOR EA v6 (aggressive M5 scalper) initialized. Symbol=", Symbol(),
           " MaxPos=", MaxOpenPositions,
           " Lot=", DefaultLot,
           " SL=", DefaultSLPips,
           " BE=", DefaultBreakevenTrigger,
           " Trail=", DefaultTrailingStep,
           " SpreadMax=", MAX_SPREAD_PIPS);
    WriteDebugLog("INIT: MaxSpreadPips=" + IntegerToString(MAX_SPREAD_PIPS) +
                  " MaxPos=" + IntegerToString(MaxOpenPositions) +
                  " Lot=" + DoubleToString(DefaultLot, 2) +
                  " Timer=10s");
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    EventKillTimer();
}

void OnTimer()
{
    // Proteksi Arsitektur v8.1: Lewatkan jika instansi duplikat
    string activeVar = "VEKTOR_ACTIVE_CHART_" + Symbol();
    if(GlobalVariableGet(activeVar) != (double)ChartID()) return;

    RecalcDailyLoss();
    g_orders.ApplyProtection();
    TrackClosedTrades();
    ApplyTimeStop();
    CheckActiveOrderRequests();

    g_collector.CollectCurrentData();
    string json = g_collector.GetMarketData(BarsCount);
    g_bridge.WriteMarketData(json);
    string posJSON = BuildPositionsJSON();
    g_bridge.WritePositions(posJSON);

    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    if(dt.hour != g_lastExportHour)
    {
        if(g_collector.ExportTrainingData())
            Print("Auto-export training data sukses");
        g_lastExportHour = dt.hour;
    }
}

void OnTick()
{
   // Proteksi Arsitektur v8.1: Lewatkan jika instansi duplikat
   string activeVar = "VEKTOR_ACTIVE_CHART_" + Symbol();
   if(GlobalVariableGet(activeVar) != (double)ChartID()) return;

   RecalcDailyLoss();

   g_orders.ApplyProtection();
   TrackClosedTrades();
   ApplyTimeStop();
   CheckActiveOrderRequests();

   datetime now = TimeCurrent();
   if(g_lastTick != 0 && (now - g_lastTick) < TickDelaySeconds) return;
   g_lastTick = now;

   g_collector.CollectCurrentData();
   string json = g_collector.GetMarketData(BarsCount);
   g_bridge.WriteMarketData(json);
   string posJSON = BuildPositionsJSON();
   g_bridge.WritePositions(posJSON);

   MqlDateTime dt;
   TimeToStruct(now, dt);
   if(dt.hour != g_lastExportHour)
   {
      if(g_collector.ExportTrainingData())
         Print("Auto-export training data sukses");
      g_lastExportHour = dt.hour;
   }

   string side = "";
   double confidence = 0.0;
   string reason = "";
   double lot_buy = 0.0, lot_sell = 0.0;
   int sl_pips = 0, tp_pips = 0, breakeven_trigger = 0, trailing_step = 0;
   string bar_time = "", session = "", regime = "";
   double spike_score = 0.0;

   if(g_bridge.ReadSignalVektor(side, confidence, reason, lot_buy, lot_sell,
      sl_pips, tp_pips, breakeven_trigger, trailing_step,
      bar_time, session, regime, spike_score))
   {
        // ── Failsafe Anti-Duplication: Atomic MT4 Global Variable Check ──
        datetime sigTime = StringToTime(bar_time);
        double sigId = (sigTime > 0) ? (double)sigTime : spike_score;
        if(sigId > 0)
        {
           string varName = "VEKTOR_LAST_SIGNAL_ID";
           if(!GlobalVariableCheck(varName))
           {
              GlobalVariableSet(varName, 0.0);
           }
           
           double lastId = GlobalVariableGet(varName);
           if(lastId == sigId)
           {
              WriteDebugLog("SKIPPED: signal already processed (id=" + DoubleToString(sigId, 1) + ")");
              return;
           }
           
           // Try to atomically set the variable from lastId to sigId
           if(!GlobalVariableSetOnCondition(varName, sigId, lastId))
           {
              // If set condition failed, another chart updated it first!
              // Let's re-verify if it was updated to our sigId.
              double currentId = GlobalVariableGet(varName);
              if(currentId == sigId)
              {
                 WriteDebugLog("SKIPPED: signal processed in race condition (id=" + DoubleToString(sigId, 1) + ")");
                 return;
              }
              // If it's something else, skip anyway to be safe
              WriteDebugLog("SKIPPED: signal lock failed (id=" + DoubleToString(sigId, 1) + ")");
              return;
           }
        }
        // ────────────────────────────────────────────────────────────

       WriteDebugLog("SIGNAL: side=" + side + " conf=" + DoubleToString(confidence, 3) +
                     " reason=\"" + reason + "\"" +
                     " lot(B/S)=" + DoubleToString(lot_buy, 2) + "/" + DoubleToString(lot_sell, 2) +
                     " sl=" + IntegerToString(sl_pips) + " tp=" + IntegerToString(tp_pips) +
                     " session=" + session + " regime=" + regime +
                     " spike=" + DoubleToString(spike_score, 1));

       if(side != "BUY" && side != "SELL" && side != "BOTH")
       {
          WriteDebugLog("REJECTED: side=" + side + " (only BUY/SELL/BOTH supported)");
          return;
       }

       // v6 aggressive: no blocks

      double point = MarketInfo(Symbol(), MODE_POINT);
      int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);

      // v6: No ATR_OVERRIDE — Python controls SL/TP completely
       if(sl_pips <= 0) sl_pips = DefaultSLPips;
       if(tp_pips <= 0) tp_pips = DefaultTPPips;
       if(breakeven_trigger < 0) breakeven_trigger = DefaultBreakevenTrigger;
       if(trailing_step < 0) trailing_step = DefaultTrailingStep;

      if(side == "BOTH")
      {
         double buyLot = NormalizeDouble(MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                                        MathMin(lot_buy, MarketInfo(Symbol(), MODE_MAXLOT))), 2);
         double sellLot = NormalizeDouble(MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                                         MathMin(lot_sell, MarketInfo(Symbol(), MODE_MAXLOT))), 2);
         if(buyLot <= 0) buyLot = DefaultLot;
         if(sellLot <= 0) sellLot = DefaultLot;

         if(!IsMarginOk(buyLot + sellLot))
         {
            WriteDebugLog("REJECTED BOTH: insufficient margin for " +
                          DoubleToString(buyLot + sellLot, 2) + " lot");
            return;
         }

         g_orders.ConfigureEx(buyLot, sl_pips, tp_pips,
                              breakeven_trigger, trailing_step, MAX_SPREAD_PIPS);
          int buyTicket = g_orders.Execute("BUY");
          if(buyTicket > 0)
          {
             g_collector.RecordTrade(buyTicket, "BUY", confidence);
             double buyEntry = (OrderSelect(buyTicket, SELECT_BY_TICKET, MODE_TRADES)) ? OrderOpenPrice() : 0;
             double buySL = buyEntry - sl_pips * point * 10;
             double buyTP = buyEntry + tp_pips * point * 10;
             AddTicket(buyTicket, "BUY", buyEntry, buySL, buyTP);
             WriteDebugLog("EXECUTED BOTH-BUY: ticket=" + IntegerToString(buyTicket) +
                           " lot=" + DoubleToString(buyLot, 2) +
                           " sl=" + IntegerToString(sl_pips) + " tp=" + IntegerToString(tp_pips));
          }
          else WriteDebugLog("FAILED BOTH-BUY: err=" + IntegerToString(GetLastError()));

         g_orders.ConfigureEx(sellLot, sl_pips, tp_pips,
                              breakeven_trigger, trailing_step, MAX_SPREAD_PIPS);
          int sellTicket = g_orders.Execute("SELL");
          if(sellTicket > 0)
          {
             g_collector.RecordTrade(sellTicket, "SELL", confidence);
             double sellEntry = (OrderSelect(sellTicket, SELECT_BY_TICKET, MODE_TRADES)) ? OrderOpenPrice() : 0;
             double sellSL = sellEntry + sl_pips * point * 10;
             double sellTP = sellEntry - tp_pips * point * 10;
             AddTicket(sellTicket, "SELL", sellEntry, sellSL, sellTP);
             WriteDebugLog("EXECUTED BOTH-SELL: ticket=" + IntegerToString(sellTicket) +
                           " lot=" + DoubleToString(sellLot, 2) +
                           " sl=" + IntegerToString(sl_pips) + " tp=" + IntegerToString(tp_pips));
          }
          else WriteDebugLog("FAILED BOTH-SELL: err=" + IntegerToString(GetLastError()));

         if(buyTicket > 0 || sellTicket > 0)
         {
            g_lastTradeTime = now;
            Print("VEKTOR v6 BOTH EXECUTED: BUY#", buyTicket, "(", DoubleToString(buyLot, 2), ") ",
                  "SELL#", sellTicket, "(", DoubleToString(sellLot, 2), ") ",
                  "SL=", sl_pips, " TP=", tp_pips,
                  " BE=", breakeven_trigger, " Trail=", trailing_step);
         }
      }
      else
      {
         double execLot = NormalizeDouble(MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                                        MathMin((side == "BUY" ? lot_buy : lot_sell), MarketInfo(Symbol(), MODE_MAXLOT))), 2);
         if(execLot <= 0) execLot = DefaultLot;

         if(!IsMarginOk(execLot))
         {
            WriteDebugLog("REJECTED: insufficient margin for " + DoubleToString(execLot, 2) + " lot");
            return;
         }

         g_orders.ConfigureEx(execLot, sl_pips, tp_pips,
                              breakeven_trigger, trailing_step, MAX_SPREAD_PIPS);
          int ticket = g_orders.Execute(side);
          if(ticket > 0)
          {
             g_collector.RecordTrade(ticket, side, confidence);
             double entry = (OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES)) ? OrderOpenPrice() : 0;
             double tSL = (side == "BUY") ? entry - sl_pips * point * 10 : entry + sl_pips * point * 10;
             double tTP = (side == "BUY") ? entry + tp_pips * point * 10 : entry - tp_pips * point * 10;
             AddTicket(ticket, side, entry, tSL, tTP);
             WriteDebugLog("EXECUTED: side=" + side + " ticket=" + IntegerToString(ticket) +
                           " lot=" + DoubleToString(execLot, 2) +
                           " sl=" + IntegerToString(sl_pips) + " tp=" + IntegerToString(tp_pips) +
                           " be=" + IntegerToString(breakeven_trigger) +
                           " trail=" + IntegerToString(trailing_step));
             g_lastTradeTime = now;
             Print("VEKTOR v6 EXECUTED: ", side, "#", ticket, "(", DoubleToString(execLot, 2), ") ",
                   "SL=", sl_pips, " TP=", tp_pips,
                   " BE=", breakeven_trigger, " Trail=", trailing_step);
          }
          else WriteDebugLog("FAILED: side=" + side + " err=" + IntegerToString(GetLastError()));
      }
   }

   double totalEquity = AccountEquity();
   double totalBalance = AccountBalance();
   if(totalEquity < totalBalance * 0.7)
   {
      WriteDebugLog("EQUITY_ALERT: equity=" + DoubleToString(totalEquity, 1) +
                    " balance=" + DoubleToString(totalBalance, 1));
   }
}
