"""v4.33 (permintaan user): kartu statistik Qt/Tk terlalu besar ->
diperkecil & dirapikan. Test penjaga: konstanta baru ada, lama hilang."""
import os

PYDIR = os.path.join(os.path.dirname(__file__), "..", "python")


def _src(fname):
    return open(os.path.join(PYDIR, fname), encoding="utf-8").read()


def test_qt_kartu_lebih_kecil():
    s = _src("cc_qtdashboard.py")
    assert "setMinimumHeight(58)" in s          # dulu 86
    assert "setMinimumHeight(86)" not in s
    assert "mono(10, True)" in s                # nilai utama, dulu mono(13)
    assert "mono(13, True)" not in s
    assert "icf.setFixedSize(17, 17)" in s      # dulu 22x22
    assert "font-size:8.5pt" in s               # ikon
    assert "font-size:6.5pt" in s               # judul & subjudul
    assert "setContentsMargins(8, 4, 8, 5)" in s
    assert "setBlurRadius(14)" in s             # dulu 20 (bloom tipis)
    assert "crow.setSpacing(5)" in s            # dulu 7


def test_qt_garis_hero_tidak_ikut_dikecilkan():
    s = _src("cc_qtdashboard.py")
    # garis emas dekoratif di bawah hero tetap 3px (bukan bagian kartu)
    assert s.count("setFixedHeight(3)") == 1    # garis hero tetap 3px
    # _Bar kartu kini 2px (konteks unik class _Bar)
    assert "self.acc = acc\n        self.setFixedHeight(2)" in s


def test_tk_kartu_paritas_kecil():
    s = _src("cc_tkdashboard.py")
    assert "bg=BG, height=64," in s             # dulu 92
    assert "H = 64" in s
    assert "ds = 17" in s                       # dulu 22
    assert 'size=10, weight="bold"' in s        # nilai, dulu 12
    assert 'size=8, weight="bold"' in s         # fallback nilai
    assert "height=92" not in s


def test_versi_maju():
    s = _src("cc_config.py")
    assert 'CC_VERSION = "4.33"' in s
