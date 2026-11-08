"""reon_policy_stress: stress test of control POLICIES on the same paired random draws, against the five baselines (plain, 2.5% balancer, 5% balancer, switches alone, hybrid).

Physics is reon_wear's: every step calls reon_wear._step (capability + depth of discharge), and the fade update is the same line as reon_wear.wear_scan. A draw is one wear_scan trial: the
draw with seed s reproduces wear_scan(..., trials=1, seed=s) exactly for the baselines (tested). Every policy in a draw sees the same fade rates, the same day-1 test noise, the same knees
and the same later measurement noise (paired draws, common random numbers).

Policies only use information observable at decision time: the day-1 noisy test (meas), later noisy capacity readings (obs, one per time step), and the scenario's prior (fade mean / spread,
costs). Never the draw's fade rates or true capacities.

The voltage floor is a pluggable function floor_fn(s, m) -> how many cells of each string may be bypassed at once (array per string). Default: the reon_wear cell-count window
(floor(m x (1 - window))). If hackkit/reon_sag.py exists, sag_floor_fn builds one from its max-bypassable helper.

Assumptions not in the repo are tagged in docs/stress/policy_assumptions.md."""
from __future__ import annotations

import numpy as np

from hackkit import reon_wear as W

# ---------------------------------------------------------------- scenario
HEADLINE = dict(value=40.0, elec=15.5, bal_cost=4.0, bal_eta=0.9, loss=0.04, closed_loss=0.02, years=12.0, steps=60, eol=0.7, rate=0.07, duty=0.7, dod_exp=0.87,
                knee_share=0.65, knee_soh=(0.82, 0.90), knee_kappa=2.4, start_soh=1.0, test_sigma=0.02, window=0.9, n=250, m=250)
KS = (1, 2, 4, 8, 16, 25)          # reon_storefront.KS
OBS_SIGMA = 0.01                    # ASSUMED: noise of the in-service capacity estimate per reading (one reading per time step)
CYCLES_PER_YEAR = 365.0             # ASSUMED: for the energy cost of bypass loss during rest hours
ENERGY_PRICE = 0.15                 # ASSUMED: $ per kWh lost in the bypass during rest hours


def scenario(p=1, fade=0.008, **over):
    sc = dict(HEADLINE, fade_mean=float(fade), fade_cv=0.45 / np.sqrt(p), p=int(p), start_sd=0.02 / np.sqrt(p))
    sc.update(over)
    return sc


def window_floor_fn(window):
    def fn(s, m):
        return np.full(s.shape[0], int(np.floor(m * (1.0 - window) + 1e-9)))
    return fn


def sag_floor_fn(v_floor_frac=0.9, current_a=None, r_cell_ohm=None):
    """Floor rule from hackkit/reon_sag.max_bypass: cells that can be bypassed at the moment the weakest cell is empty (never below 0). None if reon_sag is missing."""
    try:
        from hackkit import reon_sag as SG
    except ImportError:
        return None
    kw = dict(v_floor_frac=v_floor_frac)
    if current_a is not None:
        kw["current_a"] = current_a
    if r_cell_ohm is not None:
        kw["r_cell_ohm"] = r_cell_ohm

    def fn(s, m):
        rel = s / 100.0
        return np.array([max(int(SG.max_bypass(row, SG.soc_after(row, row.min()), **kw)), 0) for row in rel])
    return fn


def sag_energy_fn(v_floor_frac=0.9, current_a=None, r_cell_ohm=None, closed_loss=0.02):
    """Per-discharge usable ENERGY from hackkit/reon_sag.usable_fraction instead of reon_wear's Ah capability. For each build the Ah model's share of the plain-to-ideal gap it closes
    (rho, closed-path loss removed) is applied to the sag model's gap between plain and its ceiling (the better of a perfectly balanced string and every cell bypassable, both under the
    voltage floor), then the closed-path loss is charged. Scaled by a perfectly balanced fresh pack's usable energy so day 1 is about 1 x nameplate (ASSUMED mapping, see
    docs/stress/policy_assumptions.md). None if reon_sag is missing."""
    try:
        from hackkit import reon_sag as SG
    except ImportError:
        return None
    kw = dict(v_floor_frac=v_floor_frac, iters=30)
    if current_a is not None:
        kw["current_a"] = current_a
    if r_cell_ohm is not None:
        kw["r_cell_ohm"] = r_cell_ohm
    ref = {}

    def fn(s, cap, cl_share, s_day1):
        m = s.shape[1]
        key = float(s_day1.sum())
        if key not in ref:
            ref[key] = SG.usable_fraction(np.repeat(s_day1.mean(axis=1, keepdims=True), m, axis=1) / 100.0, 0, **kw)
        rel = np.maximum(s, 1e-9) / 100.0
        e_plain = SG.usable_fraction(rel, 0, **kw)
        ceil = np.maximum(SG.usable_fraction(np.repeat(rel.mean(axis=1, keepdims=True), m, axis=1), 0, **kw), SG.usable_fraction(rel, None, **kw))
        tot = s.sum(axis=1)
        cplain = m * s.min(axis=1)
        cl = closed_loss * cl_share
        rho = np.clip((cap / (1.0 - cl) - cplain) / np.maximum(tot - cplain, 1e-12), 0.0, 1.0)
        e = (e_plain + rho * np.maximum(ceil - e_plain, 0.0)) * (1.0 - cl)
        return float((e / ref[key] * tot).sum())
    return fn


