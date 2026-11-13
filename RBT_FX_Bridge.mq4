//+------------------------------------------------------------------+
//|                                                RBT_FX_Bridge.mq4 |
//|        RBT FX - JEMBATAN MT4 <-> PYTHON (file bridge, tanpa DLL) |
//|  Pasang di 1 chart APA SAJA + tombol AutoTrading ON.             |
//|  Detail lengkap: MT4_SETUP.md di folder program.                 |
//+------------------------------------------------------------------+
#property copyright "RBT FX - TRADING ALGO SYSTEM"
#property link      "https://github.com/ributprasetyoaji"
#property version   "1.00"
#property strict

// --- buffer tick utk QUOTE cepat (tidak wajib) ---
double G_LASTBID[64];
string G_SYMS[64];
int    G_NSYM = 0;

int OnInit()
  {
   EventSetMillisecondTimer(250);
   Comment("RBT FX BRIDGE AKTIF - jangan tutup chart ini");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

void OnTimer()
  {
   ProcessAll();
  }

int TFMinutes(string tf)
  {
   if(tf == "M1")  return(PERIOD_M1);
   if(tf == "M5")  return(PERIOD_M5);
   if(tf == "M15") return(PERIOD_M15);
   if(tf == "M30") return(PERIOD_M30);
   if(tf == "H1")  return(PERIOD_H1);
   if(tf == "H4")  return(PERIOD_H4);
   if(tf == "D1")  return(PERIOD_D1);
   return(0);
  }

void Respond(string suffix, string cid, string status, string payload)
  {
   string name = "rbtfx_resp_" + suffix + ".txt";
   int fh = FileOpen(name, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|
                     FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(fh == INVALID_HANDLE) return;
   FileSeek(fh, 0, SEEK_END);
   FileWrite(fh, cid + "|" + status + "|" + payload);
   FileClose(fh);
  }

void ProcessAll()
  {
   string fname;
   long handle = FileFindFirst("rbtfx_cmd_*.txt", fname, FILE_COMMON);
   if(handle == INVALID_HANDLE) return;
   do
     {
      ProcessCmdFile(fname);
     } while(FileFindNext(handle, fname));
   FileFindClose(handle);
  }

void ProcessCmdFile(string fname)
  {
   int fh = FileOpen(fname, FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|
                     FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(fh == INVALID_HANDLE) return;
   string suffix = "";
   int p1 = StringFind(fname, "rbtfx_cmd_");
   int p2 = StringFind(fname, ".txt", p1);
   if(p1 >= 0 && p2 > p1)
      suffix = StringSubstr(fname, p1 + 10, p2 - p1 - 10);
   bool dirty = false;
   while(!FileIsEnding(fh))
     {
      string ln = FileReadString(fh);
      ln = StringTrimLeft(ln);
      ln = StringTrimRight(ln);
      if(StringLen(ln) < 3) continue;
      string parts[];
      if(StringSplit(ln, StringGetCharacter("|", 0), parts) < 2) continue;
      string cid  = parts[0];
      string act  = parts[1];
      string pay  = "";
      if(ArraySize(parts) > 2) pay = parts[2];
      double idv  = StrToDouble(cid);
      string gv   = "RBTFX_LAST_" + suffix;
      if(idv <= GlobalVariableGet(gv)) continue;   // sudah diproses
      GlobalVariableSet(gv, idv);
      dirty = true;
      HandleCommand(suffix, cid, act, pay);
     }
   FileClose(fh);
   if(dirty)
     {
      int fw = FileOpen(fname, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|
                        FILE_SHARE_READ|FILE_SHARE_WRITE);
      if(fw != INVALID_HANDLE) FileClose(fw);   // kosongkan
     }
  }

void HandleCommand(string suffix, string cid, string act, string pay)
  {
   // RATES : SYM|M5|200
   if(act == "RATES")
     {
      string pp[];
      if(StringSplit(pay, StringGetCharacter("|", 0), pp) < 3)
        { Respond(suffix, cid, "ERR", "format"); return; }
      string sym = pp[0];
      int mins = TFMinutes(pp[1]);
      int n = (int)StrToDouble(pp[2]);
      if(mins <= 0 || n <= 0) { Respond(suffix, cid, "ERR", "tf"); return; }
      if(n > 1500) n = 1500;
      int dig = (int)MarketInfo(sym, MODE_DIGITS);
      string rows = "";
      // ASCENDING (lama -> baru): konvensi sama dgn MT5 copy_rates
      for(int i = n - 1; i >= 0; i--)
        {
         datetime t = iTime(sym, mins, i);
         if(t <= 0) break;
         string row = IntegerToString((int)t) + "," +
                      DoubleToStr(iOpen(sym, mins, i), dig) + "," +
                      DoubleToStr(iHigh(sym, mins, i), dig) + "," +
                      DoubleToStr(iLow(sym, mins, i), dig) + "," +
                      DoubleToStr(iClose(sym, mins, i), dig) + "," +
                      IntegerToString((int)iVolume(sym, mins, i));
         rows = (rows == "" ? row : rows + ";" + row);
        }
      if(rows == "") Respond(suffix, cid, "ERR", "nodata");
      else Respond(suffix, cid, "OK", rows);
      return;
     }
   // RHIST : SYM|TF|COUNT|BEFORE_TS -> `count` bar LEBIH LAMA dari
   // timestamp anchor (halaman riwayat dalam; blueprint s.3 AUTO)
   if(act == "RHIST")
     {
      string pp6[];
      if(StringSplit(pay, StringGetCharacter("|", 0), pp6) < 4)
        { Respond(suffix, cid, "ERR", "format"); return; }
      string sym3 = pp6[0];
      int mins3 = TFMinutes(pp6[1]);
      int n3 = (int)StrToDouble(pp6[2]);
      datetime before = (datetime)StrToDouble(pp6[3]);
      if(mins3 <= 0 || n3 <= 0)
        { Respond(suffix, cid, "ERR", "tf"); return; }
      if(n3 > 1500) n3 = 1500;
      int start = iBarShift(sym3, mins3, before, false) + 1;
      if(start <= 0) start = 1;              // aman: skip bar anchor
      int stop = start + n3 - 1;
      int total = iBars(sym3, mins3);
      if(stop > total - 1) stop = total - 1;
      int dig3 = (int)MarketInfo(sym3, MODE_DIGITS);
      string rows6 = "";
      for(int j = stop; j >= start; j--)     // ASCENDING (lama -> baru)
        {
         datetime t6 = iTime(sym3, mins3, j);
         if(t6 <= 0) continue;
         string row6 = IntegerToString((int)t6) + "," +
                       DoubleToStr(iOpen(sym3, mins3, j), dig3) + "," +
                       DoubleToStr(iHigh(sym3, mins3, j), dig3) + "," +
                       DoubleToStr(iLow(sym3, mins3, j), dig3) + "," +
                       DoubleToStr(iClose(sym3, mins3, j), dig3) + "," +
                       IntegerToString((int)iVolume(sym3, mins3, j));
         rows6 = (rows6 == "" ? row6 : rows6 + ";" + row6);
        }
      if(rows6 == "") Respond(suffix, cid, "ERR", "nodata");
      else Respond(suffix, cid, "OK", rows6);
      return;
     }
   // SYMINFO : SYM
   if(act == "SYMINFO")
     {
      double dig2 = MarketInfo(pay, MODE_DIGITS);
      if(dig2 <= 0) { Respond(suffix, cid, "ERR", "sym"); return; }
      string s = DoubleToStr(dig2, 0) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_POINT), 10) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_BID), 10) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_ASK), 10) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_TICKVALUE), 10) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_TICKSIZE), 10) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_MINLOT), 2) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_MAXLOT), 2) + ";" +
                 DoubleToStr(MarketInfo(pay, MODE_LOTSTEP), 2);
      Respond(suffix, cid, "OK", s);
      return;
     }
   // QUOTE : SYM  -> bid;ask
   if(act == "QUOTE")
     {
      RefreshRates();
      Respond(suffix, cid, "OK",
              DoubleToStr(MarketInfo(pay, MODE_BID), 10) + ";" +
              DoubleToStr(MarketInfo(pay, MODE_ASK), 10));
      return;
     }
   if(act == "PING")
     { Respond(suffix, cid, "OK", "PONG"); return; }
   if(act == "ACCOUNT")
     {
      string s2 = IntegerToString(AccountNumber()) + "|" +
                  AccountName() + "|" + AccountCurrency() + "|" +
                  IntegerToString(AccountLeverage()) + "|" +
                  AccountServer() + "|" +
                  DoubleToStr(AccountBalance(), 2) + "|" +
                  DoubleToStr(AccountEquity(), 2);
      Respond(suffix, cid, "OK", s2);
      return;
     }
   if(act == "SERVERTIME")
     {
      Respond(suffix, cid, "OK",
              IntegerToString((int)TimeCurrent()) + "|" +
              IntegerToString((int)TimeGMT()));
      return;
     }
   // POSITIONS (harga berjalan)
   if(act == "POSITIONS")
     {
      string rows2 = "";
      for(int i = 0; i < OrdersTotal(); i++)
        {
         if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;
         string row2 = IntegerToString(OrderTicket()) + ";" +
                       OrderSymbol() + ";" +
                       IntegerToString(OrderType()) + ";" +
                       DoubleToStr(OrderLots(), 2) + ";" +
                       DoubleToStr(OrderOpenPrice(), 10) + ";" +
                       DoubleToStr(OrderStopLoss(), 10) + ";" +
                       DoubleToStr(OrderTakeProfit(), 10) + ";" +
                       DoubleToStr(OrderProfit() + OrderSwap() +
                                   OrderCommission(), 2) + ";" +
                       DoubleToStr(OrderSwap(), 2) + ";" +
                       DoubleToStr(OrderCommission(), 2) + ";" +
                       IntegerToString(OrderMagicNumber()) + ";" +
                       OrderComment() + ";" +
                       IntegerToString((int)OrderOpenTime());
         rows2 = (rows2 == "" ? row2 : rows2 + "|" + row2);
        }
      Respond(suffix, cid, "OK", rows2);
      return;
     }
   // ORDER : SYM|BUY|lot|sl|tp|magic|comment
   if(act == "ORDER")
     {
      string pp2[];
      if(StringSplit(pay, StringGetCharacter("|", 0), pp2) < 7)
        { Respond(suffix, cid, "ERR", "format"); return; }
      string sym2   = pp2[0];
      bool   isbuy  = (pp2[1] == "BUY");
      double lot    = StrToDouble(pp2[2]);
      double sl     = StrToDouble(pp2[3]);
      double tp     = StrToDouble(pp2[4]);
      int    mg     = (int)StrToDouble(pp2[5]);
      string cmt    = pp2[6];
      // normalisasi lot
      double stp    = MarketInfo(sym2, MODE_LOTSTEP);
      if(stp > 0) lot = MathRound(lot / stp) * stp;
      double lmin   = MarketInfo(sym2, MODE_MINLOT);
      double lmax   = MarketInfo(sym2, MODE_MAXLOT);
      if(lot < lmin) lot = lmin;
      if(lot > lmax) lot = lmax;
      int tk = 0;
      for(int tr = 0; tr < 3 && tk <= 0; tr++)
        {
         RefreshRates();
         double pr = (isbuy ? MarketInfo(sym2, MODE_ASK)
                            : MarketInfo(sym2, MODE_BID));
         int op = (isbuy ? OP_BUY : OP_SELL);
         tk = OrderSend(sym2, op, lot, pr, 30, sl, tp, cmt, mg, 0, clrNONE);
         if(tk <= 0)
           {
            int err = GetLastError();
            // ECN: kirim tanpa SL/TP lalu pasang lewat OrderModify
            RefreshRates();
            pr = (isbuy ? MarketInfo(sym2, MODE_ASK)
                        : MarketInfo(sym2, MODE_BID));
            tk = OrderSend(sym2, op, lot, pr, 30, 0, 0, cmt, mg, 0, clrNONE);
            if(tk > 0 && (sl > 0 || tp > 0))
              {
               if(OrderSelect(tk, SELECT_BY_TICKET))
                  OrderModify(tk, OrderOpenPrice(), sl, tp, 0, clrNONE);
              }
            if(tk <= 0 && tr == 2)
              { Respond(suffix, cid, "ERR",
                        "OrderSend err " + IntegerToString(err)); return; }
            Sleep(300);
           }
        }
      if(tk > 0)
         Respond(suffix, cid, "OK",
                 IntegerToString(tk) + ";" +
                 DoubleToStr(isbuy ? MarketInfo(sym2, MODE_BID)
                                   : MarketInfo(sym2, MODE_ASK), 10));
      return;
     }
   // CLOSE : ticket|lots(0=all)
   if(act == "CLOSE")
     {
      string pp3[];
      StringSplit(pay, StringGetCharacter("|", 0), pp3);
      int    tk2  = (int)StrToDouble(pp3[0]);
      double lots = (ArraySize(pp3) > 1 ? StrToDouble(pp3[1]) : 0);
      if(!OrderSelect(tk2, SELECT_BY_TICKET))
        { Respond(suffix, cid, "ERR", "ticket"); return; }
      RefreshRates();
      double pr2 = (OrderType() == OP_BUY
                    ? MarketInfo(OrderSymbol(), MODE_BID)
                    : MarketInfo(OrderSymbol(), MODE_ASK));
      bool okc;
      if(lots <= 0 || lots >= OrderLots())
         okc = OrderClose(tk2, OrderLots(), pr2, 30, clrNONE);
      else
         okc = OrderClose(tk2, lots, pr2, 30, clrNONE);
      if(okc) Respond(suffix, cid, "OK", "1");
      else Respond(suffix, cid, "ERR", "close err " +
                   IntegerToString(GetLastError()));
      return;
     }
   // MODIFY : ticket|sl|tp
   if(act == "MODIFY")
     {
      string pp4[];
      StringSplit(pay, StringGetCharacter("|", 0), pp4);
      int tk3 = (int)StrToDouble(pp4[0]);
      if(!OrderSelect(tk3, SELECT_BY_TICKET))
        { Respond(suffix, cid, "ERR", "ticket"); return; }
      bool okm = OrderModify(tk3, OrderOpenPrice(),
                             StrToDouble(pp4[1]), StrToDouble(pp4[2]),
                             0, clrNONE);
      if(okm) Respond(suffix, cid, "OK", "1");
      else Respond(suffix, cid, "ERR", "modify err " +
                   IntegerToString(GetLastError()));
      return;
     }
   // HISTORY : from|to  (order closed dlm jendela)
   if(act == "HISTORY")
     {
      string pp5[];
      StringSplit(pay, StringGetCharacter("|", 0), pp5);
      int d1 = (int)StrToDouble(pp5[0]);
      int d2 = (int)StrToDouble(pp5[1]);
      string rows3 = "";
      int total = OrdersHistoryTotal();
      for(int i = 0; i < total; i++)
        {
         if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
         if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;
         int ct = (int)OrderCloseTime();
         if(ct < d1 || ct > d2) continue;
         string row3 = IntegerToString(OrderTicket()) + ";" +
                       OrderSymbol() + ";" +
                       IntegerToString(OrderType()) + ";" +
                       DoubleToStr(OrderLots(), 2) + ";" +
                       IntegerToString((int)OrderOpenTime()) + ";" +
                       DoubleToStr(OrderOpenPrice(), 10) + ";" +
                       IntegerToString(ct) + ";" +
                       DoubleToStr(OrderClosePrice(), 10) + ";" +
                       DoubleToStr(OrderProfit(), 2) + ";" +
                       DoubleToStr(OrderSwap(), 2) + ";" +
                       DoubleToStr(OrderCommission(), 2) + ";" +
                       IntegerToString(OrderMagicNumber());
         rows3 = (rows3 == "" ? row3 : rows3 + "|" + row3);
        }
      Respond(suffix, cid, "OK", rows3);
      return;
     }
   Respond(suffix, cid, "ERR", "aksi tidak dikenal");
  }
//+------------------------------------------------------------------+
