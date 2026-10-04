//+------------------------------------------------------------------+
//| SinyalCloud.mq5                                                  |
//| Mengeksekusi sinyal 💰 cloud proyek (XAU/BTC/ETH) di MT5 — sinyal |
//| SAMA dengan aplikasi, dibaca dari topik ntfy "<topik>-data".      |
//| + BRANKAS: pengingat tarik profit & setor ulang (tarik-setor).    |
//| Riset 4 Okt 2026 (research/tarik_setor.py, docs/TARIK_SETOR.md):  |
//| tarik-setor TIDAK menciptakan profit; profit hanya dari sinyal    |
//| yang punya keunggulan (💰 sejak Okt 2021 +0,21R XAU / +0,27R BTC). |
//| Uji di akun DEMO dulu. Bukan janji profit.                        |
//+------------------------------------------------------------------+
#property copyright "serfusion/Trading - riset"
#property version   "1.00"
#property description "Baca sinyal 💰 dari ntfy (topik aplikasi + \"-data\"), buka posisi dengan risiko tetap % modal dasar."
#property description "Posisi #1 TP1 0,7R, sisanya tahan; SL+ ke entry setelah 0,7R; tutup saat sinyal TUTUP / channel tembus."
#property description "Wajib: Tools > Options > Expert Advisors > Allow WebRequest for listed URL: https://ntfy.sh"

#include <Trade\Trade.mqh>

input group "Sumber sinyal (cloud)"
input string InpTopik         = "";                // Topik ntfy (sama dengan di aplikasi, TANPA "-data")
input string InpServer        = "https://ntfy.sh"; // Server ntfy
input int    InpCekDetik      = 20;                // Cek sinyal tiap N detik
input int    InpUmurMaksMenit = 20;                // Sinyal lebih tua dari ini tidak dibuka

input group "Pasar (simbol kosong = cari otomatis XAUUSD / XAUUSDm / XAUUSDc ...)"
input bool   InpIkutXAU     = true;   // Ikuti sinyal XAU
input string InpSimbolXAU   = "";
input bool   InpIkutBTC     = true;   // Ikuti sinyal BTC
input string InpSimbolBTC   = "";
input bool   InpIkutETH     = false;  // Ikuti sinyal ETH
input string InpSimbolETH   = "";
input bool   InpIkutLapisan = true;   // Ikuti sinyal 🔁 lapisan (lot ½)

input group "Risiko"
input double InpRisikoPersen   = 1.0;  // Risiko per sinyal (% modal dasar, semua posisi di SL)
input int    InpLeg            = 5;    // Posisi per sinyal (dikurangi otomatis bila lot terlalu kecil)
input double InpMaksSinyal     = 10;   // Maks sinyal berisiko terbuka bersamaan (lapisan = ½; 0 = tanpa batas)
input double InpGeserMaksR     = 0.5;  // Lewati bila harga broker sudah lari > X R dari entry sinyal
input bool   InpBolehLotMin    = false;// Lot hitungan < lot minimum: true = pakai lot minimum (risiko > rencana)
input double InpSLPlusOffset   = 0.10; // SL+ = harga buka ± ini (satuan harga, sama dengan cloud)
input bool   InpKeluarLokal    = true; // Cadangan: tutup sendiri bila close H1 menembus channel keluar set

input group "Brankas (tarik-setor)"
input double InpModalDasar       = 0;    // Modal dasar dalam $ (0 = saldo saat EA pertama dipasang)
input double InpTarikDiAtasPersen = 25;  // Ingatkan tarik bila saldo >= modal dasar + X%
input double InpBatasEkuitasPersen = 0;  // Tutup semua & berhenti bila ekuitas < X% modal dasar (0 = mati)
input bool   InpNotifHP          = true; // Notifikasi ke MetaTrader HP (isi MetaQuotes ID di Options > Notifications)

input group "Lain-lain"
input ulong  InpMagic    = 260410;       // Magic number (beda dengan auto order cloud 250936+)
input int    InpDeviasi  = 50;           // Deviasi harga (points)

