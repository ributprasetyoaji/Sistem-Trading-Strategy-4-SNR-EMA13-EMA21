"""v4.32: tab GOLD/SILVER Qt+Tk -- BUG lama: cat_of()->'GOLD' vs self.tab->
'GOLD/SILVER' tak pernah sama -> tab selalu kosong. Test ini menjalankan
cat_of ASLI (diekstrak via ast) + memastikan filter memakai peta label."""
import ast
import os
import re

PYDIR = os.path.join(os.path.dirname(__file__), "..", "python")
LABEL_MAP = '{"GOLD/SILVER": "GOLD"}'


def _load(fname):
    src = open(os.path.join(PYDIR, fname), encoding="utf-8").read()
    ns = {"re": re}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            nm = node.targets[0].id
            if nm.startswith("CAT_") or nm.startswith("_RX_"):
                exec(compile(ast.get_source_segment(src, node), fname, "exec"), ns)
        if isinstance(node, ast.FunctionDef) and node.name == "cat_of":
            exec(compile(ast.get_source_segment(src, node), fname, "exec"), ns)
    return ns, src


def test_qt_cat_of_runtime():
    ns, _ = _load("cc_qtdashboard.py")
    f = ns["cat_of"]
    assert f("XAUUSD") == "GOLD"
    assert f("XAGUSD") == "GOLD"
    assert f("GOLD.a") == "GOLD"
    assert f("XAUUSD.r") == "GOLD"
    assert f("xauusdm") == "GOLD"
    assert f("EURUSD") == "FOREX"
    assert f("EURUSD-i") == "FOREX"
    assert f("BTCUSD.a") == "CRYPTO"
    assert f("US30.cash") == "INDEX"
    assert f("XTIUSD") == "COMMODITY"


def test_tk_cat_of_runtime():
    ns, _ = _load("cc_tkdashboard.py")
    f = ns["cat_of"]
    assert f("XAUUSD") == "GOLD"
    assert f("GOLD.a") == "GOLD"
    assert f("XAGUSD.r") == "GOLD"
    assert f("EURUSD") == "FOREX"


def test_filter_qt_pakai_peta_label():
    _, src = _load("cc_qtdashboard.py")
    assert "_TAB_CAT.get(self.tab" in src
    assert LABEL_MAP in src
    assert 'cat_of(r.get("symbol")) != _tabc' in src


def test_filter_tk_pakai_peta_label():
    _, src = _load("cc_tkdashboard.py")
    assert "_TAB_CAT.get(self.tab" in src
    assert LABEL_MAP in src
    assert 'cat_of(r.get("symbol")) != _tabc' in src
