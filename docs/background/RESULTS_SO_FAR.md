# Results so far (2026-11-07). Read the tags before quoting anything.

Reproduce: `python examples/reon_real_prices.py <folder with SMARD price_2024.json, price_2025.json>` and `python examples/reon_carbon_example.py`
(outputs saved beside the scripts). Prices REAL (SMARD day-ahead, Germany, CC BY 4.0); cell spreads CITED (docs/REON_DATA.md); site, battery, tariff, and
every other input ASSUMED. No Reon number is used anywhere.

## 1. Energy value of the extra usable capacity (arbitrage only, 2 MWh with-control pack, 1 MW, one discharge cycle a day, no demand charge)

| Spread used (source) | Extra capacity | Value, EUR per year (90% over 26 two-day windows) | Per extra kWh |
|---|---|---|---|
| BMW i3 module 3 (CITED, 1.2% mismatch) | 24 kWh | 492 (390 to 602) | 20.6 |
| BMW i3 module 2 (CITED, 1.7%) | 34 kWh | 704 (558 to 858) | 20.6 |
| BMW i3, all 36 cells (CITED, 7.2%) | 134 kWh | 2,924 (2,331 to 3,528) | 21.9 |
| BMW i3 module 1, one outlier cell (CITED, 9.4%) | 172 kWh | 3,847 (3,054 to 4,668) | 22.4 |
| Nissan Leaf, 8 cells (CITED, 18.6%) | 314 kWh | 7,306 (5,831 to 8,864) | 23.2 |
| HYPOTHETICAL 2x (vendor claim, unverified) | 1,000 kWh | 27,971 (22,707 to 33,520) | 28.0 |

Reading it: with published retired-cell spreads, control's mismatch benefit is worth roughly 20-25 EUR per extra usable kWh per year of arbitrage. Only a
"2x" claim (which the published spreads do not support) produces five-figure numbers. The window spread is the only uncertainty shown: price level,
site, wear and the one-cycle cap are ASSUMED, and windows are not a full year (annualized by x365/2).

## 2. Is the scheduler's cleverness doing the work? (leave-one-window-out, same 26 windows, planner given the true prices)

Planner beat a price-rule tuned without the scored window in 16 of 26 windows; mean improvement 0.9% (90% range -0.1% to 2.0%). With a one-cycle-a-day
battery and no demand charge the edge is small. The value in section 1 comes from the extra capacity, not from a clever scheduler. Do not pitch the scheduler as the edge.

## 3. Carbon (2 MWh pack; see examples/reon_carbon_example_output.txt)

Net over the pack's second life: base 4.8 t CO2e, but 2.0 t BELOW zero to 36 t above over the ranges, so the sign can flip. The cited input (embodied carbon of
a new battery, 61-106 kg CO2e/kWh, IVL 2019) is not the biggest driver: the assumed extra capacity and the assumed share that would really have been
new-built are. State the carbon claim as conditional on those, or get them from Reon.

## 4. Life extension (`reon_aging.py`, hand-tested; exponent range now sourced to BLAST-Lite models)

With equal energy delivered, conventional cycles the weakest cell deepest and control cycles every cell equally, so the life ratio is (mean/min)^k.
Implied k from NREL BLAST-Lite models (BSD-3-Clause; 1 cycle/day, 25 C, 600 days; `examples/blast_k_from_models.py`): 0.96 (NMC811-GrSi, LG MJ1), 2.26 (NMC622-Gr,
DENSO), 1.08 (LFP-Gr 250 Ah), 1.58 (NCA-Gr, Panasonic). The Leaf second-life model (LMO-Gr, fit to Braco et al.) is throughput-only, i.e. k = 1 for its cycle part.
BLAST-Lite calls its models qualitative (1-3 years of accelerated data) and four of these are new-cell models, so use 0.96 to 2.26 as a range, not a prediction.

Life ratio (cycles to first cell end of life, control / conventional, cycle-driven part only): module 3 1.01-1.03; module 2 1.02-1.04; all 36 BMW cells 1.07-1.17;
module 1 1.09-1.22; Leaf 8 cells 1.18-1.47. Ignores calendar aging (which control does not change, so real gains in years are smaller), faster fading of the weak cell
(which would make conventional worse), temperature and C-rate. The 20,000-cycle figure on Reon's site is for new Na-ion cells, not retired Li-ion.

