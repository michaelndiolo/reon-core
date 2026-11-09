"""Fade slope per cell: REON's "the curve, the trend and the left-to-right comparison, not single maximums" (garbled recording: confirm what he meant).
Our reading, on REAL data: the Nature Energy 2026 packs give each of 95 cells at two ages (80,000 and 280,000 km). Two ages make a slope, not a curve; REON's own per-cell history would give the curve.
  * slope: percentage points of day-1 capacity a cell lost between the two ages;
  * left to right: each cell is compared with the median of its 8 neighbours along the pack (positions as the data give them), not only with the whole pack;
  * snapshot versus trend: is the cell that ends up weakest also the weakest at the early age? is it the steepest fader?
Not a predictor: with two ages we cannot test a forecast out of sample. It shows what a snapshot ranking misses."""
from __future__ import annotations

import csv
from typing import Dict, Tuple

import numpy as np

from hackkit.reon_guard import need


def load_cells(path: str = "examples/data/nature_fig4_cells.csv") -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """pack -> (capacity at the early age, capacity at the late age), cells in the order the data give them."""
    rows = list(csv.reader(l for l in open(path) if not l.startswith("#") and not l.startswith('"#')))[1:]
    out: Dict[str, list] = {}
    for p, c, e, l in rows:
        out.setdefault(p, []).append((int(c), float(e), float(l)))
    res = {}
    for p, v in out.items():
        v.sort()
        a = np.array(v)
        res[p] = (a[:, 1], a[:, 2])
    return res


def fade_pp(early, late) -> np.ndarray:
    e, l = np.asarray(early, float), np.asarray(late, float)
    need(e.shape == l.shape and e.ndim == 1 and e.size >= 10, "slope: two equal-length arrays of at least 10 cells")
    return (e - l) * 100.0


def local_median(x, half: int = 4) -> np.ndarray:
    """Median of the neighbours within `half` positions on each side, the cell itself excluded."""
    x = np.asarray(x, float)
    out = np.empty_like(x)
    for i in range(x.size):
        lo, hi = max(0, i - half), min(x.size, i + half + 1)
        out[i] = np.median(np.delete(x[lo:hi], i - lo))
    return out


def outliers(fade, half: int = 4, k: float = 3.0):
    """Cells fading faster than their neighbours by more than k robust standard deviations of the residuals. Returns (flag array, local median array, residual scale)."""
    f = np.asarray(fade, float)
    lm = local_median(f, half)
    res = f - lm
    scale = 1.4826 * float(np.median(np.abs(res - np.median(res)))) or 1e-9
    return res > k * scale, lm, scale


def snapshot_vs_trend(packs: Dict[str, Tuple[np.ndarray, np.ndarray]]) -> dict:
    """Per pack and overall: is the cell that ends up weakest the weakest early (snapshot), or the steepest fader (trend)? Also the spread of starting capacity against the spread of fade."""
    rows = {}
    for k, (e, l) in packs.items():
        f = fade_pp(e, l)
        wl = int(np.argmin(l))
        rows[k] = dict(final_weakest=wl, early_rank_of_final_weakest=int((e < e[wl]).sum() + 1), same_weakest=bool(int(np.argmin(e)) == wl), steepest_is_final_weakest=bool(int(np.argmax(f)) == wl),
                       early_sd_pp=float(100 * np.std(e)), fade_sd_pp=float(np.std(f)), n=int(e.size))
    n = len(rows)
    return dict(per_pack=rows, packs=n, same_weakest=sum(r["same_weakest"] for r in rows.values()), steepest_is_final_weakest=sum(r["steepest_is_final_weakest"] for r in rows.values()),
                median_early_rank=float(np.median([r["early_rank_of_final_weakest"] for r in rows.values()])), fade_spread_larger=sum(r["fade_sd_pp"] > r["early_sd_pp"] for r in rows.values()))
