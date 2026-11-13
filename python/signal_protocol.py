"""Signal protocol: flat JSON payloads, atomic file writes, validation.

The same field names are parsed by the MT5 EA (BTC_HVN/SignalProtocol.mqh),
so both sides stay in sync. Validation mirrors EA checks (spec sections 30-32).
"""
from __future__ import annotations

import json
import os
import time

SIGNAL_KEYS = (
    "type", "signal_id", "setup_id", "ts_ms", "expiry_ms", "direction", "score",
    "binance_price", "hvn_low", "hvn_high", "hvn_center", "absorption",
    "delta", "cvd", "volume_ratio", "invalidation_price",
)


def build_signal_payload(sig) -> dict:
    return {
        "type": "signal",
        "signal_id": sig.signal_id,
        "setup_id": sig.setup_id,
        "ts_ms": int(sig.ts_ms),
        "expiry_ms": int(sig.expiry_ms),
        "direction": sig.direction,
        "score": round(float(sig.score), 2),
        "binance_price": float(sig.binance_price),
        "hvn_low": float(sig.hvn_low),
        "hvn_high": float(sig.hvn_high),
        "hvn_center": float(sig.hvn_center),
        "absorption": float(sig.absorption),
        "delta": float(sig.delta),
        "cvd": float(sig.cvd),
        "volume_ratio": float(sig.volume_ratio),
        "invalidation_price": float(sig.invalidation_price),
    }


def now_ms() -> int:
    return int(time.time() * 1000)


def validate_signal(payload: dict, *, now_ms_value: int, seen_ids: set,
                    max_age_ms: int, min_score: float,
                    max_divergence_pct: float = 0.0,
                    broker_price: float | None = None) -> tuple[bool, str]:
    """Mirror of the EA-side validation: malformed / stale / expired /
    duplicate / low-score / divergence checks. Returns (ok, reason)."""
    if not isinstance(payload, dict):
        return False, "MALFORMED"
    for k in ("signal_id", "ts_ms", "direction", "score", "binance_price",
              "invalidation_price"):
        if k not in payload:
            return False, f"MALFORMED_MISSING_{k}"
    if payload["direction"] not in ("LONG", "SHORT"):
        return False, "MALFORMED_DIRECTION"
    try:
        ts = int(payload["ts_ms"])
        score = float(payload["score"])
        bp = float(payload["binance_price"])
        inv = float(payload["invalidation_price"])
        expiry = int(payload.get("expiry_ms", 0))
    except (TypeError, ValueError):
        return False, "MALFORMED_NUMERIC"
    sid = str(payload["signal_id"])
    if len(sid) < 4:
        return False, "MALFORMED_ID"
    if ts <= 0 or bp <= 0 or inv <= 0:
        return False, "MALFORMED_VALUES"
    age = now_ms_value - ts
    if age > max_age_ms:
        return False, "STALE"
    if age < -3000:
        return False, "FUTURE_TIMESTAMP"
    if expiry > 0 and now_ms_value > expiry:
        return False, "EXPIRED"
    if sid in seen_ids:
        return False, "DUPLICATE"
    if score < min_score:
        return False, "LOW_SCORE"
    if broker_price is not None and max_divergence_pct > 0 and bp > 0:
        pct = abs(broker_price - bp) / bp * 100.0
        if pct > max_divergence_pct:
            return False, f"DIVERGENCE_{pct:.3f}pct"
    return True, ""


def build_status_payload(*sections: dict) -> dict:
    out: dict = {"type": "status", "ts_ms": now_ms()}
    for s in sections:
        out.update(s)
    return out


def atomic_write_json(path: str, payload: dict) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
