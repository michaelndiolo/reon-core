"""STRESS TEST of reon_wear.recommend_build on the three real packs (Leaf 8, BMW 36, REON brief 16) and three applications. Run: PYTHONPATH=. python examples/reon_stress.py tornado  |  random <seed> <n>  |  report
tornado: one input at a time moved from the base case to a low and a high value; prints the margin of the recommended build over the best rival (positive = we win). Base case: electronics 8.8, switch loss 2%,
closed loss 0, balancer r 5%, cost 4, efficiency 90%, test error 2%, fade cv 0.2, DoD exponent 0.8, knee share 65%, duty 0.7, sorting free.
random: draws every input at once from the ranges in RANGES (ASSUMED ranges, wide on purpose) and records whether the recommended build beats the best rival; results append to examples/reon_stress_random.jsonl.
report: win share by pack and application, and which inputs differ between losing and winning draws."""
import csv, json, os, sys
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W


def load(p):
    return np.array([float(r["capacity"]) for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))])


def stabl_pack(seed=3):
    """A second-life pack with the structure STABL Energy reports (arXiv 2609.04487; 324 logical cells of 100 Ah, median SOH 75.4%, within-module SD under 1%, module SOH 64 to 73%): 8 modules of 12 cells,
    cells ~ N(module level, 0.7%), module levels ~ N(75.4 Ah, 3%), ONE outlier at 47.8/75.4 = 63% of the median (the paper's P1M6C1). RECONSTRUCTED from the reported summary numbers, not the raw data."""
    rng = np.random.default_rng(seed)
    mods = [75.4 * (1 + rng.normal(0, 0.03)) * (1 + rng.normal(0, 0.007, 12)) for _ in range(8)]
    c = np.concatenate(mods)
    c[5 * 12 + 0] = 75.4 * 47.8 / 75.4
    return c


PACKS = {"Leaf 8": (load("examples/data/leaf_8.csv"), 8), "BMW 36": (load("examples/data/bmw_36.csv"), 12), "brief 16": (np.array([85.0] * 15 + [70.0]), 16), "STABL 96": (stabl_pack(), 12)}
APPS = {"retired EV": dict(value=22.0, years=7.0, eol=0.7, fade=0.01, start=0.8), "grid": dict(value=12.0, years=15.0, eol=0.7, fade=0.02, start=1.0),
        "data-center": dict(value=8.0, years=12.0, eol=0.8, fade=0.005, start=1.0)}
BASE = dict(elec=8.8, loss=0.02, closed=0.0, r=0.05, bcost=4.0, eta=0.9, sigma=0.02, fcv=0.2, g=0.8, knee=0.65, duty=0.7, sort=0.0, vmul=1.0, emul=1.0)
RANGES = dict(elec=("log", 2.0, 16.0), loss=("u", 0.005, 0.05), closed=("c", (0.0, 0.005, 0.01)), r=("log", 0.01, 0.6), bcost=("u", 0.0, 15.0), eta=("u", 0.8, 0.95), sigma=("log", 0.01, 0.10),
              fcv=("u", 0.1, 0.4), g=("c", (0.0, 0.6, 0.9, 1.2)), knee=("c", (0.0, 0.3, 0.65)), duty=("u", 0.5, 0.95), sort=("u", 0.0, 5.0), vmul=("u", 0.6, 1.4), emul=("u", 0.5, 2.0))


def evaluate(a):
    pk, app, p = a
    c, m = PACKS[pk]
    A = APPS[app]
    ks = tuple(k for k in (1, 2, 3, 4) if k < m)
    out = W.recommend_build(c, m, balancer_r=p["r"], balancer_per_kwh=p["bcost"], ks=ks, fade_mean=A["fade"] * p["fade_mul"] if "fade_mul" in p else A["fade"], fade_cv=p["fcv"], loss=p["loss"],
                            electronics_per_kwh=p["elec"], sort_cost_per_kwh=p["sort"], value_per_kwh_year=A["value"] * p["vmul"], rate=0.07, years=A["years"], eol_frac=A["eol"], duty=p["duty"],
                            dod_exp=p["g"], knee_share=p["knee"], start_soh=A["start"], balancer_eta=p["eta"], closed_loss=p["closed"], test_sigma=p["sigma"], trials=14, steps=40, seed=5)
    return a, {"build": out["build"], "margin": out["margin"], "ours": out["ours_best"], "rival": out["rival_best"]}


CRATE = {"retired EV": (0.3, 1.0), "grid": (0.15, 0.5), "data-center": (0.3, 2.0)}   # ASSUMED discharge C-rates per application