CTrade   trade;
string   gSym[3];
bool     gIkut[3];
datetime gBarH1[3];
double   gKurs = 1.0;          // 100 untuk akun Cent (USC): uang akun / gKurs = $
double   gModal = 0.0;         // modal dasar (mata uang akun)
long     gSince = 0;           // waktu (unix) pesan ntfy terakhir
string   gIdDetik[];           // id pesan ntfy pada detik gSince (cegah dobel)
long     gHB = 0;              // heartbeat cloud terakhir (unix)
bool     gBerhenti = false;
string   gStatus = "mulai", gLog = "";
long     gNotifTarik = 0, gNotifHabis = 0, gNotifHB = 0, gBrankasT = 0;
double   gSetor = 0.0, gTarik = 0.0;

//+------------------------------------------------------------------+
string Pfx() { return "SC" + IntegerToString((long)InpMagic) + "_"; }

//+------------------------------------------------------------------+
void Catat(const string s)
  {
   Print(s);
   gLog = TimeToString(TimeCurrent(), TIME_MINUTES) + " " + s;
  }

//+------------------------------------------------------------------+
void Kabari(const string s)
  {
   Catat(s);
   if(InpNotifHP)
      SendNotification(StringSubstr(s, 0, 250));
  }

//+------------------------------------------------------------------+
string Usd(const double v) { return "$" + DoubleToString(v / gKurs, 2); }

//+------------------------------------------------------------------+
string CariSimbol(const string isian, const string dasar)
  {
   if(isian != "")
     {
      if(SymbolSelect(isian, true))
         return(isian);
      Catat("Simbol " + isian + " tidak ada di akun ini");
      return("");
     }
   string akhiran[] = {"", "m", "c", ".", "#", "z", "-ECN"};
   for(int i = 0; i < ArraySize(akhiran); i++)
     {
      string s = dasar + "USD" + akhiran[i];
      if(SymbolSelect(s, true))
         return(s);
     }
   return("");
  }

//+------------------------------------------------------------------+
//| JSON mini (cukup untuk pesan ntfy & event cloud)                  |
//+------------------------------------------------------------------+
int JPos(const string &s, const string key)
  {
   int p = StringFind(s, "\"" + key + "\":");
   if(p < 0)
      return(-1);
   p += StringLen(key) + 3;
   int n = StringLen(s);
   while(p < n)
     {
      ushort c = StringGetCharacter(s, p);
      if(c != ' ' && c != '\t')
         break;
      p++;
     }
   return(p);
  }

int Hex4(const string h)
  {
   int v = 0;
   for(int i = 0; i < StringLen(h); i++)
     {
      ushort c = StringGetCharacter(h, i);
      v *= 16;
      if(c >= '0' && c <= '9')
         v += c - '0';
      else
         if(c >= 'a' && c <= 'f')
            v += c - 'a' + 10;
         else
            if(c >= 'A' && c <= 'F')
               v += c - 'A' + 10;
     }
   return(v);
  }

string JStr(const string &s, const string key)
  {
   int p = JPos(s, key);
   if(p < 0 || StringGetCharacter(s, p) != '"')
      return("");
   string out = "";
   int n = StringLen(s);
   for(int i = p + 1; i < n; i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c == '"')
         break;
      if(c == '\\' && i + 1 < n)
        {
         i++;
         ushort e = StringGetCharacter(s, i);
         if(e == 'n')
            out += "\n";
         else
            if(e == 't')
               out += "\t";
            else
               if(e == 'r')
                  continue;
               else
                  if(e == 'u' && i + 4 < n)
                    {
                     out += ShortToString((ushort)Hex4(StringSubstr(s, i + 1, 4)));
                     i += 4;
                    }
                  else
                     out += ShortToString(e);       // \"  \\  \/
         continue;
        }
      out += ShortToString(c);
     }
   return(out);
  }

