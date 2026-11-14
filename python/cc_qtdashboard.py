# -*- coding: utf-8 -*-
"""
RBT FX :: TRADING ALGO SYSTEM - Dashboard Qt "ROYAL OBSIDIAN" (PySide6/Qt6-C++).

Rombak total visual: obsidian gelap + emas champagne, kartu gradasi ber-glow,
segmented control, gauge emas, chart legend OHLC hover, LED radial pulse.
Sumber data: http://127.0.0.1:<port>/api/status (8081/8080 otomatis).
Dependensi: PySide6-Essentials (fallback Tk: cc_tkdashboard.py).
"""
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal, QObject
    from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPen,
                               QBrush, QLinearGradient, QRadialGradient,
                               QPainterPath, QPolygonF)
    from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QLabel,
                                   QVBoxLayout, QHBoxLayout, QGridLayout,
                                   QTableWidget, QTableWidgetItem, QTextEdit,
                                   QHeaderView, QPushButton, QLineEdit,
                                   QInputDialog, QComboBox,
                                   QGraphicsDropShadowEffect)
except ImportError:  # pragma: no cover
    print("PySide6 belum terpasang. Jalankan: pip install PySide6-Essentials")
    print("(dashboard lama Tk masih bisa dipakai: python cc_tkdashboard.py)")
    sys.exit(1)

# ---- palet ROYAL OBSIDIAN ---------------------------------------------------
BG = "#07070c"       # latar utama obsidian
PAN = "#0d0d15"      # panel
PAN2 = "#12121c"     # panel inset
LINE = "#23233a"     # garis
GOLD = "#e8c574"     # emas champagne
GOLD2 = "#b9954a"    # emas tua
ACC = "#2ee6a8"      # emerald data
CY = "#38c8f0"       # cyan data
GRN = "#2ee6a8"


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


RED = "#ff4d6a"
AMBER = "#ffc857"
VIO = "#b78cff"
TX = "#f0f1fa"       # teks utama
DIM = "#8a8fa8"      # teks redup
DIM2 = "#3c4059"     # garis redup
TAPE_BG = "#0b0b12"

PORTS = [8081, 8080]

CAT_GOLD = {"XAUUSD", "XAGUSD", "GOLD", "SILVER", "XAUUSDM", "XAGUSDM"}
CAT_FOREX = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCHF",
             "USDCAD", "EURJPY", "GBPJPY", "AUDJPY", "EURGBP"}
CAT_CRYPTO = {"BTCUSD", "ETHUSD", "BTCUSDM", "ETHUSDM", "BTCEUR", "ETHEUR"}
CAT_INDEX = {"NAS100", "US30", "SPX500", "GER40", "JP225", "NAS100M", "US500",
             "UK100", "AUS200", "UT100", "USTEC"}
CAT_COMM = {"USOIL", "XTIUSD", "XBRUSD", "USOILM", "UKOIL", "NGAS", "XPTUSD",
            "XPDUSD"}

_RX_GOLD = re.compile(r"^(XAU|XAG|GOLD|SILVER|XPT)")
_RX_CRY = re.compile(r"^(BTC|ETH|SOL|XRP|LTC|DOGE|ADA|XLM|BCH|DOT|LINK)")
_RX_IDX = re.compile(r"(NAS|USTEC|US100|US30|US500|GER|DAX|UK100|FTSE|JP225|NIKKEI|HK50|AUS200|SPX)")
_RX_COM = re.compile(r"(OIL|WTI|BRENT|XBR)")
_TAB_CAT = {"GOLD/SILVER": "GOLD"}   # v4.32: label tombol tab -> kategori cat_of
# v4.36 (user): tombol SW ber-BORDER -- ON hijau, OFF merah
_SW_ON = ("QPushButton{background:#0d3b22;color:#3ddc84;"
          "border:1px solid #22c55e;border-radius:4px;"
          "font-size:7pt;font-weight:800;padding:1px 6px;}")
_SW_OFF = ("QPushButton{background:#3b0d14;color:#ff6b7a;"
           "border:1px solid #ff4d5e;border-radius:4px;"
           "font-size:7pt;font-weight:800;padding:1px 6px;}")
_LOT_QSS = ("QPushButton{background:rgba(240,180,41,0.10);color:#ffd270;"
            "border:1px solid #f0b429;border-radius:4px;"
            "font-size:7pt;font-weight:800;padding:1px 6px;}"
            "QPushButton:disabled{background:#0a0f1e;color:#8a92b8;"
            "border:1px solid #243057;}")

def cat_of(sym):
    s0 = (sym or "").upper()
    if s0 in CAT_GOLD: return "GOLD"
    if s0 in CAT_FOREX: return "FOREX"
    if s0 in CAT_CRYPTO: return "CRYPTO"
    if s0 in CAT_INDEX: return "INDEX"
    if s0 in CAT_COMM: return "COMMODITY"
    # v4.32: nama broker apapun tetap tergrup benar (GOLD.a, XAUUSD.r, ...)
    if _RX_GOLD.match(s0): return "GOLD"
    if _RX_CRY.match(s0): return "CRYPTO"
    if _RX_IDX.search(s0): return "INDEX"
    if _RX_COM.search(s0): return "COMMODITY"
    return "FOREX"


def fmt(v, d=2):
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
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
               "PROTECT": RED, "GUARD": AMBER, "INFO": "#9aa2c8",
               "OPEN": CY, "TRAIL": VIO, "SCAN": DIM}

SESSIONS_HRS = {"SYDNEY": (21, 6), "TOKYO": (0, 9), "LONDON": (7, 16),
                "NEW YORK": (12, 21)}

SANS = "'Segoe UI','DejaVu Sans',sans-serif"
MONO = "'Consolas','DejaVu Sans Mono',monospace"

QSS = """
QWidget { background-color: %s; color: %s; font-family: %s; }
QFrame#panel { background-color: %s; border: 1px solid %s; border-radius: 10px; }
QFrame#chip { background-color: qlineargradient(y1:0,y2:1,stop:0 #17172a,
  stop:1 #0e0e18); border: 1px solid %s; border-radius: 11px; }
QLabel#chipt { color: %s; font-size: 6pt; font-weight: 600;
  background: transparent; }
QLabel#chipv { color: %s; font-size: 8pt; font-weight: bold;
  background: transparent; font-family: %s; }
QTableWidget { background-color: transparent; color: %s; gridline-color: %s;
  border: none; font-size: 8pt; font-family: %s;
  alternate-background-color: #101019; }
QHeaderView::section { background-color: #10101a; color: %s; border: none;
  border-bottom: 1px solid %s; font-size: 7pt; font-weight: bold;
  padding: 3px; font-family: %s; }
QTableWidget::item:selected { background: %s; color: #101014; }
QTextEdit { background-color: %s; border: none; font-size: 8pt;
  font-family: %s; }
QPushButton#tabbtn { background: transparent; color: %s;
  border: 1px solid transparent; border-radius: 9px; padding: 2px 10px;
  font-size: 7pt; font-weight: bold; }
QPushButton#tabbtn:checked { background-color: %s; color: #14140c;
  border: 1px solid %s; }
QPushButton#haltbtn { background-color: qlineargradient(y1:0,y2:1,
  stop:0 #3d0f1c, stop:1 #25060e); color: %s;
  border: 1px solid #6b2135; border-radius: 10px; padding: 2px 7px;
  font-size: 9pt; font-weight: bold; }
QPushButton#haltbtn[hstate="on"] { background-color: qlineargradient(y1:0,y2:1,
  stop:0 #0f3320, stop:1 #071b10); color: #2ee6a8;
  border: 1px solid #1d6b3f; }
QLineEdit { background-color: %s; color: %s; border: 1px solid %s;
  border-radius: 6px; font-size: 8pt; padding: 2px 6px; font-family: %s; }
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: %s; border-radius: 3px;
  min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: %s; border-radius: 3px;
  min-width: 20px; }
""" % (BG, TX, SANS, PAN, LINE, LINE, DIM, TX, MONO, TX, DIM2, MONO, GOLD,
       GOLD2, MONO, GOLD, TAPE_BG, MONO, DIM, GOLD, GOLD2, RED, PAN2, TX,
       LINE, MONO, DIM2, DIM2)


