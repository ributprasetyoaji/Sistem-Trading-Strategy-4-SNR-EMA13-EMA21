# -*- coding: utf-8 -*-
"""v4.31 (user): MAX DAILY LOSS DIHAPUS TOTAL -- override-proof.

Akar laporan "belum terhapus": file cc_config.json runtime di VPS
menimpa DEFAULTS repo (masih memuat daily_loss_pct 10) sehingga lock
v4.29 yang masih config-driven tetap hidup.  Kini max daily loss
diputus DI KODE (dlp = 0.0 keras): config apa pun (repo maupun json
VPS) tidak bisa menyalakannya lagi.  Cabang equity-based (daily_equity_
based) + soft 95% juga wajib mati (dulu halt tanpa guard dlp).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_risk as CR                # noqa: E402


def test_versi_dan_kunci_dihapus_dari_defaults():
    assert C.CC_VERSION == "4.31"
    assert "daily_loss_pct" not in C.DEFAULTS, "kunci wajib hilang"


class _B(object):
    def account(self):
        return {"balance": 1000.0, "equity": 1000.0}


def _guard(cfg):
    df = os.path.join(tempfile.mkdtemp(), "day.json")
    return CR.RiskGuard(cfg, _B(), log=lambda *a, **k: None, day_file=df)


def test_json_vps_yang_menimpa_tetap_tidak_mengunci():
    """Simulasi persis akar masalah: config runtime memuat
    daily_loss_pct 10 -- loss $200 (20%) TIDAK boleh mengunci."""
    g = _guard({"daily_loss_pct": 10.0})            # sengaja: spt json VPS
    st = g.daily_status(800.0, realized=-200.0, balance=800.0)
    assert st["halted"] is False, st
    assert st["reason"] != "DAILY_LOSS_LIMIT"
    # bahkan nilai liar sekalipun
    g2 = _guard({"daily_loss_pct": 90.0})
    st2 = g2.daily_status(100.0, realized=-900.0, balance=100.0)
    assert st2["halted"] is False, st2


def test_cabang_equity_based_juga_mati():
    """daily_equity_based true (dulu halt TANPA guard dlp -- terlewat
    v4.29) + soft 95% -> keduanya wajib mati."""
    g = _guard({"daily_loss_pct": 10.0, "daily_equity_based": True,
                "daily_soft_pct": 95.0})
    st = g.daily_status(700.0)                      # equity -30%
    assert st["halted"] is False, st
    assert not st.get("soft_hit"), st
    st2 = g.daily_status(960.0)                     # -4% (di atas soft)
    assert st2["halted"] is False and not st2.get("soft_hit"), st2


def test_jalur_equity_lama_tanpa_realized_juga_mati():
    g = _guard({"daily_loss_pct": 5.0})
    st = g.daily_status(600.0)                      # realized None, -40%
    assert st["halted"] is False, st


def test_statistik_harian_tetap_dihitung():
    """Yang dihapus HANYA lock-nya -- kartu loss/dd tetap tampil."""
    g = _guard({"daily_loss_pct": 10.0})
    st = g.daily_status(900.0, realized=-100.0, balance=900.0)
    assert st["halted"] is False
    assert st["loss_abs_closed"] == 100.0, st
    assert st["loss_pct_closed"] == 10.0, st


def test_sumber_kode_keras_dan_display_nol():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_risk.py"), encoding="utf-8").read()
    assert "dlp = 0.0" in src                        # keras di kode
    assert 'self.cfg.get("daily_loss_pct"' not in src, \
        "cc_risk tak boleh baca config utk dlp lagi"
    eng = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert '"daily_loss_limit": 0.0}' in eng         # api/status nol
    assert "TEMPLATE KOSONG" in eng                  # log startup S4