double JNum(const string &s, const string key)
  {
   int p = JPos(s, key);
   if(p < 0)
      return(0.0);
   int q = p, n = StringLen(s);
   while(q < n)
     {
      ushort c = StringGetCharacter(s, q);
      if((c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E')
         q++;
      else
         break;
     }
   return(StringToDouble(StringSubstr(s, p, q - p)));
  }

bool JBool(const string &s, const string key)
  {
   int p = JPos(s, key);
   return(p >= 0 && StringSubstr(s, p, 4) == "true");
  }

//+------------------------------------------------------------------+
int Aset(const string simbol)
  {
   if(simbol == "XAU/USD")
      return(0);
   if(simbol == "BTC/USD")
      return(1);
   if(simbol == "ETH/USD")
      return(2);
   return(-1);
  }

//+------------------------------------------------------------------+
//| Posisi milik EA                                                   |
//+------------------------------------------------------------------+
bool Milik(const ulong tk)
  {
   return(tk != 0 && PositionSelectByTicket(tk) && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic);
  }

double NilaiPerHarga(const string s)
  {
   double ts = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE);
   return(ts > 0.0 ? SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE) / ts : 0.0);   // uang akun per 1,0 harga per lot
  }

int PosisiId(const string id)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(Milik(tk) && PositionGetString(POSITION_COMMENT) == id)
         n++;
     }
   return(n);
  }

double RisikoTerbuka()
  {
   double tot = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(!Milik(tk))
         continue;
      double op = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      if(sl > 0.0 && ((buy && sl < op) || (!buy && sl > op)))
         tot += MathAbs(op - sl) * PositionGetDouble(POSITION_VOLUME) * NilaiPerHarga(PositionGetString(POSITION_SYMBOL));
     }
   return(tot);
  }

void TutupId(const string id, const string alasan)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(Milik(tk) && PositionGetString(POSITION_COMMENT) == id && trade.PositionClose(tk))
         n++;
     }
   if(n > 0)
      Catat("TUTUP " + id + " (" + IntegerToString(n) + " posisi): " + alasan);
  }

double NormLot(const string s, const double v)
  {
   double st = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);
   if(st <= 0.0)
      st = 0.01;
   double x = MathFloor(v / st + 1e-9) * st;
   return(MathMin(x, SymbolInfoDouble(s, SYMBOL_VOLUME_MAX)));
  }

