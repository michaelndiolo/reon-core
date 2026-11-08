# Sources for the hero case (7 Nov 2026). Tags: REAL = data we computed from, CITED = number read from the source, DERIVED = our arithmetic, ASSUMED = no source yet.

| Item | Value | Tag | Source / note |
|---|---|---|---|
| Commercial demand charges | Nearly 5 million commercial customers (over a quarter of 18 million) can subscribe to tariffs with demand charges above $15/kW | CITED | NREL survey of US demand charges, https://www.osti.gov/biblio/1374803 (abstract only; no median given) |
| Value of a 60 kWh / 30 kW unit from demand charge alone | up to 30 kW x $15 x 12 / 60 kWh = $90 per kWh-year | DERIVED | Assumes 2 h duration and a full peak cut every month; real value is lower. Sweep uses 40 and 80 |
| Value of energy shifting | 12 (grid preset) and 22 (German day-ahead, retired-EV preset) per kWh-year | REAL / CITED | repo presets, see docs/background/REON_DATA.md |
| Sodium-ion cell spread, new | Capacity spread 0.69 to 1.03 % standard deviation over 20 cells per batch (two commercial 18650 NFM111/hard-carbon batches) | CITED | RSC paper d5eb00161g, https://pubs.rsc.org/en/content/articlehtml/2025/eb/d5eb00161g . Small lab cells, not REON's. Our start spread (2 %) is more conservative |
| Sodium-ion ageing | Below 80 % of initial capacity by about 300 to 350 cycles at 0.5C, 0 to 100 % SOC, 25 C; one batch showed a sharp knee after about 100 cycles and one cell fell to 40 % | CITED | same paper. Evidence that fade spread between sodium cells can be large; says nothing about REON's cells or gentler duty |
| Fade-rate spread | CV 0.20 to 0.60, median 0.45 across 12 cars | REAL (lithium) | Nature Energy 2026 Fig 4 source data, examples/data/nature_fig4_cells.csv |
| REON overhead | $560 to $1,920 per 80 kWh string = $7 to $24 per kWh nameplate; BMS about 3 times a conventional one, about 2 to 3 % of system cost | CITED | Tim Ren, REON CTO, event Discord 7 Nov and via Nalia's PDF. Unclear whether this is per kWh with a switch on every cell |
| Mini-grid batteries | Lithium-ion is replacing lead-acid; report recommends field testing, standards, training. No replacement or visit cost given | CITED | ESMAP 2023, https://www.esmap.org/Energy_Storage_for_Mini_Grids |
| Cost of one site visit | not found | ASSUMED | still needed for the remote-site case |
| Life, fade rate for sodium C&I unit | 12 years, 2 % a year | ASSUMED | no REON data |
| Sodium LCA | not done yet | CITED | Tim Ren, Discord 7 Nov |

## Added 7 Nov (afternoon): storm, cold and safety sources for the four responses
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Maine wind storm, 18-19 Dec 2023 | More than 420,000 outages statewide at the peak (early Tuesday). Five days later (Sunday) Versant still had 1,327 customers out, 900 of them in Penobscot County, and CMP 513 | CITED | Bangor Daily News: https://www.bangordailynews.com/2023/12/19/weather/maine-wind-storm-power-outages-chart/ and https://www.bangordailynews.com/2023/12/23/news/nearly-12000-mainers-still-without-power-saturday (the second article is internally inconsistent about counties; use the numbers with care). The claim "Penobscot out three days" is NOT confirmed here: ask the person who stated it for the source |
| Cold, sodium-ion vs lithium-ion | At or below -20 C lithium-ion keeps about 30 to 50 % of room-temperature capacity, engineered sodium-ion about 50 to 70 %; hard carbon shows strong polarization and early voltage cutoffs; charge-transfer resistance 3 to 5 times higher at -40 C | CITED | RSC review https://pubs.rsc.org/en/content/articlehtml/2025/eb/d5eb00121h (a review of other studies, mostly lab cells) |
| Cold charging, sodium-ion | Vendor says sodium-ion can be safely charged down to -20 C and keeps 70 % at -40 C and 2C | CITED (vendor claim) | Acculon blog https://acculonenergy.com/powering-through-the-freeze-sodium-ion-cold-temperature-testing-insights/ . Marketing page, no test data shown; do not rely without REON's own limit |
| Thermal runaway warning | In 30 mechanical-abuse tests (20 reached runaway) the best model gave about 15.6 s warning; runaway onset 150 C or 3 C/s; regimes safe below 60 C, warning 60 to 120 C, danger above 120 C | CITED | arXiv 2607.18860 (lithium, lab). Meaning for us: runaway is too fast for a policy layer that works over minutes, so the KILL for it belongs to the certified hardware; our layer handles slow fault signs |
| PMC thermal-runaway review | not read (page returned a bot check; not worked around) | - | https://pmc.ncbi.nlm.nih.gov/articles/PMC12152129 |

