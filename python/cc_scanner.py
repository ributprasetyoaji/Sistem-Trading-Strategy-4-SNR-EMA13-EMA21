"""Multi-pair scanner untuk Python Command Center.

Untuk SETIAP symbol, dari data MT5 (M15/M5/M1) dihitung:
  regime (TREND/RANGE), 6 komponen konfluensi (0-100), skor akhir,
  level SL struktural, dan sniper M1 (micro break) sebagai konfirmasi akhir.

Bobot komponen (total 100):
  trend 20 | orderflow 20 | volume/HVN 20 | structure 15 | momentum 15 | liquidity 10
Semua kuantitatif; tidak ada input manual.
"""
from __future__ import annotations

import math

WEIGHTS = {"trend": 20, "orderflow": 20, "volume": 20,
           "structure": 15, "momentum": 15, "liquidity": 10}
COMPONENT_NAMES = [("structure", "Market Structure"), ("liquidity", "Liquidity (SMC)"),
                   ("trend", "Trend Filter"), ("momentum", "Momentum"),
                   ("volume", "Volume / HVN"), ("orderflow", "Order Flow")]


# ---------------------------------------------------------------------------
# indikator dasar
# ---------------------------------------------------------------------------
def ema(vals, n):
    if not vals:
        return 0.0
    k = 2.0 / (n + 1)
    e = vals[0]
    for v in vals[1:]:
        e = v * k + e * (1 - k)
    return e


def ema_series(vals, n):
    out = []
    if not vals:
        return out
    k = 2.0 / (n + 1)
    e = vals[0]
    for v in vals:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(vals, n=14):
    if len(vals) < n + 1:
        return 50.0
    gains = losses = 0.0
    for i in range(-n, 0):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100.0 - 100.0 / (1.0 + rs)


def atr14(h, l, c, n=14):
    if len(c) < n + 1:
        return (max(h) - min(l)) / 4.0 if c else 0.0
    trs = []
    for i in range(-n, 0):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        trs.append(tr)
    return sum(trs) / len(trs)


def pivots(h, l, lb=3, last=60):
    """Index swing high/low sederhana (fractal lookback=lb)."""
    sh, sl = [], []
    seg = range(lb, len(h) - lb)
    for i in list(seg)[-last:]:
        if h[i] == max(h[i - lb:i + lb + 1]):
            sh.append(i)
        if l[i] == min(l[i - lb:i + lb + 1]):
            sl.append(i)
    return sh, sl


def volume_profile_hvn(closes, vols, bins=30, top=3, price=None):
    """Zona volume tertinggi (HVN) dari histogram harga. Return list zona.

    Volume seri (tie) dipecahkan dengan memilih bin terdekat ke harga kini.
    """
    if not closes:
        return []
    lo, hi = min(closes), max(closes)
    if hi <= lo:
        return [{"lo": lo, "hi": hi, "vol": sum(vols), "center": lo}]
    bw = (hi - lo) / bins
    bv = [0.0] * bins
    for p, v in zip(closes, vols):
        b = min(int((p - lo) / bw), bins - 1)
        bv[b] += v
    ref = price if price is not None else closes[-1]
    order = sorted(range(bins),
                   key=lambda i: (bv[i], -abs(lo + (i + 0.5) * bw - ref)),
                   reverse=True)[:top]
    zones = []
    for i in order:
        if bv[i] <= 0:
            continue
        zones.append({"lo": lo + i * bw, "hi": lo + (i + 1) * bw,
                      "vol": bv[i], "center": lo + (i + 0.5) * bw})
    zones.sort(key=lambda z: z["center"])
    return zones


def clamp(x, a=0.0, b=100.0):
    return max(a, min(b, x))


# ---------------------------------------------------------------------------
# analisis per symbol
# ---------------------------------------------------------------------------
def m15_rejection_side(m15, cfg, eps=1e-9):
    """v3.34: deteksi candle M15 REJECTION VALID pada bar terakhir.
    'BEAR' = sumbu atas panjang (harga ditolak dari atas; rawan turun),
    'BULL' = sumbu bawah panjang (harga ditolak dari bawah; rawan naik),
    None   = bukan candle rejection. Syarat valid: sumbu >= wick_body_min x
    body DAN sumbu >= wick_range_pct x range candle."""
    if not m15 or len(m15.get("close") or []) < 1:
        return None
    o = float(m15["open"][-1]); h = float(m15["high"][-1])
    l = float(m15["low"][-1]);  c = float(m15["close"][-1])
    rng = h - l
    if rng <= eps:
        return None
    body = abs(c - o)
    up = h - max(o, c)          # sumbu atas
    dn = min(o, c) - l          # sumbu bawah
    kb = float(cfg.get("rej_wick_body_min", 2.0))
    pr = float(cfg.get("rej_wick_range_pct", 0.5))
    if up >= kb * max(body, eps) and up >= pr * rng:
        return "BEAR"
    if dn >= kb * max(body, eps) and dn >= pr * rng:
        return "BULL"
    return None


