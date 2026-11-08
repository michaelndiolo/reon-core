# Hostile-case results (guarded policy vs Aaryan's adversary cases)

Run: `PYTHONPATH=. python examples/reon_adversary_vs_guard.py 4` until it says `done 48 of 48`. Output: `examples/data/adversary_vs_guard.json`.

What was run: 8 case types (base, clustered weak cells, outliers, dead cells, cold night, slow wear, fast wear, correlated fade and wide start spread) x 3 wirings (1, 4, 16 cells in parallel) x 2 seeds = 48 hostile packs. The guarded policy (`reon_policy`) picks a build on one scan (16 trials); it is scored on the draw's own seed with 24 trials, against the customer's rivals: plain string, 2.5% balancer, 5% balancer.

Result: the policy was never behind the better of plain or a balancer (worst regret $0.00 per kWh, 48 of 48, at both balancer strengths). It builds switches in 32 of 48 runs and says "a balancer is enough" in the other 16 (all of the 16-parallel base, cold and slow-wear runs, most 4-parallel base/cold runs). Against hindsight (the best build of everything, with a 5% balancer as the rival) it left at most about $1.5 per kWh on the table.

Per case (runs where it builds, of 6): base 2, clustered 6, outliers 6, dead cells 6, cold 2, slow wear 1, fast wear 5, correlated 4.

Storm hours with a cell failing open at hour 6, 5 kW, 12 real car packs, by cold-weather capacity factor (plain / cell-level control / control shedding half the load): 1.0: 6.0 / 10.1 / 20.1; 0.8: 6.0 / 8.1 / 16.1; 0.7: 6.0 / 7.1 / 14.1; 0.6: 5.9 / 6.1 / 12.1.

Limits (say these out loud): only 2 seeds per case. "Dead cells" are frozen at their end state from day 1; reon_wear has no mid-run fault, so the mid-storm timing comes from reon_storm, not from the dollar run. Cold is capacity x 0.75 with higher switch losses (a stand-in, not temperature physics). Correlated fade is approximated by weak cells fading faster (weak_corr 0.9); wear_scan cannot set fade per cell. "Slow" and "fast" are wear rates (0.2% and 3% a year), not a rest-voltage recovery model; rest recovery after a discharge is not modelled. All inputs assumed (see adversary_assumptions.md); no REON data.