//+------------------------------------------------------------------+
//| Buka sinyal                                                       |
//+------------------------------------------------------------------+
void Buka(const int a, const string id, const bool buy, const double entry, const double tp1, const double rp,
          const double mult)
  {
   string s = gSym[a];
   double px = buy ? SymbolInfoDouble(s, SYMBOL_ASK) : SymbolInfoDouble(s, SYMBOL_BID);
   if(px <= 0.0 || rp <= 0.0)
      return;
   double lari = buy ? px - entry : entry - px;             // + = harga sudah lari searah sinyal
   if(lari > InpGeserMaksR * rp)
     {
      Catat("Lewati " + id + ": harga broker sudah " + DoubleToString(lari / rp, 2) + "R dari entry sinyal");
      return;
     }
   if(lari < -rp)
     {
      Catat("Lewati " + id + ": harga broker sudah melewati SL sinyal");
      return;
     }
   double vpp = NilaiPerHarga(s);
   if(vpp <= 0.0)
      return;
   double satu = gModal * InpRisikoPersen / 100.0;          // risiko 1 sinyal penuh (uang akun)
   double total = satu * mult / (rp * vpp);                 // lot total sinyal ini
   double vmin = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
   int legs = InpLeg < 1 ? 1 : InpLeg;
   double per = NormLot(s, total / legs);
   while(legs > 1 && per < vmin)
     {
      legs--;
      per = NormLot(s, total / legs);
     }
   if(per < vmin)
     {
      if(!InpBolehLotMin)
        {
         Catat("Lewati " + id + ": lot " + DoubleToString(total, 4) + " < minimum " + DoubleToString(vmin, 2) +
               " (pakai akun Cent, naikkan modal, atau InpBolehLotMin)");
         return;
        }
      per = vmin;
      legs = 1;
     }
   double baru = per * legs * rp * vpp;
   if(InpMaksSinyal > 0 && RisikoTerbuka() + baru > InpMaksSinyal * satu * 1.0001)
     {
      Catat("Lewati " + id + ": batas " + DoubleToString(InpMaksSinyal, 1) + " sinyal berisiko terbuka");
      return;
     }
   double marg = 0.0;
   if(!OrderCalcMargin(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, s, per * legs, px, marg) ||
      marg > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      Catat("Lewati " + id + ": margin kurang");
      return;
     }
   int dg = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
   double jarakTP = MathAbs(tp1 - entry);
   if(jarakTP <= 0.0)
      jarakTP = 0.7 * rp;
   // jarak SL/TP sama dengan sinyal, diukur dari harga broker (feed cloud & broker bisa beda beberapa sen)
   double sl = NormalizeDouble(buy ? px - rp : px + rp, dg);
   double tp = NormalizeDouble(buy ? px + jarakTP : px - jarakTP, dg);
   trade.SetTypeFillingBySymbol(s);
   int ok = 0;
   for(int i = 0; i < legs; i++)
     {
      double t = (i == 0 && legs >= 2) ? tp : 0.0;          // seperti cloud: TP1 hanya bila >= 2 posisi
      bool r = buy ? trade.Buy(per, s, 0.0, sl, t, id) : trade.Sell(per, s, 0.0, sl, t, id);
      if(!r)
        {
         Catat("Order " + id + " #" + IntegerToString(i + 1) + " gagal: " + trade.ResultRetcodeDescription());
         break;
        }
      ok++;
     }
   if(ok > 0)
      Kabari("🤖 " + (buy ? "BUY " : "SELL ") + s + " " + IntegerToString(ok) + "x" + DoubleToString(per, 2) +
             " lot @" + DoubleToString(px, dg) + " SL " + DoubleToString(sl, dg) + " [" + id + "] risiko " +
             Usd(per * ok * rp * vpp));
  }

//+------------------------------------------------------------------+
//| Satu event cloud                                                  |
//+------------------------------------------------------------------+
void Proses(const string &m, const long t)
  {
   string tipe = JStr(m, "type");
   if(tipe == "heartbeat")
     {
      if(t > gHB)
         gHB = t;
      return;
     }
   string id = JStr(m, "id");
   if(id == "")
      return;
   if(tipe == "close")
     {
      TutupId(id, "cloud: " + JStr(m, "reason"));
      return;
     }
   if(tipe == "info")
     {
      if(JStr(m, "kind") == "tp1")
         SLPlus(id);
      return;
     }
   if(tipe != "signal" || JStr(m, "mode") != "trend")
      return;
   int a = Aset(JStr(m, "symbol"));
   if(a < 0 || !gIkut[a] || gSym[a] == "")
      return;
   string gv = Pfx() + id;
   if(GlobalVariableCheck(gv) || PosisiId(id) > 0)
      return;                                               // sudah diproses (juga setelah EA restart)
   GlobalVariableSet(gv, (double)t);
   bool lapis = JBool(m, "lapis");
   if(lapis && !InpIkutLapisan)
      return;
   if(gBerhenti)
     {
      Catat("Lewati " + id + ": EA berhenti (batas ekuitas)");
      return;
     }
   long umur = (long)TimeGMT() - t;
   if(umur > InpUmurMaksMenit * 60)
     {
      Catat("Lewati " + id + ": sinyal sudah " + IntegerToString(umur / 60) + " menit");
      return;
     }
   double mult = 1.0;
   if(lapis)
     {
      mult = JNum(m, "lot_mult");
      if(mult <= 0.0)
         mult = 0.5;
     }
   Buka(a, id, JStr(m, "dir") == "BUY", JNum(m, "entry"), JNum(m, "tp1"), JNum(m, "risk_points"), mult);
  }

