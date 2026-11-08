# What Tim Ren (REON cofounder/CTO) told us, 7 Nov 2026, and what we decided

Source: live call notes and Discord. The call transcripts are speech-to-text and partly garbled; lines marked (unclear) need confirming. Nothing here is a REON-approved number until Tim confirms it.

## Customer and application
- REON deliberately steers away from residential. Customers are commercial and industrial (C&I): chain stores, small businesses, suburban sites. The 60 kWh EBS Na+ unit is for them.
- They care about second life, round-trip efficiency, cost, and energy density. (unclear: "hold time")
- His scenario: big storm at night, grid down, backup runs, a cell is failing, the owner calls at midnight. How long does a replacement take? Use state blackout statistics for exposure (`examples/data/eia_reliability_by_state.csv`).
- A dashboard can serve any audience; simpler for end customers, detailed for cell experts.

## Numbers and facts he gave
- 200 to 300 cells in series per string, everything included. Cell voltage window from about 2.5 V up to 3.x V (chemistry decides). Roughly 90% of cells are connected in normal use (unclear). How many can be bypassed depends on how much redundancy you pay for.
- Per-cell sensing accuracy within 5%, often much better. BMS measures voltage, current, and two temperatures per cell (terminal and body). More variables he cannot discuss.
- Warranty standard 10 years / 8,000 cycles. Cells are 20,000-cycle NFPP sodium (maker claim, unverified).
- Switch overhead "very minimum, but not none" (depends on switch impedance). Total electronics about 3 to 4 times a conventional BMS, "still very competitive". Open: is the $7 to $24 per kWh the total or the extra over a conventional BMS?
- Installed price: a commercial-team question.
- REON can add its modules in series with a customer's existing battery. Retrofit onto an existing sealed pack or an EV pack is typically not possible. Second life means rebuilding from modules or cells. (unclear: how much of an old pack can be bypassed)
- Modules can be arranged so sections share a voltage, so part of the string can charge or discharge. (unclear)

## Ideas he stressed
- System-level, not cell-level: the whole system's capacity and cycle life are set by the weakest cell, and one or two cells at 80% condemn a whole pack. Cell life 20,000 cycles against a system guarantee of 8,000.
- The gap between strong and weak cells is the problem the industry fights over. Passive balancing burns energy as heat at tiny current. Active balancing moves charge but power electronics loss goes as current squared, so cost, copper and heat grow with the current needed. Big mismatches (second life) make it worse.
- Reliability comes from architecture, not better cells: series survival is r to the power n, so 500 cells at 99.9% each survive 60.6% of the time. Tolerating a few dead cells fixes it.
- The valuable signal in sensor data is the curve, the trend and the left-to-right comparison, not single maximums.
- IP versus frame relay: a series string is a fixed path; REON routes around problems and spends a little more on software. Lego: standard interface, mixed ages and chemistries.
- Module-level second life is possible and he supports it, but cells inside a module age differently by position, so the weak-cell problem remains.

## Data
- Some information is public. Granular per-cell data is not authorized. He will ask his data scientist about a small sample. Do NOT commit any REON sample to git (`.gitignore` blocks `data/private/` and `*.sample.csv`). Use `examples/reon_bms_sample_check.py` for a first look.

## Decisions (7 Nov, evening)
- Hero application: C&I stationary, 60 kWh sodium, suburban storefront storm-night story, with state outage statistics.
- Solar minigrid / remote site stays as one scenario (long crew lead time, high downtime cost), not the main product. No more minigrid-specific building.
- Rerun the hero at 200 to 300 cells per string, once as single cells and once as parallel groups.
- Lead metrics, system level: usable kWh per charge, system cycles to end of life, lifetime kWh delivered, probability the string survives the warranty.
- Headline depends on REON's answers: single cells and moderate fade, capacity gain; parallel groups or very slow fade, uptime and avoided crew visits.

## Questions still open for REON
1. Is each series element one cell or a parallel group, and what capacity?
2. Measured cell-to-cell spread and fade curve on the 20,000-cycle cells; field fault rate per cell-year.
3. DC string voltage, inverter minimum input, whether a DC-DC stage holds voltage when cells are bypassed.
4. Is $7 to $24 per kWh the total or the extra over a conventional BMS?
5. Visit cost and fault-to-fix time; second-life disassembly and testing cost.
6. Does REON offer module-level switching, and how many cells per switch?
7. Command interface, latency, update rate, sensing definition and rate.

## Built from these notes (7 Nov, night)
See `docs/STRESS.md`, section "Fixes from Tim Ren's problems". Key result: the capacity-gain headline depends on whether a series element is a single cell (large gain) or a parallel group (small at slow fade). Ask REON first.

## Tim Ren's answers, 8 Nov (to our five questions)
1. Series position: "could be both" (single cell or parallel group). Capacity per position not given; Tim says the EBS Sodium data sheet exists (not the lithium one) and Rhythm Doshi asked for it.
2. Field failure rate: "largely depends on the grade of the cell". No number.
3. String voltage and inverter minimum: "PCS dependent", some very wide, some very narrow.
4. Sodium cell-to-cell spread: too new for much field data, but disparity is larger than LFP.
5. Switching cost: the 7 to 24 per kWh is the cost OVER a conventional BMS, set by PCB volume. (Energy lost as heat was not answered.)

Top follow-ups: (1) what balancing the conventional BMS does (none / passive / active, what current); (2) the EBS Sodium data sheet plus the switch heat loss; (3) the PCS DC input range for a 60 kWh storefront system as a share of nominal, and a failure rate for the cell grade in this product.
