"""v4.41 (user): saat pair di-ON-kan chart kadang blank/off, harus
toggle berulang. Penyebab: baris OFF/NO-DATA tanpa ohlc + confluence
jatuh ke baris kosong + fetch MT5 gagal tanpa retry + ON nunggu tick.
Fix: ohlc di baris OFF, top ber-candle, retry 1x, scan-kick instan,
fallback chart Qt."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402


def _m5(n=80):
    return {"time": list(range(1000, 1000 + n)),
            "open": [1.0] * n, "high": [2.0] * n,
            "low": [0.5] * n, "close": [1.5] * n}


def test_off_row_membawa_candle():
    r = CC._off_row("XAUUSD", {"info": {"bid": 3850.5, "digits": 2,
                                        "spread": 168}, "m5": _m5()})
    assert len(r["ohlc"]) == 60                 # candle tampil walau OFF
    assert r["ohlc"][0][0] == 1000 + 20         # 60 candle terakhir
    assert r["status"] == "OFF"
    # tanpa data -> tetap aman
    r0 = CC._off_row("XAUUSD")
    assert r0["ohlc"] == []


def test_spark_from_bars_format():
    s = CC._spark_from_bars(_m5(5))
    assert len(s) == 5
    assert s[-1] == (1004, 1.0, 2.0, 0.5, 1.5)
    assert CC._spark_from_bars({"time": [1]}) == []
    assert CC._spark_from_bars(None) == []


def test_set_pair_switch_memicu_scan_langsung(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = types.SimpleNamespace(pair_sw={}, emit_log=lambda t, m: None,
                               _scan_kick=False)
    CC.CommandCenter.set_pair_switch(ns, "XAUUSD", True)
    assert ns._scan_kick is True                 # loop scan jalan sekarang
    CC.CommandCenter.set_pair_switch(ns, "XAUUSD", False)
    assert ns._scan_kick is True


def test_engine_source_perbaikan():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    # confluence top pilih baris ber-candle
    assert 'top = next((r for r in scanner if r.get("ohlc")), None)' in src
    # retry fetch utk pair ON
    assert '(getattr(self, "pair_sw", {}) or {})\\' in src
    assert '.get(want, False):' in src
    # loop mengonsumsi kick
    assert 'if bool(getattr(self, "_scan_kick", False)):' in src
    assert 'self._scan_kick = True' in src


def test_qt_chart_fallback_bercandle():
    qt = open(os.path.join(os.path.dirname(__file__), "..", "python",
                           "cc_qtdashboard.py"), encoding="utf-8").read()
    assert 'if top is not None and not (top.get("ohlc") or []):' in qt
    assert "baris ber-candle lain" in qt
