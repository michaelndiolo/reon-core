"""How long utility/crews take to identify and fix a fault, and what it costs.
Part 1 (ASSUMED lead times, swept): months for a conventional string to notice a dead/weak cell (detect) plus dispatch and repair (lead). Automatic bypass keeps the string up during that time; replace-on-failure is down.
Part 2 (SOURCED grid anchors): EIA-861 CAIDI = minutes to restore per interruption (Table 11.3, 2024/2025). Does the pack cover that wait? Real 12-car cell sets, 60 kWh, 5 kW critical load."""
import csv
import numpy as np
from hackkit import reon_events as E
from hackkit import reon_storm as S

print("PART 1: gap in net value per kWh nameplate, ours+crew1 minus replace-on-failure, 10 seeds, visit cost 1500, fault rate 0.01/cell-year")
print("  down_cost = penalty per month the string is down, per kWh nameplate (energy value alone is ~3 per month at 40 per kWh-year; critical loads cost much more)")
print(f"{'detect':>7} {'lead':>5} {'down mo (replace)':>18} | " + " ".join(f"gap@down_cost={d:<4g}" for d in (0, 5, 20, 60)))
for det in (0.0, 1.0, 3.0, 6.0):
    for lead in (0.5, 1.0, 3.0):
        gaps = []
        for dc in (0.0, 5.0, 20.0, 60.0):
            kw = dict(visit_cost=1500.0, lam=0.01, lead=lead, detect=det, down_cost=dc)
            r = [E.simulate("replace", s, **kw) for s in range(10)]; o = [E.simulate("ours+crew1", s, **kw) for s in range(10)]
            gaps.append(np.mean([x["net"] for x in o]) - np.mean([x["net"] for x in r])); dm = np.mean([x["down_months"] for x in r])
        print(f"{det:7.1f} {lead:5.1f} {dm:18.1f} | " + " ".join(f"{g:+16.1f}" for g in gaps))

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
packs = [np.array(v) for v in car.values()]
print("\nPART 2: hours of backup at 5 kW from a 60 kWh pack, median of 12 real packs; wait = grid restoration time")
for label, hrs in (("US typical outage, CAIDI 2025 without major events ~115 min", 1.9), ("US with major events 2025 ~196 min", 3.3), ("Maine major-event year 2024 ~481 min", 8.0), ("Florida storm year 2024 ~747 min", 12.4), ("Penobscot Dec 2023 anecdote (3 days, UNVERIFIED)", 72.0)):
    pl = np.median([min(S.hours(c, 60.0, 5.0, False, 1.0, None), 72) for c in packs]); mg = np.median([min(S.hours(c, 60.0, 5.0, True, 1.0, None), 72) for c in packs])
    sh = np.median([min(S.hours(c, 60.0, 5.0, True, 1.0, None, 0.6), 72) for c in packs])
    cov = lambda h: "covers" if h >= hrs else f"short {hrs-h:.1f} h"
    print(f"  {label:62s} plain {pl:5.1f} h ({cov(pl)}), managed {mg:5.1f} h ({cov(mg)}), managed+shed to 60% {sh:5.1f} h ({cov(sh)})")
