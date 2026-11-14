"""v4.37 (user): MENU LOT MANUAL per pair di samping kolom SW.
Klik tombol LOT -> isi lot -> pair ON ditradingkan pakai lot itu
(menimpa kalkulasi risiko); 0/ kosong = AUTO. Persisten."""
import json
import os
import sys
import threading
import types
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402
from cc_dashboard import make_server  # noqa: E402


def test_set_get_persist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert CC._load_pair_lot() == {}
    ns = types_ns()
    v = CC.CommandCenter.set_pair_lot(ns, "xauusd", 0.05)
    assert v == 0.05 and ns.pair_lot == {"XAUUSD": 0.05}
    assert CC._load_pair_lot() == {"XAUUSD": 0.05}
    # clamp & hapus
    CC.CommandCenter.set_pair_lot(ns, "XAUUSD", 9999)
    assert ns.pair_lot["XAUUSD"] <= 500
    CC.CommandCenter.set_pair_lot(ns, "XAUUSD", 0)
    assert ns.pair_lot == {}
    assert CC._load_pair_lot() == {}
    assert not os.path.exists("data/pair_lot.json.tmp")


def types_ns():
    import types
    return types.SimpleNamespace(pair_lot={}, emit_log=lambda t, m: None)


def test_pair_lot_of():
    ns = types_ns()
    ns.pair_lot = {"XAUUSD": 0.05}
    assert CC.CommandCenter.pair_lot_of(ns, "XAUUSD") == 0.05
    assert CC.CommandCenter.pair_lot_of(ns, "xauusd") == 0.05
    assert CC.CommandCenter.pair_lot_of(ns, "EURUSD") == 0.0


def test_override_dua_jalur_entry_di_source():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    # kedua jalur entry pakai lot manual
    assert src.count('_ulot = self.pair_lot_of(') == 2
    assert src.count("LOT MANUAL %.2f (menimpa kalkulasi)") == 2
    # lot_why diinisialisasi (anti NameError saat guard awal memblokir)
    assert src.count("lot_why = \"\"") >= 2
    # status rows membawa lot
    assert 'lot=float(self.pair_lot.get(' in src


def test_status_rows_lot_dan_endpoint_live():
    class FakeCC:
        version = "4.37-test"

        def __init__(self):
            self.pair_lot = {}

        def get_status(self):
            return {"version": self.version,
                    "scanner": [{"symbol": "XAUUSD", "status": "OFF",
                                 "score": 0.0, "price": 3850.5,
                                 "spread": 168, "signal": "-", "trend_pct": 0,
                                 "digits": 2, "sw": False}],
                    "positions": [], "mode": "SIMULASI",
                    "account": {"login": 0, "server": "T"}}

        def set_pair_lot(self, sym, lot):
            lot = float(lot or 0)
            if lot > 0:
                self.pair_lot[sym] = lot
            return lot

    cc = FakeCC()
    srv = make_server(cc, 0, "")
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/pair_lot" % port,
            data=json.dumps({"symbol": "xauusd", "lot": 0.07}).encode(),
            headers={"Content-Type": "application/json"})
        js = json.load(urllib.request.urlopen(req, timeout=5))
        assert js == {"ok": True, "symbol": "XAUUSD", "lot": 0.07}
        # AUTO (0)
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/pair_lot" % port,
            data=json.dumps({"symbol": "XAUUSD", "lot": 0}).encode(),
            headers={"Content-Type": "application/json"})
        js = json.load(urllib.request.urlopen(req, timeout=5))
        assert js == {"ok": True, "symbol": "XAUUSD", "lot": 0.0}
    finally:
        srv.shutdown()
        srv.server_close()


def test_qt_panel_lot_manual_dan_post_port_benar():
    qt = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_qtdashboard.py"), encoding="utf-8").read()
    # panel selalu terlihat
    assert "LOT MANUAL:" in qt
    assert "self.cmb_syms" in qt and "self.ent_lot" in qt
    assert 'QPushButton("ISI LOT LALU ENTER")' in qt
    assert "def _apply_lot" in qt and "def _set_lot_info" in qt
    assert "self.sig.lot.connect(self._set_lot_info)" in qt
    assert "lot = Signal(str, str)" in qt
    # POST tidak salah sasaran: active_port dulu
    assert "def _post_ports" in qt
    assert qt.count("for p in self._post_ports():") == 3   # sw+lot+alloff
    assert "[self.active_port] if self.active_port else []" in qt


