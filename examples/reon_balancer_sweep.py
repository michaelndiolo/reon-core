"""How strong would a balancer have to be before cell-level switching stops paying? Writes/merges examples/data/balancer_sweep.json.
For one position type (p cells in parallel), one wear level and one balancer transfer limit r (share of a cell's capacity it can move per cycle; 5% is our assumed rival, unsourced) it records the 12-year gain over a plain string, per kWh nameplate:
  * balancer alone                 : an active balancer, cost 4 per kWh, efficiency 0.9
  * REON switches alone            : the best of late / level / selective switch builds (cost 15.5 per kWh, at most 25 of 250 cells bypassed)
  * switches plus the balancer     : the best hybrid (a few switches on the weakest cells, or a switch on every cell), with the balancer's wear sharing credited to it and the weak cells exempt from its bottleneck\n  * our recommendation             : reon_policy.robust_guarded: our build only if it beats the better of balancer and plain by 1 per kWh on two seeds, otherwise the balancer or plain itself
Each build is picked on one seed and scored on an independent seed with twice the trials (the same rule as the verdict). Value 40 per kWh-year, 250 cells, 90% voltage window.
usage: PYTHONPATH=. python examples/reon_balancer_sweep.py next N   (the next N jobs not yet done; about 13 s per job on 4 cores)   or   ... P FADE[,FADE...] [R,R,...]    e.g.  ... 1 0.004,0.008   (about 25 s per 8 jobs)"""
import datetime
import json
import sys
from multiprocessing import Pool

from hackkit import reon_policy as POL
from hackkit import reon_storefront as SF

LIMITS = (0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15)
PATH = "examples/data/balancer_sweep.json"
VALUE = 40.0


def key(p, fade, r):
    return f"{int(p)}|{float(fade):.4f}|{float(r):.3f}"


def cats(table):
    reon = {k: v for k, v in table.items() if k.startswith(("late", "level", "selective"))}
    both = {k: v for k, v in table.items() if k.startswith("hybrid")}
    bal = {k: v for k, v in table.items() if k.startswith("balancer")}
    return reon, both, bal


def job(a):
    p, fade, r = a
    kw = SF._kw(p, fade, VALUE, SF.ELEC, 12.0, SF.N_SERIES)
    start = SF._start(p, SF.N_SERIES)
    rb = POL.robust_guarded(start, SF.N_SERIES, balancer_r=r, life_years=None, **kw)   # recommendation: picked on seed 5, re-checked and scored on seed 11 with twice the trials; rb["table"] is that fresh scan
    s, P = POL._params(start, SF.N_SERIES, kw["value_per_kwh_year"], kw["electronics_per_kwh"], kw["fade_cv"], kw["loss"], kw["years"], kw["eol_frac"], 0.7, kw["fade_mean"], 0.07, r, 4.0, kw["ks"], 0.87, 0.65, 1.0, 0.9,
                       kw["closed_loss"], 0.02, 0.0, 16, kw["steps"], kw["window"], True, True, 1.0)
    pick = POL._scan(s, SF.N_SERIES, seed=5, **P)   # categories are picked on seed 5, scored on the fresh seed
    fresh = rb["table"]
    out = {}
    for name, (pk, ck) in zip(("reon", "both", "balancer"), zip(cats(pick), cats(fresh))):
        best = max(pk, key=lambda k: pk[k]["mean"])
        out[name] = dict(build=best, gain=float(fresh[best]["mean"]), p10=float(fresh[best]["p10"]))
    out["recommended"] = dict(build=rb["build"], gain=float(rb["mean_gain"]), p10=float(rb["p10_gain"]), verdict=rb["verdict"])
    out["v"] = 2   # 2 = after the exempt-hybrid dominance fix (hybrid never below the balancer)
    return key(p, fade, r), out


def todo():
    try:
        done = json.load(open(PATH))["cases"]
    except (OSError, ValueError):
        done = {}
    return [(p, f, r) for p in (1, 4, 16) for f in (0.004, 0.008, 0.02) for r in LIMITS if "v" not in done.get(key(p, f, r), {})]


if __name__ == "__main__":
    if sys.argv[1] == "next":   # run the next N jobs that are not yet computed with the current algorithm (v = 2): short calls, resumable
        jobs = todo()[:int(sys.argv[2])]
        print(len(todo()), "jobs left before this call")
    else:
        p = int(sys.argv[1])
        fades = [float(x) for x in sys.argv[2].split(",")]
        limits = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else LIMITS
        jobs = [(p, f, r) for f in fades for r in limits]
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    try:
        data = json.load(open(PATH))
    except (OSError, ValueError):
        data = {"cases": {}}
    data["cases"].update(dict(res))
    data["generated"] = datetime.date.today().isoformat()
    data["note"] = ("12-year gain over a plain string, per kWh nameplate, value 40 per kWh-year, 250 cells, switch cost 15.5, balancer cost 4 and efficiency 0.9, 90% voltage window, "
                    "builds picked on one seed and scored on another. The balancer transfer limit is the swept variable; 5% is our unsourced assumption. Regenerate with examples/reon_balancer_sweep.py.")
    json.dump(data, open(PATH, "w"), indent=1, sort_keys=True)
    print(len(data["cases"]), "cases saved;", len(res), "just computed")
