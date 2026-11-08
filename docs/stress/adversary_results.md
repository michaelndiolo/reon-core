# Hostile-case results (guarded policy vs the adversary cases)

Run: `PYTHONPATH=. python examples/reon_adversary_vs_guard.py 4` repeatedly until it says `done N of N`, then `PYTHONPATH=. python examples/make_adversary_report.py`. Raw output: `examples/data/adversary_vs_guard.json`.

What was run: 11 case types x 3 wirings (1, 4, 16 cells in parallel) x 6 seeds = 198 hostile packs. The guarded policy (`reon_policy`) picks a build on one scan (16 trials) and is scored on the draw's own seed with 24 trials, against the customer's rivals: plain string, 2.5% balancer, 5% balancer. The policy does not know which hostile case it is in.

Result: worst shortfall against the better of plain or a balancer = **$0.48 per kWh** over all 198 runs; 2 run(s) were behind at all (fast_wear_p16|4 vs balancer 5%: 0.48; cold_m20_p1|3 vs balancer 2.5%: 0.44), the rest were level or ahead. The repo's tolerance is 0.50 per kWh. Against hindsight (the best build of everything, 5% balancer as the rival) it left at most about $3.9 per kWh on the table.

| Case | Runs where it builds switches | Runs |
|---|---|---|
| base | 6 | 18 |
| clustered weak cells | 18 | 18 |
| outliers | 18 | 18 |
| dead cells | 18 | 18 |
| cold, stand-in (capacity x0.75, losses 10%/5%) | 6 | 18 |
| slow wear (0.2% a year) | 1 | 18 |
| fast wear (3% a year) | 16 | 18 |
| weak cells fade fastest, wide start spread | 12 | 18 |
| cold, -20 C (95% capacity, cited) | 6 | 18 |
| cold, -40 C (85% capacity, cited) | 6 | 18 |
| neighbouring cells age together (blocks of 10, 60% shared) | 8 | 18 |

It builds in 115 of 198 runs and says a balancer is enough in the rest.

## Slow recovery between two outages (energy budget)

Second-outage hours when the grid is back for only a few hours and a 10 kW charger (assumed, about C/6) refills a 60 kWh store before a 5 kW load starts again. Median of 12 real car packs, window 0.9, switch loss 2%.

| Cell open from outage 1 | Cold factor | Recharge hours | Plain string | Cell-level control |
|---|---|---|---|---|
| no | 1.0 | 1 | 2.0 h | 2.0 h |
| no | 1.0 | 2 | 4.0 h | 3.9 h |
| no | 1.0 | 4 | 8.0 h | 7.8 h |
| no | 1.0 | 6 | 9.8 h | 10.1 h |
| no | 1.0 | 12 | 9.8 h | 10.1 h |
| no | 1.0 | 24 | 9.8 h | 10.1 h |
| no | 0.8 | 1 | 2.0 h | 2.0 h |
| no | 0.8 | 2 | 4.0 h | 3.9 h |
| no | 0.8 | 4 | 7.9 h | 7.8 h |
| no | 0.8 | 6 | 7.9 h | 8.1 h |
| no | 0.8 | 12 | 7.9 h | 8.1 h |
| no | 0.8 | 24 | 7.9 h | 8.1 h |
| yes | 1.0 | 1 | 0.0 h | 2.0 h |
| yes | 1.0 | 2 | 0.0 h | 3.9 h |
| yes | 1.0 | 4 | 0.0 h | 7.8 h |
| yes | 1.0 | 6 | 0.0 h | 10.0 h |
| yes | 1.0 | 12 | 0.0 h | 10.0 h |
| yes | 1.0 | 24 | 0.0 h | 10.0 h |
| yes | 0.8 | 1 | 0.0 h | 2.0 h |
| yes | 0.8 | 2 | 0.0 h | 3.9 h |
| yes | 0.8 | 4 | 0.0 h | 7.8 h |
| yes | 0.8 | 6 | 0.0 h | 8.0 h |
| yes | 0.8 | 12 | 0.0 h | 8.0 h |
| yes | 0.8 | 24 | 0.0 h | 8.0 h |

Reading it: with no dead cell and a slow recharge, the charger is the limit and the switches add nothing (a fraction of an hour either way). With a cell left open, a plain string delivers nothing and cell-level control keeps the lights on whatever the recharge time.

## What is and is not covered

- Seeds: 6 per case and wiring (0, 1, 2, 3, 4, 5).
- Dead cells arriving over the years (not frozen from day 1) are covered by the string-life stress test in `docs/STRESS.md` (`reon_events_adversary.py`, 300 hostile site draws). The dollar run here freezes dead cells at day 1 because `reon_wear` has no mid-run fault; the mid-storm timing comes from `reon_storm`.
- Cold: capacity from one published sodium-ion cell (a vendor's NFPP cell: about 95% of room-temperature capacity at -20 C, over 85% at -40 C; Heiwit qualification test, 2026). The extra switch and closed-path loss at cold is ASSUMED. This is a capacity-and-loss stress, not an electrochemical temperature model, and it is one vendor's cell, not REON's.
- Correlated fade: `reon_wear.wear_scan` now takes `batch_len` and `batch_corr`, so neighbouring cells share part of their fade variance (a bad batch ageing as a block). Plus the older weak-cells-fade-fastest case.
- Slow recovery: modelled as an energy budget between two outages (above). Rest-voltage rebound and per-cell charge-rate limits are NOT modelled.
- All inputs assumed unless stated; no REON data. See `adversary_assumptions.md`.
