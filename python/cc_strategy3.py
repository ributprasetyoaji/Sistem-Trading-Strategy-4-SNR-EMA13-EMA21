# -*- coding: utf-8 -*-
"""
RBT FX -- STRATEGY 3 :: RBT FINGERPRINT TRADING SYSTEM (v1 blueprint)
=====================================================================
Implementasi blueprint user (RBT_Fingerprint_Trading_System_Blueprint.txt)
di atas infrastruktur Command Center (dashboard, MT4/MT5 bridge, risk
manager, rekap harian WIB).

Peran timeframe (blueprint s.2):
  H1  -> regime/context (TIDAK memicu entry)
  M15 -> setup utama: zona S/R, struktur, fingerprint, skor setup
  M5  -> momentum development (timing, bukan strategi mandiri)
  M1  -> precision entry trigger

Prinsip inti (blueprint s.63):
  NO ZONE -> NO TRADE.  QUALITY > QUANTITY.
  +1R -> SL ke BEP+ ;  +2R -> trailing aktif (winner dibiarkan jalan);
  Breakout valid = CLOSE melewati batas zona (wick saja BUKAN breakout);
  Maks 5 posisi, 1 per pair, re-entry maks per zona, daily loss 10% lock
  (via engine risk).

FUNGSI YANG DIPANGGIL ENGINE (kontrak):
  evaluate(symbol, data, k, st)            -> dict hasil scan (shape S2)
  validate_execution(...)                  -> (ok, why, sl, tp, keep)
  ATRTrail / atr_at / atr_stop_improves    -> manajemen posisi (BEP/trail)
  s2_cfg / Strategy2State / spread_limit   -> infrastruktur
Semua parameter ada di cc_config.py blok "s3".  TANPA future leakage:
hanya bar CLOSED yang dipakai keputusan (index -2 = bar closed terakhir).
"""
import hashlib
import json
import math
import os
import time

# ===========================================================================
# [0] INDIKATOR MURNI (EMA / TR / ATR -- konvensi bar -1 berjalan, -2 closed)
# ===========================================================================
DEFAULTS = {
    "ema_fast": 13, "ema_slow": 21, "atr_period": 14,
    # H1 regime
    "regime_ema_sep_min_atr": 0.10, "regime_slope_lookback": 6,
    # zona
    "zone_swing_strength": 3, "zone_width_atr": 0.50,
    "zone_max_age_bars": 200, "zone_touch_min_exit_atr": 0.60,
    "zone_max_priority_interactions": 3, "zone_max_attempts": 2,
    "zone_min_strength": 55.0, "zone_oppose_buffer_atr": 0.30,
    "zone_invalidate_atr": 0.25,
    # v4.12 ANTI-ZONA-PALSU (laporan user: candle rejection kecil dianggap
    # zona SNR/HH-HL -> blokir 2R salah): wick rejeksi pivot minimal,
    # kaki impuls minimal, pivot selevel digabung, dan hanya zona
    # TERUJI yang boleh memblokir.
    "zone_min_wick_atr": 0.35,       # wick rejeksi < 0.35 ATR = bukan zona
    "zone_min_leg_atr": 0.60,        # kaki impuls masuk pivot minimal
    "zone_merge_atr": 0.60,          # pivot selevel <= 0.6 ATR digabung
    "zone_block_requires_touch": 1,  # zona 0 sentuhan TIDAK memblokir 2R
    "zone_block_min_quality": 40.0,  # kualitas minimum zona pemblokir
    "ema_cross_lookback": 5,         # EMA13/21 M15 cross dlm 5 bar = valid
    "w_ema_cross": 8.0,              # bonus skor tren valid (cross EMA)
    "bep_at_r": 1.0,                 # v4.25 (rumus user): floating +1R
    "bep_offset_r": 0.0,             #   SEBELUM TP1 -> SL geser ke BEP
                                     #   (entry + offset R; 0 = tepat BEP)
    "ema_rev_enable": 1,             # v4.24 (rumus user): reversal EMA =
    "ema_rev_lookback": 5,           #   SKIP BUY bila EMA13 dr atas turun
    "ema_rev_was_gap_atr": 0.10,     #   menuju/sudah cross EMA21 + candle
    "ema_rev_gap_atr": 0.15,         #   di bawah keduanya (cermin utk SELL)
    "adx_filter": 1,                 # v4.26 (permintaan user): entry hanya
    "adx_min": 25.0,                 #   saat ADX M15 > 25 (tren kuat);
    "adx_period": 14,
    "msf_enable": 1, "msf_room_atr": 1.0,
    "ml_enable": 1, "ml_min_p": 0.30, "ml_window": 120,                #   ADX <= 25 = sideways -> SKIP
    "zone_near_pad_atr": 0.70,       # dianggap "di/dekat zona" (no-chase
                                     #   final tetap di validate_execution)
    # fingerprint
    "fp_sequence_len": 5, "fp_similarity_candidate": 80.0,
    "fp_min_sample_size": 12, "fp_history_bars": 12000,
    "fp_outcome_horizon": 24, "fp_r_atr": 1.0,
    # riwayat dalam (blueprint s.3): default ~1 tahun M15; naikkan
    # hist_bars ke 105000 utk ~3 tahun (AUTO: berhenti saat broker
    # kehabisan; TIDAK pernah mengarang data)
    "hist_bars": 35040, "hist_batch": 1500, "hist_max_sec": 10.0,
    "hist_refresh_hours": 6.0,
    # setup score
    "min_setup_score": 70.0,
    "w_zone": 30.0, "w_structure": 20.0, "w_ema": 15.0,
    "w_fingerprint": 25.0, "w_regime": 10.0,
    # momentum M5 / trigger M1
    "m5_min_body_atr": 0.60, "m1_trigger_bars": 12,
    "m1_break_atr": 0.15,
    # SL / TP / chase
    "sl_structure_buffer_atr": 0.35, "min_sl_atr_ratio": 0.45,
    "max_sl_atr_ratio": 2.5, "base_rr": 2.0,
    "max_entry_distance_atr": 1.0,
    "setup_expiration_bars": 8,
    # posisi / trailing
    "max_baskets": 5,                                 # MAKS 5 posisi
    "max_total_open_risk_pct": 15.25,  # v4.14: 5 x 3% + toleransi
    "bep_trigger_r": 1.0, "bep_buffer_r": 0.10,
    "trail_trigger_r": 2.0, "trail_back_r": 1.0, "trail_hard_cap_r": 10.0,
    "tp_rr": 1.0,                     # v4.27 (user): TP1 = 1x jarak SL;
                                      #   0 = off (fallback target uang)
    "tp1_rr": 1.0,                    # v4.27 (user): TP1 = 1R (tutup 75%)
    "tp1_close_pct": 75.0,            # v4.12 persen ditutup di TP1
    "tp2_rr": 4.0,                    # v4.12 sisa posisi lanjut ke TP2 = 4R
    "tp2_trail_step_r": 0.2,          # v4.28 (user) SL trailing tiap 0.2R
    "tp1_lock_r": 0.0,                # v4.28 (user) setelah TP1: SL = BEP
    "min_entry_lot": 0.04,            # v4.16 entry wajib lot >= 0.04
    "cooldown_min": 10,               # jeda re-entry per pair
    "dq_stale_sec": 2700,            # 0=off; feed basi >45 mnt -> tolak
    "risk_per_trade_percent": 3.0,    # v4.14 (user): 3% per entry
    "warmup_sec": 20,    # v4.23: entry cepat setelah reload (dulu 150)
    # spread per pair (POINT) + default
    "spread_points": {"XAUUSD": 250, "XAGUSD": 50, "BTCUSD": 2500,
                      "USTEC": 150, "US100": 150, "NAS100": 150},
    "spread_points_default": 2500,
    # fallback risiko trail bila baseline SL struktur hilang (x ATR M5)
    "sl_atr": 1.2,
}


def s2_cfg(cfg):
    """Gabungkan default dgn override cc_config['s3'] (STRATEGY 3)."""
    d = dict(DEFAULTS)
    d.update(cfg.get("s3") or {})
    return d


def ema_series(vals, n):
    out = []
    if not vals:
        return out
    k = 2.0 / (n + 1)
    e = float(vals[0])
    for v in vals:
        e = float(v) * k + e * (1 - k)
        out.append(e)
    return out


def ema_at(rates, period):
    c = [float(v) for v in (rates.get("close") or [])]
    if len(c) < period + 2:
        return None
    s = ema_series(c[:-1], period)     # bar closed saja
    return s[-1] if s else None


def tr_series(rates):
    h = [float(v) for v in (rates.get("high") or [])]
    l = [float(v) for v in (rates.get("low") or [])]
    c = [float(v) for v in (rates.get("close") or [])]
    n = min(len(h), len(l), len(c))
    trs = []
    for i in range(n):
        if i == 0:
            trs.append(h[i] - l[i])
        else:
            trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]),
                           abs(l[i] - c[i - 1])))
    return trs


def atr_at(rates, period=14, wilder=True):
    """ATR pada bar TERAKHIR CLOSED (shift 1) -> float atau None."""
    tr = tr_series(rates)
    tr_closed = tr[:-1]
    if len(tr_closed) < period:
        return None
    win = tr_closed[-period:]
    if not wilder:
        return sum(win) / float(period)
    if len(tr_closed) >= period * 3:
        a = 1.0 / period
        v = sum(tr_closed[:period]) / float(period)
        for x in tr_closed[period:]:
            v = v + a * (x - v)
        return v
    return sum(win) / float(period)


def data_quality(m15, m5, m1, info, k=None):
    """GUARD KUALITAS DATA (blueprint s.3 DATA QUALITY + s.39 LIVE FEED
    GUARD): urutan waktu, duplikat timestamp, OHLC valid (high>=low,
    open/close dalam range), sinkronisasi antar TF, bid/ask ada, feed
    tidak basi.  Return (ok, why).  dq_stale_sec=0 -> cek basi off
    (data sintetis/backtest)."""
    k = k or {}

    def _ohlc_ok(b, name, depth=80):
        t = [int(v) for v in (b.get("time") or [])]
        h = [float(v) for v in (b.get("high") or [])]
        l = [float(v) for v in (b.get("low") or [])]
        o = [float(v) for v in (b.get("open") or [])]
        c = [float(v) for v in (b.get("close") or [])]
        n = min(len(t), len(h), len(l), len(o), len(c))
        if n == 0:
            return False, "%s kosong" % name
        for i in range(max(0, n - depth), n):
            if i > 0 and t[i] <= t[i - 1]:
                return False, "%s waktu tidak urut/duplikat di %d" % (name, i)
            if h[i] < l[i]:
                return False, "%s high<low di %d" % (name, i)
            if not (l[i] - 1e-12 <= o[i] <= h[i] + 1e-12):
                return False, "%s open di luar range di %d" % (name, i)
            if not (l[i] - 1e-12 <= c[i] <= h[i] + 1e-12):
                return False, "%s close di luar range di %d" % (name, i)
        return True, ""

    for b, nm in ((m15, "M15"), (m5, "M5"), (m1, "M1")):
        ok, why = _ohlc_ok(b, nm)
        if not ok:
            return False, why
    bid = float(info.get("bid") or 0.0)
    ask = float(info.get("ask") or 0.0)
    if bid <= 0 or ask <= 0:
        return False, "bid/ask tidak tersedia"
    try:
        t15 = int(m15["time"][-1])
        t1 = int(m1["time"][-1])
        if abs(t15 - t1) > 6 * 900:
            return False, "TF tidak sinkron (M15 vs M1 selisih %d dtk)" \
                % abs(t15 - t1)
    except Exception:
        return False, "timestamp TF tidak terbaca"
    stale = int(k.get("dq_stale_sec", 2700) or 0)
    if stale > 0 and time.time() - t15 > stale:
        return False, "feed basi (bar M15 terakhir %d dtk lalu)" \
            % int(time.time() - t15)
    return True, ""


