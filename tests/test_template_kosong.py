import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import cc_strategy3 as S
from cc_config import DEFAULTS

DATA = {"info": {"bid": 2500.5, "ask": 2500.6, "point": 0.01},
        "m5": {"time": list(range(1, 21)), "open": [1.0]*20,
               "high": [1.0]*20, "low": [1.0]*20, "close": [1.0]*20},
        "m15": {"time": [1], "open": [1.0], "high": [1.0], "low": [1.0],
                "close": [1.0]},
        "m1": {}, "h1": {}}


def test_evaluate_selalu_wait_tanpa_exec():
    r = S.evaluate("BTCUSD", DATA, {}, None)
    assert r["status"] == "WAIT"
    assert r["exec"] is None
    assert r["score"] == 0.0
    assert "template" in r["why"].lower()


def test_s2_cfg_kosong():
    assert S.s2_cfg({}) == {}
    assert S.s2_cfg({"s3": {"ema_fast": 13}}) == {}   # abaikan config lama


def test_validate_execution_memblokir_semua():
    ok, why, sl, tp, keep = S.validate_execution(
        "BTCUSD", {}, DATA, 1.0, 1.1)
    assert ok is False and keep is False and sl == 0.0 and tp == 0.0


def test_tidak_ada_satu_pun_logika_filter_s3():
    for gone in ("adx_gate", "adx_wilder", "ml_gate", "ml_features",
                 "msf_gate", "detect_zones", "zone_quality",
                 "nearest_opposing", "structure_state", "h1_regime",
                 "m5_momentum", "m1_trigger", "ema_reversal_block",
                 "ema_cross_state", "fp_database", "fp_match",
                 "fp_match_cached", "candle_feats", "fp_vector",
                 "_zones_of", "_clamp100"):
        assert not hasattr(S, gone), f"{gone} masih ada!"


def test_alat_netral_dan_infra_tersedia():
    for need in ("evaluate", "_result", "s2_cfg", "validate_execution",
                 "ema_at", "ema_series", "atr_at", "swings", "merge_bars",
                 "Strategy2State", "ATRTrail", "tp_ladder_decision",
                 "journal", "journal_exit", "hist_paged", "hist_years",
                 "session_of", "data_quality", "spread_limit",
                 "pip_entry_plan"):
        assert hasattr(S, need), f"{need} hilang!"


def test_config_parameter_s3_kosong():
    assert DEFAULTS.get("s3") == {}


def test_engine_selalu_evaluasi_template_dan_log_kosong():
    src = open(os.path.join(os.path.dirname(__file__), "..", "python",
                            "command_center.py"), encoding="utf-8").read()
    assert "self.s2_on = True" in src          # selalu evaluasi (WAIT)
    assert "TEMPLATE KOSONG" in src            # log startup jelas


def test_state_infra_tetap_jalan(tmp_path):
    st = S.Strategy2State(os.path.join(str(tmp_path), "s3_state.json"))
    tr = S.ATRTrail("BTCUSD", 1, 2500.0, 10.0)   # trail valid utk state
    st.set_trail("BTCUSD", tr)
    assert st.get_trail("BTCUSD") is not None
    st.set_cooldown("BTCUSD", minutes=5)
    assert st.cooldown_until("BTCUSD") > 0
    st.del_trail("BTCUSD")          # trail dihapus dgn del_trail
    assert st.get_trail("BTCUSD") is None
    st.clear("BTCUSD")              # clear = state sinyal/pending


def test_merge_bars_infra_tetap_jalan():
    older = {"time": [1, 2], "open": [1.0, 1.0], "high": [1.0, 1.0],
             "low": [1.0, 1.0], "close": [1.0, 1.0],
             "tick_volume": [10, 10]}
    newer = {"time": [3], "open": [1.0], "high": [1.0], "low": [1.0],
             "close": [1.0], "tick_volume": [10]}
    m = S.merge_bars(older, newer)
    assert list(m["time"]) == [1, 2, 3]
