# -*- coding: utf-8 -*-
""""BUKTI END-TO-END ENTRY S3 (v3.76, permintaan user "pastikan semua
strategy bisa entry"; difixture-ulang v4.26 utk pipeline S3): evaluate
-> paket exec READY -> _try_execute_s2 KODE ENGINE ASLI -> seluruh
gerbang (max_baskets, warmup, wick, struktur M1, late, SNR, jenuh, MTF,
risk, sniper zona v4.23) -> ORDER TERKIRIM -> POSISI TERBUKA ->
anti-duplikat.  Tanpa MT5."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_strategy3 as S2    # noqa: E402
import command_center as ENG  # noqa: E402
import s3_fixture as FX       # noqa: E402

WANT = FX.WANT
DQ = dict(FX.DQ)


def build_data():
    return FX.market()


class _Res(object):
    ok = True
    ticket = "T1"


class FakeBroker(object):
    def __init__(self, data, px):
        self.d = data
        self.px = px
        self.pl = []
        self.orders = []

    def copy_rates(self, sym, tf_, n):
        b = {"M15": self.d["m15"], "M5": self.d["m5"], "M1": self.d["m1"],
             "M30": self.d["m30"], "H1": self.d["h1"],
             "H4": self.d["h4"]}.get(tf_)
        return {k: list(v)[-int(n):] for k, v in b.items()} if b else None

    def tick_delta(self, sym, n):
        return {"buy": 10.0, "sell": 4.0}

    def symbol_info(self, sym):
        return dict(self.d["info"])

    def symbol_tick(self, sym):
        return {"bid": self.px, "ask": self.px + 0.12}

    def positions(self):
        return list(self.pl)

    def order_send(self, sym, side, lot, sl, tp, comment=""):
        self.orders.append((sym, side, round(lot, 2), round(sl, 4), tp,
                            comment))
        self.pl.append({"ticket": "T1", "symbol": sym, "type": side,
                        "lot": lot, "entry": self.px, "sl": sl, "tp": tp,
                        "manual": False, "profit": 0.0})
        return _Res()


class RiskStub(object):
    def can_open(self, s, p, alias_names=None):
        return (True, "")

    def calc_lot(self, *a):
        return (0.10, "ok")

    def note_open(self, s):
        pass


def _make_engine(data, px):
    cc = ENG.CommandCenter.__new__(ENG.CommandCenter)
    cc.cfg = {"bars_m15": 300, "bars_m5": 200, "bars_m1": 120,
              "sl_money_usd": 0.0, "tp_money_usd": 0.0,
              "tp_broker_hard": False}
    cc.s2_on = True
    cc.s2k = {}
    cc.s2state = S2.Strategy2State(None)
    cc.candidates = {}
    cc._s3_hist = {}
    cc.resolved = {WANT: WANT}
    cc._s2_hold_memo = {}
    cc.s2_started = time.time() - 9999.0
    cc.status_lock = threading.Lock()
    cc.log_lines = []
    cc.broker = FakeBroker(data, px)
    cc.risk = RiskStub()
    cc.account_usd_rate = lambda: ("USD", 1.0)
    # guard pasar diuji terpisah (test_market_guard) -> test bebas waktu
    cc._market_guard_block = lambda s, r: False
    cc._write_signal = lambda *a, **k: None
    return cc


def test_s2_entry_e2e_order_posisi_anti_duplikat(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data, px = build_data()
    cc = _make_engine(data, px)

    # -- 1. sinyal: evaluate -> siap eksekusi + paket exec BUY --
    res = S2.evaluate(WANT, data, DQ, cc.s2state)
    assert res["status"] in ("READY", "HOLD"), res.get("why")
    assert (res.get("exec") or {}).get("sig") == "BUY"

    # -- 2. ENTRY lewat kode engine asli: semua gerbang -> ORDER --
    cc._try_execute_s2(res, cc.broker.positions())
    assert res["status"] == "TRADING", res.get("block_why") or res.get("why")
    assert len(cc.broker.orders) == 1, "order tidak terkirim"
    o = cc.broker.orders[0]
    assert o[0] == WANT and o[1] == "BUY" and o[2] == 0.10
    sl_dist = o[3] and (px - o[3])
    assert sl_dist > 0                       # SL di bawah entry (BUY)
    assert len(cc.broker.pl) == 1, "posisi tidak terbuka"
    assert any(l["tag"] == "ORDER" for l in cc.log_lines)

    # -- 3. ANTI DUPLIKAT: sinyal baru saat posisi masih terbuka --
    res2 = S2.evaluate(WANT, data, DQ, cc.s2state)
    cc._try_execute_s2(res2, cc.broker.positions())
    assert len(cc.broker.orders) == 1, "ORDER DOBEL!"
    assert res2["status"] == "TRADING"


def test_s2_semua_gerbang_kunci_data_ini():
    """Bukti per-gerbang pada data yang sama (isolasi kegagalan)."""
    data, px = build_data()
    st = S2.Strategy2State(None)
    res = S2.evaluate(WANT, data, DQ, st)
    assert res["status"] in ("READY", "HOLD"), res.get("why")
    assert res["exec"]["sig"] == "BUY"
    ok, why, slp, tpp, keep = S2.validate_execution(
        WANT, res, data, px, px + 0.12, dict(DQ), st, cooldown_until=0,
        open_baskets=0, warmup_left=0)
    assert ok, why
    assert slp > 0 and tpp > slp
