"""reon_sorting: is cell-level control better than the usual alternative, sorting retired cells into matched strings?

Current second-life practice (MDPI 2024 review, ACEEE 2026 brief): grade cells or modules by state of health and regroup similar ones.
Model: the N cells are split into N/m strings of m cells in series, strings in parallel. A string without control delivers m x (its weakest cell);
the pack delivers the sum over strings. With control every cell runs to its own end, so the pack delivers the sum of all cells whatever the grouping.
  as found    : strings in the order the cells came (e.g. the real BMW modules)
  random      : cells assigned to strings at random (average over trials)
  sorted      : cells ranked and grouped in order (optimal for equal-sized strings: exchange argument, checked by brute force in the tests)
  sorted noisy: ranked by a noisy measurement, scored on the true capacity (what sorting really delivers when testing is imperfect)
Not priced: the cost of testing every cell to sort it (the reason sorting is rare at cell level), repacking labour, certification.
Pattern credit: held-out scoring (rank by the measured value, score on the true one), as in the forecaster/decision gate test of our hack kit.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def _prep(caps: Sequence[float], m: int) -> np.ndarray:
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size < 2 or (c <= 0).any():
        raise ValueError("need at least two positive capacities")
    if int(m) != m or not (1 <= m <= c.size) or c.size % int(m) != 0:
        raise ValueError("string length m must divide the number of cells")
    return c


def strings_usable(caps: Sequence[float], m: int) -> float:
    """Usable Ah when consecutive groups of m cells (in the order given) form the strings: sum over strings of m x weakest."""
    c = _prep(caps, m)
    return float(sum(m * g.min() for g in c.reshape(-1, int(m))))


def sorted_usable(caps: Sequence[float], m: int, measured: Optional[Sequence[float]] = None) -> float:
    """Strings built by ranking the cells (by `measured` if given, else the true values); the result is scored on the true capacities."""
    c = _prep(caps, m)
    key = c if measured is None else np.asarray(measured, dtype=float)
    if key.shape != c.shape:
        raise ValueError("measured must match caps")
    order = np.argsort(-key, kind="stable")
    return strings_usable(c[order], m)


def random_usable(caps: Sequence[float], m: int, trials: int = 2000, seed: int = 0) -> float:
    c = _prep(caps, m)
    rng = np.random.default_rng(seed)
    return float(np.mean([strings_usable(rng.permutation(c), m) for _ in range(trials)]))


def sorting_vs_control(caps: Sequence[float], m: int, sigma_rel: float = 0.02, trials: int = 2000, seed: int = 0) -> dict:
    """Usable Ah for each way of building the pack, and the gain of control over each. sigma_rel = relative error of the sorting measurement."""
    c = _prep(caps, m)
    rng = np.random.default_rng(seed)
    noisy = float(np.mean([sorted_usable(c, m, c * (1.0 + sigma_rel * rng.standard_normal(c.size))) for _ in range(trials)])) if sigma_rel > 0 else sorted_usable(c, m)
    out = {
        "as_found": strings_usable(c, m),
        "random": random_usable(c, m, trials, seed),
        "sorted_ideal": sorted_usable(c, m),
        "sorted_noisy": noisy,
        "control": float(c.sum()),
        "strings": int(c.size // int(m)),
        "string_length": int(m),
        "sigma_rel": float(sigma_rel),
    }
    for k in ("as_found", "random", "sorted_ideal", "sorted_noisy"):
        out[f"control_over_{k}"] = out["control"] / out[k] - 1.0
    out["sorting_over_random"] = out["sorted_ideal"] / out["random"] - 1.0
    out["share_of_control_gain_by_sorting"] = (
        (out["sorted_ideal"] - out["random"]) / (out["control"] - out["random"]) if out["control"] > out["random"] else None)
    return out