//+------------------------------------------------------------------+
//| Ambil pesan baru dari ntfy                                        |
//+------------------------------------------------------------------+
bool SudahDetik(const string nid)
  {
   for(int i = 0; i < ArraySize(gIdDetik); i++)
      if(gIdDetik[i] == nid)
         return(true);
   return(false);
  }

void Ambil()
  {
   string url = InpServer + "/" + InpTopik + "-data/json?poll=1&since=" + IntegerToString(gSince);
   char kirim[], hasil[];
   string hdr;
   ResetLastError();
   int code = WebRequest("GET", url, "", 15000, kirim, hasil, hdr);
   if(code != 200)
     {
      int err = GetLastError();
      gStatus = (code == -1 && err == 4014) ? "IZINKAN URL " + InpServer + " di Tools > Options > Expert Advisors"
                : "gagal ambil sinyal (HTTP " + IntegerToString(code) + ", galat " + IntegerToString(err) + ")";
      return;
     }
   gStatus = "OK " + TimeToString(TimeCurrent(), TIME_MINUTES | TIME_SECONDS);
   string body = CharArrayToString(hasil, 0, WHOLE_ARRAY, CP_UTF8);
   string baris[];
   int n = StringSplit(body, '\n', baris);
   for(int i = 0; i < n; i++)
     {
      if(StringFind(baris[i], "\"event\":\"message\"") < 0)
         continue;
      long t = (long)JNum(baris[i], "time");
      string nid = JStr(baris[i], "id");
      if(t < gSince || (t == gSince && SudahDetik(nid)))
         continue;
      if(t > gSince)
        {
         gSince = t;
         ArrayResize(gIdDetik, 0);
        }
      int k = ArraySize(gIdDetik);
      ArrayResize(gIdDetik, k + 1);
      gIdDetik[k] = nid;
      string m = JStr(baris[i], "message");
      Proses(m, t);
     }
   GlobalVariableSet(Pfx() + "since", (double)gSince);
  }

//+------------------------------------------------------------------+
//| Kelola posisi: SL+ setelah 0,7R, cadangan keluar channel          |
//+------------------------------------------------------------------+
void SLPlus(const string hanyaId)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(!Milik(tk) || PositionGetDouble(POSITION_TP) > 0.0)
         continue;                                          // posisi #1 (ber-TP) ditutup broker di TP1
      string id = PositionGetString(POSITION_COMMENT);
      if(hanyaId != "" && id != hanyaId)
         continue;
      string s = PositionGetString(POSITION_SYMBOL);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double op = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
      if(sl <= 0.0 || (buy && sl >= op) || (!buy && sl <= op))
         continue;                                          // SL+ sudah terpasang
      double r = MathAbs(op - sl);
      double bid = SymbolInfoDouble(s, SYMBOL_BID), ask = SymbolInfoDouble(s, SYMBOL_ASK);
      bool kena = buy ? bid >= op + 0.7 * r : ask <= op - 0.7 * r;
      if(!kena && hanyaId == "")
         continue;
      int dg = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
      double stop = SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(s, SYMBOL_POINT);
      double baru = NormalizeDouble(buy ? op + InpSLPlusOffset : op - InpSLPlusOffset, dg);
      if((buy && baru < bid - stop) || (!buy && baru > ask + stop))
         if(trade.PositionModify(tk, baru, 0.0))
            Catat("SL+ " + id + " -> " + DoubleToString(baru, dg));
     }
  }

int KeluarN(const string id)
  {
   int p = StringFind(id, "/");
   if(p < 0)
      return(0);
   int q = StringFind(id, "-", p);
   return(q < 0 ? 0 : (int)StringToInteger(StringSubstr(id, p + 1, q - p - 1)));
  }

