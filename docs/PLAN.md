# Build plan (draft v1)

## Order of work
1. Lock `docs/SPEC.md` with the team.
2. Engine: add a fixed-threshold rule as a competing policy; add a C&I EBS Na+ preset (value per kWh-year
   from peak pricing, 60 kWh, about one cycle a day, retire at 70 %, switch cost 7 to 24 $/kWh); write one
   `numbers.json` that every page reads.
3. Comparison table: every preset x policy (plain, sort, balancer, threshold, ours).
4. Dashboard pages 1 to 3, then 4 and 5, then 6.
5. Tests: unit tests per module, injected-fault detection limit, held-out comparison, independent recheck by a
   fresh reader of the spec.
6. Freeze features a few hours before the deadline; the rest of the time goes to the demo and the script.

## Owners (proposed)
- Michael: engine, numbers file, value and robustness pages, evidence
- Aaryan: app shell, schedule page, pack-model check against `recheck/`
- Nalia: story page copy, fault/storm page, pitch, REON questions
- Susan: cell-health algorithm spec and page

## Not in this repo
OlivAir work stays out. Raw datasets stay in `reon-battery`.

## Risks
- Sodium-ion ageing and spread data are missing; say so on the evidence page.
- New applications (minigrid, storm mode) need sourced inputs and their own stress run; add only after the hero case.
- Storm mode is a scenario replay, not a safety system.
