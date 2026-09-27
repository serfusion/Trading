#property strict

class CBridgeComm
{
private:
   string m_folder;

   string BuildPath(string filename) { return m_folder + "\\" + filename; }

   int SkipWhitespace(string text, int start)
   {
      int len = StringLen(text);
      for(int i = start; i < len; i++)
      {
         int ch = StringGetCharacter(text, i);
         if(ch != 32 && ch != 9 && ch != 10 && ch != 13) return i;
      }
      return len;
   }

   int FindValueEnd(string text, int start)
   {
      int len = StringLen(text);
      for(int i = start; i < len; i++)
      {
         int ch = StringGetCharacter(text, i);
         if(ch == ',' || ch == '}' || ch == ']') return i;
      }
      return len;
   }

   string TrimValue(string value)
   {
      StringTrimLeft(value);
      StringTrimRight(value);
      return value;
   }

   string ExtractStringValuePrivate(string json, string key)
   {
      int jsonLen = StringLen(json);
      string searchKey = "\"" + key + "\"";
      int keyLen = StringLen(searchKey);
      int pos = -1;
      for(int i = 0; i <= jsonLen - keyLen; i++)
      {
         bool match = true;
         for(int k = 0; k < keyLen; k++)
            if(StringGetCharacter(json, i + k) != StringGetCharacter(searchKey, k)) { match = false; break; }
         if(match) { pos = i; break; }
      }
      if(pos < 0) return "";
      int colon = -1;
      for(int i = pos + keyLen; i < jsonLen; i++)
         if(StringGetCharacter(json, i) == 58) { colon = i; break; }
      if(colon < 0) return "";
      int valStart = -1;
      for(int i = colon + 1; i < jsonLen; i++)
      {
         int c = StringGetCharacter(json, i);
         if(c != 32 && c != 9 && c != 10 && c != 13) { valStart = i; break; }
      }
      if(valStart < 0) return "";
      if(StringGetCharacter(json, valStart) == 34)
      {
         for(int i = valStart + 1; i < jsonLen; i++)
         {
            if(StringGetCharacter(json, i) == 34)
            {
               int len = i - valStart - 1;
               if(len <= 0) return "";
               return StringSubstr(json, valStart + 1, len);
            }
         }
         return "";
      }
      int valEnd = jsonLen;
      for(int i = valStart; i < jsonLen; i++)
      {
         int c = StringGetCharacter(json, i);
         if(c == 44 || c == 125 || c == 93) { valEnd = i; break; }
      }
      string result = StringSubstr(json, valStart, valEnd - valStart);
      StringTrimLeft(result);
      StringTrimRight(result);
      return result;
   }

   bool ReadFilePrivate(string filename, string &content)
   {
      string path = BuildPath(filename);
      int handle = FileOpen(path, FILE_READ | FILE_TXT | FILE_COMMON);
      if(handle == INVALID_HANDLE) return false;
      int size = (int)FileSize(handle);
      content = FileReadString(handle, size);
      FileClose(handle);
      return true;
   }

public:
   bool Initialize(string folder)
   {
      if(folder == "") folder = "ScalpDailyBridge";
      m_folder = folder;
      if(!FolderCreate(m_folder, FILE_COMMON))
      {
         int error = GetLastError();
         if(error != 5019) { Print("ERROR: Bridge folder: ", error); return false; }
      }
      return true;
   }

   bool WriteMarketData(string json) { return WriteFile("market_data.json", json); }
   bool WritePositions(string json) { return WriteFile("positions.json", json); }

   void DebugWrite(string tag, string val)
   {
      int h = FileOpen("ScalpDailyBridge\\debug_" + tag + ".txt", FILE_WRITE | FILE_TXT | FILE_COMMON);
      if(h != INVALID_HANDLE) { FileWriteString(h, val); FileClose(h); }
   }

   string ExtractStringValue(string json, string key) { return ExtractStringValuePrivate(json, key); }

   double ExtractNumberValue(string json, string key, double def)
   {
      string value = ExtractStringValue(json, key);
      if(value == "") return def;
      return StringToDouble(value);
   }

   bool ReadFile(string filename, string &content) { return ReadFilePrivate(filename, content); }

