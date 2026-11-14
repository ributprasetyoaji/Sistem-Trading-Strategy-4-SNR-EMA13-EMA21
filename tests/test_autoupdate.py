import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import cc_selfupdate as SU


def test_repo_mengarah_ke_repo_benar():
    # KRUSIAL: repo salah = engine menarik kode strategy lain!
    assert SU.REPO == "ributprasetyoaji/Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"


def test_allowlist_hanya_python_dan_requirements():
    assert SU._allowed("python/command_center.py")
    assert SU._allowed("python/cc_config.py")
    assert SU._allowed("requirements.txt")
    # data penting VPS TIDAK PERNAH ditulis oleh auto-update:
    assert not SU._allowed("MULAI_SEMUA.bat")
    assert not SU._allowed("TOKEN.txt")
    assert not SU._allowed("data/cc_state.json")
    assert not SU._allowed("cc_state.json")
    assert not SU._allowed("RBT_FX_Bridge.mq4")
    assert not SU._allowed("data_hist/x.csv")
    assert not SU._allowed("tests/t.py")


def test_resolve_token_baca_token_txt():
    import tempfile
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "TOKEN.txt"), "w") as f:
        f.write("ghp_faketoken1234567890abcdefghijklmnop")
    old = os.environ.get("RBT_GH_TOKEN")
    os.environ.pop("RBT_GH_TOKEN", None)
    try:
        assert SU.resolve_token(d) == "ghp_faketoken1234567890abcdefghijklmnop"
    finally:
        if old:
            os.environ["RBT_GH_TOKEN"] = old


def test_engine_memuat_loop_auto_update():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert "AUTO-UPDATE OTOMATIS" in src
    assert "_auto_update_loop" in src
    assert "request_restart" in src
    assert 'cfg.get("auto_update_min"' in src
