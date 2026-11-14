"""v4.32: /api/selfcheck -- ground-truth tanpa JS: server LIVE sungguhan
(make_server) + HTTP sungguhan; bukti scanner punya gold & kategori benar."""
import json
import os
import sys
import threading
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from cc_dashboard import make_server  # noqa: E402

ROWS = [
    {"symbol": "XAUUSD", "status": "WAIT", "score": 12.0, "price": 3883.111,
     "spread": 168, "signal": "-", "trend_pct": 0, "digits": 3},
    {"symbol": "XAGUSD", "status": "WAIT", "score": 10.0, "price": 48.709,
     "spread": 18, "signal": "-", "trend_pct": 0, "digits": 3},
    {"symbol": "EURUSD", "status": "WAIT", "score": 8.0, "price": 1.10213,
     "spread": 14, "signal": "-", "trend_pct": 0, "digits": 5},
    {"symbol": "BTCUSD", "status": "WAIT", "score": 20.0, "price": 68000.0,
     "spread": 3500, "signal": "-", "trend_pct": 0, "digits": 2},
]


class FakeCC:
    version = "4.32-test"

    def get_status(self):
        return {"version": self.version, "scanner": ROWS, "positions": [],
                "mode": "SIMULASI", "account": {"login": 0, "server": "T"}}


def test_server_live_selfcheck_dan_halaman():
    srv = make_server(FakeCC(), 0, "")
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        # halaman utama membawa stamp UI-2 (statis, tanpa JS)
        pg = urllib.request.urlopen(
            "http://127.0.0.1:%d/" % port, timeout=5).read().decode()
        assert "UI-2" in pg
        # ground truth JSON
        js = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/api/selfcheck" % port, timeout=5))
        assert js["ok"] is True
        assert js["ui"] == "UI-2"
        assert js["scanner"] == 4
        assert js["cat"]["GOLD"] == 2
        assert js["cat"]["FOREX"] == 1
        assert js["cat"]["CRYPTO"] == 1
        assert [g["symbol"] for g in js["gold_rows"]] == ["XAUUSD", "XAGUSD"]
        assert js["symbols"][:2] == ["XAUUSD", "XAGUSD"]
    finally:
        srv.shutdown()
        srv.server_close()