   bool WriteFile(string filename, string content)
   {
      string path = BuildPath(filename);
      int handle = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_COMMON);
      if(handle == INVALID_HANDLE) { Print("ERROR: Write ", filename, " err=", GetLastError()); return false; }
      FileWriteString(handle, content);
      FileClose(handle);
      return true;
   }

   bool ReadSignal(string &side, double &probability, string &reason,
                   double &lot, int &sl_pips, int &tp_pips,
                   int &breakeven_trigger, int &trailing_step,
                   double &lot_buy, double &lot_sell)
   {
      string json;
      if(!ReadFilePrivate("signals.json", json)) return false;
      DebugWrite("RAW_JSON", json);
      side = ExtractStringValuePrivate(json, "signal");
      DebugWrite("EXTRACTED_SIDE", side);
      probability = ExtractNumberValue(json, "probability", 0.0);
      reason = ExtractStringValuePrivate(json, "reason");
      lot = ExtractNumberValue(json, "lot", 0.0);
      sl_pips = (int)ExtractNumberValue(json, "sl_pips", 0.0);
      tp_pips = (int)ExtractNumberValue(json, "tp_pips", 0.0);
      breakeven_trigger = (int)ExtractNumberValue(json, "breakeven_trigger", 5);
      trailing_step = (int)ExtractNumberValue(json, "trailing_step", 2);
      lot_buy = ExtractNumberValue(json, "lot_buy", 0.0);
      lot_sell = ExtractNumberValue(json, "lot_sell", 0.0);
      DebugWrite("EXTRACTED_PROB", DoubleToString(probability, 5));
      FileDelete(BuildPath("signals.json"), FILE_COMMON);
      return side != "";
   }

   bool ReadSignal(string &side, double &probability, string &reason,
                   double &lot, int &sl_pips, int &tp_pips,
                   int &breakeven_trigger, int &trailing_step)
   {
      double lb = 0, ls = 0;
      return ReadSignal(side, probability, reason, lot, sl_pips, tp_pips, breakeven_trigger, trailing_step, lb, ls);
   }

   bool ReadSignalVektor(string &side, double &confidence, string &reason,
                         double &lot_buy, double &lot_sell,
                         int &sl_pips, int &tp_pips,
                         int &breakeven_trigger, int &trailing_step,
                         string &bar_time, string &session, string &regime,
                         double &spike_score)
   {
      string json;
      if(!ReadFilePrivate("signals.json", json)) return false;
      DebugWrite("RAW_JSON", json);
      side = ExtractStringValuePrivate(json, "signal");
      if(side == "") return false;
      confidence = ExtractNumberValue(json, "confidence", 0.0);
      reason = ExtractStringValuePrivate(json, "reason");
      lot_buy = ExtractNumberValue(json, "lot_buy", 0.0);
      lot_sell = ExtractNumberValue(json, "lot_sell", 0.0);
      sl_pips = (int)ExtractNumberValue(json, "sl_pips", 0.0);
      tp_pips = (int)ExtractNumberValue(json, "tp_pips", 0.0);
      breakeven_trigger = (int)ExtractNumberValue(json, "breakeven_trigger", 4);
      trailing_step = (int)ExtractNumberValue(json, "trailing_step", 2);
      bar_time = ExtractStringValuePrivate(json, "bar_time");
      session = ExtractStringValuePrivate(json, "session");
      regime = ExtractStringValuePrivate(json, "regime");
      spike_score = ExtractNumberValue(json, "spike_score", 0.0);
      DebugWrite("EXTRACTED_SIDE", side);
      DebugWrite("EXTRACTED_PROB", DoubleToString(confidence, 5));
      FileDelete(BuildPath("signals.json"), FILE_COMMON);
      return true;
   }

   bool ReadDailyTracker(string &json)
   {
      if(!ReadFilePrivate("daily_tracker.json", json))
      {
         json = "{\"date\":\"\",\"loss_pips\":0.0,\"consecutive_losses\":0,\"circuit_breaker_until\":\"\"}";
         return false;
      }
      return true;
   }

   bool WriteDailyTracker(string json) { return WriteFile("daily_tracker.json", json); }

   bool ReadOrderRequest(string &action, string &symbol, string &side, double &lot, double &sl, double &tp)
   {
      string json;
      if(!ReadFilePrivate("orders.json", json)) return false;
      action = ExtractStringValuePrivate(json, "action");
      symbol = ExtractStringValuePrivate(json, "symbol");
      side = ExtractStringValuePrivate(json, "side");
      lot = ExtractNumberValue(json, "lot", 0.0);
      sl = ExtractNumberValue(json, "sl", 0.0);
      tp = ExtractNumberValue(json, "tp", 0.0);
      FileDelete(BuildPath("orders.json"), FILE_COMMON);
      return action != "";
   }

   bool ReadSignal(string &side, double &probability, string &reason,
                   double &lot, int &sl_pips, int &tp_pips)
   {
      int bt = 5, ts = 2;
      return ReadSignal(side, probability, reason, lot, sl_pips, tp_pips, bt, ts);
   }
};
