"""Test inti strategi RBT FX (ringkas, dibangun ulang saat audit v3.41).
Fokus: gerbang zona HH/HL M5, sniper M5, rejection filter, anti sinyal lama,
daily P/L zona WIB. Lokal saja - tidak di-upload ke repo."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import cc_scanner
import cc_risk
from cc_config import CCConfig


def m5_data(closes, opens=None):
    opens = opens if opens is not None else [c - 0.1 for c in closes]
    return {"open": list(opens),
            "high": [max(o, c) + 0.1 for o, c in zip(opens, closes)],
            "low": [min(o, c) - 0.1 for o, c in zip(opens, closes)],
            "close": list(closes),
            "time": list(range(len(closes))),
            "tick_volume": [10] * len(closes)}


def uptrend_data(n=120, base=100.0, slope=0.15):
    import math
    closes = [base + slope * i + 2.0 * math.sin(i / 5.0) for i in range(n)]
    def bars(cs, mul=1.0):
        o = [c - 0.2 * mul for c in cs]
        return {"open": o, "close": list(cs),
                "high": [max(a, b) + 0.5 * mul for a, b in zip(o, cs)],
                "low": [min(a, b) - 0.5 * mul for a, b in zip(o, cs)],
                "time": list(range(len(cs))),
                "tick_volume": [100.0 + 10 * (i % 5) for i in range(len(cs))]}
    return {"m15": bars(closes, 3.0),
            "m5": bars([c + 0.05 * i for i, c in enumerate(closes)]),
            "m1": bars(closes[-120:]),
            "delta": {"buy": 60.0, "sell": 40.0}}


class TestM5ZoneGate(unittest.TestCase):
    """v3.41: sniper M5 scan zona HH/HL S/R - jangan entry di lembah/puncak.
    Fixture zigzag konkret; knob cfg dipaksa utk tiap cabang agar robust."""

    SELL_ZZ = [110,108,106,105.5,105,107,109,111,112,110,108,106,
               104.5,103,105,108,110,112.5,108,104,103.2]
    BUY_ZZ = [93,95,97,97.5,98,96,94,92,91,93,95,97,
              98.5,100,98,95,93,90.5,95,99,99.8]

    def _red(self, closes, last=None):
        o = list(closes)
        o[-1] = last if last else closes[-1] + 0.8   # candle terakhir merah
        return m5_data(closes, o)

    def _green(self, closes, last=None):
        o = list(closes)
        o[-1] = last if last else closes[-1] - 0.8   # candle terakhir hijau
        return m5_data(closes, o)

    # ---- SELL ----
    def test_sell_dekat_lembah_ditahan(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 100.0,
               "zone_pull_atr": 100.0}
        ok, why = cc_scanner.m5_zone_gate("SELL", self._red(self.SELL_ZZ),
                                          cfg)
        self.assertFalse(ok)
        self.assertEqual(why, "tunggu_breakout_lembah_atau_rebound_hh")

    def test_sell_breakout_valid_boleh(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 0.001}
        closes = self.SELL_ZZ + [102.0]          # menembus lembah 102.9
        ok, why = cc_scanner.m5_zone_gate("SELL", self._red(closes), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_breakout_lembah")

    def test_sell_rebound_hh_valid_boleh(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 100.0,
               "zone_pull_atr": 0.01}
        ok, why = cc_scanner.m5_zone_gate(
            "SELL", self._red(self.SELL_ZZ, last=104.0), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_rebound_hh_sell")

    # ---- BUY ----
    def test_buy_dekat_puncak_ditahan(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 100.0,
               "zone_pull_atr": 100.0}
        ok, why = cc_scanner.m5_zone_gate("BUY", self._green(self.BUY_ZZ),
                                          cfg)
        self.assertFalse(ok)
        self.assertEqual(why, "tunggu_breakout_puncak_atau_dip_ll")

    def test_buy_breakout_valid_boleh(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 0.001}
        closes = self.BUY_ZZ + [100.8]           # menembus puncak 100.1
        ok, why = cc_scanner.m5_zone_gate("BUY", self._green(closes), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_breakout_puncak")

    def test_buy_dip_ll_valid_boleh(self):
        cfg = {"zone_near_atr": 100.0, "zone_breakout_atr": 100.0,
               "zone_pull_atr": 0.01}
        ok, why = cc_scanner.m5_zone_gate(
            "BUY", self._green(self.BUY_ZZ, last=99.0), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_dip_ll_buy")

    def test_data_kurang_fail_open(self):
        ok, _ = cc_scanner.m5_zone_gate("SELL", m5_data([100, 101]),
                                        {"zone_near_atr": 100.0})
        self.assertTrue(ok)


class TestSniperM5Terpadu(unittest.TestCase):
    CFG = {"sniper_m5_min_score": 55.0, "zone_near_atr": 100.0,
           "zone_breakout_atr": 100.0, "zone_pull_atr": 100.0}

    def test_zona_menahan_sebelum_momentum_sell(self):
        res = {"side": "SELL", "score": 80.0}
        closes = [110,108,106,105.5,105,107,109,111,112,110,108,106,
                  104.5,103,105,108,110,112.5,108,104,103.2]
        o = list(closes); o[-1] = closes[-1] + 0.8
        ok, why = cc_scanner.sniper_m5(res, m5_data(closes, o), self.CFG)
        self.assertFalse(ok)
        self.assertEqual(why, "tunggu_breakout_lembah_atau_rebound_hh")

    def test_sell_full_lolos_breakout(self):
        res = {"side": "SELL", "score": 80.0}
        closes = [110,108,106,105.5,105,107,109,111,112,110,108,106,
                  104.5,103,105,108,110,112.5,108,104,102.0]
        cfg = {"sniper_m5_min_score": 55.0, "zone_near_atr": 100.0,
               "zone_breakout_atr": 0.001}
        o = list(closes); o[-1] = closes[-1] + 0.5
        ok, why = cc_scanner.sniper_m5(res, m5_data(closes, o), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_momentum_sell")

    def test_buy_full_lolos_breakout(self):
        res = {"side": "BUY", "score": 80.0}
        closes = [93,95,97,97.5,98,96,94,92,91,93,95,97,
                  98.5,100,98,95,93,90.5,95,99,100.8]
        cfg = {"sniper_m5_min_score": 55.0, "zone_near_atr": 100.0,
               "zone_breakout_atr": 0.001}
        o = list(closes); o[-1] = closes[-1] - 0.5
        ok, why = cc_scanner.sniper_m5(res, m5_data(closes, o), cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "m5_momentum_buy")


class TestRejectionFilter(unittest.TestCase):
    def test_bear_rej(self):
        m = {"open": [100.0], "high": [101.5], "low": [99.6], "close": [99.8]}
        self.assertEqual(cc_scanner.m15_rejection_side(m, {}), "BEAR")

    def test_block_buy_vs_bear_downtrend(self):
        self.assertIsNotNone(
            cc_scanner.rejection_block("BUY", "BEAR", 99.0, 101.0))

    def test_allow_buy_vs_bear_uptrend(self):
        self.assertIsNone(
            cc_scanner.rejection_block("BUY", "BEAR", 101.0, 99.0))


class TestAntiSinyalLama(unittest.TestCase):
    def _g(self):
        class B:
            def account(self):
                return {"balance": 10000.0, "equity": 10000.0,
                        "currency": "USD"}
        return cc_risk.RiskGuard(CCConfig(), B(),
                                 day_file=tempfile.mkstemp()[1])

    def test_born_sebelum_close_ditolak(self):
        g = self._g()
        g.note_closed("XAUUSD", -5.0, now=2000.0)
        ok, why = g.fresh_entry_ok("XAUUSD", 1500.0)
        self.assertFalse(ok)
        self.assertIn("SINYAL_LAMA", why)

    def test_born_sesudah_close_boleh(self):
        g = self._g()
        g.note_closed("XAUUSD", -5.0, now=2000.0)
        ok, _ = g.fresh_entry_ok("XAUUSD", 2500.0)
        self.assertTrue(ok)


class TestDailyZonaWIB(unittest.TestCase):
    # v3.68: user di Mataram (WIB, UTC+7) -> batas hari = tengah malam
    # WIB = jam 00:00 di HP/VPS user (dulu WIB 7.0 -> reset jam 01:00
    # waktu user, dianggap belum reset).
    def test_default_wib(self):
        self.assertEqual(CCConfig().get("day_tz_offset"), 7.0)

    def test_since_tengah_malam_wib(self):
        class B:
            def account(self):
                return {"balance": 10000.0, "equity": 10000.0,
                        "currency": "USD"}
        g = cc_risk.RiskGuard(CCConfig(), B(),
                              day_file=tempfile.mkstemp()[1])
        g.ensure_day()
        self.assertEqual(g.day_since() % 86400, 17 * 3600)


class TestAnalyzeSmoke(unittest.TestCase):
    def test_uptrend_memberi_buy(self):
        res = cc_scanner.analyze("TESTUSD", uptrend_data(),
                                 {"min_score": 70})
        self.assertIsNotNone(res)
        self.assertIn(res["side"], ("BUY", "SELL"))
        self.assertIn("rej_blocked", res)
        self.assertIn("sig_time", res)


if __name__ == "__main__":
    unittest.main()


# ============ v3.64: PERBANYAK PAIR (13 baru -> total 22) ===================
FOREX_PLAIN = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD",
               "USDCAD", "USDCHF", "EURJPY", "GBPJPY"}


def test_cfg_pair_banyak():
    import cc_config
    c = cc_config.DEFAULTS
    assert len(c["symbols"]) >= 22
    # 13 pair baru wajib ada
    for s in ("AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "EURJPY", "GBPJPY",
              "SOLUSD", "XRPUSD", "LTCUSD", "US30", "GER40", "US500",
              "XPTUSD"):
        assert s in c["symbols"], s
    # semua pair terdaftar harus bisa di-resolve: ada di alternates ATAU
    # forex mayor (nama polos)
    for s in c["symbols"]:
        assert s in c["symbol_alternates"] or s in FOREX_PLAIN, s
        if s in c["symbol_alternates"]:
            assert s in c["symbol_alternates"][s], s  # nama utk ikut di coba
            assert c["symbol_alternates"][s], s
    # pagar spread pair volatil baru
    so = c["spread_overrides"]
    assert so.get("SOLUSD") == 2500 and so.get("XRPUSD") == 2500 \
        and so.get("LTCUSD") == 2500 and so.get("XPTUSD") == 1500
