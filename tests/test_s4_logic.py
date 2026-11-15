"""v4.46 LOGIC ENTRY S4 (spesifikasi user -- PERBAIKAN POLA SWING):
Indikator EMA13/21 + BB(25,2.1) middle + ADX14>20; bias stack M15
(EMA13>EMA21>mid = BUY-only; mid>EMA21>EMA13 = SELL-only); struktur
BADAN candle (bukan wick); filter M5 kontra; max daily loss 30 USD.
DUA TIPE ENTRY (user v4.46):
  TIPE A: tren naik -> zona HH -> turun -> HL valid terkonfirmasi ->
          langsung BUY (SL = titik HL).  Mirror SELL (LL -> LH -> SELL).
  TIPE B: naik lagi -> HH BARU -> zona HH lama MENJADI zona HL -> saat
          harga turun MENYENTUH titik itu -> BUY lagi (SL di bawah
          zona).  Mirror SELL (LL baru -> zona LL lama jadi zona LH ->
          naik menyentuh -> SELL lagi).  RR 1:1; 0.6R -> SL +0.2R;
          tren pembalik + profit -> close."""
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import cc_strategy3 as S  # noqa: E402
import command_center as CC  # noqa: E402


def _bars(closes, spread=2.0):
    """bars dgn close eksplisit; high/low = close+-spread (body-driven)."""
    n = len(closes)
    return {"time": list(range(1000, 1000 + n)),
            "open": closes[:], "high": [x + spread for x in closes],
            "low": [x - spread for x in closes], "close": closes[:]}


def _uptrend_bars():
    """TIPE A (user v4.46): naik -> plateau (H0) -> dip (L0) -> naik ->
    HH 100 (H1) -> turun -> HL 96.5 (L1) -> konfirmasi naik -> live
    99.2 masih pullback DI DALAM struktur (di atas HL, BELUM menyentuh
    zona HH) -> BUY.  Wick tipis (body-driven)."""
    up = [90 + 0.5 * i for i in range(11)]          # 90 -> 95
    h0 = [95.0] * 3                                  # pivot H0
    dip = [93.2, 92.8, 93.0]                         # pivot L0
    up2 = [94.5 + 0.55 * i for i in range(10)]       # 94.5 -> 99.4
    h1 = [100.0] * 4                                 # pivot H1 (zona HH)
    pb = [98.25, 97.375, 96.5]                       # pivot L1 (HL)
    tail = [97.4, 97.7, 98.0, 98.3]                  # konfirmasi HL
    live = [99.2]                                    # pullback dalam struktur
    return _bars(up + h0 + dip + up2 + h1 + pb + tail + live,
                 spread=0.12)


def _retest_bars(h2=104.0, tail_last=102.0, live=99.8):
    """TIPE B (user v4.46): HH1=100 -> HL 97 -> naik -> HH BARU=h2 ->
    turun -> bar berjalan live MENYENTUH zona HH1=100 (touch pertama)
    -> BUY lagi.  SL = zona - 0.5 x (HH1 - HL) = 98.5."""
    up = [90 + 0.5 * i for i in range(11)]          # 90 -> 95
    h0 = [95.0] * 3                                  # pivot H0
    dip = [93.2, 92.8, 93.0]                         # pivot L0
    up2 = [94.5 + 0.55 * i for i in range(10)]       # 94.5 -> 99.45
    h1 = [100.0] * 4                                 # HH1 = 100 (zona)
    pb = [98.5, 97.0, 97.2]                          # HL 97 (pivot)
    up3 = [97.6, 98.2, 98.8, 99.4, 100.2, 101.0]     # naik lagi
    h2s = [h2] * 4                                   # HH baru (pivot di b3)
    dn2 = [103.0, 102.5, tail_last]                  # pullback
    livev = [live]
    return _bars(up + h0 + dip + up2 + h1 + pb + up3 + h2s + dn2 + livev,
                 spread=0.12)