# ---------------------------------------------------------------- draws
def start_caps(seed, sc):
    """Day-1 true capacities of a fresh pack (same shape as reon_storefront._start, own seed)."""
    return 100.0 * (1.0 + sc["start_sd"] * np.random.default_rng(seed + 7_000_000).standard_normal(sc["n"]))


def draw(seed, sc, c0=None):
    """One paired draw: exactly the random numbers wear_scan(trials=1, seed=seed) uses (weak_corr = 0), plus a separate stream of in-service readings."""
    c0 = start_caps(seed, sc) if c0 is None else np.asarray(c0, float)
    n = c0.size
    rng = np.random.default_rng(seed)
    rng_k = np.random.default_rng(seed + 1)
    z = rng.standard_normal(n)
    f = np.maximum(sc["fade_mean"] * (1.0 + sc["fade_cv"] * z), 0.0)
    meas = c0 * (1.0 + sc["test_sigma"] * rng.standard_normal(n))
    is_knee = rng_k.random(n) < sc["knee_share"]
    soh_k = rng_k.uniform(sc["knee_soh"][0], sc["knee_soh"][1], n)
    obs_noise = np.random.default_rng(seed + 3_000_000).standard_normal((sc["steps"], n))
    return dict(c0=c0, f=f, meas=meas, is_knee=is_knee, soh_k=soh_k, obs_noise=obs_noise, seed=seed)


# ---------------------------------------------------------------- policies
def P(name, kind, cost, par=None, k=0, mask="day1", rest=None, defer=None, share_wear=True, group=None):
    """Policy spec. kind/par: the reon_wear._step build. k: switched cells per string (mask 'day1' = k weakest by the day-1 test, 'all' = every cell).
    rest = (selector, frac, count): rotating rest of high-wear switched cells. defer = (years, k, selector): k switches installed at the first year (balancer only until then) and MOVED at each later year to the k cells picked by selector
    ('reading' = lowest reading now, 'projected' = lowest fitted-line projection at the horizon)."""
    return dict(name=name, kind=kind, cost=float(cost), par=par, k=int(k), mask=mask, rest=rest, defer=defer, share_wear=share_wear, group=group or name)


def baselines(sc, ks=KS):
    e, b, m = sc["elec"], sc["bal_cost"], sc["m"]
    out = [P("plain", "plain", 0.0, group="plain"), P("balancer 2.5%", "bal", b, 0.025, group="balancer 2.5%"), P("balancer 5%", "bal", b, 0.05, group="balancer 5%"),
           P("late switches", "late", e, mask="all", group="switches alone"), P("level switches", "level", e, mask="all", group="switches alone")]
    out += [P(f"selective {k}/{m} cells", "select", e * k / m, k, k=k, group="switches alone") for k in ks]
    out += [P(f"hybrid {k}/{m} + balancer 5%", "hybsel", e * k / m + b, (k, 0.05), k=k, group="hybrid") for k in ks]
    return out


