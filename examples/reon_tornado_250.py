"""One-at-a-time sensitivity at 250 series elements: how much does each uncertain input move what our recommended build earns over the BETTER of a simple balancer or a plain string (12 years, per kWh nameplate)?
The guarded policy (reon_policy.robust_guarded) decides: 0 when the answer is "a balancer is enough" or "hold". The column total_* is the gain over a plain string.
Base: one large cell per position (p=1), fade 0.008/yr, value 40 per kWh-year, switch cost 15.5 (already the extra over a conventional BMS, Tim Ren 8 Nov), switch loss 4% (+2% on all energy), balancer 5%, window 0.9, fade spread 0.45, start spread 2%.
Low and high ends are the ranges used in SOURCES.md. Writes examples/data/tornado_250.csv. Run: PYTHONPATH=. python examples/reon_tornado_250.py"""
import csv
import numpy as np
from multiprocessing import Pool
from hackkit import reon_policy as POL
from hackkit.reon_storefront import WINDOW, CLOSED_LOSS   # inverter voltage window, 0.9: every build respects it

KS = (1, 2, 4, 8, 16, 25)
BASE = dict(p=1, fade=0.008, value=40.0, elec=15.5, loss=0.04, fcv=0.45, spread=0.02, r=0.05, window=WINDOW, closed=CLOSED_LOSS)
# name, key, low, high, tag, who can answer
INPUTS = [
    ("Cell fade per year", "fade", 0.004, 0.02, "CITED claim (20,000 cycles), unverified", "REON: measured fade on the sodium cells"),
    ("Value of a kWh per year ($)", "value", 12.0, 80.0, "CITED range", "the customer's tariff (demand charge)"),
    ("Switch electronics cost per kWh ($)", "elec", 7.0, 24.0, "CITED (REON CTO)", "settled by Tim Ren: this range is the extra over a conventional BMS; it depends on PCB volume"),
    ("Usable-energy loss to switches", "loss", 0.0, 0.10, "ASSUMED", "REON: switch resistance and voltage floor"),
    ("Spread of fade between cells", "fcv", 0.20, 0.60, "ASSUMED (real cars 0.20 to 0.60)", "REON: teardown or cycling data on their cells"),
    ("Starting capacity spread", "spread", 0.01, 0.05, "ASSUMED", "REON: incoming cell data"),
    ("Cells in parallel per position", "p", 1, 16, "UNKNOWN (Tim: could be both)", "REON: the data sheet for the 60 kWh product"),
    ("Balancer strength (share of a cell moved per cycle)", "r", 0.02, 0.10, "ASSUMED, unsourced", "REON: what the baseline BMS balances, and at what current"),
    ("Voltage window (share of cells that must stay)", "window", 0.80, 0.95, "UNKNOWN (PCS dependent, Tim 8 Nov)", "REON: PCS minimum DC input voltage"),
    ("Switch loss on all energy (always-closed path)", "closed", 0.0, 0.04, "ASSUMED", "REON: switch resistance"),
]


def run(a):
    key, val = a
    c = dict(BASE)
    if key:
        c[key] = val
    p = c["p"]
    rng = np.random.default_rng(3)
    start = 100.0 * (1.0 + c["spread"] / np.sqrt(p) * rng.standard_normal(250))
    r = POL.robust_guarded(start, 250, value_per_kwh_year=c["value"], electronics_per_kwh=c["elec"], fade_cv=c["fcv"] / np.sqrt(p), fade_mean=c["fade"], loss=c["loss"], balancer_r=c["r"],
                           years=12.0, eol_frac=0.7, trials=8, steps=60, ks=KS, window=c["window"], closed_loss=c["closed"], life_years=None)
    return key, val, r["verdict"], (r["margin_vs_rival"] if r["verdict"] == "BUY" else 0.0), r["mean_gain"]


PARTIAL = "examples/data/tornado_250_partial.json"   # resumable: `python examples/reon_tornado_250.py next 8` runs the next 8 jobs not yet done; with no argument it assembles the table once all are done


def label(k, v):
    return f"{k}|{v}"


if __name__ == "__main__":
    import json
    import sys
    jobs = [(None, None)] + [(k, v) for _, k, lo, hi, _, _ in INPUTS for v in (lo, hi)]
    try:
        part = json.load(open(PARTIAL))
    except (OSError, ValueError):
        part = {}
    todo = [j for j in jobs if label(*j) not in part]
    if len(sys.argv) > 2 and sys.argv[1] == "next":
        batch = todo[:int(sys.argv[2])]
        with Pool(4) as pool:
            for k, v, vd, g, raw in pool.map(run, batch):
                part[label(k, v)] = [vd, g, raw]
        json.dump(part, open(PARTIAL, "w"))
        print(len(todo) - len(batch), "jobs left")
        sys.exit(0)
    if todo:
        with Pool(4) as pool:
            for k, v, vd, g, raw in pool.map(run, todo):
                part[label(k, v)] = [vd, g, raw]
        json.dump(part, open(PARTIAL, "w"))
    d = {(k, v): tuple(part[label(k, v)]) for k, v in jobs}
    base = d[(None, None)]
    rows = []
    for name, k, lo, hi, tag, who in INPUTS:
        a, b = d[(k, lo)], d[(k, hi)]
        rows.append(dict(input=name, key=k, low=lo, high=hi, gain_low=round(a[1], 1), gain_high=round(b[1], 1), total_low=round(a[2], 1), total_high=round(b[2], 1), verdict_low=a[0], verdict_high=b[0], swing=round(abs(b[1] - a[1]), 1), tag=tag, who_can_answer=who))
    rows.sort(key=lambda r: -r["swing"])
    with open("examples/data/tornado_250.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["base_gain", "base_total"])
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, base_gain=round(base[1], 1), base_total=round(base[2], 1)))
    print(f"Base case: extra over the better of balancer or plain {base[1]:.1f} per kWh ({base[0]}); total over plain {base[2]:.1f}. 12 years, per kWh nameplate, one input at a time (BALANCER or HOLD counts as 0 extra).")
    for r in rows:
        print(f"{r['input']:38} {r['low']:>7}: {r['gain_low']:7.1f} {r['verdict_low']:5} | {r['high']:>7}: {r['gain_high']:7.1f} {r['verdict_high']:5} | swing {r['swing']:6.1f} | {r['tag']}")
