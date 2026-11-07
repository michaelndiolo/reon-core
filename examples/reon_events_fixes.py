"""Fixes for the regimes where automatic bypass lost (cheap crew visits; bypass budget 1 with high switch loss). Same 400 hostile draws as reon_events_adversary.py.
Compares, on seeds the choice never saw (6..11 for scoring, choice made on 0..5):
  A  ours+crew only (the version that lost)
  B  bridge family: best of ours, ours+crew, ours+crew1, ours+crew2 chosen per site on separate seeds
  rivals: replace, best fixed threshold (threshold charged the same switch loss as ours, and also the old free-of-loss reading).
usage: python examples/reon_events_fixes.py START COUNT [free_thr]"""
import sys, json
import numpy as np
from multiprocessing import Pool
from hackkit import reon_events as E
from examples.reon_events_adversary import draw
THR = ("thr0.90", "thr0.85", "thr0.80")
FAM = ("ours", "ours+crew", "ours+crew1", "ours+crew2")

def one(args):
    i, free = args
    kw = draw(np.random.default_rng(7000 + i)); kw["thr_pays_loss"] = not free
    pick = {p: np.mean([E.simulate(p, s, **kw)["net"] for s in range(6)]) for p in FAM}
    b = max(pick, key=pick.get)
    sc = {p: float(np.mean([E.simulate(p, s, **kw)["net"] for s in range(6, 12)])) for p in E.EXTENDED}
    thr = max(sc[t] for t in THR)
    return dict(i=i, visit=kw["visit_cost"], budget=kw["bypass_budget"], loss=kw["loss"], A=sc["ours+crew"], B=sc[b], B_pick=b, replace=sc["replace"], thr=thr)

if __name__ == "__main__":
    a, k = int(sys.argv[1]), int(sys.argv[2]); free = len(sys.argv) > 3
    with Pool(4) as p:
        rows = p.map(one, [(i, free) for i in range(a, a + k)])
    json.dump(rows, open(f"examples/reon_events_fixes_{'free' if free else 'parity'}_{a}.jsonl", "w"))
    r = rows
    f = lambda m, rv: f"{100*np.mean([x[m] < x[rv] for x in r]):.0f}%"
    print(f"{'thr free of switch loss (old reading)' if free else 'thr pays same switch loss'}; {len(r)} hostile draws")
    print(f"  A ours+crew only : loses to replace {f('A','replace')}, to best threshold {f('A','thr')}")
    print(f"  B bridge family  : loses to replace {f('B','replace')}, to best threshold {f('B','thr')}")
    for name, sel in (("visit < 300", lambda x: x["visit"] < 300), ("budget 1 and loss > 6%", lambda x: x["budget"] == 1 and x["loss"] > .06), ("everything else", lambda x: x["visit"] >= 300 and not (x["budget"] == 1 and x["loss"] > .06))):
        s = [x for x in r if sel(x)]
        if s:
            print(f"  {name} (n={len(s)}): A loses replace {100*np.mean([x['A']<x['replace'] for x in s]):.0f}% thr {100*np.mean([x['A']<x['thr'] for x in s]):.0f}% | B loses replace {100*np.mean([x['B']<x['replace'] for x in s]):.0f}% thr {100*np.mean([x['B']<x['thr'] for x in s]):.0f}%  | B-replace median {np.median([x['B']-x['replace'] for x in s]):+.1f}")
    print("  B picks:", {n: sum(x['B_pick'] == n for x in r) for n in FAM})
