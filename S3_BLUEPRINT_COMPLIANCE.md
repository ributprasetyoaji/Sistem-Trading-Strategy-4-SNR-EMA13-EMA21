# KEPATUHAN BLUEPRINT -- RBT Fingerprint Trading System (Strategy 3)

Engine: `python/cc_strategy3.py` v1.4 (audit) | Infra: Command Center v3.83
Blueprint: RBT_Fingerprint_Trading_System_Blueprint.txt (63 seksi)
Audit: 2026-10-02 MENYELURUH pasca v1.2 (riwayat dalam) + v1.3 (TP close)
+ v1.4 (TP RR 1:2). 110 test hijau.
Kepatuhan (65 baris cek / 63 seksi): **37 FULL** / 3 FULL+USER-OVERRIDE
(s.32-34, permintaan eksplisit pemilik) / 3 FULL+PARTIAL / 3 FULL+ENGINE /
9+1 ENGINE / 3 OPT (opsional blueprint) / 5 RESEARCH (pisah live-vs-riset
s.57) / 1 PARTIAL

| Seksi Blueprint | Status | Catatan |
|---|---|---|
| 1. System Architecture (20 modul) | FULL (digabung modular) | Implementasi fungsional dalam cc_strategy3.py + infra Command Center; pemisahan file per-modul = bentuk, bukan substansi. |
| 2. Timeframe Responsibility (H1/M15/M5/M1) | FULL | h1_regime (konteks saja), setup M15 (zona/struktur/fp/skor/SL/TP), momentum M5, trigger M1; H1 tidak pernah memicu entry. |
| 3. Historical Data Engine | FULL+PARTIAL | **AUDIT v1.2**: hist_paged tarik M15 berhalaman s/d 35.040 bar (config; 105.000 = 3 th), AUTO kedalaman broker, lanjut dari cache, TANPA synthetic candles. Metadata ke strategy: hist_years/db_bars/pending. PARTIAL: subset field metadata s.3 (data_start/end, missing_bars, source) -> riset. |
| 3. Data Quality | FULL | data_quality(): urutan/duplikat/high<low/open-close di luar range/sinkron TF/feed basi -> SKIP_DATA_QUALITY (blokir sebelum apapun). |
| 3. Timezone | ENGINE | Storage UTC; rekap & risiko harian 00:00 WIB via engine (day_tz_offset 7.0, terkunci WIB). |
| 4. Feature Engineering | FULL | candle_feats(): body/range/wick/close_pos/direction + normalisasi ATR; EMA13/21 + slope + separation. |
| 5. Market Structure | FULL | swings() pivot konfirmasi + structure_state(): HH/HL/LH/LL, swing ref utk SL; tanpa future confirmation. |
| 6. Zone Engine | FULL | detect_zones(): range dua sisi, touches per KUNJUNGAN, rejection_count, breakout_status, htf_align, status FRESH/VALID/WEAK/EXHAUSTED/INVALID, invalidasi CLOSE menembus, MAX 3 = prioritas (ke-4 = kandidat breakout). |
| 7. Reversal Setup | FULL | evaluate(): harga di/dekat zona + semua gerbang; tolak tengah range via pad & gerbang skor. |
| 8. Breakout Setup | FULL | Cabang breakout: CLOSE melewati batas (wick bukan breakout), no-chase max 1 ATR dari zona. |
| 9. Fingerprint Engine | FULL | fp_vector 5-candle x6 fitur, fp_similarity kontinu 0-100 (BUKAN probabilitas), win_rate/win1_rate/MAE/MFE tersimpan; sample size menurunkan confidence & gerbang SKIP_SAMPLE_SIZE. v1.2: DB kached inkremental (fp_match_cached) utk riwayat dalam, tanpa leakage (horizon pending). |
| 10. Historical Outcome Engine | FULL+PARTIAL | _fp_outcome(): +2R sebelum -1R (win2), +1R (win1), MFE/MAE; horizon 24 bar; bebas leakage (teruji). PARTIAL: metrik waktu (time-to-1R/2R/SL) -> riset. |
| 11. Setup vs Execution Score | FULL | Skor setup berbobot (zona/struktur/EMA/fp/regime); execution = validate_execution (SL room, TP room, spread, chase, portfolio). |
| 12. M5 Momentum | FULL | Displacement 2-candle searah ATAU reclaim/retest-hold; belum ada -> HOLD (setup tidak dibatalkan 1 candle buruk). |
| 13. M1 Precision | FULL | Micro HL/LH dalam jendela + candle trigger searah; noise mikro tidak menghancurkan setup M15 (via pending/expiration, bukan reject instan). |
| 14. Pre-Trade Analyzer (20 cek) | FULL | validate_execution(): zona/setup/fp/trend/M5/M1 di evaluate; SL room, TP 2R room, zona lawan, no-chase, spread, portfolio, daily lock (engine), data quality, cooldown, warmup. |
| 15. SL Engine | FULL | SL = struktur (tepi zona / swing ref) +/- buffer ATR; min 0,45 ATR & max 2,5 ATR; tidak ada SL poin tetap. |
| 16. R Multiple | FULL | risk_dist = jarak SL awal (via sl_mult_eff = SL aktual); BEP/trailing/peak/floor/TP RR semua dalam satuan R; teruji eksak. |
| 17. TP / Reward Engine | FULL | **AUDIT v1.4**: base_rr 2.0 utk cek RUANG (SKIP_TP_BLOCKED, buffer zona lawan); TP aktual = tp_rr x jarak SL (RR 1:2, sesuai header blueprint "initial target RR 1:2"); "2R bukan TP final" berlaku di mode trail (lihat s.32-34). |
| 18. Dynamic Lot per Pair | ENGINE | risk.calc_lot per pair (tick value/point per simbol, normalisasi min/step/max broker). |
| 19. Risk Per Trade | ENGINE+CONFIG | risk_pct 0.5% (config), dipisah dari daily loss (10%). |
| 20. Portfolio Risk | FULL+ENGINE | max_baskets 5 (1/pair via engine can_open; engine set 3 = lebih ketat dari batas 5), max_total_open_risk_pct 2.75% -> SKIP_TOTAL_EXPOSURE / SKIP_MAX_POSITIONS (keep=True). |
| 21. Daily Loss Engine | ENGINE | daily_loss_pct 10.0 = LOCK keras; reset 00:00 WIB; equity-based monitor (engine v3.66+). |
| 22. Drawdown Protection | ENGINE | Peak equity/drawdown tracking + halt (engine cc_risk). |
| 23. Spread Filter | FULL | Per-pair spread_points + default; SKIP_SPREAD. |
| 24. Slippage Filter | OPT | Pre-check tidak tersedia via bridge file MT4; eksekusi pasar + retry/audit engine. Dicatat jujur. |
| 25. Commission/Cost Model | ENGINE | Komisi broker masuk rekap harian & RR bersih (engine); costs realistis saat live. |
| 26. News Filter | OPT | Opsional di blueprint; belum aktif (tanpa feed kalender). Slot config siap. |
| 27. Session Filter | FULL (fitur) | session_of(): ASIA/LONDON/LONDON_NY/NEW_YORK dicatat di journal entry + exit + ORDER_EMITTED (analisa performa per sesi). |
| 28. No-Trade Conditions | FULL | Gerbang aktif semua berkode: NO_ZONE (WAIT+why), FINGERPRINT, SAMPLE_SIZE, TREND, SL_TOO_TIGHT/WIDE, TP_BLOCKED, CHASING, SPREAD, MAX_POSITIONS, TOTAL_EXPOSURE, DATA_QUALITY, ZONE_EXHAUSTED, SETUP_EXPIRED + engine (daily/drawdown/pair-open/jendela pasar v3.86: SKIP_SESSION & SKIP_ROLLOVER). Momentum/M1 = HOLD (desain s.12/13), bukan reject. |
| 29. No-Chase Engine | FULL | Jarak entry dari TEPI zona > max_entry_distance_atr -> SKIP_CHASING (teruji). |
| 30. Setup Expiration | FULL | setup_expiration_bars 8 -> SKIP_SETUP_EXPIRED; setup hangus butuh event baru. |
| 31. State Machine | FULL (subset status) | WAIT/WAITING, HOLD (MOMENTUM_WAIT/ENTRY_ARMED), BLOCKED (SKIP/RISK_LOCKED), READY->ORDER, TRADING (POSITION_OPEN), fase trail INITIAL/BEP/TRAIL, cooldown (REENTRY_WAIT), EXPIRED. |
| 32. BEP+ di +1R | FULL + USER-OVERRIDE | ATRTrail: trigger 1.0R -> floor = +0.10R (buffer spread+komisi); ratchet; teruji eksak. Mode "trail" = blueprint penuh. DEFAULT sekarang "close" (user): posisi tamat di TP sebelum BEP relevan. |
| 33. +2R Trailing | FULL + USER-OVERRIDE | Mode "trail" = blueprint penuh: peak-1R ratchet (hybrid R), tanpa close otomatis, teruji. DEFAULT user "close" (2026-10-02): sentuh 2R -> LANGSUNG close, tanpa trailing -- permintaan EKSPLISIT pemilik, configurable (tp_mode), jalur blueprint tetap tersedia. |
| 34. Exit Conditions | FULL + USER-OVERRIDE | SL awal / BEP+ / trailing (mode trail); "tanpa TP tetap setelah +2R" berlaku mode trail. Default user "close": exit di +2R. Kode exit baru EXIT_TP (tambahan di luar daftar s.42, utk override user); kode blueprint lain utuh. |
| 35. Re-Entry Engine | FULL | attempts per zona (maks 2) di state; ditolak -> SKIP_ZONE_EXHAUSTED; entry baru = attempt baru; butuh sinyal valid penuh lagi; attempt tercatat di jurnal. |
| 36. Zone Lifecycle | FULL | FRESH->VALID->WEAK->EXHAUSTED + INVALID + BREAKOUT; eksperimen ke-3 diblok otomatis. |
| 37. Signal Ranking | ENGINE | Scanner dashboard mengurutkan skor; engine eksekusi per pair saat gerbang terbuka (aritektur per-pair, bukan batch). |
| 38. Broker Constraint Engine | ENGINE | calc_lot normalisasi + stops level broker (retry/audit engine); simbol resolve per broker. |
| 39. Live Feed Guard | FULL | data_quality(): sinkron TF, bid/ask, feed basi -> SKIP_DATA_QUALITY (teruji). |
| 40. Correlation Engine | OPT | Opsional; portfolio risk total & 1-pair-1-posisi sudah membatasi korelasi. Slot config siap. |
| 41. Trade Journal | FULL+PARTIAL | **AUDIT v1.4**: entry (zona lengkap: id/type/status/strength/touches/rejections/breakout/htf_align + EMA13/21/sep + ATR + sl_ref + entry/SL/TP/tp_target/opp_zone/room2r + sim/sample/win_rate + hist meta + attempt + spread + regime + SESI) + ORDER_EMITTED (lot, risk_money, sl) + exit (kode, R, peak, MAE, MFE, hold_sec, pl, lot). PARTIAL sisa: commission/slippage per trade, fingerprint_id, reentry flag -> riset. |
| 42. Reason Codes | FULL | ENTRY_APPROVED; SKIP_*: NO_ZONE, FINGERPRINT, SAMPLE_SIZE, TREND, SL_TOO_TIGHT/TOO_WIDE, TP_BLOCKED, CHASING, SPREAD, MAX_POSITIONS, TOTAL_EXPOSURE, DATA_QUALITY, ZONE_EXHAUSTED, SETUP_EXPIRED, DAILY_COOLDOWN (+ engine: daily risk/drawdown/pair-open); HOLD: MOMENTUM_WAIT/M1_WAIT (= SKIP_NO_MOMENTUM/SKIP_NO_M1_TRIGGER dlm bentuk HOLD per s.12/13); EXIT_*: INITIAL_SL, BEP_PLUS, TRAILING, + EXIT_TP (tambahan utk mode close user) + SKIP_SESSION (v3.86: guard jendela akhir pekan -- 1 jam sebelum tutup, auto aktif lg saat buka) + SKIP_ROLLOVER (v3.86: 30 mnt sebelum daily rollover/market break, cegah entry nyangkut; kripto 24/7 bebas guard pekan). OPT blueprint (news/slippage/correlation) menyusul saat fiturnya aktif. |
| 43. Performance Metrics | PARTIAL | Data mentah lengkap di journal (bahan hitung); agregator metrik (PF, expectancy, dsb) = modul riset. |
| 44. MAE/MFE | FULL | tr.mae/tr.mfe live + historis di fp_match; tercatat di journal exit. |
| 45. Adaptive History Confidence | FULL | sample < min -> confidence x0.5 + gerbang SKIP_SAMPLE_SIZE; hist_years mengikuti panjang riwayat broker (v1.2: s/d 1-3 th), db_bars/pending terekspos. |
| 46. Backtest Rules | RESEARCH | Fungsi murni siap-backtest; engine event-driven live. Modul backtest = riset terpisah (s.57). |
| 47. Train/Validation/Test | RESEARCH | Di luar engine live; journal menyediakan data. |
| 48. Monte Carlo | RESEARCH | Di luar engine live. |
| 49. Ablation | RESEARCH | Semua bobot/komponen configurable -> siap ablation di riset. |
| 50. Parameter Configuration | FULL | Semua di blok "s3" cc_config (50 kunci, termasuk tp_rr & tp_mode) + risk_pct/daily_loss level engine. Tidak ada hard-code strategi. |
| 51. Configuration Philosophy | FULL | Parameter set kecil sesuai blueprint (EMA/ATR/SL/seq/threshold/RR/BEP/trail/risk). |
| 52. Safety / Failure Handling | FULL+ENGINE | Bridge timeout -> skip; DQ guard; state persist JSON; broker = source of truth; tanpa resend buta (audit v3.65); close TP gagal -> retry siklus berikut (state trail dipertahankan). |
| 53. Duplicate Order Protection | FULL+ENGINE | 1 posisi/pair (can_open), kandidat di-pop saat entry/gagal, attempt per zona, audit anti-yatim v3.65; retry close TIDAK bisa menghasilkan order ganda (close idempoten per ticket). |
| 54. Logging | ENGINE | Execution Log engine (per baris, tampil di console bat) + CC_SIGNAL.csv + journal JSONL. |
| 55. Dashboard Requirements | ENGINE | Kartu akun/harian/drawdown/komisi, scanner (skor/status/reason), posisi aktif, log eksekusi, grafik per pair, sesi pasar. |
| 56. Research Database | RESEARCH | Journal JSONL = seed database; DB penuh = modul riset. |
| 57. Live vs Research Separation | FULL | Tidak ada kode riset di engine live; live hanya cc_strategy3+infra. |
| 58. Implementation Principles | FULL | Fungsi murni teruji, type-friendly, try/except di titik IO, parameter config, reason codes, 110 test. |
| 59. Coding Agent Rules | FULL | Semua 22 aturan dipatuhi (unit tests, tanpa martingale/averaging -- grep 0, tidak memaksa 5 slot, tidak kejar harga, tidak bypass risk/pretrade; perubahan v1.2-v1.4 TIDAK diam-diam: permintaan user + terdokumentasi + configurable). |
| 60. Master Entry Logic | FULL | Urutan pipeline evaluate->validate persis pseudokode s.60 (DQ gate pertama -> ... -> ENTRY_APPROVED). |
| 61. Master Position Management | FULL | update() trail: peak/floor/BEP/trailing + close virtual + SL broker digeser + TP hard close (mode close) + rencana RR persist (tp_dist/tp_r) + t_entry. |
| 62. Master Re-Entry Logic | FULL | attempts/zone + butuh event baru (evaluate penuh diulang) + cooldown exit. |
| 63. Design Philosophy | FULL | NO ZONE->NO TRADE; QUALITY>QUANTITY; +1R BEP; +2R TRAIL (mode trail); MAX 5 batas (engine 3); 10% lock. Default TP close = pilihan pemilik, tercatat. |

