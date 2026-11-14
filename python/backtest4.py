# -*- coding: utf-8 -*-
"""Backtest S4 (v4.45) -- BUKTI BISA ENTRY pada data riil.

Replay bar-per-bar memakai FUNGSI ASLI cc_strategy3 (s4_bias, adx_wilder,
s4_m5_ok, s4_structure, s4_reversal) -- bukan tiruan -- supaya hasil
backtest = perilaku live engine.

Model replay (setara live):
- tiap bar j: window = bars[:j+1] (bar j = "bar berjalan"), live=h[j].
  Entry saat TOUCH zona -> harga entry = zona (HH utk BUY / LL utk SELL),
  SL = zona lawan (HL/LH).  Persis aturan touch user v4.44.
- filter sama urutan evaluate(): bias M15 stack -> ADX>adx_min -> M5
  kontra (slice M5 s/d close time bar) -> struktur touch.
- exit: TP hard 1R, SL zona, trailing 0.6R -> SL geser +0.2R (ratchet),
  close REVERSAL (EMA flip) dgn profit -> cooldown 10 menit.
- 1 tiket/symbol (persis engine).

Catatan jujur (batasan bar-based):
- tanpa spread, tanpa daily-loss-cap (keduanya diuji unit test terpisah),
- EMA/ADX dihitung dgn close final bar "berjalan" (aproksimasi +/- 1 bar
  vs tick-live),
- bila SL & TP kena di bar yang sama, SL dihitung duluan (konservatif).

Data: Yahoo chart API (User-Agent wajib), interval 15m + 5m, max 60 hari.
Cache JSON di data/backtest4/cache/ agar re-run cepat & konsisten.

Pakai:
  python3 python/backtest4.py                     # semua pair, 60 hari
  python3 python/backtest4.py --symbols BTCUSD,XAUUSD
"""
import argparse
import bisect
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cc_strategy3 as cs3                              # noqa: E402

WARMUP = 120                      # bar M15 sebelum sinyal dievaluasi

# ---- mapping pair (nama engine) -> ticker Yahoo (alt = fallback) ----
YAHOO_MAP = {
    "XAUUSD": ["GC=F", "XAUUSD=X"],
    "XAGUSD": ["SI=F", "XAGUSD=X"],
    "EURUSD": ["EURUSD=X"], "GBPUSD": ["GBPUSD=X"], "USDJPY": ["USDJPY=X"],
    "AUDUSD": ["AUDUSD=X"], "NZDUSD": ["NZDUSD=X"], "USDCAD": ["USDCAD=X"],
    "USDCHF": ["USDCHF=X"], "EURJPY": ["EURJPY=X"], "GBPJPY": ["GBPJPY=X"],
    "BTCUSD": ["BTC-USD"], "ETHUSD": ["ETH-USD"], "SOLUSD": ["SOL-USD"],
    "XRPUSD": ["XRP-USD"], "LTCUSD": ["LTC-USD"],
    "NAS100": ["^NDX", "NQ=F"], "US30": ["^DJI", "YM=F"],
    "GER40": ["^GDAXI"], "US500": ["^GSPC", "ES=F"],
    "XPTUSD": ["PL=F", "XPTUSD=X"], "USOIL": ["CL=F", "USOIL=F"],
}

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def yahoo_fetch(ticker, interval, rng, cache_dir=None):
    """Unduh candle Yahoo -> dict {time,open,high,low,close} (time=open)."""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cpath = os.path.join(cache_dir, "%s_%s.json" % (ticker, interval))
        if os.path.exists(cpath):
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
           "?interval=%s&range=%s&includePrePost=false" %
           (ticker, interval, rng))
    import urllib.request
    last_err = None
    for _try in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            res = (data.get("chart") or {}).get("result") or []
            if not res:
                raise ValueError("chart kosong")
            q = res[0]
            ts = q.get("timestamp") or []
            qd = (q.get("indicators") or {}).get("quote") or [{}]
            qd = qd[0]
            o, h, l, c = (qd.get("open") or [], qd.get("high") or [],
                          qd.get("low") or [], qd.get("close") or [])
            out = {"time": [], "open": [], "high": [], "low": [], "close": []}
            for i in range(len(ts)):
                # buang bar dengan data tidak lengkap (null)
                if (o[i] is None or h[i] is None or l[i] is None
                        or c[i] is None):
                    continue
                out["time"].append(int(ts[i]))
                out["open"].append(float(o[i]))
                out["high"].append(float(h[i]))
                out["low"].append(float(l[i]))
                out["close"].append(float(c[i]))
            if len(out["close"]) < 50:
                raise ValueError("bar terlalu sedikit: %d" % len(out["close"]))
            if cache_dir:
                try:
                    with open(cpath, "w", encoding="utf-8") as f:
                        json.dump(out, f)
                except Exception:
                    pass
            return out
        except Exception as e:                      # noqa: BLE001
            last_err = e
            time.sleep(2.0)
    raise RuntimeError("Yahoo %s gagal: %s" % (ticker, last_err))


