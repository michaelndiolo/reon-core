"""Policy stress test on fresh paired draws (seeds 20_000+, never used elsewhere in the repo). Writes examples/data/policy_stress.json.

Pass lines (fixed before running):
 1. regret vs the best of {plain, 2.5% balancer, 5% balancer, switches alone, hybrid} never above $0.50/kWh in any scenario (fade 0.4 / 0.8 / 1.2 / 2.0 %/yr x 1 or 4 cells per position);
 2. typical wear (0.8 %/yr), 1 cell per position: mean gain over the 5% balancer > $3/kWh over >= 200 paired draws, 95% CI excluding $3;
 3. voltage floor with sag (hackkit/reon_sag): reported at floor 0.9 and 0.8, current 33.3 A and 5.6 A.
usage: PYTHONPATH=. python examples/reon_policy_stress.py [N_TYPICAL=200] [N_OTHER=60] [N_SAG=40]   (about 10 min on 8 cores at the defaults)"""
import datetime
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

from hackkit import reon_policy_stress as R

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policy_stress.json")
SEED0 = 20_000
SCEN = [(1, 0.008), (1, 0.004), (1, 0.012), (1, 0.02), (4, 0.004), (4, 0.008), (4, 0.012), (4, 0.02)]
GUARD_MARGIN = 0.5
IN_SAMPLE_TRIALS = 4
E_KEEP = ("e. switches 8 fitted yr 6 by projected + bal 5%", "e. switches 25 fitted yr 6 by projected + bal 5%", "e. switches 25 fitted yr 3+6+9 by projected + bal 5%",
          "e. switches 25 fitted yr 6 by reading + bal 5%")


def policy_sets(sc):
    base = R.baselines(sc)
    cand = R.candidates(sc) + [p for p in R.candidates(sc, bal_cost_scaled=True) if p["group"] == "d"]
    e = [p for p in R.deferred(sc, plans=((6.0,), (3.0, 6.0, 9.0)), ks=(8, 25)) if p["name"] in E_KEEP]
    return base, cand, e


def job(a):
    p, fade, seed = a
    sc = R.scenario(p, fade)
    base, cand, e = policy_sets(sc)
    dr = R.draw(seed, sc)
    v = R.net_values(base + cand + e, dr, sc)
    _, acc = R.in_sample_choice(base + cand + e, dr, sc, IN_SAMPLE_TRIALS)   # decision-time information only: day-1 test + prior
    names = lambda ps: [x["name"] for x in ps]
    b_pool = ["balancer 5%"] + [x["name"] for x in base if x["group"] == "hybrid"]
    pick_b = max(b_pool, key=acc.get)
    bn = max(names(base), key=acc.get)
    in_scope = names(cand)
    cn = max(in_scope, key=acc.get)
    pick_g = cn if acc[cn] > acc[bn] + GUARD_MARGIN else bn
    cn_e = max(in_scope + names(e), key=acc.get)
    pick_ge = cn_e if acc[cn_e] > acc[bn] + GUARD_MARGIN else bn
    v["b. per-pack k + bal 5% (in-sample)"] = v[pick_b]
    v["GUARDED (a-d)"] = v[pick_g]
    v["GUARDED (a-e, e assumed hardware)"] = v[pick_ge]
    return (p, fade), seed, v, dict(b=pick_b, g=pick_g, ge=pick_ge)


def sag_job(a):
    fl, cur, seed = a
    sc = R.scenario(1, 0.008)
    base, cand, e = policy_sets(sc)
    keep = {"plain", "balancer 2.5%", "balancer 5%", "late switches", "selective 25/250 cells", "hybrid 1/250 + balancer 5%", "hybrid 8/250 + balancer 5%",
            "c. rotating rest, hybrid 8 + bal 5%, x0.8", "d. hybrid 1 + bal 2.5%"} | set(E_KEEP)
    pols = [x for x in base + cand + e if x["name"] in keep]
    efn = R.sag_energy_fn(v_floor_frac=fl, current_a=cur, closed_loss=sc["closed_loss"])
    dr = R.draw(seed, sc)
    return (fl, cur), seed, R.net_values(pols, dr, sc, energy_fn=efn), R.net_values(pols, dr, sc), {x["name"]: x["group"] for x in pols}


