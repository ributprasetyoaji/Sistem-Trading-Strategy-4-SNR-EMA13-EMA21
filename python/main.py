#!/usr/bin/env python3
"""BTC HVN + Absorption — Python order-flow engine entrypoint.

Pipeline:
Binance BTCUSDT (aggTrade + depth + kline5m)
  -> aggregation / delta / CVD / volume profile / HVN
  -> absorption detection -> signal scoring -> signal JSON
  -> IPC (atomic file for MT5, optional localhost TCP)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config                      # noqa: E402
from logger import Logger                      # noqa: E402
from data_health import DataHealth             # noqa: E402
from trade_aggregator import TradeAggregator   # noqa: E402
from delta_engine import DeltaEngine           # noqa: E402
from cvd_engine import CVDEngine               # noqa: E402
from m5_engine import M5Engine                 # noqa: E402
from hvn_engine import HVNEngine               # noqa: E402
from absorption_engine import AbsorptionEngine  # noqa: E402
from liquidity_engine import LiquidityEngine   # noqa: E402
from signal_engine import SignalEngine         # noqa: E402
from sniper_engine import SniperEngine        # noqa: E402
from signal_protocol import (build_signal_payload, build_status_payload,  # noqa: E402
                             validate_signal)
from ipc_server import IPC                     # noqa: E402
from binance_ws import BinanceWS               # noqa: E402
from replay_engine import Recorder, Replayer   # noqa: E402


class Pipeline:
    def __init__(self, cfg: Config, log: Logger):
        self.cfg = cfg
        self.log = log
        self.health = DataHealth(cfg.max_data_age_ms)
        self.agg = TradeAggregator(keep_sec=cfg.trade_keep_sec,
                                   baseline_buckets=cfg.volume_baseline_buckets)
        self.delta = DeltaEngine(keep_sec=max(900, cfg.hvn_lookback_minutes * 60))
        self.cvd = CVDEngine()
        self.m5 = M5Engine(cfg.atr_period, cfg.m5_keep_bars, cfg.swing_k)
        self.hvn = HVNEngine(cfg)
        self.absorption = AbsorptionEngine(cfg)
        self.liq = LiquidityEngine(cfg)
        self.sig = SignalEngine(cfg)
        self.sniper_eng = SniperEngine(cfg)
        self.sniper_why = ""
        self.ipc = IPC(cfg, log)
        self.ws: BinanceWS | None = None
        self.recorder: Recorder | None = None
        self.replay_mode = False

        self.last_price = 0.0
        self.last_trade_ms = 0
        self.first_trade_ms = 0
        self._signals_seen: set[str] = set()
        self._last_status_ms = 0
        self._last_hvn_sig = ""
        self._last_health_log = 0
        self.exit_hint = "NONE"
        self.exit_hint_until_ms = 0
        self.exit_score = 0.0
        self.last_signal_payload: dict | None = None

    # ---- data handlers ---------------------------------------------------
    def on_trade(self, ts_ms: int, price: float, qty: float, is_sell: bool) -> None:
        if price <= 0 or qty <= 0:
            return
        if self.first_trade_ms == 0:
            self.first_trade_ms = ts_ms
        self.last_price = price
        self.last_trade_ms = ts_ms
        self.health.mark_trade(ts_ms)
        for b in self.agg.add_trade(price, qty, ts_ms, is_sell):
            self.cvd.add_bucket(b.sec, b.delta)
        self.delta.add_trade(qty, is_sell, ts_ms)
        self.hvn.on_trade(ts_ms, price, qty)
        self.liq.on_price(ts_ms, price)
        if self.recorder:
            self.recorder.write_trade(ts_ms, price, qty, is_sell)

    def on_kline(self, k: dict) -> None:
        self.m5.on_kline(k)

    # ---- main evaluation ---------------------------------------------------
    def evaluate(self) -> None:
        cfg = self.cfg
        now = self.last_trade_ms
        if now <= 0 or self.last_price <= 0:
            return
        atr = self.m5.atr
        zones = self.hvn.refresh(now)
        zone, dist = self.hvn.nearest(self.last_price)
        dist_atr = (dist / atr) if (zone is not None and dist is not None and atr > 0) else None

        wsec = cfg.absorption_window_sec
        now_sec = int(now // 1000)
        stats = self.agg.window_stats(now_sec, wsec)
        base = self.agg.baseline_per_sec()
        t0 = now - int(wsec * 1000)
        bursts = (self.agg.bursts(t0, now, "sell", cfg.abs_burst_gap_ms)
                  + self.agg.bursts(t0, now, "buy", cfg.abs_burst_gap_ms))
        ev = self.absorption.evaluate(stats, bursts, atr, base)

        flow = {
            "window_delta": round(self.delta.delta_window(now, wsec), 4),
            "short_delta": round(self.delta.delta_window(now, cfg.delta_short_sec), 4),
            "delta_m5": round(self.delta.delta_window(now, 300), 4),
            "delta_ctx": round(self.delta.delta_window(now, 900), 4),
            "cvd": round(self.cvd.cvd(now_sec), 3),
            "vol_mult": round((stats.vol / (base * wsec)) if (stats and base > 0) else 0.0, 3),
        }
        imbalance = None
        if self.ws is not None and self.ws.book.synced:
            imbalance = self.ws.book.imbalance(cfg.depth_levels)
        sweep = self.liq.check(now, atr) if atr > 0 else None

        if self.replay_mode:
            health_ok = not self.health.is_stale(now)
        else:
            health_ok = self.health.healthy(now)

        sniper = self.sniper_eng.evaluate(now, self.agg, self.delta,
                                          ev, dist_atr)
        self.sniper_why = str(sniper.get("why", ""))

        ctx = {
            "now_ms": now, "price": self.last_price, "atr": atr,
            "bar_ts": self.m5.current_bar_ts(), "zones": zones,
            "nearest": zone, "dist_atr": dist_atr, "absorption": ev,
            "flow": flow, "sweep": sweep, "imbalance": imbalance,
            "sniper": sniper, "health_ok": health_ok,
        }
        sig = self.sig.on_update(ctx)
        if sig is not None:
            payload = build_signal_payload(sig)
            ok, reason = validate_signal(
                payload, now_ms_value=now, seen_ids=self._signals_seen,
                max_age_ms=cfg.signal_expiry_sec * 1000 + 5000,
                min_score=cfg.min_signal_score)
            if ok:
                self._signals_seen.add(payload["signal_id"])
                if len(self._signals_seen) > 200:
                    self._signals_seen = set(list(self._signals_seen)[-100:])
                self.ipc.publish_signal(payload)
                self.last_signal_payload = payload
                self.log.log("SIGNAL", "EMITTED",
                             signal_id=payload["signal_id"], setup_id=sig.setup_id,
                             direction=sig.direction, score=sig.score,
                             invalidation=sig.invalidation_price,
                             components=json.dumps(sig.components))
            else:
                self.log.log("SIGNAL", "LOCAL_VALIDATION_REJECTED",
                             reason=reason, signal_id=payload["signal_id"])

        # ---- order-flow exit hint for the EA ------------------------------
        if ev is not None and ev.strength >= cfg.of_exit_min_strength:
            self.exit_hint = "EXIT_SHORT" if ev.direction == "LONG" else "EXIT_LONG"
            self.exit_score = ev.strength
            self.exit_hint_until_ms = now + int(cfg.of_exit_hold_sec * 1000)
            self.log.log("ABSORPTION", "EVENT",
                         direction=ev.direction, strength=ev.strength,
                         vol_mult=ev.vol_mult, disp_atr=ev.disp_atr,
                         cont_atr=ev.cont_atr, eff_decay=ev.eff_decay,
                         n_bursts=ev.n_bursts, hint=self.exit_hint)
        elif now > self.exit_hint_until_ms:
            self.exit_hint, self.exit_score = "NONE", 0.0

        # ---- HVN log on change --------------------------------------------
        hsig = json.dumps([[round(z["center"], 2), round(z["volume"], 3)] for z in zones])
        if hsig != self._last_hvn_sig:
            self._last_hvn_sig = hsig
            self.log.log("HVN", "ZONES", zones=hsig, n=len(zones))

        # ---- status ---------------------------------------------------------
        if now - self._last_status_ms >= cfg.status_interval_ms:
            self._last_status_ms = now
            self.publish_status(now, atr, zones, zone, dist_atr, ev, flow, imbalance)

        # periodic DATA heartbeat
        if now - self._last_health_log > 60_000:
            self._last_health_log = now
            self.log.log("DATA", "HEARTBEAT", **self.health.snapshot(now),
                         price=self.last_price, atr=atr)

    # ---- status publishing ------------------------------------------------
    def publish_status(self, now, atr, zones, zone, dist_atr, ev, flow, imbalance) -> None:
        st: dict = {"engine_state": self.sig.state,
                    "setup_score": round(self.sig.setup["best_score"], 1) if self.sig.setup else 0.0}
        st.update(self.health.snapshot(now))
        st["binance_price"] = round(self.last_price, 2)
        if self.ws is not None:
            st.update(self.ws.book.snapshot_state())
        else:
            st.update({"ob_bid": 0.0, "ob_ask": 0.0, "ob_synced": 0, "ob_imbalance": 0.0})
        if imbalance is not None:
            st["ob_imbalance"] = round(imbalance, 4)

        st.update({
            "delta_win": flow["window_delta"], "delta_short": flow["short_delta"],
            "delta_m5": flow["delta_m5"], "cvd": flow["cvd"], "vol_mult": flow["vol_mult"],
            "atr_m5": round(atr, 2),
            "atr_ctx": round(atr, 2),
            "delta_ctx": flow["delta_ctx"],
            "entry_mode": self.cfg.entry_mode,
            "sniper_why": self.sniper_why,
        })

        # data maturity: how full the rolling windows are (user-facing ETA)
        if self.first_trade_ms > 0:
            win_ms = self.cfg.hvn_lookback_minutes * 60_000
            st["hvn_fill_pct"] = int(min(100, (now - self.first_trade_ms) / win_ms * 100))
        else:
            st["hvn_fill_pct"] = 0
        st["atr_wait_bars"] = max(0, self.cfg.atr_period - len(self.m5.bars))

        n = min(len(zones), 5)
        st["hvn_count"] = n
        for i in range(n):
            z = zones[i]
            st[f"hvn{i}_low"] = round(z["low"], 2)
            st[f"hvn{i}_high"] = round(z["high"], 2)
            st[f"hvn{i}_center"] = round(z["center"], 2)
            st[f"hvn{i}_rel"] = round(z["rel"], 2)
        if zone is not None:
            st["nearest_low"] = round(zone["low"], 2)
            st["nearest_high"] = round(zone["high"], 2)
            st["nearest_center"] = round(zone["center"], 2)
            st["nearest_dist_atr"] = round(dist_atr, 4) if dist_atr is not None else -1
        else:
            st.update({"nearest_low": 0.0, "nearest_high": 0.0,
                       "nearest_center": 0.0, "nearest_dist_atr": -1})

        if ev is not None:
            st["absorption_direction"] = ev.direction
            st["absorption_strength"] = ev.strength
        else:
            st["absorption_direction"] = ""
            st["absorption_strength"] = 0.0
        st["exit_hint"] = self.exit_hint
        st["exit_score"] = round(self.exit_score, 1)

        lsp = self.last_signal_payload
        if lsp:
            st["signal_id"] = lsp["signal_id"]
            st["signal_direction"] = lsp["direction"]
            st["signal_score"] = lsp["score"]
        else:
            st.update({"signal_id": "", "signal_direction": "", "signal_score": 0.0})

        self.ipc.publish_status(build_status_payload(st))


# ---------------------------------------------------------------------------
async def run_live(app: Pipeline, stop: asyncio.Event) -> None:
    ws = BinanceWS(app.cfg, app.health, on_trade=app.on_trade,
                   on_kline=app.on_kline, logger=app.log)
    app.ws = ws
    task = asyncio.create_task(ws.run(stop))
    if app.cfg.record_trades:
        path = os.path.join("data", "replay",
                            f"trades_{time.strftime('%Y%m%d')}.jsonl")
        app.recorder = Recorder(path)
        app.log.log("DATA", "RECORDING_ON", path=path)
    last_beat = time.time()
    try:
        while not stop.is_set():
            await asyncio.sleep(0.5)
            try:
                app.evaluate()
            except Exception as exc:      # noqa: BLE001 - never crash the loop
                app.log.error("EVALUATE_ERROR", err=str(exc)[:200])
            if time.time() - last_beat > 30:
                last_beat = time.time()
                app.log.log("DATA", "ENGINE_ALIVE", state=app.sig.state,
                            price=app.last_price, healthy=app.health.healthy(app.last_trade_ms))
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


async def run_replay(app: Pipeline, stop: asyncio.Event) -> None:
    rows = Replayer.load(app.cfg.replay_file)
    if not rows:
        app.log.error("REPLAY_EMPTY", file=app.cfg.replay_file)
        return
    app.replay_mode = True
    app.health.mark_connected(int(rows[0]["T"]))
    app.log.log("DATA", "REPLAY_START", rows=len(rows), speed=app.cfg.replay_speed)

    def on_tick(sim_now_ms: int) -> None:
        try:
            app.evaluate()
        except Exception as exc:      # noqa: BLE001
            app.log.error("REPLAY_EVAL_ERROR", err=str(exc)[:200])

    n = await Replayer.run(rows, app.on_trade, on_tick,
                           speed=app.cfg.replay_speed, stop_event=stop,
                           on_kline=app.on_kline)
    app.log.log("DATA", "REPLAY_DONE", trades=n,
                signals=app.sig.signals_emitted)


def resolve_config_path(explicit: str) -> str:
    """Resolve the config file location. Accepts an explicit path; otherwise
    searches: CWD, the python/ folder, and the project root. Returns the
    resolved path (may point to a non-existent explicit path)."""
    if explicit and os.path.exists(explicit):
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), "config.json"),
        os.path.join(here, "config.json"),
        os.path.join(os.path.dirname(here), "config.json"),
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return cand
    return explicit


async def amain(args) -> None:
    cfg_path = resolve_config_path(args.config)
    cfg = Config.load(cfg_path)
    log = Logger(cfg.log_dir, cfg.log_console)
    app = Pipeline(cfg, log)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, stop.set)
        except (NotImplementedError, AttributeError):
            pass
    await app.ipc.start_tcp()
    log.log("DATA", "ENGINE_START", config_file=cfg_path or "defaults",
            ipc_mode=cfg.ipc_mode,
            signal_path=cfg.signal_path(), status_path=cfg.status_path(),
            replay=bool(cfg.replay_file))
    try:
        if cfg.replay_file:
            await run_replay(app, stop)
        else:
            await run_live(app, stop)
    finally:
        await app.ipc.stop()
        log.log("DATA", "ENGINE_STOP", signals=app.sig.signals_emitted)


def main() -> None:
    ap = argparse.ArgumentParser(description="BTC HVN + Absorption order-flow engine")
    ap.add_argument("--config", default="config.json", help="JSON config file")
    args = ap.parse_args()
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        print("stopped by user", flush=True)


if __name__ == "__main__":
    main()
