# -*- coding: utf-8 -*-
"""v3.xx FITUR REFRESH TANPA BAT (permintaan user): tombol UPDATE di
dashboard -> self-update file kode dari GitHub -> engine restart via
os.execv (jendela bat & port tetap).  Test ini OFFLINE (network
di-monkeypatch)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import cc_selfupdate as SU  # noqa: E402


def test_blob_sha_vektor_dikenal():
    # git hash-object (kosong) = vektor resmi git
    assert SU.blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_allowed_hanya_python():
    assert SU._allowed("python/command_center.py")
    assert SU._allowed("python/cc_config.py")
    assert SU._allowed("requirements.txt")
    # DILARANG KERAS:
    assert not SU._allowed("MULAI_SEMUA.bat")
    assert not SU._allowed("data/cc_state.json")
    assert not SU._allowed("tests/test_x.py")
    assert not SU._allowed("RBT_FX_Bridge.mq4")


def test_plan_dan_apply_offline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    os.makedirs("python", exist_ok=True)
    # file lokal SAMA dgn remote
    with open("python/sama.py", "wb") as f:
        f.write(b"ok")
    fake_tree = {"python/sama.py": SU.blob_sha(b"ok"),
                 "python/baru.py": SU.blob_sha(b"BARU"),
                 "MULAI_SEMUA.bat": "x" * 40,
                 "data/state.json": "y" * 40}
    monkeypatch.setattr(SU, "tree", lambda *a, **k: dict(fake_tree))
    need = SU.plan(root=".")
    assert need == ["python/baru.py"], need          # hanya 1, .bat/data
    # stub unduhan (offline); path terlarang tidak akan diunduh
    monkeypatch.setattr(SU, "_fetch_raw",
                        lambda url, token: b"BARU")
    # dilarang tulis .bat walau diminta paksa
    wrote = SU.apply_updates(["python/baru.py", "MULAI_SEMUA.bat"],
                             root=".")
    assert wrote == ["python/baru.py"], wrote
    assert open("python/baru.py", "rb").read() == b"BARU"
    assert not os.path.exists("MULAI_SEMUA.bat")


def test_run_tanpa_token_none(monkeypatch, tmp_path):
    monkeypatch.delenv("RBT_GH_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    files, err = SU.run(root=".")
    assert files is None and err


def test_token_dari_bat(monkeypatch, tmp_path):
    """v3.80: token cadangan dr MULAI_SEMUA.bat (kondisi
    VPS: bat lama jalan di memori tanpa passthrough env)."""
    monkeypatch.delenv("RBT_GH_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MULAI_SEMUA.bat").write_text(
        "set \"TOKEN=github_pat_FAKE123456789012345678901234\"\r\n",
        encoding="utf-8")
    assert SU.resolve_token(
        root=".") == "github_pat_FAKE123456789012345678901234"
    (tmp_path / "MULAI_SEMUA.bat").unlink()
    assert SU.resolve_token(root=".") is None


def test_integrasi_terpasang():
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    web = open(os.path.join(root, "cc_dashboard.py"),
               encoding="utf-8").read()
    assert '"/api/update"' in web
    assert "id=\"upd\"" not in web
    eng = open(os.path.join(root, "command_center.py"),
               encoding="utf-8").read()
    assert "def request_restart" in eng
    assert "os.execv" in eng
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        d = open(os.path.join(root, f), encoding="utf-8").read()
        assert "/api/update" in d and "btn_upd" not in d, f

def test_dashboard_ikut_restart_terpasang():
    """v3.81: dashboard desktop (Qt/Tk) harus me-restart dirinya saat
    versi engine berubah -- proses dashboard terpisah dr engine,
    tanpa ini label/rule lama tetap tampil stlh update."""
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        d = open(os.path.join(root, f), encoding="utf-8").read()
        assert "_rbt_self_exec" in d and "_boot_ver" in d, f
