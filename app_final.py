"""REON decision layer: dashboard v1 (replays and simulations only; no live hardware link). Run: streamlit run app_final.py
Tabs: 1 Is it worth it (live engine + go/no-go), 2 Where it flips (break-even map), 3 Life of the string (automatic bypass vs crew), 4 Storm (backup hours), 5 Voltage limit, 6 Evidence and limits."""
import csv
import numpy as np
import pandas as pd
import streamlit as st
from hackkit import reon_events as E
from hackkit import reon_storm as S
from hackkit import reon_voltage as V
from hackkit import reon_wear as W
from hackkit import reon_guard as G
from hackkit import reon_rank as RK
from hackkit import reon_presets as PR

st.set_page_config(page_title="REON decision layer", layout="wide")
st.title("Beyond the weakest cell: what cell-level control is worth")
st.caption("Draft for the MIT Energy & Climate Hack. Every input below is tagged in docs/SOURCES.md; sodium-ion data are still assumed. Simulations and replays only.")


@st.cache_data
def real_packs():
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    car = {}
    for p, _, _, late in rows:
        car.setdefault(p, []).append(float(late))
    return {k: np.array(v) for k, v in car.items()}


BE = pd.DataFrame({"fade spread 0.20": [16.2, 27.3, 45.7, None], "0.45": [25.4, 42.9, None, None], "0.60": [29.1, 49.4, None, None]}, index=["value 12", "value 22", "value 40", "value 80"])
t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(["1 Is it worth it", "2 Where it flips", "3 Life of the string", "4 Storm", "5 Voltage limit", "6 Evidence and limits", "7 Which cell is hurting", "8 Where the money comes from"])

with t1:
    c = st.columns(5)
    fade25 = c[4].slider("Cell fade per year at 25 C (20,000-cycle claim = 0.004 at one cycle a day; lithium EVs about 0.02)", 0.003, 0.04, 0.008, format="%.3f")
    temp = c[4].slider("Average cell temperature, C (ageing about doubles per 10 C, assumed)", 15, 45, 25)
    fade = fade25 * 2.0 ** ((temp - 25) / 10.0)
    value = c[0].slider("Value per kWh-year (12 grid, 22 EV, 30-90 demand-charge sites)", 5.0, 100.0, 40.0)
    fcv = c[1].slider("Spread of fade rates between cells (real cars 0.20-0.60)", 0.05, 0.8, 0.45)
    elec = c[2].slider("Switch cost per kWh nameplate (Tim Ren: 7-24)", 2.0, 40.0, 15.5)
    loss = c[3].slider("Usable-energy loss: switches + voltage floor", 0.0, 0.10, 0.04)
    if st.button("Run the engine") or True:
        rng = np.random.default_rng(3)
        start = 100.0 * (1.0 + 0.02 * rng.standard_normal(16))
        rob = G.robust_recommend(start, 16, value_per_kwh_year=value, electronics_per_kwh=elec, fade_cv=fcv, loss=loss, fade_mean=fade)
        out, _ = G.safe_recommend(start, 16, value_per_kwh_year=value, electronics_per_kwh=elec, fade_cv=fcv, loss=loss, fade_mean=fade)
        (st.success if rob["verdict"] == "BUY" else st.warning)(f"Verdict on a fresh seed: {rob['verdict']} ({rob['build']}). " + "; ".join(rob["reasons"]))
        for w in rob["warnings"]:
            st.caption(f"Note: {w}")
        t = out["table"]
        m = st.columns(4)
        m[0].metric("Recommended build", out["build"])
        m[1].metric("Net value vs plain string", f"{t[out['ours_best']]['mean']:+.1f} per kWh")
        m[2].metric("Margin over best rival", f"{out['margin']:+.1f}", help=f"best rival: {out['rival_best']}")
        m[3].metric("Service life", f"{t[out['ours_best']]['years']:.1f} y vs {t['plain']['years']:.1f} y plain")
        if out["margin"] <= 0:
            st.warning(f"No-go: at these inputs {out['rival_best']} is at least as good as switches. Do not buy switches here.")
        else:
            st.success("Go: switches beat the best alternative at these inputs.")
        st.dataframe(pd.DataFrame({k: {"net value per kWh": v["mean"], "10th percentile": v["p10"], "service years": v["years"], "cost": v["cost"]} for k, v in t.items()}).T.round(1))
    st.caption("Plain string = the brief's baseline. Balancer rival: 5 % transfer, cost 4. Start spread 2 %, 12 years, retire at 70 %. Stress tests: examples/reon_hero_stress_output.txt.")

