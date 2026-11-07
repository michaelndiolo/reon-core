"""reon_drift: sorting is a one-time fix, control keeps working while the cells drift apart.

A static comparison (reon_sorting) sorts the cells once. But cells fade at different rates, so strings that were matched on day 1 are mismatched again
later, while cell-level control follows the drift. This module ages the cells forward and compares, until the pack's deliverable capacity falls below an
end-of-life level (REON's slide: "industry retirement standard is set on system deliverable capacity"):
  single string : N x weakest cell               (the weakest-cell pack)
  as found      : strings of m in parallel in the order given
  sorted once   : strings of m built from cells ranked by their day-1 capacity, never changed
  control       : sum of the cells x (1 - loss)
Fade model: linear, c_i(t) = c_i0 x (1 - f_i t), fade rates f_i ~ Normal(mean, cv x mean) truncated at 0. The mean rate, the cv and the end-of-life level are
ASSUMED inputs (no default here). Linear fade is a simplification. weak_corr sets how the fade rate relates to day-1 weakness: 0 = independent, +1 = the weakest
cells always fade fastest (bad for sorted strings of mixed cells, good for control), -1 = the weakest fade slowest (cells converge; the case that favours sorting).
Output: mean years until end of life and mean delivered energy (Ah-years of usable capacity, an index of throughput), and the extra control gives.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

def _trap(y: np.ndarray, x: np.ndarray) -> float:
    return float(((y[1:] + y[:-1]) * 0.5 * np.diff(x)).sum()) if y.size > 1 else 0.0


METHODS = ("single_string", "as_found", "sorted_once", "control")


def _usable(c: np.ndarray, groups: np.ndarray, m: int) -> np.ndarray:
    """c: (steps, N) capacities over time. Returns usable for the four methods, each (steps,)."""
    steps, n = c.shape
    single = n * c.min(axis=1)
    as_found = m * c.reshape(steps, n // m, m).min(axis=2).sum(axis=1)
    cs = c[:, groups]
    sorted_once = m * cs.reshape(steps, n // m, m).min(axis=2).sum(axis=1)
    return single, as_found, sorted_once, c.sum(axis=1)


def lifetime_compare(caps: Sequence[float], m: int, *, fade_mean_per_year: float, fade_cv: float, eol_frac: float, loss: float,
                     trials: int = 300, seed: int = 0, horizon_years: float = 40.0, steps: int = 1600, weak_corr: float = 0.0) -> dict:
    c0 = np.asarray(caps, dtype=float)
    n = c0.size
    if c0.ndim != 1 or n < 2 or (c0 <= 0).any() or int(m) != m or n % int(m) != 0:
        raise ValueError("need positive capacities and a string length m that divides N")
    if not (0 < eol_frac < 1) or not (0 <= loss < 1) or fade_mean_per_year <= 0 or fade_cv < 0:
        raise ValueError("need 0 < eol_frac < 1, 0 <= loss < 1, fade_mean_per_year > 0, fade_cv >= 0")
    m = int(m)
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, horizon_years, steps)
    groups = np.argsort(-c0, kind="stable")
    s0 = c0.sum()
    if not (-1.0 <= weak_corr <= 1.0):
        raise ValueError("weak_corr must be in [-1, 1]")
    sd = c0.std()
    weak = (c0.mean() - c0) / sd if sd > 0 else np.zeros(n)   # >0 for cells weaker than average
    life = {k: [] for k in METHODS}
    energy = {k: [] for k in METHODS}
    for _ in range(trials):
        z = weak_corr * weak + np.sqrt(1.0 - weak_corr ** 2) * rng.standard_normal(n)
        f = np.maximum(fade_mean_per_year * (1.0 + fade_cv * z), 0.0)
        c = c0[None, :] * np.maximum(1.0 - t[:, None] * f[None, :], 0.0)
        u = _usable(c, groups, m)
        u = (u[0], u[1], u[2], u[3] * (1.0 - loss))
        for name, series in zip(METHODS, u):
            alive = series >= eol_frac * s0
            if not alive[0]:
                life[name].append(0.0)
                energy[name].append(0.0)
                continue
            idx = int(np.argmax(~alive)) if (~alive).any() else steps
            if idx == steps:  # never ended inside the horizon
                life[name].append(float(horizon_years))
                energy[name].append(_trap(series, t))
                continue
            # linear interpolation of the crossing between idx-1 and idx
            a, b = series[idx - 1], series[idx]
            thr = eol_frac * s0
            frac = (a - thr) / (a - b) if a != b else 0.0
            t_end = t[idx - 1] + frac * (t[idx] - t[idx - 1])
            life[name].append(float(t_end))
            energy[name].append(_trap(series[:idx], t[:idx]) + 0.5 * (a + thr) * (t_end - t[idx - 1]))
    out = {"years": {k: float(np.mean(v)) for k, v in life.items()}, "energy": {k: float(np.mean(v)) for k, v in energy.items()}}
    for k in ("single_string", "as_found", "sorted_once"):
        out[f"control_life_over_{k}"] = out["years"]["control"] / out["years"][k] - 1.0 if out["years"][k] > 0 else None
        out[f"control_energy_over_{k}"] = out["energy"]["control"] / out["energy"][k] - 1.0 if out["energy"][k] > 0 else None
    return out


def lifespan_loss(n_cells: int, fade_cv: float, retire_soh: float, *, init_cv: float = 0.0, trials: int = 400, seed: int = 0, steps: int = 800, horizon: float = 1.0) -> dict:
    """Weakest-cell effect on a series pack of n_cells new-ish cells, in the units of Zhou, Bian et al., Nature Energy 2026 (fleet telemetry, see docs/REON_DATA.md): the pack
    retires when its weakest cell reaches retire_soh (0.85 in that paper); the 'ideal' pack retires when the MEAN cell does. Linear fade c_i(t) = c_i0 (1 - f_i t), f_i ~ Normal(1, fade_cv)
    in units where the mean fade rate is 1 per unit time (only ratios matter; horizon must be long enough for the mean cell to reach retire_soh, i.e. >= 1 - retire_soh). Returns:
      lifespan_loss     = 1 - T_weakest / T_mean         (their 'effective pack lifespan reduction')
      energy_unused     = 1 - (energy delivered by the weakest-cell pack until it retires) / (energy an ideal pack delivers until the mean cell retires)
    Energy is the integral of usable capacity (n x weakest cell vs the sum of cells) over time."""
    if not (0 < retire_soh < 1) or fade_cv < 0 or n_cells < 2:
        raise ValueError("need 0 < retire_soh < 1, fade_cv >= 0, n_cells >= 2")
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, horizon, steps)
    loss, unused = [], []
    for _ in range(trials):
        c0 = np.maximum(1.0 + init_cv * rng.standard_normal(n_cells), 0.05)
        f = np.maximum(1.0 + fade_cv * rng.standard_normal(n_cells), 0.0)
        c = c0[None, :] * np.maximum(1.0 - t[:, None] * f[None, :], 0.0)
        soh_min = (c / c0[None, :]).min(axis=1)
        soh_mean = (c / c0[None, :]).mean(axis=1)
        i_w = int(np.argmax(soh_min <= retire_soh)) if (soh_min <= retire_soh).any() else steps - 1
        i_m = int(np.argmax(soh_mean <= retire_soh)) if (soh_mean <= retire_soh).any() else steps - 1
        loss.append(1.0 - t[i_w] / t[i_m] if t[i_m] > 0 else 0.0)
        e_w = _trap(n_cells * c.min(axis=1)[: i_w + 1], t[: i_w + 1])
        e_m = _trap(c.sum(axis=1)[: i_m + 1], t[: i_m + 1])
        unused.append(1.0 - e_w / e_m if e_m > 0 else 0.0)
    return {"lifespan_loss": float(np.mean(loss)), "energy_unused": float(np.mean(unused))}


def calibrate_fade_cv(n_cells: int, target_lifespan_loss: float, retire_soh: float, *, init_cv: float = 0.0, lo: float = 0.0, hi: float = 0.6, iters: int = 18) -> float:
    """Fade-rate CV that reproduces a measured lifespan loss (bisection; lifespan_loss rises with fade_cv)."""
    if lifespan_loss(n_cells, hi, retire_soh, init_cv=init_cv, trials=200)["lifespan_loss"] < target_lifespan_loss:
        raise ValueError("target lifespan loss not reachable below hi")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if lifespan_loss(n_cells, mid, retire_soh, init_cv=init_cv, trials=200)["lifespan_loss"] < target_lifespan_loss:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
