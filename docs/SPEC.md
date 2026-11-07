# Inputs and outputs (draft v1, 7 Nov 2026)

Rule from the official brief: per-cell monitoring and selective bypass are GIVEN. We do not design switch
hardware or low-level control. We build the decision layer on top.

## 1. Hardware boundary (assumed given)

| Direction | Signal |
|---|---|
| From the pack to us | Per-cell voltage, temperature, SOC, SOH, capacity, internal resistance, OCV, history; string current |
| From us to the pack | Per cell: engage or bypass. Pack level: current limit and SOC window (recommendation only) |
| Not ours | Safety limits (over/under voltage, over temperature, short circuit). These stay in certified hardware and are never overridden by this layer |

Open questions for REON: sensing accuracy and reporting rate, per-cell switch loss, what "overhead" means in
Tim's $560 to $1,920 per 80 kWh string, and sodium-ion spread and ageing data.

## 2. Algorithm

Inputs
- Cell table (above) for one or more series strings
- Application: duty (cycles per day, depth of discharge), retirement threshold (70 % or 80 % of beginning-of-life
  system capacity), value per delivered kWh-year, years, discount rate
- Costs: switch/electronics $ per kWh nameplate (default range 7 to 24), switch loss, balancer option (limit, cost)
- Optional: price series, outage window, temperature

Outputs
- Limiting cell(s) and kWh they strand per cycle (attributable, from `check_cells` and `recommend_build`)
- Weak cell vs bad sensor verdict
- Recommended action: nothing / sort / bypass k weakest / switch every cell, with net $ per kWh nameplate and
  margin over the best alternative (plain, sort only, balancer, fixed-threshold rule)
- Break-even switch cost and break-even loss (decision flips)
- Retirement date, plain vs managed
- Dollars and CO2e per delivered kWh

## 3. Dashboard pages

1. Story: traditional vs independent-cell on the hero application, spread slider
2. Which cell is hurting: cell table, limiting cells, recommended action
3. Value and robustness: net $ across the cost range, stress-test win rates, vs threshold rule
4. Schedule: plain vs managed envelope under a price curve
5. Fault / storm what-if: click a cell to fail it, or replay an outage window; backup hours plain vs managed
6. Evidence and limits: sources with tags, what is assumed

## 4. Profit per energy

Net value = present value of (value per kWh-year x usable kWh x years) minus electronics cost, per kWh
nameplate and per delivered kWh. Resilience value (avoided outage loss) is a second stream, added only with a
sourced value of lost load. Not yet implemented.

## 5. Autonomous action for remote sites (added 7 Nov, from the team)

Detecting a bad cell is not enough where no crew can easily reach the site (rural minigrid, remote C&I). The
algorithm's job is to act without a visit: bypass the failing or limiting cell automatically, keep the string
running, and raise an alert only for what still needs a person. Think of it as a self-healing backup, not an alarm.

Extra inputs: cost of one site visit, visits avoided per year, travel/lead time, minimum cells the inverter or
string voltage window needs, spare cells (if any), per-event persistence rule (how long a cell must look bad
before it is bypassed), allowed bypasses per string per year.

Extra outputs: bypass events and when, string voltage margin left after each bypass, visits avoided, extra
service years, and the net value of life extension plus avoided visits.

Limits to show, not hide:
- Each bypass removes one cell's voltage. A string can only lose so many before it leaves the inverter window, so
  show "bypasses remaining" and the first date a visit becomes unavoidable.
- A false bypass wastes good capacity, so act only on a persistent signal and let the system abstain when unsure.
- Hard safety limits stay in certified hardware. This layer recommends and logs; it never overrides them.
- No sourced value for a site visit yet. It is an input with a range and a slider, tagged ASSUMED until sourced.

## 6. Interface with REON hardware (DRAFT, not locked, 7 Nov)

REON already has the hardware and BMS/EMS. We build the slow policy layer and the dashboard. Their hardware
handles switch timing, current, sensing and safety; we decide, over minutes to days, which cells take part,
which rest, which are bypassed for good, and when a string is finished. The dashboard replays recorded or
simulated frames; it is not a live link.

Cell-state frame (hardware to us), one per time step: time, string current, and per cell voltage, temperature,
SOC, SOH, capacity, resistance, state (engaged / bypassed / resting).

Action plan (us to hardware): per cell engage, rest until a stated time, or bypass for good, each with a reason
code; pack level current limit, SOC window, and "open string / call crew".

Hardware stays the authority. A refused command is treated as data and the plan is redone.

Known from Tim (Discord, 7 Nov): chemistry-agnostic BMS/EMS; a hot cell can be bypassed to rest; forced-air
cooling today; temperature limits follow the cell maker's spec.

Open questions for REON: data format and reporting rate; sensing accuracy; command format (flags or schedule);
reaction time; which decisions the hardware already makes itself; sodium-ion limits for temperature, voltage and
resistance.
