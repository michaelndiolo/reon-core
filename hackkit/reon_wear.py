"""reon_wear: ageing that DEPENDS ON HOW THE PACK IS RUN, and sourced knee-like fades, so a pack of well-matched cells can still gain from cell-level control.

reon_design ages every cell on its own fixed straight line, whatever the pack does. Real cells do not: the Iowa State / ILCC dataset (59 usable test groups, DOI 10.25380/iastate.22582234,
docs/REON_DATA.md) shows fade rate rising with depth of discharge, fade ~ DoD^g with g = 0.6 to 0.9 (examples/reon_wear_iowa_fit.py). In a plain series string every cell passes the same
Ah, so the WEAKEST cell has the deepest discharge, fades fastest, and the spread grows (the divergence the Nature Energy 2026 fleet paper reports). Cell-level bypass can share the duty out
in proportion to capacity: every cell then sees the same, smaller DoD. Same Ah moved, less wear on the weak cell.

Model (n cells, strings of m). Fixed duty: each cell-slot must pass q_d = duty x (mean weakest cell of the as-found day-1 strings) per cycle, the same for every design, so no design is
given an easier job. A cell fades  f_i x c0_i x (DoD_i / duty)^g  per year, f_i = the same random rate reon_design draws (so g = 0 and no knees reproduces reon_design: tested).
 plain / sort only : every cell in a string passes min(q_d, weakest)            -> DoD_i = that / c_i.
 late switches     : bypass only when the plain string cannot meet the duty (capability formula of reon_design.deliverable_late); below that the cells run as a plain string.
 level switches    : engaged whenever that lowers the DoD: the string's cells share the duty in proportion to capacity, DoD_i = m q_d / ((1 - loss) x sum of capacities); capability is the
                     'engage always' formula (loss charged on everything), so the energy lost in the switches is not hidden.
 selective global g: switches only on the g weakest cells of the whole pack (cost g/n of full). selective k: switches only on the k weakest cells of each string (from the noisy day-1 test); the string current stops when the weakest UNswitched cell is empty. Cost = k/m of full.
 balancer(r, eta)  : closes the share rho of the gap between the plain DoD and the equal-share DoD that its capability closes, rho = (cap_bal - cap_plain)/(cap_all - cap_plain). Approximation.
Knees: a share knee_share of cells change slope when their own capacity reaches an SOH drawn from knee_soh (Iowa: 0.82 to 0.90, median 0.855); after that they fade knee_kappa times faster
(Iowa median 2.4, quartiles 2.0 to 3.1). start_soh = the pack's SOH against NEW at day 1 (retired EV pack ~0.8): the knee SOH is against new, so a cell whose knee SOH is above start_soh is already past its knee. State-triggered, so no calendar failure rate has to be invented. Lab cells at 30 C: the SHAPE is sourced, the SHARE (Iowa 65%) is an upper bound for retired packs.
Money, retirement and costs are the reon_design definitions: present value per kWh nameplate vs the plain pack, retire when the design's own deliverable falls below eol_frac of day-1 nameplate."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from hackkit import reon_design as D


def _step(s, m, qd, kind, par, loss, closed_loss, eta, mask=None):
    """Capability per string (Ah-equivalent, the m x q convention) and the DoD of every cell, for one design at one time. s: (S, m) capacities."""
    cmin = s.min(axis=1)
    tot = s.sum(axis=1)
    cap_plain = m * cmin
    dod_plain = (np.minimum(qd, cmin)[:, None]) / np.maximum(s, 1e-12)
    if kind == "plain":
        return cap_plain, dod_plain
    share = np.minimum(m * qd / np.maximum(tot, 1e-12), 1.0)[:, None] * np.ones_like(s)
    if kind == "late":
        cap = cap_plain * (1.0 - closed_loss) + (1.0 - loss) * np.maximum(tot - cap_plain, 0.0)
        need = m * qd > cap_plain * (1.0 - closed_loss)            # the plain string cannot meet the duty: bypass the empty cells
        eng = np.minimum(m * qd / np.maximum(cap_plain + (1.0 - loss) * np.maximum(tot - cap_plain, 0.0), 1e-12), 1.0)[:, None] * np.ones_like(s)
        return cap, np.where(need[:, None], np.minimum(eng, share / max(1.0 - loss, 1e-9)), dod_plain)
    if kind == "level":
        eng_cap = (1.0 - loss) * tot
        cap = np.maximum(cap_plain * (1.0 - closed_loss), eng_cap)
        on = eng_cap > cap_plain * (1.0 - closed_loss)
        dod = np.minimum(m * qd / np.maximum(eng_cap, 1e-12), 1.0)[:, None] * np.ones_like(s)
        return cap, np.where(on[:, None], dod, dod_plain)
    if kind in ("select", "selectg"):
        # only the cells in `mask` carry a bypass switch. The string current stops when the weakest cell WITHOUT a bypass is empty; each cell then delivers min(its capacity, that limit).
        q_nb = np.where(mask, np.inf, s).min(axis=1)
        ideal = np.minimum(s, q_nb[:, None]).sum(axis=1)
        cl = closed_loss * mask.mean(axis=1)   # a series switch exists only on the switched cells, so the closed-path loss scales with their share
        cap = cap_plain * (1.0 - cl) + (1.0 - loss) * np.maximum(ideal - cap_plain, 0.0)
        return cap, dod_plain
    if kind == "hybsel":
        cl = closed_loss * mask.mean(axis=1)
        cap = hybrid_select_total(s, mask, loss, par[1], eta) * (1.0 - cl)
        return np.maximum(cap, cap_plain * (1.0 - cl)), dod_plain
    q = D.balancer_q(s, par, eta)
    cap_bal = m * q
    gap = tot - cap_plain
    rho = np.where(gap > 1e-12, np.clip((cap_bal - cap_plain) / np.maximum(gap, 1e-12), 0.0, 1.0), 0.0)
    return cap_bal, (1.0 - rho)[:, None] * dod_plain + rho[:, None] * share


def hybrid_select_total(s, mask, loss, r, eta, grid=12):
    """Selective bypass PLUS a balancer. s: (S, m) capacities, mask: (S, m) True where the cell has a bypass switch. Stage 1: the balancer (limit r, efficiency eta) lets every cell deliver q Ah
    (weak cells topped up by charge moved from strong ones, D = shortfalls / eta). Stage 2: bypass the empty cells and go on, which only works if every empty cell has a switch; the string then runs until the first
    unswitched cell is empty. Total = m q + (1 - loss) x max(sum_i min(c_i - q, x) - D, 0), x = the smallest remainder among unswitched cells (0 if one is empty). q is chosen on a grid from the weakest cell
    (pure selective bypass) to the balancer's limit (pure balancer plus tail), so the hybrid is never worse than either."""
    m = s.shape[1]
    qb = D.balancer_q(s, r, eta)
    lo = s.min(axis=1)
    best = None
    for j in range(grid + 1):
        q = (lo + (qb - lo) * (j / grid))[:, None]
        strong = np.maximum(s - q, 0.0)
        d = np.maximum(q - s, 0.0).sum(axis=1) / max(eta, 1e-9)
        empty = s <= q + 1e-9
        bad = (empty & ~mask).any(axis=1)
        x = np.where(mask | empty, np.inf, strong).min(axis=1)
        x = np.where(bad, 0.0, x)
        extra = np.minimum(strong, x[:, None]).sum(axis=1)
        tot = m * q[:, 0] + (1.0 - loss) * np.maximum(extra - d, 0.0)
        best = tot if best is None else np.maximum(best, tot)
    return best


