"""Risk manager sisi Python untuk Command Center.

Aturan (sama filosofinya dengan EA v2.20):
  - struktur -> SL -> lot; lot minimum yang masih menahan risiko -> SKIP
  - komisi dihitung dalam USD lalu dikonversi ke mata uang akun (otomatis)
  - daily loss = % dari balance awal hari -> henti trading saat tembus
  - hard SL TIDAK pernah dihilangkan; semua order wajib bawa SL
"""
from __future__ import annotations

import calendar
import json
import os
import time

DAY_FILE = "data/cc_day.json"


def _utc_date() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _day_date(tz_off=7.0, now=None) -> str:
    """v3.40: tanggal "hari trading" menurut zona waktu user (KUNCI WIB,
    UTC+7 -- permintaan eksplisit user). Batas hari P/L = tengah malam WIB = sama dengan aplikasi broker
    di HP user, BUKAN tengah malam UTC (dulu: daily profit selisih jauh)."""
    now = time.time() if now is None else now
    return time.strftime("%Y-%m-%d", time.gmtime(now + float(tz_off) * 3600.0))


def _is_weekend(ts=None) -> bool:
    return time.gmtime(ts).tm_wday >= 5  # Sabtu/Minggu (UTC)



def _eff_comm_usd(broker, cfg, usd_rate):
    """v3.x: komisi efektif USD/lot dgn DETEKSI model akun.
    Broker MT5 mendukung -> hasil deteksi (SPREAD=0, KOMISI=aktual).
    Broker stub / MT4 / simulasi (tanpa method) -> fallback config.
    Defensif sengaja: harness backtest & SIM memakai broker fake."""
    f = getattr(broker, "eff_comm_usd_per_lot", None)
    if callable(f):
        try:
            return float(f(cfg, usd_rate))
        except Exception:
            pass
    return float((cfg or {}).get("commission_per_lot_usd", 0.0))


