"""Tim Ren (7 Nov): strings are 200 to 300 cells in series. Our earlier hero case used 16. Rerun at 250 series elements.
The open question is what one series element IS: a single large cell (p = 1) or a parallel group of p small cells (e.g. '40P 250S'). Parallel cells average each other out: capacity spread and fade spread both shrink by sqrt(p).
For each case: verdict (pick on one seed, check on an independent seed with double the trials), net gain over plain per kWh nameplate, and SYSTEM LIFE (years and cycles at one cycle a day, retire at 70 % of day-1) plain vs best of ours.
usage: python examples/reon_hero_250.py 12   (then 20, then 30: one horizon per call fits the 120 s limit)"""
import sys
import numpy as np
from multiprocessing import Pool
from hackkit import reon_guard as G

KS = (1, 2, 4, 8, 16, 25)
BASE = dict(value_per_kwh_year=40.0, electronics_per_kwh=15.5, loss=0.04, years=30.0, eol_frac=0.7, trials=8, steps=60)

def case(a):
    p, fade, elec, label, years = a
    rng = np.random.default_rng(3)
    start = 100.0 * (1.0 + 0.02 / np.sqrt(p) * rng.standard_normal(250))
    kw = dict(BASE, years=years, electronics_per_kwh=elec, fade_cv=0.45 / np.sqrt(p), fade_mean=fade, ks=KS)
    r = G.robust_recommend(start, 250, **kw)
    out, _ = G.safe_recommend(start, 250, seed=9, **kw)
    t = out["table"]; nm = out["ours_best"]
    return dict(label=label, years=years, p=p, fade=fade, elec=elec, verdict=r["verdict"], build=r["build"], gain=r["mean_gain"], p10=r["p10_gain"], rival=out["rival_best"], margin=out["margin"],
                life_plain=t["plain"]["years"], life_ours=t[nm]["years"], reasons=r["reasons"])

if __name__ == "__main__":
    jobs = []
    hz = [float(x) for x in sys.argv[1:]] or [12.0]
    for years in hz:
        for p in (1, 4, 16, 40):
            for fade in (0.004, 0.008, 0.02):
                jobs.append((p, fade, 15.5, "total cost", years))
    for p in (1, 40) if 12.0 in hz else ():
        jobs.append((p, 0.008, 15.5 * 0.7, "extra cost only (3.5x BMS)", 12.0))
    with Pool(4) as pool:
        rows = pool.map(case, jobs)
    print("250 series elements, value 40 per kWh-year, switch loss 4%. Horizon = years the site is valued for; 12 is bankable (warranty 10 y), 20 and 30 are cell-limited life. Life is capped at the horizon.")
    print(f"{'hor':>4} {'p':>3} {'fade/yr':>7} {'switch cost':>26} | {'verdict':7} {'ours (best)':28} {'gain':>6} {'p10':>6} {'margin vs rival':>15} | {'life plain':>10} {'life ours':>9} {'cycles plain':>12} {'cycles ours':>11}")
    for r in rows:
        print(f"{r['years']:4.0f} {r['p']:3d} {r['fade']:7.3f} {r['label']:>26} | {r['verdict']:7} {r['build'][:28]:28} {r['gain']:6.1f} {r['p10']:6.1f} {r['margin']:15.1f} | {r['life_plain']:9.1f}y {r['life_ours']:8.1f}y {365*r['life_plain']:12.0f} {365*r['life_ours']:11.0f}")
