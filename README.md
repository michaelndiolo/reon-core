# reon-core

Decision layer for REON's "Beyond the Weakest Cell" challenge (MIT Energy & Climate Hack, Nov 2026).

A plain series string delivers only as much as its weakest cell. REON's per-cell switching lets every good cell
work. This repo does not design the switch hardware (the brief says we need not). It answers the decision:
**which cells to bypass, when it pays, and what it is worth against a plain string, a sort-only pack, a balancer
and a simple threshold rule.**

One hero application: a 60 kWh REON EBS Na+ unit at a commercial/industrial site. Retired-EV, grid and
data-center presets run on the same engine as evidence that the method is not tied to one use.

## Layout

| Path | What it is |
|---|---|
| `hackkit/reon_wear.py`, `reon_design.py` | Ageing, retirement, builds (plain, sort, switches, selective bypass, balancer), `recommend_build` |
| `hackkit/reon_unit.py`, `reon_econ.py`, `finance.py` | Profit per kWh, payback, break-even cost, NPV |
| `hackkit/contract.py` | `check_cells`: weak cell vs bad sensor |
| `hackkit/flex.py` | Price-driven dispatch (LP) |
| `hackkit/reon_carbon.py` | CO2e balance |
| `app_reon.py` | Streamlit dashboard (v0; to be split into pages, see `docs/PLAN.md`) |
| `examples/` | Real-pack runs (Nature Energy 2026, 12 cars) and stress tests, each with its saved output |
| `recheck/` | Independent pack-model spec and reference implementation |
| `docs/SPEC.md` | Inputs and outputs for the hardware, the algorithm and the dashboard |
| `docs/PLAN.md` | Build order, owners, tests |
| `docs/background/` | Sources, earlier results, questions for REON |

## Run

```
pip install -r requirements.txt
python -m pytest -q
PYTHONPATH=. python examples/reon_nature_vs_brief_baseline.py
streamlit run app_reon.py
```

## Status

Source tags are kept on every number (REAL, CITED, ASSUMED). Nothing here is validated on sodium-ion cells;
the fade and knee sources are lithium. See `docs/SPEC.md` for what is assumed.

Large raw datasets (Iowa State, Leaf, LFP) are not copied here; they stay in the older `reon-battery` repo.
