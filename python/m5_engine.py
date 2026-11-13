"""M5 context from Binance kline stream: ATR(14, Wilder), swings, recent extremes."""
from __future__ import annotations

from collections import deque


class M5Engine:
    def __init__(self, atr_period: int = 14, keep_bars: int = 200, swing_k: int = 2):
        self.atr_period = int(atr_period)
        self.swing_k = int(swing_k)
        self.bars: deque[dict] = deque(maxlen=int(keep_bars))   # closed bars
        self.current: dict | None = None
        self.atr = 0.0
        self._seed: list[float] = []

    # ---- ingestion ------------------------------------------------------
    def on_kline(self, k: dict) -> None:
        """k: {'t': start_ms, 'o','h','l','c','v' (strings), 'x': closed bool}"""
        try:
            bar = {
                "t": int(k["t"]),
                "o": float(k["o"]),
                "h": float(k["h"]),
                "l": float(k["l"]),
                "c": float(k["c"]),
                "v": float(k.get("v", 0.0)),
            }
        except (KeyError, TypeError, ValueError):
            return
        if k.get("x"):
            if self.bars and self.bars[-1]["t"] == bar["t"]:
                self.bars[-1] = bar
            else:
                self.bars.append(bar)
                self._update_atr(bar)
        else:
            self.current = bar

    def _update_atr(self, bar: dict) -> None:
        pc = self.bars[-2]["c"] if len(self.bars) >= 2 else bar["o"]
        tr = max(bar["h"] - bar["l"], abs(bar["h"] - pc), abs(bar["l"] - pc))
        n = self.atr_period
        if len(self.bars) >= n and self.atr > 0:
            self.atr = (self.atr * (n - 1) + tr) / n
        else:
            self._seed.append(tr)
            if len(self._seed) >= n:
                self.atr = sum(self._seed[-n:]) / n

    # ---- queries --------------------------------------------------------
    def recent_high(self, n: int = 20) -> float:
        bars = list(self.bars)[-n:]
        return max((b["h"] for b in bars), default=0.0)

    def recent_low(self, n: int = 20) -> float:
        bars = list(self.bars)[-n:]
        return min((b["l"] for b in bars), default=0.0)

    def swings(self, k: int | None = None) -> dict:
        """Fractal swing highs/lows: bar extreme vs k bars on both sides."""
        k = k or self.swing_k
        bars = list(self.bars)
        highs, lows = [], []
        for i in range(k, len(bars) - k):
            win = bars[i - k:i + k + 1]
            if bars[i]["h"] == max(b["h"] for b in win):
                highs.append({"t": bars[i]["t"], "price": bars[i]["h"]})
            if bars[i]["l"] == min(b["l"] for b in win):
                lows.append({"t": bars[i]["t"], "price": bars[i]["l"]})
        return {"highs": highs[-8:], "lows": lows[-8:]}

    def current_bar_ts(self) -> int:
        if self.current:
            return self.current["t"]
        return self.bars[-1]["t"] if self.bars else 0

    def m5_volume_baseline(self) -> float:
        bars = list(self.bars)[-30:]
        return sum(b["v"] for b in bars) / len(bars) if bars else 0.0