def mix(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def qcol(name, alpha=255):
    c = QColor(name)
    c.setAlpha(alpha)
    return c


def mono(pt, bold=False):
    f = QFont("Consolas", pt)
    f.setStyleHint(QFont.Monospace)
    f.setBold(bold)
    return f


def sans(pt, bold=False):
    f = QFont("Segoe UI", pt)
    f.setStyleHint(QFont.SansSerif)
    if bold:
        f.setBold(True)
        f.setWeight(QFont.DemiBold)
    return f


# ------------------------------------------------------------- klient -------
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

    def pairs_reset(self, port):
        """v4.42: matikan SEMUA switch pair."""
        return self._post(port, "/api/pairs_reset", {})

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


class Sig(QObject):
    data = Signal(dict)
    lot = Signal(str, str)   # v4.38: pesan feedback set lot/switch


# -------------------------------------------------- widget custom -----------
class Crown(QWidget):
    """Mahkota emas bergradasi dengan glow."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(58, 34)
        gl = QGraphicsDropShadowEffect(self)
        gl.setColor(qcol(GOLD, 140))
        gl.setBlurRadius(14)
        gl.setOffset(0, 0)
        self.setGraphicsEffect(gl)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 2, 0, 28)
        grad.setColorAt(0.0, QColor("#f6dfa8"))
        grad.setColorAt(0.5, QColor(GOLD))
        grad.setColorAt(1.0, QColor(GOLD2))
        p.setPen(QPen(QColor("#7a5f26"), 1))
        p.setBrush(QBrush(grad))
        p.drawPolygon(QPolygonF([QPointF(9, 21), QPointF(9, 10),
                                 QPointF(18, 15), QPointF(29, 3),
                                 QPointF(40, 15), QPointF(49, 10),
                                 QPointF(49, 21)]))
        p.drawRect(9, 22, 40, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#fff6d8")))
        p.drawEllipse(QPointF(29, 6), 2.2, 2.2)
        for x0, c0 in ((13, RED), (27, CY), (41, GRN)):
            p.setBrush(QBrush(QColor(c0)))
            p.drawRect(x0, 23, 3, 3)


class GoldText(QWidget):
    """Teks brand emas bergradasi."""

    def __init__(self, txt, pt):
        super().__init__()
        self.txt = txt
        self.pt = pt
        f = QFont("Segoe UI", pt)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        self._f = f
        self.setFixedHeight(pt + 14)
        fm = QFontMetrics(f)
        self.setFixedWidth(fm.horizontalAdvance(txt) + 8)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#f6dfa8"))
        grad.setColorAt(0.55, QColor(GOLD))
        grad.setColorAt(1.0, QColor("#9c7c38"))
        p.setFont(self._f)
        p.setPen(QPen(grad, 1))
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignHCenter, self.txt)


class GlobeCyber(QWidget):
    """BOLA DUNIA CYBER: wireframe globe berputar (gaya hacker net).

    - meridian + paralel dirotasi 3D (yaw terus + tilt), proyeksi
      orthographic; sisi belakang lebih redup (depth fade);
    - blip data (titik kota) berkedip di permukaan;
    - garis scan vertikal menyapu -- kesan terminal cyber.
    Murni QPainter, tanpa gambar/aset eksternal."""

    def __init__(self, parent=None, size=58, opacity=1.0, disk=False):
        super().__init__(parent)
        import math as _m
        self._m = _m
        self.setFixedSize(size, size)
        self._opacity = opacity
        self._disk = disk         # True = cakram solid (badge utuh)
        self._t = 0.0
        self._segs = self._build_segments()
        self._blips = [(18.0, 106.0), (48.8, 2.3), (-6.2, 106.8),
                       (35.7, 139.7), (-34.6, -58.4), (1.35, 103.8),
                       (25.0, 55.2), (40.7, -74.0)]
        from PySide6.QtCore import QTimer
        tim = QTimer(self)
        tim.timeout.connect(self._tick)
        tim.start(40)

    def _build_segments(self):
        m = self._m
        segs = []
        for lat in (-60, -40, -20, 0, 20, 40, 60):
            la = m.radians(lat)
            r, y = m.cos(la), m.sin(la)
            segs.append([(r * m.cos(m.radians(a)), y,
                          r * m.sin(m.radians(a))) for a in range(0, 361, 10)])
        for lon in range(0, 180, 20):
            lo = m.radians(lon)
            segs.append([(m.sin(m.radians(a)) * m.cos(lo),
                          m.cos(m.radians(a)),
                          m.sin(m.radians(a)) * m.sin(lo))
                         for a in range(0, 361, 10)])
        return segs

    def _tick(self):
        self._t = (self._t + 1.0) % 9999.0
        self.update()

    def _rot(self, p, cy, sy, cp, sp):
        x, y, z = p
        x2 = x * cy + z * sy
        z2 = -x * sy + z * cy
        y2 = y * cp - z2 * sp
        z3 = y * sp + z2 * cp
        return x2, y2, z3

    def paintEvent(self, ev):
        from PySide6.QtGui import QPainter, QPen, QColor, QBrush
        from PySide6.QtCore import QPointF, Qt
        m = self._m
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(self._opacity)
        w, h = self.width(), self.height()
        if self._disk:
            # cakram solid: globe UTUH di depan -- garis tabel tidak bisa
            # memotongnya (mode badge, terang penuh tanpa transparan)
            p.setPen(QPen(QColor(46, 230, 168, 110), 1.2))
            p.setBrush(QBrush(QColor(10, 11, 20)))
            p.drawEllipse(QPointF(w / 2.0, h / 2.0), w / 2.0 - 1.0,
                          h / 2.0 - 1.0)
        cx, cy = w / 2.0, h / 2.0
        R = min(w, h) / 2.0 - 2.0
        yaw = self._t * 0.024
        tilt = -0.32
        cyw, syw = m.cos(yaw), m.sin(yaw)
        cp, sp = m.cos(tilt), m.sin(tilt)
        # glow lingkaran luar
        p.setPen(QPen(QColor(46, 230, 168, 70), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R + 1.0, R + 1.0)
        p.setPen(QPen(QColor(0, 224, 255, 28), 1.0))
        p.drawEllipse(QPointF(cx, cy), R + 3.5, R + 3.5)
        # wireframe: tiap ruas kecil diberi warna sesuai kedalaman
        for seg in self._segs:
            prev = None
            for pt in seg:
                x, y, z = self._rot(pt, cyw, syw, cp, sp)
                sx, sy = cx + x * R, cy - y * R
                if prev is not None:
                    d = (z + prev[2]) * 0.5
                    a = int(60 + 165 * max(0.0, (d + 1.0) * 0.5))
                    col = QColor(0, int(200 + 30 * d), int(120 + 60 * d), a) \
                        if False else QColor(46, 230, 168, a)
                    p.setPen(QPen(col, 1.0))
                    p.drawLine(QPointF(prev[0], prev[1]), QPointF(sx, sy))
                prev = (sx, sy, z)
        # blip kota: titik berkedip di sisi depan
        for i, (la, lo) in enumerate(self._blips):
            lar, lor = m.radians(la), m.radians(lo + self._t * 1.4)
            x0 = m.cos(lar) * m.cos(lor)
            z0 = m.cos(lar) * m.sin(lor)
            y0 = m.sin(lar)
            x, y, z = self._rot((x0, y0, z0), cyw, syw, cp, sp)
            if z <= 0.05:
                continue
            blink = 0.55 + 0.45 * m.sin(self._t * 0.25 + i * 1.7)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 224, 255, int(230 * blink))))
            r = 1.1 + 0.8 * blink
            p.drawEllipse(QPointF(cx + x * R, cy - y * R), r, r)
        # garis scan vertikal
        sxp = (self._t * 2.3) % (w + 18.0) - 9.0
        p.setPen(QPen(QColor(46, 230, 168, 46), 2.0))
        p.drawLine(QPointF(sxp, 2.0), QPointF(sxp, h - 2.0))
        p.end()


class HeroBar(QFrame):
    """Topbar gradient dengan garis emas bawah."""

    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.setFixedHeight(50)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#161624"))
        grad.setColorAt(1.0, QColor("#0b0b13"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1,
                                 self.height() - 1), 10, 10)
        g2 = QLinearGradient(0, 0, self.width(), 0)
        g2.setColorAt(0.0, qcol(GOLD2, 40))
        g2.setColorAt(0.5, QColor(GOLD))
        g2.setColorAt(1.0, qcol(GOLD2, 40))
        p.fillRect(QRectF(10, self.height() - 2, self.width() - 20, 1), g2)


class Divider(QWidget):
    """Garis emas simetris di bawah hero."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(3)

    def paintEvent(self, _e):
        p = QPainter(self)
        w = self.width()
        g = QLinearGradient(0, 0, w, 0)
        g.setColorAt(0.0, qcol(GOLD, 0))
        g.setColorAt(0.2, qcol(GOLD2, 130))
        g.setColorAt(0.5, QColor(GOLD))
        g.setColorAt(0.8, qcol(GOLD2, 130))
        g.setColorAt(1.0, qcol(GOLD, 0))
        p.fillRect(QRectF(0, 1, w, 1), QBrush(g))


RAIN_CHARS = "\uFF71\uFF72\uFF73\uFF74\uFF75\uFF76\uFF77\uFF78\uFF79" \
    "\uFF7a0123456789ABCDEF<>/#$%&@*"


def paint_rain(p, w, h, alpha=24):
    """Hujan digital phospor hijau (deterministik, tanpa state)."""
    t = time.time()
    p.setFont(mono(7))
    colw = 11
    ncol = int(w / colw) + 1
    for ci in range(ncol):
        seed = (ci * 97) % 211
        speed = 40 + (seed * 13) % 90
        x = ci * colw + 3
        span = h + 120
        head = (seed * 53 + t * speed) % span - 60
        for k in range(0, 110, 12):
            y = head - k
            if y < 8 or y > h - 2:
                continue
            ch = RAIN_CHARS[(seed * 31 + k * 7) % len(RAIN_CHARS)]
            if k == 0:
                p.setPen(qcol(ACC, min(255, alpha + 60)))
            else:
                p.setPen(qcol(ACC, max(0, alpha - k)))
            p.drawText(QPointF(x, y), ch)


class Panel(QFrame):
    """Panel obsidian dengan tepi gradient halus (opsi matrix rain)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.rain = False

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        gb = QLinearGradient(0, 0, 0, self.height())
        gb.setColorAt(0.0, QColor("#101019"))
        gb.setColorAt(1.0, QColor("#0c0c14"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(gb))
        p.drawRoundedRect(r, 10, 10)
        gl = QLinearGradient(0, 0, self.width(), 0)
        gl.setColorAt(0.0, qcol(GOLD2, 0))
        gl.setColorAt(0.5, qcol(GOLD2, 90))
        gl.setColorAt(1.0, qcol(GOLD2, 0))
        p.setBrush(QBrush(gl))
        p.drawRoundedRect(QRectF(8, 0.5, self.width() - 16, 1), 0, 0)
        if self.rain:
            paint_rain(p, self.width(), self.height(), 16)


class Scanlines(QWidget):
    """Overlay garis CRT halus di seluruh jendela."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.raise_()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setPen(QPen(qcol("#54ffa9", 9), 1))
        y = 0
        while y < self.height():
            p.drawLine(0, y, self.width(), y)
            y += 3


class SessionCompact(QWidget):
    """4 sesi dalam baris kompak: nama | status | bar progres."""

    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setMinimumHeight(68)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        y0 = 4
        for k in ("SYDNEY", "TOKYO", "LONDON", "NEW YORK"):
            op, txt = self.dash.sess_info.get(k, (False, "--:--"))
            p.setFont(sans(7, True))
            p.setPen(QColor(TX))
            p.drawText(QPointF(8, y0 + 8), k)
            p.setFont(mono(7))
            p.setPen(QColor(GRN if op else DIM))
            p.drawText(QPointF(100, y0 + 8), txt)
            a, z = SESSIONS_HRS[k]
            ln = (z - a) if z >= a else (z + 24 - a)
            cur = (self.dash.hr - a) if self.dash.hr >= a else \
                (self.dash.hr + 24 - a)
            f0 = cur / float(ln) if 0 <= cur < ln else 0.0
            bx = 196
            bw = w - bx - 10
            if bw > 20:
                p.setPen(QPen(QColor("#20222f"), 1))
                p.setBrush(QBrush(QColor("#14141d")))
                p.drawRoundedRect(QRectF(bx, y0 + 2, bw, 8), 4, 4)
                if f0 > 0:
                    g = QLinearGradient(bx, 0, bx + bw, 0)
                    g.setColorAt(0.0, qcol(GRN, 110))
                    g.setColorAt(1.0, QColor(GRN))
                    p.setBrush(QBrush(g))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(QRectF(bx, y0 + 2,
                                             max(6, bw * f0), 8), 4, 4)
            y0 += 15


class Aurora(QWidget):
    """Garis emas dengan 'komet' emerald yang bergerak halus."""

    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setFixedHeight(2)

    def paintEvent(self, _e):
        p = QPainter(self)
        w = self.width()
        g = QLinearGradient(0, 0, w, 0)
        g.setColorAt(0.0, qcol(GOLD, 0))
        g.setColorAt(0.2, qcol(GOLD2, 110))
        g.setColorAt(0.5, qcol(GOLD, 180))
        g.setColorAt(0.8, qcol(GOLD2, 110))
        g.setColorAt(1.0, qcol(GOLD, 0))
        p.fillRect(QRectF(0, 1, w, 1), QBrush(g))
        ph = self.dash.aurora_ph
        cx = ph * (w * 1.3) - w * 0.15
        c = QLinearGradient(cx - w * 0.12, 0, cx + w * 0.12, 0)
        c.setColorAt(0.0, qcol(ACC, 0))
        c.setColorAt(0.5, qcol(ACC, 210))
        c.setColorAt(1.0, qcol(ACC, 0))
        p.fillRect(QRectF(0, 0, w, 3), QBrush(c))


class Kicker(QWidget):
    """Garis kecil emas vertikal untuk judul section."""

    def __init__(self, col=GOLD):
        super().__init__()
        self.col = col
        self.setFixedSize(3, 12)

    def paintEvent(self, _e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, qcol(self.col, 60))
        g.setColorAt(1.0, QColor(self.col))
        p.fillRect(self.rect(), QBrush(g))


class Tape(QWidget):
    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setFixedHeight(20)
        self.off = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(55)

    def _tick(self):
        self.off -= 1
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(TAPE_BG))
        segs = self.dash.tape_segs
        if not segs:
            p.setFont(mono(8))
            p.setPen(QColor(DIM2))
            p.drawText(8, 15, "menunggu data scanner...")
            return
        fb = mono(9, True)
        f = mono(9)
        p.setFont(fb)
        fm = p.fontMetrics()
        p.setFont(f)
        fm2 = p.fontMetrics()
        widths = []
        pw = 0
        for sym, px, ar, pct, _c in segs:
            w0 = fm.horizontalAdvance(sym) + 8
            w0 += fm2.horizontalAdvance(px) + 8
            w0 += fm2.horizontalAdvance(ar + " " + pct) + 8
            w0 += fm2.horizontalAdvance("\u25c6") + 14
            widths.append(w0)
            pw += w0
        if pw <= 0:
            return
        if self.off < -pw:
            self.off = 0
        x0 = self.off
        guard = 0
        while x0 < self.width() and guard < 4:
            guard += 1
            x = x0
            for i0, (sym, px, ar, pct, c0) in enumerate(segs):
                if x + widths[i0] > 0 and x < self.width():
                    p.setFont(fb); p.setPen(QColor(GOLD))
                    p.drawText(x, 15, sym)
                    w1 = fm.horizontalAdvance(sym) + 8
                    p.setFont(f); p.setPen(QColor(TX))
                    p.drawText(x + w1, 15, px)
                    w2 = fm2.horizontalAdvance(px) + 8
                    p.setPen(QColor(c0))
                    p.drawText(x + w1 + w2, 15, ar + " " + pct)
                    w3 = fm2.horizontalAdvance(ar + " " + pct) + 8
                    p.setPen(qcol(GOLD2, 150))
                    p.drawText(x + w1 + w2 + w3, 14, "\u25c6")
                x += widths[i0]
            x0 += pw