def summarize(rows, sc):
    base, cand, e = policy_sets(sc)
    vals = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    b5 = vals["balancer 5%"]
    out = {}
    for k, x in vals.items():
        rg = R.regret(x, vals, base)
        out[k] = dict(mean=float(x.mean()), gain_vs_bal5=R.mean_ci(x - b5), regret=rg["scenario"], regret_oracle=rg["oracle_mean"], best_baseline=rg["best_baseline"])
    return out


if __name__ == "__main__":
    n_typ = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    n_oth = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    n_sag = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    jobs = [(p, f, SEED0 + i) for (p, f) in SCEN for i in range(n_typ if (p, f) == (1, 0.008) else n_oth)]
    with Pool(min(6, os.cpu_count() or 4)) as pool:
        res = pool.map(job, jobs, chunksize=2)
        sag = []
        if R.sag_energy_fn() is not None:
            sag = pool.map(sag_job, [(fl, cur, SEED0 + 50_000 + i) for fl in (0.9, 0.8) for cur in (33.3, 5.6) for i in range(n_sag)], chunksize=2)
    by = {}
    picks = {}
    for key, seed, v, pk in res:
        by.setdefault(key, []).append(v)
        picks.setdefault(key, []).append(pk)
    scen = {}
    for (p, f), rows in by.items():
        sc = R.scenario(p, f)
        s = summarize(rows, sc)
        from collections import Counter
        scen[f"p{p}|fade{f:.3f}"] = dict(n=len(rows), policies=s, picks={w: dict(Counter(x[w] for x in picks[(p, f)]).most_common(4)) for w in ("b", "g", "ge")})
    sag_out = {}
    for key in sorted({k for k, *_ in sag}):
        rows = [(vs, vw, g) for k, _s, vs, vw, g in sag if k == key]
        groups = rows[0][2]
        names = list(rows[0][0])
        sv = {k: np.array([r[0][k] for r in rows]) for k in names}
        wv = {k: np.array([r[1][k] for r in rows]) for k in names}
        best_base = max((k for k in names if groups[k] in ("plain", "balancer 2.5%", "balancer 5%", "switches alone", "hybrid")), key=lambda k: sv[k].mean())
        sag_out[f"floor{key[0]}|I{key[1]}"] = dict(n=len(rows), best_baseline_sag=best_base, policies={k: dict(sag=R.mean_ci(sv[k] - sv["balancer 5%"]), window=R.mean_ci(wv[k] - wv["balancer 5%"]),
                                                                                                         sag_regret=float(max(0.0, sv[best_base].mean() - sv[k].mean()))) for k in names})
    data = dict(generated=datetime.date.today().isoformat(), seeds=f"{SEED0}+ (sag {SEED0 + 50_000}+)", guard_margin=GUARD_MARGIN, in_sample_trials=IN_SAMPLE_TRIALS, scenarios=scen, sag=sag_out,
                note="Net $/kWh nameplate vs plain, 12-year PV, value 40, switches 15.5, balancer 4 (flat; 'cost scaled' rows assume 4 x r/5%), window 0.9 (sag rows replace the energy per discharge "
                     "with reon_sag.usable_fraction via an ASSUMED mapping). Regret = max(0, best baseline-group mean (picked in hindsight) - policy mean). e-policies are retrofit hardware with "
                     "retrofit fee 0 (ASSUMED). See docs/stress/policy_assumptions.md.")
    json.dump(data, open(PATH, "w"), indent=1, sort_keys=True)
    t = scen["p1|fade0.008"]["policies"]
    print(f"{'policy':58s} {'gain vs bal5 (CI)':>24s} {'worst regret':>12s}")
    for k in t:
        wr = max(scen[s]["policies"][k]["regret"] for s in scen)
        g = t[k]["gain_vs_bal5"]
        print(f"{k:58s} {g['mean']:7.2f} [{g['lo']:6.2f},{g['hi']:6.2f}] n={g['n']:3d} {wr:9.2f}")
    for s, d in sag_out.items():
        print(s, "best baseline:", d["best_baseline_sag"])
        for k, x in d["policies"].items():
            print(f"   {k:56s} sag {x['sag']['mean']:7.2f} [{x['sag']['lo']:6.2f},{x['sag']['hi']:6.2f}]  window {x['window']['mean']:7.2f}  sag regret {x['sag_regret']:.2f}")
