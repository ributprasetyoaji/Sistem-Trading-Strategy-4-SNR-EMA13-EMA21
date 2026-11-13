# -*- coding: utf-8 -*-
"""v4.23: SL = wick SNR TERDEKAT + clamp lantai 0.45 ATR; sniper M1
sadar zona SNR/rejection; entry cepat pasca-reload per-pair (warmup 20s).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_scanner as SC             # noqa: E402
import cc_strategy3 as S            # noqa: E402
import s3_fixture as FX             # noqa: E402


def test_versi():
    assert C.CC_VERSION >= "4.23"


def _res_exec_buy(zone_lo, zone_hi, sl_ref=None):
    return {"status": "READY",
            "exec": {"sig": "BUY", "atr15": 0.60, "atr5": 0.15,
                     "sim": 100.0, "sample": 20,
                     "zone": {"lo": zone_lo, "hi": zone_hi,
                              "id": "R45", "type": "RESISTANCE"},
                     "sl_ref": sl_ref}}


def _run(res):
    data, bid = FX.market()
    return S.validate_execution(FX.WANT, res, data, bid, bid + 0.12,
                                dict(FX.DQ), None, cooldown_until=0,
                                open_baskets=0, warmup_left=0)


def test_sl_pilih_struktur_terdekat_bukan_terjauh():
    # dua struktur di bawah entry: 106.50 (dekat) & 105.00 (jauh) ->
    # v4.23 wajib ambil yang TERDEKAT (dulu min() mengambil terjauh)
    ok, why, slp, tpp, keep = _run(_res_exec_buy(106.50, 107.14,
                                                 sl_ref=105.00))
    assert ok, why
    sl_harap = 106.50 - 0.35 * 0.60        # buffer struktur 0.35 ATR
    assert abs(slp - sl_harap) < 1e-6, (slp, sl_harap)


def test_sl_terlalu_rapat_di_clamp_lantai_045atr_tanpa_skip():
    # struktur nempel di entry -> lantai 0.45 ATR, entry TETAP JALAN
    ok, why, slp, tpp, keep = _run(_res_exec_buy(107.53, 107.80))
    assert ok, why
    entry = 107.45 + 0.12
    sl_harap = entry - 0.45 * 0.60
    assert abs(slp - sl_harap) < 1e-6, (slp, sl_harap)


def test_sniper_zone_reject_buy_wajib_rejection():
    data, bid = FX.market()
    m1 = data["m1"]
    a = 0.60
    zn = {"lo": 108.00, "hi": 108.50}
    # (1) harga di atas zona lawan = breakout valid -> boleh
    res = {"exec": {"opp": zn}}
    ok, why = SC._sniper_zone_reject(res, 1, 108.60, m1, a, {})
    assert ok is True, why
    # (2) zona masih jauh -> boleh tunggu di harga sekarang
    ok2, why2 = SC._sniper_zone_reject(res, 1, 107.45, m1, a, {})
    assert ok2 is True, why2
    # (3) harga menempel zona TANPA rejection M1 -> DITAHAN
    ok3, why3 = SC._sniper_zone_reject(res, 1, 107.90, m1, a, {})
    assert ok3 is False and "tunggu" in why3, (ok3, why3)
    # (4) dgn rejection M1 (wick atas nembus tepi, close kembali di
    #     bawah) -> boleh entry
    m1r = {k: list(v) for k, v in m1.items()}
    m1r["open"][-1] = 107.95
    m1r["high"][-1] = 108.05            # wick atas ke dalam zona
    m1r["close"][-1] = 107.97           # close kembali di bawah lo
    m1r["low"][-1] = 107.94
    ok4, why4 = SC._sniper_zone_reject(res, 1, 107.90, m1r, a, {})
    assert ok4 is True, why4


def test_sniper_failopen_tanpa_zona_lawan():
    ok, why = SC._sniper_zone_reject({"exec": {}}, 1, 107.0, {}, 0.6, {})
    assert ok is True


def test_warmup_20_detik_default():
    assert int(C.DEFAULTS["s3"].get("warmup_sec", 0)) == 20
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert 'k.get("warmup_sec", 20)' in src or \
        'cfg.get("warmup_sec", 20)' in src
