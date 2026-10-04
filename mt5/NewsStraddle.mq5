//+------------------------------------------------------------------+
//| NewsStraddle.mq5 — robot uji berita (CPI/NFP) untuk XAUUSD        |
//| Riset: docs/NEWS_DETIK.md & docs/NEWS_PRA2.md — satu-satunya      |
//| kandidat "disiapkan sebelum rilis" = Buy Stop + Sell Stop ±$1–2   |
//| beberapa detik sebelum rilis, tutup 1–3 menit. BELUM TERBUKTI:    |
//| positif di tick Exness, rugi di Dukascopy. Uji maju lot minimum.  |
//|                                                                  |
//| Cara kerja:                                                      |
//|  1. T-PlaceSecondsBefore: pasang Buy Stop (ask + Distance) dan   |
//|     Sell Stop (bid - Distance), masing-masing dengan SL.         |
//|  2. Begitu satu terisi, order lawan langsung dihapus (OCO).      |
//|  3. Posisi ditutup setelah CloseAfterSeconds (atau kena SL/TP).  |
//|  4. Bila tidak ada yang terisi sampai T+CancelAfterSeconds,       |
//|     semua order dihapus.                                         |
//|  5. Semua tick T-60 s.d. T+300 detik & hasil dicatat ke CSV di    |
//|     folder MQL5\Files (untuk dinilai: slippage nyata, hasil).    |
//| RecordOnly = true -> tidak membuka order, hanya mencatat tick.   |
//+------------------------------------------------------------------+
#property copyright "Dividend Indicator"
#property version   "1.00"

#include <Trade\Trade.mqh>

input string ReleaseUTC          = "2026.10.14 12:30"; // waktu rilis UTC (CPI 08:30 New York = 12:30 UTC saat EDT)
input bool   RecordOnly          = false; // true = hanya catat tick, tanpa order
input double Lot                 = 0.01;  // lot per order (pakai lot minimum dulu)
input double Distance            = 1.0;   // jarak Buy/Sell Stop dari harga ($)
input double StopLoss            = 5.0;   // SL dari harga isi ($)
input double TakeProfit          = 0.0;   // TP dari harga isi ($), 0 = tanpa TP (tutup karena waktu)
input int    PlaceSecondsBefore  = 5;     // pasang order N detik sebelum rilis
input int    CancelAfterSeconds  = 60;    // hapus order yang belum terisi N detik setelah rilis
input int    CloseAfterSeconds   = 180;   // tutup posisi N detik setelah terisi
input double MaxSpread           = 0.60;  // batal pasang bila spread lebih lebar dari ini ($)
input long   Magic               = 26101401;

CTrade   trade;
datetime release = 0;
int      state = 0;           // 0 menunggu, 1 order terpasang, 2 posisi terbuka, 3 selesai
double   reqBuy = 0, reqSell = 0;
datetime fillTime = 0;
int      ticksFile = INVALID_HANDLE;

//+------------------------------------------------------------------+
void Log(string what, string detail)
  {
   int h = FileOpen("NewsStraddle_log.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ';');
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS), _Symbol, what, detail);
   FileClose(h);
   Print("NewsStraddle: ", what, " ", detail);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   release = StringToTime(ReleaseUTC);
   if(release <= 0)
     {
      Alert("ReleaseUTC tidak valid, contoh: 2026.10.14 12:30");
      return(INIT_PARAMETERS_INCORRECT);
     }
   trade.SetExpertMagicNumber(Magic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(1000);
   EventSetMillisecondTimer(100);
   Log("mulai", StringFormat("rilis %s UTC, jarak %.2f, SL %.2f, TP %.2f, lot %.2f, rekam saja %s",
                             ReleaseUTC, Distance, StopLoss, TakeProfit, Lot, RecordOnly ? "ya" : "tidak"));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(ticksFile != INVALID_HANDLE)
      FileClose(ticksFile);
   Comment("");
  }

//+------------------------------------------------------------------+
//| Catat setiap tick T-60 s.d. T+300 detik                          |
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime now = TimeGMT();
   if(now < release - 60 || now > release + 300)
      return;
   MqlTick t;
   if(!SymbolInfoTick(_Symbol, t))
      return;
   if(ticksFile == INVALID_HANDLE)
     {
      string d = TimeToString(release, TIME_DATE);
      StringReplace(d, ".", "");
      string name = "NewsStraddle_ticks_" + d + ".csv";
      ticksFile = FileOpen(name, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ';');
      if(ticksFile != INVALID_HANDLE)
         FileWrite(ticksFile, "detik_dari_rilis", "time_msc", "bid", "ask");
     }
   if(ticksFile != INVALID_HANDLE)
     {
      double sec = (double)((long)t.time_msc - (long)release * 1000) / 1000.0;
      FileWrite(ticksFile, DoubleToString(sec, 3), (string)t.time_msc, DoubleToString(t.bid, _Digits),
                DoubleToString(t.ask, _Digits));
     }
  }

