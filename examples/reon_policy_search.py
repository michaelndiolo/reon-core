"""TUNE THE POLICY, THEN TRY TO BREAK IT: grid search over the bypass rule's settings (weak line, persistence, crew trigger, bypass budget) on TRAIN seeds, then score the best on HOLD-OUT seeds the search never saw, against the defaults and against detect-and-replace.
Objective: mean net value per kWh nameplate over 9 scenarios (fault rate 0.002 / 0.01 / 0.03 x visit cost 300 / 1000 / 3000, ASSUMED). Run: PYTHONPATH=. python examples/reon_policy_search.py"""
import itertools, sys
from multiprocessing import Pool
import numpy as np
from hackkit import reon_events as E

SCEN = [(lam, v) for lam in (0.002, 0.01, 0.03) for v in (300.0, 1000.0, 3000.0)]
GRID = list(itertools.product((0.80, 0.85, 0.90), (2, 3, 5), (1, 2, 3, 4), (2, 4, 6)))
DEFAULT = (0.85, 3, 3, 4)


def score(a):
    (wl, per, crew, bud), seeds, pol = a
    nets = []
    for lam, v in SCEN:
        nets.append(np.mean([E.simulate(pol, s, lam=lam, visit_cost=v, lead=1.0, weak_line=wl, persist=per, crew_at=crew, bypass_budget=bud)["net"] for s in seeds]))
    return float(np.mean(nets)), float(np.min(nets))


def replace_score(seeds):
    return float(np.mean([np.mean([E.simulate("replace", s, lam=lam, visit_cost=v, lead=1.0)["net"] for s in seeds]) for lam, v in SCEN]))


if __name__ == "__main__":
    train, test = range(0, 25), range(1000, 1060)
    with Pool() as p:
        tr = p.map(score, [(g, train, "ours+crew") for g in GRID])
    robust = len(sys.argv) > 1 and sys.argv[1] == "robust"           # robust: rank by the WORST scenario (then the mean) instead of the mean
    order = sorted(range(len(GRID)), key=lambda i: (-tr[i][1], -tr[i][0]) if robust else -tr[i][0])
    print("top 5 on TRAIN (" + ("ranked by worst scenario" if robust else "ranked by mean") + "; mean net, worst scenario):")
    for i in order[:5]:
        print("  weak line %.2f, persist %d, crew at %d bypassed, budget %d: %.1f (worst %.1f)" % (*GRID[i], *tr[i]))
    cand = [GRID[i] for i in order[:5]] + [DEFAULT]
    with Pool() as p:
        te = p.map(score, [(g, test, "ours+crew") for g in cand])
    rep = replace_score(test)
    print(f"\nHOLD-OUT (60 new seeds): detect-and-replace {rep:.1f}")
    for g, (m, w) in zip(cand, te):
        tag = "  <- default" if g == DEFAULT else ""
        print("  weak line %.2f, persist %d, crew at %d, budget %d: %.1f (worst scenario %.1f), vs replace %+.1f%s" % (*g, m, w, m - rep, tag))
    best = max(range(5), key=lambda i: (te[i][1] if robust else te[i][0]))
    print(f"\nbest train setting on hold-out: {cand[best]} = mean {te[best][0]:.1f}, worst {te[best][1]:.1f}; default = mean {te[5][0]:.1f}, worst {te[5][1]:.1f}")
