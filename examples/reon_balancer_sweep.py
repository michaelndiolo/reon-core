"""How strong would a balancer have to be before cell-level switching stops paying? Writes/merges examples/data/balancer_sweep.json.
For one position type (p cells in parallel), one wear level and one balancer transfer limit r (share of a cell's capacity it can move per cycle; 5% is our assumed rival, unsourced) it records the 12-year gain over a plain string, per kWh nameplate:
  * balancer alone                 : an active balancer, cost 4 per kWh, efficiency 0.9
  * REON switches alone            : the best of late / level / selective switch builds (cost 15.5 per kWh, at most 25 of 250 cells bypassed)
  * switches plus the balancer     : the hybrid, with the balancer's wear sharing credited to it (hybrid_shares_wear)
Each build is picked on one seed and scored on an independent seed with twice the trials (the same rule as the verdict). Value 40 per kWh-year, 250 cells, 90% voltage window.
usage: PYTHONPATH=. python examples/reon_balancer_sweep.py P FADE[,FADE...]    e.g.  ... 1 0.004,0.008   (about 25 s per 8 jobs)"""
import datetime
import json
import sys
from multiprocessing import Pool

from hackkit import reon_guard as G
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
    kw.update(balancer_r=r, hybrid_shares_wear=True)
    start = SF._start(p, SF.N_SERIES)
    pick, _ = G.safe_recommend(start, SF.N_SERIES, seed=5, **kw)
    kw2 = dict(kw, trials=2 * kw["trials"])
    chk, _ = G.safe_recommend(start, SF.N_SERIES, seed=11, **kw2)
    out = {}
    for name, (pk, ck) in zip(("reon", "both", "balancer"), zip(cats(pick["table"]), cats(chk["table"]))):
        best = max(pk, key=lambda k: pk[k]["mean"])
        out[name] = dict(build=best, gain=float(ck[best]["mean"]), p10=float(ck[best]["p10"]))
    return key(p, fade, r), out


if __name__ == "__main__":
    p = int(sys.argv[1])
    fades = [float(x) for x in sys.argv[2].split(",")]
    jobs = [(p, f, r) for f in fades for r in LIMITS]
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