## 5. Value of a longer life (2 MWh pack; `examples/reon_life_value_example.py`)

Equivalent annual cost saved by the life ratios in section 4: BMW all 36 cells about $520 to $12,000 a year, Leaf 8 cells about $1,200 to $26,000 a year over lives of 3-10 years and
pack prices of $40-120/kWh; middle case (7-year life, $80/kWh, ratio 1.12) about $2,500 a year. UPPER bounds: control does not slow calendar aging, so real gains in years are smaller than the
cycle-life ratio. Pack price per kWh is ASSUMED (NREL 2015 repurposing-cost figures are dated); service life is CITED (NREL 3-10 y; Relectrify trial 6-8 y, a different company).

## Cross-check against a real field result

Relectrify's published trial of cell-level control on retired Leaf packs reports more than 20% extra usable capacity, 2-3% fade a year and 6-8 years projected life (docs/REON_DATA.md, 2b).
That sits inside our spread-based range (7% to 27%) and far from a 2-3x gain. It is another company's product: it supports the order of magnitude, not Reon's claim.

## What is not done

Pack purchase price actually paid (ask Reon; NREL 2015 figures only); any Reon data (see questions in REON_DATA.md); demand-charge case on real
site data; the independent pack check against Aaryan's `pack.py` (reference is `recheck/pack_ref.py`, compare with `pack_ref.compare`).

## Three honesty checks on the capacity gain (2026-11-07; `hackkit/reon_window.py`, `hackkit/reon_spread.py`; output in `examples/reon_window_spread_output.txt`)

Inputs: the published cell tables (CITED). Window fractions and measurement errors are ASSUMED test values. The checks are ours, built from patterns in the participant notes (Pareto front, leave-one-out, leakage canary); nothing is REON's measured behavior.

1. **Voltage window.** The ideal model uses the sum of all cells, which needs bypassing cells one by one until a single cell remains. A converter that needs at least n_min of the N series cells in circuit gets usable = sum of min(c_i, n_min-th largest). On the BMW modules most of the gain survives a narrow window only because of one cell: module 1 keeps 83% of its ideal gain with 90% of the cells required, all 36 keep 64%, modules 2 and 3 keep only 26-41% at 90% and 80%. The Leaf set keeps 59% (10.9 points) only when the window is as wide as 50% of the cells; with 8 cells a 90% requirement means all 8, so the gain is zero. So the quoted gains are upper bounds that assume a very wide input window. New ask for REON: what share of a string's cells must stay in circuit.
2. **Fragility to one cell.** Gain = mean/min - 1 hangs on the weakest cell. Removing the single weakest cell cuts the gain from 9.4% to 1.6% in BMW module 1 (83% of it) and from 7.2% to 3.3% for all 36 (54%). So the BMW headline rests on one 84.3 Ah cell; whether it is a real weak cell or a bad reading must be checked. `contract.check_cells` flags it as a weak cell (9% below the median) only if its cut-off is set to 5%; at the default 15% nothing is flagged, and telling a weak cell from a bad sensor needs voltage readings, not capacities alone. In the Leaf set removal raises the gain (18.6% to 20.1%), because the low end is two similar weak cells and the spread is broad.
3. **Measurement noise inflates the gain.** The weakest *measured* cell is biased low, so a gain computed from noisy capacity estimates is biased high. If capacities carried 1% / 2% / 3% error, matched BMW modules 2 and 3 would show 2.1-2.5% / 3.6-3.9% / 5.4-5.6% apparent gain against 1.2-1.7% in the tables, so their small published gains are within what noise alone could produce. Module 1 and the Leaf set are barely affected. The measurement error of the published tests was not checked (open).
4. **Independent cells are a rough guide only.** The independent-normal model at the observed spread predicts 5.4% for all 36 BMW cells (published 7.2%, a heavy tail) and 25.7% for the Leaf set (published 18.6%, 90% range 11-49%). Use it for ballpark only.