class Spark(QWidget):
    """Sparkline emas utk kartu EQUITY."""

    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setFixedHeight(10)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        hh = self.dash.eq_hist
        if len(hh) < 2:
            return
        lo0, hi0 = min(hh), max(hh)
        if hi0 - lo0 < 1e-9:
            lo0, hi0 = lo0 - 1, hi0 + 1
        w, h = self.width(), self.height()
        path = QPainterPath()
        for i0, v0 in enumerate(hh):
            x0 = w * i0 / (len(hh) - 1.0)
            y0 = h - 1 - (h - 2) * (v0 - lo0) / (hi0 - lo0)
            if i0 == 0:
                path.moveTo(x0, y0)
            else:
                path.lineTo(x0, y0)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(qcol(GOLD, 70), 3))
        p.drawPath(path)
        p.setPen(QPen(QColor(GOLD), 1))
        p.drawPath(path)


class Card(QFrame):
    """Kartu mewah: gradasi + tepi gradient + gloss + glow."""

    def __init__(self, ic, title, acc, dash):
        super().__init__()
        self.acc = acc
        self.setMinimumHeight(58)
        gl = QGraphicsDropShadowEffect(self)
        gl.setColor(qcol(acc, 60))
        gl.setBlurRadius(14)
        gl.setOffset(0, 0)
        self.setGraphicsEffect(gl)
        self.glow = gl
        self.flash = 0.0
        self.hover = False
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(8, 4, 8, 5)
        self.v.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(5)
        icf = QLabel(ic)
        icf.setFixedSize(17, 17)
        icf.setAlignment(Qt.AlignCenter)
        icf.setStyleSheet(
            "color:%s;font-size:8.5pt;background:%s;border-radius:5px;"
            % (acc, mix(BG, acc, 0.22).name()))
        top.addWidget(icf)
        tt = QLabel(title)
        f = sans(7, True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
        tt.setFont(f)
        tt.setStyleSheet("color:%s;font-size:6.5pt;font-weight:bold;"
                         "background:transparent;"
                         % mix(TX, DIM, 0.35).name())
        top.addWidget(tt)
        top.addStretch(1)
        self.v.addLayout(top)
        self.val = QLabel("-")
        self.val.setFont(mono(10, True))
        self.val.setStyleSheet("color:%s;background:transparent;" % acc)
        self.v.addWidget(self.val)
        self.sub = QLabel("")
        self.sub.setFont(sans(6))
        self.sub.setStyleSheet("color:%s;font-size:6.5pt;"
                               "background:transparent;"
                               % mix(TX, DIM2, 0.4).name())
        self.v.addWidget(self.sub)
        self.spark = Spark(dash) if title == "EQUITY" else None
        if self.spark:
            self.v.addWidget(self.spark)
        self.barw = _Bar(self, acc)
        self.v.addWidget(self.barw)

    def enterEvent(self, _e):
        self.hover = True

    def leaveEvent(self, _e):
        self.hover = False

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        gb = QLinearGradient(0, 0, 0, self.height())
        gb.setColorAt(0.0, mix(BG, self.acc, 0.16))
        gb.setColorAt(1.0, mix(BG, self.acc, 0.05))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(gb))
        p.drawRoundedRect(r, 9, 9)
        gbord = QLinearGradient(0, 0, self.width(), self.height())
        gbord.setColorAt(0.0, mix(BG, self.acc, 0.22))
        gbord.setColorAt(0.5, mix(BG, self.acc, 0.60))
        gbord.setColorAt(1.0, mix(BG, self.acc, 0.22))
        p.setPen(QPen(QBrush(gbord), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 9, 9)
        p.setPen(QPen(qcol("#ffffff", 14), 1))
        p.drawLine(12, 1, self.width() - 12, 1)


class _Bar(QWidget):
    """Strip bawah kartu."""

    def __init__(self, _parent, acc):
        super().__init__()
        self.acc = acc
        self.setFixedHeight(2)

    def paintEvent(self, _e):
        p = QPainter(self)
        w = self.width()
        g = QLinearGradient(0, 0, w, 0)
        g.setColorAt(0.0, qcol(self.acc, 40))
        g.setColorAt(0.5, QColor(self.acc))
        g.setColorAt(1.0, qcol(self.acc, 40))
        p.fillRect(QRectF(0, 1, w, 1), QBrush(g))


class Gauge(QWidget):
    """Gauge emas + ticks + GLOBE penuh di dalam ring (permintaan user):
    angka % di dalam ring DIHAPUS (dobel dgn verdict sebelah); icon bola
    dunia wireframe memenuhi bagian dalam ring, warna ikut skor."""

    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setFixedSize(150, 150)
        # v3.87 (user): GLOBE BERPUTAR (GlobeCyber) FULL di dalam ring;
        # cakram solid -> garis ring/ticks tak memotong bola
        self.gglobe = GlobeCyber(self, size=108, opacity=1.0, disk=True)
        self.gglobe.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.gglobe.move((150 - 108) // 2, (150 - 108) // 2)
        self.gglobe.raise_()

    def paintEvent(self, _e):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        sc, cc = getattr(self.dash, "g_disp", self.dash.g_sc), QColor(self.dash.g_cc)
        cx, cy, R = 75, 75, 62
        ring = QLinearGradient(0, cy - R, 0, cy + R)
        ring.setColorAt(0.0, QColor("#3a3d58"))
        ring.setColorAt(1.0, QColor("#22243a"))
        pen = QPen(QBrush(ring), 10)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R, R)
        for a in range(0, 360, 30):
            r1, r2 = R + 5, R + 9
            col = cc if a <= 3.6 * max(sc, 1) - 90 else QColor("#33364e")
            p.setPen(QPen(col, 1))
            p.drawLine(QPointF(cx + r1 * math.cos(math.radians(a)),
                               cy + r1 * math.sin(math.radians(a))),
                       QPointF(cx + r2 * math.cos(math.radians(a)),
                               cy + r2 * math.sin(math.radians(a))))
        if sc > 0:
            g = QLinearGradient(cx - R, cy - R, cx + R, cy + R)
            g.setColorAt(0.0, QColor(GOLD))
            g.setColorAt(1.0, QColor(cc))
            p.setPen(QPen(QBrush(g), 10))
            p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R), 90 * 16,
                      int(-3.6 * min(sc, 100)) * 16)
        # v3.87: bola dunia = child widget GlobeCyber BERPUTAR di tengah
        # (digambar sendiri oleh child, di ATAS ring)


class Bars(QWidget):
    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setMinimumHeight(72)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        top = getattr(self.dash, "cf_top", None) or {}
        bull = top.get("signal", "-") == "BUY"
        comps = top.get("components") or {}
        w = self.width()
        y0 = 4
        for k, nm in CF_NAMES:
            v = float(comps.get(k, 0) or 0)
            word = word_for(k, "BUY" if bull else "SELL", v)
            if word in ("Bullish", "Uptrend"):
                c0 = QColor(GRN)
            elif word in ("None", "Outside", "Weak"):
                c0 = QColor(DIM2)
            else:
                c0 = QColor(RED)
            p.setPen(QColor("#565b7a")); p.setFont(sans(7))
            p.drawText(2, y0 + 8, "\u2714")
            p.setPen(QColor(DIM))
            p.drawText(16, y0 + 8, nm)
            p.setFont(sans(7, True)); p.setPen(c0)
            p.drawText(int(w * 0.40) - p.fontMetrics().horizontalAdvance(word),
                       y0 + 8, word)
            bx0 = int(w * 0.44)
            p.setPen(QPen(QColor("#20222f"), 1))
            p.setBrush(QBrush(QColor("#14141d")))
            p.drawRoundedRect(QRectF(bx0, y0 + 1, w - 34 - bx0, 10), 3, 3)
            if v > 0:
                g = QLinearGradient(bx0, 0, w - 34, 0)
                g.setColorAt(0.0, qcol(c0, 110))
                g.setColorAt(1.0, c0)
                p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(bx0, y0 + 1,
                                         max(3, (w - 34 - bx0) * v / 100.0),
                                         10), 3, 3)
            p.setPen(QColor(DIM)); p.setFont(mono(7))
            t0 = "%.0f%%" % v
            p.drawText(w - 2 - p.fontMetrics().horizontalAdvance(t0),
                       y0 + 8, t0)
            y0 += 11


class MarketBars(QWidget):
    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setFixedHeight(52)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        y0 = 4
        for k in ("SYDNEY", "TOKYO", "LONDON", "NEW YORK"):
            a, z = SESSIONS_HRS[k]
            ln = (z - a) if z >= a else (z + 24 - a)
            cur = (self.dash.hr - a) if self.dash.hr >= a else \
                (self.dash.hr + 24 - a)
            f0 = cur / float(ln) if 0 <= cur < ln else 0.0
            p.setPen(QPen(QColor("#20222f"), 1))
            p.setBrush(QBrush(QColor("#14141d")))
            p.drawRoundedRect(QRectF(0, y0, w, 6), 3, 3)
            if f0 > 0:
                g = QLinearGradient(0, 0, w, 0)
                g.setColorAt(0.0, qcol(GRN, 120))
                g.setColorAt(1.0, QColor(GRN))
                p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(0, y0, max(6, w * f0), 6), 3, 3)
            y0 += 12


