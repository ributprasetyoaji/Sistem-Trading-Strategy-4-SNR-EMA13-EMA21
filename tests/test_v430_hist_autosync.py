# -*- coding: utf-8 -*-
"""v4.31 (permintaan user): PASTIKAN backup data history ke GitHub
2X SEHARI -- muat ulang cukup restore cloud + delta, tanpa menarik
ulang 1 tahun dari broker.

  - delta_min_hours 12.0 (dulu terikat upload_min_hours 24 -> 1x/hari)
  - _cloud_autosync_tick: cek berkala tiap 10 mnt di loop utama
    (thread), upload delta saat jatuh tempo 12 jam -- TIDAK bergantung
    reload/start engine.
  - BASE tetap hemat (>= 1000 bar baru & >= 24 jam).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import command_center as ENG        # noqa: E402
import github_hist as GH            # noqa: E402


def test_versi_dan_config():
    assert C.CC_VERSION == "4.31"
    hc = C.DEFAULTS["hist_cloud"]
    assert hc["enabled"] is True
    assert abs(float(hc["delta_min_hours"]) - 12.0) < 1e-9   # 2x/hari
    assert abs(float(hc["autosync_every_sec"]) - 600.0) < 1e-9
    assert float(hc["upload_min_hours"]) == 24.0             # BASE tetap
    assert int(hc["delta_min_new_bars"]) == 20


def test_should_upload_base_kebijakan_tetap():
    now = time.time()
    # bar bertambah cukup + sudah > 24 jam -> upload BASE
    ok, why = GH.should_upload(5000, {"bars": 3000, "ts": now - 25 * 3600},
                               {"upload_min_new_bars": 1000,
                                "upload_min_hours": 24.0}, now)
    assert ok is True, why
    # bar cukup (+1100) tapi baru 5 jam -> ditahan oleh jam
    ok2, why2 = GH.should_upload(4100, {"bars": 3000, "ts": now - 5 * 3600},
                                 {"upload_min_new_bars": 1000,
                                  "upload_min_hours": 24.0}, now)
    assert ok2 is False and "jam" in why2, why2


def _mk_cc(tmp_path, state):
    cc = ENG.CommandCenter.__new__(ENG.CommandCenter)
    cc.cfg = {"hist_cloud": {"enabled": True,
                             "repo": "x/y", "branch": "main",
                             "dir": "data_hist", "delta_enabled": True,
                             "delta_min_new_bars": 20,
                             "delta_min_hours": 12.0,
                             "upload_min_hours": 24.0,
                             "upload_min_new_bars": 1000,
                             "autosync_every_sec": 600.0,
                             "timeout_sec": 30.0, "token": "TOK"}}
    os.chdir(tmp_path)
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "s3_hist_cloud.json"), "w") as f:
        json.dump(state, f)
    cc._s3_hist = {}
    cc.resolved = {}
    cc.log_lines = []
    cc.emit_log = lambda *a, **k: cc.log_lines.append(a)
    return cc


def _bars(n, t0=1700000000):
    return {"time": [t0 + i * 900 for i in range(n)],
            "open": [1.0] * n, "high": [1.5] * n, "low": [0.5] * n,
            "close": [1.2] * n, "tick_volume": [1] * n}


def test_delta_12jam_ditahan_dan_jatuh_tempo_diupload(tmp_path,
                                                      monkeypatch):
    now = time.time()
    state = {"XAUUSD": {"bars": 3000, "ts": now - 25 * 3600,
                        "cloud_time": 1700100000,
                        "delta_ts": now - 13 * 3600}}
    cc = _mk_cc(tmp_path, state)
    bars = _bars(3100)
    cc._s3_hist["XAUUSD"] = bars
    cc.resolved["XAUUSD"] = "XAUUSD"
    up = {}

    def fake_upload(repo, path, branch, tok, data, msg):
        up["path"] = path
        up["msg"] = msg
        return True
    monkeypatch.setattr(GH, "upload_bytes", fake_upload)
    monkeypatch.setattr(GH, "pack_bars", lambda b: b"gz")
    monkeypatch.setattr(GH, "resolve_token", lambda hc: "TOK")
    # 13 jam sejak delta -> jatuh tempo -> upload DELTA (bukan base)
    cc._cloud_maybe_upload("XAUUSD", bars, cc.cfg["hist_cloud"], now)
    assert "delta" in up.get("path", ""), up
    assert "delta" in up.get("msg", "").lower(), up
    # -- sekarang delta baru 1 jam -> DITAHAN (dulu 24 jam, kini 12) --
    up.clear()
    stf = os.path.join("data", "s3_hist_cloud.json")
    st = json.load(open(stf))
    st["XAUUSD"]["delta_ts"] = now - 1 * 3600
    json.dump(st, open(stf, "w"))
    cc._cloud_maybe_upload("XAUUSD", bars, cc.cfg["hist_cloud"], now)
    assert up == {}, up                     # belum jatuh tempo


def test_autosync_tick_upload_pair_jatuh_tempo(tmp_path, monkeypatch):
    now = time.time()
    state = {"XAUUSD": {"delta_ts": now - 13 * 3600, "cloud_time": 1},
             "BTCUSD": {"delta_ts": now - 1 * 3600, "cloud_time": 1}}
    cc = _mk_cc(tmp_path, state)
    cc._s3_hist = {"XAUUSD": _bars(3100), "BTCUSD": _bars(3200)}
    cc.resolved = {"XAUUSD": "XAUUSD", "BTCUSD": "BTCUSD"}
    calls = []
    monkeypatch.setattr(GH, "resolve_token", lambda hc: "TOK")
    monkeypatch.setattr(cc, "_cloud_maybe_upload",
                        lambda w, b, hc, n: calls.append(w))

    class SyncThread(object):
        def __init__(self, target, daemon=None):
            self._t = target

        def start(self):
            self._t()
    monkeypatch.setattr(ENG.threading, "Thread", SyncThread)
    cc._cloud_autosync_tick(now)
    assert calls == ["XAUUSD"], calls       # hanya yang > 12 jam
    # guard interval: belum 10 mnt -> tidak cek lagi
    calls.clear()
    cc._cloud_autosync_tick(now + 60)
    assert calls == [], calls
    # setelah 10 mnt -> cek lagi (XAUUSD masih belum diupload krn state
    # file tidak berubah oleh stub -> dipanggil ulang)
    cc._cloud_autosync_tick(now + 610)
    assert calls == ["XAUUSD"], calls


def test_autosync_off_atau_tanpa_token_diam(tmp_path, monkeypatch):
    cc = _mk_cc(tmp_path, {})
    cc.resolved = {"XAUUSD": "XAUUSD"}
    cc._s3_hist = {"XAUUSD": _bars(100)}
    called = []
    monkeypatch.setattr(cc, "_cloud_maybe_upload",
                        lambda *a, **k: called.append(1))
    monkeypatch.setattr(ENG.threading, "Thread",
                        lambda target, daemon=None: type(
                            "T", (), {"start": lambda s: target()})())
    # autosync off
    cc.cfg["hist_cloud"]["autosync_every_sec"] = 0
    cc._cloud_autosync_tick(time.time())
    assert called == []
    # tanpa token
    cc.cfg["hist_cloud"]["autosync_every_sec"] = 600.0
    monkeypatch.setattr(GH, "resolve_token", lambda hc: None)
    cc._cloud_autosync_tick(time.time())
    assert called == []


def test_hook_di_loop_utama():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"),
               encoding="utf-8").read()
    assert "self._cloud_autosync_tick(time.time())" in src
    i_hook = src.index("self._cloud_autosync_tick(time.time())")
    i_sleep = src.index('time.sleep(max(0.5, self.cfg.get('
                        '"scan_interval_sec"')
    assert i_hook < i_sleep, (i_hook, i_sleep)