def session_of(ts=None):
    """Sesi pasar (blueprint s.27): Asia/London/NY/overlap -- fitur
    journal (jam UTC)."""
    h = time.gmtime(ts or time.time()).tm_hour
    if 0 <= h < 7:
        return "ASIA"
    if 7 <= h < 12:
        return "LONDON"
    if 12 <= h < 16:
        return "LONDON_NY"
    return "NEW_YORK"


def spread_limit(k, want, sym=None):
    """Batas spread (POINT) per pair -- nama logis dulu, lalu broker."""
    k = k or {}
    lims = k.get("spread_points") or {}
    for nm in (want, sym):
        v = int(lims.get(nm, 0) or 0) if nm else 0
        if v > 0:
            return v
    return int(k.get("spread_points_default", 2500) or 0)


def pip_entry_plan(tp_price, sm_usd, tp_usd, info):
    """Kalibrasi pip (dipertahankan utk kompatibilitas engine; S3 tidak
    memakai pip_symbols secara default)."""
    try:
        point = float(info.get("point") or 0.0)
        tsz = float(info.get("trade_tick_size") or 0.0) or point
        tval = float(info.get("trade_tick_value") or 0.0)
        tv = float(info.get("tick_value") or 0.0) or tval
        if point <= 0 or tv <= 0 or tsz <= 0 or sm_usd <= 0 or tp_usd <= 0:
            return None
        tp_dist = abs(float(tp_price) - 0.0)
        if tp_dist <= 0:
            return None
        val_unit = tv / tsz
        sl_dist = (sm_usd / val_unit) if val_unit > 0 else 0.0
        lot = max(0.01, round(sm_usd / max(tp_dist * val_unit, 1e-9), 2) * 100)
        return {"tp_dist": tp_dist, "sl_dist": sl_dist, "lot": lot}
    except Exception:
        return None


# ===========================================================================
# [1] FITUR CANDLE + FINGERPRINT (normalisasi ATR -- blueprint s.4, s.9)
# ===========================================================================
def candle_feats(bars, i, atr):
    """Fitur ternormalisasi bar i (bar历史, SUDAH closed)."""
    o = float(bars["open"][i]); h = float(bars["high"][i])
    l = float(bars["low"][i]); c = float(bars["close"][i])
    a = float(atr) if atr and atr > 0 else max(h - l, 1e-9)
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    up = h - max(o, c)
    dn = min(o, c) - l
    return {
        "body": min(body / a, 3.0),
        "range": min(rng / a, 4.0),
        "up_wick": min(up / a, 3.0),
        "dn_wick": min(dn / a, 3.0),
        "close_pos": (c - l) / rng,
        "dir": 1.0 if c > o else (0.0 if abs(c - o) < 1e-12 else -1.0),
    }


def fp_vector(bars, i, seq_len=5, atr=None):
    """Fingerprint SEQUENCE bar (i-seq_len+1 .. i).  i = bar closed
    terakhir yang boleh dipakai.  Return list fitur flat (urut waktu)."""
    v = []
    for j in range(i - seq_len + 1, i + 1):
        if j < 0:
            return None
        f = candle_feats(bars, j, atr)
        v.extend([f["body"], f["range"], f["up_wick"], f["dn_wick"],
                  f["close_pos"], f["dir"]])
    return v