## Added 7 Nov (3 pm): REON's own materials, sodium cell data, similar company
| Item | Value | Tag | Source / note |
|---|---|---|---|
| REON illustration | Five cells: usable = min x N = 300 of 460 Ah without control; up to 460 Ah (sum) with cell-level control | CITED | REON_MIT_Energy_Climate_Hack_Slides.pdf (REON folder of the hack Drive) |
| EBS Na+ | 30 kW / 60 kWh sodium-ion Energy Block System for commercial and industrial sites; described as the first UL-certified sodium-ion storage system, wide temperature range | CITED | same slides and REON_WHO_WE_ARE.pdf (one pager) |
| REON range and applications | FES 21-25 kW / 50 kWh; OES100/300 30-120 kW / 66-313 kWh; CES 2.5 MW up to 5 MWh; EMS software. Applications listed: solar pairing, communities and resiliency, backup power, C&I, EV charging; use cases: bill saving, solar + off-grid, grid services, backup. Claims 2 to 4 times performance (patent-pending), team behind over 10 GW deployed | CITED (company material) | REON one pager. Resiliency and off-grid ARE in REON's own market |
| REON DC voltage, inverter minimum | not given | UNKNOWN | ask Tim; our voltage test sweeps it |
| Sodium-ion 18650 cell | nominal 3.6 V, charge cutoff 4.2 V, discharge cutoff 2.5 V, 2 Ah, AC internal resistance up to 20 mOhm; no discharge curve (one conflicting shipping-state point) | CITED | Shenzhen Asia Technology INR18650-20EB spec, https://mikrocontroller.net/attachment/540580/Specification_Rechargeable_sodium_ion_battery.pdf . Curve shapes in reon_voltage.py are ASSUMED inside this window |
| Similar company: Relectrify (cell-level control, second-life) | ReVolve 36 kW / 120 kWh from nine Leaf packs; SoH differs up to 32 % between cells; resistance varies up to 2.63 mOhm; usable capacity up over 20 % for a degraded set; one cell bypassed 32 h stayed near 25 % SoC with zero current; 2 to 3 % degradation a year; no inverter voltage window given | CITED | ARENA final report https://arena.gov.au/assets/2025/05/Relectrify-Second-life-battery-trial-Final-knowledge-sharing-report.pdf (pages 3, 8, 11, 13-14, 21) |
| Similar sodium system | HiNA 50 kW / 100 kWh station: discharge voltage differential 102 mV with continuous active balancing vs 240 mV without; 97.6 % capacity retention after 1,500 cycles; round-trip 93.9 % | CITED (abstract only) | SAE paper 2026-99-1723, https://trid.trb.org/View/2706246 . Abstract is inconsistent on kW vs kWh |

