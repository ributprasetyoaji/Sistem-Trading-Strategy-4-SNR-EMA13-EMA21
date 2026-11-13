# -*- coding: utf-8 -*-
"""v4.25 (rumus user): floating >= 1x jarak SL (1R) SEBELUM TP1 ->
SL geser ke BEP.  Di siklus yang sama TP1 tersentuh -> lewat (partial
+ lock +1R, lebih baik dari BEP; TP1 tidak boleh tertunda).  Ratchet
dgn last_sl_r.  Dua penggerak: ATR-trail paralel (engine) + ladder
BEP (tp_ladder_decision) -> hasil "BEP atau lebih baik".
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_strategy3 as S            # noqa: E402
from types import SimpleNamespace   # noqa: E402


def _tr(**kw):
    d = dict(side=1, entry=100.0, risk_dist=1.0, tp_dist=1.5,
             tp2_dist=4.0, trail_step_r=0.2, tp1_lock_r=0.0, tp_r=1.5,
             peak=0.0, last_sl_r=None, tp1_hit=0, bep_at_r=1.0,
             bep_offset_r=0.0)
    d.update(kw)
    return SimpleNamespace(**d)


def _lad(tr, tp1_touched=False, peak_r=None):
    pk = peak_r if peak_r is not None else float(tr.peak)
    px = tr.entry + pk * float(tr.risk_dist)
    return S.tp_ladder_decision(tr, px, px,
                                tp1_touched, 0.10, 0.01, 0.01,
                                tp2_touched=None, peak_r=peak_r)


def test_versi():
    assert C.CC_VERSION == "4.31"


def test_kunci_default_terpasang():
    for k, v in (("bep_at_r", 1.0), ("bep_offset_r", 0.0)):
        assert k in C.DEFAULTS and abs(float(C.DEFAULTS[k]) - v) < 1e-9
        assert k in S.DEFAULTS and abs(float(S.DEFAULTS[k]) - v) < 1e-9


def test_1r_sebelum_tp1_sl_ke_bep():
    a = _lad(_tr(), tp1_touched=False, peak_r=1.0)
    assert a == {"action": "sl", "sl_r": 0.0}, a      # BEP tepat


def test_di_bawah_1r_tidak_ada_aksi():
    a = _lad(_tr(), peak_r=0.95)
    assert a == {"action": "none"}, a


def test_ratchet_tidak_mundur_dari_bep():
    tr = _tr(last_sl_r=0.0)                            # sudah BEP
    a = _lad(tr, peak_r=1.2)
    assert a == {"action": "none"}, a                  # 0.0 > 0.0? tidak


def test_tp1_tersentuh_di_siklus_sama_menang_dari_bep():
    a = _lad(_tr(), tp1_touched=True, peak_r=1.0)
    assert a["action"] == "partial", a                 # bukan menunda TP1


def test_pasca_tp1_bep_dan_trail_02r_jalan():
    tr = _tr(tp1_hit=1, last_sl_r=0.0)
    a = _lad(tr, peak_r=2.0)      # n=int((2.0-1.5)/0.2)=2 -> BEP+0.4R
    assert a["action"] == "sl" and abs(a["sl_r"] - 0.4) < 1e-9, a


def test_engine_pasang_attr_bep_di_entry_dan_seed():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert src.count("bep_at_r") >= 3, src.count("bep_at_r")
    assert "SL dikunci" in src          # log netral v4.25
    st3 = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_strategy3.py"),
               encoding="utf-8").read()
    # ladder BEP tepat SEBELUM jalur tp1_hit (aturan urutan v4.25)
    i_bep = st3.index("bep_at > 0 and not (tp1_touched and tp1_d > 0)")
    i_tp1 = st3.index("tp1_touched and tp1_d > 0",
                      i_bep + 10)      # kemunculan ke-2 = jalur TP1
    assert i_bep < i_tp1, (i_bep, i_tp1)
