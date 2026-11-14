# -*- coding: utf-8 -*-
"""Test harness backtest S4 (python/backtest4.py).

Replay memakai FUNGSI ASLI cc_strategy3.  Data sintetis sawtooth uptrend
harus menghasilkan entry BUY (bukti jalur backtest jalan = jalur live).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "python"))
import backtest4 as bt4                                    # noqa: E402
import cc_strategy3 as cs3                                 # noqa: E402


def _sawtooth_bars(cycles=9, up=20, dn=4, up_step=0.6, dn_step=-0.3,
                   base=100.0):
    """Uptrend HH/HL badan-candle: naik 20 bar, pullback 4 bar (kecil)."""
    ts = []
    o, h, l, c = [], [], [], []
    px = base
    t0 = 1_700_000_000 - (cycles * (up + dn) + 400) * 900
    for i in range(cycles * (up + dn) + 100):
        in_up = (i % (up + dn)) < up
        step = up_step if in_up else dn_step
        op = px
        px = px + step
        cl = px
        # badan penuh, tanpa wick: high=max(o,c), low=min(o,c)
        ts.append(t0 + i * 900)
        o.append(op)
        c.append(cl)
        h.append(max(op, cl))
        l.append(min(op, cl))
    return {"time": ts, "open": o, "high": h, "low": l, "close": c}


def _k():
    return cs3.s2_cfg({})


def test_replay_sintetis_buy_entry_terjadi():
    m15 = _sawtooth_bars()
    # M5 searah uptrend -> filter M5 lolos utk BUY
    m5 = {"time": list(m15["time"]),
          "close": [100.0 + 0.05 * i for i in range(len(m15["close"]))]}
    r = bt4.replay_pair(m15, m5, _k())
    # funnel wajib monotonic turun
    assert r["bias_ok"] >= r["adx_ok"] >= r["m5_ok"] >= r["touch"]
    # BUKTI BISA ENTRY: minimal 2 trade tereksekusi penuh (in->out)
    assert r["entries"] >= 2, "backtest tidak menghasilkan entry: %r" % r
    assert r["wins"] >= 1
    for t in r["trades"]:
        assert t["side"] in ("BUY", "SELL")
    closed = [t for t in r["trades"] if t["why"] in ("TP", "SL", "REVERSAL")]
    assert len(closed) == r["entries"]


def test_replay_struktur_hasil_lengkap():
    m15 = _sawtooth_bars()
    m5 = {"time": list(m15["time"]),
          "close": [100.0 + 0.05 * i for i in range(len(m15["close"]))]}
    r = bt4.replay_pair(m15, m5, _k())
    for key in ("bars", "bias_ok", "adx_ok", "m5_ok", "touch", "entries",
                "wins", "losses", "r_tot", "gross_win", "gross_loss",
                "trades"):
        assert key in r
    # tanpa posisi gantung yang tidak tercatat: r_tot = sum R trade closed
    tot = sum(t["r"] for t in r["trades"] if t["r"] is not None)
    assert abs(tot - r["r_tot"]) < 1e-6


def test_replay_sintetis_downtrend_sell_entry_terjadi():
    m15 = _sawtooth_bars()
    # mirror: balik harga (downtrend LL/LH)
    px0 = 500.0
    inv = {"time": list(m15["time"]), "open": [], "high": [], "low": [],
           "close": []}
    for v in m15["close"]:
        inv["close"].append(px0 - (v - 100.0))
    inv["open"] = [px0 - (v - 100.0) for v in m15["open"]]
    inv["high"] = [px0 - (v - 100.0) for v in m15["low"]]
    inv["low"] = [px0 - (v - 100.0) for v in m15["high"]]
    m5 = {"time": list(m15["time"]),
          "close": [400.0 - 0.05 * i for i in range(len(m15["close"]))]}
    r = bt4.replay_pair(inv, m5, _k())
    # SELL mirror harus juga bisa entry (setara live)
    assert r["entries"] >= 1, "backtest SELL tidak entry: %r" % r


def test_sinyal_entry_sama_dengan_evaluate_path():
    """Touch yang direplay = sinyal s4_structure + bias + ADX + M5 yang
    sama dgn evaluate() (kontrak funnel = urutan gerbang live)."""
    m15 = _sawtooth_bars()
    n = len(m15["close"])
    k = _k()
    found = None
    for j in range(120, n):
        win = dict((kk, list(m15[kk])[:j + 1]) for kk in
                   ("open", "high", "low", "close"))
        bias = cs3.s4_bias(win, k)
        if bias != "buy" or cs3.adx_wilder(win, 14) <= 20.0:
            continue
        st4 = cs3.s4_structure(win, k, live=m15["high"][j])
        if st4 and st4[0] == "BUY":
            found = (j, st4)
            break
    assert found, "tak ada bar dgn bias+ADX+touch BUY valid"
    j, st4 = found
    assert st4[1] > st4[2]          # zona HH di atas SL HL
    assert st4[3].startswith("S4 touch HH")
