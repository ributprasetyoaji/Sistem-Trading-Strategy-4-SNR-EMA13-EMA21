"""CVD engine: per-second cumulative volume delta + rolling CVD windows."""
from __future__ import annotations

from collections import deque


class CVDEngine:
    def __init__(self, keep_sec: int = 3600):
        self.keep_sec = int(keep_sec)
        self.series: deque[tuple[int, float]] = deque()   # (sec, delta)
        self.total = 0.0

    def add_bucket(self, sec: int, delta: float) -> None:
        # merge into same second if already present
        if self.series and self.series[-1][0] == sec:
            s, d = self.series.pop()
            delta = d + delta
        self.series.append((sec, delta))
        self.total += delta
        cutoff = sec - self.keep_sec
        while self.series and self.series[0][0] < cutoff:
            self.series.popleft()

    def cvd(self, now_sec: int, lookback_sec: int = 1800) -> float:
        t0 = now_sec - int(lookback_sec)
        return sum(d for s, d in self.series if s >= t0)

    def snapshot(self, now_sec: int) -> dict:
        return {
            "cvd": round(self.cvd(now_sec), 3),
            "cvd_total": round(self.total, 3),
        }
