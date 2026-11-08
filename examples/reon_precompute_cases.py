"""Precompute the engine results the dashboard demo needs, so nothing takes 12 seconds on stage. Writes/merges examples/data/storefront_cases.json.
usage (add fades=0.006,0.012 to run those wear levels instead of the default three; they feed the gain-versus-wear chart)
usage (one call fits the 120 s limit per 1-2 values): PYTHONPATH=. python examples/reon_precompute_cases.py 12 22   |   ... 40 80   |   ... tab12
  numbers = value of a kWh per year; each runs p in (1, 4, 16, 40) x fade in (0.004, 0.008, 0.02) at 250 cells, switch cost 15.5.
  'tab12' runs the tariff-screen values (single cells, fade 0.008) from the 'Who buys' tab.
The saved results are deterministic (fixed seeds); tests/test_reon_storefront.py recomputes one case and fails if the file is stale."""
import datetime
import json
import sys
from multiprocessing import Pool

from hackkit import reon_storefront as SF

TAB12_VALUES = (15, 30, 45, 60, 75, 90, 120, 150)


def job(a):
    p, fade, value = a
    return SF.case_key(p, fade, value), SF.core(p, fade, value)


if __name__ == "__main__":
    jobs = []
    fades = (0.004, 0.008, 0.02)
    args = [a for a in sys.argv[1:] if not a.startswith("fades=")]
    for a in sys.argv[1:]:
        if a.startswith("fades="):
            fades = tuple(float(x) for x in a[6:].split(","))
    for arg in args or ["40"]:
        if arg == "tab12":
            jobs += [(1, 0.008, v) for v in TAB12_VALUES]
        else:
            jobs += [(p, f, float(arg)) for p in (1, 4, 16, 40) for f in fades]
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    try:
        data = json.load(open(SF.CASES_PATH))
    except (OSError, ValueError):
        data = {"cases": {}}
    data["cases"].update(dict(res))
    data["generated"] = datetime.date.today().isoformat()
    data["note"] = "250 series elements, switch cost 15.5 per kWh, loss 4%, fade spread 0.45/sqrt(p), horizon 12 y for the verdict and gain, 30 y for lives, inverter voltage window 0.9 (at most 10% of cells bypassed at once, every build). Regenerate with examples/reon_precompute_cases.py."
    json.dump(data, open(SF.CASES_PATH, "w"), indent=1, sort_keys=True)
    print(len(data["cases"]), "cases saved;", len(res), "just computed")