def test_auto_lot_terkecil_dan_manual_menang(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # AUTO = volume_min broker; fallback 0.01
    assert CC._min_lot({"volume_min": 0.01}) == 0.01
    assert CC._min_lot({"volume_min": 0.1}) == 0.1
    assert CC._min_lot({}) == 0.01
    assert CC._min_lot(None) == 0.01
    # kedua jalur entry punya cabang AUTO = terkecil
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert src.count("AUTO -> lot terkecil") == 2
    assert src.count("_ml = _min_lot(info)") == 2
    # manual tetap menang atas AUTO
    assert src.count("LOT MANUAL %.2f (menimpa kalkulasi)") == 2


def test_pairs_reset_all_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = types.SimpleNamespace(pair_sw={"BTCUSD": True, "XAUUSD": True},
                               emit_log=lambda t, m: None)
    n = CC.CommandCenter.pairs_reset_all_off(ns)
    assert n == 2 and ns.pair_sw == {}
    assert CC._load_pair_sw() == {}          # file juga dibersihkan
    # boot log menampilkan daftar pair ON (transparan)
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert '"SWITCH ON: %s" % ", ".join(_on)' in src


def test_endpoint_pairs_reset_live():
    import threading, urllib.request, json as _j
    from cc_dashboard import make_server

    class FakeCC:
        version = "4.42-test"

        def __init__(self):
            self.pair_sw = {"BTCUSD": True}

        def get_status(self):
            return {"version": self.version, "scanner": [],
                    "positions": [], "mode": "S",
                    "account": {"login": 0, "server": "T"}}

        def pairs_reset_all_off(self):
            n = len(self.pair_sw)
            self.pair_sw.clear()
            return n

    cc = FakeCC()
    srv = make_server(cc, 0, "")
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/pairs_reset" % port, data=b"{}",
            headers={"Content-Type": "application/json"})
        js = _j.load(urllib.request.urlopen(req, timeout=5))
        assert js == {"ok": True, "off": 1}
    finally:
        srv.shutdown()
        srv.server_close()


def test_klik_pair_menyinkronkan_panel_lot():
    qt = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_qtdashboard.py"), encoding="utf-8").read()
    assert "def _sync_lot_panel" in qt
    assert "self.cmb_syms.findText(sym)" in qt
    # dipanggil dari: klik baris biasa, toggle SW, klik tombol LOT tabel
    assert qt.count("self._sync_lot_panel(") == 3   # klik baris + SW + LOT
    assert "panel ikut pair" in qt
    # isian lot terisi nilai pair (kosong = AUTO)
    assert 'self.ent_lot.setText(("%g" % lot) if lot > 0 else "")' in qt


def test_fallback_get_endpoint_di_server():
    web = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_dashboard.py"), encoding="utf-8").read()
    assert 'startswith("/api/pair_lot?")' in web
    assert 'startswith("/api/pair_switch?")' in web


def test_ui_qt_tk_web_kolom_lot():
    py = os.path.join(os.path.dirname(__file__), "..", "python")
    qt = open(os.path.join(py, "cc_qtdashboard.py"), encoding="utf-8").read()
    assert '("LOT", 56)' in qt
    assert "setCellWidget(r0, 10, lotbtn)" in qt
    assert "def _edit_lot" in qt and "QInputDialog.getDouble" in qt
    assert "def pair_lot" in qt
    assert "#f0b429" in qt                      # border amber LOT
    tk = open(os.path.join(py, "cc_tkdashboard.py"), encoding="utf-8").read()
    assert '("lot", "LOT", 50)' in tk
    assert 'col == "#11"' in tk
    assert "def pair_lot" in tk
    web = open(os.path.join(py, "cc_dashboard.py"), encoding="utf-8").read()
    assert web.count("api/pair_lot") >= 2
    assert ".lotbtn" in web and "data-lot" in web
    assert "(r.lot>0?r.lot:'AUTO')" in web
    assert 'colspan="11"' in web
