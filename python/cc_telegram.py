# -*- coding: utf-8 -*-
"""CC TELEGRAM -- notifikasi Strategy 3 (v4.01, permintaan user).

Prinsip KEAMANAN TRADING:
  - SEMUA kirim lewat antrian + thread daemon -> pemanggil TIDAK PERNAH
    menunggu jaringan; Telegram lambat/mati = trading tetap jalan.
  - Tanpa token/chat -> modul OFF total (send = no-op, tidak error).
  - Anti spam: jeda antar pesan + dedupe teks sama (60 dtk) +
    dedupe event ERROR/PROTECT (300 dtk).

Sumber kredensial (urut): env RBT_TG_TOKEN/RBT_TG_CHAT >
cc_config.json "tg_token"/"tg_chat" > telegram_token.txt /
telegram_chat.txt > data/telegram_token.txt / data/telegram_chat.txt
(folder repo).  Setup sekali jalan di VPS:
    python python/cc_telegram.py --setup <TOKEN> <CHAT_ID>
(kredensial dari @BotFather + @userinfobot, lalu kirim tes otomatis).
"""
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.telegram.org/bot%s/sendMessage"
NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_UA = {"User-Agent": "Mozilla/5.0 RBT-FX-S3"}

_STATE = {
    "token": None, "chat": None, "enabled": False, "log": lambda m: None,
    "cfg": {}, "t_last": 0.0, "drop": 0,
    "online": False,          # pesan ONLINE sekali per proses
    "day": None,              # (y, m, d) WIB
    "snap": None,             # snapshot harian utk rekap
    "peak": 0.0, "dd": 0.0, "dd_eq": 0.0,
    "t0": time.time(), "status_every": 4 * 3600,
    "news_ts": 0.0, "news_cache": None,
    "news_seen": set(), "dedupe": {}, "err_last": 0.0,
    "bot": "", "last_error": "", "last_ok": 0.0,
    "acc": {},                # v4.18: info akun (currency utk format uang)
    "last_entry": {},         # v4.18: entry terakhir per pair (utk report close)
    "sig_ts": {},             # v4.18: anti-spam laporan SKIP/DITOLAK
}
_Q = queue.Queue(maxsize=300)
_CCYS = {"USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "NZD", "CNY"}
_TAG = "S3"   # branding pesan (otomatis di-replace per strategy)


# ---------------------------------------------------------------- util ----
def _f(x, d=2):
    """Angka rapi utk pesan (buang nol belakang berlebih)."""
    try:
        s = ("%." + str(d) + "f") % float(x)
        return s.rstrip("0").rstrip(".") if "." in s else s
    except Exception:
        return str(x)


def _px(x):
    """v4.18: harga rapi (nol belakang dibuang) atau '-' bila tak ada."""
    try:
        x = float(x)
    except Exception:
        return "-"
    if x == 0:
        return "-"
    s = ("%.5f" % x).rstrip("0").rstrip(".")
    return s or "0"


def _ccy_of():
    """v4.18: satuan akun (USD/IDR/dll) -- deteksi OTOMATIS dari akun
    broker (permintaan user: 'menyesuaikan kalau akun pake satuan apa')."""
    return str((_STATE.get("acc") or {}).get("currency") or "USD").upper()


def _money(x, signed=False, ccy=None):
    """v4.18: format uang sesuai satuan akun -- USD -> $1,234.56;
    IDR -> Rp 1.234.567; satuan lain -> angka + kode."""
    try:
        x = float(x or 0.0)
    except Exception:
        x = 0.0
    c = (ccy or _ccy_of()).upper()
    if c == "IDR":
        body = "Rp " + format(int(round(abs(x))), ",d").replace(",", ".")
    elif c == "USD":
        body = "$" + format(abs(x), ",.2f")
    else:
        body = "%.2f %s" % (abs(x), c)
    if x < -1e-9:
        return "-" + body
    return ("+" + body) if (signed and x > 1e-9) else body


def _pct(p):
    try:
        return "%+.1f%%" % float(p or 0.0)
    except Exception:
        return "+0.0%"


def _e(s):
    return re.sub(r"[<>&]", lambda m: {"<": "&lt;", ">": "&gt;",
                                       "&": "&amp;"}[m.group(0)], str(s))


def _log(tag, msg):
    """v4.06: tulis ke Execution Log engine (dua argumen sesuai
    emit_log) -- status BOT CONNECTED / BOT ERROR tampil di dashboard.
    Fallback 1 argumen utk logger lain; aman total (tak pernah raise)."""
    try:
        _STATE["log"](tag, msg)
    except Exception:
        try:
            _STATE["log"]("[%s] %s" % (tag, msg))
        except Exception:
            pass


def _wib_tm(ts=None):
    return time.gmtime((ts if ts is not None else time.time()) + 7 * 3600)


def _wib_day(ts=None):
    t = _wib_tm(ts)
    return (t.tm_year, t.tm_mon, t.tm_mday)


def _wib_str(day):
    return "%04d-%02d-%02d" % tuple(day)


def _wib_hm(ts=None):
    return time.strftime("%H:%M", _wib_tm(ts))


# ------------------------------------------------------- kredensial -------
def resolve_token(cfg=None):
    tok = (os.environ.get("RBT_TG_TOKEN") or "").strip()
    if tok:
        return tok
    try:
        t = (cfg or {}).get("tg_token", "") if cfg is not None else ""
        if t and str(t).strip():
            return str(t).strip()
    except Exception:
        pass
    for f in (os.path.join(ROOT, "telegram_token.txt"),
              os.path.join(ROOT, "data", "telegram_token.txt")):
        try:
            if os.path.exists(f):
                t = open(f, encoding="utf-8").read().strip()
                if t:
                    return t
        except Exception:
            pass
    return None


def resolve_chat(cfg=None):
    cid = (os.environ.get("RBT_TG_CHAT") or "").strip()
    if cid:
        return cid
    try:
        t = (cfg or {}).get("tg_chat", "") if cfg is not None else ""
        if t and str(t).strip():
            return str(t).strip()
    except Exception:
        pass
    for f in (os.path.join(ROOT, "telegram_chat.txt"),
              os.path.join(ROOT, "data", "telegram_chat.txt")):
        try:
            if os.path.exists(f):
                t = open(f, encoding="utf-8").read().strip()
                if t:
                    return t
        except Exception:
            pass
    return None


# ------------------------------------------------------------ pengiriman --
_TG_IP = "https://149.154.167.220"   # fallback: IP DC Bot API


def _proxy():
    """v4.10: proxy opsional utk Telegram -- file telegram_proxy.txt
    di ROOT berisi mis. http://user:pass@host:port atau socks5://..."""
    try:
        f = os.path.join(ROOT, "telegram_proxy.txt")
        if os.path.exists(f):
            s = open(f, encoding="utf-8").read().strip()
            if s:
                return {"https": s, "http": s}
    except Exception:
        pass
    return None


def _tg_open(url, data=None, timeout=10):
    """v4.10: buka URL Telegram dgn jalur cadangan: (1) proxy file
    kalau ada, (2) normal, (3) IP langsung DC Bot API (bypass DNS).
    Return (body|None, code|0, err). Tidak pernah raise."""
    errs = []
    px = _proxy()
    if px:
        try:
            op = urllib.request.build_opener(
                urllib.request.ProxyHandler(px))
            with op.open(urllib.request.Request(url, data=data,
                                                headers=_UA),
                         timeout=timeout) as r:
                return r.read(), r.status, ""
        except Exception as e:
            errs.append("proxy:%s" % str(e)[:90])
    try:
        req = urllib.request.Request(url, data=data, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.status, ""
    except urllib.error.HTTPError as e:
        try:
            return e.read(), e.code, "HTTP %s" % e.code
        except Exception:
            return b"", e.code, "HTTP %s" % e.code
    except Exception as e:
        errs.append(str(e)[:90])
    try:                                   # fallback: IP langsung
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        u2 = url.replace("https://api.telegram.org", _TG_IP, 1)
        req = urllib.request.Request(u2, data=data, headers=_UA)
        req.add_header("Host", "api.telegram.org")
        op = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx))
        with op.open(req, timeout=timeout) as r:
            return r.read(), r.status, ""
    except urllib.error.HTTPError as e:
        try:
            return e.read(), e.code, "HTTP %s" % e.code
        except Exception:
            return b"", e.code, "HTTP %s" % e.code
    except Exception as e:
        errs.append("ip:%s" % str(e)[:90])
    return None, 0, "; ".join(errs) or "gagal"


