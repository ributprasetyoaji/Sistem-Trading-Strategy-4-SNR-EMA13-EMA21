"""Sniper entry engine (M5/M1 precision trigger).

The M15 context decides WHERE a setup is valid (HVN zone + absorption +
delta recovery + reclaim). This engine decides WHEN to actually fire:

  LONG trigger:
    - micro delta (last ~20s) is positive
    - AND micro structure turned up:
        price broke above the 45..15s-ago micro range high
        OR micro lows are ascending (recent low > base low)
    - still near the HVN zone (not extended)

  SHORT: mirror.

Purpose: avoid entries that immediately float against the position
("floating mines") by waiting for micro confirmation.
"""
from __future__ import annotations


class SniperEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_why = ""

    def evaluate(self, now_ms: int, agg, delta, ev, dist_atr) -> dict:
        cfg = self.cfg
        if ev is None:
            self.last_why = "no_absorption_now"
            return {"ok": False, "why": self.last_why}
        if dist_atr is None or dist_atr > cfg.hvn_proximity_atr * 2.0:
            self.last_why = "too_far_from_zone"
            return {"ok": False, "why": self.last_why}

        base_t0 = now_ms - int(cfg.sniper_range_base_sec * 1000)
        base_t1 = now_ms - int(cfg.sniper_range_recent_sec * 1000)
        rec_t0 = base_t1
        blo, bhi = agg.min_max_between(base_t0, base_t1)
        rlo, rhi = agg.min_max_between(rec_t0, now_ms)
        if bhi <= 0 or rhi <= 0:
            self.last_why = "no_micro_range"
            return {"ok": False, "why": self.last_why}

        price_now = agg.last_price()
        md = delta.delta_window(now_ms, cfg.sniper_micro_delta_sec)
        if md < cfg.sniper_micro_delta_min:
            self.last_why = f"micro_delta={md:.2f}"
            return {"ok": False, "why": self.last_why}

        if ev.direction == "LONG":
            broke_up = price_now > bhi
            higher_lows = rlo > blo
            if broke_up or higher_lows:
                self.last_why = ("micro_break_up" if broke_up else "higher_lows")
                return {"ok": True, "why": self.last_why, "micro_delta": round(md, 3)}
            self.last_why = "no_micro_turn_up"
            return {"ok": False, "why": self.last_why}

        if md > -cfg.sniper_micro_delta_min:
            self.last_why = f"micro_delta={md:.2f}"
            return {"ok": False, "why": self.last_why}
        broke_down = price_now < blo
        lower_highs = rhi < bhi
        if broke_down or lower_highs:
            self.last_why = ("micro_break_down" if broke_down else "lower_highs")
            return {"ok": True, "why": self.last_why, "micro_delta": round(md, 3)}
        self.last_why = "no_micro_turn_down"
        return {"ok": False, "why": self.last_why}
