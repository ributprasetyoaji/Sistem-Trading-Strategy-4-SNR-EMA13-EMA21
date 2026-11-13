"""HVN engine: rolling trade store -> volume profile -> nearest HVN zone."""
from __future__ import annotations

from collections import deque

from volume_profile import build_bins, detect_zones


class HVNEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.trades: deque[tuple] = deque()   # (ts_ms, price, qty)
        self.zones: list[dict] = []
        self._last_refresh_ms = -10**12

    def on_trade(self, ts_ms: int, price: float, qty: float) -> None:
        self.trades.append((ts_ms, price, qty))
        self._prune(ts_ms)

    def _prune(self, now_ms: int) -> None:
        cutoff = now_ms - self.cfg.hvn_lookback_minutes * 60_000
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

    def refresh(self, now_ms: int, force: bool = False) -> list[dict]:
        if not force and (now_ms - self._last_refresh_ms) < self.cfg.hvn_refresh_sec * 1000 \
                and self.zones:
            return self.zones
        self._prune(now_ms)
        t0 = now_ms - self.cfg.hvn_lookback_minutes * 60_000
        bins = build_bins(self.trades, self.cfg.price_bin_size, t0)
        self.zones = detect_zones(
            bins,
            bin_size=self.cfg.price_bin_size,
            hvn_percentile=self.cfg.hvn_percentile,
            min_rel_volume=self.cfg.hvn_min_rel_volume,
            min_width=self.cfg.min_hvn_zone_width,
            max_width=self.cfg.max_hvn_zone_width,
            max_zones=self.cfg.max_hvn_zones,
        )
        self._last_refresh_ms = now_ms
        return self.zones

    def nearest(self, price: float):
        """Returns (zone|None, distance). Distance = 0 inside a zone."""
        best, best_d = None, None
        for z in self.zones:
            if z["low"] <= price <= z["high"]:
                d = 0.0
            else:
                d = z["low"] - price if price < z["low"] else price - z["high"]
            if best_d is None or d < best_d:
                best, best_d = z, d
        return best, best_d

    def distance_atr(self, price: float, atr: float) -> tuple[object, float | None]:
        zone, dist = self.nearest(price)
        if zone is None or dist is None or atr <= 0:
            return None, None
        return zone, dist / atr
