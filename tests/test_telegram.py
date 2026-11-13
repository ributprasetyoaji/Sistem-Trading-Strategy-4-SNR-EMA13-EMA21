# -*- coding: utf-8 -*-
"""v4.01: Notifikasi Telegram S2 -- off-line penuh (jaringan di-stub).

Kredensial wajib ada sebelum kirim; pemanggil engine TIDAK PERNAH
memblokir trading; event entry/close/rekap/status/news terformat."""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import cc_telegram as tg

_det_holder = [""]


def _reset(monkeypatch, tmp_path, cap_send):
    """State bersih + _post di-stub -> pesan terkirim tercatat."""
    monkeypatch.delenv("RBT_TG_TOKEN", raising=False)
    monkeypatch.delenv("RBT_TG_CHAT", raising=False)
    monkeypatch.chdir(tmp_path)
    tg._STATE.update({"token": "TOK", "chat": "CHAT", "enabled": True,
                      "online": True, "day": None, "snap": None,
                      "peak": 0.0, "dd": 0.0, "dd_eq": 0.0,
                      "t0": time.time(), "status_every": 4 * 3600,
                      "news_ts": 0.0, "news_cache": (0, []),
                      "news_seen": set(), "dedupe": {}, "cfg": {}})
    while not tg._Q.empty():
        tg._Q.get_nowait()
    cap_send.clear()
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None:
                        cap_send.append(txt) or (True, ""))
    monkeypatch.setattr(tg, "_post",
                        lambda txt, token=None, chat=None:
                        cap_send.append(txt) or True)


def test_kredensial_dari_file(monkeypatch, tmp_path):
    monkeypatch.delenv("RBT_TG_TOKEN", raising=False)
    monkeypatch.delenv("RBT_TG_CHAT", raising=False)
    monkeypatch.setattr(tg, "ROOT", str(tmp_path))
    assert tg.resolve_token() is None and tg.resolve_chat() is None
    (tmp_path / "telegram_token.txt").write_text("abc123", encoding="utf-8")
    (tmp_path / "telegram_chat.txt").write_text("456", encoding="utf-8")
    assert tg.resolve_token() == "abc123" and tg.resolve_chat() == "456"


def test_send_tanpa_token_noop():
    old = dict(tg._STATE)
    tg._STATE["enabled"] = False
    try:
        assert tg.send("x") is False
        assert tg.entry("XAUUSD", "BUY", 0.1, 1, 2, 3, "") is False
    finally:
        tg._STATE.update(old)


def test_entry_berisi_detail_lengkap(cap_send=True):
    m = tg.msg_entry("XAUUSD", "BUY", 0.15, 2650.0, 2643.45, 2663.10,
                     "(RR 1:2.0, hard broker)", "skor 82")
    assert "ENTRY S3" in m and "XAUUSD" in m and "BUY" in m
    assert "2643.45" in m and "2663.1" in m and "0.15" in m
    assert "WIB" in m


def test_close_positif_negatif():
    up = tg.msg_close("XAUUSD", 12.3, 0.15, "fase TRAIL")
    dn = tg.msg_close("BTCUSD", -6.5, 0.02, "")
    assert "\u2705" in up and "+$12.30" in up and "TRAIL" in up
    assert "\U0001f6d1" in dn and "-$6.50" in dn


def test_rekap_status_news_format():
    r = tg.msg_recap({"bal0": 510.0, "bal": 523.4, "realized": 13.4,
                      "float": -1.2, "dd": 1.8, "dd_eq": 515.2},
                     (2026, 10, 4))
    assert "REKAP HARIAN" in r and "510" in r and "523.4" in r
    assert "1.8" in r and "WIB" in r
    s = tg.msg_status({"bal": 100, "eq": 99, "realized": 1.5, "dd": 0.4},
                      "3.84", 2)
    assert "STATUS S3" in s and "Posisi terbuka: 2" in s
    n = tg.msg_news({"country": "USD", "title": "Non-Farm Payroll",
                     "wib": "19:30"}, 45, "XAUUSD, BTCUSD")
    assert "MARKET NEWS" in n and "Non-Farm Payroll" in n and "45" in n


def test_kirim_lewat_antrian_dan_dedupe(monkeypatch, tmp_path):
    sent = []
    _reset(monkeypatch, tmp_path, sent)
    assert tg.send("halo") is True
    assert tg.send("halo") is False          # dedupe 60 dtk
    tg._process_one()
    assert len(sent) == 1 and "halo" in sent[0]


