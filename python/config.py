"""Central configuration for the BTC HVN + Absorption order-flow engine.

Every important threshold is configurable (spec section 44). Values can be
overridden from a JSON config file and from environment variables.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


@dataclass
class Config:
    # ---- DATA / BINANCE -------------------------------------------------
    binance_symbol: str = "btcusdt"
    # multiple hosts: engine rotates automatically if one is blocked (451)
    binance_rest_hosts: list = ("https://api.binance.com",
                                "https://api1.binance.com",
                                "https://api2.binance.com",
                                "https://data-api.binance.vision")
    binance_ws_hosts: list = ("wss://stream.binance.com:9443/stream",
                              "wss://stream.binance.com:443/stream",
                              "wss://data-stream.binance.vision:9443/stream")
    context_stream: str = "kline_15m"    # stream kline M15 (konteks entry)
    max_data_age_ms: int = 5000          # stale-data threshold
    reconnect_delay_ms: int = 2000
    reconnect_delay_max_ms: int = 30000
    depth_levels: int = 50               # levels kept of the local book
    depth_speed: str = "100ms"           # diff-depth stream speed
    trade_keep_sec: int = 180            # raw trade retention
    snapshot_depth_limit: int = 1000     # REST depth snapshot limit

    # ---- IPC ------------------------------------------------------------
    ipc_mode: str = "file"               # file | tcp | both
    ipc_tcp_host: str = "127.0.0.1"
    ipc_tcp_port: int = 8765
    mt5_common_dir: str = ""             # MT5 Common\Files dir (env MT5_COMMON_FILES_DIR)
    out_dir: str = "out"
    signal_file: str = "BTC_HVN_SIGNAL.json"
    status_file: str = "BTC_HVN_STATUS.json"
    status_interval_ms: int = 1000
    signal_expiry_sec: float = 10.0

    # ---- M5 CONTEXT -------------------------------------------------------
    atr_period: int = 14
    swing_k: int = 2
    m5_keep_bars: int = 200

    # ---- HVN --------------------------------------------------------------
    hvn_lookback_minutes: int = 120
    price_bin_size: float = 10.0
    hvn_percentile: float = 85.0
    hvn_min_rel_volume: float = 1.5      # zone volume >= mean * this
    min_hvn_zone_width: float = 10.0
    max_hvn_zone_width: float = 120.0
    max_hvn_zones: int = 5
    hvn_proximity_atr: float = 0.20
    hvn_refresh_sec: float = 2.0

    # ---- ABSORPTION -------------------------------------------------------
    absorption_window_sec: float = 90.0  # M15-scale absorption window
    abs_side_baseline_split: float = 0.5  # baseline per sisi (buy/sell) dari total
    abs_min_vol_multiple: float = 1.5    # side volume vs baseline*window
    abs_max_disp_atr: float = 0.15       # max net displacement (ATR units)
    abs_continuation_factor: float = 1.5 # max total extension vs net limit
    abs_min_bursts: int = 2
    abs_eff_decay: float = 0.70          # last/first burst efficiency must be <=
    abs_burst_gap_ms: int = 700
    abs_strong: float = 85.0             # "very strong absorption" threshold

    # ---- DELTA / RECLAIM / SETUP -----------------------------------------
    delta_short_sec: float = 10.0   # snappy recovery window (M5 role)
    delta_recovery_ratio: float = 0.30
    require_delta_turn_positive: bool = True
    require_reclaim: bool = True
    reclaim_buffer_atr: float = 0.05
    invalidation_buffer_atr: float = 0.10
    setup_timeout_sec: float = 420.0     # M15 setups live longer

    # ---- SNIPER ENTRY (M5/M1 precision trigger) ---------------------------
    # entry_mode: "m15_sniper" = M15 setup, final trigger from micro
    #             structure (M1-scale ticks). "legacy" = emit immediately.
    entry_mode: str = "m15_sniper"
    sniper_active_sec: float = 180.0     # sniper window after setup ready
    sniper_micro_delta_sec: float = 20.0 # micro delta window
    sniper_range_base_sec: float = 45.0  # micro range base (older)
    sniper_range_recent_sec: float = 15.0  # micro range recent (newer)
    sniper_micro_delta_min: float = 0.0  # min |micro delta| (0 = sign only)

    # ---- OPTIONAL FILTERS (all switchable so EA does not over-filter) -----
    use_liquidity_sweep: bool = False
    liquidity_lookback_min: int = 60
    sweep_buffer_atr: float = 0.10
    use_orderbook_filter: bool = False
    min_imbalance_ratio: float = 0.10
    use_atr_filter: bool = False
    min_atr: float = 0.0
    max_atr: float = 0.0
    use_volume_filter: bool = False

    # ---- SIGNAL -----------------------------------------------------------
    min_signal_score: float = 70.0
    weight_hvn: float = 20.0
    weight_absorption: float = 30.0
    weight_displacement: float = 20.0
    weight_delta: float = 15.0
    weight_reclaim: float = 10.0
    weight_volume: float = 5.0
    volume_spike_mult: float = 1.5
    volume_baseline_buckets: int = 300
    cooldown_sec: float = 60.0
    max_signals_per_m5_bar: int = 2

    # ---- ORDER-FLOW EXIT HINT (information for the EA) --------------------
    of_exit_min_strength: float = 60.0
    of_exit_hold_sec: float = 10.0

    # ---- REPLAY / RECORDING ----------------------------------------------
    record_trades: bool = False
    replay_file: str = ""
    replay_speed: float = 10.0

    # ---- LOGGING ----------------------------------------------------------
    log_dir: str = "data/logs"
    log_console: bool = True

    # ---------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        cfg = cls()
        data = {}
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        for k, v in data.items():
            if hasattr(cfg, k) and not k.startswith("_"):
                cur = getattr(cfg, k)
                try:
                    setattr(cfg, k, type(cur)(v) if cur is not None else v)
                except (TypeError, ValueError):
                    setattr(cfg, k, v)
        cfg.mt5_common_dir = str(_env("MT5_COMMON_FILES_DIR", cfg.mt5_common_dir))
        cfg.ipc_mode = str(_env("IPC_MODE", cfg.ipc_mode))
        return cfg

    def resolve_ipc_dir(self) -> str:
        d = (self.mt5_common_dir or "").strip()
        if d:
            return d
        return os.path.join(self.out_dir, "mt5_ipc")

    def signal_path(self) -> str:
        return os.path.join(self.resolve_ipc_dir(), self.signal_file)

    def status_path(self) -> str:
        return os.path.join(self.resolve_ipc_dir(), self.status_file)

    def replay_dir(self) -> str:
        return "data/replay"

    def to_dict(self) -> dict:
        return asdict(self)