def candidates(sc, bal_cost_scaled=False):
    e, b, m = sc["elec"], sc["bal_cost"], sc["m"]
    out = []
    # a. wear-aware switching: switches on every cell; rest (partially bypass) the cells whose fitted fade slope projects them to be the limiter at the horizon
    for frac in (0.5, 0.8):
        out.append(P(f"a. wear-aware full switches, rest x{frac}", "late", e, mask="all", rest=("projected", frac, None), group="a"))
        out.append(P(f"a. wear-aware full switches + bal 5%, rest x{frac}", "hybsel", e + b, (m - 1, 0.05), k=m - 1, mask="all", rest=("projected", frac, None), group="a"))
    # c. rotating rest: hybrid k + 5% balancer; in rest hours bypass the switched cells with the most observed wear
    for k in (8, 25):
        for frac in (0.5, 0.8):
            out.append(P(f"c. rotating rest, hybrid {k} + bal 5%, x{frac}", "hybsel", e * k / m + b, (k, 0.05), k=k, rest=("observed", frac, k), group="c"))
    # d. hybrid with a weaker balancer
    for r in (0.01, 0.025):
        bc = b * r / 0.05 if bal_cost_scaled else b
        for k in (1, 8, 25):
            out.append(P(f"d. hybrid {k} + bal {r:.1%}{' (cost scaled)' if bal_cost_scaled else ''}", "hybsel", e * k / m + bc, (k, r), k=k, group="d"))
    return out


def deferred(sc, plans=((6.0,), (8.0,), (4.0, 8.0)), ks=(8, 25), selectors=("reading", "projected"), retrofit_fee=0.0):
    """e. (OUT OF SCOPE hardware, ASSUMED): 5% balancer from day 1, k bypass switches fitted at a service visit in year T on the cells observed weakest then (moved at later visits).
    Cost = balancer + switch hardware discounted to the first visit + retrofit_fee ($ per kWh nameplate, labour) discounted to every visit."""
    e, b, m, r = sc["elec"], sc["bal_cost"], sc["m"], sc["rate"]
    out = []
    for yrs in plans:
        for k in ks:
            for sel in selectors:
                cost = b + e * k / m * np.exp(-r * yrs[0]) + sum(retrofit_fee * np.exp(-r * y) for y in yrs)
                out.append(P(f"e. switches {k} fitted yr {'+'.join(format(y, 'g') for y in yrs)} by {sel} + bal 5%", "hybsel", cost, (k, 0.05), k=k, mask="deferred",
                             defer=(tuple(yrs), k, sel), group="e"))
    return out


# ---------------------------------------------------------------- simulator
def _fit_projection(hist_t, hist_obs, t_now, horizon):
    """Least-squares straight line per cell on its readings so far; projected reading at the horizon. Uses only past readings."""
    t = np.asarray(hist_t)
    y = np.asarray(hist_obs)
    if len(t) < 3:
        return y[-1]
    tm = t.mean()
    slope = ((t - tm)[:, None] * (y - y.mean(axis=0))).sum(axis=0) / max(((t - tm) ** 2).sum(), 1e-12)
    return y.mean(axis=0) + slope * (horizon - tm)


