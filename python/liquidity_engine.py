"""Liquidity sweep detection (optional filter, spec section 11).

LONG sweep: price swept below the recent low with a buffer, then reclaimed it.
SHORT sweep: mirror. Default OFF so the EA does not over-filter.
"""
from __future__ import annotations

from collections import deque


class LiquidityEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.prices: deque[tuple[int, float]] = deque()   # (ts_ms, price)
        self._last_event_ms = -10**12

    def on_price(self, ts_ms: int, price: float) -> None:
        self.prices.append((ts_ms, price))
        cutoff = ts_ms - self.cfg.liquidity_lookback_min * 60_000
        while self.prices and self.prices[0][0] < cutoff:
            self.prices.popleft()

    def check(self, now_ms: int, atr: float) -> str | None:
        """Returns 'LONG_SWEEP' | 'SHORT_SWEEP' | None (debounced 120s)."""
        if atr <= 0 or len(self.prices) < 60:
            return None
        if now_ms - self._last_event_ms < 120_000:
            return None

        split = now_ms - 30_000
        prev = [p for ts, p in self.prices if ts < split]
        recent = [p for ts, p in self.prices if ts >= split]
        if not prev or not recent:
            return None

        prev_min, prev_max = min(prev), max(prev)
        recent_min, recent_max = min(recent), max(recent)
        last = recent[-1]
        buf = atr * self.cfg.sweep_buffer_atr

        event = None
        if recent_min < prev_min - buf and last > prev_min:
            event = "LONG_SWEEP"
        elif recent_max > prev_max + buf and last < prev_max:
            event = "SHORT_SWEEP"
        if event:
            self._last_event_ms = now_ms
        return event
