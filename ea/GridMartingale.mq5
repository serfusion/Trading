//+------------------------------------------------------------------+
//| GridMartingale.mq5                                               |
//| EA grid martingale tiruan "Signal Strike" (riset 3 Okt 2026).    |
//| Uji di akun DEMO dulu. Hasil uji 2012–2026: rata-rata NEGATIF    |
//| di semua pengaturan (docs/EA_MARTINGALE.md). Bukan saran profit. |
//+------------------------------------------------------------------+
#property copyright "serfusion/Trading - riset"
#property version   "1.00"
#property description "Grid martingale: layer baru tiap harga melawan sejauh Jarak, lot x Pengali,"
#property description "semua layer ditutup saat harga = rata-rata entry +/- TP. Pengaman: batas rugi,"
#property description "tutup sebelum akhir pekan, jeda berita USD penting, jeda antar keranjang."

#include <Trade\Trade.mqh>

enum ENUM_ARAH
  {
   ARAH_BUY = 0,      // BUY saja (seperti trader)
   ARAH_SELL = 1,     // SELL saja
   ARAH_CANDLE = 2    // Ikut candle M5 terakhir
  };

input group "Grid"
input ENUM_ARAH InpArah        = ARAH_BUY;  // Arah keranjang
input double    InpLotAwal     = 0.01;      // Lot layer 1
input double    InpPengali     = 2.0;       // Pengali lot per layer (EA trader: 1.2)
input double    InpJarak       = 5.0;       // Jarak antar layer (USD harga emas)
input double    InpTP          = 1.9;       // TP keranjang: rata-rata entry +/- USD
input int       InpMaksLayer   = 15;        // Maksimal layer
input int       InpJedaMenit   = 45;        // Jeda setelah keranjang tutup (menit)

input group "Pengaman"
input double    InpBatasRugiPersen = 30.0;  // Tutup semua bila floating rugi >= % saldo (0 = mati)
input bool      InpTutupAkhirPekan = true;  // Tutup keranjang Jumat malam, buka lagi Senin
input int       InpJamTutupJumat   = 20;    // Jam server Jumat untuk menutup (Exness = UTC)
input int       InpJamBukaSenin    = 1;     // Jam server Senin mulai boleh buka keranjang
input bool      InpJedaBerita      = true;  // Tidak buka keranjang baru di sekitar berita USD penting
input int       InpMenitSebelum    = 30;    // Menit sebelum berita
input int       InpMenitSesudah    = 60;    // Menit sesudah berita
input double    InpMaksSpread      = 0.50;  // Maksimal spread (USD) untuk membuka/menambah layer

input group "Lain-lain"
input ulong     InpMagic       = 7712026;   // Magic number
input int       InpSlippage    = 30;        // Deviasi harga (points)

CTrade   trade;
datetime g_lastClose = 0;
datetime g_newsCheck = 0;
bool     g_newsBlock = false;
string   g_gvName    = "";

struct Basket
  {
   int      n;          // jumlah layer
   int      dir;        // 1 BUY, -1 SELL
   double   lots;       // total lot
   double   avg;        // rata-rata harga entry tertimbang lot
   double   lastPrice;  // harga entry layer terakhir
   double   lastLot;    // lot layer terakhir
   double   profit;     // floating (profit + swap), mata uang akun
  };

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpLotAwal <= 0.0 || InpPengali < 1.0 || InpJarak <= 0.0 || InpTP <= 0.0 || InpMaksLayer < 1)
      return(INIT_PARAMETERS_INCORRECT);
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   g_gvName = "GM_lastClose_" + IntegerToString((long)InpMagic) + "_" + _Symbol;
   if(GlobalVariableCheck(g_gvName))
      g_lastClose = (datetime)GlobalVariableGet(g_gvName);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Comment("");
  }

//+------------------------------------------------------------------+
bool IsMine()
  {
   return(PositionGetString(POSITION_SYMBOL) == _Symbol &&
          (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic);
  }

//+------------------------------------------------------------------+
void ReadBasket(Basket &b)
  {
   b.n = 0;
   b.dir = 0;
   b.lots = 0.0;
   b.avg = 0.0;
   b.lastPrice = 0.0;
   b.lastLot = 0.0;
   b.profit = 0.0;
   double sumPV = 0.0;
   long   lastMsc = -1;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !IsMine())
         continue;
      double v = PositionGetDouble(POSITION_VOLUME);
      double p = PositionGetDouble(POSITION_PRICE_OPEN);
      b.n++;
      b.dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      b.lots += v;
      sumPV += v * p;
      b.profit += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      long msc = PositionGetInteger(POSITION_TIME_MSC);
      if(msc >= lastMsc)
        {
         lastMsc = msc;
         b.lastPrice = p;
         b.lastLot = v;
        }
     }
   if(b.lots > 0.0)
      b.avg = sumPV / b.lots;
  }

//+------------------------------------------------------------------+
double NormLot(double lot)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0)
      step = 0.01;
   lot = MathRound(lot / step) * step;
   lot = MathMax(mn, MathMin(mx, lot));
   int digits = (int)MathMax(0.0, MathRound(-MathLog10(step)));
   return(NormalizeDouble(lot, digits));
  }

//+------------------------------------------------------------------+
bool FridayClose()
  {
   if(!InpTutupAkhirPekan)
      return(false);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return((dt.day_of_week == 5 && dt.hour >= InpJamTutupJumat) || dt.day_of_week == 6 || dt.day_of_week == 0);
  }

