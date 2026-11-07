"""reon_spread: how fragile is a quoted capacity gain, and how much of it could be measurement noise?

gain = mean / min - 1 depends on ONE cell, the weakest. Three questions follow, each a plain function:
  fragility(caps)            how much of the gain disappears if the weakest cell is removed (a bad sensor reads like a weak cell: contract.check_cells)
  noise_bias(caps, sigma)    the weakest MEASURED cell is biased low (winner's curse), so a gain computed from noisy capacity estimates is biased high
  iid_gain(cv, n)            the gain to expect from n independent cells with a given spread, for comparing a quoted spread with a quoted gain
Idea patterns: leakage canary / shortcut check and leave-one-out from the participant notes. Sigma and cv are inputs; nothing here is a measured value.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np


def _caps(caps: Sequence[float]) -> np.ndarray:
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size == 0:
        raise ValueError("need at least one cell")
    if not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("every capacity must be finite and positive")
    return c


def _gain(c: np.ndarray) -> float:
    return float(c.mean() / c.min() - 1.0)


def fragility(caps: Sequence[float]) -> dict:
    """{'gain', 'gain_without_weakest', 'drop', 'share_lost'}. Needs at least 2 cells."""
    c = _caps(caps)
    if c.size < 2:
        raise ValueError("need at least two cells")
    g = _gain(c)
    g2 = _gain(np.sort(c)[1:])
    return {"gain": g, "gain_without_weakest": g2, "drop": g - g2, "share_lost": (g - g2) / g if g > 0 else 0.0}


def noise_bias(caps: Sequence[float], sigma_rel: float, trials: int = 4000, seed: int = 0) -> dict:
    """Treat `caps` as the truth, add independent normal relative measurement error, recompute the gain from the noisy values.
    Returns true gain, mean apparent gain, bias, and a 90% range of the apparent gain."""
    c = _caps(caps)
    if sigma_rel < 0:
        raise ValueError("sigma_rel must be >= 0")
    rng = np.random.default_rng(seed)
    meas = c * (1.0 + sigma_rel * rng.standard_normal((trials, c.size)))
    meas = np.maximum(meas, 1e-9)
    g = meas.mean(axis=1) / meas.min(axis=1) - 1.0
    lo, hi = np.percentile(g, [5, 95])
    return {"true_gain": _gain(c), "apparent_mean": float(g.mean()), "bias": float(g.mean() - _gain(c)), "apparent_5": float(lo), "apparent_95": float(hi)}


def iid_gain(cv: float, n: int, trials: int = 4000, seed: int = 0) -> dict:
    """Gain of n independent cells with capacity ~ Normal(1, cv) (clipped at 0.05): mean and 90% range."""
    if cv < 0 or n < 1:
        raise ValueError("need cv >= 0 and n >= 1")
    rng = np.random.default_rng(seed)
    x = np.maximum(1.0 + cv * rng.standard_normal((trials, n)), 0.05)
    g = x.mean(axis=1) / x.min(axis=1) - 1.0
    lo, hi = np.percentile(g, [5, 95])
    return {"mean": float(g.mean()), "p5": float(lo), "p95": float(hi)}
