# -*- coding: utf-8 -*-
"""v4.29 -- TRAINER ML LOKAL Strategy 3 (permintaan user: "AI belajar
karakter market 1-3 tahun"): logistic regression python murni (gratis,
tanpa layanan eksternal) atas 9 fitur struktur/tren (cc_strategy3.
ml_features -- definisi sama persis dgn engine, tidak bisa drift):

  struktur HH/HL, gap EMA13/21, ADX, ruang swing lawan, extension,
  momentum, breakout pivot, jam sesi.

LABEL (tanpa look-ahead pada fitur): dari close bar i, mana yang
tersentuh lebih dulu dalam 24 bar M15 -- +1xATR (win=1) atau
-1xATR (win=0); tak keduanya -> arah net close.

Pemakaian:  python3 python/ml_train.py [--step 2] [--epochs 5]
Hasil:      python/ml_model.json  (dibaca engine saat start)
"""
import glob
import gzip
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cc_strategy3 as S    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data_hist")
HORIZON = 24
R_ATR = 1.0


def load_pair(want):
    """Gabungkan cloud + semua delta harian -> bars dedupe urut waktu."""
    files = {os.path.join(HIST, "s3_hist_%s_M15.json.gz" % want)}
    files.update(glob.glob(os.path.join(
        HIST, "delta", "s3_hist_%s_M15_*.json.gz" % want)))
    merged = {}
    for fp in sorted(files):
        try:
            with gzip.open(fp, "rb") as f:
                d = json.loads(f.read().decode("utf-8"))
        except Exception:
            continue
        for t, o, h, l, c in zip(d.get("time") or [], d.get("open") or [],
                                 d.get("high") or [], d.get("low") or [],
                                 d.get("close") or []):
            merged[int(t)] = (float(o), float(h), float(l), float(c))
    ts = sorted(merged)
    return {"time": ts,
            "open": [merged[t][0] for t in ts],
            "high": [merged[t][1] for t in ts],
            "low": [merged[t][2] for t in ts],
            "close": [merged[t][3] for t in ts]}


def atr_at_i(bars, i, period=14):
    if i < period + 1:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        tr = max(bars["high"][j] - bars["low"][j],
                 abs(bars["high"][j] - bars["close"][j - 1]),
                 abs(bars["low"][j] - bars["close"][j - 1]))
        trs.append(tr)
    return sum(trs) / float(len(trs))


def label_at(bars, i, atr):
    """+1R dulu = 1; -1R dulu = 0; tak tersentuh -> arah net close."""
    side_px = R_ATR * atr
    c0 = bars["close"][i]
    hi, lo = c0 + side_px, c0 - side_px
    for j in range(i + 1, min(len(bars["close"]), i + 1 + HORIZON)):
        if bars["low"][j] <= lo and bars["high"][j] >= hi:
            return 1 if bars["close"][j] >= c0 else 0   # ambigu -> net
        if bars["low"][j] <= lo:
            return 0
        if bars["high"][j] >= hi:
            return 1
    return 1 if (bars["close"][min(i + HORIZON,
                                    len(bars["close"]) - 1)] >= c0) else 0


def build_samples(pairs, step=2):
    X, y = [], []
    for want in pairs:
        bars = load_pair(want)
        n = len(bars["close"])
        for i in range(70, n - HORIZON - 1, step):
            atr = atr_at_i(bars, i)
            if atr <= 0:
                continue
            for side in (1, -1):
                f = S.ml_features(side, bars, i, atr)
                if not f:
                    continue
                X.append(f)
                y.append(label_at(bars, i, atr))
        print("  %s: %d bar -> total sampel %d" % (want, n, len(X)))
    return X, y


def train(X, y, epochs=5, lr=0.05, seed=42):
    """Logistic regression SGD; split temporal 80/20 (tanpa shuffle
    lintas waktu utk val)."""
    ntr = int(len(X) * 0.8)
    Xtr, ytr, Xva, yva = X[:ntr], y[:ntr], X[ntr:], y[ntr:]
    rnd = random.Random(seed)
    w = [0.0] * len(X[0])
    b = 0.0
    idx = list(range(len(Xtr)))
    for ep in range(epochs):
        rnd.shuffle(idx)
        loss = 0.0
        for ii in idx:
            z = b + sum(wj * xj for wj, xj in zip(w, Xtr[ii]))
            p = 1.0 / (1.0 + (2.718281828459045 ** (-z))) if -30 < z < 30 \
                else (0.0 if z < 0 else 1.0)
            g = p - float(ytr[ii])
            loss += -((ytr[ii] * max(p, 1e-9)) +
                      (1 - ytr[ii]) * max(1 - p, 1e-9))
            for k in range(len(w)):
                w[k] -= lr * g * Xtr[ii][k]
            b -= lr * g
        print("  epoch %d: loss %.4f" % (ep + 1, loss / len(idx)))

    def acc(XX, yy):
        if not XX:
            return 0.0
        ok = 0
        for XXi, yyi in zip(XX, yy):
            z = b + sum(wj * xj for wj, xj in zip(w, XXi))
            p = 1.0 / (1.0 + (2.718281828459045 ** (-z))) if -30 < z < 30 \
                else (0.0 if z < 0 else 1.0)
            ok += 1 if (p >= 0.5) == (yyi == 1) else 0
        return ok / float(len(XX))
    meta = {"n_train": len(Xtr), "n_val": len(Xva),
            "acc_train": round(acc(Xtr, ytr), 4),
            "acc_val": round(acc(Xva, yva), 4)}
    return w, b, meta


def main():
    step = 2
    epochs = 5
    args = sys.argv[1:]
    if "--step" in args:
        step = int(args[args.index("--step") + 1])
    if "--epochs" in args:
        epochs = int(args[args.index("--epochs") + 1])
    pairs = []
    for fp in glob.glob(os.path.join(HIST, "s3_hist_*_M15.json.gz")):
        b = os.path.basename(fp)[len("s3_hist_"):-len("_M15.json.gz")]
        if b and b not in pairs:
            pairs.append(b)
    print("PAIRS:", ", ".join(pairs))
    t0 = time.time()
    X, y = build_samples(pairs, step=step)
    print("sampel: %d (%.1f%% win) | %.1fs" %
          (len(X), 100.0 * sum(y) / max(1, len(X)), time.time() - t0))
    w, b, meta = train(X, y, epochs=epochs)
    model = {"feat_version": 1, "features": [
        "sdir", "gap_ema", "adx_n", "room", "ext", "mom3", "brkout",
        "hour_sin", "hour_cos"], "w": [round(x, 6) for x in w],
        "b": round(b, 6), "meta": dict(meta, pairs=pairs, step=step,
                                       trained_utc=time.strftime(
                                           "%Y-%m-%d %H:%M UTC",
                                           time.gmtime()))}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "ml_model.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=1)
    print("MODEL -> %s" % out)
    print("meta:", json.dumps(model["meta"]))


if __name__ == "__main__":
    main()
