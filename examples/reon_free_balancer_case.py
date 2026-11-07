"""THE ONE CASE WE LOSE (a cheap balancer that can move 20%+ of a cell per cycle), and the well-matched tie. Run: PYTHONPATH=. python examples/reon_free_balancer_case.py
Part 1: what bypass-switch loss would we need to match or beat a FREE balancer (limit 20%, efficiency 90%)? Gross value (before hardware cost) of selective bypass on the weakest cell(s) vs the balancer, over the engaged-path loss.
A balancer loses (1 - eta) of the charge it MOVES (small: only the weak cells' shortfall); a bypass loses `loss` of ALL the energy that passes while engaged (large). So the loss number decides it.
Part 2: the ceiling on a well-matched pack (BMW): value of IDEAL control with no loss and no cost vs what each build captures.
Retired EV and grid applications, linear ageing (the simplest comparison), our full hardware 8.8 per kWh, selective k/m of it, closed-path loss 0."""
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W
from examples.reon_stress import PACKS, APPS


def job(a):
    pk, app, loss, eta = a
    c, m = PACKS[pk]
    A = APPS[app]
    ks = tuple(k for k in (1, 2, 3, 4) if k < m)
    r = W.wear_scan(c, m, fade_mean=A["fade"], fade_cv=0.2, loss=loss, electronics_per_kwh=8.8, balancer_per_kwh=0.0, sort_cost_per_kwh=0.0, value_per_kwh_year=A["value"], rate=0.07,
                    years=A["years"], eol_frac=A["eol"], balancer_rs=(0.2, 1e9), balancer_eta=eta, select_counts=ks, hybrid_counts=ks[:2], test_sigma=0.02, trials=20, steps=48, seed=5, start_soh=A["start"])
    return a, r


if __name__ == "__main__":
    jobs = [(pk, app, loss, eta) for pk in ("brief 16", "Leaf 8") for app in ("retired EV", "grid") for loss in (0.02, 0.01, 0.005, 0.002) for eta in (0.9,)]
    with Pool() as pool:
        res = dict(pool.map(job, jobs))
    print("PART 1: net value per kWh nameplate. Ours = best of selective / late / hybrid at that loss; rival = FREE balancer (20% limit) at efficiency 90%")
    print(f"{'pack':9s} {'application':11s} {'bypass loss':>11s} | {'ours (net)':>10s} {'which':30s} | {'bal 20% free':>12s} {'bal unl free':>12s} | margin vs bal 20%")
    for (pk, app, loss, eta), r in res.items():
        ours = {k: v for k, v in r.items() if k.startswith(("selective", "late", "hybrid"))}
        bo = max(ours, key=lambda k: ours[k]["mean"])
        b20, bu = r["balancer 20%"]["mean"], r["balancer unlimited"]["mean"]
        print(f"{pk:9s} {app:11s} {loss:11.1%} | {ours[bo]['mean']:+10.1f} {bo:30s} | {b20:+12.1f} {bu:+12.1f} | {ours[bo]['mean'] - b20:+.1f}")
    # part 2: ceiling on the well-matched pack
    c, m = PACKS["BMW 36"]
    print(f"\nPART 2: BMW 36 cells, weakest/mean {c.min() / c.mean():.3f}: ideal gain at day 1 {c.mean() / c.min() - 1:.1%}")
    for app in ("retired EV", "grid", "data-center"):
        A = APPS[app]
        ks = (1, 2, 3, 4)
        r = W.wear_scan(c, m, fade_mean=A["fade"], fade_cv=0.2, loss=0.0, electronics_per_kwh=0.0, balancer_per_kwh=0.0, sort_cost_per_kwh=0.0, value_per_kwh_year=A["value"], rate=0.07,
                        years=A["years"], eol_frac=A["eol"], balancer_rs=(1e9,), balancer_eta=1.0, select_counts=ks, test_sigma=0.02, trials=20, steps=48, seed=5, start_soh=A["start"])
        r2 = W.wear_scan(c, m, fade_mean=A["fade"], fade_cv=0.2, loss=0.02, electronics_per_kwh=8.8, balancer_per_kwh=0.0, sort_cost_per_kwh=0.0, value_per_kwh_year=A["value"], rate=0.07,
                         years=A["years"], eol_frac=A["eol"], balancer_rs=(0.05,), balancer_eta=0.9, select_counts=ks, global_counts=(1, 2), test_sigma=0.02, trials=20, steps=48, seed=5, start_soh=A["start"])
        print(f"  {app:11s} ceiling (ideal control, no loss, no cost) gross {r['late switches']['gross']:+.1f}; sort only gross {r2['sort only']['gross']:+.1f}; "
              f"selective 1/12 per string net {r2['selective 1/12 cells']['mean']:+.1f}; ONLY the weakest cell of the pack (one switch) net {r2['selective: only the 1 weakest cell of the pack']['mean']:+.1f}, two cells {r2['selective: only the 2 weakest cells of the pack']['mean']:+.1f}; full late net {r2['late switches']['mean']:+.1f}")
