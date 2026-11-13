# -*- coding: utf-8 -*-
"""v4.20 + v4.21: TANGGA TP anti-lolos.

  - TP2 (4R) dicek PALING AWAL: spike tembus 4R = CLOSE PENUH sekarang
    (tidak sempat turun jadi partial TP1 dulu).
  - TP1 tersentuh -> partial 75% (lot kecil = full, aman).
  - Setelah TP1: SL di-lock +1R lalu naik 0.5R per kenaikan peak
    (ratchet; pakai peak sebenarnya dr M1, spike termasuk).
Fungsi murni tp_ladder_decision -> tanpa broker.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_strategy3 as S            # noqa: E402
from types import SimpleNamespace   # noqa: E402


def _tr(**kw):
    d = dict(side=1, entry=100.0, risk_dist=1.0, tp_dist=2.0,
             tp2_dist=4.0, trail_step_r=0.2, tp1_lock_r=0.0, tp_r=2.0,
             peak=0.0, last_sl_r=None, tp1_hit=0, bep_at_r=1.0,
             bep_offset_r=0.0)
    d.update(kw)
    return SimpleNamespace(**d)


def _lad(tr, tp1_touched=False, tp2_touched=None, peak_r=None,
         lot=0.10, vol_min=0.01, vol_step=0.01):
    # harga konsisten dgn peak: pk (R) x risk_dist dari entry
    pk = peak_r if peak_r is not None else float(tr.peak)
    px = tr.entry + pk * float(tr.risk_dist)
    return S.tp_ladder_decision(tr, px, px,
                                tp1_touched, lot, vol_min, vol_step,
                                tp2_touched=tp2_touched, peak_r=peak_r)


def test_versi():
    assert C.CC_VERSION >= "4.20"


def test_tp2_tercapai_langsung_close_penuh():
    a = _lad(_tr(tp1_hit=0), tp2_touched=True)
    assert a == {"action": "full", "code": "EXIT_TP2"}, a
    # bahkan saat TP1 juga tersentuh di siklus sama -> TP2 menang
    b = _lad(_tr(tp1_hit=0), tp1_touched=True, tp2_touched=True)
    assert b["action"] == "full" and b["code"] == "EXIT_TP2", b


def test_tp1_partial_75_dan_lock_bukan_bep():
    a = _lad(_tr(tp1_hit=0), tp1_touched=True)
    assert a["action"] == "partial", a
    assert a["volume"] > 0 and a["remain"] > 0
    # lot kecil tak bisa dipecah -> full (perilaku lama yang aman)
    b = _lad(_tr(tp1_hit=0), tp1_touched=True, lot=0.01)
    assert b == {"action": "full", "code": "EXIT_TP"}, b


def test_bep_sebelum_tp1_tidak_menunda_tp1():
    # v4.25: BEP di 1R hanya saat TP1 BELUM tersentuh siklus ini
    a = _lad(_tr(tp1_hit=0), tp1_touched=False, peak_r=1.0)
    assert a == {"action": "sl", "sl_r": 0.0}, a
    b = _lad(_tr(tp1_hit=0), tp1_touched=True, peak_r=1.0)
    assert b["action"] == "partial", b


def test_pasca_tp1_bep_lalu_trail_02r_dari_peak():
    # v4.31 (user): setelah TP1 SL LANGSUNG BEP, lalu tiap 0.2R peak
    tr = _tr(tp1_hit=1, last_sl_r=0.0)      # SL saat ini = BEP
    # peak 2.3R: n = int((2.3-2.0)/0.2) = 1 -> sl 0.2 > last 0.0
    a = _lad(tr, peak_r=2.3)
    assert a == {"action": "sl", "sl_r": 0.2}, a
    # peak 2.6R: n = 3 -> sl 0.6
    b = _lad(tr, peak_r=2.6)
    assert b["action"] == "sl" and abs(b["sl_r"] - 0.6) < 1e-9, b
    # peak 3.1R: n = 5 -> sl 1.0
    c = _lad(tr, peak_r=3.1)
    assert c == {"action": "sl", "sl_r": 1.0}, c
    # ratchet: jangan mundur
    tr2 = _tr(tp1_hit=1, last_sl_r=1.0)
    d = _lad(tr2, peak_r=2.6)
    assert d == {"action": "none"}, d


def test_peak_tersampel_dipakai_saattidak_ada_peak_r():
    tr = _tr(tp1_hit=1, last_sl_r=0.2, peak=2.7)
    a = _lad(tr)                            # n = int(0.7/0.2) = 3 -> 0.6
    assert a["action"] == "sl" and abs(a["sl_r"] - 0.6) < 1e-9, a
