"""Run: PYTHONPATH=. python examples/reon_adversary_vs_guard.py 4   (the next 4 draws not yet done; resumable, about 45 s per 4)
Aaryan's adversary cases (hackkit/reon_adversary.py) against OUR guarded policy (reon_policy), scored on fresh, more-trials scans.
Policy picks on draw.seed + 5000 with 16 trials; the score is the same pick on the draw's own seed with 24 trials (paired fades with the baselines).
Rivals: plain (0), 2.5% balancer, 5% balancer (the policy is run once per balancer strength, as the customer's baseline). Informational: the hindsight best of everything (his harness's baseline)."""
import json, sys, os
from multiprocessing import Pool
import numpy as np
from hackkit import reon_adversary as A
from hackkit import reon_policy as POL

OUT = "examples/data/adversary_vs_guard.json"
SEEDS = (0, 1)


def my_table(draw):
    # his Draw.table() scan without my two extra designs (exempt hybrid, adaptive hybrid); same start, fades and seed, so every shared build has identical numbers
    from hackkit import reon_wear as W
    kw = dict(A.BASE_KW, **draw.kw)
    n = len(draw.start)
    ks = tuple(k for k in A.KS if k < n)
    return W.wear_scan(draw.start, n, balancer_rs=(A.BAL_WEAK, A.BAL_STRONG), select_counts=ks, hybrid_counts=ks, seed=draw.seed, hybrid_exempt=True, adaptive_hybrid=True, **kw)


def policy(draw, r, t):
    kw = dict(A.BASE_KW, **draw.kw)
    pk = POL.guarded_recommend(draw.start, A.N_SERIES, value_per_kwh_year=kw["value_per_kwh_year"], electronics_per_kwh=kw["electronics_per_kwh"], fade_cv=kw["fade_cv"], fade_mean=kw["fade_mean"],
                               loss=kw["loss"], years=kw["years"], eol_frac=kw["eol_frac"], closed_loss=kw["closed_loss"], window=kw["window"], steps=kw["steps"], weak_corr=kw.get("weak_corr", 0.0),
                               test_sigma=kw["test_sigma"], balancer_r=r, balancer_per_kwh=kw["balancer_per_kwh"], balancer_eta=kw["balancer_eta"], ks=A.KS, trials=16, seed=draw.seed + 5000, min_margin=1.0)
    nm = pk["build"]
    return pk["verdict"], nm, (0.0 if nm == "plain" else float(t[nm]["mean"]))


def job(a):
    name, seed = a
    d = A.default_cases(parallels=(1, 4, 16))[name](seed)
    d.kw = dict(d.kw, trials=24)
    t = my_table(d)
    d._table = t
    rivals = {"plain": 0.0, "balancer 2.5%": t[A._bal_name(A.BAL_WEAK)]["mean"], "balancer 5%": t[A._bal_name(A.BAL_STRONG)]["mean"]}
    hind = max(max(rivals.values()), A._pick(t, ("late", "level", "selective")), A._pick(t, ("hybrid",)))
    out = dict(case=name, seed=seed, hindsight=float(hind))
    for r, rn in ((A.BAL_STRONG, "balancer 5%"), (A.BAL_WEAK, "balancer 2.5%")):
        try:
            v, nm, g = policy(d, r, t)
            out[rn] = dict(verdict=v, build=nm, gain=g, rival=float(max(0.0, rivals[rn])), regret=float(max(0.0, rivals[rn]) - g), regret_hindsight=float(hind - g))
        except Exception as e:
            out[rn] = dict(error=f"{type(e).__name__}: {e}"[:160], regret=99.0)
    return f"{name}|{seed}", out


if __name__ == "__main__":
    allj = [(n, s) for n in A.default_cases(parallels=(1, 4, 16)) for s in SEEDS]
    try:
        done = json.load(open(OUT))
    except (OSError, ValueError):
        done = {}
    todo = [j for j in allj if f"{j[0]}|{j[1]}" not in done]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    batch = todo[:n]
    print(len(todo), "left before this call")
    with Pool(4) as pool:
        for k, v in pool.map(job, batch):
            done[k] = v
    json.dump(done, open(OUT, "w"), indent=1)
    print("done", len(done), "of", len(allj))
