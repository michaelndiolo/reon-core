"""STORM SCENARIO (draft): 72 h outage, no solar (conservative: Maine December storm, overcast), 60 kWh nameplate string, REAL cell spreads of 12 cars (Nature Energy 2026 Fig 4, 280,000 km).
Compares plain vs cell-level control on backup hours, with and without a cell failing open at hour 24, with cold derating (0.8, ASSUMED between lithium and sodium reviews: docs/SOURCES.md) and with load shed to 50 %.
Then prices the wear of staying in bypass mode. Run: PYTHONPATH=. python examples/reon_storm_scenario.py"""
import csv
import numpy as np
from hackkit import reon_storm as S

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
CARS = {}
for p, _, _, late in rows:
    CARS.setdefault(p, []).append(float(late))
CARS = {k: np.array(v) for k, v in CARS.items()}
NAME, D, TF = 60.0, 72.0, 24.0


def med(f):
    v = [f(c) for c in CARS.values()]
    return np.median(v), min(v), max(v)


print(f"72 h outage, 60 kWh nameplate, 12 real packs; hours of supply (median, worst, best over packs); '-' means covered the full {D:.0f} h")
for load in (1.0, 2.0):
    for cold in (1.0, 0.8):
        for label, tf in (("no failure", None), (f"one cell fails open at hour {TF:.0f}", TF)):
            for mg, name in ((False, "plain"), (True, "managed")):
                m, lo, hi = med(lambda c: min(S.hours(c, NAME, load, mg, cold, tf), D))
                print(f"load {load:.0f} kW, cold x{cold:.1f}, {label:32s} {name:8s} {m:6.1f} h  (worst {lo:5.1f}, best {hi:5.1f})")
            m, lo, hi = med(lambda c: min(S.hours(c, NAME, load, True, cold, tf, power_fraction=0.5), D))
            print(f"load {load:.0f} kW, cold x{cold:.1f}, {label:32s} managed + load shed to 50 %  {m:6.1f} h  (worst {lo:5.1f}, best {hi:5.1f})")
print("\nExtra gain of managed over plain with no failure (energy): median %.1f %%, range %.1f to %.1f %%" % tuple(100 * (np.array(med(lambda c: S.usable_kwh(c, NAME, True) / S.usable_kwh(c, NAME, False) - 1.0)))))

print("\nWear price of staying in bypass mode (16-cell string, constant power, DoD exponent 0.87 from the Iowa State fit):")
for k in (1, 2, 4):
    f = S.stress_factors(16, k)
    print(f"  {k} cell(s) bypassed for good: current and depth of discharge x{f['current_and_dod_x']:.3f}, wear rate x{f['wear_rate_x']:.3f}, heating x{f['heat_x']:.3f}")
pack_cost, life_y = 60.0 * 98.0, 12.0   # 98 EUR/kWh new cells (Chalmers/BNEF 2024, repo), 12 y life (ASSUMED); currency units as in the repo
day = pack_cost / (life_y * 365.0)
for k in (1, 4):
    f = S.stress_factors(16, k)
    extra = (f["wear_rate_x"] - 1.0) * day
    gain = np.median([S.hours(c, NAME, 1.0, True, 1.0, TF) - S.hours(c, NAME, 1.0, False, 1.0, TF) for c in CARS.values()]) * 1.0
    print(f"  one storm day with {k} bypassed costs about {extra:.2f} of pack life value (pack {pack_cost:.0f}, {life_y:.0f} y); the same outage with one failed cell delivers {gain:.0f} kWh more than plain (1 kW, no cold, failure at hour 24): break-even value of lost load {extra / gain:.4f} per kWh")
