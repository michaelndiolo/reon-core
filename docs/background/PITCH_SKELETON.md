# Pitch skeleton for the REON challenge (What / How / Who / Why), rewritten Nov 7

Every number carries its tag: REAL (data we analysed), CITED (a source), ASSUMED (ours). Replace ASSUMED with REON's answers when mentors reply. Regenerate figures with `examples/reon_pack_report.py`, `reon_history_leaf.py`, `reon_history_iowa.py`, `reon_learn_flip.py`.

**One line.** A string stops at its weakest cell; cell-level control lets it run every cell to its own end. We built a dashboard that says how much that is worth for one real application, against the plain fixed string, and under what conditions it does and does not pay.

## The 3-minute path through the app (nothing else needs showing)
1. Sidebar "0. Application": pick **Retired EV packs reused as stationary storage**; cells **8 Nissan Leaf cells** (REAL retired cells). Top tiles: ideal gain about 18.6% day 1, 19.1% a year later.
2. Tab 1 **What we gain**: weakest cell vs sum, the 16-cell example from the brief (70 Ah vs average 84.06 Ah) as the intuition, then the real Leaf cells.
3. Tab 3 **Money**: payback and break-even against simply adding cells.
4. Tab 5 **Beats current methods?** section C: robust choice and the conditions table (when it wins, when sorting or a plain pack is enough). Then C2: type failures seen and cell-years watched, the answer updates.
5. Switch the preset to **Grid-scale** and **Data-center backup** to show it is one method with different inputs. Close on tab 6 (story + report download).

## What (problem and opportunity)
A battery is limited by its weakest cell. In a fixed string the same current passes through every cell, so the weakest sets the limit while the rest hold unused energy. Nature Energy 2026 (116 cars, 17 buses) found the weakest-cell effect shortens pack life by 17.7% (cars) and 22.8% (buses), and leaves 19.3% and 27.1% of energy unused [CITED, abstract level]. Our retired Leaf cells strand 19.1% [REAL].

## How (technical capability)
REON's per-cell sensing and bypass lets the string skip a finished or faulty cell. Usable energy goes from N x weakest to the sum. We model the limits: switch loss (break-even 1.2% to 15.7% depending on spread), converter voltage window, test noise, and a closed switch's own loss, then ask when engaging pays (late-engaging switches). We do not design hardware (the brief says we need not).

## Who benefits
Owners of second-life storage and integrators of retired packs; operators who sell energy (value 22 per kWh-year on German day-ahead prices, one cycle a day [REAL prices, ASSUMED battery]); grid and data-center operators in the presets [ASSUMED values, sources in the sidebar].