def yahoo_pair(pair, cache_dir):
    """Ambil M15 + M5 utk pair engine (coba tiap ticker alt)."""
    last_err = None
    for tk in YAHOO_MAP.get(pair, [pair]):
        try:
            m15 = yahoo_fetch(tk, "15m", "60d", cache_dir)
            time.sleep(0.35)
            m5 = yahoo_fetch(tk, "5m", "60d", cache_dir)
            return m15, m5
        except Exception as e:                      # noqa: BLE001
            last_err = e
    raise RuntimeError("pair %s tak ada data Yahoo: %s" % (pair, last_err))


def _slice(win, upto):
    return dict((kk, list(win.get(kk) or [])[:upto])
                for kk in ("open", "high", "low", "close"))


def replay_pair(m15, m5, k, warmup=WARMUP):
    """Replay 1 pair -> hasil funnel + daftar trade (dalam satuan R)."""
    ts = [int(v) for v in (m15.get("time") or [])]
    h = [float(v) for v in (m15.get("high") or [])]
    l = [float(v) for v in (m15.get("low") or [])]
    c = [float(v) for v in (m15.get("close") or [])]
    m5t = [int(v) for v in ((m5 or {}).get("time") or [])]
    m5c = [float(v) for v in ((m5 or {}).get("close") or [])]
    n = len(c)
    out = {"bars": max(0, n - warmup), "bias_ok": 0, "adx_ok": 0,
           "m5_ok": 0, "touch": 0, "entries": 0, "wins": 0, "losses": 0,
           "rev_close": 0, "r_tot": 0.0, "gross_win": 0.0,
           "gross_loss": 0.0, "trades": []}
    pos = None
    cooldown_until = 0
    be_r = float(k.get("be_r", 0.6) or 0.6)
    lk_r = float(k.get("be_lock_r", 0.2) or 0.2)

    for j in range(warmup, n):
        t_close = ts[j] + 900
        # ---------------- kelola posisi terbuka (bar j penuh) ----------
        if pos:
            side, entry, dist = pos["side"], pos["entry"], pos["dist"]
            sl_cur = float(pos["sl"])
            hit_sl = (l[j] <= sl_cur) if side > 0 else (l[j] >= 0 and
                                                        h[j] >= sl_cur)
            # (BUY: low <= SL; SELL: high >= SL)
            if side > 0:
                hit_sl = l[j] <= sl_cur
            else:
                hit_sl = h[j] >= sl_cur
            exit_r = None
            why = ""
            if hit_sl:
                exit_r = (sl_cur - entry) * side / dist
                why = "SL"
            else:
                # trailing pakai ekstrem bar ini (ratchet, persis engine)
                peak = ((h[j] - entry) / dist) if side > 0 else \
                    ((entry - l[j]) / dist)
                if peak > pos["peak"]:
                    pos["peak"] = peak
                if pos["peak"] >= be_r:
                    new_sl = entry + lk_r * dist * side
                    if (side > 0 and new_sl > sl_cur) or \
                            (side < 0 and new_sl < sl_cur):
                        pos["sl"] = new_sl
                        sl_cur = new_sl
                tp = pos["tp"]
                if (side > 0 and h[j] >= tp) or (side < 0 and l[j] <= tp):
                    exit_r = 1.0
                    why = "TP"
                else:
                    win = _slice(m15, j + 1)
                    sig = "BUY" if side > 0 else "SELL"
                    if (c[j] - entry) * side > 0 and cs3.s4_reversal(
                            win, sig, k):
                        exit_r = (c[j] - entry) * side / dist
                        why = "REVERSAL"
            if exit_r is not None:
                out["entries"] += 1
                out["r_tot"] += exit_r
                if exit_r > 0:
                    out["wins"] += 1
                    out["gross_win"] += exit_r
                else:
                    out["losses"] += 1
                    out["gross_loss"] += -exit_r
                if why == "REVERSAL":
                    out["rev_close"] += 1
                    cooldown_until = t_close + 600      # 10 menit (user)
                out["trades"].append({
                    "in": ts[pos["j_in"]], "out": ts[j],
                    "side": "BUY" if side > 0 else "SELL",
                    "entry": round(entry, 6), "r": round(exit_r, 3),
                    "why": why, "peak_r": round(pos["peak"], 2)})
                pos = None
            continue

        # ---------------- cari sinyal baru (urutan = evaluate) ---------
        if t_close < cooldown_until:
            continue
        win = _slice(m15, j + 1)
        bias = cs3.s4_bias(win, k)
        if not bias:
            continue
        out["bias_ok"] += 1
        adx = cs3.adx_wilder(win, int(k.get("adx_period", 14)))
        if adx <= float(k.get("adx_min", 20.0)):
            continue
        out["adx_ok"] += 1
        sig_req = "BUY" if bias == "buy" else "SELL"
        idx = bisect.bisect_right(m5t, t_close)
        m5ok = cs3.s4_m5_ok(sig_req, {"close": m5c[:idx]}, k) if idx else True
        if not m5ok:
            continue
        out["m5_ok"] += 1
        st4 = cs3.s4_structure(win, k, live=h[j])    # touch di dalam bar j
        if not st4:
            continue
        out["touch"] += 1
        sig, zone, sl_px, _why = st4
        if (sig == "BUY" and bias != "buy") or \
                (sig == "SELL" and bias != "sell"):
            continue
        entry = zone                                  # harga saat touch
        dist = abs(entry - sl_px)
        if dist <= 0:
            continue
        tp = entry + dist * (1 if sig == "BUY" else -1)   # RR 1:1
        pos = {"side": 1 if sig == "BUY" else -1, "entry": entry,
               "dist": dist, "sl": sl_px, "tp": tp, "peak": 0.0,
               "j_in": j}
        out["trades"].append({"in": ts[j],
                              "side": sig, "entry": round(entry, 6),
                              "r": None, "why": "OPEN", "peak_r": 0.0})
    return out


