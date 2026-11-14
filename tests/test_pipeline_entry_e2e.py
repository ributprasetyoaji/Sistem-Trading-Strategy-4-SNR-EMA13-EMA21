"""AUDIT SISTEM S4 (user: 'pastikan semua berjalan sebelum isi logic'):
buktikan jalur ENTRY end-to-end yang akan dipakai logic baru:
evaluate -> res['exec'] -> candidates -> try_execute -> guard ->
validate_execution -> LOT (manual/min) -> broker.order_send.
Template kosong = WAJIB tidak ada order (validate memblokir)."""
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import command_center as CC  # noqa: E402
import cc_strategy3 as S3   # noqa: E402


class FakeState:
    def cooldown_until(self, want):
        return 0.0

    def clear(self, want):
        pass

    def save(self):
        pass

    def __getattr__(self, name):
        # metode state lain (set_trail dst) -> no-op utk simulasi
        return lambda *a, **k: None


class FakeBroker:
    def __init__(self):
        self.orders = []

    def symbol_tick(self, sym):
        return {"bid": 3850.10, "ask": 3850.50}

    def order_send(self, sym, side, lot, sl, tp, comment=""):
        self.orders.append({"sym": sym, "side": side, "lot": lot,
                            "sl": sl, "tp": tp, "comment": comment})
        return types.SimpleNamespace(ok=True, comment="OK", ticket=1)


class FakeRisk:
    def can_open(self, sym, pos):
        return True, ""

    def note_open(self, sym):
        pass

    def calc_lot(self, sym, info, sl_points, cur, rate):
        return 0.01, "fake-min"


def _bars(n=80, px=3850.0):
    return {"time": list(range(1000, 1000 + n)),
            "open": [px] * n, "high": [px + 5] * n,
            "low": [px - 5] * n, "close": [px + 1] * n}


def _ns(broker, pair_lot=None):
    ns = types.SimpleNamespace()
    ns.cfg = {"bars_m5": 200, "bars_m1": 120, "scan_interval_sec": 5,
              "min_score": 70, "max_baskets": 3, "warmup_sec": 20,
              "sl_money_usd": 0.0, "tp_money_usd": 0.0, "tp_rr": 0.0,
              "tp1_rr": 0.0, "tp2_rr": 0.0, "tp_mode": "close",
              "tp_broker_hard": False, "min_entry_lot": 0.04,
              "tp_min_rr_net": 0.6}
    ns.resolved = {"XAUUSD": "XAUUSD.x"}
    ns.broker = broker
    ns.risk = FakeRisk()
    ns.s2state = FakeState()
    ns.s2_started = time.time() - 10000
    ns.s2k = {}
    ns.s2_on = True
    ns.scan = {}
    ns.candidates = {}
    ns._scan_fail = {}
    ns._scan_warn_ts = {}
    ns._scan_allfail = 0
    ns.pair_sw = {"XAUUSD": True}
    ns.pair_lot = dict(pair_lot or {})
    ns._s2_hold_memo = {}
    ns.emit_log = lambda tag, msg: None
    ns._write_signal = lambda *a, **k: None
    ns.account_usd_rate = lambda: ("USD", 1.0)
    ns._fetch_data = lambda want, sym: {
        "m15": _bars(), "m5": _bars(), "m1": _bars(),
        "info": {"bid": 3850.10, "ask": 3850.50, "digits": 2,
                 "spread_points": 150, "point": 0.1, "volume_min": 0.01}}
    ns._market_guard_block = lambda s, r: False   # jendela pasar terbuka
    ns.pair_lot_of = lambda want: \
        CC.CommandCenter.pair_lot_of(ns, want)   # logika asli engine
    return ns


def _res_exec():
    return {"symbol": "XAUUSD", "price": 3850.1, "side": "BUY",
            "score": 85.0, "status": "READY", "strategy": "S2",
            "info": {"bid": 3850.10, "ask": 3850.50, "digits": 2,
                     "spread_points": 150, "point": 0.1,
                     "volume_min": 0.01},
            "sl_price": 3840.0, "tp_price": 3870.0, "sl_points": 101,
            "point": 0.1,
            "exec": {"sig": "BUY", "price": 3850.5, "sl": 3840.0,
                     "tp": 3870.0, "lot": 0.0},
            "components_buy": {}, "components_sell": {}, "ohlc": []}


