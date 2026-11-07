"""String view (Nalia's click-to-fail idea, rebuilt at Tim Ren's scale: 250 cells in series, about 90 % connected in normal use).
Pure logic for the dashboard grid; the drawing is in reon_visuals.py.

Health of each cell = capacity / day-1 capacity. The 250 cells are drawn from the REAL spread of late-life cells (Nature Energy 2026, pooled and scaled to the chosen mean health), plus a few planted weak cells like REON's 16-cell example (one at 70 %).
Rules, all simple on purpose:
  * at most K = floor(n x (1 - window)) cells may be out of the string at once (the inverter's minimum voltage; REON: about 90 % connected -> window 0.9, K = 25 at n = 250);
  * a cell that fails open is out for good and uses up one of the K places (cells in series: an open cell breaks the path, so a plain string with any open cell delivers nothing);
  * with the rest, control lets up to K - failed of the weakest cells leave early as they empty (reon_window.window_usable), losing `loss` to switches;
  * one more failure than K places = the string drops below the inverter minimum: refused, string offline (hardware keeps safety authority).
The five responses come from reon_response.decide on the live cells. Nothing here is REON's measured behaviour."""
from __future__ import annotations

import numpy as np

from hackkit import reon_response as R
from hackkit import reon_window as RW
from hackkit.reon_guard import need
from hackkit.reon_reliability import bypass_cap


def pooled_relative(packs) -> np.ndarray:
    """Every real cell as capacity / median capacity of its own pack."""
    return np.concatenate([np.asarray(v, dtype=float) / np.median(v) for v in packs.values()])


def make_string(pool, n: int = 250, seed: int = 4, mean_health: float = 0.85, planted=(0.70, 0.78)) -> np.ndarray:
    """n cell healths: a draw from the real relative spread scaled to `mean_health`, with the planted weak cells (health values) put at spread-out positions."""
    pool = np.asarray(pool, dtype=float)
    need(n >= 10 and 0.3 < mean_health <= 1.0 and pool.size >= 10, "grid: n >= 10, mean health in (0.3, 1], a pool of real cells")
    rng = np.random.default_rng(seed)
    h = rng.choice(pool, size=n, replace=True) * mean_health
    pos = rng.choice(n, size=len(planted), replace=False)
    for p, v in zip(pos, planted):
        h[p] = v
    return np.clip(h, 0.05, 1.0)


def analyse(health, failed, window: float = 0.9, nameplate_kwh: float = 60.0, loss: float = 0.04, load_kw: float = 5.0) -> dict:
    h = np.asarray(health, dtype=float)
    n = h.size
    need(n >= 10 and (h > 0).all() and 0.0 < window <= 1.0 and nameplate_kwh > 0 and 0 <= loss < 1 and load_kw > 0, "grid: n >= 10, positive healths, window in (0, 1], positive kWh and load, loss in [0, 1)")
    failed = sorted({int(i) for i in failed})
    need(all(0 <= i < n for i in failed), "grid: failed cell index out of range")
    K = bypass_cap(n, window)
    f = len(failed)
    unit = nameplate_kwh / n
    live_idx = [i for i in range(n) if i not in set(failed)]
    out = dict(n=n, K=K, failed=f, room=K - f, online=f <= K, window=window, refused=False, message="", early=[], actions=[], failed_cells=failed)
    out["plain_kwh"] = 0.0 if f > 0 else float(h.min() * nameplate_kwh)
    if f > K:
        out.update(refused=True, message="Cannot bypass: the inverter minimum voltage is reached. String offline; the hardware opens it and calls a crew.", ours_kwh=0.0)
        out["v_now"] = (n - f) / n
    else:
        live = h[live_idx]
        usable = RW.window_usable(live, n - K) * (1.0 - loss)
        out["ours_kwh"] = float(usable * unit)
        out["v_now"] = (n - f) / n
        thr = np.sort(live)[::-1][n - K - 1]                         # the (n-K)th largest live cell: weaker cells may leave early
        out["early"] = [i for i in live_idx if h[i] < thr]
        med = np.median(live)
        cells = []
        for pos, i in enumerate(live_idx):
            rest = np.delete(live, pos)
            rel = float(h[i] / np.median(rest))
            cells.append(R.Cell(i=i, cap_rel=rel, bad_cycles=R.Limits().persist_cycles if rel < 1 - R.Limits().weak_frac else 0))
        acts = R.decide(cells, R.Context(n_engaged=len(live), n_min=n - K, bypass_left=K - f, islanded=True))
        out["actions"] = [dict(kind=a.kind, cells=list(a.cells), reason=a.reason) for a in acts]
    out["plain_h"] = out["plain_kwh"] / load_kw
    out["ours_h"] = out["ours_kwh"] / load_kw
    out["v_end"] = (n - K) / n
    return out