Consequence for the pitch: say "gain is large only when the weakest cells are far below the rest (retired Leaf-type packs) and the converter accepts a wide window; for matched cells it is within measurement noise and within a 2% switching loss". That is more credible than a single percentage.

## Carbon: where the displaced cells are made, and where the sign flips (2026-11-07; `hackkit/reon_carbon.py`, output in `examples/reon_carbon_origin_output.txt`)

Idea source: topic only of a public LinkedIn post by an IBM summer intern (author not identified, no method given) about monitoring and modeling supplier emissions. We turned it into: embodied carbon of a new battery = non-electric part + electricity per kWh x the grid where it is made. Structure CITED to the IVL/Energimyndigheten 2017 report (65 kg non-electric, 160 kWh electricity per kWh of battery, grids Sweden 50, Brazil 300, USA 700, China 1000, Poland 1050, India 1400 g/kWh); it reproduces the report's Table 17 to about 2 points. It is dated and one manufacturer's data, and it runs HIGH against IVL's 2019 range (61-106, up to 146). The regional mix of displaced cells is ASSUMED.

- Embodied carbon by region (kg CO2e/kWh): Sweden 73, Brazil 113, USA 177, China 225, Poland 233, India 289.
- Net carbon for the 2 MWh example (other inputs as in the earlier carbon example): 4.8 t with IVL 2019 (range 61-106), 13.3 t for an assumed 70% China / 30% USA mix, 4.1 t if all displaced cells were made in Sweden. Origin changes the size by about 3x. It does not decide the sign.
- **Flip points** (one input at a time, others at base; `flip_point`, `flip_table`): the net turns negative if fewer than about 7% of the extra capacity would really have been bought new (base assumption 50%; inside its range), if the extra capacity is below about 19 kWh (about 1% of 2 MWh; the low end of our range is 24), if the electronics carry more than about 5.6 t CO2e, or if embodied carbon of a new battery is below about 12 kg/kWh (far below any source). So the carbon claim stands or falls on the displaced share, which nobody has measured, and not on factory location.
- Pitch line: "carbon benefit is positive unless almost none of the extra capacity would have been built new; the size depends on where the replaced batteries would have been made".

## What would have to be true for "2-3X" (2026-11-07; `hackkit/reon_claim.py`, output in `examples/reon_claim_output.txt`)

Pattern: "what would have to be true" (participant notes). The meaning of "2-3X" is unknown, so we test two readings. Targets 2 and 3 are REON's public wording; the normal-capacity and lognormal-fade-rate shapes and linear fade are ASSUMED. Results cross-checked with an independent 200,000-draw simulation (within about 0.03 of target).

- **Reading A, usable energy today versus a weakest-cell-limited pack.** Needs a capacity spread (coefficient of variation) of about 22-29% for 2X and 28-36% for 3X, depending on string length (8 to 36 cells). Observed: BMW modules 0.8-2.8%, Leaf cells 13.8%. So the published retired sets are 2 to 30 times too uniform to give 2X. If the converter must keep 90% of the cells in circuit, 2X is not reachable at any spread up to 100%; with a 50% requirement it needs 24-31%.
- **Reading B, service life.** If cells fade linearly at their own rates, the life ratio is the fastest rate divided by the mean rate, whatever the end-of-life level (brute-force checked in the tests). 2X needs the fade rates to vary by about 36-62% (CV) across 36 to 8 cells; 3X needs 63-146%. No fade-rate data exist for the cells in our sources, so this cannot be compared with data yet.
- **Conclusion.** Neither reading reaches 2-3X from the mismatch we can document. So "2-3X" probably compares against something else: a pack scrapped when any cell hits an SoH limit, a pack the old BMS cannot use at all, or new-cell nameplate. This is the most useful single question for the REON mentors (draft question 1 now says so).

## Is control cheaper than just adding more cells, and how likely are the answers? (2026-11-07; `hackkit/reon_unit.py`, `hackkit/reon_mc.py`; output in `examples/reon_unit_mc_output.txt`)

