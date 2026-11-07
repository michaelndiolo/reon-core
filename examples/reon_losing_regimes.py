"""WORST CASES FIRST: where does the recommended build NOT beat the best rival, who beats it, and at what switch cost does the verdict flip? Run: PYTHONPATH=. python examples/reon_losing_regimes.py
Part 1: losing draws from the stress runs (examples/reon_hero_stress_*.jsonl): which rival wins and what we still deliver against the plain string.
Part 2: DECISION FLIP: break-even switch cost (per kWh nameplate, a switch on every cell) at which our best build stops beating the best rival, by value per kWh-year, fade-spread CV and voltage-floor loss. 'above 60' = never flips in range."""
import json, glob, collections
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W


def part1():
    rows = [json.loads(l) for f in glob.glob("examples/reon_hero_stress_*.jsonl") for l in open(f)]
    lose = [r for r in rows if r["margin"] <= 0]
    print(f"{len(rows)} stress draws, {len(lose)} where we do not beat the best rival ({100 * len(lose) / len(rows):.0f}%)")
    print("  winning rival:", dict(collections.Counter(r["rival_name"] for r in lose)))
    print("  our best build there:", dict(collections.Counter(r["ours_name"] for r in lose)))
    o = np.array([r["ours"] for r in lose])
    print(f"  in those draws our best build vs the PLAIN string: median {np.median(o):+.1f}, still positive in {100 * np.mean(o > 0.05):.0f}%")
    m = np.array([r["margin"] for r in lose])
    print(f"  size of the loss to the best rival: median {np.median(m):+.1f}, worst {m.min():+.1f} per kWh nameplate")


def margin(a):
    v, f, loss, e = a
    rng = np.random.default_rng(3)
    start = 100.0 * (1.0 + 0.02 * rng.standard_normal(16))
    o = W.recommend_build(start, 16, balancer_r=0.05, balancer_per_kwh=4.0, ks=(1, 2, 3, 4), fade_mean=0.02, fade_cv=f, loss=loss, electronics_per_kwh=e, sort_cost_per_kwh=0.0, value_per_kwh_year=v,
                          rate=0.07, years=12.0, eol_frac=0.7, duty=0.7, dod_exp=0.87, knee_share=0.65, start_soh=1.0, balancer_eta=0.9, closed_loss=0.0, test_sigma=0.02, trials=14, steps=40, seed=5)
    return o["margin"]


def flip(c):
    v, f, loss = c
    lo, hi = 1.0, 60.0
    if margin((v, f, loss, hi)) > 0:
        return c, None
    if margin((v, f, loss, lo)) <= 0:
        return c, 0.0
    for _ in range(6):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if margin((v, f, loss, mid)) > 0 else (lo, mid)
    return c, 0.5 * (lo + hi)


if __name__ == "__main__":
    part1()
    cells = [(v, f, l) for l in (0.02, 0.05) for v in (12.0, 22.0, 40.0, 80.0) for f in (0.2, 0.45, 0.6)]
    with Pool() as p:
        res = p.map(flip, cells)
    print("\nbreak-even switch cost vs the best rival (balancer 5 %, cost 4), per kWh nameplate; Tim Ren's range is 7 to 24")
    print("value/kWh-yr  fade CV   usable-energy loss 2 %   loss 5 % (voltage floor)")
    d = dict(res)
    for v in (12.0, 22.0, 40.0, 80.0):
        for f in (0.2, 0.45, 0.6):
            def s(x):
                return "above 60" if x is None else ("below 1" if x == 0.0 else f"{x:6.1f}")
            print(f"{v:9.0f} {f:9.2f}   {s(d[(v, f, 0.02)]):>20}   {s(d[(v, f, 0.05)]):>10}")
