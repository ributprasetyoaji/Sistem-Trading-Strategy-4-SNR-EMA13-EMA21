# -*- coding: utf-8 -*-
"""v3.44: pemilihan terminal MT5 di VPS multi-terminal (S1 & S2)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import cc_broker  # noqa: E402


def test_read_mt5_path_skip_komentar(tmp="/tmp/test_mt5_path.txt"):
    with open(tmp, "w") as f:
        f.write("# komentar\n\n")
        f.write('"C:\\\\Program Files\\\\Broker X\\\\terminal64.exe"\n')
    assert cc_broker.read_mt5_path_file(tmp) == \
        "C:\\Program Files\\Broker X\\terminal64.exe"
    # dobel-backslash (copy dari JSON) ikut dinormalisasi
    with open(tmp, "w") as f:
        f.write("C:\\\\MT5\\\\terminal64.exe\n")
    assert cc_broker.read_mt5_path_file(tmp) == "C:\\MT5\\terminal64.exe"
    # UNC path tidak diubah
    with open(tmp, "w") as f:
        f.write("\\\\NAS\\share\\terminal64.exe\n")
    assert cc_broker.read_mt5_path_file(tmp) == "\\\\NAS\\share\\terminal64.exe"
    with open(tmp, "w") as f:
        f.write("# hanya komentar\n")
    assert cc_broker.read_mt5_path_file(tmp) == ""
    assert cc_broker.read_mt5_path_file("/tmp/tidak_ada_9x.txt") == ""


def test_write_read_sticky(tmp="/tmp/test_mt5_path2.txt"):
    assert cc_broker.write_mt5_path_file("C:\\MT5\\terminal64.exe", tmp)
    assert cc_broker.read_mt5_path_file(tmp) == "C:\\MT5\\terminal64.exe"


def test_build_attempts_urutan():
    """Prioritas: config -> MT5_PATH.txt -> attach -> scan."""
    cfg = {"mt5_terminal_path": "C:\\A\\t.exe"}
    att = cc_broker.build_attempts(cfg, "/tmp/tidak_ada_9x.txt")
    assert att[0] == {"path": "C:\\A\\t.exe", "src": "config"}
    assert att[1] == {"src": "attach"}
    assert all("path" in a for a in att[2:])          # hasil scan
    # tanpa config tapi ada MT5_PATH.txt -> jadi prioritas pertama
    with open("/tmp/test_mt5_path3.txt", "w") as f:
        f.write("C:\\B\\t.exe\n")
    att2 = cc_broker.build_attempts({}, "/tmp/test_mt5_path3.txt")
    assert att2[0]["src"] == "MT5_PATH.txt"
    assert att2[0]["path"] == "C:\\B\\t.exe"