def simulate(pol, dr, sc, floor_fn=None, meas=None, energy_fn=None):
    """PV (capability-years, discounted, as wear_scan) and lost-energy dollars per kWh for one policy on one draw. meas overrides the day-1 test the policy sees."""
    floor_fn = floor_fn or window_floor_fn(sc["window"])
    c0, f = dr["c0"], dr["f"]
    meas = dr["meas"] if meas is None else meas
    n, m = c0.size, sc["m"]
    S = n // m
    steps, years = sc["steps"], sc["years"]
    t = np.linspace(0.0, years, steps)
    dt = np.diff(t)
    disc = np.exp(-sc["rate"] * t)
    s0 = c0.sum()
    qd = sc["duty"] * float(np.mean(c0.reshape(-1, m).min(axis=1)))
    kind, par = pol["kind"], pol["par"]
    mask = None
    if pol["mask"] == "all":
        mask = np.ones((S, m), bool)
    elif pol["mask"] == "day1" and kind in ("select", "hybsel"):
        mask = np.zeros((S, m), bool)
        if pol["k"] > 0:
            mask[np.arange(S)[:, None], np.argsort(meas.reshape(-1, m), axis=1)[:, :pol["k"]]] = True
    c = c0.copy()
    u = np.zeros(steps)
    lost = np.zeros(steps)
    hist_t, hist_o = [], []
    visits = list(pol["defer"][0]) if pol["defer"] else None
    for j in range(steps):
        s = c.reshape(-1, m)
        obs = c * (1.0 + OBS_SIGMA * dr["obs_noise"][j])
        hist_t.append(t[j]); hist_o.append(obs / np.maximum(meas, 1e-9))
        kmax = np.asarray(floor_fn(s, m))
        n_min = int(m - kmax.min())
        k_j, par_j, mask_j = kind, par, mask
        if visits is not None:
            if visits and t[j] >= visits[0] - 1e-9:   # service visit: fit / move the k switches using readings up to now only
                visits.pop(0)
                score = (_fit_projection(hist_t, hist_o, t[j], years) * meas if pol["defer"][2] == "projected" else obs).reshape(-1, m)   # absolute capacity: the limiter
                mask = np.zeros((S, m), bool)
                mask[np.arange(S)[:, None], np.argsort(score, axis=1)[:, :pol["defer"][1]]] = True
            if mask is None:
                k_j, par_j, mask_j = "bal", par[1], None
            else:
                mask_j = mask
        if k_j in ("select", "hybsel") and mask_j is not None and mask_j.sum(axis=1).max() > kmax.min() and pol["mask"] != "all":
            raise ValueError("switched cells exceed the voltage floor's bypass limit")
        if k_j == "hybsel" and pol["mask"] == "all":
            # every cell switched, but only kmax may be bypassed at once: the floor limits the hybrid's tail exactly like the window limits 'late'
            cap, dod = W._step(s, m, qd, "hybsel", par_j, sc["loss"], sc["closed_loss"], sc["bal_eta"], _limit_mask(s, kmax), None, pol["share_wear"])
            cl_part = sc["closed_loss"] * kmax / m   # _step charged the closed-path loss only on the kmax-cell mask; every cell carries a switch, so charge all of it
            cap = cap * (1.0 - sc["closed_loss"]) / (1.0 - cl_part)
            cap = np.maximum(cap, W._step(s, m, qd, "bal", par_j[1], sc["loss"], sc["closed_loss"], sc["bal_eta"], None, n_min)[0] * (1.0 - sc["closed_loss"]))
        else:
            cap, dod = W._step(s, m, qd, k_j, par_j, sc["loss"], sc["closed_loss"], sc["bal_eta"], mask_j, n_min, pol["share_wear"])
        if pol["rest"] is not None:
            dod, d_ah = _rest(pol["rest"], dod, s, mask_j if mask_j is not None else np.ones((S, m), bool), kmax, hist_t, hist_o, t[j], years, sc["loss"], m, meas)
            lost[j] = sc["loss"] * d_ah / s0
        if energy_fn is None:
            u[j] = cap.sum()
        else:
            cl_share = 0.0 if k_j in ("plain", "bal") else (1.0 if (pol["mask"] == "all" or k_j in ("late", "level")) else mask_j.mean(axis=1))
            u[j] = energy_fn(s, cap, cl_share, c0.reshape(-1, m))
        if j == steps - 1:
            break
        rate_i = f.copy()
        if sc["dod_exp"] != 0.0:
            rate_i = rate_i * (np.maximum(dod, 1e-9) / sc["duty"]).reshape(-1) ** sc["dod_exp"]
        if sc["knee_share"] > 0:
            rate_i = np.where(dr["is_knee"] & (c * sc["start_soh"] <= dr["soh_k"] * c0), rate_i * sc["knee_kappa"], rate_i)
        c = np.maximum(c - dt[j] * rate_i * c0, 0.0)
    alive = np.cumprod(u / s0 >= sc["eol"])
    y = (u / s0) * alive * disc
    pv = float(((y[1:] + y[:-1]) * 0.5 * dt).sum())
    yl = lost * alive * disc * CYCLES_PER_YEAR * ENERGY_PRICE
    lost_usd = float(((yl[1:] + yl[:-1]) * 0.5 * dt).sum())
    return pv, lost_usd


def _limit_mask(s, kmax):
    """With every cell switched but at most kmax bypassable, the cells that matter for bypass are the kmax weakest right now (the controller picks them live)."""
    mask = np.zeros_like(s, dtype=bool)
    for i, k in enumerate(kmax):
        if k > 0:
            mask[i, np.argsort(s[i])[:int(k)]] = True
    return mask


def _rest(rest, dod, s, mask, kmax, hist_t, hist_o, t_now, horizon, loss, m, meas):
    """Rotating rest: in low-load hours the chosen switched cells are bypassed for a share (1 - frac) of the cycle, so they pass frac of their Ah; the other cells of the string carry the
    deficit, inflated by 1/(1 - loss) for the bypass loss. Returns new DoD and the deficit Ah moved (for the energy charge)."""
    sel, frac, count = rest
    o = hist_o[-1].reshape(-1, m)
    if sel == "projected":
        score = (_fit_projection(hist_t, hist_o, t_now, horizon) * meas).reshape(-1, m)   # low = projected limiter (absolute capacity at the horizon)
    else:
        score = o   # observed: lowest reading relative to day 1 = most wear so far
    dod = dod.copy()
    total = 0.0
    for i in range(s.shape[0]):
        cnt = int(min(kmax[i], count if count is not None else kmax[i]))
        cand = np.where(mask[i])[0]
        if cnt <= 0 or cand.size == 0:
            continue
        r = cand[np.argsort(score[i, cand])[:cnt]]
        ah = dod[i, r] * s[i, r]
        d = float(((1.0 - frac) * ah).sum())
        dod[i, r] = dod[i, r] * frac
        carry = np.ones(m, bool); carry[r] = False
        dod[i, carry] = np.minimum(dod[i, carry] + d / ((1.0 - loss) * carry.sum()) / np.maximum(s[i, carry], 1e-12), 1.0)
        total += d
    return dod, total


