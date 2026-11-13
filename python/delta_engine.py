"""Delta engine: aggressive buy minus aggressive sell volume over sliding windows."""
from __future__ import annotations

from collections import deque


class DeltaEngine:
    def __init__(self, keep_sec: int = 900):
        self.keep_sec = int(keep_sec)
        self.events: deque[tuple[int, float]] = deque()   # (ts_ms, signed qty)
        self.cvd_total = 0.0

    def add_trade(self, qty: float, is_sell: bool, ts_ms: int) -> None:
        d = -qty if is_sell else qty
        self.events.append((ts_ms, d))
        self.cvd_total += d
        cutoff = ts_ms - self.keep_sec * 1000
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def delta_window(self, now_ms: int, window_sec: float) -> float:
        t0 = now_ms - int(window_sec * 1000)
        return sum(d for ts, d in self.events if ts >= t0)

    def recovery_ratio(self, now_ms: int, main_sec: float, short_sec: float) -> float:
        """0..1 measure of delta recovery: how strongly the short-window delta
        has turned AGAINST the main-window direction (negative->positive for a
        negative main delta, positive->negative for a positive main delta)."""
        wd = self.delta_window(now_ms, main_sec)
        sd = self.delta_window(now_ms, short_sec)
        if abs(wd) < 1e-12:
            return 1.0 if sd != 0 else 0.0
        oriented = sd if wd < 0 else -sd          # recovery means opposing wd
        raw = oriented / abs(wd)
        return max(0.0, min(1.0, raw))
