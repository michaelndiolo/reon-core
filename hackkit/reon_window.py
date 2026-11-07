"""reon_window: what a limited string-voltage window does to the capacity gain of cell-level control.

The ideal pack model (recheck/SPEC.md) lets control use sum(cells). That needs every cell to be bypassed one by one as it empties, until a single
cell is left driving the string. A converter or inverter behind the string only accepts a voltage window, so in practice at least n_min of the N
series cells must stay in circuit. Constant-current discharge, equal cell voltage curves, bypass when a cell is empty (and the mirror image on charge):

    usable(n_min) = sum_i min(c_i, c_(n_min))      where c_(k) is the k-th LARGEST capacity

n_min = N gives the conventional pack (N x weakest); n_min = 1 gives the ideal sum. The string voltage fraction at the end of discharge is n_min / N
(equal cell voltages assumed, so this is a first-order picture, not a battery model).

Idea pattern: a Pareto front between two goals (usable energy vs the converter window), after the auxetic-metamaterial post in the participant notes.
Nothing in here is REON's measured behavior: REON's patents describe series columns in parallel, spares and a converter stage, which this does not model.
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


def window_usable(caps: Sequence[float], n_min: int) -> float:
    """Usable Ah when at least n_min of the N series cells must stay in circuit."""
    c = _caps(caps)
    n = c.size
    if not (1 <= int(n_min) <= n) or int(n_min) != n_min:
        raise ValueError("n_min must be an integer between 1 and the number of cells")
    q_stop = np.sort(c)[::-1][int(n_min) - 1]
    return float(np.minimum(c, q_stop).sum())


def window_gain(caps: Sequence[float], n_min: int) -> float:
    c = _caps(caps)
    return window_usable(c, n_min) / (c.size * c.min()) - 1.0


def window_curve(caps: Sequence[float]) -> list[dict]:
    """One row per n_min from N down to 1: voltage fraction at the end of discharge, usable Ah, gain over conventional, share of the ideal gain captured."""
    c = _caps(caps)
    n = c.size
    conv = n * c.min()
    full = c.sum() - conv
    rows = []
    for k in range(n, 0, -1):
        u = window_usable(c, k)
        rows.append({"n_min": k, "voltage_fraction": k / n, "usable_ah": u, "gain": u / conv - 1.0, "share_of_ideal_gain": (u - conv) / full if full > 0 else 1.0})
    return rows


def narrowest_window_for_share(caps: Sequence[float], share: float) -> dict:
    """Smallest string-voltage swing (largest n_min) that still captures `share` of the ideal gain. For equal cells there is nothing to capture and n_min = N."""
    if not (0.0 < share <= 1.0):
        raise ValueError("share must be in (0, 1]")
    rows = window_curve(caps)
    for r in rows:                      # n_min descending, share nondecreasing
        if r["share_of_ideal_gain"] >= share - 1e-12:
            return r
    return rows[-1]
