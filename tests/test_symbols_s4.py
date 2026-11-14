import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from cc_config import DEFAULTS
import command_center as CC
import market_guard as MG

CRYPTO = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "LTCUSD"]
METALS = ["XAUUSD", "XAGUSD"]          # gold + silver (permintaan user S4)


def test_defaults_memuat_crypto_dan_gold_silver():
    syms = DEFAULTS["symbols"]
    for s in CRYPTO + METALS:
        assert s in syms, f"{s} harus ada di symbols default S4"


def test_force_include_default():
    fi = DEFAULTS.get("symbols_force_include") or []
    assert set(CRYPTO + METALS) <= set(fi)


def test_merge_paksa_tetap_masuk_walau_config_json_tua():
    # simulasi cc_config.json VPS yang daftar simbolnya lama
    merged = CC._merge_symbols(["EURUSD", "GBPUSD"],
                               DEFAULTS["symbols_force_include"])
    for s in CRYPTO + METALS:
        assert s in merged
    assert merged[0] == "EURUSD"           # urutan config tetap dulu


def test_merge_tanpa_duplikat():
    merged = CC._merge_symbols(["EURUSD", "BTCUSD"],
                               DEFAULTS["symbols_force_include"])
    assert merged.count("BTCUSD") == 1
    assert len(merged) == len(set(merged))


def test_merge_dipakai_engine_dan_log_pair_aktif():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert "_merge_symbols(self.cfg.get" in src
    assert "PAIR AKTIF" in src             # bukti di log startup


def test_alternate_nama_broker_crypto_dan_logam():
    alts = DEFAULTS["symbol_alternates"]
    for s in ["XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD"]:
        assert s in alts and len(alts[s]) >= 3


def test_market_guard_crypto_24_7_gold_ikut_sesi():
    assert MG.sym_always_open("BTCUSD")
    assert MG.sym_always_open("ETHUSD")
    assert MG.sym_always_open("SOLUSD")
    # gold/silver ikut sesi forex (bukan 24/7 - ada weekend/rollover)
    assert not MG.sym_always_open("XAUUSD")
    assert not MG.sym_always_open("XAGUSD")