## Added 7 Nov (3:45 pm): gap-closing round
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Demand charges, how many customers | About 5 million (over a quarter of 18 million) US commercial customers can subscribe to tariffs above $15/kW, about 3 million (15 %) above $20/kW; demand charges are 30 to 70 % of commercial bills; state average of utilities' top charges ranges from $5.83 (Georgia) to $17.43 (Vermont), medians $3.60 to $16.05 | CITED | NREL survey https://www.nrel.gov/docs/fy17osti/68963.pdf . Meaning: our $40 to $90 per kWh-year range holds only for the top quarter of customers; at $5/kW-month the same 30 kW / 60 kWh unit earns about $30 (DERIVED, 2 h, full peak cut every month). Stress test already spans 10 to 90 |
| System failure rate | Stationary lithium-ion systems fail at 0.04 to 0.14 % a year (EPRI compares with about 0.1 % for oil-filled transformers); global failure rate fell 98 % from 2018 to 2025; older systems fail more; no split by cause | CITED | Utility Dive on the EPRI report https://www.utilitydive.com/news/battery-system-failures-fell-98-in-7-years-but-older-systems-need-special/832882/ . These are system incidents, not dead cells, so they do not set our per-cell fault rate. Per cell-year this implies far below our 0.002 sweep floor for NEW systems; 0.002 to 0.03 stays as the second-life / harsh-site range. Event sim re-run at 0.0002 and 0.001 |
| Off-grid systems left unmaintained | Batteries often go unreplaced; a World Bank official is quoted that systems stop working within two to three years; 78 % of stakeholders cite lack of technical skills as the main barrier to remote maintenance; no costs or visit counts | CITED (qualitative) | arXiv 2507.21314 https://arxiv.org/html/2507.21314v1 . Supports the no-crew argument, gives no number |
| Cost of a crew visit | not found in ESMAP, MicrogridNews or the off-grid paper | ASSUMED | still open |
| Value of lost load per kWh | not found; the LBNL ICE update lists regional GDP per kWh (average $6.93, range $2.8 to $16) which is not an outage cost | ASSUMED | still open; storm page shows a break-even instead |
| Not read | energy-storage.news EPRI page (site error); PMC thermal-runaway paper (bot check) | - | not worked around |

## Added 7 Nov (evening): Tim Ren's answers (Discord, 3:33 pm) and grid restoration times
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Switch overhead | "Very minimum overhead, but not none" versus a conventional busbar; depends on the internal impedance of the switches. No number given | CITED (REON CTO, verbal) | our 2% default for conduction loss stays ASSUMED; swept 0 to 12% |
| Warranty, stationary | Industry standard 10 years / 8,000 cycles (mostly from the cell maker) | CITED (REON CTO, verbal) | |
| Cell life | REON's sodium cells are 20,000-cycle NFPP | CITED (REON CTO, verbal; maker claim, not verified) | implies about 0.4 to 1.2% fade a year at one cycle a day; hero stress mode `longlife` uses 0.003 to 0.012 |
| Per-cell capacity/SOH sensing accuracy | "Within 5%, often much better; industry standard is around that" | CITED (REON CTO, verbal) | `examples/reon_sensing_noise.py`: weak line 0.15 stays safe |
| Installed price per kWh | commercial team question (EPC, FEOC, incentives) | UNKNOWN | |
| Time for a utility to restore power | EIA-861 Table 11.3 (2025 / 2024), CAIDI, minutes per interruption. U.S. without major events 115 / 121; with major events 196 / 402. Maine with major events 162 / 481; Florida 82 / 747 | REAL | https://www.eia.gov/electricity/annual/html/epa_11_03.html. This is grid restoration, not time to service a battery cell |
| Time to identify, dispatch and repair a battery fault | not found | ASSUMED | lead 0.5 to 3 months and detect 0 to 6 months are swept in `examples/reon_crew_time.py` |
| Cost per month a string is down | not found | ASSUMED | swept 0 to 60 per kWh nameplate per month |
| Fade from the cell claim | 20,000 cycles to 80 % = 0.01 of capacity per 1,000 cycles at 25 C; 0.0037 a year at one cycle a day | CITED claim, unverified | `reon_presets.fade_per_year` |
| Temperature effect on ageing | doubling per 10 C | ASSUMED (common rule of thumb, not measured on sodium) | stress mode `sitefade` |
| Site presets | C&I with a crew nearby; remote minigrid with no crew: visit cost, lead, detect, downtime cost, fault rate | ASSUMED | `hackkit/reon_presets.py` |
| Current shedding lowers switch loss | conduction loss share = I x R / V | DERIVED (physics) | `slack` in `reon_events.simulate` |

