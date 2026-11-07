"""Reference implementation of recheck/SPEC.md, written from the spec alone (no sight of hackkit/pack.py).

usable(caps, eta, r, volts=None) -> dict with usable_conv_ah, usable_ctrl_ah, util_conv, util_ctrl, gain (and kWh when volts is given).
compare(candidate, n_random, seed) runs a candidate implementation against this one on the spec's cases plus seeded random cell sets.
`candidate(caps, eta, r)` must return a dict with keys usable_conv_ah and usable_ctrl_ah (wrap Aaryan's pack.py in a lambda if its names differ).
"""
from __future__ import annotations

import numpy as np

SPEC_CASES = {
    "A": ([100, 90, 80, 70], 1.00, 0.0),
    "B": ([100, 90, 80, 70], 0.97, 0.0),
    "C": ([100, 90, 80, 70], 1.00, 0.10),
    "D": ([100, 100, 100, 100], 1.00, 0.0),
    "E": ([100], 1.00, 0.0),
    "F": ([100, 100, 100, 50], 1.00, 0.0),
    "G": ([20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59], 1.00, 0.0),
}


def usable(caps, eta: float = 1.0, r: float = 0.0, volts: float | None = None) -> dict:
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size == 0:
        raise ValueError("need at least one cell")
    if not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("every capacity must be finite and positive")
    if not (0.0 < eta <= 1.0):
        raise ValueError("eta must be in (0, 1]")
    if not (0.0 <= r < 1.0):
        raise ValueError("r must be in [0, 1)")
    total = float(c.sum())
    conv = float(c.size * c.min()) * (1.0 - r)
    ctrl = total * eta * (1.0 - r)
    out = {"usable_conv_ah": conv, "usable_ctrl_ah": ctrl, "util_conv": conv / total, "util_ctrl": ctrl / total, "gain": ctrl / conv - 1.0}
    if volts is not None:
        out["usable_conv_kwh"] = conv * volts * 1e-3
        out["usable_ctrl_kwh"] = ctrl * volts * 1e-3
    return out


def compare(candidate, n_random: int = 200, seed: int = 0, tol: float = 1e-9) -> int:
    """Number of disagreements between candidate and the reference over the spec cases and n_random seeded cell sets (0 = agree)."""
    rng = np.random.default_rng(seed)
    cases = list(SPEC_CASES.values())
    for _ in range(n_random):
        n = int(rng.integers(1, 17))
        cases.append((list(rng.uniform(40.0, 110.0, n)), float(rng.uniform(0.8, 1.0)), float(rng.uniform(0.0, 0.3))))
    bad = 0
    for caps, eta, r in cases:
        ref = usable(caps, eta, r)
        got = candidate(caps, eta, r)
        for k in ("usable_conv_ah", "usable_ctrl_ah"):
            if abs(got[k] - ref[k]) > tol * max(1.0, abs(ref[k])):
                bad += 1
                print(f"MISMATCH {k}: caps={caps} eta={eta} r={r} candidate={got[k]} reference={ref[k]}")
    return bad