def rejection_block(side, rej_side, e20, e50):
    """v3.34: larang entry MELAWAN candle rejection M15 yang valid + arah EMA.
    - BUY dilarang bila rejection BEAR valid DAN EMA turun (e20 < e50)
    - SELL dilarang bila rejection BULL valid DAN EMA naik (e20 > e50)
    Berlaku utk entry baru MAUPUN re-entry. Return alasan blok / None."""
    if side == "BUY" and rej_side == "BEAR" and e20 < e50:
        return ("REJECTION_M15: candle rejection bearish valid + EMA turun "
                "-> entry/re-entry BUY dilarang")
    if side == "SELL" and rej_side == "BULL" and e20 > e50:
        return ("REJECTION_M15: candle rejection bullish valid + EMA naik "
                "-> entry/re-entry SELL dilarang")
    return None


def analyze(symbol, data, cfg):
    """data = {"m15": rates, "m5": rates, "m1": rates, "delta": {"buy","sell"}}.

    Return dict hasil lengkap (komponen oriented ke sinyal terpilih).
    """
    m15, m5, m1 = data.get("m15"), data.get("m5"), data.get("m1")
    if not m15 or len(m15["close"]) < 60:
        return None
    c15, h15, l15 = m15["close"], m15["high"], m15["low"]
    v15 = m15["tick_volume"]
    a = atr14(h15, l15, c15, cfg.get("atr_period", 14)) or 1e-9
    price = c15[-1]

    # regime
    e20, e50 = ema(c15, 20), ema(c15, 50)
    sep_atr = (e20 - e50) / a
    regime = "TREND" if abs(sep_atr) > 0.35 else "RANGE"
    regime_dir = "UP" if sep_atr > 0 else ("DOWN" if sep_atr < 0 else "-")
    # seberapa "terlambat" harga vs EMA20 (positif = sudah jauh di atas rata2)
    ext_atr = (price - e20) / a

    # structure (swing)
    sh, sl_ = pivots(h15, l15, lb=3, last=80)
    hh = len(sh) >= 2 and h15[sh[-1]] > h15[sh[-2]]
    hl = len(sl_) >= 2 and l15[sl_[-1]] > l15[sl_[-2]]
    lh = len(sh) >= 2 and h15[sh[-1]] < h15[sh[-2]]
    ll = len(sl_) >= 2 and l15[sl_[-1]] < l15[sl_[-2]]
    struct_bull = 100.0 if (hh and hl) else (60.0 if (hh or hl) else 25.0)
    struct_bear = 100.0 if (lh and ll) else (60.0 if (lh or ll) else 25.0)

    # trend component (oriented: >50 = bull)
    trend_o = clamp(50.0 + sep_atr * 50.0)

    # momentum (RSI M5, oriented sama)
    r = rsi(m5["close"] if m5 else c15, 14)
    mom_o = clamp((r - 50.0) * 5.0 + 50.0)

    # volume / HVN proximity
    look = min(cfg.get("hvn_bars", 200), len(c15))
    zones = volume_profile_hvn(c15[-look:], v15[-look:], bins=30, top=3,
                               price=price)
    dist_atr = 9.9
    near_zone = None
    for z in zones:
        d = 0.0 if z["lo"] <= price <= z["hi"] else min(abs(price - z["lo"]),
                                                        abs(price - z["hi"]))
        d /= a
        if d < dist_atr:
            dist_atr = d
            near_zone = z
    prox = cfg.get("zone_proximity_atr", 0.20)
    vol_base = clamp(100.0 * (1.0 - dist_atr / prox)) if dist_atr < 9 else 0.0
    vol_o = clamp(50.0 + vol_base * 0.5)  # oriented netral kalau tidak dekat zona

    # order flow dari delta agresor
    d = data.get("delta") or {}
    tot = (d.get("buy", 0.0) + d.get("sell", 0.0)) or 1.0
    ratio = (d.get("buy", 0.0) - d.get("sell", 0.0)) / tot   # -1..1
    of_o = clamp(50.0 + ratio * 50.0)

    # liquidity sweep: tusuk swing lalu tutup balik (oriented)
    liq_bull = liq_bear = 50.0
    if len(sl_) >= 1:
        prev_low = l15[sl_[-1]]
        wick = min(l15[-3:])
        if wick < prev_low - 0.05 * a and price > prev_low:
            liq_bull = 100.0
    if len(sh) >= 1:
        prev_high = h15[sh[-1]]
        wick = max(h15[-3:])
        if wick > prev_high + 0.05 * a and price < prev_high:
            liq_bear = 100.0

    # skor dua arah
    comp_buy = {"structure": struct_bull, "liquidity": liq_bull,
                "trend": trend_o, "momentum": mom_o,
                "volume": vol_o, "orderflow": of_o}
    comp_sell = {"structure": struct_bear, "liquidity": liq_bear,
                 "trend": 100.0 - trend_o, "momentum": 100.0 - mom_o,
                 "volume": vol_o, "orderflow": 100.0 - of_o}
    score_buy = sum(comp_buy[k] * w for k, w in WEIGHTS.items()) / 100.0
    score_sell = sum(comp_sell[k] * w for k, w in WEIGHTS.items()) / 100.0
    side = "BUY" if score_buy >= score_sell else "SELL"
    score = max(score_buy, score_sell)
    comp = comp_buy if side == "BUY" else comp_sell

    # SL struktural
    if side == "BUY":
        swing = min(l15[-12:]) if len(l15) >= 12 else min(l15)
        sl_price = swing - 0.5 * a
    else:
        swing = max(h15[-12:]) if len(h15) >= 12 else max(h15)
        sl_price = swing + 0.5 * a
    point = data.get("point") or a / 10.0 or 1e-9
    sl_points = abs(price - sl_price) / point
    tp_points = sl_points * cfg.get("tp_r", 1.5)

    # normalisasi tipe -> python natives (numpy dari MT5 tidak json-able)
    tp_price = price + (tp_points * point if side == "BUY"
                        else -tp_points * point)
    price, a, point = float(price), float(a), float(point)
    sl_price = float(sl_price)
    sl_points, tp_points = float(sl_points), float(tp_points)
    dist_atr, r, ratio = float(dist_atr), float(r), float(ratio)
    score_buy, score_sell = float(score_buy), float(score_sell)
    score = float(score)
    comp = {k: float(v) for k, v in comp.items()}
    comp_buy = {k: float(v) for k, v in comp_buy.items()}
    comp_sell = {k: float(v) for k, v in comp_sell.items()}

    # v3.34: entry/re-entry dilarang melawan rejection M15 valid + arah EMA
    rej_side = m15_rejection_side(m15, cfg)
    rej_blocked = (rejection_block(side, rej_side, e20, e50)
                   if cfg.get("rej_filter_enabled", True) else None)

    return {
        "symbol": symbol, "price": price, "atr": a, "point": point,
        "sig_time": int(m15["time"][-1]),  # v3.33: bar M15 pembentuk sinyal
        "rej_side": rej_side, "rej_blocked": rej_blocked,
        "regime": regime, "regime_dir": regime_dir,
        "side": side, "score": round(score, 1),
        "score_buy": round(score_buy, 1), "score_sell": round(score_sell, 1),
        "components": {k: round(v, 1) for k, v in comp.items()},
        "components_buy": {k: round(v, 1) for k, v in comp_buy.items()},
        "components_sell": {k: round(v, 1) for k, v in comp_sell.items()},
        "sl_price": sl_price, "tp_price": tp_price,
        "sl_points": sl_points, "tp_points": tp_points,
        "zone": near_zone, "dist_atr": round(dist_atr, 3),
        "ext_atr": round(float(ext_atr), 3),
        "rsi_m5": round(r, 1), "delta_ratio": round(ratio, 3),
        "spark_ohlc": [(int(m15["time"][i]), float(m15["open"][i]),
                        float(m15["high"][i]), float(m15["low"][i]),
                        float(m15["close"][i]))
                       for i in range(max(0, len(c15) - 60), len(c15))],
    }


