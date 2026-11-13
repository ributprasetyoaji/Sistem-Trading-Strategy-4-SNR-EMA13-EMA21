# -*- coding: utf-8 -*-
"""MARKET GUARD (permintaan user, KETIGA strategy):
1. SKIP entry 1 jam sebelum penutupan akhir pekan -> aktif lg otomatis
   saat pembukaan market.
2. SKIP semua entry 30 menit sebelum daily rollover/market break.
Minggu referensi: Jumat 2026-10-02, Sabtu 03, Minggu 04, Senin 05."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import market_guard as MG  # noqa: E402

K = dict(MG.DEFAULTS)


def ep(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp()


def blocked(sym, ts, k=None):
    return MG.entry_blocked(sym, k or K, ts)


def test_jumat_sebelum_guard_pass():
    blk, _, _ = blocked("EURUSD", ep(2026, 10, 2, 19, 0))
    assert blk is False


def test_jumat_satu_jam_sebelum_tutup_block():
    blk, code, _ = blocked("EURUSD", ep(2026, 10, 2, 20, 30))
    assert blk is True and code == "SKIP_SESSION"


def test_sabtu_block_dan_minggu_dini_hari_block():
    for ts in (ep(2026, 10, 3, 12, 0), ep(2026, 10, 4, 4, 0)):
        blk, code, _ = blocked("XAUUSD", ts)
        assert blk is True and code == "SKIP_SESSION"


def test_minggu_sudah_buka_aktif_lagi():
    blk, _, _ = blocked("EURUSD", ep(2026, 10, 4, 23, 0))
    assert blk is False                       # auto AKTIF LAGI saat buka


def test_hari_kerja_pass():
    for ts in (ep(2026, 10, 5, 10, 0), ep(2026, 10, 1, 23, 50),
               ep(2026, 10, 5, 14, 0)):
        blk, _, _ = blocked("EURUSD", ts)
        assert blk is False


def test_kripto_247_bebas_guard_akhir_pekan():
    for sym in ("BTCUSD", "ETHUSDm", "SOLUSD"):
        blk, _, _ = blocked(sym, ep(2026, 10, 3, 12, 0))
        assert blk is False


def test_rollover_30_menit_block_non_kripto():
    # v3.70: rollover hanya utk pair BUKA 24/7-kripto (kripto tak punya
    # market break -- permintaan user: sabtu minggu crypto tetap aktif)
    for sym in ("EURUSD", "XAUUSD", "USOIL"):
        blk, code, _ = blocked(sym, ep(2026, 10, 5, 20, 45))
        assert blk is True and code == "SKIP_ROLLOVER", (sym, code)
    blk, code, _ = blocked("EURUSD", ep(2026, 10, 5, 21, 2))
    assert blk is True and code == "SKIP_ROLLOVER"
    # kripto: bebas rollover kapan pun
    for sym in ("BTCUSD", "ETHUSD"):
        blk, _, why = blocked(sym, ep(2026, 10, 5, 20, 45))
        assert blk is False, (sym, why)

def test_config_disabled_pass():
    k = dict(K, enabled=False)
    for ts in (ep(2026, 10, 3, 12, 0), ep(2026, 10, 5, 20, 45)):
        blk, _, _ = blocked("EURUSD", ts, k)
        assert blk is False


def test_config_custom_jam_broker():
    k = dict(K, weekend_close_utc="22:00", rollover_utc="22:00",
             rollover_skip_before_min=30)
    blk, code, _ = blocked("EURUSD", ep(2026, 10, 2, 20, 59), k)
    assert blk is False                       # weekend mulai 21:00, rollover 21:30
    blk, code, _ = blocked("EURUSD", ep(2026, 10, 2, 21, 31), k)
    assert blk is True and code == "SKIP_SESSION"


def test_hhmm_salah_tidak_raise():
    k = dict(K, weekend_close_utc="xx", rollover_utc="")
    blk, _, _ = blocked("EURUSD", ep(2026, 10, 3, 12, 0), k)
    assert blk is True                        # fallback default tetap aman


# ============ v3.70: KRIPTO 24/7 (permintaan user) ====================
# "kan sabtu minggu pair crypto tetap aktif seharusnya" -- kripto bebas
# akhir pekan DAN bebas rollover (tidak punya market break).  Non-kripto
# tetap diblokir keduanya.

def test_kripto_sabtu_minggu_bebas_penuh():
    for ts in (ep(2026, 10, 3, 12, 0),      # Sabtu siang
               ep(2026, 10, 3, 20, 50),     # Sabtu: dulu kena rollover (BUG)
               ep(2026, 10, 4, 21, 30),     # Minggu: dulu kena rollover (BUG)
               ep(2026, 10, 4, 23, 0)):     # Minggu malam
        for sym in ("BTCUSD", "ETHUSD", "SOLUSD"):
            blk, code, why = blocked(sym, ts)
            assert blk is False, (sym, ts, why)


def test_kripto_hari_kerja_bebas_rollover():
    # Rabu 20:50 UTC = jendela rollover -> non-kripto BLOK, kripto BEBAS
    # (Jumat 20:50 sudah masuk jendela weekend, bukan rollover)
    ts = ep(2026, 9, 30, 20, 50)
    blk, _, why = blocked("XAUUSD", ts)
    assert blk is True and "ROLLOVER" in why, why
    for sym in ("BTCUSD", "ETHUSD"):
        blk, _, why = blocked(sym, ts)
        assert blk is False, (sym, why)


def test_non_kripto_weekend_tetap_diblokir():
    blk, code, _ = blocked("XAUUSD", ep(2026, 10, 3, 12, 0))
    assert blk is True and code == "SKIP_SESSION"
    blk, code, _ = blocked("EURUSD", ep(2026, 10, 4, 12, 0))
    assert blk is True and code == "SKIP_SESSION"