def _downtrend_a_bars():
    """TIPE A SELL (mirror): turun -> LL 120 -> naik -> LH 124.2 valid
    terkonfirmasi -> live 122.5 masih pullback (di atas LL zona, di
    bawah LH) -> SELL (SL = titik LH)."""
    dn = [130 - 0.5 * i for i in range(9)]           # 130 -> 126
    h0 = [126.0] * 3                                 # pivot H0
    dip = [124.8, 124.4, 124.9]                      # pivot L0
    h1 = [125.3, 125.6]                              # lower high
    dn2 = [125.2 - 0.4 * i for i in range(13)]       # 125.2 -> 120.4
    l1 = [120.0] * 4                                 # LL zona = 120
    pb = [121.0, 122.0, 123.0, 124.2]                # pivot LH
    tail = [123.0, 122.72, 122.44, 122.16]           # konfirmasi LH
    live = [122.5]                                   # pullback dalam struktur
    return _bars(dn + h0 + dip + h1 + dn2 + l1 + pb + tail + live,
                 spread=0.12)


def _downtrend_b_bars():
    """TIPE B SELL (mirror): LL1=120 -> LH 124.2 -> turun -> LL BARU
    116.8 -> naik -> bar berjalan live MENYENTUH zona LL1=120 (touch
    pertama dari bawah) -> SELL lagi.  SL = zona + 0.5 x (LH - LL1)."""
    dn = [130 - 0.5 * i for i in range(9)]           # 130 -> 126
    h0 = [126.0] * 3                                 # pivot H0
    dip = [124.8, 124.4, 124.9]                      # pivot L0
    h1 = [125.3, 125.6]                              # lower high
    dn2 = [125.2 - 0.4 * i for i in range(13)]       # 125.2 -> 120.4
    l1 = [120.0] * 4                                 # LL1 zona = 120
    pb = [121.0, 122.0, 123.0, 124.2]                # pivot LH
    dn3 = [123.8, 123.4, 123.0]                      # turun lagi
    dn4 = [122.5, 121.8, 121.2, 120.5, 119.8, 119.0,
           118.4, 117.8, 117.2, 116.8]               # LL baru 116.8
    up = [117.5, 118.2, 118.9, 119.6]                # konfirmasi LL baru
    live = [119.9]                                   # NAIK menyentuh zona 120
    return _bars(dn + h0 + dip + h1 + dn2 + l1 + pb + dn3 + dn4 + up +
                 live, spread=0.12)


def _info(bid=99.2, point=0.01):
    return {"bid": bid, "ask": bid + 0.1, "digits": 2,
            "spread_points": 150, "point": point, "volume_min": 0.01}


K = S.s2_cfg({})


# -------------------------- indikator & bias --------------------------

def test_adx_tren_vs_flat():
    flat = _bars([100.0] * 60)
    up = _bars([100 + i * 0.5 for i in range(60)])
    assert S.adx_wilder(flat, 14) < 20.0
    assert S.adx_wilder(up, 14) > 20.0
    assert S.adx_wilder({"high": [1], "low": [1], "close": [1]}, 14) == 0.0


def test_bias_stack_user():
    # BUY: EMA13 > EMA21 > mid -> naik stabil
    assert S.s4_bias(_bars([100 + 0.4 * i for i in range(60)]), K) == "buy"
    # SELL: mid > EMA21 > EMA13 -> turun stabil
    assert S.s4_bias(_bars([130 - 0.4 * i for i in range(60)]), K) == "sell"
    # netral: flat sempurna (semua garis sama -> tak lulus stack manapun)
    assert S.s4_bias(_bars([100.0] * 60), K) is None
    assert S.s4_bias({}, K) is None


def test_m5_kontra_filter():
    up5 = _bars([100 + 0.3 * i for i in range(40)])
    dn5 = _bars([130 - 0.3 * i for i in range(40)])
    assert S.s4_m5_ok("BUY", up5, K) is True
    assert S.s4_m5_ok("BUY", dn5, K) is False     # M5 kontra -> skip BUY
    assert S.s4_m5_ok("SELL", dn5, K) is True
    assert S.s4_m5_ok("SELL", up5, K) is False
    assert S.s4_m5_ok("BUY", {"close": [1]}, K) is True   # data kurang


