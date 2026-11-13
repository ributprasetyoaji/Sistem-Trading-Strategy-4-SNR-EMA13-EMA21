# -*- coding: utf-8 -*-
"""Suite strategi inti S3 (pengganti test_strategy2 era-S2).

Menguji API S3 yang AKTIF: gerbang data-quality, deteksi zona v4.12,
regime H1, rescue cross EMA, trigger M1, dan evaluate() end-to-end
pada fixture pasar S3-valid (BUY breakout + cermin SELL breakdown).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_strategy3 as S            # noqa: E402
import s3_fixture as FX             # noqa: E402


def test_e2e_buy_breakout_lolos_semua_gerbang():
    data, bid = FX.market()
    res = S.evaluate(FX.WANT, data, dict(FX.DQ), None)
    assert res["status"] in ("HOLD", "READY", "TRADING", "WAIT"), \
        (res.get("why"), res.get("block_why"))
    assert res["side"] == "BUY", (res.get("side"), res.get("why"),
                                  res.get("block_why"))
    assert (res.get("score") or 0) >= 70.0, res.get("score")
    assert res.get("exec"), "paket exec tidak ada"


def test_e2e_sell_breakdown_cermin():
    data, bid = FX.market_sell()
    res = S.evaluate(FX.WANT, data, dict(FX.DQ), None)
    assert res["status"] in ("HOLD", "READY", "TRADING", "WAIT"), \
        (res.get("why"), res.get("block_why"))
    assert res["side"] == "SELL", (res.get("side"), res.get("why"),
                                   res.get("block_why"))
    assert (res.get("score") or 0) >= 70.0, res.get("score")


def test_data_quality_guard():
    data, bid = FX.market()
    ok, why = S.data_quality(data["m15"], data["m5"], data["m1"],
                             data["info"], dict(FX.DQ))
    assert ok, why
    # waktu tidak urut -> ditolak
    import copy
    d2 = copy.deepcopy(data)
    t = d2["m15"]["time"]
    t[-1], t[-2] = t[-2], t[-1]
    ok2, why2 = S.data_quality(d2["m15"], d2["m5"], d2["m1"],
                               d2["info"], dict(FX.DQ))
    assert not ok2 and "urut" in why2
    # feed basi (dq_stale_sec aktif + waktu lampau) -> ditolak
    import copy
    d3 = copy.deepcopy(data)
    for tf in ("m15", "m5", "m1"):        # semua TF mundur bersama ->
        d3[tf]["time"] = [t - 40000       # sinkron tetap, feed basi
                          for t in d3[tf]["time"]]
    ok3, why3 = S.data_quality(d3["m15"], d3["m5"], d3["m1"],
                               d3["info"],
                               {"dq_stale_sec": 2700})
    assert not ok3 and "basi" in why3


def test_h1_regime_trend_up():
    data, bid = FX.market()
    atr15 = S.atr_at(data["m15"], 14)
    regime, sc = S.h1_regime(data["h1"], atr15, {})
    assert regime == "TREND_UP", (regime, sc)


def test_v412_ema_cross_rescue_state():
    # naik -> koreksi -> pulih kuat: cross-up di ekor
    c = [100.0 + 0.5 * i for i in range(30)]
    c += [c[-1] - 0.5 * i for i in range(1, 15)]
    c += [c[-1] + 1.2 * i for i in range(1, 7)]
    cu, cd = S.ema_cross_state(c, 13, 21, 5)
    assert cu is True and cd is False, (cu, cd)
    # cross lama (di luar lookback) tidak dihitung
    c2 = c + [c[-1]] * 6
    cu2, cd2 = S.ema_cross_state(c2, 13, 21, 5)
    assert cu2 is False and cd2 is False, (cu2, cd2)


def test_m1_trigger_micro_hl():
    data, bid = FX.market()
    atr5 = S.atr_at(data["m5"], 14)
    ok, why = S.m1_trigger(data["m1"], 1, atr5, {})
    assert ok, why
    ok_s, why_s = S.m1_trigger(FX.mirror_bars(data["m1"]), -1, atr5, {})
    assert ok_s, why_s


def test_zona_v412_anti_palsu_wick_kecil():
    """Pivot tanpa rejection (wick kecil) TIDAK jadi zona."""
    rows = []
    p = 100.0
    for i in range(60):
        c = p + 0.2 if i % 2 == 0 else p - 0.2
        rows.append((p, p + 0.05, c - 0.05, c))   # range kecil semua
        p = c
    bars = {"time": list(range(60)),
            "open": [r[0] for r in rows], "high": [r[1] for r in rows],
            "low": [r[2] for r in rows], "close": [r[3] for r in rows],
            "tick_volume": [1] * 60}
    a = S.atr_at(bars, 14)
    zones = S.detect_zones(bars, a, {}, 58)
    assert zones == [], zones


def test_validate_execution_tanpa_paket_menunggu():
    data, bid = FX.market()
    ok, why, slp, tpp, keep = S.validate_execution(
        FX.WANT, {}, data, bid, bid + 0.12, {}, None)
    assert ok is False and slp == 0.0 and tpp == 0.0
