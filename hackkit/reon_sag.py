"""reon_sag: a VOLTAGE floor with sag, for policy modules, in place of the cell-count window (reon_wear window=0.9 -> at most 25 of 250 cells bypassed).

The cell-count rule (reon_window.window_usable) says "keep at least n_min cells in circuit". The inverter does not count cells, it reads volts: the string voltage is
    V(Q) = sum over engaged cells of ( OCV(soc_i) - I x R_i ),      soc_i = 1 - Q / c_i
where Q is the charge every engaged cell has passed (series string, one current I, so the weakest engaged cell's SOC falls fastest). A cell is EMPTY when its terminal voltage
OCV - I R reaches v_cut (2.5 V datasheet cutoff). An empty cell is bypassed if the bypass rule allows it (a count cap k, a per-cell mask of which cells carry a switch, or no limit);
otherwise the string stops. The string also stops the moment V(Q) falls below v_floor_frac x n x v_nom_cell (250 x 3.6 V = 900 V nominal).

V(Q) only falls as Q grows (every OCV falls, every bypass removes a positive voltage), so the stop charge is found by bisection, vectorized over draws, and the energy up to it is
exact (OCV curves are piecewise linear, so its integral is closed form). Constant CURRENT, not constant power: at the 0.5 C rated default the current would rise by about 10 % as the
string sags; ignored (first-order picture, like reon_window).

Every parameter below the curve shapes is ASSUMED (docs/stress/sag_assumptions.md). Curve shapes are reon_voltage.CURVES (shapes ASSUMED inside the sourced 2.5 to 4.2 V window).
Not REON's measured behavior: the inverter minimum voltage is UNKNOWN (top question for REON).
"""
from __future__ import annotations

import numpy as np

from hackkit.reon_voltage import CURVES

V_NOM_CELL = 3.6                     # sodium-ion nominal, datasheet (docs/SOURCES.md row "Sodium-ion 18650 cell")
V_CUT = 2.5                          # sodium-ion discharge cutoff, same datasheet
PACK_WH = 60_000.0                   # 60 kWh EBS Na+ (REON one pager)
RATED_W = 30_000.0                   # 30 kW EBS Na+ (REON one pager)
N_CELLS = 250
Q0_AH = PACK_WH / (N_CELLS * V_NOM_CELL)          # 66.7 Ah per series cell (DERIVED)
CURRENT_A = RATED_W / (N_CELLS * V_NOM_CELL)      # 33.3 A at rated power (DERIVED, worst case for sag)
R_CELL_OHM = 0.6e-3                  # ASSUMED: 20 mOhm (2 Ah 18650 AC IR, datasheet upper bound) scaled by 2/66.7 for a 66.7 Ah cell -> 0.6 mOhm; sweep 0.3 to 3 mOhm


def _curve(curve):
    if curve not in CURVES:
        raise ValueError(f"reon_sag: unknown curve {curve!r}")
    xs, ys = (np.array(a, dtype=float) for a in zip(*CURVES[curve]))
    # cumulative integral of OCV over soc at each breakpoint (trapezoids are exact for a piecewise-linear curve)
    F = np.concatenate([[0.0], np.cumsum(np.diff(xs) * (ys[1:] + ys[:-1]) / 2.0)])
    return xs, ys, F


def _ocv(xs, ys, soc):
    return np.interp(soc, xs, ys)


def _F(xs, ys, F, soc):
    """Integral of OCV from soc = 0 to soc (soc in [0, 1])."""
    soc = np.clip(soc, 0.0, 1.0)
    j = np.clip(np.searchsorted(xs, soc, side="right") - 1, 0, len(xs) - 2)
    v = _ocv(xs, ys, soc)
    return F[j] + (soc - xs[j]) * (ys[j] + v) / 2.0


def _soc_at_voltage(xs, ys, v):
    """Inverse OCV (curves are increasing). Below the curve -> 0, above -> 1."""
    return np.interp(v, ys, xs, left=0.0, right=1.0)


