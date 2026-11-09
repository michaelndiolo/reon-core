"""reon_loss: how much switching/conversion loss a cell-level controller can afford before it stops beating a conventional pack.

Pack model (recheck/SPEC.md): conventional usable = N x weakest cell; control usable = sum of cells x eta, where eta is the fraction of
energy that survives the switching and conversion path. Both are scaled by (1 - r) for a reserve, which cancels in every ratio here.

break_even_eta(caps) = N x min / sum. At or below it, control delivers no more than the conventional pack.
No default efficiency lives here: eta is an input and must be sourced (the literature range is 0.95 to 0.99).
Patterns only; the idea of a break-even loss is generic, no code is taken from anywhere.
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


def break_even_eta(caps: Sequence[float]) -> float:
    """Efficiency at which control and conventional deliver the same energy: N x min / sum. 1.0 when all cells are equal."""
    c = _caps(caps)
    return float(c.size * c.min() / c.sum())


def break_even_loss(caps: Sequence[float]) -> float:
    """1 - break_even_eta: the largest loss fraction control can carry and still tie the conventional pack."""
    return 1.0 - break_even_eta(caps)


def net_gain(caps: Sequence[float], eta: float) -> float:
    """Control usable / conventional usable - 1 at efficiency eta. Negative means control delivers less than the conventional pack."""
    if not (0.0 < eta <= 1.0):
        raise ValueError("eta must be in (0, 1]")
    c = _caps(caps)
    return float(c.sum() * eta / (c.size * c.min()) - 1.0)


def loss_table(caps: Sequence[float], losses: Sequence[float]) -> dict:
    """{'gain_at_no_loss', 'break_even_loss', 'net_gain': {loss: gain}} for each loss fraction in `losses` (each in [0, 1))."""
    out = {}
    for loss in losses:
        if not (0.0 <= loss < 1.0):
            raise ValueError("each loss must be in [0, 1)")
        out[float(loss)] = net_gain(caps, 1.0 - float(loss))
    return {"gain_at_no_loss": net_gain(caps, 1.0), "break_even_loss": break_even_loss(caps), "net_gain": out}
