import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


def _page():
    return open(os.path.join(os.path.dirname(__file__), "..", "python",
                             "cc_dashboard.py"), encoding="utf-8").read()


def test_stamp_versi_ui_di_header():
    assert 'id="uiver"' in _page()
    assert "UI-2 v" in _page()
    assert "TRADING ALGO SYSTEM &middot; UI-2" in _page()   # statis, terlihat tanpa JS


def test_stamp_statis_di_halaman_login():
    assert "COMMAND CENTER &middot; UI-2" in _page()


def test_auto_reload_saat_versi_engine_ganti():
    js = _page()
    assert "window.__ev!==s.version" in js
    assert "location.reload()" in js


def test_penghitung_pair_per_tab():
    js = _page()
    assert "_cnt[catOf(r.symbol)]" in js or "_cnt[_c]=(_cnt[_c]||0)+1" in js
    assert "b.dataset.lb" in js
    assert "catOf(r.symbol)!==TAB" in js      # filter tab tetap ada


def test_catof_prefix_gold_tetap_ada():
    assert "/^(XAU|XAG|GOLD|SILVER|XPT)/" in _page()
