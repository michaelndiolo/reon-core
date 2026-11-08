# reon_adversary assumptions (all tagged "assumed" unless sourced in docs/SOURCES.md)

- Start caps: mean 100, spread 2%/sqrt(p), fade CV 0.45/sqrt(p), 250 series positions as ONE string (m = 250), window 0.9, switch cost 15.5, loss 0.04, closed loss 0.02, value 40 per kWh-year, 12 years: copied from reon_storefront (as used there).
- Clustered weak: 3 clusters x 10 adjacent positions, 12% weaker, weak_corr 0.8 (assumed). Fade cannot be set per cell in wear_scan, so "shared bad batch fades faster" is approximated by weak_corr (assumed).
- Outliers: 3 positions 45% below the pack, weak_corr 0.5 (assumed).
- Fail-open: capacity 0 from day 1 (assumed; wear_scan has no mid-run fault). reon_storm hours for a failure at hour 10 stored in meta, not in $/kWh.
- Cold sag: capacity x 0.75 (assumed), switch loss 0.10 and closed-path loss 0.05 (assumed, stand-ins for higher resistance). Both are parameters of gen_cold_sag.
- Slow / fast wear: fade 0.002 / 0.03 per year (assumed; storefront grid is 0.004-0.02).
- Correlated: weak_corr 0.9, start spread 3x default (assumed).
- Baselines: 2.5% and 5% balancers (transfer limit; 5% is the repo's own unsourced rival assumption), balancer cost 4 per kWh, eta 0.9. Hybrid wear sharing credited (hybrid_shares_wear=True), as in the balancer sweep.
- Draw = one start-cap draw plus one wear_scan seed (trials 6, steps 40: fast, noisier than the verdict's 8-16 trials); regret threshold 0.50 $/kWh (given).
