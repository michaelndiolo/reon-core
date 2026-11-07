"""Turn past per-cell capacity measurements into fade rates for the learner (reon_learn.FadeBelief), instead of waiting for new data.
Input: rows of (cell, time_years, capacity). Output: per-cell fade rate (share of the cell's own starting capacity lost per year; negative = capacity rose).
Caveat from the Nissan Leaf retired-cell study (arXiv 2402.18859): capacity there ROSE 0.6% to 16.1% over 15 months, driven mostly by seasonal temperature, so a straight-line
fit over a short window measures temperature as much as ageing. fade_rates_from_series reports the fit's R^2 so weak fits can be dropped, and seasonal_flag warns when the window is under 2 years."""
from __future__ import annotations
import csv
from collections import defaultdict
from typing import Iterable, Sequence
import numpy as np


def fade_rates_from_series(rows: Iterable[Sequence], min_points: int = 4) -> dict:
    """rows: (cell, time_years, capacity). Returns {cell: {fade_per_year, r2, n, span_years}} using a straight-line fit relative to the fitted starting capacity."""
    by = defaultdict(list)
    for cell, t, q in rows:
        by[str(cell)].append((float(t), float(q)))
    out = {}
    for cell, pts in by.items():
        if len(pts) < min_points:
            continue
        pts.sort()
        t = np.array([p[0] for p in pts]); q = np.array([p[1] for p in pts])
        if np.ptp(t) <= 0:
            continue
        slope, icpt = np.polyfit(t, q, 1)
        if icpt <= 0:
            continue
        resid = q - (slope * t + icpt)
        ss_tot = float(((q - q.mean()) ** 2).sum())
        out[cell] = {"fade_per_year": float(-slope / icpt), "r2": 1.0 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else 0.0, "n": len(pts), "span_years": float(np.ptp(t))}
    return out


def read_csv(path: str, cell_col: str = "cell", time_col: str = "time_years", cap_col: str = "capacity") -> list:
    with open(path, newline="") as f:
        return [(r[cell_col], r[time_col], r[cap_col]) for r in csv.DictReader(f)]


def usable_fades(fits: dict, min_r2: float = 0.5) -> list:
    """Fade rates from fits good enough to trust, ready for FadeBelief.update."""
    return [v["fade_per_year"] for v in fits.values() if v["r2"] >= min_r2]


def seasonal_flag(fits: dict) -> bool:
    """True when the data window is under two years: seasonal temperature can masquerade as ageing."""
    return any(v["span_years"] < 2.0 for v in fits.values())