void KeluarLokal(const int a)
  {
   string s = gSym[a];
   if(s == "")
      return;
   datetime t0 = iTime(s, PERIOD_H1, 0);
   if(t0 == 0 || t0 == gBarH1[a])
      return;
   gBarH1[a] = t0;
   double c1 = iClose(s, PERIOD_H1, 1);
   string tutup[];
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(!Milik(tk) || PositionGetString(POSITION_SYMBOL) != s)
         continue;
      string id = PositionGetString(POSITION_COMMENT);
      int n = KeluarN(id);
      if(n <= 0)
         continue;
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      int k = buy ? iLowest(s, PERIOD_H1, MODE_LOW, n, 2) : iHighest(s, PERIOD_H1, MODE_HIGH, n, 2);
      if(k < 0)
         continue;
      if((buy && c1 < iLow(s, PERIOD_H1, k)) || (!buy && c1 > iHigh(s, PERIOD_H1, k)))
        {
         int j = ArraySize(tutup);
         ArrayResize(tutup, j + 1);
         tutup[j] = id;
        }
     }
   for(int j = 0; j < ArraySize(tutup); j++)
      TutupId(tutup[j], "lokal: close H1 menembus channel " + IntegerToString(KeluarN(tutup[j])));
  }

//+------------------------------------------------------------------+
//| Brankas: setoran/tarikan dari riwayat akun + pengingat            |
//+------------------------------------------------------------------+
void HitungBrankas()
  {
   gSetor = 0.0;
   gTarik = 0.0;
   if(!HistorySelect(0, TimeCurrent()))
      return;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetInteger(d, DEAL_TYPE) != DEAL_TYPE_BALANCE)
         continue;
      double p = HistoryDealGetDouble(d, DEAL_PROFIT);
      if(p > 0.0)
         gSetor += p;
      else
         gTarik -= p;
     }
  }

void Brankas()
  {
   long now = (long)TimeGMT();
   if(now - gBrankasT >= 300)
     {
      HitungBrankas();
      gBrankasT = now;
     }
   double bal = AccountInfoDouble(ACCOUNT_BALANCE), eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpBatasEkuitasPersen > 0.0 && !gBerhenti && eq < gModal * InpBatasEkuitasPersen / 100.0)
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(Milik(tk))
            trade.PositionClose(tk);
        }
      gBerhenti = true;
      Kabari("⛔ Ekuitas " + Usd(eq) + " < " + DoubleToString(InpBatasEkuitasPersen, 0) +
             "% modal dasar: semua posisi EA ditutup, EA berhenti membuka sinyal (pasang ulang EA untuk lanjut).");
     }
   if(InpTarikDiAtasPersen > 0.0 && bal >= gModal * (1.0 + InpTarikDiAtasPersen / 100.0) && now - gNotifTarik > 86400)
     {
      gNotifTarik = now;
      Kabari("💰 Saldo " + Usd(bal) + " sudah >= modal dasar " + Usd(gModal) + " + " + DoubleToString(InpTarikDiAtasPersen, 0) +
             "%. Tarik " + Usd(bal - gModal) + " lewat Personal Area Exness (sisakan modal dasar; cek margin bila ada posisi). "
             + "Total ditarik sejauh ini " + Usd(gTarik) + ".");
     }
   double satu = gModal * InpRisikoPersen / 100.0;
   if(eq < satu && now - gNotifHabis > 86400)
     {
      gNotifHabis = now;
      Kabari("⚠️ Akun hampir habis (ekuitas " + Usd(eq) + "). Rencana tarik-setor: setor ulang modal dasar " + Usd(gModal) +
             " HANYA dari uang tarikan (sudah ditarik " + Usd(gTarik) + ", disetor " + Usd(gSetor) +
             "). Bila tarikan sudah habis, berhenti: strategi sedang rugi.");
     }
  }

