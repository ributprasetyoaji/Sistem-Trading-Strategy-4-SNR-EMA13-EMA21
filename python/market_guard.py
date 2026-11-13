"""MARKET GUARD -- RBT FX (permintaan user utk KETIGA strategy):

1. AKHIR PEKAN: pair yang libur Sabtu/Minggu -> SKIP entry mulai 1 jam
   sebelum PENUTUPAN market mingguan, dan AKTIF LAGI otomatis saat
   PEMBUKAAN market (jendela waktu murni -- tanpa state, auto resume).
   Pair 24/7 (kripto: BTC/ETH/SOL/dll) dikecualikan via kata kunci.
2. ROLLOVER HARIAN: 30 menit sebelum daily rollover/market break ->
   SKIP SEMUA entry (mencegah entry nyangkut saat spread melebar),
   aktif lagi beberapa menit sesudahnya (configurable).

Semua waktu dihitung UTC (epoch broker aman dipetakan).  Modul MURNI
(testable, tanpa broker/import engine).  Reason codes blueprint s.42:
SKIP_SESSION + tambahan SKIP_ROLLOVER (dok kepatuhan).
"""
import time
from datetime import datetime, timedelta, timezone

DEFAULTS = {
    "enabled": True,
    "weekend_skip_before_min": 60,      # user: SKIP 1 jam sebelum tutup
    "weekend_close_dow": 4,             # 4 = Jumat (weekday() Python)
    "weekend_close_utc": "21:00",       # tipikal NY-close broker;
                                        #   sesuaikan jam broker Anda
    "weekend_open_dow": 6,              # 6 = Minggu
    "weekend_open_utc": "22:00",        # buka ulang Minggu malam UTC
    "rollover_skip_before_min": 30,     # user: SKIP 30 menit sebelum
    "rollover_after_min": 5,            #   +5 mnt sesudah (spread normal)
    "rollover_utc": "21:00",            # tipikal midnight server GMT+2/3
    "always_open_keywords": ["BTC", "ETH", "SOL", "XRP", "LTC", "DOGE",
                             "ADA", "XLM", "BCH", "DOT", "LINK"],
}

_DOW = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat",
        5: "Sabtu", 6: "Minggu"}


def parse_hhmm(s, dflt=(0, 0)):
    """"21:00" -> (21, 0).  Salah format -> default (tidak pernah raise)."""
    try:
        hh, mm = str(s).strip().split(":")
        return (max(0, min(23, int(hh))), max(0, min(59, int(mm))))
    except Exception:
        return dflt


def sym_always_open(symbol, k=None):
    """Pair 24/7 (kripto) -> bebas guard akhir pekan."""
    kws = ((k or {}).get("always_open_keywords") or DEFAULTS[
        "always_open_keywords"])
    up = str(symbol or "").upper()
    return any(str(x).upper() in up for x in kws)


def weekend_block(now, k=None):
    """(blocked, why): jendela [tutup - N mnt, buka) tiap minggu."""
    k = k or {}
    if k.get("enabled", True) is False:
        return (False, "")
    b = int(k.get("weekend_skip_before_min", 60) or 0)
    cd = int(k.get("weekend_close_dow", 4) or 0)
    ch, cm = parse_hhmm(k.get("weekend_close_utc", "21:00"), (21, 0))
    od = int(k.get("weekend_open_dow", 6) or 0)
    oh, om = parse_hhmm(k.get("weekend_open_utc", "22:00"), (22, 0))
    now_dt = datetime.fromtimestamp(int(now), tz=timezone.utc)
    mid = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    # Jumat terdekat MUNDUR (siklus yg sedang berjalan), pembukaan
    # Minggu = Jumat tsb + delta hari -- jendela [Jumat tutup, Minggu buka)
    base = mid - timedelta(days=(now_dt.weekday() - cd) % 7)
    close_dt = base.replace(hour=ch, minute=cm)
    open_dt = (close_dt + timedelta(days=(od - cd) % 7)).replace(
        hour=oh, minute=om)
    if open_dt <= close_dt:              # konfig tak logis -> fail-safe
        return (False, "")
    if close_dt - timedelta(minutes=b) <= now_dt < open_dt:
        return (True, "SKIP_SESSION: market menuju tutup %s %02d:%02d UTC "
                "(guard %d mnt) -- entry otomatis AKTIF LAGI saat buka "
                "%s %02d:%02d UTC"
                % (_DOW.get(cd, "?"), ch, cm, b, _DOW.get(od, "?"), oh, om))
    return (False, "")


def rollover_block(now, k=None):
    """(blocked, why): jendela harian [rollover - N mnt, rollover + M)."""
    k = k or {}
    if k.get("enabled", True) is False:
        return (False, "")
    rh, rm = parse_hhmm(k.get("rollover_utc", "21:00"), (21, 0))
    b = int(k.get("rollover_skip_before_min", 30) or 0)
    a = int(k.get("rollover_after_min", 5) or 0)
    now_dt = datetime.fromtimestamp(int(now), tz=timezone.utc)
    mod = now_dt.hour * 60 + now_dt.minute
    r = rh * 60 + rm
    start = (r - b) % 1440
    end = (r + a) % 1440
    hit = ((mod >= start and mod < end) if start <= end
           else (mod >= start or mod < end))
    if hit:
        return (True, "SKIP_ROLLOVER: mendekati daily rollover/market "
                "break (%02d:%02d UTC, guard %d mnt sebelum/%d sesudah) "
                "-- cegah entry nyangkut" % (rh, rm, b, a))
    return (False, "")


def entry_blocked(symbol, k=None, now=None):
    """Gabungan utk 1 simbol: (blocked, code, why).  Pair 24/7 (kripto)
    bebas akhir pekan DAN bebas rollover (v3.70, permintaan user: sabtu
    minggu crypto tetap aktif -- kripto tidak punya market break)."""
    k = k or {}
    now = int(now if now is not None else time.time())
    if sym_always_open(symbol, k):            # kripto: 24/7 penuh
        return (False, "", "")
    hit, why = weekend_block(now, k)          # akhir pekan dulu (utama)
    if hit:
        return (True, "SKIP_SESSION", why)
    hit, why = rollover_block(now, k)         # lalu rollover harian
    if hit:
        return (True, "SKIP_ROLLOVER", why)
    return (False, "", "")
