"""Write docs/stress/adversary_results.md from examples/data/adversary_vs_guard.json and examples/data/slow_recovery.json (so the numbers in the write-up cannot drift from the runs).
Run: PYTHONPATH=. python examples/make_adversary_report.py"""
import json
import numpy as np
from hackkit import reon_demo as DM

d = json.load(open("examples/data/adversary_vs_guard.json"))
a = DM.adversary_summary()
seeds = sorted({int(k.split("|")[1]) for k in d})
behind = [(k, b, x["regret"]) for k, v in d.items() for b, x in v.items() if b.startswith("balancer") and "error" not in x and x.get("regret", 0) > 0.01]
behind_txt = "; ".join(f"{k} vs {b}: {r:.2f}" for k, b, r in behind) or "none"
names = {"base": "base", "clustered_weak": "clustered weak cells", "outliers": "outliers", "fail_open": "dead cells", "cold_sag": "cold, stand-in (capacity x0.75, losses 10%/5%)",
         "cold_m20": "cold, -20 C (95% capacity, cited)", "cold_m40": "cold, -40 C (85% capacity, cited)", "slow_wear": "slow wear (0.2% a year)", "fast_wear": "fast wear (3% a year)",
         "correlated": "weak cells fade fastest, wide start spread", "batch_fade": "neighbouring cells age together (blocks of 10, 60% shared)"}
lines = ["# Hostile-case results (guarded policy vs the adversary cases)", "",
         "Run: `PYTHONPATH=. python examples/reon_adversary_vs_guard.py 4` repeatedly until it says `done N of N`, then `PYTHONPATH=. python examples/make_adversary_report.py`. Raw output: `examples/data/adversary_vs_guard.json`.", "",
         f"What was run: {len(a['cases'])} case types x 3 wirings (1, 4, 16 cells in parallel) x {len(seeds)} seeds = {a['runs']} hostile packs. The guarded policy (`reon_policy`) picks a build on one scan (16 trials) and is scored on the draw's own seed with 24 trials, "
         "against the customer's rivals: plain string, 2.5% balancer, 5% balancer. The policy does not know which hostile case it is in.", "",
         f"Result: worst shortfall against the better of plain or a balancer = **${a['worst_regret']:.2f} per kWh** over all {a['runs']} runs; {len(behind)} run(s) were behind at all ({behind_txt}), the rest were level or ahead. The repo's tolerance is 0.50 per kWh. "
         f"Against hindsight (the best build of everything, 5% balancer as the rival) it left at most about ${a['hindsight_gap_5']:.1f} per kWh on the table.", "",
         "| Case | Runs where it builds switches | Runs |", "|---|---|---|"]
for k, (b, n) in a["cases"].items():
    lines.append(f"| {names.get(k, k)} | {b} | {n} |")
tot_b = sum(b for b, _ in a["cases"].values())
lines += ["", f"It builds in {tot_b} of {a['runs']} runs and says a balancer is enough in the rest.", ""]
try:
    sr = json.load(open("examples/data/slow_recovery.json"))
    lines += ["## Slow recovery between two outages (energy budget)", "",
              "Second-outage hours when the grid is back for only a few hours and a 10 kW charger (assumed, about C/6) refills a 60 kWh store before a 5 kW load starts again. Median of 12 real car packs, window 0.9, switch loss 2%.", "",
              "| Cell open from outage 1 | Cold factor | Recharge hours | Plain string | Cell-level control |", "|---|---|---|---|---|"]
    for r in sr:
        lines.append(f"| {'yes' if r['failed'] else 'no'} | {r['cold']:.1f} | {r['recharge_h']} | {r['plain_h']:.1f} h | {r['control_h']:.1f} h |")
    lines += ["", "Reading it: with no dead cell and a slow recharge, the charger is the limit and the switches add nothing (a fraction of an hour either way). With a cell left open, a plain string delivers nothing and cell-level control keeps the lights on whatever the recharge time.", ""]
except OSError:
    pass
lines += ["## What is and is not covered", "",
          f"- Seeds: {len(seeds)} per case and wiring ({', '.join(map(str, seeds))}).",
          "- Dead cells arriving over the years (not frozen from day 1) are covered by the string-life stress test in `docs/STRESS.md` (`reon_events_adversary.py`, 300 hostile site draws). The dollar run here freezes dead cells at day 1 because `reon_wear` has no mid-run fault; the mid-storm timing comes from `reon_storm`.",
          "- Cold: capacity from one published sodium-ion cell (a vendor's NFPP cell: about 95% of room-temperature capacity at -20 C, over 85% at -40 C; Heiwit qualification test, 2026). The extra switch and closed-path loss at cold is ASSUMED. This is a capacity-and-loss stress, not an electrochemical temperature model, and it is one vendor's cell, not REON's.",
          "- Correlated fade: `reon_wear.wear_scan` now takes `batch_len` and `batch_corr`, so neighbouring cells share part of their fade variance (a bad batch ageing as a block). Plus the older weak-cells-fade-fastest case.",
          "- Slow recovery: modelled as an energy budget between two outages (above). Rest-voltage rebound and per-cell charge-rate limits are NOT modelled.",
          "- All inputs assumed unless stated; no REON data. See `adversary_assumptions.md`.", ""]
open("docs/stress/adversary_results.md", "w").write("\n".join(lines))
print("\n".join(lines[:14]))
