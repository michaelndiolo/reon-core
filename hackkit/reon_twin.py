"""reon_twin: the data behind the 3D twin tab (no Streamlit here, so it can be tested).

The twin is a drawing of one store's 250-cell string and the store it powers. It decides nothing: every number comes from reon_grid.analyse (the same engine the dashboard uses tab).
This module only turns that analysis into the small dict the 3D scene draws, and handles click-to-fail / click-to-repair. Simulation on assumed sodium-ion behaviour, not REON data."""
from __future__ import annotations

import numpy as np


def toggle(failed, cell: int, n: int = 250) -> list[int]:
    """Click on a cell: fail it if it is healthy, repair it if it is already open. Returns a sorted list of failed cell indices."""
    cell = int(cell)
    if not 0 <= cell < n:
        return sorted(int(i) for i in failed)
    s = {int(i) for i in failed}
    s.symmetric_difference_update({cell})
    return sorted(s)


def payload(health, an: dict, load_kw: float) -> dict:
    """What the scene needs. `an` is the dict returned by reon_grid.analyse for the same health and failed list.
    line_plain / line_ours are the usable-level planes as a fraction of day-1 capacity: a plain string is capped by its weakest cell (and is 0 with any open cell); with control the weakest cells may leave early, so the line sits at the (n-K)th strongest live cell."""
    h = np.asarray(health, dtype=float)
    n, K = int(an["n"]), int(an["K"])
    failed = list(an["failed_cells"])
    live = np.sort(np.delete(h, failed))[::-1] if failed else np.sort(h)[::-1]
    online = not an["refused"]
    line_ours = float(live[n - K - 1]) if online and live.size > n - K - 1 else 0.0
    line_plain = float(h.min()) if not failed else 0.0
    return dict(
        health=[round(float(x), 4) for x in h], failed=[int(i) for i in failed], early=[int(i) for i in an["early"]],
        refused=bool(an["refused"]), plain_kwh=float(an["plain_kwh"]), ours_kwh=float(an["ours_kwh"]), plain_h=float(an["plain_h"]), ours_h=float(an["ours_h"]),
        line_plain=line_plain, line_ours=line_ours, load_kw=float(load_kw), K=K,
    )
