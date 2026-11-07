"""AUTOMATIC BYPASS vs DETECT-AND-REPLACE vs FIXED THRESHOLDS over the life of a 16-cell, 60 kWh string (hackkit/reon_events.py). Run: PYTHONPATH=. python examples/reon_auto_bypass_sim.py
Sweep (all ASSUMED, no source yet for visit cost or fault rate): fault rate per cell-year 0.002 / 0.01 / 0.03, cost of one crew visit 250 / 1000 / 3000, crew lead time 0.5 / 2 months; value 40 per kWh-year, electronics 15.5 per kWh nameplate (Tim Ren range 7 to 24), fade-rate spread CV 0.45 (REAL lithium median).
Net value is per kWh nameplate, discounted at 7 %, averaged over trials; common random numbers across policies."""
from multiprocessing import Pool
import numpy as np
from hackkit import reon_events as E

TRIALS = 60
CONFIGS = [(lam, v, lead) for lam in (0.002, 0.01, 0.03) for v in (250.0, 1000.0, 3000.0) for lead in (0.5, 2.0)]


def job(c):
    lam, v, lead = c
    out = {}
    for p in E.POLICIES:
        r = [E.simulate(p, s, lam=lam, visit_cost=v, lead=lead) for s in range(TRIALS)]
        out[p] = {k: float(np.mean([x[k] for x in r])) for k in r[0]}
    return c, out


if __name__ == "__main__":
    with Pool() as pool:
        res = pool.map(job, CONFIGS)
    print("fault/cell-yr  visit  lead(mo) |  net per kWh nameplate: replace  thr.95  thr.90  thr.85  thr.80   ours  ours+crew | visits: replace thr.85 ours ours+crew | downtime months: replace  ours | life y: replace ours")
    w_rep = w_thr = w_best = 0
    for (lam, v, lead), o in res:
        best_thr = max(o[p]["net"] for p in E.POLICIES if p.startswith("thr"))
        w_rep += o["ours"]["net"] > o["replace"]["net"]
        w_best += max(o["ours"]["net"], o["ours+crew"]["net"]) > o["replace"]["net"]
        w_thr += o["ours"]["net"] > best_thr
        print(f"{lam:8.3f} {v:10.0f} {lead:6.1f}   | {o['replace']['net']:19.1f} {o['thr0.95']['net']:7.1f} {o['thr0.90']['net']:7.1f} {o['thr0.85']['net']:7.1f} {o['thr0.80']['net']:7.1f} {o['ours']['net']:7.1f} {o['ours+crew']['net']:9.1f} | {o['replace']['visits']:12.1f} {o['thr0.85']['visits']:6.1f} {o['ours']['visits']:5.1f} {o['ours+crew']['visits']:5.1f} | {o['replace']['down_months']:17.1f} {o['ours']['down_months']:5.1f} | {o['replace']['life_years']:8.1f} {o['ours']['life_years']:4.1f}")
    print(f"\nours (never books a crew) beats detect-and-replace in {w_rep} of {len(res)} configurations and the best fixed threshold in {w_thr} of {len(res)}; the better of ours / ours+crew beats detect-and-replace in {w_best} of {len(res)}")