def test_1_sinyal_tak_valid_tidak_pernah_order():
    """Filter eksekusi S4: data yang tak lolos re-check -> TIDAK order."""
    br = FakeBroker()
    ns = _ns(br)
    res = _res_exec()
    ns.candidates["XAUUSD"] = {"t": time.time(), "side": "BUY"}
    CC.CommandCenter._try_execute_s2(ns, res, [])
    assert br.orders == []                       # TIDAK ada order
    assert res["status"] == "BLOCKED"
    assert "S4" in res["block_why"]              # filter eksekusi S4
    assert "XAUUSD" not in ns.candidates         # kandidat dibuang


def test_2_exec_tanpa_paket_tidak_order():
    br = FakeBroker()
    ns = _ns(br)
    res = _res_exec()
    res["exec"] = None
    CC.CommandCenter._try_execute_s2(ns, res, [])
    assert br.orders == []
    assert res["status"] == "BLOCKED"


def _allow(*a, **k):
    return True, "", 3840.0, 3870.0, False


def test_3_manual_lot_dipakai_utuh(monkeypatch):
    monkeypatch.setattr(S3, "validate_execution", _allow)
    br = FakeBroker()
    ns = _ns(br, pair_lot={"XAUUSD": 0.05})
    res = _res_exec()
    ns.candidates["XAUUSD"] = {"t": time.time(), "side": "BUY"}
    CC.CommandCenter._try_execute_s2(ns, res, [])
    assert len(br.orders) == 1
    o = br.orders[0]
    assert o["sym"] == "XAUUSD.x" and o["side"] == "BUY"
    assert abs(o["lot"] - 0.05) < 1e-9           # LOT MANUAL dipakai UTUH
    assert res["status"] == "TRADING"


def test_4_auto_lot_terkecil_broker(monkeypatch):
    monkeypatch.setattr(S3, "validate_execution", _allow)
    br = FakeBroker()
    ns = _ns(br, pair_lot={})                    # AUTO
    res = _res_exec()
    ns.candidates["XAUUSD"] = {"t": time.time(), "side": "BUY"}
    CC.CommandCenter._try_execute_s2(ns, res, [])
    assert len(br.orders) == 1
    assert abs(br.orders[0]["lot"] - 0.01) < 1e-9   # volume_min broker


def test_5_evaluate_exec_membuat_kandidat(monkeypatch):
    """evaluate baru (user) mengembalikan exec -> candidates terisi."""
    import cc_broker as B

    def _ev(symbol, data, k=None, st=None):
        r = S3._result(symbol, data, "BUY", "logic user")
        r["exec"] = {"sig": "BUY", "price": 3850.5, "sl": 3840.0,
                     "tp": 3870.0, "lot": 0.0}
        r["score"] = 90.0
        return r

    monkeypatch.setattr(S3, "evaluate", _ev)
    ns = _ns(FakeBroker())
    msgs = []
    ns.emit_log = lambda tag, m: msgs.append("%s %s" % (tag, m))
    CC.CommandCenter.scan_all(ns)
    assert "XAUUSD" in ns.candidates, \
        "kandidat kosong; scan=%s logs=%s" % (
            list(ns.scan.keys()), msgs)          # exec -> kandidat
    assert ns.candidates["XAUUSD"]["side"] == "BUY"
    assert ns.scan["XAUUSD"]["score"] == 90.0


def test_6_kontrak_res_evaluate_template_lengkap():
    """Field kontrak _result yang dibaca engine/Qt harus ada."""
    data = {"m15": _bars(), "m5": _bars(), "m1": _bars(),
            "info": {"bid": 1.0, "digits": 5, "spread_points": 10,
                     "point": 0.01}}
    r = S3._result("XAUUSD", data, "WAIT", "tes")
    for f in ("symbol", "price", "side", "score", "status", "why",
              "sl_price", "sl_points", "point", "exec",
              "components_buy", "components_sell", "spark_ohlc"):
        assert f in r, "kontrak hilang: %s" % f