//+------------------------------------------------------------------+
void Panel()
  {
   long now = (long)TimeGMT();
   string hb = gHB > 0 ? IntegerToString((now - gHB) / 60) + " menit lalu" : "belum ada";
   MqlDateTime w;
   TimeToStruct(TimeGMT(), w);
   bool pasarBuka = w.day_of_week >= 1 && w.day_of_week <= 5;
   if(gHB > 0 && pasarBuka && now - gHB > 7200 && now - gNotifHB > 21600)
     {
      gNotifHB = now;
      Kabari("⚠️ Cloud tidak mengirim heartbeat " + hb + ": cek Vercel/cron. Posisi tetap dijaga SL & keluar lokal.");
     }
   int npos = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(Milik(PositionGetTicket(i)))
         npos++;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   string sym = "";
   string nama[3] = {"XAU", "BTC", "ETH"};
   for(int a = 0; a < 3; a++)
      if(gIkut[a])
         sym += nama[a] + "=" + (gSym[a] == "" ? "TIDAK ADA" : gSym[a]) + "  ";
   Comment("SinyalCloud v1.00 — bukan jaminan profit, uji di DEMO dulu\n",
           "Sumber: ", gStatus, " | heartbeat cloud: ", hb, "\n",
           "Pasar: ", sym, "\n",
           "Risiko/sinyal: ", DoubleToString(InpRisikoPersen, 2), "% = ", Usd(gModal * InpRisikoPersen / 100.0),
           " | posisi EA: ", npos, " | risiko terbuka: ", Usd(RisikoTerbuka()), (gBerhenti ? " | BERHENTI" : ""), "\n",
           "BRANKAS: modal dasar ", Usd(gModal), " | saldo ", Usd(AccountInfoDouble(ACCOUNT_BALANCE)), " | ekuitas ", Usd(eq), "\n",
           "  disetor ", Usd(gSetor), " | ditarik ", Usd(gTarik), " | dompet bersih (ditarik - disetor + ekuitas) ",
           Usd(gTarik - gSetor + eq), "\n",
           "Terakhir: ", gLog);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringLen(InpTopik) < 4 || InpRisikoPersen <= 0.0)
     {
      Alert("SinyalCloud: isi InpTopik (topik ntfy dari aplikasi) dan risiko > 0");
      return(INIT_PARAMETERS_INCORRECT);
     }
   string cur = AccountInfoString(ACCOUNT_CURRENCY);
   gKurs = (cur == "USC" || cur == "USc") ? 100.0 : 1.0;
   string gm = Pfx() + "modal";
   if(InpModalDasar > 0.0)
      gModal = InpModalDasar * gKurs;
   else
      gModal = GlobalVariableCheck(gm) ? GlobalVariableGet(gm) : AccountInfoDouble(ACCOUNT_BALANCE);
   GlobalVariableSet(gm, gModal);
   gIkut[0] = InpIkutXAU;
   gIkut[1] = InpIkutBTC;
   gIkut[2] = InpIkutETH;
   gSym[0] = InpIkutXAU ? CariSimbol(InpSimbolXAU, "XAU") : "";
   gSym[1] = InpIkutBTC ? CariSimbol(InpSimbolBTC, "BTC") : "";
   gSym[2] = InpIkutETH ? CariSimbol(InpSimbolETH, "ETH") : "";
   for(int a = 0; a < 3; a++)
      gBarH1[a] = 0;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviasi);
   long now = (long)TimeGMT();
   string gs = Pfx() + "since";
   gSince = GlobalVariableCheck(gs) ? (long)GlobalVariableGet(gs) : now - InpUmurMaksMenit * 60;
   if(gSince < now - 12 * 3600)
      gSince = now - 12 * 3600;                             // ntfy menyimpan pesan ±12 jam
   HitungBrankas();
   EventSetTimer(InpCekDetik < 5 ? 5 : InpCekDetik);
   Catat("SinyalCloud aktif: modal dasar " + Usd(gModal) + ", risiko " + DoubleToString(InpRisikoPersen, 2) + "%/sinyal");
   OnTimer();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Ambil();
   SLPlus("");
   if(InpKeluarLokal)
      for(int a = 0; a < 3; a++)
         if(gIkut[a])
            KeluarLokal(a);
   Brankas();
   Panel();
  }

//+------------------------------------------------------------------+
void OnTick()
  {
  }
//+------------------------------------------------------------------+