def _prep(caps, r_cell_ohm):
    c = np.asarray(caps, dtype=float)
    if c.ndim == 1:
        c = c[None, :]
    if c.ndim != 2 or c.shape[1] < 1:
        raise ValueError("reon_sag: caps must be (cells,) or (draws, cells)")
    if not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("reon_sag: capacities must be finite and positive")
    r = np.broadcast_to(np.asarray(r_cell_ohm, dtype=float), c.shape)
    if not np.isfinite(r).all() or (r < 0).any():
        raise ValueError("reon_sag: resistance must be finite and >= 0")
    return c, r


def _q_rule(q_empty, bypass):
    """Charge at which the bypass rule forces a stop (before any voltage check). q_empty: (D, n) charge at which each cell is empty."""
    D, n = q_empty.shape
    if bypass is None:                                   # every cell has a switch, no count cap
        return q_empty.max(axis=1)
    b = np.asarray(bypass)
    if b.dtype == bool:                                  # mask: True where the cell carries a bypass switch
        m = np.broadcast_to(b, (D, n))
        return np.where(m, np.inf, q_empty).min(axis=1).clip(max=q_empty.max(axis=1))
    k = np.broadcast_to(b.astype(int), (D,))             # count cap: at most k cells bypassed at once -> stop when the (k+1)-th cell is empty
    if (k < 0).any():
        raise ValueError("reon_sag: bypass count must be >= 0")
    srt = np.sort(q_empty, axis=1)
    kk = np.minimum(k, n - 1)
    return srt[np.arange(D), kk]


def string_voltage(caps, q, *, curve="sodium-ion", r_cell_ohm=R_CELL_OHM, current_a=CURRENT_A, q0_ah=Q0_AH, v_cut=V_CUT):
    """Terminal string voltage after charge q (relative units, 1 = q0_ah) has passed every engaged cell, empty cells assumed bypassed. caps (D, n) or (n,), q (D,) or scalar. Returns (D,)."""
    xs, ys, _ = _curve(curve)
    c, r = _prep(caps, r_cell_ohm)
    ir = current_a * r
    q_empty = c * (1.0 - _soc_at_voltage(xs, ys, v_cut + ir))
    q = np.broadcast_to(np.asarray(q, dtype=float), (c.shape[0],))[:, None]
    eng = q < q_empty
    v = _ocv(xs, ys, 1.0 - np.minimum(q, c) / c) - ir
    return np.where(eng, v, 0.0).sum(axis=1)


