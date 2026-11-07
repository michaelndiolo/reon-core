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
