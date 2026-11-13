# -*- coding: utf-8 -*-
"""Fixture pasar sintetis S3-VALID (dipakai lintas test).

Data dirancang lolos SELURUH gerbang evaluate() S3 utk BUY breakout:
  - M15: gelombang naik (struktur HH/HL, ATR ~0.6) -> konsolidasi dgn
    pivot RESISTANCE bar 45 (wick besar, v4.12 lolos anti-zona-palsu)
    -> push breakout: close[70] DI JENDELA (hi+0.05ATR, hi+0.25ATR]
    (di atas itu zona INVALID, di bawah tidak breakout).
  - Fingerprint: bar 30-34 = kembaran bentuk candle 66-70 -> sim ~100.
  - ADX M15 > 25 (tren), EMA13>EMA21 naik (no reversal v4.24),
    regime H1 TREND_UP, skor >= 70.
  - Waktu real (bar terakhir ~sekarang) + dq_stale_sec 0 utk cek basi.
SELL = cermin harga (mirror_bars) -> breakdown SUPPORT.
"""
import os
import sys
import time as _t

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

WANT = "XAUUSD"
DQ = {"dq_stale_sec": 0}      # data sintetis -> cek feed basi OFF


def _up(o, c, wk=0.15):
    return (o, max(o, c) + wk, min(o, c) - wk, c)


def _mk(rows, t_end, step):
    n = len(rows)
    t0 = t_end - (n - 1) * step
    return {"time": [t0 + i * step for i in range(n)],
            "open": [r[0] for r in rows], "high": [r[1] for r in rows],
            "low": [r[2] for r in rows], "close": [r[3] for r in rows],
            "tick_volume": [1] * n}


def _m15_rows():
    rows = []
    b = 90.0
    for i in range(40):                       # gelombang naik 90 -> ~103.5
        c = b + 0.35 if (i // 5) % 2 == 0 else b - 0.30
        rows.append(_up(b, c))
        b = c
    drift = 103.5 - rows[-1][3]
    rows = [(o + drift, h + drift, l + drift, c + dr) for
            (o, h, l, c), dr in
            zip(rows, [drift] * len(rows))]
    p = 103.5
    for i in range(10):                       # konsolidasi 1 (bar 40-49)
        if i == 5:
            rows.append((104.2, 107.0, 104.0, 104.5))   # pivot RESISTANCE
            p = 104.5
        else:
            c = p + 0.12 if i % 2 == 0 else p - 0.12
            rows.append(_up(p, c))
            p = c
    p = 104.4
    for i in range(10):                       # konsolidasi 2 (bar 50-59)
        if i == 5:
            rows.append((104.0, 104.4, 102.6, 104.3))   # pivot SUPPORT (HL)
            p = 104.3
        else:
            c = p + 0.12 if i % 2 == 0 else p - 0.12
            rows.append(_up(p, c))
            p = c
    p = 104.4                                 # push breakout (60-70)
    for d in [0.40, 0.40, 0.40, 0.40, 0.32, 0.28, 0.24, 0.18, 0.10,
              0.08, 0.05]:
        rows.append(_up(p, p + d))
        p += d
    rows.append((p, p + 0.25, p - 0.25, p + 0.05))      # bar forming (71)
    assert len(rows) == 72, len(rows)
    # kembaran fingerprint: bar 30-34 = bentuk candle 66-70
    for k, d in zip(range(30, 35), [0.24, 0.18, 0.10, 0.08, 0.05]):
        o = rows[k][0]
        rows[k] = (o, o + d + 0.15, o - 0.15, o + d)
    return rows


def _m5_rows():
    rows = []
    p = 107.4
    for i in range(120):
        c = p + (0.30 if i == 118 else (0.12 if i % 6 else -0.08))
        rows.append(_up(p, c, 0.08))          # bar 118 = displacement M5
        p = c
    return rows


def _m1_rows():
    """M1 trigger: micro-HL (lembah mikro) + candle trigger bull."""
    rows = []
    p = 107.9
    for i in range(10):
        c = p + 0.06
        rows.append(_up(p, c, 0.05))
        p = c
    rows.append(_up(p, p - 0.12, 0.05))       # lembah
    p -= 0.12
    for i in range(4):
        c = p + 0.05
        rows.append(_up(p, c, 0.05))
        p = c
    lo1 = p
    p += 0.05
    rows.append(_up(p, p - 0.06, 0.05))       # low ke-2 DI ATAS lembah
    p -= 0.06
    for i in range(4):
        c = p + 0.08
        rows.append(_up(p, c, 0.05))
        p = c
    rows.append(_up(p, p + 0.12, 0.05))       # trigger bull tembus close
    return rows


def market():
    """Return (data, bid) -- BUY breakout valid utk evaluate() S3."""
    t_end = int(_t.time()) - 60
    m15 = _mk(_m15_rows(), t_end, 900)
    m5 = _mk(_m5_rows(), t_end, 300)
    m1 = _mk(_m1_rows(), t_end, 60)
    bid = 107.45
    data = {"m1": m1, "m5": m5, "m15": m15, "m30": m5, "h1": m15,
            "h4": m15,
            "info": {"point": 0.01, "spread_points": 12, "digits": 2,
                     "bid": bid, "ask": bid + 0.12},
            "point": 0.01, "delta": {"buy": 10.0, "sell": 4.0}}
    return data, bid


def mirror_bars(bars, center=105.0):
    """Cermin harga: BUY breakout -> SELL breakdown (sah OHLC)."""
    out = {}
    for k in ("open", "high", "low", "close"):
        out[k] = [2.0 * center - float(v) for v in bars[k]]
    out["high"], out["low"] = [2.0 * center - v for v in bars["low"]], \
                              [2.0 * center - v for v in bars["high"]]
    out["time"] = list(bars["time"])
    out["tick_volume"] = list(bars["tick_volume"])
    return out


def market_sell():
    """Return (data, bid) -- SELL breakdown valid (cermin market())."""
    data, bid = market()
    c = 105.0
    for tf in ("m1", "m5", "m15", "m30", "h1", "h4"):
        data[tf] = mirror_bars(data[tf], c)
    bid2 = 2.0 * c - (bid + 0.12)             # cermin ask (entry SELL=bid)
    data["info"] = {"point": 0.01, "spread_points": 12, "digits": 2,
                    "bid": bid2 - 0.12, "ask": bid2}
    data["delta"] = {"buy": 4.0, "sell": 10.0}
    return data, bid2
