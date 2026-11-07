"""One file every dashboard page reads: numbers.json. Run: PYTHONPATH=. python examples/export_numbers.py
Every block carries its source tags, so a front end can show REAL / CITED / ASSUMED beside the number."""
import csv, json, datetime
import numpy as np
from hackkit import reon_events as E, reon_guard as G, reon_presets as PR, reon_storm as S

out = {"generated": datetime.date.today().isoformat(), "units": "net value per kWh nameplate, present value, unless stated", "note": "Simulations and replays only. Hardware keeps safety authority."}

# Hero numbers come from the SAME precomputed 250-cell cases the dashboard shows (examples/data/storefront_cases.json), so no page can disagree with another.
# 60 kWh, switch cost 15.5 per kWh, value 40 per kWh-year, one large cell per position; gain is the 12-year net value per kWh nameplate against a plain string.
from hackkit import reon_storefront as SF
hero = []
for fade in (0.004, 0.008, 0.02):
    c = SF.cached_core(1, fade, 40)
    hero.append(dict(fade_per_year=fade, verdict=c["verdict"], build=c["build"], gain_vs_plain=round(c["dollars_per_kwh"], 1), p10_gain_vs_plain=round(c["p10_per_kwh"], 1), reasons=c["reasons"], warnings=[]))
out["hero_capacity"] = dict(tags="250 cells in series, one large cell per position; fade ASSUMED (Tim Ren 20,000-cycle claim implies 0.004 to 0.012); value CITED/DERIVED; switch cost 15.5 (CITED range 7 to 24). Does NOT enforce the inverter voltage window for the late-switch build: see docs/SOURCES.md", rows=hero)

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
_pl, _mg, _sh = SF.backup_policies({k: np.array(v) for k, v in car.items()}, 60.0, 5.0)
out["backup_hours"] = dict(tags="cell data REAL (Nature Energy 2026, 12 cars); 60 kWh, 5 kW, cold-weather capacity 80% (same as the dashboard); boundary: string DC terminals, no inverter loss, no solar; grid restoration times REAL (EIA-861 Table 11.3)",
                           plain=round(_pl, 1), managed=round(_mg, 1), managed_shed50=round(_sh, 1),
                           grid_restoration_hours=dict(us_typical=1.9, us_major_events_2025=3.3, maine_2024=8.0, florida_2024=12.4))

def win(path):
    r = [json.loads(l) for l in open(path)]
    return dict(draws=len(r), beats_best_rival_pct=round(100 * np.mean([x["ours"] > x["rival"] for x in r])), beats_plain_pct=round(100 * np.mean([x["ours"] > 0 for x in r])), median_margin=round(float(np.median([x["margin"] for x in r])), 1))
out["stress"] = dict(sourced=win("examples/reon_hero_stress_sourced.jsonl"), long_life_fade=win("examples/reon_hero_stress_longlife.jsonl"), site_driven_fade=win("examples/reon_hero_stress_sitefade.jsonl"),
                     verdict_hostile="96 hostile packs, 0 false BUY (examples/reon_adversary.py)", policy_chooser="regret 1.1 per kWh mean over 300 hostile sites (examples/reon_events_selector_test.py)")
out["unknown_ask_reon"] = ["measured cell-to-cell spread on the 20,000-cycle sodium cells", "field fault rate per cell or string-year", "cost and lead time of a service visit", "switch conduction resistance and per-cell cost split", "DC string voltage and inverter minimum input", "command interface and latency", "sensing accuracy definition and rate"]
json.dump(out, open("numbers.json", "w"), indent=1)
print("wrote numbers.json", len(json.dumps(out)), "bytes")
