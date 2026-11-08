"""Slow recovery between two outages: hours of the SECOND outage against how long the grid is back for recharge (reon_storm.second_outage_hours, an energy budget).
Run from the repo root: PYTHONPATH=. python examples/reon_slow_recovery.py   Writes examples/data/slow_recovery.json and prints a table.
With failed=1 the first outage left one cell open (a plain string delivers nothing). Assumed: 60 kWh store, 5 kW load, charger 10 kW (about C/6, ASSUMED), first outage emptied the string, 12 real car packs (median), window 0.9, switch loss 2%."""
import csv, json
import numpy as np
from hackkit import reon_storm as S

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
packs = list(car.values())
out = []
for failed in (0, 1):
  for cold in (1.0, 0.8):
    for h in (1, 2, 4, 6, 12, 24):
        med = lambda managed: float(np.median([S.second_outage_hours(np.array(v), 60.0, 5.0, 10.0, h, managed, cold, window=0.9 if managed else None, failed=failed) for v in packs]))
        out.append(dict(failed=failed, cold=cold, recharge_h=h, plain_h=med(False), control_h=med(True)))
json.dump(out, open("examples/data/slow_recovery.json", "w"), indent=1)
for r in out:
    print(f"failed {r['failed']}  cold {r['cold']:.1f}  recharge {r['recharge_h']:>2} h   plain {r['plain_h']:.1f} h   cell-level control {r['control_h']:.1f} h   gain {r['control_h'] - r['plain_h']:+.1f} h")
