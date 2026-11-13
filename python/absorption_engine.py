"""Absorption engine — strictly quantitative (spec sections 7-8).

SELL ABSORPTION (LONG candidate):
  high aggressive sell volume
  + small downward price displacement
  + no significant continuation lower
  + declining seller efficiency (later sell bursts move price less per volume)

BUY ABSORPTION (SHORT candidate): mirror.

Nothing subjective is coded: only volume multiples, ATR-normalized
displacement and burst efficiency ratios.
"""
from __future__ import annotations

from dataclasses import dataclass

from trade_aggregator import WindowStats, Burst


@dataclass
class AbsorptionEvent:
    direction: str        # "LONG" (sell absorption) | "SHORT" (buy absorption)
    strength: float       # 0..100
    vol_mult: float       # side volume / (baseline * window)
    disp_atr: float       # |net displacement| / ATR
    cont_atr: float       # total extension / ATR
    eff_decay: float      # last burst efficiency / first burst efficiency
    n_bursts: int
    extreme: float        # window low (LONG) or window high (SHORT) -> invalidation anchor
    window_delta: float


class AbsorptionEngine:
    def __init__(self, cfg):
        self.cfg = cfg

    def evaluate(self, stats: WindowStats | None, bursts: list[Burst],
                 atr: float, baseline_per_sec: float) -> AbsorptionEvent | None:
        cfg = self.cfg
        if stats is None or atr <= 0 or baseline_per_sec <= 0:
            return None
        window = stats.window_sec
        if window < max(3.0, cfg.absorption_window_sec * 0.5):
            return None

        split = max(0.1, min(0.9, cfg.abs_side_baseline_split))
        for side, direction in (("sell", "LONG"), ("buy", "SHORT")):
            side_vol = stats.sell if side == "sell" else stats.buy
            side_base = baseline_per_sec * split   # aggression vs normal SAME-side flow
            vol_mult = side_vol / (side_base * window)
            if vol_mult < cfg.abs_min_vol_multiple:
                continue

            if side == "sell":
                net = stats.open - stats.close          # >0 = price fell
                total = stats.open - stats.low          # full downward extension
                extreme = stats.low
            else:
                net = stats.close - stats.open          # >0 = price rose
                total = stats.high - stats.open
                extreme = stats.high

            net_atr = net / atr
            cont_atr = total / atr
            if net_atr > cfg.abs_max_disp_atr:
                continue                                 # displacement too large -> continuation, not absorption
            if cont_atr > cfg.abs_max_disp_atr * cfg.abs_continuation_factor:
                continue                                 # significant continuation low/high

            side_bursts = [b for b in bursts if b.side == side and b.volume > 0]
            if not side_bursts:
                continue
            mx = max(b.volume for b in side_bursts)
            # background micro-prints are noise for efficiency analysis
            side_bursts = [b for b in side_bursts if b.volume >= 0.25 * mx]
            if len(side_bursts) < cfg.abs_min_bursts:
                continue

            effs = [max(abs(b.disp), 1e-9) / b.volume for b in side_bursts]
            eff_decay = effs[-1] / effs[0] if effs[0] > 0 else 1.0
            if eff_decay > cfg.abs_eff_decay:
                continue                                 # aggression NOT weakening

            vol_s = min(1.0, vol_mult / (cfg.abs_min_vol_multiple * 2.0))
            disp_s = min(1.0, max(0.0, 1.0 - abs(net_atr) / cfg.abs_max_disp_atr))
            eff_s = min(1.0, max(0.0,
                                 0.5 + (cfg.abs_eff_decay - eff_decay) / cfg.abs_eff_decay * 0.5))
            strength = 100.0 * (0.5 * vol_s + 0.3 * disp_s + 0.2 * eff_s)

            return AbsorptionEvent(
                direction=direction,
                strength=round(strength, 2),
                vol_mult=round(vol_mult, 3),
                disp_atr=round(net_atr, 4),
                cont_atr=round(cont_atr, 4),
                eff_decay=round(eff_decay, 4),
                n_bursts=len(side_bursts),
                extreme=extreme,
                window_delta=stats.delta,
            )
        return None
