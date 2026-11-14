# -*- coding: utf-8 -*-
"""CC SELF-UPDATE (v3.74, permintaan user: "refresh tanpa mulai ulang
bat"): engine memperbarui file KODE dari repo GitHub-nya sendiri, lalu
engine di-restart via /api/update (tombol UPDATE di dashboard).

KEAMANAN FILE (allowlist KETAT):
  - Hanya path berawalan "python/" + "requirements.txt" yang boleh
    ditulis.  .bat / data/ / tests/ / state TIDAK PERNAH disentuh.
  - File ditulis tmp + os.replace (atomic; gagal = file lama utuh).
  - Tanpa token -> fitur off (return None, tidak pernah raise).
"""
import base64
import hashlib
import json
import os
import re
import urllib.request

REPO = "ributprasetyoaji/Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
BRANCH = "main"
ALLOW_PREFIX = ("python/",)
ALLOW_FILES = ("requirements.txt",)
TIMEOUT = 20.0
# folder repo = induk dari python/ (BUKAN CWD -- bat VPS
# selalu cd dulu, tapi jangan percaya kebetulan)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_BAT_TOKEN_RE = re.compile(
    r'set\s+"?(?:RBT_GH_)?TOKEN\s*=\s*([A-Za-z0-9_.\-]{20,})', re.I)


def _token_from_bat(root):
    """v3.96: token cadangan dari MULAI_SEMUA.bat / *.bat
    di folder repo (bat VPS menanam token di baris set "TOKEN=").
    KRUSIAL utk bat LAMA yang jalan di memori sebelum ada baris
    passthrough RBT_GH_TOKEN -- klik UPDATE tetap harus bisa."""
    cands = [os.path.join(root, "MULAI_SEMUA.bat")]
    try:
        for n in sorted(os.listdir(root)):
            if n.lower().endswith(".bat"):
                fp = os.path.join(root, n)
                if fp not in cands:
                    cands.append(fp)
    except Exception:
        pass
    for fp in cands:
        try:
            if not os.path.isfile(fp):
                continue
            txt = open(fp, encoding="utf-8", errors="ignore").read()
            m = _BAT_TOKEN_RE.search(txt)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
    return None


def resolve_token(root="."):
    """Env RBT_GH_TOKEN > github_token.txt > data/gh_token.txt >
    token yang ditanam di MULAI_SEMUA.bat / *.bat (folder repo)."""
    tok = (os.environ.get("RBT_GH_TOKEN") or "").strip()
    if tok:
        return tok
    for f in (os.path.join(root, "github_token.txt"),
              os.path.join(root, "TOKEN.txt"),
              os.path.join(root, "data", "gh_token.txt")):
        try:
            if os.path.exists(f):
                t = open(f, encoding="utf-8").read().strip()
                if t:
                    return t
        except Exception:
            pass
    return _token_from_bat(root)


def blob_sha(content):
    """Git blob SHA-1 dari bytes (utk banding dgn tree GitHub)."""
    h = hashlib.sha1()
    h.update(b"blob %d\x00" % len(content))
    h.update(content)
    return h.hexdigest()


def _req_json(url, token):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "RBT-FX-selfupdate")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_raw(url, token):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Accept", "application/vnd.github.raw")
    req.add_header("User-Agent", "RBT-FX-selfupdate")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def _allowed(path):
    return (path.startswith(ALLOW_PREFIX) or path in ALLOW_FILES)


def tree(repo=None, branch=None, token=None):
    """{path: blob_sha} file DIIZINKAN di repo (blob saja)."""
    repo = repo or REPO
    branch = branch or BRANCH
    d = _req_json("https://api.github.com/repos/%s/git/trees/%s"
                  "?recursive=1" % (repo, branch), token)
    out = {}
    for it in (d.get("tree") or []):
        if it.get("type") != "blob":
            continue
        p = str(it.get("path") or "")
        if _allowed(p):
            out[p] = str(it.get("sha") or "")
    return out


def plan(repo=None, branch=None, token=None, root="."):
    """Daftar path yang BEDA dgn lokal (urut).  File lokal hilang =
    perlu diunduh.  Error network -> raises (pemanggil tangkap)."""
    remote = tree(repo, branch, token)
    need = []
    for p, sha in sorted(remote.items()):
        if not _allowed(p):
            continue                       # pengaman pertama: jangan
                                           #   bandingkan path terlarang
        fp = os.path.join(root, *p.split("/"))
        try:
            with open(fp, "rb") as f:
                if blob_sha(f.read()) == sha:
                    continue
        except OSError:
            pass
        need.append(p)
    return need


def apply_updates(paths, repo=None, branch=None, token=None, root="."):
    """Unduh & tulis file (tmp + replace).  Return daftar yang sukses."""
    repo = repo or REPO
    branch = branch or BRANCH
    ok = []
    for p in paths:
        if not _allowed(p):
            continue                       # pengaman kedua
        data = _fetch_raw("https://api.github.com/repos/%s/contents/%s"
                          "?ref=%s" % (repo, p, branch), token)
        fp = os.path.join(root, *p.split("/"))
        os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
        tmp = fp + ".upd"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, fp)
        ok.append(p)
    return ok


def run(root=None):
    """High-level: (files, err).  files=None bila gagal/error (dgn
    pesan err); files=[] = sudah termutakhir (tanpa perubahan).
    root default = folder repo dr lokasi file ini (bukan CWD)."""
    root = ROOT if root is None else root
    try:
        tok = resolve_token(root)
        if not tok:
            return None, ("token GitHub tidak ada -- butuh env "
                          "RBT_GH_TOKEN, github_token.txt, atau token "
                          "di MULAI_SEMUA.bat")
        need = plan(token=tok, root=root)
        if not need:
            return [], None
        return apply_updates(need, token=tok, root=root), None
    except Exception as e:
        return None, str(e)
