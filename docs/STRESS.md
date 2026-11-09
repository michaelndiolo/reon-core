# Stress tests (7 Nov 2026)

Every run is reproducible from `examples/`; saved outputs sit beside the scripts.

| Test | Script | Result |
|---|---|---|
| Input fuzz, warnings as errors | `reon_fuzz.py` | 0 unexpected failures; bad inputs stop with a clear message, never silent NaN or infinity |
| Hero case, inputs from real sources, fresh seeds | `reon_hero_stress.py sourced` | 280 earlier draws: beats best rival 85%, plain 95%. 186 fresh draws (seeds 9001, 9002): 84% and 94%, median margin +13 per kWh. Worst draw -5.6 per kWh (low value, high switch cost) |
| Hostile packs: BUY verdict scored on an unseen seed | `reon_adversary.py` | 96 draws (dead cell, hot cell, bimodal, ramp, identical, wide, tight; switch cost to 45, fade spread to 0.9): 70 BUY, 26 HOLD, 0 false BUY. Every HOLD had at most +5 per kWh left on the table. A first version with a strict p10 rule had 2 false BUYs in 40, both outside sourced ranges; the rule was relaxed to 5% of the gain and the check seed gets twice the trials |
| Hostile sites: string life with faults and crews | `reon_events_adversary.py` | 400 draws. Automatic bypass loses to a fixed threshold in 10% and to replace-on-failure in 31%. Replace beats automatic bypass in 56% of draws where a visit costs under 300 (153 draws). A threshold beats it in 32% of draws with a bypass budget of 1 and switch loss above 6% (31 draws), against 8% in the other draws |
| Per-site policy chooser | `reon_events_selector_test.py` | 240 draws, regret vs best policy in hindsight on unseen seeds: chooser 1.3 mean (worst 34), always ours+crew 10.9 (worst 110), best fixed threshold 36.2, always replace 50.7 (worst 481). Chooser picks automatic bypass at 147 of 240 sites |

## Added later on 7 Nov: fixes for the losing regimes, REON's answers, crew time
| Test | Script | Result |
|---|---|---|
| Bridge policies (bypass at once, then book the crew after 1 or 2 bypassed cells) | `reon_events_fixes.py` | Same 400 hostile draws, switch loss now charged to threshold rivals too. Losses to replace-on-failure fall from 33% (ours+crew only) to 14% (best of the bridge family, chosen on separate seeds). Cheap visits (under 300): 56% to 18%. Budget 1 and loss above 6%: 13% to 6% vs replace. Losses to the best threshold: 2% to 1%. With thresholds free of switch loss (the old, rival-friendly reading): 11% to 8% |
| Per-site chooser, bridge variants included | `reon_events_selector_test.py` | 300 draws: regret 1.1 per kWh mean (worst 30) vs always ours+crew 17.2, best fixed threshold 67.6, always replace 54.9 (worst 481). It picks automatic bypass at 257 of 300 sites (was 147 of 240) |
| Sensing error of 5% (REON) | `reon_sensing_noise.py` | Worst case, a fixed per-cell error within +-5%: false bypass 1 in 1,000 healthy cells at weak line 0.15, 0 at 0.20; a cell 20% weak is caught every time, 15% weak about half the time. Line 0.10 would false-bypass 17 in 1,000. Keep 0.15 |
| Crew time to identify and fix | `reon_crew_time.py` | Automatic bypass keeps the string up while a crew is found. With a downtime cost of 20 per kWh nameplate per month, the gain over replace-on-failure is +47 (detect 0, lead 0.5 months) to +273 (detect 6, lead 3). At zero downtime cost it is +7 to +18, so the value is resilience, not energy. Lead below one month rounds to one month (monthly steps) |
| Grid restoration anchors | `reon_crew_time.py` part 2 | A 60 kWh pack at 5 kW lasts 9.8 h plain, 10.4 h managed, 17.4 h with load shed to 60% (median of 12 real packs). That covers the U.S. typical outage and Maine's 8 h average in 2024, but not Florida's 12.4 h without load shed, and nothing covers a 72 h outage without solar |
| Long-life sodium (20,000 cycles) | `reon_hero_stress.py longlife` | **Warning.** 150 draws with fade 0.003 to 0.012 a year and life 10 to 25 years: beats the best rival only 46% of the time, plain 77%, median margin about 0, median gain over plain +5.4 per kWh (versus +33.6 at the normal-fade sourced draws). Capacity spread barely opens when cells fade this slowly. Fault tolerance still pays: in the string-life simulation at 0.004 fade with a fault rate of 0.01 per cell-year and visits of 3,000, automatic bypass nets 276 vs 200 for replace-on-failure (163 with a downtime cost) |

