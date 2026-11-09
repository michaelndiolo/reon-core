"""REON (7 Nov): per-cell capacity/SOH sensing is 'within 5%, often much better'. What does that do to the weak-cell line (reon_response.Limits.weak_frac)?
Real late-life capacities of 1,140 cells (12 cars, Nature Energy 2026). Measured = true x (1 + error). Two error models, both worst-case reading of '5%':
  bias: one fixed error per cell, uniform in +-5% (does not average out over cycles)    gauss: new error every cycle, sd = 5%/2 (averages over N persistent cycles)
A false bypass = a healthy real cell measured below (1 - weak_frac) x median of its string for ALL of N cycles. Detection = a cell truly `loss` below the string median is flagged."""
import csv
import numpy as np
rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
packs = [np.array(v) for v in car.values()]
rng = np.random.default_rng(11)

def err(shape, model, mag):
    if model == "bias":
        return rng.uniform(-mag, mag, shape[:2])[:, :, None] * np.ones(shape)       # one fixed error per cell, same every cycle
    return rng.normal(0, mag / 2, shape)                                              # fresh each cycle

def false_rate(mag, model, line, N, reps=200):
    bad = tot = 0
    for c in packs:
        true = c / np.median(c)
        for _ in range(reps):
            m = true[None, :, None] * (1 + err((1, len(c), N), model, mag))
            med = np.median(m[0], axis=0)                       # string median measured each cycle
            flag = (m[0] < (1 - line) * med[None, :]).all(axis=1)
            bad += flag.sum(); tot += len(c)
    return bad / tot

def detect_rate(loss, mag, model, line, N, reps=400):
    hit = 0
    for _ in range(reps):
        n = 95; true = np.ones(n); true[0] = 1 - loss
        m = true[None, :, None] * (1 + err((1, n, N), model, mag))
        med = np.median(m[0], axis=0)
        hit += (m[0][0] < (1 - line) * med).all()
    return hit / reps

print("false bypass rate on real healthy cells (per 1,000 cells)")
print(f"{'error model':14} {'line':>5} {'N=1':>6} {'N=2':>6} {'N=3':>6}")
for model, mag in (("bias", 0.05), ("gauss", 0.05), ("bias", 0.02)):
    for line in (0.10, 0.15, 0.20):
        print(f"{model+' '+str(int(mag*100))+'%':14} {line:5.2f} " + " ".join(f"{1000*false_rate(mag, model, line, N, reps=30):6.1f}" for N in (1, 2, 3)))
print("\ndetection of a truly weak cell (share flagged), N=3 cycles")
print(f"{'error model':14} {'line':>5} " + " ".join(f"{int(l*100)}%weak" .rjust(7) for l in (0.15, 0.20, 0.25, 0.30)))
for model, mag in (("bias", 0.05), ("gauss", 0.05)):
    for line in (0.10, 0.15, 0.20):
        print(f"{model+' '+str(int(mag*100))+'%':14} {line:5.2f} " + " ".join(f"{detect_rate(l, mag, model, line, 3):7.2f}" for l in (0.15, 0.20, 0.25, 0.30)))
