"""Second life (REON: module-level second life is possible and he supports it; rebuilding from modules or cells is needed; cells inside a module age differently by position).
Scenario: a retired EV pack's cells are re-used as ONE fixed series string in a stationary system (the brief's baseline). Real late-life cell capacities (Nature Energy 2026, Fig 4, 12 EVs at 280,000 km, REAL).
Options, all scored on the same cells:
  plain        n x weakest cell (the brief's baseline)
  module g     modules of g neighbouring cells (in the order the pack gave them) switch as one; a module's capacity is its weakest cell
  cell level   every cell can leave individually
  BOTH switched options obey the same voltage window: at least `window` of the cells must stay in the string (REON: about 90 % connected in normal use), so a coarse module may not be able to leave at all
  (reon_window.window_usable on the module-weakest values, times g)
  upper bound  sum of all cells
Value is STATIC (no further ageing, the same cells for `years`), so it is a first-order screen, not a forecast. Rather than invent how switch cost scales with the number of switches, it reports the FLIP POINT: the most
electronics can cost per kWh of cell energy before the option stops paying: value per kWh-year x years x extra usable share (decision-flip threshold pattern from the participant notes).
Not priced: testing and disassembly (REON has not said), certification of a rebuilt pack. Sorting cells into matched parallel strings is the usual rival and recovers most of the gain at these spreads (hackkit/reon_sorting.py)."""
from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np

from hackkit import reon_window as RW
from hackkit.reon_guard import need


def options(caps: Sequence[float], groups=(19, 5), window: float = 0.9) -> Dict[str, float]:
    """Usable capacity (same units as caps) for each option."""
    c = np.asarray(caps, dtype=float)
    need(c.ndim == 1 and c.size >= 2 and (c > 0).all() and 0.0 < window <= 1.0, "secondlife: positive capacities, window in (0, 1]")
    out = {"plain": float(c.size * c.min())}
    for g in groups:
        need(c.size % g == 0 and g >= 1, "secondlife: module size must divide the number of cells")
        mod = c.reshape(-1, g).min(axis=1)
        out[f"module of {g}"] = float(g * RW.window_usable(mod, int(math.ceil(window * mod.size - 1e-9))))
    out["cell level"] = float(RW.window_usable(c, int(math.ceil(window * c.size - 1e-9))))
    out["upper bound"] = float(c.sum())
    return out


def table(packs: Dict[str, Sequence[float]], groups=(19, 5), window: float = 0.9, loss: float = 0.04, value: float = 40.0, years: float = 8.0) -> Dict[str, dict]:
    """Per option, over all packs: gain over plain (before switch loss) median/min/max, and the flip point (max electronics cost per kWh of cell energy at which the option pays).
    Switch loss applies to the switched options only (usable x (1 - loss)); the plain string has none."""
    need(0.0 <= loss < 0.5 and value >= 0 and years > 0, "secondlife: loss in [0, 0.5), nonnegative value, positive years")
    rows: Dict[str, dict] = {}
    per = {k: [] for k in options(next(iter(packs.values())), groups, window)}
    share = {k: [] for k in per}
    for caps in packs.values():
        o = options(caps, groups, window)
        total = o["upper bound"]
        for k, v in o.items():
            per[k].append(v / o["plain"] - 1.0)
            net = v * (1.0 - loss if k not in ("plain", "upper bound") else 1.0) / total - o["plain"] / total
            share[k].append(net)
    for k in per:
        if k in ("plain",):
            continue
        sh = np.array(share[k])
        flip = value * years * sh
        rows[k] = dict(gain_median=float(np.median(per[k])), gain_min=float(np.min(per[k])), gain_max=float(np.max(per[k])),
                       extra_share_median=float(np.median(sh)), flip_cost_median=float(np.median(flip)), flip_cost_min=float(np.min(flip)), flip_cost_max=float(np.max(flip)))
    return rows
