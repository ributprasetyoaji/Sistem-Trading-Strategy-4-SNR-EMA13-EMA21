"""Data health: heartbeat, stale detection, connection state (spec section 3).

A signal is NEVER generated from stale / desynchronized data.
"""
from __future__ import annotations

import time


class DataHealth:
    def __init__(self, max_data_age_ms: int = 5000):
        self.max_data_age_ms = int(max_data_age_ms)
        self.connected = False
        self.ws_up_since_ms = 0
        self.last_trade_ms = 0
        self.last_depth_ms = 0
        self.last_kline_ms = 0
        self.book_synced = False
        self.reconnects = 0
        self.resyncs = 0
        self.malformed_msgs = 0
        self.last_error = ""

    # ---- mutators -------------------------------------------------------
    def mark_connected(self, now_ms: int) -> None:
        self.connected = True
        self.ws_up_since_ms = now_ms

    def mark_disconnected(self, err: str = "") -> None:
        self.connected = False
        self.book_synced = False
        if err:
            self.last_error = err
        self.reconnects += 1

    def mark_trade(self, ts_ms: int) -> None:
        self.last_trade_ms = max(self.last_trade_ms, ts_ms)

    def mark_depth(self, ts_ms: int) -> None:
        self.last_depth_ms = max(self.last_depth_ms, ts_ms)

    def mark_kline(self, ts_ms: int) -> None:
        self.last_kline_ms = max(self.last_kline_ms, ts_ms)

    def mark_resync(self) -> None:
        self.resyncs += 1

    def mark_malformed(self) -> None:
        self.malformed_msgs += 1

    # ---- queries --------------------------------------------------------
    def data_age_ms(self, now_ms: int | None = None) -> int:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        return max(0, now - self.last_trade_ms) if self.last_trade_ms else 10**12

    def depth_age_ms(self, now_ms: int | None = None) -> int:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        return max(0, now - self.last_depth_ms) if self.last_depth_ms else 10**12

    def is_stale(self, now_ms: int | None = None) -> bool:
        if not self.connected:
            return True
        return self.data_age_ms(now_ms) > self.max_data_age_ms

    def healthy(self, now_ms: int | None = None) -> bool:
        return (not self.is_stale(now_ms)) and self.book_synced

    def snapshot(self, now_ms: int | None = None) -> dict:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        return {
            "binance_connected": 1 if self.connected else 0,
            "data_age_ms": self.data_age_ms(now) if self.last_trade_ms else -1,
            "depth_age_ms": self.depth_age_ms(now) if self.last_depth_ms else -1,
            "stale": 1 if self.is_stale(now) else 0,
            "book_synced": 1 if self.book_synced else 0,
            "reconnects": self.reconnects,
            "resyncs": self.resyncs,
            "malformed_msgs": self.malformed_msgs,
            "last_error": self.last_error[:120],
        }