## Why it matters (value and impact)
- **Where it pays:** mismatched packs. On the 8 Leaf cells the design engine picks late-engaging switches at every fade rate from 0% to 4% a year, net +9 to +10 per kWh of nameplate over 7 years at 0 to 1% fade, about +35 at 4% where the plain pack would retire early [ASSUMED costs]. Grid-scale preset on the same cells: +29 to +31 (value 12 per kWh-year, 15 years); data-center preset: +4 to +11 [ASSUMED values].
- **Where it does not:** well-matched cells. On the 36 BMW cells sorting alone wins in the retired-EV and data-center presets (net +0.3 to +0.7, i.e. about nothing), and switches only win in the grid preset. Say this out loud: it makes the rest credible.
- **Against adding cells:** control wins on cost only above a gain of 9.8% (new cells at 98 EUR/kWh) to 28% (retired cells at 40 EUR/kWh) [CITED / ASSUMED].
- **Against a balancer:** a free active balancer beats us unless cells fail (about 0.2% per cell-year with no repair; about 2.6% with 91-day repair), our electronics cost less than the balancer's, and a closed switch loses under about 0.4% [simulated, ASSUMED rates]. The brief's baseline is a plain string; the balancer is our stress test.
- **Round 5 stress result (say this, it is honest):** across 612 random draws over wide ASSUMED ranges, the recommended build beats the best alternative in 79%; in 94 to 100% when the balancer moves under 10% of a cell per cycle or costs over 10 per kWh; and we lose mostly when the balancer is cheap (under 5) and moves 20% or more. The dashboard shows the recommendation next to the tiles (tab 5, C0). On the well-matched BMW pack it is a tie (+0.1 to +0.3).
- **Round 4 headline (replaces the older rule above):** one recommended build, chosen by `reon_wear.recommend_build` from the pack's own cell test: sort only when matched; bypass switches only on the few weak cells when a pack has outliers (REON brief example, BattGP, Leaf); switches on every cell for broad long-life grid spread. On the real Leaf, BMW and brief packs it beats a typical-current (1 to 5 A) or transformer-class costed balancer in 18 of 18 cases (+0.4 to +20.6 per kWh nameplate; BMW is a tie-level +0.4). It loses only to a balancer that is both free and moves 20% of a cell per cycle. [balancer currents and chip cost SOURCED; our 8.8 per kWh ASSUMED]
- **The condition rule (one policy, not two fixes):** at day 1 test the cells. If the weakest cell is within about 5% of the mean (cv under 5%): sort only (retired EVs and data-centres: 0 to +4 per kWh), do not add switches. If the spread is larger or the pack is a long-life grid system: engage late switches, but only if our electronics cost no more than the best balancer on offer (cost-to-win table, `examples/reon_wear_cost_to_win_output.txt`). Against a free balancer with 20%+ transfer we cannot win on cost. [ASSUMED costs; balancer current SOURCED: LTC3300-1, 10 A, 92%.]
- **Faults, honestly:** no public open-circuit rate, so we model what IS measured: accelerating fade in 65% of 205 Iowa lab cells (median 2.4x, from ~0.855 of start) and fade rising with depth of discharge (exponent 0.7 to 0.9). Both are in the simulator; they add 0.1 to 1.2 per kWh to our case and equally to a balancer's, so we do not claim them as a win.
- **The app learns:** failures seen and cell-years watched update the belief and the call; about 5,000 cell-years settle the common case [simulated test of the rule].
- **Environment:** embodied emissions 61 to 106 kg CO2e per kWh of new battery [CITED, IVL 2019, checked against the report page]. The result hinges on one assumption, the share of extra capacity that displaces new-build; carbon breaks even above about 7% displacement, so say "we need only 7%", not a headline tonnage [ASSUMED share].

## Practical limits (say them before they ask)
- Ideal sum is an upper bound; voltage window, switch loss, cell safety limits when bypassing.
- Fade of retired cells: the Leaf cells showed about 0 to 1% a year [REAL]; six Mini-E packs lost 0 to 6% in 2.5 years, up to about 2.4% a year [CITED, NREL 2019]. The app defaults to 1% and the plain pack only retires inside the service period when fade is near 4%, which we show as a stress case.
- Failure and repair rates: no public figure for aged cells. Published catastrophic cell failure is 1 in 10 to 40 million cells [CITED, Faraday Institute 2023, from Doughty and Roth 2012], about five orders of magnitude below the roughly 0.2% per cell-year where bypass beats a free balancer. So failures are a what-if, off by default in every preset, not a claimed advantage.
- Electronics cost, closed-switch loss, REON's own balancing: not REON's numbers; see `docs/ASK_REON_DRAFT.md`.
- Grid value: CAISO market monitor 2024, actual batteries about $50 per kW-year, over an assumed 4 hours = about 12 per kWh-year [CITED, ASSUMED duration]. Data-center value (8) is the new-cell price over 12 years [derived], with lithium-ion life 10 to 15 years from Schneider; UPS runtimes are 1 to 5 minutes so the value is deferred replacement, not energy sold.

## Likely judge questions
- *"Is this just sum vs min?"* No: it tells you when sum-vs-min survives real limits (loss, window, noise, sorting, balancing, cost) and when it does not.
- *"Why trust your fade numbers?"* Spread comes from 248 real cells (median 0.20 within a group) and a fleet study; the mean fade is shown as a range because retired cells showed almost none.
- *"What would change your answer?"* The conditions table and the flip values: retire level, balancer cost, closed-switch loss, failure rate.
- *"Did an AI write this?"* Say what is true: tool-assisted, with hand-checkable formulas in `docs/HAND_CHECK.md`; two errors were found by that check and fixed.
