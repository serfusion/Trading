#property strict

string SD_TimeframeToString(int tf)
{
   if(tf == PERIOD_M1) return "M1";
   if(tf == PERIOD_M5) return "M5";
   if(tf == PERIOD_M15) return "M15";
   if(tf == PERIOD_M30) return "M30";
   if(tf == PERIOD_H1) return "H1";
   if(tf == PERIOD_H4) return "H4";
   if(tf == PERIOD_D1) return "D1";
   if(tf == PERIOD_W1) return "W1";
   if(tf == PERIOD_MN1) return "MN1";
   return "M1";
}

class CDataCollector
{
private:
   string            m_symbol;
   ENUM_TIMEFRAMES   m_primaryTF;
   ENUM_TIMEFRAMES   m_timeframes[3];
   string            m_tfNames[3];

   double            m_currentOpen;
   double            m_currentHigh;
   double            m_currentLow;
   double            m_currentClose;
   int               m_currentVolume;
   double            m_currentRSI;
   double            m_currentATR;

   struct HistoryBar
   {
      datetime ts;
      double   open;
      double   high;
      double   low;
      double   close;
      int      volume;
      double   rsi;
      double   atr;
   };
   HistoryBar m_history[];
   int m_historyCount;
   string            m_trainingFolder;
   datetime          m_lastBarTime;
   datetime          m_lastBarM5Time;

   int PrimaryIndex()
   {
      for(int i = 0; i < 3; i++)
         if(m_timeframes[i] == m_primaryTF) return i;
      return 0;
   }

   string BuildBarsJSON(ENUM_TIMEFRAMES tf, int maxBars)
   {
      string result = "";
      MqlRates rates[];
      int copied = CopyRates(m_symbol, tf, 1, maxBars, rates);
      if(copied <= 0) return "[]";
      for(int i = 0; i < copied; i++)
      {
         if(i > 0) result += ",";
         result += "{";
         result += "\"timestamp\":\"" + TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES) + "\",";
         result += "\"open\":" + DoubleToString(rates[i].open, 2) + ",";
         result += "\"high\":" + DoubleToString(rates[i].high, 2) + ",";
         result += "\"low\":" + DoubleToString(rates[i].low, 2) + ",";
         result += "\"close\":" + DoubleToString(rates[i].close, 2) + ",";
         result += "\"volume\":" + IntegerToString((int)rates[i].tick_volume);
         result += "}";
      }
      return "[" + result + "]";
   }

