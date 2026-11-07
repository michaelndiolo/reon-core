"""Life-of-the-string event simulation: what happens over years when cells fade at different rates and some fail, under four ways of running a series string (monthly steps).
  replace   conventional: sensors flag a dead or persistently weak cell, a crew visit replaces it after a lead time; the plain string is DOWN while a cell is dead.
  thr<x>    fixed-threshold rival: the cell is bypassed automatically when it is below x of the median (or dead), for good; usable = engaged cells x weakest engaged cell / n (a static bypass loses that cell's voltage).
            When the bypass budget or the voltage margin is used up, it calls a crew like `replace`.
  ours+crew like ours, and when `crew_at` cells are bypassed it books ONE crew visit to put them back (restores voltage and budget; costs a visit).
  ours      same permanent-bypass rule at 0.85 with a persistence of 3 months, PLUS per-cycle late switching: usable = sum of engaged cells x (1 - switch loss) / n.
Bypass stress is charged: with k bypassed, engaged cells wear (n / engaged)^g faster (g = DoD exponent, Iowa State fit 0.87).
Retired when usable (ignoring downtime) falls below `retire` of beginning-of-life (brief: 70 %). Value = value per kWh-year x usable x nameplate while up; costs = visits, replacement cells, and (for the bypassing policies) the electronics; discounted monthly.
Common random numbers across policies. Every default is ASSUMED unless docs/SOURCES.md says otherwise."""
import numpy as np

POLICIES = ("replace", "thr0.95", "thr0.90", "thr0.85", "thr0.80", "ours", "ours+crew")


def _draw(rng, n, months, fade, fcv, start_cv, lam, reps=6):
    sig = np.sqrt(np.log(1 + fcv ** 2))
    f = fade * rng.lognormal(-sig ** 2 / 2, sig, (n, reps))              # yearly fade fractions, slot x generation
    c0 = 1.0 + start_cv * rng.standard_normal((n, reps))
    ft = rng.geometric(max(lam / 12.0, 1e-12), (n, reps)).astype(float)   # month of first fault, from the cell's start
    return f, c0, ft


def simulate(policy, seed, n=16, months=144, fade=0.02, fcv=0.45, start_cv=0.02, lam=0.01, lead=1.0, visit_cost=1000.0, nameplate=60.0, value=40.0, e=15.5, cell_cost_per_kwh=98.0,
             n_min=12, bypass_budget=4, crew_at=3, g=0.87, loss=0.02, persist=3, retire=0.7, rate=0.07):
    rng = np.random.default_rng(seed)
    f, c0, ft = _draw(rng, n, months, fade, fcv, start_cv, lam)
    gen = np.zeros(n, int)
    cap = c0[:, 0].copy()
    born = np.zeros(n)
    byp = np.zeros(n, bool)
    weak = np.zeros(n, int)
    theta = 0.85 if policy.startswith("ours") else (1.0 if policy == "replace" else float(policy[3:]))
    if policy == "replace":
        theta = 0.85
    auto = policy != "replace"
    budget = bypass_budget
    pend = None
    pv_val = pv_cost = 0.0
    visits = down = life = 0
    cell_cost = cell_cost_per_kwh * nameplate / n
    if auto:
        pv_cost += e * nameplate
    for t in range(months):
        d = (1 + rate) ** (-t / 12.0)
        eng = ~byp
        mult = (n / max(eng.sum(), 1)) ** g if auto else 1.0
        cap = np.where(eng, cap - f[np.arange(n), gen] * mult / 12.0, cap)
        dead = (t - born >= ft[np.arange(n), gen]) & ~byp
        cap = np.where(dead, 0.0, cap)
        alive = eng & ~dead
        med = np.median(cap[alive]) if alive.any() else 1.0
        weak = np.where(alive & (cap < theta * med), weak + 1, 0)
        flagged = dead | (weak >= persist)
        if auto:
            for i in np.flatnonzero(flagged):
                if budget > 0 and (~byp).sum() - 1 >= n_min:
                    byp[i] = True
                    budget -= 1
                    flagged[i] = False
        eng = ~byp
        up = not (dead & eng).any()
        if (flagged.any() or (policy == "ours+crew" and byp.sum() >= crew_at)) and pend is None:
            pend = t + lead
        if pend is not None and t >= pend:
            fl = np.flatnonzero(flagged | (auto & byp) | (dead & ~byp))
            for i in fl:
                gen[i] = min(gen[i] + 1, f.shape[1] - 1)
                cap[i], born[i], byp[i], weak[i] = c0[i, gen[i]], t, False, 0
            budget = bypass_budget
            visits += 1
            pv_cost += d * (visit_cost + len(fl) * cell_cost)
            pend = None
            eng = ~byp
            dead = np.zeros(n, bool)
            up = True
        live = eng & ~dead                      # a dead cell waiting for the crew is a fault, not a reason to retire the string: retirement looks at the cells that work
        ce = cap[live]
        if not live.any():
            usable = 0.0
        elif policy.startswith("ours"):
            usable = ce.sum() * (1 - loss) / n
        else:
            usable = (live.sum() if auto else eng.sum()) * ce.min() / n
        if usable < retire:
            life = t
            break
        life = t + 1
        if up:
            pv_val += d * value * nameplate / 12.0 * usable
        else:
            down += 1
    return dict(net=(pv_val - pv_cost) / nameplate, visits=visits, down_months=down, life_years=life / 12.0)
