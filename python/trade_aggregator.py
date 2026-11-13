"""Trade aggregation: 1-second buckets, rolling baseline, window stats, bursts."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


class Bucket:
    __slots__ = ("sec", "open", "high", "low", "close", "buy", "sell", "count")

    def __init__(self, sec: int, price: float):
        self.sec = sec
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.buy = 0.0
        self.sell = 0.0
        self.count = 0

    def update(self, price: float, qty: float, is_sell: bool) -> None:
        if price > self.high:
            self.high = price
        if price < self.low:
            self.low = price
        self.close = price
        if is_sell:
            self.sell += qty
        else:
            self.buy += qty
        self.count += 1

    @property
    def vol(self) -> float:
        return self.buy + self.sell

    @property
    def delta(self) -> float:
        return self.buy - self.sell


@dataclass
class WindowStats:
    t0: int            # first bucket sec
    t1: int            # last bucket sec
    open: float
    high: float
    low: float
    close: float
    buy: float
    sell: float

    @property
    def vol(self) -> float:
        return self.buy + self.sell

    @property
    def delta(self) -> float:
        return self.buy - self.sell

    @property
    def window_sec(self) -> float:
        return max(1.0, float(self.t1 - self.t0))


@dataclass
class Burst:
    side: str          # "buy" | "sell"
    volume: float
    disp: float        # signed price change across the burst
    t0: int
    t1: int


class TradeAggregator:
    def __init__(self, keep_sec: int = 180, baseline_buckets: int = 300):
        self.keep_sec = int(keep_sec)
        self.baseline_buckets = int(baseline_buckets)
        self.buckets: deque[Bucket] = deque()
        self.trades: deque[tuple] = deque()   # (ts_ms, price, qty, is_sell)

    # ---- ingestion ------------------------------------------------------
    def add_trade(self, price: float, qty: float, ts_ms: int, is_sell: bool) -> list[Bucket]:
        closed: list[Bucket] = []
        sec = int(ts_ms // 1000)
        if self.buckets:
            last = self.buckets[-1]
            if sec < last.sec:
                return closed                      # late/duplicate trade -> ignore
            if sec > last.sec:
                closed.append(last)
                self.buckets.append(Bucket(sec, price))
        else:
            self.buckets.append(Bucket(sec, price))
        self.buckets[-1].update(price, qty, is_sell)
        self.trades.append((ts_ms, price, qty, is_sell))

        cutoff = ts_ms - self.keep_sec * 1000
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()
        while len(self.buckets) > self.baseline_buckets + 2:
            self.buckets.popleft()
        return closed

    # ---- queries --------------------------------------------------------
    def last_price(self) -> float:
        return self.buckets[-1].close if self.buckets else 0.0

    def window_stats(self, now_sec: int, window_sec: float) -> WindowStats | None:
        t0 = int(now_sec - window_sec)
        sel = [b for b in self.buckets if t0 <= b.sec <= now_sec]
        if not sel:
            return None
        return WindowStats(
            t0=sel[0].sec,
            t1=sel[-1].sec,
            open=sel[0].open,
            high=max(b.high for b in sel),
            low=min(b.low for b in sel),
            close=sel[-1].close,
            buy=sum(b.buy for b in sel),
            sell=sum(b.sell for b in sel),
        )

    def baseline_per_sec(self) -> float:
        """Robust per-second volume baseline: MEDIAN of closed buckets so that
        spike seconds (bursts) do not inflate the baseline. Falls back to the
        mean when the median collapses to zero."""
        if len(self.buckets) <= 1:
            return 0.0
        bs = list(self.buckets)[:-1][-self.baseline_buckets:]
        if not bs:
            return 0.0
        vols = sorted(b.vol for b in bs)
        n = len(vols)
        med = vols[n // 2] if n % 2 else (vols[n // 2 - 1] + vols[n // 2]) / 2.0
        mean = sum(vols) / n
        return med if med > 0 else mean

    def bursts(self, t0_ms: int, t1_ms: int, side: str, gap_ms: int = 700) -> list[Burst]:
        want_sell = (side == "sell")
        out: list[Burst] = []
        cur: dict | None = None
        for ts, price, qty, is_sell in self.trades:
            if ts < t0_ms or ts > t1_ms or is_sell != want_sell:
                continue
            if cur is None or ts - cur["t1"] > gap_ms:
                if cur is not None:
                    out.append(Burst(side, cur["vol"], cur["p_end"] - cur["p_start"],
                                     cur["t0"], cur["t1"]))
                cur = {"vol": 0.0, "p_start": price, "p_end": price, "t0": ts, "t1": ts}
            cur["vol"] += qty
            cur["p_end"] = price
            cur["t1"] = ts
        if cur is not None:
            out.append(Burst(side, cur["vol"], cur["p_end"] - cur["p_start"],
                             cur["t0"], cur["t1"]))
        return out

    def min_max_between(self, t0_ms: int, t1_ms: int) -> tuple[float, float]:
        hi, lo = -10**18, 10**18
        found = False
        for ts, price, _q, _s in self.trades:
            if t0_ms <= ts <= t1_ms:
                found = True
                if price > hi:
                    hi = price
                if price < lo:
                    lo = price
        return (lo, hi) if found else (0.0, 0.0)
