"""One-at-a-time sensitivity at 250 series elements: how much does each uncertain input move the 12-year net gain over a plain string (per kWh nameplate)?
Base: one large cell per position (p=1), fade 0.008/yr, value 40 per kWh-year, switch cost 15.5, switch loss 4%, fade spread 0.45, start spread 2%.
Low and high ends are the ranges used in SOURCES.md. Writes examples/data/tornado_250.csv. Run: PYTHONPATH=. python examples/reon_tornado_250.py"""
import csv
import numpy as np
from multiprocessing import Pool
from hackkit import reon_guard as G
from hackkit.reon_storefront import WINDOW, CLOSED_LOSS   # inverter voltage window, 0.9: every build respects it

KS = (1, 2, 4, 8, 16, 25)
BASE = dict(p=1, fade=0.008, value=40.0, elec=15.5, loss=0.04, fcv=0.45, spread=0.02)
# name, key, low, high, tag, who can answer
INPUTS = [
    ("Cell fade per year", "fade", 0.004, 0.02, "CITED claim (20,000 cycles), unverified", "REON: measured fade on the sodium cells"),
    ("Value of a kWh per year ($)", "value", 12.0, 80.0, "CITED range", "the customer's tariff (demand charge)"),
    ("Switch electronics cost per kWh ($)", "elec", 7.0, 24.0, "CITED (REON CTO)", "REON: quote, and whether it is total or extra over a BMS"),
    ("Usable-energy loss to switches", "loss", 0.0, 0.10, "ASSUMED", "REON: switch resistance and voltage floor"),
    ("Spread of fade between cells", "fcv", 0.20, 0.60, "ASSUMED (real cars 0.20 to 0.60)", "REON: teardown or cycling data on their cells"),
    ("Starting capacity spread", "spread", 0.01, 0.05, "ASSUMED", "REON: incoming cell data"),
    ("Cells in parallel per position", "p", 1, 16, "UNKNOWN", "REON: is a position one cell or a parallel group"),
]


def run(a):
    key, val = a
    c = dict(BASE)
    if key:
        c[key] = val
    p = c["p"]
    rng = np.random.default_rng(3)
    start = 100.0 * (1.0 + c["spread"] / np.sqrt(p) * rng.standard_normal(250))
    r = G.robust_recommend(start, 250, value_per_kwh_year=c["value"], electronics_per_kwh=c["elec"], fade_cv=c["fcv"] / np.sqrt(p), fade_mean=c["fade"], loss=c["loss"],
                           years=12.0, eol_frac=0.7, trials=8, steps=60, ks=KS, window=WINDOW, closed_loss=CLOSED_LOSS)
    return key, val, r["verdict"], (r["mean_gain"] if r["verdict"] == "BUY" else 0.0), r["mean_gain"]


if __name__ == "__main__":
    jobs = [(None, None)] + [(k, v) for _, k, lo, hi, _, _ in INPUTS for v in (lo, hi)]
    with Pool(4) as pool:
        res = pool.map(run, jobs)
    d = {(k, v): (vd, g, raw) for k, v, vd, g, raw in res}
    base = d[(None, None)]
    rows = []
    for name, k, lo, hi, tag, who in INPUTS:
        a, b = d[(k, lo)], d[(k, hi)]
        rows.append(dict(input=name, key=k, low=lo, high=hi, gain_low=round(a[1], 1), gain_high=round(b[1], 1), verdict_low=a[0], verdict_high=b[0], swing=round(abs(b[1] - a[1]), 1), tag=tag, who_can_answer=who))
    rows.sort(key=lambda r: -r["swing"])
    with open("examples/data/tornado_250.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["base_gain"])
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, base_gain=round(base[1], 1)))
    print(f"Base case gain {base[1]:.1f} per kWh ({base[0]}). Net gain over plain, 12 years, per kWh nameplate, one input at a time (a HOLD counts as 0).")
    for r in rows:
        print(f"{r['input']:38} {r['low']:>7}: {r['gain_low']:7.1f} {r['verdict_low']:5} | {r['high']:>7}: {r['gain_high']:7.1f} {r['verdict_high']:5} | swing {r['swing']:6.1f} | {r['tag']}")
