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
