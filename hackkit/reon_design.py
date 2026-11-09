"""reon_design: ONE model, every way of building the pack, scored on money over the pack's life, with the winning rule chosen by the code.

Replaces the two separate fixes (switch spacing, drift) with a single design search. A pack is N cells arranged as N/m parallel strings of m cells in series
(m is fixed by the application's voltage). The designs differ in two choices:
  order : "as_found" (cells stay where they came) or "sorted" (cells ranked by a day-1 test and regrouped, test error test_sigma)
  k     : cells per switch group inside a string. k = m means no switches. k = 1 is a switch on every cell.
A string with switches is ADAPTIVE: it leaves its switches closed (plain weakest-cell string, no switching loss) and engages the bypass only while the bypassed
deliverable is higher, so a switch can never make a string worse than the same string without it, apart from its electronics cost. (closed_loss is the loss of a closed switch path, 0 by default = a closed switch costs
nothing beyond a plain string; ask REON, and see the stress test in examples/reon_design_stress.py.) Engaged, a string delivers  sum over groups of k x weakest-in-group, times (1 - loss_cell / k^p).
Cells age forward (linear fade, random rates), the pack retires when its deliverable falls below eol_frac of day-1 nameplate or after `years`, and the money is the
discounted value of the usable energy over that life minus the electronics (e / k^q per kWh nameplate) and the sorting/repacking cost, all per kWh of nameplate and
measured against the plain pack of the same m with no switches and no sorting. The net value is a PRESENT VALUE over the service period per kWh of nameplate (not per year).
Assumptions to be confirmed by REON are exposed as scenario axes: fade-rate spread (fade_cvs), loss exponent p (loss_exps), cost exponent q (cost_exps).
`recommend` returns the best design in each scenario, the design with the smallest worst-case regret across all scenarios (the robust pick), and plain conditions.
No default numbers: every cost, loss, value and rate is an argument that must be sourced or flagged ASSUMED.
"""
from __future__ import annotations

from itertools import product
from typing import Optional, Sequence

import numpy as np


