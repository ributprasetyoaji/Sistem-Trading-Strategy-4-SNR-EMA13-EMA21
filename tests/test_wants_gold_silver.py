import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC
from cc_config import DEFAULTS

CRYPTO = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "LTCUSD"]
METALS = ["XAUUSD", "XAGUSD"]


def test_status_builder_pakai_self_wants():
    # PANEL SCANNER dashboard WAJIB iterasi self.wants (bukan cfg mentah)
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert "for want in self.wants:" in src
    assert "scanner = []" in src
    # tidak ada lagi consumer daftar mentah cfg["symbols"] di engine
    import re
    raw = re.findall(r'for want in self\.cfg\.get\("symbols"', src)
    assert not raw, f"masih ada iterasi cfg mentah: {raw}"


def test_wants_selalu_memuat_gold_silver_crypto():
    merged = CC._merge_symbols(["EURUSD", "GBPUSD"],
                               DEFAULTS["symbols_force_include"])
    for s in METALS + CRYPTO:
        assert s in merged, f"{s} hilang dari wants"


def test_resolver_dan_wants_satu_sumber():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    # resolver pakai self.wants (bukan merge ulang dgn sumber beda)
    assert "for want in self.wants:" in src
    assert "self.wants = _merge_symbols(" in src


def test_alternate_gold_silver_cukup_utk_broker_umum():
    alts = DEFAULTS["symbol_alternates"]
    assert set(alts["XAUUSD"]) >= {"XAUUSD", "GOLD", "XAUUSDm", "GOLD.a"}
    assert set(alts["XAGUSD"]) >= {"XAGUSD", "SILVER", "XAGUSDm"}