def test_forward_hanya_error_protect(monkeypatch, tmp_path):
    sent = []
    _reset(monkeypatch, tmp_path, sent)
    assert tg.forward("INFO", "x") is False
    assert tg.forward("ERROR", "cek error") is True
    assert tg.forward("PROTECT", "cek protect") is True
    tg._process_one()
    tg._process_one()
    assert any("ERROR" in s for s in sent)
    assert any("PROTECT" in s for s in sent)


def test_news_high_impact_terdeteksi(monkeypatch, tmp_path):
    sent = []
    _reset(monkeypatch, tmp_path, sent)
    rilis = (datetime.now(timezone.utc) + timedelta(minutes=45))
    rilis_edt = rilis.astimezone(timezone(timedelta(hours=-4)))
    data = [{"title": "Non-Farm Employment Change", "country": "USD",
             "impact": "High",
             "date": rilis_edt.strftime("%Y-%m-%dT%H:%M:%S-04:00")},
            {"title": "Low event", "country": "USD", "impact": "Low",
             "date": rilis_edt.strftime("%Y-%m-%dT%H:%M:%S-04:00")}]
    tg._STATE["news_cache"] = (time.time(), data)
    tg._STATE["news_ts"] = 0.0
    tg._news_tick(["XAUUSD", "BTCUSD"])
    tg._process_one()
    assert any("MARKET NEWS" in s and "Non-Farm" in s for s in sent)
    # dedupe: tick lagi -> tidak dobel
    tg._STATE["news_ts"] = 0.0
    tg._news_tick(["XAUUSD"])
    tg._process_one()
    assert sum(1 for s in sent if "MARKET NEWS" in s) == 1


def test_tick_ganti_hari_wib_kirim_rekap(monkeypatch, tmp_path):
    sent = []
    _reset(monkeypatch, tmp_path, sent)
    tg._STATE["online"] = True
    tg._STATE["day"] = (2026, 10, 3)
    tg._STATE["snap"] = {"bal0": 510.0, "bal": 497.5, "eq": 497.5,
                         "realized": -12.5, "float": 0.0,
                         "dd": 2.4, "dd_eq": 498.0}
    # waktu nyata: gmtime(+7h) pasti BUKAN 2026-10-03 -> rekap terkirim
    tg.tick("3.84", 497.5, 497.5, 0.0, 0.0, 0, {}, ["XAUUSD"])
    tg._process_one()
    assert any("REKAP HARIAN" in s and "-$12.50" in s for s in sent)
    assert tg._STATE["day"] == tg._wib_day()


def test_config_kunci_telegram():
    import cc_config as c
    for k in ("tg_enabled", "tg_token", "tg_chat", "tg_news_enabled",
              "tg_news_lead_min", "tg_status_hours"):
        assert k in c.DEFAULTS, k
    assert c.DEFAULTS["tg_enabled"] is True
    assert c.CC_VERSION == "4.31"


def test_integrasi_engine_terpasang():
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    src = open(os.path.join(root, "command_center.py"),
               encoding="utf-8").read()
    assert "import cc_telegram as _tg" in src
    assert "_tg.tick(" in src          # online/dd/rekap/status/news
    assert "_tg.entry(" in src         # detail entry
    assert "_tg.close(" in src         # hasil close
    assert "_tg.forward(" in src       # ERROR/PROTECT + order gagal
    assert "_tg.restart(" in src       # self-update
    assert "_tg.engine_offline(" in src

def test_msg_connected_connecting_sukses():
    m = tg.msg_connected()
    assert "CONNECTING SUKSES" in m and "RBT FX S3" in m
    assert "WIB" in m


def test_test_send_sinkron_pakai_kredensial_argumen(monkeypatch):
    calls = []
    monkeypatch.setattr(tg, "_get_me", lambda tok: (True, "bot"))
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None:
                        calls.append((token, chat, txt)) or (True, ""))
    assert tg.test_send("TOK1", "CH1", "halo") == (True, "")
    assert calls == [("TOK1", "CH1", "halo")]


def test_rebind_aktifkan_worker_tanpa_init(monkeypatch):
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None: (True, ""))
    old = dict(tg._STATE)
    tg._STATE["enabled"] = False
    try:
        tg.rebind("TOKX", "CHX")
        assert tg._STATE["enabled"] is True
        assert tg._STATE["token"] == "TOKX"
        assert tg.send("pes") is True
    finally:
        tg._STATE.clear()
        tg._STATE.update(old)


