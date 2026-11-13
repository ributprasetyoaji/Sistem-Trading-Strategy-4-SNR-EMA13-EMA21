"""Broker layer untuk Python Command Center.

Dua implementasi dengan antarmuka sama:
  - MT5Broker        : koneksi NYATA ke terminal MetaTrader 5 (Windows + paket
                       `MetaTrader5`). Python yang mengirim order langsung
                       (order_send) -> "perintah dari Python".
  - SimulationBroker : market buatan (random-walk) supaya dashboard & scanner
                       bisa dites/dilihat tanpa MT5.

Kalau MetaTrader5 tidak tersedia / terminal tidak jalan -> otomatis SIM.
"""
from __future__ import annotations

import math
import os
import random
import threading
import types
import time

try:  # hanya ada di Windows VPS dengan terminal MT5 terpasang
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except Exception:
    mt5 = None
    MT5_AVAILABLE = False


ORDER_TYPE_BUY = "BUY"
ORDER_TYPE_SELL = "SELL"


def filling_prefs(flags):
    """v3.36: bitmask filling simbol (1=FOK, 2=IOC) -> urutan preferensi.
    Selalu diakhiri fallback lengkap [IOC, FOK, RETURN] agar error MT5
    10030 'Unsupported filling mode' tidak pernah mati total."""
    prefs = []
    if flags & 1:
        prefs.append("FOK")
    if flags & 2:
        prefs.append("IOC")
    for f in ("IOC", "FOK", "RETURN"):
        if f not in prefs:
            prefs.append(f)
    return prefs


def send_deal(mt5mod, req, prefs, on_ping=None):
    """v3.36: kirim order dgn TANGGA FILLING. Retry HANYA utk retcode 10030
    (Unsupported filling mode) -> coba mode berikutnya. Return (result, mode)."""
    t0 = time.time()
    r = None
    for f in prefs:
        req["type_filling"] = f
        r = mt5mod.order_send(req)
        if r is None:
            break  # terminal tidak siap -> retry filling tidak menolong
        if r.retcode == mt5mod.TRADE_RETCODE_DONE:
            break
        if r.retcode != getattr(mt5mod, "TRADE_RETCODE_INVALID_FILL", 10030):
            break  # error lain (harga/margin/dll) -> kembalikan apa adanya
    if on_ping:
        on_ping(int((time.time() - t0) * 1000))
    return r, req.get("type_filling")


class OrderResult:
    def __init__(self, ok, ticket=0, retcode=0, comment=""):
        self.ok = ok
        self.ticket = ticket
        self.retcode = retcode
        self.comment = comment

    def __repr__(self):
        return "OrderResult(ok=%s, ticket=%s, rc=%s, %s)" % (
            self.ok, self.ticket, self.retcode, self.comment)


def find_terminal_paths():
    """Cari terminal64.exe di lokasi standar Windows (semua folder broker)."""
    import glob
    out = []
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    for root in roots:
        for pat in ("*MetaTrader*", "*MT5*", "*Meta*"):
            try:
                out += glob.glob(root + os.sep + pat + os.sep + "terminal64.exe")
            except Exception:
                pass
    return sorted(set(out))