def test_body_pivots_bukan_wick():
    # wick tinggi di idx 10 TAPI body (close) tak jadi pivot tertinggi
    b = _bars([100 + 0.2 * i for i in range(30)])
    b["high"][10] = 200.0                          # wick palsu
    pv = S.body_pivots(b, 3)
    hs = [p[2] for p in pv if p[0] == "H"]
    assert all(x < 200.0 for x in hs)              # wick TIDAK dipakai


# ---------------------- struktur & entry touch ------------------------

def test_s4_structure_buy_hl_valid():
    """TIPE A: HH -> HL valid terkonfirmasi -> harga masih pullback di
    dalam struktur -> BUY (SL = titik HL)."""
    b = _uptrend_bars()
    r = S.s4_structure(b, K)
    assert r is not None and r[0] == "BUY"
    zona, sl = r[1], r[2]
    assert abs(zona - 100.0) < 0.2                  # zona = titik HH (body)
    assert abs(sl - 96.5) < 0.4                     # SL = titik HL (body)
    assert zona > sl
    # harga sudah menyentuh zona HH (bar berjalan/berjalan lewat) ->
    # fase pullback pertama lewat -> TIDAK entry tipe A
    b2 = _uptrend_bars()
    b2["close"][-1] = b2["high"][-1] = 100.2        # live >= zona
    assert S.s4_structure(b2, K) is None
    # bar selesai menyentuh zona HH -> zona sudah dipakai -> None
    b3 = _uptrend_bars()
    b3["close"][-2] = b3["high"][-2] = 100.5
    assert S.s4_structure(b3, K) is None
    # harga jatuh di bawah HL -> HL gagal -> None
    b4 = _uptrend_bars()
    b4["close"][-1] = 96.4
    assert S.s4_structure(b4, K) is None


def test_s4_structure_sell_lh_valid():
    """TIPE A SELL (mirror): LL -> LH valid terkonfirmasi -> pullback ->
    SELL (SL = titik LH)."""
    b = _downtrend_a_bars()
    r = S.s4_structure(b, K)
    assert r is not None and r[0] == "SELL"
    assert abs(r[1] - 120.0) < 0.2                  # zona = titik LL (body)
    assert abs(r[2] - 124.2) < 0.3                  # SL = titik LH (body)


def test_s4_structure_buy_retest_hh_lama():
    """TIPE B: HH baru terbentuk -> zona HH lama menjadi zona HL -> saat
    harga TURUN MENYENTUH titik itu -> BUY LAGI (SL di bawah zona)."""
    b = _retest_bars()                               # live 99.8 sentuh 100
    r = S.s4_structure(b, K)
    assert r is not None and r[0] == "BUY"
    zona, sl = r[1], r[2]
    assert abs(zona - 100.0) < 0.2                  # zona = HH LAMA
    assert abs(sl - 98.5) < 0.2                     # SL = zona - 0.5 x (3.0)
    assert zona > sl
    # HH "baru" TIDAK lebih tinggi (bukan HH baru) -> None
    assert S.s4_structure(_retest_bars(h2=100.0), K) is None
    # bar selesai sudah menyentuh zona -> touch pertama lewat -> None
    assert S.s4_structure(_retest_bars(tail_last=99.5), K) is None
    # harga turun melewati batas bawah zona (chase) -> None
    assert S.s4_structure(_retest_bars(live=98.0), K) is None


def test_s4_structure_sell_retest_ll_lama():
    """TIPE B SELL (mirror): LL baru -> zona LL lama menjadi zona LH ->
    harga NAIK menyentuh titik itu -> SELL lagi (SL di atas zona)."""
    b = _downtrend_b_bars()                          # live 119.9 sentuh 120
    r = S.s4_structure(b, K)
    assert r is not None and r[0] == "SELL"
    zona, sl = r[1], r[2]
    assert abs(zona - 120.0) < 0.2                  # zona = LL LAMA
    assert abs(sl - 122.1) < 0.2                    # SL = zona + 0.5 x (4.2)
    assert sl > zona


def test_evaluate_full_buy_rr11():
    b = _uptrend_bars()
    data = {"m15": b, "m5": _bars([100 + 0.3 * i for i in range(40)]),
            "m1": _bars([100.0] * 40), "info": _info()}
    r = S.evaluate("XAUUSD", data, K, None)
    assert r["status"] == "READY"
    assert r["side"] == "BUY" and r["exec"]["sig"] == "BUY"
    ex = r["exec"]
    assert abs(ex["sl"] - ex["price"]) > 0
    assert abs((ex["tp"] - ex["price"]) -
               (ex["price"] - ex["sl"])) < 1e-9    # TP = 1 x jarak SL
    assert r["score"] >= 70                        # READY di dashboard