# ---------------------------------------------------------------------------
# sniper M5 (v3.38): gerbang momentum M5 SEBELUM sniper M1
# ---------------------------------------------------------------------------
def m5_zone_gate(side, m5, cfg):
    """v3.41: SNIPER M5 = SCAN ZONA HH/HL SUPPORT-RESISTANCE.
    Entry tidak boleh dilakukan di posisi yang BURUK secara struktur:

    SELL (tren turun):
      x DILARANG di dekat LEMBAH/HL lama (harga terlalu rendah; riskan
        bounce dari support). Dua jalan keluar agar boleh entry:
        (a) BREAKOUT VALID: close menembus lembah lama ke bawah dengan
            jarak > brk_atr x ATR, ATAU
        (b) TUNGGU NAIK: harga naik >= pull_atr x ATR dari lembah DAN
            sudah membentuk HH valid (swing high baru > swing high lama)
            lalu candle M5 turun (mulai turun) -> entry di kebangkitan.
    BUY (cermin): x dekat puncak/HH lama kecuali breakout valid ke atas
        atau sudah turun & membentuk LL valid + candle M5 naik.

    Return (ok, why). ok=False -> entry ditahan (SNIPER_WAIT).
    """
    need = max(16, int(cfg.get("sniper_m5_need_bars", 12)))
    if m5 is None or len(m5.get("close") or []) < need:
        return True, "m5_data_kurang"          # fail-open: biarkan M1 yang nilai
    h, l, c = m5["high"], m5["low"], m5["close"]
    a = atr14(h, l, c, 14)
    if not a or a <= 0:
        return True, "m5_atr_nol"
    lb = int(cfg.get("zone_pivot_lb", 3))
    sh, sl = pivots(h, l, lb=lb, last=60)
    brk_atr = float(cfg.get("zone_breakout_atr", 0.30))
    near_atr = float(cfg.get("zone_near_atr", 0.40))
    pull_atr = float(cfg.get("zone_pull_atr", 0.60))

    if side == "SELL":
        if not sl:
            return True, "m5_tanpa_lembah"
        v_old = float(l[sl[-1]])               # HL/lembah support lama
        cur = float(c[-1])
        near_v = cur - v_old <= near_atr * a   # terlalu dekat lembah?
        breakout = (v_old - cur) > brk_atr * a  # sudah menembus ke bawah?
        if near_v and not breakout:
            # opsi (b): naik dulu & valid HH lalu candle turun
            rose = (float(max(h[-12:])) - v_old) >= pull_atr * a
            hh_ok = (len(sh) >= 2
                     and float(h[sh[-1]]) > float(h[sh[-2]]) + 1e-9)
            falling = float(c[-1]) < float(m5["open"][-1])
            if rose and hh_ok and falling:
                return True, "m5_rebound_hh_sell"
            return False, "tunggu_breakout_lembah_atau_rebound_hh"
        return True, ("m5_breakout_lembah" if breakout else "m5_posisi_aman_sell")

    # BUY (cermin)
    if not sh:
        return True, "m5_tanpa_puncak"
    p_old = float(h[sh[-1]])
    cur = float(c[-1])
    near_p = p_old - cur <= near_atr * a
    breakout = (cur - p_old) > brk_atr * a
    if near_p and not breakout:
        dropped = (p_old - float(min(l[-12:]))) >= pull_atr * a
        ll_ok = (len(sl) >= 2
                 and float(l[sl[-1]]) < float(l[sl[-2]]) - 1e-9)
        rising = float(c[-1]) > float(m5["open"][-1])
        if dropped and ll_ok and rising:
            return True, "m5_dip_ll_buy"
        return False, "tunggu_breakout_puncak_atau_dip_ll"
    return True, ("m5_breakout_puncak" if breakout else "m5_posisi_aman_buy")


