"""GITHUB HISTORY CLOUD -- RBT FX S3 (v3.88, permintaan user):
backup/restore cache riwayat M15 (data/s3_hist_*.json) ke repo GitHub,
supaya muat ulang bot / pindah VPS TIDAK perlu download ulang lama dari
broker -- cache diambil dari cloud dlm hitungan detik.

- BASE (penuh): data_hist/s3_hist_<SYM>_M15.json.gz -- di-upload JARANG
  (tumbuh >= upload_min_new_bars & >= upload_min_hours).
- DELTA (v3.90, harian & RINGAN): data_hist/delta/s3_hist_<SYM>_M15_
  <YYYYMMDD>.json.gz -- HANYA bar sejak backup terakhir (1 hari M15
  ~ 96 bar ~ 2-4 KB gzip).  Restore = base + delta berurutan + ekor live.
  Base baru -> delta lama otomatis dibersihkan (repo tetap ramping).
- Download HANYA saat cache lokal tipis/absen -- lalu TAIL di-refresh dgn
  bar live (merge_bars) supaya sinyal tetap dari harga TERBARU.
- Token: env RBT_GH_TOKEN > config token > file github_token.txt /
  data/gh_token.txt.  Tanpa token -> fitur off (aman, tidak error).
Modul fungsi murni + IO terguard; tidak pernah melempar ke engine."""
import base64
import gzip
import json
import os
import time
import urllib.request

DEFAULTS = {
    "enabled": True,
    "repo": "ributprasetyoaji/Sistem-Trading-Strategy-3",
    "branch": "main",
    "dir": "data_hist",                # folder di repo
    "upload_min_new_bars": 1000,       # ~10 hari M15 -- jaga repo ramping
    "upload_min_hours": 24.0,          # maks 1x upload/pair/hari
    "download_min_bars": 2000,         # cache lokal dianggap tipis jika <
    "delta_enabled": True,             # v3.90 backup lanjutan harian
    "delta_min_new_bars": 20,          # min bar baru utk 1 delta (noise guard)
    "delta_dir": "delta",              # subfolder file delta harian
    "timeout_sec": 20.0,
    "token": "",                       # opsional (env/file lebih aman)
}


def cloud_name(want):
    """Nama file di repo utk 1 pair."""
    return "s3_hist_%s_M15.json.gz" % want


def cloud_path(want, k=None):
    return "%s/%s" % ((k or {}).get("dir") or DEFAULTS["dir"],
                      cloud_name(want))


def delta_dir_path(k=None):
    """Folder delta di repo: <dir>/delta."""
    k = k or {}
    return "%s/%s" % (k.get("dir") or DEFAULTS["dir"],
                      k.get("delta_dir") or DEFAULTS["delta_dir"])


def delta_name(want, date_str):
    """Nama file delta harian (YYYYMMDD -> urut alfabet = urut waktu)."""
    return "s3_hist_%s_M15_%s.json.gz" % (want, date_str)


def delta_path(want, k=None, date_str=""):
    return "%s/%s" % (delta_dir_path(k), delta_name(want, date_str))


def last_time(bars):
    """Time bar TERAKHIR (0 bila kosong)."""
    tm = (bars or {}).get("time") or []
    return int(tm[-1]) if tm else 0


def slice_after(bars, t):
    """v3.90 DELTA: hanya bar dgn time > t (sejak backup terakhir)."""
    import bisect
    tm = (bars or {}).get("time") or []
    i = bisect.bisect_right(tm, int(t))
    return {kk: list(vv[i:]) for kk, vv in (bars or {}).items()}


def list_deltas(repo, want, k=None, token=None):
    """Daftar path delta 1 pair, urut LAMA->BARU; [] bila tidak ada."""
    k = k or {}
    try:
        d = delta_dir_path(k)
        items = _req("https://api.github.com/repos/%s/contents/%s?ref=%s"
                     % (repo, d, k.get("branch") or DEFAULTS["branch"]),
                     token)
        pre = "s3_hist_%s_M15_" % want
        out = []
        for it in (items if isinstance(items, list) else []):
            n = str(it.get("name") or "")
            if n.startswith(pre) and n.endswith(".json.gz"):
                out.append("%s/%s" % (d, n))
        out.sort()
        return out
    except Exception:
        return []


def resolve_token(k=None):
    """Prioritas: env RBT_GH_TOKEN > k['token'] > file. None = off."""
    tok = (os.environ.get("RBT_GH_TOKEN") or "").strip()
    if tok:
        return tok
    tok = str((k or {}).get("token") or "").strip()
    if tok:
        return tok
    for f in ("github_token.txt", os.path.join("data", "gh_token.txt")):
        try:
            if os.path.exists(f):
                tok = open(f, encoding="utf-8").read().strip()
                if tok:
                    return tok
        except Exception:
            pass
    return None