## Closing the HOLD regime and the slow-fade problem (7 Nov, night)
| Test | Script | Result |
|---|---|---|
| Cheap visits with high switch loss (HOLD sites) | `reon_cheap_visit_fix.py` | 300 hostile draws: the chooser picks replace or a threshold at 43 (14%). At 35 of those 43 a break-even switch loss exists (median 7.7%, their actual median 8.5%): automatic bypass pays if the loss falls just below it. At 31 of 43 a break-even switch cost exists (median 12.8 per kWh against 15.5 assumed, REON range 7 to 24). Letting the site shed 30% of the current (conduction loss share falls with current) flips 25 of 43 to automatic bypass, 50% flips 27. Only 3 of the 43 HOLD sites have a loss at or under 4% ("very minimum", REON); 116 of the 300 draws had loss at or under 4%, so about 3% of the plausible-loss sites HOLD. The dashboard now prints the break-even targets instead of just HOLD |
| Slow fade tied to the site | `reon_hero_stress.py sitefade` | 120 draws, fade from the 20,000-cycle claim x 0.8 to 2 cycles a day x cell temperature 15 to 45 C (ageing doubling per 10 C is an ASSUMED rule of thumb). Capacity gain beats the best rival 29% of the time below 0.006 a year, 70% at 0.006 to 0.012, 88% above 0.012. By temperature: 27% at 15 to 25 C, 61% at 25 to 35 C, 84% at 35 to 45 C (median margin +9.4 per kWh). So capacity gain is a hot-site, heavy-cycling story |
| Where the money comes from | `reon_events.value_streams`, `numbers.json` | Remote minigrid preset (visit 3,000, lead 3 months, detect 3 months, fault rate 0.01, downtime cost 20 ASSUMED), fade 0.004: capacity and switch cost -7, dead cells kept working +16, crew visits avoided +80, downtime avoided +201, total +289. With downtime cost 0 the total is +89. C&I site with a crew nearby (visit 500): total +5 to +9 per kWh, so the case there is thin |
| Break-even fault rate | `reon_events.break_even` | Automatic bypass starts to beat replace-on-failure at 0.002 faults per cell-year at the remote preset (about 3% of 16-cell strings a year), and at 0.0044 at the C&I preset with 0.004 fade. The field fault rate is the number to get from REON |

## Fixes from REON's problems (7 Nov, night)
| REON's problem | Fix | Where |
|---|---|---|
| Strings are 200 to 300 cells, not 16 | Hero rerun at 250 series elements, single cell versus parallel group of p small cells (spread shrinks by the square root of p) | `examples/reon_hero_250.py`, outputs `reon_hero_250_h12_output.txt` and `_h30_output.txt` |
| System life, not cell life; cell 20,000 cycles vs system guarantee 8,000 | System view: service life, system cycles, share of the cell rating, lifetime kWh per kWh, cost per kWh delivered | `hackkit/reon_system.py`, dashboard tab 9 |
| Weak cells condemn the pack; reliability comes from architecture | Survival of n cells in series versus tolerating k dead cells; budget limited by the inverter voltage floor | `hackkit/reon_reliability.py`, dashboard tab 9 |
| Why not balance? Loss goes as I squared R | Balancer feasibility: needed current, efficiency, heat, hours to balance, passive and active limits | `hackkit/reon_balance.py`, dashboard tab 10 |
| Module-level second life still has within-module spread | Granularity ladder: cell, module, none; between-module share swept | `hackkit/reon_ladder.py`, dashboard tab 10 |
| REON costs 3 to 4 times a BMS | Extra-cost-only switch: (k-1)/k of the total | `reon_system.incremental_cost`, dashboard tab 1 |
| Use state blackout statistics; midnight storm scenario | State picker with SAIDI, SAIFI, CAIDI beside the backup hours | `examples/data/eia_reliability_by_state.csv`, dashboard tab 4 |
| Do not publish sensor data; value is in curves and trends | Sample first-look script; REON samples blocked from git | `examples/reon_bms_sample_check.py`, `.gitignore` |

