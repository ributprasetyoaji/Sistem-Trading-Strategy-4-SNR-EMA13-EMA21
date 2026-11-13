#!/usr/bin/env python3
"""Health check laptop - jalankan sebelum deploy ke VPS.

Menguji 6 hal secara berurutan:
 1. Versi Python
 2. Paket websockets
 3. Koneksi REST ke Binance (semua host fallback)
 4. WebSocket live Binance (aggTrade + depth + kline M5) selama 15 detik
 5. Pipeline penuh via replay data (HVN -> absorption -> delta -> sinyal)
 6. Penulisan file IPC (signal/status) yang akan dibaca MT5

Jalankan dari folder root project:
    python python/doctor.py
atau klik dua kali CEK_LAPTOP.bat (Windows).
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESULTS: list[tuple[str, bool, str]] = []
HINTS: list[str] = []


def mark(name: str, ok: bool, detail: str = "", count: bool = True) -> None:
    tag = "[ OK  ]" if ok else ("[INFO]" if not count else "[GAGAL]")
    line = f"{tag} {name}"
    if detail:
        line += f" - {detail}"
    print(line, flush=True)
    if count:
        RESULTS.append((name, ok, detail))


def header(text: str) -> None:
    print("", flush=True)
    print(f"--- {text} ---", flush=True)


def step1_python() -> None:
    header("1/6 Versi Python")
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    ok = v >= (3, 9)
    mark(f"Versi Python {ver}", ok,
         "butuh 3.9+" if ok else "terlalu lama, install Python 3.10+ dari python.org")
    if not ok:
        HINTS.append("Install Python 3.10+ dari https://python.org (centang 'Add to PATH')")


def step2_websockets() -> bool:
    header("2/6 Paket websockets")
    try:
        import websockets  # noqa: F401
        mark("Paket websockets terpasang", True, websockets.__version__)
        return True
    except ImportError:
        mark("Paket websockets terpasang", False,
             "jalankan: pip install -r requirements.txt")
        HINTS.append("Buka CMD di folder project, jalankan: pip install -r requirements.txt")
        return False


def step3_rest(cfg: Config) -> list[str]:
    header("3/6 Koneksi REST ke Binance (uji semua host fallback)")
    working: list[str] = []
    for host in cfg.binance_rest_hosts:
        url = (f"{host}/api/v3/depth?symbol={cfg.binance_symbol.upper()}&limit=5")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "btc-hvn-ea/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            bids = data.get("bids") or []
            top = float(bids[0][0]) if bids else 0.0
            mark(f"REST {host}", True, f"top bid BTCUSDT = {top:,.2f}", count=False)
            working.append(host)
        except Exception as exc:  # noqa: BLE001
            reason = str(exc)[:90]
            if "451" in reason:
                reason += " (diblokir dari lokasi/IP ini)"
            mark(f"REST {host}", False, reason, count=False)
    if working:
        mark("Koneksi REST Binance (host fallback)", True,
             f"{len(working)}/{len(cfg.binance_rest_hosts)} host bisa dipakai: "
             + ", ".join(working))
    else:
        mark("Koneksi REST Binance (host fallback)", False,
             "tidak ada host yang bisa dijangkau dari jaringan ini")
        HINTS.append("Semua host Binance diblokir dari jaringan ini - gunakan VPS di "
                     "lokasi yang menjangkau Binance (mis. Jepang/UE/Dubai) atau "
                     "jaringan/VPN lain")
    return working


async def _run_ws(cfg: Config, seconds: int) -> dict:
    """Run the engine against cfg.binance_ws_hosts (already pinned by caller)
    for N seconds and gather stream statistics."""
    from binance_ws import BinanceWS
    from data_health import DataHealth
    health = DataHealth(cfg.max_data_age_ms)
    counts = {"trades": 0, "depth": 0, "kline": 0, "price": 0.0}

    def on_trade(ts, price, qty, is_sell):
        counts["trades"] += 1
        counts["price"] = price

    def on_kline(_k):
        counts["kline"] += 1

    ws = BinanceWS(cfg, health, on_trade=on_trade, on_kline=on_kline)
    orig_apply = ws.book.apply_diff

    def counting_apply(*a, **kw):
        counts["depth"] += 1
        return orig_apply(*a, **kw)

    ws.book.apply_diff = counting_apply  # type: ignore[method-assign]
    stop = asyncio.Event()
    task = asyncio.create_task(ws.run(stop))
    await asyncio.sleep(seconds)
    out = {"connected": health.connected, "trades": counts["trades"],
           "depth": counts["depth"], "kline": counts["kline"],
           "synced": ws.book.synced, "price": counts["price"] or ws.book.best_bid(),
           "host": ws.ws_host, "err": health.last_error}
    stop.set()
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=20)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()
    return out


def step4_websocket(cfg: Config, rest_working: list[str]) -> float:
    header("4/6 WebSocket live Binance (uji tiap host satu per satu)")
    original_hosts = tuple(cfg.binance_ws_hosts)
    original_rest = tuple(cfg.binance_rest_hosts)
    working: list[str] = []
    for host in original_hosts:
        cfg.binance_ws_hosts = (host,)
        try:
            r = asyncio.run(_run_ws(cfg, seconds=10))
        except Exception as exc:  # noqa: BLE001
            r = {"connected": False, "trades": 0, "depth": 0, "kline": 0,
                 "synced": False, "price": 0.0, "host": host,
                 "err": str(exc)[:90]}
        if r["connected"] and r["trades"] > 5:
            mark(f"WS {host}", True, f"{r['trades']} trades/10 detik", count=False)
            working.append(host)
        else:
            reason = r.get("err") or f"trades={r.get('trades', 0)}"
            mark(f"WS {host}", False, reason[:90], count=False)
    cfg.binance_ws_hosts = original_hosts

    if not working:
        mark("Koneksi WebSocket Binance", False,
             "semua host WS gagal dari jaringan ini (REST normal)")
        HINTS.append("Semua host WebSocket Binance diblokir jaringan ini. Coba "
                     "hotspot HP: kalau hotspot jalan, berarti ISP/router memblokir. "
                     "Di VPS dengan lokasi tepat jalur ini biasanya normal - "
                     "keputusan VPS tetap berdasarkan doctor yang dijalankan DI VPS.")
        return 0.0

    mark("Koneksi WebSocket Binance (host fallback)", True,
         f"{len(working)}/{len(original_hosts)} host bisa dipakai: " + ", ".join(working))

    # full check (order book depth sync + kline) on the first working host,
    # with REST hosts reordered so the hosts that measured FAST are tried first
    cfg.binance_ws_hosts = (working[0],)
    cfg.binance_rest_hosts = (tuple(rest_working)
                              + tuple(h for h in original_rest
                                      if h not in rest_working))
    try:
        r = asyncio.run(_run_ws(cfg, seconds=16))
    except Exception as exc:  # noqa: BLE001
        r = {"synced": False, "depth": 0, "kline": 0, "price": 0.0}
    finally:
        cfg.binance_ws_hosts = original_hosts
        cfg.binance_rest_hosts = original_rest
    if r.get("synced"):
        mark("Order book tersinkron (depth stream)", True,
             f"{r.get('depth', 0)} update depth diterima")
    else:
        mark("Order book tersinkron (depth stream)", False,
             f"{r.get('depth', 0)} update diterima tapi snapshot REST belum "
             f"lengkap (auto-retry tiap 2 dtk; di VPS cek lagi - kalau tetap "
             f"gagal laporkan ke agent)")
        HINTS.append("Order book belum sinkron meski WS jalan - engine sudah "
                     "punya auto-retry snapshot; jalankan ulang doctor sekali "
                     "lagi sebelum menyimpulkan ada masalah")
    mark("Stream kline M5 aktif", True,
         f"{r.get('kline', 0)} update (0 normal jika belum ada bar M5 baru)")
    return float(r.get("price") or 0.0)


def step5_replay() -> dict:
    header("5/6 Pipeline penuh (replay data contoh)")
    replay_path = os.path.join(PROJECT_ROOT, "data", "replay", "smoke.jsonl")
    if not os.path.exists(replay_path):
        mark("File replay ditemukan", False, replay_path)
        HINTS.append("File data/replay/smoke.jsonl hilang - extract ulang ZIP project")
        return {}
    cfg = Config()
    cfg.ipc_mode = "file"
    cfg.mt5_common_dir = ""                 # tulis ke out/mt5_ipc lokal
    cfg.log_console = False
    cfg.log_dir = tempfile.mkdtemp(prefix="bhvn_doctor_")
    cfg.hvn_refresh_sec = 0.0
    cfg.status_interval_ms = 0

    from logger import Logger
    from main import Pipeline
    log = Logger(cfg.log_dir, console=False)
    app = Pipeline(cfg, log)
    app.replay_mode = True

    rows = []
    with open(replay_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: int(r["T"]))
    if rows:
        app.health.mark_connected(int(rows[0]["T"]))
    for r in rows:
        if "K" in r:
            app.on_kline(r["K"])
        else:
            app.on_trade(int(r["T"]), float(r["p"]), float(r["q"]),
                         bool(int(r.get("m", 0))))
        app.evaluate()

    sig_path = cfg.signal_path()
    out = {}
    if os.path.exists(sig_path):
        with open(sig_path, "r", encoding="utf-8") as f:
            sig = json.load(f)
        out = {"direction": sig.get("direction"), "score": sig.get("score"),
               "invalidation": sig.get("invalidation_price")}
        mark("Sinyal dihasilkan dari pipeline", True,
             f"{out['direction']} score={out['score']} invalidation={out['invalidation']}")
    else:
        mark("Sinyal dihasilkan dari pipeline", False,
             "tidak ada file sinyal - laporkan output ini ke agent")
        HINTS.append("Pipeline tidak menghasilkan sinyal dari data contoh")
    shutil.rmtree(cfg.log_dir, ignore_errors=True)
    return out


def step6_ipc() -> str:
    header("6/6 File IPC untuk MT5 (mode laptop)")
    local_dir = os.path.join(PROJECT_ROOT, "out", "mt5_ipc")
    status_path = os.path.join(local_dir, "BTC_HVN_STATUS.json")
    ok = os.path.exists(status_path)
    if ok:
        with open(status_path, "r", encoding="utf-8") as f:
            st = json.load(f)
        mark("Status engine tertulis", True,
             f"state={st.get('engine_state')} harga={st.get('binance_price')}")
        mark("Folder output lokal", True, local_dir)
    else:
        mark("Status engine tertulis", False, status_path)
        HINTS.append("File status tidak tertulis - jalankan ulang dari folder root project")
    return local_dir


def main() -> None:
    print("=" * 62)
    print("  CEK KESIAPAN LAPTOP - BTC HVN + ABSORPTION EA")
    print("=" * 62)
    step1_python()
    have_ws = step2_websockets()
    cfg = Config()
    cfg.ipc_mode = "file"
    cfg.mt5_common_dir = ""
    rest_ok: list[str] = []
    price = 0.0
    if have_ws:
        rest_ok = step3_rest(cfg)
        if rest_ok:
            price = step4_websocket(cfg, rest_ok)
    step5_replay()
    step6_ipc()

    header("RINGKASAN")
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, _detail in RESULTS:
        print(f"  {'[OK]' if ok else '[XX]'} {name}")
    print("-" * 62)
    if not failed:
        print("  HASIL: SEMUA LOLOS - laptop SIAP.")
        print("  Langkah berikutnya:")
        print("   1. Jalankan engine live : python python/main.py")
        print("   2. out/mt5_ipc/BTC_HVN_STATUS.json akan terupdate tiap detik")
        print("   3. Kalau laptop juga ada MT5 demo: ikuti README tahap C")
        print("   4. Setelah yakin, ulangi langkah yang sama di VPS")
        if price > 0:
            print(f"   (Harga BTC terakhir terlihat: {price:,.2f} USD)")
    else:
        print(f"  HASIL: {len(failed)} item GAGAL. Perbaiki dulu:")
        for h in HINTS:
            print(f"   -> {h}")
    print("=" * 62)


if __name__ == "__main__":
    main()
