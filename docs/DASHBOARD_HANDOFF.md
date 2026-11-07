# Dashboard handoff

Rule: the engine writes the numbers, the dashboard shows them. Nobody retypes a figure. Run `PYTHONPATH=. python examples/export_numbers.py` (about 20 seconds) and every page reads `numbers.json`. A working reference exists: `streamlit run app_final.py` (8 tabs, runs the engine live).

| Page | Question it answers | Reads from `numbers.json` | Live engine call if you want sliders |
|---|---|---|---|
| 1 Story | What is a plain string worth against per-cell control at one site? | `hero_capacity.rows` (verdict, build, gain, p10 at three fade rates) | `reon_guard.robust_recommend` |
| 2 Which cell is hurting | Which cells cost money, and what should the controller do? | (live only) | `reon_rank.rank_cells`, `reon_response.decide` |
| 3 Where the money comes from | Capacity, dead cells, crew visits, downtime: which pays? | `site_value.sites[*].rows[*].streams` and `fault_rate_break_even` | `reon_events.value_streams`, `break_even` |
| 4 Policy for this site | Automatic bypass, replace-on-failure or a threshold? | (live only) | `reon_events.choose_policy` |
| 5 Storm and backup | Does the pack cover the outage? | `backup_hours` | `reon_storm.hours` |
| 6 Evidence and limits | What is real, cited, assumed, unknown? | `stress`, `unknown_ask_reon`, tags on every block; full list in `docs/SOURCES.md` | none |

Rules for any front end
- Show the source tag (REAL, CITED, ASSUMED) beside every number.
- Show HOLD and "does not pay here" as plainly as BUY. They are part of the evidence.
- Do not present a capacity gain as the headline when fade is below about 0.006 a year; the stress test shows it wins only 29% of the time there.
- Safety limits stay in REON's hardware. The dashboard recommends, it never commands.
- The downtime cost and visit cost are assumed; label them so.

Inputs the dashboard needs from REON (open): see `unknown_ask_reon`.
