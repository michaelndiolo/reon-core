"""REON page: what is cell-level control worth for a pack? Run:  streamlit run app_reon.py

Top to bottom: pick or paste the cells (sidebar), set the practical limits and the money inputs (each with a REAL / CITED / ASSUMED tag), read the verdict and
the five tiles, then the tabs: What we gain, How solid is it, Money, Carbon, Story (What / How / Who / Why). Every number comes from the tested modules in hackkit/.
The starting values in the sidebar are literature or test values, NOT REON's: replace them with REON's answers (see docs/ASK_REON_DRAFT.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from hackkit import contract as K
from hackkit import headline as H
from hackkit import reon_carbon as C
from hackkit import reon_loss as L
from hackkit import reon_mc as M
from hackkit import reon_design as DS
from hackkit import reon_drift as DR
from hackkit import reon_granularity as GR
from hackkit import reon_learn as LN
from hackkit import reon_report as R
from hackkit import reon_sorting as SO
from hackkit import reon_spread as S
from hackkit import reon_unit as U
from hackkit import reon_wear as RW
from hackkit import reon_window as W
from hackkit.atstake import SOURCES, Lever
from hackkit.ui import show_contract

M1 = [93.8, 92.6, 93.8, 91.9, 84.3, 92.4, 93.4, 91.5, 92.8, 92.5, 94.2, 93.4]
M2 = [91.6, 88.1, 87.6, 88.5, 88.6, 90.3, 88.4, 88.3, 90.1, 90.2, 89.2, 88.6]
M3 = [91.0, 89.2, 88.9, 89.2, 88.6, 89.1, 89.5, 90.8, 90.1, 89.7, 89.8, 90.2]
LEAF = [20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59]
SAMPLES = {
    "8 Nissan Leaf cells (arXiv 2402.18859)": LEAF,
    "36 BMW i3 cells (arXiv 2507.14020)": M1 + M2 + M3,
    "REON brief: 16 cells (15 at 85 Ah, one at 70 Ah)": [85.0] * 15 + [70.0],
    "BMW i3 module 1 (has an outlier)": M1,
    "BMW i3 module 2": M2,
    "BMW i3 module 3": M3,
    "Paste or upload my own": None,
}

# One engine, three applications. Each preset only changes inputs; every value carries its source tag. Currency follows the page (EUR for the German price runs); the grid figure is USD-derived and only an order of magnitude.
PRESETS = {
    "Custom (my inputs)": None,
    "Retired EV packs reused as stationary storage": dict(
        value=22.0, value_tag="REAL", life=7.0, life_tag="CITED", rate=7.0, eol=0.7, fade_m=1.0, fail_pct=0.0, repair_days=0,
        note="Value: our German day-ahead price runs, one cycle a day (REAL). Years: NREL 2015 repurposing 3 to 10, Relectrify trial 6 to 8 (CITED). Retire at 70%: the brief's stationary threshold (CITED). "
             "Fade 1% a year: the 8 retired Leaf cells showed about 0 to 1% a year over a year (REAL), and six Mini-E packs lost 0 to 6% in 2.5 years, up to about 2.4% a year (NREL 2019, CITED). Failures off: published catastrophic cell failure rates are 1 in 10 to 40 million cells (Faraday Institute 2023), far below the 0.2% per cell-year where bypass would matter; no public figure for aged cells."),
    "Grid-scale storage": dict(
        value=12.0, value_tag="ASSUMED", life=15.0, life_tag="CITED", rate=7.0, eol=0.7, fade_m=2.0, fail_pct=0.0, repair_days=0,
        note="Value: CAISO's market monitor reports actual batteries earned about $43 per kW-year from energy and $7 from regulation in 2024 (about $50), and a simulated full fleet $52 + $28; divided by an ASSUMED 4-hour duration, $50 is about $12 per kWh-year (resource adequacy payments excluded; ERCOT June 2025 gives about $9). "
             "Years: NREL ATB 2024 assumes 15 with augmentation (CITED). Retire 70% (brief). Fade 2% a year is ASSUMED, within the 0 to 2.4% NREL measured. Real strings hold hundreds of cells in series; only the pack you load is simulated."),
    "Data-center backup": dict(
        value=8.0, value_tag="ASSUMED", life=12.0, life_tag="CITED", rate=7.0, eol=0.8, fade_m=0.5, fail_pct=0.0, repair_days=0,
        note="Backup is rarely cycled and sized for minutes (hyperscale 1 to 2, colocation about 5), so extra usable energy is worth the capacity you would otherwise buy or the replacement you defer: 98 EUR per kWh of new cells (Chalmers/BNEF, CITED) over 12 years is about 8 per kWh-year. "
             "Years: lithium-ion UPS batteries last 10 to 15 years (design target 15), lead-acid 3 to 6; lithium-ion costs 1.5 to 2 times lead-acid; maintenance about 1.5% of capex a year (Schneider Electric 2018, via Introl and Schneider, CITED). Retire at 80% and fade 0.5% a year are ASSUMED. "
             "The unquantified value is reliability: one dead cell can take down a string, and a bypass keeps backup alive."),
}


def apply_preset():
    p = PRESETS.get(st.session_state.get("preset"))
    if p:
        for k, v in p.items():
            if k != "note":
                st.session_state[k] = v

ASK = [
    "What is '2-3X more usable capacity' measured against (new or retired cells, which spread, which baseline BMS, which end-of-life level)?",
    "What is the efficiency of the switching path per cell, and its standby draw?",
    "What does the cell-level electronics cost per cell or per kWh, and what do you pay for retired packs per kWh?",
    "Do you have per-cell logs (capacity, voltage, temperature) from retired packs run with and without control?",
    "What input-voltage window does the converter accept (what share of a string's cells must stay in circuit)?",
    "Which application and tariff should we model, and which practical limit (technical, economic, safety) matters most?",
]


def tagged(label: str, value: float, key: str, tag: str, help: str = "", **kw):
    """A number box with its source tag beside it. Returns (value, tag)."""
    c1, c2 = st.sidebar.columns([3, 2])
    v = c1.number_input(label, value=value, key=key, help=help, **kw)
    t = c2.selectbox("source", SOURCES, index=SOURCES.index(tag), key=key + "_tag", label_visibility="visible")
    return float(v), t


@st.cache_data(show_spinner=False)
def run_design_scan(caps_t, m, fade_mean, loss_cell, e_cell, sort_cost, value, rate, years, eol, test_sigma, weak_corr, bal_r, bal_eta, bal_cost, closed_loss, hybrid_cost, fail_rate, repair_years):
    recs = DS.design_scan(list(caps_t), m, fade_mean=fade_mean, fade_cvs=[0.1, 0.2, 0.3], loss_cell=loss_cell, loss_exps=[1.0, 0.0], cost_exps=[1.0, 0.5, 0.0],
                          electronics_per_kwh_cell=e_cell, sort_cost_per_kwh=sort_cost, value_per_kwh_year=value, rate=rate, years=years, eol_frac=eol,
                          test_sigma=test_sigma, weak_corr=weak_corr, trials=80, seed=1,
                          balancer_rs=[bal_r] if bal_r else [], balancer_eta=bal_eta, balancer_per_kwh=bal_cost,
                          closed_loss=closed_loss, hybrid_per_kwh=hybrid_cost,
                          fail_rate_per_cell_year=fail_rate, repair_years=repair_years)
    free = recs if sort_cost == 0 else DS.design_scan(list(caps_t), m, fade_mean=fade_mean, fade_cvs=[0.1, 0.2, 0.3], loss_cell=loss_cell, loss_exps=[1.0, 0.0],
                                                      cost_exps=[1.0, 0.5, 0.0], electronics_per_kwh_cell=e_cell, sort_cost_per_kwh=0.0, value_per_kwh_year=value,
                                                      rate=rate, years=years, eol_frac=eol, test_sigma=test_sigma, weak_corr=weak_corr, trials=80, seed=1,
                                                      balancer_rs=[bal_r] if bal_r else [], balancer_eta=bal_eta, balancer_per_kwh=bal_cost,
                                                      closed_loss=closed_loss, hybrid_per_kwh=hybrid_cost,
                                                      fail_rate_per_cell_year=fail_rate, repair_years=repair_years)
    return recs, free


@st.cache_data(show_spinner=False)
def learn_flip(caps_t, m, cv, fade_mean, e_cell, value, rate, years, eol, closed_loss, bal_r, bal_cost, repair_years):
    return LN.flip_failure_rate(list(caps_t), m, cv=cv, fade_mean=fade_mean, electronics_per_kwh_cell=e_cell, value_per_kwh_year=value, rate=rate, years=years,
                                eol_frac=eol, closed_loss=closed_loss, balancer_r=bal_r, balancer_per_kwh=bal_cost, repair_years=repair_years)


@st.cache_data(show_spinner=False)
def run_build(caps_t, m, fade_mean, loss, e_cost, sort_cost, value, rate, years, eol, tsig, wcorr, bal_r, bal_eta, bal_cost, closed_loss, dod_exp, knee_share):
    """One policy: the best build for THIS pack (plain, sort only, selective bypass on the k weakest cells of each string, switches everywhere, hybrid, balancer) and its margin over the best rival."""
    ks = tuple(k for k in (1, 2, 3, 4) if k < m)
    return RW.recommend_build(list(caps_t), m, balancer_r=bal_r, balancer_per_kwh=bal_cost, ks=ks, fade_mean=fade_mean, fade_cv=0.2, loss=loss, electronics_per_kwh=e_cost,
                              sort_cost_per_kwh=sort_cost, value_per_kwh_year=value, rate=rate, years=years, eol_frac=eol, test_sigma=tsig, weak_corr=wcorr, balancer_eta=bal_eta,
                              closed_loss=closed_loss, dod_exp=dod_exp, knee_share=knee_share, trials=16, steps=48, seed=5)


def pct(x) -> str:
    return "n/a" if x is None else f"{x:.1%}"


st.set_page_config(page_title="REON: what is cell-level control worth?", layout="wide")
st.markdown("<style>@media (min-width: 1000px){[data-testid='stSidebar']{min-width:400px;max-width:520px}}</style>", unsafe_allow_html=True)   # the source-tag boxes were cut off at the default width
st.title("What is cell-level control worth for this pack?")
st.caption("Without control a string stops at its weakest cell (usable = N x weakest). With a switch at every cell it can run every cell to its own end (usable = sum). "
           "This page asks how much of that survives real limits, what it is worth, and how sure we are.")

# ---------------------------------------------------------------- sidebar
sb = st.sidebar
sb.header("0. Application")
sb.selectbox("Start from a preset (changes only the inputs below; each value is tagged)", list(PRESETS), key="preset", on_change=apply_preset)
if PRESETS.get(st.session_state.get("preset")):
    sb.caption(PRESETS[st.session_state["preset"]]["note"])
sb.header("1. The cells")
choice = sb.selectbox("Cell capacities", list(SAMPLES), key="choice")
caps = SAMPLES[choice]
fade = None
if caps is None:
    txt = sb.text_area("Paste capacities (Ah): one per line, or separated by commas or spaces", value="100\n90\n80\n70", key="paste")
    up = sb.file_uploader("...or upload a CSV (optional fade_rate column)", type=["csv", "txt"], key="upload")
    try:
        parsed = R.parse_caps_text(up.getvalue().decode("utf-8", "replace") if up is not None else txt)
        caps, fade = parsed["caps"], parsed["fade_rates"]
    except ValueError as e:
        sb.error(f"Could not read the capacities: {e}")
        st.stop()
if len(caps) < 2 or min(caps) <= 0:
    sb.error("Need at least two cells with positive capacity.")
    st.stop()
c = np.asarray(caps, dtype=float)
n = len(c)
cell_tag = sb.selectbox("Source of the capacities", SOURCES, index=1 if choice != "Paste or upload my own" else 2, key="cap_tag")
volts, volts_tag = tagged("Nominal cell voltage (V)", 3.7, "volts", "ASSUMED", min_value=0.5, max_value=5.0, step=0.1)
nameplate_kwh, nameplate_tag = tagged("Scale the result to a pack of (kWh nameplate)", 2000.0, "nameplate", "ASSUMED", min_value=1.0, step=100.0,
                                      help="The tests used 2 MWh. Per-kWh results do not depend on this; yearly money and carbon do.")

sb.header("2. Practical limits")
loss_pct, loss_tag = tagged("Switching / conversion loss (%)", 2.0, "loss", "ASSUMED", min_value=0.0, max_value=30.0, step=0.5,
                            help="Literature range 1 to 5% (Chalmers, simulation). Not REON's number.")
use_win = sb.checkbox("The converter needs a minimum share of cells in circuit", value=False, key="use_win",
                      help="Off = REON's ideal sum. On = a first-order limit from the string-voltage window.")
win_frac = None
if use_win:
    win_frac = sb.slider("Minimum share of cells in circuit", 0.1, 1.0, 0.5, 0.05, key="win") 
weak_pct = sb.slider("Weak-cell cut-off for the data check (% below median)", 3, 25, 5, key="weak")

sb.header("3. Money")
e_cost, e_tag = tagged("Control electronics, cost per kWh of nameplate", 8.8, "e_cost", "CITED", min_value=0.0, step=0.5,
                       help="Chalmers bottom-up for NEW EV packs: 8.5 to 9.4% of a 98 EUR/kWh pack. Not REON's cost.")
value_kwh, value_tag = tagged("Value of one extra usable kWh per year", 22.0, "value", "REAL", min_value=0.1, step=0.5,
                              help="20.6 to 23.2 EUR from our German day-ahead price runs (2 MWh pack, one cycle a day, regulation off).")
alt_cost, alt_tag = tagged("Cost of getting that capacity by adding cells instead (per kWh)", 60.0, "alt", "ASSUMED", min_value=1.0, step=5.0,
                           help="New cells about 98 EUR/kWh (Chalmers/BNEF 2024); retired cells 20 to 60 (NREL 2015 repurposing, excludes the used-cell price).")
rate_pct, rate_tag = tagged("Discount rate (%)", 7.0, "rate", "ASSUMED", min_value=0.0, max_value=20.0, step=0.5)
life_y, life_tag = tagged("Years of service", 7.0, "life", "CITED", min_value=1.0, max_value=20.0, step=1.0, help="NREL 2015: 3 to 10 years; Relectrify trial: 6 to 8.")
sb.caption("Starting values are literature or test values, not REON's. Change them, and change the tag if you know better.")

# ---------------------------------------------------------------- numbers
loss = loss_pct / 100.0
g_ideal = L.net_gain(c, 1.0)
g_prac = R.gain_after(c, loss, win_frac)
conv_ah, ideal_ah = float(n * c.min()), float(c.sum())
extra_frac = g_prac / (1.0 + g_prac)                      # extra usable kWh per kWh of nameplate (nameplate = usable x (1 + g))
extra_kwh = nameplate_kwh * extra_frac if g_prac > 0 else 0.0
cost_extra = U.cost_per_extra_kwh(e_cost, g_prac) if g_prac > 0 else None
payback = U.payback_years(cost_extra, value_kwh) if cost_extra is not None else None
lev_cost = U.levelized_cost_per_extra_kwh_year(cost_extra, rate_pct / 100.0, life_y) if cost_extra is not None else None
be_alt = U.breakeven_gain(e_cost, alt_cost)

# verdict
if g_prac <= 0:
    st.error("Day-1 view: with these limits control delivers no more than the conventional pack on these cells. Loosen the limits or use a pack with more spread.")
elif lev_cost is not None and lev_cost > value_kwh:
    near = "does not quite repay" if lev_cost <= 1.15 * value_kwh else "does not repay"
    st.warning(f"Day-1 view: control adds {pct(g_prac)} usable energy, but its yearly cost per extra kWh ({lev_cost:.1f}) is above the yearly value ({value_kwh:.1f}) at a "
               f"{rate_pct:.0f}% rate over {life_y:.0f} years: it {near}.")
else:
    st.success(f"Day-1 view: control adds {pct(g_prac)} usable energy after your limits and repays: yearly cost per extra kWh {lev_cost:.1f} against a value of {value_kwh:.1f}.")
if g_prac > 0:
    if be_alt is None or g_prac < be_alt:
        st.info(f"Against simply adding capacity at {alt_cost:g} per kWh, control is cheaper only above a gain of {pct(be_alt) if be_alt is not None else 'never'}; this pack has {pct(g_prac)}. "
                "It can still win where there is no room, weight or cell supply for extra cells.")
    else:
        st.info(f"Against adding capacity at {alt_cost:g} per kWh, control is cheaper here (break-even gain {pct(be_alt)}, this pack {pct(g_prac)}).")

# carbon at base (for the tile and tab)
carbon_levers = [
    Lever(C.EMBODIED, 84.0, 61.0, 106.0, "CITED", "kg CO2e/kWh", "IVL 2019 range (press page)"),
    Lever(C.EXTRA_KWH, max(extra_kwh, 1e-6), 0.5 * max(extra_kwh, 1e-6), 1.5 * max(extra_kwh, 1e-6), "ASSUMED", "kWh", "from the gain above, +/-50%"),
    Lever(C.DISPLACED, 0.5, 0.0, 1.0, "ASSUMED", "", "share of the extra capacity that would otherwise be new-built"),
    Lever(C.CONTROL_EMBODIED, 800.0, 200.0, 2000.0, "ASSUMED", "kg CO2e", "no source: ask REON"),
    Lever(C.GRID_SAVED, 0.0, 0.0, 0.2, "ASSUMED", "t CO2e/yr", "no carbon series used"),
    Lever(C.YEARS, float(life_y), max(1.0, life_y * 0.5), life_y * 1.5, life_tag, "yr"),
]
net_t = C.carbon_balance({l.name: l.base for l in carbon_levers})["net_t"] if g_prac > 0 else None

tiles = [
    H.Metric("Gain, ideal control", 100 * g_ideal, "%", 1, None, "", "", False, "Usable energy with control vs the weakest-cell pack, every cell run to its own end."),
    H.Metric("Gain after your limits", 100 * g_prac, "%", 1, 100 * (g_prac - g_ideal), " pts", "vs ideal", False, "After the switching loss and (if on) the converter window."),
]
if payback is not None:
    tiles.append(H.Metric("Payback", payback, " yr", 1, None, "", "", True, "Years for the yearly value of an extra kWh to repay its electronics cost, no discounting."))
if be_alt is not None and g_prac > 0:
    tiles.append(H.Metric("Break-even vs adding cells", 100 * be_alt, "%", 1, 100 * (g_prac - be_alt), " pts", "vs break-even", False,
                          "Control is cheaper than adding capacity only above this gain; positive change = this pack is above it."))
if net_t is not None:
    tiles.append(H.Metric("Net carbon (base)", net_t, " t CO2e", 1, None, "", "", False, "Avoided new-battery manufacturing minus control electronics plus operation, for the scaled pack. See the Carbon tab."))
H.render(st, tiles)
tags_line = f"capacities [{cell_tag}] | loss [{loss_tag}] | electronics [{e_tag}] | value [{value_tag}] | alternative cost [{alt_tag}] | rate [{rate_tag}] | life [{life_tag}]"
st.caption("Source tags: " + tags_line)
st.caption("The verdict and tiles above are a day-1 snapshot. Tab 5 adds ageing and retirement and can change the answer: it is the one to quote.")

rec_slot = st.container()   # filled by the recommended-build block in tab 5, so the answer sits next to the tiles

# ---------------------------------------------------------------- tabs
t1, t2, t3, t4, tv, t5 = st.tabs(["1 What we gain", "2 How solid is it", "3 Money", "4 Carbon", "5 Beats current methods?", "6 Story"])

with t1:
    st.markdown(f"Without control every cell stops when the weakest ({c.min():.2f} Ah) is empty, so the string delivers **{conv_ah:.1f} Ah**. "
                f"With control each cell runs to its own end: **{ideal_ah:.1f} Ah**, a gain of **{pct(g_ideal)}** [{cell_tag}].")
    st.bar_chart(pd.DataFrame({"capacity (Ah)": c}, index=pd.RangeIndex(1, n + 1, name="cell")))
    st.caption(f"Spread (coefficient of variation) {pct(float(c.std(ddof=1) / c.mean()))}. Gain = mean / weakest - 1, so it depends on how far the weakest cells sit below the rest.")
    st.dataframe(pd.DataFrame({"": ["Without control", "With ideal control", "After your limits"],
                               "usable (Ah)": [conv_ah, ideal_ah, conv_ah * (1 + g_prac)],
                               "usable (kWh)": [conv_ah * volts / 1000, ideal_ah * volts / 1000, conv_ah * (1 + g_prac) * volts / 1000]}).round(2), hide_index=True)

with t2:
    st.markdown("**Switching loss.** A loss takes a share of the energy that passes the switches.")
    lt = L.loss_table(c, [0.0, 0.01, 0.02, 0.05, 0.10])
    st.dataframe(pd.DataFrame({"loss": [f"{k:.0%}" for k in lt["net_gain"]], "net gain": [pct(v) for v in lt["net_gain"].values()]}), hide_index=True)
    st.caption(f"The gain disappears at a loss of {pct(lt['break_even_loss'])}." + (" On cells this well matched, a 2% loss already erases it." if lt["break_even_loss"] < 0.02 else ""))
    st.markdown("**Converter window.** If the converter needs a minimum share of cells in circuit, the weakest cells cannot be bypassed all the way.")
    rows = []
    for f in (1.0, 0.9, 0.8, 0.5, 0.25):
        k = max(1, int(np.ceil(f * n)))
        r = [x for x in W.window_curve(c) if x["n_min"] == k][0]
        rows.append({"cells that must stay in circuit": f"{f:.0%} ({k} of {n})", "share of the ideal gain kept": pct(r["share_of_ideal_gain"]), "gain": pct(r["gain"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    fr = S.fragility(c)
    st.markdown("**One cell?** " + (f"Without the single weakest cell the gain would be {pct(fr['gain_without_weakest'])}: {pct(fr['share_lost'])} of the gain rests on that one cell. Check it is a real weak cell and not a bad reading."
                                    if fr["share_lost"] >= 0 else f"Removing the weakest cell would raise the gain to {pct(fr['gain_without_weakest'])}: the result does not hang on one cell."))
    st.markdown("**Measurement noise.** The weakest *measured* cell is biased low, so noisy capacity estimates inflate the gain.")
    nz = [{"capacity error": f"{s:.0%}", "apparent gain from noise and spread": pct(S.noise_bias(c, s)["apparent_mean"])} for s in (0.01, 0.02, 0.03)]
    st.dataframe(pd.DataFrame(nz), hide_index=True)
    st.markdown("**Against the usual alternative: sorting cells into matched strings.** Second-life packs are normally graded and regrouped, not controlled cell by cell.")
    divs = [d for d in range(1, n + 1) if n % d == 0 and d >= 2 and n // d >= 2]
    if divs:
        m_len = st.selectbox("Cells per string (strings run in parallel)", divs, index=len(divs) - 1 if len(divs) < 3 else len(divs) // 2, key="m_len")
        sig = st.slider("Capacity test error used for sorting (%)", 0, 10, 2, key="sort_sig") / 100.0
        sr = SO.sorting_vs_control(c, m_len, sigma_rel=sig, trials=300)
        base = sr["as_found"]
        st.dataframe(pd.DataFrame({"way of building the pack": ["As found", "Random regrouping", "Sorted, with test error", "Sorted, perfect test", "Cell-level control (ideal)"],
                                   "usable (Ah)": [sr[k] for k in ("as_found", "random", "sorted_noisy", "sorted_ideal", "control")],
                                   "vs as found": [pct(sr[k] / base - 1) for k in ("as_found", "random", "sorted_noisy", "sorted_ideal", "control")]}).round(1), hide_index=True)
        st.caption(f"Control beats perfect sorting by {pct(sr['control_over_sorted_ideal'])} (the switching loss that cancels this is about {pct(1 - 1 / (1 + sr['control_over_sorted_ideal']))}) "
                   f"and sorting with a {sig:.0%} test error by {pct(sr['control_over_sorted_noisy'])}. Testing every cell for sorting has a cost that is not counted here.")
    show_contract(K.check_cells(list(c), weak_frac=weak_pct / 100.0), "Cell data check")

with t3:
    if g_prac <= 0:
        st.info("No gain after your limits, so nothing to pay for.")
    else:
        st.markdown(f"Cost per extra usable kWh = electronics per kWh x (1 + gain) / gain = **{cost_extra:.1f}** [{e_tag}]; payback **{payback:.1f} years** without discounting. "
                    f"At {rate_pct:.0f}% over {life_y:.0f} years the yearly cost per extra kWh is **{lev_cost:.1f}** against a yearly value of **{value_kwh:.1f}** [{value_tag}].")
        st.markdown(f"For a pack of {nameplate_kwh:,.0f} kWh nameplate, the extra usable energy is about **{extra_kwh:,.0f} kWh**, worth about **{extra_kwh * value_kwh:,.0f} per year**.")
        th = U.repay_thresholds(g_prac, e_cost, value_kwh, rate_pct / 100.0, life_y)
        st.markdown("**What would flip the verdict** (one input at a time, the others as set):")
        st.dataframe(pd.DataFrame({"input": ["Electronics cost per kWh", "Value of an extra kWh per year", "Gain after your limits", "Extra loss the gain can take"],
                                   "now": [f"{e_cost:.1f}", f"{value_kwh:.1f}", pct(g_prac), "n/a"],
                                   "still repays up to / down to": [f"{th['max_electronics_per_kwh']:.1f} (max)",
                                                                    "n/a" if th["min_value_per_kwh_year"] is None else f"{th['min_value_per_kwh_year']:.1f} (min)",
                                                                    "never" if th["min_gain"] is None else f"{pct(th['min_gain'])} (min)",
                                                                    "already does not repay" if th["extra_loss_tolerated"] is None else f"{pct(th['extra_loss_tolerated'])} more"]}), hide_index=True)
        be = [{"alternative: adding capacity at (per kWh)": a, "control cheaper only above a gain of": pct(U.breakeven_gain(e_cost, a)) if U.breakeven_gain(e_cost, a) is not None else "never",
               "this pack": pct(g_prac)} for a in (98.4, 60.0, 40.0, 20.0)]
        st.dataframe(pd.DataFrame(be), hide_index=True)
        lv = [Lever("e", e_cost, 0.5 * e_cost, 1.7 * e_cost, e_tag, "per kWh"), Lever("value", value_kwh, 0.9 * value_kwh, 1.1 * value_kwh, value_tag, "per kWh/yr")]
        mc = M.monte_carlo(lv, lambda v: life_y - U.payback_years(U.cost_per_extra_kwh(v["e"], g_prac), v["value"]), n=4000)
        st.caption(f"Under triangular ranges around your inputs (electronics x0.5 to x1.7, value +/-10%; ranges ASSUMED), payback comes within {life_y:.0f} years in {1 - mc['prob_negative']:.0%} of draws. "
                   "That is a probability under the ranges typed, not a frequency in the world.")

with t4:
    if g_prac <= 0:
        st.info("No gain after your limits, so no avoided manufacturing.")
    else:
        sens = C.sensitivity(carbon_levers)
        mcc = M.monte_carlo(carbon_levers, lambda v: C.carbon_balance(v)["net_t"], n=4000)
        st.markdown(f"Base net **{sens['base_net_t']:.1f} t CO2e** over the pack's second life; best and worst combinations {sens['min_net_t']:.1f} to {sens['max_net_t']:.1f} t; "
                    f"below zero in {mcc['prob_negative']:.0%} of draws under the ranges typed.")
        st.dataframe(sens["table"].round(2), hide_index=True)
        ft = C.flip_table(carbon_levers)
        ft = ft.rename(columns={"input": "input", "base": "base", "flip_value": "net is zero at", "inside_range": "inside its range?", "net_at_base": "net at base"})
        st.markdown("**Where the sign flips** (one input at a time):")
        st.dataframe(ft.round(3), hide_index=True)
        st.caption("Most of these inputs are ASSUMED. The decisive one is the share of the extra capacity that would otherwise be new-built. "
                   "Carbon is optional in the REON brief: economic value or environmental sustainability.")

with tv:
    st.markdown("Sorting cells into matched strings is the usual alternative, and on well-matched cells it captures most of a per-cell switch's gain (tab 2). "
                "Two things can still make control the better answer. Both rest on assumptions you can change; none is REON's measured value.")
    st.subheader("C. The answer: best way to build this pack, with the conditions")
    st.caption("One search over every combination of the fixes below (sort first or not, switch on every cell or every k cells), scored on money over the pack's life against "
               "the plain pack. A string with switches leaves them closed unless engaging pays, so a switch never makes it worse apart from its electronics cost.")
    c1, c2, c3, c4, c5 = st.columns(5)
    fade_m = c1.number_input("Mean fade (% of day-1 capacity per year)", value=1.0, min_value=0.0, max_value=20.0, step=0.5, key="fade_m", help="Default 1%: the 8 retired Leaf cells showed about 0 to 1% a year (REAL); NREL measured up to about 2.4% (CITED). Hard cycling fades faster (Iowa State cells).") / 100.0
    eol = c2.slider("Retire when deliverable falls below (share of day-1 nameplate)", 0.3, 0.9, 0.7, 0.05, key="eol",
                    help="REON's brief: a simple capacity threshold, 80% is common for EVs and 70% for stationary storage; it depends on duty, warranty and service obligation, and the operator may accept reduced service instead of retiring (CITED, challenge brief).")
    wcorr = c3.slider("Do weak cells fade faster? (-1 slower, +1 faster)", -1.0, 1.0, 0.0, 0.1, key="wcorr")
    sort_cost = c4.number_input("Cost to test, sort and repack (per kWh nameplate)", value=0.0, min_value=0.0, step=0.5, key="sort_cost",
                                help="0 = most favourable to sorting. ACEEE: UL1974 testing may cost about 30% of a used battery's value.")
    tsig = c5.slider("Capacity test error used for sorting (%)", 0, 10, 2, key="tsig") / 100.0
    b1, b2, b3, b4 = st.columns(4)
    use_bal = b1.checkbox("Compare with an active balancer", value=True, key="use_bal",
                          help="The usual alternative that moves charge between cells. Passive balancing only equalises state of charge and equals the plain pack.")
    bal_r = b2.slider("Balancer transfer limit (% of a cell's capacity per discharge)", 1, 60, 10, key="bal_r",
                      help="Balancer current x discharge time / cell capacity. A 1 A module balancer is about 2-4%; an 'up to 10 A' balancer (LTC3300, per a vendor article) on a 90 Ah cell over 2 h is about 22%.") / 100.0
    bal_eta = b3.slider("Balancer efficiency (%)", 70, 98, 90, key="bal_eta") / 100.0
    bal_cost = b4.number_input("Balancer cost (per kWh nameplate)", value=float(e_cost), min_value=0.0, step=0.5, key="bal_cost",
                               help="ASSUMED. Set equal to the switch electronics by default; 0 is the most favourable case for the balancer.")
    f1, f2 = st.columns(2)
    fail_pct = f1.number_input("Cells that die per year (% of cells, open circuit)", value=0.0, min_value=0.0, max_value=20.0, step=0.1, key="fail_pct",
                               help="ASSUMED: no public figure for retired cells. A dead cell breaks its string; only a switch on every cell can bypass it, a balancer cannot.") / 100.0
    repair_days = f2.number_input("Days to replace a dead cell (0 = never within the service period)", value=0, min_value=0, max_value=730, step=15, key="repair_days")
    h1, h2 = st.columns(2)
    closed_loss = h1.number_input("Loss of a CLOSED switch (% of throughput)", value=0.0, min_value=0.0, max_value=5.0, step=0.25, key="closed_loss",
                                  help="0 = switches that sit beside the cells and carry nothing until used. Equal to the engaged loss = a series switch on every cell (the pessimistic bound). ASK REON.") / 100.0
    hyb_shared = h2.checkbox("One set of hardware does both balancing and bypass (hybrid)", value=False, key="hyb_shared",
                             help="If off, the hybrid pays for switch electronics plus a balancer.")
    mopts = [d for d in range(1, n + 1) if n % d == 0 and d >= 2]
    m_str = st.selectbox("Cells per series string (fixed by the application's voltage; the rest run in parallel)", mopts, index=len(mopts) - 1, key="m_str")
    recs, free = run_design_scan(tuple(float(x) for x in c), int(m_str), fade_m, loss, e_cost, float(sort_cost), value_kwh, rate_pct / 100.0, life_y, eol, tsig, wcorr,
                                  bal_r if use_bal else 0.0, bal_eta, float(bal_cost), closed_loss,
                                  float(e_cost) if hyb_shared else float(e_cost + bal_cost),
                                  float(fail_pct), (repair_days / 365.0) if repair_days else None)
    rec = DS.recommend(recs)
    ref_years = float(np.mean([x["years"] for x in recs if x["design"].endswith("(reference)")]))
    inside = ref_years < life_y - 0.25
    rb = rec["robust"]
    rb_vals = list(rec["robust_mean_by_scenario"].values())
    if rb.endswith("(reference)"):
        st.warning("Under these assumptions no design beats the plain pack in the worst case. Do not add switches or sorting here unless the inputs change (see the conditions).")
    else:
        st.success(f"Robust choice: **{rb}**. Net value {min(rb_vals):+.2f} to {max(rb_vals):+.2f} per kWh of nameplate (present value over the {life_y:.0f}-year service period) across {len(rec['scenarios'])} assumption sets "
                   f"(worst-case regret {rec['max_regret'][rb]:.2f}).")
    st.info(f"The plain pack stays in service **{ref_years:.1f} of {life_y:.0f} years** under your retirement rule. "
            + ("It retires inside the service period, so keeping it in service is what pays: per-cell or group switches beat sorting here." if inside
               else "It outlasts the service period, so switches mostly add the small day-1 gain and a cheap, perfect sort does about as well."))
    st.subheader("C0. Recommended build for THIS pack (one policy)")
    st.caption("Tests every build on this pack's own cell capacities: plain, sort only, switches on only the k weakest cells of each string (k = 1 to 4, hardware cost k/m of a full set), switches on every cell, "
               "switches plus a balancer, and the balancer alone. Net value per kWh of nameplate against the plain pack, using the inputs above. Ageing is a straight line unless you switch on the two options below (Iowa State fits).")
    w1, w2 = st.columns(2)
    dod_g = w1.number_input("Fade rises with depth of discharge: exponent (0 = off)", value=0.0, min_value=0.0, max_value=2.0, step=0.1, key="dod_g",
                            help="Iowa State / ILCC cells: 0.7 to 0.9 (90% CI 0.69 to 1.18 to 90% capacity). In a plain string the weakest cell works hardest and drifts away; bypass shares the load.")
    knee_pct = w2.number_input("Cells with an accelerating (knee) fade (%)", value=0, min_value=0, max_value=100, step=5, key="knee_pct",
                               help="Iowa State: 65% of 205 lab cells fade about 2.4x faster from about 85% of their start. An upper bound for retired packs; no public figure for retired ones.")
    bres = run_build(tuple(float(x) for x in c), int(m_str), fade_m, loss, float(e_cost), float(sort_cost), value_kwh, rate_pct / 100.0, life_y, eol, tsig, wcorr,
                     bal_r if use_bal else 0.0, bal_eta, float(bal_cost), closed_loss, float(dod_g), knee_pct / 100.0)
    btab = bres["table"]
    won = bres["margin"] > 0
    msg = (f"Recommended build: **{bres['build']}**, net {btab[bres['build']]['mean']:+.1f} per kWh of nameplate over the plain pack"
           + (f"; {bres['margin']:+.1f} ahead of the best alternative ({bres['rival_best']})." if won else f"; our best ({bres['ours_best']}) is {-bres['margin']:.1f} behind it."))
    (st.success if won else st.warning)(msg)
    with rec_slot:
        (st.success if won else st.warning)(msg + " Details: tab 5, section C0. Ageing and costs are the inputs in tab 5 and the sidebar (ASSUMED unless tagged).")
    st.dataframe(pd.DataFrame([{"build": k, "net value (mean)": round(v["mean"], 1), "p10": round(v["p10"], 1), "p90": round(v["p90"], 1), "hardware cost": round(v["cost"], 1),
                                "years in service": round(v["years"], 1)} for k, v in sorted(btab.items(), key=lambda kv: -kv[1]["mean"])]), hide_index=True)
    st.caption("Switches on only some cells scale our hardware cost by k/m (extra wiring ignored). The test error you set above decides which cells get the switches. Stress-tested in examples/reon_stress*.py; "
               "we lose when the balancer is both cheap and able to move 20% or more of a cell per cycle, or when our electronics cost more than about 12.")
    if use_bal:
        def kbest(kinds):
            names = {r["design"] for r in recs if r["kind"] in kinds and r["order"] == "as_found"}
            return max((np.mean([r["mean"] for r in recs if r["design"] == nm]) for nm in names), default=None)
        sw_b, late_b, bal_b, hyb_b = kbest(("switch",)), kbest(("late",)), kbest(("balancer",)), kbest(("hybrid",))
        if None not in (sw_b, late_b, bal_b, hyb_b):
            top = max([("switches engaged always", sw_b), ("late-engaging switches", late_b), ("active balancer", bal_b), ("hybrid", hyb_b)], key=lambda kv: kv[1])
            (st.warning if top[0] == "active balancer" else st.info)(
                f"Average net value per kWh of nameplate, as found: switches engaged always {sw_b:+.1f}; late-engaging switches {late_b:+.1f}; active balancer ({bal_r:.0%} limit, "
                f"{bal_eta:.0%}, cost {bal_cost:g}) {bal_b:+.1f}; hybrid {hyb_b:+.1f}. Best: **{top[0]}**. "
                + ("The balancer wins here: switches need a lower balancer limit, a dearer balancer, a less lossy closed switch, or more mismatch (or dead cells)." if top[0] == "active balancer"
                   else "The hybrid only adds value over late-engaging switches when the switch loss is high and the cells are badly mismatched, and only if one set of hardware does both." if top[0] == "hybrid"
                   else ""))
        mstr = int(m_str)
        wi = int(np.argmin(c)) // mstr
        pol = DS.policy(list(c[wi * mstr:(wi + 1) * mstr]), loss=loss, closed_loss=closed_loss, balancer_r=bal_r, balancer_eta=bal_eta)
        st.caption("Controller decision today, for the string with the weakest cell: " + "; ".join(f"{k} {v:.1f} Ah" for k, v in pol["modes"].items())
                   + f" -> runs **{pol['best']}** ({pct(pol['gain_over_plain'])} over the plain string, before electronics cost). The simulation takes this max at every time step as the cells age.")
    cond = DS.conditions(recs)
    st.dataframe(pd.DataFrame([{"design that wins": k, "wins in (of %d)" % len(rec["scenarios"]): v["n"], "fade-rate spread": ", ".join(f"{x:.2f}" for x in v["fade_cv"]),
                                "loss scales with switches (p)": ", ".join(f"{x:g}" for x in v["loss_exp"]), "electronics cost scaling (q)": ", ".join(f"{x:g}" for x in v["cost_exp"])}
                               for k, v in sorted(cond.items(), key=lambda kv: -kv[1]["n"])]), hide_index=True)
    be = DS.sort_cost_breakeven(free)
    if be["median"] is not None:
        st.caption("Sorting/repacking is worth at most " + (f"{be['median']:.2f} per kWh of nameplate (median over assumption sets; range {be['min']:.2f} to {be['max']:.2f})"
                   if be["median"] > 0 else "nothing here (switches do better even if sorting is free)") + ". Compare with what it really costs to test and repack a cell: ask REON.")
    else:
        st.caption("One string: sorting changes nothing.")
    st.subheader("C2. Learn from data: the answer updates as failures and capacity snapshots come in")
    st.caption("Enter what has actually been observed (REON's retired packs, or any fleet). Nothing simulated goes in here: made-up failures would only teach the app our own guess. "
               "Prior belief is ASSUMED (about 0.5% per cell-year, wide); the update is exact. Test the rule on simulated fleets with examples/reon_learn_flip.py.")
    l1, l2 = st.columns(2)
    seen_f = l1.number_input("Cells that failed open-circuit (count)", value=0, min_value=0, step=1, key="learn_f")
    seen_cy = l2.number_input("Cell-years watched (cells x years)", value=0.0, min_value=0.0, step=100.0, key="learn_cy")
    fade_txt = st.text_input("Measured fade rate per cell (% of day-1 capacity per year, comma-separated; needs two or more)", value="", key="learn_fades")
    try:
        obs_fades = [float(x) / 100.0 for x in fade_txt.replace(";", ",").split(",") if x.strip()]
    except ValueError:
        obs_fades = []
        st.warning("Could not read the fade rates; use numbers separated by commas.")
    fbel = LN.FailureBelief().update(int(seen_f), float(seen_cy))
    cvbel = LN.FadeBelief(prior_cv=0.20).update(obs_fades)
    flip = learn_flip(tuple(float(x) for x in c), int(m_str), round(cvbel.cv, 3), fade_m, e_cost, value_kwh, rate_pct / 100.0, life_y, eol, closed_loss,
                      bal_r if use_bal else 1e9, float(bal_cost), (repair_days / 365.0) if repair_days else None)
    lo_f, hi_f = fbel.interval()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Believed failure rate / cell-year", f"{fbel.mean:.2%}", help=f"90% range {lo_f:.2%} to {hi_f:.2%}")
    m2.metric("Believed fade-rate spread (CV)", f"{cvbel.cv:.2f}", help="Starts at 0.20 (median within-group spread of the Iowa State cells, CITED-derived) and moves with measured per-cell fade rates.")
    if flip is None:
        m3.metric("Failure rate where switches win", "never")
        st.warning("With these inputs the balancer wins at every failure rate up to 20% per cell-year. Change the balancer cost, retirement level or repair time to see when switches can win.")
    else:
        m3.metric("Failure rate where switches win", f"{flip:.2%}" if flip > 1.5e-4 else "none needed")
        if flip <= 1.5e-4:
            st.info("With these inputs switches beat the balancer even if no cell ever fails, so failure data cannot change the answer. Failure data starts to matter when the balancer is free or cheap (lower its cost above) or the retirement level is low.")
        else:
            pa = LN.p_above(fbel, flip)
            dec = LN.decide(fbel, flip)
            m4.metric("Chance the true rate is above that", f"{pa:.0%}")
            (st.success if dec == "switches" else st.info)(
                {"switches": "Data says cell-level switches: we are at least 90% sure the failure rate is above the point where they beat the balancer.",
                 "balancer": "Data says a balancer: we are at least 90% sure the failure rate is below the point where switches pay.",
                 "undecided": "Not enough data to call it yet. " + ("Add observed failures and cell-years." if seen_cy == 0 else "Keep watching: more cell-years will settle it.")}[dec]
                + f" (flip computed for fade spread {cvbel.cv:.2f}, balancer cost {bal_cost:g}, retire at {eol:.0%}.)")
    st.subheader("A. Why: where to put the switches, every cell or every k cells?")
    st.caption("A switch on a group of k cells treats the group as one big cell limited by its weakest member, and costs about 1/k as much electronics. Per-cell voltage sensing is assumed to exist already.")
    g1, g2, g3 = st.columns(3)
    order = g1.selectbox("Cells grouped", ["as found (modules as they came)", "sorted first (needs repacking)"], key="gr_order")
    p_loss = g2.selectbox("Series loss scales with the number of switches?", ["yes, in proportion (p=1)", "no, it stays fixed (p=0)"], key="gr_p")
    q_cost = g3.selectbox("Electronics cost falls with fewer switches?", ["fully, per switch (q=1)", "half as fast (q=0.5)", "not at all (q=0)"], key="gr_q")
    rows = GR.granularity_table(c, electronics_per_kwh_cell_level=e_cost, loss_cell_level=loss, value_per_kwh_year=value_kwh, rate=rate_pct / 100.0, years=life_y,
                                loss_exponent=1.0 if p_loss.startswith("yes") else 0.0, cost_exponent={"f": 1.0, "h": 0.5, "n": 0.0}[q_cost[0]],
                                order="sorted" if order.startswith("sorted") else "as_found")
    if rows:
        st.dataframe(pd.DataFrame([{"cells per switch (k)": r["k"], "switches": r["switches"], "ideal gain": pct(r["gain_ideal"]), "gain after loss": pct(r["gain_net"]),
                                    "electronics per kWh": round(r["electronics_per_kwh"], 2),
                                    "cost per extra kWh": "n/a" if r["cost_per_extra_kwh"] is None else f"{r['cost_per_extra_kwh']:.1f}",   # text column: a mix of numbers and "n/a" breaks Arrow serialisation in the real frontend
                                    "net value per kWh-year": round(r["net_value_per_nameplate_kwh_year"], 2), "repays": "yes" if r["repays"] else "no"} for r in rows]), hide_index=True)
        b = GR.best_granularity(rows)
        st.info(f"Day-1 view, best here: {'a switch on every cell' if b['k'] == 1 else 'a switch every ' + str(b['k']) + ' cells'} ({b['switches']} switches), net value {b['net_value_per_nameplate_kwh_year']:.2f} per kWh of nameplate per year (no ageing)." if b
                else "No switch spacing beats doing nothing under these assumptions.")
    st.subheader("B. Why: cells drift apart, and sorting is a one-time fix")
    st.caption("Cells fade at different rates, so strings matched on day 1 are mismatched later, while per-cell control follows the drift. The fade rate, its spread and the end-of-life level are ASSUMED.")
    fade_cv = st.slider("Spread of fade rates (CV)", 0.0, 0.6, 0.3, 0.05, key="fade_cv")
    divs2 = [d for d in range(1, n + 1) if n % d == 0 and d >= 2]
    if divs2:
        m2 = st.selectbox("Cells per sorted string", divs2, index=min(len(divs2) - 1, len(divs2) // 2), key="drift_m")
        dr = DR.lifetime_compare(c, m2, fade_mean_per_year=fade_m, fade_cv=fade_cv, eol_frac=eol, loss=loss, trials=120, seed=1, weak_corr=wcorr)
        st.dataframe(pd.DataFrame({"way of building the pack": ["Weakest-cell pack", "Strings as found", "Sorted once", "Cell-level control"],
                                   "years to end of life": [dr["years"][k] for k in DR.METHODS],
                                   "energy delivered (Ah-years)": [dr["energy"][k] for k in DR.METHODS]}).round(1), hide_index=True)
        cl = dr["control_life_over_sorted_once"]
        if cl is not None and cl > 0:
            st.info(f"With drift, sorted strings fall behind: control lasts {pct(cl)} longer and delivers {pct(dr['control_energy_over_sorted_once'])} more energy. "
                    "Set the spread to 0 to see the case with no drift.")
        else:
            st.info("With these settings control does not last longer than sorting: with little drift, sorting wins by about the switching loss.")
        st.caption("The result hinges on the spread of fade rates, which nothing public in this repo measures. Per-cell capacity over time from one retired pack would settle it: ask REON.")

with t5:
    st.markdown(f"**What.** A battery is limited by its weakest cell, so retired packs are retired while most cells are still good. Here that strands **{pct(g_ideal)}** of the usable energy [{cell_tag}].")
    st.markdown(f"**How.** A switch and monitor at every cell lets the string run around a finished cell. After a {loss_pct:.1f}% loss [{loss_tag}]"
                + (f" and a converter that needs {win_frac:.0%} of cells in circuit" if win_frac else "") + f", the gain is **{pct(g_prac)}**.")
    st.markdown(f"**Who.** Owners of second-life storage, battery makers who sort packs, and operators who sell the energy (an extra kWh is worth about {value_kwh:.0f} per year [{value_tag}]).")
    if g_prac > 0:
        st.markdown(f"**Why.** Payback {payback:.1f} years undiscounted; yearly cost {lev_cost:.1f} vs value {value_kwh:.1f} at {rate_pct:.0f}% over {life_y:.0f} years; carbon net {net_t:.1f} t CO2e (mostly ASSUMED inputs).")
    st.markdown("**Limits.** The ideal sum is an upper bound; the converter window, parallel columns, spares, cell safety limits and the electronics cost are not REON's measured values.")
    res = R.analyze_pack(c, name=choice, volts=volts, losses=(loss,), electronics_per_kwh=e_cost, value_per_kwh_year=value_kwh, alt_costs=[98.4, 60.0, 40.0],
                         rate=rate_pct / 100.0, years=life_y, fade_rates=fade, weak_frac=weak_pct / 100.0,
                         sources={"capacities": cell_tag, "volts": volts_tag, "losses": loss_tag, "electronics_per_kwh": e_tag, "value_per_kwh_year": value_tag, "alt_costs": alt_tag})
    st.download_button("Download this report (Markdown)", R.render_markdown(res), file_name="reon_report.md", mime="text/markdown")
    with st.expander("Questions to ask REON (each one replaces a guess with a fact)"):
        for q in ASK:
            st.write("- " + q)
