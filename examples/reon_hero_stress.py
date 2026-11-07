"""STRESS TEST of the hero case (new sodium-style pack, commercial/industrial duty, retire at 70 %). Run: PYTHONPATH=. python examples/reon_hero_stress.py random|sourced|sourcedv <seed> <n>  |  report
Each draw moves EVERY input at once and asks: does reon_wear.recommend_build beat the best rival (plain, sort only, balancer)? and does it beat the plain string (the brief's baseline)?
random: wide ASSUMED ranges on every input (balancer strength and cost drawn independently, on purpose harsh).
sourced: fade-rate spread drawn from the 12 REAL cars (Nature Energy 2026 Fig 4); switch cost from Tim Ren's 7 to 24 per kWh; balancer strength and cost tied together by real parts (as in reon_stress.draw_sourced); value per kWh-year 10 to 90
(12 grid preset, 22 EV preset, 90 = derived demand-charge ceiling, see docs/SOURCES.md). Still ASSUMED: sodium life, fade rate, start spread, cell size, duty, wear exponents."""
import csv, json, sys
from multiprocessing import Pool
import numpy as np
from hackkit import reon_wear as W

OUT = {"random": "examples/reon_hero_stress_random.jsonl", "sourced": "examples/reon_hero_stress_sourced.jsonl", "sourcedv": "examples/reon_hero_stress_sourced_voltage.jsonl", "longlife": "examples/reon_hero_stress_longlife.jsonl"}


def real_fade_cvs():
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    cars = {}
    for p, _, e, l in rows:
        cars.setdefault(p, []).append((float(e), float(l)))
    out = []
    for v in cars.values():
        a = np.array(v)
        loss = 1.0 - a[:, 1] / a[:, 0]
        out.append(min(float(loss.std(ddof=1) / loss.mean()), 0.6))
    return out


def u(rng, lo, hi):
    return float(rng.uniform(lo, hi))


def lg(rng, lo, hi):
    return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))


def draw(rng, mode, cvs):
    volt = mode == "sourcedv"      # sourced draws PLUS the voltage-floor derating of docs: extra usable-energy loss of 2.3 to 5.0 points (sodium curve, minimum voltage 0.60 to 0.75 of nominal; examples/reon_voltage_limit.py); the minimum voltage is UNKNOWN
    mode = "sourced" if volt else mode
    p = dict(value=lg(rng, 10, 90), years=u(rng, 8, 15), fade=u(rng, 0.01, 0.04), duty=u(rng, 0.5, 0.95), g=float(rng.choice([0.0, 0.6, 0.9, 1.2])), knee=float(rng.choice([0.0, 0.3, 0.65])),
             loss=u(rng, 0.005, 0.05), start_cv=u(rng, 0.01, 0.04), sigma=lg(rng, 0.01, 0.10), sort=u(rng, 0.0, 5.0), closed=float(rng.choice([0.0, 0.005, 0.01])), n=int(rng.choice([16, 48])), seed=int(rng.integers(1, 10**6)))
    if mode == "random":
        p.update(fcv=u(rng, 0.1, 0.6), elec=lg(rng, 2.0, 24.0), r=lg(rng, 0.01, 0.6), bcost=u(rng, 0.0, 15.0), eta=u(rng, 0.8, 0.95))
    else:
        amps = float(rng.choice([1.0, 2.0, 5.5, 10.0]))
        ah = u(rng, 20.0, 100.0)               # ASSUMED stationary cell size
        crate = u(rng, 0.15, 0.5)              # ASSUMED C&I discharge rate
        per_cell = u(rng, 2.1, 3.2) * u(rng, 1.0, 2.5) if amps >= 5.5 else u(rng, 0.5, 2.0)
        p.update(fcv=float(rng.choice(cvs)), elec=u(rng, 7.0, 24.0), r=min(amps / (crate * ah), 1.0), bcost=per_cell / (ah * 3.2 / 1000.0), eta=u(rng, 0.85, 0.95), amps=amps, ah=ah)
    if mode == "longlife":   # Tim Ren 7 Nov: the NFPP sodium cells are specified at 20,000 cycles (maker claim, UNVERIFIED). Roughly 0.003 to 0.012 per year of capacity fade at 1 cycle a day; life 10 to 25 y
        p["fade"] = lg(rng, 0.003, 0.012); p["years"] = u(rng, 10.0, 25.0)
    if volt:
        p["loss"] = 0.02 + float(rng.choice([0.023, 0.029, 0.039, 0.050]))
    return p