def _sniper_zone_reject(res, side, cur, m1, a, cfg):
    """v4.23 (laporan user "sniper buta zona rejection/SNR"): gerbang
    zona SNR LAWAN utk sniper M1.  Zona lawan diambil dari paket exec
    strategi (ex["opp"] = RESISTANCE terdekat utk BUY / SUPPORT utk
    SELL, hasil deteksi zona M15 asli).

    BUY : zona lawan = RESISTANCE di atas.  Bila harga menempel/di
          dalam zona (jarak <= sniper_zone_buf_atr x ATR) WAJIB ada
          bukti rejection M1 (wick atas menembus tepi zona lalu close
          kembali di bawahnya) -- kalau tidak, entry DITAHAN.  Harga
          sudah di atas zona = breakout valid (boleh).
    SELL: cermin dgn SUPPORT di bawah.

    Return (ok, why).  ok=False -> entry ditahan (SNIPER_WAIT), bukan
    blokir permanen -- siklus berikutnya dicek lagi.  Fail-open bila
    paket exec tidak punya zona lawan."""
    ex = (res or {}).get("exec") or {}
    zn = ex.get("opp") or {}
    try:
        lo, hi = float(zn.get("lo") or 0.0), float(zn.get("hi") or 0.0)
    except Exception:
        return True, "zona_lawan_tak_valid"
    if lo <= 0 or hi <= 0 or hi <= lo:
        return True, "tanpa_zona_lawan"
    buf = float(cfg.get("sniper_zone_buf_atr", 0.45)) * float(a or 0.0)
    rej_lb = max(1, int(cfg.get("sniper_rej_lookback", 3)))
    wf = float(cfg.get("sniper_rej_wick_frac", 0.5))
    o, h, l, c = m1["open"], m1["high"], m1["low"], m1["close"]

    def _rej_buy():
        for i in range(max(0, len(c) - rej_lb), len(c)):
            rng = max(1e-12, float(h[i]) - float(l[i]))
            upper = float(h[i]) - max(float(o[i]), float(c[i]))
            if (float(h[i]) >= lo - 0.1 * (a or 0.0)
                    and upper >= wf * rng and float(c[i]) < lo):
                return True
        return False

    def _rej_sell():
        for i in range(max(0, len(c) - rej_lb), len(c)):
            rng = max(1e-12, float(h[i]) - float(l[i]))
            lower = min(float(o[i]), float(c[i])) - float(l[i])
            if (float(l[i]) <= hi + 0.1 * (a or 0.0)
                    and lower >= wf * rng and float(c[i]) > hi):
                return True
        return False

    if side > 0:
        if cur > hi:
            return True, "breakout_di_atas_zona_lawan"
        if lo - cur > buf:
            return True, "zona_lawan_masih_jauh"
        if _rej_buy():
            return True, "entry_rejeksi_resistensi"
        return False, "tunggu_rejeksi_resistensi"
    if cur < lo:
        return True, "breakout_di_bawah_zona_lawan"
    if cur - hi > buf:
        return True, "zona_lawan_masih_jauh"
    if _rej_sell():
        return True, "entry_rejeksi_support"
    return False, "tunggu_rejeksi_support"


