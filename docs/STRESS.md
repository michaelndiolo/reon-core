# Stress tests (7 Nov 2026)

Every run is reproducible from `examples/`; saved outputs sit beside the scripts.

| Test | Script | Result |
|---|---|---|
| Input fuzz, warnings as errors | `reon_fuzz.py` | 0 unexpected failures; bad inputs stop with a clear message, never silent NaN or infinity |
| Hero case, inputs from real sources, fresh seeds | `reon_hero_stress.py sourced` | 280 earlier draws: beats best rival 85%, plain 95%. 186 fresh draws (seeds 9001, 9002): 84% and 94%, median margin +13 per kWh. Worst draw -5.6 per kWh (low value, high switch cost) |
| Hostile packs: BUY verdict scored on an unseen seed | `reon_adversary.py` | 96 draws (dead cell, hot cell, bimodal, ramp, identical, wide, tight; switch cost to 45, fade spread to 0.9): 70 BUY, 26 HOLD, 0 false BUY. Every HOLD had at most +5 per kWh left on the table. A first version with a strict p10 rule had 2 false BUYs in 40, both outside sourced ranges; the rule was relaxed to 5% of the gain and the check seed gets twice the trials |
| Hostile sites: string life with faults and crews | `reon_events_adversary.py` | 400 draws. Automatic bypass loses to a fixed threshold in 10% and to replace-on-failure in 31%. Replace beats automatic bypass in 56% of draws where a visit costs under 300 (153 draws). A threshold beats it in 32% of draws with a bypass budget of 1 and switch loss above 6% (31 draws), against 8% in the other draws |
| Per-site policy chooser | `reon_events_selector_test.py` | 240 draws, regret vs best policy in hindsight on unseen seeds: chooser 1.3 mean (worst 34), always ours+crew 10.9 (worst 110), best fixed threshold 36.2, always replace 50.7 (worst 481). Chooser picks automatic bypass at 147 of 240 sites |

## Added later on 7 Nov: fixes for the losing regimes, Tim's answers, crew time
| Test | Script | Result |
|---|---|---|
| Bridge policies (bypass at once, then book the crew after 1 or 2 bypassed cells) | `reon_events_fixes.py` | Same 400 hostile draws, switch loss now charged to threshold rivals too. Losses to replace-on-failure fall from 33% (ours+crew only) to 14% (best of the bridge family, chosen on separate seeds). Cheap visits (under 300): 56% to 18%. Budget 1 and loss above 6%: 13% to 6% vs replace. Losses to the best threshold: 2% to 1%. With thresholds free of switch loss (the old, rival-friendly reading): 11% to 8% |
| Per-site chooser, bridge variants included | `reon_events_selector_test.py` | 300 draws: regret 1.1 per kWh mean (worst 30) vs always ours+crew 17.2, best fixed threshold 67.6, always replace 54.9 (worst 481). It picks automatic bypass at 257 of 300 sites (was 147 of 240) |
| Sensing error of 5% (Tim Ren) | `reon_sensing_noise.py` | Worst case, a fixed per-cell error within +-5%: false bypass 1 in 1,000 healthy cells at weak line 0.15, 0 at 0.20; a cell 20% weak is caught every time, 15% weak about half the time. Line 0.10 would false-bypass 17 in 1,000. Keep 0.15 |
| Crew time to identify and fix | `reon_crew_time.py` | Automatic bypass keeps the string up while a crew is found. With a downtime cost of 20 per kWh nameplate per month, the gain over replace-on-failure is +47 (detect 0, lead 0.5 months) to +273 (detect 6, lead 3). At zero downtime cost it is +7 to +18, so the value is resilience, not energy. Lead below one month rounds to one month (monthly steps) |
| Grid restoration anchors | `reon_crew_time.py` part 2 | A 60 kWh pack at 5 kW lasts 9.8 h plain, 10.4 h managed, 17.4 h with load shed to 60% (median of 12 real packs). That covers the U.S. typical outage and Maine's 8 h average in 2024, but not Florida's 12.4 h without load shed, and nothing covers a 72 h outage without solar |
| Long-life sodium (20,000 cycles) | `reon_hero_stress.py longlife` | **Warning.** 150 draws with fade 0.003 to 0.012 a year and life 10 to 25 years: beats the best rival only 46% of the time, plain 77%, median margin about 0, median gain over plain +5.4 per kWh (versus +13 at normal fade). Capacity spread barely opens when cells fade this slowly. Fault tolerance still pays: in the string-life simulation at 0.004 fade with a fault rate of 0.01 per cell-year and visits of 3,000, automatic bypass nets 276 vs 200 for replace-on-failure (163 with a downtime cost) |

## What this means for the pitch
- If the cells really fade 0.4 to 1.2% a year, lead with reliability and avoided crew visits at remote sites, not with extra capacity. Capacity gain is the headline only at normal lithium-like fade rates.
- The 20,000-cycle figure is the cell maker's claim and Tim said so himself. Ask him for a measured cell-to-cell spread on sodium.
- Say where the method does not pay: cheap crew visits, switch cost above the sourced range, low value per kWh. The dashboard shows a HOLD or a "does not pay here" banner for those.
- Hostile draws are wider than any sourced range on purpose; the 84% to 85% figure is for the sourced ranges.

## Still not tested or still assumed
Sodium fade and life, fault rate, visit cost, value of lost load, inverter minimum voltage, sensing noise on a real REON board.
