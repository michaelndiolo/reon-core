# What we have, how it compares to current practice, and what to ask

Plain-language map of the REON repo. Every number is tagged REAL (we computed it from data we hold), CITED (a published number, link in docs/REON_DATA.md) or ASSUMED (a range we typed). None of the cost or efficiency numbers are REON's own; replacing them is what the questions below are for.

## 1. The one idea

A series string of cells delivers only what its weakest cell can. With a switch at every cell, each cell can run to its own end. So:

- without control: usable = N x weakest cell
- with ideal control: usable = sum of the cells
- gain = mean / weakest - 1 (REON's own slide example, 100/90/80/70 Ah: 280 vs 340 Ah, +21.4%)

Everything else asks how much of that gain survives real limits, what it is worth, and how sure we are.

## 2. What the code does (open `streamlit run app_reon.py` to see it in one place)

| Question | Module | What it does |
|---|---|---|
| How big is the gain? | `reon_loss`, `reon_report` | Gain from cell capacities; break-even loss; net gain after a switching loss |
| Does a voltage window limit it? | `reon_window` | If the converter needs a minimum share of cells in circuit, how much of the ideal gain is kept |
| Is the gain robust? | `reon_spread` | Gain with the weakest cell removed (fragility); how much measurement error alone fakes a gain |
| Is the data believable? | `contract.check_cells` | Flags weak outliers and suspect readings |
| Can "2-3X" be true? | `reon_claim` | How much cell-to-cell spread or fade-rate spread a 2X or 3X claim would need, against what is observed |
| What does an extra kWh cost? | `reon_unit` | Cost per extra usable kWh, payback, discounted yearly cost, break-even gain vs simply adding cells |
| What is it worth? | `flex`, `value_split` | Battery scheduling against German day-ahead prices (extra usable kWh about 20.6 to 23.2 per year, REAL) |
| What does it do to carbon? | `reon_carbon` | Avoided manufacturing minus electronics; sensitivity; where the sign flips; effect of the grid used to make cells |
| How sure are we? | `reon_mc`, `atstake` | Ranges on every input with source tags; Monte Carlo probabilities (under the ranges typed, not frequencies) |
| Doing it for a new pack | `reon_report`, `examples/reon_pack_report.py`, `app_reon.py` | Paste or upload capacities, get the whole analysis as a page or a Markdown report |

Headline results on the public cell data (details in docs/RESULTS_SO_FAR.md):

- Ideal gain: Leaf 8 cells 18.6%, BMW module 1 9.4%, all 36 BMW cells 7.2%, BMW modules 2 and 3 only 1.7% and 1.2% (REAL, from CITED capacities).
- A 2% switching loss takes 2 points off every case and erases the gain on well-matched modules (break-even loss 1.2% and 1.7%).
- Against adding capacity at 60 per kWh, control is cheaper only above about 17% gain (8.8 per kWh electronics, a CITED new-pack analog, not REON's).
- At 7% over 7 years, Leaf repays (11.7 vs 22.0 per extra kWh per year); BMW module 1 and all 36 cells do not.
- 83% of BMW module 1's gain rests on one cell; 1 to 3% capacity measurement error alone fakes a 2 to 6% gain on matched modules.
- Carbon: positive in almost all draws, but the sign depends on whether the extra capacity displaces new cells.
- "2-3X more usable capacity" needs a spread far above what is observed (CV about 22 to 36%, observed 1 to 14%), so it must be measured against something other than a typical retired string (question 1 below).

## 3. How this compares with how it is done now

Sources are the ones we pulled; see docs/REON_DATA.md for links.

| Topic | Current practice | What cell-level control changes | Evidence |
|---|---|---|---|
| Weakest-cell limit | Series module or pack stops at the weakest cell; most BMSs are designed for first life | Each cell runs to its own end | MDPI 2024 review; ACEEE 2026 brief ("only as well as its weakest link") |
| Balancing | Passive balancing (shunt resistors) burns off charge; active balancing moves charge between cells. Both work on charge state, not on a cell that has lost capacity | Bypasses a short cell instead of balancing around it | MDPI review |
| Retiring packs | EV packs retire at 75 to 80% of nominal capacity, judged at pack or module level; many keep more than 80% | Pack could stay in use until many cells are low, not one | MDPI review; ACEEE |
| Sorting for second life | Grade by state of health (often impedance spectroscopy), then regroup matched modules. Cell-level disassembly is costly, so packs are often resold at module level | Matching matters less because mismatch is handled in operation | MDPI review |
| Testing and certification | UL 1974 testing may cost about 30% of a used battery's value (one estimate); about 1.2M USD certification per battery type | Not removed by control. Probably adds a certification item | ACEEE brief |
| Closest cell-level analog | Relectrify: more than 20% usable capacity gain on degraded Leaf cells; modelled cost within 5 to 10% of a new battery | Same mechanism; REON adds series-column topology and spares | Relectrify ARENA trial; REON patents |
| The alternative to control | Add capacity or buy a new pack (about 98 per kWh new, 20 to 60 repurposed) | Control wins only above the break-even gain (9.8% vs new, 17% at 60, 28% at 40) | Chalmers; NREL 2015; our `reon_unit` |

What we can say: the mechanism is real and published by others. What we cannot say: that REON beats sorting-and-matching, because no source compares them, and that is the comparison a buyer would ask for.

## 3b. Is it better than current methods? (tested, with the sorting comparison)

Short answer: it depends on what you compare with, and on matched cells the answer is mostly no.

| Compared with | Result on the public cell tables | Verdict |
|---|---|---|
| A pack that stops at its weakest cell | Leaf 18.6% ideal, 16.3% after a 2% loss; BMW 36 cells 7.2% ideal, 5.0% after 2% | Better where cells are mismatched; a 2% loss erases it on matched modules |
| Sorting cells into matched strings (the usual second-life practice) | Control beats perfectly sorted strings by only 2.3% for the BMW cells in 3 strings of 12, 1.0% in 6 of 6, and 9.7% for the Leaf cells in 2 strings of 4. Break-even switching loss against sorting: 2.2%, 1.0% and 8.8% | Sorting captures most of the available gain on moderately matched cells. Control wins only with large spread inside each string, or when testing every cell to sort it costs too much |
| Adding capacity | Control is cheaper only above about 17% gain at 60 per kWh (9.8% vs new cells, 28% at 40) | Wins mainly where there is no room, weight or cell supply for more cells |
| Repaying its own electronics (7%, 7 years) | Leaf repays; BMW module 1 and the 36 cells do not | Case by case. The max electronics cost that still repays for the Leaf is 16.6 per kWh (we used 8.8, not REON's) |

Why this matters for the pitch: the strongest honest claim is not "better than everything". It is: where retired cells are widely mismatched, or cannot be tested and sorted cheaply, cell-level control recovers the capacity that sorting cannot, and we can say how much spread, how low a loss and how low a cost it takes. The repo now answers each of those with a number (`reon_sorting`, `reon_loss`, `reon_unit.repay_thresholds`).

What we have not shown: REON's real gain on real packs (no with/without logs), the cost of testing a cell for sorting, or the cycle-life benefit. Consistency check only: Relectrify reported over 20% usable-capacity gain on degraded Leaf cells; our model on the published Leaf spread gives 18.6% ideal. Different cells, so this is a ballpark match, not a validation.

Methods borrowed from the participant and LinkedIn notes in memory (patterns only, no code copied): held-out scoring (sort by the measured value, score on the true one: `sorted_noisy`); decision-flip thresholds (`repay_thresholds`, the "What would flip the verdict" table); Pareto front (converter window); leave-one-out (fragility); Latin hypercube Monte Carlo (Doshi post); independent re-check (Cairn, `recheck/`); LCA hotspot and sensitivity (Richard). Not yet used and possibly useful: fault injection into real series (Numair) to test the cell data check; before/after event study (Mateo) once REON gives with/without logs; shock test (Xposure) for "what if one cell fails", which needs a failure rate we do not have.

## 3c. One engine with conditions: closing the gap on well-matched cells (`reon_design`)

The two earlier fixes (a switch on a group of cells instead of every cell; control following cells as they drift) are now ONE model. `reon_design` builds the pack as parallel strings of m series cells (m fixed by the application's voltage) and scores every design on money over the service period: sort first or not, a switch on every cell or every k cells, or no switches. A string with switches is adaptive: it leaves them closed (plain weakest-cell string) and engages the bypass only while that delivers more, so a switch can never make a string worse apart from its electronics cost. Cells age forward (linear fade, random rates), the pack retires when its deliverable capacity falls below a share of day-1 nameplate (REON's slide: retirement is set on system deliverable capacity) or when the service period ends. Net value is a present value per kWh of nameplate over the service period, against the plain pack of the same string length. Uncertain assumptions are scenario axes (fade-rate spread, how loss scales with switches, how electronics cost scales with switches), and the code returns the best design per scenario, the robust pick (smallest worst-case regret), and the conditions under which each design wins.

What the engine says (BMW 36 cells in strings of 12, REAL cell data, ASSUMED ageing; `examples/reon_design_output.txt`, `reon_design_rules_output.txt`, `reon_design_stress_output.txt`):

- **The master condition is whether the plain pack retires inside the service period.** If it does (retire at 70% of nameplate, 4%/yr fade, 7 years: plain pack lasts 5.4 of 7 years), a switch on every cell, cells as found, is best in 11 of 12 assumption sets and sorting is never worth paying for, even if free. If the plain pack outlasts the service period, a cheap, perfect sort does about as well (switches gain 0.5 to 1 per kWh at most).
- **Switches win only inside these bounds** (one at a time, others at base): electronics up to about 12 per kWh at cell level (we used 8.8; 20 or more flips to sort-only), retire level 70 to 80% (50% or below flips), cell-level loss up to about 4% (5% can lose, 8% flips), service of 7 years or more, value of an extra kWh at least about 15, fade at least about 4%/yr.
- **It can lose money** when weak cells fade slower than the rest (cells converge), when the value of an extra kWh halves, or when the cell-level loss is 5%. In those cases the code does not recommend switches.
- **A lossy closed switch does not change the answer** (0.5 to 2% closed-path loss tested), because the engine only engages when it pays.
- On the Leaf cells (large spread) per-cell switches win in every assumption set once the plain pack retires inside the service period.

The claim to make: "Where retired cells are matched, per-cell switches alone do not repay on day 1. They repay when the weakest-cell rule would retire the pack inside its service life, because control keeps the pack above the retirement line longer than sorting can. The tool says when." Everything rests on the retirement rule, the fade-rate spread and the electronics scaling: that is what to ask REON for.

Honest limits: linear fade and independent or simply correlated fade rates; a plant could re-sort at maintenance (not priced); closed-switch behaviour assumed; per-cell sensing assumed to exist already; electronics cost and loss are literature or assumed values, not REON's; the value of an extra kWh is a German day-ahead price run, not a site tariff; the retirement threshold is a free parameter.

Seeds from other people's methods that built this (patterns only): held-out scoring (sort on the measured value, score on the true one), decision-flip thresholds and one-at-a-time sweeps ("what would have to be true"), Pareto trade-off, Latin hypercube-style scenario grids (Doshi), independent re-checks and brute-force tests (Cairn), the gate-test idea of ranking by the decision's cost rather than by error, and fault-injection thinking (the stress script tries to break the recommendation).

## 3d. Tested against everything (plain pack, passive and ACTIVE balancing, sorting, DC-DC converters, extra cells)

What I had missed: **active balancing**, the standard way to move charge from stronger to weaker cells so a string empties together. `reon_design` now models it (`balancer_q`: charge moves at an efficiency, and no cell can exchange more than a transfer limit r, a share of its capacity per discharge) and an always-lossy DC-DC converter per group of cells. Passive balancing only equalises state of charge, so it equals the plain pack. Buying extra cells is compared by a break-even price (`add_capacity_breakeven`). The balancer is idealised (an upper bound, as our ideal control is). Anchors: one vendor article says an LTC3300 balancer provides up to 10 A (so r can be 20% or more on a 90 Ah cell; a 1 A module balancer is a few percent); other balancer figures are ASSUMED.

Results, mean net value per kWh of nameplate over the service period, 12 assumption sets (`examples/reon_design_everything_output.txt`, `reon_design_regime_map_output.txt`, `reon_design_vs_balancer_output.txt`):

| Pack, retire at 70% | Plain | Sort only | Switches | DC-DC converters | Balancer r=5% / 10% / 20% / unlimited (balancer free) |
|---|---|---|---|---|---|
| BMW 36 cells, strings of 12 (plain pack in service 5.9 of 7 yrs) | 0 | +1.0 | +11.1 | +9.3 | +11.1 / +17.8 / +21.7 / +22.2 |
| Leaf 8 cells, strings of 4 (4.4 of 7 yrs) | 0 | +16.5 | +28.0 | +26.1 | +15.9 / +27.4 / +37.9 / +39.3 |

- **Switches beat every non-balancer option** (plain, passive, sorting, converters) when the plain pack would retire inside the service period. If it outlasts it, sorting wins and switches lose money on average.
- **Against an active balancer, switches do not win on these cells if the balancer is free and can move at least about 5 to 10% of a cell's capacity.** A balancer only moves the difference between cells, while switches pass the whole string current and pay a loss on it. That is the honest result: on matched cells, a decent balancer is the real competitor.
- **Switches win when the balancer is limited, costs as much, or cells are badly mismatched.** At a balancer cost equal to the switch electronics (8.8 per kWh), switches beat balancers with limits up to 10% on every mismatch level from CV 2% to 25%, and 20% limits from CV 10%. Free balancer at r=10%: it wins until it costs about 7 to 9 per kWh. Switch electronics cheaper than about 2 per kWh also flips it. Balancer efficiency from 70 to 95% and switch loss from 0.25 to 2% do not change who wins.
- **Dead or very weak cells.** With one dead cell in 24, balancers capped at 50% or less deliver nothing (their transfer limit blocks them) while switches deliver almost everything; only an unlimited ideal balancer beats switches, which is not a real device.
- **Against buying extra cells**, switches are cheaper only if extra capacity costs more than: BMW 3x12 at 70% retirement 27 to 53 per kWh; one BMW string 19 to 34; Leaf 15 to 16; at 50% retirement 117 to 207 (never). Compare with 20 to 98 per kWh in docs/REON_DATA.md.

Revised claim: "Per-cell switches are not the cheapest answer for slightly mismatched cells; a good active balancer is. They win (a) when mismatch exceeds what a balancer can move or cells are dead or fail, (b) when a balancer of that capability costs about as much as the switches, and (c) when the plain pack would retire inside its service life. The tool says which." The things REON offers beyond this model (fault isolation, mixed chemistries, bypassing a dead cell entirely, safety) are real but not valued here.

Ask REON: what balancer is in the baseline battery management system (current, efficiency, cost)? Is the 2-3X measured against a pack with active balancing?

## 3e. Taking the balancer's idea into the switches, and the hybrid with conditions

Idea taken from the active balancer: do not push everything through the lossy path, move only the difference. For switches that becomes **late engagement**: run the plain string with the switches closed until the weakest cell is empty, then bypass and keep going, so only the extra energy beyond the plain string passes through engaged bypasses and pays the loss (`deliverable_late`). The **hybrid** goes one step further (`hybrid_total`): the balancer holds the string together up to the point where its transfer loss exceeds the switch loss, and the switches handle the rest. The controller condition is a max over modes (plain, balancer only, late switches, hybrid) at every time step (`policy`); the app shows today's decision for the string with the weakest cell.

Tested (`examples/reon_design_hybrid*_output.txt`, `reon_design_late_vs_balancer_output.txt`; BMW 36 cells in strings of 12, retire 70%, balancer cost = switch cost = 8.8, all ASSUMED except cells):

- **Late engagement is a real improvement over switches that are engaged all the time**: +13.4 vs +11.1 (BMW), +30.8 vs +28.0 (Leaf).
- **Against a balancer at equal cost, the improved switches win**: they beat a 10% transfer-limit balancer (+9.0) whatever the closed-switch loss from 0 to 2%, and beat a 20% balancer (+12.9) only if a closed switch loses less than about 0.4%. With a balancer at 30% or more, the two are close.
- **The hybrid is not a free lunch.** With separate hardware (switches plus a balancer) it loses (+4.6). With one set of hardware doing both it adds only +0.1 to +0.5 at a 2% switch loss. It adds +1 to +5 only when the switch loss is 5 to 10% and the cells are badly mismatched (CV 15 to 25%). So the code only recommends it under those conditions.
- **When the pack outlasts the service period (retire at 50%)**, nothing with electronics pays and sorting wins (+0.6).

What this changes in the claim: "A good active balancer is the benchmark. Switches that engage late beat a balancer of equal cost when the balancer's transfer limit is modest or the cells are badly mismatched, and the choice depends on two numbers REON can give: the loss of a closed switch and whether one set of hardware can also shuttle charge." Everything uses assumed loss, cost and ageing numbers.

New asks: the loss of a closed bypass switch, and whether the cell-level hardware can also move charge between cells (shared hardware).

## 3f. Can we close the free-balancer gap? What settles it (calibrated, with failures)

Short answer: **no design can beat a free balancer on cost**, so we stopped trying to and instead found the exact conditions under which ours wins. Everything below is computed (`examples/reon_design_settle.py`, `examples/reon_design_failures.py`, saved outputs next to them).

- **Fade-rate spread is now anchored to real data (CITED).** Nature Energy 2026 fleet result (read via a secondary summary; the paper itself is still unread): weakest-cell effects cost 17.7% of lifespan in cars and 22.8% in buses. `calibrate_fade_cv` turns that into a fade-rate spread (CV) of about 0.087 (cars) and 0.111 (buses). The app scenarios now use 0.09, 0.11 and 0.20 instead of the earlier ASSUMED 0.15 / 0.30.
- **Settle table (BMW 36 cells, strings of 12, retire at 70%, 7 years, balancer cost = ours):** ours beats the best other method when the retire level is at least about 70% of day-1 nameplate, our electronics cost is at most the balancer cost (about 8.8 per kWh), closed-switch loss is below about 0.4%, and the baseline balancer is not free. Below a 65% retire level the plain pack never retires inside the service period, so the edge disappears (the "retirement rule" unknown).
- **A free balancer wins whenever it is really free and cells do not die.** Transfer limit does not rescue it: at 5% it is already slightly worse than ours, from 10% up it is a tie to a small loss for ours.
- **Cells that die change the answer (ASSUMED rates, no public figure).** A dead cell breaks a string for plain packs, sorting, balancers and group switches; only a bypass on every cell survives it. With a free unlimited balancer: no repair, ours wins from about 0.5% of cells dying per year (+16.0 vs +9.2); with a 91-day replacement, only from about 5% per year (+13.9 vs +11.4); with a 29-day replacement the free balancer still wins at 10% per year (+9.7 vs +12.0).
- **Three unknowns reduced to flip values:** retire level (flips at about 70%), closed-switch loss (flips at about 0.4%), electronics versus balancer cost (flips at equal cost). Failure and repair rates are a fourth.

All of these are controls in tab 5 of the app (fail rate, days to replace a dead cell, retire level, balancer cost, closed-switch loss).

## 3g. The app learns from data (`reon_learn`, tab 5 section C2)

- Two beliefs are updated from what is actually observed: the failure rate per cell-year (Gamma prior, exact update; prior ASSUMED, about 0.5%/cell-year and wide) and the fade-rate spread (starts at the fleet-calibrated 0.10, moves with measured per-cell fade rates).
- The app computes the **flip rate** (failures per cell-year above which late-engaging switches beat the balancer) from the design engine, then reports how sure we are that the true rate is above it. Decision rule: call "switches" or "balancer" only at 90% confidence, otherwise "undecided".
- Flip rates (BMW 36 cells, retire 70%, 7 years, switches 8.8, log-scale bisection): free balancer no repair about 0.2%/cell-year (0.11% to 0.24% across five simulation seeds, so quote it as roughly 0.1 to 0.25%); balancer costing 4 flips at about 0.05%; free balancer with 91-day repair about 2.6%.
- Test-retest on SIMULATED fleets (`examples/reon_learn_flip.py`, tests): wrong calls are rare (0 to 4% at 200 to 1,000 cell-years, up to 7% at 200 cell-years when the balancer costs 4, 0 to 2% beyond) and most fleets are simply "undecided" with little data. Right calls rise with cell-years: about 5,000 cell-years settle a true rate twice the flip (no repair); a true rate half the flip needs about 20,000 (50,000 when the balancer costs 4). With a 91-day repair the flip is larger and 500 to 1,000 cell-years suffice.
- Checked by hand (`docs/HAND_CHECK.md`): this round found and fixed two faults, the fade-spread sampling (inflated by the degrees of freedom, CV drawn around 0.26 instead of 0.10) and a flip search too coarse for small flips.
- Simulated failures never enter the app's real belief: made-up failures would only echo our own guess and cannot raise the real chance of winning. They are used to test the learning rule and to stress-test designs.

## 3h. First real past data: cell-to-cell spread from the Iowa State set, and an exploratory look at the field LFP systems

- **Iowa State / ILCC NMC cells (DOI 10.25380/iastate.22582234; 248 cells in 62 groups of 3 to 4, identical conditions within a group).** Within-group CV of the fade rate: median 0.20, quartiles 0.14 to 0.29 (0.18 for the 14 groups that lasted over 30 weeks). That is about double the 0.09 to 0.11 we derived from the Nature Energy fleet figure, and it supports the earlier 0.15 to 0.3 guess. `examples/reon_history_iowa.py` and its saved output reproduce it. Caveats: new 250 mAh cells, aggressive cycling, 30 C, fade is not linear (a straight-line fit has mean R^2 0.89), day-1 capacity spread was only 0.5% (retired packs show 20 to 30%, from ageing history). A higher spread favours switches, so the app now runs 0.1, 0.2 and 0.3 and the learner's prior is 0.20.
- **Field LFP systems (Zenodo 13715694).** Files are per-cell voltage with one shared current, not capacity. Exploratory pass over 4 of the 28 systems, looking at each cell's voltage under load against the string mean: only 2 of the 4 had enough loaded data in the passes run, and one (system 12) has cell 8 about 170 mV below the string mean. That matches the paper's "one cell behaves differently" finding, but it is one system, not a rate, and not yet checked for sensor faults. No failure rate comes out of this.
- **Still open:** the Leaf-cell series (third download), and a proper per-cell capacity estimate from the field data.

## 3i. What the REON brief and Tim Ren settled (Nov 7)

- The deliverable is a dashboard that shows the idea, so the app is the right form; spend the remaining time on clarity, not more engine.
- The brief's baseline is a plain fixed string with no effective energy redistribution. Against that baseline the balancer comparison in 3d to 3g is a stress test, not the challenge's own comparison. Lead the pitch with the plain-string result; present the balancer as "what if the customer already has one".
- Retirement level: 70% for stationary, 80% for EVs (brief). That removes the biggest unknown: at 70% and above our edge exists in the settle table. The brief also says an operator may keep running at reduced service, so show the result at both 70% and 80%.
- Faulty or completed cells can be bypassed (brief): that is the case where cell-level control beats even a free balancer, so the failure results in 3f are on-brief.
- The brief's 16-cell example is now a sample in the app and a test.

## 3j. Per-cell capacity over time for the 8 retired Leaf cells (real data, OSF FNS57)

`examples/reon_history_leaf.py` (saved output next to it) reads the C/20 characterisation spreadsheets for each cell (7 to 11 checks per cell, April 2022 to spring 2023, one consistent procedure).
- **Capacity is essentially flat.** Change first to last check: -1.4% to +2.6% (8 cells); straight-line fits -2.1% to +0.9% per year with low R^2 (mostly noise and temperature). No cell failed. This is gentle second-life duty (3 to 4 V window), so our 4%/yr fade is not supported for this use; it stays ASSUMED, and the fade input should be run from 0 to 4%.
- **The mismatch does not shrink.** Spread of capacity across the 8 cells: CV 0.105 at the first checks, 0.115 at the last. At the last check the weakest cell is 0.84 of the mean, so ideal control gains mean/min - 1 = 19.1%.
- **What the design engine says for these 8 cells** (one string of 8, retire at 70%, 7 years, value 22 per kWh-year, switches 8.8, balancer 8.8): robust pick is late-engaging switches at every fade rate tried; net value per kWh of nameplate +9.9 at 0% fade, +9.3 to +9.6 at 1%, +8.9 to +12.5 at 2%, +35 to +38 at 4% (where the plain pack retires inside the service period). So for retired packs the value comes first from stranded capacity on day 1, and lifetime extension is a bonus that only appears when fade is fast.
- Caveats: first checks are April 2022, not the cells' real day 1 (paper day-1 values are 1% to 15% lower than the April capacities for some cells, measured earlier under a different procedure); one string of 8 cells; value and cost per kWh are ASSUMED.

## 3k. One engine, three applications (sidebar "0. Application")

A preset only changes inputs (value per kWh-year, years, retire level, fade, failure and repair); every number keeps its tag and the sidebar shows where it came from. Presets: retired EV packs reused as stationary storage (headline; REAL value, 7 years, retire 70%, fade 1% from the Leaf cells), grid-scale storage (value 12 per kWh-year from CAISO's 2024 market monitor, about $50 per kW-year over an assumed 4 hours, 15 years from NREL ATB), data-center backup (value 8 = new-cell price 98 over 12 years, 80% retire, standby fade 0.5%, mostly ASSUMED; reliability benefit not valued). Failures are off in every preset: published catastrophic cell failure rates are about five orders of magnitude below where bypass would matter.. Grid and data-center values are order-of-magnitude and say "same method, different inputs", not "validated for that market".

## 4. Questions to ask REON and sponsors about their pain points

These are written to be asked as stories ("last time you did X, how long did it take?"), not as a survey. Items 1 to 6 are in docs/ASK_REON_DRAFT.md. The rest are about code and process.

**Evidence and numbers**

1. What is "2-3X more usable capacity" measured against: new or retired cells, which spread, which baseline BMS?
2. What is the switching-path efficiency and standby draw per cell? Everything we show depends on it.
3. What do the electronics cost per cell or per kWh, and what do you pay for retired packs per kWh?
4. Do you have per-cell capacity, voltage and temperature logs from the same pack run with and without control?
5. What input-voltage window does the converter accept, and does the string need a minimum number of cells in circuit?
6. Which application, tariff and practical limit (technical, economic, safety) should we model?

**Code and process**

7. How do you estimate the usable-capacity gain for a customer's pack before deploying? A spreadsheet, a simulation, a bench test? How long does it take and what does it cost per pack?
8. When you quote the value over a conventional BMS, what do customers push back on? Which number do they not believe?
9. What do you do today when a cell reads wrong: a bad sensor and a really weak cell look the same in capacity data. Do you have an automatic check, or does someone look?
10. Which decisions repeat every week (accept this pack, set this cut-off, size this order) and are still done by hand?
11. Which input is hardest to get: cell-level capacity before intake, the price of retired packs, or the electricity price the customer actually pays?

**Money**

12. What does a stranded kWh cost you: a pack retired early, a pack you refused to buy, a customer's unused energy?
13. What do you pay per pack for testing and certification, and does cell-level control change which tests are needed?
14. How is the electronics cost split between the one-off cost and the cost that grows with the number of cells?

**Carbon**

15. Do customers ask for carbon figures (for example the EU battery passport), and how do you compute them today? Which grid mix and which "avoided new cell" assumption?
16. Would you accept a range with the assumptions shown, or does the customer need one number?

**Safety and limits**

17. What voltage, thermal or current limit stops you from bypassing a cell? Does a cell with low capacity also have a safety issue you must not run?

## 5. How the app is organised

One page, top to bottom, no code needed:

1. Sidebar, step 1: pick a sample pack or paste or upload your own cell capacities.
2. Sidebar, step 2: practical limits (switching loss, converter window, data-check cut-off).
3. Sidebar, step 3: money (electronics, value per kWh, cost of adding cells, rate, years). Each number has a source tag; change the tag when you change the number.
4. A one-line verdict, then five tiles: ideal gain, gain after your limits, payback, break-even vs adding cells, net carbon.
5. Tabs in the order of the pitch: 1 What we gain, 2 How solid is it, 3 Money, 4 Carbon, 5 Story (What / How / Who / Why, filled in with the current numbers, a Markdown download and the questions for REON).

Known gaps: REON's own efficiency, electronics cost, pack price and retirement rule are not public; the app starts from literature values and says so on the page.


## 3l. Learning layer compared against every rival, and first look at the rendered page

- `reon_learn` now compares late-engaging switches with the best of every other way to build the pack (balancer, DC-DC converters, sort-only, plain pack), not the balancer alone. The saved flip and example outputs did not change, because the balancer was already the toughest rival in those cases; a test checks that extra rivals can only lower our edge.
- The app was rendered in a real browser for the first time. It surfaced an Arrow serialisation warning (a table column mixing numbers and "n/a", now text), truncated source-tag boxes in the sidebar (sidebar widened), a clipped tile label, and a C2 message that said "Data says switches" when no data had been entered (it now says failure data cannot change the answer when switches win with no failures). The default fade was changed from 4% to 1%, in line with the Leaf and NREL data.


## 3m. Round 3 (Nov 7 afternoon): ageing that depends on how the pack is run, sourced knees, and the cost to win

Code: `hackkit/reon_wear.py` (`wear_scan`), tests `tests/test_reon_wear.py` (with `dod_exp = 0` and no knees it reproduces `reon_design.design_scan` to 1e-9 for the late switches and the balancer). Examples with saved output:
`reon_wear_iowa_fit.py`, `reon_wear_regimes.py`, `reon_wear_cost_to_win.py`, `reon_wear_sensitivity.py`.

- **Fade depends on depth of discharge (SOURCED, Iowa State/ILCC, 59 usable groups).** fade rate ~ DoD^g with g = 0.87 (90% CI 0.69 to 1.18) for the time to 90% and 0.71 (0.60 to 0.91) for the time to 70%. In a plain string the weakest cell
  has the deepest discharge, so it fades fastest and the spread grows (the divergence Nature Energy 2026 reports). Bypass shares the duty out in proportion to capacity.
- **Knee-like fades (SOURCED shape, lab cells).** 65% of 205 cells fade faster after a bend: median 2.4x steeper (quartiles 2.0 to 3.1), starting at 0.82 to 0.90 of their own start (median 0.855). State-triggered, so no calendar failure rate is invented.
  This replaces the open-circuit rate that nothing public supports. The 65% is an upper bound for retired packs (continuous lab cycling, 30 C).
- **Result: the mechanism is real but small.** Over 15 grid years it adds 0.1 to 1.2 per kWh nameplate (example `reon_wear_sensitivity_output.txt`), and a balancer that moves charge gains the same, so it does not close the gap to a balancer. Level (always engaged) switches are worse than late switches.
  Well-matched packs (cv 0.5 to 2%): sort-only is the best choice for retired EVs and data-centres (0 to +0.7), and nothing we have beats a free balancer in the grid case.
- **Cost to win (the reverse of the worst case).** `reon_wear_cost_to_win_output.txt`: the most our electronics may cost, per kWh nameplate, and still beat every rival.
  Against a FREE balancer that can move 20% or more of a cell per cycle the answer is about 0 at every spread up to 15% (cannot win on cost). Against a free 10% balancer: 0 to 5 (retired EV, cv up to 10%), 2 to 11 (grid, cv up to 10%), 10 to 24 at cv 15%.
  With the balancer costing 4 (against the 10% balancer): retired EV 2.7 to 11.7, grid 6 to 24, data-centre 1.4 to 5.6; against a 50% or unlimited one the ceiling is about 4 everywhere except data-centre at low spread. So the pitchable target is electronics at or below the balancer's cost, which is already the old conclusion, now with a table and sources for the balancer limits.
- **Balancer limits (SOURCED).** Analog Devices LTC3300-1: up to 10 A per cell, up to 92% transfer efficiency, 6 cells per IC (electronicdesign.com article). 10 A moves 10% of a 100 Ah cell per hour of idle time, so a balancer is limited by cell size and idle hours, not by a fixed percentage. Its COST per kWh is not sourced.
- **What is still not closed.** (1) a free, big-current balancer beats us in every case modelled; (2) nobody publishes the balancer's cost; (3) the duty (share of the weakest cell cycled daily, 0.7) is ASSUMED, but the sensitivity run shows it hardly matters; (4) knee share in retired packs unknown.
- The Nature Energy paper's source data (four Excel files for Fig 3 to 5) and code are open on GitHub (Rico-dicp/Ev-battery-cell-to-cell-inconsistency, MIT; vehicle parquet data via an external link): the next calibration step for fade spread and knee timing, not yet downloaded.


## 3n. Round 4 (Nov 7 evening): selective bypass and ONE recommended build (beats a real balancer)

Code: `reon_wear.wear_scan(select_counts=...)` and `reon_wear.recommend_build`; tests in `tests/test_reon_wear.py` (7 pass). Examples with saved output: `reon_select_vs_balancer.py`, `reon_recommend_build.py`.

- **Idea:** retired packs mostly have a FEW weak cells (REON brief: one at 70 Ah among 85 Ah; BattGP field data: one or two odd cells in 9 of 21 systems; knees hit individual cells). Put bypass switches only on the k weakest cells of each string (chosen at the day-1 test) so hardware cost is k/m of full. The string current stops when the weakest UNswitched cell is empty.
- **One policy, not two fixes:** `recommend_build` evaluates plain, sort only, selective k = 1..m-1, switches on every cell, and an active balancer with the user's limit r and cost, and returns the best by net value plus the margin over the best rival.
- **Balancer limit from physics (SOURCED inputs):** a balancer can only cover a weak cell during the discharge, so r = I_bal / (C_rate x cell Ah). I_bal: about 1 A typical storage BMS (DALY), 5.5 A (Heltec 3-21S), 10 A (LTC3300-1, which costs A$19 to 29 per 6-cell chip at element14, roughly A$3 to 5 per cell before transformers and FETs). So a 1 A balancer on a 94 Ah cell at 0.5C covers 2%, a 10 A one 21%.
- **Result on the real packs** (Leaf 8, BMW 36, REON brief 16; retired EV, grid, data-centre; wear and knees on): against a typical-current balancer (5%, cost 4) or a transformer-based one (20%, cost 12) the recommended build wins in all 18 cases, by +0.4 to +20.6 per kWh nameplate (Leaf retired EV +10.4 / +5.0, brief +13.3 / +7.1, grid +19 to +21 / +6 to +9). On the well-matched BMW pack the margin is only +0.4 to +0.6 in retired EV and data-centre (selective on one cell vs sort only): not a meaningful win, so there the answer is sort only.
- **Still loses** to a balancer that is both FREE and able to move 20% of a cell per cycle (margins -1.2 to -7.0). Part 1 of `reon_select_vs_balancer_output.txt` shows when 20% is reachable (10 A class, 94 Ah at 0.5C or smaller cells) and that class is not free. On Gaussian spread with no outliers (cv 2 to 5%) retired-EV packs still lose to a costed balancer or sort only, and the cv-10% cases are marginal.
- **Assumptions:** electronics 8.8 per kWh for a switch on every cell (selective scales it by k/m, ignoring extra wiring), balancer cost 4 and 12 (12 from chip price only), duty 0.7, knee share 65% (lab upper bound). The outlier packs in the regime run are constructed from the brief and BattGP statements, the Leaf, BMW and brief packs in `reon_recommend_build.py` are real.


## 3o. Round 5: hybrid test, stress test, and the recommendation on the page

- **Dashboard:** tab 5, section C0, and a one-line copy of the answer under the tiles ("Recommended build: ..."). `reon_wear.recommend_build` via a cached `run_build` in `app_reon.py`; two new inputs (DoD exponent, knee share, both off by default); all 16 app tests pass, including a new one for the brief pack. Not yet checked by eye in a browser.
- **Hybrid (selective switches + a balancer): does NOT close the last gap.** `reon_wear.hybrid_select_total`, tested to equal selective bypass when the balancer moves nothing and never to be worse than it. When the balancer already covers the mismatch (its limit exceeds the weak cells' shortfall) the hybrid adds only hardware cost; it was the chosen build in only 8 of 612 random draws, all with a balancer limit of 50 to 60% or tiny.
- **Stress test** (`examples/reon_stress.py`; outputs `reon_stress_tornado_output.txt`, `reon_stress_random_output.txt`, `reon_stress_winmap_output.txt`): 612 random draws over ASSUMED ranges chosen to be wide (our electronics 2 to 16, switch loss 0.5 to 5%, closed loss 0 to 1%, balancer limit 1 to 60%, balancer cost 0 to 15, balancer efficiency 80 to 95%, test error 1 to 10%, fade spread 0.1 to 0.4, DoD exponent 0 to 1.2, knee share 0 to 65%, duty 0.5 to 0.95, sorting 0 to 5, value x0.6 to 1.4) on the three real packs and three applications.
  - The recommended build beats the best alternative in **79% of draws** (median margin +5.5, 10th percentile -1.1, worst -3.9 per kWh nameplate). Leaf 8: 74 to 87%; brief 16: 85 to 99%; BMW 36 (well matched): 54 to 56% in retired EV and data-centre with a median margin of +0.1 to +0.3 (a tie), 87% in grid.
  - Packs with outlier cells (Leaf, brief): we win 94 to 100% of draws when the balancer moves under 10% of a cell, 100% when it costs over 10, 28 to 54% when it moves 20 to 100% and costs under 10. Our electronics cost matters less than the balancer: 93% of draws win at under 4, 78% at 8 to 12.
  - One-at-a-time (`reon_stress_tornado_output.txt`): the margin is most sensitive to the balancer limit r (Leaf grid +23.6 at 2% to -1.3 at 20%), the balancer cost, and our electronics cost; hardly at all to efficiency, test error, duty or the ageing model. A 10% test error costs the BMW pack about 1 per kWh and almost nothing on packs with clear outliers.
  - **The limit that remains:** a balancer that is cheap (under about 5 per kWh) AND moves 20% or more of a cell per cycle beats us. Section 3n part 1 shows what that needs (a 10 A class balancer on a cell of 94 Ah at 0.5C or smaller, plus transformers), not found at a cheap price.
- **Not tested:** real per-cell data over time from a retired pack, a measured test error for retired cells, wiring cost of selective switches, balancer hardware bill of materials.


## 3p. Round 6: the free-balancer case and the well-matched tie

Code: `reon_wear` gained (a) switches on only the g weakest cells of the WHOLE pack (`global_counts`, cost g/n of a full set), (b) closed-path loss that scales with the share of switched cells (a series switch exists only where there is a switch). Tests: 11 in `tests/test_reon_wear.py`. Examples: `reon_free_balancer_case.py`; stress re-run (`reon_stress_*`, 558 draws).

- **The one case we lost (a free balancer that moves 20%+ of a cell): reuse their method.** That is exactly the hybrid: the balancer moves the small shortfall first (it only loses 10% of the charge it moves), switches handle what is left. With the balancer free for both, our best build is a tie within -0.8 to +0.4 per kWh nameplate (Leaf and brief packs: retired EV -0.5 / -0.8, grid +0.4 / +0.4), i.e. the switch tail adds +0.4 in grid and costs more than it earns in retired EV, where the right answer is the balancer alone (a tie at 0). The result does not depend on the bypass loss (0.2 to 2% gave identical rankings), because the hybrid takes its gain through the balancer. So the policy never does worse than the best existing method, provided REON is willing to ship the balancer too; it BEATS it only by +0.4 in grid.
- **Well-matched BMW pack: bounded by the ceiling.** Ideal control with no loss and no cost is worth only +4.9 (retired EV), +17.7 (grid), +2.6 (data-centre) per kWh nameplate; sort only captures +0.7 / +1.0 / +0.4. One switch on the single weakest cell of the pack (1/36 of a full set) nets +1.8 / +1.6 / +0.9, about 40% of the retired-EV ceiling. Against a balancer of 5% and cost 4 that is a margin of about +1.2 in retired EV and +0.6 in data-centre (was +0.4 each). More than this is not available on this pack. Per-string selective is similar (+2.0 / +1.6 / +0.7).
- **Stress re-run with the new design (558 draws, new seeds):** we win in 78% of draws. BMW retired EV 54 to 66%, median margin +0.3 to +0.7; BMW data-centre 56 to 66%; packs with outliers about the same as before (73 to 97%). Overall it did not move, so the gain is confined to the well-matched packs. We still lose to a cheap balancer (under about 5 per kWh) that moves 20%+ of a cell, except by adopting it.
- **Sourcing for the engaged and closed loss still open.** A Frontiers in Energy Research 2023 paper (Loss and reliability analysis of solid-state battery reconfiguration topologies) compares 2-, 3- and 4-MOSFET cell topologies and reports about 33% lower conduction loss for the proposed one, but the page I could read had no Rds(on) values or percentages. Our own estimate: closed loss = I x R_on / V per series switch (50 A, 2 mOhm, 3.7 V = 2.7% if EVERY cell has a series switch; selective switching divides it by n/g). Ask 14/17 to REON stays open.
