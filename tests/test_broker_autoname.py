import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from cc_broker import match_symbol, ALIAS_BUILTIN, _norm


def alts_of(want, cfg_alts=None):
    """Persis logika resolve_symbol: want + config alternates + builtin."""
    cfg_alts = cfg_alts or []
    return ([want] + [a for a in cfg_alts if a != want]
            + [a for a in ALIAS_BUILTIN.get(want, [])
               if a not in cfg_alts and a != want])


def test_gold_alias_otomatis():
    assert match_symbol("XAUUSD", alts_of("XAUUSD"),
                        ["EURUSD", "GOLD.a", "BTCUSD"]) == "GOLD.a"
    assert match_symbol("XAGUSD", alts_of("XAGUSD"),
                        ["SILVER", "EURUSD"]) == "SILVER"


def test_config_alternate_tetap_menang():
    assert match_symbol("XAUUSD", alts_of("XAUUSD", ["GOLD"]),
                        ["GOLD", "GOLD.a"]) == "GOLD"


def test_ternormalisasi_tanda_baca():
    assert _norm("BTC/USD") == "BTCUSD"
    assert match_symbol("BTCUSD", alts_of("BTCUSD"),
                        ["BTC/USD", "EURUSD"]) == "BTC/USD"


def test_suffix_luar_biasa_otomatis():
    assert match_symbol("EURUSD", alts_of("EURUSD"), ["EURUSD.r"]) == "EURUSD.r"
    assert match_symbol("EURUSD", alts_of("EURUSD"), ["EURUSDm"]) == "EURUSDm"


def test_alias_index_energi_logam():
    assert match_symbol("NAS100", alts_of("NAS100"), ["US100"]) == "US100"
    assert match_symbol("USOIL", alts_of("USOIL"), ["WTI"]) == "WTI"
    assert match_symbol("XPTUSD", alts_of("XPTUSD"), ["PLATINUM"]) == "PLATINUM"


def test_tidak_salah_pilih():
    assert match_symbol("GBPUSD", alts_of("GBPUSD"),
                        ["EURUSD", "USDJPY"]) == ""


def test_semua_pair_force_include_punya_alias_builtin():
    from cc_config import DEFAULTS
    for s in DEFAULTS["symbols_force_include"]:
        assert s in ALIAS_BUILTIN, f"{s} tanpa alias builtin"


def test_resolve_symbol_menggabung_builtin():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_broker.py"), encoding="utf-8").read()
    assert "ALIAS_BUILTIN.get(want" in src
    assert "symbol_alternates" in src
