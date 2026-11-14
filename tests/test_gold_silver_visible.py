import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC


def test_placeholder_row_bentuk_lengkap():
    r = CC._no_data_row("XAUUSD")
    assert r["symbol"] == "XAUUSD"
    assert r["status"] == "NO-DATA"
    assert r["score"] == 0.0
    for k in ("price", "digits", "spread", "regime", "signal",
              "trend_pct", "components", "ohlc"):
        assert k in r


def test_status_tidak_melewati_pair_tanpa_data():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert "_no_data_row(want)" in src          # placeholder selalu ditambah
    # tidak ada lagi 'continue' polos setelah scan.get miss di builder
    assert "if not res:\n                # TIDAK di-skip" in src


def test_frontend_catof_prefix_gold_silver_crypto():
    js = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_dashboard.py"), encoding="utf-8").read()
    assert "/^(XAU|XAG|GOLD|SILVER|XPT)/" in js   # XAUUSDm dkk tetap GOLD
    assert "/^(BTC|ETH|SOL|XRP|LTC" in js          # crypto prefix
    assert "XAUUSD:'GOLD'" in js and "XAGUSD:'GOLD'" in js


def test_gold_silver_wants_force():
    from cc_config import DEFAULTS
    fi = DEFAULTS.get("symbols_force_include") or []
    assert "XAUUSD" in fi and "XAGUSD" in fi