def draw_sourced(rng, pk, app):
    """Balancer strength and cost TIED together by real parts. Current class I in {1, 2, 5.5, 10} A (DALY ~1 A, Heltec 5.5 A, LTC3300-1 10 A). Transfer limit r = I / (C_rate x cell Ah). Cost per kWh = cost per cell / cell kWh:
    for the 5.5 and 10 A classes the LTC3300-1 chip alone is A$19.1 to 29.4 per 6 cells (element14) = USD 2.1 to 3.2 per cell at 0.66 USD/AUD, times 1.0 to 2.5 for transformers and FETs (ASSUMED); for the 1 and 2 A classes USD 0.5 to 2
    per cell (ASSUMED, no price found). So a balancer that moves a lot of a cell (small cell, low C-rate, big current) is on a SMALL cell, where the same cost per cell is a LARGE cost per kWh."""
    p = draw(rng)
    c, m = PACKS[pk]
    ah = float(c.mean())
    cr = float(rng.uniform(*CRATE[app]))
    amps = float(rng.choice([1.0, 2.0, 5.5, 10.0]))
    kwh_cell = ah * 3.7 / 1000.0
    per_cell = float(rng.uniform(2.1, 3.2) * rng.uniform(1.0, 2.5)) if amps >= 5.5 else float(rng.uniform(0.5, 2.0))
    p["r"] = min(amps / (cr * ah), 1.0)
    p["bcost"] = per_cell / kwh_cell
    p["amps"], p["crate"] = amps, cr
    return p


def draw(rng):
    p = {}
    for k, (kind, *a) in RANGES.items():
        p[k] = float(np.exp(rng.uniform(np.log(a[0]), np.log(a[1])))) if kind == "log" else float(rng.uniform(a[0], a[1])) if kind == "u" else float(rng.choice(a[0]))
    return p


