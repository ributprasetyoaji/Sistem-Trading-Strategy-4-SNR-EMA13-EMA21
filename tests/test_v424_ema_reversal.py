# -*- coding: utf-8 -*-
"""v4.24 (rumus user): REVERSAL EMA13/21 -> SKIP.

  SKIP BUY bila EMA13 tadinya jelas DI ATAS EMA21 (gap >= 0.10 ATR,
  lookback 5 bar), kini melandai turun AKAN/SUDAH cross EMA21
  (gap kini <= 0.15 ATR dan mengecil), sementara candle close DI
  BAWAH EMA13 dan DI BAWAH EMA21.  SKIP SELL = cermin.
  Bar closed saja (tanpa look-ahead); fail-open data kurang.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_strategy3 as S            # noqa: E402

ATR = 1.0


def _dwn_closes():
    """EMA13 dari atas turun menuju EMA21, candle di bawah keduanya."""
    c = [100.0 + 0.30 * i for i in range(25)]      # naik -> gap besar
    c += [c[-1]] * 30                              # flat: gap mulai mematus
    for i in range(4):                             # ekor turun kecil:
        c.append(c[-1] - 0.10)                     #   close di bawah EMA
    return c


def test_versi():
    assert C.CC_VERSION >= "4.24"


def test_kunci_default_terpasang():
    assert int(S.DEFAULTS["ema_rev_enable"]) == 1
    assert int(S.DEFAULTS["ema_rev_lookback"]) == 5
    assert abs(float(S.DEFAULTS["ema_rev_was_gap_atr"]) - 0.10) < 1e-9
    assert abs(float(S.DEFAULTS["ema_rev_gap_atr"]) - 0.15) < 1e-9


def test_skip_buy_reversal_turun():
    c = _dwn_closes()
    # pastikan kondisi memang terpenuhi pada data ini
    ef = S.ema_series(c, 13)
    es = S.ema_series(c, 21)
    n = min(len(ef), len(es))
    gp = (ef[-1 - 5] - es[-1 - 5]) / ATR
    gn = (ef[-1] - es[-1]) / ATR
    assert gp >= 0.10 and gn <= 0.15 and gn < gp, (gp, gn)
    assert c[-1] < ef[-1] and c[-1] < es[-1]
    blok, why = S.ema_reversal_block(1, c, ATR, {})
    assert blok is True and "SKIP_EMA_REVERSAL" in why, (blok, why)


def test_skip_sell_cermin():
    c = [200.0 - x for x in _dwn_closes()]
    blok, why = S.ema_reversal_block(-1, c, ATR, {})
    assert blok is True and "SKIP_EMA_REVERSAL" in why, (blok, why)
    # arah salah tidak diblok: data dwn tdk memblokir SELL
    blok2, _ = S.ema_reversal_block(-1, _dwn_closes(), ATR, {})
    assert blok2 is False


def test_tren_sehat_tidak_diblok():
    # uptrend konsisten (gap besar & TIDAK mengecil) -> BUY lolos
    c = [100.0 + 0.30 * i for i in range(70)]
    assert S.ema_reversal_block(1, c, ATR, {}) == (False, "")
    c2 = [170.0 - 0.30 * i for i in range(70)]
    assert S.ema_reversal_block(-1, c2, ATR, {}) == (False, "")


def test_bisa_dimatikan_dan_failopen():
    c = _dwn_closes()
    assert S.ema_reversal_block(1, c, ATR,
                                {"ema_rev_enable": 0}) == (False, "")
    assert S.ema_reversal_block(1, c[:10], ATR, {}) == (False, "")
    assert S.ema_reversal_block(1, [], ATR, {}) == (False, "")


def test_wiring_evaluat_setelah_pintu_cross_valid():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_strategy3.py"),
               encoding="utf-8").read()
    i_ema = src.index('res["block_why"] = "SKIP_TREND: EMA13/21')
    i_rev = src.index("ema_reversal_block(side, tail.get")
    i_adx = src.index("_axb, _axw = adx_gate(")
    assert i_ema < i_rev < i_adx, (i_ema, i_rev, i_adx)
