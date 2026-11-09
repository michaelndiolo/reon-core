"""HERO CASE (draft): new 16-cell string, commercial/industrial stationary duty, daily cycling, retire at 70 % (brief). Run: PYTHONPATH=. python examples/reon_hero_cni.py
Cells start nearly matched (ASSUMED start spread 2 %); what separates them is the spread of FADE RATES, taken from REAL lithium cars (Nature Energy 2026 Fig 4: fade-spread CV 0.20 to 0.60, median 0.45). No sodium-ion spread data yet: ASK REON.
Sweep: value per delivered kWh-year (12 = grid preset, 22 = retired-EV preset, 40 and 80 = C&I peak-shaving range, ASSUMED until sourced) x switch cost (7, 15.5, 24 per kWh nameplate = REON's 7 Nov range, with a switch on every cell) x fade-spread CV.
Reports net value per kWh nameplate of the best build (late switches, level switches or selective bypass) against the plain string and against sort only."""
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

N = 16
VALUES = (12.0, 22.0, 40.0, 80.0)
COSTS = (7.0, 15.5, 24.0)
FCVS = (0.20, 0.45, 0.60)


def job(a):
    v, c, f = a
    rng = np.random.default_rng(11)
    start = 100.0 * (1.0 + 0.02 * rng.standard_normal(N))
    r = W.wear_scan(start, N, fade_cv=f, loss=0.02, electronics_per_kwh=c, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, rate=0.07, trials=14, steps=40, seed=5,
                    balancer_rs=(), global_counts=(1, 2, 3, 4, 8), value_per_kwh_year=v, years=12.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0)
    ours = {k: x["mean"] for k, x in r.items() if k.startswith("late") or k.startswith("selective") or k.startswith("level")}
    k = max(ours, key=ours.get)
    return a, k, ours[k], r["sort only"]["mean"]


if __name__ == "__main__":
    jobs = [(v, c, f) for v in VALUES for c in COSTS for f in FCVS]
    with Pool() as p:
        out = p.map(job, jobs)
    print("value/kWh-yr  switch cost  fade CV   best build            net vs plain   net vs sort-only")
    for (v, c, f), k, g, s in out:
        print(f"{v:8.0f} {c:12.1f} {f:9.2f}   {k:20s} {g:+10.1f} {g - max(s, 0.0):+14.1f}")
    print("\nwins vs plain:", sum(o[2] > 0.05 for o in out), "of", len(out), "; vs sort-only:", sum(o[2] - max(o[3], 0) > 0.05 for o in out), "of", len(out))