//+------------------------------------------------------------------+
int CountOrders()
  {
   int n = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk > 0 && OrderGetInteger(ORDER_MAGIC) == Magic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         n++;
     }
   return n;
  }

void DeleteOrders(string why)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk > 0 && OrderGetInteger(ORDER_MAGIC) == Magic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         if(trade.OrderDelete(tk))
            Log("hapus order", StringFormat("#%I64u (%s)", tk, why));
     }
  }

ulong OurPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk > 0 && PositionGetInteger(POSITION_MAGIC) == Magic && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return tk;
     }
   return 0;
  }

//+------------------------------------------------------------------+
//| OCO: begitu satu order terisi, order lawan langsung dihapus       |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.symbol != _Symbol)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != Magic)
      return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   double price = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   long type = HistoryDealGetInteger(trans.deal, DEAL_TYPE);
   if(entry == DEAL_ENTRY_IN && state == 1)
     {
      DeleteOrders("OCO: sisi lain terisi");
      fillTime = TimeGMT();
      double req = (type == DEAL_TYPE_BUY) ? reqBuy : reqSell;
      double slip = (type == DEAL_TYPE_BUY) ? price - req : req - price;
      Log("terisi", StringFormat("%s @ %s (diminta %s, slippage %.2f), detik dari rilis %d",
                                 type == DEAL_TYPE_BUY ? "BUY" : "SELL", DoubleToString(price, _Digits),
                                 DoubleToString(req, _Digits), slip, (int)(fillTime - release)));
      state = 2;
     }
   else
      if(entry == DEAL_ENTRY_OUT)
        {
         double pl = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) + HistoryDealGetDouble(trans.deal, DEAL_SWAP)
                     + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
         Log("tutup", StringFormat("@ %s, hasil %.2f %s, detik dari rilis %d", DoubleToString(price, _Digits), pl,
                                   AccountInfoString(ACCOUNT_CURRENCY), (int)(TimeGMT() - release)));
         state = 3;
        }
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   datetime now = TimeGMT();
   long left = (long)(release - now);
   Comment(StringFormat("NewsStraddle %s\nRilis %s UTC — %s\nStatus: %s", _Symbol, ReleaseUTC,
                        left > 0 ? StringFormat("%d detik lagi", (int)left) : StringFormat("%d detik lalu", (int)(-left)),
                        state == 0 ? (RecordOnly ? "rekam saja" : "menunggu") : state == 1 ? "order terpasang" :
                        state == 2 ? "posisi terbuka" : "selesai"));
   if(RecordOnly || state == 3)
      return;

   if(state == 0 && now >= release - PlaceSecondsBefore && now < release + 2)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(ask - bid > MaxSpread)
        {
         Log("batal", StringFormat("spread %.2f > %.2f", ask - bid, MaxSpread));
         state = 3;
         return;
        }
      reqBuy = NormalizeDouble(ask + Distance, _Digits);
      reqSell = NormalizeDouble(bid - Distance, _Digits);
      double tpB = TakeProfit > 0 ? NormalizeDouble(reqBuy + TakeProfit, _Digits) : 0.0;
      double tpS = TakeProfit > 0 ? NormalizeDouble(reqSell - TakeProfit, _Digits) : 0.0;
      bool b = trade.BuyStop(Lot, reqBuy, _Symbol, NormalizeDouble(reqBuy - StopLoss, _Digits), tpB,
                             ORDER_TIME_GTC, 0, "berita BUY");
      bool s = trade.SellStop(Lot, reqSell, _Symbol, NormalizeDouble(reqSell + StopLoss, _Digits), tpS,
                              ORDER_TIME_GTC, 0, "berita SELL");
      Log("pasang", StringFormat("bid %s ask %s -> Buy Stop %s (%s), Sell Stop %s (%s)",
                                 DoubleToString(bid, _Digits), DoubleToString(ask, _Digits),
                                 DoubleToString(reqBuy, _Digits), b ? "ok" : "GAGAL",
                                 DoubleToString(reqSell, _Digits), s ? "ok" : "GAGAL"));
      state = (b || s) ? 1 : 3;
      return;
     }

   if(state == 1)
     {
      if(OurPosition() > 0)        // cadangan bila OnTradeTransaction terlambat
        {
         DeleteOrders("OCO (cadangan)");
         if(fillTime == 0)
            fillTime = now;
         state = 2;
        }
      else
         if(now > release + CancelAfterSeconds)
           {
            DeleteOrders("tidak terisi");
            Log("selesai", "tidak ada order terisi");
            state = 3;
           }
      return;
     }

   if(state == 2)
     {
      if(CountOrders() > 0)
         DeleteOrders("OCO (cek ulang)");
      ulong pos = OurPosition();
      if(pos == 0)
         return;                    // sudah tertutup SL/TP (dicatat OnTradeTransaction)
      if(now >= fillTime + CloseAfterSeconds)
        {
         if(trade.PositionClose(pos))
            Log("tutup waktu", StringFormat("setelah %d detik", CloseAfterSeconds));
        }
     }
  }
//+------------------------------------------------------------------+
