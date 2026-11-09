"""VOLTAGE LIMIT on cell-level control, on the 12 REAL cars (Nature Energy 2026 Fig 4, 95 cells, 280,000 km; relative capacities). Run: PYTHONPATH=. python examples/reon_voltage_limit.py
For each chemistry curve and each system minimum voltage (fraction of nominal string voltage; REON's inverter minimum is UNKNOWN, ask REON), discharge at 0.3C constant power and report hours as a gain over the plain string:
ideal (usable = sum of cells, no voltage floor) vs floor (cells bypassed only while the string stays at or above the minimum). Share kept = floor gain / ideal gain."""
import csv
import numpy as np
from hackkit import reon_voltage as V

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
CARS = {}
for p, _, _, late in rows:
    CARS.setdefault(p, []).append(float(late))
CARS = {k: np.array(v) for k, v in CARS.items()}
print("median over 12 real packs: gain over plain (percent), ideal vs with the voltage floor, and share of the ideal gain kept")
print("curve        v_min / nominal   plain h   ideal gain   floor gain   share kept   cells bypassed at end (median)")
for curve in V.CURVES:
    for f in (0.60, 0.65, 0.70, 0.75, 0.80):
        g_i, g_f, sk, hp, nb = [], [], [], [], []
        for c in CARS.values():
            hpl, _ = V.run(c, curve, "plain", f)
            if hpl < 0.99 * V.run(c, curve, "plain", 0.0)[0]:
                continue                      # the system minimum voltage cuts even the plain string short: not a fair comparison, skip
            hid, _ = V.run(c, curve, "ideal", f)
            hfl, b = V.run(c, curve, "floor", f)
            g_i.append(hid / hpl - 1); g_f.append(hfl / hpl - 1); hp.append(hpl); nb.append(b)
            sk.append((hfl - hpl) / (hid - hpl) if hid > hpl else np.nan)
        if not hp:
            print(f"{curve:12s} {f:10.2f}   plain string itself cannot use its full range at this minimum voltage (system infeasible)")
            continue
        print(f"{curve:12s} {f:10.2f} {np.median(hp):12.2f} {100 * np.median(g_i):10.1f}% {100 * np.median(g_f):10.1f}% {np.nanmedian(sk):11.2f} {np.median(nb):12.0f}")
print("\nMost cells that can be bypassed in a 16-cell string if all cells sit at the same SOC (worst-case rule of thumb), v_min = 0.8 of nominal:")
for curve in V.CURVES:
    print(f"  {curve:11s} " + "  ".join(f"SOC {int(s * 100):3d}%: {V.bypass_room(16, s, curve, 0.8)}" for s in (1.0, 0.5, 0.2, 0.1, 0.05)))
