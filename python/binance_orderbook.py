"""Local Binance order book with snapshot + diff-depth synchronization.

Implements the official Binance procedure:
  1. buffer diff events while the REST snapshot is in flight
  2. apply snapshot (lastUpdateId)
  3. drop buffered events with u <= lastUpdateId
  4. first event must satisfy U <= lastUpdateId+1 <= u
  5. each subsequent event's pu must equal previous u, else RESYNC
"""
from __future__ import annotations

from collections import OrderedDict


class LocalOrderBook:
    def __init__(self, levels: int = 50):
        self.levels = int(levels)
        self.last_update_id = 0
        self.synced = False
        self._awaiting_snapshot = False
        self._buffer: list[tuple] = []
        self.bids: OrderedDict[float, float] = OrderedDict()
        self.asks: OrderedDict[float, float] = OrderedDict()

    # ---- lifecycle ------------------------------------------------------
    def start_resync(self) -> None:
        self.synced = False
        self._awaiting_snapshot = True
        self._buffer = []

    def needs_snapshot(self) -> bool:
        """True while the book still waits for a valid snapshot."""
        return self._awaiting_snapshot or not self.synced

    def apply_snapshot(self, last_update_id: int, bids, asks) -> bool:
        """bids/asks: iterable of [price, qty] strings. Returns True if the
        buffered events could be applied consistently."""
        self.bids = OrderedDict()
        self.asks = OrderedDict()
        self._apply(self.bids, bids)
        self._apply(self.asks, asks)
        self.last_update_id = int(last_update_id)
        self._awaiting_snapshot = False

        pending = self._buffer
        self._buffer = []
        for (U, u, pu, b, a) in pending:
            if u <= self.last_update_id:
                continue
            status = self.apply_diff(U, u, pu, b, a)
            if status != "ok":
                # gap during replay -> need a fresh snapshot
                self.start_resync()
                return False
        self.synced = True
        return True

    # ---- diffs ----------------------------------------------------------
    def buffer_diff(self, U: int, u: int, pu: int, b, a) -> None:
        if self._awaiting_snapshot:
            self._buffer.append((int(U), int(u), int(pu), b, a))
            # safety: cap memory; keep the OLDEST events so the replay stays
            # contiguous from the snapshot point (dropping the newest is
            # recoverable - following live diffs bridge the gap)
            if len(self._buffer) > 5000:
                self._buffer = self._buffer[:2000]

    def apply_diff(self, U: int, u: int, pu: int, b, a) -> str:
        if self._awaiting_snapshot:
            self.buffer_diff(U, u, pu, b, a)
            return "buffered"
        if u <= self.last_update_id:
            return "stale"
        if self.last_update_id and not (U <= self.last_update_id + 1 <= u):
            self.synced = False          # book is unreliable from this moment
            return "gap"
        if self.last_update_id and pu and int(pu) != self.last_update_id:
            self.synced = False
            return "gap"
        self._apply(self.bids, b)
        self._apply(self.asks, a)
        self.last_update_id = int(u)
        self.synced = True
        return "ok"

    @staticmethod
    def _apply(book: OrderedDict, updates) -> None:
        for row in updates or []:
            try:
                p = float(row[0])
                q = float(row[1])
            except (TypeError, ValueError, IndexError):
                continue
            if q <= 0.0:
                book.pop(p, None)
            else:
                book[p] = q

    # ---- queries --------------------------------------------------------
    def best_bid(self) -> float:
        return max(self.bids) if self.bids else 0.0

    def best_ask(self) -> float:
        return min(self.asks) if self.asks else 0.0

    def top(self, n: int | None = None):
        n = n or self.levels
        bids = sorted(self.bids.items(), key=lambda kv: -kv[0])[:n]
        asks = sorted(self.asks.items(), key=lambda kv: kv[0])[:n]
        return bids, asks

    def imbalance(self, n: int | None = None) -> float:
        """(bidQty - askQty) / (bidQty + askQty) over the top n levels."""
        bids, asks = self.top(n)
        bq = sum(q for _, q in bids)
        aq = sum(q for _, q in asks)
        tot = bq + aq
        if tot <= 0:
            return 0.0
        return (bq - aq) / tot

    def snapshot_state(self) -> dict:
        bids, asks = self.top(1)
        return {
            "ob_bid": bids[0][0] if bids else 0.0,
            "ob_ask": asks[0][0] if asks else 0.0,
            "ob_synced": 1 if self.synced else 0,
            "ob_imbalance": round(self.imbalance(), 4),
        }
