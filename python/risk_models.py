"""Pure-Python risk models mirroring the EA's RiskManager (used by unit tests
and offline checks). The MT5 EA implements the identical rules natively
(see mt5/Include/BTC_HVN/RiskManager.mqh).

Rules (spec sections 18-21):
- structure determines SL, SL + risk determine lot
- risk budget includes commission and optional slippage allowance
- never raise the lot to satisfy a broker minimum (reject instead)
- daily loss = % of BALANCE AT START OF DAY, reset at midnight
"""
from __future__ import annotations

from dataclasses import dataclass


def calc_lot(risk_money: float, entry: float, sl: float, *,
             tick_size: float, tick_value_loss: float,
             commission_rt: float = 0.0,
             slippage_points: float = 0.0,
             point: float = 0.0,
             volume_min: float = 0.01, volume_max: float = 100.0,
             volume_step: float = 0.01) -> tuple[float, str]:
    """Returns (lot, reason). lot == 0.0 means SKIP the trade."""
    if risk_money <= 0:
        return 0.0, "NO_RISK_BUDGET"
    if tick_size <= 0 or tick_value_loss <= 0:
        return 0.0, "BAD_SYMBOL_SPEC"
    dist = abs(entry - sl)
    if dist <= 0:
        return 0.0, "ZERO_SL_DISTANCE"

    slip = slippage_points * point
    loss_per_lot = (dist + slip) / tick_size * tick_value_loss + commission_rt
    if loss_per_lot <= 0:
        return 0.0, "BAD_LOSS_CALC"

    step = volume_step if volume_step > 0 else (volume_min if volume_min > 0 else 0.01)
    raw = risk_money / loss_per_lot
    if raw < volume_min - 1e-12:
        return 0.0, "MIN_LOT_EXCEEDS_RISK"
    lot = max(volume_min, int(raw / step + 1e-9) * step)
    if lot > volume_max:
        lot = volume_max
    return round(lot, 8), ""


@dataclass
class DailyLossGuard:
    daily_loss_percent: float = 5.0
    day_key: int = -1
    day_start_balance: float = 0.0
    locked: bool = False

    def update_day(self, key: int, balance: float) -> None:
        if key != self.day_key:
            self.day_key = key
            self.day_start_balance = balance
            self.locked = False

    def check(self, balance: float) -> bool:
        if self.day_start_balance <= 0:
            self.day_start_balance = balance
        if balance <= self.stop_level():
            self.locked = True
        return self.locked

    def stop_level(self) -> float:
        return self.day_start_balance * (1.0 - self.daily_loss_percent / 100.0)