def run(symbols=None, cache_dir="data/backtest4/cache"):
    import cc_config
    cfg = json.loads(json.dumps(cc_config.DEFAULTS))
    k = cs3.s2_cfg(cfg)
    pairs = symbols or cfg.get("symbols") or []
    rows = []
    for p in pairs:
        try:
            m15, m5 = yahoo_pair(p, cache_dir)
        except Exception as e:                      # noqa: BLE001
            rows.append({"pair": p, "error": str(e)})
            continue
        r = replay_pair(m15, m5, k)
        r["pair"] = p
        r["pf"] = (round(r["gross_win"] / r["gross_loss"], 2)
                   if r["gross_loss"] > 0 else
                   (float("inf") if r["gross_win"] > 0 else 0.0))
        rows.append(r)
        time.sleep(0.35)
    tot_e = sum(x.get("entries", 0) for x in rows)
    tot_r = sum(x.get("r_tot", 0.0) for x in rows)
    print("")
    print("%-8s %6s %7s %7s %7s %7s %5s %5s %7s %8s" %
          ("PAIR", "BARS", "BIAS", "ADX", "M5OK", "TOUCH", "ENTRY",
           "W/L", "PF", "R TOT"))
    for x in rows:
        if "error" in x:
            print("%-8s  ERROR: %s" % (x["pair"], x["error"][:60]))
            continue
        print("%-8s %6d %7d %7d %7d %7d %5d %3d/%d %7s %8.1f" %
              (x["pair"], x["bars"], x["bias_ok"], x["adx_ok"],
               x["m5_ok"], x["touch"], x["entries"], x["wins"],
               x["losses"],
               ("inf" if x["pf"] == float("inf") else str(x["pf"])),
               x["r_tot"]))
    print("-" * 78)
    print("TOTAL ENTRY: %d  |  TOTAL R: %+.1f  |  pair: %d" %
          (tot_e, tot_r, len(rows)))
    try:
        os.makedirs(os.path.dirname(cache_dir) or ".", exist_ok=True)
        ser = []
        for x in rows:
            if "error" not in x:
                x2 = dict(x)
                x2.pop("pf", None)
                ser.append(x2)
        with open(os.path.join(os.path.dirname(cache_dir),
                               "hasil.json"), "w", encoding="utf-8") as f:
            json.dump({"rows": ser, "total_entries": tot_e,
                       "total_r": round(tot_r, 2)}, f, indent=1)
    except Exception:
        pass
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    run(syms or None)