public:
   CDataCollector()
   {
      m_symbol = "";
      m_primaryTF = PERIOD_M15;
      m_timeframes[0] = PERIOD_M15;
      m_timeframes[1] = PERIOD_H1;
      m_timeframes[2] = PERIOD_H4;
      m_tfNames[0] = "M15";
      m_tfNames[1] = "H1";
      m_tfNames[2] = "H4";
      m_historyCount = 0;
      m_lastBarTime = 0;
      ArrayResize(m_history, 10000);
   }

   void Configure(string symbol,
                  ENUM_TIMEFRAMES tf1 = PERIOD_M1,
                  ENUM_TIMEFRAMES tf2 = PERIOD_M5,
                  ENUM_TIMEFRAMES tf3 = PERIOD_H1)
   {
      m_symbol = symbol;
      m_timeframes[0] = tf1;
      m_timeframes[1] = tf2;
      m_timeframes[2] = tf3;
      m_tfNames[0] = SD_TimeframeToString(tf1);
      m_tfNames[1] = SD_TimeframeToString(tf2);
      m_tfNames[2] = SD_TimeframeToString(tf3);
      m_primaryTF = tf1;
   }

   bool SetupTrainingExport(string folder)
   {
      m_trainingFolder = folder;
      string fullPath = m_trainingFolder + "\\";
      if(!FolderCreate(fullPath, FILE_COMMON))
      {
         int error = GetLastError();
         if(error != 5019) { Print("ERROR: Training folder: ", error); return false; }
      }
      return true;
   }

   bool Initialize()
   {
      if(m_symbol == "") m_symbol = Symbol();
      Print("DataCollector (M15 scalping): ", m_symbol, " TFs=", m_tfNames[0], "/", m_tfNames[1], "/", m_tfNames[2]);
      return true;
   }

   void CollectCurrentData()
   {
      datetime barTime = iTime(m_symbol, m_primaryTF, 0);
      if(barTime == m_lastBarTime) return;
      m_lastBarTime = barTime;

      m_currentOpen   = iOpen(m_symbol, m_primaryTF, 0);
      m_currentHigh   = iHigh(m_symbol, m_primaryTF, 0);
      m_currentLow    = iLow(m_symbol, m_primaryTF, 0);
      m_currentClose  = iClose(m_symbol, m_primaryTF, 0);
      m_currentVolume = (int)iVolume(m_symbol, m_primaryTF, 0);
      m_currentRSI    = iRSI(m_symbol, m_primaryTF, 7, PRICE_CLOSE, 0);
      m_currentATR    = iATR(m_symbol, m_primaryTF, 5, 0);

      if(m_historyCount < ArraySize(m_history))
      {
         m_history[m_historyCount].ts        = TimeCurrent();
         m_history[m_historyCount].open      = m_currentOpen;
         m_history[m_historyCount].high      = m_currentHigh;
         m_history[m_historyCount].low       = m_currentLow;
         m_history[m_historyCount].close     = m_currentClose;
         m_history[m_historyCount].volume    = m_currentVolume;
         m_history[m_historyCount].rsi       = m_currentRSI;
         m_history[m_historyCount].atr       = m_currentATR;
         m_historyCount++;
      }
      else
      {
         for(int i = 1; i < m_historyCount; i++)
            m_history[i - 1] = m_history[i];
         m_history[m_historyCount - 1].ts        = TimeCurrent();
         m_history[m_historyCount - 1].open      = m_currentOpen;
         m_history[m_historyCount - 1].high      = m_currentHigh;
         m_history[m_historyCount - 1].low       = m_currentLow;
         m_history[m_historyCount - 1].close     = m_currentClose;
         m_history[m_historyCount - 1].volume    = m_currentVolume;
         m_history[m_historyCount - 1].rsi       = m_currentRSI;
         m_history[m_historyCount - 1].atr       = m_currentATR;
      }
   }

   string GetMarketData(int maxBars)
   {
      string json = "{";
      json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + "\",";
      json += "\"symbol\":\"" + m_symbol + "\",";
      json += "\"primary_timeframe\":\"" + m_tfNames[0] + "\",";
      json += "\"timeframes\":[\"" + m_tfNames[0] + "\",\"" + m_tfNames[1] + "\",\"" + m_tfNames[2] + "\"],";
      json += "\"ohlcv\":{\"open\":" + DoubleToString(m_currentOpen, 2) + ",\"high\":" + DoubleToString(m_currentHigh, 2) + ",\"low\":" + DoubleToString(m_currentLow, 2) + ",\"close\":" + DoubleToString(m_currentClose, 2) + ",\"volume\":" + IntegerToString(m_currentVolume) + "},";
      json += "\"indicators\":{\"rsi\":" + DoubleToString(m_currentRSI, 2) + ",\"atr\":" + DoubleToString(m_currentATR, 2) + ",\"close\":" + DoubleToString(m_currentClose, 2) + "},";
      json += "\"bars\":" + BuildBarsJSON(m_primaryTF, maxBars) + ",";
      json += "\"bars_" + m_tfNames[0] + "\":" + BuildBarsJSON(m_timeframes[0], maxBars) + ",";
      json += "\"bars_" + m_tfNames[1] + "\":" + BuildBarsJSON(m_timeframes[1], maxBars) + ",";
      json += "\"bars_" + m_tfNames[2] + "\":" + BuildBarsJSON(m_timeframes[2], maxBars);
      json += "}";
      return json;
   }

   string GetMarketData() { return GetMarketData(200); }

   bool ExportTrainingData()
   {
      if(m_historyCount == 0) { Print("No data to export"); return false; }
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      string filename = m_trainingFolder + "\\" + m_symbol + "_" +
                        SD_TimeframeToString(m_primaryTF) + "_" +
                        IntegerToString(dt.year) +
                        (dt.mon < 10 ? "0" + IntegerToString(dt.mon) : IntegerToString(dt.mon)) +
                        (dt.day < 10 ? "0" + IntegerToString(dt.day) : IntegerToString(dt.day)) +
                        ".csv";
      int handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON, ",");
      if(handle == INVALID_HANDLE) { Print("ERROR: File open: ", GetLastError()); return false; }
      FileWrite(handle, "timestamp", "open", "high", "low", "close", "volume", "rsi", "atr");
      for(int i = 0; i < m_historyCount; i++)
         FileWrite(handle,
                  TimeToString(m_history[i].ts, TIME_DATE|TIME_MINUTES),
                  DoubleToString(m_history[i].open, 2),
                  DoubleToString(m_history[i].high, 2),
                  DoubleToString(m_history[i].low, 2),
                  DoubleToString(m_history[i].close, 2),
                  IntegerToString(m_history[i].volume),
                  DoubleToString(m_history[i].rsi, 2),
                  DoubleToString(m_history[i].atr, 2));
      FileClose(handle);
      Print("Training data exported: ", m_historyCount, " rows to ", filename);
      return true;
   }

    void DumpHistoryToCSV(string folder, int maxM15Bars, int maxM1Bars)
    {
       string path_m15 = folder + "\\history_M15.csv";
       int h_m15 = FileOpen(path_m15, FILE_WRITE|FILE_CSV|FILE_COMMON, ",");
       if(h_m15 != INVALID_HANDLE)
       {
          FileWrite(h_m15, "timestamp,open,high,low,close,volume");
          int bars = MathMin(maxM15Bars, Bars(NULL, PERIOD_M15));
          for(int i = bars - 1; i >= 0; i--)
          {
             FileWrite(h_m15,
                TimeToString(iTime(NULL, PERIOD_M15, i), TIME_DATE|TIME_MINUTES),
                DoubleToString(iOpen(NULL, PERIOD_M15, i), 5),
                DoubleToString(iHigh(NULL, PERIOD_M15, i), 5),
                DoubleToString(iLow(NULL, PERIOD_M15, i), 5),
                DoubleToString(iClose(NULL, PERIOD_M15, i), 5),
                (int)iVolume(NULL, PERIOD_M15, i));
          }
          FileClose(h_m15);
          Print("M15 history dumped: ", bars, " bars -> ", path_m15);
       }

       string path_m1 = folder + "\\history_M1.csv";
       int h_m1 = FileOpen(path_m1, FILE_WRITE|FILE_CSV|FILE_COMMON, ",");
       if(h_m1 != INVALID_HANDLE)
       {
          FileWrite(h_m1, "timestamp,open,high,low,close,volume");
          int bars = MathMin(maxM1Bars, Bars(NULL, PERIOD_M1));
          for(int i = bars - 1; i >= 0; i--)
          {
             FileWrite(h_m1,
                TimeToString(iTime(NULL, PERIOD_M1, i), TIME_DATE|TIME_MINUTES),
                DoubleToString(iOpen(NULL, PERIOD_M1, i), 5),
                DoubleToString(iHigh(NULL, PERIOD_M1, i), 5),
                DoubleToString(iLow(NULL, PERIOD_M1, i), 5),
                DoubleToString(iClose(NULL, PERIOD_M1, i), 5),
                (int)iVolume(NULL, PERIOD_M1, i));
          }
          FileClose(h_m1);
          Print("M1 history dumped: ", bars, " bars -> ", path_m1);
       }
    }

    void RecordTrade(int ticket, string side, double probability)
   {
      string filename = m_trainingFolder + "\\trades_log.csv";
      int handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_READ, ",");
      if(handle == INVALID_HANDLE) { Print("WARNING: Record trade: ", GetLastError()); return; }
      FileSeek(handle, 0, SEEK_END);
      FileWrite(handle,
               TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
               IntegerToString(ticket), side,
               DoubleToString(probability, 3),
               DoubleToString(m_currentClose, 2),
               DoubleToString(m_currentRSI, 2),
               DoubleToString(m_currentATR, 2));
      FileClose(handle);
   }
};
