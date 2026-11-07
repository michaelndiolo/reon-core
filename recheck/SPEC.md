# Independent re-derivation: pack capacity model

Purpose: someone who has NOT seen `hackkit/pack.py` writes the model from this page alone, then we compare outputs. If the two agree on
every case below, the code solves the problem as specified. It does not prove the specification matches a real Reon pack (see
"What this cannot show").

## Setting (all ASSUMED unless a mentor says otherwise)

One series string of N cells. Cell i has usable capacity `c_i` in Ah (retired cells differ; `c_i > 0`). Every cell has the same nominal
voltage `V` (V), so energy in Wh = Ah x V.

* Conventional BMS: current is common to every cell in the string, so the string is empty when the weakest cell is empty.
  `usable_conv_Ah = N x min(c_i)`.
* Cell-level control: each cell can be switched in or out, so every cell's charge can be used.
  `usable_ctrl_Ah = (sum of c_i) x eta`, where `eta` in (0, 1] is the efficiency of the switching/conversion path (ASSUMED; Reon's real
  value is unknown, ask the mentors; with eta = 1 control is the ideal upper bound).
* Reserve: a fraction `r` in [0, 1) of capacity is held back from both cases (default 0): both usable figures are multiplied by `1 - r`.
* Utilization (of the pack's total capacity, `sum c_i`): `util_conv = usable_conv / sum c_i`, `util_ctrl = usable_ctrl / sum c_i`.
* Gain from control: `gain = usable_ctrl / usable_conv - 1`.

Energy: `usable_kWh = usable_Ah x V x 1e-3`.

## Cases (expected values worked by hand; write your own code, then check against these)

| # | cells (Ah) | eta | r | usable_conv (Ah) | usable_ctrl (Ah) | util_conv | util_ctrl | gain |
|---|---|---|---|---|---|---|---|---|
| A | 100, 90, 80, 70 | 1.00 | 0 | 280 | 340 | 280/340 = 0.8235 | 1.0 | 340/280 - 1 = 0.2143 |
| B | 100, 90, 80, 70 | 0.97 | 0 | 280 | 329.8 | 0.8235 | 0.97 | 329.8/280 - 1 = 0.1779 |
| C | 100, 90, 80, 70 | 1.00 | 0.10 | 252 | 306 | 0.7412 | 0.9 | 0.2143 |
| D | 100, 100, 100, 100 | 1.00 | 0 | 400 | 400 | 1.0 | 1.0 | 0.0 |
| E | 100 (one cell) | 1.00 | 0 | 100 | 100 | 1.0 | 1.0 | 0.0 |
| F | 100, 100, 100, 50 | 1.00 | 0 | 200 | 350 | 200/350 = 0.5714 | 1.0 | 0.75 |
| G | 20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59 | 1.00 | 0 | 139.36 | 165.34 | 0.8429 | 1.0 | 0.1864 |

Case G uses the eight retired Nissan Leaf cell capacities reported in arXiv 2402.18859 (Table 1, as read by us). They came from two packs, so treat
it as an illustration of a realistic spread, not one string. See `docs/REON_DATA.md`.

Energy check for case A at V = 3.7 V: usable_conv = 1.036 kWh, usable_ctrl = 1.258 kWh.

Errors the model must raise (not return a number for): no cells; any `c_i <= 0` or not finite; `eta` outside (0, 1]; `r` outside [0, 1).
Order of cells must not change any result. Scaling every `c_i` by k scales both usable figures by k and leaves utilization and gain unchanged.

## Weak cell mid-life (optional second step)

A cell's capacity fades over time `t`. Give the model a function `capacity_at(t)` per cell. Inject a failure: from time `t0`, cell j drops to a
fraction `f` of its capacity. Output the usable capacity of both cases before and after `t0`. Hand case: cells 100/100/100/100, at `t0` cell 3
drops to f = 0.5: conv goes 400 -> 200, ctrl goes 400 -> 350.

## How to compare

1. Fresh Claude session, no access to `hackkit/pack.py`. Give it this file only. Ask it to write `recheck/pack_ref.py` and `recheck/test_pack_ref.py`
   that reproduce the table.
2. Then run both implementations over the table plus 200 random cell sets (seeded) and require agreement to 1e-9.
3. Any disagreement is either a bug in one of them or an ambiguity in this spec: fix the spec first, then the code.

## What this cannot show

REON's published patent applications describe series columns wired in PARALLEL with per-cell bypass, spare cells and a converter stage; this spec models ONE series column with ideal bypass, so parallel columns, spares and the voltage window are outside it (see `docs/REON_DATA.md`, 1b).

That a real Reon switch behaves like `sum c_i x eta`; that cells in a real second-life pack are in a single series string (parallel groups change
the min rule); that capacity is the only limit (current, temperature and voltage windows are ignored); or any dollar value. Those need Reon's data.