def win_map():
    """After `report`: share of random draws where we win, by balancer transfer limit r (rows) and balancer cost (columns); and by our electronics cost. Packs with outliers (Leaf, brief) and the well-matched BMW pack."""
    rows = [json.loads(l) for l in open("examples/reon_stress_random.jsonl")]
    rb = [(0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.40), (0.40, 1.0)]
    cb = [(0, 2), (2, 5), (5, 10), (10, 15.1)]
    for name, sel in (("Leaf 8 + brief 16 (packs with outlier cells)", [r for r in rows if r["pack"] != "BMW 36"]), ("BMW 36 (well matched)", [r for r in rows if r["pack"] == "BMW 36"])):
        print("\n" + name + ": share of draws where the recommended build beats the best rival (rows: balancer transfer limit; columns: balancer cost per kWh) [n per cell]")
        print(" " * 12 + "".join("%14s" % ("%g-%g" % (a, b)) for a, b in cb))
        for lo, hi in rb:
            line = "%12s" % ("%.0f%%-%.0f%%" % (100 * lo, 100 * hi))
            for a, b in cb:
                s_ = [r for r in sel if lo <= r["r"] < hi and a <= r["bcost"] < b]
                txt = ("%.0f%% [%d]" % (100 * np.mean([r["margin"] > 0 for r in s_]), len(s_))) if s_ else "n/a"
                line += "%14s" % txt
            print(line)
        eb = [(0, 4), (4, 8), (8, 12), (12, 16.1)]
        print("by our electronics cost: " + "  ".join("%g-%g: %.0f%%" % (a, b, 100 * np.mean([r["margin"] > 0 for r in sel if a <= r["elec"] < b])) for a, b in eb))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "tornado":
        lows_highs = dict(elec=(4.0, 16.0), loss=(0.01, 0.05), closed=(0.0, 0.01), r=(0.02, 0.2), bcost=(0.0, 12.0), eta=(0.8, 0.95), sigma=(0.01, 0.10), fcv=(0.1, 0.4), g=(0.0, 1.2), knee=(0.0, 0.65), duty=(0.5, 0.95), sort=(0.0, 5.0))
        jobs, keys = [], []
        for pk in [x for x in PACKS if x == os.environ.get('ONLY', x)]:
            for app in APPS:
                jobs.append((pk, app, dict(BASE))); keys.append((pk, app, "base", None))
                for k, (lo, hi) in lows_highs.items():
                    for lab, v in (("low", lo), ("high", hi)):
                        jobs.append((pk, app, {**BASE, k: v})); keys.append((pk, app, k, lab, v))
        with Pool() as pool:
            res = pool.map(evaluate, jobs)
        base = {(a[0], a[1]): r["margin"] for a, r in res if a[2] == BASE and True}
        by = {}
        for (a, r), key in zip(res, keys):
            by[key] = r
        print("margin of the recommended build over the best rival, per kWh nameplate (positive = we win); base case in the first column")
        print(f"{'pack / application':24s} {'base':>6s} | " + " | ".join(f"{k} lo / hi" for k in lows_highs))
        for pk in [x for x in PACKS if x == os.environ.get('ONLY', x)]:
            for app in APPS:
                b = by[(pk, app, "base", None)]["margin"]
                cells = []
                for k, (lo, hi) in lows_highs.items():
                    cells.append(f"{by[(pk, app, k, 'low', lo)]['margin']:+5.1f}/{by[(pk, app, k, 'high', hi)]['margin']:+5.1f}")
                print(f"{pk + ' ' + app:24s} {b:+6.1f} | " + " | ".join(cells))
        print("\ninput ranges (low, high):", {k: v for k, v in lows_highs.items()})
    elif mode == "random":
        seed, n = int(sys.argv[2]), int(sys.argv[3])
        rng = np.random.default_rng(seed)
        draws = [draw(rng) for _ in range(n)]
        jobs = [(pk, app, p) for p in draws for pk in PACKS for app in APPS]
        with Pool() as pool:
            res = pool.map(evaluate, jobs)
        with open("examples/reon_stress_random.jsonl", "a") as f:
            for (pk, app, p), r in res:
                f.write(json.dumps({"pack": pk, "app": app, **p, **r}) + "\n")
        print("wrote", len(res))
    elif mode == "sourced":
        seed, n = int(sys.argv[2]), int(sys.argv[3])
        rng = np.random.default_rng(seed)
        jobs = [(pk, app, draw_sourced(rng, pk, app)) for _ in range(n) for pk in PACKS for app in APPS]
        with Pool() as pool:
            res = pool.map(evaluate, jobs)
        with open("examples/reon_stress_sourced.jsonl", "a") as f:
            for (pk, app, p), r in res:
                f.write(json.dumps({"pack": pk, "app": app, **p, **r}) + "\n")
        print("wrote", len(res))
    elif mode == "sourced_report":
        rows = [json.loads(l) for l in open("examples/reon_stress_sourced.jsonl")]
        print(f"{len(rows)} draws with balancer strength and cost tied to real parts; ours wins in {np.mean([r['margin'] > 0 for r in rows]):.0%}; margin quartiles {np.percentile([r['margin'] for r in rows], [10, 25, 50, 75, 90]).round(1)}")
        for pk in PACKS:
            for app in APPS:
                sel = [r for r in rows if r["pack"] == pk and r["app"] == app]
                print("  %-9s %-12s wins %3.0f%%  median margin %+5.1f  worst %+5.1f" % (pk, app, 100 * np.mean([r["margin"] > 0 for r in sel]), np.median([r["margin"] for r in sel]), min(r["margin"] for r in sel)))
        for amps in (1.0, 2.0, 5.5, 10.0):
            sel = [r for r in rows if r["amps"] == amps]
            print("  balancer %4.1f A: we win %3.0f%% (n=%d); median balancer limit %.0f%%, median cost %.1f per kWh" % (amps, 100 * np.mean([r["margin"] > 0 for r in sel]), len(sel), 100 * np.median([r["r"] for r in sel]), np.median([r["bcost"] for r in sel])))
        lose = [r for r in rows if r["margin"] <= 0]
        print("losing draws: %d; of them by pack: %s" % (len(lose), {pk: sum(1 for r in lose if r["pack"] == pk) for pk in PACKS}))
    elif mode == "winmap":
        win_map()
    else:
        rows = [json.loads(l) for l in open("examples/reon_stress_random.jsonl")]
        print(f"{len(rows)} draws; ours wins (margin > 0) in {np.mean([r['margin'] > 0 for r in rows]):.0%}; margin quartiles {np.percentile([r['margin'] for r in rows], [10, 25, 50, 75, 90]).round(1)}")
        for pk in PACKS:
            for app in APPS:
                sel = [r for r in rows if r["pack"] == pk and r["app"] == app]
                print(f"  {pk:9s} {app:12s} wins {np.mean([r['margin'] > 0 for r in sel]):4.0%}  median margin {np.median([r['margin'] for r in sel]):+5.1f}  worst {min(r['margin'] for r in sel):+5.1f}")
        keys = list(RANGES)
        print("\nmedian input in LOSING vs WINNING draws (all packs and applications)")
        for k in keys:
            lo = np.median([r[k] for r in rows if r["margin"] <= 0]) if any(r["margin"] <= 0 for r in rows) else float("nan")
            wi = np.median([r[k] for r in rows if r["margin"] > 0])
            print(f"  {k:6s} losing {lo:8.3f}   winning {wi:8.3f}")
        print("\nbuilds recommended:", {b: sum(1 for r in rows if r['build'] == b) for b in sorted({r['build'] for r in rows}, key=str)})