def wear_scan(caps: Sequence[float], m: int, *, fade_mean: float, fade_cv: float, loss: float, electronics_per_kwh: float, balancer_per_kwh: float,
              sort_cost_per_kwh: float, value_per_kwh_year: float, rate: float, years: float, eol_frac: float, duty: float = 0.7, dod_exp: float = 0.0,
              knee_share: float = 0.0, knee_soh: Sequence[float] = (0.82, 0.90), knee_kappa: float = 2.4, start_soh: float = 1.0, balancer_rs: Sequence[float] = (0.1, 1e9),
              balancer_eta: float = 0.9, select_counts: Sequence[int] = (), global_counts: Sequence[int] = (), hybrid_counts: Sequence[int] = (), hybrid_per_kwh: float = None, closed_loss: float = 0.0, weak_corr: float = 0.0, test_sigma: float = 0.02, trials: int = 60, seed: int = 0,
              steps: int = 120) -> dict:
    """Net value per kWh nameplate vs the plain pack (mean, p10, p90, gross, cost, years in service) for: sort only, late switches, level switches (each as found and sorted),
    balancers at each transfer limit. Common random numbers across designs. dod_exp = 0 and knee_share = 0 reproduce reon_design."""
    c0 = np.asarray(caps, dtype=float)
    n = c0.size
    if n % m:
        raise ValueError("string length m must divide the number of cells")
    rng = np.random.default_rng(seed)
    rng_k = np.random.default_rng(seed + 1)   # knee draws on their own stream so that knee_share = 0 reproduces reon_design draw for draw
    t = np.linspace(0.0, years, steps)
    dt = np.diff(t)
    disc = np.exp(-rate * t)
    s0 = c0.sum()
    sd = c0.std()
    weak = (c0.mean() - c0) / sd if sd > 0 else np.zeros(n)
    asfound = np.arange(n)
    designs = [("plain", "plain", None, False, 0.0), ("sort only", "plain", None, True, sort_cost_per_kwh),
               ("late switches", "late", None, False, electronics_per_kwh), ("late switches, sorted", "late", None, True, electronics_per_kwh + sort_cost_per_kwh),
               ("level switches", "level", None, False, electronics_per_kwh), ("level switches, sorted", "level", None, True, electronics_per_kwh + sort_cost_per_kwh)]
    for r_ in balancer_rs:
        designs.append((f"balancer {('unlimited' if r_ > 1e6 else format(r_, '.0%'))}", "bal", r_, False, balancer_per_kwh))
    for k_ in select_counts:   # SELECTIVE bypass: switches only on the k_ weakest cells of each string (by the noisy day-1 test); cost scales with k_ / m
        designs.append((f"selective {k_}/{m} cells", "select", k_, False, electronics_per_kwh * k_ / m))
        designs.append((f"selective {k_}/{m} cells, sorted", "select", k_, True, electronics_per_kwh * k_ / m + sort_cost_per_kwh))
    for g_ in global_counts:   # switches on only the g_ weakest cells of the WHOLE pack (by the day-1 test), wherever they sit: hardware cost g_/n of a full set
        designs.append((f"selective: only the {g_} weakest cell{'s' if g_ > 1 else ''} of the pack", "selectg", g_, False, electronics_per_kwh * g_ / n))
    for k_ in hybrid_counts:   # selective bypass on the k_ weakest cells of each string PLUS a balancer at each transfer limit; hardware = switches k_/m + balancer unless shared (hybrid_per_kwh)
        for r_ in balancer_rs:
            designs.append((f"hybrid {k_}/{m} + balancer {('unlimited' if r_ > 1e6 else format(r_, '.0%'))}", "hybsel", (k_, r_), False,
                            hybrid_per_kwh if hybrid_per_kwh is not None else electronics_per_kwh * k_ / m + balancer_per_kwh))
    pv = {d[0]: np.zeros(trials) for d in designs}
    yrs = {d[0]: np.zeros(trials) for d in designs}
    qd = duty * float(np.mean(c0.reshape(-1, m).min(axis=1)))
    for i in range(trials):
        z = weak_corr * weak + np.sqrt(1.0 - weak_corr ** 2) * rng.standard_normal(n)
        f = np.maximum(fade_mean * (1.0 + fade_cv * z), 0.0)
        meas = c0 * (1.0 + test_sigma * rng.standard_normal(n))
        sorted_idx = np.argsort(-meas, kind="stable")
        is_knee = rng_k.random(n) < knee_share
        soh_k = rng_k.uniform(knee_soh[0], knee_soh[1], n)
        for nm, kind, par, srt, _ in designs:
            idx = sorted_idx if srt else asfound
            c = c0.copy()
            u = np.zeros(steps)
            mask = None
            if kind == "selectg":
                flat = np.zeros(n, dtype=bool)
                flat[np.argsort(meas[idx], kind="stable")[:par]] = True
                mask = flat.reshape(-1, m)
            if kind in ("select", "hybsel"):
                kk = par if kind == "select" else par[0]
                mask = np.zeros((n // m, m), dtype=bool)
                if kk > 0:
                    mask[np.arange(n // m)[:, None], np.argsort(meas[idx].reshape(-1, m), axis=1)[:, :kk]] = True
            for j in range(steps):
                cap, dod = _step(c[idx].reshape(-1, m), m, qd, kind, par, loss, closed_loss, balancer_eta, mask)
                u[j] = cap.sum()
                if j == steps - 1:
                    break
                rate_i = f.copy()
                if dod_exp != 0.0:
                    w = np.empty(n)
                    w[idx] = (np.maximum(dod, 1e-9) / duty).reshape(-1) ** dod_exp
                    rate_i = rate_i * w
                if knee_share > 0:
                    rate_i = np.where(is_knee & (c * start_soh <= soh_k * c0), rate_i * knee_kappa, rate_i)
                c = np.maximum(c - dt[j] * rate_i * c0, 0.0)
            alive = np.cumprod(u / s0 >= eol_frac)
            y = (u / s0) * alive * disc
            pv[nm][i] = float(((y[1:] + y[:-1]) * 0.5 * dt).sum())
            yrs[nm][i] = float(alive.mean() * years)
    out = {}
    base = pv["plain"]
    for nm, _k, _p, _s, cst in designs:
        gross = value_per_kwh_year * (pv[nm] - base)
        net = gross - cst
        out[nm] = {"mean": float(net.mean()), "p10": float(np.percentile(net, 10)), "p90": float(np.percentile(net, 90)), "years": float(yrs[nm].mean()),
                   "gross": float(gross.mean()), "cost": float(cst)}
    return out


def recommend_build(caps: Sequence[float], m: int, *, balancer_r: float, balancer_per_kwh: float, ks: Sequence[int] = None, global_ks: Sequence[int] = (1, 2, 3, 4), hybrid: bool = True, hybrid_per_kwh: float = None, **kw) -> dict:
    """ONE conditional policy instead of separate fixes. Evaluates, on the pack's own day-1 capacities, every build we have (plain, sort only, selective bypass on the k weakest cells of each string
    for k in ks (default 1..m-1), switches on every cell, selective bypass plus the balancer (hybrid, if hybrid), and the active balancer alone with transfer limit balancer_r and cost balancer_per_kwh)
    and returns the best by net value per kWh nameplate, its margin over the best rival that is not ours, and the full table. kw are wear_scan arguments (fade, loss, electronics, value, years, eol...).
    Nothing here is a default: every cost and limit is passed in. The hybrid counts as ours (it is our hardware plus a balancer)."""
    ks = tuple(k for k in (ks if ks is not None else range(1, m)) if 0 < k < m)
    res = wear_scan(caps, m, balancer_rs=(balancer_r,), balancer_per_kwh=balancer_per_kwh, select_counts=ks, global_counts=tuple(g for g in global_ks if g < len(caps)), hybrid_counts=ks if hybrid else (), hybrid_per_kwh=hybrid_per_kwh, **kw)
    ours = {k: v for k, v in res.items() if k.startswith(("selective", "late", "level", "hybrid"))}
    rivals = {k: v for k, v in res.items() if k in ("plain", "sort only") or k.startswith("balancer")}
    best_o = max(ours, key=lambda k: ours[k]["mean"])
    best_r = max(rivals, key=lambda k: rivals[k]["mean"])
    win = ours[best_o]["mean"] > rivals[best_r]["mean"]
    return {"build": best_o if win else best_r, "ours_best": best_o, "rival_best": best_r, "margin": ours[best_o]["mean"] - rivals[best_r]["mean"], "table": res}