with t2:
    st.subheader("Break-even switch cost against a typical balancer (per kWh nameplate)")
    st.dataframe(BE.fillna(">60 (never flips)"))
    st.write("Above the number in a cell, a typical balancer is better than switches. Tim Ren's overhead range is 7 to 24. Only the lowest-value, narrowest-spread corner puts that range partly in the losing zone. Source: examples/reon_losing_regimes_output.txt.")
    st.write("A logistic go/no-go screen on all inputs, tested on held-out draws, is right 88.5 % of the time against 82.7 % for always saying go, and catches about half the cases we lose: use it as a screen, not a verdict.")

with t3:
    c = st.columns(7)
    lam = c[0].select_slider("Cell fault rate per cell-year", [0.0002, 0.001, 0.002, 0.01, 0.03], 0.01)
    visit = c[1].select_slider("Cost of one crew visit", [250, 1000, 3000, 6000], 1000)
    lead = c[2].select_slider("Crew lead time (months)", [0.5, 1.0, 2.0, 4.0], 1.0)
    wl = c[3].select_slider("Weak line (fraction of the others)", [0.80, 0.85, 0.90], 0.80)
    detect = c[4].select_slider("Months before a plain string notices a fault", [0.0, 1.0, 3.0, 6.0], 0.0)
    dcost = c[5].select_slider("Cost per month down, per kWh nameplate (assumed)", [0, 5, 20, 60], 0)
    slack = c[6].select_slider("Share of current the site can shed (loss falls with current)", [0.0, 0.3, 0.5], 0.0)
    rows = []
    for pol in E.EXTENDED:
        r = [E.simulate(pol, s, lam=lam, visit_cost=float(visit), lead=lead, weak_line=wl, detect=detect, down_cost=float(dcost), slack=slack) for s in range(40)]
        rows.append({"policy": pol, "net value per kWh": np.mean([x["net"] for x in r]), "crew visits": np.mean([x["visits"] for x in r]), "months down": np.mean([x["down_months"] for x in r]), "life (years)": np.mean([x["life_years"] for x in r])})
    st.dataframe(pd.DataFrame(rows).round(1).set_index("policy"))
    site = dict(lam=lam, visit_cost=float(visit), lead=lead, weak_line=wl, detect=detect, down_cost=float(dcost), slack=slack)
    pick = E.choose_policy(E.EXTENDED, **site)
    if pick["auto_wins"]:
        st.success(f"For this site the policy to use is: {pick['policy']} (picked on one set of random seeds, confirmed on another). Automatic bypass pays here.")
    else:
        ls, ld = E.break_even("loss", 0.0, 0.3, seeds=range(6), iters=10, **{k: v for k, v in site.items() if k != "slack"})
        es, ed = E.break_even("e", 0.0, 80.0, seeds=range(6), iters=10, **site)
        tip = []
        if ls is not None and ld == "below":
            tip.append(f"switch conduction loss below {100*ls:.1f}% (now 2%)")
        if es is not None and ed == "below":
            tip.append(f"switch cost below {es:.0f} per kWh (assumed 15.5)")
        st.warning(f"For this site the policy to use is: {pick['policy']}. Automatic bypass does not pay here yet. It would if: " + (" or ".join(tip) if tip else "visits cost more or faults are more frequent (no switch loss or cost in range fixes it)") + ". Shedding current (the slider above) also lowers the loss.")
    st.write("replace = detect, wait for a crew, swap the cell. thr = fixed-threshold automatic bypass. ours = persistent-fault bypass plus per-cycle switching; ours+crew also books one visit to restore bypassed cells; ours+crew1/2 book it after 1 or 2 bypassed cells (cheap-visit sites). Fault rates and visit cost are ASSUMED.")

with t4:
    c = st.columns(4)
    load = c[0].slider("Critical load (kW)", 0.5, 5.0, 1.0)
    cold = c[1].slider("Cold capacity factor", 0.5, 1.0, 0.8)
    shed = c[2].slider("Load kept when shedding", 0.2, 1.0, 0.5)
    fail = c[3].slider("A cell fails open at hour (0 = none)", 0, 72, 24)
    ff = None if fail == 0 else float(fail)
    pk = real_packs()
    tab = pd.DataFrame({"plain": [min(S.hours(v, 60.0, load, False, cold, ff), 72) for v in pk.values()], "managed": [min(S.hours(v, 60.0, load, True, cold, ff), 72) for v in pk.values()],
                        "managed + load shed": [min(S.hours(v, 60.0, load, True, cold, ff, power_fraction=shed), 72) for v in pk.values()]}, index=list(pk))
    st.bar_chart(tab)
    st.write(f"Median hours over the 12 real packs (72 h outage, 60 kWh, no solar): plain {tab['plain'].median():.1f}, managed {tab['managed'].median():.1f}, managed with load shed {tab['managed + load shed'].median():.1f}.")
    st.caption(f"Effective fade used: {fade:.3f} per year. In the 120-draw stress test, capacity gain beat the best rival 29% of the time below 0.006 a year, 70% at 0.006-0.012, and 88% above 0.012 (hot or heavily cycled sites).")
    st.write("In bypass mode the remaining cells carry n/(n-k) more current: wear x1.06 for 1 of 16 bypassed, x1.28 for 4 (DoD exponent 0.87). Storm days cost cents of pack life; leaving healthy cells bypassed all year does not.")