def test_evaluate_filter_rantai():
    # ADX lemah -> WAIT
    b = _uptrend_bars()
    flat5 = _bars([100.0] * 60)
    data = {"m15": b, "m5": flat5, "m1": {}, "info": _info()}
    k2 = dict(K); k2["adx_min"] = 99.0
    r = S.evaluate("XAUUSD", data, k2, None)
    assert r["status"] == "WAIT" and "ADX" in r["why"]
    # M5 kontra -> WAIT
    data2 = {"m15": b, "m5": _bars([130 - 0.3 * i for i in range(40)]),
             "m1": {}, "info": _info()}
    r2 = S.evaluate("XAUUSD", data2, K, None)
    assert r2["status"] == "WAIT" and "M5" in r2["why"]


def test_validate_execution_ok_dan_gagal():
    b = _uptrend_bars()
    data = {"m15": b, "m5": _bars([100 + 0.3 * i for i in range(40)]),
            "m1": {}, "info": _info()}
    res = S.evaluate("XAUUSD", data, K, None)
    ok, why, sl, tp, keep = S.validate_execution(
        "XAUUSD", res, data, 99.2, 99.3, K, None)
    assert ok is True and keep is False
    assert abs(sl - res["exec"]["sl"]) < 1e-9
    assert abs((tp - 99.2) - (99.2 - sl)) < 1e-9   # RR 1:1
    # bias berbalik saat eksekusi -> blokir
    res2 = S.evaluate("XAUUSD", data, K, None)
    dn15 = _bars([130 - 0.4 * i for i in range(60)])
    ok2, why2, _, _, _ = S.validate_execution(
        "XAUUSD", res2, {"m15": dn15, "m5": data["m5"]}, 99.2, 99.3,
        K, None)
    assert ok2 is False and "bias" in why2


def test_s4_reversal():
    up = _bars([100 + 0.4 * i for i in range(60)])
    dn = _bars([130 - 0.4 * i for i in range(60)])
    assert S.s4_reversal(dn, "BUY", K) is True     # BUY: EMA13 < EMA21
    assert S.s4_reversal(up, "BUY", K) is False
    assert S.s4_reversal(up, "SELL", K) is True


# --------------------------- engine gates ---------------------------

