"""Stress test for the guarded policy: random scenarios across every input we are unsure of, pick on seed 5, score on a fresh seed with more trials.
A scenario is a failure when the pick earns less than the better of 'balancer alone' and 'plain' by more than 0.5 per kWh (regret). Writes/merges examples/data/policy_fuzz.json.
usage: PYTHONPATH=. python examples/reon_policy_fuzz.py SEED N      (about 25 s per scenario per core, 4 cores)"""
import datetime
import json
import sys
from multiprocessing import Pool

import numpy as np

from hackkit import reon_policy as POL
from hackkit import reon_wear as W

PATH = "examples/data/policy_fuzz.json"
N = 250
KS = (1, 2, 4, 8, 16, 25)


def draw(rng):
    p = int(rng.choice([1, 2, 4, 8, 16, 40]))
    return dict(p=p, fade=float(np.exp(rng.uniform(np.log(0.002), np.log(0.03)))), r=float(np.exp(rng.uniform(np.log(0.005), np.log(0.3)))), value=float(np.exp(rng.uniform(np.log(8), np.log(100)))),
                elec=float(rng.uniform(7, 24)), loss=float(rng.uniform(0.0, 0.10)), closed=float(rng.uniform(0.0, 0.04)), cvk=float(rng.uniform(0.3, 0.6)), spread=float(rng.uniform(0.005, 0.05)),
                window=float(rng.choice([0.8, 0.9, 0.95])), bal_cost=float(rng.uniform(2, 8)), eta=float(rng.uniform(0.8, 0.97)), knee=float(rng.choice([0.0, 0.65])), g=float(rng.choice([0.0, 0.6, 0.87])),
                years=float(rng.choice([8.0, 12.0])), sid=int(rng.integers(1, 10**6)))


def job(sc):
    rng = np.random.default_rng(sc["sid"])
    start = 100.0 * (1.0 + sc["spread"] / np.sqrt(sc["p"]) * rng.standard_normal(N))
    kw = dict(value_per_kwh_year=sc["value"], electronics_per_kwh=sc["elec"], fade_cv=sc["cvk"] / np.sqrt(sc["p"]), fade_mean=sc["fade"], loss=sc["loss"], years=sc["years"], eol_frac=0.7, closed_loss=sc["closed"],
              window=sc["window"], steps=40, balancer_eta=sc["eta"], balancer_per_kwh=sc["bal_cost"], dod_exp=sc["g"], knee_share=sc["knee"])
    try:
        g = POL.guarded_recommend(start, N, balancer_r=sc["r"], trials=16, seed=5, ks=KS, z=1.0, **{k: kw[k] for k in kw if k not in ("balancer_per_kwh", "balancer_eta")}, balancer_per_kwh=sc["bal_cost"], balancer_eta=sc["eta"])
        wkw = dict(kw); wkw.pop("balancer_per_kwh"); wkw["rate"] = 0.07; wkw["duty"] = 0.7; wkw["sort_cost_per_kwh"] = 0.0; wkw["test_sigma"] = 0.02
        gains = []; bals = []
        for sd in (11, 17):
            f = W.wear_scan(start, N, balancer_rs=(sc["r"],), balancer_per_kwh=sc["bal_cost"], select_counts=KS, global_counts=(), hybrid_counts=KS, hybrid_shares_wear=True, hybrid_exempt=True, adaptive_hybrid=True,
                            return_trials=True, trials=24, seed=sd, **wkw)
            gains.append(float(np.mean(f[g["build"]]["net"]))); bals.append(float(np.mean(f[g["rival"] if g["rival"] != "plain" else f"balancer {sc['r']:.1%}".replace('.0%', '%')]["net"])) if False else None)
            bn = [k for k in f if k.startswith("balancer")][0]
            bals[-1] = float(np.mean(f[bn]["net"]))
        gain = float(np.mean(gains)); bal = float(np.mean(bals))
        return str(sc["sid"]), dict(sc, build=g["build"], verdict=g["verdict"], gain=gain, balancer=bal, regret=float(max(0.0, bal) - gain), ok=True)
    except Exception as e:   # a crash is a failure too
        return str(sc["sid"]), dict(sc, ok=False, error=f"{type(e).__name__}: {e}"[:200], regret=99.0)


if __name__ == "__main__":
    seed, n = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(seed)
    scs = [draw(rng) for _ in range(n)]
    with Pool(4) as pool:
        res = pool.map(job, scs)
    try:
        data = json.load(open(PATH))
    except (OSError, ValueError):
        data = {"cases": {}}
    data["cases"].update(dict(res)); data["generated"] = datetime.date.today().isoformat()
    json.dump(data, open(PATH, "w"), indent=1, sort_keys=True)
    bad = [v for _, v in res if v["regret"] > 0.5]
    print(len(data["cases"]), "cases saved;", len(res), "just run;", len(bad), "with regret > 0.5")
