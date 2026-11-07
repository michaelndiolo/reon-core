# Stress tests (7 Nov 2026)

Every run is reproducible from `examples/`; saved outputs sit beside the scripts.

| Test | Script | Result |
|---|---|---|
| Input fuzz, warnings as errors | `reon_fuzz.py` | 0 unexpected failures; bad inputs stop with a clear message, never silent NaN or infinity |
| Hero case, inputs from real sources, fresh seeds | `reon_hero_stress.py sourced` | 280 earlier draws: beats best rival 85%, plain 95%. 186 fresh draws (seeds 9001, 9002): 84% and 94%, median margin +13 per kWh. Worst draw -5.6 per kWh (low value, high switch cost) |
| Hostile packs: BUY verdict scored on an unseen seed | `reon_adversary.py` | 96 draws (dead cell, hot cell, bimodal, ramp, identical, wide, tight; switch cost to 45, fade spread to 0.9): 70 BUY, 26 HOLD, 0 false BUY. Every HOLD had at most +5 per kWh left on the table. A first version with a strict p10 rule had 2 false BUYs in 40, both outside sourced ranges; the rule was relaxed to 5% of the gain and the check seed gets twice the trials |
| Hostile sites: string life with faults and crews | `reon_events_adversary.py` | 400 draws. Automatic bypass loses to a fixed threshold in 10% and to replace-on-failure in 31%. Replace wins when a visit costs under about 300. Thresholds win when the bypass budget is 1 and switch loss is above 6% |
| Per-site policy chooser | `reon_events_selector_test.py` | 240 draws, regret vs best policy in hindsight on unseen seeds: chooser 1.3 mean (worst 34), always ours+crew 10.9 (worst 110), best fixed threshold 36.2, always replace 50.7 (worst 481). Chooser picks automatic bypass at 147 of 240 sites |

## What this means for the pitch
- Say where the method does not pay: cheap crew visits, switch cost above the sourced range, low value per kWh. The dashboard shows a HOLD or a "does not pay here" banner for those.
- Hostile draws are wider than any sourced range on purpose; the 84% to 85% figure is for the sourced ranges.

## Still not tested or still assumed
Sodium fade and life, fault rate, visit cost, value of lost load, inverter minimum voltage, sensing noise on a real REON board.
