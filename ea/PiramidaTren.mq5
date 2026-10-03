//+------------------------------------------------------------------+
//| PiramidaTren.mq5                                                 |
//| Kebalikan martingale: tambah layer SEARAH tren, stop ikut naik.  |
//| Riset 3 Okt 2026 (research/piramida.py, docs/GRID_CARI.md):      |
//| positif di data lama & 5 tahun terakhir, tetapi kecil (risiko    |
//| 0,5%/keranjang: +$5–7/bulan per $400, drawdown 21–30%) dan menang |
//| hanya ±25% keranjang. Uji di akun DEMO dulu. Bukan janji profit. |
//+------------------------------------------------------------------+
#property copyright "serfusion/Trading - riset"
#property version   "1.00"
#property description "Arah = H4 close > EMA50 dan D1 close > EMA200 (BUY) atau keduanya di bawah (SELL)."
#property description "Layer baru tiap harga bergerak searah Jarak x ATR H1; stop semua layer = layer terakhir - Stop x ATR."
#property description "Keluar saat stop kena, tren tidak lagi searah, atau Jumat malam."

#include <Trade\Trade.mqh>

input group "Piramida"
input double InpRisikoPersen = 0.5;    // Risiko per keranjang (% saldo) di stop awal
input double InpJarakATR     = 3.0;    // Jarak layer berikut (x ATR H1)
input double InpStopATR      = 2.0;    // Stop dari layer terakhir (x ATR H1)
input int    InpMaksLayer    = 6;      // Maksimal layer
input double InpPengali      = 1.0;    // Pengali lot per layer (1 = sama)
input int    InpATRPeriode   = 14;     // Periode ATR H1

input group "Pengaman"
input bool   InpTutupAkhirPekan = true; // Tutup keranjang Jumat malam
input int    InpJamTutupJumat   = 20;   // Jam server Jumat (Exness = UTC)
input int    InpJamBukaSenin    = 1;    // Jam server Senin mulai boleh buka
input double InpMaksSpread      = 0.50; // Maksimal spread (USD)

input group "Lain-lain"
input ulong  InpMagic    = 7712027;     // Magic number
input int    InpSlippage = 30;          // Deviasi (points)

CTrade trade;
int    hEmaH4 = INVALID_HANDLE, hEmaD1 = INVALID_HANDLE, hAtr = INVALID_HANDLE;
string gvStep, gvStopD;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpRisikoPersen <= 0.0 || InpJarakATR <= 0.0 || InpStopATR <= 0.0 || InpMaksLayer < 1 || InpPengali <= 0.0)
      return(INIT_PARAMETERS_INCORRECT);
   hEmaH4 = iMA(_Symbol, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE);
   hEmaD1 = iMA(_Symbol, PERIOD_D1, 200, 0, MODE_EMA, PRICE_CLOSE);
   hAtr   = iATR(_Symbol, PERIOD_H1, InpATRPeriode);
   if(hEmaH4 == INVALID_HANDLE || hEmaD1 == INVALID_HANDLE || hAtr == INVALID_HANDLE)
      return(INIT_FAILED);
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   gvStep  = "PT_step_" + IntegerToString((long)InpMagic) + "_" + _Symbol;
   gvStopD = "PT_stopd_" + IntegerToString((long)InpMagic) + "_" + _Symbol;
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(hEmaH4);
   IndicatorRelease(hEmaD1);
   IndicatorRelease(hAtr);
   Comment("");
  }

//+------------------------------------------------------------------+
double Buf(const int handle, const int shift)
  {
   double v[1];
   if(CopyBuffer(handle, 0, shift, 1, v) != 1)
      return(EMPTY_VALUE);
   return(v[0]);
  }

//+------------------------------------------------------------------+
//| +1 BUY, -1 SELL, 0 tidak searah (bar yang sudah selesai)         |
//+------------------------------------------------------------------+
int Arah()
  {
   double e4 = Buf(hEmaH4, 1), e1 = Buf(hEmaD1, 1);
   if(e4 == EMPTY_VALUE || e1 == EMPTY_VALUE)
      return(0);
   double c4 = iClose(_Symbol, PERIOD_H4, 1), c1 = iClose(_Symbol, PERIOD_D1, 1);
   if(c4 > e4 && c1 > e1)
      return(1);
   if(c4 < e4 && c1 < e1)
      return(-1);
   return(0);
  }

//+------------------------------------------------------------------+
bool IsMine()
  {
   return(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic);
  }

//+------------------------------------------------------------------+
struct Keranjang
  {
   int    n;
   int    dir;
   double lastPrice;
   double lot0;
   double stop;
   double profit;
  };

void Baca(Keranjang &k)
  {
   k.n = 0;
   k.dir = 0;
   k.lastPrice = 0.0;
   k.lot0 = 0.0;
   k.stop = 0.0;
   k.profit = 0.0;
   long first = LONG_MAX, last = -1;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMine())
         continue;
      long msc = PositionGetInteger(POSITION_TIME_MSC);
      k.n++;
      k.dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      k.profit += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double sl = PositionGetDouble(POSITION_SL);
      if(sl > 0.0)
         k.stop = (k.stop == 0.0) ? sl : ((k.dir > 0) ? MathMax(k.stop, sl) : MathMin(k.stop, sl));
      if(msc < first)
        {
         first = msc;
         k.lot0 = PositionGetDouble(POSITION_VOLUME);
        }
      if(msc > last)
        {
         last = msc;
         k.lastPrice = PositionGetDouble(POSITION_PRICE_OPEN);
        }
     }
  }

