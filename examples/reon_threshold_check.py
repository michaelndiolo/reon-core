"""What a fixed health threshold can and cannot do on REAL cells (Nature Energy 2026, Zhou et al., Fig 4 source data, CC BY 4.0; 12 EVs, 95 NMC cells each, 280,000 km).
Part 1: share of cells below a cut-off set relative to the pack mean (false-alarm check for a fault threshold).
Part 2: best STATIC bypass: remove the k weakest cells for good. String energy ~ (n-k) x capacity of the weakest remaining cell, so each bypass also removes that cell's voltage.
Compare with the dynamic ideal (every cell used until it empties): gain = mean/min - 1. Run: PYTHONPATH=. python examples/reon_threshold_check.py"""
import csv
import numpy as np

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
C = {}
for p, _, _, late in rows:
    C.setdefault(p, []).append(float(late))
C = {k: np.sort(np.array(v)) for k, v in C.items()}
R = np.concatenate([v / v.mean() for v in C.values()])
print(f"{len(C)} cars, {len(R)} cells")
for t in (0.97, 0.95, 0.92, 0.90, 0.85):
    print(f"cells below {t:.2f} x pack mean: {np.mean(R < t) * 100:.1f}% ({int((R < t).sum())} of {len(R)})")
print("\ncar    static best k  static gain   dynamic ideal (mean/min-1)")
for k, c in C.items():
    n = len(c)
    en = [(n - j) * c[j] for j in range(16)]
    g = [e / en[0] - 1 for e in en]
    bk = int(np.argmax(g))
    print(f"{k:<6} {bk:>6} {g[bk] * 100:12.1f}% {(c.mean() / c.min() - 1) * 100:14.1f}%")
