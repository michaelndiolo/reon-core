# Policy stress test: assumptions (hackkit/reon_policy_stress.py, examples/reon_policy_stress.py)

Everything not already in reon_wear / reon_storefront is listed here. Physics (capability, depth of discharge, fade, knees) is reon_wear._step and the wear_scan fade line, unchanged.

| Item | Value | Status |
|---|---|---|
| Fresh pack per draw | day-1 capacities 100 x (1 + 0.02/sqrt(p) x N(0,1)), own seed (seed + 7,000,000); same shape as reon_storefront._start | assumed (the headline uses one fixed pack, seed 3) |
| In-service capacity reading | one reading per time step (60 over 12 years), noise 1% (OBS_SIGMA) | assumed |
| Policies know the scenario prior | fade mean and spread, costs, value; never the draw's fade rates or true capacities | assumed (the headline also takes the fade as an input) |
| In-sample choice (b, GUARDED) | 4 prior draws per pack; prior truth = day-1 test x (1 + 2% noise); guard margin $0.50/kWh | assumed, chosen before running |
| Weaker balancer cost (d) | $4/kWh flat, as the repo's 5% balancer (no source for strength vs cost). Extra "cost scaled" rows: 4 x r / 5% | assumed (both) |
| Rotating rest (a, c) | a rested cell passes `frac` of its Ah; the rest of the string carries the deficit / (1 - loss); lost energy charged at 365 cycles/yr x $0.15/kWh | assumed |
| Full switches + balancer (a) | capability = reon_wear hybrid on the kmax weakest cells right now, closed-path loss charged on every cell | approximation |
| e. deferred / moved switches | NOT a repo build: 5% balancer from day 1; k bypass switches fitted at a service visit (year 6, or years 3+6+9) on the cells observed (or projected by a straight-line fit) weakest at that time. Switch cost discounted to the first visit. Retrofit fee 0 | assumed hardware and service model; break-even fee reported |
| Sag energy mapping (line 3) | per-discharge energy from reon_sag.usable_fraction: each build closes the same share (rho, from the Ah model) of the sag model's gap between plain and its ceiling (best of a perfectly balanced string and every cell bypassable, both under the floor), then the closed-path loss; scaled by a balanced fresh pack's usable energy so day 1 is about 1 x nameplate and the 70% retirement line keeps its meaning | assumed mapping (the balancer is not in reon_sag) |
| Regret | per scenario: max(0, best baseline-group mean picked in hindsight - policy mean). Per-draw oracle regret also reported (no ex-ante policy can reach 0 there) | definition |
