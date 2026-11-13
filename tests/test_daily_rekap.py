# -*- coding: utf-8 -*-
"""v3.54: rekap harian basis deal = riwayat aplikasi broker."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from cc_broker import _agg_deals

DAY = 1740000000  # epoch tengah malam "hari broker" (fiktif tetap)


class D(object):
    """Deal palsu ala MetaTrader5 TradeDeal."""
    def __init__(self, t, time, profit=0.0, swap=0.0, commission=0.0,
                 volume=0.0, entry=0, pid=0):
        self.type = t
        self.time = time
        self.profit = profit
        self.swap = swap
        self.commission = commission
        self.volume = volume
        self.entry = entry          # 0=IN 1=OUT 2=INOUT 3=OUT_BY
        self.position_id = pid


B, S = 0, 1
YDAY = DAY - 3600        # kemarin (sebelum jendela)
NOW = DAY + 3600         # hari ini

DEALS = [
    # 1) order penuh hari ini: IN + OUT, untung (profit di deal OUT)
    D(B, NOW, profit=0.0, commission=-2.0, volume=0.02, entry=0, pid=1),
    D(B, NOW + 60, profit=80.0, commission=-2.0, volume=0.02, entry=1, pid=1),
    # 2) partial close: 2x OUT, rugi total
    D(S, NOW, profit=-30.0, commission=-1.5, volume=0.01, entry=0, pid=2),
    D(S, NOW + 30, profit=-25.0, commission=-1.0, volume=0.01, entry=1, pid=2),
    D(S, NOW + 40, profit=-15.0, commission=-0.5, volume=0.01, entry=1, pid=2),
    # 3) dibuka KEMARIN, ditutup hari ini (komisi IN jatuh kemarin)
    D(S, YDAY, profit=0.0, commission=-3.0, volume=0.05, entry=0, pid=3),
    D(S, NOW + 90, profit=60.0, commission=-1.0, volume=0.05, entry=1, pid=3),
    # 4) REVERSAL (entry=2) - dulu TIDAK terhitung sama sekali
    D(B, NOW, profit=0.0, commission=-1.0, volume=0.03, entry=0, pid=4),
    D(B, NOW + 120, profit=12.0, commission=-1.0, volume=0.06, entry=2, pid=4),
    # 5) CLOSE BY (entry=3) - dulu juga tidak terhitung
    D(S, NOW, profit=0.0, commission=-1.0, volume=0.04, entry=0, pid=5),
    D(S, NOW + 150, profit=-20.0, commission=0.0, volume=0.04, entry=3, pid=5),
    # 6) dibuka hari ini, MASIH TERBUKA: komisinya ikut rekap hari ini
    D(B, NOW + 10, profit=0.0, commission=-2.5, volume=0.02, entry=0, pid=6),
    # 7) deal balance (deposit) - harus diabaikan
    D(6, DAY + 5, profit=500.0, pid=0),
]


def test_rekap():
    r = _agg_deals(DEALS, DAY, B, S)
    # uang = deal-based (hanya deal hari broker ini; deposit & komisi
    # IN-kemarin keluar; komisi OUT order kemarin tetap hari ini)
    assert r["profit_deal"] == 80.0 - 70.0 + 60.0 + 12.0 - 20.0, r
    assert r["commission"] == -13.5, r          # 6 kelompok komisi hari ini
    assert r["realized"] == round(r["profit_deal"] + r["commission"], 2)
    # split per EVENT CLOSE (v3.55): tiap deal close dihitung sendiri
    # win : +80 (TP penuh) | +60 (order kemarin ditutup) | +12 (reversal)
    # loss: -25 & -15 (2x partial) | -20 (close-by)
    assert r["wins"] == 3 and r["losses"] == 3, r
    assert r["gross_win"] == round(80 + 60 + 12, 2), r
    assert r["gross_loss"] == round(25 + 15 + 20, 2), r
    # deposit tidak bocor
    assert r["realized"] < 100
    # volume OUT saja (0.02+0.02+0.05+0.06+0.04)
    assert abs(r["lots"] - 0.19) < 1e-9, r


def test_kosong_dan_batas():
    r0 = _agg_deals([], DAY)
    assert r0["realized"] == 0.0 and r0["wins"] == 0
    # deal tepat di batas tengah malam ikut
    r1 = _agg_deals([D(B, DAY, profit=5.0, entry=1, pid=9)], DAY)
    assert r1["profit_deal"] == 5.0
    # deal 1 detik sebelum tengah malam tidak ikut
    r2 = _agg_deals([D(B, DAY - 1, profit=5.0, entry=1, pid=9)], DAY)
    assert r2["profit_deal"] == 0.0


def test_data_nyata_screenshot():
    """Replika PERSIS 5 order 'Hari ini 01 Oktober' dari app broker user
    (IDR): 3 close profit + 2 SL. PROFIT/LOSS dijumlah terpisah."""
    deals = [
        # XAG/USD SL -158,034.53 (Beli 0.02)
        D(B, NOW, profit=0.0, commission=0.0, volume=0.02, entry=0, pid=11),
        D(B, NOW + 10, profit=-158034.53, volume=0.02, entry=1, pid=11),
        # USTEC SL +63,267.27 (Beli 0.61)
        D(B, NOW + 20, profit=0.0, volume=0.61, entry=0, pid=12),
        D(B, NOW + 30, profit=63267.27, volume=0.61, entry=1, pid=12),
        # EUR/USD SL +277,924.26 (Jual 0.97) -> close-nya deal BUY
        D(S, NOW + 40, profit=0.0, volume=0.97, entry=0, pid=13),
        D(B, NOW + 50, profit=277924.26, volume=0.97, entry=1, pid=13),
        # EUR/USD SL -76,085.14 (Jual 0.53)
        D(S, NOW + 60, profit=0.0, volume=0.53, entry=0, pid=14),
        D(B, NOW + 70, profit=-76085.14, volume=0.53, entry=1, pid=14),
        # BTC SL +6,444.22 (Jual 0.01)
        D(S, NOW + 80, profit=0.0, volume=0.01, entry=0, pid=15),
        D(S, NOW + 90, profit=6444.22, volume=0.01, entry=1, pid=15),
    ]
    r = _agg_deals(deals, DAY, B, S)
    assert r["wins"] == 3 and r["losses"] == 2, r
    assert r["gross_win"] == round(63267.27 + 277924.26 + 6444.22, 2), r
    assert r["gross_loss"] == round(158034.53 + 76085.14, 2), r
    # net = +113,516.08 = persis header "Hari ini" di app
    assert r["profit_deal"] == 113516.08, r


def test_deposit_ke_bal_ops():
    """Deposit hari ini: TIDAK masuk P/L, TAPI tercatat di bal_ops."""
    deals = [
        D(2, DAY + 5, profit=5000.0, pid=0),            # deposit (balance)
        D(B, DAY + 10, profit=0.0, commission=-1.0,
          volume=0.01, entry=0, pid=21),
        D(B, DAY + 20, profit=100.0, commission=-1.0,
          volume=0.01, entry=1, pid=21),
    ]
    r = _agg_deals(deals, DAY, B, S, t_bal=2)
    assert r["bal_ops"] == 5000.0, r
    assert r["profit_deal"] == 100.0, r                 # deposit tidak bocor
    assert r["realized"] == 98.0, r                     # 100 - 2 komisi
