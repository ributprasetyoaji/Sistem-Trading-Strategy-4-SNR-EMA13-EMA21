"""PYTHON COMMAND CENTER v3.00 - multi-pair scanner + eksekusi dari Python.

Alur tiap loop:
  1. Update market & akun (broker MT5 nyata / simulasi).
  2. Scan semua symbol -> regime + skor konfluensi (cc_scanner).
  3. Skor >= min_score + sniper M1 OK + semua gate risiko OK -> order_send DARI PYTHON.
  4. Kelola posisi (trailing ke BE setelah >= 1R).
  5. Publish status JSON utk dashboard web (localhost:8081, S2).

Log/berkas: data/CC_SIGNAL.csv, data/cc_status.json, data/cc_day.json.
"""
from __future__ import annotations

import csv
import json
import os
import signal
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cc_config import CCConfig, CC_VERSION            # noqa: E402

def _eff_comm_usd(broker, cfg, usd_rate):
    """v3.x: komisi efektif USD/lot dgn DETEKSI model akun.
    Broker MT5 mendukung -> hasil deteksi (SPREAD=0, KOMISI=aktual).
    Broker stub / MT4 / simulasi (tanpa method) -> fallback config.
    Defensif sengaja: harness backtest & SIM memakai broker fake."""
    f = getattr(broker, "eff_comm_usd_per_lot", None)
    if callable(f):
        try:
            return float(f(cfg, usd_rate))
        except Exception:
            pass
    return float((cfg or {}).get("commission_per_lot_usd", 0.0))

from cc_broker import (MT5Broker, SimulationBroker, MT4Broker,
                        MT5_AVAILABLE, create_broker)  # noqa: E402
from cc_risk import RiskGuard                         # noqa: E402
import cc_scanner                                     # noqa: E402
import cc_strategy3 as cc_strategy2                   # noqa: E402  (S3 TEMPLATE)
import market_guard                                   # noqa: E402
import github_hist                                    # noqa: E402


def _disk_free_mb(path="."):
    """Sisa ruang disk dlm MB (-1 = tak bisa dicek).  v3.85: entry butuh
    tulis state/sinyal -- disk penuh harus terdeteksi & dihindari."""
    try:
        import shutil
        return int(shutil.disk_usage(path).free / (1024 * 1024))
    except Exception:
        return -1


def _trim_csv(path, max_bytes=5 * 1024 * 1024, keep=2000):
    """Jaga file log CSV agar tak tumbuh tanpa batas (disk VPS aman)."""
    try:
        if os.path.exists(path) and os.path.getsize(path) > max_bytes:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.writelines(lines[-keep:])
            os.replace(tmp, path)
    except Exception:
        pass


def _merge_symbols(wants, force):
    """S4 (user): gabung daftar simbol dgn PAKSA-INCLUDED (crypto +
    gold/silver) -- walau cc_config.json di VPS menimpa "symbols"
    dgn daftar lama, pair penting ini TETAP discan.
    Urutan: daftar config dulu, tambahan dibelakang, tanpa duplikat."""
    out = list(wants or [])
    for s in (force or []):
        if s and s not in out:
            out.append(s)
    return out


def _no_data_row(want):
    """S4 (user): baris scanner utk pair yang BELUM ada data (nama
    broker tidak match / terminal belum siap) - WAJIB tetap tampil
    di dashboard (gold/silver tidak boleh 'hilang' dari panel)."""
    return {"symbol": want, "price": 0.0, "digits": 2, "spread": 0,
            "regime": "-", "regime_dir": "-", "side": "-",
            "signal": "-", "score": 0.0, "trend_pct": 0.0,
            "status": "NO-DATA", "sniper_why": "menunggu data pair ini",
            "block_why": "", "sl": 0.0, "tp": 0.0, "sl_points": 0,
            "sl_price": 0.0, "tp_price": 0.0,
            "components": {}, "components_buy": {}, "components_sell": {},
            "ohlc": []}


def _pair_sw_path():
    return os.path.join("data", "pair_switch.json")