## Added 7 Nov (night): customer front page and environmental number
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Embodied carbon, sodium-ion pack | 56.8 kg CO2e/kWh cradle to gate (China); LFP pack 75.5, about 25 % higher. The study does not account for cycle life | CITED | Environmental Impact Assessment Review study, reported by ess-news.com; read through the article, not the paper itself |
| Embodied carbon, cell level (opposite ranking) | sodium-ion 75 to 87, LFP 59 to 70 kg CO2e/kWh | CITED | Fraunhofer / RWTH 2025 as reported; cell level, not pack level, so not directly comparable |
| Embodied-carbon range used | low 56.8, high 87.0, base 68.9 (midpoint of 56.8 and 81, the middle of 75 to 87) | DERIVED | `hackkit/reon_enviro.py`; wired through `reon_carbon.carbon_balance` and `sensitivity` |
| Share of avoided cells that would really have been replaced | 0.5 / 0.8 / 1.0 | ASSUMED | no source; shown as a range |
| Embodied carbon of REON's control electronics | 1 / 4 / 10 kg CO2e per kWh nameplate, counted in full | ASSUMED | no source; conservative (whole electronics, not the extra over a BMS) |
| Grid emissions saved | 0 | not claimed | manufacturing carbon only |
| Cells not replaced | nameplate x horizon x (1/life plain - 1/life ours) | DERIVED | lives come from the simulated engine (cell-limited, capped at 30 years) |
| Storm-night backup hours | median over 12 real car packs, 60 kWh, steady load, 80 % cold capacity | REAL cell data, ASSUMED sodium behaviour | `reon_storefront.backup_hours`; switching adds under an hour on day one |
| Front-page dollars | first 12 years only, whole 60 kWh battery | DERIVED | `reon_storefront.storefront`; cases in `examples/reon_storefront_cases_output.txt` |

## Added 7 Nov (late): deployment and policy
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Commercial storage installed 2025 | Community, commercial and industrial about 95.6 MW of 18.9 GW (51 GWh) total; Wood Mackenzie forecast: 39% growth 2025 to 2030, dip in 2026 | CITED | https://www.ess-news.com/2026/03/25/us-energy-storage-installations-reach-record-51-gwh-in-2025/ (ACP release gave only Q4 2025 C&I, 77 MW). The roughly 0.5 GW by 2030 figure is OUR extrapolation (95.6 x 1.39^5, ignores the 2026 dip) |
| Storage tax credit and FEOC | Sections 48 and 48E; storage escapes the early wind/solar sunset; prohibited-foreign-entity material-assistance rules stricter for storage; preliminary Treasury guidance Feb 2026 | CITED | https://www.morganlewis.com/pubs/2026/03/how-feoc-rules-are-reshaping-energy-storage-tax-credit-eligibility . The article gives no percentage or thresholds: check the statute and IRS guidance before quoting any number |
| Where REON's cells are made | unknown | UNKNOWN | decides tax-credit eligibility; ask REON |
| Certification path | UL 9540, UL 1973, NFPA 855 named in industry guidance | CITED (named only, not read) | not verified for REON; REON engineers to confirm. Claim that our layer sits outside the safety loop is DESIGN INTENT |
| Value from a tariff | demand charge x 12 / hours of storage per kW | DERIVED | tab 12; at $5/kW-month and 2 h about 30 per kWh-year |
| Sensitivity ranking | `examples/reon_tornado_250_output.txt` | DERIVED | tab 11; 250 cells, single cells, one input at a time |