def read_mt5_path_file(pf="MT5_PATH.txt"):
    """Baris pertama VALID di MT5_PATH.txt (baris kosong/# diabaikan).
    File ini = kunci pilihan terminal MT5 saat VPS berisi beberapa terminal."""
    try:
        with open(pf, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    ln = ln.strip('"').strip()
                    # normalisasi dobel-backslash (hasil copy dari JSON),
                    # kecuali UNC path (\\server\share)
                    if not ln.startswith("\\\\"):
                        ln = ln.replace("\\\\", "\\")
                    return ln
    except Exception:
        pass
    return ""


def write_mt5_path_file(path, pf="MT5_PATH.txt"):
    """Simpan terminal yang sukses dipakai (sticky: run berikutnya sama)."""
    try:
        with open(pf, "w", encoding="utf-8") as f:
            f.write("# Terminal MT5 yang dipakai robot ini (auto-tersimpan).\n")
            f.write("# Ganti path di bawah utk memakai terminal lain.\n")
            f.write(str(path).strip() + "\n")
        return True
    except Exception:
        return False


def build_attempts(cfg, pf="MT5_PATH.txt"):
    """Urutan pemilihan terminal MT5 (fungsi murni, testable):
    1) cfg mt5_terminal_path  2) MT5_PATH.txt  3) terminal yang sudah jalan
    4) hasil scan Program Files.  VPS multi-terminal WAJIB isi (1) atau (2)
    supaya tidak salah konek ke akun broker yang salah."""
    attempts = []
    if cfg.get("mt5_terminal_path"):
        attempts.append({"path": cfg["mt5_terminal_path"], "src": "config"})
    p = read_mt5_path_file(pf)
    if p:
        attempts.append({"path": p, "src": "MT5_PATH.txt"})
    attempts.append({"src": "attach"})          # terminal yang sudah jalan
    for pth in find_terminal_paths():
        attempts.append({"path": pth, "src": "scan"})
    return attempts

def rates_to_py(r):
    """copy_rates MT5 (numpy array) -> dict list python murni.

    numpy.int64/float64 TIDAK bisa diserialisasi json -> dashboard error.
    Semua dikonversi di sini, di pintu masuk data.
    """
    return {"time": [int(t) for t in r["time"]],
            "open": [float(v) for v in r["open"]],
            "high": [float(v) for v in r["high"]],
            "low": [float(v) for v in r["low"]],
            "close": [float(v) for v in r["close"]],
            "tick_volume": [int(v) for v in r["tick_volume"]]}


SYMBOL_SUFFIXES = ["", "m", "c", "z", "i", "pro", ".a", ".c", ".m", ".pro",
                   ".standard", ".raw", "#", "-ecn"]


def match_symbol(want, alts, names, suffixes=SYMBOL_SUFFIXES):
    """Cocokkan nama pair dgn daftar nama symbol broker (fungsi murni, uji-able).

    Urutan prioritas:
      1. persis sama            (USTEC == USTEC)
      2. persis + akhiran       (USTEC -> USTECm, akun Standard Exness)
      3. diawali nama alternat  (NAS100 -> NAS100.a)
      4. mengandung nama        (paling longgar)
    Return nama ASLI di broker, atau "" kalau tidak ada.
    """
    up = {n.upper(): n for n in names}
    for a in alts:
        if a.upper() in up:
            return up[a.upper()]
    for a in alts:
        for suf in suffixes:
            c = (str(a) + suf).upper()
            if c in up:
                return up[c]
    for a in alts:
        au = str(a).upper()
        for n in sorted(names):          # sorted -> hasil deterministik
            if n.upper().startswith(au):
                return n
    for a in alts:
        au = str(a).upper()
        for n in sorted(names):
            if au in n.upper():
                return n
    return ""


# ---------------------------------------------------------------------------
# MT5 REAL
# ---------------------------------------------------------------------------
_TF_NAMES = frozenset(("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"))


def tf_known(tf):
    """True bila nama timeframe dikenal (pure, tanpa modul MT5)."""
    return str(tf).upper() in _TF_NAMES


def mt5_timeframe(tf):
    """String timeframe -> konstanta MT5; None bila tak dikenal/mt5 tak ada.
    (v3.20: dict lama sempit -> KeyError 'H1' = loop error & tak ada entry)."""
    t = str(tf).upper()
    if t not in _TF_NAMES:
        return None
    try:
        return getattr(mt5, "TIMEFRAME_" + t)
    except Exception:
        return None


def _round30(raw):
    """Bulatkan detik ke kelipatan 30 menit (offset server broker)."""
    return int(round(raw / 1800.0) * 1800.0)


def _day_start_from(now_ts, off_s):
    """Epoch tengah malam 'hari' menurut zona waktu offset off_s detik."""
    import calendar
    d0 = time.strftime("%Y-%m-%d", time.gmtime(now_ts + off_s))
    return calendar.timegm(time.strptime(d0, "%Y-%m-%d")) - off_s


def _agg_deals(deals, since, t_buy=0, t_sell=1, t_bal=2):
    """v3.55: rekap harian = PERSIS cara user membaca riwayat broker.

    - PROFIT TERCATAT = SEMUA event close untung (TP/close manual): deal
      OUT/INOUT/OUT_BY hari broker dgn profit(+swap) >= 0, dijumlah.
    - LOSS TERCATAT   = SEMUA event close rugi (mines/loss/SL): deal close
      dgn profit(+swap) < 0, nilai positifnya dijumlah. Partial close
      dihitung per event-nya masing-masing.
    - KOMISI          = komisi SEMUA deal hari broker (entry open MAUPUN
      close). Akun spread -> deal tanpa komisi -> otomatis 0.
    - realized        = profit+swap+komisi semua deal (perubahan balance).
    Deposit/WD (deal balance) TIDAK masuk P/L, tapi dihitung terpisah
    sbg bal_ops utk rekonstruksi day_start. Murni - dites tanpa MT5."""
    profit = comm = 0.0
    lots = 0.0
    gw = gl = 0.0
    wins = losses = 0
    ndeal = 0
    bal_ops = 0.0
    for d in deals or []:
        if getattr(d, "type", -1) == t_bal:
            bal_ops += float(getattr(d, "profit", 0.0) or 0.0)
            continue                       # deposit/WD: keluar dari P/L
        if getattr(d, "type", -1) not in (t_buy, t_sell):
            continue                       # kredit/bonus dll: abaikan
        if int(getattr(d, "time", 0) or 0) < int(since):
            continue                       # di luar hari broker
        ndeal += 1
        pv = (float(getattr(d, "profit", 0.0) or 0.0)
              + float(getattr(d, "swap", 0.0) or 0.0))
        profit += pv
        comm += float(getattr(d, "commission", 0.0) or 0.0)
        if getattr(d, "entry", 0) in (1, 2, 3):
            lots += float(getattr(d, "volume", 0.0) or 0.0)
            if pv >= 0:
                wins += 1
                gw += pv
            else:
                losses += 1
                gl += -pv
    return {"realized": round(profit + comm, 2),
            "profit_deal": round(profit, 2),
            "commission": round(comm, 2),
            "lots": round(lots, 2),
            "wins": wins, "losses": losses,
            "gross_win": round(gw, 2), "gross_loss": round(gl, 2),
            "deals": ndeal, "bal_ops": round(bal_ops, 2)}


def classify_account_deals(deals, t_buy=0, t_sell=1, eps=0.01):
    """v3.98 DETEKSI MODEL AKUN (murni, dites tanpa MT5):
    komisi AKTUAL semua deal (entry+close) dalam window history.
    - SPREAD  : total komisi ~0 -> akun 0-komisi (biaya lewat spread);
                estimasi komisi config HARUS dimatikan.
    - KOMISI  : ada komisi -> komisi/lot roundtrip = |total komisi| /
                total lot CLOSED (deal OUT).
    - UNKNOWN : belum ada deal (akun baru / data kosong) -> fallback
                config.
    Komisi broker dicatat NEGATIF -> dipakai nilai absolutnya."""
    ndeal = 0
    comm_total = 0.0
    closed_lots = 0.0
    for d in deals or []:
        if getattr(d, "type", -1) not in (t_buy, t_sell):
            continue
        ndeal += 1
        comm_total += float(getattr(d, "commission", 0.0) or 0.0)
        if getattr(d, "entry", 0) in (1, 2, 3):
            closed_lots += float(getattr(d, "volume", 0.0) or 0.0)
    if ndeal <= 0:
        return {"model": "UNKNOWN", "comm_per_lot": 0.0, "deals": 0,
                "comm_total": 0.0, "closed_lots": 0.0}
    if abs(comm_total) <= eps:
        return {"model": "SPREAD", "comm_per_lot": 0.0, "deals": ndeal,
                "comm_total": round(comm_total, 2),
                "closed_lots": round(closed_lots, 2)}
    if closed_lots <= 0:
        return {"model": "UNKNOWN", "comm_per_lot": 0.0, "deals": ndeal,
                "comm_total": round(comm_total, 2), "closed_lots": 0.0}
    return {"model": "KOMISI",
            "comm_per_lot": round(abs(comm_total) / closed_lots, 4),
            "deals": ndeal, "comm_total": round(comm_total, 2),
            "closed_lots": round(closed_lots, 2)}



class MT5Broker:
    is_sim = False

    def __init__(self, cfg, log=print):
        self.cfg = cfg
        self.log = log
        self.connected = False
        self.last_ping_ms = 0
        # v4.19 ANTI-BENGONG: MetaTrader5 IPC TIDAK thread-safe -- dulu
        # thread dashboard (account/positions/closed_stats tiap 2 dtk)
        # dan loop utama (copy_rates 22 pair) saling menerobos -> hasil
        # None massal / panggilan gantung = 'momentum 0% semua pair'.
        self._ipc = threading.RLock()

    # -- koneksi ------------------------------------------------------------
    def connect(self) -> bool:
        """Pilih terminal MT5 yang BENAR (VPS bisa berisi beberapa terminal
        MT5 sekaligus): 1) cfg mt5_terminal_path -> 2) file MT5_PATH.txt ->
        3) terminal yang sudah jalan -> 4) scan Program Files.  Terminal
        yang sukses di-INGAT ke MT5_PATH.txt (sticky).  Akun diverifikasi
        bila cfg mt5_login diisi: salah akun -> engine MENOLAK jalan."""
        if not MT5_AVAILABLE:
            return False
        creds = {}
        if (self.cfg.get("mt5_login") and self.cfg.get("mt5_password")
                and self.cfg.get("mt5_server")):
            creds = {"login": int(self.cfg["mt5_login"]),
                     "password": str(self.cfg["mt5_password"]),
                     "server": str(self.cfg["mt5_server"])}
        pf = "MT5_PATH.txt"
        used_saved = read_mt5_path_file(pf)
        for kw in build_attempts(self.cfg, pf):
            src = kw.pop("src", "")
            try:
                if not mt5.initialize(**dict(kw, **creds)):
                    continue
                acc = mt5.account_info()
                if acc is None and creds:
                    mt5.login(**creds)
                    acc = mt5.account_info()
                if acc is None:
                    # terminal terbuka tapi belum login -> jangan tutup terminalnya
                    self.log("[BROKER] MT5 terbuka tapi belum login akun manapun")
                    return False
                # v3.44: ANTI SALAH AKUN -- kalau config menetapkan nomor
                # akun dan ternyata konek ke akun lain -> login ulang;
                # tetap tidak cocok -> STOP (keamanan dana di atas segalanya)
                want = int(self.cfg.get("mt5_login") or 0)
                if want and acc.login != want:
                    self.log("[PROTECT] AKUN BERBEDA: konek ke %s@%s, "
                             "config minta %s -> coba login ulang..."
                             % (acc.login, acc.server, want))
                    mt5.login(**creds)
                    acc = mt5.account_info()
                    if acc is None or acc.login != want:
                        self.log("[PROTECT] Akun tetap tidak cocok dgn "
                                 "mt5_login=%s. Engine TIDAK jalan. Pilih "
                                 "terminal lain di MT5_PATH.txt / perbaiki "
                                 "login di cc_config.json." % want)
                        return False
                # sticky: ingat terminal terpilih (kecuali sudah sama)
                try:
                    ti = mt5.terminal_info()
                    used_path = kw.get("path") or (getattr(ti, "path", "") or "")
                    if used_path and used_path.replace("/", "\\") != used_saved.replace("/", "\\"):
                        write_mt5_path_file(used_path, pf)
                        self.log("[BROKER] Terminal dipilih (%s): %s "
                                 "-> tersimpan di MT5_PATH.txt"
                                 % (src or "attach", used_path))
                except Exception:
                    pass
                self.connected = True
                self.log("[BROKER] MT5 tersambung: akun %s (%s) server=%s"
                         % (acc.login, acc.currency, acc.server))
                return True
            except Exception:
                continue
        cand = find_terminal_paths()
        self.log("[BROKER] GAGAL konek MT5. Terminal ketemu: %s. Pilih "
                 "manual: isi path terminal64.exe di MT5_PATH.txt (folder "
                 "robot) atau mt5_terminal_path di cc_config.json."
                 % (cand or "tidak ada"))
        return False

    def shutdown(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()

    # -- symbol -------------------------------------------------------------
    def resolve_symbol(self, want: str) -> str:
        """Cari nama symbol di broker (NAS100=USTEC/USTECm di Exness dll)."""
        alts = self.cfg.get("symbol_alternates", {}).get(want, [want])
        try:
            allsyms = mt5.symbols_get() or []
        except Exception:
            allsyms = []
        names = [s.name for s in allsyms]
        got = match_symbol(want, alts, names)
        if got:
            self._select(got)
        return got

    def _select(self, sym):
        try:
            mt5.symbol_select(sym, True)
        except Exception:
            pass

    def symbol_info(self, sym) -> dict:
        si = mt5.symbol_info(sym)
        st = mt5.symbol_info_tick(sym)
        if si is None:
            return {}
        point = si.point or 10 ** -si.digits
        bid = st.bid if st else 0.0
        ask = st.ask if st else 0.0
        return {
            "symbol": sym, "digits": si.digits, "point": point,
            "bid": bid, "ask": ask,
            "spread_points": round((ask - bid) / point) if point else 0,
            "trade_tick_value": si.trade_tick_value or 0.0,
            "trade_tick_size": si.trade_tick_size or point,
            "volume_min": si.volume_min or 0.01,
            "volume_max": si.volume_max or 100.0,
            "volume_step": si.volume_step or 0.01,
        }

    # -- data ----------------------------------------------------------------
    def copy_rates(self, sym, timeframe, count):
        tf = mt5_timeframe(timeframe)
        if tf is None:
            return None                    # timeframe tak dikenal -> caller fallback
        r = mt5.copy_rates_from_pos(sym, tf, 0, count)
        if r is None:
            return None
        return rates_to_py({"time": r["time"], "open": r["open"],
                            "high": r["high"], "low": r["low"],
                            "close": r["close"], "tick_volume": r["tick_volume"]})

    def copy_rates_before(self, sym, timeframe, count, anchor):
        """v3.81 HALAMAN RIWAYAT DALAM (blueprint s.3): bar LEBIH LAMA dr
        posisi `anchor` (anchor = jumlah bar yang sudah dimiliki, hitung
        dari terbaru=0).  Return dict rates ascending spt copy_rates atau
        None kalau broker tak punya lebih."""
        tf = mt5_timeframe(timeframe)
        if tf is None or int(count) <= 0:
            return None
        try:
            r = mt5.copy_rates_from_pos(sym, tf, int(anchor), int(count))
        except Exception:
            return None
        if r is None or len(r) == 0:
            return None
        return rates_to_py({"time": r["time"], "open": r["open"],
                            "high": r["high"], "low": r["low"],
                            "close": r["close"],
                            "tick_volume": r["tick_volume"]})

    def tick_delta(self, sym, seconds=300):
        """Delta agresor dari tick flags. Fallback: arah candle M1."""
        from datetime import datetime, timedelta
        to = datetime.now() + timedelta(minutes=1)
        frm = to - timedelta(seconds=seconds)
        bv = sv = 0.0
        have_flags = False
        try:
            ticks = mt5.copy_ticks_range(sym, frm, to, mt5.COPY_TICKS_TRADE)
            if ticks is not None and len(ticks) and "flags" in ticks.dtype.names:
                have_flags = True
                for t in ticks:
                    f = t["flags"]
                    vol = t["volume"] or 1.0
                    if f & 32:    # TICK_FLAG_BUY
                        bv += vol
                    elif f & 64:  # TICK_FLAG_SELL
                        sv += vol
        except Exception:
            have_flags = False
        if not have_flags or (bv + sv) == 0:
            m1 = self.copy_rates(sym, "M1", max(2, min(seconds // 60, 60)))
            if m1:
                for o, c, v in zip(m1["open"], m1["close"], m1["tick_volume"]):
                    if c >= o:
                        bv += v
                    else:
                        sv += v
        return {"buy": float(bv), "sell": float(sv)}

    # -- akun ----------------------------------------------------------------
    def account(self) -> dict:
        a = mt5.account_info()
        if a is None:
            return {}
        return {"login": a.login, "name": a.name, "currency": a.currency,
                "leverage": a.leverage, "server": a.server,
                "balance": a.balance, "equity": a.equity, "margin": a.margin}

    def positions(self) -> list:
        """v3.26: posisi BOT + posisi MANUAL user (magic 0) — semua sistem
        pelindung (trailing/MTRAIL/basket/smart exit) mengelola keduanya.
        Posisi EA lain (magic beda) tetap tidak disentuh."""
        manage = bool(self.cfg.get("manage_manual_positions", True))
        bot_magic = self.cfg.get("magic")
        out = []
        for p in (mt5.positions_get() or []):
            inc, manual = include_position(p.magic, bot_magic, manage)
            if not inc:
                continue  # posisi EA lain tidak disentuh
            try:
                pt = mt5.symbol_info(p.symbol)
                point = float(pt.point) if pt and pt.point else 0.0
                digits = int(pt.digits) if pt else 2
            except Exception:
                point, digits = 0.0, 2
            out.append({"ticket": p.ticket, "symbol": p.symbol,
                        "type": "BUY" if p.type == 0 else "SELL",
                        "lot": p.volume, "entry": p.price_open,
                        "sl": p.sl, "tp": p.tp,
                        "price": p.price_current, "pl": p.profit,
                        "time": p.time, "trailing": False,
                        "manual": manual,
                        "point": point, "digits": digits})
        return out

    def server_time(self):
        st = None
        for s in ("EURUSD",) + tuple(self.cfg.get("symbols", [])[:3]):
            try:
                st = mt5.symbol_info_tick(s)
            except Exception:
                st = None
            if st and getattr(st, "time", 0):
                return time.localtime(st.time)
        return time.localtime()

    def usd_to_account_rate(self, currency: str) -> float:
        """Kurs 1 USD -> mata uang akun (untuk konversi komisi)."""
        if currency == "USD":
            return 1.0
        for cand in ("USD" + currency, currency + "USD"):
            try:
                si = mt5.symbol_info(cand)
                st = mt5.symbol_info_tick(cand)
            except Exception:
                si = st = None
            if si and st:
                mid = (st.bid + st.ask) / 2
                if not mid:
                    continue
                return mid if cand == "USD" + currency else 1.0 / mid
        return 0.0  # tidak ketemu -> komisi diabaikan (dengan warning)

    def account_model(self, days=45, ttl=6 * 3600):
        """v3.98 DETEKSI MODEL AKUN dari komisi AKTUAL deal history
        (window `days` hari, cache `ttl` detik -- scan history mahal,
        jangan tiap tick).  Return dict classify_account_deals, atau
        None bila MT5 tak tersedia (pemanggil pakai fallback config)."""
        now = time.time()
        prev = getattr(self, "_acc_model", None)
        if prev and now - getattr(self, "_acc_model_ts", 0.0) < ttl:
            return prev
        try:
            from datetime import datetime
            frm = datetime.fromtimestamp(max(0, now - int(days) * 86400))
            to = datetime.fromtimestamp(now + 3600)
            if mt5 is None:
                return prev
            try:
                deals = mt5.history_deals_get(frm, to) or []
            except Exception:
                deals = []
            m = classify_account_deals(deals)
        except Exception:
            return prev          # MT5 bermasalah -> cache lama bila ada
        if not prev or prev.get("model") != m.get("model") \
                or prev.get("comm_per_lot") != m.get("comm_per_lot"):
            try:
                if m["model"] == "SPREAD":
                    self.log("[AKUN] Model akun: SPREAD (0 komisi) -- "
                             "estimasi komisi DIMATIKAN, biaya = spread")
                elif m["model"] == "KOMISI":
                    self.log("[AKUN] Model akun: KOMISI (aktual %.4f/"
                             "lot roundtrip, %d deal)"
                             % (m["comm_per_lot"], m["deals"]))
                else:
                    self.log("[AKUN] Model akun belum terdeteksi "
                             "(belum ada deal) -> pakai config")
            except Exception:
                pass
        self._acc_model = m
        self._acc_model_ts = now
        return m

    def eff_comm_usd_per_lot(self, cfg=None, usd_rate=0.0):
        """v3.98 Komisi efektif per lot dalam USD utk kalkulasi risiko.
        DETEKSI model akun menang atas config:  SPREAD -> 0 (akun
        0-komisi, biaya lewat spread);  KOMISI -> komisi/mot (mata
        uang akun) / kurs;  UNKNOWN -> fallback config (USD)."""
        try:
            m = self.account_model()
        except Exception:
            m = None
        rate = float(usd_rate or 0.0)
        if m and m.get("model") == "SPREAD":
            return 0.0
        if m and m.get("model") == "KOMISI":
            v = float(m.get("comm_per_lot") or 0.0)
            return v / rate if rate > 0 else v
        return float((cfg or {}).get("commission_per_lot_usd", 0.0))


    # -- order ----------------------------------------------------------------
    def _filling_candidates(self, sym):
        """v3.36: baca bitmask filling simbol dgn NAMA FIELD YG BENAR
        (filling_mode; trade_fill_flags cuma fallback lama) -> daftar mode."""
        flags = 0
        try:
            si = mt5.symbol_info(sym)
            for attr in ("filling_mode", "trade_fill_flags"):
                flags = getattr(si, attr, 0) or 0
                if flags:
                    break
        except Exception:
            flags = 0
        cmap = {"FOK": mt5.ORDER_FILLING_FOK,
                "IOC": mt5.ORDER_FILLING_IOC,
                "RETURN": mt5.ORDER_FILLING_RETURN}
        return [cmap[n] for n in filling_prefs(int(flags))]

    def order_send(self, sym, side, lot, sl, tp, comment="CC"):
        si = mt5.symbol_info(sym)
        st = mt5.symbol_info_tick(sym)
        if si is None or st is None:
            return OrderResult(False, retcode=-1, comment="symbol tidak tersedia")
        price = st.ask if side == ORDER_TYPE_BUY else st.bid
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(lot),
            "type": mt5.ORDER_TYPE_BUY if side == ORDER_TYPE_BUY else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": float(sl), "tp": float(tp),
            "deviation": int(self.cfg.get("deviation_points", 50)),
            "magic": int(self.cfg.get("magic", 777001)),
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        # v3.36: tangga filling (FOK/IOC/RETURN sesuai simbol) - anti error
        # "Unsupported filling mode" (USDJPY dsb.)
        r, used = send_deal(mt5, req, self._filling_candidates(sym),
                            on_ping=lambda ms: setattr(self, "last_ping_ms", ms))
        if r is None:
            return OrderResult(False, retcode=-1,
                               comment="order_send None (aktifkan Algo Trading)")
        if r.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(False, ticket=getattr(r, "order", 0),
                               retcode=r.retcode,
                               comment="%s (filling=%s)" % (r.comment, used))
        return OrderResult(True, ticket=getattr(r, "order", 0),
                           retcode=r.retcode, comment="OK")

    def modify_sl(self, ticket, sl, tp=None):
        p = mt5.positions_get(ticket=ticket)
        if not p:
            return False
        p = p[0]
        req = {"action": mt5.TRADE_ACTION_SLTP, "position": ticket,
               "symbol": p.symbol, "sl": float(sl),
               "tp": float(tp if tp is not None else p.tp)}
        r = mt5.order_send(req)
        return bool(r and r.retcode == mt5.TRADE_RETCODE_DONE)

    def close_volume(self, ticket, volume):
        """v4.12: tutup SEBAGIAN posisi (TP1 75%).  Volume dibulatkan
        ke step broker; kalau hasil pembulatan >= volume posisi ->
        jadi full close.  Return OrderResult."""
        p = mt5.positions_get(ticket=ticket)
        if not p:
            return OrderResult(False, comment="posisi tidak ada")
        p = p[0]
        si = mt5.symbol_info(p.symbol)
        step = float(getattr(si, "volume_step", 0.0) or 0.0) if si else 0.0
        vmin = float(getattr(si, "volume_min", 0.0) or 0.0) if si else 0.0
        vol = float(volume or 0.0)
        if step > 0:
            vol = float(int(vol / step + 1e-9) * step)
        if vol <= 0 or (vmin > 0 and vol < vmin - 1e-12) \
                or vol >= float(p.volume) - 1e-12:
            return self.close_position(ticket)   # fallback: penuh
        st = mt5.symbol_info_tick(p.symbol)
        price = st.bid if p.type == 0 else st.ask
        req = {"action": mt5.TRADE_ACTION_DEAL, "position": ticket,
               "symbol": p.symbol, "volume": vol,
               "type": mt5.ORDER_TYPE_SELL if p.type == 0
               else mt5.ORDER_TYPE_BUY,
               "price": price,
               "deviation": int(self.cfg.get("deviation_points", 50)),
               "magic": int(self.cfg.get("magic", 777001)),
               "comment": "CC-TP1", "type_time": mt5.ORDER_TIME_GTC}
        r, used = send_deal(mt5, req, self._filling_candidates(p.symbol))
        ok = bool(r and r.retcode == mt5.TRADE_RETCODE_DONE)
        return OrderResult(ok, retcode=getattr(r, "retcode", -1),
                           comment="close-partial")

    def close_position(self, ticket):
        p = mt5.positions_get(ticket=ticket)
        if not p:
            return OrderResult(False, comment="posisi tidak ada")
        p = p[0]
        st = mt5.symbol_info_tick(p.symbol)
        price = st.bid if p.type == 0 else st.ask
        req = {"action": mt5.TRADE_ACTION_DEAL, "position": ticket,
               "symbol": p.symbol, "volume": p.volume,
               "type": mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY,
               "price": price,
               "deviation": int(self.cfg.get("deviation_points", 50)),
               "magic": int(self.cfg.get("magic", 777001)),
               "comment": "CC-close", "type_time": mt5.ORDER_TIME_GTC}
        r, used = send_deal(mt5, req, self._filling_candidates(p.symbol))
        ok = bool(r and r.retcode == mt5.TRADE_RETCODE_DONE)
        return OrderResult(ok, retcode=getattr(r, "retcode", -1),
                           comment="close")

    def symbol_tick(self, sym):
        st = mt5.symbol_info_tick(sym)
        return {"bid": st.bid, "ask": st.ask} if st else {}

    def _broker_tz_off(self):
        """v3.52: deteksi offset detik zona waktu SERVER broker via tick
        segar (tick time = waktu server). Cache; fallback UTC+3."""
        off = getattr(self, "_tz_off_s", None)
        if off is not None:
            return off
        off = None
        for s0 in ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD"):
            try:
                st = mt5.symbol_info_tick(s0)
            except Exception:
                st = None
            tt = int(getattr(st, "time", 0) or 0) if st else 0
            if tt <= 0:
                continue
            raw = tt - int(time.time())
            if abs(raw) > 48 * 3600:       # tick basi (pasar tutup)
                continue
            off = _round30(raw)
            break
        if off is None:
            off = 3 * 3600
        self._tz_off_s = off
        return off

    def broker_day_since(self):
        """v3.52: epoch tengah malam HARI SERVER BROKER -> jendela
        pencatatan = PERSIS riwayat 'Today' aplikasi MT5/HP user."""
        return _day_start_from(int(time.time()), self._broker_tz_off())

    def closed_stats(self, since_epoch=0):
        """v3.56: rekap harian = riwayat broker. FIX REGRESI v3.54:
        history_deals_get DIPANGGIL DENGAN OBJEK datetime (format yang
        terdokumentasi & terbukti jalan di live); int dicoba dulu lalu
        di-fallback. Tanpa ini daftar deal bisa kosong -> rekap 0."""
        from datetime import datetime, timedelta, timezone
        since = int(since_epoch or 0)
        try:
            frm = int(max(0, since - 7 * 86400))
            to = int(time.time()) + 2 * 86400
            deals = None
            try:
                deals = mt5.history_deals_get(frm, to)
            except Exception:
                deals = None
            if not deals:
                deals = mt5.history_deals_get(
                    datetime.fromtimestamp(frm, tz=timezone.utc),
                    datetime.now(timezone.utc) + timedelta(hours=2))
            deals = deals or []
            t_buy = getattr(mt5, "DEAL_TYPE_BUY", 0)
            t_sell = getattr(mt5, "DEAL_TYPE_SELL", 1)
            r = _agg_deals(deals, since, t_buy, t_sell,
                           getattr(mt5, "DEAL_TYPE_BALANCE", 2))
            r["deals"] = len(deals)
            return r
        except Exception:
            return {"realized": 0.0, "profit_deal": 0.0, "commission": 0.0,
                    "lots": 0.0, "wins": 0, "losses": 0,
                    "gross_win": 0.0, "gross_loss": 0.0, "deals": 0,
                    "bal_ops": 0.0}

    def closed_trades_since(self, since_epoch=0):
        """v3.40: baris per POSISI tertutup (basis posisi, = riwayat broker).
        pl = profit+swap deal OUT + KOMISI UTUH posisi (IN bisa kemarin).
        Hanya posisi dengan OUT dalam jendela hari yang dikembalikan."""
        from datetime import datetime, timedelta, timezone
        out = []
        try:
            frm_w = datetime.fromtimestamp(max(0, since_epoch - 7 * 86400),
                                           tz=timezone.utc)
            to = datetime.now(timezone.utc) + timedelta(hours=1)
            deals = mt5.history_deals_get(frm_w, to) or []
            t_buy = getattr(mt5, "DEAL_TYPE_BUY", 0)
            t_sell = getattr(mt5, "DEAL_TYPE_SELL", 1)
            pos = {}
            for d in deals:
                if getattr(d, "type", 0) not in (t_buy, t_sell):
                    continue
                pos.setdefault(getattr(d, "position_id", 0), []).append(d)
            for pid, ds in pos.items():
                outs = [d for d in ds
                        if getattr(d, "entry", None) == 1
                        and int(d.time) >= int(since_epoch)]
                if not outs:
                    continue
                comm = sum(float(getattr(d, "commission", 0.0) or 0.0)
                           for d in ds)
                first = True
                for d in sorted(outs, key=lambda x: int(x.time)):
                    pl = (float(d.profit)
                          + float(getattr(d, "swap", 0.0) or 0.0)
                          + (comm if first else 0.0))
                    first = False
                    out.append({"symbol": d.symbol, "pl": pl,
                                "time": int(d.time),
                                "lot": float(getattr(d, "volume", 0.0) or 0.0)})
        except Exception:
            return []
        return out

    # ------------------------------------------------ v4.19 ANTI-BENGONG
    def reconnect(self) -> bool:
        """v4.19: sesi MT5 mati (terminal restart/auto-update/crash) ->
        sambung ulang TANPA restart engine.  Dipanggil watchdog engine
        saat scan gagal total 3x berurutan."""
        try:
            mt5.shutdown()
        except Exception:
            pass
        time.sleep(1.0)
        return bool(self.connect())


def _ipc_locked(fn):
    """v4.19: serialkan SEMUA panggilan MetaTrader5 dari thread mana
    pun (loop utama + dashboard + prewarm).  Tanpa ini, panggilan IPC
    yang beririsan bisa mengembalikan None massal atau menggantung --
    inilah mekanis 'bot tampak hidup tapi bengong'."""
    def _w(self, *a, **k):
        with self._ipc:
            return fn(self, *a, **k)
    _w._ipc_wrapped = True
    return _w


for _n in ("connect", "reconnect", "resolve_symbol", "_select",
           "symbol_info", "copy_rates", "copy_rates_before", "tick_delta",
           "account", "positions", "server_time", "usd_to_account_rate",
           "symbol_tick", "_broker_tz_off", "broker_day_since",
           "closed_stats", "closed_trades_since", "account_model",
           "order_send", "modify_sl", "close_volume", "close_position"):
    try:
        setattr(MT5Broker, _n, _ipc_locked(getattr(MT5Broker, _n)))
    except AttributeError:
        pass


def include_position(pmagic, bot_magic, manage_manual=True):
    """v3.26: putuskan apakah posisi dikelola CC.
    -> (dikelola?, manual?)
    - magic bot  -> dikelola (bukan manual)
    - magic 0    -> entry MANUAL user -> dikelola bila manage_manual_positions
    - magic lain -> posisi EA lama -> JANGAN disentuh"""
    if pmagic == bot_magic:
        return True, False
    if manage_manual and pmagic == 0:
        return True, True
    return False, False


# ---------------------------------------------------------------------------
# SIMULASI
# ---------------------------------------------------------------------------
_SIM_SYMBOLS = {
    # symbol: (harga awal, digits, volatilitas per tick)
    "XAUUSD": (2330.00, 2, 0.00035), "XAGUSD": (28.614, 3, 0.0009),
    "EURUSD": (1.08342, 5, 0.00006), "GBPUSD": (1.27310, 5, 0.00007),
    "USDJPY": (157.230, 3, 0.00006), "BTCUSD": (61342.50, 2, 0.0009),
    "ETHUSD": (3348.12, 2, 0.0011), "NAS100": (20648.30, 1, 0.0005),
    "USOIL": (78.420, 3, 0.0008),
}


class SimulationBroker:
    """Market + akun palsu. Angka P/L simulasi BUKAN kondisi broker nyata."""
    is_sim = True

    def __init__(self, cfg, log=print, seed=None):
        self.cfg = cfg
        self.log = log
        self.connected = False
        self.rnd = random.Random(seed)
        self.prices = {}
        self.digits = {}
        self.vol = {}
        self._lock = threading.Lock()
        for s, (p, d, v) in _SIM_SYMBOLS.items():
            self.prices[s] = p
            self.digits[s] = d
            self.vol[s] = v
        self.candles = {}
        self._gen_history()
        self.account_state = {"balance": float(cfg.get("sim_start_balance", 10000.0)),
                              "currency": cfg.get("sim_account_currency", "USD"),
                              "login": 12345678, "name": "SIMULASI",
                              "leverage": 500, "server": "SIM-SERVER",
                              "margin": 0.0, "equity": 0.0}
        self.account_state["equity"] = self.account_state["balance"]
        self.peak = self.account_state["balance"]
        self._ticket = 532781
        self.positions_state = []
        self.closed = []            # riwayat posisi ditutup (untuk statistik)
        self.last_ping_ms = self.rnd.randint(8, 24)
        self.connected = True

    # -- internal -------------------------------------------------------------
    def _gen_history(self):
        periods = {"M1": (60, 130), "M5": (300, 220), "M15": (900, 320),
                   "M30": (1800, 200), "H1": (3600, 120), "H4": (14400, 60)}
        now = int(time.time())
        for s in self.prices:
            for tf, (per, n) in periods.items():
                bars = []
                px = self.prices[s] * (1 + self.rnd.gauss(0, 0.01))
                t0 = now - now % per - n * per
                for i in range(n):
                    o = px
                    drift = self.rnd.gauss(0, self.vol[s]) * math.sqrt(per / 5.0)
                    c = o * (1 + drift)
                    h = max(o, c) * (1 + abs(self.rnd.gauss(0, self.vol[s] * 0.4)))
                    lo = min(o, c) * (1 - abs(self.rnd.gauss(0, self.vol[s] * 0.4)))
                    bars.append({"t": t0 + i * per, "o": o, "h": h, "l": lo, "c": c,
                                 "v": self.rnd.randint(80, 900)})
                    px = c
                self.candles[(s, tf)] = bars
        for s in self.prices:
            self.prices[s] = self.candles[(s, "M1")][-1]["c"]

    def _tick_market(self):
        with self._lock:
            now = int(time.time())
            for s in self.prices:
                self.prices[s] *= (1 + self.rnd.gauss(0, self.vol[s]))
                px = self.prices[s]
                for tf, per in (("M1", 60), ("M5", 300), ("M15", 900),
                                ("M30", 1800), ("H1", 3600), ("H4", 14400)):
                    bars = self.candles[(s, tf)]
                    if now // per > bars[-1]["t"] // per:
                        bars.append({"t": now - now % per, "o": px, "h": px,
                                     "l": px, "c": px, "v": self.rnd.randint(80, 900)})
                        if len(bars) > 400:
                            bars.pop(0)
                    else:
                        b = bars[-1]
                        b["c"] = px
                        b["h"] = max(b["h"], px)
                        b["l"] = min(b["l"], px)
                        b["v"] += self.rnd.randint(0, 6)
            for p in self.positions_state:
                px = self.prices.get(p["symbol"], p["entry"])
                d = (px - p["entry"]) if p["type"] == "BUY" else (p["entry"] - px)
                p["price"] = px
                p["pl"] = round(d / (10 ** -self.digits[p["symbol"]]) * p["lot"], 2)
            eq = self.account_state["balance"] + sum(p["pl"] for p in self.positions_state)
            self.peak = max(self.peak, eq)
            self.account_state["equity"] = round(eq, 2)

    # -- antarmuka sama dengan MT5Broker --------------------------------------
    def connect(self):
        self.log("[BROKER] Mode SIMULASI (MetaTrader5 tidak tersedia di mesin ini)")
        return True

    def shutdown(self):
        pass

    def resolve_symbol(self, want):
        return want if want in self.prices else ""

    def symbol_info(self, sym):
        if sym not in self.prices:
            return {}
        px = self.prices[sym]
        d = self.digits[sym]
        point = 10 ** -d
        spr = int(abs(self.rnd.gauss(25, 8))) + 2
        return {"symbol": sym, "digits": d, "point": point,
                "bid": round(px, d), "ask": round(px + spr * point, d),
                "spread_points": spr,
                "trade_tick_value": 1.0, "trade_tick_size": point,
                "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

    def copy_rates(self, sym, timeframe, count):
        bars = self.candles.get((sym, timeframe))
        if not bars:
            return None
        b = bars[-count:]
        return {"time": [x["t"] for x in b], "open": [x["o"] for x in b],
                "high": [x["h"] for x in b], "low": [x["l"] for x in b],
                "close": [x["c"] for x in b], "tick_volume": [x["v"] for x in b]}

    def tick_delta(self, sym, seconds=300):
        m5 = self.copy_rates(sym, "M5", 30)
        bv = sv = 0.0
        if m5:
            for o, c, v in zip(m5["open"], m5["close"], m5["tick_volume"]):
                if c >= o:
                    bv += v * 1.15
                else:
                    sv += v * 1.15
        return {"buy": bv, "sell": sv}

    def account(self):
        return dict(self.account_state)

    def positions(self):
        with self._lock:
            return [dict(p) for p in self.positions_state]

    def server_time(self):
        return time.localtime()

    def usd_to_account_rate(self, currency):
        return 1.0 if currency == "USD" else 0.0

    def order_send(self, sym, side, lot, sl, tp, comment="CC"):
        if sym not in self.prices:
            return OrderResult(False, comment="symbol tidak ada")
        si = self.symbol_info(sym)
        price = si["ask"] if side == ORDER_TYPE_BUY else si["bid"]
        self._ticket += 1
        pos = {"ticket": self._ticket, "symbol": sym, "type": side,
               "lot": float(lot), "entry": price, "sl": float(sl),
               "tp": float(tp), "price": price, "pl": 0.0,
               "time": int(time.time()), "trailing": False, "manual": False,
               "point": 10 ** -self.digits[sym], "digits": self.digits[sym]}
        with self._lock:
            self.positions_state.append(pos)
        self._tick_market()
        return OrderResult(True, ticket=self._ticket, retcode=10009, comment="OK")

    def modify_sl(self, ticket, sl, tp=None):
        for p in self.positions_state:
            if p["ticket"] == ticket:
                p["sl"] = float(sl)
                p["trailing"] = True
                return True
        return False

    def close_position(self, ticket):
        for i, p in enumerate(self.positions_state):
            if p["ticket"] == ticket:
                with self._lock:
                    self.positions_state.pop(i)
                    self.account_state["balance"] = round(
                        self.account_state["balance"] + p["pl"], 2)
                    self.closed.append({"time": int(time.time()),
                                        "symbol": p["symbol"], "type": p["type"],
                                        "lot": float(p["lot"]), "entry": p["entry"],
                                        "exit": p["price"], "pl": float(p["pl"])})
                return OrderResult(True, retcode=10009, comment="closed")
        return OrderResult(False, comment="tidak ada")

    def broker_day_since(self):
        return None                      # sim: pakai hari WIB

    def closed_stats(self, since_epoch=0):
        st = {"realized": 0.0, "wins": 0, "losses": 0, "lots": 0.0,
              "gross_win": 0.0, "gross_loss": 0.0, "profit_deal": 0.0,
              "bal_ops": 0.0}
        for c in self.closed_trades_since(since_epoch):
            st["realized"] += c["pl"]
            st["lots"] += float(c.get("lot", 0.0))
            if c["pl"] >= 0:
                st["wins"] += 1
                st["gross_win"] += float(c["pl"])
            else:
                st["losses"] += 1
                st["gross_loss"] += -float(c["pl"])
        st["gross_win"] = round(st["gross_win"], 2)
        st["gross_loss"] = round(st["gross_loss"], 2)
        st["profit_deal"] = st["realized"]
        return st

    def closed_trades_since(self, since_epoch=0):
        return [c for c in self.closed if c["time"] >= since_epoch]

    def symbol_tick(self, sym):
        px = self.prices.get(sym)
        if px is None:
            return {}
        si = self.symbol_info(sym)
        return {"bid": si["bid"], "ask": si["ask"]}

    # ekstra untuk demo dashboard
    def seed_demo_positions(self):
        self.order_send("XAUUSD", "SELL", 0.02, 0, 0)
        self.order_send("BTCUSD", "BUY", 0.01, 0, 0)
        self.order_send("EURUSD", "BUY", 0.02, 0, 0)
        with self._lock:
            for p in self.positions_state:
                d = self.digits[p["symbol"]]
                p["tp"] = round(p["entry"] * (1.0008 if p["type"] == "BUY" else 0.9992), d)
                p["sl"] = round(p["entry"] * (0.9985 if p["type"] == "BUY" else 1.0015), d)

# ---------------------------------------------------------------------------
# v3.63/v3.70 SUPPORT METATRADER 4 -- JEMBATAN FILE (tanpa DLL, tanpa port)
# ---------------------------------------------------------------------------
class BridgeError(Exception):
    """Perintah ke EA MT4 gagal/timeout."""


def _m4f(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _m4i(v, d=0):
    try:
        return int(float(v))
    except Exception:
        return d


class MT4Broker:
    """Broker MetaTrader 4 via JEMBATAN FILE dengan EA MQL4
    `RBT_FX_Bridge.mq4` (dipasang di 1 chart apa saja + AutoTrading ON).

    Cara kerja: Python menulis perintah ke rbtfx_cmd_<magic>.txt dan EA
    menjawab lewat rbtfx_resp_<magic>.txt di folder COMMON MT4 (folder
    yang sama utk semua terminal -> anti salah lokasi). Suffix = magic
    number -> S1 & S2 bisa jalan BERSAMAAN ke satu terminal MT4 tanpa
    saling menimpa. Antarmuka = sama persis dgn MT5Broker/Simulation
    Broker, jadi seluruh engine/risiko/dashboard tak perlu diubah.

    Batasan MT4 (jujur): volume = tick volume (delta = proxy arah tick);
    riwayat = order closed (deposit/WD tidak ikut rekap bal_ops); latensi
    jembatan ~0,3-1 dtk (cukup utk strategi M5/M15, bukan scalping HFT).
    """

    is_sim = False
    kind = "MT4"
    _TFS = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")

    def __init__(self, cfg, log=print):
        self.cfg = cfg
        self.log = log
        self.connected = False
        self.last_ping_ms = 0
        d = str(cfg.get("mt4_files_dir") or os.path.join(
            os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal",
            "Common", "Files"))
        self.dir = d
        self.magic = int(cfg.get("mt4_magic") or
                         cfg.get("magic", 777001) or 777001)
        self.suffix = str(self.magic)
        self.cmdf = os.path.join(d, "rbtfx_cmd_%s.txt" % self.suffix)
        self.respf = os.path.join(d, "rbtfx_resp_%s.txt" % self.suffix)
        self.timeout = float(cfg.get("mt4_timeout", 6.0) or 6.0)
        self._seq = 0
        self._base = int(time.time() * 10) % 1000000000
        self._syminfo = {}

    # -- transport --------------------------------------------------------
    def _cmd(self, action, payload="", timeout=None):
        os.makedirs(self.dir, exist_ok=True)
        attempts = 2
        for att in range(attempts):
            self._seq += 1
            cid = "%d%04d" % (self._base, self._seq % 10000)
            line = "|".join((cid, action, payload)).rstrip("|")
            with open(self.cmdf, "w", encoding="ascii",
                      errors="replace") as f:
                f.write(line + "\n")
            deadline = time.time() + float(timeout or self.timeout)
            while time.time() < deadline:
                try:
                    with open(self.respf, "r", encoding="ascii",
                              errors="replace") as f:
                        for ln in f:
                            ln = ln.strip()
                            if ln.startswith(cid + "|OK|"):
                                self._trim_resp()
                                return ln.split("|", 2)[2]
                            if ln.startswith(cid + "|ERR|"):
                                raise BridgeError(ln.split("|", 2)[2])
                except BridgeError:
                    raise
                except OSError:
                    pass
                time.sleep(0.12)
        raise BridgeError("timeout %s (EA terpasang di chart? AutoTrading "
                          "ON? lihat MT4_SETUP.md)" % action)

    def _trim_resp(self):
        try:
            if os.path.getsize(self.respf) > 524288:
                open(self.respf, "w").close()
        except Exception:
            pass

    # -- antarmuka sama dgn MT5Broker -------------------------------------
    def connect(self) -> bool:
        if not os.path.isdir(self.dir):
            self.log("MT4 bridge: folder Common MT4 belum ada (MT4/EA "
                     "belum pernah jalan) -> lewati")
            return False
        try:
            t0 = time.time()
            out = self._cmd("PING", timeout=min(4.0, self.timeout))
            self.last_ping_ms = int((time.time() - t0) * 1000)
            if out.strip() == "PONG":
                self.connected = True
                acc = self.account()
                self.log("MT4 bridge tersambung (%d ms): akun %s @ %s "
                         "(magic %s)" % (self.last_ping_ms,
                                         acc.get("login", "?"),
                                         acc.get("server", "?"),
                                         self.magic))
                return True
        except Exception as e:
            self.log("MT4 bridge gagal: %s" % e)
        return False

    def resolve_symbol(self, want):
        try:
            si = self.symbol_info(want)
        except Exception:
            return ""
        return want if si else ""

    def symbol_info(self, sym):
        try:
            f = self._cmd("SYMINFO", str(sym)).split(";")
        except Exception:
            return {}
        if len(f) < 9:
            return {}
        d = {"symbol": sym, "digits": _m4i(f[0], 4),
             "point": _m4f(f[1], 0.0001) or 0.0001, "bid": _m4f(f[2]),
             "ask": _m4f(f[3]), "trade_tick_value": _m4f(f[4], 1.0),
             "trade_tick_size": _m4f(f[5], 0.0001),
             "volume_min": _m4f(f[6], 0.01),
             "volume_max": _m4f(f[7], 100.0),
             "volume_step": _m4f(f[8], 0.01)}
        d["spread_points"] = int(round((d["ask"] - d["bid"]) / d["point"]))
        self._syminfo[sym] = d
        return d

    def copy_rates(self, sym, timeframe, count):
        tf = str(timeframe).upper()
        if tf not in self._TFS or int(count) <= 0:
            return None
        try:
            raw = self._cmd("RATES", "%s|%s|%d" % (sym, tf, int(count)))
        except Exception:
            return None
        t, o, h, l, c, v = [], [], [], [], [], []
        for row in raw.split(";"):
            fl = row.split(",")
            if len(fl) < 6:
                continue
            t.append(_m4i(fl[0]))
            o.append(_m4f(fl[1]))
            h.append(_m4f(fl[2]))
            l.append(_m4f(fl[3]))
            c.append(_m4f(fl[4]))
            v.append(_m4i(fl[5]))
        if not t:
            return None
        # GUARD URUTAN: EA harus kirim ASCENDING (lama->baru); kalau
        # terbalik, balikkan di sini agar konvensi = MT5 (teruji test)
        if len(t) > 1 and t[0] > t[-1]:
            t, o, h, l, c, v = (t[::-1], o[::-1], h[::-1], l[::-1],
                                c[::-1], v[::-1])
        return {"time": t, "open": o, "high": h, "low": l, "close": c,
                "tick_volume": v}

    def copy_rates_before(self, sym, timeframe, count, anchor):
        """v3.81 HALAMAN RIWAYAT DALAM (blueprint s.3): `count` bar lebih
        LAMA dari epoch `anchor` (via perintah RHIST ke EA).  Anchor =
        timestamp bar tertua yang sudah dimiliki."""
        tf = str(timeframe).upper()
        if tf not in self._TFS or int(count) <= 0:
            return None
        try:
            raw = self._cmd("RHIST", "%s|%s|%d|%d"
                            % (sym, tf, int(count), int(anchor)))
        except Exception:
            return None
        t, o, h, l, c, v = [], [], [], [], [], []
        for row in raw.split(";"):
            fl = row.split(",")
            if len(fl) < 6:
                continue
            t.append(_m4i(fl[0]))
            o.append(_m4f(fl[1]))
            h.append(_m4f(fl[2]))
            l.append(_m4f(fl[3]))
            c.append(_m4f(fl[4]))
            v.append(_m4i(fl[5]))
        if not t:
            return None
        if len(t) > 1 and t[0] > t[-1]:
            t, o, h, l, c, v = (t[::-1], o[::-1], h[::-1], l[::-1],
                                c[::-1], v[::-1])
        return {"time": t, "open": o, "high": h, "low": l, "close": c,
                "tick_volume": v}

    def tick_delta(self, sym, seconds=300):
        m5 = self.copy_rates(sym, "M5", 30)
        bv = sv = 0.0
        if m5:
            for o, c, v in zip(m5["open"], m5["close"], m5["tick_volume"]):
                if c >= o:
                    bv += v * 1.15
                else:
                    sv += v * 1.15
        return {"buy": bv, "sell": sv}

    def account(self):
        try:
            f = self._cmd("ACCOUNT").split("|")
        except Exception:
            return {}
        if len(f) < 7:
            return {}
        return {"login": f[0], "name": f[1], "currency": (f[2] or "USD"),
                "leverage": _m4i(f[3]), "server": f[4],
                "balance": _m4f(f[5]), "equity": _m4f(f[6])}

    def positions(self):
        try:
            raw = self._cmd("POSITIONS")
        except Exception:
            return []
        out = []
        for row in [r for r in raw.split("|") if r]:
            f = row.split(";")
            if len(f) < 13:
                continue
            mg = _m4i(f[10])
            sym = f[1]
            si = self._syminfo.get(sym) or {}
            out.append({"ticket": _m4i(f[0]), "symbol": sym,
                        "type": "BUY" if f[2] == "0" else "SELL",
                        "lot": _m4f(f[3]), "entry": _m4f(f[4]),
                        "sl": _m4f(f[5]), "tp": _m4f(f[6]),
                        "price": _m4f(f[4]), "pl": _m4f(f[7]),
                        "time": _m4i(f[12]), "trailing": False,
                        "manual": mg == 0,
                        "point": si.get("point", 0.0001),
                        "digits": int(si.get("digits", 4))})
        return out

    def order_send(self, sym, side, lot, sl, tp, comment="CC"):
        try:
            out = self._cmd("ORDER", "%s|%s|%s|%s|%s|%d|%s"
                            % (sym, "BUY" if side == "BUY" else "SELL",
                               _m4f(lot), _m4f(sl), _m4f(tp), self.magic,
                               comment or "CC"))
            f = out.split(";")
            return OrderResult(True, ticket=_m4i(f[0]), retcode=10009,
                               comment="OK")
        except Exception as e:
            return OrderResult(False, retcode=-1, comment=str(e))

    def close_position(self, ticket, lots=0.0):
        try:
            self._cmd("CLOSE", "%d|%s" % (int(ticket), _m4f(lots)))
            return OrderResult(True, ticket=int(ticket), retcode=10009)
        except Exception as e:
            return OrderResult(False, retcode=-1, comment=str(e))

    def modify_position(self, ticket, sl, tp):
        try:
            self._cmd("MODIFY", "%d|%s|%s"
                      % (int(ticket), _m4f(sl), _m4f(tp)))
            return OrderResult(True, ticket=int(ticket), retcode=10009)
        except Exception as e:
            return OrderResult(False, retcode=-1, comment=str(e))

    def _history(self, since):
        to = int(time.time()) + 2 * 86400
        raw = self._cmd("HISTORY", "%d|%d" % (int(since), to))
        rows = []
        for row in [r for r in raw.split("|") if r]:
            f = row.split(";")
            if len(f) < 12:
                continue
            rows.append({"ticket": _m4i(f[0]), "symbol": f[1],
                         "type": _m4i(f[2]), "lot": _m4f(f[3]),
                         "time": _m4i(f[6]),
                         "closeprice": _m4f(f[7]),
                         "profit": _m4f(f[8]), "swap": _m4f(f[9]),
                         "commission": _m4f(f[10]),
                         "magic": _m4i(f[11]),
                         "pl": _m4f(f[8]) + _m4f(f[9]) + _m4f(f[10])})
        return rows

    def closed_stats(self, since_epoch=0):
        since = int(since_epoch or 0)
        try:
            raw = self._history(since)
            deals = [types.SimpleNamespace(
                type=int(r["type"]), entry=1, time=int(r["time"]),
                profit=r["profit"], swap=r["swap"],
                commission=r["commission"], volume=r["lot"],
                symbol=r["symbol"], position_id=int(r["ticket"]))
                for r in raw]
            r = _agg_deals(deals, since, 0, 1, 2)
            r["deals"] = len(deals)
            return r
        except Exception:
            return {"realized": 0.0, "profit_deal": 0.0, "commission": 0.0,
                    "lots": 0.0, "wins": 0, "losses": 0,
                    "gross_win": 0.0, "gross_loss": 0.0, "deals": 0,
                    "bal_ops": 0.0}

    def closed_trades_since(self, since_epoch=0):
        since = int(since_epoch or 0)
        try:
            out = []
            for r in self._history(since):
                if int(r["time"]) < since:
                    continue
                out.append({"symbol": r["symbol"],
                            "pl": round(r["pl"], 2),
                            "time": int(r["time"]), "lot": r["lot"]})
            return out
        except Exception:
            return []

    def broker_day_since(self):
        try:
            f = self._cmd("SERVERTIME").split("|")
            srv, gmt = _m4i(f[0]), _m4i(f[1])
        except Exception:
            return 0
        if srv <= 0 or gmt <= 0:
            off = 3 * 3600
        else:
            off = max(0, min(13, int(round((srv - gmt) / 3600.0)))) * 3600
        return _day_start_from(int(time.time()), off)

    def server_time(self):
        try:
            srv = _m4i(self._cmd("SERVERTIME").split("|")[0])
            return time.gmtime(srv) if srv > 0 else time.gmtime()
        except Exception:
            return time.gmtime()

    def usd_to_account_rate(self, currency):
        cur = (currency or "USD").upper()
        if cur == "USD":
            return 1.0
        for pair, invert in (("USD" + cur, True), (cur + "USD", False)):
            try:
                f = self._cmd("QUOTE", pair, timeout=3.0).split(";")
            except Exception:
                continue
            px = _m4f(f[0]) if f else 0.0
            if px > 0:
                return round(1.0 / px, 6) if invert else round(px, 6)
        return 0.0

    def seed_demo_positions(self):
        pass


def create_broker(cfg, log=print):
    """v3.63/v3.70: pilih broker sesuai cfg "broker_mode":
    "auto" (default) = MT5 dulu -> MT4 (EA RBT_FX_Bridge) -> SIMULASI;
    "mt5"/"mt4" = paksa satu platform."""
    mode = str(cfg.get("broker_mode", "auto") or "auto").lower()
    if mode == "mt4":
        return MT4Broker(cfg, log=log)
    return MT5Broker(cfg, log=log)
