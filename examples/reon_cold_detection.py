"""COLD-AWARE DETECTION (regime conditioning, pattern from Nima and Nicole, credited; self-reported, other domains). Cold cells show less capacity. Does a cold edge of the string cause false bypasses, and does conditioning on temperature fix it?
Healthy cells: the 1,140 REAL cells (capacity / median of the others). Ambient and edge cooling are ASSUMED (the 4 cells at each end of every 16-cell segment are DT degrees colder); capacity loss in the cold = 0.7 % per degree below 25 C (ASSUMED from the sodium review: 50 to 70 % kept at -20 C, i.e. 0.7 to 1.1 % per degree).
Naive rule: flag when observed < 0.85 of the others for 3 cycles. Conditioned rule: first divide each observation by the temperature factor. Sensing error 2 %. Run: PYTHONPATH=. python examples/reon_cold_detection.py"""
import csv
import numpy as np

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
rel = np.concatenate([np.array([v[i] / np.median(np.delete(v, i)) for i in range(len(v))]) for v in map(np.array, car.values())])
G = len(rel) // 16
rel = rel[:G * 16]
n = G * 16
edge = (np.arange(n) % 16 < 4) | (np.arange(n) % 16 >= 12)
rng = np.random.default_rng(5)
K, SIG, CYC = 0.007, 0.02, 200


def flagged(obs, line=0.85, need=3):
    """obs: (cells, cycles). Each cycle every cell is compared with the MEDIAN OF ITS 16-CELL SEGMENT in that same cycle (so a cold string cancels out and only differences remain)."""
    o = obs.reshape(G, 16, -1)
    r = (o / np.median(o, axis=1, keepdims=True)).reshape(n, -1)
    low = r < line
    run = np.zeros(n, int)
    out = np.zeros(n, bool)
    for t in range(r.shape[1]):
        run = np.where(low[:, t], run + 1, 0)
        out |= run >= need
    return out


print("false bypass rate per healthy REAL cell over 200 cycles (injected cold, 2 % sensing error; cells compared with their segment median in the same cycle)")
print("ambient C  edge cells colder by   naive rule   conditioned on temperature   (cell injected at 0.70 detected: naive / conditioned)")
for amb in (25, 0, -10, -20):
    for dT in (0, 5, 10):
        temp = np.where(edge, amb - dT, amb).astype(float)
        fac = 1.0 - K * np.maximum(25.0 - temp, 0.0)
        obs = (rel * fac)[:, None] * (1 + SIG * rng.standard_normal((n, CYC)))
        naive = flagged(obs).mean()
        cond = flagged(obs / fac[:, None]).mean()
        inj = rel.copy()
        inj[::16] = 0.70
        o2 = (inj * fac)[:, None] * (1 + SIG * rng.standard_normal((n, CYC)))
        hit = lambda f: f[::16].mean()
        print(f"{amb:8d} {dT:14d} K {100 * naive:12.2f} % {100 * cond:20.2f} %       {100 * hit(flagged(o2)):5.1f}% / {100 * hit(flagged(o2 / fac[:, None])):5.1f}%")
