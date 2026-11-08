"""Does the policy ever lose to a balancer or to doing nothing? Picks the build on seed A, then scores the pick, the balancer and plain on two fresh seeds (B, C) with more trials.
Policies compared: old (best of everything by mean on A, hybrid without the exemption), plain-exempt (same rule, exempt hybrid), guarded (paired z rule, exempt hybrid).
Regret = max(0, balancer gain, 0) minus the pick's gain, on the fresh seeds (positive = the pick lost to the better rival). Resumable: results merge into examples/data/policy_eval.json.
usage: PYTHONPATH=. python examples/reon_policy_eval.py P FADE[,FADE..] R[,R..] VALUE[,VALUE..]      (about 20 s per scenario per core)"""
import datetime
import json
import sys
from multiprocessing import Pool

import numpy as np

from hackkit import reon_policy as POL
from hackkit import reon_storefront as SF
from hackkit import reon_wear as W

PATH = "examples/data/policy_eval.json"
KS = (1, 2, 4, 8, 16, 25)


def base_kw(p, fade, value):
    kw = SF._kw(p, fade, value, SF.ELEC, 12.0, SF.N_SERIES)
    kw.pop("ks"); kw.pop("trials")
    kw.update(steps=40, balancer_eta=0.9, dod_exp=0.87, knee_share=0.65, duty=0.7, rate=0.07, sort_cost_per_kwh=0.0, test_sigma=0.02)
    return kw


def scan(start, kw, r, seed, trials, exempt):   # exempt=True also switches on the adaptive hybrid (a switch on every cell)
    return W.wear_scan(start, SF.N_SERIES, balancer_rs=(r,), balancer_per_kwh=4.0, select_counts=KS, global_counts=(), hybrid_counts=KS, hybrid_shares_wear=True, hybrid_exempt=exempt, adaptive_hybrid=exempt,
                       return_trials=True, trials=trials, seed=seed, **kw)


def best_by_mean(res):
    ours = {k: v for k, v in res.items() if k.startswith(POL.OURS)}
    riv = {k: v for k, v in res.items() if k in ("plain",) or k.startswith("balancer")}
    bo = max(ours, key=lambda k: ours[k]["mean"]); br = max(riv, key=lambda k: riv[k]["mean"])
    return bo if ours[bo]["mean"] > riv[br]["mean"] else br


def job(a):
    p, fade, r, value = a
    kw = base_kw(p, fade, value)
    start = SF._start(p, SF.N_SERIES)
    bname = f"balancer {r:.1%}".replace(".0%", "%")
    out = {}
    for exempt, label in ((False, "old"), (True, "unguarded")):
        A = scan(start, kw, r, 5, 16, exempt)
        pick = best_by_mean(A)
        out[label] = dict(pick=pick)
        out[label]["fresh"] = {}
        for sd in (11, 17):
            out[label]["fresh"][sd] = None  # filled below
        out[label]["_A"] = None
    # fresh scoring: one scan per exempt flag per seed, reused for the picks of every policy
    guarded = POL.guarded_recommend(start, SF.N_SERIES, balancer_r=r, trials=16, seed=5, ks=KS, **{k: kw[k] for k in ("value_per_kwh_year", "electronics_per_kwh", "fade_cv", "fade_mean", "loss", "years", "eol_frac", "closed_loss", "window", "steps")}, z=1.0)
    picks = {"old": out["old"]["pick"], "unguarded": out["unguarded"]["pick"], "guarded": guarded["build"]}
    exflag = {"old": False, "unguarded": True, "guarded": True}
    score = {k: [] for k in picks}; bal = {k: [] for k in picks}; best_alt = []
    for sd in (11, 17):
        F = {False: scan(start, kw, r, sd, 32, False), True: scan(start, kw, r, sd, 32, True)}
        for k, nm in picks.items():
            f = F[exflag[k]]
            net = np.asarray(f[nm]["net"]); b = np.asarray(F[exflag[k]][bname]["net"])
            score[k].append(float(net.mean())); bal[k].append(float(b.mean()))
        best_alt.append(max(float(np.asarray(F[True][nm]["net"]).mean()) for nm in F[True] if nm.startswith(POL.OURS)))
    res = {}
    for k in picks:
        g = float(np.mean(score[k])); b = float(np.mean(bal[k]))
        res[k] = dict(pick=picks[k], gain=g, balancer=b, regret=float(max(0.0, b, 0.0) - g), vs_balancer=g - b)
    res["guarded"]["verdict"] = guarded["verdict"]
    res["best_ours_hindsight"] = float(np.mean(best_alt))
    return f"{int(p)}|{fade:.4f}|{r:.3f}|{value:g}", res


if __name__ == "__main__":
    p = int(sys.argv[1]); fades = [float(x) for x in sys.argv[2].split(",")]; rs = [float(x) for x in sys.argv[3].split(",")]; vals = [float(x) for x in sys.argv[4].split(",")]
    jobs = [(p, f, r, v) for f in fades for r in rs for v in vals]
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    try:
        data = json.load(open(PATH))
    except (OSError, ValueError):
        data = {"cases": {}}
    data["cases"].update(dict(res)); data["generated"] = datetime.date.today().isoformat()
    json.dump(data, open(PATH, "w"), indent=1, sort_keys=True)
    print(len(data["cases"]), "cases saved;", len(res), "just computed")