def sniper_m5(res, m5, cfg):
    """ALUR SNIPER 3 TAHAP (v3.38/v3.39):
      M15 sinyal valid -> turun ke M5 cari MOMENTUM (minim floating minus)
      -> turun ke M1 cari TITIK ENTRY pas & searah.
    Tahap M5: wajib momentum searah sebelum M1 mencari momen pullback:
      BUY : close M5 > EMA8 M5  DAN candle M5 terakhir bullish (c>o)
      SELL: close M5 < EMA8 M5  DAN candle M5 terakhir bearish (c<o)
    Return (ok, why). Tidak ok -> entry DITAHAN (SNIPER_WAIT), bukan blokir.
    """
    need = max(12, int(cfg.get("sniper_m5_need_bars", 12)))
    if m5 is None or len(m5.get("close") or []) < need:
        return False, "m5_data_kurang"
    o, c = m5["open"], m5["close"]
    e8 = ema(c[-40:] if len(c) >= 40 else c, 8)
    msc = float(cfg.get("sniper_m5_min_score", 55.0))
    if float(res.get("score", 0.0)) < msc:
        return False, "tunggu_skor_m15_turun"
    # v3.41: scan zona HH/HL support-resistance — jangan entry di lembah
    # (untuk SELL) / puncak (untuk BUY) kecuali breakout valid atau sudah
    # rebound/dip + struktur baru valid
    zok, zwhy = m5_zone_gate(res["side"], m5, cfg)
    if not zok:
        return False, zwhy
    if res["side"] == "BUY":
        if c[-1] <= e8:
            return False, "tunggu_m5_di_atas_ema8"
        if c[-1] <= o[-1]:
            return False, "tunggu_candle_m5_bullish"
        return True, "m5_momentum_buy"
    if c[-1] >= e8:
        return False, "tunggu_m5_di_bawah_ema8"
    if c[-1] >= o[-1]:
        return False, "tunggu_candle_m5_bearish"
    return True, "m5_momentum_sell"