with t5:
    vm = st.slider("System minimum voltage as a fraction of nominal string voltage (REON's value is UNKNOWN)", 0.60, 0.80, 0.70, 0.05)
    out = []
    for curve in V.CURVES:
        gi, gf = [], []
        for cap in real_packs().values():
            p, _ = V.run(cap, curve, "plain", vm); i, _ = V.run(cap, curve, "ideal", vm); f, _ = V.run(cap, curve, "floor", vm)
            gi.append(i / p - 1); gf.append(f / p - 1)
        out.append({"curve": curve, "ideal gain %": 100 * np.median(gi), "gain with voltage floor %": 100 * np.median(gf)})
    st.dataframe(pd.DataFrame(out).round(1).set_index("curve"))
    st.write("Cells can only be bypassed while the string stays above the system minimum; sloping sodium curves lose the most. Curve shapes are ASSUMED inside a sourced voltage window.")

with t6:
    st.markdown(open("docs/SOURCES.md").read())

with t7:
    st.write("Rule, then money, then rank: for each cell of a plain string, what bypassing it would be worth per year, and what the response layer would do with it.")
    packs = real_packs()
    car = st.selectbox("Real car pack (Nature Energy 2026, 95 cells; first 16 shown as one string)", list(packs))
    v7 = st.slider("Value per kWh-year", 5.0, 100.0, 40.0, key="v7")
    rows = RK.rank_cells(packs[car][:16], 60.0, v7)
    st.dataframe(pd.DataFrame(rows).round(2).set_index("cell"))
    st.caption("Negative dollars: bypassing a healthy cell loses more than it gains. Responses come from reon_response.decide; hardware keeps safety authority.")

with t8:
    st.write("Where the extra money comes from, automatic bypass minus replace-on-failure, per kWh nameplate. Presets are assumptions, tagged in docs/SOURCES.md.")
    name = st.selectbox("Site", list(PR.PRESETS))
    base = PR.PRESETS[name]
    c = st.columns(4)
    fade8 = c[0].select_slider("Cell fade per year", [0.004, 0.008, 0.012, 0.02], base["fade"], key="f8")
    lam8 = c[1].select_slider("Faults per cell-year", [0.001, 0.003, 0.01, 0.03], base["lam"], key="l8")
    visit8 = c[2].select_slider("Crew visit cost", [250, 500, 1000, 3000, 6000], int(base["visit_cost"]), key="v8")
    dc8 = c[3].select_slider("Cost per month down (assumed)", [0, 5, 20, 60], int(base["down_cost"]), key="d8")
    kw8 = dict(base, fade=fade8, lam=lam8, visit_cost=float(visit8), down_cost=float(dc8))

    @st.cache_data(show_spinner=False)
    def streams(items):
        return E.value_streams(**dict(items))

    @st.cache_data(show_spinner=False)
    def fault_breakeven(items):
        return E.break_even("lam", 0.0, 0.1, **dict(items))

    vs = streams(tuple(sorted(kw8.items())))
    st.bar_chart(pd.DataFrame({"per kWh nameplate": [vs["spread"], vs["faults"], vs["crew"], vs["downtime"]]}, index=["capacity and switch cost", "dead cells kept working", "crew visits avoided", "downtime avoided"]))
    st.metric("Total gain over replace-on-failure", f"{vs['total']:+.1f} per kWh", help=f"best automatic variant: {vs['variant']}")
    lb, ld = fault_breakeven(tuple(sorted(kw8.items())))
    st.write("Fault rate at which automatic bypass starts to pay at this site: " + (f"{lb:.4f} per cell-year (about {100*(1-(1-lb)**16):.0f}% of 16-cell strings a year)" if lb is not None and ld == "above" else ("it pays at any fault rate here" if ld == "always a" else "it does not pay at any fault rate up to 0.1 here")) + ". The fault rate is the number to ask REON for.")
    st.caption("At slow fade the capacity stream is near zero or negative: the case rests on faults, crew visits and downtime, and the downtime cost is assumed.")
