# -*- coding: utf-8 -*-
"""======================================================================
STRATEGY 4 - TEMPLATE KOSONG (permintaan user: parameter entry, logic
entry, dan filter DIKOSONGKAN SEMUA - akan diisi baru).

ISI STRATEGI BARU DI SINI:
  1) evaluate()        <- di bawah, satu-satunya titik keputusan entry.
                          Kembalikan _result(...) dgn "exec" berisi paket
                          order saat sinyal layak (lihat contoh komentar).
  2) validate_execution() <- filter eksekusi terakhir sebelum order
                          dikirim (sementara: selalu blokir karena kosong).
  3) Parameter angka   <- taruh di cc_config.py DEFAULTS["s3"] (sekarang
                          {}) dan baca lewat k = k or {} di evaluate.

YANG TERSISA HANYA INFRAstruktur (dipanggil engine, JANGAN dihapus):
  Strategy2State (state file), merge_bars (gabung history), journal,
  hist_paged/hist_years (loader), session_of/data_quality/spread_limit/
  pip_entry_plan (gerbang data), ATRTrail + tp_ladder (manajemen posisi),
  serta ALAT MATEMATIKA netral utk dipakai strategi baru: ema/atr/swings.
Tidak ada satu pun logika entry/filter/parameter warisan Strategy 3.
======================================================================"""
import hashlib
import json
import math
import os
import time


# ============================ ALAT MATEMATIKA (netral) ============================

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


# ============================ INFRA DATA ENGINE ==================================

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


# ============================ STATE + JOURNAL (infra) ============================

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


# ============================ MANAJEMEN POSISI (infra exit) ======================

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


# ============================ HASIL (plumbing) ===================================

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


# ============================ PARAMETER (KOSONG) =================================

def s2_cfg(cfg):
    """S4: parameter strategy DIKOSONGKAN (user isi baru).  Kembalikan
    dict kosong - tidak ada satu pun parameter warisan S3."""
    return {}


# ============================ FILTER EKSEKUSI (KOSONG) ===========================

def validate_execution(symbol, res, data, bid, ask, k=None, st=None,
                       cooldown_until=0, open_baskets=0, spread_points=0,
                       warmup_left=0):
    """S4: filter eksekusi DIKOSONGKAN (user isi baru).  Sementara
    SELALU blokir - tidak pernah ada paket eksekusi yang lolos."""
    return (False, "filter eksekusi kosong - strategy 4 belum diisi",
            0.0, 0.0, False)


# ============================ EVALUATE (TITIK ISI STRATEGI BARU) =================

def evaluate(symbol, data, k=None, st=None):
    """S4: LOGIC ENTRY DIKOSONGKAN - selalu WAIT sampai user mengisi
    strategi baru.  (Baris di bawah adalah satu-satunya isi file ini.)"""
    return _result(symbol, data, "WAIT",
                   "template kosong -- entry/logic/filter menunggu diisi baru")

# ---------------------------------------------------------------------------
# PANDUAN MENGISI (contoh bentuk, hapus saat mengisi):
#   def evaluate(symbol, data, k=None, st=None):
#       k = k or {}
#       ... hitung sinyal dari data["m15"]/data["m5"]/data["m1"]/data["h1"]
#       ... gunakan alat netral di atas (ema_at, atr_at, swings)
#       layak  -> return _result(symbol, data, "BUY"/"SELL", "alasan") dgn
#                 res["exec"] = {"sig":..,"price":..,"sl":..,"tp":..,"lot":..}
#                 res["score"], res["components_buy"/"_sell"] utk conformance
#       tidak  -> return _result(symbol, data, "WAIT", "alasan menolak")
# ---------------------------------------------------------------------------
