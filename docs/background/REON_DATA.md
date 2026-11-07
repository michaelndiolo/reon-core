# Reon: what is public, what real data exists, and what we must ask

Collected 2026-11-07. Tags: REAL = a company or measurement page we read; CITED = a named published source; "our arithmetic" = computed by us
from the cited numbers with the pack-model rules in `recheck/SPEC.md`. Vendor statements are claims, not measurements.

## 0. The challenge as presented (REON CTO Tim Ren, opening-ceremony video, from Michael's screenshots of the slides and the auto-generated transcript, 2026-11-07)

Seen: seven slides and about half of the transcript. The auto-transcript has errors ("Rayon", "Rion", "HyphaSong"); slide text was read from phone screenshots, so small print is uncertain. The supplemental material the CTO mentions was NOT seen.

- **The ask.** Build a tool that shows how cell-level intelligence and control can optimize battery performance, extend system cycle life and unlock new opportunities, and quantify the economic and environmental value in a SPECIFIC real-world application. Given: a cell-level control system that manages the pack at the level of each cell. The solution must show at least ONE of two things: economic value or environmental sustainability (so carbon is optional).
- **Their model of the problem.** Slide: "usable = min x N" without control, "usable = sum" with control ("every cell runs to its own end"). This is exactly the pack model in `recheck/SPEC.md`. Stranded energy: healthy cells keep capacity the system never reaches. Shorter system life: "the current industry retirement standard is set on system deliverable capacity", so as cells drift apart a system drops below spec and is retired while most of its cells are still good. (This is reading B in `hackkit/reon_claim.py`.)
- **How REON does it.** A switch at every cell plus cell-level intelligence (voltage, temperature, state of charge, state of health, capacity and performance history). A cell can be paused or bypassed based on its own condition and what the system needs; "the string keeps running around the cell that is done". A conventional BMS sees every cell but cannot act on one.
- **Three opportunities named.** Capacity recovery (retired EV packs, how much stranded energy can be recovered), lifetime and cycle optimization (how many more cycles from a retired cell when one cell does not stop the pack), economic value and environmental impact versus a conventional BMS in a real use case.
- **Four questions every team must answer.** What (problem or opportunity), How (does the solution use cell-level monitoring or control; what becomes possible that a fixed series string cannot do), Who (battery makers, system operators, asset owners, utilities, new customer segments), Why (technical, economic or environmental value: better utilization, longer life, lower cost, less waste). Also: "consider practical limits, the technical, economic and safety constraints that could affect feasibility."
- **Not in what we saw.** No "2-3X", no efficiency, no cost, no data set, no named application, no judging weights.

## 1. What Reon says publicly (vendor claims; no test data on any page)