def net_values(pols, dr, sc, floor_fn=None, meas=None, energy_fn=None):
    """Net $ per kWh nameplate vs plain for every policy on one draw (same convention as wear_scan: value x (pv - pv_plain) - cost, minus lost-energy dollars)."""
    pv_plain, _ = simulate(P("plain", "plain", 0.0), dr, sc, floor_fn, meas, energy_fn)
    out = {}
    for p in pols:
        pv, lost = (pv_plain, 0.0) if p["kind"] == "plain" else simulate(p, dr, sc, floor_fn, meas, energy_fn)
        out[p["name"]] = sc["value"] * (pv - pv_plain) - p["cost"] - lost
    return out


# ---------------------------------------------------------------- per-pack / guarded choice (decision-time information only)
def in_sample_choice(pols, dr, sc, trials=4, floor_fn=None, seed_base=900_000, energy_fn=None):
    """Pick the policy with the best mean net value on PRIOR draws built only from the day-1 test: the pack's true capacities are unknown, so each prior draw's truth is
    meas x (1 + test_sigma x noise), the fade rates come from the scenario prior on an independent seed, and the mask is built from the real meas. Returns (name, means)."""
    meas = dr["meas"]
    acc = {p["name"]: 0.0 for p in pols}
    for i in range(trials):
        sd = seed_base + dr["seed"] * 10 + i
        truth = meas * (1.0 + sc["test_sigma"] * np.random.default_rng(sd + 5).standard_normal(meas.size))
        d2 = draw(sd, sc, truth)
        v = net_values(pols, d2, sc, floor_fn, meas=meas, energy_fn=energy_fn)
        for k in acc:
            acc[k] += v[k] / trials
    return max(acc, key=acc.get), acc


def guarded_choice(cands, base, dr, sc, trials=4, margin=0.0, floor_fn=None, energy_fn=None):
    """GUARDED meta-policy: choose a candidate only if its in-sample mean beats the best baseline's in-sample mean by `margin`; otherwise the best baseline."""
    _, acc = in_sample_choice(cands + base, dr, sc, trials, floor_fn, energy_fn=energy_fn)
    bn = max((p["name"] for p in base), key=acc.get)
    cn = max((p["name"] for p in cands), key=acc.get) if cands else bn
    return (cn if acc[cn] > acc[bn] + margin else bn), acc


# ---------------------------------------------------------------- stats
def mean_ci(x):
    x = np.asarray(x, float)
    n = x.size
    se = x.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
    return dict(mean=float(x.mean()), lo=float(x.mean() - 1.96 * se), hi=float(x.mean() + 1.96 * se), n=int(n))


def group_best(values_by_name, pols):
    """Per group (plain, balancer 2.5%, balancer 5%, switches alone, hybrid): the member with the best MEAN over the draws (picked in hindsight, which favours the baselines)."""
    best = {}
    for p in pols:
        g = p["group"]
        v = np.asarray(values_by_name[p["name"]])
        if g not in best or v.mean() > best[g][1].mean():
            best[g] = (p["name"], v)
    return best


def regret(policy_vals, base_vals_by_name, base):
    """Scenario regret = max(0, best baseline group mean - policy mean) >= 0. Also the per-draw regret vs the per-draw best baseline (an oracle no ex-ante policy can match)."""
    gb = group_best(base_vals_by_name, base)
    best_mean = max(v.mean() for _, v in gb.values())
    pv = np.asarray(policy_vals)
    per_draw_best = np.max(np.stack([np.asarray(base_vals_by_name[p["name"]]) for p in base]), axis=0)
    return dict(scenario=float(max(0.0, best_mean - pv.mean())), best_baseline=max(gb, key=lambda g: gb[g][1].mean()),
                oracle_mean=float(np.maximum(per_draw_best - pv, 0.0).mean()))
