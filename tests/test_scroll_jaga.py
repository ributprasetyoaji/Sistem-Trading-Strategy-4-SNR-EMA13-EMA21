# -*- coding: utf-8 -*-
"""v4.47 (user): scroll tabel pair tidak boleh lompat ke atas saat
refresh.  Guard AST pada cc_qtdashboard._apply:
  1. posisi scrollbar dibaca SEBELUM setRowCount(0);
  2. dikembalikan SETELAH rebuild (setValue(min(vprev, maximum)));
  3. selectRow hanya bila baris seleksi benar-benar pindah (dulu
     selectRow tiap tick ikut menggeser tampilan)."""
import ast
import os

PYDIR = os.path.join(os.path.dirname(__file__), "..", "python")


def _apply_src():
    src = open(os.path.join(PYDIR, "cc_qtdashboard.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply":
            return ast.get_source_segment(src, node)
    raise AssertionError("method _apply tidak ditemukan")


def test_scroll_disimpan_sebelum_rebuild():
    src = _apply_src()
    iv = src.find("_vprev = _vsb.value()")
    iw = src.find("self.tv.setRowCount(0)")
    assert iw != -1, "rebuild tabel hilang?"
    assert iv != -1 and iv < iw, \
        "posisi scroll harus dibaca SEBELUM setRowCount(0)"


def test_scroll_dikembalikan_setelah_rebuild():
    src = _apply_src()
    ir = src.find("_vsb.setValue(min(_vprev, _vsb.maximum()))")
    iw = src.find("self.tv.setRowCount(0)")
    iend = src.find("self._apply_lot_panel(s)")
    assert ir != -1, "scroll tidak dikembalikan"
    assert iw < ir < iend, \
        "restore scroll harus SETELAH rebuild, sebelum lanjut panel lot"


def test_selectrow_tidak_menggeser_tiap_tick():
    src = _apply_src()
    ig = src.find("if self.tv.currentRow() != want:")
    isel = src.find("self.tv.selectRow(want)")
    assert ig != -1 and isel != -1 and ig < isel, \
        "selectRow harus dibungkus guard currentRow (dulu tiap tick menggeser)"
