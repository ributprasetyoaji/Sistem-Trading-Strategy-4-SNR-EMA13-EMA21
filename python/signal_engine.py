"""Signal engine: state machine + weighted scoring (spec sections 15, 28, 43).

Sequence per setup:
  HVN proximity -> absorption -> delta recovery -> (optional liquidity sweep)
  -> price reclaim -> score threshold -> signal (with expiry + cooldown).

States:
  IDLE SEARCH_HVN APPROACH_HVN ABSORPTION_BUILDING ABSORPTION_CONFIRMED
  DELTA_CONFIRMATION PRICE_RECLAIM SIGNAL_READY COOLDOWN
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

STATE_IDLE = "IDLE"
STATE_SEARCH = "SEARCH_HVN"
STATE_APPROACH = "APPROACH_HVN"
STATE_BUILDING = "ABSORPTION_BUILDING"
STATE_CONFIRMED = "ABSORPTION_CONFIRMED"
STATE_DELTA = "DELTA_CONFIRMATION"
STATE_RECLAIM = "PRICE_RECLAIM"
STATE_SNIPER = "SNIPER_WAIT"
STATE_READY = "SIGNAL_READY"
STATE_COOLDOWN = "COOLDOWN"


@dataclass
class Signal:
    signal_id: str
    setup_id: str
    ts_ms: int
    expiry_ms: int
    direction: str
    score: float
    binance_price: float
    hvn_low: float
    hvn_high: float
    hvn_center: float
    absorption: float
    delta: float
    cvd: float
    volume_ratio: float
    invalidation_price: float
    components: dict = field(default_factory=dict)


def _same_zone(a: dict | None, b: dict | None, tol: float = 1e-6) -> bool:
    if not a or not b:
        return False
    return abs(a.get("center", 0.0) - b.get("center", 0.0)) <= tol + 0.25 * max(
        a.get("width", 0.0), b.get("width", 0.0))


class SignalEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.state = STATE_IDLE
        self.setup: dict | None = None
        self.cooldown_until_ms = 0
        self.bar_counts: dict = {}
        self.signals_emitted = 0
        self.rejections = 0
        self._setup_n = 0

    # ------------------------------------------------------------------
    def on_update(self, ctx: dict) -> Signal | None:
        """ctx keys:
        now_ms, price, atr, bar_ts, zones, nearest(zone|None), dist_atr(float|None),
        absorption(AbsorptionEvent|None), flow{window_delta, short_delta, delta_m5,
        cvd, vol_mult}, sweep(str|None), health_ok(bool)
        """
        cfg = self.cfg
        now = int(ctx["now_ms"])
        price = float(ctx["price"])
        atr = float(ctx.get("atr") or 0.0)

        if not ctx.get("health_ok", False) or atr <= 0 or price <= 0:
            self.state = STATE_IDLE if not ctx.get("health_ok", False) else self.state
            return None

        if now < self.cooldown_until_ms:
            self.state = STATE_COOLDOWN
            return None
        if self.state == STATE_COOLDOWN:
            self.state = STATE_IDLE

        nearest = ctx.get("nearest")
        dist_atr = ctx.get("dist_atr")
        prox = cfg.hvn_proximity_atr
        ev = ctx.get("absorption")

        # ---- zone refinement: re-anchor an active setup when the volume
        #      profile produced a different (more mature) nearest zone while
        #      the same-direction absorption evidence is still live --------
        if (self.setup is not None and ev is not None
                and ev.direction == self.setup["direction"]
                and nearest is not None and self.setup["zone"] is not None
                and not _same_zone(self.setup["zone"], nearest)
                and dist_atr is not None and dist_atr <= prox):
            st0 = self.setup
            z_half0 = max(1e-9, nearest.get("width", 0.0) / 2.0)
            enter_off0 = min(0.10 * atr, 0.25 * z_half0)
            st0["zone"] = dict(nearest)
            st0["entered"] = (ev.extreme <= nearest["center"] - enter_off0) \
                if st0["direction"] == "LONG" \
                else (ev.extreme >= nearest["center"] + enter_off0)
            st0["reclaimed"] = False

        # ---- maintain / create setup ---------------------------------
        st = self.setup
        if st is not None:
            if now - st["started_ms"] > cfg.setup_timeout_sec * 1000:
                self.setup = None
                st = None
            elif (not _same_zone(st["zone"], nearest)) and \
                    (dist_atr is None or dist_atr > prox * 2.0):
                self.setup = None
                st = None

        if st is None and ev is not None and dist_atr is not None and dist_atr <= prox:
            self._setup_n += 1
            z_center = float(nearest["center"]) if nearest else ev.extreme
            z_half = max(1e-9, (nearest.get("width", 0.0) / 2.0) if nearest else 0.0)
            enter_off = min(0.10 * atr, 0.25 * z_half)
            # the absorption extreme already proves whether price penetrated
            # the zone area during the event window
            entered = (ev.extreme <= z_center - enter_off) if ev.direction == "LONG" \
                else (ev.extreme >= z_center + enter_off)
            st = {
                "setup_id": f"SU{now:x}{self._setup_n:03d}",
                "direction": ev.direction,
                "zone": dict(nearest) if nearest else None,
                "started_ms": now,
                "entered": bool(entered),
                "reclaimed": False,
                "event": ev,
                "last_ev_ms": now,
                "delta_ok_seen": False,
                "best_score": 0.0,
            }
            self.setup = st
            self.state = STATE_BUILDING

        st = self.setup
        if st is None:
            self.state = STATE_SEARCH if (dist_atr is not None and dist_atr <= prox) \
                else STATE_IDLE
            return None

        d = st["direction"]
        z = st["zone"]
        if z is None:
            self.state = STATE_IDLE
            return None

        # ---- entered / reclaim (center based, robust to zone width) ---
        zone_half = max(1e-9, z.get("width", 0.0) / 2.0)
        enter_level_off = min(0.10 * atr, 0.25 * zone_half)
        # reclaim line: halfway from the zone low back to its center
        # (robust when bins are locked to one side of the zone)
        reclaim_up = (z["low"] + z["center"]) * 0.5 + cfg.reclaim_buffer_atr * atr
        reclaim_dn = (z["high"] + z["center"]) * 0.5 - cfg.reclaim_buffer_atr * atr
        if d == "LONG":
            if price <= z["center"] - enter_level_off:
                st["entered"] = True
            if st["entered"] and price >= reclaim_up:
                st["reclaimed"] = True
        else:
            if price >= z["center"] + enter_level_off:
                st["entered"] = True
            if st["entered"] and price <= reclaim_dn:
                st["reclaimed"] = True

        # keep the strongest absorption evidence for this setup
        if ev is not None and ev.direction == d and ev.strength > st["event"].strength:
            st["event"] = ev
        if ev is not None and ev.direction == d:
            st["last_ev_ms"] = now
        ev_use = st["event"]
        self.state = STATE_CONFIRMED

        # ---- delta confirmation ---------------------------------------
        flow = ctx.get("flow", {})
        wd = float(flow.get("window_delta", 0.0))
        sd = float(flow.get("short_delta", 0.0))
        if d == "LONG":
            rec = (sd / abs(wd)) if wd < 0 else (1.0 if sd > 0 else 0.0)
        else:
            rec = (-sd / abs(wd)) if wd > 0 else (1.0 if sd < 0 else 0.0)
        rec = max(0.0, min(1.0, rec))
        strong = ev_use.strength >= cfg.abs_strong
        delta_ok = rec >= cfg.delta_recovery_ratio
        if cfg.require_delta_turn_positive and not strong:
            if d == "LONG" and sd <= 0:
                delta_ok = False
            if d == "SHORT" and sd >= 0:
                delta_ok = False
        if delta_ok:
            st["delta_ok_seen"] = True
            self.state = STATE_DELTA
        elif st.get("delta_ok_seen"):
            delta_ok = True          # recovery already happened during setup
        if st["reclaimed"]:
            self.state = STATE_RECLAIM

        # ---- optional filters (spec 43: secondary, switchable) --------
        if cfg.use_liquidity_sweep:
            sweep = ctx.get("sweep")
            want = "LONG_SWEEP" if d == "LONG" else "SHORT_SWEEP"
            if sweep != want:
                self.rejections += 1
                return None
        if cfg.use_orderbook_filter and ctx.get("imbalance") is not None:
            imb = float(ctx["imbalance"])
            if d == "LONG" and imb < -cfg.min_imbalance_ratio:
                return None
            if d == "SHORT" and imb > cfg.min_imbalance_ratio:
                return None
        if cfg.use_atr_filter:
            if cfg.min_atr > 0 and atr < cfg.min_atr:
                return None
            if cfg.max_atr > 0 and atr > cfg.max_atr:
                return None
        if cfg.use_volume_filter and float(flow.get("vol_mult", 0.0)) < 1.0:
            return None

        # ---- score -----------------------------------------------------
        total, comps = self._score(ctx, st, rec)
        st["best_score"] = max(st["best_score"], total)
        reclaim_ok = st["reclaimed"] or not cfg.require_reclaim

        if not (reclaim_ok and delta_ok and total >= cfg.min_signal_score):
            return None

        # ---- sniper gate (M5/M1 precision trigger) ----------------------
        # The M15 context has a valid setup; the FINAL trigger waits for
        # micro confirmation so entries do not float against us.
        if cfg.entry_mode == "m15_sniper":
            sn = ctx.get("sniper") or {}
            age_ok = (now - st.get("last_ev_ms", now)) <= cfg.sniper_active_sec * 1000
            if not (bool(sn.get("ok")) and age_ok):
                self.state = STATE_SNIPER
                return None

        bar = int(ctx.get("bar_ts") or 0)
        key = (bar, d)
        if self.bar_counts.get(key, 0) >= cfg.max_signals_per_m5_bar:
            return None

        sig = self._emit(ctx, st, total, comps, wd, rec)
        self.bar_counts[key] = self.bar_counts.get(key, 0) + 1
        self.signals_emitted += 1
        self.cooldown_until_ms = now + cfg.cooldown_sec * 1000
        self.setup = None
        self.state = STATE_READY
        return sig

    # ------------------------------------------------------------------
    def _score(self, ctx: dict, st: dict, rec: float):
        cfg = self.cfg
        ev = st["event"]
        atr = float(ctx.get("atr") or 0.0)
        dist_atr = ctx.get("dist_atr")

        hvn_s = 0.0 if dist_atr is None else max(0.0, 1.0 - min(1.0, dist_atr / cfg.hvn_proximity_atr))
        abs_s = ev.strength / 100.0
        disp_s = max(0.0, 1.0 - min(1.0, abs(ev.disp_atr) / cfg.abs_max_disp_atr))
        # recovery already proven during this setup -> full credit even if
        # the short-window delta has since faded into two-way flow
        delta_s = max(rec, 1.0 if st.get("delta_ok_seen") else 0.0)

        z = st["zone"]
        price = float(ctx["price"])
        if st["reclaimed"]:
            rec_s = 1.0
        elif z["low"] <= price <= z["high"]:
            rec_s = 0.3
        else:
            rec_s = 0.0

        vm = float(ctx.get("flow", {}).get("vol_mult", 0.0))
        vol_s = min(1.0, vm / cfg.volume_spike_mult) if cfg.volume_spike_mult > 0 else 0.0

        comps = {
            "hvn": round(hvn_s * cfg.weight_hvn, 2),
            "absorption": round(abs_s * cfg.weight_absorption, 2),
            "displacement": round(disp_s * cfg.weight_displacement, 2),
            "delta": round(delta_s * cfg.weight_delta, 2),
            "reclaim": round(rec_s * cfg.weight_reclaim, 2),
            "volume": round(vol_s * cfg.weight_volume, 2),
        }
        return round(sum(comps.values()), 2), comps

    def _emit(self, ctx: dict, st: dict, score: float, comps: dict,
              window_delta: float, rec: float) -> Signal:
        cfg = self.cfg
        ev = st["event"]
        now = int(ctx["now_ms"])
        atr = float(ctx.get("atr") or 0.0)
        z = st["zone"]
        inv_buf = cfg.invalidation_buffer_atr * atr
        if st["direction"] == "LONG":
            invalidation = ev.extreme - inv_buf
        else:
            invalidation = ev.extreme + inv_buf
        return Signal(
            signal_id=f"{now:x}-{st['direction'][0]}-{uuid.uuid4().hex[:8]}",
            setup_id=st["setup_id"],
            ts_ms=now,
            expiry_ms=now + int(cfg.signal_expiry_sec * 1000),
            direction=st["direction"],
            score=score,
            binance_price=float(ctx["price"]),
            hvn_low=z["low"],
            hvn_high=z["high"],
            hvn_center=z["center"],
            absorption=ev.strength,
            delta=round(window_delta, 4),
            cvd=round(float(ctx.get("flow", {}).get("cvd", 0.0)), 3),
            volume_ratio=round(float(ctx.get("flow", {}).get("vol_mult", 0.0)), 3),
            invalidation_price=invalidation,
            components=comps,
        )