//+------------------------------------------------------------------+
double NormLot(double lot)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0)
      step = 0.01;
   lot = MathFloor(lot / step) * step;
   lot = MathMax(mn, MathMin(mx, lot));
   return(NormalizeDouble(lot, (int)MathMax(0.0, MathRound(-MathLog10(step)))));
  }

//+------------------------------------------------------------------+
bool AkhirPekan(const bool untukBuka)
  {
   if(!InpTutupAkhirPekan)
      return(false);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool tutup = (dt.day_of_week == 5 && dt.hour >= InpJamTutupJumat) || dt.day_of_week == 6 || dt.day_of_week == 0;
   return(tutup || (untukBuka && dt.day_of_week == 1 && dt.hour < InpJamBukaSenin));
  }

//+------------------------------------------------------------------+
void TutupSemua(const string why)
  {
   for(int pass = 0; pass < 3; pass++)
     {
      int sisa = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0 || !IsMine())
            continue;
         if(!trade.PositionClose(tk))
            sisa++;
        }
      if(sisa == 0)
         break;
      Sleep(300);
     }
   PrintFormat("Keranjang ditutup (%s), saldo %.2f", why, AccountInfoDouble(ACCOUNT_BALANCE));
  }

//+------------------------------------------------------------------+
void PasangStop(const double stop)
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double s = NormalizeDouble(stop, digits);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !IsMine())
         continue;
      if(MathAbs(PositionGetDouble(POSITION_SL) - s) > SymbolInfoDouble(_Symbol, SYMBOL_POINT))
         if(!trade.PositionModify(tk, s, 0.0))
            PrintFormat("Gagal pasang stop #%I64u: %u", tk, trade.ResultRetcode());
     }
  }

//+------------------------------------------------------------------+
bool Buka(const int dir, const double lot, const string cmt)
  {
   bool ok = (dir > 0) ? trade.Buy(lot, _Symbol, 0.0, 0.0, 0.0, cmt) : trade.Sell(lot, _Symbol, 0.0, 0.0, 0.0, cmt);
   if(!ok)
      PrintFormat("Gagal buka %s: %u %s", cmt, trade.ResultRetcode(), trade.ResultRetcodeDescription());
   return(ok);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spread = ask - bid;
   int arah = Arah();
   Keranjang k;
   Baca(k);
   string info;

   if(k.n > 0)
     {
      if(AkhirPekan(false) || arah != k.dir)
        {
         TutupSemua(arah != k.dir ? "tren tidak searah" : "akhir pekan");
         return;
        }
      double step = GlobalVariableCheck(gvStep) ? GlobalVariableGet(gvStep) : InpJarakATR * Buf(hAtr, 1);
      double sld  = GlobalVariableCheck(gvStopD) ? GlobalVariableGet(gvStopD) : InpStopATR * Buf(hAtr, 1);
      double next = k.lastPrice + k.dir * step;
      if(k.n < InpMaksLayer && spread <= InpMaksSpread && ((k.dir > 0 && ask >= next) || (k.dir < 0 && bid <= next)))
        {
         double lot = NormLot(k.lot0 * MathPow(InpPengali, k.n));
         if(Buka(k.dir, lot, "P" + IntegerToString(k.n + 1)))
           {
            double px = (k.dir > 0) ? ask : bid;
            double ns = px - k.dir * sld;
            k.stop = (k.dir > 0) ? MathMax(k.stop, ns) : MathMin(k.stop, ns);
           }
        }
      if(k.stop > 0.0)
         PasangStop(k.stop);
      info = StringFormat("%s %d layer | stop %.3f | layer berikut %.3f | floating %.2f", k.dir > 0 ? "BUY" : "SELL", k.n,
                          k.stop, next, k.profit);
     }
   else
     {
      if(arah == 0)
         info = "Menunggu: H4 & D1 belum searah";
      else if(AkhirPekan(true))
         info = "Menunggu: akhir pekan";
      else if(spread > InpMaksSpread)
         info = StringFormat("Menunggu: spread %.2f", spread);
      else
        {
         double atr = Buf(hAtr, 1);
         if(atr == EMPTY_VALUE || atr <= 0.0)
            return;
         double step = InpJarakATR * atr, sld = InpStopATR * atr;
         double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
         double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
         if(tickVal <= 0.0 || tickSize <= 0.0)
            return;
         double perLot = (sld + spread) * tickVal / tickSize;           // rugi per 1 lot di stop awal
         double lot = NormLot(AccountInfoDouble(ACCOUNT_BALANCE) * InpRisikoPersen / 100.0 / perLot);
         if(lot * perLot > AccountInfoDouble(ACCOUNT_BALANCE) * InpRisikoPersen / 100.0 * 1.5)
            PrintFormat("Peringatan: lot minimum %.2f = risiko %.2f (lebih dari %.1f%% saldo)", lot, lot * perLot, InpRisikoPersen);
         if(Buka(arah, lot, "P1"))
           {
            GlobalVariableSet(gvStep, step);
            GlobalVariableSet(gvStopD, sld);
            double px = (arah > 0) ? ask : bid;
            PasangStop(px - arah * sld);
           }
         info = "Membuka layer 1";
        }
     }
   Comment("PiramidaTren (uji demo dulu)\n", info, StringFormat("\nSaldo %.2f | Ekuitas %.2f", AccountInfoDouble(ACCOUNT_BALANCE),
           AccountInfoDouble(ACCOUNT_EQUITY)));
  }
//+------------------------------------------------------------------+
