"""Does cell-level control help WELL-MATCHED packs once ageing depends on how the pack is run, and once knee-like fades are included? Run: PYTHONPATH=. python examples/reon_wear_regimes.py
24 cells in 3 strings of 8, day-1 capacity ~ Normal(90, cv x 90). Dynamics: (A) linear fade as in reon_design; (B) fade ~ DoD^g with g = 0.8 (Iowa fit, 0.6 to 0.9; duty 0.7 of the weakest cell, ASSUMED);
(C) B plus knees (65% of cells, 2.4x faster fade from an SOH of 0.82 to 0.90 against new; Iowa; start SOH 1.0 for fresh cells, 0.8 for a retired EV pack).
Electronics 8.8 per kWh nameplate (switch on every cell), switch loss 2%, balancer efficiency 90%, sorting free. Balancer free (best case for the rival) and costing 4.
Numbers: mean net value per kWh nameplate vs the plain pack over 40 trials; ASSUMED parameters flagged in the text. fade fade_cv 0.2 (Iowa)."""
import sys
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

APPS = {"retired EV": dict(value_per_kwh_year=22.0, years=7.0, eol_frac=0.7, fade_mean=0.01, start_soh=0.8),
        "grid": dict(value_per_kwh_year=12.0, years=15.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0),
        "data-center": dict(value_per_kwh_year=8.0, years=12.0, eol_frac=0.8, fade_mean=0.005, start_soh=1.0)}
DYN = {"A linear": dict(dod_exp=0.0, knee_share=0.0), "B wear g=0.8": dict(dod_exp=0.8, knee_share=0.0), "C wear + knees": dict(dod_exp=0.8, knee_share=0.65)}
CVS = (0.005, 0.02, 0.05, 0.10)


def job(a):
    app, dyn, cv, bal = a
    rng = np.random.default_rng(11)
    caps = np.maximum(rng.normal(90, cv * 90, 24), 20)
    return a, W.wear_scan(caps, 8, fade_cv=0.2, loss=0.02, electronics_per_kwh=8.8, balancer_per_kwh=bal, sort_cost_per_kwh=0.0, rate=0.07, duty=0.7,
                          trials=40, seed=5, **APPS[app], **DYN[dyn])


if __name__ == "__main__":
    jobs = [(a, d, cv, b) for a in APPS for d in DYN for cv in CVS for b in (0.0, 4.0)]
    with Pool() as p:
        res = dict(p.map(job, jobs))
    for bal in (0.0, 4.0):
        print(f"\n######## balancer costs {bal:g} per kWh nameplate ########")
        for app in APPS:
            print(f"\n== {app} ==  (net value per kWh nameplate; winner in brackets)")
            for dyn in DYN:
                for cv in CVS:
                    r = res[(app, dyn, cv, bal)]
                    best = max((k for k in r if k != "plain"), key=lambda k: r[k]["mean"])
                    show = "  ".join(f"{k.replace('late switches', 'late').replace('level switches', 'level').replace('balancer', 'bal')}:{r[k]['mean']:+.1f}" for k in
                                     ("sort only", "late switches", "level switches", "balancer 10%", "balancer unlimited"))
                    print(f"{dyn:15s} cv {cv:5.1%} | {show} | best [{best}] {r[best]['mean']:+.1f}")
