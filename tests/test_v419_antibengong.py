# -*- coding: utf-8 -*-
"""v4.19: ANTI-BENGONG engine -- heartbeat, watchdog, alert dashboard.

Engine tidak boleh diam tanpa jejak: heartbeat file (cc_heartbeat.json)
+ watchdog internal (_watchdog_check / _broker_reconnect) + dashboard
menampilkan alert ENGINE BENGONG + api/status punya engine_stale.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402

_PY = os.path.join(os.path.dirname(__file__), "..", "python")


def test_versi():
    assert C.CC_VERSION >= "4.19"


def test_heartbeat_watchdog_terpasang():
    src = open(os.path.join(_PY, "command_center.py"),
               encoding="utf-8").read()
    assert "cc_heartbeat.json" in src
    assert "_watchdog_check" in src and "_broker_reconnect" in src
    assert '"engine_stale": bool(hb_stale)' in src
    assert "SCAN GAGAL TOTAL" in src


def test_dashboard_alert_bengong():
    dsh = open(os.path.join(_PY, "cc_dashboard.py"),
               encoding="utf-8").read()
    assert "hb-alert" in dsh and "ENGINE BENGONG" in dsh


def test_ipc_lock_broker_mt5():
    import cc_broker
    b5 = cc_broker.MT5Broker({})
    assert hasattr(b5, "_ipc")
    fn = getattr(cc_broker.MT5Broker, "order_send", None)
    assert fn is not None and getattr(fn, "_ipc_wrapped", False)
