"""reon_granularity: where should the switches go? One per cell, one per group of k cells, or none.

Worst result so far: on well-matched cells a switch at every cell gains only 1 to 3% and costs more per extra kWh than anything
else. Reversing that: put a switch on a GROUP of k series cells instead. The group then behaves like one big cell limited by its weakest member, and groups
can be bypassed, so the pack delivers   sum over groups of  k x (weakest cell in the group).   k = 1 is cell-level control (the sum of all cells), k = N is
no control (N x weakest). Electronics scale with the number of switches (e / k per kWh of nameplate); the series loss scales with the number of switches in
the path (loss / k^p, p = 1 if proportional to switch count, p = 0 if fixed); electronics e / k^q (q = 1 if per switch, q = 0 if the cost does not fall
at all, 0.5 if bigger-voltage switches eat half the saving). These scalings are assumptions to be confirmed by REON; the table shows whether the
conclusion survives them. Per-cell voltage sensing is assumed to exist already (any BMS has it) and is not charged to the switches.
order = "as_found" keeps the cells in the order given (modules as they came); "sorted" ranks the cells first (needs repacking at cell level).
No default numbers live here: every cost, loss and value is an argument that must be sourced or flagged ASSUMED.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from .reon_econ import capital_recovery_factor


def group_usable(caps: Sequence[float], k: int, order: str = "as_found") -> float:
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size < 2 or (c <= 0).any():
        raise ValueError("need at least two positive capacities")
    if int(k) != k or not (1 <= k <= c.size) or c.size % int(k) != 0:
        raise ValueError("group size k must divide the number of cells")
    if order == "sorted":
        c = np.sort(c)[::-1]
    elif order != "as_found":
        raise ValueError("order must be 'as_found' or 'sorted'")
    return float(sum(k * g.min() for g in c.reshape(-1, int(k))))


def granularity_table(caps: Sequence[float], *, electronics_per_kwh_cell_level: float, loss_cell_level: float, value_per_kwh_year: float,
                      rate: float, years: float, ks: Optional[Sequence[int]] = None, loss_exponent: float = 1.0, cost_exponent: float = 1.0, order: str = "as_found") -> list:
    """One row per group size k (k < N). Money is per kWh of NAMEPLATE per year: value of the extra usable energy minus the yearly cost of the electronics."""
    c = np.asarray(caps, dtype=float)
    n = c.size
    if ks is None:
        ks = [k for k in range(1, n) if n % k == 0]
    base, nameplate = n * c.min(), c.sum()
    crf = capital_recovery_factor(rate, years)
    rows = []
    for k in ks:
        u = group_usable(c, k, order)
        loss = loss_cell_level / (k ** loss_exponent)
        net = u * (1.0 - loss)
        extra = net - base
        e_k = electronics_per_kwh_cell_level / (k ** cost_exponent)
        value = max(extra, 0.0) / nameplate * value_per_kwh_year
        cost = e_k * crf
        rows.append({
            "k": int(k), "switches": n // k, "gain_ideal": u / base - 1.0, "loss": loss, "gain_net": net / base - 1.0,
            "electronics_per_kwh": e_k,
            "cost_per_extra_kwh": (e_k * nameplate / extra) if extra > 0 else None,
            "net_value_per_nameplate_kwh_year": value - cost, "repays": value - cost >= 0.0 and extra > 0,
        })
    return rows


def best_granularity(rows: list) -> Optional[dict]:
    """Row with the highest net value, or None when no row beats doing nothing (net value > 0 is required)."""
    ok = [r for r in rows if r["net_value_per_nameplate_kwh_year"] > 0]
    return max(ok, key=lambda r: r["net_value_per_nameplate_kwh_year"]) if ok else None
