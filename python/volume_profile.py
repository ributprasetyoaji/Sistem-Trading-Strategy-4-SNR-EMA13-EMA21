"""Rolling volume profile: price bins -> HVN zone clustering (spec section 5).

HVN is a ZONE (low/high/center/relative volume), never a single round number.
"""
from __future__ import annotations

import math


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def build_bins(trades, bin_size: float, t0_ms: int, t1_ms: int | None = None) -> dict[int, float]:
    """trades: iterable of (ts_ms, price, qty[, is_sell])."""
    bins: dict[int, float] = {}
    for row in trades:
        ts, price, qty = row[0], row[1], row[2]
        if ts < t0_ms:
            continue
        if t1_ms is not None and ts > t1_ms:
            continue
        idx = int(math.floor(price / bin_size))
        bins[idx] = bins.get(idx, 0.0) + qty
    return bins


def detect_zones(bins: dict[int, float], bin_size: float,
                 hvn_percentile: float = 85.0,
                 min_rel_volume: float = 1.5,
                 min_width: float = 0.0,
                 max_width: float | None = None,
                 max_zones: int = 5) -> list[dict]:
    """Cluster adjacent high-volume bins into HVN zones.

    Threshold = max(volume percentile, mean * min_rel_volume). When the
    distribution is too concentrated for the relative rule to make sense
    (few bins) or the relative rule rejects everything, the pure percentile
    threshold is used as fallback so zones always reflect the volume data.
    """
    if not bins or bin_size <= 0:
        return []
    items = sorted(bins.items())
    vols = sorted(v for _, v in items)
    pth = percentile(vols, hvn_percentile)
    mean = sum(vols) / len(vols)
    thresh = pth
    if len(vols) >= 8 and min_rel_volume > 0:
        thresh = max(pth, mean * min_rel_volume)
    if thresh <= 0:
        return []

    hot = [i for i, v in items if v >= thresh and v > 0]
    if not hot and pth > 0:
        hot = [i for i, v in items if v >= pth and v > 0]   # fallback
    if not hot:
        return []

    clusters: list[list[int]] = []
    for i in hot:
        if clusters and i == clusters[-1][-1] + 1:
            clusters[-1].append(i)
        else:
            clusters.append([i])

    zones: list[dict] = []
    for cl in clusters:
        vol = sum(bins[i] for i in cl)
        if vol <= 0:
            continue
        wsum = sum(((i + 0.5) * bin_size) * bins[i] for i in cl)
        center = wsum / vol
        low = cl[0] * bin_size
        high = (cl[-1] + 1) * bin_size
        width = high - low
        if width < min_width:
            pad = (min_width - width) / 2.0
            low -= pad
            high += pad
            width = high - low
        zones.append({
            "low": low,
            "high": high,
            "center": center,
            "volume": vol,
            "rel": vol / mean if mean > 0 else 0.0,
            "width": width,
            "bins": len(cl),
        })

    zones.sort(key=lambda z: -z["volume"])
    if max_zones and len(zones) > max_zones:
        zones = zones[:max_zones]
    zones.sort(key=lambda z: z["center"])
    return zones
