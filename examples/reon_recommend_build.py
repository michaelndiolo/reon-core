"""ONE policy: reon_wear.recommend_build on the real packs, three applications, three balancer cases. Run: PYTHONPATH=. python examples/reon_recommend_build.py
Packs: 8 Nissan Leaf cells (REAL, arXiv 2402.18859, one string of 8), 36 BMW i3 cells (REAL, arXiv 2507.14020, three strings of 12), REON brief 16 cells (15 at 85 Ah, one at 70 Ah, one string of 16).
Candidates: plain, sort only, selective bypass on the k weakest cells of each string (k = 1..m-1), switches on every cell, an active balancer (limit r, cost). Our electronics 8.8 per kWh for a switch on every cell, k/m of that
for selective (ASSUMED). Net value per kWh nameplate. Balancer cases: (r 5%, cost 4) = typical-current balancer; (r 20%, cost 12) = 10 A class with transformers; (r 20%, cost 0) = the hardest case, free and big."""
import csv
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

def load(p):
    return np.array([float(r["capacity"]) for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))])

PACKS = {"Leaf 8 cells": (load("examples/data/leaf_8.csv"), 8), "BMW i3 36 cells": (load("examples/data/bmw_36.csv"), 12), "REON brief 16 cells": (np.array([85.0] * 15 + [70.0]), 16)}
APPS = {"retired EV": dict(value_per_kwh_year=22.0, years=7.0, eol_frac=0.7, fade_mean=0.01, start_soh=0.8),
        "grid": dict(value_per_kwh_year=12.0, years=15.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0),
        "data-center": dict(value_per_kwh_year=8.0, years=12.0, eol_frac=0.8, fade_mean=0.005, start_soh=1.0)}
BALS = {"balancer 5%, cost 4": (0.05, 4.0), "balancer 20%, cost 12": (0.20, 12.0), "balancer 20%, FREE": (0.20, 0.0)}


def job(a):
    pk, app, bal = a
    c, m = PACKS[pk]
    r, cost = BALS[bal]
    return a, W.recommend_build(c, m, balancer_r=r, balancer_per_kwh=cost, fade_cv=0.2, loss=0.02, electronics_per_kwh=8.8, sort_cost_per_kwh=0.0, rate=0.07, trials=30, seed=5, steps=60,
                                dod_exp=0.8, knee_share=0.65, **APPS[app])


if __name__ == "__main__":
    jobs = [(p, a, b) for p in PACKS for a in APPS for b in BALS]
    with Pool() as pool:
        res = dict(pool.map(job, jobs))
    for p in PACKS:
        c, m = PACKS[p]
        print(f"\n== {p}: weakest/mean {c.min() / c.mean():.2f}, cells below 0.9 x median: {(c < 0.9 * np.median(c)).sum()} ==")
        for a in APPS:
            for b in BALS:
                r = res[(p, a, b)]
                t = r["table"]
                print(f"{a:12s} {b:24s} -> build: {r['build']:34s} net {t[r['build']]['mean']:+6.1f}   (ours best: {r['ours_best']} {t[r['ours_best']]['mean']:+.1f}; rival best: {r['rival_best']} {t[r['rival_best']]['mean']:+.1f}; margin {r['margin']:+.1f})")