## Added 7 Nov (late night): precomputed cases and second life
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Precomputed demo cases | 88 engine results at 250 cells (p 1/4/16/40 x fade 0.004/0.006/0.008/0.012/0.02 x value 12/22/40/80, plus 8 tariff-screen values; 0.006 and 0.012 feed the gain-versus-wear chart) | DERIVED | `examples/data/storefront_cases.json`, made by `examples/reon_precompute_cases.py`; a test recomputes one case and fails if the file is stale |
| Second life, cell data | 12 retired EV packs, 95 cells each, capacity at 280,000 km | REAL | Nature Energy 2026 Fig 4 (`examples/data/nature_fig4_cells.csv`) |
| Second life, voltage window | at least 50/70/90% of cells stay in the string; modules obey the same window | CITED (REON CTO: about 90% connected in normal use, unclear) / ASSUMED | `hackkit/reon_secondlife.py` |
| Second life, flip cost | value per kWh-year x years x extra usable share, after switch loss; compared with REON's 7 to 24 per kWh | DERIVED | static, no further ageing; testing and disassembly not priced (REON has not said) |
| Value of lost load (an anchor) | $35,685 per MWh = about $35.7 per kWh, blended residential, commercial and large industrial, ERCOT region; PUC of Texas adopted Brattle's study 29 Aug 2024 | CITED | https://www.utilitydive.com/news/texas-power-outages-cost-consumers-VOLL/726807/ (article only; the Brattle report itself not read). Small commercial and industrial said to have "disproportionately high" VOLL, no number given. A teammate's $5.92 per kWh "summary of 90 estimates" and a $6 to $54 band were NOT verified |

## Added 7 Nov (night): string view and material
| Item | Value | Tag | Source / note |
|---|---|---|---|
| String view, cell health | 250 cells drawn from the pooled REAL relative spread of the 12 retired EV packs, scaled to mean health 0.85, plus planted weak cells at 0.70 and 0.78 | REAL spread, ASSUMED mean | `hackkit/reon_grid.py`; the planted cells echo REON's 16-cell example |
| String view, how many cells may leave | floor(n x (1 - window)); window 0.9 gives 25 of 250 | CITED (REON CTO: about 90% connected, unclear) | `reon_reliability.bypass_cap` |
| Open cell in a plain string | delivers nothing; control bypasses it | DERIVED (series circuit); REON to confirm bypass time and whether the inverter trips | open question added for REON |
| Battery material not made | cells avoided x 10 kg per kWh | ASSUMED | placeholder from the team's earlier candidate-solutions file; replace with REON's pack mass |
| Three-policy hours | plain, cell-level, cell-level with half the load shed; median of 12 real packs, 80% cold capacity | REAL cell data, ASSUMED sodium behaviour | `reon_storefront.backup_policies` |

## Added 7 Nov (night): cell trends and gain against wear
| Item | Value | Tag | Source / note |
|---|---|---|---|
| Fade slope per cell | capacity lost between 80,000 and 280,000 km for each of 95 cells in 12 retired EV packs | REAL | Nature Energy 2026 Fig 4 (`examples/data/nature_fig4_cells.csv`); `hackkit/reon_slope.py` |
| Neighbour comparison | each cell against the median of the 8 nearest cells in the order the data give; flagged when its excess is above 3 robust standard deviations | DERIVED | In a real string the order would be the wiring order |
| Snapshot versus trend | final-weakest cell was also weakest early in only 1 of 12 packs; the steepest fader was the final weakest in 8 of 12; fade spread above start spread in 12 of 12 | DERIVED | Two ages give a slope, not a curve; this is not an out-of-sample forecast |
| What "slope and curve" meant | Tim Ren's recorded wording is garbled; this is our reading | OPEN | confirm with Tim; REON per-cell history would give the real curve |
| Gain against wear | 12-year gain per kWh at fade 0.004 to 0.02, four parallel arrangements, four values of a kWh-year | DERIVED | `reon_storefront.gain_vs_fade` reads only the cached cases |
| State tile map | 51 tiles in an NPR-style grid; layers Exposure (SAIDI major events 2025), Coverage (cell-level backup hours / CAIDI major 2025 in hours), Where to pilot (SAIDI hours x kW x value of lost load) | REAL (EIA-861) / DERIVED | `hackkit/reon_map.py`; utility-wide state averages, not a store's own record; the only sourced value of lost load is the Texas anchor (35.7 $/kWh), everything else on the slider is the user's choice |

