"""Adversarial stress: draw hostile conditions, ask the robust verdict (BUY/HOLD/PLAIN), then score the pick on a THIRD, unseen seed with more trials.
A false BUY = verdict BUY but the pick loses money vs plain, or has worse p10, on the unseen seed. Goal: false BUY rate near zero.
usage: python examples/reon_adversary.py START COUNT   (chunks fit the 120 s limit)"""
import sys, json, numpy as np
from hackkit import reon_guard as G

def hostile(rng):
    n = 16
    kind = rng.choice(["tight", "wide", "bimodal", "one_dead", "one_hot", "all_equal", "ramp"])
    base = 100.0
    if kind == "tight": c = base * (1 + 0.01 * rng.standard_normal(n))
    elif kind == "wide": c = base * (1 + 0.12 * rng.standard_normal(n))
    elif kind == "bimodal": c = base * np.where(rng.random(n) < .5, 1.0, rng.uniform(.6, .85))
    elif kind == "one_dead": c = base * (1 + 0.02 * rng.standard_normal(n)); c[rng.integers(n)] = base * rng.uniform(.05, .4)
    elif kind == "one_hot": c = base * (1 + 0.02 * rng.standard_normal(n)); c[rng.integers(n)] = base * rng.uniform(1.2, 1.6)
    elif kind == "all_equal": c = np.full(n, base)
    else: c = base * np.linspace(.7, 1.0, n)
    c = np.clip(c, 1.0, None)
    p = dict(value_per_kwh_year=float(np.exp(rng.uniform(np.log(3), np.log(150)))), electronics_per_kwh=float(rng.uniform(0, 45)),
             fade_cv=float(rng.uniform(0.0, 0.9)), loss=float(rng.uniform(0, 0.12)), years=float(rng.uniform(3, 20)), eol_frac=float(rng.choice([.6, .7, .8])),
             duty=float(rng.uniform(.2, 1.0)), rate=float(rng.uniform(0, .15)), trials=10, steps=32)
    return kind, c, p

def main(a, k):
    out = []
    for i in range(a, a + k):
        rng = np.random.default_rng(1000 + i)
        kind, c, p = hostile(rng)
        try:
            r = G.robust_recommend(c, 16, seeds=(5 + i, 500 + i), **p)
            fresh, _ = G.safe_recommend(c, 16, seed=9000 + i, **{**p, "trials": 24})
        except ValueError as e:
            out.append(dict(i=i, kind=kind, error=str(e))); continue
        t = fresh["table"]; nm = r["build"]
        d = t[nm]["mean"] - t["plain"]["mean"] if nm in t else 0.0
        d10 = t[nm]["p10"] - t["plain"]["p10"] if nm in t else 0.0
        out.append(dict(i=i, kind=kind, verdict=r["verdict"], build=nm, fresh_gain=float(d), fresh_p10=float(d10), **{x: round(p[x], 3) for x in ("value_per_kwh_year", "electronics_per_kwh", "fade_cv")}))
    json.dump(out, open(f"examples/reon_adversary_{a}.jsonl", "w"))
    buy = [o for o in out if o.get("verdict") == "BUY"]
    fb = [o for o in buy if o["fresh_gain"] < 0 or o["fresh_p10"] < -0.10 * max(o["fresh_gain"], 0)]   # wider than the verdict tolerance (5%): not tuned to the metric
    print(f"{a}-{a+k}: {len(out)} runs, errors {sum('error' in o for o in out)}, BUY {len(buy)}, false BUY {len(fb)}, HOLD {sum(o.get('verdict')=='HOLD' for o in out)}, PLAIN {sum(o.get('verdict')=='PLAIN' for o in out)}")
    for o in fb[:5]: print("  false BUY:", o)

main(int(sys.argv[1]), int(sys.argv[2]))