# ---------------------------------------------------------------------------
# sniper M1 "PULLBACK-RESUME" (v3.08)
# ---------------------------------------------------------------------------
def sniper_m1(res, m1, cfg, delta=None):
    """Sinyal M15 kasih ARAH; M1 tidak memblokir, tapi MENAHAN entry sampai
    momen momentum pas: harga menarik napas (pullback) lalu momentum balik
    searah sinyal -> entry. Anti "buy di HH / sell di LL".

    Return (ok, why). why menjelaskan KAPAN akan entry (hold reason).
    """
    need = cfg.get("sniper_need_bars", 24)
    if m1 is None or len(m1["close"]) < need:
        return False, "m1_data_kurang"
    o, h, l, c = m1["open"], m1["high"], m1["low"], m1["close"]
    cur = c[-1]
    a = atr14(h, l, c, 14) or (((max(h[-20:]) - min(l[-20:])) / 4.0) or 1e-9)
    e8 = ema(c[-40:] if len(c) >= 40 else c, 8)
    d = delta or {}
    buy_flow = d.get("buy", 0.0) >= d.get("sell", 0.0)
    sell_flow = d.get("sell", 0.0) >= d.get("buy", 0.0)
    max_ext = cfg.get("entry_max_extension_atr", 1.2)
    pull_min = cfg.get("pull_min_atr", 0.15) * a

    if res["side"] == "BUY":
        pullback = max(h[-15:]) - cur          # seberapa jauh menarik napas
        if pullback < pull_min:
            return False, "tunggu_pullback"    # masih menempel di HH -> jangan beli
        if pullback > max_ext * a:
            return False, "pullback_terlalu_dalam"  # momentum balik habis
        if cur <= e8 or c[-1] <= o[-1]:
            return False, "tunggu_momentum_buy"
        if not buy_flow:
            return False, "tunggu_delta_buy"
        # v4.23: sadar zona SNR lawan -- jangan entry menempel zona
        # tanpa bukti rejection (keluhan user "buta zona")
        zok, zwhy = _sniper_zone_reject(res, 1, cur, m1, a, cfg)
        if not zok:
            return False, zwhy
        return True, "pullback_resume_buy"

    pullback = cur - min(l[-15:])
    if pullback < pull_min:
        return False, "tunggu_pullback"        # masih menempel di LL -> jangan jual
    if pullback > max_ext * a:
        return False, "pullback_terlalu_dalam"
    if cur >= e8 or c[-1] >= o[-1]:
        return False, "tunggu_momentum_sell"
    if not sell_flow:
        return False, "tunggu_delta_sell"
    # v4.23: sadar zona SNR lawan (cermin BUY)
    zok, zwhy = _sniper_zone_reject(res, -1, cur, m1, a, cfg)
    if not zok:
        return False, zwhy
    return True, "pullback_resume_sell"