class RiskGuard:
    def __init__(self, cfg, broker, log=print, day_file=DAY_FILE):
        self.cfg = cfg
        self.broker = broker
        self.log = log
        self.day_file = day_file
        self.day_start_balance = None
        self.day = None
        self.peak_equity = None
        self.peak_bal = None          # v3.51: peak BALANCE (closed-only)
        self.halted_reason = ""
        # pelindung anti SL-beruntun (v3.06)
        self.cooldowns = {}        # symbol -> epoch sampai kapan boleh entry lagi
        self.trades_today = {}     # symbol -> jumlah entry hari ini
        self.consec_losses = 0     # kekalahan beruntun global
        self.pause_until = 0.0     # epoch: jeda total setelah streak
        self.last_close = {}       # v3.33: symbol -> epoch close terakhir
        self.tz_off = float(cfg.get("day_tz_offset", 7.0))  # v3.69: WIB
        self._load_day()

    # -- daily state ---------------------------------------------------------
    def _load_day(self):
        try:
            with open(self.day_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("date") == _day_date(self.tz_off):
                self.day = d["date"]
                self.day_start_balance = float(d["balance"])
                self.peak_equity = float(d.get("peak", 0.0)) or None
                self.peak_bal = float(d.get("peak_bal", 0.0)) or None
                self.trades_today = dict(d.get("trades_today", {}))
                self.consec_losses = int(d.get("consec_losses", 0))
                self.pause_until = float(d.get("pause_until", 0.0))
                self.cooldowns = dict(d.get("cooldowns", {}))
                self.last_close = dict(d.get("last_close", {}))
        except Exception:
            pass

    def _save_day(self):
        if not self.day:               # v3.58 FIX: jaga-jaga pakai WIB
            self.day = _day_date(self.tz_off)   # (dulu _utc_date() ->
                                                #  00:00-07:00 WIB = kemarin!)
            if self.day_start_balance is None:
                acc = self.broker.account()
                self.day_start_balance = float(acc.get("balance", 0.0))
            if self.peak_equity is None:
                self.peak_equity = self.day_start_balance
            if self.peak_bal is None:
                self.peak_bal = self.day_start_balance
        try:   # v3.85: disk penuh -> state DI MEMORI tetap benar; tulis
               #   ulang saat ada ruang -- jangan biarkan entry gagal
            os.makedirs(os.path.dirname(self.day_file), exist_ok=True)
            with open(self.day_file, "w", encoding="utf-8") as f:
                json.dump({"date": self.day,
                           "balance": self.day_start_balance,
                           "peak": self.peak_equity,
                           "peak_bal": self.peak_bal,
                           "trades_today": self.trades_today,
                           "consec_losses": self.consec_losses,
                           "pause_until": self.pause_until,
                           "cooldowns": self.cooldowns,
                           "last_close": self.last_close}, f)
        except OSError:
            pass

    def day_since(self):
        """v3.40: epoch awal hari trading (tengah malam WIB, UTC+7).
        v3.58 FIX RESET: panggil ensure_day() dulu -> tanggal hari SELALU
        segar di setiap pembacaan (dashboard/rekap/guard).  Dulu: bila
        engine start 00:00-07:00 WIB dgn day file kemarin, self.day bisa
        nyangkut tanggal UTC (= kemarin WIB) -> kartu harian memuat
        transaksi hari kemarin."""
        self.ensure_day()
        if not self.day:
            self.day = _day_date(self.tz_off)
        return (calendar.timegm(time.strptime(self.day, "%Y-%m-%d"))
                - self.tz_off * 3600.0)

    def ensure_day(self):
        today = _day_date(self.tz_off)
        if self.day != today:
            self.day = today
            acc = self.broker.account()
            self.day_start_balance = float(acc.get("balance", 0.0))
            self.peak_equity = self.day_start_balance   # reset peak tiap hari
            self.peak_bal = self.day_start_balance      # reset peak balance
            self.trades_today = {}                      # reset kuota harian
            self.halted_reason = ""
            self._save_day()
            self.log("[PROTECT] Hari baru %s | balance awal=%.2f %s"
                     % (today, self.day_start_balance, acc.get("currency", "")))
        if self.day_start_balance is None:
            acc = self.broker.account()
            self.day_start_balance = float(acc.get("balance", 0.0))
            if self.peak_equity is None:
                self.peak_equity = self.day_start_balance
            if self.peak_bal is None:
                self.peak_bal = self.day_start_balance
            self._save_day()

    # -- status ---------------------------------------------------------------
    def daily_status(self, equity, realized=None, balance=None):
        """v3.25: pencatatan harian RAPI —
        - daily loss/guard dihitung dari REALIZED (posisi ditutup) saja;
          floating TIDAK dihitung, deposit/WD TIDAK dihitung.
        - Deposit/WD dideteksi dari lompatan balance yang tidak dijelaskan
          oleh P/L close -> day_start digeser (netral), ada log.
        Panggilan lama daily_status(equity) tetap jalan (perilaku lama)."""
        self.ensure_day()
        equity = float(equity)
        # v4.31 (user): MAX DAILY LOSS DIHAPUS TOTAL DI KODE.
        # Akar laporan "belum terhapus": cc_config.json runtime di
        # VPS menimpa default repo (daily_loss_pct 10) -> lock
        # tetap hidup.  Kini 0.0 KERAS -- config apa pun tidak
        # bisa menyalakannya lagi.
        dlp = 0.0
        limit = self.day_start_balance * (1.0 - dlp / 100.0)

        # v3.58: heuristik netralisasi deposit/WD DIHAPUS - salah deteksi
        # close sebagai deposit (spam [STATE] & day_start bergeser terus).
        # day_start KARTU kini direkonstruksi command_center dgn formula
        # self-correcting: balance - realized - bal_ops (deal balance
        # asli dari riwayat broker).

        # --- peak equity (persist; dd equity utk guard/monitoring)
        if self.peak_equity is None or equity > self.peak_equity:
            self.peak_equity = equity
            self._save_day()
        dd_pct = 0.0
        if self.peak_equity and self.peak_equity > 0:
            dd_pct = max(0.0, (self.peak_equity - equity)
                         / self.peak_equity * 100.0)

        # --- v3.51: peak BALANCE + DD basis CLOSED-ONLY (tampilan kartu) ---
        #     balance hanya berubah saat order close -> pencatatan murni
        #     dari order close (floating TIDAK masuk).
        if balance is not None:
            bal0 = float(balance)
            if self.peak_bal is None or bal0 > self.peak_bal:
                self.peak_bal = bal0
                self._save_day()
            dd_bal = (max(0.0, (self.peak_bal - bal0)
                          / self.peak_bal * 100.0)
                      if self.peak_bal and self.peak_bal > 0 else 0.0)
        else:
            dd_bal = dd_pct
        loss_closed_abs = max(0.0, -float(realized)) \
            if realized is not None else 0.0
        loss_closed_pct = (loss_closed_abs / self.day_start_balance
                           * 100.0) if self.day_start_balance else 0.0

        # --- loss & guard: STRATEGY 2 (EA v6.05) = EQUITY-based (floating
        #     ikut dihitung; lock bila equity <= modal_awal - 15%).
        #     Mode lama S1 (realized-only) tetap dipakai bila
        #     daily_equity_based False/absen.
        #     AMBANG AWAL (daily_soft_pct, default 95%): sebelum tembus
        #     batas penuh, soft_hit = True -> command_center S2 menutup
        #     SEMUA posisi bot & stop trading hari itu (buffer anti
        #     slippage; contoh batas 100 -> tutup semua di ~95).
        eq_mode = bool(self.cfg.get("daily_equity_based", False))
        soft_pct = float(self.cfg.get("daily_soft_pct", 95.0) or 95.0)
        soft_val = (self.day_start_balance * dlp / 100.0
                    * soft_pct / 100.0) if self.day_start_balance > 0 else 0.0
        soft_hit = False
        if eq_mode:
            halted = (dlp > 0 and self.day_start_balance > 0
                      and equity <= limit + 1e-7)   # v4.31: dlp 0 = mati
            soft_hit = (self.day_start_balance > 0 and soft_val > 0
                        and equity <= self.day_start_balance - soft_val + 1e-7)
            if halted:
                self.halted_reason = "DAILY_LOSS_LIMIT"
            loss_pct = (max(0.0, self.day_start_balance - equity)
                        / self.day_start_balance * 100.0
                        if self.day_start_balance > 0 else 0.0)
        elif realized is not None:
            loss_abs = max(0.0, -float(realized))
            halted = (dlp > 0 and self.day_start_balance > 0
                      and loss_abs >= self.day_start_balance * dlp / 100.0)
            if halted:
                self.halted_reason = "DAILY_LOSS_LIMIT"
            loss_pct = (loss_abs / self.day_start_balance * 100.0
                        if self.day_start_balance > 0 else 0.0)
        else:
            halted = (dlp > 0 and equity <= limit)
            if halted:
                self.halted_reason = "DAILY_LOSS_LIMIT"
            loss_pct = 0.0
            if self.day_start_balance > 0:
                loss_pct = max(0.0, (self.day_start_balance - equity)
                               / self.day_start_balance * 100.0)
        return {"day_start": self.day_start_balance,
                "limit": limit, "halted": halted,
                "soft_limit": round(soft_val, 2), "soft_hit": soft_hit,
                "reason": self.halted_reason,
                "loss_abs": round(max(0.0, (loss_pct / 100.0)
                                      * self.day_start_balance), 2)
                if self.day_start_balance else 0.0,
                "loss_pct": round(loss_pct, 2),
                "dd_pct": round(dd_pct, 2),
                "peak": round(float(self.peak_equity), 2),
                "loss_abs_closed": round(loss_closed_abs, 2),
                "loss_pct_closed": round(loss_closed_pct, 2),
                "dd_bal_pct": round(dd_bal, 2),
                "peak_bal": round(float(self.peak_bal or 0.0), 2),
                "limit_used_pct": round(min(100.0, loss_pct / dlp * 100.0), 1)
                if dlp > 0 else 0.0,
                "since": self.day_since()}

    # -- gates -----------------------------------------------------------------
    def weekend_ok(self, now_ts=None):
        if not self.cfg.get("weekend_guard", True):
            return True, ""
        if _is_weekend(now_ts):
            return False, "WEEKEND"
        return True, ""

    def spread_ok(self, symbol, spread_points):
        lim = self.cfg.get("spread_overrides", {}).get(symbol,
                                                       self.cfg.get("max_spread_points", 1000))
        if spread_points > lim:
            return False, "SPREAD %d > %d" % (spread_points, lim)
        return True, ""

    def can_open(self, symbol, positions):
        # STRATEGY 2: max N PAIR berbeda terbuka bersamaan (user: 3)
        max_pairs = int(self.cfg.get("max_open_pairs", 0) or 0)
        if max_pairs > 0:
            syms = set(p["symbol"] for p in positions if not p.get("manual"))
            if symbol not in syms and len(syms) >= max_pairs:
                return False, "MAX_OPEN_PAIRS %d" % max_pairs
        if len(positions) >= self.cfg.get("max_positions", 5):
            return False, "MAX_POSITIONS %d" % len(positions)
        for p in positions:
            if p["symbol"] == symbol:
                return False, "POSISI_SUDAH_ADA"
        return True, ""

    # -- lot sizing --------------------------------------------------------------
    def calc_lot(self, symbol, info, sl_points, account_currency, usd_rate):
        """Return (lot, skip_reason). struktur->SL->lot (lot terakhir)."""
        if info.get("trade_tick_size", 0) <= 0 or info.get("trade_tick_value", 0) <= 0:
            return 0.0, "SYMBOL_INFO_KURANG"
        acc = self.broker.account()
        balance = float(acc.get("balance", 0.0))
        risk_money = balance * self.cfg.get("risk_pct", 1.0) / 100.0
        # STRATEGY 2: risiko FIX per entry (USD), bukan % balance.
        # sl_money_usd=12 -> akun IDR: 12 x kurs (18.000) = Rp216.000.
        # Lot tiap pair otomatis menyesuaikan jarak SL 0.8 x ATR pair itu.
        sm_usd = float(self.cfg.get("sl_money_usd", 0.0) or 0.0)
        if sm_usd > 0:
            risk_money = sm_usd * (float(usd_rate or 0) or 1.0)
        if risk_money <= 0:
            return 0.0, "BALANCE_KOSONG"

        ticks_in_sl = sl_points * info["point"] / info["trade_tick_size"]
        loss_per_lot = ticks_in_sl * info["trade_tick_value"]     # mata uang akun
        # v3.98: komisi efektif dr DETEKSI model akun
        # (SPREAD=0 / KOMISI=aktual); USD final, kurs di dalam resolver
        commission = _eff_comm_usd(self.broker, self.cfg, usd_rate or 0.0)
        loss_per_lot_total = loss_per_lot + commission
        if loss_per_lot_total <= 0:
            return 0.0, "LOSS_PER_LOT_INVALID"

        raw = risk_money / loss_per_lot_total
        step = info.get("volume_step", 0.01) or 0.01
        vmin = info.get("volume_min", 0.01) or 0.01
        vmax = info.get("volume_max", 100.0) or 100.0
        lot = math_floor_step(raw, step)
        if lot < vmin:
            # v3.21: SL lebar TIDAK lagi membatalkan entry (sinyal momentum
            # valid tetap masuk) -> pakai lot minimum. Pengaman: risiko
            # efektif lot minimum maksimal max_risk_overrun_x x target.
            eff = loss_per_lot_total * vmin
            cap = risk_money * float(self.cfg.get("max_risk_overrun_x", 3.0))
            if not self.cfg.get("force_min_lot_entry", True):
                return 0.0, "LOT<MIN (SL terlalu lebar utk risiko %.2f)" % risk_money
            if eff > cap:
                return 0.0, ("RISIKO_LOT_MIN %.2f > %.1fx target (%.2f) -> SKIP"
                             % (eff, float(self.cfg.get("max_risk_overrun_x", 3.0)),
                                risk_money))
            self.log("[LOT] %s lot min %.2f dipaksa (SL lebar; risiko efektif "
                     "%.2f = %.1fx target)" % (symbol, vmin, eff,
                                               eff / risk_money if risk_money else 0))
            lot = vmin
        lot = min(lot, vmax)
        return round(lot, 8), ""

    # -- SL bounds -----------------------------------------------------------------
    def sl_bounds_ok(self, sl_points):
        if sl_points < self.cfg.get("min_sl_points", 100):
            return False, "SL_TERLALU_SEMPIT %dpt" % int(sl_points)
        if sl_points > self.cfg.get("max_sl_points", 100000):
            return False, "SL_TERLALU_LEBAR %dpt" % int(sl_points)
        return True, ""

    # -- pelindung anti SL-beruntun (v3.06) -----------------------------------
    def note_open(self, symbol, now=None):
        self.trades_today[symbol] = self.trades_today.get(symbol, 0) + 1
        self._save_day()

    def note_closed(self, symbol, pl, now=None):
        """Dipanggil utk SETIAP posisi tertutup. pl <= 0 dihitung rugi."""
        now = time.time() if now is None else now
        self.last_close[str(symbol).upper()] = float(now)  # v3.33
        if pl > 0:
            self.consec_losses = 0
        else:
            self.consec_losses += 1
            cd = self.cfg.get("cooldown_after_sl_min", 90) * 60
            self.cooldowns[str(symbol).upper()] = now + cd
            if self.consec_losses >= self.cfg.get("max_consec_losses", 3):
                self.pause_until = now + self.cfg.get("consec_pause_min", 240) * 60
                self.log("[PROTECT] %d SL beruntun -> robot jeda otomatis %.0f jam"
                         % (self.consec_losses,
                            self.cfg.get("consec_pause_min", 240) / 60.0))
        self._save_day()

    def cooldown_ok(self, symbol, now=None):
        now = time.time() if now is None else now
        until = self.cooldowns.get(str(symbol).upper(), 0)
        if now < until:
            return False, "COOLDOWN %d mnt lagi" % int((until - now) / 60)
        return True, ""

    def fresh_entry_ok(self, symbol, born, now=None):
        """v3.33: re-entry WAJIB sinyal segar. Kandidat yang LAHIR sebelum
        close terakhir simbol ini = sinyal lama -> ditolak. Entry baru hanya
        boleh dari analisa BARU yang dibuat setelah posisi sebelumnya tutup,
        dan tetap melewati semua filter (sniper, skor, kuota, dll)."""
        lt = self.last_close.get(str(symbol).upper(), 0)
        if lt and born and float(born) < float(lt):
            return False, "SINYAL_LAMA (close terbaru terjadi setelah sinyal dibuat)"
        return True, ""

    def trades_ok(self, symbol):
        n = self.trades_today.get(symbol, 0)
        cap = self.cfg.get("max_trades_per_symbol_day", 2)
        if n >= cap:
            return False, "KUOTA %d entry/hari habis" % cap
        return True, ""

    def streak_ok(self, now=None):
        now = time.time() if now is None else now
        if now < self.pause_until:
            return False, "JEDA %d mnt (SL beruntun)" % int((self.pause_until - now) / 60)
        return True, ""

    def _is_crypto(self, symbol):
        u = str(symbol).upper()
        return "BTC" in u or "ETH" in u

    def session_ok(self, symbol, now=None):
        """Crypto 24 jam; aset lain hanya jam pasar aktif (default 7-20 UTC)."""
        if self._is_crypto(symbol):
            return True, ""
        if not self.cfg.get("weekend_guard", True) and False:
            pass
        win = self.cfg.get("trade_hours_utc", [7, 20])
        t = time.gmtime(now)
        if t.tm_wday >= 5:
            return False, "WEEKEND"
        if not (win[0] <= t.tm_hour < win[1]):
            return False, "DI LUAR JAM %02d-%02d UTC" % (win[0], win[1])
        return True, ""

    def cluster_of(self, symbol):
        u = str(symbol).upper()
        for name, members in self.cfg.get("correlation_clusters", {}).items():
            for m in members:
                if m in u or u in m:
                    return name
        return None

    def cluster_ok(self, symbol, positions):
        cl = self.cluster_of(symbol)
        if not cl:
            return True, ""
        cap = self.cfg.get("max_per_cluster", 2)
        n = 0
        for p in positions:
            if self.cluster_of(p["symbol"]) == cl:
                n += 1
        if n >= cap:
            return False, "KLASTER %s penuh (%d)" % (cl, cap)
        return True, ""

    @staticmethod
    def extension_ok(side, ext_atr, max_ext):
        """True jika harga TIDAK terlambat mengejar (entry tidak mengejar top)."""
        if side == "BUY":
            return ext_atr <= max_ext
        return -ext_atr <= max_ext

    # -- trailing BE --------------------------------------------------------------
    def smart_exit(self, positions, broker, usd_rate=0.0):
        """v3.25 SYSTEM PINTAR: bekerja saat ada posisi terbuka. Scan M5 ->
        M15 -> H1 mencari zona BODY SNR/HH-HL di depan harga. Posisi BUY yang
        sudah MENYENTUH zona HH (dan floating profit) -> tutup sekarang
        (TP saja berapapun) karena rawan candle rejection; lebih baik
        re-entry dgn sinyal baru yang valid. Mirror utk SELL (zona LL/HL).
        Return jumlah posisi ditutup."""
        import cc_scanner  # lazy (hindari circular import)
        if not self.cfg.get("smart_exit_enabled", True):
            return 0
        min_usd = float(self.cfg.get("smart_exit_min_profit_usd", 0.0))
        rate = usd_rate if usd_rate and usd_rate > 0 else 1.0
        closed = 0
        for p in list(positions):
            info = broker.symbol_info(p["symbol"])
            if not info:
                continue
            tsz = float(info.get("trade_tick_size") or 0.0)
            tv = float(info.get("trade_tick_value") or 0.0)
            lot = float(p.get("lot") or 0.0)
            if tsz <= 0 or tv <= 0 or lot <= 0:
                continue
            comm_usd = (_eff_comm_usd(self.broker, self.cfg, rate)
                        * lot)                     # v3.98: deteksi akun
            net_usd = (float(p.get("pl") or 0.0)
                       - comm_usd * rate) / rate
            if net_usd <= min_usd:
                continue                       # belum profit -> biarkan jalan
            side = p["type"]
            for tf in ("M5", "M15", "H1"):     # kecil -> besar (paling reaktif)
                bars = broker.copy_rates(p["symbol"], tf, 60)
                if not bars:
                    continue
                touched, zpx = cc_scanner.zone_touch(side, float(p["entry"]),
                                                     float(p["price"]), bars)
                if touched:
                    r = broker.close_position(p["ticket"])
                    if getattr(r, "ok", False):
                        closed += 1
                        self.log("[SMART] %s #%s %s sentuh zona %s %.5f "
                                 "-> TP dini (net $%.2f, anti rejection)"
                                 % (p["symbol"], p["ticket"], side, tf,
                                    zpx, net_usd))
                    break
        return closed

    def basket_net(self, positions, usd_rate=0.0):
        """v3.22: total PROFIT BERSIH semua posisi terbuka (floating -
        total komisi penuh, konversi kurs akun). Return (net, total_komisi).
        """
        tot = 0.0
        comm = 0.0
        for p in positions:
            lot = float(p.get("lot") or 0.0)
            # v3.98: deteksi model akun (SPREAD -> 0)
            comm += _eff_comm_usd(self.broker, self.cfg,
                                  usd_rate or 0.0) * lot * (usd_rate or 0.0)
            tot += float(p.get("pl") or 0.0)
        return (tot - comm), comm

    def basket_tp(self, positions, broker, usd_rate=0.0):
        """v3.22: BASKET TAKE PROFIT — bila PROFIT BERSIH gabungan SEMUA
        posisi terbuka (beda pair, campur profit & minus) >=
        basket_tp_usd (default 5 USD ~ Rp90.000), TUTUP SEMUA posisi
        seketika (lock profit gabungan). Tambahan terpisah; TIDAK
        mengubah TP/MTRAIL per posisi. Return (jumlah_tutup, net).
        """
        if not self.cfg.get("basket_tp_enabled", True):
            return 0, 0.0
        target = float(self.cfg.get("basket_tp_usd", 5.0))
        if target <= 0 or not positions:
            return 0, 0.0
        net_acct, comm = self.basket_net(positions, usd_rate)
        rate = usd_rate if usd_rate and usd_rate > 0 else 1.0
        net = net_acct / rate                    # v3.23: bandingkan dalam USD
        if net < target:
            return 0, net
        self.log("[BASKET] net gabungan $%.2f >= target $%.2f -> tutup %d "
                 "posisi" % (net, target, len(positions)))
        closed = 0
        for p in list(positions):
            try:
                r = broker.close_position(p["ticket"])
                if getattr(r, "ok", False):
                    closed += 1   # pencatatan guard lewat closed_trades_since
                else:
                    self.log("[BASKET] gagal tutup #%s (%s)"
                             % (p.get("ticket"),
                                getattr(r, "comment", "")))
            except Exception as e:
                self.log("[BASKET] error tutup #%s: %s"
                         % (p.get("ticket"), e))
        if closed:
            self.log("[BASKET] %d/%d posisi ditutup | profit bersih dikunci "
                     "~$%.2f" % (closed, len(positions), net))
        return closed, net

    def money_trail(self, positions, broker, usd_rate=0.0):
        """v3.21: trailing berbasis PROFIT BERSIH posisi (pl dikurangi komisi
        penuh posisi tsb, dikonversi ke mata uang akun).

        Aturan user: net >= money_trail_start_usd (2 USD / ~Rp36.000) ->
        SL digeser ke harga yang mengunci net profit 1 step (1 USD);
        setiap tambahan 1 step net profit, SL digeser 1 step lagi.
        SL hanya bergerak maju (tidak pernah mundur). Return jumlah geseran.
        """
        if not self.cfg.get("money_trail_enabled", True):
            return 0
        start = float(self.cfg.get("money_trail_start_usd", 2.0))
        step = float(self.cfg.get("money_trail_step_usd", 1.0))
        if start <= 0 or step <= 0:
            return 0
        moved = 0
        for p in positions:
            info = broker.symbol_info(p["symbol"])
            if not info:
                continue
            tsz = float(info.get("trade_tick_size") or 0.0)
            tv = float(info.get("trade_tick_value") or 0.0)
            lot = float(p.get("lot") or 0.0)
            point = float(info.get("point") or 0.0)
            digits = int(info.get("digits") or 5)
            if tsz <= 0 or tv <= 0 or lot <= 0:
                continue
            rate = usd_rate if usd_rate and usd_rate > 0 else 1.0
            comm = (_eff_comm_usd(self.broker, self.cfg, rate)
                    * lot * rate)   # v3.98: deteksi model akun
            # v3.23 FIX: pl posisi dalam MATA UANG AKUN (mis. IDR) -> sudahi
            # ke USD dulu SEBELUM dibandingkan dgn start/step yang ber-satuan
            # USD (bug lama: Rp16.500 (= $1) dibanding angka 2 -> geser dini)
            net_usd = (float(p.get("pl") or 0.0) - comm) / rate
            if net_usd < start:
                continue
            lock = (int((net_usd - start) / step) + 1) * step   # 2..3->lock1
            val_per_unit = tv / tsz * lot                        # nilai akun/1.0 harga
            if val_per_unit <= 0 or point <= 0:
                continue
            need = (lock * rate + comm) / val_per_unit
            if p["type"] == "BUY":
                new_sl = p["entry"] + need
                if p["sl"] and new_sl <= float(p["sl"]) + point * 0.5:
                    continue
                if new_sl >= float(p["price"]) - point:          # brokernya tolak
                    continue
            else:
                new_sl = p["entry"] - need
                if p["sl"] and new_sl >= float(p["sl"]) - point * 0.5:
                    continue
                if new_sl <= float(p["price"]) + point:
                    continue
            new_sl = round(round(new_sl / point) * point, digits)
            if broker.modify_sl(p["ticket"], new_sl):
                moved += 1
                p["trailing"] = True
                self.log("[MTRAIL] %s #%s net $%.2f -> kunci $%.2f "
                         "(SL %.5f)" % (p["symbol"], p["ticket"], net_usd,
                                        lock, new_sl))
        return moved

    def check_trailing(self, positions, broker):
        at_r = self.cfg.get("trail_be_at_r", 1.0)
        if at_r <= 0:
            return 0
        moved = 0
        for p in positions:
            if p.get("trailing"):
                continue
            info = broker.symbol_info(p["symbol"])
            if not info:
                continue
            sl_dist = abs(p["entry"] - p["sl"]) if p["sl"] else 0.0
            if sl_dist <= 0:
                continue
            gain = (p["price"] - p["entry"]) if p["type"] == "BUY" \
                else (p["entry"] - p["price"])
            if gain >= sl_dist * at_r:
                buffer = (info["ask"] - info["bid"]) or info["point"] * 2
                new_sl = p["entry"] + buffer if p["type"] == "BUY" \
                    else p["entry"] - buffer
                if broker.modify_sl(p["ticket"], new_sl):
                    moved += 1
                    self.log("[TRAIL] %s #%s SL -> BE (%.5f)"
                             % (p["symbol"], p["ticket"], new_sl))
        return moved


def math_floor_step(x, step):
    """Floor ke kelipatan step (lot step broker)."""
    import math as _m
    if step <= 0:
        return x
    return _m.floor(x / step + 1e-9) * step
