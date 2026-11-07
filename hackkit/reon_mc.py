"""reon_mc: probability ranges for guessed inputs, by Monte Carlo over triangular (low, base, high) distributions with Latin hypercube sampling.

The corners in reon_carbon.sensitivity answer "what is the worst and best case"; they say nothing about how likely a sign flip is. This module draws each
Lever from a triangular distribution (low, base as the mode, high) and reports percentiles of any function of the levers and the share of draws below zero.

READ THE RESULT AS: "under the ranges we typed", not as a frequency in the world. Triangular shapes, independence between inputs and the ranges themselves
are ASSUMED; an input tagged ASSUMED stays a guess however many draws we make. Correlations are ignored.

Technique pattern (no code taken from anywhere): triangular input distributions for expert-estimated unit costs, Latin hypercube sampling and a Monte Carlo
run of 10,000 draws, as described in a public Medium post by Rhythm Doshi (Dec 2023) that summarizes a published cost-probability analysis of
spent-fuel reprocessing. The post is a secondary source; the technique itself is standard.
"""
from __future__ import annotations

from typing import Callable, Dict, Sequence

import numpy as np

from .atstake import Lever


def triangular_ppf(u, low: float, mode: float, high: float):
    """Inverse CDF of the triangular distribution on [low, high] with the given mode (u in [0, 1], scalar or array)."""
    if not (low <= mode <= high):
        raise ValueError("need low <= mode <= high")
    u = np.asarray(u, dtype=float)
    if high == low:
        return np.full_like(u, low)
    fc = (mode - low) / (high - low)
    left = low + np.sqrt(u * (high - low) * (mode - low))
    right = high - np.sqrt((1.0 - u) * (high - low) * (high - mode))
    return np.where(u < fc, left, right)


def lhs_unit(n: int, rng: np.random.Generator) -> np.ndarray:
    """n values in (0, 1), exactly one in each of the n equal strata, in random order."""
    return (rng.permutation(n) + rng.random(n)) / n


def sample_levers(levers: Sequence[Lever], n: int = 10000, seed: int = 0, method: str = "lhs") -> Dict[str, np.ndarray]:
    """{lever name: n draws}. method 'lhs' (Latin hypercube, each input stratified separately) or 'random'."""
    if n < 100:
        raise ValueError("use at least 100 draws")
    if method not in ("lhs", "random"):
        raise ValueError("method must be 'lhs' or 'random'")
    rng = np.random.default_rng(seed)
    out = {}
    for lev in levers:
        u = lhs_unit(n, rng) if method == "lhs" else rng.random(n)
        out[lev.name] = np.asarray(triangular_ppf(u, lev.low, lev.base, lev.high))
    return out


def monte_carlo(levers: Sequence[Lever], fn: Callable[[Dict[str, float]], float], n: int = 10000, seed: int = 0, method: str = "lhs") -> dict:
    """Evaluate fn(values) on n joint draws. Returns mean, p5, p50, p95, prob_negative (share of draws below 0) and the draws themselves."""
    draws = sample_levers(levers, n, seed, method)
    names = [l.name for l in levers]
    y = np.array([fn({k: float(draws[k][i]) for k in names}) for i in range(n)], dtype=float)
    return {"n": n, "mean": float(y.mean()), "p5": float(np.percentile(y, 5)), "p50": float(np.percentile(y, 50)), "p95": float(np.percentile(y, 95)),
            "prob_negative": float((y < 0).mean()), "values": y}
