"""reon_claim: what would have to be true for a "2-3X" claim, under each plausible meaning of it.

We do not know what REON's "2-3X more usable capacity" is measured against. Two readings can be tested with plain arithmetic:
  A. today's usable energy, control vs a conventional pack limited by its weakest cell. Ratio = mean / min (or less with a limited converter window).
     required_cv() = the cell-to-cell spread (coefficient of variation of capacity, independent normal cells) at which the expected ratio reaches a target.
  B. how long the pack stays in service. If every cell fades linearly at its own rate, a conventional pack must be retired when its fastest-fading cell
     reaches the end-of-life level and a controlled pack when the AVERAGE reaches it, so the life ratio = max rate / mean rate, whatever the end-of-life level.
     required_rate_cv() = the spread of fade rates at which the expected life ratio reaches a target.
Both return None if the target cannot be reached below `cv_max`. All spreads are inputs to compare with data; nothing here is a measured value.
Patterns: "what would have to be true" and decision-flip threshold, from the participant notes. No code taken from anywhere.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from .reon_window import window_usable


def _bisect(f, target: float, lo: float, hi: float, iters: int = 50) -> Optional[float]:
    """Smallest x in [lo, hi] with f(x) >= target for nondecreasing f; None if f(hi) < target."""
    if f(hi) < target:
        return None
    if f(lo) >= target:
        return lo
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if f(mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def expected_ratio(cv: float, n: int, n_min: Optional[int] = None, trials: int = 3000, seed: int = 0) -> float:
    """Expected (control usable / conventional usable) for n independent Normal(1, cv) cells (clipped at 0.05); n_min = cells that must stay in
    circuit (None = ideal, uses every cell). Same random draws for every cv, so the result is smooth in cv."""
    if cv < 0 or n < 1:
        raise ValueError("need cv >= 0 and n >= 1")
    if n_min is not None and not (1 <= n_min <= n):
        raise ValueError("n_min must be between 1 and n")
    z = np.random.default_rng(seed).standard_normal((trials, n))
    x = np.maximum(1.0 + cv * z, 0.05)
    if n_min is None:
        return float((x.sum(axis=1) / (n * x.min(axis=1))).mean())
    return float(np.mean([window_usable(r, n_min) / (n * r.min()) for r in x]))


def required_cv(target_ratio: float, n: int, n_min: Optional[int] = None, cv_max: float = 1.0, trials: int = 3000, seed: int = 0) -> Optional[float]:
    """Spread of capacities (CV) at which the expected usable-energy ratio reaches target_ratio (2.0 = "2X"). None if not reachable below cv_max."""
    if target_ratio < 1.0:
        raise ValueError("target_ratio must be >= 1")
    return _bisect(lambda c: expected_ratio(c, n, n_min, trials, seed), target_ratio, 0.0, cv_max)


def life_ratio_linear(rates: Sequence[float]) -> float:
    """Service-life ratio (control / conventional) when cell i fades linearly at rate_i: max rate / mean rate."""
    r = np.asarray(rates, dtype=float)
    if r.ndim != 1 or r.size == 0 or not np.isfinite(r).all() or (r <= 0).any():
        raise ValueError("need positive finite fade rates")
    return float(r.max() / r.mean())


def expected_life_ratio(cv: float, n: int, trials: int = 3000, seed: int = 0) -> float:
    """Expected max/mean of n lognormal fade rates whose coefficient of variation is cv (common random draws)."""
    if cv < 0 or n < 1:
        raise ValueError("need cv >= 0 and n >= 1")
    sigma = np.sqrt(np.log(1.0 + cv * cv))
    z = np.random.default_rng(seed).standard_normal((trials, n))
    r = np.exp(sigma * z - 0.5 * sigma * sigma)
    return float((r.max(axis=1) / r.mean(axis=1)).mean())


def required_rate_cv(target_ratio: float, n: int, cv_max: float = 3.0, trials: int = 3000, seed: int = 0) -> Optional[float]:
    """Spread (CV) of cell fade rates at which the expected life ratio reaches target_ratio. None if not reachable below cv_max."""
    if target_ratio < 1.0:
        raise ValueError("target_ratio must be >= 1")
    return _bisect(lambda c: expected_life_ratio(c, n, trials, seed), target_ratio, 0.0, cv_max)
