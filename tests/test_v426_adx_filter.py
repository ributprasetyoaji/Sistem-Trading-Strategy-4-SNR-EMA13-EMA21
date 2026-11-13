# -*- coding: utf-8 -*-
"""v4.31 (permintaan user): FILTER ADX > 25 utk Strategy 3.

  - adx_wilder  = ADX klasik Wilder di M15 (tanpa look-ahead).
  - adx_gate    = entry hanya saat ADX > adx_min (default 25);
                  ADX <= 25 = sideways -> SKIP; fail-open data kurang;
                  bisa dimatikan (adx_filter 0).
  - Wiring      = evaluate() SETELAH gerbang EMA + reversal v4.24
                  (aturan arah dulu, baru kekuatan tren).
Catatan sejarah: ADX justru DIHAPUS dari S1 (v3.92); S3 diminta
memakainya (permintaan user v4.31).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_strategy3 as S            # noqa: E402
import s3_fixture as FX             # noqa: E402


def _trend_bars(n=120, step=1.2, base=100.0):
    h, l, c, p = [], [], [], base
    for i in range(n):
        h.append(p + 3.0)
        l.append(p - 1.0)
        c.append(p + 2.0)
        p += step
    return h, l, c


def _side_bars(n=120, amp=1.5):
    import math
    h, l, c = [], [], []
    p = 100.0
    for i in range(n):
        o = amp * math.sin(i * 1.7)
        h.append(p + o + 1.5)
        l.append(p + o - 1.5)
        c.append(p + o * 0.3)
    return h, l, c


def test_adx_wilder_tren_tinggi_sideways_rendah():
    ht, lt, ct = _trend_bars()
    a_tren = S.adx_wilder(ht, lt, ct, 14)
    hs, ls, cs = _side_bars()
    a_side = S.adx_wilder(hs, ls, cs, 14)
    assert a_tren is not None and a_tren > 30.0, a_tren
    assert a_side is not None and a_side < 25.0, a_side


def test_adx_wilder_data_kurang_failopen():
    h, l, c = _trend_bars(n=20)
    assert S.adx_wilder(h, l, c, 14) is None      # < 2*14+1 bar
    assert S.adx_wilder([], [], []) is None
    h2, l2, c2 = _trend_bars(n=60)
    assert S.adx_wilder(h2, l2, c2, 7) is not None


def test_adx_gate_blokir_sideways_dgn_pesan_skip():
    hs, ls, cs = _side_bars()
    blok, why = S.adx_gate(hs, ls, cs, {})
    assert blok is True
    assert "SKIP_ADX" in why and "25" in why


def test_adx_gate_lolos_saattren():
    ht, lt, ct = _trend_bars()
    blok, why = S.adx_gate(ht, lt, ct, {})
    assert blok is False and why == ""


def test_adx_gate_bisa_dimatikan():
    hs, ls, cs = _side_bars()
    blok, why = S.adx_gate(hs, ls, cs, {"adx_filter": 0})
    assert blok is False and why == ""


def test_adx_gate_failopen_data_kurang():
    h, l, c = _trend_bars(n=20)
    blok, why = S.adx_gate(h, l, c, {})
    assert blok is False and why == ""


def test_adx_gate_adx_min_kustom_strict_more_than():
    ht, lt, ct = _trend_bars()
    a = S.adx_wilder(ht, lt, ct, 14)
    # min DI ATAS adx nyata -> wajib blok (hanya > min yang lolos)
    blok, why = S.adx_gate(ht, lt, ct, {"adx_min": a + 5.0})
    assert blok is True and "SKIP_ADX" in why
    # min DI BAWAH adx nyata -> lolos
    blok2, _ = S.adx_gate(ht, lt, ct, {"adx_min": a - 5.0})
    assert blok2 is False
    # min 0 -> sideways pun lolos (ADX > 0)
    hs, ls, cs = _side_bars()
    blok3, _ = S.adx_gate(hs, ls, cs, {"adx_min": 0.0})
    assert blok3 is False


def test_config_kunci_default_terpasang():
    for k, v in (("adx_filter", 1), ("adx_min", 25.0), ("adx_period", 14)):
        assert k in C.DEFAULTS, k
        assert C.DEFAULTS[k] == v, k
        assert k in S.DEFAULTS, k
    assert C.CC_VERSION == "4.31"


def test_e2e_evaluate_zona_valid_tapi_adx_dibawah_min_blokir():
    """Bukti wiring: pasar fixture (zona valid, lolos EMA/reversal)
    diblok SKIP_ADX saat adx_min dinaikkan di atas ADX nyata; dan
    kembali lolos (HOLD) saat adx_filter=0."""
    data, bid = FX.market()
    atr15 = 0.60
    # ADX fixture ~35 (cek nyata, jangan hard-code buta)
    adx = S.adx_wilder(data["m15"]["high"], data["m15"]["low"],
                       data["m15"]["close"], 14)
    assert adx > 25.0, adx
    k1 = dict(FX.DQ)
    k1["adx_min"] = 99.0                       # mustahil -> wajib SKIP_ADX
    res = S.evaluate(FX.WANT, data, k1, None)
    # skor gerbang dsb tetap harus terlewati -> yang menangkap = ADX
    assert res["status"] == "BLOCKED", (res.get("why"),
                                        res.get("block_why"))
    assert str(res.get("block_why", "")).startswith("SKIP_ADX"), \
        res.get("block_why")
    # matikan filter -> tidak ada SKIP_ADX lagi
    k2 = dict(FX.DQ)
    k2["adx_min"] = 99.0
    k2["adx_filter"] = 0
    res2 = S.evaluate(FX.WANT, data, k2, None)
    assert "SKIP_ADX" not in str(res2.get("block_why") or "")
    assert res2.get("status") in ("HOLD", "READY", "TRADING", "WAIT"), \
        (res2.get("status"), res2.get("why"), res2.get("block_why"))


def test_e2e_fixture_default_lolos_gerbang_adx_25():
    """Default produksi (ADX > 25): fixture tren lolos gerbang ADX."""
    data, bid = FX.market()
    res = S.evaluate(FX.WANT, data, dict(FX.DQ), None)
    assert str(res.get("block_why") or "") != "x"
    assert "SKIP_ADX" not in str(res.get("block_why") or ""), \
        res.get("block_why")
    assert res["status"] in ("HOLD", "READY", "TRADING", "WAIT"), \
        (res["status"], res.get("why"), res.get("block_why"))