def evaluate(p):
    rng = np.random.default_rng(p["seed"])
    start = 100.0 * (1.0 + p["start_cv"] * rng.standard_normal(p["n"]))
    out = W.recommend_build(start, 16, balancer_r=p["r"], balancer_per_kwh=p["bcost"], ks=(1, 2, 3, 4), fade_mean=p["fade"], fade_cv=p["fcv"], loss=p["loss"], electronics_per_kwh=p["elec"],
                            sort_cost_per_kwh=p["sort"], value_per_kwh_year=p["value"], rate=0.07, years=p["years"], eol_frac=0.7, duty=p["duty"], dod_exp=p["g"], knee_share=p["knee"], start_soh=1.0,
                            balancer_eta=p["eta"], closed_loss=p["closed"], test_sigma=p["sigma"], trials=14, steps=40, seed=5)
    t = out["table"]
    return dict(p, build=out["build"], ours_name=out["ours_best"], rival_name=out["rival_best"], margin=float(out["margin"]), ours=float(t[out["ours_best"]]["mean"]), rival=float(t[out["rival_best"]]["mean"]),
                years_plain=float(t["plain"]["years"]), years_ours=float(t[out["ours_best"]]["years"]))


def report(mode):
    rows = [json.loads(l) for l in open(OUT[mode])]
    m = np.array([r["margin"] for r in rows])
    o = np.array([r["ours"] for r in rows])
    print(f"{mode}: {len(rows)} draws")
    print(f"  beat best rival in {np.mean(m > 0) * 100:.0f}%  (margin median {np.median(m):+.1f}, 10th pct {np.percentile(m, 10):+.1f}, worst {m.min():+.1f} per kWh nameplate)")
    print(f"  beat plain string (brief baseline) in {np.mean(o > 0.05) * 100:.0f}%  (median {np.median(o):+.1f}, 10th pct {np.percentile(o, 10):+.1f})")
    for key, bins in (("value", (10, 20, 40, 90)), ("fcv", (0.1, 0.2, 0.4, 0.6)), ("elec", (2, 7, 15, 24))):
        for lo, hi in zip(bins[:-1], bins[1:]):
            s = [r for r in rows if lo <= r[key] < hi + (1e-9 if hi == bins[-1] else 0)]
            if s:
                print(f"  {key} {lo}-{hi}: n={len(s)}, win vs rival {np.mean([r['margin'] > 0 for r in s]) * 100:.0f}%, vs plain {np.mean([r['ours'] > 0.05 for r in s]) * 100:.0f}%")
    lose = [r for r in rows if r["margin"] <= 0]
    if lose:
        print("  losing draws, median input vs all draws:", {k: (round(float(np.median([r[k] for r in lose])), 3), round(float(np.median([r[k] for r in rows])), 3)) for k in ("value", "fcv", "elec", "r", "bcost", "start_cv", "fade")})


if __name__ == "__main__":
    if sys.argv[1] == "report":
        for md in ("random", "sourced", "sourcedv", "longlife"):
            try:
                report(md)
            except FileNotFoundError:
                pass
        sys.exit()
    mode, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = np.random.default_rng(seed)
    cvs = real_fade_cvs()
    draws = [draw(rng, mode, cvs) for _ in range(n)]
    with Pool() as pool:
        res = pool.map(evaluate, draws)
    with open(OUT[mode], "a") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    print("wrote", len(res), "draws to", OUT[mode])
