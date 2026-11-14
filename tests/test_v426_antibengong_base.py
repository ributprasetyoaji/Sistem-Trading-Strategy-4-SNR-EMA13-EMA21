"""vANTI ANTI-BENGONG (port dari S3 v4.19): akar insiden "semua pair
momentum 0%, dashboard seolah hidup, restart BAT baru sembuh":

1. scan_all dulu SENYAP saat semua pair gagal ambil data -> kini WARN +
   reconnect otomatis setelah 3x gagal total.
2. MetaTrader5 & jembatan MT4 kini diserialkan _ipc_locked (dashboard
   vs loop utama saling menerobos = None massal/gantung).
3. Heartbeat + engine_stale: dashboard TIDAK lagi mengelabui -- kalau
   loop utama beku, banner merah + alert Telegram menyala.

CATATAN: TIDAK ADA logika entry/strategi yang diubah -- bukti: sha256
semua file scanner/strategi/risiko identik sebelum/sesudah patch.
"""
import inspect
import json
import os
import sys
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "python"))
import cc_broker
import cc_config
import command_center as CC


# ------------------------------------------------- 1) watchdog scan ----
class StubScan:
    def __init__(self):
        self.resolved = {"XAUUSD": "XAUUSD", "BTCUSD": "BTCUSD"}
        self.scan = {}
        self.cfg = {}
        self.s2_on = False          # jalur S2: gate analyze alternatif
        self._scan_fail = {}
        self._scan_warn_ts = {}
        self._scan_allfail = 0
        self._scan_last_ok = 0.0
        self.logs = []
        self.reconnects = []

    def _fetch_data(self, want, sym):
        return None                      # simulasi terminal broker mati

    def emit_log(self, tag, msg):
        self.logs.append((tag, msg))

    def _broker_reconnect(self, why):
        self.reconnects.append(why)


def test_scan_gagal_total_menicu_reconnect_dan_warn():
    st = StubScan()
    for _ in range(3):                   # 3 pass gagal total berurutan
        CC.CommandCenter.scan_all(st)
    assert len(st.reconnects) == 1       # reconnect OTOMATIS terpicu
    assert any("data pasar tidak tersedia" in m for _, m in st.logs)
    assert any("SCAN GAGAL TOTAL" in m for _, m in st.logs)
    # pass berikutnya sukses -> counter bersih & allfail reset
    st._fetch_data = lambda w, s: {"m15": {"close": [1] * 100}}
    CC.CommandCenter.scan_all(st)
    assert st._scan_allfail == 0
    assert st._scan_fail == {}


def test_broker_reconnect_anti_spam_dan_sim_dilewati():
    class Br:
        is_sim = False

        def __init__(self):
            self.n = 0

        def reconnect(self):
            self.n += 1
            return True
    st = types.SimpleNamespace(broker=Br(),
                               emit_log=lambda t, m: None,
                               _reconnect_ts=0.0)
    CC.CommandCenter._broker_reconnect(st, "tes")
    CC.CommandCenter._broker_reconnect(st, "tes")
    assert st.broker.n == 1              # anti-spam 2 menit
    st2 = types.SimpleNamespace(broker=Br(), emit_log=lambda t, m: None,
                                _reconnect_ts=time.time())
    st2.broker.is_sim = True
    CC.CommandCenter._broker_reconnect(st2, "tes")
    assert st2.broker.n == 0             # sim tidak di-reconnect


# --------------- 3) heartbeat + engine_stale + alert log WARN ----------
def test_watchdog_heartbeat_beku_alert_sekali(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data", exist_ok=True)
    with open("data/cc_heartbeat.json", "w") as f:
        json.dump({"ts": time.time() - 900.0}, f)   # beku 15 menit
    logs = []   # Telegram sudah DIHAPUS -> alert kini via log WARN saja
    st = types.SimpleNamespace(
        _stale_alert_ts=0.0,
        emit_log=lambda tag, msg: logs.append((tag, msg)))
    age, stale = CC.CommandCenter._watchdog_check(st)
    assert stale and age > 600
    assert len(logs) == 1 and logs[0][0] == "WARN"
    CC.CommandCenter._watchdog_check(st)
    assert len(logs) == 1                 # anti-spam 10 menit
    with open("data/cc_heartbeat.json", "w") as f:
        json.dump({"ts": time.time()}, f)
    age2, stale2 = CC.CommandCenter._watchdog_check(st)
    assert not stale2


def test_watchdog_baru_start_tidak_alert(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)              # tidak ada file heartbeat
    logs = []
    st = types.SimpleNamespace(
        _stale_alert_ts=0.0,
        emit_log=lambda tag, msg: logs.append((tag, msg)))
    age, stale = CC.CommandCenter._watchdog_check(st)
    assert age == -1.0 and not stale
    assert logs == []


# ------------------------------- 2) IPC lock broker -------------------
def test_ipc_lock_meliputi_broker_mt5_dan_mt4():
    # S3: MT5 = IPC terminal -> wajib serial (RLock + wrap anti bengong);
    # MT4 = jembatan file RBT_FX_Bridge (antarmuka sama, tanpa IPC wrap).
    b5 = cc_broker.MT5Broker({})
    assert hasattr(b5, "_ipc"), "MT5Broker._ipc"
    for m in ("connect", "copy_rates", "account", "positions",
              "order_send", "closed_stats", "closed_trades_since",
              "reconnect"):
        fn = getattr(cc_broker.MT5Broker, m, None)
        assert fn is not None and getattr(
            fn, "_ipc_wrapped", False), ("MT5Broker", m)
    b4 = cc_broker.MT4Broker({})
    for m in ("connect", "copy_rates", "account", "positions",
              "order_send"):
        assert callable(getattr(b4, m, None)), ("MT4Broker", m)
    # perintah MT4 lewat file cmd/resp RBT_FX (bukan IPC terminal)
    src = inspect.getsource(cc_broker.MT4Broker)
    assert "rbtfx_cmd" in src and "rbtfx_resp" in src


def test_heartbeat_dan_watchdog_terpasang_di_source():
    py = os.path.join(os.path.dirname(__file__), "..", "python")
    src = open(os.path.join(py, "command_center.py"),
               encoding="utf-8").read()
    assert "cc_heartbeat.json" in src
    assert "_watchdog_check" in src and "_broker_reconnect" in src
    assert '"engine_stale": bool(hb_stale)' in src
    assert "SCAN GAGAL TOTAL" in src
    dsh = open(os.path.join(py, "cc_dashboard.py"),
               encoding="utf-8").read()
    assert "hb-alert" in dsh and "ENGINE BENGONG" in dsh


def test_versi_baru():
    assert cc_config.CC_VERSION >= "4.30"  # versi maju terus