//+------------------------------------------------------------------+
bool WeekendBlock()
  {
   if(!InpTutupAkhirPekan)
      return(false);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return(FridayClose() || (dt.day_of_week == 1 && dt.hour < InpJamBukaSenin));
  }

//+------------------------------------------------------------------+
//| Berita USD penting (kalender MT5; tidak tersedia di tester)      |
//+------------------------------------------------------------------+
bool NewsBlock()
  {
   if(!InpJedaBerita || MQLInfoInteger(MQL_TESTER))
      return(false);
   datetime now = TimeCurrent();
   if(now - g_newsCheck < 300)
      return(g_newsBlock);
   g_newsCheck = now;
   g_newsBlock = false;
   MqlCalendarValue vals[];
   if(!CalendarValueHistory(vals, now - InpMenitSesudah * 60, now + InpMenitSebelum * 60, NULL, "USD"))
      return(false);
   for(int i = 0; i < ArraySize(vals); i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev))
         continue;
      if(ev.importance == CALENDAR_IMPORTANCE_HIGH)
        {
         g_newsBlock = true;
         break;
        }
     }
   return(g_newsBlock);
  }

//+------------------------------------------------------------------+
int CountMine()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk != 0 && IsMine())
         n++;
     }
   return(n);
  }

//+------------------------------------------------------------------+
void CloseAll(const string why)
  {
   for(int pass = 0; pass < 3; pass++)
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0 || !IsMine())
            continue;
         if(!trade.PositionClose(tk))
            PrintFormat("Gagal tutup #%I64u: %u %s", tk, trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
      if(CountMine() == 0)
         break;
      Sleep(300);
     }
   if(CountMine() == 0)
     {
      g_lastClose = TimeCurrent();
      GlobalVariableSet(g_gvName, (double)g_lastClose);
      PrintFormat("Keranjang ditutup (%s), saldo %.2f", why, AccountInfoDouble(ACCOUNT_BALANCE));
     }
  }

//+------------------------------------------------------------------+
bool OpenLayer(const int dir, const double lot, const string cmt)
  {
   ENUM_ORDER_TYPE type = (dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double price = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double margin = 0.0;
   if(!OrderCalcMargin(type, _Symbol, lot, price, margin))
      return(false);
   if(margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      PrintFormat("Margin tidak cukup untuk %s %.2f lot", cmt, lot);
      return(false);
     }
   bool ok = (dir > 0) ? trade.Buy(lot, _Symbol, 0.0, 0.0, 0.0, cmt)
                       : trade.Sell(lot, _Symbol, 0.0, 0.0, 0.0, cmt);
   if(!ok)
      PrintFormat("Gagal buka %s: %u %s", cmt, trade.ResultRetcode(), trade.ResultRetcodeDescription());
   return(ok);
  }

//+------------------------------------------------------------------+
int NewDir()
  {
   if(InpArah == ARAH_BUY)
      return(1);
   if(InpArah == ARAH_SELL)
      return(-1);
   return(iClose(_Symbol, PERIOD_M5, 1) >= iOpen(_Symbol, PERIOD_M5, 1) ? 1 : -1);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   Basket b;
   ReadBasket(b);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spread = ask - bid;
   double bal    = AccountInfoDouble(ACCOUNT_BALANCE);
   string info   = "";

   if(b.n > 0)
     {
      if(InpBatasRugiPersen > 0.0 && b.profit <= -bal * InpBatasRugiPersen / 100.0)
        {
         CloseAll("batas rugi");
         return;
        }
      if(FridayClose())
        {
         CloseAll("akhir pekan");
         return;
        }
      double tp = b.avg + b.dir * InpTP;
      if((b.dir > 0 && bid >= tp) || (b.dir < 0 && ask <= tp))
        {
         CloseAll("TP keranjang");
         return;
        }
      double next = b.lastPrice - b.dir * InpJarak;
      if(b.n < InpMaksLayer && spread <= InpMaksSpread &&
         ((b.dir > 0 && ask <= next) || (b.dir < 0 && bid >= next)))
         OpenLayer(b.dir, NormLot(b.lastLot * InpPengali), "L" + IntegerToString(b.n + 1));
      info = StringFormat("%s %d layer | %.2f lot | rata-rata %.3f | TP %.3f | layer berikut %.3f\n"
                          "Floating %.2f (%.1f%% saldo) | batas rugi %.0f%%",
                          b.dir > 0 ? "BUY" : "SELL", b.n, b.lots, b.avg, tp, next,
                          b.profit, bal > 0 ? 100.0 * b.profit / bal : 0.0, InpBatasRugiPersen);
     }
   else
     {
      bool wk = WeekendBlock();
      bool news = NewsBlock();
      long wait = (long)InpJedaMenit * 60 - (long)(TimeCurrent() - g_lastClose);
      if(wk)
         info = "Menunggu: akhir pekan";
      else if(news)
         info = "Menunggu: berita USD penting";
      else if(spread > InpMaksSpread)
         info = StringFormat("Menunggu: spread %.2f > %.2f", spread, InpMaksSpread);
      else if(wait > 0)
         info = StringFormat("Menunggu: jeda %d menit lagi", (int)(wait / 60) + 1);
      else
        {
         OpenLayer(NewDir(), NormLot(InpLotAwal), "L1");
         info = "Membuka layer 1";
        }
     }
   Comment("GridMartingale (uji demo dulu)\n", info, StringFormat("\nSaldo %.2f | Ekuitas %.2f",
           bal, AccountInfoDouble(ACCOUNT_EQUITY)));
  }
//+------------------------------------------------------------------+