def deliverable(c: np.ndarray, m: int, k: int, loss_k: float, closed_loss: float = 0.0) -> np.ndarray:
    """c: (T, N) capacities already arranged in string order. Usable Ah at each time step for a design with group size k (k == m: no switches)."""
    t, n = c.shape
    s = c.reshape(t, n // m, m)
    conv = m * s.min(axis=2)
    if k == m:
        return conv.sum(axis=1)
    g = s.reshape(t, n // m, m // k, k)
    ctrl = (k * g.min(axis=3)).sum(axis=2) * (1.0 - loss_k)
    return np.maximum(conv * (1.0 - closed_loss), ctrl).sum(axis=1)


def design_list(n: int, m: int) -> list:
    if m < 1 or n % m != 0:
        raise ValueError("string length m must divide the number of cells")
    ks = [k for k in range(1, m + 1) if m % k == 0]
    out = []
    for order in ("as_found", "sorted"):
        for k in ks:
            if order == "as_found" and k == m:
                continue  # the reference pack
            if order == "sorted" and k == m and m == n:
                continue  # sorting inside a single string changes nothing
            out.append((order, k))
    return out


def label(order: str, k: int, m: int) -> str:
    if k == m:
        return "sort only (no switches)"
    where = "a switch on every cell" if k == 1 else f"a switch every {k} cells"
    return where + (", cells sorted first" if order == "sorted" else ", cells as found")


def balancer_q(c: np.ndarray, r: float, eta: float, iters: int = 40) -> np.ndarray:
    """Active balancer. c: (..., m) capacities of the cells of a string. Returns q, the Ah every cell passes at the terminal before the string is empty
    (the string delivers m x q, the same units as the weakest-cell pack's m x min). Charge is moved from cells with spare capacity to cells that would run out
    first, at transfer efficiency eta, and no cell may exchange more than beta = r x (mean capacity) in total. Largest q such that
       every weak cell's shortfall (q - c_i)+ <= beta   and   sum of shortfalls <= eta x sum over strong cells of min(beta, c_i - q)+.
    r = infinity, eta = 1 gives q = mean (the ideal sum); r = 0 gives the weakest cell. Feasibility is monotone in q, so bisection finds it."""
    c = np.asarray(c, dtype=float)
    beta = r * c.mean(axis=-1, keepdims=True)
    lo = c.min(axis=-1, keepdims=True)
    hi = c.mean(axis=-1, keepdims=True)
    dead = c.min(axis=-1) <= 0.0   # an open-circuit cell breaks the string: only a bypass can save it, a balancer cannot move charge through it
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        short = np.maximum(mid - c, 0.0)
        spare = np.minimum(beta, np.maximum(c - mid, 0.0))
        ok = (short.max(axis=-1, keepdims=True) <= beta + 1e-12) & (short.sum(axis=-1, keepdims=True) <= eta * spare.sum(axis=-1, keepdims=True) + 1e-12)
        lo = np.where(ok, mid, lo)
        hi = np.where(ok, hi, mid)
    return np.where(dead, 0.0, lo[..., 0])


def deliverable_balancer(c: np.ndarray, m: int, r: float, eta: float) -> np.ndarray:
    t, n = c.shape
    return m * balancer_q(c.reshape(t, n // m, m), r, eta).sum(axis=1)


def deliverable_converter(c: np.ndarray, m: int, k: int, loss: float) -> np.ndarray:
    """A DC-DC converter per group of k cells: every group delivers k x its weakest member, always through a lossy converter (it cannot be left 'closed')."""
    t, n = c.shape
    g = c.reshape(t, n // m, m // k, k)
    return (k * g.min(axis=3)).sum(axis=(2,)).sum(axis=1) * (1.0 - loss)


def deliverable_late(c: np.ndarray, m: int, k: int, loss_k: float, closed_loss: float = 0.0) -> np.ndarray:
    """Switches that engage LATE. Run the plain string (switches closed, no loss) until the weakest cell is empty, then bypass and keep going. Only the extra energy beyond
    the plain string passes through engaged bypasses, so only that pays the loss:  m x min + (1 - loss) x (sum over groups of k x weakest - m x min).  Never below the
    plain string, and never below 'engage always' (which pays the loss on everything). Same closed-switch-is-lossless assumption as the adaptive design."""
    t, n = c.shape
    s = c.reshape(t, n // m, m)
    conv = m * s.min(axis=2)
    if k == m:
        return conv.sum(axis=1)
    g = s.reshape(t, n // m, m // k, k)
    ctrl = (k * g.min(axis=3)).sum(axis=2)
    return (conv * (1.0 - closed_loss) + (1.0 - loss_k) * np.maximum(ctrl - conv, 0.0)).sum(axis=1)


def hybrid_total(c: np.ndarray, loss: float, r: float, eta: float, grid: int = 16) -> np.ndarray:
    """HYBRID: balancer first, switches for what the balancer cannot reach. c: (..., m) cells of one string. Stage 1: the active balancer holds the string together while every
    cell delivers q Ah (weak cells topped up by charge moved from strong cells at efficiency eta, limit r x mean capacity per cell). Stage 2: cells that are empty are
    bypassed and the rest deliver what is left, through engaged switches that pay `loss`. Total  = m q + (1 - loss) (sum over strong cells of (c_i - q) - D(q)),  D(q) = sum of
    shortfalls / eta = the charge moved out of donors. q is chosen on a grid between the weakest cell (pure late switches) and the balancer's limit q_B (pure balancer, plus
    the switch tail), so the hybrid is never worse than either one. Conditions are the choice of q and the max over modes in the caller."""
    c = np.asarray(c, dtype=float)
    qb = balancer_q(c, r, eta)
    lo = c.min(axis=-1)
    best = None
    for j in range(grid + 1):
        q = (lo + (qb - lo) * (j / grid))[..., None]
        short = np.maximum(q - c, 0.0)
        strong = np.maximum(c - q, 0.0)
        d = short.sum(axis=-1) / max(eta, 1e-9)
        tot = c.shape[-1] * q[..., 0] + (1.0 - loss) * np.maximum(strong.sum(axis=-1) - d, 0.0)
        best = tot if best is None else np.maximum(best, tot)
    return best


def deliverable_hybrid(c: np.ndarray, m: int, loss: float, r: float, eta: float) -> np.ndarray:
    t, n = c.shape
    return hybrid_total(c.reshape(t, n // m, m), loss, r, eta).sum(axis=1)


def _designs(n, m, balancer_rs, converter_loss):
    d = [(o, k, "switch", None) for o, k in design_list(n, m)]
    ks = [k for k in range(1, m + 1) if m % k == 0 and k < m]
    d += [(o, k, "late", None) for o, k in design_list(n, m) if k < m]
    for o in ("as_found", "sorted"):
        if o == "sorted" and m == n:
            continue
        d += [(o, 0, "balancer", float(r)) for r in balancer_rs]
        d += [(o, 1, "hybrid", float(r)) for r in balancer_rs]
        if converter_loss is not None:
            d += [(o, k, "converter", None) for k in ks]
    return d


def design_label(d, m) -> str:
    order, k, kind, par = d
    suffix = ", cells sorted first" if order == "sorted" else ", cells as found"
    if kind == "balancer":
        return f"active balancer (moves up to {par:.0%} of a cell's capacity)" + suffix
    if kind == "hybrid":
        return f"hybrid: balancer (limit {par:.0%}) first, switches for the rest" + suffix
    if kind == "late":
        return ("late-engaging switch on every cell" if k == 1 else f"late-engaging switch every {k} cells") + suffix
    if kind == "converter":
        return ("a DC-DC converter on every cell" if k == 1 else f"a DC-DC converter every {k} cells") + " (always lossy)" + suffix
    return label(order, k, m)


def _simulate(caps, m, *, fade_mean, fade_cv, weak_corr, eol_frac, loss_cell, loss_exp, rate, years, test_sigma, trials, seed, steps, closed_loss=0.0,
              balancer_rs=(), balancer_eta=0.9, converter_loss=None, fail_rate=0.0, repair_years=None):
    c0 = np.asarray(caps, dtype=float)
    n = c0.size
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, years, steps)
    disc = np.exp(-rate * t)
    s0 = c0.sum()
    sd = c0.std()
    weak = (c0.mean() - c0) / sd if sd > 0 else np.zeros(n)
    designs = _designs(n, m, balancer_rs, converter_loss)
    pv = {d: np.zeros(trials) for d in designs}
    pv_base = np.zeros(trials)
    base_y = np.zeros(trials)
    alive_y = {d: np.zeros(trials) for d in designs}

    def pv_of(u, u_age):
        """Value of the usable energy u over the service period. Retirement is set by AGEING only (u_age = the same design with no failures): an outage from a dead cell
        costs the energy lost while it lasts, it does not retire the pack."""
        alive = np.cumprod(u_age / s0 >= eol_frac)
        y = (u / s0) * alive * disc
        return float(((y[1:] + y[:-1]) * 0.5 * np.diff(t)).sum()), float(alive.mean() * years)

    def run(d, c_, cs_):
        order, k, kind, par = d
        cc = c_ if order == "as_found" else cs_
        if kind == "switch":
            return deliverable(cc, m, k, loss_cell / (k ** loss_exp), closed_loss)
        if kind == "late":
            return deliverable_late(cc, m, k, loss_cell / (k ** loss_exp), closed_loss)
        if kind == "hybrid":
            return deliverable_hybrid(cc, m, loss_cell, par, balancer_eta) * (1.0 - closed_loss)
        if kind == "balancer":
            return deliverable_balancer(cc, m, par, balancer_eta)
        return deliverable_converter(cc, m, k, converter_loss)

    for i in range(trials):
        z = weak_corr * weak + np.sqrt(1.0 - weak_corr ** 2) * rng.standard_normal(n)
        f = np.maximum(fade_mean * (1.0 + fade_cv * z), 0.0)
        c_age = c0[None, :] * np.maximum(1.0 - t[:, None] * f[None, :], 0.0)
        c = c_age
        if fail_rate > 0:   # open-circuit failures: a failed cell delivers nothing and breaks its string unless bypassed
            tf = rng.exponential(1.0 / fail_rate, n)
            back = tf + (rng.exponential(repair_years, n) if repair_years else np.inf)   # a repaired cell is replaced by one that follows the same ageing
            c = c_age * ~((t[:, None] >= tf[None, :]) & (t[:, None] < back[None, :]))
        meas = c0 * (1.0 + test_sigma * rng.standard_normal(n))
        order_idx = np.argsort(-meas, kind="stable")
        cs, cs_age = c[:, order_idx], c_age[:, order_idx]
        u_base = deliverable(c, m, m, 0.0)
        pv_base[i], base_y[i] = pv_of(u_base, deliverable(c_age, m, m, 0.0) if fail_rate > 0 else u_base)
        for d in designs:
            u = run(d, c, cs)
            pv[d][i], alive_y[d][i] = pv_of(u, run(d, c_age, cs_age) if fail_rate > 0 else u)
    return designs, pv, pv_base, alive_y, base_y


def design_scan(caps: Sequence[float], m: int, *, fade_mean: float, fade_cvs: Sequence[float], loss_cell: float, loss_exps: Sequence[float],
                cost_exps: Sequence[float], electronics_per_kwh_cell: float, sort_cost_per_kwh: float, value_per_kwh_year: float, rate: float,
                years: float, eol_frac: float, test_sigma: float = 0.0, weak_corr: float = 0.0, trials: int = 80, seed: int = 0, steps: int = 240,
                closed_loss: float = 0.0, balancer_rs: Sequence[float] = (), balancer_eta: float = 0.9, balancer_per_kwh: float = 0.0,
                converter_loss: Optional[float] = None, converter_per_kwh_cell: float = 0.0, hybrid_per_kwh: Optional[float] = None,
                fail_rate_per_cell_year: float = 0.0, repair_years: Optional[float] = None) -> list:
    """One record per (scenario, design): mean/p10/p90 of the net value per kWh nameplate vs the plain pack, probability it is positive, years in service, and
    the pieces (gross = value of the extra usable energy, cost, value of the plain pack's own energy) used for the add-capacity break-even.
    Competitors beyond switches: balancer_rs = transfer limits (share of a cell's capacity) of an active balancer with efficiency balancer_eta and cost
    balancer_per_kwh; converter_loss and converter_per_kwh_cell = an always-lossy DC-DC converter per group of k cells (cost scales as 1/k^q like switches).
    Passive balancing equals the plain pack (it only equalises state of charge) and has no row.
    fail_rate_per_cell_year > 0 adds open-circuit cell failures (exponential times, no repair unless repair_years is given: a failed cell is replaced after an exponential time with that mean): a failed cell kills its string for plain, sorted, balancer and group-switch designs
    that cannot bypass it, while a switch on every cell loses only that cell. The rate is ASSUMED: nothing public gives it for retired cells (see docs/SOURCES.md).
    Late-engaging switches ('late') and the hybrid (balancer first, switches for the rest) are the improved designs; the hybrid costs hybrid_per_kwh, by default the
    switch electronics plus the balancer (separate hardware); pass a smaller number if one set of hardware does both."""
    n = len(caps)
    if not (0 < eol_frac < 1) or years <= 0 or value_per_kwh_year < 0 or not (-1 <= weak_corr <= 1):
        raise ValueError("bad scan inputs")
    recs = []
    for fcv, p in product(fade_cvs, loss_exps):
        designs, pv, base, alive, base_years = _simulate(caps, m, fade_mean=fade_mean, fade_cv=fcv, weak_corr=weak_corr, eol_frac=eol_frac, loss_cell=loss_cell,
                                                         loss_exp=p, rate=rate, years=years, test_sigma=test_sigma, trials=trials, seed=seed, steps=steps,
                                                         closed_loss=closed_loss, balancer_rs=balancer_rs, balancer_eta=balancer_eta, converter_loss=converter_loss,
                                                         fail_rate=fail_rate_per_cell_year, repair_years=repair_years)
        for q in cost_exps:
            recs.append({"fade_cv": fcv, "loss_exp": p, "cost_exp": q, "order": "as_found", "k": m, "kind": "reference", "design": "no switches, no sorting (reference)",
                         "mean": 0.0, "p10": 0.0, "p90": 0.0, "prob_positive": 0.0, "years": float(base_years.mean()), "gross": 0.0, "cost": 0.0,
                         "base_value": float(value_per_kwh_year * base.mean())})
            for d in designs:
                order, k, kind, par = d
                if kind in ("switch", "late"):
                    elec = electronics_per_kwh_cell / (k ** q) if k < m else 0.0
                elif kind == "hybrid":
                    elec = hybrid_per_kwh if hybrid_per_kwh is not None else electronics_per_kwh_cell + balancer_per_kwh
                elif kind == "balancer":
                    elec = balancer_per_kwh
                else:
                    elec = converter_per_kwh_cell / (k ** q)
                cost = elec + (sort_cost_per_kwh if order == "sorted" else 0.0)
                gross = value_per_kwh_year * (pv[d] - base)
                net = gross - cost
                recs.append({"fade_cv": fcv, "loss_exp": p, "cost_exp": q, "order": order, "k": k, "kind": kind, "design": design_label(d, m),
                             "mean": float(net.mean()), "p10": float(np.percentile(net, 10)), "p90": float(np.percentile(net, 90)),
                             "prob_positive": float((net > 0).mean()), "years": float(alive[d].mean()), "gross": float(gross.mean()), "cost": float(cost),
                             "base_value": float(value_per_kwh_year * base.mean())})
    return recs


def add_capacity_breakeven(recs: list, design: str) -> dict:
    """Buying extra cells instead of `design`: adding a share x of capacity at c per kWh yields x times the plain pack's value. To match the design's gross gain it
    must spend c x gross / base_value. So the design is cheaper than extra capacity whenever extra capacity costs more than  c* = cost x base_value / gross
    (per kWh of nameplate; compare with 20 to 98 per kWh). Returns per-scenario c* and min / median / max (None where gross <= 0)."""
    out = {}
    for r in recs:
        if r["design"] == design:
            out[(r["fade_cv"], r["loss_exp"], r["cost_exp"])] = (r["cost"] * r["base_value"] / r["gross"]) if r["gross"] > 0 else None
    vals = sorted(v for v in out.values() if v is not None)
    return {"per_scenario": out, "min": vals[0] if vals else None, "median": vals[len(vals) // 2] if vals else None, "max": vals[-1] if vals else None}


def _top(names, table, s):
    """Best design in scenario s; ties (to 1e-9) go to the one that does not need sorting."""
    return max(names, key=lambda nm: (round(table[(nm, s)], 9), "sorted" not in nm, nm))


def recommend(recs: list) -> dict:
    """Best design in each scenario, the robust (smallest worst-case regret) design, and the designs that never lose money in any scenario."""
    scen = sorted({(r["fade_cv"], r["loss_exp"], r["cost_exp"]) for r in recs})
    names = sorted({r["design"] for r in recs})
    table = {(r["design"], (r["fade_cv"], r["loss_exp"], r["cost_exp"])): r["mean"] for r in recs}
    best = {}
    regret = {nm: 0.0 for nm in names}
    for s in scen:
        top = _top(names, table, s)
        best[s] = (top, table[(top, s)])
        for nm in names:
            regret[nm] = max(regret[nm], table[(top, s)] - table[(nm, s)])
    robust = min(names, key=lambda nm: (regret[nm], nm))
    never_lose = [nm for nm in names if all(table[(nm, s)] >= -1e-9 for s in scen) and nm != "no switches, no sorting (reference)"]
    wins = {nm: sum(1 for s in scen if best[s][0] == nm) for nm in names}
    return {"scenarios": scen, "best": best, "robust": robust, "max_regret": regret, "never_lose": never_lose, "win_counts": wins,
            "robust_mean_by_scenario": {s: table[(robust, s)] for s in scen}}


def sort_cost_breakeven(recs_at_zero_sort_cost: list) -> dict:
    """Run design_scan with sort_cost_per_kwh = 0 and pass the records here. For each scenario: the sorting/repacking cost per kWh nameplate above which
    'sort only' stops beating the best design that does not sort (switches without sorting, or the plain pack). Positive = sorting is worth that much.
    Returns the per-scenario values and their min / median / max."""
    by = {}
    for r in recs_at_zero_sort_cost:
        by.setdefault((r["fade_cv"], r["loss_exp"], r["cost_exp"]), []).append(r)
    out = {}
    for s, rows in by.items():
        sort_only = [r["mean"] for r in rows if r["design"] == "sort only (no switches)"]
        rest = [r["mean"] for r in rows if r["order"] == "as_found"] + [0.0]
        if sort_only:
            out[s] = max(sort_only) - max(rest)
    vals = sorted(out.values())
    if not vals:
        return {"per_scenario": {}, "min": None, "median": None, "max": None}
    return {"per_scenario": out, "min": vals[0], "median": vals[len(vals) // 2], "max": vals[-1]}


def conditions(recs: list) -> dict:
    """For every design that is best somewhere: the values of each scenario axis where it is best (the 'put conditions on it' table)."""
    scen = sorted({(r["fade_cv"], r["loss_exp"], r["cost_exp"]) for r in recs})
    table = {(r["design"], (r["fade_cv"], r["loss_exp"], r["cost_exp"])): r["mean"] for r in recs}
    names = sorted({r["design"] for r in recs})
    out = {}
    for s in scen:
        top = _top(names, table, s)
        d = out.setdefault(top, {"fade_cv": set(), "loss_exp": set(), "cost_exp": set(), "n": 0})
        d["fade_cv"].add(s[0]); d["loss_exp"].add(s[1]); d["cost_exp"].add(s[2]); d["n"] += 1
    return {k: {a: (sorted(v) if isinstance(v, set) else v) for a, v in d.items()} for k, d in out.items()}


def policy(c_string: Sequence[float], *, loss: float, closed_loss: float, balancer_r: float, balancer_eta: float) -> dict:
    """The controller's condition, for ONE string right now: usable Ah in each mode and the mode it would run. Modes: plain (switches closed), balancer only,
    late-engaging switches, hybrid (balancer first, switches for the rest). The hybrid and the late switches include the closed-path loss; the balancer has none
    on the plain path. This is the 'if ... then ...' the code runs at every time step inside the simulation (as a max over modes)."""
    c = np.asarray(c_string, dtype=float)
    m = c.size
    plain = float(m * c.min())
    late = float(plain * (1.0 - closed_loss) + (1.0 - loss) * max(c.sum() - plain, 0.0))
    bal = float(m * balancer_q(c, balancer_r, balancer_eta))
    hyb = float(hybrid_total(c, loss, balancer_r, balancer_eta))
    hyb = hyb * (1.0 - closed_loss) if closed_loss else hyb
    modes = {"plain string": plain, "balancer only": bal, "late-engaging switches": late, "hybrid": hyb}
    best = max(modes, key=lambda k_: modes[k_])
    return {"modes": modes, "best": best, "gain_over_plain": modes[best] / plain - 1.0}
