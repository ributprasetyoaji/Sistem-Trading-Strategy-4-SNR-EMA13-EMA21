# -*- coding: utf-8 -*-
## 3.70 TEST MT4 BRIDGE (EA RBT_FX_Bridge palsu, tanpa MT4 asli)
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import pytest  # noqa: E402,F401

# ====== v3.63/v3.70 SUPPORT MT4: adapter jembatan file (EA RBT_FX_Bridge) ==
import os as _os
import threading as _th
import time as _t

import cc_broker as _cb


class FakeEA(_th.Thread):
    """EA MT4 palsu: baca cmd file -> tulis resp (protocol sama dgn EA asli)."""

    def __init__(self, folder, magic="777001"):
        super().__init__(daemon=True)
        self.folder = folder
        self.cmd = _os.path.join(folder, "rbtfx_cmd_%s.txt" % magic)
        self.resp = _os.path.join(folder, "rbtfx_resp_%s.txt" % magic)
        self.last_id = 0
        self.alive = True

    def run(self):
        while self.alive:
            try:
                with open(self.cmd) as f:
                    lines = f.read().splitlines()
            except OSError:
                _t.sleep(0.03)
                continue
            for ln in lines:
                if not ln.strip():
                    continue
                parts = (ln.split("|", 2) + ["", ""])[:3]
                cid, act, pay = parts
                iid = int(float(cid))
                if iid <= self.last_id:
                    continue
                self.last_id = iid
                with open(self.resp, "a") as f:
                    f.write(self.answer(cid, act, pay) + "\n")
            _t.sleep(0.02)

    def answer(self, cid, act, p):
        if act == "PING":
            return cid + "|OK|PONG"
        if act == "ACCOUNT":
            return cid + "|OK|12345|Akun Demo|USD|500|Exness-MT4|1000.00|995.50"
        if act == "RATES":
            sym, tf, n = p.split("|")
            n = int(n)
            base = 1600000000
            rows = []
            for i in range(n):
                o = 1.1000 + i * 0.0001
                c = o + (0.0002 if i % 2 == 0 else -0.0002)
                rows.append("%d,%.5f,%.5f,%.5f,%.5f,%d"
                            % (base + i * 300, o, o + 0.0005,
                               o - 0.0005, c, 100 + i))
            return cid + "|OK|" + ";".join(rows)
        if act == "SYMINFO":
            return cid + "|OK|5;0.00001;1.10230;1.10237;1.0;0.00001;" \
                         "0.01;100.0;0.01"
        if act == "POSITIONS":
            r1 = "111;EURUSD;0;0.10;1.10000;1.09500;1.11000;12.50;0.10;" \
                 "-0.20;777001;CC-BUY;1600000100"
            r2 = "222;GBPUSD;1;0.05;1.25000;0;0;3.20;0.00;-0.10;0;" \
                 "manual;1600000200"
            return cid + "|OK|" + r1 + "|" + r2
        if act == "ORDER":
            if p.startswith("BAD"):
                return cid + "|ERR|tidak cukup margin"
            return cid + "|OK|333;1.10240"
        if act == "HISTORY":
            rows = [
                "401;EURUSD;0;0.10;1600000000;1.10000;1600001000;1.10500;"
                "50.00;0.00;-3.00;777001",
                "402;XAUUSD;1;0.01;1600000500;2400.00;1600001500;2395.00;"
                "-25.00;0.00;-2.00;777001",
                "399;EURUSD;0;0.10;1500000000;1.10000;1500001000;1.10500;"
                "40.00;0.00;-3.00;777001",
            ]
            return cid + "|OK|" + "|".join(rows)
        if act == "SERVERTIME":
            now = int(_t.time())
            return cid + "|OK|%d|%d" % (now + 3 * 3600, now)
        if act == "QUOTE":
            return cid + "|OK|1.10230;1.10237"
        return cid + "|ERR|aksi tidak dikenal"


def _make(tmpdir):
    import tempfile
    d = tempfile.mkdtemp(dir=tmpdir)
    ea = FakeEA(d)
    ea.start()
    br = _cb.MT4Broker({"mt4_files_dir": d, "mt4_timeout": 5.0,
                        "mt4_magic": 777001})
    return ea, br


