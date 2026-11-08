# Sag model assumptions (`hackkit/reon_sag.py`)

Rows in the `docs/SOURCES.md` format, ready to paste. Every number here is ASSUMED or DERIVED; none is REON's measured value.

| Item | Value (range) | Tag | Source / note |
|---|---|---|---|
| Sag model: string voltage | V = sum over engaged cells of (OCV(soc_i) - I x R_i); stop when V < v_floor_frac x 250 x 3.6 V, or when an empty cell cannot be bypassed | ASSUMED | `reon_sag.usable_fraction`; constant current (no rise in current as the string sags), equal OCV curve shape for all cells, no temperature, no relaxation |
| String minimum voltage (inverter floor) | 0.9 of 900 V = 810 V default (sweep 0.6 to 0.9) | ASSUMED | 0.9 is the REON CTO's cell-count window carried over to volts; the inverter minimum voltage itself is UNKNOWN (top question for REON) |
| Nominal string voltage | 250 x 3.6 V = 900 V | DERIVED | 3.6 V nominal from the INR18650-20EB datasheet (SOURCES row "Sodium-ion 18650 cell"); note `reon_voltage` normalises to OCV(0.5) = 3.65 V instead |
| Cell discharge cutoff | 2.5 V terminal (OCV - I R) | CITED | same datasheet |
| Cell OCV curve | `reon_voltage.CURVES["sodium-ion"]`: 2.5 / 3.0 / 3.65 / 4.05 / 4.2 V at SOC 0 / 0.1 / 0.5 / 0.9 / 1 | ASSUMED (shape) | shape inside the sourced 2.5 to 4.2 V window; no sodium discharge curve is sourced |
| Cell capacity | 66.7 Ah per series cell | DERIVED | 60 kWh / (250 x 3.6 V); EBS Na+ one pager |
| Discharge current | 33.3 A (rated 30 kW / 900 V, about 0.5 C); low end 5.6 A (5 kW load) | DERIVED | rated power from the EBS Na+ one pager; rated is the worst case for sag. Pass `current_a` for the site's load |
| Cell resistance | 0.6 mOhm per 66.7 Ah cell (sweep 0.3 to 3 mOhm; per-cell arrays allowed) | ASSUMED | 20 mOhm AC IR upper bound for a 2 Ah 18650 (datasheet) scaled by 2 / 66.7 Ah, assuming the cell is built from parallel 18650s; AC IR understates DC resistance, and aged cells run higher (Relectrify: spread up to 2.63 mOhm between cells) |
| Usable-energy denominator | each cell's own zero-current energy from full to empty, summed | DEFINITION | so 1.0 = every cell emptied and nothing lost in R |
| Year-10 sanity pack | day-1 caps 1 +/- 2 %, fade 0.8 %/yr per cell with CV 0.45 (200 draws) | ASSUMED | fade from `reon_presets` (0.008), CV from `reon_storefront` (0.45 / sqrt(p), p = 1) |

## Sanity result (median of 200 draws, rated current, R = 0.6 mOhm)

| Pack | Floor | plain | at most 25 bypassed | unlimited bypass |
|---|---|---|---|---|
| fresh | none (cell count only, R = 0) | 0.959 | 0.981 | 1.000 |
| fresh | 0.9 of 900 V | 0.777 | 0.777 | 0.777 |
| year 10, 0.8 %/yr | none (cell count only, R = 0) | 0.907 | 0.957 | 1.000 |
| year 10, 0.8 %/yr | 0.8 of 900 V | 0.899 | 0.919 | 0.919 |
| year 10, 0.8 %/yr | 0.9 of 900 V | 0.776 | 0.776 | 0.776 |

Meaning: on this sloped sodium curve a 810 V floor stops even the plain string near 3.24 V per cell (SOC about 0.27), before the weakest cell is empty, so bypass adds nothing (same as the team's 0.0 % at the 90 % floor on 12 real packs). R from 0.3 to 3 mOhm moves the year-10, 0.9-floor figure from 0.784 to 0.715.