Techniques taken from a public Medium post on nuclear-waste reprocessing economics (Rhythm Doshi, Dec 2023, a secondary summary of a published cost-probability analysis): triangular (low, mode, high) distributions for uncertain unit costs with Latin hypercube Monte Carlo, and cost buckets reduced to a cost per unit. The reprocessing numbers themselves are unused. A second post by the same author (pyroprocessing chemistry) has nothing for batteries. In the economics post the units are mixed in places (a per-pound uranium price quoted per kg) and one discount factor is written two ways, so we cite the technique, not the figures.

Tags: gains CITED (published cell tables, ideal sum); electronics cost 8.3-9.2 EUR per kWh of nameplate CITED to the Chalmers study of NEW EV packs (not REON's cost); new-cell alternative 98.4 EUR/kWh CITED (Chalmers/BNEF 2024); cheap retired capacity 20-60 EUR/kWh ASSUMED (NREL 2015 repurposing cost, excludes the price paid for used cells, so a floor); value of an extra usable kWh 20.6-23.2 EUR/yr from our REAL German price run (assumed battery); triangular shapes ASSUMED.

- **Cost per extra usable kWh** = e x (1 + g) / g, because nameplate = usable x (1 + g). It runs from about 53-59 EUR for the Leaf set (g 18.6%) and 97-107 for BMW module 1 to 124-137 for all 36 BMW cells and 500-780 for the matched modules 2 and 3.
- **Payback** (no discounting): Leaf 2.3-2.5 years, BMW module 1 4.3-4.8, all 36 cells 5.6-6.3, modules 2 and 3 24-38 years (longer than any pack lasts).
- **The competitor is not only a conventional BMS.** Control beats simply adding more cells only above a break-even gain: 9.8% against new cells at 98.4 EUR/kWh, 17.2% against retired cells at 60, 28.2% at 40, 78.6% at 20. So against cheap retired capacity only the Leaf-type spread wins on cost alone. Control still wins where there is no room, weight, voltage headroom or cell supply for extra cells (not priced here), and against a conventional BMS on the same cells it always adds value; say which comparison is meant.
- **Probability under our ranges (not frequencies in the world):** payback within 7 years in 75% of draws for the 36 BMW cells (median 5.7 years) and in 100% for the Leaf set (median 2.4). Carbon: net below zero in about 1% of draws, 5/50/95 percentiles 0.8 / 5.3 / 13.5 t CO2e (corners -2.0 to 35.1), so the sign flip is possible but unlikely if the guessed ranges are right.
- Caveat: all gains here are the ideal sum. A 2% switching loss or a limited converter window lowers them (see the honesty checks above), which lengthens the paybacks.

## One-command report and a discounting catch (2026-11-07; `hackkit/reon_report.py`, `examples/reon_pack_report.py`, outputs `examples/reon_pack_report_*_output.md`)

`analyze_pack` and `render_markdown` combine the pack model, loss, window, fragility, noise, data checks, economics and life into one tagged report from a CSV of cell capacities, with no default for efficiency, cost, value or fade. Sample data: `examples/data/leaf_8.csv`, `bmw_36.csv`.

Catch from running it on the 36 BMW cells with a 7% discount rate over 7 years: the levelized yearly cost per extra kWh (131.6 x 0.1856 = 24.4) is above the yearly value (21.9), so the undiscounted 6.0-year payback hides that it does not quite repay once money has a cost. The Leaf set (10.4 against 23.2) and BMW module 1 (about 19 against 22.4) still do. The earlier "payback within 7 years in 75% of draws" for the 36 BMW cells is an undiscounted statement.


## Control vs sorting into matched strings (reon_sorting; examples/reon_sorting_output.txt)
Strings of m cells in series, in parallel; a string delivers m x weakest. Sorting is optimal for equal strings (brute-force checked). REAL (computed) from CITED capacities; the sorting test error is ASSUMED.
- BMW 36 cells: control beats perfectly sorted strings by 2.3% (3 x 12), 1.0% (6 x 6), 0.6% (9 x 4); break-even switching loss 2.2%, 1.0%, 0.6%. The 3 x 12 case is the real BMW modules as found (3126 Ah) vs sorted 3180 vs control 3252.
- Leaf 8 cells: control beats sorted by 3.0% (4 x 2) and 9.7% (2 x 4); break-even loss 2.9% and 8.8%.
- Sorting with a 2% test error loses little of the sorting gain on these spreads. The cost of testing every cell is not counted.
- Money flip points (`repay_thresholds`, Leaf after 2% loss, 7% over 7 years, value 22): repays up to electronics 16.6 per kWh; needs gain >= 8.0%; can take 7.1% more loss.

## Closing the gap on well-matched cells (reon_granularity, reon_drift; examples/*granularity*, *drift*, *screen* outputs)
- Switch spacing (BMW 36 cells, 2% cell-level loss, 8.8 per kWh cell-level electronics CITED analog, value 22 REAL, 7% over 7 years): per-cell net value -0.60 per nameplate kWh-year; k=4..9 as found +0.48 to +0.63, sorted +0.81 to +0.90 (best k=6). Fails if electronics cost does not fall with fewer switches (q=0). ASSUMED scalings p (loss) and q (cost).
- Drift (mean fade 4%/yr, end of life 50% of day-1 nameplate, loss 2%, all ASSUMED): control life vs sorted-once strings: BMW 3x12 +0.2%, +22%, +46%, +78% at fade CV 0, 0.15, 0.30, 0.50; BMW 6x6 -1.0%, +16%, +35%, +60%; Leaf 2x4 +8%, +16%, +30%, +52%. Worst corner over weak-cell correlation -0.9..+0.9: +6.7%. Break-even fade CV 0 to 9%.

## One engine: reon_design (examples/reon_design_*.txt)
Net value = present value over the service period per kWh of nameplate vs the plain pack of the same string length; all ageing, retirement, loss-scaling and cost-scaling inputs ASSUMED; cell data CITED; value 22 REAL.
- BMW 36 cells, strings of 12, retire at 70%, fade 4%/yr, 7 yrs: plain pack in service 5.4 of 7 yrs; robust pick = switch on every cell, cells as found (best in 11 of 12 assumption sets), net +5.5 to +16.0; sort-only is never worth paying for.
- Same pack, retire at 50%: plain pack in service 7.0 of 7 yrs; robust pick = sort only (net +0.5 to +0.7); sorting must cost under about 0.5 per kWh nameplate to beat switches.
- Flip points (BMW 3x12, one at a time): electronics > ~16, retire level <= 60% or 90%, loss >= 5%, service <= 5 yrs, value <= ~11, fade <= 3%/yr, fade-rate spread 0, weak cells fading slower (-0.9), all flip away from switches.
- Closed-switch loss 0.5 to 2%: no change.

## Tested against everything (examples/reon_design_everything*, *regime_map*, *vs_balancer*)
- Active balancer model: charge moves at efficiency 90% (ASSUMED), each cell can exchange at most r x mean capacity per discharge (r ASSUMED; LTC3300 'up to 10 A' is a vendor-article anchor). Passive balancing = plain pack. Converter loss 3% (ASSUMED).
- BMW 3x12, retire 70%, balancer free: switches +11.1, balancer r=5% +11.1, 10% +17.8, 20% +21.7, unlimited +22.2. Leaf 4-strings: switches +28.0, balancer 10% +27.4, 20% +37.9.
- Balancer cost equal to switches (8.8): switches beat r<=10% at CV 2 to 25%, r=20% from CV 10%; dead-cell string: switches +94 vs balancers <= 50% limit +0 or -8.8.
- Break-even balancer cost at r=10% (BMW 3x12): about 7 to 9 per kWh. Balancer efficiency 70 to 95% and switch loss 0.25 to 2% do not flip the winner. Switch electronics <= 2 per kWh flips it.
- Buying extra cells: switches cheaper only above 27 to 53 (BMW 3x12, 70%), 15 to 16 (Leaf, 70%), 117 to 207 (BMW 3x12, 50%) per kWh.

## Late engagement and hybrid (examples/reon_design_hybrid*, *late_vs_balancer*)
- BMW 3x12, retire 70%, switches 8.8, balancer 8.8 (ASSUMED): plain 0; sort only +1.0; switches engaged always +11.1; late-engaging +13.4; balancer 5/10/20% +2.3/+9.0/+12.9; hybrid separate hardware +4.6, shared +13.4. Leaf 4-strings: late +30.8, balancer 20% +29.1, hybrid shared +30.8.
- Closed-switch loss 0 to 2%: late switches beat the 10% balancer throughout, the 20% balancer only below about 0.4%.
- Hybrid minus the better parent (shared hardware, 24 cells): +0.1 to +0.3 at 2% loss; +1.2 to +5.3 at 5 to 10% loss with CV 15 to 25%. Separate hardware: loses.
- Retire at 50%: late -1.0, balancers -1.2 to -4.5, sort only +0.6.


## Round: closing the balancer gap (calibrated, with failures)

See docs/WHAT_WE_HAVE.md section 3f. A free balancer cannot be beaten on cost; ours wins iff retire level >= ~70%, electronics <= balancer cost, closed-switch loss <~0.4%, or cells fail (>=~0.5%/cell-year with no repair, >=~5% with 91-day repair). Fade CV calibrated to Nature Energy 2026 (0.087 cars, 0.111 buses). Tests: full suite green.

## Round 3: wear, knees, cost to win (examples/reon_wear_*)
- Iowa fit: fade ~ DoD^0.7 to 0.9; 65% of cells knee (2.4x, from 0.855). Tested in a state-dependent simulator that reproduces reon_design when both are off.
- Wear and knees add 0.1 to 1.2 per kWh, helping a charge-moving balancer equally. Well-matched packs: sort only. Free balancer with 20%+ transfer is not beatable on cost; our electronics must cost no more than the balancer's. See docs/WHAT_WE_HAVE.md 3m.

## Round 4: selective bypass and recommend_build (examples/reon_select_vs_balancer*, reon_recommend_build*)
- Switches only on the weakest cells (cost k/m) beat balancers with r <= 10% on outlier packs and beat costed balancers on the real Leaf/brief packs; only a free 20% balancer wins. See docs/WHAT_WE_HAVE.md 3n.

## Round 5: hybrid, stress, dashboard (examples/reon_stress*)
- Hybrid adds nothing against a balancer that already covers the mismatch. 612-draw stress: win 79%; loses when the balancer is cheap and moves 20%+. Recommendation now on the dashboard. docs/WHAT_WE_HAVE.md 3o.

## Round 6: free-balancer case and the tie (examples/reon_free_balancer_case*)
- Free 20% balancer: adopt it plus a switch tail = tie to +0.4. Well-matched BMW: ceiling +4.9 (retired EV); one switch on the weakest cell nets +1.8. See docs/WHAT_WE_HAVE.md 3p.

## Round 6: sourced stress, real Nature cars (7 Nov)
- Stress tests: random draws over wide ASSUMED ranges give 78-79 % wins (612 and 558 draws). With balancer current, per-cell cost and cell size coupled to published parts (DALY 1 A, Heltec 5.5 A, LTC3300-1 10 A at A$19-29 per IC; strong balancers sit on small cells so their cost per kWh is high) 768 draws give 95 % wins, median +7.6 per kWh. By pack: Leaf 92-97 %, BMW 80-92 %, brief pack 98-100 %, STABL 97-100 %. Assumed ranges that remain: extras factor 1-2.5, 1-2 A balancer cost USD 0.5-2 per cell, C-rate by application.
- Real data (Nature Energy 2026 Source Data Fig 4, 12 EVs, examples/data/nature_fig4_cells.csv): real fade-rate spread CV median 0.45 (0.26-0.57), higher than our scenario range 0.1-0.4. Late packs are mostly well matched (beta 0.86-0.98).
- Retired EV on those 12 real packs vs a 5 %/cost-4 balancer: we win 5 of 12 (median -0.1 = tie, max +6.0). Against 20 %/cost-12: 11 of 12. Grid: 12 of 12 (median +28.6).
- Break-even switch cost vs a 5 %/cost-4 balancer (per kWh nameplate, switch on every cell): retired EV median 12.1 (min 3.5, max 38.8), at or above our assumed 8.8 in 7 of 12 cars and above 4 in 11 of 12; grid median 37.4 (min 22.8), 12 of 12. This is why question 2 for REON (hardware cost per cell) matters most.
- Failure rate: STABL 2 of 324 cells faulty (0.6 %), repairable busbar contacts; EPRI gives system-level incidents only. No public per-cell-year open-circuit rate exists.