### 250 series elements, value 40 per kWh-year, switch loss 4%, 8 trials (verdict picked on one seed, checked on another)
12-year bankable horizon (warranty is 10 years):
- Single cells (p = 1): fade 0.004 a year, gain over plain +11.8 per kWh and a tie with a balancer (margin -0.5); 0.008, +27.3 (margin +8.2); 0.02, +99.4 (margin +88.7).
- Parallel groups of 4: gain +6.2 at 0.004 and +8.0 at 0.008, ties with a balancer; +70.2 at 0.02.
- Parallel groups of 16: +1.1 and +2.7 at slow fade; +44.5 at 0.02.
- Parallel groups of 40: HOLD at 0.004 and 0.008 (gain about 0); +32.8 at 0.02.
- Counting only the extra cost over a BMS (x0.7): p = 1, 0.008, +31.9 (from +27.3); p = 40 still HOLD.

Cell-limited life (30-year horizon), system cycles at one cycle a day, plain versus best of ours:
- p = 1, fade 0.004: 7,825 vs 10,950 (capped); 0.008: 3,992 vs 8,669; 0.02: 1,711 vs 3,536.
- p = 40, fade 0.008: 6,775 vs 8,965; 0.02: 2,806 vs 3,650.

What this says: with single large cells the plain string reaches 70% at about 4,000 cycles (fade 0.008), half the 8,000-cycle system standard, and per-cell control roughly doubles that. With parallel groups and slow fade, the capacity case disappears inside a bankable horizon, so uptime and avoided visits carry the argument. Gains beyond about 15 years are not bankable (inverter and enclosure life), which is why the 30-year figures are shown as cell-limited life only.

### Balancing (Monolithic Power for the 0.25 A and 6 A limits; path resistance assumed)
Needed balancing current is load current times the capacity gap. A 15% gap at 0.5C on a 100 Ah cell needs 7.5 A, over the 6 A limit; a 32% gap exceeds it at all but the gentlest settings.

### Module versus cell (our simulation)
240 cells in modules of 24, 10% mean capacity loss: switching whole modules keeps 42% of the cell-level gain if all the spread is inside modules and 76% if 90% of it is between modules.

## What this means for the pitch
- If the cells really fade 0.4 to 1.2% a year, lead with reliability and avoided crew visits at remote sites, not with extra capacity. Capacity gain returns above about 0.006 a year, which hot cabinets and two cycles a day reach. Lead with reliability and avoided crew visits at remote sites, not with extra capacity. Capacity gain is the headline only at normal lithium-like fade rates.
- The 20,000-cycle figure is the cell maker's claim and REON said so himself. Ask him for a measured cell-to-cell spread on sodium.
- Say where the method does not pay: cheap crew visits, switch cost above the sourced range, low value per kWh. The dashboard shows a HOLD or a "does not pay here" banner for those.
- Hostile draws are wider than any sourced range on purpose; the 84% to 85% figure is for the sourced ranges.

## Still not tested or still assumed
Sodium fade and life, fault rate, visit cost, value of lost load, inverter minimum voltage, sensing noise on a real REON board.