def _load_pair_sw():
    """v4.34: switch ON/OFF per pair (persisten). DEFAULT = SEMUA OFF --
    pair hanya dianalisa/ditradingkan setelah user menyalakan switchnya."""
    try:
        with open(_pair_sw_path(), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return {str(k).upper(): True for k, v in d.items() if v}
    except Exception:
        pass
    return {}


def _pair_lot_path():
    return os.path.join("data", "pair_lot.json")


def _load_pair_lot():
    """v4.37: lot MANUAL per pair (persisten). {} / 0 = AUTO (kalkulasi
    risiko); nilai > 0 = lot tetap dari user untuk pair itu."""
    try:
        with open(_pair_lot_path(), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            out = {}
            for k, v in d.items():
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                if fv > 0:
                    out[str(k).upper()] = fv
            return out
    except Exception:
        pass
    return {}


def _spark_from_bars(bars, n=60):
    """v4.41: candle utk chart dari bars mentah (format sama dgn
    spark_ohlc strategy: [(t,o,h,l,c),...]) -- chart TETAP HIDUP walau
    pair OFF / menunggu analisa (tampilan saja, bukan sinyal)."""
    try:
        t = [int(v) for v in (bars.get("time") or [])]
        o = [float(v) for v in (bars.get("open") or [])]
        h = [float(v) for v in (bars.get("high") or [])]
        l = [float(v) for v in (bars.get("low") or [])]
        c = [float(v) for v in (bars.get("close") or [])]
        k = min(len(t), len(o), len(h), len(l), len(c))
        if k < 2:
            return []
        return [(t[i], o[i], h[i], l[i], c[i])
                for i in range(max(0, k - int(n)), k)]
    except Exception:
        return []


def _min_lot(info):
    """v4.42 (user): lot TERKECIL pair = volume_min broker (fallback
    0.01).  Mode AUTO (tanpa lot manual) memakai ini."""
    try:
        vm = float((info or {}).get("volume_min", 0) or 0)
    except (TypeError, ValueError):
        vm = 0.0
    return vm if vm > 0 else 0.01


def _off_row(want, data=None):
    """v4.34 (user): baris scanner utk pair yang di-OFF-kan lewat switch
    kolom SW -- tidak dianalisa, tidak di-tradingkan, tetap tampil."""
    r = _no_data_row(want)
    r["status"] = "OFF"
    r["sniper_why"] = "switch OFF -- pair tidak dianalisa/ditradingkan"
    info = (data or {}).get("info") or {}
    try:
        r["price"] = float(info.get("bid") or 0.0)
        r["digits"] = int(info.get("digits", 2) or 2)
        r["spread"] = int(info.get("spread", 0) or 0)
    except Exception:
        pass
    # v4.41: chart tetap hidup utk pair OFF (candle live, tanpa sinyal)
    r["ohlc"] = _spark_from_bars((data or {}).get("m5") or {})
    return r


class CommandCenter:
    def __init__(self, cfg: CCConfig, log=print):
        self.cfg = cfg
        self.log = log
        self.running = True
        self.manual_halt = False
        # v3.19: status ON/OFF trading TERSIMPAN (tetap OFF walau VPS restart)
        try:
            _sp = os.path.join("data", "cc_state.json")
            if os.path.exists(_sp):
                with open(_sp, "r", encoding="utf-8") as _f:
                    self.manual_halt = bool(json.load(_f).get("manual_halt", False))
                if self.manual_halt:
                    self.log("[STATE] Trading OFF tersimpan dari sesi sebelumnya")
        except Exception:
            pass
        self.loop_ms = 0
        self.started = time.time()

        self.broker = None
        self.resolved = {}        # want -> broker symbol
        self.risk = None
        self.scan = {}            # symbol -> hasil analyze
        self.log_lines = []       # [{ts,tag,msg}]
        self.status_lock = threading.Lock()
        self._last_mt5_try = 0.0
        self._last_close_ts = 0.0
        self._rate_ts = 0.0
        self._rate_val = 0.0
        # ---- v4.19 ANTI-BENGONG (watchdog + prewarm) ----
        self._prewarm_need = set()   # pair riwayat tipis -> thread prewarm
        self._paged_try = {}         # anti-spam paging broker per pair
        self._scan_fail = {}         # hitung gagal ambil data per pair
        self.pair_sw = _load_pair_sw()   # v4.34: switch ON/OFF per pair
        # v4.43 (user): START = SEMUA OFF -- file state yang tersisa
        # (mis. BTCUSD nyala dari sesi lama) dibersihkan saat boot.
        # Set "pairs_start_all_off": false di cc_config.json utk
        # mempertahankan switch antar restart.
        if self.cfg.get("pairs_start_all_off", True) and self.pair_sw:
            _sisa = sorted(self.pair_sw.keys())
            self.pair_sw.clear()
            try:
                os.makedirs("data", exist_ok=True)
                _tmp = _pair_sw_path() + ".tmp"
                with open(_tmp, "w", encoding="utf-8") as _f:
                    json.dump({}, _f)
                os.replace(_tmp, _pair_sw_path())
                self.log("INFO", "START BERSIH: SEMUA OFF -- state lama "
                         "dibersihkan (%s)" % ", ".join(_sisa))
            except Exception as _e:
                self.log("WARN", "start bersih gagal: %s" % _e)
        self.pair_lot = _load_pair_lot()  # v4.37: lot manual per pair
        _on = sorted(self.pair_sw.keys())
        self.log("INFO", "SWITCH PAIR: %d ON dari %d (default OFF)" %
                 (len(_on), len(getattr(self, "wants", []) or [])))
        if _on:   # v4.42: daftar eksplisit -- tak ada pair "misterius"
            self.log("INFO", "SWITCH ON: %s" % ", ".join(_on))
        self._scan_warn_ts = {}      # anti-spam WARN per pair (5 mnt)
        self._scan_allfail = 0       # scan gagal TOTAL berurutan
        self._scan_last_ok = 0.0     # scan terakhir yang berhasil
        self._reconnect_ts = 0.0     # anti-spam reconnect (2 mnt)
        self._stale_alert_ts = 0.0   # anti-spam TG bengong (10 mnt)
        self._tpmode_warned = False  # v4.20 guard tangga 1x per run
        self.candidates = {}   # want -> {'t','side','score'}: sinyal M15 yang
                               #   MASIH BERLAKU; M1 menahan sampai momen pas
        # ---- STRATEGY 2 (port EA v6.05): state pending HOLD + ATR trail ----
        # S4 (user): template KOSONG -> selalu dievaluasi (selalu WAIT)
        # sampai user mengisi logic entry baru di cc_strategy3.py.
        self.s2_on = True
        self.s2k = cc_strategy2.s2_cfg(self.cfg) if self.s2_on else {}
        self.s2state = cc_strategy2.Strategy2State(
            os.path.join("data", "s3_state.json"))
        # v3.81 RIWAYAT DALAM (blueprint s.3): cache bar lama per pair
        self._s3_hist = {}
        self._s3_hist_ts = {}
        self._s3_hist_try = {}
        self._s3_cloud_try = {}
        self.s2_started = time.time()
        self.emit_log("ENGINE", "STRATEGY 4: SNR BODY + EMA STACK aktif "
                      "(v4.44, parameter user -- bias M15 + ADX>20 + "
                      "M5 kontra + touch HH/HL, RR 1:1)")
        self._signal_csv_init()

    # ------------------------------------------------------------------ log --
    def _signal_csv_init(self):
        os.makedirs("data", exist_ok=True)
        p = "data/CC_SIGNAL.csv"
        if not os.path.exists(p):
            with open(p, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["ts", "symbol", "side", "score", "lot",
                                        "entry", "sl", "tp", "action", "why"])

    def _disk_warn(self, ctx="", force=False):
        """Peringatan disk SESEKALI (1x/10 mnt, bukan spam): Errno 28 =
        disk penuh -> entry bisa gagal.  v3.85."""
        now = time.time()
        if not force and now - getattr(self, "_disk_warn_ts", 0.0) < 600.0:
            return
        self._disk_warn_ts = now
        free = _disk_free_mb(".")
        self.emit_log("PROTECT", "DISK VPS KRITIS (sisa %s MB): bersihkan "
                      "ruang -- entry bisa GAGAL karena state tak bisa "
                      "ditulis!  %s" % (free if free >= 0 else "?", ctx))

    def emit_log(self, tag, msg):
        with self.status_lock:
            self.log_lines.append({"ts": time.strftime("%H:%M:%S"), "tag": tag,
                                   "msg": msg})
            if len(self.log_lines) > 220:
                self.log_lines = self.log_lines[-200:]
        # v4.01: ERROR & PROTECT (halt harian, disk kritis, dll) -> TG
    def _adapt_log(self, m):
        """Adapter: modul lama memanggil log("[TAG] pesan") satu argumen."""
        try:
            if m.startswith("["):
                tag = m[1:m.index("]")]
                self.emit_log(tag, m[m.index("]") + 1:].strip())
                return
        except Exception:
            pass
        self.emit_log("INFO", str(m))

    def _write_signal(self, sym, side, score, lot, entry, sl, tp, action, why):
        try:   # v3.85: disk penuh -> CATATAN bolong, TRADING JALAN TERUS
            _trim_csv(os.path.join("data", "CC_SIGNAL.csv"),
                      max_bytes=5 * 1024 * 1024, keep=2000)
            with open("data/CC_SIGNAL.csv", "a", newline="",
                      encoding="utf-8") as f:
                csv.writer(f).writerow([time.strftime("%Y-%m-%d %H:%M:%S"),
                                        sym, side, round(score, 1), lot,
                                        entry, sl, tp, action, why])
        except OSError:
            self._disk_warn("CC_SIGNAL gagal ditulis")

    # -------------------------------------------------------------- connect --
    def connect(self):
        self.emit_log("INFO", "PYTHON COMMAND CENTER v%s mulai..." % CC_VERSION)
        _bmode = str(self.cfg.get("broker_mode", "auto") or "auto").lower()
        if _bmode != "mt4" and MT5_AVAILABLE:
            b = MT5Broker(self.cfg, log=self._adapt_log)
            if b.connect():
                self.broker = b
            else:
                self.emit_log("WARN", "MT5 ada tapi tidak bisa konek (terminal jalan? "
                                      "login?)")
        # v3.63/v3.70 SUPPORT MT4: auto = coba MT4 kalau MT5 tidak jalan
        if self.broker is None and _bmode in ("auto", "mt4"):
            b4 = MT4Broker(self.cfg, log=self._adapt_log)
            if b4.connect():
                self.broker = b4
                self.emit_log("BROKER", ">>> METATRADER 4 tersambung via "
                              "jembatan file (EA RBT_FX_Bridge) <<<")
            else:
                self.emit_log("WARN", "MT4 bridge tidak merespons (EA terpasang "
                              "di chart + AutoTrading ON? lihat MT4_SETUP.md)")
        if self.broker is None:
            self.broker = SimulationBroker(self.cfg, log=self._adapt_log)
            self.broker.connect()
        self.risk = RiskGuard(self.cfg, self.broker, log=self._adapt_log)
        self._last_close_ts = time.time()   # riwayat sebelum start tidak dihitung
        # S4 (user): SATU daftar simbol gabungan utk SEMUA pemakai
        # (resolver, scanner-panel dashboard, dsb) - force include
        # crypto + gold/silver selalu masuk walau cc_config.json VPS
        # menimpa "symbols" dgn daftar lama.
        self.wants = _merge_symbols(self.cfg.get("symbols", []),
                                    self.cfg.get("symbols_force_include"))
        self._resolve_symbols()
        _cr = ",".join(s for s in self.resolved
                       if s.startswith(("BTC", "ETH", "SOL", "XRP", "LTC"))) or "-"
        _mt = ",".join(s for s in self.resolved
                       if s.startswith(("XAU", "XAG", "XPT"))) or "-"
        self.emit_log("INFO", "PAIR AKTIF %d | crypto: %s | gold/silver: %s"
                      % (len(self.resolved), _cr, _mt))
        if self.broker.is_sim and self.cfg.get("sim_force_signals", True):
            if not self.s2_on:
                self.broker.seed_demo_positions()
                self.emit_log("INFO", "Posisi demo di-seed untuk tampilan simulasi")
            else:
                self.emit_log("INFO", "posisi demo TIDAK di-seed (slot pair "
                              "dipakai sinyal asli engine)")

    def _resolve_symbols(self):
        self.resolved = {}
        for want in self.wants:
            got = self.broker.resolve_symbol(want)
            if got:
                self.resolved[want] = got
                self.emit_log("INFO", "Symbol %s -> %s" % (want, got))
            else:
                self.emit_log("WARN", "Symbol %s tidak ditemukan di broker, dilewati" % want)

    def _try_upgrade_live(self):
        """Mode SIM + paket MT5 ada -> coba konek ulang tiap 30 dtk.
        Berguna saat user membuka/login MT5 setelah engine start."""
        if not MT5_AVAILABLE or not self.broker.is_sim:
            return
        if time.time() - self._last_mt5_try < 30:
            return
        if str(self.cfg.get("broker_mode", "auto") or "auto").lower() == "mt4":
            return  # v3.63: mode MT4 -> jangan naikkan ke MT5 otomatis
        self._last_mt5_try = time.time()
        b = MT5Broker(self.cfg, log=self._adapt_log)
        if b.connect():
            self.broker = b
            self.risk = RiskGuard(self.cfg, self.broker, log=self._adapt_log)
            self._resolve_symbols()
            self.emit_log("BROKER", ">>> UPGRADE: MT5 tersambung -> mode LIVE <<<")

    # ------------------------------------------------------------- scanning --
    def _cache_save(self, want, bars, ts):
        """v4.17: cache GZ (3.5x lebih kecil dr JSON, baca ~5x cepat);
        file .json lama otomatis diganti."""
        try:
            os.makedirs("data", exist_ok=True)
            import gzip as _gz
            cfgz = os.path.join("data", "s3_hist_%s_M15.json.gz" % want)
            tmp = cfgz + ".tmp"
            # level 1: tulis secepat JSON, baca jauh lebih cepat
            with _gz.open(tmp, "wt", compresslevel=1) as f:
                json.dump({"ts": ts, "bars": bars}, f,
                          separators=(",", ":"))
            os.replace(tmp, cfgz)
            cf = os.path.join("data", "s3_hist_%s_M15.json" % want)
            try:
                if os.path.exists(cf):
                    os.remove(cf)
            except Exception:
                pass
        except Exception:
            pass

    def _s3_deep(self, want, sym):
        """Riwayat M15 dalam utk fingerprint DB (v3.81).

        v4.19 ANTI-BENGONG: method ini TIDAK BOLEH menyentuh jaringan.
        Dulu restore GitHub + paging broker dijalankan DI SINI (tengah
        loop scan): GitHub/terminal lambat = SEMUA pair momentum 0%
        belasan menit = keluhan 'bengong'.  Kini scan hanya pakai cache
        (memori/disk) + ekor live; cache tipis -> ditandai utk thread
        prewarm (di belakang)."""
        try:
            hc = self.cfg.get("hist_cloud") or {}
            need_min = int(hc.get("download_min_bars", 2000) or 0)
            cur = self._s3_hist.get(want)
            if cur is None:
                cf = os.path.join("data", "s3_hist_%s_M15.json" % want)
                cfgz = os.path.join("data", "s3_hist_%s_M15.json.gz"
                                    % want)
                if os.path.exists(cfgz) or os.path.exists(cf):
                    try:
                        if os.path.exists(cfgz):
                            import gzip as _gz
                            with _gz.open(cfgz, "rt") as f:
                                d = json.load(f)
                        else:
                            with open(cf) as f:
                                d = json.load(f)
                        b = d.get("bars") if isinstance(d, dict) else None
                        if b and len(b.get("close") or []) >= need_min:
                            cur = b
                            self._s3_hist[want] = cur
                            self._s3_hist_ts[want] = float(d.get("ts")
                                                           or 0.0)
                    except Exception:
                        pass
            if cur is None or len(cur.get("close") or []) < need_min:
                # cache tipis/absen -> JANGAN download di jalur scan;
                # thread prewarm yang mengisi (cloud -> paging broker)
                self._prewarm_need.add(want)
                return None
            live = self.broker.copy_rates(sym, "M15", 300)
            if not live:
                return cur
            base = cc_strategy2.merge_bars(cur, live)
            self._s3_hist[want] = base
            return base
        except Exception:
            return self._s3_hist.get(want)

    # ---------------------------------------------- prewarm riwayat ----
    def _prewarm_loop(self):
        """v4.19 ANTI-BENGONG: SEMUA download riwayat (restore cloud
        GitHub + paging broker) pindah ke thread belakang ini.  Loop scan
        TIDAK PERNAH menunggu jaringan -> momentum tidak bisa 0% gegara
        restore lambat (akar 'muat ulang lama' & 'bengong 0%')."""
        while self.running:
            try:
                # v4.23: 4 pair/tick @2 dtk -> 22 pair cloud selesai
                # ~11 dtk; pair siap BISA ENTRY tanpa nunggu yang lain
                for want in sorted(self._prewarm_need)[:4]:
                    self._prewarm_one(want)
                time.sleep(2.0)
            except Exception:
                time.sleep(2.0)

    def _prewarm_one(self, want):
        sym = self.resolved.get(want, want)
        hc = self.cfg.get("hist_cloud") or {}
        now = time.time()
        need_min = int(hc.get("download_min_bars", 2000) or 0)
        have = self._s3_hist.get(want)
        if have is not None and len(have.get("close") or []) >= need_min:
            self._prewarm_need.discard(want)
            return
        # ---- sumber 1: RESTORE CLOUD (GitHub) -- TTL anti-spam ----
        if now - self._s3_cloud_try.get(want, 0.0) >= \
                float(hc.get("restore_retry_sec", 180.0)):
            self._s3_cloud_try[want] = now
            _t0 = time.time()
            try:
                tok = github_hist.resolve_token(hc)
                if tok and hc.get("enabled", True):
                    repo = hc.get("repo",
                                  github_hist.DEFAULTS["repo"])
                    branch = hc.get("branch", "main")
                    raw = github_hist.download_gz(
                        repo, github_hist.cloud_path(want, hc),
                        branch, tok)
                    rst = github_hist.unpack_bars(raw) if raw else None
                    ndl = 0
                    if rst:
                        for dp in github_hist.list_deltas(repo, want,
                                                          hc, tok):
                            try:
                                db = github_hist.unpack_bars(
                                    github_hist.download_gz(
                                        repo, dp, branch, tok))
                                if db:
                                    rst = cc_strategy2.merge_bars(rst,
                                                                  db)
                                    ndl += 1
                            except Exception:
                                pass
                    if rst:
                        live = self.broker.copy_rates(sym, "M15", 300)
                        base_r = cc_strategy2.merge_bars(rst, live) \
                            if live else rst
                        if len(base_r.get("close") or []) > \
                                len((live or {}).get("close") or []):
                            self._s3_hist[want] = base_r
                            self._s3_hist_ts[want] = now
                            self._prewarm_need.discard(want)
                            self._cache_save(want, base_r, now)
                            self.emit_log(
                                "HIST", "%s: RESTORE dari cloud %d bar "
                                "(+%d delta, +ekor live) dalam %.1fs "
                                "-- tanpa download ulang"
                                % (want, len(rst.get("close") or []),
                                   ndl, time.time() - _t0))
                            return
                    else:
                        self.emit_log(
                            "HIST", "%s: restore cloud TIDAK ada/valid "
                            "(base kosong/rusak?) -- coba %d dtk lagi"
                            % (want, int(hc.get("restore_retry_sec",
                                                180.0))))
                else:
                    self.emit_log(
                        "HIST", "%s: restore cloud DILEWATI (%s) -- "
                        "coba %d dtk lagi"
                        % (want, "token GitHub tidak ada" if not tok
                           else "fitur hist_cloud off",
                           int(hc.get("restore_retry_sec", 180.0))))
            except Exception as e:
                self.emit_log("WARN", "%s: restore cloud ERROR: %s -- "
                              "coba %d dtk lagi"
                              % (want, str(e)[:90],
                                 int(hc.get("restore_retry_sec",
                                            180.0))))
        # ---- sumber 2: PAGING BROKER (di belakang; dulu di jalur scan
        # = sumber 'muat ulang belasan menit') ----
        if now - self._paged_try.get(want, 0.0) >= 600.0:
            self._paged_try[want] = now
            try:
                base = cc_strategy2.hist_paged(self.broker, sym, "M15",
                                               target=35040,
                                               budget_sec=10.0)
                if base and len(base.get("close") or []) >= need_min:
                    live = self.broker.copy_rates(sym, "M15", 300)
                    base_r = cc_strategy2.merge_bars(base, live) \
                        if live else base
                    self._s3_hist[want] = base_r
                    self._s3_hist_ts[want] = now
                    self._prewarm_need.discard(want)
                    if _disk_free_mb(".") >= 250:
                        self._cache_save(want, base_r, now)
                    self.emit_log("HIST", "%s: riwayat M15 %d bar "
                                  "(%.1f tahun) via broker (prewarm)"
                                  % (want, len(base_r["close"]),
                                     cc_strategy2.hist_years(
                                         len(base_r["close"]))))
                    if hc.get("enabled", True):
                        self._cloud_maybe_upload(want, base_r, hc, now)
            except Exception as e:
                self.emit_log("WARN", "%s: paging riwayat gagal: %s"
                              % (want, str(e)[:90]))

    def _broker_reconnect(self, why):
        """v4.19: sesi MT5 mati (terminal restart/update/crash) ->
        sambung ulang TANPA restart engine; max 1x/2 menit."""
        now = time.time()
        if now - self._reconnect_ts < 120.0:
            return
        self._reconnect_ts = now
        rc = getattr(self.broker, "reconnect", None)
        if rc is None or getattr(self.broker, "is_sim", False):
            return
        self.emit_log("WARN", "RECONNECT broker: %s" % why)
        try:
            ok = bool(rc())
        except Exception as e:
            ok = False
            self.emit_log("WARN", "reconnect error: %s" % str(e)[:90])
        self.emit_log("BROKER", "reconnect %s" %
                      ("SUKSES" if ok else
                       "GAGAL (terminal MT5 jalan?)"))
    def _cloud_autosync_tick(self, now):
        """v4.30 (permintaan user): PASTIKAN data di-backup 2X SEHARI ke
        GitHub -- cek berkala (default tiap 10 mnt, di thread) semua
        pair: delta terakhir >= delta_min_hours (12 jam) & ada bar baru
        -> upload delta ringan.  TIDAK tergantung reload/start: engine
        hidup terus punsa backup tetap jalan."""
        hc = self.cfg.get("hist_cloud") or {}
        if not hc.get("enabled", True):
            return
        every = float(hc.get("autosync_every_sec", 600.0) or 0.0)
        if every <= 0:
            return
        if not github_hist.resolve_token(hc):
            return
        if now - float(getattr(self, "_cloud_sync_ts", 0.0) or 0.0) \
                < every:
            return
        self._cloud_sync_ts = now
        if getattr(self, "_cloud_sync_busy", False):
            return
        self._cloud_sync_busy = True

        def _work():
            try:
                stf = os.path.join("data", "s3_hist_cloud.json")
                try:
                    st = json.load(open(stf))
                except Exception:
                    st = {}
                dmh = float(hc.get("delta_min_hours", 12.0) or 0.0)
                for want in list(self.resolved.keys()):
                    bars = self._s3_hist.get(want)
                    if not bars or not (bars.get("close")):
                        continue
                    rec = st.get(want) or {}
                    dts = float(rec.get("delta_ts") or 0.0)
                    if dts and (now - dts) < dmh * 3600.0:
                        continue          # belum jatuh tempo 12 jam
                    try:
                        self._cloud_maybe_upload(want, bars, hc, now)
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                self._cloud_sync_busy = False
        threading.Thread(target=_work, daemon=True).start()

    def _cloud_maybe_upload(self, want, bars, hc, now):
        """v3.90: backup cloud 2 tingkat di THREAD (tak menahan loop):
        - DELTA harian RINGAN: hanya bar sejak backup terakhir
          (1 hari M15 ~ 96 bar ~ 2-4 KB) -> cloud selalu segar.
        - BASE penuh: jarang (tumbuh >= upload_min_new_bars & >=
          upload_min_hours) -> lalu delta lama dibersihkan."""
        try:
            tok = github_hist.resolve_token(hc)
            if not tok or not hc.get("enabled", True):
                return
            stf = os.path.join("data", "s3_hist_cloud.json")
            try:
                st = json.load(open(stf)) if os.path.exists(stf) else {}
            except Exception:
                st = {}
            rec = dict(st.get(want) or {})
            nb = len(bars.get("close") or [])
            repo = hc.get("repo", github_hist.DEFAULTS["repo"])
            branch = hc.get("branch", "main")
            cloud_time = float(rec.get("cloud_time") or 0)
            minh = float(hc.get("upload_min_hours", 24.0) or 0)

            base = (not cloud_time) or \
                github_hist.should_upload(nb, rec, hc, now)[0]
            if base:
                payload = bars
                path = github_hist.cloud_path(want, hc)
                date_s = time.strftime("%Y%m%d", time.gmtime(now))
                cmsg = "RBT S3 history %s (%d bar)" % (want, nb)
            else:
                if not hc.get("delta_enabled", True):
                    return
                nd = len(github_hist.slice_after(bars, cloud_time)
                         .get("close") or [])
                dmh = float(hc.get("delta_min_hours", minh) or 0.0)
                if nd < int(hc.get("delta_min_new_bars", 20) or 0) or \
                        (dmh > 0 and now - float(
                            rec.get("delta_ts") or 0) < dmh * 3600.0):
                    return
                payload = github_hist.slice_after(bars, cloud_time)
                date_s = time.strftime("%Y%m%d", time.gmtime(now))
                path = github_hist.delta_path(want, hc, date_s)
                cmsg = "RBT S3 delta %s %s (+%d bar)" % (want, date_s, nd)
            data = github_hist.pack_bars(payload)
            if len(data) > 40 * 1024 * 1024:
                return                      # pengaman ukuran
            npl = len(payload.get("close") or [])
            lt = github_hist.last_time(payload)

            def _up():
                try:
                    ok2 = github_hist.upload_bytes(repo, path, branch,
                                                   tok, data, cmsg)
                    if ok2:
                        if base:
                            st[want] = {"bars": nb, "ts": now,
                                        "cloud_time": lt, "delta_ts": now}
                        else:
                            r2 = dict(st.get(want) or {})
                            r2["cloud_time"] = max(
                                float(r2.get("cloud_time") or 0), lt)
                            r2["delta_ts"] = now
                            st[want] = r2
                        try:
                            tmp = stf + ".tmp"
                            with open(tmp, "w") as f:
                                json.dump(st, f)
                            os.replace(tmp, stf)
                        except Exception:
                            pass
                        if base:
                            self.emit_log("HIST", "%s: backup cloud OK "
                                          "(BASE %d bar, %.1f KB gzip)"
                                          % (want, npl,
                                             len(data) / 1024.0))
                            # delta lama sudah tercakup base -> bersihkan
                            for dp in github_hist.list_deltas(
                                    repo, want, hc, tok):
                                try:
                                    github_hist.delete_file(repo, dp,
                                                            branch, tok)
                                except Exception:
                                    pass
                        else:
                            self.emit_log("HIST", "%s: delta cloud OK "
                                          "(+%d bar, %.1f KB gzip)"
                                          % (want, npl,
                                             len(data) / 1024.0))
                except Exception:
                    pass
            import threading
            threading.Thread(target=_up, daemon=True).start()
        except Exception:
            pass

    def _fetch_data(self, want, sym):
        b = self.broker
        m15 = b.copy_rates(sym, "M15", self.cfg.get("bars_m15", 300))
        if not m15 or len(m15["close"]) < 60:
            return None
        m5 = b.copy_rates(sym, "M5", self.cfg.get("bars_m5", 200))
        m1 = b.copy_rates(sym, "M1", self.cfg.get("bars_m1", 120))
        info = b.symbol_info(sym)
        delta = b.tick_delta(sym, 300)
        out = {"m15": m15, "m5": m5, "m1": m1, "delta": delta,
               "info": info, "point": info.get("point") if info else None}
        if self.s2_on:
            # WPR 6 TF (H4,H1,M30,M15,M5,M1) + ADX/ATR M5 -- cc_strategy2
            out["m30"] = b.copy_rates(sym, "M30", 100)
            out["h1"] = b.copy_rates(sym, "H1", 100)
            out["h4"] = b.copy_rates(sym, "H4", 60)
            # v3.81 RIWAYAT DALAM: ganti m15 dgn cache deep (fingerprint
            # DB memakai window besar; pipeline live tetap pakai ekor)
            hist = self._s3_deep(want, sym)
            if hist and len(hist.get("close") or []) >= len(
                    m15.get("close") or []):
                out["m15"] = hist
        return out

    def pair_on(self, want):
        return bool(self.pair_sw.get(str(want or "").upper(), False))

    def set_pair_switch(self, want, on):
        """v4.34 (user): switch per pair -- ON = dianalisa & ditradingkan;
        OFF (default) = skip total. Persist di data/pair_switch.json."""
        want = str(want or "").upper()
        if on:
            self.pair_sw[want] = True
        else:
            self.pair_sw.pop(want, None)
        # v4.41: minta loop scan jalan SEKARANG -- pair ON langsung
        # dianalisa (dulu nunggu tick berikut -- chart kesan "off")
        self._scan_kick = True
        try:
            os.makedirs("data", exist_ok=True)
            _tmp = _pair_sw_path() + ".tmp"
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump({k: True for k in self.pair_sw}, _f)
            os.replace(_tmp, _pair_sw_path())
            self.emit_log("INFO", "SWITCH %s -> %s"
                          % (want, "ON" if on else "OFF"))
        except Exception as e:
            self.emit_log("WARN", "pair_switch save gagal: %s" % e)

    def pairs_reset_all_off(self):
        """v4.42 (user): matikan SEMUA switch -- kembali default OFF."""
        n = len(self.pair_sw)
        self.pair_sw.clear()
        try:
            os.makedirs("data", exist_ok=True)
            _tmp = _pair_sw_path() + ".tmp"
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump({}, _f)
            os.replace(_tmp, _pair_sw_path())
        except Exception as e:
            self.emit_log("WARN", "pairs_reset save gagal: %s" % e)
        self.emit_log("INFO", "SEMUA SWITCH DIMATIKAN (%d pair)" % n)
        return n

    def pair_lot_of(self, want):
        """v4.37: lot manual utk pair ini -- 0/None = AUTO."""
        try:
            v = float(self.pair_lot.get(str(want or "").upper(), 0) or 0)
        except (TypeError, ValueError):
            return 0.0
        return v if v > 0 else 0.0

    def set_pair_lot(self, want, lot):
        """v4.37 (user): isi lot manual per pair. lot<=0 = AUTO lagi.
        Persist di data/pair_lot.json (dilindungi robocopy /XF)."""
        want = str(want or "").upper()
        try:
            lot = float(lot)
        except (TypeError, ValueError):
            lot = 0.0
        if lot > 0:
            lot = max(0.01, min(lot, 500.0))
            self.pair_lot[want] = lot
        else:
            lot = 0.0
            self.pair_lot.pop(want, None)
        try:
            os.makedirs("data", exist_ok=True)
            _tmp = _pair_lot_path() + ".tmp"
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump(self.pair_lot, _f)
            os.replace(_tmp, _pair_lot_path())
            self.emit_log("INFO", "LOT %s = %s"
                          % (want, ("%.2f MANUAL" % lot) if lot else "AUTO"))
        except Exception as e:
            self.emit_log("WARN", "pair_lot save gagal: %s" % e)
        return lot

    def scan_all(self):
        n_ok = 0
        for want, sym in list(self.resolved.items()):
            try:
                data = self._fetch_data(want, sym)
                if not data and (getattr(self, "pair_sw", {}) or {})\
                        .get(want, False):
                    # v4.41: pair ON -- 1x retry cepat (MT5 kadang
                    # gagal sesaat; dulu langsung dianggap no-data ->
                    # chart kosong & user toggle berulang)
                    data = self._fetch_data(want, sym)
                if not data:
                    # v4.19: JANGAN SENYAP -- data None = terminal MT5
                    # putus/simbol hilang; inilah 'momentum 0% semua
                    # pair' TANPA jejak log.  Catat max 1x/5 mnt/pair.
                    self._scan_fail[want] = \
                        self._scan_fail.get(want, 0) + 1
                    if time.time() - self._scan_warn_ts.get(want,
                                                            0.0) > 300.0:
                        self._scan_warn_ts[want] = time.time()
                        self.emit_log(
                            "WARN", "%s: data pasar tidak tersedia "
                            "(terminal MT5 putus?) x%d"
                            % (want, self._scan_fail[want]))
                    continue
                self._scan_fail.pop(want, None)
                n_ok += 1
                if not self.pair_sw.get(want, False):
                    # v4.34 (user): switch OFF -> TIDAK dianalisa &
                    # TIDAK diberi sinyal; tetap tampil dgn status OFF
                    self.scan[want] = _off_row(want, data)
                    self.candidates.pop(want, None)
                    continue
                if self.s2_on:
                    # STRATEGY 2: momentum M1 -> MTF WPR 6TF -> presisi ->
                    # HOLD tunggu close M5 (cc_strategy2.evaluate)
                    res = cc_strategy2.evaluate(want, data, self.s2k,
                                                self.s2state)
                    res["info"] = data["info"]
                    res["ohlc"] = res.pop("spark_ohlc", [])
                    res.setdefault("regime", "MOMENTUM")
                    res.setdefault("regime_dir", "")
                    self.scan[want] = res
                    if res.get("exec"):
                        # M5 konfirmasi sudah close -> kandidat eksekusi
                        self.candidates[want] = {
                            "t": time.time(), "born": time.time(),
                            "side": res["exec"]["sig"],
                            "score": float(res.get("score", 0)),
                            "s2_exec": True}
                    else:
                        self.candidates.pop(want, None)
                    continue
                res = cc_scanner.analyze(want, data, self.cfg)
                if res:
                    res["info"] = data["info"]
                    res["ohlc"] = res.pop("spark_ohlc", [])
                    self.scan[want] = res
            except Exception as e:
                self.emit_log("WARN", "scan %s error: %s" % (want, e))
        # v4.19 WATCHDOG SCAN: SEMUA pair tanpa data = sesi MT5 bermasalah
        # -> reconnect otomatis (dulu: diam terus sampai user restart BAT)
        if self.resolved and n_ok == 0:
            self._scan_allfail += 1
            self.emit_log("WARN", "SCAN GAGAL TOTAL x%d (%d pair tanpa "
                          "data) -- cek terminal MT5"
                          % (self._scan_allfail, len(self.resolved)))
            if self._scan_allfail >= 3:
                self._scan_allfail = 0
                self._broker_reconnect("3x scan gagal total")
        elif n_ok:
            self._scan_allfail = 0
            self._scan_last_ok = time.time()

    # ------------------------------------------------------------ eksekusi ---
    def account_usd_rate(self):
        cur = self.broker.account().get("currency", "USD")
        # v3.24: kurs manual (default 18.000 utk akun IDR user). Setel 0 di
        # cc_config.json utk kembali ke kurs otomatis dari simbol broker.
        man = float(self.cfg.get("usd_rate_manual", 0.0) or 0.0)
        if man > 0 and cur != "USD":
            return cur, man
        rate = self.broker.usd_to_account_rate(cur)
        if rate == 0 and cur != "USD":
            self.emit_log("WARN", "Kurs USD->%s tidak ketemu; pakai kurs "
                          "manual %s" % (cur,
                          self.cfg.get("usd_rate_manual", 0.0)))
            man2 = float(self.cfg.get("usd_rate_manual", 0.0) or 0.0)
            if man2 > 0:
                return cur, man2
        return cur, rate

    def _apply_structural_tp(self, res, side, score, lot, info, sym, rate):
        """v3.20: hitung TP struktural (body SNR/HH-HL H1 terdekat) + gerbang
        RR bersih penuh (spread+komisi). Dipanggil dalam try/except fail-open.
        Bila struktur membantu -> res["tp_price"] dipotong ke body lilin."""
        sl_dist = res["sl_points"] * (res.get("point") or 0.0)
        point_sz = res.get("point") or 0.0
        m15 = self.broker.copy_rates(sym, "M15", 60)
        h1 = self.broker.copy_rates(sym, "H1", 60)   # aman: copy_rates return
        bars_tp = h1 or m15 or {}                    # None utk tf tak dikenal
        spr_price = float(info.get("spread_points", 0)) * point_sz
        tsz = float(info.get("trade_tick_size", 0.0) or 0.0)
        tv = float(info.get("trade_tick_value", 0.0) or 0.0)
        comm_price = 0.0
        if tv > 0 and tsz > 0:
            # v3.98: komisi efektif dr deteksi model akun
            comm_price = (_eff_comm_usd(self.broker, self.cfg,
                                        rate or 0.0)
                          * (rate or 0.0)) / tv * tsz
        cost_dist = spr_price + comm_price
        tp_use = cc_scanner.structural_tp(side, res["price"], sl_dist,
                                          res["tp_price"], bars_tp,
                                          min_rr=self.cfg.get("tp_min_rr_net", 0.6),
                                          body_pos=self.cfg.get("tp_body_pos", 0.4),
                                          cost_dist=cost_dist)
        if tp_use != res["tp_price"]:
            res["tp_price"] = tp_use
            self.emit_log("INFO", "%s TP dipotong ke BODY SNR/HH-HL %.*f "
                                 "(bukan wick -> anti candle rejection)"
                          % (sym, info.get("digits", 2), tp_use))
        net_ok, net_rr = cc_scanner.tp_net_check(side, res["price"],
                                                 res["tp_price"], sl_dist,
                                                 cost_dist,
                                                 self.cfg.get("tp_min_rr_net", 0.6))
        if not net_ok:
            res["block_why"] = ("TP_NET_RR %.2fR < %.2fR setelah spread+komisi"
                                % (net_rr, self.cfg.get("tp_min_rr_net", 0.6)))
            raise ValueError(res["block_why"])

    def try_execute(self, res, positions):
        if self._market_guard_block(res.get("symbol"), res):
            return              # v3.86: guard jendela pasar (ketiga strg)
        if res.get("strategy") == "S2":
            return self._try_execute_s2(res, positions)
        sym = self.resolved.get(res["symbol"], res["symbol"])
        side, score = res["side"], res["score"]
        # v3.34: entry/re-entry DILARANG melawan candle rejection M15 valid
        # + arah EMA (cek paling awal, sebelum sniper & filter lain)
        if res.get("rej_blocked"):
            res["status"] = "BLOCKED"
            res["block_why"] = res["rej_blocked"]
            self.emit_log("PROTECT", "%s %s -> SKIP (%s)"
                          % (res["symbol"], side, res["rej_blocked"]))
            return
        # v3.26: gate kuota/klaster hanya menghitung posisi BOT — entry
        # manual user tidak menghalangi robot mengambil sinyal baru
        bot_positions = [p for p in positions if not p.get("manual")]

        # v3.38: SNIPER DUA LAPIS saat menerima sinyal dari M15
        # LAPIS 1 - M5: momentum searah wajib (EMA8 M5 + candle M5 searah)
        m5 = self.broker.copy_rates(sym, "M5", self.cfg.get("bars_m5", 200))
        ok5, why5 = cc_scanner.sniper_m5(res, m5, self.cfg)
        if not ok5:
            res["status"] = "SNIPER_WAIT"
            res["sniper_why"] = why5
            return
        # LAPIS 2 - M1: pullback-resume, momen paling presisi (v3.08)
        m1 = self.broker.copy_rates(sym, "M1", self.cfg.get("bars_m1", 120))
        delta = self.broker.tick_delta(sym, 120)
        ok, why = cc_scanner.sniper_m1(res, m1, self.cfg, delta)
        if not ok:
            res["status"] = "SNIPER_WAIT"
            res["sniper_why"] = why
            return
        res["sniper_why"] = "%s + %s" % (why5, why)

        # gates pelindung anti SL-beruntun (v3.06)
        now = time.time()
        g_ok, g_why = self.risk.streak_ok(now)
        if g_ok:
            g_ok, g_why = self.risk.session_ok(res["symbol"], now)
        if g_ok:
            g_ok, g_why = self.risk.cooldown_ok(res["symbol"], now)
        # v3.35: filter KUOTA harian DIHAPUS (permintaan user). Satu-satunya
        # filter jeda = COOLDOWN 30 menit utk pair yang baru saja minus.
        if g_ok:
            g_ok, g_why = self.risk.cluster_ok(res["symbol"], bot_positions)
        # CATATAN v3.08: anti-kejar-harga TIDAK lagi memblokir -> sniper M1
        # MENAHAN entry sampai pullback+momentum pas (lihat sniper_m1).
        # gates lama
        info = res.get("info") or {}
        if g_ok:
            g_ok, g_why = self.risk.spread_ok(res["symbol"], info.get("spread_points", 0))
        if g_ok:
            g_ok, g_why = self.risk.sl_bounds_ok(res["sl_points"])
        if g_ok:
            g_ok, g_why = self.risk.can_open(res["symbol"], bot_positions)
        cur, rate = self.account_usd_rate()
        lot = 0.0
        lot_why = ""
        if g_ok:
            lot, lot_why = self.risk.calc_lot(res["symbol"], info, res["sl_points"],
                                              cur, rate)
            if lot <= 0:
                g_ok, g_why = False, lot_why
        # v4.37 (user): LOT MANUAL per pair -- menimpa kalkulasi risiko;
        # blokir khusus lot<=0 dibolehkan lewat (guard lain tetap jalan)
        _ulot = self.pair_lot_of(res["symbol"])
        if _ulot:
            if not g_ok and lot <= 0 and lot_why and g_why == lot_why:
                g_ok, g_why = True, ""
            self.emit_log("INFO", "%s: LOT MANUAL %.2f (menimpa kalkulasi)"
                          % (res["symbol"], _ulot))
            lot = _ulot
        else:
            # v4.42 (user): AUTO = lot TERKECIL pair (volume_min broker)
            _ml = _min_lot(info)
            if not g_ok and lot <= 0 and lot_why and g_why == lot_why:
                g_ok, g_why = True, ""
            if abs(float(lot or 0) - _ml) > 1e-12:
                self.emit_log("INFO", "%s: AUTO -> lot terkecil %.2f"
                              % (res["symbol"], _ml))
            lot = _ml
        if not g_ok:
            res["status"] = "BLOCKED"
            res["block_why"] = g_why
            self._write_signal(res["symbol"], side, score, lot, res["price"],
                               res["sl_price"], res["tp_price"], "SKIP", g_why)
            self.emit_log("WARN", "%s %s skor %.1f -> SKIP (%s)"
                          % (res["symbol"], side, score, g_why))
            return

        # TP struktural v3.16: BODY SNR/HH-HL H1 terdekat (bukan wick) +
        # wajib RR BERSIH setelah dikurangi spread + komisi
        # v3.20: seluruh blok analisis TP dibungkus fail-open -> kalau apapun
        # gagal (data H1 error dsb), pakai TP hard 1.0R dan ORDER TETAP JALAN.
        try:
            self._apply_structural_tp(res, side, score, lot, info, sym, rate)
        except ValueError as e:
            # RR bersih kurang -> SKIP sungguhan (RR terjaga)
            res["status"] = "BLOCKED"
            res["block_why"] = str(e)
            self._write_signal(sym, side, score, lot, res["price"],
                               res["sl_price"], res["tp_price"], "SKIP", str(e))
            self.emit_log("WARN", "%s %s -> SKIP (%s)" % (sym, side, str(e)))
            return
        except Exception:
            # error data/analisis lain -> jangan blokir entry: pakai TP hard
            self.emit_log("WARN", "%s analisis TP gagal -> pakai TP hard %.2f"
                          % (sym, res["tp_price"]))
        net_ok, net_rr = cc_scanner.tp_net_check(side, res["price"],
                                                 res["tp_price"],
                                                 res["sl_points"]
                                                 * (res.get("point") or 0.0),
                                                 0.0,
                                                 self.cfg.get("tp_min_rr_net", 0.6))
        if not net_ok:
            res["status"] = "BLOCKED"
            res["block_why"] = ("TP_NET_RR %.2fR < %.2fR"
                                % (net_rr, self.cfg.get("tp_min_rr_net", 0.6)))
            self._write_signal(sym, side, score, lot, res["price"],
                               res["sl_price"], res["tp_price"], "SKIP",
                               res["block_why"])
            self.emit_log("WARN", "%s %s -> SKIP (%s)"
                          % (sym, side, res["block_why"]))
            return

        # ORDER DARI PYTHON
        r = self.broker.order_send(sym, side, lot, res["sl_price"], res["tp_price"],
                                   comment="CC-%s" % side)
        if r.ok:
            res["status"] = "TRADING"
            self.risk.note_open(res["symbol"])
            # v3.33: sinyal ini SUDAH DIPAKAI -> hapus kandidatnya. Re-entry
            # nanti harus dari sinyal baru hasil analisa terkini (semua filter
            # dijalankan ulang), bukan sinyal bekas.
            self.candidates.pop(res["symbol"], None)
            self.emit_log("ORDER", "%s %s %.2f lot @ %.*f | SL %.*f TP %.*f (skor %.1f, %s)"
                          % (res["symbol"], side, lot, info.get("digits", 2),
                             res["price"], info.get("digits", 2), res["sl_price"],
                             info.get("digits", 2), res["tp_price"], score, why))
            self.emit_log("BROKER", "MT5 order diterima (Ticket: %s)" % r.ticket)
            self._write_signal(res["symbol"], side, score, lot, res["price"],
                               res["sl_price"], res["tp_price"], "EMITTED", why)
        else:
            res["status"] = "BLOCKED"
            res["block_why"] = "BROKER: %s" % r.comment
            self.emit_log("WARN", "Order %s gagal: %s" % (res["symbol"], r.comment))
            self._write_signal(res["symbol"], side, score, lot, res["price"],
                               res["sl_price"], res["tp_price"], "FAIL", r.comment)

    # ------------------------------------------------------- STRATEGY 2 ----
    def _try_execute_s2(self, res, positions):
        """Eksekusi sinyal Strategy 2 (M5 konfirmasi sudah close).

        Urutan gerbang = EA v6.05 TryExecutePendingFirstEntry:
        max baskets -> cooldown -> warmup -> wick -> M1 struktur -> late ->
        SNR -> revalidasi momentum+presisi+MTF -> risk (spread/lot) -> order.
        SL = 0.80 x ATR M5 (frozen), TP = 0 (dikelola ATR trailing).
        """
        if self._market_guard_block(res.get("symbol"), res):
            return              # v3.86: guard jendela pasar (ketiga strg)
        sym = self.resolved.get(res["symbol"], res["symbol"])
        want = res["symbol"]
        ex = res.get("exec") or {}
        if not ex.get("sig"):
            # v3.60: tanpa paket sniper (pending EXPIRED/dll) -> jangan
            # pernah entry dari res usang
            self.candidates.pop(want, None)  # v3.65 AUDIT: buang kandidat
            res["status"] = "BLOCKED"
            res["block_why"] = "S2 tanpa paket eksekusi (sniper belum trigger)"
            return
        sig = ex.get("sig", res.get("side"))
        k = self.s2k
        bot_positions = [p for p in positions if not p.get("manual")]
        info = res.get("info") or self.broker.symbol_info(sym) or {}
        point = float(info.get("point") or res.get("point") or 0.0)

        def _hold_keep(why):
            # pending DITAHAN (gerbang pasar; v3.59 juga SNR/MTF saat bar
            # konfirmasi -- padanan EA "sinyal tetap disimpan"); log sekali
            # per alasan agar tidak spam tiap loop
            res["status"] = "HOLD_WAIT"
            res["why"] = why
            memo = getattr(self, "_s2_hold_memo", None)
            if not isinstance(memo, dict):
                memo = {}
            if memo.get(want) != why:      # v3.65 AUDIT: per-simbol
                memo[want] = why
                self._s2_hold_memo = memo
                self.emit_log("INFO", "%s %s" % (want, why))

        def _cancel(why):
            self.s2state.clear(want)
            self.s2state.save()
            self.candidates.pop(want, None)
            res["status"] = "BLOCKED"
            res["block_why"] = why
            self.emit_log("PROTECT", "%s %s" % (want, why))

        # posisi sudah ada di simbol -> jangan dobel (1 tiket/symbol EA)
        if any(p["symbol"] == sym for p in bot_positions):
            self.s2state.clear(want)
            self.s2state.save()
            self.candidates.pop(want, None)
            res["status"] = "TRADING"
            return
        # -- gerbang kuota & waktu (pending TETAP; padanan EA "sinyal tetap
        #    disimpan") --
        open_syms = set(p["symbol"] for p in bot_positions)
        max_b = int(k.get("max_baskets", 3))
        if len(open_syms) >= max_b:
            _hold_keep("MAX_BASKETS %d pair terbuka; sinyal %s menunggu slot"
                       % (len(open_syms), sig))
            return
        warmup_left = max(0, int(self.s2_started + float(k.get("warmup_sec", 20))
                                 - time.time()))
        if warmup_left > 0:
            _hold_keep("WARMUP %ds tersisa; sinyal %s menunggu"
                       % (warmup_left, sig))
            return
        cd = self.s2state.cooldown_until(want)
        if cd and time.time() < cd:
            _cancel("COOLDOWN exit %s masih aktif %d dtk"
                    % (want, int(cd - time.time())))
            return

        # v4.44 (user S4): MAX DAILY LOSS 30 USD / Rp 540.000 -- ikut
        # mata uang akun (IDR/USD); realized hari ini dari riwayat close.
        _dl = float(k.get("daily_loss_usd", 0.0) or 0.0)
        if _dl > 0:
            _now0 = time.time()
            _ts0, _real0 = getattr(self, "_s4_dl_cache", (0.0, 0.0))
            if _now0 - _ts0 > 60.0:
                try:
                    _cs = self.broker.closed_stats(
                        self.risk.day_since() if self.risk else 0)
                    _real0 = float((_cs or {}).get("realized", 0.0) or 0.0)
                except Exception:
                    _real0 = 0.0
                self._s4_dl_cache = (_now0, _real0)
            _cur0, _rate0 = self.account_usd_rate()
            _cu0 = str(_cur0 or "").upper()
            if _cu0 == "IDR":
                _cap0 = float(k.get("daily_loss_idr", 540000.0) or 540000.0)
            elif _cu0 == "USD":
                _cap0 = _dl
            else:
                _cap0 = _dl * float(_rate0 or 1.0)
            if _cap0 > 0 and _real0 <= -abs(_cap0):
                res["status"] = "BLOCKED"
                res["block_why"] = ("DAILY LOSS %.0f/%.0f %s"
                                    % (_real0, -_cap0, _cu0))
                self.emit_log("PROTECT", "%s -> SKIP (MAX DAILY LOSS "
                              "%.0f %s)" % (want, _cap0, _cu0))
                self.candidates.pop(want, None)
                return

        # -- data terbaru utk validasi eksekusi --
        data = self._fetch_data(want, sym)
        if not data or not data.get("m1") or not data.get("m5"):
            _hold_keep("data eksekusi belum siap; sinyal %s menunggu" % sig)
            return
        tick = self.broker.symbol_tick(sym) if hasattr(self.broker, "symbol_tick") else {}
        bid = float((tick or {}).get("bid") or info.get("bid") or 0.0)
        ask = float((tick or {}).get("ask") or info.get("ask") or 0.0)
        if bid <= 0 or ask <= 0:
            _hold_keep("harga belum siap; sinyal %s menunggu" % sig)
            return
        ok, why, sl_price, tp_price, keep = cc_strategy2.validate_execution(
            want, res, data, bid, ask, k, self.s2state,
            cooldown_until=cd, open_baskets=len(open_syms),
            warmup_left=warmup_left)
        if not ok:
            # v3.59: keep=True (SNR/MTF/ATR belum siap) -> pending DITAHAN
            # spt EA (retry sepanjang bar konfirmasi); keep=False -> hangus
            (_hold_keep if keep else _cancel)(why)
            return

        # -- PIP-KALIBRASI (mis. BTCUSD dgn data lama user): TP fix poin,
        #    SL = TP x (12/20), lot = ceil agar TP uang tercapai.  Pair di
        #    cfg["s2"]["pip_symbols"] TIDAK lewat calc_lot ATR.
        plan = None
        pip_syms = k.get("pip_symbols") or {}
        sm_usd2 = float(self.cfg.get("sl_money_usd", 0.0) or 0.0)
        tp_usd2 = float(self.cfg.get("tp_money_usd", 0.0) or 0.0)
        if want in pip_syms and sm_usd2 > 0 and tp_usd2 > 0:
            plan = cc_strategy2.pip_entry_plan(
                float((pip_syms[want] or {}).get("tp_price", 0.0) or 0.0),
                sm_usd2, tp_usd2, info)
            if plan and plan["lot"] > 0:
                sl_dist_px = plan["sl_dist"]
                sl_price = (ask - sl_dist_px) if sig == "BUY" \
                    else (bid + sl_dist_px)
                tp_price = 0.0
                if self.cfg.get("tp_broker_hard", False):
                    tp_price = (ask + plan["tp_dist"]) if sig == "BUY" \
                        else (bid - plan["tp_dist"])
        # -- gates risk (lot dinamis per pair = "seperti strategy 1 lama") --
        g_ok, g_why = True, ""
        spread_lim = cc_strategy2.spread_limit(k, want, sym)
        spr = int(info.get("spread_points", 0) or 0)
        if spread_lim > 0 and spr > spread_lim:
            g_ok, g_why = False, "SPREAD %d > %d" % (spr, spread_lim)
        if g_ok:
            g_ok, g_why = self.risk.can_open(want, bot_positions)
        cur, rate = self.account_usd_rate()
        lot = 0.0
        lot_why = ""
        if plan:
            lot = plan["lot"]          # lot hasil kalibrasi pip (BTC)
        else:
            sl_points = abs(ask - sl_price) / point if point > 0 else 0.0
            if g_ok:
                lot, lot_why = self.risk.calc_lot(want, info, sl_points,
                                                  cur, rate)
                if lot <= 0:
                    g_ok, g_why = False, lot_why
        # v4.22 (permintaan user -- mencabut SKIP_LOT_KECIL v4.16):
        # TIDAK ADA entry yang di-SKIP karena lot.  Lot kalkulasi di
        # bawah minimum TANGGA TP diNAIKKAN ke min_entry_lot (0.04)
        # agar trailing TP selalu bisa jalan di semua entry.  Catatan
        # jujur: risiko riil bisa melebihi 3%% bila SL lebar -- daily
        # loss cap 10%% tetap pengaman terakhir.  Lot 0 (guard risiko/
        # daily lock) TETAP diblokir -- itu pelindung, bukan soal lot.
        if g_ok and float(self.cfg.get("tp2_rr", 0.0) or 0.0) > 0:
            _ml = float(self.cfg.get("min_entry_lot", 0.04) or 0.04)
            if 0.0 < float(lot or 0.0) < _ml - 1e-12:
                self.emit_log("INFO", "%s: lot %.3f < minimum tangga TP "
                              "-> dinaikkan ke %.2f (v4.22, tanpa "
                              "skip)" % (want, float(lot), _ml))
                lot = _ml
        # v4.37 (user): LOT MANUAL per pair -- menimpa lot plan/kalkulasi;
        # blokir khusus lot<=0 dibolehkan lewat (guard lain tetap jalan)
        _ulot = self.pair_lot_of(want)
        if _ulot:
            if not g_ok and lot <= 0 and lot_why and g_why == lot_why:
                g_ok, g_why = True, ""
            self.emit_log("INFO", "%s: LOT MANUAL %.2f (menimpa kalkulasi)"
                          % (want, _ulot))
            lot = _ulot
        else:
            # v4.42 (user): AUTO = lot TERKECIL pair (volume_min broker)
            # -- menimpa kalkulasi risiko & lift min_entry_lot (v4.22)
            _ml = _min_lot(info)
            if not g_ok and lot <= 0 and lot_why and g_why == lot_why:
                g_ok, g_why = True, ""
            if abs(float(lot or 0) - _ml) > 1e-12:
                self.emit_log("INFO", "%s: AUTO -> lot terkecil %.2f"
                              % (want, _ml))
            lot = _ml
        if not g_ok:
            res["status"] = "BLOCKED"
            res["block_why"] = g_why
            self._write_signal(want, sig, res.get("score", 0), lot, ask,
                               sl_price, 0.0, "SKIP", g_why)
            self.emit_log("WARN", "%s %s -> SKIP (%s)" % (want, sig, g_why))
            return

        # -- TP minimal (USD): jarak = SL_dist x (tp/sl).  SL 0.8 ATR dgn
        #    12 USD -> TP 20 USD = 1.333 x ATR.  Mode default VIRTUAL:
        #    begitu +20 tersentuh, SL dikunci >= +20 dan ATR trailing
        #    lanjut (profit bisa jauh lebih besar dari 20).
        sm_usd = float(self.cfg.get("sl_money_usd", 0.0) or 0.0)
        tp_usd = float(self.cfg.get("tp_money_usd", 0.0) or 0.0)
        tp_price = 0.0
        sl_dist_px = abs(ask - sl_price)
        tp_hard = str(self.cfg.get("tp_mode", "close") or "close").strip()\
            .lower() == "close"
        # v3.83 (permintaan user): ACUAN TP = RR -- TP = tp_rr x jarak SL
        # (RR 1:2 = tp_rr 2.0).  tp_rr <= 0 -> fallback cara lama (rasio
        # uang tp_money/sl_money).  TP virtual kecuali tp_broker_hard.
        tp_rr_v = float(self.cfg.get("tp_rr", 0.0) or 0.0)
        # v4.12 TANGGA TP (permintaan user): TP1 = tp1_rr (2R) tutup
        # tp1_close_pct% (75%); sisanya ke TP2 = tp2_rr (4R) dgn SL
        # trailing tiap tp2_trail_step_r (0.5R).  tp1_rr<=0 -> perilaku
        # lama (tp_rr penuh, tanpa tangga).
        self._tp1_rr = float(self.cfg.get("tp1_rr", 0.0) or 0.0)
        self._tp2_rr = float(self.cfg.get("tp2_rr", 0.0) or 0.0)
        self._tp1_pct = float(self.cfg.get("tp1_close_pct", 75.0) or 75.0)
        self._tp_step = float(self.cfg.get("tp2_trail_step_r", 0.5) or 0.0)
        if self._tp1_rr <= 0:
            self._tp1_rr = tp_rr_v
        tp1_v = self._tp1_rr
        tp_tpd = 0.0
        if tp1_v > 0 and sl_dist_px > 0:
            tp_tpd = sl_dist_px * tp1_v
            # v3.99 FIX "TP kelewatan/terlambat": TP dipasang DI
            # BROKER (server-side) -> dieksekusi broker saat harga
            # menyentuh, TANPA menunggu polling engine.  Hanya utk
            # tp_mode "close"; mode "trail" tetap virtual (SL dikunci
            # di target + trailing lanjut).
            if self.cfg.get("tp_broker_hard", False) and tp_hard:
                # v4.12: TP broker = TP2 (bukan TP1!) supaya broker
                # tidak menutup 100% saat TP1 (2R) tersentuh.
                _tp2d = (sl_dist_px * self._tp2_rr) \
                    if (self._tp2_rr > 0 and sl_dist_px > 0) else 0.0
                if _tp2d > 0:
                    tp_price = (ask + _tp2d) if sig == "BUY" \
                        else (bid - _tp2d)
        elif tp_usd > 0 and sm_usd > 0 and sl_dist_px > 0 and \
                tp_hard and self.cfg.get("tp_broker_hard", False):
            tp_dist = sl_dist_px * (tp_usd / sm_usd)
            tp_price = (ask + tp_dist) if sig == "BUY" else (bid - tp_dist)
        r = self.broker.order_send(sym, sig, lot, sl_price, tp_price,
                                   comment="S2-%s" % sig)
        if r.ok:
            res["status"] = "TRADING"
            self.risk.note_open(want)
            self.s2state.clear(want)
            self.candidates.pop(want, None)
            # seed ATR trail dari fill aktual (ATR frozen at entry)
            entry_px = float(ask)
            atr_m5 = cc_strategy2.atr_at(data["m5"],
                                         int(k.get("atr_period", 14)))
            try:
                for p in self.broker.positions():
                    if p["symbol"] == sym and not p.get("manual"):
                        entry_px = float(p.get("entry", entry_px))
                        break
            except Exception:
                pass
            if atr_m5 and atr_m5 > 0:
                k2 = dict(k)
                try:   # v3.60: lantai SL breathing ikut ke baseline trail
                    k2["sl_atr"] = float(ex.get("sl_mult_eff")
                                         or k.get("sl_atr", 0.80))
                except Exception:
                    pass
                _tr = cc_strategy2.ATRTrail(
                    want, 1 if sig == "BUY" else -1, entry_px, atr_m5, k2,
                    tp_dist=tp_tpd,
                    tp_r=(tp1_v if tp_tpd > 0 else 0.0))
                if tp_tpd > 0 and self._tp2_rr > 0 and sl_dist_px > 0:
                    _tr.tp2_dist = sl_dist_px * self._tp2_rr
                    _tr.tp2_r = self._tp2_rr
                    _tr.trail_step_r = self._tp_step
                _tr.tp1_lock_r = float(
                    self.cfg.get("tp1_lock_r", 0.0) or 0.0)
                # v4.25: BEP di +1R sebelum TP1 (rumus user)
                _tr.bep_at_r = float(self.cfg.get("bep_at_r", 1.0)
                                     or 0.0)
                _tr.bep_offset_r = float(self.cfg.get("bep_offset_r",
                                                      0.0) or 0.0)
                self.s2state.set_trail(want, _tr)
            # v4.44 (user S4): baseline = entry - SL ZONA aktual
            # (aturan 0.6R -> +0.2R harus presisi thd SL struktural,
            # bukan ATR).  Menimpa seed ATR di atas.
            if k.get("s4_exit"):
                try:
                    _rd = abs(entry_px - float(sl_price or 0.0))
                    if _rd > 0:
                        _k2 = dict(k)
                        _sm = float(_k2.get("sl_atr", 1.2) or 1.2)
                        self.s2state.set_trail(
                            want, cc_strategy2.ATRTrail(
                                want, 1 if sig == "BUY" else -1, entry_px,
                                _rd / _sm, _k2,
                                tp_dist=(abs(float(tp_price or 0.0)
                                             - entry_px)
                                         if tp_price else 0.0),
                                tp_r=(float(k.get("tp_rr", 1.0) or 0.0)
                                      if tp_price else 0.0)))
                except Exception:
                    pass
            self.s2state.save()
            if tp_tpd > 0 and self._tp2_rr > 0:
                tp_txt = ("TP1 %.1fR tutup %.0f%% -> TP2 %.1fR "
                          "(SL trail %.1fR, %s)"
                          % (tp1_v, self._tp1_pct, self._tp2_rr,
                             self._tp_step,
                             "TP2 hard broker" if tp_price else
                             "TP2 virtual engine"))
            elif tp_tpd > 0:
                tp_txt = ("TP %.1fR (RR 1:%.1f, %s)"
                          % (tp1_v, tp1_v,
                             "hard broker" if tp_price else
                             ("virtual CLOSE-TP" if tp_hard else
                              "virtual + trailing")))
            else:
                tp_txt = ("TP min %.0f USD (=%.2fxATR, %s)"
                          % (tp_usd,
                             float(k.get("sl_atr", 0.80)) * tp_usd /
                             max(sm_usd, 1e-9),
                             "hard broker" if tp_price else
                             ("virtual CLOSE-TP" if tp_hard else
                              "virtual + trailing")))
            self.emit_log("ORDER", "%s %s %.2f lot @ %.*f | SL %.2fxATR=%.*f "
                          "(=%.0f USD) | %s | skor %.0f MTF %s"
                          % (want, sig, lot, int(info.get("digits", 2)), entry_px,
                             float(k.get("sl_atr", 0.80)),
                             int(info.get("digits", 2)), sl_price,
                             sm_usd, tp_txt,
                             float(res.get("score", 0)),
                             (res.get("mtf") or {}).get("final", "-")))
            self.emit_log("BROKER", "MT5 order diterima (Ticket: %s)" % r.ticket)
            try:   # s.41 audit: lot & estimasi risiko uang ke journal
                _tsz = float(info.get("trade_tick_size", 0.0) or 0.0) or \
                    float(info.get("point", 0.0) or 0.0)
                _tv = float(info.get("trade_tick_value", 0.0) or 0.0)
                _vu = (_tv / _tsz) if (_tsz > 0 and _tv > 0) else 0.0
                cc_strategy2.journal(
                    os.path.join("data", "s3_journal.jsonl"),
                    {"symbol": want, "reason": "ORDER_EMITTED", "lot": lot,
                     "risk_money": (round(sl_dist_px * lot * _vu, 2)
                                    if _vu > 0 else None),
                     "entry": round(entry_px, 6), "sl": round(sl_price, 6),
                     "session": cc_strategy2.session_of()})
            except Exception:
                pass
            self._write_signal(want, sig, res.get("score", 0), lot, entry_px,
                               sl_price, 0.0, "EMITTED",
                               "S2 ATR entry MTF=%.1f"
                               % float((res.get("mtf") or {}).get("final", 0.0)))
        else:
            res["status"] = "BLOCKED"
            res["block_why"] = "BROKER: %s" % r.comment
            self.emit_log("WARN", "Order %s gagal: %s" % (want, r.comment))
            self._write_signal(want, sig, res.get("score", 0), lot, ask,
                               sl_price, 0.0, "FAIL", r.comment)
            # v3.65 AUDIT: order ditolak broker -> pending hangus + pair
            # dijeda 2 menit (anti spam order reject tiap scan)
            self.s2state.clear(want)
            self.s2state.set_cooldown(want, 2)
            self.s2state.save()
            self.candidates.pop(want, None)

    def _market_guard_block(self, want, res):
        """v3.86 MARKET GUARD (permintaan user, KETIGA strategy): SKIP
        entry 1 jam sebelum PENUTUPAN akhir pekan (auto AKTIF LAGI saat
        pembukaan) + SKIP semua entry 30 mnt sebelum daily ROLLOVER/
        market break (cegah entry nyangkut).  Pair 24/7 (kripto) bebas
        guard akhir pekan.  Reason: SKIP_SESSION / SKIP_ROLLOVER."""
        try:
            blk, _code, why = market_guard.entry_blocked(
                want, self.cfg.get("market_guard") or {})
        except Exception:
            return False
        if blk:
            res["status"] = "BLOCKED"
            res["block_why"] = why
            self.emit_log("PROTECT", "%s %s" % (want, why))
        return blk

    def _want_of(self, sym):
        """Peta symbol broker (mis. XAUUSDm) -> nama want (XAUUSD).

        State S2 (trail/cooldown) disimpan per nama want; posisi broker
        memakai nama symbol broker. Tanpa peta ini trailing S2 tidak jalan
        di broker bersuffix (bug audit)."""
        for w, s in (self.resolved or {}).items():
            if s == sym:
                return w
        return sym

    def _s2_manage_exits(self):
        """ATR trailing per posisi bot (padanan ManageBasketExitsOnly).

        floor ratio: peak<0.85 -> -0.80 initial; 0.85<=peak<1.25 -> lock
        +0.30 sekali; peak>=1.25 -> 1.20 + N x 0.05.  SL broker digeser ke
        floor; bila floor tertembus (stops level broker) -> close market.
        v3.82 tp_mode "close": begitu target tp_money_usd tersentuh ->
        LANGSUNG close di pasar (EXIT_TP), TANPA trailing.  tp_mode
        "trail" = perilaku lama: SL dikunci >= +target, trailing lanjut.
        """
        k = self.s2k
        pos = self.broker.positions()
        by_sym = {}
        for p in pos:
            if not p.get("manual"):
                by_sym.setdefault(p["symbol"], p)
        changed = False
        # v4.15 FIX BUG2: posisi bot dgn trail aktif MENGHILANG dari
        # broker antar siklus (harga gap tembus TP2 hard / SL broker)
        # -> tanpa ini trail nyangkut selamanya & cooldown tak terpasang.
        _openw = set()
        for _p in pos:
            if not _p.get("manual"):
                try:
                    _openw.add(self._want_of(_p["symbol"]))
                except Exception:
                    pass
        for _w in list(self.s2state.trail.keys()):
            if _w in _openw or not self.s2state.trail.get(_w):
                continue
            _tr = cc_strategy2.ATRTrail.from_dict(
                dict(self.s2state.trail.get(_w)))
            _sym2 = getattr(_tr, "symbol", _w)
            _tk2 = (self.broker.symbol_tick(_sym2)
                    if hasattr(self.broker, "symbol_tick") else {})
            _info2 = self.broker.symbol_info(_sym2) or {}
            _b2 = float((_tk2 or {}).get("bid")
                        or _info2.get("bid") or 0.0)
            _a2 = float((_tk2 or {}).get("ask")
                        or _info2.get("ask") or 0.0)
            _px2 = _b2 if getattr(_tr, "side", 1) > 0 else (_a2 or _b2)
            _rd2 = float(getattr(_tr, "risk_dist", 0.0) or 0.0)
            _rn2 = ((_px2 - _tr.entry) / _rd2
                    * getattr(_tr, "side", 1)) if (_rd2 > 0 and _px2 > 0) \
                else 0.0
            _t22 = float(getattr(_tr, "tp2_r", 0.0) or 0.0)
            if _t22 > 0 and _rn2 >= _t22 * 0.8:
                _cc2, _vv2 = "EXIT_TP2", _t22
            elif _rn2 <= 0.2:
                _cc2, _vv2 = "EXIT_SL_BROKER", _rn2
            else:
                _cc2, _vv2 = "EXIT_BROKER", _rn2
            self.emit_log("WARN", "%s posisi sudah ditutup broker "
                          "(%s @ %.2fR) -> state dirapikan + cooldown "
                          "aktif" % (_w, _cc2, _rn2))
            try:
                cc_strategy2.journal_exit(
                    os.path.join("data", "s3_journal.jsonl"),
                    _w, _tr, code=_cc2, r_multiple=_vv2)
            except Exception:
                pass
            self.s2state.set_cooldown(_w, int(k.get("cooldown_min", 10)))
            self.s2state.del_trail(_w)
            changed = True
        tp_usd = float(self.cfg.get("tp_money_usd", 0.0) or 0.0)
        rate_acc = float(self._rate_val or 0.0) or 1.0
        for bsym, p in list(by_sym.items()):
            want = self._want_of(bsym)
            tr = self.s2state.get_trail(want)
            if not tr:
                # v3.59: posisi BOT tanpa baseline (state hilang/engine
                # restart) -> seed ulang ATR trail dari entry aktual;
                # peak mulai 0 -> lantai kembali -0.8xATR awal (aman).
                # Posisi manual tetap TIDAK dipakaikan trail S2.
                if p.get("manual"):
                    continue
                try:
                    m5o = self.broker.copy_rates(bsym, "M5", 120)
                    atr_o = cc_strategy2.atr_at(
                        m5o, int(k.get("atr_period", 14))) if m5o else None
                    if atr_o and atr_o > 0:
                        _rr = float(self.cfg.get("tp_rr", 0.0) or 0.0)
                        _td = (_rr * atr_o *
                               float(k.get("sl_atr", 1.2))) if _rr > 0 \
                            else 0.0
                        tr = cc_strategy2.ATRTrail(
                            want, 1 if str(p.get("type")) == "BUY" else -1,
                            float(p.get("entry") or 0.0), atr_o, k,
                            tp_dist=_td, tp_r=(_rr if _td > 0 else 0.0))
                        # v4.25: BEP di +1R sebelum TP1 (rumus user)
                        tr.bep_at_r = float(self.cfg.get("bep_at_r",
                                                         1.0) or 0.0)
                        tr.bep_offset_r = float(self.cfg.get(
                            "bep_offset_r", 0.0) or 0.0)
                        self.s2state.set_trail(want, tr)
                        changed = True
                        self.emit_log("INFO", "%s: baseline trail hilang -> "
                                      "seed ulang (ATR %.5f, entry %.5f)"
                                      % (want, atr_o,
                                         float(p.get("entry") or 0.0)))
                except Exception:
                    tr = None
                if not tr:
                    continue
            sym = bsym
            info = self.broker.symbol_info(sym) or {}
            tick = self.broker.symbol_tick(sym) if hasattr(self.broker, "symbol_tick") else {}
            bid = float((tick or {}).get("bid") or info.get("bid") or 0.0)
            ask = float((tick or {}).get("ask") or info.get("ask") or 0.0)
            if bid <= 0 or ask <= 0:
                continue
            # v4.44 (user S4): exit khusus S4 -- floating 0.6R -> SL
            # geser ke +0.2R; tren pembalik + profit -> close market
            # (TP 1:1 sudah di broker).  Jalur ATR lama TIDAK utk S4.
            if k.get("s4_exit"):
                _rd = float(tr.risk_dist or 0.0)
                _px = bid if tr.side > 0 else ask
                _rn = ((_px - tr.entry) / _rd * tr.side) if _rd > 0 \
                    else 0.0
                if _rn > float(tr.peak or 0.0):
                    tr.peak = _rn
                _be_r = float(k.get("be_r", 0.6) or 0.6)
                _lk = float(k.get("be_lock_r", 0.2) or 0.2)
                if tr.peak >= _be_r and _rd > 0:
                    _new = tr.entry + _lk * _rd * tr.side
                    _cur = float(p.get("sl") or 0.0)
                    _imp = ((_new > _cur) if tr.side > 0
                            else (_cur <= 0 or _new < _cur))
                    if _imp:
                        try:
                            self.broker.modify_sl(p["ticket"], _new)
                            self.emit_log("INFO", "%s: S4 trailing "
                                          "peak %.1fR -> SL ke +%.1fR"
                                          % (want, tr.peak, _lk))
                        except Exception:
                            pass
                if _rn > 0:
                    try:
                        _m15 = self.broker.copy_rates(bsym, "M15", 300)
                        _sg = "BUY" if tr.side > 0 else "SELL"
                        if _m15 and cc_strategy2.s4_reversal(_m15, _sg, k):
                            self.broker.close_position(p["ticket"])
                            self.emit_log("INFO", "%s: S4 close "
                                          "REVERSAL dgn profit %.2fR"
                                          % (want, _rn))
                            try:
                                cc_strategy2.journal_exit(
                                    os.path.join("data",
                                                 "s3_journal.jsonl"),
                                    want, tr, code="S4_REVERSAL",
                                    r_multiple=_rn)
                            except Exception:
                                pass
                            self.s2state.set_cooldown(
                                want, int(k.get("cooldown_min", 10)))
                            self.s2state.del_trail(want)
                            changed = True
                    except Exception:
                        pass
                self.s2state.set_trail(want, tr)   # persist peak/mae
                continue
            u = tr.update(bid, ask)
            # ---- TP MINIMAL (USD), mode "trail" (lama): harga menyentuh
            #      +tp_usd -> SL DIKUNCI di level +tp_usd (lantai uang),
            #      ATR trailing lanjut -> profit minimal 20, bisa lebih.
            floor_price = u["floor_price"]
            lotp = float(p.get("lot", p.get("volume", 0.0)) or 0.0)
            tsz = float(info.get("trade_tick_size", 0.0) or 0.0) or \
                float(info.get("point", 0.0) or 0.0)
            tval = float(info.get("trade_tick_value", 0.0) or 0.0)
            val_unit = (tval / tsz) if (tsz > 0 and tval > 0) else 0.0
            tp_mode = str(self.cfg.get("tp_mode", "close") or \
                          "close").strip().lower()
            # v3.83: acuan TP = RR (tr.tp_dist dr rencana entry, RR 1:2 =
            # 2 x jarak SL); fallback target uang utk trail state lama.
            tp_td = float(getattr(tr, "tp_dist", 0.0) or 0.0)
            tp_rv = float(getattr(tr, "tp_r", 0.0) or 0.0)
            tp_touch = 0.0
            if tp_td > 0:
                tp_touch = (tr.entry + tp_td) if tr.side > 0 \
                    else (tr.entry - tp_td)
            elif tp_usd > 0 and val_unit > 0 and lotp > 0:
                tp_touch = cc_strategy2.tp_touch_price(
                    tr.entry, tr.side, tp_usd, lotp, val_unit, rate_acc)
            if tp_touch > 0:
                touched = cc_strategy2.tp_hit(tr.side, bid, ask, tp_touch)
                _det = "harga sekarang"
                _hi = _lo = None
                # v4.21: ekstrem candle M1 sejak posisi dibuka dihitung
                # SELALU (bukan cuma saat TP1 belum sentuh) -- dipakai
                # utk deteksi TP1/TP2 anti-lolos DAN puncak sebenarnya
                # utk geser SL (rumus user "SL geser tiap 0.5R" dari
                # puncak SEBENARNYA -- spike termasuk).
                try:
                    _m1 = self.broker.copy_rates(sym, "M1", 90)
                    _t0 = float(p.get("time") or 0.0)
                    # TANPA open-time valid -> candle DILEWATI (jangan
                    # pakai bar PRA-ENTRY -- false positive).
                    if _m1 and _m1.get("time") and _t0 > 0:
                        _tt, _hh, _ll = (_m1["time"], _m1["high"],
                                         _m1["low"])
                        for _i in range(len(_tt)):
                            if _t0 and float(_tt[_i]) < _t0:
                                continue
                            _hi = (float(_hh[_i]) if _hi is None
                                   else max(_hi, float(_hh[_i])))
                            _lo = (float(_ll[_i]) if _lo is None
                                   else min(_lo, float(_ll[_i])))
                except Exception:
                    _hi = _lo = None
                # v4.20 ANTI-LOLOS TP1: 3 detektor -- (1) harga sekarang,
                # (2) puncak R tersampel, (3) high/low candle M1.
                if not touched:
                    _tp1r = float(getattr(tr, "tp_r", 0.0) or 0.0)
                    if _tp1r > 0 and float(getattr(
                            tr, "peak", 0.0) or 0.0) >= _tp1r:
                        touched = True
                        _det = "puncak %.1fR" % float(
                            getattr(tr, "peak", 0.0))
                if not touched and _hi is not None:
                    touched = ((_hi >= tp_touch) if tr.side > 0
                               else (_lo <= tp_touch))
                    if touched:
                        _det = "candle M1 (spike)"
                # v4.20 GUARD TANGGA: tangga TP v4.13 (keputusan user)
                # WAJIB jalan -- tp_mode "trail" dari config lama TIDAK
                # BOLEH mematikan TP1/TP2 diam-diam.
                if tp_mode != "close" and float(getattr(
                        self, "_tp2_rr", 0.0) or 0.0) > 0.0:
                    tp_mode = "close"
                    if not self._tpmode_warned:
                        self._tpmode_warned = True
                        self.emit_log(
                            "WARN", "tp_mode 'trail' DIABAIKAN -- "
                            "tangga TP v4.13 aktif (TP1 %.0f%% di %.1fR "
                            "-> TP2 %.1fR)"
                            % (float(self.cfg.get("tp1_close_pct", 75.0)
                                     or 75.0),
                               float(getattr(tr, "tp_r", 0.0) or 0.0),
                               float(getattr(self, "_tp2_rr", 0.0)
                                     or 0.0)))
                if tp_mode == "close":
                    # v4.12 TANGGA TP: TP1 = 2R tutup 75% (SL -> BE),
                    # sisa jalan ke TP2 (4R) dgn SL trailing 0.5R.
                    # Lot terlalu kecil utk dipecah -> full close (lama).
                    _vmin = float(getattr(info, "volume_min", 0.0) or 0.0) \
                        if hasattr(info, "volume_min") else \
                        float((info or {}).get("volume_min", 0.0) or 0.0)
                    _vstep = float(getattr(info, "volume_step", 0.0) or 0.0) \
                        if hasattr(info, "volume_step") else \
                        float((info or {}).get("volume_step", 0.0) or 0.0)
                    _t2c = None
                    _pk = None
                    _rdk = float(getattr(tr, "risk_dist", 0.0) or 0.0)
                    try:   # v4.20: TP2 anti-lolos (candle + harga)
                        _tp2d = float(getattr(tr, "tp2_dist", 0.0) or 0.0)
                        if _tp2d > 0:
                            _tp2px = tr.entry + tr.side * _tp2d
                            _t2c = cc_strategy2.tp_hit(tr.side, bid, ask,
                                                       _tp2px)
                            if not _t2c and _hi is not None:
                                _t2c = ((_hi >= _tp2px) if tr.side > 0
                                        else (_lo <= _tp2px))
                    except Exception:
                        _t2c = None
                    try:   # v4.21: puncak SEBENARNYA utk geser SL
                        if _hi is not None and _rdk > 0:
                            _rp = ((_hi - tr.entry) / _rdk) * tr.side
                            _pk = max(float(getattr(tr, "peak", 0.0)
                                            or 0.0), _rp)
                    except Exception:
                        _pk = None
                    _d = cc_strategy2.tp_ladder_decision(
                        tr, bid, ask, touched, lotp, _vmin, _vstep,
                        tp1_pct=float(self.cfg.get("tp1_close_pct", 75.0)),
                        tp2_touched=_t2c, peak_r=_pk)
                    if _d["action"] == "partial":
                        r2 = self.broker.close_volume(p["ticket"],
                                                      _d["volume"])
                        if r2 and getattr(r2, "ok", False):
                            tr.tp1_hit = 1
                            _lock = float(getattr(tr, "tp1_lock_r",
                                                  0.0) or 0.0)
                            _lockpx = (tr.entry + tr.side * _lock *
                                       float(getattr(tr, "risk_dist",
                                                     0.0) or 0.0)) \
                                if _lock > 0 else tr.entry
                            self.emit_log(
                                "CLOSE", "%s TP1 +%.1fR: tutup %.0f%% "
                                "(%.2f lot) -- sisa %.2f lot lanjut TP2 "
                                "+%.1fR, SL DIKUNCI +%.1fR, trailing "
                                "tiap %.1fR (deteksi: %s)"
                                % (want, tp_rv,
                                   float(self.cfg.get("tp1_close_pct",
                                                      75.0)),
                                   _d["volume"], _d["remain"],
                                   float(getattr(tr, "tp2_r", 0.0) or 0.0),
                                   _lock,
                                   float(getattr(tr, "trail_step_r", 0.0)
                                         or 0.0), _det))
                            # v4.15 FIX BUG1: TP1 (profit 75%) WAJIB
                            # masuk jurnal -- dulu hanya log dashboard,
                            # statistik jurnal jadi kelihatan lebih
                            # jelek dari kenyataan.
                            try:
                                cc_strategy2.journal_exit(
                                    os.path.join("data",
                                                 "s3_journal.jsonl"),
                                    want, tr, lot=float(_d["volume"]),
                                    code="EXIT_TP1",
                                    r_multiple=(tp_rv if tp_rv > 0
                                                else None))
                            except Exception:
                                pass
                            try:
                                self.broker.modify_sl(p["ticket"],
                                                      _lockpx, None)
                            except Exception:
                                pass
                            self.s2state.trail[want] = tr.to_dict()
                            self.s2state.save()
                            changed = True
                            continue
                        self.emit_log("WARN", "%s partial TP1 gagal (%s) "
                                      "-> full close"
                                      % (want, getattr(r2, "comment", "?")))
                        _d = {"action": "full", "code": "EXIT_TP"}
                    if _d["action"] == "full":
                        r2 = self.broker.close_position(p["ticket"])
                        if r2 and getattr(r2, "ok", False):
                            _code = _d.get("code", "EXIT_TP")
                            _rv = (float(getattr(tr, "tp2_r", 0.0) or 0.0)
                                   if _code == "EXIT_TP2" else tp_rv)
                            if _code == "EXIT_TP2":
                                self.emit_log("CLOSE", "%s TP2 +%.1fR "
                                              "tercapai -> posisi ditutup "
                                              "penuh" % (want, _rv))
                            elif tp_rv > 0:
                                self.emit_log("CLOSE", "%s ditutup CLOSE "
                                              "TP @ +%.1fR (RR 1:%.1f)"
                                              % (want, tp_rv, tp_rv))
                            else:
                                self.emit_log("CLOSE", "%s ditutup CLOSE "
                                              "TP @ target +%.0f USD"
                                              % (want, tp_usd))
                            sm_m = float(self.cfg.get("sl_money_usd",
                                                      0.0) or 0.0)
                            try:
                                cc_strategy2.journal_exit(
                                    os.path.join("data",
                                                 "s3_journal.jsonl"),
                                    want, tr,
                                    pl_money=(float(tp_usd)
                                              if tp_rv <= 0 else None),
                                    lot=lotp, code=_code,
                                    r_multiple=(_rv if _rv > 0 else
                                                ((tp_usd / sm_m)
                                                 if sm_m > 0 else None)))
                            except Exception:
                                pass
                            self.s2state.set_cooldown(
                                want, int(k.get("cooldown_min", 10)))
                            self.s2state.del_trail(want)
                            changed = True
                            continue
                        # v4.15 FIX BUG2: posisi bisa sudah ditutup
                        # broker sendiri (harga gap tembus TP2 hard /
                        # SL broker) -> jangan deadlock: posisi hilang
                        # tapi trail nyangkut & cooldown tak terpasang.
                        _still = [q for q in
                                  (self.broker.positions() or [])
                                  if q.get("ticket") == p["ticket"]]
                        if not _still:
                            _pxx = bid if tr.side > 0 else ask
                            _rdd = float(getattr(tr, "risk_dist",
                                                 0.0) or 0.0)
                            _rnow = ((_pxx - tr.entry) / _rdd
                                     * tr.side) if _rdd > 0 else 0.0
                            _t2 = float(getattr(tr, "tp2_r", 0.0)
                                        or 0.0)
                            if _t2 > 0 and _rnow >= _t2 * 0.8:
                                _c2, _v2 = "EXIT_TP2", _t2
                            elif _rnow <= 0.2:
                                _c2, _v2 = "EXIT_SL_BROKER", _rnow
                            else:
                                _c2, _v2 = "EXIT_BROKER", _rnow
                            self.emit_log(
                                "WARN", "%s posisi sudah ditutup "
                                "broker (%s @ %.2fR) -> state "
                                "dirapikan + cooldown aktif"
                                % (want, _c2, _rnow))
                            try:
                                cc_strategy2.journal_exit(
                                    os.path.join("data",
                                                 "s3_journal.jsonl"),
                                    want, tr, lot=lotp, code=_c2,
                                    r_multiple=_v2)
                            except Exception:
                                pass
                            self.s2state.set_cooldown(
                                want, int(k.get("cooldown_min", 10)))
                            self.s2state.del_trail(want)
                            changed = True
                            continue
                        self.emit_log("WARN", "%s close TP retry: %s"
                                      % (want, getattr(r2, "comment", "?")))
                        continue      # posisi benar2 masih ada -> retry
                    if _d["action"] == "sl":
                        # v4.12: SL trailing (ratchet, min BE); v4.28:
                        # step 0.2R -> wajib bulatkan ke digits simbol
                        # (float 0.6000000000001 = reject broker)
                        sl_px = tr.entry + tr.side * float(_d["sl_r"]) \
                            * float(getattr(tr, "risk_dist", 0.0) or 0.0)
                        sl_px = round(sl_px, int(info.get("digits", 5)
                                                 or 5))
                        cur_sl = float(p.get("sl", 0.0) or 0.0)
                        tks = float(info.get("trade_tick_size", 0.0) or 0.0) \
                            or float(info.get("point", 0.0) or 0.00001)
                        if cc_strategy2.atr_stop_improves(
                                tr.side, sl_px, cur_sl, tks):
                            rr2 = self.broker.modify_sl(p["ticket"],
                                                        sl_px, None)
                            if rr2 and getattr(rr2, "ok", True):
                                tr.last_sl_r = float(_d["sl_r"])
                                self.emit_log("TRAIL", "%s: peak "
                                              "%.1fR -> SL dikunci +%.1fR"
                                              % (want, tr.peak,
                                                 float(_d["sl_r"])))
                                self.s2state.trail[want] = tr.to_dict()
                                changed = True
                        else:
                            tr.last_sl_r = float(_d["sl_r"])
                if touched and not getattr(tr, "tp_released", 0):
                    tr.tp_released = 1
                    if tp_rv > 0:
                        self.emit_log("TRAIL", "%s: TP +%.1fR (RR 1:%.1f) "
                                      "tersentuh -> SL DIKUNCI, trailing "
                                      "LANJUT" % (want, tp_rv, tp_rv))
                    else:
                        self.emit_log("TRAIL", "%s: TP min %.0f USD "
                                      "tersentuh -> SL DIKUNCI >= +%.0f USD, "
                                      "trailing LANJUT" % (want, tp_usd, tp_usd))
                if getattr(tr, "tp_released", 0):
                    floor_price = max(floor_price, tp_touch) if tr.side > 0 \
                        else min(floor_price, tp_touch)
                    # lantai uang AKTIF juga sbg virtual close: harga
                    # MENEMBUS ke bawah lantai -> tutup seketika (jangan
                    # tunggu floor ATR yg jauh di bawah -- khusus pair
                    # pip-kalibrasi spt BTC).  Di pas lantai = masih hold
                    # (lock +20, trailing lanjut).
                    if tr.side > 0:
                        u["close_now"] = u["close_now"] or (bid < floor_price)
                    else:
                        u["close_now"] = u["close_now"] or (ask > floor_price)
            # PERSIST progress trail (peak/floor/tp_released): get_trail()
            # memberi COPY -- tanpa simpan balik, progress hilang antar loop
            # (bug audit: virtual floor bisa "turun" setelah restart loop).
            prev_t = self.s2state.trail.get(want) or {}
            if (tr.peak > float(prev_t.get("peak", -1e18)) + 1e-12
                    or tr.floor > float(prev_t.get("floor", -1e18)) + 1e-12
                    or int(getattr(tr, "tp_released", 0))
                    != int(prev_t.get("tp_released", 0))):
                self.s2state.trail[want] = tr.to_dict()
                changed = True
            if u["close_now"]:
                r = self.broker.close_position(p["ticket"])
                why = ("ATR %s floor crossed (peak %.2fx, floor %.2fx)"
                       % (u["phase"], u["peak"], u["floor"]))
                if r and getattr(r, "ok", False):
                    self.emit_log("CLOSE", "%s ditutup ATR TRAIL | %s"
                                  % (want, why))
                    # S3 JOURNAL (blueprint s.41/s.44): kode exit + R/MAE/MFE
                    try:
                        cc_strategy2.journal_exit(
                            os.path.join("data", "s3_journal.jsonl"),
                            want, tr, lot=lotp)
                    except Exception:
                        pass
                else:
                    self.emit_log("WARN", "%s close retry: %s"
                                  % (want, getattr(r, "comment", "?")))
                self.s2state.set_cooldown(want, int(k.get("cooldown_min", 10)))
                self.s2state.del_trail(want)
                changed = True
                continue
            if floor_price > -float(k.get("sl_atr", 0.80)) + 1e-9:
                # SL broker digeser ke floor gabungan (ATR trail / lantai
                # uang TP minimal) -- hanya membaik; virtual floor tetap
                # jaga bila broker menolak
                cur_sl = float(p.get("sl", 0.0) or 0.0)
                tick_size = float(info.get("trade_tick_size", 0.0) or 0.0) or \
                    float(info.get("point", 0.0) or 0.00001)
                improves = cc_strategy2.atr_stop_improves(
                    tr.side, floor_price, cur_sl, tick_size)
                if improves:
                    rr = self.broker.modify_sl(p["ticket"], floor_price, None)
                    if rr and getattr(rr, "ok", True):
                        self.emit_log("TRAIL", "%s %s: peak %.2fx -> SL %.5f"
                                      % (want, u["phase"], u["peak"],
                                         floor_price))
                    else:
                        self.emit_log("WARN", "%s modify SL gagal (%s); "
                                      "virtual floor tetap jaga"
                                      % (want, getattr(rr, "comment", "?")))
        if changed:
            self.s2state.save()

    # -------------------------------------------------------------- status ---
    def _watchdog_check(self):
        """v4.19 ANTI-BENGONG: heartbeat ditulis loop utama tiap siklus;
        method ini dipanggil dari THREAD DASHBOARD (tetap hidup walau
        loop utama gantung) -> banner merah + alert TG anti-spam 10 mnt.
        Inilah pengganti 'seolah aktif padahal bengong'."""
        hb_age = -1.0          # -1 = belum ada heartbeat (baru start)
        try:
            with open(os.path.join("data", "cc_heartbeat.json")) as _f:
                hb_age = time.time() - float(json.load(_f).get("ts")
                                             or 0.0)
        except Exception:
            pass
        stale = hb_age > 45.0
        if hb_age > 600.0 and \
                time.time() - self._stale_alert_ts > 600.0:
            self._stale_alert_ts = time.time()
            self.emit_log("WARN", "ENGINE BENGONG: loop utama tidak "
                          "aktif %.0f menit (heartbeat beku) -- cek "
                          "terminal MT5/VPS" % (hb_age / 60.0))
        return hb_age, stale

    def get_status(self) -> dict:
        with self.status_lock:
            log_lines = list(self.log_lines[-40:])
        hb_age, hb_stale = self._watchdog_check()
        b = self.broker
        acc = b.account() if b else {}
        pos = b.positions() if b else []
        balance = float(acc.get("balance", 0.0))
        equity = float(acc.get("equity", balance))
        ccy = (acc.get("currency") or "USD").upper()
        try:
            self.risk.ensure_day()   # v3.58/3.66: reset harian WIB selalu
        except Exception:            #   segar SEBELUM kartu dihitung
            pass
        since0 = self.risk.day_since() if self.risk else 0
        # statistik posisi TERTUTUP hari ini (riwayat deal nyata / simulasi)
        closed = {"realized": 0.0, "wins": 0, "losses": 0, "lots": 0.0,
                  "commission": 0.0}
        usd_rate = 0.0
        rekap_since = 0
        if b is not None:
            # v3.57: jendela rekap mengikuti APLIKASI HP user = tengah
            # malam WIB (day_stats_mode "wib", default). "broker" = hari
            # server broker (opsional di cc_config).
            if str(self.cfg.get("day_stats_mode", "wib")).lower() == \
                    "broker" and b is not None:
                try:
                    since_stats = b.broker_day_since()
                except Exception:
                    since_stats = None
                since_stats = since_stats or since0
            else:
                since_stats = since0
            try:
                closed = b.closed_stats(since_stats)
            except Exception:
                pass
            rekap_since = int(since_stats or 0)
            try:
                usd_rate = float(b.usd_to_account_rate(ccy) or 0.0)
            except Exception:
                usd_rate = 0.0
        floating = equity - balance
        # v3.51 komisi: pakai komisi ASLI broker dari riwayat deal closed
        # (account ccy). Fallback estimasi lots x tarif x kurs bila broker
        # tidak menyediakan (mis. simulasi).
        real_comm = closed.get("commission")
        if real_comm is not None:
            # v3.98 FIX PENCATATAN: data ASLI broker menang
            # TERMASUK nilainya 0 (akun 0-komisi/spread) -- dulu 0
            # dianggap "tak ada" -> tercatat estimasi $4/lot (phantom)
            commission = round(float(real_comm), 2)
        else:
            commission = round(float(closed.get("lots", 0.0))
                               * _eff_comm_usd(self.broker, self.cfg,
                                               usd_rate)
                               * usd_rate, 2) if usd_rate else 0.0
        # v3.37: realized SUDAH memakai komisi ASLI broker (dalam mata uang
        # akun) -> TIDAK dikurangi estimasi lagi (dulu dobel -> salah catat)
        realized_ccy = round(float(closed.get("realized", 0.0)), 2)
        # v3.53: PROFIT & LOSS TERCATAT = bruto per order close
        gw = round(float(closed.get("gross_win", 0.0) or 0.0), 2)
        gl = round(float(closed.get("gross_loss", 0.0) or 0.0), 2)
        # v3.58: operasi balance asli (deposit/WD) dari riwayat deal
        bal_ops = round(float(closed.get("bal_ops", 0.0) or 0.0), 2)
        # v3.55: deteksi otomatis akun KOMISI vs SPREAD
        _cmm = ("KOMISI" if abs(commission) > 0.004
                else ("SPREAD" if float(closed.get("lots", 0.0) or 0.0) > 0
                      else "-"))
        # v3.51: daily_status dgn realized+balance -> kartu harian basis
        # CLOSED-ONLY (loss/dd dari order close), guard tetap sesuai mode.
        daily = self.risk.daily_status(equity, realized=realized_ccy,
                                       balance=balance) \
            if self.risk else {}
        # v3.58: day_start KARTU = self-correcting, bebas drift/restart:
        # balance sekarang - P/L hari ini - deposit/WD hari ini
        day_start_live = (round(balance - realized_ccy - bal_ops, 2)
                          if balance > 0 else
                          float(daily.get("day_start") or 0.0))
        # heartbeat berkala, alert market news -- semua anti-blokir.
        scanner = []
        for want in self.wants:            # S4: pakai daftar gabungan
                                           #   (XAUUSD/XAGUSD/crypto selalu ada)

            res = self.scan.get(want)
            if not res:
                # TIDAK di-skip: pair wajib TAMPIL walau belum ada data
                scanner.append(_no_data_row(want))
                continue
            if res.get("status") == "OFF":
                # v4.35: baris OFF sudah bentuk tampilan lengkap --
                # JANGAN masuk cabang normal (akses kunci langsung -> crash)
                scanner.append(dict(res))
                continue
            info = res.get("info") or {}
            has_pos = any(p["symbol"] == self.resolved.get(want, want) for p in pos)
            if res.get("strategy") == "S2":
                # ---- tampilan STRATEGY 2 (bentuk sama, logika sinyal S2) --
                st2 = res.get("status", "WAIT")
                if has_pos:
                    status = "TRADING"
                elif st2 == "HOLD":
                    status = "HOLD"
                elif st2 in ("BLOCKED", "EXPIRED"):
                    status = "BLOCKED"
                else:
                    status = "WAIT"
                mtf_fin = float((res.get("mtf") or {}).get("final", 0.0))
                comps = {kk: round((float(res.get("components_buy", {}).get(kk, 0.0))
                                    + float(res.get("components_sell", {}).get(kk, 0.0))) / 2.0, 1)
                         for kk in ("structure", "liquidity", "trend", "momentum",
                                    "volume", "orderflow")}
                scanner.append({
                    "symbol": want, "price": res["price"],
                    "digits": info.get("digits", 2),
                    "spread": info.get("spread_points", 0),
                    "regime": "MOMENTUM",
                    "signal": res.get("side") or "-",
                    "score": mtf_fin,
                    "trend_pct": mtf_fin,
                    "status": status,
                    "sniper_why": res.get("why", ""),
                    "block_why": res.get("block_why", ""),
                    "sl": res.get("sl_price", 0.0), "tp": 0.0,
                    "sl_points": int(res.get("sl_points", 0)),
                    "components": comps,
                    "components_buy": res.get("components_buy", {}),
                    "components_sell": res.get("components_sell", {}),
                    "ohlc": res.get("ohlc", [])[-60:],
                })
                continue
            if has_pos:
                status = "TRADING"
            elif res.get("status") == "SNIPER_WAIT":
                status = "SNIPER_WAIT"
            elif res.get("status") == "BLOCKED":
                status = "BLOCKED"
            elif res["score"] >= self.cfg.get("min_score", 70):
                status = "READY"
            else:
                status = "WAIT"
            scanner.append({
                "symbol": want, "price": res["price"],
                "digits": info.get("digits", 2),
                "spread": info.get("spread_points", 0),
                "regime": str(res.get("regime", "-")) +
                          ("" if res.get("regime_dir", "-") == "-"
                           else " " + str(res.get("regime_dir", "-"))),
                "signal": res.get("side", "-")
                          if res.get("score", 0) >=
                          self.cfg.get("min_score", 70) * 0.85 else "-",
                "score": res["score"], "trend_pct": res["components"].get("trend", 50),
                "status": status,
                "sniper_why": res.get("sniper_why", ""),
                "block_why": res.get("block_why", ""),
                "sl": res.get("sl_price", 0.0),
                "tp": res.get("tp_price", 0.0),
                "sl_points": int(res.get("sl_points", 0)),
                "components": res.get("components", {}),
                "components_buy": res["components_buy"],
                "components_sell": res["components_sell"],
                "ohlc": res.get("ohlc", [])[-60:],
            })
        scanner.sort(key=lambda r: -r["score"])

        top = next((r for r in scanner
                    if r["status"] in ("READY", "TRADING",
                                       "SNIPER_WAIT", "HOLD")), None)
        # v4.41: jangan jatuh ke baris TANPA candle (OFF/NO-DATA) --
        # pilih baris ber-candle supaya panel & chart tak kosong
        if top is None:
            top = next((r for r in scanner if r.get("ohlc")), None)
        if top is None:
            top = scanner[0] if scanner else None
        confluence = None
        if top:
            comps = [{"name": n, "key": k,
                      "value": float(top.get("components_buy", {})
                                     .get(k, 0.0) or 0.0),
                      "value_sell": float(top.get("components_sell", {})
                                          .get(k, 0.0) or 0.0)}
                     for k, n in cc_scanner.COMPONENT_NAMES]
            confluence = {"symbol": top["symbol"], "side": top["signal"],
                          "score": top["score"], "components": comps,
                          "sniper_why": top.get("sniper_why", ""),
                          "status": top["status"], "ohlc": top["ohlc"],
                          "sl": top["sl"], "tp": top["tp"],
                          "digits": top["digits"], "price": top["price"]}

        trade_on = (self.cfg.get("trade_enabled", True) and not self.manual_halt
                    and not daily.get("halted", False))
        t = time.gmtime()
        sess = {"SYDNEY": (21, 6), "TOKYO": (0, 9), "LONDON": (7, 16), "NEW YORK": (12, 21)}
        sessions = {}
        for k, (a, z) in sess.items():
            op = (t.tm_hour >= a) if a <= z else (t.tm_hour >= a or t.tm_hour < z)
            sessions[k] = {"open": bool(op), "hour": "%02d:00" % t.tm_hour}
        return {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ts_epoch": time.time(),
            # v4.00: jam utk dashboard = WIB (UTC+7)
            # eksplisit -- tidak tergantung setting jam VPS.
            # PENTING: "ts" lama sengaja tidak diubah (dipakai
            # deteksi data beku, localtime mesin).
            "ts_wib": time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.gmtime(time.time() + 7 * 3600)),
            "version": CC_VERSION,
            "terminal": (getattr(b, "kind", "MT5")
                     if (b and not b.is_sim) else "SIM"),
        "mode": "SIMULASI" if (b and b.is_sim) else "LIVE",
            "connected": bool(b and b.connected),
            "ping_ms": getattr(b, "last_ping_ms", 0),
            "uptime_min": int((time.time() - self.started) / 60),
            "account": {"login": acc.get("login", ""),
                        "name": acc.get("name", ""), "currency": acc.get("currency", "USD"),
                        "leverage": acc.get("leverage", 0), "server": acc.get("server", "")},
            "metrics": {"balance": round(balance, 2),
                        "equity": round(equity, 2),
                        "floating": round(floating, 2),
                        "realized_today": realized_ccy,
                        "commission_today": commission,
                        # v3.98: model akun terdeteksi
                        "account_model": ((getattr(
                            self.broker, "account_model", dict)()
                            or {}).get("model") or "N/A"),
                        "usd_rate": round(usd_rate, 4),
                        "account_currency": ccy,
                        "wins": int(closed["wins"]), "losses": int(closed["losses"]),
                        "daily_profit": gw,
                        "floating_open": round(floating, 2),
                        "daily_loss": round(
                            gl / day_start_live * 100.0, 2)
                        if day_start_live > 0 else 0.0,
                        "daily_loss_abs": gl,
                        "gross_win": gw,
                        "gross_loss": gl,
                        "comm_mode": _cmm,
                        "rekap_deals": int(closed.get("deals", 0) or 0),
                        "rekap_since": rekap_since,
                        "drawdown_pct": daily.get(
                            "dd_bal_pct", daily.get("dd_pct", 0.0)),
                        "day_start": day_start_live,
                        "day_peak": daily.get(
                            "peak_bal", daily.get("peak", 0.0)),
                        "bal_ops": bal_ops,
                        "day_limit": daily.get("limit", 0.0),
                        "limit_used_pct": daily.get("limit_used_pct", 0.0),
                        "daily_loss_limit": 0.0},   # v4.31: dihapus
            "risk": {"halted": daily.get("halted", False),
                     "reason": daily.get("reason", ""),
                     "day_start": daily.get("day_start", 0.0),
                     "limit": daily.get("limit", 0.0),
                     "manual_halt": self.manual_halt,
                     "consec_losses": self.risk.consec_losses,
                     "pause_until": self.risk.pause_until,
                     "trade_on": trade_on},
            "scanner": [dict(r0,
                             sw=self.pair_on(r0.get("symbol")),
                             lot=float(self.pair_lot.get(
                                 str(r0.get("symbol", "")).upper(),
                                 0) or 0))
                        for r0 in scanner],
            "confluence": confluence,
            "positions": [{"ticket": p["ticket"], "symbol": p["symbol"],
                        "type": p["type"], "manual": bool(p.get("manual")),
                           "lot": p["lot"], "entry": p["entry"], "sl": p["sl"],
                           "tp": p["tp"], "price": p["price"], "pl": round(p["pl"], 2),
                           "trailing": p.get("trailing", False)} for p in pos],
            "log": log_lines,
            "sessions": sessions,
            "modules": {"scanner": True, "strategy": True, "risk": True,
                        "trade": trade_on, "trailing": self.cfg.get("trail_be_at_r", 0) > 0,
                        "news": False},
            "loop_ms": self.loop_ms,
            "hb_age": int(min(max(hb_age, 0.0), 86399)),
            "engine_stale": bool(hb_stale),
            "nscan": len(self.scan),
        }

    # ----------------------------------------------------------------- loop --
    def request_restart(self, delay=1.2):
        """v4.43 FIX FATAL: docstring lama memakai %% ver -> NameError
        SAAT DIPANGGIL, dan pemanggilnya AUTO-UPDATE -> update terunduh
        tapi engine TIDAK PERNAH restart (exception ditelan) -> VPS
        terus jalan kode lama.  Sekarang bersih: restart jalan lagi."""
        try:
            self.emit_log("UPDATE", "engine dimulai ulang dalam %.1f dtk "
                          "(jendela ini tetap jalan)..." % float(delay))
        except Exception:
            pass
        def _go():
            try:
                time.sleep(max(0.2, float(delay)))
                exe = sys.executable or "python"
                _r = os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))
                os.execv(exe, [exe, "-u",
                               os.path.join(_r, "python",
                                            "command_center.py")])
            except Exception as e:
                try:
                    self.emit_log("WARN", "restart gagal: %s "
                                  "(jalankan ulang bat utk update)" % e)
                except Exception:
                    pass
        threading.Thread(target=_go, daemon=True).start()

    def toggle_halt(self):
        self.manual_halt = not self.manual_halt
        try:
            os.makedirs("data", exist_ok=True)
            with open(os.path.join("data", "cc_state.json"), "w",
                      encoding="utf-8") as _f:
                json.dump({"manual_halt": self.manual_halt}, _f)
        except Exception:
            pass
        self.emit_log("PROTECT", "KILL SWITCH -> %s"
                      % ("HALT (tidak ada order baru)" if self.manual_halt else "LANJUT"))
        return self.manual_halt

    def run(self):
        self.connect()
        # v3.85: cek ruang disk saat mulai -- entry butuh tulis state
        free0 = _disk_free_mb(".")
        if 0 <= free0 < 500:
            self._disk_warn("sisa %d MB saat mulai" % free0, force=True)
        last_heavy = 0.0
        last_force = time.time()
        # v4.19: thread prewarm riwayat -- restore cloud & paging broker
        # kini di BELAKANG; loop scan bebas jaringan (anti-bengong)
        threading.Thread(target=self._prewarm_loop, daemon=True,
                         name="prewarm").start()
        while self.running:
            t0 = time.time()
            try:
                self.broker._tick_market() if hasattr(self.broker, "_tick_market") else None
                # S2: begitu candle M5 berganti -> scan SEGERA (eksekusi HOLD
                # di awal candle baru, bukan menunggu siklus 15 dtk)
                m5_bound = int(t0 // 300)
                if m5_bound != getattr(self, "_s2_m5_bound", m5_bound):
                    self._s2_m5_bound = m5_bound
                    if self.s2_on:
                        last_heavy = 0.0
                if t0 - last_heavy >= self.cfg.get("rates_refresh_sec", 60.0) or not self.scan:
                    self.scan_all()
                    last_heavy = t0
                    self.emit_log("SCANNER", "Scan %d pair selesai | top: %s (%s %.0f%%)"
                                  % (len(self.scan),
                                     self._top()[0] if self._top() else "-",
                                     (self._top()[1].get("side") if self._top() else ""),
                                     (self._top()[1].get("score") if self._top() else 0)))
                # harga terbaru + status per loop
                for want, sym in list(self.resolved.items()):
                    res = self.scan.get(want)
                    if not res:
                        continue
                    info = self.broker.symbol_info(sym)
                    if info:
                        res["info"] = info
                        res["price"] = info.get("bid", res["price"])

                # kandidat M15 yang masih berlaku (M1 MENAHAN, bukan blokir)
                now_c = time.time()
                ttl = self.cfg.get("setup_valid_min", 45) * 60
                for want, res in self.scan.items():
                    if res["score"] >= self.cfg.get("min_score", 70):
                        cand = self.candidates.get(want)
                        if cand and cand["side"] == res["side"]:
                            cand["t"] = now_c          # masih kuat -> perpanjang
                        else:
                            self.candidates[want] = {"t": now_c,
                                                     "born": now_c,
                                                     "side": res["side"],
                                                     "score": res["score"]}
                    else:
                        cand = self.candidates.get(want)
                        if cand and now_c - cand["t"] > ttl:
                            self.candidates.pop(want, None)

                positions = self.broker.positions()
                # deteksi posisi tertutup -> catat ke pelindung (cooldown/streak)
                try:
                    for t in self.broker.closed_trades_since(self._last_close_ts):
                        if t["time"] > self._last_close_ts:
                            self._last_close_ts = t["time"]
                            self.risk.note_closed(t["symbol"], t["pl"], now=t["time"])
                            if self.s2_on:
                                # S2: cooldown exit 10 mnt + lepas baseline
                                # trail (key = nama want, bukan symbol broker)
                                w2 = self._want_of(t["symbol"])
                                # S3 JOURNAL (blueprint s.41): close yang
                                # DILAKUKAN BROKER (SL kena) tetap dicatat
                                # dgn kode exit + R/MAE/MFE dari baseline
                                try:
                                    _tr3 = self.s2state.get_trail(w2)
                                    if _tr3 is not None:
                                        cc_strategy2.journal_exit(
                                            os.path.join(
                                                "data", "s3_journal.jsonl"),
                                            w2, _tr3,
                                            pl_money=float(t.get("pl", 0.0)
                                                           or 0.0),
                                            lot=float(t.get("lot", 0.0)
                                                      or 0.0))
                                        self.emit_log(
                                            "CLOSE", "%s %s | R %.2f "
                                            "(MAE %.2f MFE %.2f)"
                                            % (w2, _tr3.phase,
                                               _tr3.floor, _tr3.mae,
                                               _tr3.mfe))
                                except Exception:
                                    pass
                                self.s2state.set_cooldown(
                                    w2, int(self.s2k.get("cooldown_min", 10)))
                                self.s2state.del_trail(w2)
                                self.s2state.save()
                            self.emit_log("CLOSE", "%s ditutup P/L %+.2f (%s) | streak L%d"
                                          % (t["symbol"], t["pl"],
                                             "WIN" if t["pl"] > 0 else "LOSS",
                                             self.risk.consec_losses))
                except Exception:
                    pass
                # trailing BE + v3.21: MTRAIL profit-bersih (start 2 USD ->
                # kunci 1 USD, geser tiap +1 USD); kurs di-cache 60 dtk
                now_t = time.time()
                if now_t - self._rate_ts > 60:
                    self._rate_ccy, self._rate_val = self.account_usd_rate()
                    self._rate_ts = now_t
                # STRATEGY 2: SL dikelola ATR trailing (bukan trailing/money
                # trail/basket/smart exit S1 -- semua OFF via config)
                if self.s2_on:
                    try:
                        self._s2_manage_exits()
                    except Exception:
                        self.emit_log("WARN", "exits error: %s"
                                      % traceback.format_exc(limit=0)[-120:])
                else:
                    moved = self.risk.check_trailing(positions, self.broker)
                    try:
                        self.risk.money_trail(positions, self.broker,
                                              self._rate_val)
                    except Exception:
                        self.emit_log("WARN", "money_trail error (diabaikan): %s"
                                      % traceback.format_exc(limit=0)[-80:])
                    # v3.22: BASKET TP — net gabungan >= target -> tutup semua
                    # (dijalankan SETELAH trailing; posisi baru di-refresh)
                    try:
                        n_closed, basket_net = self.risk.basket_tp(
                            self.broker.positions(), self.broker, self._rate_val)
                        if n_closed:
                            positions = self.broker.positions()
                            self.emit_log("CLOSE", "BASKET TP: %d posisi ditutup, "
                                          "net +%.2f terkunci"
                                          % (n_closed, basket_net))
                    except Exception:
                        self.emit_log("WARN", "basket_tp error (diabaikan): %s"
                                      % traceback.format_exc(limit=0)[-80:])
                    # v3.25 SYSTEM PINTAR: sentuh zona SNR/HH-HL (M5->H1) sambil
                    # profit -> TP dini (anti candle rejection); re-entry nanti
                    try:
                        n_s = self.risk.smart_exit(positions, self.broker,
                                                   self._rate_val)
                        if n_s:
                            positions = self.broker.positions()
                    except Exception:
                        self.emit_log("WARN", "smart_exit error (diabaikan): %s"
                                      % traceback.format_exc(limit=0)[-80:])
                # daily guard v3.25: realized-only (floating & deposit/WD
                # tidak tercampur daily loss/profit). Realized dihitung dari
                # SEMUA posisi ditutup hari ini (bot + manual).
                acc = self.broker.account()
                try:
                    _since = self.risk.day_since()   # v3.40: tengah malam WIB
                    _cs = self.broker.closed_stats(_since)
                    _real_now = float(_cs.get("realized", 0.0))
                except Exception:
                    _real_now = 0.0
                daily = self.risk.daily_status(
                    float(acc.get("equity", 0.0)),
                    realized=_real_now,
                    balance=float(acc.get("balance", 0.0)))
                if daily.get("halted", False):
                    pass  # pesan dijalankan di bawah
                self._try_upgrade_live()
                if daily["halted"]:
                    self.emit_log("PROTECT", "DAILY LOSS LIMIT tembus -> trading berhenti hari ini")
                elif daily.get("soft_hit"):
                    self.emit_log("PROTECT", "AMBANG DAILY %.2f (95%% x batas) tembus "
                                  "-> tutup semua posisi & stop hari ini"
                                  % float(daily.get("soft_limit", 0.0)))
                if (daily["halted"] or daily.get("soft_hit")) and self.s2_on:
                        # STRATEGY 2 (EA v6.05 DailyCloseAllEA): saat lock,
                        # SEMUA posisi BOT ditutup (posisi manual tidak
                        # disentuh); engine tetap OFF sampai reset 00:00 WIB.
                        # Loop berikut otomatis retry sampai flat (spt EA).
                        try:
                            closed_n = 0
                            for p in self.broker.positions():
                                if p.get("manual"):
                                    continue
                                r = self.broker.close_position(p["ticket"])
                                if r and getattr(r, "ok", False):
                                    closed_n += 1
                            if closed_n:
                                self.emit_log("CLOSE", "DAILY LOCK: %d posisi "
                                              "bot ditutup | modal awal %.2f, "
                                              "batas %.2f (OFF s/d reset 00:00 WIB)"
                                              % (closed_n,
                                                 float(daily.get("day_start", 0.0)),
                                                 float(daily.get("limit", 0.0))))
                                self.s2state.pending.clear()
                                self.s2state.save()
                        except Exception:
                            self.emit_log("WARN", "daily closeAll error: %s"
                                          % traceback.format_exc(limit=0)[-100:])

                # eksekusi kandidat
                # v3.93 FIX 2 HARI TANPA ENTRY: weekend_ok TIDAK BOLEH di
                # level engine -- Sabtu/Minggu mematikan SEMUA pair
                # TERMASUK kripto 24/7.  Guard weekend per-pair sudah ada
                # di try_execute (market_guard: non-kripto SKIP_SESSION,
                # kripto bebas).
                trade_on = (self.cfg.get("trade_enabled", True)
                            and not self.manual_halt
                            and not (daily["halted"] or
                                     (self.s2_on and
                                      daily.get("soft_hit"))))
                if trade_on:
                    # eksekusi berbasis kandidat ber-TTL: saat pullback skor turun,
                    # kandidat TETAP hidup -> M1 tinggal menunggu momen momentum
                    for want in list(self.candidates.keys()):
                        cand = self.candidates[want]
                        # v3.33: kandidat lahir SEBELUM close terakhir simbol
                        # ini = SINYAL LAMA -> dibuang. Re-entry hanya boleh
                        # dari sinyal segar (analisa baru setelah close).
                        if not cand.get("s2_exec"):
                            # S1 gate TTL/fresh -- tidak dipakai Strategy 2
                            # (S2 punya umur sinyal sendiri: wait_bar M5).
                            fresh, fwhy = self.risk.fresh_entry_ok(
                                want, cand.get("born", cand["t"]))
                            if not fresh:
                                self.candidates.pop(want, None)
                                self.emit_log("INFO", "%s kandidat lama dibuang "
                                              "-> re-entry wajib sinyal segar (%s)"
                                              % (want, fwhy))
                                continue
                        res = self.scan.get(want)
                        if not res:
                            continue
                        if res.get("status") in ("SNIPER_WAIT", "BLOCKED", "TRADING"):
                            continue
                        # v3.65 AUDIT: sinyal EXPIRED -> kandidat hangus
                        # (anti kandidat yatim dipanggil tiap loop tanpa
                        # paket eksekusi)
                        if res.get("status") == "EXPIRED":
                            self.candidates.pop(want, None)
                            continue
                        # v3.33: arah kandidat wajib sama dgn analisa TERBARU;
                        # kalau pasar sudah berbalik -> kandidat usang, buang
                        if res.get("side") != cand["side"]:
                            self.candidates.pop(want, None)
                            continue
                        work = dict(res)
                        work["side"] = cand["side"]
                        self.try_execute(work, positions)
                # demo sugar: paksa sinyal berkala saat simulasi
                if (self.broker.is_sim and self.cfg.get("sim_force_signals", True)
                        and trade_on and time.time() - last_force > 45):
                    last_force = time.time()
                    self._sim_force_signal(positions)

                # tulis status utk dashboard (default= pengaman numpy)
                # v3.85: tulis status = try TERPISAH -- disk penuh di
                # sini BUKAN "loop error" (dulu menyesatkan: sinyal ok
                # tapi log bilang error)
                try:
                    with open("data/cc_status.json", "w",
                              encoding="utf-8") as f:
                        import json
                        from cc_dashboard import json_default
                        json.dump(self.get_status(), f, default=json_default)
                except OSError as e:
                    self._disk_warn("cc_status: %s" % e)
            except Exception as e:
                now = time.time()   # v3.85: pesan sama max 1x/60 dtk
                if now - getattr(self, "_loop_err_ts", 0.0) > 60.0:
                    self._loop_err_ts = now
                    self.emit_log("WARN", "loop error: %s"
                                  % traceback.format_exc(limit=1)[-160:])
            self.loop_ms = int((time.time() - t0) * 1000)
            try:   # v4.19 HEARTBEAT: bukti loop hidup utk watchdog
                _hb = os.path.join("data", "cc_heartbeat.json.tmp")
                with open(_hb, "w") as _f:
                    json.dump({"ts": time.time(),
                               "cycle_ms": self.loop_ms,
                               "nscan": len(self.scan)}, _f)
                os.replace(_hb, os.path.join("data",
                                             "cc_heartbeat.json"))
            except Exception:
                pass
            try:   # v4.30 (user): backup otomatis 2x/hari ke GitHub
                self._cloud_autosync_tick(time.time())
            except Exception:
                pass
            # v4.41: kick dari set_pair_switch -> scan langsung (max 1x)
            if bool(getattr(self, "_scan_kick", False)):
                self._scan_kick = False
            else:
                time.sleep(max(0.5,
                               self.cfg.get("scan_interval_sec", 5.0)))

    def _top(self):
        if not self.scan:
            return None
        s = max(self.scan.values(), key=lambda r: r["score"])
        return (s["symbol"], s)

    def _sim_force_signal(self, positions):
        if self.s2_on:
            return  # S2: sinyal demo dipaksa TIDAK dipakai (logika EA murni)
        import random
        cands = [w for w in self.resolved if w not in
                 [p["symbol"] for p in positions]]
        if not cands:
            return
        sym = random.choice(cands)
        res = self.scan.get(sym)
        if not res:
            return
        side = res["side"]
        res["score"] = round(random.uniform(74, 92), 1)
        self.emit_log("SCANNER", "%s New setup detected" % sym)
        self.emit_log("CONFLUENCE", "%s Score: %.0f%% (%s)"
                      % (sym, res["score"], side))
        m1 = self.broker.copy_rates(self.resolved[sym], "M1", self.cfg.get("bars_m1", 120))
        delta = self.broker.tick_delta(self.resolved[sym], 120)
        ok, why = cc_scanner.sniper_m1(res, m1, self.cfg, delta)
        if not ok:
            res["status"] = "SNIPER_WAIT"
            res["sniper_why"] = why
            return
        positions = self.broker.positions()
        self.try_execute(res, positions)

    def stop(self, *a):
        self.running = False


def main():
    cfg = CCConfig()
    cc = CommandCenter(cfg)
    signal.signal(signal.SIGINT, cc.stop)
    signal.signal(signal.SIGTERM, cc.stop)

    # dashboard web di thread terpisah
    from cc_dashboard import make_server
    port = int(cfg.get("dashboard_port", 8081))  # S2: port terpisah
    pw = str(cfg.get("dashboard_password", "") or "")
    srv = make_server(cc, port, pw)
    try:
        import socket as _sk
        _t = _sk.socket(_sk.AF_INET, _sk.SOCK_DGRAM)
        _t.connect(("8.8.8.8", 80))
        _ip = _t.getsockname()[0]
        _t.close()
    except Exception:
        _ip = "127.0.0.1"
    cc.log("[WEB] Dashboard: http://%s:%d  | Password: %s"
           % (_ip, port, ("AKTIF" if pw else "KOSONG (isi dashboard_password "
                                          "di cc_config.json supaya aman online)")))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    print("Dashboard: http://localhost:%d  (biarkan jendela ini terbuka)" % port)
    # ---- AUTO-UPDATE OTOMATIS (tanpa klik apa pun): engine cek
    # GitHub berkala (cc_selfupdate: hanya file python/, state/data/
    # bat TIDAK pernah disentuh) dan restart sendiri bila ada versi baru.
    def _auto_update_loop():
        try:
            import cc_selfupdate as _su
        except Exception:
            return
        mins = float(cfg.get("auto_update_min", 120.0) or 0.0)
        if mins <= 0:
            return
        time.sleep(90)                 # biarkan engine stabil dulu
        while cc.running:
            try:
                files, err = _su.run()
                if files:
                    cc.log("UPDATE", "AUTO-UPDATE: %d file baru dari "
                           "GitHub -- engine di-restart otomatis"
                           % len(files))
                    time.sleep(2.0)
                    cc.request_restart(delay=1.0)
                    return
                # err (tanpa token/offline) -> diam, coba lagi nanti
            except Exception:
                pass
            for _ in range(int(mins * 12)):
                if not cc.running:
                    return
                time.sleep(5.0)
    threading.Thread(target=_auto_update_loop, daemon=True).start()

    try:
        cc.run()
    finally:
        srv.shutdown()
        if cc.broker:
            cc.broker.shutdown()


if __name__ == "__main__":
    main()
