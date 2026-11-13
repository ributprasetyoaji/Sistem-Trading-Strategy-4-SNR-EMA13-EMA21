# -*- coding: utf-8 -*-
"""v3.88 HISTORY CLOUD: backup/restore cache bar M15 ke repo (gz json)
+ v3.90 delta harian (slice_after).  Nama file urut = urut waktu.
"""
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cc_config as C               # noqa: E402
import github_hist as GH            # noqa: E402


def test_versi():
    assert C.CC_VERSION >= "3.88"


def test_nama_file_cloud_dan_delta():
    assert GH.cloud_name("XAUUSD") == "s3_hist_XAUUSD_M15.json.gz"
    assert GH.cloud_name("BTCUSD").endswith(".json.gz")
    assert GH.delta_name("XAUUSD", "20261006") == \
        "s3_hist_XAUUSD_M15_20261006.json.gz"
    # path delta selalu di subfolder delta/
    assert GH.delta_path("XAUUSD", None, "20261006").split("/")[-2] == \
        "delta"


def test_last_time_dan_slice_after():
    bars = {"time": [10, 20, 30, 40], "close": [1.0, 2.0, 3.0, 4.0]}
    assert GH.last_time(bars) == 40
    assert GH.last_time({}) == 0
    sl = GH.slice_after(bars, 20)
    assert sl["time"] == [30, 40] and sl["close"] == [3.0, 4.0]
    # t terakhir -> kosong (tidak ada bar baru)
    sl2 = GH.slice_after(bars, 40)
    assert sl2["time"] == []
    # format kontrak: gz json round-trip
    blob = gzip.compress(json.dumps(bars).encode("utf-8"))
    back = json.loads(gzip.decompress(blob).decode("utf-8"))
    assert back == bars


def test_delta_unggah_kontrak_repo():
    """Delta & cloud memakai folder/dir yang konsisten (blueprint
    repo private, jangan dihapus)."""
    d = GH.delta_dir_path({"dir": "data_hist", "delta_dir": "delta"})
    assert d == "data_hist/delta"
    assert GH.cloud_path("XAUUSD", {"dir": "data_hist"}) == \
        "data_hist/s3_hist_XAUUSD_M15.json.gz"