def test_dashboard_tg_setup_terpasang():
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    d = open(os.path.join(root, "cc_dashboard.py"),
             encoding="utf-8").read()
    assert '"/api/telegram"' in d and "CONNECTING SUKSES" in d
    assert 'id="tg-go"' in d and "tg-token" in d
    c = open(os.path.join(root, "command_center.py"),
             encoding="utf-8").read()
    assert '"tg_on"' in c
    for f, mark in (("cc_qtdashboard.py", "telegram_setup"),
                    ("cc_tkdashboard.py", "telegram_setup")):
        x = open(os.path.join(root, f), encoding="utf-8").read()
        assert mark in x and "_tg_setup" in x, f

def test_ui_input_tg_kembali_update_tetap_hapus():
    """v4.11: input Telegram manual KEMBALI di dashboard (permintaan
    user) -- tombol UPDATE tetap dihapus; auto-popup tetap mati."""
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    d = open(os.path.join(root, "cc_dashboard.py"),
             encoding="utf-8").read()
    assert 'id="tg-go"' in d and "tg-token" in d
    assert "SUBMIT TG" in d and "SUBMIT MANUAL" in d
    assert 'id="tg-info"' in d and "function tgInfo" in d
    assert "keyup" in d and 'id="tg-diag"' in d
    assert 'id="upd"' not in d          # tombol update tetap dihapus
    assert "_tgPrompted" not in d       # auto-popup tetap mati
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        x = open(os.path.join(root, f), encoding="utf-8").read()
        assert "SUBMIT TG" in x and "def _tg_setup" in x, f
        assert "_tg_asked" not in x and "def _tg_offer" not in x, f
        assert "btn_upd" not in x, f


def test_dashboard_error_sertakan_detail_terpasang():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "cc_dashboard.py"), encoding="utf-8").read()
    assert '"GAGAL: %s' % "" in src or "GAGAL: %s" in src
    assert "_ok, _det = cc_telegram.test_send" in src

def test_badge_diag_tes_diagnosa(monkeypatch):
    """v3.88: badge status + TES DIAGNOSA langkah demi langkah."""
    st = tg.state()
    for k in ("on", "bot", "err", "ok_ts"):
        assert k in st, k
    # diag tanpa kredensial
    old = (tg._STATE["token"], tg._STATE["chat"])
    tg._STATE["token"] = tg._STATE["chat"] = None
    try:
        d = tg.diag()
        assert d["ok"] is False and d["steps"]
    finally:
        tg._STATE["token"], tg._STATE["chat"] = old
    # token salah
    monkeypatch.setattr(tg, "_get_me",
                        lambda tok: (False, "401: Unauthorized"))
    d = tg.diag("T", "1")
    assert d["ok"] is False and "TOKEN" in d["message"]
    # token ok tapi chat gagal (belum START)
    monkeypatch.setattr(tg, "_get_me", lambda tok: (True, "MyRbt"))
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None:
                        (False, "403: bot can't initiate"))
    d = tg.diag("T", "1")
    assert d["ok"] is False and "START" in d["message"]
    assert any("bot @MyRbt" in s["msg"] for s in d["steps"])
    # semua OK
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None: (True, ""))
    d = tg.diag("T", "1")
    assert d["ok"] is True and "AKTIF" in d["message"]
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    dweb = open(os.path.join(root, "cc_dashboard.py"),
                encoding="utf-8").read()
    assert 'id="tg-diag"' in dweb and 'id="tgb"' in dweb
    assert 'id="tg-diag"' in dweb and 'id="tgb"' in dweb
    cc = open(os.path.join(root, "command_center.py"),
              encoding="utf-8").read()
    assert '"tg_state"' in cc
    for f in ("cc_qtdashboard.py", "cc_tkdashboard.py"):
        x = open(os.path.join(root, f), encoding="utf-8").read()
        assert "lb_tg" in x and "tg_state" in x, f

