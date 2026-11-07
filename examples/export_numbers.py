"""One file every dashboard page reads: numbers.json. Run: PYTHONPATH=. python examples/export_numbers.py
Every block carries its source tags, so a front end can show REAL / CITED / ASSUMED beside the number."""
import csv, json, datetime
import numpy as np
from hackkit import reon_events as E, reon_guard as G, reon_presets as PR, reon_storm as S

out = {"generated": datetime.date.today().isoformat(), "units": "net value per kWh nameplate, present value, unless stated", "note": "Simulations and replays only. Hardware keeps safety authority."}

rng = np.random.default_rng(3); start = 100.0 * (1.0 + 0.02 * rng.standard_normal(16))
hero = []
for fade in (0.004, 0.008, 0.02):
    r = G.robust_recommend(start, 16, value_per_kwh_year=40.0, electronics_per_kwh=15.5, fade_cv=0.45, loss=0.04, fade_mean=fade, trials=10, steps=32)
    hero.append(dict(fade_per_year=fade, verdict=r["verdict"], build=r["build"], gain_vs_plain=round(r["mean_gain"], 1), p10_gain_vs_plain=round(r["p10_gain"], 1), reasons=r["reasons"], warnings=r["warnings"]))
out["hero_capacity"] = dict(tags="fade ASSUMED (Tim Ren 20,000-cycle claim implies 0.004 to 0.012); value CITED/DERIVED; switch cost CITED range 7 to 24", rows=hero)

sites = {}
for name, base in PR.PRESETS.items():
    rows = []
    for fade in (0.004, 0.008, 0.02):
        kw = dict(base, fade=fade)
        vs = E.value_streams(seeds=range(10), **kw)
        lb, d = E.break_even("lam", 0.0, 0.1, seeds=range(6), iters=10, **kw)
        rows.append(dict(fade_per_year=fade, streams={k: (round(v, 1) if k != "variant" else v) for k, v in vs.items()}, fault_rate_break_even=(round(lb, 4) if lb is not None else None), direction=d))
    sites[name] = dict(inputs=base, notes=PR.NOTES, rows=rows)
out["site_value"] = dict(tags="all site inputs ASSUMED", sites=sites)

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
packs = [np.array(v) for v in car.values()]
out["backup_hours"] = dict(tags="cell data REAL (Nature Energy 2026, 12 cars); 60 kWh, 5 kW load, no solar; grid restoration times REAL (EIA-861 Table 11.3)",
                           plain=round(float(np.median([min(S.hours(c, 60.0, 5.0, False, 1.0, None), 72) for c in packs])), 1), managed=round(float(np.median([min(S.hours(c, 60.0, 5.0, True, 1.0, None), 72) for c in packs])), 1),
                           managed_shed60=round(float(np.median([min(S.hours(c, 60.0, 5.0, True, 1.0, None, 0.6), 72) for c in packs])), 1),
                           grid_restoration_hours=dict(us_typical=1.9, us_major_events_2025=3.3, maine_2024=8.0, florida_2024=12.4))

def win(path):
    r = [json.loads(l) for l in open(path)]
    return dict(draws=len(r), beats_best_rival_pct=round(100 * np.mean([x["ours"] > x["rival"] for x in r])), beats_plain_pct=round(100 * np.mean([x["ours"] > 0 for x in r])), median_margin=round(float(np.median([x["margin"] for x in r])), 1))
out["stress"] = dict(sourced=win("examples/reon_hero_stress_sourced.jsonl"), long_life_fade=win("examples/reon_hero_stress_longlife.jsonl"), site_driven_fade=win("examples/reon_hero_stress_sitefade.jsonl"),
                     verdict_hostile="96 hostile packs, 0 false BUY (examples/reon_adversary.py)", policy_chooser="regret 1.1 per kWh mean over 300 hostile sites (examples/reon_events_selector_test.py)")
out["unknown_ask_reon"] = ["measured cell-to-cell spread on the 20,000-cycle sodium cells", "field fault rate per cell or string-year", "cost and lead time of a service visit", "switch conduction resistance and per-cell cost split", "DC string voltage and inverter minimum input", "command interface and latency", "sensing accuracy definition and rate"]
json.dump(out, open("numbers.json", "w"), indent=1)
print("wrote numbers.json", len(json.dumps(out)), "bytes")