## USER OVERRIDE (BUKAN pelanggaran diam-diam -- §59.3)
- **tp_mode "close"** (default sejak v3.82): target tersentuh -> LANGSUNG
  close tanpa trailing. Permintaan eksplisit pemilik (2026-10-02), wlan
  `"tp_mode": "trail"` mengembalikan perilaku blueprint s.32-34 PENUH.
- **tp_rr 2.0** (v3.83): TP = 2 x jarak SL (RR 1:2) sesuai header blueprint;
  menggantikan acuan uang (tp_money_usd jadi fallback saat tp_rr=0).

## TANDA BESAR
- **FULL** = diimplementasi & teruji di engine live (110 test, smoke OK).
- **FULL+PARTIAL** = inti penuh & teruji; sebagian kecil field/metrik = riset.
- **FULL+ENGINE** = strategi penuh + dijalankan infra Command Center.
- **ENGINE** = dijalankan infrastruktur Command Center yang sudah terbukti.
- **OPT** = opsional di blueprint, slot config tersedia, belum aktif.
- **RESEARCH** = sengaja dipisah dari live sesuai s.57.
- **PARTIAL** = data mentah lengkap; agregator = modul riset.
- **USER-OVERRIDE** = menyimpang dari default blueprint atas permintaan
  EKSPLISIT pemilik; configurable; jalur blueprint tetap tersedia.

## PERUBAHAN v1.1 -> v1.4 (audit trail)
- v1.2: riwayat dalam 1-3 th (hist_paged AUTO, RHIST MT4, fp DB cached
  inkremental, DQ gate, journal exit + sesi) -- layani s.3/s.9/s.45.
- v1.3: tp_mode "close" (USER-OVERRIDE s.32-34).
- v1.4: tp_rr 2.0 = RR 1:2 (s.16/s.17) + rencana TP persist di state.
- Audit: jurnal diperkaya (s.41), EXIT_TP + hold_sec, dok dikoreksi
  (klaim lama yang kedaluwarsa/berlebihan dirapikan).

Tanggal audit: 2026-10-02