Source: [reoncorp.com](https://www.reoncorp.com/), [technology](https://reoncorp.com/technology), [solutions](https://www.reoncorp.com/solutions),
[contact](https://www.reoncorp.com/contact). REON Technology, Inc., 200 Turnpike Road, Suite 10, Chelmsford, MA 01824. information@reoncorp.com.

| Item | What the pages say | Tag |
|---|---|---|
| Headline claim | "2-3X more usable capacity" from optimizing every cell individually (a single weak cell limits a pack). No test data, baseline or conditions given | vendor claim |
| BMS | monitors every cell at 100 Hz, responds in under 10 ms; active cell balancing; zero-downtime fault isolation; supports Li-ion, Na-ion, solid-state, second-life and future chemistries | vendor claim |
| EMS | peak shaving, time-of-use optimization, demand response, VPP participation, AI/ML dispatch; integrates aggregators CPower and Voltus | vendor claim |
| Products | MPS 7.5 kW / 10 kWh; FES 25 kW / 50 kWh; EBS 30 kW / 60 kWh (Na+ or Li+); OES 60 kW / 250 kWh; CESS 2.5 MW / 5 MWh | vendor spec |
| EBS Na+ | rated 20,000 cycles; -40 F to +140 F; Li+ version "more than twice the energy" in the same footprint (baseline not stated) | vendor claim |

Not on any page we read: efficiency or switching losses, cost, voltage/current specs (except OES100 208 V / 480 V), second-life pilots or customers,
capacity-utilization metrics, datasheets or whitepapers, founders, funding. The About page names the leadership (Simon Zhang, co-founder and CEO; Tim Ren, co-founder and CTO; John Ireland, CFO; Carson Pucello, CMO; Sean Zhang, VP sales/BD;
Keith Desrosiers, head of engineering) and the tagline "Make every cell count"; it names five partner logos without text, gives no origin lab, patents, funding,
pilots or performance data, and makes no second-life claim (the only second-life mention found is the BMS line on the Solutions page).

## 1b. What REON's own patent applications disclose (public; the best primary source we have)

REON Technology is the applicant on seven US applications filed 2023-2025 (inventor Tiegeng Ren, per [Justia](https://patents.justia.com/inventor/tiegeng-ren)). Summaries below were extracted by a
summarizer from the Justia pages; the last 2-25% of the two long pages was not read, so check the claims before quoting. None of the seven quantifies a capacity gain, an efficiency or a loss.

| Application | Filed | What it describes |
|---|---|---|
| [20230280808](https://patents.justia.com/patent/20230280808) Software-Defined Energy Storage System Interface | Mar 2023 | cells in series columns, columns in parallel; software-controlled switches couple, decouple or bypass individual cells, units and columns; reuse of second-life cells, mixed chemistries and ages; N+1 or 2N redundancy; voltages 48 V to 1000 V |
| [20230341471](https://patents.justia.com/patent/20230341471) Battery Performance Tracking Across Battery Cells | Apr 2023 | per-cell tracking (SOC, SOH, temperature, impedance, cycle count) from manufacture through second life; predicts a per-cell "capability metric" (voltage, power, energy or cycles); bypasses a weak cell and enables a spare in the same column |
| 20240154430 Battery Management System with Controlled Replacement | Oct 2023 | battery units on a bus through switch pairs, shunt switches bypass a selected unit |
| [20240421600](https://patents.justia.com/patent/20240421600) Distributed Power System for Management and Control | Aug 2024 | DC sources in series, each with a bypass switch and a series switch (mutually exclusive); IGBT-type switches; hot swap; feeds a DC-DC converter or inverter |
| 20240429469 Battery Management System with Low Latency | Sep 2024 | units cache data locally and report changes to a master controller |
| 20250330033 BMS with In Situ Cell Rejuvenation | Jun 2025 | reconfigures switches to send pulsed rejuvenation current through individual cells |
| 20250385525 Integrated Solar and Battery Systems with Virtual Power Point Tracking | Aug 2025 | series PV sources with bypass switches plus a BMS-set load voltage |

What this answers: (3) topology. It is series columns wired in parallel with per-cell bypass and spare cells, not a single series string, and bypassing a cell changes the string voltage, which is why a converter or
inverter stage follows. Our `N x min` and `sum x eta` rules describe one column with ideal bypass; parallel columns, spares and the voltage window are NOT modeled.
What it does not answer: efficiency or switch losses (none stated), cost, any measured gain, what "2-3X" is measured against. Other public facts: founded 2022, Greentown Labs member
([page](https://greentownlabs.com/members/reon-technology/)); $100K MassCEC grant, article dated 2026-08-26 ([Dealroom](https://dealroom.co/news/146975-reon-technology-lands-100k-masscec-grant-for-battery-solar-tech/)).
Hardware page ([reoncorp.com/hardware](https://www.reoncorp.com/hardware)) repeats the product table and states no efficiency, certification, warranty or price.

## 1c. Second pass over REON's own pages (read in full 2026-11-07)

| Page | Quantitative content | Compared against |
|---|---|---|
| [/technology](https://reoncorp.com/technology) | product table only: MPS 7.5 kW/10 kWh, FES 25 kW/50 kWh, EBS 30 kW/60 kWh, OES line 60 kW/250 kWh, CESS 2.5 MW/5 MWh; EBS Na+ "20,000-cycle life", -40 to +140 F; EBS Li+ "more than twice the energy in the same form factor"; OES300 "double the capacity" | Li+ claim: not named (context suggests the Na+ unit); OES300: OES100; cycle-life: no baseline |
| [/solutions](https://www.reoncorp.com/solutions) | every cell monitored at 100 Hz; "sub-10 ms response"; "prevents weak cells from limiting the entire pack"; names CPower and Voltus as demand-response/VPP aggregators; no pricing, no named customers | no baselines |
| [/about](https://reoncorp.com/about/) | "more usable energy, longer system life"; Chelmsford, MA address; five partner logos with no description | none |

Result: no page states "2-3X", an efficiency, a cost, a customer or a pilot. The "2-3X" wording must come from the challenge text or the mentors; its baseline is still unknown. The technology page lists no second-life product, so retired-cell use is an application of the patents, not a product on the site.

## 1d. New outside anchors found in the same pass

- Relectrify final ARENA report ([PDF](https://arena.gov.au/assets/2025/05/Relectrify-Second-life-battery-trial-Final-knowledge-sharing-report.pdf)), re-read directly: ">20% increase in usable capacity" on a set of "particularly degraded" Leaf cells (executive summary, p. 3; p. 11), growing with SoH and resistance spread; modelled cost within 5-10% of a new-battery BESS (pp. 29-30, a levelised cost, not a pack price); shipping US$20-40/kWh (p. 33). Round-trip efficiency, bypass/switching loss, pack price and electronics cost: NOT reported. This closes the earlier "re-read before quoting" gap.
- Chalmers / PHINIA / Scania, "System-level assessment of dynamic reconfiguration for lifetime and cost outcomes in electric vehicle battery packs", Nature Communications, reported by [electrive 2026-10-09](https://www.electrive.com/2026/10/09/cell-bypass-aims-to-extend-the-usable-life-of-ev-batteries/): simulated lifespan gain "more than 20%" for some high-voltage vehicles in the per-cell case, called a theoretical upper limit; example 80 kWh pack, 12,000 km/yr, 10 years vs about 11. Model output, not measurement; extra electronics raise initial cost; no efficiency figure. Not yet read in the original paper. It is a simulation upper bound that sits inside our toy life-ratio range (cycle part 1.01-1.47), not a measurement of REON.
- arXiv 2301.05168 (Farakhor, Wu, Wang, Fang): self-reconfigurable pack with DC/DC converters per cell; abstract gives no capacity or loss numbers (only abstract read).
- Carbon: IVL's 2019 update ("Lithium-Ion Vehicle Battery Production - Status 2019") is 61-106 kg CO2e/kWh, up to 146 with less transparent data, vs 150-200 in the 2017 report, per the [IVL press page](https://ivl.se/appresource/5.3caf9fbe174fee4974b8e17/12.19b39e311838a550c3c3031d/accept). I opened the 2017 report text ([Energimyndigheten c243](https://www.energimyndigheten.se/globalassets/forskning--innovation/transporter/c243-the-life-cycle-energy-consumption-and-co2-emissions-from-lithium-ion-batteries-.pdf)): 150-200 "most likely", 120-250 across studies, use phase excluded, grid-intensity table (Sweden 50, USA 700, China 1000 g/kWh), and "no second life market at present" (2017 wording, dated). The 2019 report PDF itself still could not be opened (its link redirects to an index page), so the 2019 numbers rest on the press page and trade-press copies.

## 1e. Third pass: published numbers for the efficiency, electronics-cost, pack-price and tariff asks

None of these is REON's own number. They are literature analogs we can use as CITED ranges, and each one is labelled that way wherever it is used.

**Chalmers study (Nature Communications; [full text](https://research.chalmers.se/publication/552955/file/552955_Fulltext.pdf), read directly).** Cell-level reconfiguration, EV packs, simulation:
- Hardware cost: reconfigurable pack costs (1+v) x the conventional pack, v varied 1% to 15%; bottom-up estimate "approximately 9.36% for LFP and 8.47% for NMC of the total pack cost". With their pack price of 98.37 EUR/kWh (BloombergNEF 2024, 115 USD/kWh) that is about 8.3-9.2 EUR per kWh of pack, or 1.0-14.8 EUR/kWh across the full 1-15% range. (The 8.3-9.2 and 1.0-14.8 figures are our arithmetic.)
- Losses: ohmic losses raise energy cost by 1% to 5%; parallel switches can keep added losses "below 2%" (their ref. 60).
- Life: cell-level control is stated to be an upper bound; no lifetime numbers by granularity in the main text. Coefficient of variation of the life extension about 22% for LFP under manufacturing variability. Resale coefficient 0.5 (range 0.2-0.8).
- Not covered: retired cells, measured hardware, REON's switches.

**What the Chalmers loss range does to our gains** (computed by `hackkit/reon_loss.py`, output in `examples/reon_loss_output.txt`; the table above it was first rounded by hand and is corrected here: usable = sum of cells x eta, conventional = N x min cell):

| Cell set | Gain at eta=1 | Break-even loss | Net gain at 2% loss | Net gain at 5% loss |
|---|---|---|---|---|
| BMW module 3 | 1.2% | 1.2% | -0.8% | -3.8% |
| BMW module 2 | 1.7% | 1.7% | -0.3% | -3.3% |
| BMW all 36 cells | 7.2% | 6.7% | 5.0% | 1.8% |
| BMW module 1 | 9.4% | 8.6% | 7.2% | 3.9% |
| 8 Leaf cells | 18.6% | 15.7% | 16.3% | 12.7% |

Reading it: when cells are well matched, a 2% loss erases the whole gain, so the efficiency question (ask 2) matters most exactly where the spread is small. Retired packs with large spread are where the idea pays. This also means the "2-3X" claim cannot come from spread alone at these published spreads.

**Pack price and repurposing cost.** New pack 98.37 EUR/kWh (Chalmers, BNEF 2024). Repurposing cost "around $12/kWh at the pack level and $41/kWh at the module level" for a Tesla Model S pack at 500 MWh/year ([ScienceDirect, Applied Energy 2026](https://www.sciencedirect.com/science/article/pii/S0306261926004617), abstract-level read; yields 90% pack / 95% module, average used-pack SoH 80%, discount rate 7%; LFP favours reuse, NCA recycling). Added to the earlier NREL $20-60/kWh (2015) and Relectrify $20-40/kWh shipping. A real used-pack purchase price (ask 9) is still missing.

**Reference site and tariff (ask 7), vendor summary, approximate.** Massachusetts demand charges per kW-month: National Grid G-2 13.42, G-3 18.76; Eversource B-1 11.89, B-2 15.93, B-3 22.47; Unitil G-1 9.84 ([NuWatt](https://nuwattenergy.com/en/massachusetts/commercial-demand-charge-battery-calculator-2026), updated Aug 2026; the page says rates are approximate, so verify against a utility tariff before quoting). ConnectedSolutions battery programs (same vendor's summary of utility pages): daily dispatch about 200 $/kW-summer, targeted dispatch about 45. REON is in Chelmsford, MA and names CPower and Voltus, so a Massachusetts C&I site is a reasonable ASSUMED reference. National Grid's own table page gave only basic-service rates (about 21.7-21.9 cents/kWh for Nov 2026 to Jan 2027), no demand charges.

**Patent text.** The remaining text of application 20230341471 was read: no efficiency, loss, cost or cycle-life numbers; claim 6 mentions a carbon-saving "quantification number" without a value.

## 2. Real published data on how much retired cells differ (what control can exploit)

Control's capacity gain from cell mismatch alone, with an ideal switching path, is `mean / min - 1` (conventional = N x weakest, control = sum).
It depends entirely on the spread, and published spreads are modest:

| Source | Cells | Spread | Gain from mismatch alone (our arithmetic, eta = 1) |
|---|---|---|---|
| Influence of Cell Position on the Capacity of Retired Batteries, [arXiv 2507.14020](https://arxiv.org/html/2507.14020v1): 3 second-life BMW i3 modules, 12 cells each, 94 Ah NMC | 36 | CV 2.4%; min 84.3, mean about 90.3, max 94.2 Ah | 7.2% across all 36 cells; 9.4% inside module 1 (one outlier cell, 84.3 Ah), 1.7% inside module 2, 1.2% inside module 3 |
| Taking Second-life Batteries from Exhausted to Empowered, [arXiv 2402.18859](https://arxiv.org/pdf/2402.18859): 8 retired Nissan Leaf pouch cells from two packs, 32.5 Ah new | 8 | 17.42 to 25.04 Ah; CV about 13.8% | 18.6% across all 8 (139.36 vs 165.34 Ah); 9.3% in pack 1, 26.7% in pack 2 |

Two consequences for the pitch. (a) To reach "2-3X" from mismatch alone the weakest cell would have to be 50% or 33% of the mean: far beyond
these published spreads, so Reon's figure must come from something else or compare against something else; ask (see 3). (b) Our
tool should present the gain as a function of spread with these two real points marked, not assume a spread. Caveats: the cell sets are not
single series strings, the capacities were checked against the printed tables, and
the data in 2507.14020 is not stated to be public.

## 2b. The closest real analog: Relectrify's second-life trial (a different company; NOT Reon)

Relectrify also puts cell-level control (its "ReVolve" system) on retired Nissan Leaf packs and published a final knowledge-sharing report to ARENA (the Australian Renewable
Energy Agency, 2025): [report](https://arena.gov.au/assets/2025/05/Relectrify-Second-life-battery-trial-Final-knowledge-sharing-report.pdf). Figures below were extracted by a
summarizer with page references; the report's charts were not readable, so re-read the pages before quoting.

| What | Figure (page) | Use |
|---|---|---|
| Usable capacity vs a conventional system | more than 20% more in field data from one unit, 130 cycles (p.11); the gain scales with SoH and resistance variation | matches our spread arithmetic (7% to 27%); not 2-3x |
| Cell spread | SoH differs by up to 32% between cells in some packs (p.8); about 15% between weakest and strongest in one discharge test (p.10) | range for the spread input |
| Fade and life | 2.0% to 3.0% capacity fade a year, linear model; projected life about 6-8 years; warranty 4 years (p.21, p.31) | service-life input (now CITED, analog) |
| Economics | modeled cost per kWh within 5-10% of an equivalent new battery system in several early sales (p.30); payback typically 4-7 years (p.31); shipping US$20-40/kWh vs under US$10 expected (p.33) | second-life is not clearly cheaper; say so in the pitch |
| Not reported | efficiency of the cell-level path, second-life pack price per kWh, electronics cost | still asks 2, 4, 9 for Reon |
| Scale | 8 units (about 960 kWh) first rollout, 15 installed by end of 2024; 9 packs per 36 kW / 120 kWh unit; about 244 MWh through the fleet (p.3-7, p.16) | context |

Cost anchor for retired packs: NREL poster NREL/PO-5400-64149 (2015 dollars, dated): repurposing cost about $20-60/kWh nameplate, minimum-cost scenario about $20/kWh, selling price
about $40/kWh in that scenario; predicted second-use lifetimes 3-10 years. Used for ranges only; ask Reon what they pay.

Public data to pull later: Leaf cell cycling data on OSF, DOI 10.17605/OSF.IO/FNS57 (license not stated; contact the corresponding author, Simona
Onori, before reuse); an IEEE DataPort "experimental dataset retired batteries first life, second life and third life" surfaced in search and
was NOT opened. NREL BLAST-Lite is BSD-3-Clause (GitHub page label; the installed package carries the Alliance for Energy Innovation copyright and the BSD text). The Leaf OSF record's license is still unchecked.

## 3. Questions to ask Reon (mentors on Discord Saturday, or information@reoncorp.com), with what each unblocks

1. What is the "2-3X more usable capacity" measured against (new or retired cells, what cell spread, which baseline BMS, what conditions)? Sets the headline and whether the gap to section 2 is real.
2. Efficiency of the switching path per cell, and standby draw. Becomes `eta` in the pack model (now ASSUMED).
3. Topology: can each cell be bypassed individually in a series string, are there parallel groups, and what voltage window must the string hold? Decides whether `N x min` and `sum` are the right rules.
4. Cost of the cell-level electronics per cell and per kWh. Becomes `control_capex` in `control_npv`.
5. Any per-cell logs (capacity, voltage, temperature) from retired packs run with and without control. The only thing that can validate the pack model and test `check_cells` on real data.
6. Which baseline BMS they want us to compare against (passive balancing? none?) and which chemistry/application they care most about.
7. A reference site: which tariff or demand charge, what load, which aggregator program (CPower/Voltus). Replaces our invented site and ASSUMED demand rate.
8. Cycle-life evidence for retired cells with control vs without (the 20,000-cycle figure is for new Na-ion). Needed for the aging model.
9. Where retired packs come from, what is paid per kWh, and what spread is seen at intake. Sets second-life pack cost and the spread range.

10. Embodied carbon of the control electronics, and the service life they expect for a second-life pack. Both are ASSUMED in the carbon and finance modules.
11. What input-voltage window the converter accepts (what share of a string's cells must stay in circuit while discharging). Decides how much of the ideal gain survives; see `hackkit/reon_window.py` and `docs/RESULTS_SO_FAR.md`. Added 2026-11-07.

How `docs/ASK_REON_DRAFT.md` maps to this list: draft 1 = Q1, 2 = Q2, 3 = Q4 and Q9, 4 = Q5, 5 = Q11, 6 = Q7. Q3 (topology) is answered from the patents; Q6, Q8 and Q10 are not in the draft because the answers would not change a number we can compute this weekend.

Carbon source in use: embodied carbon of a new battery, 61-106 kg CO2e/kWh (up to 146 with less transparent data), IVL / Emilsson and Dahllof 2019, read from
IVL's press page and confirmed by an independent news article (electrive, Dec 2019), not from the report itself (its abstract page confirms the title and scope only); the earlier 2017 report said 150-200. Open the 2019 report itself before quoting it on a slide.

## 4. Status of the asks

Answered from public sources: 3 (topology; see 1b), and chemistry mixing from part of 6. REON-specific answers still missing: 1, 2, 4, 5, 7, 8, 9, 10. Literature analogs now exist for 2 (loss 1-5%, below 2% with parallel switches), 4 (electronics 8.5-9.4% of pack cost, 1-15% range), 7 (assumed MA tariff) and 9 (new pack 98 EUR/kWh, repurposing 12-41 USD/kWh); see 1e. Nothing public for 1, 5, 8 beyond simulations (the patent applications and every page we could read give no efficiency, cost, measured gain or baseline). A short message to send is in `docs/ASK_REON_DRAFT.md`.

Original status line: none answered yet. Nothing in `reon_econ` / `reon_carbon` / the pack model may use a Reon number until an answer or a public source is logged here.


## Fade-rate spread and spread sources (added)

- Nature Energy 2026 (via https://xenospectrum.com/en/ev-battery-pack-weakest-cell-energy-waste-nature-energy/, secondary summary; original paper unread): lifespan loss from weakest-cell effects 17.7% cars, 22.8% buses. CITED. Used only through `reon_drift.calibrate_fade_cv` (CV about 0.087 / 0.111). The mapping from lifespan loss to CV is our model, so the CV is CITED-derived, not directly cited.
- arXiv 2512.01294: capacity spread 20-30% within a pack, retired cells at 70-80% SOH, stationary tier 50-80% SOH. CITED.
- LTC3300 vendor article: balancing current up to 10 A (a part, not REON's baseline). CITED.
- Failure rates per cell-year, repair time: ASSUMED (no public figure found).

## Past public data to calibrate from (found Nov 7; files NOT yet downloaded: the cloud and device egress policies return 403 for zenodo.org)

- arXiv 2402.18859, Onori group / Relyion: 8 retired Nissan Leaf LMO/graphite pouch cells (32.5 Ah new; 17.42 to 25.04 Ah at start, the capacities already in the app), about 15 months, about 100,000 Ah throughput, 3-4 V window, 1C/C-2 discharge, C/2 charge. C/20 capacity ROSE 0.6% to 16.1%, no cell died, rise tied mainly to seasonal temperature. CITED. Data: https://doi.org/10.17605/OSF.IO/FNS57. Consequence: fade of retired cells under gentle use can be about zero, so the fade rate and the retirement-inside-service-period condition stay ASSUMED until per-cell series are loaded (hackkit/reon_history.py).
- Zenodo 13715694 (BattGP, Schaeffer et al., Cell Reports Physical Science): 28 field LFP systems x 8 prismatic cells, 1 month to 5 years, per-cell voltage, active balancing, CC BY-NC 4.0, 1.7 GB. Systems were returned for bad behaviour (biased). In 9 of 21 modelled systems one or two cells behaved differently from the rest. CITED; no failure rate.
- Iowa State 225 NMC cells, DOI 10.25380/iastate.22582234 (arXiv 2307.08382): lifetime spread across cycling conditions, 1.5 to 60.9 weeks. CITED; per-group spread not reported in the text.

- UPDATE Nov 7 (analysed from downloaded files): Iowa State within-group fade-rate CV median 0.20 (0.14 to 0.29), 62 groups; derived by examples/reon_history_iowa.py. Field LFP: exploratory only; one of the inspected systems has a cell about 170 mV below the string mean under load. Files live in data_external/ (not in git; CC BY-NC 4.0 for the Zenodo set).


## From the REON challenge brief and Discord (Nov 7), CITED / REON-stated

- Task: "an innovative tool" that uses cell-level intelligence and control to improve performance and cycle life, "quantifying the potential economic and environmental value in a specific real-world application", against "a clear baseline", at least one economic or environmental outcome. Tim Ren (REON CTO), asked whether the tool must be a new REON feature: **no, it is just a dashboard for the presentation to show your idea.** Our Streamlit app is that dashboard.
- Baseline in the brief's 16-cell example: a fixed series string "without effective energy redistribution during the modeled discharge". Balancing "can reduce differences in SOC, but it cannot restore capacity lost to aging." So the challenge baseline is the plain fixed string; an active balancer is our own extra stress test, not the brief's baseline. (A participant's question lists "active cell balancing and the bypass strategy" as REON features; Tim did not contradict it, so REON may sell both.)
- Retirement: a simple capacity threshold; "80% ... common for EVs; stationary storage may use a lower threshold like 70%", application, warranty and service dependent; the operator may accept reduced service, maintain, augment or replace; real decisions should use delivered kWh and kW at a defined system boundary. Our retire-level default 70% matches stationary; use 80% for EVs.
- 16-cell example: 15 cells 85 Ah, one 70 Ah of 100 Ah new; string = 70 Ah (70%), average cell 84.06%, ratio 83.3%. Now a sample in the app (ideal gain = 84.06/70 - 1 = 20.1%), with a test.
- Given capabilities: per-cell voltage, temperature, SOC, SOH, capacity, resistance, OCV and history; switching and selective bypass of a "completed or faulty cell", "you can choose when to activate or bypass cells"; no need to design the hardware. Suggested applications: retired EV packs, grid-scale storage, data-center backup.
- Tim Ren: REON packs can be connected in series with other manufacturers' packs; they cannot manage the other packs' DC voltage but can compensate their power drop to keep the string voltage. A possible extra application (mixed or legacy strings), not modelled.
- Product one-pager: FES 21-25 kW / 50 kWh, MPS 7.5 kW / 10 kWh, EBS 30 kW / 60 kWh (sodium-ion, UL-certified per REON), OES 60-120 kW / 66-313 kWh, CES 2.5 MW / up to 5 MWh, plus EMS software.

- Leaf cells series (OSF FNS57, analysed Nov 7): flat capacity, -1.4% to +2.6% over about a year, CV across cells 0.105 to 0.115, ideal-control gain 19.1% at the last check. REAL (data from the cited study, our fit). See WHAT_WE_HAVE 3j.


## Nature Energy 2026 (Zhou et al.), checked against two secondary summaries (nature.com refused automated access; full text still unread)
- Data: 116 passenger cars (NMC) and 17 buses (LFP), over three years, up to 300,000 km. CITED (Mendeley abstract page).
- Lifetime shortening from cell-to-cell inconsistency 17.7% (cars), 22.8% (buses); pack health reduction 6.2% and 7.5%; power capability decrease 12.9% and 15.1%; energy utilisation over the lifespan 80.7% (cars), 72.9% (buses), so 19.3% and 27.1% unused. CITED.
- The same numbers were used for our fade-spread calibration (CV 0.087 and 0.111), so that calibration stands at abstract level. The paper's spread statistics (sd, ranges) were not available to us.
- Cross-check: 19.3% of energy unused implies ideal control could use 1/0.807 - 1 = 23.9% more (cars) and 1/0.729 - 1 = 37% more (buses), if "utilisation" is defined against the cells' own potential (definition not verified). Our retired Leaf cells: 19.1% (REAL), same order of magnitude.

## Application preset sources (added Nov 7)
- Grid-scale: Modo Energy, ERCOT $3.01 per kW-month and CAISO $2.74 per kW-month in June 2025 (one month), GB 73,145 pounds per MW-year for two-hour batteries (12 months to April 2026); duration for ERCOT and CAISO not stated, 4 hours ASSUMED to get about $9 per kWh-year. NREL ATB 2024: 15-year life with augmentation, fixed O&M 2.5% of capex, round-trip efficiency 85%, about one cycle a day. CITED / ASSUMED.
- Data-center backup: Schneider Electric TradeOff blog (2018): lithium-ion life 10 to 15 years versus VRLA 3 to 6; lithium-ion costs 1.5 to 2 times VRLA; maintenance 1.5% versus 8% of capex a year; lithium-ion forecast 40% of data-center backup by 2025. CITED. No cost per kWh or runtime in that source.


## Gap-closing round, Nov 7 (sources opened this session)
- Second-life fade: NREL 2019 (fy19osti/72557): six Mini-E batteries lost 0 to 6% capacity in 2.5 years (up to about 2.4% a year, our arithmetic) and 0 to 16% power; modelled remaining capacity 65 to 75% at year 15; used EV batteries "could last another 10 years" in some second uses; average battery temperature is the biggest factor. CITED. With the Leaf series (REAL, 0 to 1% a year) this bounds the fade range at 0 to about 2.4%.
- Failure rates: Faraday Institute Insights, July 2023: catastrophic cell failure 1 in 10 million to 1 in 40 million cells (Doughty and Roth, 2012, general Li-ion, fire or explosion, not open circuit, not per year); it says aged and second-life cells may be riskier but gives no rate and calls second-life testing "in its infancy". CITED. No public open-circuit or second-life rate was found.
- Embodied carbon: IVL 2019 (press page): 61 to 106 kg CO2e per kWh of battery produced, up to 146 with less transparent data, earlier report 150 to 200. CITED, verified.
- Grid value: CAISO Department of Market Monitoring, 2024 annual report (executive summary): actual CAISO batteries with a full year earned nearly $43 per kW-year from energy and $7 from regulation; a hypothetical fleet across all nodes $52 + $28; fleet about 13,000 MW. CITED. Resource adequacy revenue not read; duration not confirmed (4 hours ASSUMED).
- Data-center backup: UPS runtime hyperscale 1 to 2 minutes, colocation 5, financial 10 to 15; lithium-ion design life up to 15 years, efficiency 95% or more (Schneider Electric via Introl). CITED second-hand. No cost per kWh found.
- Not closed: Nature Energy full text (nature.com blocks automated access; Michael can download the PDF).


## Round 3 additions (Nov 7 afternoon)

- Nature Energy 2026, Zhou et al., full text read (11 pages): metric definitions: beta_SOH = min/mean capacity; beta_life = N min(EFC_i) / sum EFC_i at each cell's end of life (EOL threshold 0.8 in EVs, they use 0.85 because the cars are still running); beta_SOC = 1 - sum (SOC_max - SOC_i) SOH_i / sum SOH_i;
  beta_power from the cell power limits P_cell,i = I_max,i [V + R0 (I_max,i - I)]; beta_energy = beta_life x mean(beta_SOC). Data and code: github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency (MIT, four source-data Excel files; vehicle parquet via external link). Paper text has no failure rate for cells.
- Iowa State / ILCC (DOI 10.25380/iastate.22582234): conditions per group from the README table A1. Fit by `examples/reon_wear_iowa_fit.py`: DoD exponent 0.87 (0.69 to 1.18) to 90% and 0.71 (0.60 to 0.91) to 70%; 65% of 205 cells show an accelerating fade (median 2.4x, onset SOH median 0.855). Caveats: 250 mAh polymer cells, continuous cycling at 30 C, groups are not an orthogonal design, smooth curvature also scores as a knee.
- Analog Devices LTC3300-1 active balancer: up to 10 A, up to 92% transfer efficiency, 6 cells per IC ([electronicdesign.com](https://www.electronicdesign.com/products/bidirectional-multicell-active-battery-balancer-maximizes-capacity)). Cost per kWh: NOT found.


## Round 4 additions (Nov 7 evening): balancer currents and chip cost
- DALY BMS: storage active balancing "typically in the 1A range", LM-B variant 2 A, passive about 100 mA ([article](https://www.dalybms.com/news/when-energy-storage-systems-need-active-balancing-and-when-passive-is-enough/)).
- Heltec active balancer 3S to 21S: max balance current 5.5 A ([product page](https://www.heltec-energy.com/active-balancer-3-21s-5a-battery-equalizer-for-lifepo4lipolto-product/)); no price listed.
- LTC3300-1 on element14 Australia: A$29.42 (1+) down to A$19.10 (500+) per IC, 6 cells per IC, up to 10 A set by external parts ([listing](https://au.element14.com/analog-devices/ltc3300ilxe-1-pbf/battery-balancer-lifepo4-li-ion/dp/4027986)); one transformer per cell and FETs are extra and not priced here. The A$3 to 5 per cell is the chip only.
- Transfer limit derivation (ours, not a published figure): r = I_bal / (C_rate x cell Ah).
