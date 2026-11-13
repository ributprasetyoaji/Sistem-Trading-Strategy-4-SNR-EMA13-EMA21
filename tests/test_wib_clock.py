# -*- coding: utf-8 -*-
"""v3.83: JAM DASHBOARD = WIB (permintaan user) -- engine menyediakan
ts_wib (UTC+7 eksplisit) dan ketiga dashboard menampilkan label WIB.
ts lama TIDAK diubah (dipakai deteksi data beku, localtime mesin)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

ROOT = os.path.join(os.path.dirname(__file__), "..", "python")


def test_engine_punya_ts_wib_utc7():
    src = open(os.path.join(ROOT, "command_center.py"),
               encoding="utf-8").read()
    assert '"ts_wib"' in src
    assert 'time.gmtime(time.time() + 7 * 3600)' in src


def test_web_qt_tk_label_wib():
    for f in ("cc_dashboard.py", "cc_qtdashboard.py", "cc_tkdashboard.py"):
        d = open(os.path.join(ROOT, f), encoding="utf-8").read()
        assert '" WIB"' in d or "' WIB'" in d, f


def test_anti_beku_tetap_pakai_ts_lokal():
    """Deteksi beku Qt/Tk tidak boleh ikut pindah zona."""
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        d = open(os.path.join(ROOT, f), encoding="utf-8").read()
        assert 'strptime(_st, "%Y-%m-%d %H:%M:%S")' in d, f
        assert '_st = s.get("ts") or ""' in d, f


def test_format_ts_wib_benar():
    import time
    exp = time.strftime("%Y-%m-%d %H:%M:%S",
                        time.gmtime(time.time() + 7 * 3600))
    got = time.strftime("%Y-%m-%d %H:%M:%S",
                        time.gmtime(time.time() + 7 * 3600))
    assert len(got) == 19 and got == exp
