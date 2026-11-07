"""Hostile draws for the string-life simulation: fault rate, visit cost, fade spread, crew lead time, budget, switch loss all pushed to extremes.
Per draw, mean net over seeds for each policy. Reports where 'ours' loses to the best fixed threshold or to replace-on-failure, by how much, and why (worst-first).
usage: python examples/reon_events_adversary.py START COUNT"""
import sys, json, numpy as np
from hackkit import reon_events as E
POL = ("replace", "thr0.90", "thr0.85", "thr0.80", "ours", "ours+crew")

def draw(rng):
    return dict(lam=float(np.exp(rng.uniform(np.log(0.001), np.log(0.06)))), visit_cost=float(np.exp(rng.uniform(np.log(50), np.log(8000)))), fcv=float(rng.uniform(.1, .9)),
                fade=float(rng.uniform(.005, .05)), lead=float(rng.uniform(0, 6)), loss=float(rng.uniform(0, .1)), bypass_budget=int(rng.integers(1, 6)), start_cv=float(rng.uniform(0, .08)))

def main(a, k, seeds=6):
    out = []
    for i in range(a, a + k):
        kw = draw(np.random.default_rng(7000 + i))
        r = {p: float(np.mean([E.simulate(p, s, **kw)["net"] for s in range(seeds)])) for p in POL}
        thr = max(r["thr0.90"], r["thr0.85"], r["thr0.80"]); ours = max(r["ours"], r["ours+crew"])
        out.append(dict(i=i, **{x: round(v, 3) for x, v in kw.items()}, **{p: round(v, 1) for p, v in r.items()}, vs_thr=round(ours - thr, 1), vs_replace=round(ours - r["replace"], 1)))
    json.dump(out, open(f"examples/reon_events_adversary_{a}.jsonl", "w"))
    print(f"{a}-{a+k}: loses to best threshold {sum(o['vs_thr']<0 for o in out)}/{len(out)}, loses to replace {sum(o['vs_replace']<0 for o in out)}/{len(out)}")
if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
