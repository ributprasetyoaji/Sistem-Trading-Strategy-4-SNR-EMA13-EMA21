#!/usr/bin/env python3
"""Panel pantau engine: membaca out/mt5_ipc/BTC_HVN_STATUS.json dan
menampilkannya sebagai dashboard teks yang mudah dibaca.
Dipanggil berulang oleh PANTAU_STATUS.bat."""
from __future__ import annotations

import json
import os
import sys

W = 64


def line(ch="-"):
    print(ch * W)


def row(label, value):
    print(f" {label:<22}: {value}")


def main() -> None:
    path = os.path.join("out", "mt5_ipc", "BTC_HVN_STATUS.json")
    print("=" * W)
    print("  PANTAUAN BTC HVN ENGINE  (refresh tiap 3 detik)")
    print("=" * W)
    if not os.path.exists(path):
        print("  [!] File status belum ada.")
        print("      Pastikan JALANKAN_ENGINE.bat sedang berjalan")
        print("      di jendela lain (tunggu ~10 detik).")
        line()
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("  [!] File status sedang ditulis, coba lagi...")
        line()
        return

    conn = "UP" if d.get("binance_connected") else "DOWN"
    stale = "YA (jangan entry)" if d.get("stale") else "tidak"
    book = "SINKRON" if d.get("book_synced") else "belum sinkron"
    age = d.get("data_age_ms", -1)
    age_s = f"{age/1000:.1f} dtk" if age >= 0 else "-"

    line("=")
    print("  SISTEM")
    line("-")
    row("Koneksi Binance", conn)
    row("Umur data terakhir", age_s)
    row("Data stale", stale)
    row("Order book", book)
    row("State engine", d.get("engine_state", "-"))
    row("Setup skor terbaik", d.get("setup_score", 0))

    line("=")
    print("  HARGA")
    line("-")
    row("Binance BTCUSDT", f"{d.get('binance_price', 0):,.2f}")
    row("Book bid / ask", f"{d.get('ob_bid', 0):,.2f} / {d.get('ob_ask', 0):,.2f}")
    row("Imbalance buku", f"{d.get('ob_imbalance', 0):+.2f}")

    line("=")
    print("  ORDER FLOW")
    line("-")
    row("Delta 30 dtk", f"{d.get('delta_win', 0):+.1f}")
    row("Delta 10 dtk", f"{d.get('delta_short', 0):+.1f}")
    row("Delta M5", f"{d.get('delta_m5', 0):+.1f}")
    row("CVD", f"{d.get('cvd', 0):+.1f}")
    row("Volume x baseline", f"{d.get('vol_mult', 0):.2f}")
    atr_ctx = d.get("atr_ctx") or d.get("atr_m5", 0)
    row("ATR M15 (konteks)", atr_ctx)
    if not atr_ctx:
        w = int(d.get("atr_wait_bars", 14) or 14)
        print(f"        (ATR aktif dalam {w} bar M15 lagi, ~{w * 15} menit)")
    if d.get("entry_mode") == "m15_sniper":
        print(f"  Sniper M5/M1 : {d.get('sniper_why', '-')}")
    fill = d.get("hvn_fill_pct")
    if fill is not None:
        print(f"  Profil HVN terisi: {fill}%  (100% = data penuh, awal mulai ~2 jam)")

    line("=")
    print("  HVN (zona volume tinggi)")
    line("-")
    n = int(d.get("hvn_count", 0) or 0)
    if n == 0:
        print("  Belum ada zona - profil penuh butuh ~2 jam data")
    for i in range(min(n, 5)):
        lo = d.get(f"hvn{i}_low", 0)
        hi = d.get(f"hvn{i}_high", 0)
        rel = d.get(f"hvn{i}_rel", 0)
        print(f"   Zona {i+1}: {lo:,.0f} - {hi:,.0f}  (rel vol {rel:.1f}x)")
    if d.get("nearest_low"):
        row("Zona terdekat", (f"{d.get('nearest_low'):,.0f} - "
                              f"{d.get('nearest_high'):,.0f}"))
        dist = d.get("nearest_dist_atr", -1)
        row("Jarak (ATR)", "di dalam zona" if dist == 0 else f"{dist:.2f}")

    line("=")
    print("  SINYAL / ABSORPSI")
    line("-")
    ad = d.get("absorption_direction", "")
    row("Absorpsi", (f"{ad} kekuatan {d.get('absorption_strength', 0):.0f}"
                     if ad else "tidak terdeteksi"))
    row("Exit hint", f"{d.get('exit_hint','NONE')} ({d.get('exit_score',0):.0f})")
    sid = d.get("signal_id", "")
    row("Sinyal terakhir", (f"{sid} {d.get('signal_direction','')} "
                            f"skor {d.get('signal_score',0):.0f}" if sid else "-"))

    line("=")
    if d.get("stale"):
        print("  STATUS: DATA STALE - engine menahan sinyal (by design)")
    elif d.get("engine_state") == "IDLE":
        print("  STATUS: sehat, menunggu harga mendekati HVN + absorpsi")
    else:
        print(f"  STATUS: aktif - {d.get('engine_state')}")
    line("=")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
