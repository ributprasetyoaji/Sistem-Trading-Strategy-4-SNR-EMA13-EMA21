"""Konfigurasi PYTHON COMMAND CENTER (multi-pair, Python kirim order langsung).

Semua nilai bisa dioverride lewat file JSON (cc_config.json) di root proyek.
Tidak mengubah config.py lama (engine BTC v2.20 tetap utuh).
"""
from __future__ import annotations

import json
import os

CC_VERSION = "4.39"

DEFAULTS = {
    # ---- HISTORY CLOUD (v3.88, permintaan user): backup/restore cache
    #      riwayat ke repo GitHub -> muat ulang/pindah VPS TANPA
    #      download ulang lama.  Token: env RBT_GH_TOKEN (diisi bat)
    #      atau file github_token.txt -- tidak disimpan di repo.
    "hist_cloud": {
        "enabled": True,
        "repo": "ributprasetyoaji/Sistem-Trading-Strategy-3",
        "branch": "main",
        "dir": "data_hist",              # folder file .json.gz di repo
        "upload_min_new_bars": 1000,     # BASE: upload saat tumbuh ~10 hari M15
        "upload_min_hours": 24.0,        # BASE: maks 1x/hari/pair (repo ramping)
        "download_min_bars": 2000,       # lokal < ini -> restore cloud
        "delta_enabled": True,           # v4.30 (user): backup 2X SEHARI
        "delta_min_new_bars": 20,        #   hanya bar baru (ringan,
                                         #   ~2-4 KB gzip)
        "delta_min_hours": 12.0,         #   delta tiap 12 jam -> muat
                                         #   ulang tak perlu tarik 1
                                         #   tahun ulang dr broker
        "autosync_every_sec": 600.0,     #   cek backup tiap 10 mnt
        "timeout_sec": 30.0,             # v4.17: 20->30 (VPS lambat)
        "restore_retry_sec": 180.0,      # v4.17: retry restore tiap 3 mnt
        "token": "",
    },
    # ---- MARKET GUARD (v3.86, permintaan user -- berlaku S1/S2/S3) ----
    "market_guard": {                # SKIP entry 1 jam sebelum tutup akhir
                                      #   pekan + aktif lg otomatis saat
                                      #   buka; SKIP semua entry 30 mnt
                                      #   sebelum rollover harian
        "enabled": True,
        "weekend_skip_before_min": 60,
        "weekend_close_dow": 4,      # 4 = Jumat
        "weekend_close_utc": "21:00",    # tipikal NY-close; sesuaikan broker
        "weekend_open_dow": 6,       # 6 = Minggu
        "weekend_open_utc": "22:00",
        "rollover_skip_before_min": 30,
        "rollover_after_min": 5,
        "rollover_utc": "21:00",     # tipikal midnight server GMT+2/3
        "always_open_keywords": ["BTC", "ETH", "SOL", "XRP", "LTC",
                                 "DOGE", "ADA", "XLM", "BCH"],
    },
    # ---- DASHBOARD ----
    "auto_update_min": 120.0,      # AUTO-UPDATE: cek GitHub
                                      #   tiap N menit (0=off);
                                      #   ada versi baru -> engine
                                      #   restart OTOMATIS tanpa klik
    "dashboard_port": 8082,          # S2: port TERPISAH dari Strategy 1 (8080); buka http://localhost:8081 di browser VPS
    "dashboard_password": "",        # v3.19: SANDI login dashboard. ISI ini
                                      #   (mis. "KunciKuat123") kalau dashboard
                                      #   dibuka ke internet/HP; kosong = tanpa
                                      #   sandi (hanya aman di VPS lokal)
    # ---- KONEKSI / EKSEKUSI ----
    "mt5_terminal_path": "",          # kosong = auto-deteksi folder Program Files
    "mt5_login": 0,                   # opsional: nomor akun utk AUTO-LOGIN (0 = manual)
    "mt5_password": "",               # opsional: password akun (disimpan lokal di VPS Anda)
    "mt5_server": "",                 # opsional: nama server broker, mis "Exness-MT5Trial8"
    "broker_mode": "auto",           # v3.70 SUPPORT MT4 + MT5:
                                      #   auto = MT5 dulu -> MT4 (EA
                                      #   RBT_FX_Bridge) -> SIMULASI;
                                      #   "mt5"/"mt4" = paksa satu
    "mt4_files_dir": "",             #   folder Common MT4 (kosong =
                                      #   auto APPDATA Common Files)
    "mt4_magic": 0,                  #   0 = ikut "magic" di bawah
    "mt4_timeout": 6.0,              #   batas tunggu jawaban EA (dtk)
    "magic": 777003,                  # magic number khusus Command Center (beda dari EA)
    "deviation_points": 50,           # slippage maksimum (points)
    # ---- DAFTAR PAIR (kosongkan list -> auto pakai ALTERNATE names) ----
    "symbols": ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY",
                "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "EURJPY",
                "GBPJPY", "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD",
                "LTCUSD", "NAS100", "US30", "GER40", "US500",
                "XPTUSD", "USOIL"],
    "symbols_force_include": ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD",
                              "LTCUSD", "XAUUSD", "XAGUSD"],
                                      # S4 (user): crypto + gold/silver
                                      #   PAKSA ADA walau cc_config.json
                                      #   di VPS menimpa "symbols"
    "symbol_alternates": {            # nama symbol beda-beda tiap broker;
        # akhiran "m" = akun Standard Exness (mis. USTECm, XAUUSDm)
        "XAUUSD": ["XAUUSD", "GOLD", "XAUUSDm", "GOLDm", "GOLD.a", "XAUUSD.a"],
        "XAGUSD": ["XAGUSD", "SILVER", "XAGUSDm", "XAGUSD.a"],
        "BTCUSD": ["BTCUSD", "BTCUSDM", "BTCUSDm", "BTCUSD.a", "Bitcoin", "BTCUSD.pro"],
        "ETHUSD": ["ETHUSD", "ETHUSDM", "ETHUSDm", "ETHUSD.a", "Ethereum"],
        "NAS100": ["NAS100", "USTEC", "USTECm", "NAS100m", "US100", "UT100", "NDX100"],
        "USOIL":  ["USOIL", "WTI", "USOILm", "XTIUSD", "USOIL.a", "USCRUDE"],
        "AUDUSD": ["AUDUSD", "AUDUSDm", "AUDUSD.a"],
        "NZDUSD": ["NZDUSD", "NZDUSDm", "NZDUSD.a"],
        "USDCAD": ["USDCAD", "USDCADm", "USDCAD.a"],
        "USDCHF": ["USDCHF", "USDCHFm", "USDCHF.a"],
        "EURJPY": ["EURJPY", "EURJPYm", "EURJPY.a"],
        "GBPJPY": ["GBPJPY", "GBPJPYm", "GBPJPY.a"],
        "SOLUSD": ["SOLUSD", "SOLUSDm", "SOLUSDT", "SOLUSD.a", "Solana"],
        "XRPUSD": ["XRPUSD", "XRPUSDm", "XRPUSDT", "XRPUSD.a", "Ripple"],
        "LTCUSD": ["LTCUSD", "LTCUSDm", "LTCUSDT", "LTCUSD.a", "Litecoin"],
        "US30":   ["US30", "US30m", "Dow", "DJI30", "USA30", "WallStreet",
                   "WS30"],
        "GER40":  ["GER40", "GER40m", "DE40", "DAX40", "GER30", "DAX",
                   "DE30"],
        "US500":  ["US500", "US500m", "SPX500", "SP500", "USA500"],
        "XPTUSD": ["XPTUSD", "XPTUSDm", "PLAT", "Platinum", "XPTUSD.a"],
    },
    # ---- FILTER & GATE ----
    "max_spread_points": 1000,        # default; bisa dioverride per symbol
    "spread_overrides": {"EURUSD": 60, "GBPUSD": 80, "USDJPY": 60, "XAGUSD": 200, "SOLUSD": 2500, "XRPUSD": 2500, "LTCUSD": 2500, "XPTUSD": 1500},
    "min_score": 70,              # S3: samakan dgn min_setup_score                  # skor konfluensi minimal untuk kandidat
    "sniper_required": True,          # wajib konfirmasi micro M1 sebelum order
    "setup_valid_min": 45,            # sinyal M15 berlaku 45 menit:
                                      #   M1 MENAHAN (hold), bukan memblokir,
                                      #   sampai momen momentum pas ditemukan
    "pull_min_atr": 0.15,             # pullback minimal (x ATR M1) dari puncak
                                      #   -> anti "buy di HH / sell di LL"
    "sniper_need_bars": 24,           # bar M1 minimal utk keputusan sniper
    "weekend_guard": True,            # jangan trading Sabtu/Minggu
    # ---- RISIKO (input dalam USD, auto dikonversi ke mata uang akun) ----
    "risk_pct": 3.0,                  # v4.14 (permintaan user): risiko
                                      #   per entry 3% balance
                                      #   (dulu 0.5% blueprint) -> lot
                                      #   cukup besar utk tangga TP
                                      #   75/25 (min_entry_lot 0.05)
    "commission_per_lot_usd": 4.0,    # komisi/lot USD -- FALLBACK bila deteksi UNKNOWN; deteksi model akun (SPREAD=0) yg menang
    "usd_rate_manual": 18000.0,       # v3.24: KUNCI 1 USD = Rp18.000 utk
                                      #   konversi komisi/MTRAIL/BASKET di
                                      #   akun IDR. Setel 0 = pakai kurs
                                      #   otomatis dari simbol broker.
    "min_sl_points": 100,             # SL terlalu sempit -> SKIP
    "max_sl_points": 100000,          # SL lebih lebar dari ini -> SKIP
    # ================= STRATEGY 2 (bind - spesifikasi user) =================
    # Port EA MQL5 "RBT FX v6.05 ATR" -> cc_strategy2.py.
    # SL/TP = ATR trailing dari file spec: TIDAK ada TP fixed, TIDAK ada
    # trailing BE / money trail / basket TP / smart exit (semua OFF di bawah;
    # SL dikelola cc_strategy2.ATRTrail).
    "day_stats_mode": "wib",   # rekap = riwayat aplikasi HP (WIB); "broker" = tengah malam server
    "daily_equity_based": True,       # S2 (EA v6.05): floating IKUT dihitung
                                      #   (lock bila equity <= modal - 15%)
    "daily_soft_pct": 95.0,           # S2: AMBANG AWAL = 95% x batas harian
                                      #   (batas 100 -> di ~95 semua posisi
                                      #   bot DITUTUP & stop s/d reset 00:00)
    "sl_money_usd": 0.0,             # S2: SL per entry = 12 USD (Rp216.000)
                                      #   FIX -> lot dinamis per pair mengikuti
                                      #   0.8 x ATR pair tsb (bukan % balance)
    "tp_rr": 1.0,                    # v4.27 (user): TP1 = 1x jarak SL
                                      #   (dulu 1.5 -- v4.22; masih
                                      #   lebih dulu dari BEP); 0 = off
    "tp1_rr": 1.0,                   # v4.27 (user) TP1 = 1R (dulu 1.5R
                                      #   v4.22) -> tutup 75% posisi,
                                      #   SL langsung +1R
    "tp1_close_pct": 75.0,           # v4.12 persen ditutup di TP1 (75%)
    "tp2_rr": 4.0,                   # v4.12 sisa posisi jalan ke TP2 =
                                      #   4R; 0 = tanpa TP2 (ride trail)
    "tp2_trail_step_r": 0.2,         # v4.28 (user): setelah TP1 SL
                                      #   trailing tiap 0.2R (ratchet)
    "tp1_lock_r": 0.0,               # v4.28 (user): setelah TP1 -> SL
                                      #   LANGSUNG ke BEP (0 = entry)
    "bep_at_r": 1.0,                 # v4.25 (rumus user): floating +1R
    "bep_offset_r": 0.0,             #   sebelum TP1 -> SL geser ke BEP
    "adx_filter": 1,                 # v4.26 (permintaan user): ADX M15
    "adx_min": 25.0,                 #   wajib > 25 -- sideways di-skip
    "adx_period": 14,
    "msf_enable": 1,                 # v4.29 (user): FILTER STRUKTUR
    "msf_room_atr": 1.0,             #   MARKET: HH/HL + ruang HH/
                                      #   resistance < 1 ATR -> SKIP
                                      #   (belum breakout = jangan
                                      #   beli di bawah puncak)
    "ml_enable": 1,                  # v4.29 (user): FILTER AI/ML
    "ml_min_p": 0.30,                #   lokal (belajar riwayat 1-3
                                      #   thn: struktur, EMA, ADX,
                                      #   breakout, jam); v1 hanya
                                      #   blokir ekor terburuk
                                      #   (p < 0.30); naikkan utk
                                      #   lebih ketat
    "ml_window": 120,
    "min_entry_lot": 0.04,           # v4.16 (user pilih opsi A): entry
                                      #   WAJIB lot >= 0.04 -> pecahan
                                      #   TP 75/25 tetap jalan (0.03+0.01)
    "tp_money_usd": 0.0,             # CADANGAN (kalau tp_rr = 0): TP
                                      #   minimal uang 20 USD (Rp360.000)
    "tp_mode": "close",              # v3.82 (permintaan user) "close" =
                                      #   sentuh TP -> LANGSUNG close, TANPA
                                      #   trailing; "trail" = lama: SL
                                      #   dikunci +20 & trailing lanjut
    "tp_broker_hard": True,           # v3.99 FIX "TP KELLEWATAN/TELABAT"
                                      #   (laporan user): TP 2R dipasang
                                      #   DI SERVER BROKER -> eksekusi
                                      #   INSTAN saat disentuh (dulu TP
                                      #   virtual = engine polling, harga
                                      #   sentuh 2R lalu rebound sebelum
                                      #   engine close -> profit berkurang).
                                      #   Hard TP khusus tp_mode "close";
                                      #   mode "trail" otomatis virtual.
                                      #   (cadangan lama: exit TEPAT 20)
    "max_positions": 3,               # max 3 PAIR terbuka bersamaan (user)
    "max_open_pairs": 3,              # alias eksplisit utk gerbang S2
    "trail_be_at_r": 0,               # OFF: BE trailing S1 bentrok dgn ATR trail
    "money_trail_enabled": False,     # OFF di S2 (SL dikelola ATR trail)
    "basket_tp_enabled": False,       # OFF di S2 (tidak ada TP profit di EA)
    "smart_exit_enabled": False,      # OFF di S2
    "s3": {  # ===== PARAMETER STRATEGY 4 DIKOSONGKAN (user isi baru) =====
             # taruh parameter angka strategi baru di sini, contoh:
             #   "ema_fast": 13, "ema_slow": 21, "snr_strength": 3
             },
    "tp_r": 1.0,                      # (tidak dipakai S2; TP=0 dari ATR spec)
    "tp_body_pos": 0.4,               # v3.16: posisi TP di BATANG lilin SNR
                                      #   0=tepi batang sisi-dekat, 0.5=tengah
                                      #   batang, 1=tepi jauh (bukan wick!)
    "tp_min_rr_net": 0.6,             # v3.16: RR BERSIH minimal (TP sudah
                                      #   dikurangi spread+komisi); kurang -> SKIP
    "money_trail_start_usd": 2.0,     #   net >= 2 USD (~Rp36.000) -> SL
                                      #   digeser mengunci net 1 USD
    "money_trail_step_usd": 1.0,      #   tiap net nambah 1 USD -> geser lagi
    "basket_tp_usd": 5.0,             #   semua posisi >= 5 USD (~Rp90.000)
                                      #   -> tutup SEMUA posisi seketika
    "smart_exit_min_profit_usd": 0.0, #   syarat minimal profit (USD) utk
                                      #   boleh TP dini di zona
    "rej_filter_enabled": True,       # v3.34: larang entry melawan candle
                                      #   rejection M15 valid + arah EMA
    "rej_wick_body_min": 2.0,         #   sumbu >= 2x body = rejection valid
    "rej_wick_range_pct": 0.5,        #   sumbu >= 50% range candle
    "manage_manual_positions": True,  # v3.26: posisi ENTRY MANUAL Anda juga
                                      #   diikuti trailing/MTRAIL/basket/
                                      #   smart exit (dashboard ditandai
                                      #   MANUAL). false = hanya posisi bot
    "force_min_lot_entry": True,      # v3.21: SL lebar TIDAK skip entry ->
                                      #   pakai lot minimum (momentum valid
                                      #   tetap masuk)
    "max_risk_overrun_x": 3.0,        #   pengaman: risiko efektif lot min
                                      #   maks 3x target risiko, lebih -> SKIP
    "trade_enabled": True,            # kill-switch global (bisa juga dari dashboard)
    # ---- PELINDUNG ANTI SL-BERUNTUN (v3.06) ----
    "day_tz_offset": 7.0,             # v3.69: KUNCI WIB (UTC+7), permintaan
                                      #   user: reset kartu & stop harian =
                                      #   tengah malam WIB (Jakarta) =
                                      #   pukul 01:00 waktu Mataram (WITA)
    "sniper_m5_need_bars": 12,
    "zone_pivot_lb": 3,               # v3.41: sniper M5 scan zona HH/HL S/R
    "zone_near_atr": 0.40,            #   jarak "dekat zona" (x ATR M5)
    "zone_breakout_atr": 0.30,        #   tembus valid = >0.30 ATR di luar zona
    "zone_pull_atr": 0.60,            #   ketinggian rebound/dip min utk re-entry
    "sniper_m5_min_score": 55.0,      # v3.39: skor sinyal M15 minimal saat
                                      #   entry utk sniper 3 tahap jalan        # v3.38: sniper 2 lapis - konfirmasi
                                      #   momentum M5 sebelum presisi M1
    "cooldown_after_sl_min": 30,      # v3.35: pair yang MINUS -> cooldown
                                      #   30 menit (satu2nya filter jeda)
                                    # v3.35: kuota entry/hari DIHAPUS
    "max_consec_losses": 3,           # 3 SL beruntun global ->
    "consec_pause_min": 240,          #   robot jeda otomatis 4 jam
    "entry_max_extension_atr": 1.2,   # di sniper: pullback > 1.2 ATR = momentum
                                      #   hilang -> tunggu sinyal M15 baru
    "trade_hours_utc": [7, 20],       # forex/metals/indeks: 07:00-20:00 UTC saja
    "max_per_cluster": 2,             # maks 2 posisi dalam 1 klaster korelasi
    "correlation_clusters": {
        "LOGAM": ["XAUUSD", "XAGUSD"],
        "KRIPTO": ["BTCUSD", "ETHUSD"],
        "INDEKS": ["NAS100", "US30", "USTEC", "GER40"],
        "ENERGI": ["USOIL", "UKOIL", "WTI"],
    },
    # ---- ANALISIS ----
    "atr_period": 14,
    "hvn_bars": 200,                  # bar M15 untuk volume profile
    "zone_proximity_atr": 0.20,       # jarak maks ke HVN (x ATR)
    "bars_m15": 300,
    "bars_m5": 200,
    "bars_m1": 120,
    "scan_interval_sec": 5.0,
    "rates_refresh_sec": 15.0,         # S2: scan berat tiap 15 dtk (entry M5-close jangan telat 60 dtk)
    # ---- MODE DEMO (hanya jalan kalau MT5 tidak tersedia -> SIMULASI) ----
    "sim_force_signals": True,        # tiap ~45 dtk paksa 1 sinyal supaya dashboard hidup
    "sim_start_balance": 10000.0,
    "sim_account_currency": "USD",
}


class CCConfig:
    """Dict-like config dengan override JSON + env CC_CONFIG."""

    def __init__(self, path: str = None):
        vals = dict(DEFAULTS)
        cands = [path, os.environ.get("CC_CONFIG"), "cc_config.json"]
        for p in cands:
            if p and os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    vals.update(json.load(f))
                break
        self._vals = vals

    def __getattr__(self, k):
        try:
            return self._vals[k]
        except KeyError:
            raise AttributeError(k)

    def get(self, k, d=None):
        return self._vals.get(k, d)

    def as_dict(self) -> dict:
        return dict(self._vals)

    def keys(self):
        """Hardening: dict(cfg) & iterasi TIDAK crash lagi (bug v3.66
        S1: dict(CCConfig) -> TypeError not iterable -> entry skor
        kuat gagal di early lane)."""
        return list(self._vals.keys())

    def __getitem__(self, k):
        return self._vals[k]

    def __iter__(self):
        return iter(self._vals)

    def __len__(self):
        return len(self._vals)
