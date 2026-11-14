"""v4.34 (user): switch ON/OFF per pair di kolom sebelah STATUS.
OFF (default) = pair TIDAK dianalisa/ditradingkan; ON = normal.
Persisten di data/pair_switch.json; toggle via /api/pair_switch."""
import json
import os
import sys
import threading
import types
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402
from cc_dashboard import make_server  # noqa: E402


def _fake_self(pair_sw=None):
    ns = types.SimpleNamespace()
    ns.resolved = {"XAUUSD": "XAUUSD.x", "EURUSD": "EURUSD.x"}
    ns.pair_sw = dict(pair_sw or {})
    ns._scan_fail = {}
    ns._scan_warn_ts = {}
    ns._scan_allfail = 0
    ns.scan = {}
    ns.candidates = {}
    ns.s2_on = True
    ns.s2k = {}
    ns.s2state = None
    ns.emit_log = lambda tag, msg: None
    ns._broker_reconnect = lambda why: None
    ns._fetch_data = lambda want, sym: {
        "info": {"bid": 3850.5 if "XAU" in want else 1.1,
                 "digits": 2, "spread": 168}}
    return ns


def test_default_semua_off_gating(monkeypatch):
    called = []
    import cc_strategy3 as S3
    monkeypatch.setattr(S3, "evaluate",
                        lambda *a, **k: called.append(a) or {})
    ns = _fake_self()
    CC.CommandCenter.scan_all(ns)
    # XAUUSD & EURUSD: default OFF -> status OFF, tanpa evaluate
    assert ns.scan["XAUUSD"]["status"] == "OFF"
    assert ns.scan["EURUSD"]["status"] == "OFF"
    assert ns.scan["XAUUSD"]["price"] == 3850.5    # harga tetap live
    assert called == []                             # tidak ada analisa
    assert ns.candidates == {}                      # tidak ada sinyal


def test_pair_on_dianalisa_normal(monkeypatch):
    called = []
    import cc_strategy3 as S3
    monkeypatch.setattr(S3, "evaluate",
                        lambda *a, **k: called.append(a) or {})
    ns = _fake_self(pair_sw={"XAUUSD": True})
    CC.CommandCenter.scan_all(ns)
    assert len(called) == 1                          # XAUUSD dianalisa
    assert ns.scan["XAUUSD"].get("info")            # res strategy normal
    assert ns.scan["EURUSD"]["status"] == "OFF"     # yang lain tetap OFF


def test_persist_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert CC._load_pair_sw() == {}                  # default kosong=OFF
    ns = types.SimpleNamespace(pair_sw={},
                               emit_log=lambda tag, msg: None)
    CC.CommandCenter.set_pair_switch(ns, "xauusd", True)
    assert ns.pair_sw == {"XAUUSD": True}
    assert CC._load_pair_sw() == {"XAUUSD": True}
    CC.CommandCenter.set_pair_switch(ns, "XAUUSD", False)
    assert ns.pair_sw == {}
    assert CC._load_pair_sw() == {}
    # file tanpa trailing .tmp
    assert not os.path.exists("data/pair_switch.json.tmp")


class FakeCC:
    version = "4.34-test"

    def __init__(self):
        self.pair_sw = {}
        self.rows = [{"symbol": "XAUUSD", "status": "OFF", "score": 0.0,
                      "price": 3850.5, "spread": 168, "signal": "-",
                      "trend_pct": 0, "digits": 2}]

    def get_status(self):
        return {"version": self.version,
                "scanner": [dict(r, sw=self.pair_on(r["symbol"]))
                            for r in self.rows],
                "positions": [], "mode": "SIMULASI",
                "account": {"login": 0, "server": "T"}}

    def pair_on(self, sym):
        return bool(self.pair_sw.get(sym, False))

    def set_pair_switch(self, sym, on):
        if on:
            self.pair_sw[sym] = True
        else:
            self.pair_sw.pop(sym, None)


def test_endpoint_post_pair_switch_live():
    cc = FakeCC()
    srv = make_server(cc, 0, "")
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        # default: OFF
        st = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/api/status" % port, timeout=5))
        assert st["scanner"][0]["sw"] is False
        # ON
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/pair_switch" % port,
            data=json.dumps({"symbol": "xauusd", "on": True}).encode(),
            headers={"Content-Type": "application/json"})
        js = json.load(urllib.request.urlopen(req, timeout=5))
        assert js == {"ok": True, "symbol": "XAUUSD", "sw": True}
        st = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/api/status" % port, timeout=5))
        assert st["scanner"][0]["sw"] is True          # UI melihat ON
        # OFF lagi
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/pair_switch" % port,
            data=json.dumps({"symbol": "XAUUSD", "on": False}).encode(),
            headers={"Content-Type": "application/json"})
        json.load(urllib.request.urlopen(req, timeout=5))
        st = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/api/status" % port, timeout=5))
        assert st["scanner"][0]["sw"] is False
    finally:
        srv.shutdown()
        srv.server_close()


def test_status_scanner_memakai_pair_on():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert 'dict(r0, sw=self.pair_on(r0.get("symbol")))' in src
    assert "_off_row(want, data)" in src
    assert "self.pair_sw.get(want, False)" in src


def test_ui_qt_tk_web_kolom_sw():
    py = os.path.join(os.path.dirname(__file__), "..", "python")
    qt = open(os.path.join(py, "cc_qtdashboard.py"), encoding="utf-8").read()
    assert '("SW", 40)' in qt
    assert "if _col == 9:" in qt                 # klik area kolom SW
    assert "def pair_switch" in qt
    assert "def _toggle_sw" in qt                # v4.36
    assert "setCellWidget(r0, 9" in qt           # tombol SW di sel
    assert "#22c55e" in qt                       # border ON hijau
    assert "#ff4d5e" in qt                       # border OFF merah
    tk = open(os.path.join(py, "cc_tkdashboard.py"), encoding="utf-8").read()
    assert '("sw", "SW", 40)' in tk
    assert "def _tv_click" in tk
    assert "def pair_switch" in tk
    web = open(os.path.join(py, "cc_dashboard.py"), encoding="utf-8").read()
    assert web.count("api/pair_switch") >= 2
    assert "swbtn" in web and "data-sw" in web
    assert ".swbtn.off" in web                   # border merah web
    assert "(r.sw?' on':' off')" in web
    assert 'colspan="10"' in web
    assert "JSON.stringify({symbol:sym,on:on})" in web
