"""Replay support: record live aggTrades to JSONL and replay them through the
full pipeline with simulated time (spec sections 17, 40, 41)."""
from __future__ import annotations

import json
import os
import time


class Recorder:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.count = 0

    def write_trade(self, ts_ms: int, price: float, qty: float, is_sell: bool) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"T": ts_ms, "p": price, "q": qty, "m": 1 if is_sell else 0},
                               separators=(",", ":")) + "\n")
        self.count += 1


class Replayer:
    @staticmethod
    def load(path: str) -> list[dict]:
        rows: list[dict] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        rows.sort(key=lambda r: int(r["T"]))
        return rows

    @staticmethod
    async def run(rows: list[dict], on_trade, on_tick, speed: float = 10.0,
                  stop_event=None, on_kline=None) -> int:
        """Feed recorded trades/klines preserving relative timing, accelerated
        by `speed`. on_tick(sim_now_ms) is invoked after every row so engines
        can evaluate with simulated time."""
        if not rows:
            return 0
        t_prev = int(rows[0]["T"])
        count = 0
        for r in rows:
            if stop_event is not None and stop_event.is_set():
                break
            t = int(r["T"])
            delay = (t - t_prev) / 1000.0 / max(0.1, speed)
            if delay > 0:
                await asyncio.sleep(delay)
            t_prev = t
            if "K" in r:
                if on_kline is not None:
                    on_kline(r["K"])
            else:
                on_trade(t, float(r["p"]), float(r["q"]), bool(int(r.get("m", 0))))
            on_tick(t)
            count += 1
        return count


import asyncio  # noqa: E402  (kept at bottom so the class defs read first)