class LED(QWidget):
    """LED radial dengan halo glow."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(18, 18)
        self.col = QColor(AMBER)
        self.ph = False

    def set_col(self, col, ph=None):
        self.col = QColor(col)
        if ph is not None:
            self.ph = ph
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        halo = mix(QColor(BG), self.col, 0.38 if self.ph else 0.16)
        g = QRadialGradient(QPointF(9, 9), 9)
        g.setColorAt(0.0, QColor(self.col))
        g.setColorAt(0.45, halo)
        g.setColorAt(1.0, qcol(self.col, 0))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(0, 0, 18, 18))
        p.setBrush(QBrush(QColor(self.col)))
        p.drawEllipse(QPointF(9, 9), 3.2, 3.2)


class Chart(QWidget):
    """Chart kustom mewah: legend OHLC hover, glow, gradient, gold pill."""

    def __init__(self, dash):
        super().__init__()
        self.dash = dash
        self.setMinimumHeight(116)
        self.setMouseTracking(True)
        self.mx = self.my = -1
        self.top = {}

    def set_top(self, top):
        self.top = top or {}
        d = self.dash
        d.lb_chsym.setText(self.top.get("symbol", "-"))
        self.update()

    def mouseMoveEvent(self, e):
        self.mx, self.my = e.position().x(), e.position().y()
        self.update()

    def leaveEvent(self, _e):
        self.mx = self.my = -1
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        top = self.top
        ohlc = top.get("ohlc") or []
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#0a0a11"))
        try:
            last = float(ohlc[-1][4])
            first = float(ohlc[0][4])
            chg = (last - first) / first * 100 if first else 0.0
        except (IndexError, TypeError, ValueError, ZeroDivisionError):
            last, chg = 0.0, 0.0
        digits = top.get("digits", 2)
        dcol = QColor(GRN if chg >= 0 else RED)
        d = self.dash
        d.lb_chpx.setText(fmt(last, digits))
        d.lb_chpx.setStyleSheet("color:%s;font-size:11pt;font-weight:bold;"
                                "background:transparent;" % dcol.name())
        d.lb_chpct.setText(("\u25b2 +" if chg >= 0 else "\u25bc ")
                           + "%.2f%%" % chg)
        d.lb_chpct.setStyleSheet("color:%s;font-size:9pt;font-weight:bold;"
                                 "background:transparent;" % dcol.name())
        if len(ohlc) < 2:
            p.setPen(QColor(DIM)); p.setFont(sans(8))
            p.drawText(self.rect(), Qt.AlignCenter, "menunggu data candle...")
            return
        R = 56
        PW = W - R
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
            return 8 + (hi - v) / (hi - lo) * (H - 26)

        for b0 in range(3):
            p.fillRect(0, int(H * b0 / 3.0), W,
                       int(H * (b0 + 1) / 3.0) - int(H * b0 / 3.0),
                       mix("#0a0a11", BG, 0.22 * b0 / 2.0))
        paint_rain(p, W, H - 18, 20)
        pen = QPen(QColor("#191926"), 1)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([2, 4])
        p.setBrush(Qt.NoBrush)
        for g0 in range(5):
            gy = 8 + (H - 26) * g0 / 4.0
            p.setPen(pen)
            p.drawLine(QPointF(0, gy), QPointF(PW, gy))
            gv = hi - (hi - lo) * g0 / 4.0
            p.setPen(QColor("#565b7a")); p.setFont(mono(6))
            p.drawText(QPointF(W - R + 6, gy + 3), fmt(gv, digits))
        n = len(ohlc)
        step = (PW - 8) / float(n)
        cw = min(7.0, max(2.0, step * 0.72))
        cl = [float(k[4]) for k in ohlc]
        apath = QPainterPath()
        for i0 in range(n):
            pt = QPointF(4 + i0 * step + cw / 2, y(cl[i0]))
            if i0 == 0:
                apath.moveTo(pt)
            else:
                apath.lineTo(pt)
        afill = QPainterPath(apath)
        afill.lineTo(4 + (n - 1) * step + cw / 2, H - 20)
        afill.lineTo(4 + cw / 2, H - 20)
        afill.closeSubpath()
        grad = QLinearGradient(QPointF(0, 8), QPointF(0, H - 20))
        ctop = QColor(dcol); ctop.setAlpha(44)
        cbot = QColor(dcol); cbot.setAlpha(0)
        grad.setColorAt(0.0, ctop)
        grad.setColorAt(1.0, cbot)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(afill)
        for i0, k in enumerate(ohlc):
            x0 = 4 + i0 * step
            up = float(k[4]) >= float(k[1])
            c0 = QColor(GRN if up else RED)
            xc = x0 + cw / 2
            p.setPen(QPen(c0, 1))
            p.drawLine(QPointF(xc, y(float(k[2]))), QPointF(xc, y(float(k[3]))))
            ytp, ybt = y(max(float(k[1]), float(k[4]))), \
                y(min(float(k[1]), float(k[4])))
            if ybt - ytp < 1:
                ybt = ytp + 1
            p.setBrush(QBrush(c0))
            p.drawRect(QRectF(x0, ytp, cw, ybt - ytp))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(qcol(CY, 80), 3))
        p.drawPath(apath)
        p.setPen(QPen(QColor(CY), 1))
        p.drawPath(apath)
        for val, c0, nm in ((top.get("sl"), RED, "SL"),
                            (top.get("tp"), GRN, "TP")):
            try:
                v = float(val)
                if v > 0:
                    yy = y(v)
                    pen2 = QPen(QColor(c0), 1)
                    pen2.setStyle(Qt.CustomDashLine)
                    pen2.setDashPattern([3, 3])
                    p.setPen(pen2)
                    p.drawLine(QPointF(0, yy), QPointF(PW, yy))
                    p.setPen(QColor(c0)); p.setFont(mono(6, True))
                    p.drawText(QPointF(5, yy - 3), nm)
                    p.setBrush(qcol(c0, 40))
                    p.setPen(QPen(QColor(c0), 1))
                    p.drawRoundedRect(QRectF(PW + 2, yy - 6, R - 4, 12), 6, 6)
                    p.setFont(mono(6))
                    p.drawText(QPointF(PW + 7, yy + 3), fmt(v, digits))
            except (TypeError, ValueError):
                pass
        ly = y(last)
        pen3 = QPen(dcol, 1)
        pen3.setStyle(Qt.CustomDashLine)
        pen3.setDashPattern([1, 3])
        p.setPen(pen3)
        p.drawLine(QPointF(0, ly), QPointF(PW, ly))
        p.setBrush(QBrush(dcol)); p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(2, ly), QPointF(8, ly - 4),
                                 QPointF(8, ly + 4)]))
        gpill = QLinearGradient(PW, 0, W, 0)
        gpill.setColorAt(0.0, dcol)
        gpill.setColorAt(1.0, mix(dcol, GOLD, 0.25))
        p.setBrush(QBrush(gpill))
        p.drawRoundedRect(QRectF(PW + 2, ly - 7, R - 4, 14), 7, 7)
        p.setPen(QColor("#101014")); p.setFont(mono(6, True))
        p.drawText(QPointF(PW + 7, ly + 3), fmt(last, digits))
        if getattr(self.dash, "_aph", False):
            p.setBrush(QBrush(qcol(dcol, 210)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(4 + (n - 1) * step + cw / 2, ly), 2.6, 2.6)
        p.setPen(QColor("#565b7a")); p.setFont(mono(6))
        for i0 in (0, n // 3, n * 2 // 3, n - 1):
            t0 = time.strftime("%H:%M", time.localtime(int(ohlc[i0][0])))
            x0 = 4 + i0 * step + cw / 2
            p.drawText(QPointF(min(max(x0 - 12, 2), PW - 26), H - 7), t0)
        hi0 = None
        if 0 <= self.mx <= PW and 2 <= self.my <= H - 20:
            penx = QPen(QColor(DIM), 1)
            penx.setStyle(Qt.CustomDashLine)
            penx.setDashPattern([1, 3])
            p.setPen(penx)
            i0 = int(max(0, min(n - 1, (self.mx - 4) / step)))
            xc = 4 + i0 * step + cw / 2
            p.drawLine(QPointF(xc, 0), QPointF(xc, H - 20))
            p.drawLine(QPointF(0, self.my), QPointF(PW, self.my))
            vv = hi - (self.my - 8) * (hi - lo) / float(H - 26)
            p.setBrush(QBrush(mix("#0a0a11", ACC, 0.75))); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(PW + 2, self.my - 6, R - 4, 12), 6, 6)
            p.setPen(QColor("#101014")); p.setFont(mono(6, True))
            p.drawText(QPointF(PW + 7, self.my + 3), fmt(vv, digits))
            hi0 = i0
        if hi0 is not None:
            k = ohlc[hi0]
            t0 = time.strftime("%H:%M", time.localtime(int(k[0])))
            info = ("%s   O %s   H %s   L %s   C %s" % (
                t0, fmt(k[1], digits), fmt(k[2], digits),
                fmt(k[3], digits), fmt(k[4], digits)))
            up = float(k[4]) >= float(k[1])
            p.setBrush(qcol("#0a0a11", 200))
            p.setPen(QPen(qcol(GOLD2, 120), 1))
            pr = p.fontMetrics().horizontalAdvance(info) + 16
            p.drawRoundedRect(QRectF(6, 6, pr, 16), 4, 4)
            p.setPen(QColor(GRN if up else RED)); p.setFont(mono(7))
            p.drawText(QPointF(14, 17), info)


# --------------------------------------------------------------- jendela ----
class Dash(QWidget):
    def __init__(self, ports=None, shot=None):
        super().__init__()
        self.ports = list(ports or PORTS)
        self.shot = shot
        self.client = EngineClient()
        self.active_port = None
        self.snap = {}
        self.need_auth = False
        self.sel_sym = None
        self._sw_map = {}   # v4.34: symbol -> bool switch
        self._lot_map = {}  # v4.37: symbol -> float lot manual
        self.tab = "ALL"
        self.tape_segs = []
        self.eq_hist = []
        self.g_sc = 0
        self.g_disp = 0.0
        self.g_cc = DIM2
        self.aurora_ph = 0.0
        self.cf_top = {}
        self.hr = 0.0
        self.setWindowTitle("RBT FX :: TRADING ALGO SYSTEM")
        self.sig = Sig()
        self.sig.data.connect(self._on_data)
        self.sig.lot.connect(self._set_lot_info)
        self._build()
        self.thr = threading.Thread(target=self._poll_loop, daemon=True)
        self.thr.start()

    def _ptitle(self, parent, txt, right=None, rcol=DIM, col=GOLD):
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 5, 10, 2)
        lay.setSpacing(7)
        lay.addWidget(Kicker(col))
        lb = QLabel(txt)
        f = sans(9, True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
        lb.setFont(f)
        lb.setStyleSheet("color:%s;font-size:9pt;font-weight:bold;"
                         "background:transparent;" % TX)
        lay.addWidget(lb)
        lay.addStretch(1)
        if right:
            lr = QLabel(right)
            lr.setFont(sans(7, True))
            lr.setStyleSheet("color:%s;font-size:7pt;font-weight:bold;"
                             "background:transparent;" % rcol)
            lay.addWidget(lr)
        parent.layout().addWidget(bar)
        return bar

    def _chip(self, title):
        f = QFrame()
        f.setObjectName("chip")
        v = QVBoxLayout(f)
        v.setContentsMargins(4, 1, 4, 1)
        v.setSpacing(0)
        t = QLabel(title)
        t.setObjectName("chipt")
        val = QLabel("-")
        val.setObjectName("chipv")
        v.addWidget(t)
        v.addWidget(val)
        return f, val

    def _build(self):
        self.resize(1306, 724)
        self.setMinimumSize(1024, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(2)

        # ===== HERO =====
        hero = HeroBar()
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(5)
        hl.addWidget(Crown())
        hl.addWidget(GoldText("RBT FX", 14))
        title = QLabel(" TRADING ALGO SYSTEM ")
        f = sans(9, True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
        title.setFont(f)
        title.setStyleSheet("color:%s;border:1px solid %s;border-radius:3px;"
                            "padding:2px 7px;background:transparent;"
                            % (GOLD, GOLD2))
        hl.addWidget(title)
        hl.addSpacing(6)
        self.ch = {}
        for key in ("PYTHON ENGINE", "MTS", "AKUN", "RISK MANAGER",
                    "DAILY PROTECTION", "WEEKEND GUARD"):
            fc, val = self._chip(key)
            hl.addWidget(fc)
            self.ch[key] = (fc, val)
        # v3.57: panel DEVELOPER = gaya SAMA persis dgn chip sampingnya
        # (judul abu kecil + nilai tebal 8pt, satu baris)
        fdev, valdev = self._chip("DEVELOPER")
        valdev.setText("RIBUT PRASETYOAJI - 0811 347 1112 - "
                       "JOMBANG,JAWA TIMUR,IND")
        hl.addWidget(fdev)
        hl.addStretch(1)
        self.btn_halt = QPushButton("⚡ ON")
        self.btn_halt.setObjectName("haltbtn")
        self.btn_halt.setProperty("hstate", "on")
        self.btn_halt.clicked.connect(self._halt)
        hl.addWidget(self.btn_halt)
        self._upd_armed = 0.0
        self.lb_clock = QLabel("--:--:--")
        self.lb_clock.setFont(mono(12, True))
        self.lb_clock.setStyleSheet("color:%s;font-size:12pt;font-weight:"
                                    "bold;background:transparent;" % GOLD)
        hl.addWidget(self.lb_clock)
        root.addWidget(hero)

        self.aurora = Aurora(self)
        root.addWidget(self.aurora)

        # ===== TAPE =====
        self.tape = Tape(self)
        root.addWidget(self.tape)

        # ===== CARDS =====
        self.card_defs = [("\u25c8", "BALANCE", AMBER),
                          ("\u25c9", "EQUITY", GOLD),
                          ("\u25b2", "DAILY PROFIT", GRN),
                          ("\u25bc", "DAILY LOSS", AMBER),
                          ("\u2248", "FLOATING TERBUKA", CY),
                          ("\u26a0", "DRAWDOWN", RED),
                          ("\u00a4", "KOMISI / FEE", VIO),
                          ("\u25a3", "OPEN POSITIONS", ACC)]
        crow = QHBoxLayout()
        crow.setSpacing(5)
        self.cards = []
        for ic, ttl, acc in self.card_defs:
            c = Card(ic, ttl, acc, self)
            crow.addWidget(c, 1)
            self.cards.append((c.val, c.sub, c))
        root.addLayout(crow)

        # ===== STATUSBAR =====
        bot = QFrame()
        bot.setObjectName("panel")
        blay = QHBoxLayout(bot)
        blay.setContentsMargins(10, 3, 10, 3)
        self.led = LED()
        blay.addWidget(self.led)
        self.lb_status = QLabel("BOOTING SYSTEM...")
        self.lb_status.setFont(sans(10, True))
        self.lb_status.setStyleSheet("color:%s;font-size:10pt;font-weight:"
                                     "bold;background:transparent;"
                                     % AMBER)
        blay.addWidget(self.lb_status)
        blay.addStretch(1)
        self.ent_pw = QLineEdit()
        self.ent_pw.setEchoMode(QLineEdit.Password)
        self.ent_pw.setPlaceholderText("password")
        self.ent_pw.setFixedWidth(110)
        self.ent_pw.setVisible(False)
        self.ent_pw.returnPressed.connect(self._try_pw)
        self.btn_auth = QPushButton("PASSWORD")
        self.btn_auth.setObjectName("tabbtn")
        self.btn_auth.setVisible(False)
        self.btn_auth.clicked.connect(self._try_pw)
        blay.addWidget(self.ent_pw)
        blay.addWidget(self.btn_auth)
        self.lb_info = QLabel("")
        self.lb_info.setFont(mono(7))
        self.lb_info.setStyleSheet("color:%s;font-size:7pt;background:"
                                   "transparent;" % "#565b7a")
        blay.addWidget(self.lb_info)
        root.addWidget(bot)
        self._ph = False
        pt = QTimer(self)
        pt.timeout.connect(self._pulse)
        pt.start(700)
        at = QTimer(self)
        at.timeout.connect(self._anim_tick)
        at.start(100)

        # ===== AREA UTAMA =====
        mid = QHBoxLayout()
        mid.setSpacing(7)
        root.addLayout(mid, 1)
        left = QVBoxLayout()
        left.setSpacing(5)
        mid.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(5)
        rw = QWidget()
        rw.setFixedWidth(342)
        rw.setLayout(right)
        mid.addWidget(rw)

        # ---- 1. SCANNER ----
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 6)
        pl.setSpacing(3)
        self._ptitle(pl, "MULTI-PAIR SCANNER", "\u25b2 AUTO SCAN \u2699",
                     ACC)
        tabs = QHBoxLayout()
        tabs.setContentsMargins(10, 0, 10, 0)
        tabs.setSpacing(5)
        tbl = QHBoxLayout()
        tbl.setContentsMargins(10, 0, 0, 0)
        tbl.setSpacing(5)
        self.tab_btns = {}
        for name in ("ALL", "FOREX", "GOLD/SILVER", "CRYPTO", "INDEX",
                     "COMMODITY"):
            b = QPushButton(name)
            b.setObjectName("tabbtn")
            b.setCheckable(True)
            b.setChecked(name == "ALL")
            b.clicked.connect(lambda _c=False, n=name: self._set_tab(n))
            tbl.addWidget(b)
            self.tab_btns[name] = b
        tbl.addStretch(1)
        tabs.addLayout(tbl)
        tabs.addStretch(1)
        pl.addLayout(tabs)
        # v3.57: kolom pengisi (stretch) di akhir -> STATUS nempel TREND
        cols = [("#", 26), ("SYMBOL", 86), ("PRICE", 90), ("SPREAD", 56),
                ("REGIME", 86), ("SIGNAL", 60), ("SCORE", 52), ("TREND", 50),
                ("STATUS", 90), ("SW", 40), ("LOT", 56), ("", 24)]
        self.tv = QTableWidget(0, len(cols))
        self.tv.setHorizontalHeaderLabels([c for c, _ in cols])
        self.tv.verticalHeader().setVisible(False)
        self.tv.setShowGrid(False)
        self.tv.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tv.setSelectionBehavior(QTableWidget.SelectRows)
        self.tv.setFocusPolicy(Qt.NoFocus)
        self.tv.setAlternatingRowColors(True)
        self.tv.verticalHeader().setDefaultSectionSize(20)
        self.tv.setFixedHeight(4 * 20 + 28)
        hh = self.tv.horizontalHeader()
        hh.setDefaultSectionSize(60)
        for i0, (_c, w) in enumerate(cols):
            self.tv.setColumnWidth(i0, w)
        hh.setSectionsClickable(False)
        hh.setStretchLastSection(True)
        self.tv.cellClicked.connect(self._on_select)
        # GLOBE CYBER (layout final USER v2): bola dunia berputar di
        # AREA BARIS KOSONG tabel -- DI BAWAH garis header, sebelah kanan
        # kolom STATUS (overlay kolom pengisi kosong; data tak tertutup).
        # v3.57 layout final v3 (user): globe BACKGROUND -- besar & agak
        # cakram solid DI DEPAN tabel: globe UTUH, terang penuh (tanpa
        # transparan), garis tabel tidak memotong.  Tabel ditinggikan ke
        # 4 baris supaya cakram 72px muat utuh di badan tabel.
        # v3.87 (user): globe berputar DIPINDAH ke dalam ring gauge
        # (dulu overlay tabel) -- lihat class Gauge.__init__
        pl.addWidget(self.tv)
        # v4.38 (user): panel LOT MANUAL -- selalu terlihat, isi lot
        # TANPA bergantung tombol di tabel (pilih pair -> tulis lot ->
        # ISI LOT).  Feedback sukses/gagal langsung di sebelahnya.
        lotrow = QHBoxLayout()
        lotrow.setSpacing(5)
        lb_lm = QLabel("LOT MANUAL:")
        lb_lm.setFont(sans(7, True))
        lb_lm.setStyleSheet("color:%s;font-size:7pt;font-weight:bold;"
                            "background:transparent;" % GOLD)
        lotrow.addWidget(lb_lm)
        self.cmb_syms = QComboBox()
        self.cmb_syms.setMinimumWidth(110)
        self.cmb_syms.setStyleSheet(
            "QComboBox{background:#0a0f1e;color:#e8c574;border:1px solid "
            "#243057;border-radius:4px;padding:2px 6px;font-size:8pt;}"
            "QComboBox QAbstractItemView{background:#0a0f1e;"
            "color:#e8c574;}")
        lotrow.addWidget(self.cmb_syms)
        self.ent_lot = QLineEdit()
        self.ent_lot.setPlaceholderText("0.05  (0=AUTO=terkecil)")
        self.ent_lot.setFixedWidth(110)
        self.ent_lot.setStyleSheet(
            "QLineEdit{background:#0a0f1e;color:#ffd270;border:1px solid "
            "#f0b429;border-radius:4px;padding:2px 6px;font-size:8pt;}")
        self.ent_lot.returnPressed.connect(self._apply_lot)
        lotrow.addWidget(self.ent_lot)
        btn_lot = QPushButton("ISI LOT LALU ENTER")
        btn_lot.setObjectName("tabbtn")
        btn_lot.setCursor(Qt.PointingHandCursor)
        btn_lot.clicked.connect(self._apply_lot)
        lotrow.addWidget(btn_lot)
        btn_alloff = QPushButton("SEMUA OFF")
        btn_alloff.setObjectName("tabbtn")
        btn_alloff.setCursor(Qt.PointingHandCursor)
        btn_alloff.clicked.connect(self._all_off)
        lotrow.addWidget(btn_alloff)
        self.lb_lot_info = QLabel("")
        self.lb_lot_info.setFont(mono(7))
        lotrow.addWidget(self.lb_lot_info)
        lotrow.addStretch(1)
        pl.addLayout(lotrow)
        left.addWidget(p)

        # ---- 2. CONFLUENCE ----
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 5)
        pl.setSpacing(2)
        bar = self._ptitle(pl, "STRATEGY CONFLUENCE", None)
        self.lb_cfsym = QLabel("( - )")
        self.lb_cfsym.setFont(mono(9, True))
        self.lb_cfsym.setStyleSheet("color:%s;font-size:9pt;font-weight:bold;"
                                    "background:transparent;" % GOLD)
        bar.layout().addWidget(self.lb_cfsym)
        self.lb_age = QLabel("")
        self.lb_age.setStyleSheet("color:#8a8fa8;font-size:8pt;font-weight:bold;padding:0 6px;")
        bar.layout().addWidget(self.lb_age)
        crow2 = QHBoxLayout()
        crow2.setContentsMargins(8, 0, 8, 0)
        crow2.setSpacing(10)
        self.gauge = Gauge(self)
        crow2.addWidget(self.gauge)
        cinfo = QVBoxLayout()
        cinfo.setSpacing(2)
        vrow = QHBoxLayout()
        vrow.setSpacing(14)
        self.lb_verdict = QLabel("WAIT")
        self.lb_verdict.setFont(mono(12, True))
        self.lb_verdict.setStyleSheet(
            "color:%s;background:%s;border:1px solid %s;border-radius:6px;"
            "padding:2px 12px;" % (AMBER, PAN2, DIM2))
        vrow.addWidget(self.lb_verdict)
        self.lb_score = QLabel("0%")
        self.lb_score.setFont(mono(12, True))
        self.lb_score.setStyleSheet("color:%s;font-size:12pt;font-weight:"
                                    "bold;background:transparent;"
                                    % DIM2)
        vrow.addWidget(self.lb_score)
        self.lb_valid = QLabel("[ STAND BY ]")
        self.lb_valid.setFont(sans(9, True))
        self.lb_valid.setStyleSheet("color:%s;font-size:9pt;font-weight:bold;"
                                    "background:transparent;" % DIM)
        vrow.addWidget(self.lb_valid)
        vrow.addStretch(1)
        cinfo.addLayout(vrow)
        self.bars = Bars(self)
        cinfo.addWidget(self.bars)
        crow2.addLayout(cinfo, 1)
        pl.addLayout(crow2)
        # v3.91: baris ">> sniper: ..." DIHAPUS dari tampilan
        # (mengganggu pandangan chart, permintaan user).  Alasan blokir
        # tetap bisa dilihat di panel status & API.
        self.lb_why = QLabel("")
        self.lb_why.hide()
        left.addWidget(p)

        # ---- 3. POSITIONS ----
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 6)
        pl.setSpacing(2)
        self.lb_post = self._ptitle(pl, "ACTIVE POSITIONS (0)", None)
        pcols = [("#", 26), ("SYMBOL", 84), ("TYPE", 46), ("LOT", 44),
                 ("ENTRY", 72), ("SL", 64), ("TP", 64), ("", 22),
                 ("PRICE", 70), ("P/L", 62), ("R", 40), ("STATUS", 62)]
        self.tvp = QTableWidget(0, len(pcols))
        self.tvp.setHorizontalHeaderLabels([c for c, _ in pcols])
        self.tvp.verticalHeader().setVisible(False)
        self.tvp.setShowGrid(False)
        self.tvp.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tvp.setSelectionMode(QTableWidget.NoSelection)
        self.tvp.setFocusPolicy(Qt.NoFocus)
        self.tvp.setAlternatingRowColors(True)
        self.tvp.verticalHeader().setDefaultSectionSize(20)
        self.tvp.setFixedHeight(2 * 20 + 28)
        hh = self.tvp.horizontalHeader()
        hh.setDefaultSectionSize(60)
        for i0, (_c, w) in enumerate(pcols):
            self.tvp.setColumnWidth(i0, w)
        hh.setStretchLastSection(True)
        pl.addWidget(self.tvp)
        left.addWidget(p)

        # ---- 4. CHART ----
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 2)
        pl.setSpacing(1)
        bar = QWidget()
        bl2 = QHBoxLayout(bar)
        bl2.setContentsMargins(10, 3, 10, 3)
        bl2.setSpacing(7)
        self.lb_chsym = QLabel("-")
        self.lb_chsym.setFont(mono(10, True))
        self.lb_chsym.setStyleSheet("color:%s;font-size:10pt;font-weight:"
                                    "bold;background:transparent;" % TX)
        bl2.addWidget(self.lb_chsym)
        tf = QLabel(" M15 ")
        tf.setFont(mono(7, True))
        tf.setStyleSheet("color:%s;background:%s;border-radius:5px;"
                         "padding:1px 5px;" % (GOLD, "#1a1a28"))
        bl2.addWidget(tf)
        bl2.addStretch(1)
        self.lb_chpct = QLabel("")
        self.lb_chpct.setFont(mono(9, True))
        self.lb_chpct.setStyleSheet("font-size:9pt;font-weight:bold;"
                                    "background:transparent;")
        bl2.addWidget(self.lb_chpct)
        self.lb_chpx = QLabel("-")
        self.lb_chpx.setFont(mono(11, True))
        self.lb_chpx.setStyleSheet("font-size:11pt;font-weight:bold;"
                                   "background:transparent;")
        bl2.addWidget(self.lb_chpx)
        pl.addWidget(bar)
        self.chart = Chart(self)
        pl.addWidget(self.chart, 1)
        left.addWidget(p, 1)

        # ===== KOLOM KANAN =====
        # EXECUTION LOG
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 6)
        pl.setSpacing(2)
        self.log_panel = p
        p.rain = True
        tbar = self._ptitle(pl, "EXECUTION LOG", None)
        self.lb_rec = QLabel("[ REC   ]")
        self.lb_rec.setFont(mono(7, True))
        self.lb_rec.setStyleSheet("color:%s;font-size:7pt;font-weight:bold;"
                                  "background:transparent;" % "#4a4f6a")
        tbar.layout().addWidget(self.lb_rec)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet("background:transparent;border:none;")
        pl.addWidget(self.txt, 1)
        right.addWidget(p, 1)

        # SESSIONS + MARKET (gabung kompak, mentok bawah)
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 5)
        pl.setSpacing(1)
        self._ptitle(pl, "SESSIONS \u00b7 MARKET", None)
        self.sess_info = {}
        self.sessw = SessionCompact(self)
        pl.addWidget(self.sessw)
        right.addWidget(p)

        # MODULES
        p = Panel()
        pl = QVBoxLayout(p)
        pl.setContentsMargins(2, 0, 2, 6)
        pl.setSpacing(3)
        self._ptitle(pl, "MODULES", None)
        grid = QGridLayout()
        grid.setContentsMargins(4, 0, 4, 4)
        grid.setSpacing(3)
        self.lb_mods = {}
        mods = [("\u25c8", "SCANNER"), ("\u2316", "STRATEGY"),
                ("\u25b2", "RISK MANAGER"), ("\u26a1", "TRADE ENGINE"),
                ("\u25ce", "TRAILING SYSTEM"), ("\u270e", "NEWS FILTER")]
        for i0, (ic, nm) in enumerate(mods):
            f = QFrame()
            f.setStyleSheet("QFrame{background:qlineargradient(y1:0,y2:1,"
                            "stop:0 #15151f,stop:1 #0f0f17);"
                            "border:1px solid #1e1e30;border-radius:6px;}")
            v = QVBoxLayout(f)
            v.setContentsMargins(4, 2, 2, 2)
            v.setSpacing(0)
            t = QLabel(ic + " " + nm)
            fs = sans(6, True)
            t.setFont(fs)
            t.setStyleSheet("color:%s;font-size:6pt;font-weight:bold;"
                            "background:transparent;" % TX)
            lbv = QLabel("[off]")
            lbv.setFont(mono(7, True))
            lbv.setStyleSheet("color:%s;font-size:7pt;font-weight:bold;"
                              "background:transparent;" % DIM2)
            v.addWidget(t)
            v.addWidget(lbv)
            grid.addWidget(f, i0 // 3, i0 % 3)
            self.lb_mods[nm] = lbv
        for c0 in range(3):
            grid.setColumnStretch(c0, 1)
        pl.addLayout(grid)
        right.addWidget(p)

        self.scan = Scanlines(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "scan", None):
            self.scan.setGeometry(self.rect())

    # ---- interaksi ----
    def _set_tab(self, n):
        self.tab = n
        for nm, b in self.tab_btns.items():
            b.setChecked(nm == n)
        if self.snap:
            self._apply(self.snap)


    def eventFilter(self, obj, ev):
        return super().eventFilter(obj, ev)

    def _on_select(self, row, _col):
        if _col == 9:   # v4.36: klik area kolom SW -> toggle
            it1 = self.tv.item(row, 1)
            if it1 is None:
                return
            sym = it1.text()
            self._toggle_sw(sym, not self._sw_map.get(sym, False))
            return
        it = self.tv.item(row, 1)
        if it:
            self.sel_sym = it.text()
            self._sync_lot_panel(it.text())   # v4.39: panel ikut pair
            if self.snap:
                self._apply(self.snap)

    def _toggle_sw(self, sym, on, btn=None):
        """v4.36: toggle switch pair -- feedback instan (border hijau/
        merah), lalu kirim ke engine (snapshot berikut menyegarkan)."""
        self._sw_map[sym] = bool(on)
        self.sel_sym = sym
        self._sync_lot_panel(sym)   # v4.39: panel ikut pair yang diklik
        if btn is not None:
            try:
                btn.setText("ON" if on else "OFF")
                btn.setStyleSheet(_SW_ON if on else _SW_OFF)
            except Exception:
                pass
        threading.Thread(target=self._sw_bg, args=(sym, bool(on)),
                         daemon=True).start()

    def _sync_lot_panel(self, sym):
        """v4.39 (user): klik pair di tabel -> panel LOT MANUAL otomatis
        pindah ke pair itu (tak perlu cari di dropdown lagi); isian lot
        terisi nilai pair tersebut (kosong = AUTO)."""
        sym = str(sym or "").upper()
        try:
            idx = self.cmb_syms.findText(sym)
            if idx >= 0:
                self.cmb_syms.setCurrentIndex(idx)
        except Exception:
            pass
        try:
            lot = float(self._lot_map.get(sym, 0) or 0)
            self.ent_lot.setText(("%g" % lot) if lot > 0 else "")
        except Exception:
            pass

    def _set_lot_info(self, txt, col):
        """v4.38: feedback panel LOT (thread-safe via sig.lot)."""
        try:
            self.lb_lot_info.setText(str(txt))
            self.lb_lot_info.setStyleSheet(
                "color:%s;font-size:7pt;font-weight:bold;"
                "background:transparent;" % col)
        except Exception:
            pass

    def _apply_lot_panel(self, s):
        syms = []
        for r0 in (s.get("scanner") or []):
            s0 = str(r0.get("symbol") or "")
            if s0 and s0 not in syms:
                syms.append(s0)
        cur = self.cmb_syms.currentText()
        self.cmb_syms.blockSignals(True)
        self.cmb_syms.clear()
        self.cmb_syms.addItems(syms)
        if cur in syms:
            self.cmb_syms.setCurrentText(cur)
        self.cmb_syms.blockSignals(False)

    def _apply_lot(self):
        """v4.38 (user): tombol ISI LOT di panel -- selalu bisa dipakai."""
        sym = str(self.cmb_syms.currentText() or "").strip().upper()
        if not sym:
            self._set_lot_info("PILIH PAIR DULU", RED)
            return
        txt = str(self.ent_lot.text() or "").strip().replace(",", ".")
        try:
            lot = float(txt) if txt else 0.0
        except ValueError:
            self._set_lot_info("ANGKA TIDAK VALID", RED)
            return
        if lot < 0:
            lot = 0.0
        self._set_lot_info("MENGIRIM %s = %s ..."
                           % (sym, ("%g" % lot) if lot > 0 else "AUTO"),
                           "#f0b429")
        self.sel_sym = sym
        threading.Thread(target=self._lot_bg, args=(sym, lot),
                         daemon=True).start()

    def _all_off(self):
        """v4.42 (user): matikan SEMUA switch -- perbaiki state tersimpan
        yang tak diinginkan (mis. pair nyala sendiri saat testing)."""
        threading.Thread(target=self._all_off_bg, daemon=True).start()

    def _all_off_bg(self):
        for p in self._post_ports():
            try:
                body, code = self.client.pairs_reset(p)
                if code == 200:
                    self.sig.lot.emit("SEMUA SWITCH DIMATIKAN", GRN)
                    return
            except Exception:
                pass
        self.sig.lot.emit("GAGAL reset -- engine tidak merespons", RED)

    def _post_ports(self):
        """v4.38: port engine UTAMA = yang terbukti hidup (active_port),
        sisanya cadangan -- POST tidak lagi salah sasaran."""
        pts = ([self.active_port] if self.active_port else []) + \
              [p for p in self.ports if p != self.active_port]
        return pts

    def _sw_bg(self, sym, on):
        for p in self._post_ports():
            try:
                body, code = self.client.pair_switch(p, sym, on)
                if code == 200:
                    self.sig.lot.emit(
                        "SWITCH %s = %s TERSIMPAN" % (sym, "ON" if on
                                                      else "OFF"), GRN)
                    return
            except Exception:
                pass
        self.sig.lot.emit("GAGAL %s -- engine tidak merespons" % sym, RED)

    def _edit_lot(self, sym, cur, btn=None):
        """v4.37 (user): dialog isi lot manual utk pair ini."""
        self._sync_lot_panel(sym)   # v4.39: panel ikut pair yang diklik
        val, ok = QInputDialog.getDouble(
            self, "LOT " + str(sym),
            "Isi lot MANUAL untuk %s\n(0 = AUTO, pakai kalkulasi risiko):"
            % str(sym),
            value=float(cur or 0.0), min=0.0, max=500.0, decimals=2)
        if not ok:
            return
        self._lot_map[sym] = val
        if btn is not None:
            try:
                btn.setText(("%g" % val) if val > 0 else "AUTO")
            except Exception:
                pass
        self.sel_sym = sym
        threading.Thread(target=self._lot_bg, args=(sym, val),
                         daemon=True).start()

    def _lot_bg(self, sym, lot):
        for p in self._post_ports():
            try:
                body, code = self.client.pair_lot(p, sym, lot)
                if code == 200:
                    self.sig.lot.emit(
                        "%s = %s TERSIMPAN" % (sym, ("%g" % lot) if lot > 0
                                               else "AUTO"), GRN)
                    return
            except Exception:
                pass
        self.sig.lot.emit("GAGAL %s -- engine tidak merespons "
                          "(cek jendela engine)" % sym, RED)

    def _halt(self):
        threading.Thread(target=self._halt_bg, daemon=True).start()

    def _try_pw(self):
        if self.client.login(self.active_port or self.ports[0],
                             self.ent_pw.text()):
            self.ent_pw.setText("")

    def _pulse(self):
        self._ph = not self._ph
        col = getattr(self, "_led_col", AMBER)
        self.led.set_col(col, self._ph)

    def _anim_tick(self):
        # sapuan gauge menuju skor target (ease-out)
        tgt = self.g_sc
        if abs(tgt - self.g_disp) > 0.05:
            self.g_disp += (tgt - self.g_disp) * 0.18
            if abs(tgt - self.g_disp) <= 0.05:
                self.g_disp = tgt
            self.gauge.update()
        # glow kartu: kilat saat nilai berubah + hover
        for _v, _s, card in self.cards:
            want = 20 + card.flash * 26 + (14 if card.hover else 0)
            if abs(card.glow.blurRadius() - want) > 0.5:
                card.glow.setBlurRadius(want)
            if card.flash > 0:
                card.flash = max(0.0, card.flash - 0.12)
        # aurora berjalan
        self.aurora_ph = (self.aurora_ph + 0.02) % 1.0
        self.aurora.update()
        # denyut titik harga live (5 fps)
        self._aph = not getattr(self, "_aph", False)
        self.chart.update()
        self.log_panel.update()
        self.sessw.update()
        if self._aph:
            self.lb_rec.setText("[ REC \u25cf ]")
            self.lb_rec.setStyleSheet("color:%s;font-size:7pt;font-weight:"
                                      "bold;background:transparent;" % RED)
        else:
            self.lb_rec.setText("[ REC   ]")
            self.lb_rec.setStyleSheet("color:%s;font-size:7pt;font-weight:"
                                      "bold;background:transparent;"
                                      % "#4a4f6a")

    # ---- polling ----
    def _poll_loop(self):
        while True:
            data = None
            for port in self.ports:
                cl = EngineClient()
                cl.cookie = self.client.cookie
                body, code = cl._get(port, "/api/status", timeout=2.5)
                if code == 200:
                    try:
                        data = json.loads(body)
                        self.client.cookie = cl.cookie
                        self.active_port = port
                    except ValueError:
                        data = {"error": "offline"}
                    break
                if code == 401:
                    data = {"error": "auth"}
                    self.client.cookie = cl.cookie
                    break
            if data is None:
                data = {"error": "offline"}
            self.sig.data.emit(data)
            time.sleep(2.0)

    def _on_data(self, data):
        if isinstance(data, dict) and "error" not in data:
            self.snap = data
            self.need_auth = False
            self.ent_pw.setVisible(False)
            self.btn_auth.setVisible(False)
            self._apply(data)
        elif isinstance(data, dict) and data.get("error") == "auth":
            if not self.need_auth:
                self.need_auth = True
                self.lb_status.setText(
                    "AKSES DITOLAK \u2014 ISI PASSWORD LALU TEKAN [PASSWORD]")
                self.lb_status.setStyleSheet(
                "color:%s;font-size:10pt;font-weight:bold;background:"
                "transparent;" % RED)
                self.led.set_col(RED)
                self.ent_pw.setVisible(True)
                self.btn_auth.setVisible(True)
        else:
            self.led.set_col(RED)
            self.lb_status.setText(
                "ENGINE OFFLINE \u2014 JALANKAN MULAI_SEMUA.BAT DULU")
            self.lb_status.setStyleSheet(
                "color:%s;font-size:10pt;font-weight:bold;background:"
                "transparent;" % RED)

    def _led(self, col):
        self._led_col = col
        self.led.set_col(col)

    # ---- penerapan data ----
    def _apply(self, s):
        # v3.67 ANTI DATA BEKU: snapshot > 120 dtk (engine mati/ditutup)
        # -> kartu harian DIKOSONGKAN + chip engine merah.  Dulu: angka
        # terakhir tetap tampak spt data hidup (keliru disangka belum reset)
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

        self.lb_clock.setText(((s.get("ts_wib")
                                or s.get("ts")
                                or "--:--:--")[11:]) + " WIB")
        _te = s.get("ts_epoch")
        if _te:
            _age = max(0, int(time.time() - float(_te)))
            _ac = "#2ee6a8" if _age <= 15 else ("#f5a623" if _age <= 60 else "#ff2d55")
            _at = "DATA BARU" if _age <= 15 else ("DATA %ds" % _age if _age <= 60 else "DATA LAMA %ds" % _age)
            self.lb_age.setText(_at)
            self.lb_age.setStyleSheet("color:%s;font-size:8pt;font-weight:bold;padding:0 6px;" % _ac)


        chipstyle = ("color:%s;font-size:9pt;font-weight:bold;"
                     "background:transparent;font-family:%s;")
        if beku:
            self.ch["PYTHON ENGINE"][1].setText(
                "\u25cf OFFLINE (DATA BEKU %s)" % (_st[11:16] or "--:--"))
            self.ch["PYTHON ENGINE"][1].setStyleSheet(
                chipstyle % (RED, MONO))
        else:
            self.ch["PYTHON ENGINE"][1].setText(
                "\u25cf ONLINE v%s" % s.get("version", "-"))
            self.ch["PYTHON ENGINE"][1].setStyleSheet(
                chipstyle % (GRN, MONO))
        self.ch["MTS"][1].setText(
            "\u25cf CONNECTED" if conn else "\u25cf SIMULASI")
        self.ch["MTS"][1].setStyleSheet(
            chipstyle % (GRN if conn else AMBER, MONO))
        self.ch["MTS"][0].findChild(QLabel, "chipt").setText(
            s.get("terminal", "MT5"))   # v3.87 (user): tanpa nama server
        self.ch["AKUN"][1].setText("%s #%s" % (mode, acc.get("login", "-")))
        self.ch["AKUN"][1].setStyleSheet(chipstyle % (TX, MONO))
        if rsk.get("halted"):
            self.ch["RISK MANAGER"][1].setText("\u25cf HALTED")
            self.ch["RISK MANAGER"][1].setStyleSheet(chipstyle % (RED, MONO))
        elif rsk.get("pause_until", 0) > 0:
            self.ch["RISK MANAGER"][1].setText("\u25cf PAUSED")
            self.ch["RISK MANAGER"][1].setStyleSheet(chipstyle % (AMBER, MONO))
        else:
            self.ch["RISK MANAGER"][1].setText("\u25cf ACTIVE")
            self.ch["RISK MANAGER"][1].setStyleSheet(chipstyle % (GRN, MONO))
        self.ch["DAILY PROTECTION"][1].setText(
            "\u25cf LOSS LIMIT" if rsk.get("halted") else "\u25cf ACTIVE")
        self.ch["DAILY PROTECTION"][1].setStyleSheet(
            chipstyle % (RED if rsk.get("halted") else GRN, MONO))
        self.ch["WEEKEND GUARD"][1].setText("\u25cf ACTIVE")
        self.ch["WEEKEND GUARD"][1].setStyleSheet(chipstyle % (GRN, MONO))

        # tape
        self.tape_segs = []
        for r in s.get("scanner") or []:
            pc = float(r.get("trend_pct", 0) or 0)
            self.tape_segs.append((
                r.get("symbol"), fmt(r.get("price"), r.get("digits", 2)),
                "\u25b2" if pc >= 0 else "\u25bc", "%.2f%%" % abs(pc),
                GRN if pc >= 0 else RED))
        self.tape.update()

        # cards
        rp = lambda v: fmt(abs(float(v or 0)), 0 if abs(float(v or 0)) >= 1000
                           else 2)
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
            # kartu harian (PROFIT/LOSS/DRAWDOWN/KOMISI) dikosongkan --
            # jangan tampilkan angka lama spt data hidup
            for _i in (2, 3, 5, 6):
                card_vals[_i] = ("-", RED, "DATA BEKU %s - engine offline, "
                                 "jalankan bat" % (_st[11:16] or "--:--"))
        for (val, sub, card), (v0, _c, s0) in zip(self.cards, card_vals):
            if val.text() != v0:
                card.flash = 1.0
            val.setText(v0)
            sub.setText(s0)
            card.barw.update()
            if card.spark:
                card.spark.update()

        # scanner
        rows = s.get("scanner") or []
        st_col = {"TRADING": AMBER, "READY": GRN, "HOLD": CY, "BLOCKED": TX,
                  "WAIT": TX}
        keep = []
        self.tv.setRowCount(0)
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
            if stag not in st_col:
                stag = "WAIT"
            sc = float(r.get("score", 0) or 0)
            reg = (r.get("regime") or "-").split(" ")[0]
            swv = "ON" if r.get("sw") else "OFF"
            self._sw_map[r.get("symbol")] = bool(r.get("sw"))
            ulot = float(r.get("lot") or 0.0)
            self._lot_map[r.get("symbol")] = ulot
            lotv = ("%g" % ulot) if ulot > 0 else "AUTO"
            vals = ("%02d" % i, r.get("symbol"),
                    fmt(r.get("price"), r.get("digits", 2)), r.get("spread"),
                    reg, sig, "%.0f%%" % sc, str(tb) + "%", stag, swv, lotv)
            r0 = self.tv.rowCount()
            self.tv.insertRow(r0)
            for c0, v0 in enumerate(vals):
                if c0 == 10:
                    # v4.37 (user): tombol LOT -- klik = dialog isi lot
                    lotbtn = QPushButton(str(v0))
                    lotbtn.setStyleSheet(_LOT_QSS)
                    lotbtn.setCursor(Qt.PointingHandCursor)
                    lotbtn.clicked.connect(
                        lambda _c=False, s=r.get("symbol"),
                        u=ulot, w=lotbtn: self._edit_lot(s, u, w))
                    self.tv.setCellWidget(r0, 10, lotbtn)
                    continue
                if c0 == 9:
                    # v4.36 (user): tombol SW dgn BORDER -- ON hijau,
                    # OFF merah; klik tombol = toggle langsung
                    btn = QPushButton(str(v0))
                    btn.setStyleSheet(_SW_ON if r.get("sw") else _SW_OFF)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(
                        lambda _c=False, s=r.get("symbol"),
                        cur=bool(r.get("sw")), w=btn:
                        self._toggle_sw(s, not cur, w))
                    self.tv.setCellWidget(r0, 9, btn)
                    continue
                it = QTableWidgetItem(str(v0))
                it.setFont(mono(8, c0 == 1))
                it.setForeground(QColor(st_col.get(stag, TX))
                                 if c0 in (5, 8) else QColor(TX))
                self.tv.setItem(r0, c0, it)
            keep.append(r.get("symbol"))
        if self.sel_sym and self.sel_sym in keep:
            self.tv.selectRow(keep.index(self.sel_sym))
        self._apply_lot_panel(s)

        # confluence + chart
        self._apply_cf(s)

        # positions
        self.tvp.setRowCount(0)
        for j, pp in enumerate(s.get("positions") or []):
            digits = pp.get("digits") or 2
            vals = ("%02d" % (j + 1), pp.get("symbol"), pp.get("type"),
                    "%.2f" % float(pp.get("lot", 0) or 0),
                    fmt(pp.get("entry"), digits),
                    fmt(pp.get("sl"), digits) if pp.get("sl") else "-",
                    fmt(pp.get("tp"), digits) if pp.get("tp") else "-",
                    "", fmt(pp.get("price"), digits),
                    ("+" if float(pp.get("pl", 0) or 0) >= 0 else "")
                    + fmt(pp.get("pl")), "-",
                    "Trailing" if pp.get("trailing") else "Open")
            r0 = self.tvp.rowCount()
            self.tvp.insertRow(r0)
            plcol = GRN if float(pp.get("pl", 0) or 0) >= 0 else RED
            for c0, v0 in enumerate(vals):
                it = QTableWidgetItem(str(v0))
                it.setFont(mono(8))
                it.setForeground(QColor(plcol) if c0 in (1, 2, 9)
                                 else QColor(TX))
                self.tvp.setItem(r0, c0, it)
        for w0 in self.lb_post.findChildren(QLabel):
            if w0.text().startswith("ACTIVE POSITIONS") or \
                    "POSITIONS" in w0.text():
                w0.setText("ACTIVE POSITIONS (%d)" % npos)

        # log
        html = []
        for ln in list(s.get("log") or [])[::-1]:
            tag = (ln.get("tag") or "INFO").upper()
            col = LOG_TAG_COL.get(tag, "#9aa2c8")
            html.append("<span style='color:#3f7a5c'>[%s]</span> "
                        "<span style='color:%s'>[ %s ]</span> "
                        "<span style='color:#a9ffd0'>%s</span>" % (
                            ln.get("ts", ""), col, tag,
                            (ln.get("msg", "") or "")))
        html.append("<span style='color:%s'>root@rbt-fx:~$ \u258a</span>"
                    % GOLD)
        self.txt.setHtml("<br>".join(html))

        # sessions
        try:
            ts = s.get("ts", "")
            hh, mm = int(ts[11:13]), int(ts[14:16])
        except (ValueError, IndexError):
            hh, mm = time.gmtime().tm_hour, time.gmtime().tm_min
        self.hr = hh + mm / 60.0
        for k in ("SYDNEY", "TOKYO", "LONDON", "NEW YORK"):
            v = (s.get("sessions") or {}).get(k) or {}
            op = bool(v.get("open", False))
            self.sess_info[k] = (op, "%02d:%02d %s" % (
                hh, mm, "(Open)" if op else "(Closed)"))
        self.sessw.update()

        # modules
        mods = s.get("modules") or {}
        keymap = {"SCANNER": "scanner", "STRATEGY": "strategy",
                  "RISK MANAGER": "risk", "TRADE ENGINE": "trade",
                  "TRAILING SYSTEM": "trailing", "NEWS FILTER": "news"}
        for nm, lbv in self.lb_mods.items():
            on = bool(mods.get(keymap.get(nm, nm.lower()), False))
            lbv.setText("[ON]" if on else "[OFF]")
            lbv.setStyleSheet("color:%s;font-size:7pt;font-weight:bold;"
                              "background:transparent;"
                              % (GRN if on else "#4a4f6a"))

        # account + info
        up = int(s.get("uptime_min", 0) or 0)
        upt = ((str(up // 1440) + "D ") if up >= 1440 else "") + \
              "%02d:%02d" % (up // 60 % 24, up % 60)
        self.lb_info.setText(
            "UPTIME %s  \u25c6  PING %s ms  \u25c6  LOOP %s ms  \u25c6  %d PAIRS  \u25c6  v%s" % (
                upt, s.get("ping_ms", "-"), s.get("loop_ms", "-"),
                len(rows), s.get("version", "-")))

        # statusline
        if rsk.get("halted"):
            msg, c0 = "TRADING HALTED \u2014 DAILY LOSS LIMIT ACTIVE", RED
        elif rsk.get("manual_halt"):
            msg, c0 = "MANUAL HALT \u2014 NO NEW ORDERS", RED
        elif conn:
            msg, c0 = "ALL SYSTEMS OPERATIONAL [%s]" % mode, GRN
        else:
            msg, c0 = "LINK DOWN - RETRYING...", AMBER
        self.lb_status.setText(msg)
        self.lb_status.setStyleSheet("color:%s;font-size:10pt;font-weight:"
                                     "bold;background:transparent;" % c0)
        self._led(c0)
        # v3.95: label tombol = STATUS (bukan aksi): jalan=ON, halt=OFF
        halted = bool(rsk.get("manual_halt"))
        self.btn_halt.setText("⏸ OFF" if halted else "⚡ ON")
        self.btn_halt.setToolTip(
            "TRADING BERHENTI (MANUAL HALT) — klik untuk ON lagi"
            if halted else
            "TRADING AKTIF — klik untuk HALT (hentikan order baru)")
        if halted != getattr(self, "_halt_state", None):
            self._halt_state = halted
            self.btn_halt.setProperty("hstate", "off" if halted else "on")
            _st = self.btn_halt.style()
            _st.unpolish(self.btn_halt)
            _st.polish(self.btn_halt)
        # v3.96: versi di judul window (bukti update terlihat)
        _v = str(s.get("version") or "")
        if _v and getattr(self, "_vttl", "") != _v:
            self._vttl = _v
            self.setWindowTitle("RBT FX :: TRADING ALGO SYSTEM  v" + _v)
        # v3.97: dashboard IKUT dimuat ulang bila versi engine
        # berubah (proses dashboard terpisah dr engine -- engine yang
        # lama tidak akan pernah memuat kode baru sendiri)
        if _v:
            if not getattr(self, "_boot_ver", ""):
                self._boot_ver = _v
            elif (_v != self._boot_ver
                    and not getattr(self, "_restarting", False)):
                self._restarting = True
                self.lb_status.setText(
                    "ENGINE v" + _v + " TERPASANG - DASHBOARD DIMUAT "
                    "ULANG OTOMATIS...")
                _rbt_self_exec()

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
        # v4.41: baris terpilih sesaat TANPA candle (NO-DATA / fetch MT5
        # gagal) -> pakai baris ber-candle lain; chart TIDAK pernah kosong
        if top is not None and not (top.get("ohlc") or []):
            for r in rows:
                if r.get("ohlc"):
                    top = r
                    break
        if not top:
            return
        self.cf_top = top
        sym, sig, sc = top.get("symbol", "-"), top.get("signal", "-"), \
            float(top.get("score", 0) or 0)
        status = top.get("status", "")
        self.lb_cfsym.setText("( %s - %s )" % (sym, sig if sc >= 70 else "-"))
        cc = (GRN if sig == "BUY" else RED) if sc >= 70 else \
            (AMBER if sc >= 55 else DIM2)
        self.g_sc = sc
        self.g_cc = cc
        self.gauge.update()
        self.lb_score.setText("%.0f%%" % sc)
        self.lb_score.setStyleSheet("color:%s;font-size:12pt;font-weight:"
                                    "bold;background:transparent;" % cc)
        valid = status in ("READY", "TRADING")
        vcol = (GRN if sig == "BUY" else RED) if valid else AMBER
        self.lb_verdict.setText(
            ("BUY \u25b2" if sig == "BUY" else "SELL \u25bc") if valid
            else "WAIT")
        self.lb_verdict.setStyleSheet(
            "color:%s;background:%s;border:1px solid %s;border-radius:6px;"
            "padding:2px 12px;" % (vcol, PAN2, vcol))
        self.lb_valid.setText(
            "[ ENTRY VALID ]" if valid else
            ("[ HOLD - CARI MOMEN ]" if status == "SNIPER_WAIT"
             else "[ STAND BY ]"))
        self.lb_valid.setStyleSheet(
            "color:%s;font-size:9pt;font-weight:bold;background:transparent;"
            % (GRN if valid else (AMBER if status == "SNIPER_WAIT" else DIM)))
        # v3.91: teks ">> ..." tidak ditampilkan lagi (permintaan user)
        self.lb_why.setText("")
        self.bars.update()
        self.chart.set_top(top)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=None,
                    help="paksa port engine (default auto 8081/8080)")
    ap.add_argument("--shot", default=None,
                    help="screenshot ke file lalu keluar (mode uji)")
    args = ap.parse_args()
    ports = [args.port] if args.port else PORTS
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    d = Dash(ports=ports, shot=args.shot)
    d.show()

    def shot_now():
        pix = d.grab()
        pix.save(args.shot)
        print("SHOT SAVED", args.shot)
        app.quit()

    if args.shot:
        QTimer.singleShot(8000, shot_now)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
