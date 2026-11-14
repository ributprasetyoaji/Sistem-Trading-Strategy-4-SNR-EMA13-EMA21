"""v4.35 REGRESI (foto user: 'ENGINE OFFLINE' padahal engine hidup):
get_status crash KeyError 'regime_dir'/'structure' saat ada baris OFF/
NO-DATA -> /api/status {"error":...} -> semua dashboard mati.
Test: row OFF/NO-DATA wajib punya SEMUA kunci yang dibaca get_status,
dan source TIDAK BOLEH akses res["..."] langsung utk kunci tersebut."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402

KEYS = {"symbol", "price", "digits", "spread", "regime", "regime_dir",
        "side", "signal", "score", "trend_pct", "status", "sniper_why",
        "block_why", "sl", "tp", "sl_price", "tp_price", "sl_points",
        "components", "components_buy", "components_sell", "ohlc"}


def test_off_row_dan_no_data_row_lengkap():
    for row in (CC._off_row("XAUUSD"),
                CC._off_row("XAGUSD", {"info": {"bid": 48.7,
                                                "digits": 3, "spread": 18}}),
                CC._no_data_row("BTCUSD")):
        missing = KEYS - set(row.keys())
        assert not missing, "kunci hilang: %s" % missing
    assert CC._off_row("XAUUSD")["status"] == "OFF"


def test_get_status_jalur_off_tanpa_cabang_normal():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert 'if res.get("status") == "OFF":' in src
    assert "scanner.append(dict(res))" in src
    # cabang normal get_status kini pakai .get (tahan row bentuk apapun)
    assert 'res.get("regime_dir", "-")' in src
    assert 'res.get("side", "-")' in src
    assert 'res.get("sl_price", 0.0)' in src
    assert 'res.get("tp_price", 0.0)' in src
    # tidak ada lagi akses langsung di confluence
    assert 'top["components_buy"][' not in src
    assert 'top["components_sell"][' not in src
    # satu-satunya res["regime_dir"] langsung harusnya sudah tiada
    assert 'res["regime_dir"]' not in src


def test_confluence_pakai_get():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert 'top.get("components_buy", {})' in src
    assert 'top.get("components_sell", {})' in src
