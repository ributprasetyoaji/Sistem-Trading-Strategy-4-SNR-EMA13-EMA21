# -*- coding: utf-8 -*-
"""
RBT FX :: TRADING ALGO SYSTEM - Dashboard jendela Python (Tkinter).

Jendela desktop TANPA WEB BROWSER - tampilan disalin persis dari dashboard
web RBT FX (topbar chip, tape, cards, scanner, confluence + gauge, positions,
chart, execution log, sessions, modules, statusbar).
Sumber data: http://127.0.0.1:<port>/api/status (8081/8080 otomatis).
Pustaka standar Python saja - tanpa install.
"""
import json
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import tkinter as tk
    from tkinter import ttk, font as tkfont
    from tkinter import simpledialog, messagebox
except ImportError:  # pragma: no cover
    print("Tkinter tidak tersedia di Python ini.")
    sys.exit(1)

# ---- palet RBT FX (identik web) -------------------------------------------
BG = "#020604"; PAN = "#06130c"; PAN2 = "#0a1d12"; BD2 = "#2e5340"; BD = "#0d2c1d"
ACC = "#00ff9c"; CY = "#00e0ff"; GRN = "#00ff9c"; RED = "#ff2d55"


def _rbt_self_exec(delay=1.5):
    """v3.97: muat ulang PROSES dashboard (os.execv) -- dipanggil saat
    versi engine berubah: file dashboard di disk sudah baru hasil
    self-update engine, execv memuat kode baru TANPA tutup bat
    (jendela kedip sekali, lalu hidup lagi dgn label/rule terbaru)."""
    def _go():
        import os as _os
        import sys as _sys
        import threading as _th
        import time as _t
        _t.sleep(max(0.2, float(delay)))
        _exe = _sys.executable or "pythonw"
        _os.execv(_exe, [_exe, _os.path.abspath(_sys.argv[0])]
                  + list(_sys.argv[1:]))
    threading.Thread(target=_go, daemon=True).start()


AMBER = "#ffc857"; VIO = "#b78cff"; TX = "#dcffee"; DIM = "#5d9678"
DIM2 = "#2a5440"; TAPE_BG = "#02150c"

PORTS = [8081, 8080]

CAT_GOLD = {"XAUUSD","XAGUSD","GOLD","SILVER","XAUUSDM","XAGUSDM"}
CAT_FOREX = {"EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCHF","USDCAD",
             "EURJPY","GBPJPY","AUDJPY","EURGBP"}
CAT_CRYPTO = {"BTCUSD","ETHUSD","BTCUSDM","ETHUSDM","BTCEUR","ETHEUR"}
CAT_INDEX = {"NAS100","US30","SPX500","GER40","JP225","NAS100M","US500",
             "UK100","AUS200","UT100","USTEC"}
CAT_COMM = {"USOIL","XTIUSD","XBRUSD","USOILM","UKOIL","NGAS","XPTUSD","XPDUSD"}

_RX_GOLD = re.compile(r"^(XAU|XAG|GOLD|SILVER|XPT)")
_RX_CRY = re.compile(r"^(BTC|ETH|SOL|XRP|LTC|DOGE|ADA|XLM|BCH|DOT|LINK)")
_RX_IDX = re.compile(r"(NAS|USTEC|US100|US30|US500|GER|DAX|UK100|FTSE|JP225|NIKKEI|HK50|AUS200|SPX)")
_RX_COM = re.compile(r"(OIL|WTI|BRENT|XBR)")
_TAB_CAT = {"GOLD/SILVER": "GOLD"}   # v4.32: label tombol tab -> kategori cat_of


def cat_of(sym):
    s = (sym or "").upper()
    if s in CAT_GOLD: return "GOLD"
    if s in CAT_FOREX: return "FOREX"
    if s in CAT_CRYPTO: return "CRYPTO"
    if s in CAT_INDEX: return "INDEX"
    if s in CAT_COMM: return "COMMODITY"
    # v4.32: nama broker apapun tetap tergrup benar (GOLD.a, XAUUSD.r, ...)
    if _RX_GOLD.match(s): return "GOLD"
    if _RX_CRY.match(s): return "CRYPTO"
    if _RX_IDX.search(s): return "INDEX"
    if _RX_COM.search(s): return "COMMODITY"
    return "FOREX"


def fmt(v, d=2):
    try: v = float(v)
    except (TypeError, ValueError): v = 0.0
    s0 = "%.*f" % (d, abs(v))
    ip, _, op = s0.partition(".")
    ip = "".join(("," if i and (len(ip) - i) % 3 == 0 else "") + c
                 for i, c in enumerate(ip))
    return ("-" if v < 0 else "") + ip + (("." + op) if op else "")


def mn(v, ccy):
    a = abs(float(v or 0))
    return fmt(a, 0 if a >= 1000 else 2) + " " + ccy


def col_for(v):
    return GRN if float(v or 0) >= 0 else RED


def word_for(key, side, v):
    bull = side == "BUY"
    if key == "liquidity": return "Sweep" if v >= 55 else "None"
    if key == "trend":
        return ("Uptrend" if bull else "Downtrend") if v >= 55 else \
               ("Downtrend" if bull else "Uptrend")
    if key == "momentum": return "Strong" if v >= 55 else "Weak"
    if key == "volume": return "Confirmed" if v >= 55 else "Outside"
    return ("Bullish" if bull else "Bearish") if v >= 55 else \
           ("Bearish" if bull else "Bullish")


CF_NAMES = [("structure", "MARKET STRUCTURE"), ("liquidity", "LIQUIDITY (SMC)"),
            ("trend", "TREND FILTER"), ("momentum", "MOMENTUM"),
            ("volume", "VOLUME"), ("orderflow", "ORDER FLOW")]

LOG_TAG_COL = {"BUY": GRN, "SELL": RED, "CLOSE": CY, "TP": GRN, "SL": RED,
               "HALT": RED, "RESUME": GRN, "ERROR": RED, "WARN": AMBER,
               "PROTECT": RED, "GUARD": AMBER, "INFO": "#9adfb9",
               "OPEN": CY, "TRAIL": VIO, "SCAN": DIM}

SESSIONS_HRS = {"SYDNEY": (21, 6), "TOKYO": (0, 9), "LONDON": (7, 16),
                "NEW YORK": (12, 21)}