def usable_fraction(caps, bypass=None, *, v_floor_frac=0.9, curve="sodium-ion", r_cell_ohm=R_CELL_OHM, current_a=CURRENT_A, q0_ah=Q0_AH,
                    v_nom_cell=V_NOM_CELL, v_cut=V_CUT, iters=60, details=False):
    """Share of each pack's energy delivered at the DC terminals before the string stops.

    caps: (n,) or (draws, n) capacities relative to q0_ah. bypass: None (every cell switchable, no cap), an int or (draws,) ints (at most k cells bypassed at once: the cell-count
    rule), or a bool mask (n,) / (draws, n) (True = cell has a switch). v_floor_frac: string minimum as a share of n x v_nom_cell; 0 = no floor. r_cell_ohm: scalar or (n,)/(draws, n).
    Denominator = the cells' own zero-current energy from full to empty (sum_i c_i x integral of OCV over 0..1), so 1.0 means nothing is left in any cell and nothing lost in R.
    Returns (draws,) array, or a scalar for 1-D caps; with details=True also a dict (q_stop, q_rule, stop_by ('floor' or 'rule'), ah_equiv = sum_i min(q_stop, c_i) the
    reon_window units, energy_wh, ideal_wh, bypassed = cells emptied and bypassed before the stop)."""
    one = np.asarray(caps).ndim == 1
    xs, ys, F = _curve(curve)
    c, r = _prep(caps, r_cell_ohm)
    if not 0.0 <= v_floor_frac < 1.5:
        raise ValueError("reon_sag: v_floor_frac must be in [0, 1.5)")
    if current_a < 0 or q0_ah <= 0:
        raise ValueError("reon_sag: current >= 0, q0 > 0")
    D, n = c.shape
    ir = current_a * r
    q_empty = c * (1.0 - _soc_at_voltage(xs, ys, v_cut + ir))
    q_rule = _q_rule(q_empty, bypass)
    v_floor = v_floor_frac * n * v_nom_cell

    def vstr(q):
        qq = q[:, None]
        v = _ocv(xs, ys, 1.0 - np.minimum(qq, c) / c) - ir
        return np.where(qq < q_empty, v, 0.0).sum(axis=1)

    ok_end = vstr(q_rule * (1.0 - 1e-12)) >= v_floor            # just before the rule stop, still above the floor -> the rule stops it
    lo = np.zeros(D)
    hi = q_rule.copy()
    for _ in range(iters):                                        # sup{q : V(q) >= floor}; V is nonincreasing in q
        mid = (lo + hi) / 2.0
        good = vstr(mid) >= v_floor
        lo = np.where(good, mid, lo)
        hi = np.where(good, hi, mid)
    v0_ok = vstr(np.zeros(D)) >= v_floor
    q_stop = np.where(ok_end, q_rule, np.where(v0_ok, lo, 0.0))

    qi = np.minimum(q_stop[:, None], q_empty)                    # charge each cell actually passed
    e_rel = c * (_F(xs, ys, F, np.ones_like(c)) - _F(xs, ys, F, 1.0 - qi / c)) - ir * qi   # per cell, V x relative Ah
    ideal_rel = c * F[-1]
    frac = e_rel.sum(axis=1) / ideal_rel.sum(axis=1)
    out = frac[0] if one else frac
    if not details:
        return out
    info = dict(q_stop=q_stop, q_rule=q_rule, stop_by=np.where(ok_end, "rule", "floor"), ah_equiv=np.minimum(q_stop[:, None], c).sum(axis=1),
                energy_wh=e_rel.sum(axis=1) * q0_ah, ideal_wh=ideal_rel.sum(axis=1) * q0_ah, bypassed=(q_empty < q_stop[:, None]).sum(axis=1))
    return out, info


def max_bypass(caps, soc, *, v_floor_frac=0.9, curve="sodium-ion", r_cell_ohm=R_CELL_OHM, current_a=CURRENT_A, v_nom_cell=V_NOM_CELL):
    """Most cells that can be bypassed right now without the string falling below the floor, bypassing the lowest-voltage cells first. soc: per-cell SOC, broadcastable to caps
    (a scalar means every cell sits at that SOC; use soc_after(caps, q) for a series string that has passed charge q). caps only sets the shape (and pairs with an R array).
    Returns (draws,) ints, or an int for 1-D caps; -1 means the string is already below the floor with nothing bypassed."""
    one = np.asarray(caps).ndim == 1
    xs, ys, _ = _curve(curve)
    c, r = _prep(caps, r_cell_ohm)
    s = np.broadcast_to(np.asarray(soc, dtype=float), c.shape)
    if ((s < 0) | (s > 1)).any():
        raise ValueError("reon_sag: soc must be in [0, 1]")
    n = c.shape[1]
    v = np.sort(_ocv(xs, ys, s) - current_a * r, axis=1)[:, ::-1]      # highest first
    keep = np.cumsum(v, axis=1)                                          # keep[:, j] = string voltage with the j+1 best cells
    ok = keep >= v_floor_frac * n * v_nom_cell
    need_cells = np.where(ok.any(axis=1), ok.argmax(axis=1) + 1, n + 1)
    k = np.where(need_cells <= n, n - need_cells, -1)
    return int(k[0]) if one else k


def soc_after(caps, q):
    """Per-cell SOC of a series string after charge q (relative units) with no cell bypassed yet: 1 - q / c_i, floored at 0."""
    c = np.asarray(caps, dtype=float)
    q = np.asarray(q, dtype=float)
    if c.ndim == 2 and q.ndim == 1:
        q = q[:, None]
    return np.clip(1.0 - q / c, 0.0, 1.0)
