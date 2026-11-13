"""Structured CSV logging, one file per category (spec section 39).

Categories: DATA, HVN, ABSORPTION, SIGNAL, EXECUTION, POSITION, RISK, ERROR.
Every row: ts, event, detail(json) so each trade is reconstructable.
"""
from __future__ import annotations

import csv
import json
import os
import threading
import time

CATEGORIES = ("DATA", "HVN", "ABSORPTION", "SIGNAL",
              "EXECUTION", "POSITION", "RISK", "ERROR")


class Logger:
    def __init__(self, log_dir: str = "data/logs", console: bool = True):
        self.dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.console = console
        self._lock = threading.Lock()

    def log(self, cat: str, event: str, **fields) -> None:
        cat = cat.upper() if cat.upper() in CATEGORIES else "DATA"
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            detail = json.dumps(fields, default=str, separators=(",", ":"))
        except (TypeError, ValueError):
            detail = json.dumps({"raw": str(fields)}, separators=(",", ":"))
        path = os.path.join(self.dir, f"BHVN_{cat}.csv")
        row = [ts, event, detail]
        with self._lock:
            new_file = not os.path.exists(path)
            with open(path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(["ts", "event", "detail"])
                w.writerow(row)
        if self.console:
            print(f"[{ts}][{cat}] {event} {detail}", flush=True)

    def error(self, msg: str, **fields) -> None:
        self.log("ERROR", msg, **fields)
