# -*- coding: utf-8 -*-
"""ANTI-REGRESI v3.67/3.73/3.87:
1. BUG FATAL S1: dict(CCConfig) -> TypeError not iterable -> entry
   skor kuat (early lane) GAGAL.  Kini CCConfig iterable + early lane
   memakai as_dict().
2. Chip topbar TANPA nama server broker (privasi user)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import cc_config as CC  # noqa: E402


def test_ccconfig_iterable():
    cfg = CC.CCConfig()
    d = dict(cfg)                     # dulu: TypeError
    assert isinstance(d, dict) and len(d) > 10
    assert len(list(cfg.keys())) == len(d)
    assert cfg["dashboard_port"] == CC.DEFAULTS["dashboard_port"]


def test_early_lane_pakai_as_dict():
    """S1: early lane WAJIB as_dict().  S2/S3 (arsitektur beda): cukup
    pastikan pola crash dict(self.cfg) tidak ada di mana pun."""
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    if "cfg_sn = self.cfg.as_dict()" in src:
        return                            # S1: sudah benar
    assert "dict(self.cfg)" not in src    # S2/S3: pola crash dilarang


def test_chip_tanpa_server():
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                                f), encoding="utf-8").read()
        assert 'acc.get("server") or "BROKER"' not in src, f


def test_baris_why_dihapus():
    """v3.75 (permintaan user): teks overlay '>> sniper: ...' di panel
    pair TIDAK boleh tampil lagi di kedua dashboard desktop."""
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                                f), encoding="utf-8").read()
        assert '">> " + why' not in src, f
        assert '("sniper: " + top["sniper_why"])' not in src, f
    qt = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_qtdashboard.py"), encoding="utf-8").read()
    assert "lb_why.hide()" in qt
    tk = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_tkdashboard.py"), encoding="utf-8").read()
    assert "lb_why.pack(" not in tk
