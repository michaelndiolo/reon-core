"""COST TO WIN: the most our switch electronics may cost (per kWh nameplate) and still beat every rival, by application, day-1 spread and ageing model. Run: PYTHONPATH=. python examples/reon_wear_cost_to_win.py
Same packs as reon_wear_regimes.py (24 cells, 3 strings of 8, 40 trials). For each case: break-even electronics cost = gross value of our late switches - max(0, sort-only net, best balancer net), with the balancer
free and costing 4. Balancer transfer limits: 10%, 20%, 50% of a cell's capacity per cycle (current x hours / cell Ah: a 10 A balancer, the Analog Devices LTC3300-1 figure, moves 10% of a 100 Ah cell per hour of idle
time) and unlimited. 'ours wins at 8.8' = our electronics at the assumed 8.8 per kWh. Ageing: A linear (as reon_design); C = DoD^0.8 wear + knees (Iowa). ASSUMED: duty 0.7, balancer cost, 8.8."""
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

APPS = {"retired EV": dict(value_per_kwh_year=22.0, years=7.0, eol_frac=0.7, fade_mean=0.01, start_soh=0.8),
        "grid": dict(value_per_kwh_year=12.0, years=15.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0),
        "data-center": dict(value_per_kwh_year=8.0, years=12.0, eol_frac=0.8, fade_mean=0.005, start_soh=1.0)}
DYN = {"A linear": dict(dod_exp=0.0, knee_share=0.0), "C wear+knees": dict(dod_exp=0.8, knee_share=0.65)}
CVS = (0.02, 0.05, 0.10, 0.15)
RS = (0.1, 0.2, 0.5, 1e9)


def job(a):
    app, dyn, cv = a
    rng = np.random.default_rng(11)
    caps = np.maximum(rng.normal(90, cv * 90, 24), 20)
    return a, W.wear_scan(caps, 8, fade_cv=0.2, loss=0.02, electronics_per_kwh=0.0, balancer_per_kwh=0.0, sort_cost_per_kwh=0.0, rate=0.07, duty=0.7, trials=40, seed=5,
                          balancer_rs=RS, **APPS[app], **DYN[dyn])


if __name__ == "__main__":
    with Pool() as p:
        res = dict(p.map(job, [(a, d, c) for a in APPS for d in DYN for c in CVS]))
    for bal in (0.0, 4.0):
        print(f"\n######## balancer costs {bal:g} per kWh nameplate. Break-even electronics cost for our late switches (negative = cannot win even if free) ########")
        print(f"{'application':12s} {'ageing':13s} {'cv':>5s} | " + "  ".join(f"vs bal {('unl' if r > 1e6 else format(r, '.0%')):>4s}" for r in RS) + " | vs sort only | wins at 8.8 against")
        for app in APPS:
            for dyn in DYN:
                for cv in CVS:
                    r = res[(app, dyn, cv)]
                    gl = r["late switches"]["gross"]
                    gs = r["sort only"]["gross"]
                    cells, wins = [], []
                    for rr in RS:
                        nm = f"balancer {('unlimited' if rr > 1e6 else format(rr, '.0%'))}"
                        be = gl - max(0.0, gs, r[nm]["gross"] - bal)
                        cells.append(f"{be:9.1f}")
                        if be >= 8.8:
                            wins.append("unl" if rr > 1e6 else format(rr, ".0%"))
                    print(f"{app:12s} {dyn:13s} {cv:5.0%} | " + "  ".join(f"{c:>9s}" for c in cells) + f" | {gl - max(0.0, gs):12.1f} | {', '.join(wins) or 'nothing'}")