def fp_similarity(v1, v2):
    """Similarity kontinu 0..100 (BUKAN probabilitas -- blueprint s.9)."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    s = 0.0
    for a, b in zip(v1, v2):
        d = abs(float(a) - float(b))
        s += min(d / 2.0, 1.0)          # skala: selisih 2.0 = beda total
    return round(100.0 * (1.0 - s / len(v1)), 2)


def fp_bias(bars, i):
    """Arah sekuens terakhir: +1 bull, -1 bear, 0 netral."""
    o = float(bars["open"][i]); c = float(bars["close"][i])
    po = float(bars["open"][i - 1]) if i >= 1 else o
    pc = float(bars["close"][i - 1]) if i >= 1 else c
    if c > o and c >= pc:
        return 1
    if c < o and c <= pc:
        return -1
    return 0


def _fp_outcome(bars, j, r_unit, horizon):
    """Outcome historis setup yg "entry" di close[j] dgn risiko r_unit:
    +2R tercapai sebelum -1R?  Hanya memakai bar SETELAH j (masih semua
    di masa lalu saat keputusan live -> bebas future leakage)."""
    hi = [float(v) for v in bars["high"]]
    lo = [float(v) for v in bars["low"]]
    base = float(bars["close"][j])
    up1 = base + 1.0 * r_unit
    up2 = base + 2.0 * r_unit
    dn1 = base - 1.0 * r_unit
    mfe = mae = 0.0
    win1 = False
    for i in range(j + 1, min(j + 1 + horizon, len(hi))):
        mfe = max(mfe, (hi[i] - base) / r_unit)
        mae = min(mae, (lo[i] - base) / r_unit)
        if not win1 and hi[i] >= up1:
            win1 = True
        if hi[i] >= up2:
            return True, True, mfe, mae
        if lo[i] <= dn1:
            return False, win1, mfe, mae
    return False, win1, mfe, mae


def fp_database(bars, k):
    """Bangun DB fingerprint historis dr jendela bar yg tersedia.
    Return list dict(vector, win, mfe, mae, j).  Bar terakhir (berjalan)
    dan horizon outcome TIDAK pernah masuk fitur (no leakage)."""
    n = len(bars["close"])
    seq = int(k.get("fp_sequence_len", 5))
    hor = int(k.get("fp_outcome_horizon", 24))
    win_n = int(k.get("fp_history_bars", 480))
    start = max(seq - 1, n - 1 - win_n)
    end = n - 1 - hor                   # outcome butuh bar sesudah j
    trs = tr_series(bars)[:-1]
    db = []
    for j in range(start, end + 1):
        lo = max(0, j - 40)
        atr_j = (sum(trs[max(0, j - 13):j + 1]) / float(min(14, j + 1))) \
            if j >= 0 else None
        if not atr_j or atr_j <= 0:
            continue
        v = fp_vector(bars, j, seq, atr_j)
        if not v:
            continue
        r_unit = atr_j * float(k.get("fp_r_atr", 1.0))
        w2, w1, mfe, mae = _fp_outcome(bars, j, r_unit, hor)
        db.append({"v": v, "win": w2, "win1": w1, "mfe": mfe, "mae": mae,
                   "j": j})
    return db


def fp_match(db, vec, k):
    """Cocokkan vec ke DB -> dict(sim, sample, win_rate, mfe, mae).
    sample_size mempengaruhi confidence (blueprint s.9 SAMPLE SIZE)."""
    thr = float(k.get("fp_similarity_candidate", 80.0))
    matches = []
    for rec in db:
        s = fp_similarity(vec, rec["v"])
        if s >= thr:
            matches.append((s, rec))
    if not matches:
        return {"sim": 0.0, "sample": 0, "win_rate": 0.0, "win1_rate": 0.0,
                "mfe": 0.0, "mae": 0.0}
    matches.sort(key=lambda x: -x[0])
    top = matches[:60]
    sample = len(top)
    win_rate = sum(1 for _, r in top if r["win"]) / float(sample)
    win1_rate = sum(1 for _, r in top if r.get("win1")) / float(sample)
    return {"sim": round(max(s for s, _ in top), 2),
            "sample": sample,
            "win_rate": round(win_rate * 100.0, 1),
            "win1_rate": round(win1_rate * 100.0, 1),
            "mfe": round(sum(r["mfe"] for _, r in top) / sample, 2),
            "mae": round(sum(r["mae"] for _, r in top) / sample, 2)}


# ===========================================================================
# [2] STRUKTUR PASAR (swing HH/HL/LH/LL -- blueprint s.5)
# ===========================================================================
def swings(bars, strength=3):
    """Pivot swing (konfirmasi: strength bar di KIRI+KANAN -- bar kanan
    sudah closed saat dipakai, bukan masa depan).  Return (highs, lows)
    list (i, price)."""
    h = [float(v) for v in bars["high"]]
    l = [float(v) for v in bars["low"]]
    n = len(h)
    s = int(strength)
    highs, lows = [], []
    for i in range(s, n - s):
        # kiri STRICT -> plateau harga sama tidak menghasilkan pivot kembar
        if h[i] > max(h[i - s:i]) and h[i] >= max(h[i + 1:i + s + 1]):
            highs.append((i, h[i]))
        if l[i] < min(l[i - s:i]) and l[i] <= min(l[i + 1:i + s + 1]):
            lows.append((i, l[i]))
    return highs, lows


def structure_state(highs, lows, cur_i):
    """Label struktur dr 2 swing terakhir masing2: HH+HL=UP, LH+LL=DOWN."""
    hs = [(i, p) for i, p in highs if i <= cur_i]
    ls = [(i, p) for i, p in lows if i <= cur_i]
    if len(hs) < 2 or len(ls) < 2:
        return 0.0, None, None
    (i1, h1), (i2, h2) = hs[-2], hs[-1]
    (j1, l1), (j2, l2) = ls[-2], ls[-1]
    hh = h2 > h1
    hl = l2 > l1
    lh = h2 < h1
    ll = l2 < l1
    if hh and hl:
        return 1.0, j2, l2          # up: swing low terakhir utk SL
    if lh and ll:
        return -1.0, i2, h2         # down: swing high terakhir utk SL
    mid_i = j2 if j2 >= i2 else i2
    mid_p = l2 if j2 >= i2 else h2
    return 0.0, mid_i, mid_p


# ===========================================================================
# [3] ZONA S/R (range, bukan harga tunggal -- blueprint s.6)
# ===========================================================================
def detect_zones(bars, atr, k, cur_i=None):
    """Deteksi zona S/R dr pivot M15.  Zona = RANGE [lo,hi] di sekitar
    ekstrem swing.  Hitung interaksi per KUNJUNGAN (bukan per candle).
    Status: FRESH/VALID/WEAK/EXHAUSTED/INVALID."""
    if cur_i is None:
        cur_i = len(bars["close"]) - 2      # bar closed terakhir
    a = float(atr) if atr and atr > 0 else 1e-9
    w = float(k.get("zone_width_atr", 0.5)) * a
    inv = float(k.get("zone_invalidate_atr", 0.25)) * a
    max_age = int(k.get("zone_max_age_bars", 200))
    strg = int(k.get("zone_swing_strength", 3))
    highs, lows = swings(bars, strg)
    c = [float(v) for v in bars["close"]]
    h = [float(v) for v in bars["high"]]
    l = [float(v) for v in bars["low"]]
    o = [float(v) for v in bars["open"]]
    # v4.12 ANTI-ZONA-PALSU (laporan user: "candle rejection kecil
    # dianggap zona SNR/HH-HL"): pivot wajib (1) punya REJEKSI NYATA
    # (wick/close jauh dr badan >= zone_min_wick_atr), (2) kaki
    # impuls yg masuk pivot cukup besar (>= zone_min_leg_atr).
    min_wick = float(k.get("zone_min_wick_atr", 0.35)) * a
    min_leg = float(k.get("zone_min_leg_atr", 0.60)) * a
    zones = []
    for i, p in highs:
        if cur_i - i > max_age:
            continue
        if max(h[i] - max(o[i], c[i]), h[i] - c[i]) < min_wick:
            continue                      # rejeksi kecil -> bukan zona
        if h[i] - min(l[max(0, i - 16):i]) < min_leg:
            continue                      # kaki terlalu kecil
        zones.append({"id": "R%d" % i, "type": "RESISTANCE", "i": i,
                      "lo": p - w * 0.5, "hi": p + w * 0.5,
                      "center": p, "extreme": p})
    for i, p in lows:
        if cur_i - i > max_age:
            continue
        if max(min(o[i], c[i]) - l[i], c[i] - l[i]) < min_wick:
            continue
        if max(h[max(0, i - 16):i]) - l[i] < min_leg:
            continue
        zones.append({"id": "S%d" % i, "type": "SUPPORT", "i": i,
                      "lo": p - w * 0.5, "hi": p + w * 0.5,
                      "center": p, "extreme": p})
    zones.sort(key=lambda z: z["i"])
    # v4.12 MERGE: beberapa pivot selevel (jarak <= zone_merge_atr)
    # = SATU zona (dulu jadi beberapa mikro-zona palsu).
    merge_d = float(k.get("zone_merge_atr", 0.60)) * a
    if merge_d > 0:                 # v4.12: 0 = merge MATI (mekanik lama)
        changed = True
        while changed:              # ANY-PAIR: pivot R,S,R,S berselang --
            changed = False         #   cek tetangga berurutan TIDAK cukup!
            merged = []
            for z in zones:
                hit = None
                for mm in merged:
                    if mm["type"] == z["type"] and \
                            abs(mm["center"] - z["center"]) <= merge_d:
                        hit = mm
                        break
                if hit is not None:
                    hit["lo"] = min(hit["lo"], z["lo"])
                    hit["hi"] = max(hit["hi"], z["hi"])
                    hit["center"] = (hit["lo"] + hit["hi"]) * 0.5
                    if z["type"] == "RESISTANCE":
                        hit["extreme"] = max(hit["extreme"], z["extreme"])
                    else:
                        hit["extreme"] = min(hit["extreme"], z["extreme"])
                    changed = True
                else:
                    merged.append(z)
            zones = merged
    exit_d = float(k.get("zone_touch_min_exit_atr", 0.6)) * a
    for z in zones:
        touches, last_side = 0, False
        rejections = 0              # kunjungan dgn penolakan kuat (wick)
        for i in range(z["i"] + 1, cur_i + 1):
            inside = (l[i] <= z["hi"] and h[i] >= z["lo"])
            if inside and not last_side:
                touches += 1
                last_side = True
                # penolakan: close kembali keluar + wick menembus dlm
                if z["type"] == "SUPPORT" and c[i] > z["hi"] \
                        and (z["hi"] - l[i]) >= 0.6 * a:
                    rejections += 1
                if z["type"] == "RESISTANCE" and c[i] < z["lo"] \
                        and (h[i] - z["lo"]) >= 0.6 * a:
                    rejections += 1
            elif not inside:
                far = (h[i] < z["lo"] - exit_d) or (l[i] > z["hi"] + exit_d)
                if far:
                    last_side = False
        z["touches"] = touches
        z["rejection_count"] = rejections
        # breakout status: close bar CLOSED terakhir di luar batas zona
        bo = (z["type"] == "SUPPORT" and c[cur_i] < z["lo"]) or \
             (z["type"] == "RESISTANCE" and c[cur_i] > z["hi"])
        z["breakout_status"] = "BREAKOUT" if bo else "NONE"
        z["htf_align"] = 0          # diisi dr regime H1 di evaluate
        if z["type"] == "SUPPORT" and c[cur_i] < z["lo"] - inv:
            z["status"] = "INVALID"
        elif z["type"] == "RESISTANCE" and c[cur_i] > z["hi"] + inv:
            z["status"] = "INVALID"
        elif touches >= 4:
            z["status"] = "EXHAUSTED"
        elif touches == 3:
            z["status"] = "WEAK"
        elif touches >= 1:
            z["status"] = "VALID"
        else:
            z["status"] = "FRESH"
        strength = 100.0 - min(touches, 4) * 12.0 \
            + (10.0 if z["status"] == "FRESH" else 0.0)
        z["strength"] = max(0.0, min(100.0, strength))
    return zones


def zone_quality(z, k):
    """Skor kualitas zona 0..100 (interaksi, freshness, status)."""
    if not z:
        return 0.0
    base = z.get("strength", 50.0)
    st = z.get("status", "VALID")
    if st in ("INVALID", "EXHAUSTED") or int(z.get("touches", 0)) >= 4:
        return 0.0
    if st == "WEAK":
        base *= 0.6
    return round(min(100.0, base), 1)


def nearest_opposing(zones, side, entry, k=None):
    """Zona lawan terdekat di depan entry (RESISTANCE utk BUY).
    v4.12 (laporan user "blokir 2R salah"): zona yang TIDAK PERNAH
    teruji (0 sentuhan), sudah DITEMBUS (breakout), atau kualitasnya
    di bawah zone_block_min_quality TIDAK dihitung sbg pemblokir."""
    k = k or {}
    need_touch = int(k.get("zone_block_requires_touch", 1))
    minq = float(k.get("zone_block_min_quality", 40.0))
    best = None
    for z in zones or []:
        if z.get("status") in ("INVALID",):
            continue
        if z.get("breakout_status") == "BREAKOUT":
            continue
        if need_touch and int(z.get("touches", 0)) < 1:
            continue
        if minq > 0 and zone_quality(z, k) < minq:
            continue
        if side > 0 and z["type"] == "RESISTANCE" and z["lo"] > entry:
            if best is None or z["lo"] < best["lo"]:
                best = z
        if side < 0 and z["type"] == "SUPPORT" and z["hi"] < entry:
            if best is None or z["hi"] > best["hi"]:
                best = z
    return best


def ema_cross_state(closes, fast, slow, lookback=5):
    """v4.12: deteksi PERSILANGAN EMA fast/slow (M15) dlm N bar
    terakhir (bar closed, tanpa look-ahead).  Return (cross_up,
    cross_dn)."""
    try:
        ef = ema_series([float(v) for v in closes], int(fast))
        es = ema_series([float(v) for v in closes], int(slow))
        n = min(len(ef), len(es))
        lb = max(1, int(lookback))
        if n < lb + 1:
            return False, False
        up = dn = False
        for j in range(n - lb, n):
            if ef[j - 1] <= es[j - 1] and ef[j] > es[j]:
                up = True
            if ef[j - 1] >= es[j - 1] and ef[j] < es[j]:
                dn = True
        return up, dn
    except Exception:
        return False, False


def adx_wilder(highs, lows, closes, period=14):
    """ADX Wilder (0..100): kekuatan tren pada M15.  None = data kurang.

    Definisi klasik Wilder: TR / +DM / -DM dihaluskan gaya Wilder
    (s = s - s/period + x), lalu DX dihaluskan lagi menjadi ADX.
    Tanpa look-ahead: hanya memakai nilai bar sampai indeks terakhir
    yang diberikan (bar closed)."""
    try:
        h = [float(v) for v in (highs or [])]
        l = [float(v) for v in (lows or [])]
        c = [float(v) for v in (closes or [])]
    except Exception:
        return None
    n = min(len(h), len(l), len(c))
    if n < period * 2 + 1:
        return None
    h, l, c = h[:n], l[:n], c[:n]
    tr_s = p_s = m_s = 0.0
    dxs = []
    for i in range(1, n):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        pdm = up if (up > dn and up > 0) else 0.0
        mdm = dn if (dn > up and dn > 0) else 0.0
        if i <= period:                 # seed: jumlah periode pertama
            tr_s += tr
            p_s += pdm
            m_s += mdm
            if i < period:
                continue
        else:                           # halus gaya Wilder
            tr_s = tr_s - tr_s / period + tr
            p_s = p_s - p_s / period + pdm
            m_s = m_s - m_s / period + mdm
        if tr_s > 0:
            dip = 100.0 * p_s / tr_s
            dim = 100.0 * m_s / tr_s
            den = dip + dim
            dxs.append(100.0 * abs(dip - dim) / den if den > 0 else 0.0)
        else:
            dxs.append(0.0)
    if len(dxs) < period:
        return None
    adx = sum(dxs[:period]) / period
    for x in dxs[period:]:
        adx = (adx * (period - 1) + x) / period
    return adx


def adx_gate(highs, lows, closes, k=None):
    """v4.26 (permintaan user) -- filter kekuatan tren ADX M15:

      Entry hanya saat ADX > adx_min (default 25).  ADX <= 25 = pasar
      sideways -> SKIP.  Fail-open kalau data kurang (ADX None) -- data
      tidak boleh menghentikan engine, konsisten dgn gerbang lain."""
    k = k or {}
    if not int(k.get("adx_filter", 1) or 0):
        return False, ""
    try:
        a = adx_wilder(highs, lows, closes,
                       int(k.get("adx_period", 14) or 14))
    except Exception:
        return False, ""
    if a is None:
        return False, ""
    mn = float(k.get("adx_min", 25.0))
    if a <= mn:
        return True, ("SKIP_ADX: ADX M15 %.1f <= %.0f (pasar sideways)"
                      % (a, mn))
    return False, ""


def _window(bars, i, w):
    """Slice window bar [i-w+1 .. i] (bar closed; tanpa look-ahead)."""
    i0 = max(0, i - w + 1)
    return ([float(v) for v in bars["high"][i0:i + 1]],
            [float(v) for v in bars["low"][i0:i + 1]],
            [float(v) for v in bars["close"][i0:i + 1]])


def ml_features(side, bars, i, atr, k=None):
    """v4.29 -- 9 FITUR karakter market pada bar closed ke-i (dipakai
    BERSAMA oleh trainer & engine -> tidak bisa beda definisi):

      1 sdir    : arah struktur pivot (HH+HL=+1 utk BUY / LH+LL=+1 utk
                  SELL; campuran = 0; lawan = -1)
      2 gap_ema : (EMA13-EMA21)/ATR x side  (tren searah?)
      3 adx_n   : kekuatan tren ADX/50 (0..1)
      4 room    : ruang ke swing lawan terdekat /3 ATR (0..1; 1=bersih)
      5 ext     : (close-EMA13)/ATR x side  (over-extension negatif)
      6 mom3    : momentum 3 bar /ATR x side
      7 brkout  : close menembus pivot high (BUY)/low (SELL) terakhir
      8/9 jam   : sin/cos jam UTC (karakter sesi Asia/London/NY)
    Return list 9 float, atau None bila data tipis."""
    k = k or {}
    try:
        hs, ls, cs = _window(bars, i, int(k.get("ml_window", 120)))
    except Exception:
        return None
    n = len(cs)
    if n < 60 or atr <= 0:
        return None
    strg = int(k.get("zone_swing_strength", 3))
    sh, sl_ = swings({"high": hs, "low": ls}, strg)
    j = n - 1
    ph = [p for _, p in sh]
    pl = [p for _, p in sl_]
    hh = len(ph) >= 2 and ph[-1] > ph[-2]
    hl = len(pl) >= 2 and pl[-1] > pl[-2]
    lh = len(ph) >= 2 and ph[-1] < ph[-2]
    ll = len(pl) >= 2 and pl[-1] < pl[-2]
    if side > 0:
        sdir = 1.0 if (hh and hl) else (-1.0 if (lh and ll) else 0.0)
    else:
        sdir = 1.0 if (lh and ll) else (-1.0 if (hh and hl) else 0.0)
    ef = ema_series(cs, 13)
    es = ema_series(cs, 21)
    gap = max(-4.0, min(4.0, (ef[-1] - es[-1]) / atr * side))
    ax = adx_wilder(hs, ls, cs, int(k.get("adx_period", 14))) or 0.0
    adx_n = min(ax, 50.0) / 50.0
    if side > 0:
        above = [p for p in ph if p > cs[j]]
        d = (min(above) - cs[j]) / atr if above else 3.0
    else:
        below = [p for p in pl if p < cs[j]]
        d = (cs[j] - max(below)) / atr if below else 3.0
    room = min(max(d, 0.0), 3.0) / 3.0
    ext = max(-4.0, min(4.0, (cs[j] - ef[-1]) / atr * side))
    mom = max(-4.0, min(4.0,
                        (cs[j] - cs[max(0, j - 3)]) / atr * side))
    if side > 0:
        bo = 1.0 if (ph and cs[j] > ph[-1]) else 0.0
    else:
        bo = 1.0 if (pl and cs[j] < pl[-1]) else 0.0
    try:
        hr = time.gmtime(float(bars["time"][i])).tm_hour
    except Exception:
        hr = 0
    ang = 2.0 * math.pi * hr / 24.0
    return [sdir, gap, adx_n, room, ext, mom, bo,
            math.sin(ang), math.cos(ang)]


_ML_MODEL = {"path": None, "m": None}


def ml_load_model(path=None):
    """Muat model ML (JSON kecil: bobot logistic regression) sekali --
    model dilatih OFFLINE dr riwayat 1-3 thn oleh python/ml_train.py."""
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "ml_model.json")
    if _ML_MODEL.get("path") == p:
        return _ML_MODEL.get("m")
    m = None
    try:
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m.get("w"), list) or not m.get("w"):
            m = None
    except Exception:
        m = None
    _ML_MODEL["path"] = p
    _ML_MODEL["m"] = m
    return m


def ml_predict(model, feats):
    """Logistic regression: p(win) = sigmoid(w.x + b)."""
    z = float(model.get("b", 0.0))
    for w, x in zip(model.get("w", []), feats):
        z += float(w) * float(x)
    if z > 40.0:
        return 1.0
    if z < -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def ml_gate(side, bars, atr, k=None, model=None):
    """v4.29 (permintaan user) -- FILTER PINTAR berbasis ML lokal:
    setup dengan prediksi p(win) < ml_min_p di-SKIP.  Entry tetap
    candle-pattern/sniper -- ML hanya menyaring karakter market.
    Fail-open bila model belum ada (engine tetap jalan)."""
    k = k or {}
    if not int(k.get("ml_enable", 1) or 0):
        return False, ""
    m = model if model is not None else ml_load_model()
    if not m:
        return False, ""
    i = len(bars["close"]) - 2          # bar CLOSED terakhir
    f = ml_features(side, bars, i, atr, k)
    if not f:
        return False, ""
    p = ml_predict(m, f)
    mn = float(k.get("ml_min_p", 0.50))
    if p < mn:
        return True, ("SKIP_ML: model p=%.2f < %.2f -- karakter market "
                      "lemah utk %s" % (p, mn,
                                        "BUY" if side > 0 else "SELL"))
    return False, ""


def msf_gate(side, bars, atr, k=None):
    """v4.29 (keluhan user "bot entry padahal struktur akan rejection"):
    FILTER STRUKTUR MARKET M15 sebelum entry --

      (a) Arah struktur: BUY dilarang saat struktur LH+LL jelas (turun);
          SELL dilarang saat HH+HL jelas (naik).
      (b) RUANG 1R: di depan entry ada swing HIGH (utk BUY) / swing LOW
          (utk SELL) dengan jarak < msf_room_atr x ATR dan close BELUM
          menembusnya -> harga menempel di titik rejection klasik ->
          SKIP.  Sudah breakout (close di atas HH / bawah LL) = lolos.

    Return (block, why)."""
    k = k or {}
    if not int(k.get("msf_enable", 1) or 0):
        return False, ""
    try:
        hs, ls, cs = _window(bars, len(bars["close"]) - 2,
                             int(k.get("ml_window", 120)))
    except Exception:
        return False, ""
    if len(cs) < 60 or atr <= 0:
        return False, ""
    strg = int(k.get("zone_swing_strength", 3))
    sh, sl_ = swings({"high": hs, "low": ls}, strg)
    ph = [p for _, p in sh]
    pl = [p for _, p in sl_]
    if len(ph) < 2 or len(pl) < 2:
        return False, ""
    hh = ph[-1] > ph[-2]
    hl = pl[-1] > pl[-2]
    lh = ph[-1] < ph[-2]
    ll = pl[-1] < pl[-2]
    nm = "BUY" if side > 0 else "SELL"
    if side > 0 and lh and ll:
        return True, ("SKIP_MSF: struktur M15 LH+LL (turun) -- jangan "
                      "BUY melawan struktur")
    if side < 0 and hh and hl:
        return True, ("SKIP_MSF: struktur M15 HH+HL (naik) -- jangan "
                      "SELL melawan struktur")
    px = cs[-1]
    ra = float(k.get("msf_room_atr", 1.0))
    if side > 0:
        above = [p for p in ph if p > px + 0.05 * atr]   # belum ditembus
        if above:
            d = min(above) - px
            if d < ra * atr:
                return True, ("SKIP_MSF: HH/resistance di atas hanya "
                              "%.2f ATR < %.1f ATR (belum breakout) -- "
                              "rawan rejection" % (d / atr, ra))
    else:
        below = [p for p in pl if p < px - 0.05 * atr]
        if below:
            d = px - max(below)
            if d < ra * atr:
                return True, ("SKIP_MSF: LL/support di bawah hanya "
                              "%.2f ATR < %.1f ATR (belum breakdown) -- "
                              "rawan rejection" % (d / atr, ra))
    return False, ""


def ema_reversal_block(side, closes, atr, k=None):
    """v4.24 (rumus user) -- cegah entry lawan pisau jatuh/naik:

      SKIP BUY bila: EMA13 tadinya DI ATAS EMA21, kini melandai turun
        (gap mengecil) dan AKAN atau SUDAH menyilang EMA21, sementara
        candle close DI BAWAH EMA13 dan DI BAWAH EMA21.
      SKIP SELL: cermin -- EMA13 tadinya DI BAWAH, naik mendekati/sudah
        cross ke atas EMA21, candle di ATAS keduanya.

    Return (block, why).  Bar closed saja (tanpa look-ahead)."""
    k = k or {}
    if not int(k.get("ema_rev_enable", 1) or 0):
        return False, ""
    try:
        vals = [float(v) for v in (closes or [])]
    except Exception:
        return False, ""
    lb = int(k.get("ema_rev_lookback", 5) or 5)
    if len(vals) < lb + 12:
        return False, ""
    ef = ema_series(vals, int(k.get("ema_fast", 13)))
    es = ema_series(vals, int(k.get("ema_slow", 21)))
    n = min(len(ef), len(es))
    if n < lb + 2:
        return False, ""
    a = float(atr or 0.0)
    if a <= 0:
        a = 1e-9
    gap = [(ef[i] - es[i]) / a for i in range(n)]
    gp, gn = gap[-1 - lb], gap[-1]        # gap dulu vs sekarang (ATR)
    was_thr = float(k.get("ema_rev_was_gap_atr", 0.10))
    near_thr = float(k.get("ema_rev_gap_atr", 0.15))
    px, e13n, e21n = vals[-1], ef[-1], es[-1]
    if side > 0:
        # EMA13 tadinya jelas di atas, sekarang turun mendekati / sudah
        # menyilang ke bawah EMA21, candle di bawah keduanya
        if (gp >= was_thr and gn < gp and gn <= near_thr
                and px < e13n and px < e21n):
            return True, ("SKIP_EMA_REVERSAL: EMA13 turun menuju/sudah "
                          "cross EMA21 (gap %.2f->%.2f ATR) + candle di "
                          "bawah EMA13/21 -- jangan BUY" % (gp, gn))
        return False, ""
    if side < 0:
        # cermin: EMA13 tadinya di bawah, naik mendekati / sudah cross
        # ke atas, candle di atas keduanya
        if (gp <= -was_thr and gn > gp and gn >= -near_thr
                and px > e13n and px > e21n):
            return True, ("SKIP_EMA_REVERSAL: EMA13 naik menuju/sudah "
                          "cross EMA21 (gap %.2f->%.2f ATR) + candle di "
                          "atas EMA13/21 -- jangan SELL" % (gp, gn))
    return False, ""


# ===========================================================================
# [4] REGIME H1 (blueprint s.2 -- konteks, TIDAK memicu entry)
# ===========================================================================
def h1_regime(h1, atr, k):
    """Label regime + skor arah -1..1 dr EMA13/21 H1, slope, separasi."""
    c = [float(v) for v in (h1.get("close") or [])] if h1 else []
    if len(c) < 40:
        return "UNCERTAIN", 0.0
    cc = c[:-1]
    e13 = ema_series(cc, int(k.get("ema_fast", 13)))
    e21 = ema_series(cc, int(k.get("ema_slow", 21)))
    lb = int(k.get("regime_slope_lookback", 6))
    if len(e13) <= lb:
        return "UNCERTAIN", 0.0
    a = float(atr) if atr and atr > 0 else 1e-9
    sep = (e13[-1] - e21[-1]) / a
    slope = (e13[-1] - e13[-1 - lb]) / a
    s = 0.0
    if abs(sep) >= float(k.get("regime_ema_sep_min_atr", 0.10)):
        s += 0.5 * (1 if sep > 0 else -1)
    if abs(slope) >= 0.05:
        s += 0.5 * (1 if slope > 0 else -1)
    if s >= 0.75:
        return "TREND_UP", round(min(1.0, s), 2)
    if s <= -0.75:
        return "TREND_DOWN", round(max(-1.0, s), 2)
    if abs(sep) > 1.2 and abs(slope) > 0.8:
        return "HIGH_VOLATILITY", 0.0
    return "RANGE", round(s, 2)


# ===========================================================================
# [5] MOMENTUM M5 + TRIGGER M1 (blueprint s.12, s.13)
# ===========================================================================
def m5_momentum(m5, side, atr, k, zone=None):
    """Momentum M5 (blueprint s.12): displacement candle searah ATAU
    reclaim/retest-hold di zona (dip ke zona lalu close balik di atas
    dasar zona utk BUY -- mirror utk SELL).  Return (ready, why, str)."""
    o = [float(v) for v in (m5.get("open") or [])]
    c = [float(v) for v in (m5.get("close") or [])]
    l = [float(v) for v in (m5.get("low") or [])]
    h = [float(v) for v in (m5.get("high") or [])]
    if len(c) < 22 or not atr or atr <= 0:
        return False, "M5 data tipis", 0.0
    i = len(c) - 2                       # bar closed terakhir
    thr = float(k.get("m5_min_body_atr", 0.6)) * atr
    # momentum = PERKEMBANGAN: salah satu dari 2 candle closed terakhir
    # menunjukkan displacement searah (continuation/displacement)
    for j in (i, i - 1):
        body = abs(c[j] - o[j])
        bull = c[j] > o[j]
        if ((side > 0 and bull) or (side < 0 and not bull)) and body >= thr:
            return True, "M5 displacement searah", min(1.0, body / (2.0 * atr))
    # RECLAIM / RETEST-HOLD di zona (blueprint s.12 "reclaim", "retest hold")
    if zone:
        zlo = float(zone.get("lo") or 0.0)
        zhi = float(zone.get("hi") or 0.0)
        if side > 0 and zlo > 0:
            touched = any(l[j] <= zhi for j in (i - 1, i - 2))
            if touched and c[i] > zlo and c[i] > o[i]:
                return True, "M5 reclaim: retest zona tahan + close bull", 0.6
        if side < 0 and zhi > 0:
            touched = any(h[j] >= zlo for j in (i - 1, i - 2))
            if touched and c[i] < zhi and c[i] < o[i]:
                return True, "M5 reclaim: retest zona tahan + close bear", 0.6
    bull_last = c[i] > o[i]
    if (side > 0 and bull_last) or (side < 0 and not bull_last):
        return False, "M5 searah tapi body kecil (tunggu displacement)", 0.3
    return False, "M5 belum searah (tunggu momentum)", 0.0


def m1_trigger(m1, side, atr5, k):
    """Trigger presisi M1 (blueprint s.13): micro HL (BUY) / LH (SELL)
    di dalam jendela + candle trigger searah.  Micro HL = low bar closed
    terakhir DI ATAS low terendah jendela (lembah mikro terbentuk) +
    close menembus close bar sebelumnya.  Return (ready, why)."""
    o = [float(v) for v in (m1.get("open") or [])]
    h = [float(v) for v in (m1.get("high") or [])]
    l = [float(v) for v in (m1.get("low") or [])]
    c = [float(v) for v in (m1.get("close") or [])]
    n = int(k.get("m1_trigger_bars", 12))
    if len(c) < n + 6 or not atr5 or atr5 <= 0:
        return False, "M1 data tipis"
    last = len(c) - 2                    # bar closed terakhir
    wlo = min(l[last - n + 1:last + 1])
    whi = max(h[last - n + 1:last + 1])
    bull = c[last] > o[last]
    bear = c[last] < o[last]
    if side > 0:
        hl = l[last] > wlo and c[last] > c[last - 1]
        if bull and hl:
            return True, "M1 micro HL + trigger bull"
        return False, "M1 tunggu micro HL/trigger bull"
    lh = h[last] < whi and c[last] < c[last - 1]
    if bear and lh:
        return True, "M1 micro LH + trigger bear"
    return False, "M1 tunggu micro LH/trigger bear"


# ===========================================================================
# [6] STATE (per simbol; persist JSON -- data/s3_state.json)
# ===========================================================================
class Strategy2State(object):
    """pending (HOLD per simbol) + cooldown + trail + attempts per zona."""

    def __init__(self, path=None):
        self.path = path
        self.pending = {}
        self.cooldown = {}
        self.trail = {}
        self.attempts = {}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    d = json.load(f)
                self.pending = d.get("pending", {})
                self.cooldown = d.get("cooldown", {})
                self.trail = d.get("trail", {})
                self.attempts = d.get("attempts", {})
            except Exception:
                pass

    def save(self):
        if not self.path:
            return
        try:
            d = os.path.dirname(self.path)
            if d and not os.path.exists(d):
                os.makedirs(d)
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"pending": self.pending,
                           "cooldown": self.cooldown,
                           "trail": self.trail,
                           "attempts": self.attempts}, f)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def save_pending(self, sym, sig, groups, signal_bar, wait_bar,
                     mode="m5"):
        self.pending[sym] = {"sig": sig, "groups": int(groups),
                             "signal_bar": int(signal_bar),
                             "wait_bar": int(wait_bar), "mode": str(mode),
                             "born_ts": int(time.time())}

    def clear(self, sym):
        self.pending.pop(sym, None)

    def set_cooldown(self, sym, minutes=None, now=None):
        mins = int(minutes if minutes is not None else 10)
        self.cooldown[sym] = (now or time.time()) + mins * 60

    def cooldown_until(self, sym):
        return float(self.cooldown.get(sym, 0))

    def set_trail(self, sym, trail):
        self.trail[sym] = trail.to_dict() if isinstance(trail, ATRTrail) \
            else trail

    def get_trail(self, sym):
        d = self.trail.get(sym)
        return ATRTrail.from_dict(d) if d else None

    def del_trail(self, sym):
        self.trail.pop(sym, None)

    # -- re-entry per zona (blueprint s.35) ---------------------------------
    def attempt(self, zone_key):
        self.attempts[str(zone_key)] = int(self.attempts.get(str(zone_key), 0)) + 1

    def attempts_of(self, zone_key):
        return int(self.attempts.get(str(zone_key), 0))


# ===========================================================================
# [7] MANAJEMEN POSISI: BEP +1R, TRAILING +2R (blueprint s.32, s.33)
#     Kontrak engine: ATRTrail(sym, side, entry, atr, k) + update(bid,ask)
#     -> {floor_price, close_now, phase, peak, floor};  floor = harga SL.
#     Unit R = jarak SL awal (atr x sl_mult).  Peak/floor dlm satuan RATIO
#     thd risiko (spt S2) supaya kompatibel penuh dgn engine.
# ===========================================================================
def atr_signed_move(side, entry, bid, ask, atr):
    return (bid - entry) / atr if side > 0 else (entry - ask) / atr


def atr_stop_improves(side, candidate, old_sl, tick):
    if candidate <= 0:
        return False
    if old_sl <= 0:
        return True
    return candidate >= old_sl + tick * 0.5 if side > 0 else \
        candidate <= old_sl - tick * 0.5


class ATRTrail(object):
    """S3: +1R -> BEP+ (buffer spread/komisi kecil, dlm R); +2R ->
    trailing = peak - trail_back_r (ratchet, tak pernah mundur)."""

    def __init__(self, symbol, side, entry, atr, k=None, tp_dist=0.0,
                 tp_r=0.0):
        k = k or {}
        self.symbol = symbol
        self.side = int(side)
        self.entry = float(entry)
        self.atr = float(atr)
        self.sl_mult = float(k.get("sl_atr", 1.2))
        self.bep_trigger = float(k.get("bep_trigger_r", 1.0))
        self.bep_buffer = float(k.get("bep_buffer_r", 0.10))
        self.trail_trigger = float(k.get("trail_trigger_r", 2.0))
        self.trail_back = float(k.get("trail_back_r", 1.0))
        self.peak = 0.0            # R tertinggi
        self.risk_dist = self.atr * self.sl_mult
        if self.risk_dist <= 0:
            self.risk_dist = max(self.atr, 1e-9)
        self.floor = -1.0          # RATIO: -1.0 = SL awal (satu risiko penuh)
        self.mae = 0.0
        self.mfe = 0.0
        self.phase = "INITIAL"
        self.t_entry = time.time()             # s.41: holding time
        self.tp_dist = float(tp_dist or 0.0)   # v3.83: jarak TP (harga)
        self.tp_r = float(tp_r or 0.0)         #       & R rencana (RR)
        # v4.12 TANGGA TP: TP1 partial -> TP2 + trail 0.5R
        self.tp1_hit = 0            # TP1 (2R) sudah dieksekusi 75%?
        self.tp1_lock_r = 0.0       # v4.13: SL setelah TP1 = +lock R (1R)
        self.tp2_dist = 0.0         # jarak TP2 (harga); 0 = tanpa TP2
        self.tp2_r = 0.0            # TP2 dlm R
        self.trail_step_r = 0.0     # jarak trailing SL stlh TP1 (0.5R)
        self.last_sl_r = -1e18      # level SL (R) terakhir dipasang

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        obj = cls.__new__(cls)
        obj.__dict__.update(d)
        obj.side = int(obj.side)
        return obj

    def update(self, bid, ask):
        px = bid if self.side > 0 else ask
        if self.risk_dist <= 0:
            self.risk_dist = max(self.atr, 1e-9)
        r = (px - self.entry) / self.risk_dist * self.side
        if r > self.peak:
            self.peak = r
        self.mfe = max(self.mfe, r)
        self.mae = min(self.mae, r)
        if self.peak >= self.trail_trigger:
            new_floor = self.peak - self.trail_back
            self.phase = "TRAIL"
        elif self.peak >= self.bep_trigger:
            new_floor = self.bep_buffer
            self.phase = "BEP"
        else:
            new_floor = -1.0
            self.phase = "INITIAL"
        if new_floor > self.floor:      # ratchet: SL hanya membaik
            self.floor = new_floor
        floor_price = self.entry + self.side * self.risk_dist * self.floor
        protected = self.floor > -0.999
        if self.side > 0:
            close_now = protected and bid < floor_price
        else:
            close_now = protected and ask > floor_price
        return {"floor_price": floor_price, "close_now": close_now,
                "phase": self.phase, "peak": round(self.peak, 3),
                "floor": round(self.floor, 3)}


def _norm_vol(vol, vol_min, vol_step):
    """v4.12: bulatkan volume ke step broker (ke bawah)."""
    step = float(vol_step or 0.0)
    if step <= 0:
        return float(vol)
    return float(int(float(vol) / step + 1e-9) * step)


def tp_ladder_decision(tr, bid, ask, tp1_touched, lot, vol_min,
                       vol_step, tp1_pct=75.0, tp2_touched=None,
                       peak_r=None):
    """v4.12 MESIN TANGGA TP (permintaan user) -- rumus final user:
      TP1 = 2R  -> tutup tp1_close_pct% (75%), SL pindah ke +1R
                   (sisa 25% dijamin profit walau tren balik);
      tren lanjut -> SL bergeser tiap 0.5R dari PUNCAK sebenarnya;
      TP2 = 4R  -> close PENUH.
    v4.20: tp2_touched/anti-lolos spike antar-siklus.
    v4.21 (rumus user "spike lewat jauh ya udah TP"): TP2 dicek PALING
      AWAL -- spike sekali tembus 4R langsung CLOSE PENUH (fill di
      harga pasar saat deteksi -> profit >= target), bukan partial TP1
      dulu.  peak_r = puncak SEBENARNYA (dari candle M1, spike
      termasuk) utk langkah SL; None = pakai peak tersampel.
    Fungsi MURNI (tanpa broker) -> mudah diuji.  Aksi:
      {"action":"none"}
      {"action":"partial","volume":..,"remain":..}   tutup sebagian TP1
      {"action":"full","code":"EXIT_TP"|"EXIT_TP2"}  tutup semua
      {"action":"sl","sl_r":..}                      geser SL (ratchet)
    Lot terlalu kecil utk dipecah -> "full" (perilaku lama yang aman).
    """
    side = int(tr.side)
    entry = float(tr.entry)
    risk = float(getattr(tr, "risk_dist", 0.0) or 0.0)
    tp1_d = float(getattr(tr, "tp_dist", 0.0) or 0.0)
    tp2_d = float(getattr(tr, "tp2_dist", 0.0) or 0.0)
    step = float(getattr(tr, "trail_step_r", 0.0) or 0.0)
    # ---- v4.21: TP2 DULU -- spike tembus 4R = target jarak terjauh
    #      sudah tersentuh -> semua profit dikunci sekarang ----
    if tp2_d > 0:
        tp2_px = entry + side * tp2_d
        t2 = tp_hit(side, bid, ask, tp2_px) if tp2_touched is None \
            else bool(tp2_touched)
        if t2:
            return {"action": "full", "code": "EXIT_TP2"}
    if not int(getattr(tr, "tp1_hit", 0) or 0):
        # v4.25 (rumus user): floating profit >= bep_at_r (1R) SEBELUM
        # TP1 -> SL geser ke BEP (entry + offset; default tepat BEP).
        # Di siklus yang sama TP1 tersentuh -> lewat (partial + lock
        # +1R langsung, lebih baik dari BEP).  Ratchet dgn last_sl_r.
        bep_at = float(getattr(tr, "bep_at_r", 0.0) or 0.0)
        if bep_at > 0 and not (tp1_touched and tp1_d > 0):
            pk = tr.peak if peak_r is None else \
                max(float(tr.peak), float(peak_r))
            if pk >= bep_at:
                sl_r = float(getattr(tr, "bep_offset_r", 0.0) or 0.0)
                _raw = getattr(tr, "last_sl_r", -1e18)
                last = float(_raw) if _raw is not None else -1e18
                # CATATAN: 0.0 (BEP) falsy -- jangan pakai `or` sentinel
                if sl_r > last + 1e-9:
                    return {"action": "sl", "sl_r": sl_r}
        if not (tp1_touched and tp1_d > 0):
            return {"action": "none"}
        if float(vol_min) <= 0:        # batasan lot broker tak diketahui
            return {"action": "full", "code": "EXIT_TP"}
        vol = _norm_vol(float(lot) * float(tp1_pct) / 100.0,
                        vol_min, vol_step)
        remain = float(lot) - vol
        if vol >= float(vol_min) - 1e-12 and remain >= float(vol_min) - 1e-12:
            return {"action": "partial", "volume": vol,
                    "remain": remain}
        return {"action": "full", "code": "EXIT_TP"}   # lot kecil
    # ---- setelah TP1: SL BEP lalu geser tiap 0.2R dari puncak ----
    if step > 0 and risk > 0:
        # v4.28 (rumus user): setelah TP1 -> SL LANGSUNG ke BEP
        # (titik entry; lock 0), lalu bergeser tiap 0.2R kenaikan
        # peak.  v4.21: peak = puncak SEBENARNYA (peak_r dr candle
        # M1 -- spike antar-siklus termasuk), bukan harga tersampel.
        lock = float(getattr(tr, "tp1_lock_r", 0.0) or 0.0)
        base = lock if lock > 0 else 0.0      # BEP tepat (v4.28)
        tp1r = float(getattr(tr, "tp_r", 0.0) or 0.0)
        pk = tr.peak if peak_r is None else \
            max(float(tr.peak), float(peak_r))
        n = int(max(0.0, pk - tp1r) / step + 1e-9)
        sl_r = base + n * step
        last = float(getattr(tr, "last_sl_r", -1e18) or -1e18)
        if sl_r > last + 1e-9:
            return {"action": "sl", "sl_r": sl_r}
    return {"action": "none"}

# ===========================================================================
def journal(path, rec):
    try:
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            os.makedirs(d)
        rec = dict(rec)
        rec["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def journal_exit(path, symbol, tr, pl_money=None, lot=None,
                 code=None, r_multiple=None):
    """Catat EXIT ke journal (blueprint s.41 EXIT + s.44 MAE/MFE):
    reason dr fase trail (INITIAL->EXIT_INITIAL_SL, BEP->EXIT_BEP_PLUS,
    TRAIL->EXIT_TRAILING), R multiple = floor terkunci, MAE/MFE dari
    trail.  Dipanggil engine saat posisi S3 tertutup.  v3.82: `code`
    memaksa reason (mis. "EXIT_TP" utk close TP hard) & `r_multiple`
    mengganti R dr floor (close TP = R nominal rencana)."""
    phase = getattr(tr, "phase", "INITIAL")
    reason = {"INITIAL": "EXIT_INITIAL_SL", "BEP": "EXIT_BEP_PLUS",
              "TRAIL": "EXIT_TRAILING"}.get(phase, "EXIT_INITIAL_SL")
    if code:
        reason = str(code)
    if r_multiple is None:
        r_multiple = float(getattr(tr, "floor", 0.0))
    t0 = float(getattr(tr, "t_entry", 0.0) or 0.0)
    hold = round(time.time() - t0, 1) if t0 > 0 else None
    rec = {"symbol": symbol, "reason": reason,
           "r_multiple": round(float(r_multiple), 3),
           "peak_r": round(float(getattr(tr, "peak", 0.0)), 3),
           "mae": round(float(getattr(tr, "mae", 0.0)), 3),
           "mfe": round(float(getattr(tr, "mfe", 0.0)), 3),
           "hold_sec": hold, "pl": pl_money, "lot": lot}
    journal(path, rec)
    return rec


# ===========================================================================
# [8c] TP HARD (v3.82, permintaan user): sentuh target -> LANGSUNG close,
#      tanpa trailing.  tp_mode "trail" = perilaku lama (SL dikunci +20).
# ===========================================================================
def tp_touch_price(entry, side, tp_money, lot, val_unit, rate_acc=1.0):
    """Harga TP virtual utk target uang: entry +/- dist.
    dist = (tp_money x rate_acc) / (lot x val_unit).  0.0 = TP off
    (tp_money/lot/val_unit tak valid)."""
    lot = float(lot or 0.0)
    val_unit = float(val_unit or 0.0)
    tp_money = float(tp_money or 0.0)
    if lot <= 0 or val_unit <= 0 or tp_money <= 0:
        return 0.0
    dist = (tp_money * float(rate_acc or 1.0)) / (lot * val_unit)
    e = float(entry or 0.0)
    return e + dist if int(side) > 0 else e - dist


def tp_hit(side, bid, ask, tp_px):
    """True bila pasar menyentuh/menembus TP virtual.  Konvensi close:
    BUY ditutup di BID, SELL di ASK -> yang dibandingkan itu."""
    tp_px = float(tp_px or 0.0)
    if tp_px <= 0:
        return False
    return (float(bid) >= tp_px) if int(side) > 0 else (float(ask) <= tp_px)


# ===========================================================================
# [8b] RIWAYAT DALAM + DB FINGERPRINT INKREMENTAL (blueprint s.3, s.9)
# ===========================================================================
def merge_bars(older, newer):
    """Gabung dua array rates ASCENDING, dedupe by time (hist paging)."""
    if not older:
        return newer
    if not newer:
        return older
    cut = float(older["time"][-1])
    out = {kk: list(vv) for kk, vv in older.items()}
    for i, t in enumerate(newer["time"]):
        if float(t) > cut:
            for kk in ("time", "open", "high", "low", "close",
                       "tick_volume"):
                out[kk].append(newer[kk][i])
    return out


def hist_paged(broker, sym, tf="M15", target=35040, batch=1500,
               cur=None, budget_sec=10.0, live_bars=300):
    """HALAMAN RIWAYAT DALAM (blueprint s.3 AUTO): kumpulkan bar lama
    per halaman sampai target / broker kehabisan / anggaran waktu habis.
    `cur` = hasil sebelumnya (lanjutan antar-refresh; konvergen ke target
    tanpa mengarang data).  Anchor: MT4 = epoch bar tertua; MT5 = posisi
    (jumlah bar yang sudah dimiliki)."""
    base = cur
    if base is None:
        try:
            base = broker.copy_rates(sym, tf, min(live_bars, target))
        except Exception:
            base = None
    if not base:
        return None
    t0 = time.time()
    for _ in range(200):
        if time.time() - t0 > float(budget_sec):
            break
        if len(base["close"]) >= int(target):
            break
        try:
            if getattr(broker, "kind", "MT5") == "MT4":
                older = broker.copy_rates_before(sym, tf, int(batch),
                                                 int(base["time"][0]))
            else:
                older = broker.copy_rates_before(sym, tf, int(batch),
                                                 len(base["close"]))
        except Exception:
            break                        # broker tak dukung paging -> berhenti
        if not older:
            break
        nb = merge_bars(older, base)
        if len(nb["close"]) <= len(base["close"]):
            break                      # broker kehabisan riwayat (AUTO)
        base = nb
    return base


def hist_years(n_bars, tf_min=15):
    """Panjang data dlm TAHUN (metadata blueprint s.3)."""
    return round(n_bars * tf_min / (60.0 * 24.0 * 365.0), 2)


_FPDB = {}          # {symbol: {"ci","db","pend","nlen"}} -- cache lokal


def fp_match_cached(symbol, bars, k):
    """Versi CACHED fp_database+fp_match utk engine live: DB dibangun
    SEKALI lalu ditambah INKREMENTAL per bar closed baru (tetap ringan
    walau riwayat 1-3 tahun).  Tanpa future leakage: outcome hanya utk
    bar yang sudah lengkap horizon-nya (sisanya pending)."""
    n = len(bars["close"])
    ci = n - 2                          # bar closed terakhir
    seq = int(k.get("fp_sequence_len", 5))
    hor = int(k.get("fp_outcome_horizon", 24))
    window = int(k.get("fp_history_bars", 12000))
    trs = tr_series(bars)[:-1]
    atrs = {}

    def atr_of(j):
        if j not in atrs:
            lo = max(0, j - 13)
            atrs[j] = sum(trs[lo:j + 1]) / float(max(1, j + 1 - lo))
        return atrs[j]

    mem = _FPDB.get(symbol)
    if mem is None or mem["ci"] > ci or len(bars["time"]) < mem.get("nlen", 0):
        mem = {"ci": -1, "db": [], "pend": {}, "nlen": len(bars["time"])}
        _FPDB[symbol] = mem
    start_j = max(seq - 1, n - 1 - window)
    done_until = n - 1 - hor            # outcome lengkap sampai j ini
    # 1) pending yang horizon-nya sudah lengkap -> final + outcome
    for j in sorted(list(mem["pend"].keys())):
        if j <= done_until:
            vec = mem["pend"].pop(j)
            r_unit = atr_of(j) * float(k.get("fp_r_atr", 1.0))
            w2, w1, mfe, mae = _fp_outcome(bars, j, r_unit, hor)
            mem["db"].append({"v": vec, "win": w2, "win1": w1,
                              "mfe": mfe, "mae": mae, "j": j})
    # 2) bar closed baru -> vector; final atau pending
    if ci > mem["ci"]:
        for j in range(mem["ci"] + 1, ci + 1):
            if j - seq + 1 < 0:
                continue
            a = atr_of(j)
            if not a or a <= 0:
                continue
            vec = fp_vector(bars, j, seq, a)
            if not vec:
                continue
            if j <= done_until:
                r_unit = a * float(k.get("fp_r_atr", 1.0))
                w2, w1, mfe, mae = _fp_outcome(bars, j, r_unit, hor)
                mem["db"].append({"v": vec, "win": w2, "win1": w1,
                                  "mfe": mfe, "mae": mae, "j": j})
            else:
                mem["pend"][j] = vec
        mem["ci"] = ci
        mem["nlen"] = len(bars["time"])
    # 3) jendela bergeser -> buang entri terlalu tua
    if mem["db"] and mem["db"][0]["j"] < start_j:
        mem["db"] = [r for r in mem["db"] if r["j"] >= start_j]
    for j in [j for j in mem["pend"] if j < start_j]:
        mem["pend"].pop(j)
    vec_now = fp_vector(bars, ci, seq, atr_of(ci)) if ci - seq + 1 >= 0 \
        else None
    m = fp_match(mem["db"], vec_now, k)
    m["db_bars"] = len(mem["db"])
    m["years"] = hist_years(len(bars["close"]))
    m["pending"] = len(mem["pend"])
    return m


# ===========================================================================
# [9] TEMPLATE HASIL (shape engine/dashboard -- JANGAN ubah bentuknya)
# ===========================================================================
_COMP_KEYS = ("structure", "liquidity", "trend", "momentum", "volume",
              "orderflow")


def _result(symbol, data, status="WAIT", why=""):
    info = data.get("info") or {}
    price = float(info.get("bid") or 0.0)
    m5 = data.get("m5") or {}
    t = [int(v) for v in (m5.get("time") or [])]
    o = [float(v) for v in (m5.get("open") or [])]
    h = [float(v) for v in (m5.get("high") or [])]
    l = [float(v) for v in (m5.get("low") or [])]
    c = [float(v) for v in (m5.get("close") or [])]
    spark = [(t[i], o[i], h[i], l[i], c[i])
             for i in range(max(0, len(t) - 60), len(t))]
    zero = dict.fromkeys(_COMP_KEYS, 0.0)
    return {"symbol": symbol, "price": price, "side": "-", "score": 0.0,
            "status": status, "strategy": "S2", "why": why,
            "block_why": "", "sniper_why": "", "sl_price": 0.0,
            "sl_points": 0, "point": float(info.get("point") or 0.0),
            "rej_blocked": None, "exec": None, "mtf": {"final": 0.0},
            "components_buy": dict(zero), "components_sell": dict(zero),
            "spark_ohlc": spark}


def _clamp100(v):
    return max(0.0, min(100.0, float(v)))


# ===========================================================================
# [10] EVALUATE -- pipeline utama (engine memanggil ini tiap scan)
# ===========================================================================
def evaluate(symbol, data, k=None, st=None):
    return _result(symbol,data,"WAIT","template kosong -- strategy baru belum diisi")
    k = k or {}
    now = int(time.time())
    m15 = data.get("m15") or {}
    m5 = data.get("m5") or {}
    m1 = data.get("m1") or {}
    h1 = data.get("h1") or {}
    info = data.get("info") or {}
    point = float(data.get("point") or info.get("point") or 0.0)
    if len(m15.get("close") or []) < 60 or not m5 or not m1 or point <= 0:
        res = _result(symbol, data, "WAIT", "data TF belum siap")
        return res

    ci = len(m15["close"]) - 2          # bar M15 CLOSED terakhir
    atr15 = atr_at(m15, int(k.get("atr_period", 14)))
    atr5 = atr_at(m5, int(k.get("atr_period", 14)))
    bid = float(info.get("bid") or m15["close"][-1])
    if not atr15 or atr15 <= 0 or not atr5 or atr5 <= 0:
        return _result(symbol, data, "WAIT", "ATR belum siap")

    ok_dq, why_dq = data_quality(m15, m5, m1, info, k)
    if not ok_dq:
        res = _result(symbol, data, "BLOCKED", "")
        res["block_why"] = "SKIP_DATA_QUALITY: %s" % why_dq
        return res

    res = _result(symbol, data, "WAIT", "")
    # ---- H1 regime ----
    regime, reg_score = h1_regime(h1, atr15, k)
    # ---- zona + struktur di EKOR (zona >200 bar = tua; array DALAM
    #      hanya untuk DB fingerprint) ----
    if len(m15["close"]) > 400:
        tail = {kk: vv[-320:] for kk, vv in m15.items()
                if isinstance(vv, list)}
    else:
        tail = m15
    cti = len(tail["close"]) - 2        # bar closed terakhir di ekor
    zones = detect_zones(tail, atr15, k, cti)
    highs, lows = swings(tail, int(k.get("zone_swing_strength", 3)))
    st_score, sl_ref_i, sl_ref_p = structure_state(highs, lows, cti)
    # ---- fingerprint ----
    vec = fp_vector(m15, ci, int(k.get("fp_sequence_len", 5)), atr15)
    m = fp_match_cached(symbol, m15, k) if vec else \
        {"sim": 0.0, "sample": 0, "win_rate": 0.0, "win1_rate": 0.0,
         "mfe": 0.0, "mae": 0.0, "db_bars": 0, "years": 0.0,
         "pending": 0}
    bias = fp_bias(m15, ci)

    # ---- kandidat setup: zona terdekat yg VALID & harga di dekatnya ----
    side = 0
    zone = None
    near_pad = float(k.get("zone_near_pad_atr", 0.35)) * atr15
    max_dist = float(k.get("max_entry_distance_atr", 1.0)) * atr15
    for z in sorted(zones, key=lambda z: abs(bid - z["center"])):
        if z["status"] in ("INVALID", "EXHAUSTED"):
            continue
        q = zone_quality(z, k)
        if q <= 0:
            continue
        near = (z["lo"] - near_pad) <= bid <= (z["hi"] + near_pad)
        # REVERSAL: harga DI/DEKAT zona (dua sisi)
        if near:
            if z["type"] == "SUPPORT":
                side, zone = 1, z
                break
            if z["type"] == "RESISTANCE":
                side, zone = -1, z
                break
        # BREAKOUT: close M15 melewati batas zona (wick saja bukan breakout)
        # dan harga belum lari terlalu jauh (no-chase)
        if z["type"] == "RESISTANCE" and \
                m15["close"][ci] > z["hi"] + 0.05 * atr15 and \
                0 < bid - z["hi"] <= max_dist:
            side, zone = 1, z
            break
        if z["type"] == "SUPPORT" and \
                m15["close"][ci] < z["lo"] - 0.05 * atr15 and \
                0 < z["lo"] - bid <= max_dist:
            side, zone = -1, z
            break
    if not zone or side == 0:
        res["why"] = "NO_ZONE: tidak ada zona valid di dekat harga"
        return res

    # ---- gerbang sebelum skor: cooldown / re-entry per zona ----
    zkey = "%s:%s" % (symbol, zone["id"])
    if st:
        cd = st.cooldown_until(symbol)
        if cd and now < cd:
            res["status"] = "BLOCKED"
            res["block_why"] = ("SKIP_DAILY_COOLDOWN exit %s (%d dtk)"
                                % (symbol, int(cd - now)))
            return res
        if st.attempts_of(zkey) >= int(k.get("zone_max_attempts", 2)):
            res["status"] = "BLOCKED"
            res["block_why"] = ("SKIP_ZONE_EXHAUSTED %s (%d percobaan)"
                                % (zone["id"], st.attempts_of(zkey)))
            return res

    # ---- EMA context M15 (acceptable, bukan hard-only) ----
    e13 = ema_at(tail, int(k.get("ema_fast", 13)))
    e21 = ema_at(m15, int(k.get("ema_slow", 21)))
    ema_ok = True
    ema_ctx = 0.5
    if e13 and e21:
        sep = (e13 - e21) / atr15
        ema_ctx = max(0.0, min(1.0, 0.5 + sep * 2.0))
        # blueprint: konteks "acceptable" -- lawan tren kuat = tolak
        if side > 0 and sep < -0.8:
            ema_ok = False
        if side < 0 and sep > 0.8:
            ema_ok = False
    # v4.12 (permintaan user): EMA13/21 M15 SUDAH BERSILANGAN arah
    # sinyal dlm beberapa bar terakhir = TREN VALID -> tidak diblok
    # konteks EMA + bonus skor.  Zona SNR/HH-HL tetap jadi syarat.
    _cu, _cd = ema_cross_state(tail["close"],
                               int(k.get("ema_fast", 13)),
                               int(k.get("ema_slow", 21)),
                               int(k.get("ema_cross_lookback", 5)))
    ema_cross = 1 if ((side > 0 and _cu) or (side < 0 and _cd)) else 0
    if ema_cross:
        ema_ok = True
        ema_ctx = max(ema_ctx, 0.75)
    regime_ok = True
    reg_align = 0.5
    if regime == "TREND_UP":
        reg_align = 1.0 if side > 0 else 0.0
        regime_ok = regime_ok and (side > 0 or reg_score > -0.9)
    elif regime == "TREND_DOWN":
        reg_align = 1.0 if side < 0 else 0.0
        regime_ok = regime_ok and (side < 0 or reg_score < 0.9)

    # ---- skor setup (blueprint s.11) ----
    zq = zone_quality(zone, k)
    fp_conf = m["sim"]
    if m["sample"] < int(k.get("fp_min_sample_size", 12)):
        fp_conf *= 0.5                  # sampel kecil -> confidence turun
    score = (_clamp100(zq) * float(k.get("w_zone", 30.0)) / 100.0
             + _clamp100(50.0 + 50.0 * st_score)
             * float(k.get("w_structure", 20.0)) / 100.0
             + _clamp100(ema_ctx * 100.0) * float(k.get("w_ema", 15.0)) / 100.0
             + _clamp100(fp_conf) * float(k.get("w_fingerprint", 25.0)) / 100.0
             + _clamp100(reg_align * 100.0) * float(k.get("w_regime", 10.0))
             / 100.0)
    if ema_cross:
        score += float(k.get("w_ema_cross", 8.0))   # v4.12 bonus tren
    score = round(_clamp100(score), 1)
    sname = "BUY" if side > 0 else "SELL"
    res["ema_cross"] = ema_cross

    zone["htf_align"] = 1 if ((side > 0 and regime == "TREND_UP")
                              or (side < 0 and regime == "TREND_DOWN")) \
        else (-1 if ((side > 0 and regime == "TREND_DOWN")
                     or (side < 0 and regime == "TREND_UP")) else 0)
    res["side"] = sname
    res["score"] = score
    res["mtf"] = {"final": score}
    for kk, vv in (("structure", zq), ("liquidity", zq * 0.8),
                   ("trend", ema_ctx * 100.0), ("momentum", 0.0),
                   ("volume", 0.0), ("orderflow", fp_conf)):
        b = dict.fromkeys(_COMP_KEYS, 0.0)
        s = dict.fromkeys(_COMP_KEYS, 0.0)
        tgt = b if side > 0 else s
        oth = s if side > 0 else b
        tgt[kk] = round(_clamp100(vv), 1)
        res["components_buy"], res["components_sell"] = b, s

    # ---- gerbang skor minimum & konteks ----
    if score < float(k.get("min_setup_score", 70.0)):
        res["status"] = "WAIT"
        res["why"] = ("skor setup %.1f < %.1f (zona %s %s, fp %.0f%%/%d)"
                      % (score, float(k.get("min_setup_score", 70.0)),
                         zone["type"], zone["status"], m["sim"], m["sample"]))
        return res
    if not ema_ok:
        res["status"] = "BLOCKED"
        res["block_why"] = "SKIP_TREND: EMA13/21 M5/M15 lawan arah kuat"
        return res
    # v4.24 (rumus user): reversal EMA13/21 + candle salah sisi -> SKIP
    # (dipasang SETELAH pintu cross-valid: aturan reversal user menang)
    _rvb, _rvw = ema_reversal_block(side, tail.get("close") or [],
                                    atr15, k)
    if _rvb:
        res["status"] = "BLOCKED"
        res["block_why"] = _rvw
        return res
    # v4.26 (permintaan user): filter kekuatan tren -- ADX M15 wajib > 25
    _axb, _axw = adx_gate(tail.get("high") or [], tail.get("low") or [],
                          tail.get("close") or [], k)
    if _axb:
        res["status"] = "BLOCKED"
        res["block_why"] = _axw
        return res
    # v4.29 (permintaan user): FILTER STRUKTUR MARKET (HH/HL, breakout,
    # ruang HH 1R) + FILTER ML lokal (belajar karakter market riwayat)
    _mb, _mw = msf_gate(side, tail, atr15, k)
    if _mb:
        res["status"] = "BLOCKED"
        res["block_why"] = _mw
        return res
    _lb, _lw = ml_gate(side, tail, atr15, k)
    if _lb:
        res["status"] = "BLOCKED"
        res["block_why"] = _lw
        return res
    if not regime_ok:
        res["status"] = "BLOCKED"
        res["block_why"] = "SKIP_TREND: regime H1 %s lawan" % regime
        return res
    if m["sim"] < float(k.get("fp_similarity_candidate", 80.0)):
        res["status"] = "BLOCKED"
        res["block_why"] = ("SKIP_FINGERPRINT: similarity %.1f%% < %.0f%%"
                            % (m["sim"],
                               float(k.get("fp_similarity_candidate", 80.0))))
        return res
    if m["sample"] < int(k.get("fp_min_sample_size", 12)):
        res["status"] = "BLOCKED"
        res["block_why"] = ("SKIP_SAMPLE_SIZE: %d sampel < %d"
                            % (m["sample"],
                               int(k.get("fp_min_sample_size", 12))))
        return res

    # ---- momentum M5 (timing; belum ada -> HOLD) ----
    mo_ok, mo_why, mo_str = m5_momentum(m5, side, atr5, k, zone=zone)
    res["components_buy"]["momentum" if side > 0 else "momentum"] = \
        round(mo_str * 100.0, 1)
    if not mo_ok:
        res["status"] = "HOLD"
        res["why"] = "MOMENTUM_WAIT: %s (zona %s skor %.1f)" \
            % (mo_why, zone["id"], score)
        if st:
            exp = int(k.get("setup_expiration_bars", 8))
            pend = st.pending.get(symbol)
            if pend and ci - pend.get("signal_bar", ci) > exp:
                st.clear(symbol)
                st.save()
                res["status"] = "WAIT"
                res["why"] = "SKIP_SETUP_EXPIRED (>%d bar M15)" % exp
            elif not pend:
                st.save_pending(symbol, sname, int(score), ci, ci)
                st.save()
        return res
    if st:
        st.clear(symbol)
        st.save()

    # ---- trigger M1 (presisi) ----
    t_ok, t_why = m1_trigger(m1, side, atr5, k)
    if not t_ok:
        res["status"] = "HOLD"
        res["why"] = "M1_WAIT: %s" % t_why
        return res

    # ---- siap dieksekusi: paket exec utk engine ----
    res["status"] = "READY"
    res["why"] = ("SETUP OK zona %s (%s, %s) skor %.1f | fp %.0f%%/%d "
                  "win%.0f%% | regime %s" % (zone["id"], zone["type"],
                                             zone["status"], score,
                                             m["sim"], m["sample"],
                                             m["win_rate"], regime))
    res["exec"] = {"sig": sname, "zone": dict(zone), "sim": m["sim"],
                   "sample": m["sample"], "win_rate": m["win_rate"],
                   "atr15": atr15, "atr5": atr5, "st_score": st_score,
                   "sl_ref": float(sl_ref_p) if sl_ref_p else None,
                   # v4.23: zona SNR LAWAN terdekat -- sniper M1 pakai
                   # ini agar entry tidak "buta zona" (wajib rejection
                   # bila harga menempel zona lawan)
                   "opp": (nearest_opposing(zones, side, bid, k) or None),
                   "zone_key": zkey, "regime": regime,
                   "ema_cross": ema_cross,
                   "hist_years": m.get("years", 0.0),
                   "db_bars": int(m.get("db_bars", 0))}
    return res


# ===========================================================================
# [11] VALIDATE EXECUTION -- gerbang KERAS pra-order (blueprint s.14)
# ===========================================================================
def validate_execution(symbol, res, data, bid, ask, k=None, st=None,
                       cooldown_until=0, open_baskets=0, spread_points=0,
                       warmup_left=0):
    k = k or {}
    ex = (res or {}).get("exec") or {}
    side = 1 if ex.get("sig") == "BUY" else (-1 if ex.get("sig") == "SELL" else 0)
    keep_wait = (False, "tidak ada paket eksekusi", 0.0, 0.0, False)
    if not ex or side == 0:
        return keep_wait
    atr15 = float(ex.get("atr15") or 0.0)
    atr5 = float(ex.get("atr5") or 0.0)
    zone = ex.get("zone") or {}
    info = data.get("info") or {}
    point = float(data.get("point") or info.get("point") or 0.0)
    if atr15 <= 0 or point <= 0:
        return (False, "SKIP_DATA_QUALITY: ATR/point belum siap",
                0.0, 0.0, True)
    entry = ask if side > 0 else bid

    # warmup engine
    if warmup_left and warmup_left > 0:
        return (False, "WARMUP %ds tersisa" % int(warmup_left),
                0.0, 0.0, True)
    # kuota portofolio (blueprint: MAX 5 = batas, bukan target)
    if open_baskets >= int(k.get("max_baskets", 5)):
        return (False, "SKIP_MAX_POSITIONS (%d terbuka)" % int(open_baskets),
                0.0, 0.0, True)
    # total open risk (aproksimasi: risk% x jumlah posisi)
    rpt = float(k.get("risk_per_trade_percent", 0.5))
    if (open_baskets + 1) * rpt > float(k.get("max_total_open_risk_pct", 15.25)):
        return (False, "SKIP_TOTAL_EXPOSURE (>%.2f%%)"
                % float(k.get("max_total_open_risk_pct", 15.25)),
                0.0, 0.0, True)
    # spread
    spr = int(info.get("spread_points", 0) or 0)
    lim = spread_limit(k, symbol, info.get("symbol"))
    if lim > 0 and spr > lim:
        return (False, "SKIP_SPREAD %d > %d" % (spr, lim), 0.0, 0.0, False)
    # cooldown exit
    if st and cooldown_until and time.time() < cooldown_until:
        return (False, "SKIP cooldown exit aktif", 0.0, 0.0, False)

    # ---- SL ENGINE: struktur + buffer ATR (blueprint s.15) ----
    sl_ref = ex.get("sl_ref")
    # v4.23 (laporan user "SL pertama kelewatan melebihi wick SNR
    # terdekat"): pilih struktur TERDEKAT di luar entry -- dulu min/max
    # justru mengambil struktur TERJAUH sehingga SL sering jauh di luar
    # wick SNR terdekat (risk besar percuma).
    if side > 0:
        cands = [v for v in (zone.get("lo"), sl_ref) if v and v < entry]
        if not cands:
            return (False, "SKIP_SL_TOO_TIGHT: tak ada struktur di bawah",
                    0.0, 0.0, False)
        sl_price = max(cands) - float(k.get("sl_structure_buffer_atr", 0.35)) * atr15
    else:
        cands = [v for v in (zone.get("hi"), sl_ref) if v and v > entry]
        if not cands:
            return (False, "SKIP_SL_TOO_TIGHT: tak ada struktur di atas",
                    0.0, 0.0, False)
        sl_price = min(cands) + float(k.get("sl_structure_buffer_atr", 0.35)) * atr15
    sl_dist = abs(entry - sl_price)
    ratio = sl_dist / atr15
    # v4.23: terlalu rapat TIDAK skip -- CLAMP ke lantai 0.45 ATR
    # (aturan user: SL dari struktur, min 0.45 ATR; entry tetap jalan).
    mn_r = float(k.get("min_sl_atr_ratio", 0.45))
    _clamped = False
    if ratio < mn_r:
        sl_price = entry - side * mn_r * atr15
        sl_dist = abs(entry - sl_price)
        ratio = sl_dist / atr15
        _clamped = True      # lantai user -- jangan di-skip lg sbg wide
    if ratio > float(k.get("max_sl_atr_ratio", 2.5)) and not _clamped:
        return (False, "SKIP_SL_TOO_WIDE (SL %.2fxATR > %.2f)"
                % (ratio, float(k.get("max_sl_atr_ratio", 2.5))),
                0.0, 0.0, False)

    # ---- TP ROOM 2R (blueprint s.17): zona lawan tak boleh memblokir ----
    rr = float(k.get("base_rr", 2.0))
    target = entry + side * rr * sl_dist
    opp = nearest_opposing(_zones_of(data, atr15, k), side, entry, k)
    if opp:
        buf = float(k.get("zone_oppose_buffer_atr", 0.30)) * atr15
        blocker = opp["lo"] - buf if side > 0 else opp["hi"] + buf
        if (side > 0 and blocker < target) or (side < 0 and blocker > target):
            return (False, "SKIP_TP_BLOCKED: zona %s memblokir 2R "
                    "(room s/d %.5f < target %.5f)"
                    % (opp["id"], blocker, target), 0.0, 0.0, False)
    # s.41 audit: teoretis TP, zona lawan terdekat, room utk jurnal
    ex["tp_target"] = round(target, 6)
    ex["opp_zone_id"] = (opp.get("id") if opp else None)
    ex["room2r_ok"] = True

    # ---- NO-CHASE (blueprint s.29): jarak dari TEPI zona (sisi terdekat)
    if side > 0:
        dist = max(0.0, entry - float(zone.get("hi", entry)))
    else:
        dist = max(0.0, float(zone.get("lo", entry)) - entry)
    if dist > float(k.get("max_entry_distance_atr", 1.0)) * atr15:
        return (False, "SKIP_CHASING (jarak %.2fxATR > %.2f)"
                % (dist / atr15, float(k.get("max_entry_distance_atr", 1.0))),
                0.0, 0.0, False)

    # ---- fingerprint & sample (double-check) ----
    if float(ex.get("sim", 0.0)) < float(k.get("fp_similarity_candidate", 80.0)):
        return (False, "SKIP_FINGERPRINT", 0.0, 0.0, False)
    if int(ex.get("sample", 0)) < int(k.get("fp_min_sample_size", 12)):
        return (False, "SKIP_SAMPLE_SIZE", 0.0, 0.0, False)

    # ---- TP akhir: pengaman jauh (trailing yang mengelola) ----
    cap = float(k.get("trail_hard_cap_r", 10.0))
    tp_price = (entry + side * cap * sl_dist) if cap > 0 else 0.0

    # ---- unit risiko trail = SL aktual (via sl_mult_eff, x ATR M5) ----
    atr_m5 = atr5 or atr15
    sl_mult_eff = sl_dist / atr_m5 if atr_m5 > 0 else \
        float(k.get("sl_atr", 1.2))

    # ---- catat percobaan per zona + journal (blueprint s.35, s.41) ----
    if st:
        st.attempt(ex.get("zone_key") or ("%s:%s" % (symbol, zone.get("id"))))
        st.save()
    _att = None
    try:
        _zk = ex.get("zone_key") or ""
        _att = int(getattr(st, "attempts", {}).get(_zk, 0)) if st else None
    except Exception:
        _att = None
    # s.41: EMA context dihitung lokal (closed closes M15) utk jurnal
    try:
        _c15 = [float(v) for v in
                ((data.get("m15") or {}).get("close") or [])][:-1]
        _e13s = ema_series(_c15, int(k.get("ema_fast", 13)))
        _e21s = ema_series(_c15, int(k.get("ema_slow", 21)))
        _e13v = _e13s[-1] if _e13s else None
        _e21v = _e21s[-1] if _e21s else None
    except Exception:
        _e13v = _e21v = None
    _sep = ((_e13v - _e21v) / atr15) if (_e13v is not None and
            _e21v is not None and atr15 and atr15 > 0) else None
    journal(os.path.join("data", "s3_journal.jsonl"), {
        "symbol": symbol, "side": ex.get("sig"), "zone_id": zone.get("id"),
        "zone_type": zone.get("type"), "zone_status": zone.get("status"),
        "zone_strength": zone.get("strength"), "zone_touches": zone.get("touches"),
        "zone_rejections": zone.get("rejection_count"),
        "zone_breakout": zone.get("breakout_status"),
        "htf_align": zone.get("htf_align"),
        "score": res.get("score"), "sim": ex.get("sim"),
        "sample": ex.get("sample"), "win_rate": ex.get("win_rate"),
        "ema13": (round(float(_e13v), 6) if _e13v is not None else None),
        "ema21": (round(float(_e21v), 6) if _e21v is not None else None),
        "ema_sep_atr": (round(float(_sep), 3) if _sep is not None else None),
        "atr15": round(float(atr15), 6), "sl_ref": ex.get("sl_ref"),
        "entry": round(entry, 6), "sl": round(sl_price, 6),
        "tp": round(tp_price, 6), "tp_target": ex.get("tp_target"),
        "opp_zone_id": ex.get("opp_zone_id"),
        "room2r_ok": ex.get("room2r_ok"), "sl_atr": round(ratio, 2),
        "hist_years": ex.get("hist_years"), "db_bars": ex.get("db_bars"),
        "attempt": _att, "spread": spr,
        "ema_cross": int(ex.get("ema_cross", 0) or 0),
        "reason": "ENTRY_APPROVED",
        "regime": ex.get("regime"), "session": session_of()})
    why = ("ENTRY_APPROVED %s zona %s | SL %.2fxATR | %d sampel fp %.0f%%"
           % (ex.get("sig"), zone.get("id"), ratio,
              int(ex.get("sample", 0)), float(ex.get("sim", 0.0))))
    ex["sl_mult_eff"] = sl_mult_eff
    return (True, why, sl_price, tp_price, False)


def _zones_of(data, atr15, k):
    """Zona segar utk cek TP room (dihitung ulang dr data saat ini)."""
    try:
        return detect_zones(data.get("m15") or {}, atr15, k)
    except Exception:
        return []