def test_mt4_connect_and_account(tmpdir):
    import tempfile
    d = tempfile.mkdtemp(dir=tmpdir)
    ea = FakeEA(d)
    ea.start()
    br = _cb.MT4Broker({"mt4_files_dir": d, "mt4_timeout": 5.0,
                        "mt4_magic": 777001})
    assert br.connect() is True
    acc = br.account()
    assert acc["login"] == "12345" and acc["currency"] == "USD"
    assert abs(acc["balance"] - 1000.0) < 0.01


def test_mt4_rates_symbolinfo_positions(tmpdir):
    ea, br = _make(tmpdir)
    assert br.connect()
    r = br.copy_rates("EURUSD", "M5", 50)
    assert r and len(r["close"]) == 50
    assert all(isinstance(v, float) for v in r["close"])
    si = br.symbol_info("EURUSD")
    assert si["digits"] == 5 and si["point"] > 0
    assert si["spread_points"] == 7      # (1.10237-1.10230)/0.00001
    pos = br.positions()
    assert len(pos) == 2
    bot = [p for p in pos if not p["manual"]]
    man = [p for p in pos if p["manual"]]
    assert len(bot) == 1 and len(man) == 1
    assert bot[0]["type"] == "BUY" and man[0]["type"] == "SELL"
    assert abs(bot[0]["pl"] - 12.50) < 0.01


def test_mt4_order_send_ok_and_fail(tmpdir):
    ea, br = _make(tmpdir)
    assert br.connect()
    r = br.order_send("EURUSD", "SELL", 0.05, 1.105, 1.095)
    assert r.ok and r.ticket == 333
    r2 = br.order_send("BADSYM", "BUY", 0.05, 0, 0)
    assert not r2.ok and "margin" in r2.comment


def test_mt4_closed_stats_filter_hari(tmpdir):
    """Deal di luar jendela (order 399, 25 hari lalu) TIDAK boleh masuk."""
    ea, br = _make(tmpdir)
    assert br.connect()
    s = br.closed_stats(1600000200)
    assert s["wins"] == 1 and s["losses"] == 1
    assert abs(s["gross_win"] - 50.0) < 0.01
    assert abs(s["gross_loss"] - 25.0) < 0.01
    assert abs(s["commission"] - (-5.0)) < 0.01
    assert abs(s["realized"] - 20.0) < 0.01   # 50-25-5
    ts = br.closed_trades_since(1600000200)
    assert len(ts) == 2
    pls = sorted(t["pl"] for t in ts)
    assert abs(pls[0] - (-27.0)) < 0.01 and abs(pls[1] - 47.0) < 0.01


def test_mt4_broker_day_since_offset_server(tmpdir):
    """Server MT4 UTC+3 -> jendela 'Today' = tengah malam zona server."""
    ea, br = _make(tmpdir)
    assert br.connect()
    s = br.broker_day_since()
    assert s % 86400 == 21 * 3600        # 00:00 server = 21:00 UTC (H-1)


def test_mt4_tick_delta_proxy(tmpdir):
    ea, br = _make(tmpdir)
    assert br.connect()
    d = br.tick_delta("EURUSD", 300)
    assert d["buy"] > 0 and d["sell"] > 0


def test_mt4_folder_kosong_fail_cepat(tmpdir):
    """Tanpa folder Common MT4 -> connect gagal CEPAT (jangan menggantung)."""
    import tempfile
    br = _cb.MT4Broker({"mt4_files_dir": _os.path.join(str(tmpdir), "kosong"),
                        "mt4_timeout": 5.0})
    t0 = _t.time()
    assert br.connect() is False
    assert _t.time() - t0 < 1.0


def test_create_broker_factory(tmpdir):
    b4 = _cb.create_broker({"broker_mode": "mt4"})
    assert isinstance(b4, _cb.MT4Broker)
    b5 = _cb.create_broker({"broker_mode": "mt5"})
    assert isinstance(b5, _cb.MT5Broker)
    bauto = _cb.create_broker({})
    assert isinstance(bauto, _cb.MT5Broker)


def test_config_support_mt4_pin(tmpdir):
    src = open("python/cc_config.py", encoding="utf-8").read()
    assert '"broker_mode": "auto"' in src
    assert '"mt4_files_dir": ""' in src
    assert '"mt4_magic": 0' in src
    assert '"mt4_timeout": 6.0' in src