def test_execution_log_bot_connected_error(monkeypatch):
    """v3.89: Execution Log menampilkan BOT CONNECTED / BOT ERROR --
    permintaan user: jelas konek atau tidak langsung di log."""
    events = []
    tg._STATE["log"] = lambda tag, msg: events.append((tag, msg))
    import tempfile as _tf
    _oroot = tg.ROOT
    tg.ROOT = _tf.mkdtemp()          # tanpa file kredensial -> pasti TG OFF
    try:
        tg._STATE["enabled"] = False
        tg._STATE["token"] = tg._STATE["chat"] = None
        tg._STATE["cfg"] = {}
        tg.init({}, log=lambda a, b: events.append((a, b)))
    finally:
        tg.ROOT = _oroot
    assert any("TG OFF" in m for _, m in events)
    events.clear()
    monkeypatch.setattr(tg, "_get_me", lambda tok: (True, "BotRbt"))
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None: (True, ""))
    tg._STATE.update({"token": "T", "chat": "1"})
    tg.test_send("T", "1", "halo")
    assert any(tg_ == "INFO" and "BOT CONNECTED" in m and "@BotRbt" in m
               for tg_, m in events), events
    events.clear()
    monkeypatch.setattr(tg, "_get_me",
                        lambda tok: (False, "401: Unauthorized"))
    tg.test_send("T", "1", "halo")
    assert any(tg_ == "ERROR" and "BOT ERROR" in m for tg_, m in events), \
        events

def test_tg_info_dan_files_present():
    """v3.90: panel SUBMIT menampilkan status + apakah kredensial
    tersimpan -- bedakan 'belum submit' vs 'gagal' vs 'tersimpan'."""
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    src = open(os.path.join(root, "cc_telegram.py"),
               encoding="utf-8").read()
    assert "def files_present" in src
    web = open(os.path.join(root, "cc_dashboard.py"),
               encoding="utf-8").read()
    assert 'elif self.path == "/api/telegram":' in web
    assert 'id="tg-info"' in web and "function tgInfo" in web
    assert "keyup" in web               # Enter = submit
    # files_present False di folder tanpa file
    old = tg.ROOT
    tg.ROOT = "/nonexistent_rbt"
    try:
        f = tg.files_present()
        assert f == {"token": False, "chat": False}
    finally:
        tg.ROOT = old

def test_input_kutip_otomatis_dibersihkan():
    """v3.91: CHAT_ID/token yang diketik pakai kutip ("123") tetap
    diterima -- penyebab nyata gagal konek di lapangan."""
    assert tg._clean('"6560789003"') == "6560789003"
    assert tg._clean("'1234567890:AAE'") == "1234567890:AAE"
    assert tg._clean("  6560789003  ") == "6560789003"
    assert tg._clean('"6560789003') == "6560789003"


def test_test_send_menggunakan_kredensial_bersih(monkeypatch):
    seen = {}
    monkeypatch.setattr(tg, "_clean", lambda v: "BERSIH")
    monkeypatch.setattr(tg, "_get_me",
                        lambda tok: seen.__setitem__("tok", tok)
                        or (True, "b"))
    monkeypatch.setattr(tg, "_post_detail",
                        lambda txt, token=None, chat=None: (True, ""))
    tg.test_send('"TOK"', '"123"', "x")
    assert seen["tok"] == "BERSIH"

def test_alasan_gagal_dan_fallback_ip():
    """v4.10: (a) kegagalan kirim runtime mencantumkan ALASAN asli
    Telegram di log & last_error; (b) fallback IP langsung + proxy
    file ada di kode; (c) rujukan panel SUBMIT TG hilang."""
    root = os.path.join(os.path.dirname(__file__), "..", "python")
    src = open(os.path.join(root, "cc_telegram.py"),
               encoding="utf-8").read()
    assert "def _tg_open" in src and "_TG_IP" in src
    assert "def _proxy" in src and "telegram_proxy.txt" in src
    assert "panel SUBMIT TG" not in src
    events = []
    tg._STATE["log"] = lambda tag, msg: events.append((tag, msg))
    oldp, olds = tg._post_detail, tg.time.sleep
    tg._post_detail = lambda txt, token=None, chat=None: \
        (False, "403: bot was blocked by the user")
    tg.time.sleep = lambda s: None
    try:
        tg._Q.put("tes-alasan")
        tg._STATE["t_last"] = 0.0
        tg._process_one()
    finally:
        tg._post_detail, tg.time.sleep = oldp, olds
    assert tg._STATE["last_error"].startswith("kirim gagal: 403")
    assert any("403" in m for _, m in events), events
    assert not any("SUBMIT TG" in m for _, m in events)

