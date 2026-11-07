"""Customer-view numbers at 250 series elements for the front page: verdict, dollars over 12 years on a 60 kWh battery, life plain vs ours, cells not replaced and net manufacturing carbon (range). Run: PYTHONPATH=. python examples/reon_storefront_cases.py"""
import csv
import numpy as np
from multiprocessing import Pool
from hackkit import reon_storefront as SF


def packs():
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    car = {}
    for p, _, _, late in rows:
        car.setdefault(p, []).append(float(late))
    return {k: np.array(v) for k, v in car.items()}


def job(a):
    p, fade = a
    return a, SF.storefront(p, fade, 40.0, 15.5, packs())


if __name__ == "__main__":
    with Pool(4) as pool:
        res = pool.map(job, [(p, f) for p in (1, 4, 16, 40) for f in (0.004, 0.008, 0.02)])
    print("60 kWh, 250 series elements, value 40 per kWh-year, switch cost 15.5, 5 kW load. Dollars = first 12 years, whole battery. Carbon: horizon 20 y, net t CO2e (range over sourced/assumed inputs).")
    print(f"{'p':>3} {'fade':>6} | {'verdict':7} {'$ total':>8} {'p10 $':>7} | {'life plain':>10} {'life ours':>9} | {'cells kWh':>9} {'net t':>6} {'low':>6} {'high':>6}")
    for (p, f), r in res:
        e = r["env"]
        c = f"{e['kwh_cells_avoided']:9.0f} {e['net_t']:6.1f} {e['low_t']:6.1f} {e['high_t']:6.1f}" if e else f"{'-':>9} {'-':>6} {'-':>6} {'-':>6}"
        print(f"{p:3d} {f:6.3f} | {r['verdict']:7} {r['dollars_total']:8.0f} {r['p10_total']:7.0f} | {r['life_plain']:9.1f}y {r['life_ours']:8.1f}y | {c}")
