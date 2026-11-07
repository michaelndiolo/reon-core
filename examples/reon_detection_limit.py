"""DETECTION LIMIT of the permanent-bypass rule by INJECTING faults (pattern from Numair's simulated-fault evaluation, credited; participant results are self-reported, other domain).
Healthy cells: the 1,140 REAL cells (Nature Energy 2026 Fig 4), each as capacity / median of the others. Each cycle the controller sees that value plus measurement error (sigma = SENSING ACCURACY, UNKNOWN: ask REON, swept 0.5 to 4 %).
Rule: flag a cell as persistently weak when its observed capacity stays below (1 - weak_frac) of the others for N consecutive cycles. Reports, over 200 cycles: false-alarm rate on healthy real cells, and detection rate and delay for an injected weak cell at 0.85 / 0.80 / 0.70 of the others.
Run: PYTHONPATH=. python examples/reon_detection_limit.py"""
import csv
import numpy as np

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
healthy = np.concatenate([np.array([v[i] / np.median(np.delete(v, i)) for i in range(len(v))]) for v in map(np.array, car.values())])
rng = np.random.default_rng(7)
CYC = 200


def first_flag(true_rel, sigma, n_consec, weak_frac):
    """True_rel: array of cells (true relative capacity). Returns first cycle index at which each cell is flagged (CYC if never)."""
    obs = true_rel[:, None] * (1.0 + sigma * rng.standard_normal((len(true_rel), CYC)))
    low = obs < (1.0 - weak_frac)
    run = np.zeros(len(true_rel), int)
    first = np.full(len(true_rel), CYC)
    for t in range(CYC):
        run = np.where(low[:, t], run + 1, 0)
        hit = (run >= n_consec) & (first == CYC)
        first[hit] = t
    return first


print(f"{len(healthy)} real healthy cells; weak line = 15 % below the others; {CYC} cycles")
print("sigma(sensing)  N consecutive | false alarm per healthy cell | detect rate (delay in cycles) for injected weak cell at 0.85 / 0.80 / 0.70")
for sigma in (0.005, 0.01, 0.02, 0.04):
    for n in (1, 3, 5, 10):
        fa = np.mean(first_flag(healthy, sigma, n, 0.15) < CYC)
        out = []
        for d in (0.85, 0.80, 0.70):
            f = first_flag(np.full(2000, d), sigma, n, 0.15)
            ok = f < CYC
            out.append(f"{ok.mean() * 100:5.1f}% ({f[ok].mean() if ok.any() else float('nan'):4.1f})")
        print(f"{sigma * 100:8.1f} %  {n:12d} | {fa * 100:25.2f} %      | " + "   ".join(out))