# ---------------------------------------------------------------------------
# TP struktural v3.16: BODY lilin SNR/HH-HL terdekat (BUKAN wick) + RR bersih
# ---------------------------------------------------------------------------
def structural_tp(side, entry, sl_dist, tp_price, bars, min_rr=0.6,
                  body_pos=0.4, cost_dist=0.0):
    """TP dipotong ke BODY lilin SNR/HH-HL TERDEKAT di depan entry.

    v3.08 lama memakai high/low (WICK) lilin swing -> TP jarang kejemput
    karena harga sering ditolak (candle rejection) sebelum menyentuh ujung
    wick. Sekarang level diambil dari BATANG lilin (open/close):
      BUY  -> lilin swing-high (resistensi) di atas entry;
              cand = body_lo + body_pos*(body_hi-body_lo)
      SELL -> lilin swing-low (support) di bawah entry;
              cand = body_hi - body_pos*(body_hi-body_lo)
    body_pos 0.4 = "di batang, mendekati tengah batang" (sering kejemput).

    Syarat pemakaian: lebih dekat dari TP hard (1.0R) DAN RR bersih
    (gain - cost_dist, cost = spread+komisi) >= min_rr x jarak SL.
    Return harga TP terpakai (= tp_price bila struktur tidak membantu).
    """
    try:
        o, h, l, c = bars["open"], bars["high"], bars["low"], bars["close"]
        n = len(h)
        if n < 8 or sl_dist <= 0:
            return tp_price
        stop = n - 2                      # 2 lilin terakhir masih berjalan
        if stop < 6:
            return tp_price
        look = min(24, stop)
        w0 = max(2, stop - look)
        cands = []
        for i in range(w0, stop - 2):
            blo, bhi = min(o[i], c[i]), max(o[i], c[i])
            if side == "BUY":
                ph = (h[i] >= h[i-1] and h[i] >= h[i-2]
                      and h[i] >= h[i+1] and h[i] >= h[i+2])
                if ph:
                    cands.append(blo + body_pos * (bhi - blo))
            else:
                pl = (l[i] <= l[i-1] and l[i] <= l[i-2]
                      and l[i] <= l[i+1] and l[i] <= l[i+2])
                if pl:
                    cands.append(bhi - body_pos * (bhi - blo))
        # HH/LL jendela ikut jadi kandidat (walau bukan pivot ketat)
        j = (max(range(w0, stop), key=lambda i: h[i]) if side == "BUY"
             else min(range(w0, stop), key=lambda i: l[i]))
        blo, bhi = min(o[j], c[j]), max(o[j], c[j])
        cands.append(blo + body_pos * (bhi - blo) if side == "BUY"
                     else bhi - body_pos * (bhi - blo))
        tp_dist = abs(tp_price - entry)
        best = None
        for cand in cands:
            if side == "BUY":
                if not (entry < cand <= entry + tp_dist):
                    continue
                gain = cand - entry
            else:
                if not (entry > cand >= entry - tp_dist):
                    continue
                gain = entry - cand
            if gain - cost_dist < min_rr * sl_dist:
                continue
            if best is None or abs(cand - entry) < abs(best - entry):
                best = cand
        return best if best is not None else tp_price
    except Exception:
        return tp_price


def zone_touch(side, entry, price, bars, atr_k=0.2):
    """v3.25 SYSTEM PINTAR: apakah harga SEDANG menyentuh zona BODY
    SNR/HH-HL (lilin pivot) di depan entry. Baris lilin pivot = high/low
    tertinggi/terendah vs 2 tetangga kiri-kanan. Zona = batang (bukan wick).

    BUY  : zona pivot-high di ATAS entry; sentuh bila blo <= price
           <= bhi + atr_k*ATR (belum ditembus jauh -> rawan rejection).
    SELL : cermin dgn pivot-low di BAWAH entry.

    Return (touched, zone_price) — zone_price = batas zona terdekat.
    """
    try:
        o, h, l, c = bars["open"], bars["high"], bars["low"], bars["close"]
        n = len(h)
        if n < 8:
            return False, 0.0
        stop = n - 2
        if stop < 6:
            return False, 0.0
        atr = atr14(h, l, c, 14) or 0.0
        buf = atr_k * atr
        look = min(40, stop)
        w0 = max(2, stop - look)
        for i in range(w0, stop - 2):
            if side == "BUY":
                if not (h[i] >= h[i-1] and h[i] >= h[i-2]
                        and h[i] >= h[i+1] and h[i] >= h[i+2]):
                    continue
                blo, bhi = min(o[i], c[i]), max(o[i], c[i])
                if blo > entry and blo <= price <= bhi + buf:
                    return True, blo
            else:
                if not (l[i] <= l[i-1] and l[i] <= l[i-2]
                        and l[i] <= l[i+1] and l[i] <= l[i+2]):
                    continue
                blo, bhi = min(o[i], c[i]), max(o[i], c[i])
                if bhi < entry and bhi >= price >= blo - buf:
                    return True, bhi
        return False, 0.0
    except Exception:
        return False, 0.0


def tp_net_check(side, entry, tp, sl_dist, cost_dist, min_rr=0.6):
    """RR BERSIH v3.16: (jarak TP - spread - komisi) / jarak SL.

    Return (ok, rr). ok=False -> TP tidak layak (profit bersih kurang),
    trade di-SKIP agar "RR terjaga" seperti keinginan user."""
    try:
        if sl_dist <= 0:
            return False, 0.0
        gain = (tp - entry) if side == "BUY" else (entry - tp)
        rr = (gain - cost_dist) / sl_dist
        return (rr >= min_rr), round(rr, 2)
    except Exception:
        return False, 0.0