## Added 7 Nov (night): checks after a teammate's review
| Item | Finding | Tag | Note |
|---|---|---|---|
| numbers.json | was a stale 16-cell export (11.4 per kWh, 9.8 h plain, no cold factor); regenerated from the same 250-cell cached cases the dashboard shows (27.3 per kWh, 7.9 / 8.4 / 16.7 h) | FIXED | `examples/export_numbers.py` now reads `storefront_cases.json` and `reon_storefront.backup_policies` |
| System boundary | energy and hours are counted at the string DC terminals; no inverter loss, no solar; kW power capability not modelled | OPEN (stated on the page) | a lifetime delivered-kWh figure, plain against ours, is still to add |
| Voltage floor in the life simulation | the late-switch and level-switch builds in `reon_wear` bypass any number of empty cells; only the selective and hybrid builds are limited (at most 25 of 250 switches); `reon_events` limits a count (n_min), not a voltage | FIXED 8 Nov | `reon_wear.wear_scan(window=0.9)`: every build may bypass at most 25 of 250 cells at once (`window_usable` row by row); selective and hybrid counts above the cap are dropped. `reon_storefront.WINDOW = 0.9` feeds the cached cases, the tornado and the live tabs. Typical single-cell case 27.3 -> 15.3 per kWh (919 over 12 y, pessimistic 25), life 10.9 / 16.0 y; hard wear 99.4 -> 34.2; gentle wear unchanged (11.8, hybrid already within the cap). One case flipped (value 12, fade 0.02, single cell: BUY -> HOLD). Inverter minimum still UNKNOWN. Unbounded results kept in `examples/data/storefront_cases_unbounded.json`; older studies (`reon_hero_250*`, `reon_losing_regimes`, the tab-2 break-even table) were run without the window |
| Switch loss on all switched energy | the dollar engine charged the 4% usable-energy loss only on the extra energy beyond plain, so a switched string's baseline energy was loss-free; the backup-hours calculation already charged 2% on all of it (Aaryan's check, REON requirement 7: both packs measured at the same named point) | FIXED 8 Nov | `reon_storefront.CLOSED_LOSS = 0.02` (ASSUMED) is now passed in every build (`_kw`, live tabs, tornado). Backup hours also respect the voltage window: managed 8.35 -> 8.08 h, shed 16.7 -> 16.16 h, plain 7.87 h. Typical single-cell case 15.3 -> 17.7 per kWh because the pick flips from late switches to the hybrid with a 5% balancer (pessimistic 12.1); REON switches alone fall to 9.7 per kWh at 0.8% fade and 0.6 at 0.4% fade |
| Cell-count window vs voltage sag | the window counts cells; real cell voltage sags near the end of a discharge so more cells must stay engaged | OPEN (stated on the page) | `reon_voltage` on 12 real packs: median energy gain over plain at a 90% floor is 4.3% by cell count and 0.0% with sag (ideal 32.0%). Dollar figures are an upper bound until REON gives the inverter minimum voltage; top question for REON |
| Balancer strength | an active balancer (transfer limit r = share of a cell's capacity moved per cycle, efficiency 0.9, cost 4 per kWh) is the rival; r = 5% is our assumption | ASSUMED | `examples/reon_balancer_sweep.py`, `examples/data/balancer_sweep.json`. Single-cell, 0.8% fade: a balancer matches REON switches alone at about 2.8%; at 2% fade the crossover is about 12%. Page expander "Against a simple balancer" |
| Stress branch assumptions (stress/aaryan) | sag floor, policy search, adversary cases | ASSUMED | every assumed parameter is listed with value and range in `docs/stress/sag_assumptions.md` (cell resistance 0.6 mOhm assumed, swept 0.3 to 3; current 33.3 A at rated 30 kW / 900 V, 5.6 A at 5 kW), `docs/stress/policy_assumptions.md` (retrofit labour 0 in lap 1, rest-energy price 0.15 per kWh, scaled balancer cost 4 x r / 5%), `docs/stress/adversary_assumptions.md` (cold = capacity x 0.75, fail-open = capacity 0 from day 1). None are sourced |
