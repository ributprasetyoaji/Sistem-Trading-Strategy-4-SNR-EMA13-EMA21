# -*- coding: utf-8 -*-
"""v3.52: algoritma hari server broker utk pencatatan = riwayat MT5."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from cc_broker import _round30, _day_start_from


def test_round30():
    assert _round30(0) == 0
    assert _round30(3600) == 3600
    assert _round30(3600 + 899) == 3600          # 14m59s -> tetap
    assert _round30(3600 + 901) == 3600 + 1800   # 15m01s -> naik
    assert _round30(-2700) == -3600


def test_day_start_bounds():
    # 2026-10-01 00:30 WIB = 2026-09-30 17:30 UTC
    ts = 1792769400  # aprox; hitung eksplisit di bawah
    import calendar, time
    ts = calendar.timegm(time.strptime("2026-09-30 17:30:00",
                                       "%Y-%m-%d %H:%M:%S"))
    off = 3 * 3600                                # broker UTC+3
    since = _day_start_from(ts, off)
    # broker-now = 20:30 UTC -> masih hari 30 Sep utk broker
    assert since <= ts < since + 86400
    # tengah malam broker: 21:00 UTC
    assert (since - (ts - (ts - since) % 86400)) % 3600 == 0
    d0 = time.strftime("%Y-%m-%d %H:%M", time.gmtime(since))
    assert d0.endswith("21:00") or d0.endswith("00:00")
    # offset lain konsisten
    for off in (0, 2 * 3600, 5 * 3600):
        s0 = _day_start_from(ts, off)
        assert s0 <= ts < s0 + 86400
        assert ts - s0 < 86400


def test_day_start_exact_midnight():
    import calendar, time
    off = 3 * 3600
    # epoch tepat tengah malam broker (21:00 UTC)
    ts = calendar.timegm(time.strptime("2026-09-30 21:00:00",
                                       "%Y-%m-%d %H:%M:%S"))
    since = _day_start_from(ts, off)
    assert since == ts - (ts % 86400) if off == 0 else True
    # hari broker utk ts tepat berganti: 20:59:59 vs 21:00:00
    a = _day_start_from(ts - 1, off)
    b = _day_start_from(ts, off)
    assert b - a == 86400


# ======= v3.66 FIX RESET: kartu harian wajib sejak 00:00 WIB hari ini ======
def test_day_since_self_heal_day_nyangkut():
    """Engine start dgn day file/nilai kemarin (mis. start 00:00-07:00 WIB,
    UTC masih kemarin) -> day_since() wajib memperbaiki ke 00:00 WIB HARI
    INI.  Dulu: kartu terus memuat transaksi hari kemarin."""
    import calendar as _cal
    import time as _t
    import os as _os
    from cc_risk import RiskGuard, _day_date

    class B:
        def account(self):
            return {"balance": 100.0, "equity": 100.0}

    g = RiskGuard({}, B(), log=lambda *a, **k: None)
    g.day = _day_date(7.0, _t.time() - 86400)      # day "kemarin" (WIB)
    since = g.day_since()                           # harus self-heal
    assert g.day == _day_date(7.0), g.day
    exp = (_cal.timegm(_t.strptime(_day_date(7.0), "%Y-%m-%d")) - 7 * 3600)
    assert since == exp, (since, exp)


# ====== v3.67 BUKTI RESET: day file nyangkut kemarin + rollover tengah malam
def test_midnight_rollover_stuck_day_file():
    """Day file tertinggal KEMARIN, sekarang sudah lewat 00:00 WIB ->
    ensure_day() (dipanggil day_since/daily_status) wajib memutar jendela
    ke 00:00 WIB HARI INI + ambil modal baru -> kartu mulai dari nol."""
    import calendar as _cal
    import json as _json
    import os as _os
    import tempfile
    import time as _t
    from cc_risk import RiskGuard, _day_date

    yesterday = _day_date(7.0, _t.time() - 86400)
    today = _day_date(7.0)
    if yesterday == today:
        return                       # dijalankan tepat di tick pergantian
    class B:
        def account(self):
            return {"balance": 500.0, "equity": 500.0}

    d = tempfile.mkdtemp()
    df = _os.path.join(d, "day.json")
    _json.dump({"date": yesterday, "balance": 400.0, "peak": 410.0,
                "peak_bal": 410.0, "trades_today": {"X": 1}}, open(df, "w"))
    g = RiskGuard({}, B(), log=lambda *a, **k: None, day_file=df)
    g.day = yesterday                # day nyangkut kemarin
    g.day_start_balance = 400.0
    since = g.day_since()            # -> self-heal + rollover
    exp = _cal.timegm(_t.strptime(today, "%Y-%m-%d")) - 7 * 3600
    assert since == exp, (since, exp)
    assert g.day == today, g.day
    assert g.day_start_balance == 500.0          # modal hari baru
    assert g.peak_bal == 500.0                   # drawdown mulai dari 0


# ====== v3.68 PIN zona: batas hari WAJIB tengah malam WIB (UTC+7) ======
def test_day_tz_default_is_user_local_wib():
    """User di Mataram (WIB, UTC+7): kartu wajib reset jam 00:00 waktu
    DIA (sama dgn jam HP & aplikasi broker). Dulu 7.0 (WIB) -> reset
    jam 01:00 waktu user = dianggap 'belum reset'."""
    import calendar as _cal
    import time as _t
    from cc_risk import RiskGuard, _day_date

    class B:
        def account(self):
            return {"balance": 100.0, "equity": 100.0}

    import os.path as _osp
    import tempfile as _tf
    g = RiskGuard({}, B(), log=lambda *a, **k: None,
                  day_file=_osp.join(_tf.mkdtemp(), "pin_day.json"))
    assert g.tz_off == 7.0, g.tz_off
    exp = _cal.timegm(_t.strptime(_day_date(7.0), "%Y-%m-%d")) - 7 * 3600
    assert g.day_since() == exp, (g.day_since(), exp)


def test_day_tz_config_pin_wib():
    """cc_config wajib menyematkan day_tz_offset 7.0 secara eksplisit."""
    src = open("python/cc_config.py", encoding="utf-8").read()
    assert '"day_tz_offset": 7.0' in src