# ------------------------------------------------------------- klien -------
def _mixc(c1, c2, t):
    """Campur 2 warna hex (#rrggbb), t=0..1."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(
        int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class GlobeTk(tk.Canvas):
    """BOLA DUNIA CYBER utk Tk: wireframe globe berputar (hacker net).

    Meridian + paralel dirotasi 3D, sisi belakang redup, blip data
    berkedip, lingkar glow luar. 12 fps -- hemat CPU di VPS."""

    SHADES = 8

    def __init__(self, master, size=56, bg=None, acc="#00ff9c",
                 dim="#2a5440", fade=0.30, **kw):
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bg", bg if bg else master["bg"])
        tk.Canvas.__init__(self, master, width=size, height=size, **kw)
        import math as _m
        self._m = _m
        self._acc, self._dim = acc, dim
        self._sz = size
        self._t = 0.0
        self._segs = self._build_segments()
        self._blips = [(18.0, 106.0), (48.8, 2.3), (-6.2, 106.8),
                       (35.7, 139.7), (-34.6, -58.4), (1.35, 103.8),
                       (25.0, 55.2), (40.7, -74.0)]
        bg0 = self["bg"]
        # fade <1 -> warna dilereng ke latar = tampak BACKGROUND/watermark
        self._disk = kw.pop("disk", False)
        self._cols = [_mixc(bg0, _mixc(dim, acc, i / float(self.SHADES - 1)),
                            fade) for i in range(self.SHADES)]
        self._blip = _mixc(bg0, "#00e0ff", fade)
        self.after(85, self._tick)

    def _build_segments(self):
        m = self._m
        segs = []
        for lat in (-60, -40, -20, 0, 20, 40, 60):
            la = m.radians(lat)
            r, y = m.cos(la), m.sin(la)
            segs.append([(r * m.cos(m.radians(a)), y,
                          r * m.sin(m.radians(a))) for a in range(0, 361, 12)])
        for lon in range(0, 180, 20):
            lo = m.radians(lon)
            segs.append([(m.sin(m.radians(a)) * m.cos(lo),
                          m.cos(m.radians(a)),
                          m.sin(m.radians(a)) * m.sin(lo))
                         for a in range(0, 361, 12)])
        return segs

    def _tick(self):
        self._t = (self._t + 1.0) % 9999.0
        self.delete("g")
        self._draw()
        self.after(85, self._tick)

    def _rot(self, p, cy, sy, cp, sp):
        x, y, z = p
        x2 = x * cy + z * sy
        z2 = -x * sy + z * cy
        y2 = y * cp - z2 * sp
        z3 = y * sp + z2 * cp
        return x2, y2, z3

    def _draw(self):
        m = self._m
        s = self._sz
        cx = cy = s / 2.0
        R = s / 2.0 - 2.0
        if self._disk:
            # cakram solid: globe UTUH, garis tabel tidak memotong
            self.create_oval(1, 1, s - 1, s - 1, fill="#0a0b14",
                             outline="#2e6e57", width=1, tags="g")
        yaw = self._t * 0.036
        tilt = -0.32
        cyw, syw = m.cos(yaw), m.sin(yaw)
        cp, sp = m.cos(tilt), m.sin(tilt)
        self.create_oval(cx - R - 1, cy - R - 1, cx + R + 1, cy + R + 1,
                         outline=self._dim, width=1, tags="g")
        for seg in self._segs:
            prev = None
            for pt in seg:
                x, y, z = self._rot(pt, cyw, syw, cp, sp)
                sx, sy = cx + x * R, cy - y * R
                if prev is not None:
                    d = (z + prev[2]) * 0.5
                    ci = int(max(0.0, (d + 1.0) * 0.5)
                             * (self.SHADES - 1) + 0.5)
                    self.create_line(prev[0], prev[1], sx, sy,
                                     fill=self._cols[ci], width=1, tags="g")
                prev = (sx, sy, z)
        for i, (la, lo) in enumerate(self._blips):
            lar, lor = m.radians(la), m.radians(lo + self._t * 2.1)
            x0 = m.cos(lar) * m.cos(lor)
            z0 = m.cos(lar) * m.sin(lor)
            y0 = m.sin(lar)
            x, y, z = self._rot((x0, y0, z0), cyw, syw, cp, sp)
            if z <= 0.05:
                continue
            px, py = cx + x * R, cy - y * R
            r = 1.0 + 0.7 * (0.55 + 0.45 * m.sin(self._t * 0.4 + i * 1.7))
            self.create_oval(px - r, py - r, px + r, py + r,
                             fill=self._blip, outline="", tags="g")


class EngineClient(object):
    """Klien HTTP engine lokal (cookie password didukung)."""

    _opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def __init__(self):
        self.cookie = ""

    def _get(self, port, path, timeout=2.5):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with self._opener.open(req, timeout=timeout) as r:
                sc = r.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0].strip()
                return r.read().decode("utf-8", "ignore"), r.code
        except urllib.error.HTTPError as e:
            if e.headers.get("Set-Cookie"):
                self.cookie = e.headers.get("Set-Cookie").split(";")[0].strip()
            return e.read().decode("utf-8", "ignore"), e.code
        except Exception:
            return "", 0

    def _post(self, port, path, obj, timeout=3.0):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (port, path),
            data=json.dumps(obj).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with self._opener.open(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore"), r.status
        except Exception:
            return "", 0

    def pair_switch(self, port, sym, on):
        """v4.34: toggle switch ON/OFF per pair di engine."""
        return self._post(port, "/api/pair_switch",
                          {"symbol": sym, "on": bool(on)})

    def pair_lot(self, port, sym, lot):
        """v4.37: set lot manual per pair (0 = AUTO)."""
        return self._post(port, "/api/pair_lot",
                          {"symbol": sym, "lot": float(lot)})

    def status(self, port):
        body, code = self._get(port, "/api/status")
        if code != 200:
            return {"error": "auth" if code == 401 else "offline"}
        try:
            return json.loads(body)
        except ValueError:
            return {"error": "offline"}

    def login(self, port, password):
        data = urllib.parse.urlencode({"password": password or ""}).encode()
        req = urllib.request.Request("http://127.0.0.1:%d/login" % port,
                                     data=data, method="POST")
        try:
            with self._opener.open(req, timeout=2.5) as r:
                sc = r.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0].strip()
                return True
        except Exception:
            return False

    def halt(self, port):
        req = urllib.request.Request("http://127.0.0.1:%d/api/halt" % port,
                                     data=b"", method="POST")
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with self._opener.open(req, timeout=2.5) as r:
                return r.code == 200
        except Exception:
            return False

    def update_engine(self, port):
        """v3.xx REFRESH: POST /api/update (self-update + restart)."""
        req = urllib.request.Request("http://127.0.0.1:%d/api/update" % port,
                                     data=b"", method="POST")
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with self._opener.open(req, timeout=60) as r:
                return r.code == 200
        except Exception:
            return False

# ---------------------------------------------------------------- jendela ---
class Dash(object):
    def __init__(self, ports=None, shot=None):
        self.ports = list(ports or PORTS)
        self.shot = shot
        self.client = EngineClient()
        self.active_port = None
        self.q = queue.Queue()
        self.stop = threading.Event()
        self.snap = {}
        self.need_auth = False
        self.sel_sym = None
        self._sw_map = {}   # v4.34: symbol -> bool switch
        self._lot_map = {}  # v4.37: symbol -> float lot manual
        self.tab = "ALL"
        self.tape_segs = []
        self.tape_x = 0
        self._build()
        self.thread = threading.Thread(target=self._poll_loop)
        self.thread.daemon = True
        self.thread.start()
        self.root.after(150, self._drain)
        self.root.after(80, self._tape_loop)
        self.root.after(700, self._pulse)
        if self.shot:
            self.root.after(9000, self._shot_now)

    # ---- widget kecil --------------------------------------------------
    def _chip(self, parent, title):
        f = tk.Frame(parent, bg=PAN2, highlightthickness=1,
                     highlightbackground=BD)
        l1 = tk.Label(f, text=title, bg=PAN2, fg=DIM, font=("Consolas", 7))
        l1.pack(anchor="w", padx=6, pady=(1, 0))
        l2 = tk.Label(f, text="-", bg=PAN2, fg=TX,
                      font=("Consolas", 9, "bold"))
        l2.pack(anchor="w", padx=6, pady=(0, 1))
        return f, l2

    def _ptitle(self, parent, left_txt, right_txt=None, rcol=DIM,
                accent=ACC):
        bar = tk.Frame(parent, bg=PAN)
        bar.pack(fill="x")
        tk.Frame(bar, bg=accent, width=3).pack(side="left", fill="y",
                                               padx=(6, 0), pady=3)
        tk.Label(bar, text=left_txt, bg=PAN, fg=TX,
                 font=("Consolas", 9, "bold"), anchor="w").pack(side="left",
                                                                padx=6)
        if right_txt:
            tk.Label(bar, text=right_txt, bg=PAN, fg=rcol,
                     font=("Consolas", 7, "bold")).pack(side="right", padx=6)
        return bar

    def _panel(self, parent):
        f = tk.Frame(parent, bg=PAN, highlightthickness=1,
                     highlightbackground=BD)
        f.pack(fill="x", pady=(0, 4))
        hc = self._mix(BD2, ACC, 0.45)
        for rx, ry, an in ((0, 0, "nw"), (1, 0, "ne"),
                           (0, 1, "sw"), (1, 1, "se")):
            for wd, ht in ((12, 2), (2, 12)):
                k = tk.Frame(f, bg=hc, width=wd, height=ht)
                k.place(in_=f, relx=rx, rely=ry, anchor=an)
        return f

    # ---- pembangunan jendela ------------------------------------------
    def _build(self):
        self.root = tk.Tk()
        self.root.title("RBT FX :: TRADING ALGO SYSTEM")
        self.root.configure(bg=BG)
        sh = self.root.winfo_screenheight()
        wh = 830 if sh >= 900 else max(560, sh - 46)
        self.root.geometry("1300x%d" % wh)
        self.root.minsize(1150, 560)
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Treeview", background=PAN, fieldbackground=PAN,
                     foreground=TX, rowheight=17, font=("Consolas", 9),
                     bordercolor=BD, relief="flat")
        st.configure("Treeview.Heading", background=PAN2, foreground=ACC,
                     font=("Consolas", 7, "bold"), bordercolor=BD,
                     relief="flat")
        st.map("Treeview", background=[("selected", PAN2)],
               foreground=[("selected", ACC)])

        # ================= TOPBAR =================
        top = tk.Frame(self.root, bg=PAN, highlightthickness=1,
                       highlightbackground=BD)
        top.pack(fill="x", padx=6, pady=(6, 2))
        cv = tk.Canvas(top, bg=PAN, width=52, height=30, highlightthickness=0)
        cv.pack(side="left", padx=(8, 4))
        cv.create_polygon(6, 20, 6, 10, 15, 15, 26, 3, 37, 15, 46, 10, 46, 20,
                          fill=AMBER, outline="#8a6a1c")
        cv.create_rectangle(6, 21, 46, 25, fill="#e6b84c", outline="#8a6a1c")
        cv.create_oval(24, 4, 28, 8, fill="#fff2b0", outline="")
        cv.create_rectangle(10, 22, 13, 25, fill=RED, outline="")
        cv.create_rectangle(24, 22, 27, 25, fill=CY, outline="")
        cv.create_rectangle(38, 22, 41, 25, fill=GRN, outline="")
        tk.Label(top, text="RBT FX", bg=PAN, fg=AMBER,
                 font=("Consolas", 15, "bold")).pack(side="left", padx=(2, 8))
        tk.Label(top, text="TRADING ALGO SYSTEM", bg=PAN, fg=TX,
                 font=("Consolas", 11, "bold"), highlightthickness=1,
                 highlightbackground=ACC, padx=8, pady=2).pack(side="left")
        self.ch = {}
        for key in ("PYTHON ENGINE", "MTS", "AKUN", "RISK MANAGER",
                    "DAILY PROTECTION", "WEEKEND GUARD"):
            f, val = self._chip(top, key)
            f.pack(side="left", padx=(8, 0), pady=3)
            self.ch[key] = val
        self.lb_clock = tk.Label(top, text="--:--:--", bg=PAN, fg=ACC,
                                 font=("Consolas", 15, "bold"))
        self.lb_clock.pack(side="right", padx=8)
        self.btn_halt = tk.Button(top, text="⚡ ON", bg="#0e2a16",
                                  fg=GRN, font=("Consolas", 9, "bold"),
                                  relief="flat", bd=0, padx=8, pady=3,
                                  activebackground="#12341f",
                                  activeforeground="#00ff9c", command=self._halt)
        self.btn_halt.pack(side="right", padx=4)
        self._upd_armed = 0.0

        # ================= TAPE =================
        self.cv_div = tk.Canvas(self.root, bg=BG, height=2,
                                highlightthickness=0)
        self.cv_div.pack(side="top", fill="x")
        self.cv_div.bind("<Configure>", self._paint_div)
        self.cv_tape = tk.Canvas(self.root, bg=TAPE_BG, height=18,
                                 highlightthickness=1,
                                 highlightbackground=BD2)
        self.cv_tape.pack(fill="x", padx=6)

        # ================= CARDS (8, kartu modern berwarna) =================
        self.card_defs = [("\u25c8", "BALANCE", AMBER),
                          ("\u25c9", "EQUITY", CY),
                          ("\u25b2", "DAILY PROFIT", GRN),
                          ("\u25bc", "DAILY LOSS", AMBER),
                          ("\u2248", "FLOATING TERBUKA", CY),
                          ("\u26a0", "DRAWDOWN", RED),
                          ("\u00a4", "KOMISI / FEE", VIO),
                          ("\u25a3", "OPEN POSITIONS", ACC)]
        self.cv_cards = tk.Canvas(self.root, bg=BG, height=64,
                                  highlightthickness=0)
        self.cv_cards.pack(fill="x", padx=6, pady=(4, 0))
        self.cv_cards.bind("<Configure>", lambda e: self._draw_cards())
        self._card_vals = []
        self.eq_hist = []

        # ================= STATUSBAR =================
        bot = tk.Frame(self.root, bg=PAN, highlightthickness=1,
                       highlightbackground=BD)
        bot.pack(fill="x", padx=6, pady=(4, 6))
        self.cv_led = tk.Canvas(bot, bg=PAN, width=18, height=18,
                                highlightthickness=0)
        self.cv_led.pack(side="left", padx=(8, 2), pady=4)
        self.cv_led.create_oval(3, 3, 15, 15,
                                fill=self._mix(PAN, AMBER, 0.28),
                                outline="", tags="ledh")
        self.cv_led.create_oval(6, 6, 12, 12, fill=AMBER, outline=AMBER,
                                tags="led")
        self.lb_status = tk.Label(bot, text="BOOTING SYSTEM...", bg=PAN,
                                  fg=AMBER, font=("Consolas", 10, "bold"),
                                  anchor="w")
        self.lb_status.pack(side="left", padx=4)
        self.lb_info = tk.Label(bot, text="", bg=PAN, fg=DIM2,
                                font=("Consolas", 7), anchor="e")
        self.lb_info.pack(side="right", padx=8)
        self.btn_auth = tk.Button(bot, text="PASSWORD", bg=PAN2, fg=AMBER,
                                  font=("Consolas", 7, "bold"),
                                  relief="flat", padx=8,
                                  command=lambda: None)
        self.ent_pw = tk.Entry(bot, show="*", width=14, bg=PAN2, fg=TX,
                               font=("Consolas", 8), insertbackground=TX,
                               relief="flat")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # ================= AREA UTAMA =================
        mid = tk.Frame(self.root, bg=BG)
        mid.pack(fill="both", expand=True, padx=6, pady=(4, 0))
        left = tk.Frame(mid, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(mid, bg=BG, width=318)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        # ---- 1. SCANNER ----
        p = self._panel(left)
        self._ptitle(p, "\u2315 MULTI-PAIR SCANNER",
                     "\u25b2 AUTO SCAN \u2699", ACC)
        tabs = tk.Frame(p, bg=PAN)
        tabs.pack(fill="x", padx=6, pady=(2, 2))
        self.tab_btns = {}
        for name in ("ALL", "FOREX", "GOLD/SILVER", "CRYPTO", "INDEX",
                     "COMMODITY"):
            b = tk.Button(tabs, text=name, bg=PAN2, fg=DIM,
                          font=("Consolas", 7, "bold"), relief="flat", bd=0,
                          padx=8, pady=2, activebackground=ACC,
                          activeforeground="#02150c",
                          command=lambda n=name: self._set_tab(n))
            b.pack(side="left", padx=(0, 4))
            self.tab_btns[name] = b
        self._paint_tabs()
        # v3.57: kolom pengisi (stretch) di akhir -> STATUS nempel TREND
        cols = ("no", "sym", "px", "spr", "reg", "sig", "sco", "tre", "st",
                "sw", "lot", "fill")
        heads = [("no", "#", 24), ("sym", "SYMBOL", 86), ("px", "PRICE", 90),
                 ("spr", "SPREAD", 56), ("reg", "REGIME", 86),
                 ("sig", "SIGNAL", 60), ("sco", "SCORE", 52),
                 ("tre", "TREND", 50), ("st", "STATUS", 90),
                 ("sw", "SW", 40), ("lot", "LOT", 50), ("fill", "", 24)]
        self.tv = ttk.Treeview(p, columns=cols, show="headings", height=4)
        for c, t, w in heads:
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, anchor="w", stretch=(c == "fill"))
        for tag, col in (("TRADING", AMBER), ("READY", GRN), ("HOLD", CY),
                         ("SNIPER_WAIT", VIO), ("BLOCKED", TX),
                         ("WAIT", TX)):
            self.tv.tag_configure(tag, foreground=col)
        self.tv.tag_configure("r0", background=PAN)
        self.tv.tag_configure("r1", background="#081b11")
        self.tv.pack(fill="x", padx=6, pady=(0, 4))
        self.tv.bind("<<TreeviewSelect>>", self._on_select)
        self.tv.bind("<Button-1>", self._tv_click)   # v4.34: toggle SW
        # v3.87 (user): globe berputar DIPINDAH ke dalam ring gauge
        # (dulu overlay tabel) -- lihat _draw_gauge

        # ---- 2. CONFLUENCE + GAUGE ----
        p = self._panel(left)
        bar = self._ptitle(p, "\u2297 STRATEGY CONFLUENCE", None)
        self.lb_cfsym = tk.Label(bar, text="( - )", bg=PAN, fg=TX,
                                 font=("Consolas", 9, "bold"))
        self.lb_cfsym.pack(side="right", padx=6)
        self.lb_age = tk.Label(bar, text="", bg=PAN, fg=DIM,
                               font=("Consolas", 9, "bold"))
        self.lb_age.pack(side="right", padx=6)
        crow = tk.Frame(p, bg=PAN)
        crow.pack(fill="x", padx=6, pady=(0, 2))
        self.cv_gauge = tk.Canvas(crow, bg=PAN, width=150, height=150,
                                  highlightthickness=0)
        self.cv_gauge.pack(side="left", padx=(6, 8))
        cinfo = tk.Frame(crow, bg=PAN)
        cinfo.pack(side="left", fill="both", expand=True)
        vrow = tk.Frame(cinfo, bg=PAN)
        vrow.pack(fill="x")
        self.lb_verdict = tk.Label(vrow, text="WAIT", bg=PAN2, fg=AMBER,
                                   font=("Consolas", 12, "bold"),
                                   padx=9, pady=2, highlightthickness=1,
                                   highlightbackground=DIM2)
        self.lb_verdict.pack(side="left")
        self.lb_score = tk.Label(vrow, text="0%", bg=PAN, fg=DIM2,
                                 font=("Consolas", 12, "bold"))
        self.lb_score.pack(side="left", padx=(14, 0))
        self.lb_valid = tk.Label(vrow, text="[ STAND BY ]", bg=PAN, fg=DIM,
                                 font=("Consolas", 9, "bold"))
        self.lb_valid.pack(side="left", padx=(14, 0))
        self.cv_bars = tk.Canvas(cinfo, bg=PAN, height=66, highlightthickness=0)
        self.cv_bars.pack(fill="x", pady=(2, 0))
        # v3.91: baris ">> sniper: ..." DIHAPUS (mengganggu, permintaan
        # user); alasan blokir tetap ada di panel status & API.
        self.lb_why = tk.Label(p, text="")

        # ---- 3. POSITIONS ----
        p = self._panel(left)
        self.lb_post = tk.Label(p, text="\u21c4 ACTIVE POSITIONS (0)", bg=PAN,
                                fg=ACC, font=("Consolas", 9, "bold"),
                                anchor="w")
        self.lb_post.pack(fill="x", padx=6)
        pcols = ("no", "sym", "typ", "lot", "ent", "sl", "tp", "dash",
                 "px", "pl", "r", "stt")
        pheads = [("no", "#", 24), ("sym", "SYMBOL", 84), ("typ", "TYPE", 46),
                  ("lot", "LOT", 44), ("ent", "ENTRY", 72),
                  ("sl", "SL", 64), ("tp", "TP", 64), ("dash", "", 22),
                  ("px", "PRICE", 70), ("pl", "P/L", 62), ("r", "R", 40),
                  ("stt", "STATUS", 62)]
        self.tvp = ttk.Treeview(p, columns=pcols, show="headings", height=2)
        for c, t, w in pheads:
            self.tvp.heading(c, text=t)
            self.tvp.column(c, width=w, anchor="w", stretch=False)
        self.tvp.tag_configure("buy", foreground=GRN)
        self.tvp.tag_configure("sell", foreground=RED)
        self.tvp.tag_configure("r0", background=PAN)
        self.tvp.tag_configure("r1", background="#081b11")
        self.tvp.pack(fill="x", padx=6, pady=(0, 4))

        # ---- 4. CHART (besar, mengisi sisa ruang kiri) ----
        p = tk.Frame(left, bg=PAN, highlightthickness=1,
                     highlightbackground=BD)
        p.pack(fill="both", expand=True, pady=(0, 4))
        bar = tk.Frame(p, bg=PAN)
        bar.pack(fill="x")
        self.lb_chsym = tk.Label(bar, text="-", bg=PAN, fg=TX,
                                 font=("Consolas", 10, "bold"))
        self.lb_chsym.pack(side="left", padx=6)
        tk.Label(bar, text="M15", bg=PAN2, fg=DIM,
                 font=("Consolas", 7, "bold"), padx=4).pack(side="left")
        self.lb_chpct = tk.Label(bar, text="", bg=PAN, fg=DIM,
                                 font=("Consolas", 9, "bold"))
        self.lb_chpct.pack(side="right", padx=6)
        self.lb_chpx = tk.Label(bar, text="-", bg=PAN, fg=ACC,
                                font=("Consolas", 10, "bold"))
        self.lb_chpx.pack(side="right")
        self.cv_chart = tk.Canvas(p, bg=PAN2, height=60,
                                  highlightthickness=0)
        self.cv_chart.pack(fill="both", expand=True, padx=6, pady=(2, 4))
        self.cv_chart.bind("<Motion>", self._cmove)
        self.cv_chart.bind("<Leave>", self._cout)

        # ================= KOLOM KANAN =================
        # EXECUTION LOG (di posisi ex-GLOBAL FLOW, mengisi ruang)
        p = tk.Frame(right, bg=PAN, highlightthickness=1,
                     highlightbackground=BD)
        p.pack(fill="both", expand=True, pady=(0, 4))
        self._ptitle(p, "\u2328 EXECUTION LOG :: PYTHON ENGINE",
                     "\u25b2 REAL-TIME", ACC)
        self.txt = tk.Text(p, bg=TAPE_BG, fg=TX, font=("Consolas", 8),
                           height=6, relief="flat", state="disabled",
                           wrap="word", highlightthickness=0)
        self.txt.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        for tag, col in LOG_TAG_COL.items():
            self.txt.tag_configure(tag, foreground=col)
        self.txt.tag_configure("ts", foreground=DIM2)

        # [ SESSIONS ]
        p = self._panel(right)
        tk.Label(p, text="[ SESSIONS ]", bg=PAN, fg=ACC,
                 font=("Consolas", 9, "bold"), anchor="w").pack(fill="x",
                                                                padx=6)
        self.lb_sess = {}
        self.lb_sess_nm = {}
        for k in ("SYDNEY", "TOKYO", "LONDON", "NEW YORK"):
            row = tk.Frame(p, bg=PAN)
            row.pack(fill="x", padx=6)
            nm = tk.Label(row, text="\u25cf " + k, bg=PAN, fg=DIM,
                          font=("Consolas", 8))
            nm.pack(side="left")
            self.lb_sess_nm[k] = nm
            lb = tk.Label(row, text="-", bg=PAN, fg=DIM,
                          font=("Consolas", 8))
            lb.pack(side="right")
            self.lb_sess[k] = lb

        # [ MARKET SESSION ]
        p = self._panel(right)
        tk.Label(p, text="[ MARKET SESSION ]", bg=PAN, fg=ACC,
                 font=("Consolas", 9, "bold"), anchor="w").pack(fill="x",
                                                                padx=6)
        self.ms_names, self.ms_bars = [], []
        for k in ("SYDNEY", "TOKYO", "LONDON", "NEW YORK"):
            row = tk.Frame(p, bg=PAN)
            row.pack(fill="x", padx=6)
            tk.Label(row, text=k, bg=PAN, fg=TX,
                     font=("Consolas", 7, "bold"), width=9,
                     anchor="w").pack(side="left")
            stt = tk.Label(row, text="-", bg=PAN, fg=DIM,
                           font=("Consolas", 7))
            stt.pack(side="right")
            self.ms_names.append(stt)
        self.cv_ms = tk.Canvas(p, bg=PAN, height=48, highlightthickness=0)
        self.cv_ms.pack(fill="x", padx=6, pady=(0, 4))

        # MODULES
        p = self._panel(right)
        self.lb_post2 = tk.Label(p, text="\u25a3 MODULES", bg=PAN, fg=ACC,
                                 font=("Consolas", 9, "bold"), anchor="w")
        self.lb_post2.pack(fill="x", padx=6)
        grid = tk.Frame(p, bg=PAN)
        grid.pack(fill="x", padx=4, pady=(0, 4))
        self.lb_mods = {}
        for i, (ic, nm) in enumerate([("\u25c8", "SCANNER"),
                                      ("\u2316", "STRATEGY"),
                                      ("\u25b2", "RISK MANAGER"),
                                      ("\u26a1", "TRADE ENGINE"),
                                      ("\u25ce", "TRAILING SYSTEM"),
                                      ("\u270e", "NEWS FILTER")]):
            f = tk.Frame(grid, bg=PAN2, highlightthickness=1,
                         highlightbackground=BD)
            f.grid(row=i // 3, column=i % 3, padx=2, pady=1, sticky="we")
            grid.grid_columnconfigure(i % 3, weight=1)
            tk.Label(f, text=ic + " " + nm, bg=PAN2, fg=TX,
                     font=("Consolas", 7, "bold")).pack(anchor="w", padx=4,
                                                        pady=(2, 0))
            lb = tk.Label(f, text="[off]", bg=PAN2, fg=DIM2,
                          font=("Consolas", 7, "bold"), anchor="w")
            lb.pack(anchor="w", padx=4, pady=(0, 2))
            self.lb_mods[nm] = lb

        # INFO AKUN
        p = self._panel(right)
        tk.Label(p, text="[ ACCOUNT ]", bg=PAN, fg=ACC,
                 font=("Consolas", 9, "bold"), anchor="w").pack(fill="x",
                                                                padx=6)
        self.kv = {}
        for k in ("MODE", "SERVER", "LOGIN", "LEVERAGE", "UPTIME", "PING",
                  "LOOP", "PAIRS"):
            row = tk.Frame(p, bg=PAN)
            row.pack(fill="x", padx=6)
            tk.Label(row, text=k, bg=PAN, fg=DIM, font=("Consolas", 7),
                     anchor="w").pack(side="left")
            lb = tk.Label(row, text="-", bg=PAN, fg=TX, font=("Consolas", 7),
                          anchor="e")
            lb.pack(side="right")
            self.kv[k] = lb


    # ---- kartu modern: rounded rect + tint warna + medali ikon --------
    @staticmethod
    def _mix(h1, h2, t):
        a = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t)
                                       for i in range(3))

    def _rr(self, cv, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0 + r, x1, y1 - r,
               x1 - r, y1, x0 + r, y1, x0, y1 - r, x0, y0 + r]
        return cv.create_polygon(pts, smooth=True, **kw)

    def _draw_cards(self):
        cv = self.cv_cards
        cv.delete("all")
        vals = self._card_vals or []
        cv.update_idletasks()
        W = cv.winfo_width() or 1300
        H = 64
        n = len(self.card_defs)
        gap = 6
        cw = (W - gap * (n - 1)) / float(n)
        base = "#04120b"
        for i, (ic, title, acc) in enumerate(self.card_defs):
            x = i * (cw + gap)
            self._rr(cv, x + 2, 4, x + cw + 1, H - 1, 8,
                     fill="#010603", outline="")
            self._rr(cv, x, 2, x + cw, H - 4, 8,
                     fill=self._mix(base, acc, 0.10),
                     outline=self._mix(base, acc, 0.45))
            self._rr(cv, x + 8, 3, x + cw - 8, 4, 1,
                     fill=self._mix(base, acc, 0.55), outline="")
            ds = 17
            self._rr(cv, x + 5, 6, x + 5 + ds, 6 + ds, 5,
                     fill=self._mix(base, acc, 0.30), outline="")
            cv.create_text(x + 5 + ds / 2.0, 6 + ds / 2.0 + 1, text=ic,
                           fill=acc, font=("Consolas", 9, "bold"))
            cv.create_text(x + 5 + ds + 6, 14, text=title, anchor="w",
                           fill=self._mix(TX, DIM, 0.45),
                           font=("Consolas", 7, "bold"))
            if i < len(vals):
                val, vcol, sub = vals[i]
                # nilai: ukur lebar piksel asli -> turunkan font / pangkas
                avail = cw - 22
                f12 = tkfont.Font(family="Consolas", size=10, weight="bold")
                f10 = tkfont.Font(family="Consolas", size=8, weight="bold")
                fnt, txt = f12, val
                if f12.measure(val) > avail:
                    fnt, txt = f10, val
                    # pangkas NET -1 char per langkah (anti infinite loop)
                    while f10.measure(txt) > avail and len(txt) > 3:
                        txt = txt[:-3].rstrip() + ".."
                cv.create_text(x + 10, 30, text=txt, anchor="w", fill=vcol,
                               font=fnt)
                if sub:
                    f7 = tkfont.Font(family="Consolas", size=7)
                    st = sub
                    while f7.measure(st) > avail and len(st) > 3:
                        st = st[:-3].rstrip() + ".."
                    cv.create_text(x + 10, 44, text=st, anchor="w",
                                   fill=self._mix(TX, DIM2, 0.55),
                                   font=("Consolas", 7))
            if title == "EQUITY" and len(self.eq_hist) >= 2:
                hh = self.eq_hist
                lo0, hi0 = min(hh), max(hh)
                if hi0 - lo0 < 1e-9:
                    lo0, hi0 = lo0 - 1, hi0 + 1
                pts = []
                for k0, v0 in enumerate(hh):
                    pts += [x + 12 + (cw - 24) * k0 / (len(hh) - 1.0),
                            54 - 10 * (v0 - lo0) / (hi0 - lo0)]
                cv.create_line(*pts, fill=CY, width=1)
            self._rr(cv, x + 10, H - 11, x + cw - 10, H - 8, 2,
                     fill=self._mix(base, acc, 0.60), outline="")

    def _paint_tabs(self):
        for n, b in self.tab_btns.items():
            if n == self.tab:
                b.configure(bg=ACC, fg="#02150c",
                            font=("Consolas", 8, "bold"))
            else:
                b.configure(bg=PAN2, fg=DIM, font=("Consolas", 8))

    def _set_tab(self, n):
        self.tab = n
        self._paint_tabs()
        if self.snap:
            self._apply(self.snap)

    # ---- interaksi ------------------------------------------------------
    def _ask_pw(self):
        self.ent_pw.pack_forget()
        self.btn_auth.pack_forget()
        self.ent_pw.pack(side="right", padx=4)
        self.btn_auth.pack(side="right", padx=4)

        def _try(_e=None):
            if self.client.login(self.active_port or self.ports[0],
                                 self.ent_pw.get()):
                self.ent_pw.delete(0, "end")
                self.ent_pw.pack_forget()
                self.btn_auth.pack_forget()
                self._kick()
            else:
                self.lb_status.configure(text="PASSWORD SALAH", fg=RED)

        self.btn_auth.configure(command=_try)
        self.ent_pw.bind("<Return>", _try)

    def _halt(self):
        threading.Thread(target=self._halt_bg, daemon=True).start()

    def _halt_bg(self):
        self.client.halt(self.active_port or self.ports[0])
        self._kick()

    def _kick(self):
        self.q.put(("__kick__", None))


    def _on_select(self, _e=None):
        sel = self.tv.selection()
        if sel:
            self.sel_sym = sel[0]
            if self.snap:
                self._apply(self.snap)

    def _tv_click(self, ev):
        """v4.34: klik kolom SW -> toggle ON/OFF pair di engine."""
        try:
            if self.tv.identify_region(ev.x, ev.y) != "cell":
                return
            col = self.tv.identify_column(ev.x)
            iid = self.tv.identify_row(ev.y)
        except Exception:
            return
        if col == "#10" and iid:
            cur = self._sw_map.get(iid, False)
            self._sw_map[iid] = not cur
            try:
                self.tv.set(iid, "sw", "ON" if not cur else "OFF")
            except Exception:
                pass
            threading.Thread(target=self._sw_bg, args=(iid, not cur),
                             daemon=True).start()
        elif col == "#11" and iid:
            # v4.37 (user): kolom LOT -> dialog isi lot manual
            cur = float(self._lot_map.get(iid, 0) or 0)
            v = simpledialog.askstring(
                "LOT " + str(iid),
                "Isi lot MANUAL untuk %s (0/kosong = AUTO):" % str(iid),
                initialvalue=("%.2f" % cur) if cur else "0",
                parent=self.root)
            if v is None:
                return
            try:
                fv = float(str(v).strip().replace(",", "."))
            except ValueError:
                return
            self._lot_map[iid] = fv
            try:
                self.tv.set(iid, "lot", ("%g" % fv) if fv > 0 else "AUTO")
            except Exception:
                pass
            threading.Thread(target=self._lot_bg, args=(iid, fv),
                             daemon=True).start()

    def _lot_bg(self, sym, lot):
        for p in self._post_ports():
            try:
                body, code = self.client.pair_lot(p, sym, lot)
                if code == 200:
                    return
            except Exception:
                pass

    def _post_ports(self):
        """v4.38: port engine UTAMA dulu (active_port), sisanya cadangan."""
        pts = ([self.active_port] if self.active_port else []) + \
              [p for p in self.ports if p != self.active_port]
        return pts

    def _sw_bg(self, sym, on):
        for p in self._post_ports():
            try:
                body, code = self.client.pair_switch(p, sym, on)
                if code == 200:
                    return
            except Exception:
                pass


    def _close(self):
        self.stop.set()
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---- polling --------------------------------------------------------
    def _poll_loop(self):
        while not self.stop.is_set():
            data = None
            for port in self.ports:
                if self.stop.is_set():
                    return
                cl = EngineClient()
                cl.cookie = self.client.cookie
                body, code = cl._get(port, "/api/status", timeout=2.5)
                if code == 200:
                    try:
                        data = json.loads(body)
                        data["_port"] = port
                        self.client.cookie = cl.cookie
                        self.active_port = port
                    except ValueError:
                        data = {"error": "offline"}
                    break
                if code == 401:
                    data = {"error": "auth", "_port": port}
                    self.client.cookie = cl.cookie
                    break
            if data is None:
                data = {"error": "offline"}
            self.q.put(("data", data))
            self.stop.wait(2.0)

    def _drain(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "data":
                    if isinstance(data, dict) and "error" not in data:
                        self.snap = data
                        self.need_auth = False
                        self._apply(data)
                    elif isinstance(data, dict) and data.get("error") == "auth":
                        if not self.need_auth:
                            self.need_auth = True
                            self.lb_status.configure(
                                text="AKSES DITOLAK \u2014 ISI PASSWORD LALU "
                                     "TEKAN [PASSWORD]", fg=RED)
                            self._led(RED)
                            self._ask_pw()
                    else:
                        self._offline()
                elif kind == "__kick__":
                    pass
        except queue.Empty:
            pass
        self.root.after(150, self._drain)

    def _led(self, col):
        self._led_col = col
        self.cv_led.itemconfigure("ledh",
                                  fill=self._mix(PAN, col, 0.28))
        self.cv_led.itemconfigure("led", fill=col, outline=col)

    def _pulse(self):
        col = getattr(self, "_led_col", AMBER)
        self._ph = not getattr(self, "_ph", False)
        self.cv_led.itemconfigure(
            "ledh", fill=self._mix(PAN, col, 0.36 if self._ph else 0.16))
        self.root.after(700, self._pulse)

    def _paint_div(self, _e=None):
        cv = self.cv_div
        cv.delete("all")
        w = cv.winfo_width() or 1300
        for i in range(0, w, 4):
            cv.create_rectangle(i, 0, i + 5, 2,
                                fill=self._mix(AMBER, ACC,
                                               min(1.0, i / float(max(w, 1)))),
                                outline="")

    def _offline(self):
        self._led(RED)
        self.lb_status.configure(
            text="ENGINE OFFLINE \u2014 JALANKAN MULAI_SEMUA.BAT DULU", fg=RED)

    # ---- penerapan data (port tick() web) --------------------------------
    def _apply(self, s):
        # v3.67 ANTI DATA BEKU (spt Qt): snapshot > 120 dtk -> kartu
        # harian dikosongkan + chip engine merah
        import time as _tm
        _st = s.get("ts") or ""
        try:
            _age = _tm.time() - _tm.mktime(
                _tm.strptime(_st, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            _age = 0.0
        beku = _age > 120.0
        acc = s.get("account") or {}
        m = s.get("metrics") or {}
        rsk = s.get("risk") or {}
        ccy = m.get("account_currency") or "USD"
        mode = s.get("mode", "-")
        conn = s.get("connected")

        self.lb_clock.configure(text=((s.get("ts_wib")
                                      or s.get("ts")
                                      or "--:--:--")[11:])
                                + " WIB")
        _te = s.get("ts_epoch")
        if _te:
            _age = max(0, int(time.time() - float(_te)))
            _ac = GRN if _age <= 15 else (AMBER if _age <= 60 else RED)
            _at = "DATA BARU" if _age <= 15 else ("DATA %ds" % _age if _age <= 60 else "DATA LAMA %ds" % _age)
            self.lb_age.configure(text=_at, fg=_ac)

        self.ch["PYTHON ENGINE"].configure(
            text="\u25cf ONLINE v%s" % s.get("version", "-"), fg=GRN)
        self.ch["MTS"].configure(
            text="\u25cf CONNECTED" if conn else "\u25cf SIMULASI",
            fg=GRN if conn else AMBER)
        self.ch["MTS"].master.winfo_children()[0].configure(
            text=s.get("terminal", "MT5"))   # v3.87 (user): tanpa server
        self.ch["AKUN"].configure(
            text="%s #%s" % (mode, acc.get("login", "-")), fg=TX)
        if rsk.get("halted"):
            self.ch["RISK MANAGER"].configure(text="\u25cf HALTED", fg=RED)
        elif rsk.get("pause_until", 0) > 0:
            self.ch["RISK MANAGER"].configure(text="\u25cf PAUSED", fg=AMBER)
        else:
            self.ch["RISK MANAGER"].configure(text="\u25cf ACTIVE", fg=GRN)
        self.ch["DAILY PROTECTION"].configure(
            text="\u25cf ACTIVE" if not rsk.get("halted")
                 else "\u25cf LOSS LIMIT",
            fg=GRN if not rsk.get("halted") else RED)
        self.ch["WEEKEND GUARD"].configure(text="\u25cf ACTIVE", fg=GRN)

        # tape segments
        self.tape_segs = []
        for r in s.get("scanner") or []:
            pc = float(r.get("trend_pct", 0) or 0)
            self.tape_segs.append((
                r.get("symbol"), fmt(r.get("price"), r.get("digits", 2)),
                "\u25b2" if pc >= 0 else "\u25bc", "%.2f%%" % abs(pc),
                GRN if pc >= 0 else RED))

        # cards (8, persis web)
        rp = lambda v: fmt(abs(float(v or 0)), 0 if abs(float(v or 0)) >= 1000 else 2)
        self.eq_hist.append(float(m.get("equity", 0) or 0))
        del self.eq_hist[:-60]
        eqb = float(m.get("equity", 0)) - float(m.get("balance", 0))
        pctb = abs(eqb) / float(m.get("balance") or 1) * 100
        npos = len(s.get("positions") or [])
        _lmt = float(m.get("daily_loss_limit", 0) or 0)
        _luse = (min(100.0, float(m.get("daily_loss", 0) or 0)
                     / _lmt * 100.0) if _lmt > 0 else 0.0)
        card_vals = [
            (mn(m.get("balance"), ccy), AMBER, "SALDO AKUN"),
            (mn(m.get("equity"), ccy), col_for(eqb),
             ("+" if eqb >= 0 else "-") + fmt(pctb, 2) + "% vs saldo"),
            (("+" if float(m.get("daily_profit", 0)) >= 0 else "-")
             + rp(m.get("daily_profit")) + " " + ccy,
             col_for(m.get("daily_profit")),
             "dari %d close profit/TP" % int(m.get("wins", 0) or 0)),
            ("-" + rp(m.get("daily_loss_abs")) + " " + ccy +
             " (" + fmt(m.get("daily_loss"), 2) + "%)", AMBER,
             "dari %d close loss/SL | limit %s%% terpakai" % (
                 int(m.get("losses", 0) or 0), fmt(_luse, 0))),
            (("+" if float(m.get("floating_open", 0)) >= 0 else "-")
             + rp(m.get("floating_open")) + " " + ccy,
             col_for(m.get("floating_open")),
             str(npos) + " posisi jalan (bukan daily)"),
            ("-" + fmt(m.get("drawdown_pct"), 2) + "%", RED,
             "Peak: " + mn(m.get("day_peak"), ccy)),
            ("-" + rp(m.get("commission_today")) + " " + ccy, TX,
             ("Akun KOMISI - fee asli broker"
              if m.get("comm_mode") == "KOMISI" else
              ("Akun SPREAD - tanpa komisi"
               if m.get("comm_mode") == "SPREAD" else "menunggu deal..."))),
            (str(npos) + " / 5", CY,
             ("+" if float(m.get("floating", 0)) >= 0 else "-")
             + rp(m.get("floating")) + " " + ccy + " Float"),
        ]
        if beku:
            for _i in (2, 3, 5, 6):
                card_vals[_i] = ("-", RED, "DATA BEKU %s - engine offline, "
                                 "jalankan bat" % (_st[11:16] or "--:--"))
        self._card_vals = card_vals
        self._draw_cards()

        # scanner table
        rows = s.get("scanner") or []
        self.tv.delete(*self.tv.get_children())
        i = 0
        for r in rows:
            _tabc = _TAB_CAT.get(self.tab, self.tab)
            if self.tab != "ALL" and cat_of(r.get("symbol")) != _tabc:
                continue
            i += 1
            sig = r.get("signal", "-") if float(r.get("score", 0) or 0) >= 70 \
                else "-"
            tb = int(round(float(r.get("trend_pct", 0) or 0)))
            stag = r.get("status", "WAIT")
            stag = "WAIT" if stag == "SNIPER_WAIT" else stag
            if stag not in ("TRADING", "READY", "HOLD", "BLOCKED"):
                stag = "WAIT"
            sc = float(r.get("score", 0) or 0)
            sco = "%.0f%%" % sc
            reg = (r.get("regime") or "-").split(" ")[0]
            swv = "ON" if r.get("sw") else "OFF"
            self._sw_map[r.get("symbol")] = bool(r.get("sw"))
            ulot = float(r.get("lot") or 0.0)
            self._lot_map[r.get("symbol")] = ulot
            lotv = ("%g" % ulot) if ulot > 0 else "AUTO"
            self.tv.insert("", "end", iid=r.get("symbol"), values=(
                "%02d" % i, r.get("symbol"), fmt(r.get("price"),
                                                 r.get("digits", 2)),
                r.get("spread"), reg, sig, sco, str(tb) + "%", stag, swv,
                lotv),
                tags=(stag, "r1" if i % 2 else "r0"))
        if self.sel_sym and self.tv.exists(self.sel_sym):
            self.tv.selection_set(self.sel_sym)

        # confluence + gauge + chart
        self._apply_cf(s)

        # positions
        self.tvp.delete(*self.tvp.get_children())
        for j, p in enumerate(s.get("positions") or []):
            digits = p.get("digits") or 2
            self.tvp.insert("", "end", values=(
                "%02d" % (j + 1), p.get("symbol"), p.get("type"),
                "%.2f" % float(p.get("lot", 0) or 0),
                fmt(p.get("entry"), digits),
                fmt(p.get("sl"), digits) if p.get("sl") else "-",
                fmt(p.get("tp"), digits) if p.get("tp") else "-",
                "", fmt(p.get("price"), digits),
                ("+" if float(p.get("pl", 0) or 0) >= 0 else "")
                + fmt(p.get("pl")),
                "-", "Trailing" if p.get("trailing") else "Open"),
                tags=(("buy",) if float(p.get("pl", 0) or 0) >= 0
                      else ("sell",)) + ("r1" if j % 2 else "r0",))
        self.lb_post.configure(text="\u21c4 ACTIVE POSITIONS (%d)" % npos)

        # log (terbaru di atas + prompt, persis web)
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for ln in list(s.get("log") or [])[::-1]:
            tag = (ln.get("tag") or "INFO").upper()
            self.txt.insert("end", "[%s] " % ln.get("ts", ""), ("ts",))
            self.txt.insert("end", "[ %s ] " % tag, (tag,))
            self.txt.insert("end", "%s\n" % ln.get("msg", ""))
        self.txt.insert("end", "root@rbt-fx:~$ \u258a\n")
        self.txt.configure(state="disabled")

        # sessions + market session
        try:
            ts = s.get("ts", "")
            hh, mm = int(ts[11:13]), int(ts[14:16])
        except (ValueError, IndexError):
            hh, mm = time.gmtime().tm_hour, time.gmtime().tm_min
        hr = hh + mm / 60.0
        for k, lb in self.lb_sess.items():
            v = (s.get("sessions") or {}).get(k) or {}
            op = v.get("open", False)
            lb.configure(text="%02d:%02d %s" % (hh, mm,
                                                "(Open)" if op else "(Closed)"),
                         fg=GRN if op else DIM)
            self.lb_sess_nm[k].configure(fg=GRN if op else DIM)
        self.cv_ms.delete("all")
        y0 = 3
        for k, stt in zip(("SYDNEY", "TOKYO", "LONDON", "NEW YORK"),
                          self.ms_names):
            a, z = SESSIONS_HRS[k]
            ln = (z - a) if z >= a else (z + 24 - a)
            cur = (hr - a) if hr >= a else (hr + 24 - a)
            f = cur / float(ln) if 0 <= cur < ln else 0.0
            opn = 0 < cur < ln or (cur == 0 and ln > 0)
            stt.configure(text="Open" if f > 0 else "Closed",
                          fg=GRN if f > 0 else DIM)
            w = self.cv_ms.winfo_width() or 300
            self.cv_ms.create_text(2, y0 + 5, text="", anchor="w",
                                   font=("Consolas", 7))
            self._rr(self.cv_ms, 0, y0, w, y0 + 6, 3, fill=PAN2,
                     outline=DIM2)
            if f > 0:
                self._rr(self.cv_ms, 0, y0, max(6, w * f), y0 + 6, 3,
                         fill=GRN, outline=GRN)
            y0 += 12

        # modules
        mods = s.get("modules") or {}
        keymap = {"SCANNER": "scanner", "STRATEGY": "strategy",
                  "RISK MANAGER": "risk", "TRADE ENGINE": "trade",
                  "TRAILING SYSTEM": "trailing", "NEWS FILTER": "news"}
        for nm, lb in self.lb_mods.items():
            on = bool(mods.get(keymap.get(nm, nm.lower()), False))
            lb.configure(text="[ON]" if on else "[OFF]",
                         fg=GRN if on else DIM2)

        # account kv + info
        up = int(s.get("uptime_min", 0) or 0)
        upt = ((str(up // 1440) + "D ") if up >= 1440 else "") + \
              "%02d:%02d" % (up // 60 % 24, up % 60)
        self.kv["MODE"].configure(text=mode)
        self.kv["SERVER"].configure(text=acc.get("server", "-"))
        self.kv["LOGIN"].configure(text=str(acc.get("login", "-")))
        self.kv["LEVERAGE"].configure(text="1:" + str(acc.get("leverage", "-")))
        self.kv["UPTIME"].configure(text=upt)
        self.kv["PING"].configure(text=str(s.get("ping_ms", "-")) + " ms")
        self.kv["LOOP"].configure(text=str(s.get("loop_ms", "-")) + " ms")
        self.kv["PAIRS"].configure(text=str(len(rows)))
        self.lb_info.configure(
            text="UPTIME %s | PING %s ms | LOOP %s ms | %d PAIRS | v%s" % (
                upt, s.get("ping_ms", "-"), s.get("loop_ms", "-"),
                len(rows), s.get("version", "-")))

        # statusline + led
        if rsk.get("halted"):
            msg, col = "TRADING HALTED \u2014 DAILY LOSS LIMIT ACTIVE", RED
        elif rsk.get("manual_halt"):
            msg, col = "MANUAL HALT \u2014 NO NEW ORDERS", RED
        elif conn:
            msg, col = "ALL SYSTEMS OPERATIONAL [%s]" % mode, GRN
        else:
            msg, col = "LINK DOWN - RETRYING...", AMBER
        self.lb_status.configure(text=msg, fg=col)
        self._led(col)
        # v3.95: label tombol = STATUS (bukan aksi): jalan=ON, halt=OFF
        halted = bool(rsk.get("manual_halt"))
        self.btn_halt.configure(
            text="⏸ OFF" if halted else "⚡ ON",
            fg=RED if halted else GRN,
            bg="#2a0b12" if halted else "#0e2a16")
        # v3.96: versi di judul window (bukti update terlihat)
        _v = str(s.get("version") or "")
        if _v and getattr(self, "_vttl", "") != _v:
            self._vttl = _v
            try:
                self.root.title("RBT FX :: TRADING ALGO SYSTEM  v" + _v)
            except Exception:
                pass
        # v3.97: dashboard IKUT dimuat ulang bila versi engine
        # berubah (proses dashboard terpisah dr engine)
        if _v:
            if not getattr(self, "_boot_ver", ""):
                self._boot_ver = _v
            elif (_v != self._boot_ver
                    and not getattr(self, "_restarting", False)):
                self._restarting = True
                try:
                    self.lb_status.configure(
                        text="ENGINE v" + _v
                        + " TERPASANG - DASHBOARD DIMUAT ULANG OTOMATIS...",
                        fg=AMBER)
                except Exception:
                    pass
                _rbt_self_exec()

    # ---- confluence + gauge + chart -------------------------------------
    def _apply_cf(self, s):
        rows = s.get("scanner") or []
        top = None
        if self.sel_sym:
            for r in rows:
                if r.get("symbol") == self.sel_sym:
                    top = r
                    break
        if top is None and s.get("confluence"):
            cs = s["confluence"].get("symbol")
            for r in rows:
                if r.get("symbol") == cs:
                    top = r
                    break
        if top is None and rows:
            top = rows[0]
        if not top:
            return
        sym, sig, sc = top.get("symbol", "-"), top.get("signal", "-"), \
            float(top.get("score", 0) or 0)
        status = top.get("status", "")
        self.lb_cfsym.configure(text="( %s - %s )" % (
            sym, sig if sc >= 70 else "-"))
        cc = (GRN if sig == "BUY" else RED) if sc >= 70 else \
            (AMBER if sc >= 55 else DIM2)
        self.lb_score.configure(text="%.0f%%" % sc, fg=cc)
        valid = status in ("READY", "TRADING")
        vcol = (GRN if sig == "BUY" else RED) if valid else AMBER
        self.lb_verdict.configure(
            text=(("BUY \u25b2" if sig == "BUY" else "SELL \u25bc")
                  if valid else "WAIT"),
            fg=vcol, highlightbackground=vcol)
        self.lb_valid.configure(
            text="[ ENTRY VALID ]" if valid else
            ("[ HOLD - CARI MOMEN ]" if status == "SNIPER_WAIT"
             else "[ STAND BY ]"),
            fg=GRN if valid else (AMBER if status == "SNIPER_WAIT" else DIM))
        # v3.91: teks ">> ..." tidak ditampilkan lagi (permintaan user)
        self.lb_why.configure(text="")
        self._draw_gauge(sc, cc)
        self._draw_bars(top)
        self._draw_chart(top)

    def _draw_gauge(self, sc, cc):
        """Gauge + GLOBE penuh di dalam ring (permintaan user): % di
        dalam ring DIHAPUS (dobel dgn verdict); bola dunia wireframe
        memenuhi bagian dalam ring, warna ikut skor."""
        cv = self.cv_gauge
        cv.delete("all")
        cxg, cyg, R = 75, 75, 60
        import math as _m
        for a in range(0, 360, 30):
            r1, r2 = R + 4, R + 8
            cv.create_line(cxg + r1 * _m.cos(_m.radians(a)),
                           cyg + r1 * _m.sin(_m.radians(a)),
                           cxg + r2 * _m.cos(_m.radians(a)),
                           cyg + r2 * _m.sin(_m.radians(a)),
                           fill=cc if a <= 3.6 * max(sc, 1) - 90 else DIM2,
                           width=1)
        cv.create_oval(cxg - R, cyg - R, cxg + R, cyg + R, outline=DIM2,
                       width=9)
        if sc > 0:
            cv.create_arc(cxg - R, cyg - R, cxg + R, cyg + R, start=90,
                          extent=-3.6 * min(sc, 100), style="arc", outline=cc,
                          width=9)
        # v3.87: bola dunia BERPUTAR (GlobeTk, timer sendiri) ditempel
        # di TENGAH ring -- widget child di atas canvas gauge
        if not getattr(self, "_gg", None):
            self._gg = GlobeTk(cv, size=108, bg=PAN, acc=ACC, dim=DIM2,
                               fade=1.0, disk=True)
        cv.create_window((cxg, cyg), window=self._gg)

    def _draw_bars(self, top):
        cv = self.cv_bars
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width() or 380
        bull = top.get("signal", "-") == "BUY"
        comps = top.get("components") or {}
        y0 = 3
        for k, nm in CF_NAMES:
            v = float(comps.get(k, 0) or 0)
            word = word_for(k, "BUY" if bull else "SELL", v)
            if word in ("Bullish", "Uptrend"):
                col = GRN
            elif word in ("None", "Outside", "Weak"):
                col = DIM2
            else:
                col = RED
            cv.create_text(2, y0 + 6, text="\u2714", fill=DIM2,
                           font=("Consolas", 7))
            cv.create_text(16, y0 + 6, text=nm, fill=DIM,
                           font=("Consolas", 7), anchor="w")
            cv.create_text(int(w * 0.40), y0 + 6, text=word, fill=col,
                           font=("Consolas", 7, "bold"), anchor="e")
            bx0 = int(w * 0.44)
            cv.create_rectangle(bx0, y0 + 1, w - 34, y0 + 11, fill=PAN2,
                                outline=BD)
            if v > 0:
                cv.create_rectangle(bx0, y0 + 1,
                                    bx0 + int((w - 34 - bx0) * v / 100.0),
                                    y0 + 11, fill=col, outline=col)
            cv.create_text(w - 2, y0 + 6, text="%.0f%%" % v, fill=DIM,
                           font=("Consolas", 7), anchor="e")
            y0 += 11

    def _draw_chart(self, top):
        cv = self.cv_chart
        cv.delete("all")
        self.lb_chsym.configure(text=top.get("symbol", "-"))
        ohlc = top.get("ohlc") or []
        try:
            last = float(ohlc[-1][4])
            first = float(ohlc[0][4])
            chg = (last - first) / first * 100 if first else 0.0
        except (IndexError, TypeError, ValueError, ZeroDivisionError):
            last, chg = 0.0, 0.0
        digits = top.get("digits", 2)
        self.lb_chpx.configure(text=fmt(last, digits))
        self.lb_chpct.configure(
            text=("\u25b2 +" if chg >= 0 else "\u25bc ") + "%.2f%%" % chg,
            fg=GRN if chg >= 0 else RED)
        if len(ohlc) < 2:
            cv.create_text(200, 60, text="menunggu data candle...", fill=DIM,
                           font=("Consolas", 8))
            return
        cv.update_idletasks()
        W = cv.winfo_width() or 800
        H = cv.winfo_height() or 84
        R = 54
        PW = W - R
        dcol = GRN if chg >= 0 else RED
        lo = min(min(float(k[3]) for k in ohlc), 1e18)
        hi = max(max(float(k[2]) for k in ohlc), -1e18)
        for val in (top.get("sl"), top.get("tp")):
            try:
                v = float(val)
                if v > 0:
                    lo = min(lo, v)
                    hi = max(hi, v)
            except (TypeError, ValueError):
                pass
        if hi <= lo:
            lo, hi = lo - 1, hi + 1
        pad = (hi - lo) * 0.07
        lo -= pad
        hi += pad

        def y(v):
            return int(6 + (hi - v) / (hi - lo) * (H - 22))

        for b0 in range(3):
            cv.create_rectangle(0, int(H * b0 / 3.0), W,
                                int(H * (b0 + 1) / 3.0),
                                fill=self._mix(PAN2, BG, 0.20 * b0 / 2.0),
                                outline="")
        for g0 in range(5):
            gy = 6 + int((H - 22) * g0 / 4.0)
            cv.create_line(0, gy, PW, gy, fill="#0a2a1c", dash=(2, 4))
            gv = hi - (hi - lo) * g0 / 4.0
            cv.create_text(W - R + 6, gy, text=fmt(gv, digits), anchor="w",
                           fill=DIM2, font=("Consolas", 6))
        n = len(ohlc)
        step = (PW - 8) / float(n)
        cw = min(7.0, max(2.0, step * 0.72))
        cl = [float(k[4]) for k in ohlc]
        sx = 0
        while sx < PW - 10:
            fi = sx / step
            i0 = min(n - 2, int(fi))
            fr = max(0.0, min(1.0, fi - i0))
            yl = y(cl[i0] * (1 - fr) + cl[i0 + 1] * fr)
            h0 = (H - 16) - yl
            if h0 > 6:
                for b0, a0 in ((0, 0.15), (1, 0.07), (2, 0.03)):
                    cv.create_rectangle(
                        sx, yl + h0 * b0 / 3.0, sx + 6,
                        yl + h0 * (b0 + 1) / 3.0,
                        fill=self._mix(PAN2, dcol, a0), outline="")
            sx += 6
        for i, k in enumerate(ohlc):
            x = 4 + i * step
            up = float(k[4]) >= float(k[1])
            col = GRN if up else RED
            xc = x + cw / 2
            cv.create_line(xc, y(float(k[2])), xc, y(float(k[3])), fill=col)
            ytp, ybt = y(max(float(k[1]), float(k[4]))), \
                y(min(float(k[1]), float(k[4])))
            if ybt - ytp < 1:
                ybt = ytp + 1
            cv.create_rectangle(x, ytp, x + cw, ybt, fill=col, outline=col)
        pts = []
        for i0 in range(n):
            pts += [4 + i0 * step + cw / 2, y(cl[i0])]
        cv.create_line(*pts, fill=self._mix(PAN2, CY, 0.40), width=3,
                       smooth=True)
        cv.create_line(*pts, fill=CY, width=1, smooth=True)
        for val, col, nm in ((top.get("sl"), RED, "SL"),
                             (top.get("tp"), GRN, "TP")):
            try:
                v = float(val)
                if v > 0:
                    yy = y(v)
                    cv.create_line(0, yy, PW, yy, fill=col, dash=(3, 3))
                    cv.create_text(5, yy - 7, text=nm, anchor="w", fill=col,
                                   font=("Consolas", 6, "bold"))
                    self._rr(cv, PW + 2, yy - 6, W - 2, yy + 6, 3,
                             fill=self._mix(PAN2, col, 0.30), outline=col)
                    cv.create_text(PW + 7, yy, text=fmt(v, digits),
                                   anchor="w", fill=col,
                                   font=("Consolas", 6))
            except (TypeError, ValueError):
                pass
        ly = y(last)
        cv.create_line(0, ly, PW, ly, fill=dcol, dash=(1, 3))
        cv.create_polygon(2, ly, 8, ly - 4, 8, ly + 4, fill=dcol,
                          outline="")
        self._rr(cv, PW + 2, ly - 7, W - 2, ly + 7, 4, fill=dcol,
                 outline="")
        cv.create_text(PW + 7, ly, text=fmt(last, digits), anchor="w",
                       fill="#02150c", font=("Consolas", 6, "bold"))
        import time as _t
        for i0 in (0, n / 3, n * 2 / 3, n - 1):
            i0 = int(i0)
            t0 = _t.strftime("%H:%M", _t.localtime(int(ohlc[i0][0])))
            cv.create_text(4 + i0 * step + cw / 2, H - 7, text=t0,
                           fill=DIM2, font=("Consolas", 6))
        self._ch_geo = (step, cw, lo, hi, H, PW, W, digits, n)
        if getattr(self, "_m_in", False) and getattr(self, "_mx", 0) > 0:
            self._xhair()

    def _xhair(self):
        geo = getattr(self, "_ch_geo", None)
        if not geo:
            return
        cv = self.cv_chart
        cv.delete("xh")
        step, cw, lo, hi, H, PW, W, digits, n = geo
        mx, my = self._mx, self._my
        if mx < 0 or mx > PW or my < 2 or my > H - 16:
            return
        i0 = int(max(0, min(n - 1, (mx - 4) / step)))
        xc = 4 + i0 * step + cw / 2
        vv = hi - (my - 6) * (hi - lo) / float(H - 22)
        cv.create_line(xc, 0, xc, H - 16, fill=DIM, dash=(1, 3), tags="xh")
        cv.create_line(0, my, PW, my, fill=DIM, dash=(1, 3), tags="xh")
        self._rr(cv, PW + 2, my - 6, W - 2, my + 6, 3,
                 fill=self._mix(PAN2, ACC, 0.75), outline="", tags="xh")
        cv.create_text(PW + 7, my, text=fmt(vv, digits), anchor="w",
                       fill="#02150c", font=("Consolas", 6, "bold"),
                       tags="xh")

    def _cmove(self, e):
        self._mx, self._my, self._m_in = e.x, e.y, True
        self._xhair()

    def _cout(self, _e=None):
        self._m_in = False
        self.cv_chart.delete("xh")

    # ---- animasi tape ----------------------------------------------------
    def _tape_loop(self):
        cv = self.cv_tape
        cv.delete("all")
        w = cv.winfo_width() or 1200
        for s0 in range(4):
            cv.create_rectangle(0, s0 * 5, w, s0 * 5 + 5,
                                fill=self._mix(TAPE_BG, "#07301f", s0 / 3.0),
                                outline="")
        if self.tape_segs:
            self.tape_x -= 1
            if self.tape_x < -w:
                self.tape_x = 0
            # dua salinan berjalan agar mulus tanpa putus
            x = self.tape_x
            for _rep in range(2):
                for seg in self.tape_segs:
                    sym, px, ar, pct, col = seg
                    cv.create_text(x, 10, text=sym, fill=ACC,
                                   font=("Consolas", 9, "bold"), anchor="w")
                    x += 8 + len(sym) * 8
                    cv.create_text(x, 10, text=px, fill=TX,
                                   font=("Consolas", 9), anchor="w")
                    x += 8 + len(px) * 8
                    cv.create_text(x, 10, text=ar + " " + pct, fill=col,
                                   font=("Consolas", 9), anchor="w")
                    x += 26 + len(pct) * 8
        self.root.after(60, self._tape_loop)

    def _shot_now(self):
        try:
            self.root.update_idletasks()
            self.root.update()
            from PIL import ImageGrab
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            img = ImageGrab.grab(
                bbox=(x, y, x + self.root.winfo_width(),
                      y + self.root.winfo_height()),
                xdisplay=None)
            img.save(self.shot)
            print("SHOT SAVED", self.shot)
        except Exception as e:
            print("SHOT GAGAL:", e)
        self._close()

    def run(self):
        self.root.mainloop()

def main():
    ports = None
    shot = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            ports = [int(args[i + 1])]
            i += 1
        elif args[i] == "--shot" and i + 1 < len(args):
            shot = args[i + 1]
            i += 1
        i += 1
    app = Dash(ports=ports, shot=shot)
    app.run()


if __name__ == "__main__":
    main()
