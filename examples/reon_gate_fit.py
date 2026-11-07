"""GO / NO-GO GATE: can we predict, before running the engine, when switches will NOT beat the best rival? Tested on the 500 stress draws (examples/reon_hero_stress_*.jsonl). Run: PYTHONPATH=. python examples/reon_gate_fit.py
Gate A (break-even table): go when the switch cost is below the break-even for the nearest value and fade-spread cell of examples/reon_losing_regimes_output.txt (typical balancer only).
Gate B (logistic on the draw's inputs, including balancer strength and cost), trained on 70 % of draws and scored on the other 30 %, 30 random splits. Baseline: always say go."""
import json, glob
import numpy as np
from scipy.optimize import minimize

rows = [json.loads(l) for f in sorted(glob.glob("examples/reon_hero_stress_*.jsonl")) for l in open(f)]
y = np.array([r["margin"] > 0 for r in rows], float)
BE = {(12, .2): 16.2, (12, .45): 25.4, (12, .6): 29.1, (22, .2): 27.3, (22, .45): 42.9, (22, .6): 49.4, (40, .2): 45.7}
VALS, FCVS = (12, 22, 40, 80), (.2, .45, .6)


def be(r):
    v = min(VALS, key=lambda x: abs(np.log(x / r["value"])))
    f = min(FCVS, key=lambda x: abs(x - r["fcv"]))
    return BE.get((v, f), 60.0)


gateA = np.array([r["elec"] <= be(r) for r in rows], float)
X = np.array([[np.log10(r["value"]), r["fcv"], r["elec"], np.log10(r["r"]), np.log10(r["bcost"] + 1), r["loss"], r["start_cv"], r["fade"], r["years"]] for r in rows])


def fit(Xt, yt, lam=0.5):
    mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
    Z = np.c_[np.ones(len(Xt)), (Xt - mu) / sd]
    f = lambda w: -np.mean(yt * (Z @ w) - np.log1p(np.exp(Z @ w))) + lam * np.sum(w[1:] ** 2) / len(yt)
    w = minimize(f, np.zeros(Z.shape[1]), method="L-BFGS-B").x
    return lambda Xn: 1 / (1 + np.exp(-(np.c_[np.ones(len(Xn)), (Xn - mu) / sd] @ w))), w


rng = np.random.default_rng(0)
acc_b, acc_g, acc_a, miss = [], [], [], []
for _ in range(30):
    idx = rng.permutation(len(y)); cut = int(0.7 * len(y)); tr, te = idx[:cut], idx[cut:]
    p, _ = fit(X[tr], y[tr])
    pred = (p(X[te]) > 0.5).astype(float)
    acc_g.append(np.mean(pred == y[te])); acc_b.append(np.mean(y[te])); acc_a.append(np.mean(gateA[te] == y[te]))
    lose = y[te] == 0
    miss.append(np.mean(pred[lose] == 0) if lose.any() else np.nan)
print(f"{len(y)} draws, we beat the best rival in {100 * y.mean():.0f}%")
print(f"always 'go' (baseline):            accuracy {100 * np.mean(acc_b):.1f}%")
print(f"Gate A (break-even table):         accuracy {100 * np.mean(acc_a):.1f}% on all draws (no training)  [on all 500: {100 * np.mean(gateA == y):.1f}%]")
print(f"Gate B (logistic, hold-out):       accuracy {100 * np.mean(acc_g):.1f}% +/- {100 * np.std(acc_g):.1f}; catches {100 * np.nanmean(miss):.0f}% of the draws where we lose")
p, w = fit(X, y)
names = ["log10 value", "fade CV", "switch cost", "log10 balancer strength", "log10 balancer cost", "usable-energy loss", "start spread", "fade rate", "years"]
print("Gate B drivers (standardised weight, positive = helps us win):")
for n, c in sorted(zip(names, w[1:]), key=lambda t: -abs(t[1])):
    print(f"  {n:26s} {c:+.2f}")