def test_daily_loss_gate_blokir():
    class Br:
        def closed_stats(self, since):
            return {"realized": -60.0}              # -60 USD hari ini

    ns = types.SimpleNamespace()
    ns.broker = Br()
    ns.risk = types.SimpleNamespace(day_since=lambda: 0)
    ns.account_usd_rate = lambda: ("USD", 1.0)
    ns._s4_dl_cache = (0.0, 0.0)
    ns.candidates = {"XAUUSD": {}}
    ns.emit_log = lambda t, m: None
    res = {"status": "READY", "block_why": "", "exec": {"sig": "BUY"}}
    # panggil via wrapper: tempel logika gate -> gunakan method asli
    # (gate ada di _try_execute_s2; uji lewat _ns pipeline)
    class FakeState:
        def cooldown_until(self, w):
            return 0.0

        def clear(self, w):
            pass

        def save(self):
            pass

        def __getattr__(self, n):
            return lambda *a, **k: None

    class Risk2:
        def can_open(self, s, p):
            return True, ""

        def day_since(self):
            return 0

    def bars(n=80, px=3850.0):
        return {"time": list(range(1000, 1000 + n)), "open": [px] * n,
                "high": [px + 5] * n, "low": [px - 5] * n,
                "close": [px + 1] * n}

    br = Br()
    ns2 = types.SimpleNamespace()
    ns2.cfg = {"bars_m5": 200, "bars_m1": 120, "min_score": 70,
               "max_baskets": 3, "warmup_sec": 20, "sl_money_usd": 0.0,
               "tp_money_usd": 0.0, "tp_rr": 1.0, "tp1_rr": 1.0,
               "tp2_rr": 1.0, "tp_mode": "close", "tp_broker_hard": True,
               "min_entry_lot": 0.04, "tp_min_rr_net": 0.6}
    ns2.resolved = {"XAUUSD": "XAUUSD.x"}
    ns2.broker = br
    ns2.risk = Risk2()
    ns2.s2state = FakeState()
    ns2.s2_started = time.time() - 1000
    ns2.s2k = dict(K)
    ns2.s2_on = True
    ns2.scan = {}
    ns2.candidates = {"XAUUSD": {"t": time.time(), "side": "BUY"}}
    ns2.pair_sw = {"XAUUSD": True}
    ns2.pair_lot = {}
    ns2._s2_hold_memo = {}
    ns2.emit_log = lambda t, m: None
    ns2._write_signal = lambda *a, **k: None
    ns2.account_usd_rate = lambda: ("USD", 1.0)
    ns2._market_guard_block = lambda s, r: False
    ns2.pair_lot_of = lambda w: 0.0
    ns2._fetch_data = lambda w, s: {
        "m15": bars(), "m5": bars(), "m1": bars(),
        "info": {"bid": 3850.1, "ask": 3850.5, "digits": 2,
                 "spread_points": 150, "point": 0.1, "volume_min": 0.01}}
    res2 = {"symbol": "XAUUSD", "price": 3850.5, "side": "BUY",
            "score": 85.0, "status": "READY", "strategy": "S2",
            "info": ns2._fetch_data("XAUUSD", "X")["info"],
            "exec": {"sig": "BUY", "price": 3850.5, "sl": 3840.0,
                     "tp": 3860.5, "lot": 0.0},
            "components_buy": {}, "components_sell": {}, "ohlc": []}
    CC.CommandCenter._try_execute_s2(ns2, res2, [])
    assert res2["status"] == "BLOCKED"
    assert "DAILY LOSS" in res2["block_why"]       # -60 < -30 -> blokir


def test_trailing_s4_rules():
    """0.6R -> SL ke +0.2R; reversal + profit -> close market."""
    class Br:
        def __init__(self):
            self.mod = []
            self.closed = []

        def positions(self):
            return [{"symbol": "XAUUSD", "manual": False, "ticket": 77,
                     "entry": 100.0, "sl": 99.0, "lot": 0.01,
                     "type": "BUY"}]

        def symbol_tick(self, s):
            return {"bid": 100.7, "ask": 100.75}

        def symbol_info(self, s):
            return {"bid": 100.7, "ask": 100.75}

        def copy_rates(self, s, tf, n=300):
            if tf == "M15":
                return _bars([130 - 0.4 * i for i in range(60)])  # flip
            return _bars([100.0] * 40)

        def modify_sl(self, t, sl, tp=None):
            self.mod.append((t, sl))

        def close_position(self, t):
            self.closed.append(t)

    class St:
        trail = {}

        def get_trail(self, w):
            return self._tr

        def set_trail(self, w, tr):
            pass

        def set_cooldown(self, w, m=10):
            pass

        def del_trail(self, w):
            pass

        def save(self):
            pass

    br = Br()
    st = St()
    tr = S.ATRTrail("XAUUSD", 1, 100.0, 1.0 / 1.2,
                    {"sl_atr": 1.2})               # risk_dist = 1.0
    st._tr = tr
    ns = types.SimpleNamespace()
    ns.s2k = dict(K)                               # s4_exit True
    ns.broker = br
    ns.s2state = st
    ns.cfg = {"tp_money_usd": 0.0}
    ns._rate_val = 0.0
    ns._want_of = lambda s: "XAUUSD"
    ns.emit_log = lambda t, m: None
    pos = [{"symbol": "XAUUSD", "manual": False, "ticket": 77,
            "entry": 100.0, "sl": 99.0, "lot": 0.01, "type": "BUY"}]
    CC.CommandCenter._s2_manage_exits(ns)
    # R = 0.7 >= 0.6 -> SL digeser ke 100.2 (+0.2R)
    assert (77, 100.2) in [tuple(x) for x in br.mod]
    # M15 sudah flip ke sell & profit>0 -> close reversal
    assert br.closed == [77]
