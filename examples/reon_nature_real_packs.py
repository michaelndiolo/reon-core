"""REAL per-cell capacities of 12 electric cars (Nature Energy 2026, Zhou et al., Source Data Fig. 4, CC BY 4.0): 95 NMC cells per car, normalised capacity at 80,000 km and at 280,000 km. Run: PYTHONPATH=. python examples/reon_nature_real_packs.py
Part 1: spread and fade spread, straight from the data (no model). Part 2: reon_wear.recommend_build on each car's 280,000 km pack (one string of 95 cells) with fade spread taken from that car's own cells,
for retired EV and grid, against three balancers: typical-current (5% limit, cost 4), transformer-class (20%, cost 12), free (20%). Our electronics 8.8 per kWh for every cell (ASSUMED), selective k/n of it."""
import csv, sys
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith('"#') and not l.startswith("#")))[1:]
CARS = {}
for p, _, e, l in rows:
    CARS.setdefault(p, []).append((float(e), float(l)))
CARS = {k: np.array(v) for k, v in CARS.items()}
BAL = {"balancer 5%, cost 4": (0.05, 4.0), "balancer 20%, cost 12": (0.20, 12.0), "balancer 20%, FREE": (0.20, 0.0)}
APPS = {"retired EV": dict(value_per_kwh_year=22.0, years=7.0, eol_frac=0.7, fade_mean=0.01, start_soh=0.8), "grid": dict(value_per_kwh_year=12.0, years=15.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0)}


def job(a):
    car, app, bal = a
    d = CARS[car]
    late = d[:, 1] / d[:, 1].mean() * 90.0
    loss = 1.0 - d[:, 1] / d[:, 0]
    fcv = float(loss.std(ddof=1) / loss.mean())
    r, cost = BAL[bal]
    ks = (1, 2, 3, 4)
    return a, W.recommend_build(late, len(late), balancer_r=r, balancer_per_kwh=cost, ks=ks, fade_cv=min(fcv, 0.6), loss=0.02, electronics_per_kwh=8.8, sort_cost_per_kwh=0.0, rate=0.07,
                                trials=14, steps=40, seed=5, **APPS[app])


if __name__ == "__main__":
    print("PART 1: real packs. beta = weakest / mean capacity. per-cell loss = 1 - cap(280k km)/cap(80k km); its CV is the real fade-rate spread within a car.")
    print(f"{'car':7s} {'cells':>5s} | {'cv 80k':>7s} {'beta 80k':>8s} | {'cv 280k':>7s} {'beta 280k':>9s} | {'ideal gain 280k':>15s} | {'loss mean':>9s} {'loss cv':>7s} | cells under 0.9 x median at 280k")
    cvs = []
    for k, d in CARS.items():
        e, l = d[:, 0], d[:, 1]
        loss = 1 - l / e
        cvs.append(loss.std(ddof=1) / loss.mean())
        print(f"{k:7s} {len(d):5d} | {e.std(ddof=1) / e.mean():7.3f} {e.min() / e.mean():8.3f} | {l.std(ddof=1) / l.mean():7.3f} {l.min() / l.mean():9.3f} | {l.mean() / l.min() - 1:15.1%} | {loss.mean():9.3f} {cvs[-1]:7.2f} | {(l < 0.9 * np.median(l)).sum()}")
    print(f"fade-rate spread (CV of per-cell loss) across the 12 cars: median {np.median(cvs):.2f}, range {min(cvs):.2f} to {max(cvs):.2f}  (Iowa State lab cells: median 0.20)")
    jobs = [(c, a, b) for c in CARS for a in APPS for b in BAL]
    with Pool() as pool:
        res = dict(pool.map(job, jobs))
    print("\nPART 2: recommend_build margin over the best alternative, per kWh nameplate (positive = we win); build chosen in brackets for the typical-current balancer")
    for a in APPS:
        for b in BAL:
            m_ = [res[(c, a, b)]["margin"] for c in CARS]
            print(f"  {a:11s} {b:22s}: we win in {sum(x > 0 for x in m_)} of 12 cars; margin median {np.median(m_):+5.1f}, min {min(m_):+5.1f}, max {max(m_):+5.1f}")
    print("\nper car, retired EV, balancer 5% cost 4: " + "; ".join(f"{c}: {res[(c, 'retired EV', 'balancer 5%, cost 4')]['margin']:+.1f} ({res[(c, 'retired EV', 'balancer 5%, cost 4')]['build'][:22]})" for c in CARS))


def breakeven(a):
    """Highest electronics cost (per kWh nameplate for a switch on EVERY cell; selective k of n costs k/n of it) at which we still beat the best rival: typical-current balancer (5%, cost 4), sort only, plain."""
    car, app = a
    d = CARS[car]
    late = d[:, 1] / d[:, 1].mean() * 90.0
    n = len(late)
    loss = 1.0 - d[:, 1] / d[:, 0]
    fcv = min(float(loss.std(ddof=1) / loss.mean()), 0.6)
    r = W.wear_scan(late, n, fade_cv=fcv, loss=0.02, electronics_per_kwh=0.0, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, rate=0.07, trials=14, steps=40, seed=5, balancer_rs=(0.05,),
                    select_counts=(), global_counts=(1, 2, 3, 4, 8), **APPS[app])
    rival = max(0.0, r["balancer 5%"]["mean"], r["sort only"]["mean"])
    best = 0.0
    for k, v in r.items():
        if k == "late switches":
            best = max(best, (v["gross"] - rival) / 1.0)
        elif k.startswith("selective: only the"):
            g = int(k.split("the ")[1].split(" ")[0])
            best = max(best, (v["gross"] - rival) * n / g)
    return a, best, r["late switches"]["gross"], rival


if __name__ == "__main__":
    print("\nPART 3: break-even electronics cost (per kWh nameplate, switch on every cell) for each car against a typical-current balancer (5%, cost 4), sort only and plain; 0 = cannot win at any cost")
    with Pool() as pool:
        out = pool.map(breakeven, [(c, a) for c in CARS for a in APPS])
    for a in APPS:
        v = [x[1] for x in out if x[0][1] == a]
        print(f"  {a:11s}: median {np.median(v):5.1f}, min {min(v):5.1f}, max {max(v):5.1f}; cars where break-even >= 8.8 (our assumed cost): {sum(x >= 8.8 for x in v)} of 12;  >= 4: {sum(x >= 4 for x in v)} of 12")
        print("     per car: " + ", ".join(f"{x[0][0][-1]}:{x[1]:.1f}" for x in out if x[0][1] == a))
