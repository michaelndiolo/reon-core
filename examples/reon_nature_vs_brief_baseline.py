"""The 12 real Nature cars against the brief's OWN baseline (plain fixed string), not against a balancer.
Reports, per application and switch cost: cars where our best build beats plain, and cars where it also beats sort only."""
from multiprocessing import Pool
import numpy as np
from examples.reon_nature_real_packs import CARS, APPS
from hackkit import reon_wear as W

COSTS = (4.4, 8.8, 13.2)   # electronics cost per kWh with a switch on EVERY cell: half, our assumed, 1.5x


def job(a):
    car, app, c = a
    d = CARS[car]
    late = d[:, 1] / d[:, 1].mean() * 90.0
    n = len(late)
    loss = 1.0 - d[:, 1] / d[:, 0]
    fcv = min(float(loss.std(ddof=1) / loss.mean()), 0.6)
    r = W.wear_scan(late, n, fade_cv=fcv, loss=0.02, electronics_per_kwh=c, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, rate=0.07, trials=14, steps=40, seed=5,
                    balancer_rs=(), global_counts=(1, 2, 3, 4, 8), **APPS[app])
    ours = {k: v["mean"] for k, v in r.items() if k.startswith("late") or k.startswith("selective")}
    # selective cost is charged by the engine as g/n of electronics_per_kwh
    best = max(ours.values())
    return a, best, r["sort only"]["mean"]


if __name__ == "__main__":
    jobs = [(c_, app, e) for c_ in CARS for app in APPS for e in COSTS]
    with Pool() as p:
        out = p.map(job, jobs)
    for app in APPS:
        for e in COSTS:
            rows = [o for o in out if o[0][1] == app and o[0][2] == e]
            vs_plain = [o[1] for o in rows]
            vs_sort = [o[1] - max(o[2], 0.0) for o in rows]
            print(f"{app:11s} switch cost {e:5.1f}: beat plain in {sum(v > 0.05 for v in vs_plain)} of 12 (median {np.median(vs_plain):+6.1f}, min {min(vs_plain):+6.1f}, max {max(vs_plain):+6.1f}); beat plain AND sort-only in {sum(v > 0.05 for v in vs_sort)} of 12 (median {np.median(vs_sort):+6.1f})")
