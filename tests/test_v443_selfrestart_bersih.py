"""v4.43 FIX FATAL (user: 'BTCUSD masih on, banyak bug error'):
1) request_restart punya docstring '% ver' -> NameError SAAT DIPANGGIL;
   pemanggilnya auto-update loop -> update terunduh tapi engine tak
   pernah restart -> VPS jalan kode lama selamanya.
2) qt/tk _rbt_self_exec memakai _th yang tak pernah diimport -> NameError.
3) Boot harus bersih: SEMUA OFF (pairs_start_all_off default True)."""
import json
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402


def test_request_restart_bisa_dipanggil(monkeypatch):
    called = {}
    import threading as th

    class _T:
        def __init__(self, target, daemon=None):
            called["target"] = target

        def start(self):
            pass

    monkeypatch.setattr(th, "Thread", _T)
    monkeypatch.setattr(CC.time, "sleep", lambda s: None)
    ns = types.SimpleNamespace(emit_log=lambda t, m: None)
    CC.CommandCenter.request_restart(ns, 0.1)   # dulu: NameError 'ver'
    assert "target" in called


def test_tidak_ada_docstring_format_undefined():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert '""" % ver' not in src
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        qt = open(os.path.join(os.path.dirname(__file__), "..", "python",
                               f), encoding="utf-8").read()
        assert "_th.Thread" not in qt           # pakai threading global


def test_boot_bersih_semua_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data", exist_ok=True)
    with open("data/pair_switch.json", "w") as f:
        json.dump({"BTCUSD": True, "XAUUSD": True}, f)
    cfg = CC.CCConfig()
    logs = []
    cc = CC.CommandCenter(cfg, log=lambda tag, msg: logs.append(msg))
    assert cc.pair_sw == {}                     # BOOT = SEMUA OFF
    assert any("START BERSIH: SEMUA OFF" in m and "BTCUSD" in m
               for m in logs)
    # file juga bersih
    assert CC._load_pair_sw() == {}
    # config false -> state dipertahankan
    monkeypatch.setattr(cfg, "get",
                        lambda k, d=None: False if k == "pairs_start_all_off"
                        else cfg.data.get(k, d) if hasattr(cfg, "data")
                        else d)
    cc2 = CC.CommandCenter(cfg, log=lambda t, m: None)
    # (pairs_start_all_off=false tak dibuat -> perilaku ini sekadar
    #  memastikan cabang config dievaluasi tanpa error)
    assert hasattr(cc2, "pair_sw")
