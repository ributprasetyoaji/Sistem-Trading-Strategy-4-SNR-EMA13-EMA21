# -*- coding: utf-8 -*-
"""v4.31 (permintaan user):

  1. MAX DAILY LOSS DIHAPUS (daily_loss_pct 0 = OFF, tanpa lock).
  2. FILTER STRUKTUR MARKET (msf_gate): BUY dilarang saat struktur
     LH+LL / saat ada HH di atas < 1 ATR yang belum ditembus (rawan
     rejection); SELL cermin.  Breakout sah = lolos.
  3. FILTER AI/ML LOKAL (ml_gate): logistic regression yang dilatih
     OFFLINE dari riwayat 1-3 tahun (python/ml_train.py, 9 fitur
     karakter market; model = python/ml_model.json).  p < ml_min_p
     -> SKIP.  Fail-open bila model belum ada.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import cc_risk as CR                # noqa: E402
import cc_strategy3 as S            # noqa: E402


def test_versi_config_dan_daily_loss_dihapus():
    assert C.CC_VERSION == "4.31"
    assert "daily_loss_pct" not in C.DEFAULTS           # v4.31: dihapus total
    assert int(C.DEFAULTS["msf_enable"]) == 1
    assert abs(float(C.DEFAULTS["msf_room_atr"]) - 1.0) < 1e-9
    assert int(C.DEFAULTS["ml_enable"]) == 1
    assert abs(float(C.DEFAULTS["ml_min_p"]) - 0.30) < 1e-9


class _B(object):
    def account(self):
        return {"balance": 1000.0, "equity": 1000.0}


def test_max_daily_loss_off_besar_berapa_pun():
    import tempfile
    df = os.path.join(tempfile.mkdtemp(), "day.json")
    g = CR.RiskGuard({"daily_loss_pct": 0}, _B(), log=lambda *a, **k: None,
                     day_file=df)
    st = g.daily_status(1000.0, realized=-900.0, balance=100.0)
    assert st["halted"] is False, st          # dulu: halted di 10%
    st2 = g.daily_status(500.0)               # jalur equity lama pun bebas
    assert st2["halted"] is False


def _bars(rows, t0=1700000000):
    return {"time": [t0 + i * 900 for i in range(len(rows))],
            "open": [r[0] for r in rows], "high": [r[1] for r in rows],
            "low": [r[2] for r in rows], "close": [r[3] for r in rows],
            "tick_volume": [1] * len(rows)}


def _up(o, c, wk=0.10):
    return (o, max(o, c) + wk, min(o, c) - wk, c)


def bars_downtrend_lhll(n=88):
    """Bloks: 6 bar turun 0.4 + 2 bar pantul 0.3 -> pivot HIGH lokal
    (pantulan) selalu LEBIH RENDAH (LH) & pivot LOW makin rendah (LL)."""
    rows = []
    p = 140.0
    while len(rows) < n:
        for k in range(5):                 # 5 turun 0.4
            rows.append(_up(p, p - 0.4))
            p -= 0.4
        for k in range(3):                 # 3 pantul 0.5 (pivot LH)
            rows.append(_up(p, p + 0.5))
            p += 0.5
    return _bars(rows[:n])


def bars_uptrend_hhhl(n=88):
    """Cermin: 6 naik 0.4 + 2 koreksi 0.3 -> HH & HL jelas."""
    rows = []
    p = 60.0
    while len(rows) < n:
        for k in range(5):                 # 5 naik 0.4
            rows.append(_up(p, p + 0.4))
            p += 0.4
        for k in range(3):                 # 3 koreksi 0.5 (pivot HH)
            rows.append(_up(p, p - 0.5))
            p -= 0.5
    return _bars(rows[:n])


def bars_pivot_di_atas(px_close=100.5, pivot=100.9, n=80):
    """Oszilasi sempit + spike high (pivot) & spike low (pivot);
    bar CLOSED terakhir = px_close (di bawah pivot -> belum breakout)."""
    rows = []
    for i in range(n):
        if i == 40:                        # pivot HIGH (spike)
            rows.append((100.4, pivot, 100.3, 100.5))
            continue
        if i == 55:                        # pivot LOW (spike)
            rows.append((100.2, 100.3, 99.1, 100.2))
            continue
        if i == 64:                        # pivot LOW ke-2 (HL)
            rows.append((100.2, 100.35, 99.3, 100.25))
            continue
        o = 100.1
        c = o + (0.12 if i % 4 < 2 else -0.12)
        rows.append(_up(o, c, 0.05))
    rows[-2] = (px_close - 0.08, px_close + 0.08, px_close - 0.16,
                px_close)                  # bar CLOSED
    rows[-1] = (px_close, px_close + 0.1, px_close - 0.1,
                px_close + 0.04)           # bar forming
    return _bars(rows)


def test_msf_buy_diblokir_struktur_lhll():
    ok, why = S.msf_gate(1, bars_downtrend_lhll(), 0.5, {})
    assert ok is True and "SKIP_MSF" in why and "LH+LL" in why, (ok, why)


def test_msf_sell_diblokir_struktur_hhhl():
    ok, why = S.msf_gate(-1, bars_uptrend_hhhl(), 0.5, {})
    assert ok is True and "SKIP_MSF" in why and "HH+HL" in why, (ok, why)


def test_msf_buy_diblokir_hh_dekat_belum_breakout():
    b = bars_pivot_di_atas(px_close=100.5, pivot=100.9)
    ok, why = S.msf_gate(1, b, 0.50, {})     # jarak 0.4 ATR < 1.0 ATR
    assert ok is True and "HH/resistance" in why, (ok, why)


def test_msf_buy_lolos_setelah_breakout_di_atas_hh():
    b = bars_pivot_di_atas(px_close=101.3, pivot=100.9)
    ok, why = S.msf_gate(1, b, 0.50, {})
    assert ok is False, why                  # close sudah di atas pivot


def test_msf_sell_cermin_ruang_support():
    b = bars_pivot_di_atas(px_close=100.5, pivot=100.9)
    mir = {"time": b["time"],
           "open": [2 * 100.5 - v for v in b["open"]],
           "high": [2 * 100.5 - v for v in b["low"]],
           "low": [2 * 100.5 - v for v in b["high"]],
           "close": [2 * 100.5 - v for v in b["close"]],
           "tick_volume": b["tick_volume"]}
    ok, why = S.msf_gate(-1, mir, 0.50, {})
    assert ok is True and "LL/support" in why, (ok, why)


def test_msf_switch_off():
    b = bars_downtrend_lhll()
    ok, why = S.msf_gate(1, b, 0.5, {"msf_enable": 0})
    assert ok is False and why == ""


def test_ml_features_9_fitur_terikat():
    b = bars_pivot_di_atas()
    f = S.ml_features(1, b, len(b["close"]) - 2, 0.5)
    assert f is not None and len(f) == 9
    assert -1.001 <= f[0] <= 1.001            # sdir
    assert 0.0 <= f[2] <= 1.0                 # adx_n
    assert 0.0 <= f[3] <= 1.0                 # room
    assert -1.01 <= f[7] <= 1.01 and -1.01 <= f[8] <= 1.01  # jam


def test_ml_predict_dan_gate_blokir_low_p():
    m = {"w": [0.0] * 9, "b": 0.0}
    assert abs(S.ml_predict(m, [0.0] * 9) - 0.5) < 1e-9
    mblok = {"w": [0.0] * 9, "b": -3.0}       # p ~ 0.047
    b = bars_pivot_di_atas()
    ok, why = S.ml_gate(1, b, 0.5, {"ml_min_p": 0.5}, model=mblok)
    assert ok is True and "SKIP_ML" in why, (ok, why)
    # p tepat 0.50 (b=0) -> lolos (rule: blokir p < min_p)
    ok2, _ = S.ml_gate(1, b, 0.5, {"ml_min_p": 0.5}, model=m)
    assert ok2 is False


def test_ml_failopen_tanpa_model(monkeypatch):
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "tidak_ada.json")
    assert S.ml_load_model(p) is None
    monkeypatch.setattr(S, "ml_load_model", lambda pth=None: None)
    b = bars_pivot_di_atas()
    ok, why = S.ml_gate(1, b, 0.5, {}, model=None)
    assert ok is False                        # engine tetap jalan


def test_model_terlatih_ada_di_repo():
    p = os.path.join(os.path.dirname(__file__), "..", "python",
                     "ml_model.json")
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    assert m.get("feat_version") == 1
    assert len(m.get("w") or []) == 9
    meta = m.get("meta") or {}
    assert int(meta.get("n_train", 0)) > 5000          # belajar sungguhan
    assert float(meta.get("acc_val", 0.0)) > 0.5       # lebih baik dr tebak


def test_wiring_msf_ml_di_evaluate_setelah_adx():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_strategy3.py"),
               encoding="utf-8").read()
    i_adx = src.index("_axb, _axw = adx_gate(")
    i_msf = src.index("msf_gate(side, tail, atr15, k)")
    i_ml = src.index("ml_gate(side, tail, atr15, k)")
    assert i_adx < i_msf < i_ml, (i_adx, i_msf, i_ml)
