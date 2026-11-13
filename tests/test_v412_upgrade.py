# -*- coding: utf-8 -*-
"""v4.12: RESCUE cross EMA valid + ANTI-zona-palsu + bonus skor tren.

  - EMA13/21 M15 SUDAH bersilangan searah sinyal (dlm lookback) =
    tren valid -> konteks EMA tidak memblokir + bonus skor.
  - Zona dari pivot tanpa rejection nyata (wick/leg kecil) dibuang.
  - Merge pivot selevel = satu zona (bukan mikro-zona palsu).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_strategy3 as S            # noqa: E402


def test_versi():
    assert C.CC_VERSION >= "4.12"


def test_bonus_skor_tren_valid_default():
    assert float(S.DEFAULTS["w_ema_cross"]) == 8.0
    assert int(S.DEFAULTS["ema_cross_lookback"]) == 5


def test_cross_valid_naik_dan_turun():
    # naik -> koreksi (gap EMA negatif) -> pulih kuat: cross-up di ekor
    up = [100.0 + 0.5 * i for i in range(30)]
    up += [up[-1] - 0.5 * i for i in range(1, 15)]
    up += [up[-1] + 1.2 * i for i in range(1, 7)]
    cu, cd = S.ema_cross_state(up, 13, 21, 5)
    assert (cu, cd) == (True, False), (cu, cd)
    # cermin: cross-down
    dn = [230.0 - x for x in up]
    cu2, cd2 = S.ema_cross_state(dn, 13, 21, 5)
    assert (cu2, cd2) == (False, True), (cu2, cd2)
    # cross lama (sudah > lookback bar) tidak dihitung
    old = up + [up[-1]] * 6
    cu3, cd3 = S.ema_cross_state(old, 13, 21, 5)
    assert (cu3, cd3) == (False, False), (cu3, cd3)


def test_pivot_wick_kecil_ditolak_leg_kecil_ditolak():
    # range kecil konsisten -> tanpa rejection nyata -> nol zona
    rows = []
    p = 100.0
    for i in range(60):
        c = p + 0.2 if i % 2 == 0 else p - 0.2
        rows.append((p, p + 0.05, c - 0.05, c))
        p = c
    bars = {"time": list(range(60)),
            "open": [r[0] for r in rows], "high": [r[1] for r in rows],
            "low": [r[2] for r in rows], "close": [r[3] for r in rows],
            "tick_volume": [1] * 60}
    a = S.atr_at(bars, 14)
    assert S.detect_zones(bars, a, {}, 58) == []
