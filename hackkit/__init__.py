"""Decision layer for REON's cell-level control challenge.

Engine: reon_wear / reon_design (ageing, retirement, builds, recommended policy), reon_unit / reon_econ / finance
(profit per kWh, payback, break-even), contract (weak cell vs bad sensor), flex (price-driven dispatch), reon_carbon
(CO2e). Streamlit helpers: headline, ui. Submodules are imported directly
(e.g. `from hackkit import flex`), not re-exported here, so a missing optional dependency (streamlit)
only breaks the module that needs it.
"""
