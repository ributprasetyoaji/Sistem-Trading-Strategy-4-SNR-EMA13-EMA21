# -*- coding: utf-8 -*-
"""v3.78: DETEKSI MODEL AKUN -- komisi aktual deal menang atas
config; akun 0-komisi (spread) tidak boleh kena estimasi $4/lot."""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import cc_broker as cb
import cc_risk as cr


def D(t, entry=0, vol=0.0, comm=0.0):
    return NS(type=t, entry=entry, volume=vol, commission=comm)


def test_akun_spread_komisi_nol():
    deals = [D(0, 0, 0.10, 0.0), D(1, 1, 0.10, 0.0)] * 5
    m = cb.classify_account_deals(deals)
    assert m["model"] == "SPREAD" and m["comm_per_lot"] == 0.0


def test_akun_komisi_per_lot():
    deals = [D(0, 0, 0.5, -1.0), D(1, 1, 0.5, -1.0)]  # $2 roundtrip/0.5 lot
    m = cb.classify_account_deals(deals)
    assert m["model"] == "KOMISI" and abs(m["comm_per_lot"] - 4.0) < 1e-6


def test_tanpa_deal_unknown():
    assert cb.classify_account_deals([])["model"] == "UNKNOWN"
    m = cb.classify_account_deals([D(0, 0, 0.1, -5.0)])  # komisi tnpa close
    assert m["model"] == "UNKNOWN"


class FakeB:
    def __init__(self, m):
        self._m = m

    def account_model(self):
        return self._m


def test_resolver_spread_menang_config():
    v = cb.MT5Broker.eff_comm_usd_per_lot(
        FakeB({"model": "SPREAD", "comm_per_lot": 0.0}),
        {"commission_per_lot_usd": 4.0}, 16000.0)
    assert v == 0.0


def test_resolver_komisi_konversi_kurs():
    v = cb.MT5Broker.eff_comm_usd_per_lot(
        FakeB({"model": "KOMISI", "comm_per_lot": 32000.0}),  # IDR/lot
        {"commission_per_lot_usd": 4.0}, 16000.0)             # -> $2/lot
    assert abs(v - 2.0) < 1e-9


def test_resolver_unknown_fallback_config():
    v = cb.MT5Broker.eff_comm_usd_per_lot(
        FakeB({"model": "UNKNOWN"}),
        {"commission_per_lot_usd": 4.0}, 16000.0)
    assert v == 4.0


def test_resolver_defensif_broker_tanpa_method():
    """Broker fake/stub (backtest, SIM, MT4) -> fallback config."""
    class Stub:
        pass
    assert cr._eff_comm_usd(Stub(), {"commission_per_lot_usd": 4.0},
                            16000.0) == 4.0
    assert cr._eff_comm_usd(None, {"commission_per_lot_usd": 4.0},
                            1.0) == 4.0


def test_integrasi_terpasang():
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    br = open(os.path.join(root, "cc_broker.py"), encoding="utf-8").read()
    assert "def classify_account_deals" in br
    assert "def account_model" in br
    assert "def eff_comm_usd_per_lot" in br
    rk = open(os.path.join(root, "cc_risk.py"), encoding="utf-8").read()
    assert rk.count("_eff_comm_usd") >= 5        # helper + 4 titik
    cc = open(os.path.join(root, "command_center.py"),
              encoding="utf-8").read()
    assert cc.count("_eff_comm_usd") >= 3        # helper + 2 titik
    assert "account_model" in cc
    assert "if real_comm is not None:" in cc
    web = open(os.path.join(root, "cc_dashboard.py"),
               encoding="utf-8").read()
    assert "account_model" in web