def _post_detail(text, token=None, chat=None):
    """v4.04: kirim sinkron + ALASAN GAGAL dari
    Telegram (mis. 401 Unauthorized / 403 bot belum di-START / 400
    chat not found).  Return (ok, detail).  Tidak pernah raise."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat or _STATE["chat"], "text": text[:3900],
            "parse_mode": "HTML", "disable_web_page_preview": "true",
        }).encode("utf-8")
        body, code, err = _tg_open(API % (token or _STATE["token"]),
                                   data=data)
        if body:
            d = json.loads(body.decode("utf-8", "ignore"))
            if d.get("ok"):
                return True, ""
            return False, "%s: %s" % (d.get("error_code", code),
                                      str(d.get("description", ""))[:180])
        return False, (err or ("HTTP %s" % code))[:180]
    except Exception as e:
        return False, str(e)[:180]


def _post(text, token=None, chat=None):
    """Kirim sinkron. Return True sukses. Tidak pernah raise."""
    return _post_detail(text, token, chat)[0]


def _clean(v):
    """v4.08: bersihkan input user: kutip pembuka/penutup, spasi,
    dan spasi non-breaking yang sering ikut saat copy-paste."""
    s = str(v or "").strip().strip('"').strip("'").strip()
    return s.replace("\u00a0", "").strip()


def _get_me(token):
    """v4.05: verifikasi TOKEN terpisah via getMe -> (ok, username|err)."""
    try:
        body, code, err = _tg_open(
            "https://api.telegram.org/bot%s/getMe" % token)
        if body:
            d = json.loads(body.decode("utf-8", "ignore"))
            if d.get("ok"):
                return True, str((d.get("result") or {})
                                 .get("username", ""))
            return False, "%s: %s" % (d.get("error_code", code),
                                      str(d.get("description", ""))[:120])
        return False, (err or ("HTTP %s" % code))[:150]
    except Exception as e:
        return False, str(e)[:150]


def _set_err(msg):
    _STATE["last_error"] = str(msg)[:300]


def state():
    """v4.05: status koneksi utk badge dashboard (persistent)."""
    return {"on": bool(_STATE["enabled"]),
            "bot": _STATE.get("bot", ""),
            "err": _STATE.get("last_error", ""),
            "ok_ts": _STATE.get("last_ok", 0.0)}


def files_present():
    """v4.07: apakah kredensial SUDAH TERSIMPAN di file?  Dipakai panel
    SUBMIT utk membedakan 'user belum submit' vs 'submit gagal' vs
    'tersimpan tapi engine belum memuat'."""
    def _has(name):
        try:
            f = os.path.join(ROOT, name)
            return bool(os.path.exists(f)
                        and open(f, encoding="utf-8").read().strip())
        except Exception:
            return False
    return {"token": _has("telegram_token.txt"),
            "chat": _has("telegram_chat.txt")}


def test_send(token, chat, text):
    """v4.05: diagnosa 2 LANGKAH: (1) getMe -> token valid & nama bot,
    (2) kirim ke chat -> alasan persis (START/chat id/jaringan).
    Return (ok, detail)."""
    token, chat = _clean(token), _clean(chat)   # v4.08: kutip/spasi ikut
    okb, bot = _get_me(token)
    if not okb:
        _set_err("TOKEN salah (%s)" % bot)
        _log("ERROR", "TG BOT ERROR -- TOKEN salah (%s) -- "
             "ambil ulang dari @BotFather" % bot)
        return False, "LANGKAH 1 TOKEN GAGAL -> %s" % bot
    ok, det = _post_detail(text, token, chat)
    if not ok:
        time.sleep(1.5)
        ok, det = _post_detail(text, token, chat)
    if not ok:
        low = det.lower()
        if "403" in det or "initiate" in low:
            det = ("BOT @%s valid, tapi BELUM BISA kirim ke chat %s -> "
                   "BUKA bot @%s di Telegram lalu TEKAN START (%s)"
                   % (bot, chat, bot, det))
        elif "chat not found" in low or "400" in det:
            det = ("CHAT_ID %s salah/tak dikenal bot @%s -> harus angka "
                   "dari @userinfobot (%s)" % (chat, bot, det))
        elif "401" in det:
            det = "TOKEN salah (%s)" % det
        _set_err(det)
        _log("ERROR", "TG BOT ERROR -- %s" % det)
        return False, "LANGKAH 2 CHAT GAGAL -> %s" % det
    _STATE["bot"] = "@" + bot
    _STATE["last_error"] = ""
    _STATE["last_ok"] = time.time()
    _log("INFO", "TG BOT CONNECTED -- @%s (tes kirim sukses, "
         "notifikasi AKTIF)" % bot)
    return True, ""


def diag(token=None, chat=None):
    """v4.05: TES DIAGNOSA utk dashboard -- langkah demi langkah dgn
    hasil per langkah (token / kirim chat).  Return dict steps."""
    token, chat = _clean(token or _STATE["token"]), \
        _clean(chat or _STATE["chat"])
    steps = []
    if not token or not chat:
        return {"ok": False, "steps": [
            {"step": "kredensial", "ok": False,
             "msg": "token/chat belum ada -- isi form dulu"}],
            "message": "Isi BOT_TOKEN & CHAT_ID dulu"}
    okb, bot = _get_me(token)
    steps.append({"step": "1. CEK BOT_TOKEN (getMe)", "ok": okb,
                  "msg": ("valid -> bot @%s" % bot) if okb else bot})
    if not okb:
        _set_err("TOKEN salah (%s)" % bot)
        _log("ERROR", "TG BOT ERROR (diagnosa) -- TOKEN salah: %s" % bot)
        return {"ok": False, "steps": steps,
                "message": "TOKEN salah -- ambil ulang dari @BotFather"}
    ok, det = _post_detail("RBT FX diagnosa koneksi", token, chat)
    if ok:
        steps.append({"step": "2. KIRIM ke CHAT_ID %s" % chat, "ok": True,
                      "msg": "terkirim -- cek Telegram Anda"})
        _STATE["bot"] = "@" + bot
        _STATE["last_error"] = ""
        _STATE["last_ok"] = time.time()
        _log("INFO", "TG BOT CONNECTED (diagnosa) -- @%s -- SEMUA OK, "
             "notifikasi AKTIF" % bot)
        return {"ok": True, "steps": steps,
                "message": "SEMUA OK -- notifikasi Telegram AKTIF"}
    low = det.lower()
    if "403" in det or "initiate" in low:
        hint = ("Buka chat bot @%s di Telegram lalu TEKAN START, "
                "setelah itu TES DIAGNOSA lagi" % bot)
    elif "chat not found" in low or "400" in det:
        hint = ("CHAT_ID harus angka dari @userinfobot "
                "(bukan @username)")
    else:
        hint = "cek internet VPS ke api.telegram.org"
    steps.append({"step": "2. KIRIM ke CHAT_ID %s" % chat, "ok": False,
                  "msg": "%s -> %s" % (det, hint)})
    _set_err("%s -> %s" % (det, hint))
    return {"ok": False, "steps": steps,
            "message": "BOT @%s OK, tapi chat gagal -> %s" % (bot, hint)}


def _process_one():
    """Ambil 1 item antrian + kirim (dgn jeda & 3x percobaan)."""
    try:
        text = _Q.get(timeout=0.5)
    except Exception:
        return
    gap = time.time() - _STATE["t_last"]
    if gap < 1.2:
        time.sleep(1.2 - gap)
    ok, det = False, ""
    for _ in range(3):
        ok, det = _post_detail(text)
        if ok:
            break
        time.sleep(2.0)
    _STATE["t_last"] = time.time()
    if not ok:
        _STATE["drop"] += 1
        _STATE["last_error"] = "kirim gagal: %s" % det
        _log("ERROR", "TG BOT ERROR -- kirim pesan gagal (total %d) "
             "-- %s -- cek internet VPS ke api.telegram.org "
             "(CEK_TELEGRAM.bat)" % (_STATE["drop"], det or "?"))
    else:
        if _STATE["drop"] > 0:
            _log("INFO", "TG BOT CONNECTED (pulih) -- kirim sukses lagi")
        _STATE["drop"] = 0
        _STATE["last_error"] = ""


def _worker():
    while True:
        _process_one()


def enabled():
    return bool(_STATE["enabled"])


def send(text):
    """Antrikan pesan. False = modul off/antrian penuh. TIDAK raise."""
    if not _STATE["enabled"]:
        return False
    now = time.time()
    key = hash(text)
    if now - _STATE["dedupe"].get(key, 0) < 60:
        return False
    if len(_STATE["dedupe"]) > 400:
        _STATE["dedupe"].clear()
    _STATE["dedupe"][key] = now
    try:
        _Q.put_nowait(text)
    except Exception:
        try:                       # penuh -> buang terlama, sisip baru
            _Q.get_nowait()
            _Q.put_nowait(text)
        except Exception:
            return False
    return True


def forward(tag, msg):
    """Forward log engine: ERROR/PROTECT -> Telegram (dedupe 300 dtk)."""
    if tag not in ("ERROR", "PROTECT"):
        return False
    now = time.time()
    if now - _STATE["err_last"] < 300 and tag == "PROTECT":
        pass                        # PROTECT sering berulang -> tetap
                                    #   dilindungi dedupe teks di send()
    _STATE["err_last"] = now
    icon = "\u26a0\ufe0f" if tag == "ERROR" else "\U0001f6a8"
    return send("%s <b>S3 %s</b>\n%s\n(%s WIB)"
                % (icon, _e(tag), _e(msg), _wib_hm()))


# ------------------------------------------------------- pesan (murni) ----
def msg_online(version, info):
    return ("\U0001f7e2 <b>ENGINE S3 ONLINE v%s</b>\n%s\n(%s WIB)"
            % (_e(version), _e(info), _wib_hm()))


def msg_offline(reason):
    return ("\U0001f534 <b>ENGINE S3 OFFLINE</b>\n%s\n(%s WIB)"
            % (_e(reason), _wib_hm()))


def msg_restart(reason):
    return ("\U0001f504 <b>S3 RESTART</b> -- %s\nEngine memuat ulang, "
            "pesan ONLINE menyusul.\n(%s WIB)"
            % (_e(reason), _wib_hm()))


def _acct_block(snap=None, max_dd=False):
    """v4.18: blok bawah template user -- EQUITY, DAILY PROFIT, DAILY
    LOSS, DRAWDOWN; Rp/% menyesuaikan satuan akun otomatis."""
    s = dict(snap or _STATE.get("snap") or {})
    eq = float(s.get("eq") or 0.0)
    bal0 = float(s.get("bal0") or 0.0) or eq
    base = bal0 if bal0 > 0 else (eq if eq > 0 else 1.0)
    real = float(s.get("realized") or 0.0)
    prof, loss = max(real, 0.0), min(real, 0.0)
    if max_dd:      # rekap: DD MAKSIMUM hari ini (+ equity terendah)
        dd_line = "-%.1f%% (terendah %s)" % (float(s.get("dd") or 0.0),
                                             _money(s.get("dd_eq")))
    else:           # live: DD berjalan dari puncak equity
        peak = float(s.get("peak") or 0.0) or eq
        dm = max(0.0, peak - eq)
        dp = (dm / peak * 100.0) if peak > 0 else 0.0
        dd_line = "%s ( %s )" % (_money(-dm), _pct(-dp))
    return ("----------------------------------------\n"
            "EQUITY\t\t: %s\n"
            "DAILY PROFIT\t: %s ( %s )\n"
            "DAILY LOSS\t: %s ( %s )\n"
            "DRAWDOWN\t: %s"
            % (_money(eq), _money(prof, signed=True),
               _pct(prof / base * 100.0), _money(loss, signed=True),
               _pct(loss / base * 100.0), dd_line))


def _wib_full():
    return time.strftime("%Y-%m-%d %H:%M", _wib_tm())


def msg_signal(sym, side, note, why, price=None, sl=None, tp1=None,
               tp2=None):
    """v4.18: laporan sinyal TIDAK jadi entry (SKIP) / order gagal broker
    (DITOLAK) -- template sama; anti-spam 30 mnt di signal()."""
    return ("\u26a0\ufe0f <b>S3 SIGNAL -- %s</b>\n"
            "NAMA PAIR\t: %s\n"
            "WAKTU/JAM\t: %s WIB\n"
            "SIGNAL\t\t: %s\n"
            "ENTRY DI HARGA\t: %s\n"
            "NOTE SIGNAL/LOG\t: %s -- %s\n"
            "HARGA SL\t: %s\n"
            "HARGA TP 1\t: %s\n"
            "HARGA TP 2\t: %s\n"
            "P/L\t\t: -\n%s"
            % (_e(str(note)), _e(str(sym)), _wib_full(),
               _e(str(side or "-")), _px(price), _e(str(note)),
               _e(str(why or "")), _px(sl), _px(tp1), _px(tp2),
               _acct_block()))


def signal(sym, side, note, why, price=None, sl=None, tp1=None, tp2=None):
    """v4.18: kirim laporan SKIP/DITOLAK, maks 1x / 30 mnt / pair+note."""
    try:
        k = "%s|%s|%s" % (str(sym).upper(), note,
                         str(side or "-"))
        ts = _STATE.setdefault("sig_ts", {})
        now = time.time()
        if now - float(ts.get(k, 0.0) or 0.0) < 1800.0:
            return False
        ts[k] = now
    except Exception:
        pass
    return send(msg_signal(sym, side, note, why, price, sl, tp1, tp2))


def msg_entry(sym, side, lot, price, sl, tp, tp_txt, extra="", tp2=0.0,
              risk_money=None, risk_pct=0.0):
    """v4.18 TEMPLATE LENGKAP (permintaan user): pair, jam WIB, signal,
    entry, note, SL/TP1/TP2, P/L + blok akun.  P/L saat entry = 0 plus
    estimasi risiko jika SL kena.  Uang menyesuaikan satuan akun."""
    try:
        _STATE.setdefault("last_entry", {})[str(sym).upper()] = {
            "side": side, "price": price, "sl": sl, "tp1": tp, "tp2": tp2}
    except Exception:
        pass
    rk = ""
    if risk_money:
        rk = " | risiko %s ( %.1f%% ) jk SL" % (
            _money(-abs(float(risk_money))), float(risk_pct or 0.0))
    note = _e(tp_txt or "OK")
    if extra:
        note += " | " + _e(str(extra))
    return ("\U0001f3af <b>ENTRY S3</b> (lot %s)\n"
            "NAMA PAIR\t: %s\n"
            "WAKTU/JAM\t: %s WIB\n"
            "SIGNAL\t\t: %s\n"
            "ENTRY DI HARGA\t: %s\n"
            "NOTE SIGNAL/LOG\t: OK -- %s\n"
            "HARGA SL\t: %s\n"
            "HARGA TP 1\t: %s\n"
            "HARGA TP 2\t: %s\n"
            "P/L\t\t: %s ( +0.0%% )%s\n%s"
            % (_f(lot), _e(str(sym)), _wib_full(), _e(str(side)),
               _px(price), note, _px(sl), _px(tp), _px(tp2),
               _money(0.0, signed=True), rk, _acct_block()))


def msg_close(sym, pl, lot, extra=""):
    """v4.18: template lengkap hasil close -- P/L real (satuan akun) +
    blok akun; detail entry diambil dari memori entry terakhir."""
    icon = "\u2705" if pl >= 0 else "\U0001f6d1"
    le = (_STATE.get("last_entry") or {}).get(str(sym).upper()) or {}
    s = dict(_STATE.get("snap") or {})
    bal0 = float(s.get("bal0") or 0.0)
    eq = float(s.get("eq") or 0.0)
    base = bal0 if bal0 > 0 else (eq if eq > 0 else 0.0)
    pp = (float(pl) / base * 100.0) if base > 0 else 0.0
    note = "CLOSE %s -- %s" % ("WIN" if pl >= 0 else "LOSS",
                               _e(extra or "ditutup broker"))
    return ("%s <b>CLOSE S3</b> (lot %s)\n"
            "NAMA PAIR\t: %s\n"
            "WAKTU/JAM\t: %s WIB\n"
            "SIGNAL\t\t: %s\n"
            "ENTRY DI HARGA\t: %s\n"
            "NOTE SIGNAL/LOG\t: %s\n"
            "HARGA SL\t: %s\n"
            "HARGA TP 1\t: %s\n"
            "HARGA TP 2\t: %s\n"
            "P/L\t\t: %s ( %s )\n%s"
            % (icon, _f(lot), _e(str(sym)), _wib_full(),
               _e(str(le.get("side") or "-")), _px(le.get("price")),
               note, _px(le.get("sl")), _px(le.get("tp1")),
               _px(le.get("tp2")), _money(pl, signed=True), _pct(pp),
               _acct_block()))


def msg_recap(snap, day):
    return ("\U0001f4ca <b>REKAP HARIAN S3</b> (%s)\n"
            "Balance: %s \u2192 <b>%s</b> | Realized: %s\n"
            "%s\n(%s WIB)"
            % (_e(str(day)), _money(snap.get("bal0", 0.0)),
               _money(snap.get("bal", 0.0)),
               _money(snap.get("realized", 0.0), signed=True),
               _acct_block(snap, max_dd=True), _wib_hm()))


def msg_status(snap, version, npos):
    return ("\U0001f493 <b>STATUS S3 v%s</b>\n"
            "Posisi terbuka: %d\n%s\n(%s WIB)"
            % (_e(str(version)), int(npos), _acct_block(snap),
               _wib_hm()))


def msg_news(ev, lead_min, syms):
    return ("\U0001f4f0 <b>MARKET NEWS high-impact</b>\n%s %s\n"
            "Rilis %s WIB (\u2248 %d mnt lagi)\n"
            "Perhatikan: %s\n(%s WIB)"
            % (_e(ev.get("country", "")), _e(ev.get("title", "")),
               _e(ev.get("wib", "")), int(lead_min), _e(syms), _wib_hm()))


def msg_connected():
    """Pesan sukses konek dari dashboard (permintaan user)."""
    return ("\U0001f7e2 <b>RBT FX %s: CONNECTING SUKSES</b>\n"
            "Notifikasi Telegram AKTIF -- entry, close, rekap harian "
            "dan alert news akan masuk ke chat ini.\n(%s WIB)"
            % (_TAG, _wib_hm()))


# ------------------------------------------------- event level engine -----
def rebind(token, chat):
    """v4.02: pasang kredensial baru dari dashboard + aktifkan worker."""
    _STATE["token"] = (token or "").strip()
    _STATE["chat"] = str(chat or "").strip()
    _STATE["dedupe"] = {}
    if not _STATE["enabled"]:
        _STATE["enabled"] = True
        threading.Thread(target=_worker, daemon=True).start()
        _install_excepthook()
    _log("INFO", "TG kredensial baru dipasang dari dashboard "
         "(%s)" % (_STATE.get("bot") or ("chat " + _STATE["chat"])))
    return True


def init(cfg=None, log=print):
    """Resolve kredensial + nyalakan thread kirim. Aman dipanggil 2x."""
    _STATE["cfg"] = cfg or {}
    try:
        _STATE["log"] = log
    except Exception:
        pass
    if _STATE["enabled"]:
        return True
    _STATE["token"] = resolve_token(cfg)
    _STATE["chat"] = resolve_chat(cfg)
    if not _STATE["token"] or not _STATE["chat"]:
        _log("INFO", "TG OFF -- notifikasi belum dikonfigurasi "
             "(isi BOT_TOKEN & CHAT_ID lewat CLI: python python/cc_telegram.py --setup TOKEN CHAT_ID)")
        return False
    if str(_STATE["cfg"].get("tg_enabled", True)) in ("0", "False", "false"):
        return False
    _STATE["enabled"] = True
    _STATE["status_every"] = (float(_STATE["cfg"].get("tg_status_hours", 4)
                                     or 0) * 3600)
    threading.Thread(target=_worker, daemon=True).start()
    _install_excepthook()
    # v4.06: status koneksi LANGSUNG terlihat di Execution Log
    _okb, _bot = _get_me(_STATE["token"])
    if _okb:
        _STATE["bot"] = "@" + _bot
        _STATE["last_error"] = ""
        _log("INFO", "TG BOT CONNECTED -- @%s (token valid, "
             "notifikasi Telegram AKTIF)" % _bot)
    else:
        _STATE["last_error"] = str(_bot)
        _log("ERROR", "TG BOT ERROR -- %s -- cek internet VPS ke "
             "api.telegram.org (jalankan CEK_TELEGRAM.bat)" % _bot)
    return True


def engine_online(version, info):
    _STATE["online"] = True
    return send(msg_online(version, info))


def engine_offline(reason):
    if not _STATE["enabled"]:
        return False
    return send(msg_offline(reason))


def restart(reason):
    return send(msg_restart(reason))


def entry(sym, side, lot, price, sl, tp, tp_txt, extra="", tp2=0.0,
          risk_money=None, risk_pct=0.0):
    return send(msg_entry(sym, side, lot, price, sl, tp, tp_txt, extra,
                          tp2=tp2, risk_money=risk_money,
                          risk_pct=risk_pct))


def close(sym, pl, lot, extra=""):
    return send(msg_close(sym, pl, lot, extra))


def error(msg):
    return forward("ERROR", msg)


# ------------------------------------ tick utama: online/dd/rekap/status --
def _snap_of(balance, equity, realized, floating):
    s = _STATE
    return {"bal0": (s["snap"] or {}).get("bal0", balance) or balance,
            "bal": balance, "eq": equity, "realized": realized,
            "float": floating, "dd": s["dd"], "dd_eq": s["dd_eq"],
            "peak": s.get("peak", 0.0)}


def _news_tick(symbols, now=None):
    """Market news high-impact (ForexFactory mingguan, cache 6 jam)."""
    now = now if now is not None else time.time()
    if not _STATE["cfg"].get("tg_news_enabled", True):
        return
    if now - _STATE["news_ts"] < 15 * 60:
        return
    _STATE["news_ts"] = now
    if (_STATE["news_cache"] is None
            or now - _STATE["news_cache"][0] > 6 * 3600):
        try:
            req = urllib.request.Request(NEWS_URL, headers=_UA)
            with urllib.request.urlopen(req, timeout=12) as r:
                _STATE["news_cache"] = (now, json.loads(
                    r.read().decode("utf-8", "ignore")))
        except Exception:
            _STATE["news_cache"] = (now, [])
    evs = (_STATE["news_cache"] or (0, []))[1] or []
    watched = set()
    for s in symbols or []:
        su = str(s).upper()
        for c in (su[:3], su[-3:]):
            if c in _CCYS:
                watched.add(c)
    lead = float(_STATE["cfg"].get("tg_news_lead_min", 120) or 120)
    from datetime import datetime
    for ev in evs:
        try:
            if str(ev.get("impact", "")).lower() != "high":
                continue
            ccy = str(ev.get("country", "")).upper()
            if ccy not in watched:
                continue
            dt = datetime.fromisoformat(str(ev.get("date", "")).strip())
            ts = dt.timestamp()
            mins = (ts - now) / 60.0
            if not (0 <= mins <= lead):
                continue
            key = (ccy, str(ev.get("title", "")), int(ts // 3600))
            if key in _STATE["news_seen"]:
                continue
            _STATE["news_seen"].add(key)
            if len(_STATE["news_seen"]) > 500:
                _STATE["news_seen"].clear()
            wib = time.strftime("%H:%M", _wib_tm(ts))
            send(msg_news({"country": ccy, "title": ev.get("title", ""),
                           "wib": wib}, mins, ", ".join(
                               sorted(symbols or [])[:4])))
        except Exception:
            continue


def tick(version, equity, balance, realized, floating, npos=0,
         acc=None, symbols=None):
    """Dipanggil engine tiap loop: ONLINE sekali, lacak DD, rekap
    otomatis saat ganti hari WIB, heartbeat berkala, market news."""
    if not _STATE["enabled"]:
        return
    try:
        _STATE["acc"] = acc or {}      # v4.18: satuan akun utk format uang
        now = time.time()
        d = _wib_day(now)
        if not _STATE["online"]:
            _STATE["online"] = True
            _STATE["day"] = d
            _STATE["peak"] = equity
            _STATE["dd"] = 0.0
            _STATE["dd_eq"] = equity
            _STATE["snap"] = _snap_of(balance, equity, realized, floating)
            _STATE["t0"] = now
            info = []
            try:
                a = acc or {}
                info.append("Akun %s @ %s" % (a.get("login", "?"),
                                              a.get("server", "?")))
            except Exception:
                pass
            info.append("Balance %s" % _f(balance))
            try:
                info.append("Pair: %s" % ", ".join(symbols or []))
            except Exception:
                pass
            send(msg_online(version, "\n".join(info)))
            return
        if d != _STATE["day"]:
            send(msg_recap(_STATE["snap"] or {}, _STATE["day"]))
            _STATE["day"] = d
            _STATE["peak"] = equity
            _STATE["dd"] = 0.0
            _STATE["dd_eq"] = equity
            _STATE["snap"] = {"bal0": balance, "bal": balance, "eq": equity,
                              "realized": realized, "float": floating,
                              "dd": 0.0, "dd_eq": equity}
            _STATE["t0"] = now
            return
        if equity > _STATE["peak"]:
            _STATE["peak"] = equity
        dd = ((_STATE["peak"] - equity) / _STATE["peak"] * 100.0
              if _STATE["peak"] > 0 else 0.0)
        if dd > _STATE["dd"]:
            _STATE["dd"] = dd
            _STATE["dd_eq"] = equity
        _STATE["snap"] = _snap_of(balance, equity, realized, floating)
        every = _STATE["status_every"]
        if every > 0 and now - _STATE["t0"] >= every:
            _STATE["t0"] = now
            send(msg_status(_STATE["snap"], version, npos))
        _news_tick(symbols, now)
    except Exception:
        pass


def _install_excepthook():
    if getattr(_STATE, "_hooked", False):
        return
    _STATE["_hooked"] = True
    _orig = sys.excepthook

    def _hook(t, v, tb):
        try:
            if _STATE["enabled"]:
                tail = "".join(__import__("traceback")
                               .format_exception(t, v, tb))[-800:]
                send("\U0001f534 <b>S3 CRASH</b>\n<code>%s</code>\n(%s WIB)"
                     % (_e(tail), _wib_hm()))
        except Exception:
            pass
        try:
            _orig(t, v, tb)
        except Exception:
            pass
    sys.excepthook = _hook


# ---------------------------------------------------------------- CLI -----
if __name__ == "__main__":
    a = sys.argv[1:] if len(sys.argv) > 1 else []
    if a and a[0] == "--setup" and len(a) >= 3:
        _tok, _cid = _clean(a[1]), _clean(a[2])
        open(os.path.join(ROOT, "telegram_token.txt"), "w",
             encoding="utf-8").write(_tok)
        open(os.path.join(ROOT, "telegram_chat.txt"), "w",
             encoding="utf-8").write(_cid)
        _STATE["token"], _STATE["chat"] = _tok, _cid
        _STATE["enabled"] = True
        print("Kredensial disimpan. Tes kirim...")
        ok = send("\U0001f7e2 RBT FX S3: koneksi Telegram BERHASIL. "
                  "Notifikasi engine akan masuk ke chat ini.")
        if ok:
            _process_one()
            print("SELESAI -- cek Telegram Anda.")
        else:
            _process_one()
            print("Tersimpan, tapi tes kirim belum terkonfirmasi -- "
                  "cek token/chat id lalu jalankan --test.")
    elif a and a[0] == "--test":
        _STATE["token"] = resolve_token()
        _STATE["chat"] = resolve_chat()
        _STATE["enabled"] = bool(_STATE["token"] and _STATE["chat"])
        print("token:", "ada" if _STATE["token"] else "TIDAK ADA")
        print("chat :", "ada" if _STATE["chat"] else "TIDAK ADA")
        send("\U0001f7e2 RBT FX S3: tes kirim Telegram (%s WIB)" % _wib_hm())
        ok, det = _post_detail("tes koneksi engine")
        print("hasil:", "SUKSES (cek Telegram)" if ok
              else "GAGAL -- " + str(det))
    else:
        print("Pemakaian:\n"
              "  python cc_telegram.py --setup <TOKEN_BOT> <CHAT_ID>\n"
              "  python cc_telegram.py --test")