def pack_bars(bars):
    """dict-of-lists bar -> bytes gzip (kompak, hemat repo)."""
    raw = json.dumps(bars, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw, 6)


def unpack_bars(data):
    """bytes gzip -> dict bars; None bila rusak/tak valid."""
    try:
        b = json.loads(gzip.decompress(data).decode("utf-8"))
        if not isinstance(b, dict) or not b.get("time") or \
                not b.get("close"):
            return None
        return b
    except Exception:
        return None


def should_upload(cur_bars, state, k=None, now=None):
    """Kebijakan upload: (bool, alasan).  state = {'bars':n,'ts':t}."""
    k = k or {}
    if k.get("enabled", True) is False:
        return (False, "off")
    now = float(now if now is not None else time.time())
    minb = int(k.get("upload_min_new_bars", 1000) or 0)
    minh = float(k.get("upload_min_hours", 24.0) or 0)
    last_b = int((state or {}).get("bars", 0) or 0)
    last_t = float((state or {}).get("ts", 0.0) or 0.0)
    if cur_bars <= last_b:
        return (False, "tak bertambah")
    if minb > 0 and cur_bars - last_b < minb:
        return (False, "baru +%d bar (< %d)" % (cur_bars - last_b, minb))
    if minh > 0 and last_t > 0 and now - last_t < minh * 3600.0:
        return (False, "baru %.1f jam (< %.0f jam)"
                % ((now - last_t) / 3600.0, minh))
    return (True, "+%d bar" % (cur_bars - last_b) if last_b else "pertama")


def _req(url, token, method=None, data=None, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "RBT-FX-S3")
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body, timeout=DEFAULTS["timeout_sec"]) as r:
        return json.loads(r.read().decode("utf-8"))


def head_sha(repo, path, branch, token):
    """SHA blob di repo, atau None bila belum ada."""
    try:
        d = _req("https://api.github.com/repos/%s/contents/%s?ref=%s"
                 % (repo, path, branch), token)
        return d.get("sha")
    except Exception:
        return None


def download_gz(repo, path, branch, token):
    """Isi file (bytes gzip mentah) dari repo, atau None."""
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/%s/contents/%s?ref=%s"
            % (repo, path, branch))
        req.add_header("Authorization", "Bearer %s" % token)
        req.add_header("Accept", "application/vnd.github.raw")
        req.add_header("User-Agent", "RBT-FX-S3")
        with urllib.request.urlopen(
                req, timeout=DEFAULTS["timeout_sec"]) as r:
            return r.read()
    except Exception:
        return None


def upload_bytes(repo, path, branch, token, data, msg="RBT history sync"):
    """Upload bytes ke repo (gzip/base64).  <=900KB via Contents API;
    lebih besar via Git Data API (bebas limit 1MB).  Return True/False."""
    try:
        b64 = base64.b64encode(data).decode("ascii")
        if len(data) <= 900 * 1024:
            body = {"message": msg, "content": b64, "branch": branch}
            sha = head_sha(repo, path, branch, token)
            if sha:
                body["sha"] = sha
            _req("https://api.github.com/repos/%s/contents/%s"
                 % (repo, path), token, method="PUT", data=body)
            return True
        # ---- Git Data API (file besar) ----
        blob = _req("https://api.github.com/repos/%s/git/blobs" % repo,
                    token, method="PUT",
                    data={"content": b64, "encoding": "base64"})
        head = _req("https://api.github.com/repos/%s/git/ref/heads/%s"
                    % (repo, branch), token)["object"]["sha"]
        base = _req("https://api.github.com/repos/%s/git/commits/%s"
                    % (repo, head), token)
        tree = _req("https://api.github.com/repos/%s/git/trees" % repo,
                    token, method="PUT",
                    data={"base_tree": base["tree"]["sha"],
                          "tree": [{"path": path, "mode": "100644",
                                    "type": "blob", "sha": blob["sha"]}]})
        com = _req("https://api.github.com/repos/%s/git/commits" % repo,
                   token, method="PUT",
                   data={"message": msg, "tree": tree["sha"],
                         "parents": [head]})
        _req("https://api.github.com/repos/%s/git/refs/heads/%s"
             % (repo, branch), token, method="PATCH",
             data={"sha": com["sha"]})
        return True
    except Exception:
        return False


def delete_file(repo, path, branch, token):
    try:
        sha = head_sha(repo, path, branch, token)
        if not sha:
            return True
        _req("https://api.github.com/repos/%s/contents/%s" % (repo, path),
             token, method="DELETE",
             data={"message": "RBT history: hapus", "sha": sha,
                   "branch": branch})
        return True
    except Exception:
        return False
