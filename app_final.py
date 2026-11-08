"""REON decision layer: dashboard v1 (replays and simulations only; no live hardware link). Run: streamlit run app_final.py
Front page: customer view (storm night, years, dollars, environmental value). Engineering and evidence tabs sit behind it.
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
from hackkit import reon_reliability as RL
from hackkit import reon_balance as BAL
from hackkit import reon_ladder as LAD
from hackkit import reon_system as SYS
from hackkit import reon_storefront as SF
from hackkit import reon_policy as POL
from hackkit import reon_enviro as EN
from hackkit import reon_secondlife as SL
from hackkit import reon_grid as GR
from hackkit import reon_visuals as VZ
from hackkit import reon_slope as SLP
from hackkit import reon_map as MP
from hackkit import reon_demo as DM
from hackkit import reon_twin as TWN
from hackkit import reon_twin_ui as TWU

st.set_page_config(page_title="REON decision layer", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp, .stApp p, .stApp div, .stApp label, .stApp li, .stApp a, .stApp button, .stApp input, .stApp textarea, .stApp select, .stApp span:not([data-testid="stIconMaterial"]) { font-family: 'Figtree', -apple-system, sans-serif !important; }
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu { display: none !important; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }
h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.03em; line-height: 1.08; color: #12161c; }
[data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -0.02em; color: #17324f; }
[data-testid="stMetricLabel"] p { font-size: 0.78rem; letter-spacing: 0.06em; text-transform: uppercase; color: #5b6472; font-weight: 700; }
[data-testid="stCaptionContainer"] { color: #5b6472; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #e3e7ee; }
.stTabs [data-baseweb="tab"] { font-weight: 700; color: #5b6472; font-size: 1.02rem; padding: 10px 14px; }
.stTabs [aria-selected="true"] { color: #12161c; }
[data-testid="stAlert"] { border-radius: 16px; border: 1px solid #e3e7ee; background: #e8eff8 !important; color: #17324f !important; }
[data-testid="stAlert"] * { color: #17324f !important; }
.rn-eyebrow { font-size: 13px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #5b6472; margin: 0 0 6px; }
.rn-h1 { font-size: 46px; font-weight: 800; letter-spacing: -0.035em; line-height: 1.04; color: #12161c; margin: 0 0 8px; }
.rn-sub { font-size: 19px; color: #5b6472; margin: 0 0 18px; max-width: 760px; line-height: 1.4; }
.rn-q { font-size: 15px; font-weight: 700; color: #12161c; margin: 8px 0 2px; }
.rn-q span { display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; border-radius: 12px; background: #17324f; color: #fff; font-size: 13px; margin-right: 8px; }
.rn-verdict { border-radius: 24px; padding: 28px 34px; margin: 18px 0 8px; }
.rn-buy { background: #17324f; color: #fff; }
.rn-bal { background: #e8eff8; color: #17324f; border: 1px solid #d3e0f1; }
.rn-hold { background: #f4f6fa; color: #12161c; border: 1px solid #e3e7ee; }
.rn-verdict .rn-eyebrow { color: inherit; opacity: .7; }
.rn-vt { font-size: 44px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.05; margin: 0 0 6px; }
.rn-buy .rn-vt { color: #ffc857; }
.rn-vl { font-size: 19px; line-height: 1.4; max-width: 900px; margin: 0 0 18px; }
.rn-nums { display: flex; gap: 40px; flex-wrap: wrap; }
.rn-nums b { display: block; font-size: 34px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
.rn-nums i { display: block; font-style: normal; font-size: 13px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .7; margin-top: 2px; }
.rn-ans { background: #f4f6fa; border: 1px solid #e3e7ee; border-radius: 18px; padding: 18px 24px; font-size: 18px; line-height: 1.5; color: #12161c; margin-top: 10px; }
.rn-sec { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; margin: 30px 0 4px; color: #12161c; }
.rn-note { font-size: 15px; color: #5b6472; line-height: 1.5; }
</style>""", unsafe_allow_html=True)
st.html('<p class="rn-eyebrow">REON decision layer · MIT Energy &amp; Climate Hack 2026</p><h1 class="rn-h1">Should this store get cell-level switches?</h1>'
        '<p class="rn-sub">Answer three questions. We give a recommendation, then test it on a storm night. Everything is a simulation on assumed sodium-ion behaviour, not REON data.</p>')


@st.cache_data
def real_packs():
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    car = {}
    for p, _, _, late in rows:
        car.setdefault(p, []).append(float(late))
    return {k: np.array(v) for k, v in car.items()}


BE = pd.DataFrame({"fade spread 0.20": [16.2, 27.3, 45.7, None], "0.45": [25.4, 42.9, None, None], "0.60": [29.1, 49.4, None, None]}, index=["value 12", "value 22", "value 40", "value 80"])
demo, twin_tab, details = st.tabs(["Ask", "3D Twin", "Details and evidence"])
with details:
    front, trend_tab, eng_wrap = st.tabs(["Customer view", "Cell trends", "Engineering and evidence"])
@st.cache_data
def storm_demo(fail_h):
    return DM.storm(real_packs(), fail_h)


def _twin_pick():
    c = TWU.last_pick("twin3d")
    if c is not None:
        st.session_state["tfail"] = TWN.toggle(st.session_state.get("tfail", []), c)


with twin_tab:
    st.markdown("**A twin of one store's battery, and the decision layer behind it.** 250 cells in series, drawn from the real spread of late-life cells. Click a cell to fail it, turn the view, and compare a plain string with cell-level control. "
                "A twin shows the pack; the Ask tab says whether to build the switches. Every number here comes from the same decision engine. Simulation on assumed sodium-ion behaviour, not REON data.")
    ts = st.session_state
    ts.setdefault("tfail", [])
    tc = st.columns([1.5, 1.2, 0.8, 0.8])
    t_win = tc[0].select_slider("Share of cells that must stay in the string (REON: about 90%)", [0.5, 0.7, 0.9], 0.9, key="t_win")
    t_load = tc[1].slider("Load (kW)", 1.0, 10.0, 5.0, key="t_load")
    h_t = GR.make_string(GR.pooled_relative(real_packs()))
    if tc[2].button("Fail a random cell", key="t_rand"):
        live_t = [i for i in range(len(h_t)) if i not in ts.tfail]
        ts.tfail = TWN.toggle(ts.tfail, int(np.random.default_rng(len(ts.tfail) + 7).choice(live_t)))
    if tc[3].button("Reset", key="t_reset"):
        ts.tfail = []
    an_t = GR.analyse(h_t, ts.tfail, t_win, 60.0, 0.04, t_load)
    TWU.mount(TWN.payload(h_t, an_t, t_load), key="twin3d", on_pick=_twin_pick)
    tm = st.columns(4)
    tm[0].metric("Plain string", f"{an_t['plain_kwh']:.0f} kWh", f"{an_t['plain_h']:.1f} h at {t_load:.0f} kW", delta_color="off")
    tm[1].metric("With cell-level control", f"{an_t['ours_kwh']:.0f} kWh", f"{an_t['ours_h']:.1f} h at {t_load:.0f} kW", delta_color="off")
    tm[2].metric("Cells that can still leave", f"{max(an_t['room'], 0)} of {an_t['K']}")
    tm[3].metric("Cells failed", f"{an_t['failed']}")
    st.caption("Red plane: what a plain string can use (its weakest cell; nothing with any open cell). Amber plane: with control, the weakest cells may leave early, so the usable level is higher. "
               "Switch loss 4% and the inverter minimum voltage are assumed (REON: about 90% of cells connected). REON's hardware keeps safety authority.")


with demo:
    def _pick(label, n, fmt, default, key, num):
        st.html(f'<p class="rn-q"><span>{num}</span>{label}</p>')
        v = st.segmented_control(label, list(range(n)), default=default, format_func=fmt, key=key, label_visibility="collapsed")
        return default if v is None else v

    wear_i = _pick("How fast do this store's cells wear?", len(DM.WEAR), lambda i: f"{DM.WEAR[i][0]} · {DM.WEAR[i][1] * 100:.1f}% a year", 1, "d_wear", 1)
    wire_i = _pick("How are the cells wired?", len(DM.WIRING), lambda i: DM.WIRING[i][0], 0, "d_wire", 2)
    val_i = _pick("What is backup worth to the owner, per kWh per year?", len(DM.VALUES), lambda i: DM.VALUES[i][1], 2, "d_val", 3)
    case_d = SF.cached_core(DM.WIRING[wire_i][1], DM.WEAR[wear_i][1], DM.VALUES[val_i][0])
    card = DM.verdict_card(case_d)
    if card is None:
        st.info("No precomputed result for this combination.")
    else:
        kind = card["kind"]
        cls, head = {"BUY": ("rn-buy", "Build the switches."), "BALANCER": ("rn-bal", "A simple balancer is enough."), "HOLD": ("rn-hold", "Keep the plain string.")}[kind]
        nums = []
        if kind == "BUY":
            nums = [(f"${card['dollars']:,.0f}", "12-year value"), (f"${card['vs_balancer']:,.0f}", "beyond a balancer"),
                    (f"{card['life_plain']:.0f} → {card['life_ours']:.0f} years", "battery life"), (f"{card['carbon_t']:.1f} t CO2e" if card["carbon_t"] else "none claimed", "carbon avoided")]
        elif kind == "BALANCER":
            nums = [(f"${card['balancer']:,.0f}", "a balancer earns over 12 years"), ("under $1 a kWh", "what switches would add")]
        st.html(f'<div class="rn-verdict {cls}"><p class="rn-eyebrow">Our answer for this store</p><p class="rn-vt">{head}</p><p class="rn-vl">{card["line"]}</p>'
                + ('<div class="rn-nums">' + "".join(f"<div><b>{a}</b><i>{b}</i></div>" for a, b in nums) + "</div>" if nums else "") + "</div>")

        st.html('<p class="rn-sec">Now a storm night</p><p class="rn-note">60 kWh store, 5 kW load, power out for 24 hours. What happens if one cell opens?</p>')
        fail_v = st.segmented_control("Cell failure", [0, 3, 6, 9], default=0, format_func=lambda h: "No failure" if h == 0 else f"A cell opens at hour {h}", key="d_failh", label_visibility="collapsed") or 0
        failed = fail_v > 0
        fail_h = fail_v if failed else 6
        sm = storm_demo(fail_h)
        if failed:
            rows = [("Plain string", sm["plain_fail"]), ("Plain string + simple balancer", sm["plain_fail"]), ("Cell-level control", sm["ours_fail"]), ("Cell-level control, shedding half the load", sm["shed_fail"])]
            plain_h, ours_h, shed_h = sm["plain_fail"], sm["ours_fail"], sm["shed_fail"]
            st.caption("A dead cell breaks a plain string: no current flows. A balancer cannot move charge through a dead cell either. Cell-level control bypasses it and keeps going.")
        else:
            rows = [("Plain string", sm["plain"]), ("Cell-level control", sm["ours"]), ("Cell-level control, shedding half the load", sm["shed"])]
            plain_h, ours_h, shed_h = sm["plain"], sm["ours"], sm["shed"]
            st.caption("With no failure the runs look alike. Pick a failure hour.")
        st.altair_chart(VZ.storm_timeline(rows, 24.0, fail_h if failed else None), use_container_width=True)
        m = st.columns(3)
        m[0].metric("Plain string", f"{plain_h:.1f} h of lights")
        m[1].metric("Cell-level control", f"{ours_h:.1f} h of lights", f"{ours_h - plain_h:+.1f} h", delta_color="normal")
        m[2].metric("Control, shedding half the load", f"{shed_h:.1f} h of lights", f"{shed_h - plain_h:+.1f} h", delta_color="normal")

    st.html('<p class="rn-sec">Ask us</p><p class="rn-note">Tap a question. Every answer is computed from the model, not written by a chatbot.</p>')
    QS = ["What happens if a cell dies mid-storm?", "When is a simple balancer enough?", "How do we know the policy is safe?", "What have we not tested?", "What do we need from REON?", "Can I see it in 3D?"]
    q = st.pills("Ask us", QS, selection_mode="single", key="d_q", label_visibility="collapsed")
    ans = None
    if q == QS[0]:
        s6 = storm_demo(6)
        ans = (f"A plain string goes dark the moment the cell opens: {s6['plain_fail']:.1f} hours of lights. A balancer cannot help, because it cannot move charge through a dead cell. "
               f"Cell-level control bypasses the cell and keeps {s6['ours_fail']:.1f} hours, or {s6['shed_fail']:.1f} hours if the store sheds half its load. (Failure at hour 6, 5 kW, 12 real car packs.)")
    elif q == QS[1]:
        def vc(w, wv, v):
            return DM.verdict_card(SF.cached_core(w, wv, v))
        a1, a2, a3, a4 = vc(1, 0.004, 40), vc(1, 0.008, 12), vc(16, 0.008, 40), vc(1, 0.012, 40)
        parts = []
        if a1 and a2 and a3:
            parts.append(f"When cells wear slowly, backup is worth little, or cells sit in parallel groups. At the maker's claim a balancer earns ${a1['balancer']:,.0f} and we add under $1 a kWh; at typical wear and $12 a kWh it earns ${a2['balancer']:,.0f}; with 16 cells in parallel, ${a3['balancer']:,.0f}.")
        if a4:
            parts.append(f"The switches start to pay when wear is hard: at 1.2% a year they add about ${a4['vs_balancer']:,.0f} beyond a balancer per store.")
        ans = " ".join(parts) or "No precomputed cases found."
    elif q == QS[2]:
        pr = DM.proof()
        ans = (f"We ran {pr['runs']} stress runs on fresh random draws: random wear, balancer strength, costs and hostile packs. The policy was never behind the better of a plain string or a balancer by more than ${pr['worst_regret']:.2f} a kWh. "
               "REON's hardware keeps safety authority; our layer only recommends.")
    elif q == QS[3]:
        ans = ("Cold nights, slow recovery, faster wear and failures that hit neighbouring cells together are not run yet, so we do not claim them. There is no REON data in the model: sodium-ion behaviour is assumed, and backup hours use 12 real car packs. "
               "Every input is tagged in the sources file.")
    elif q == QS[4]:
        tor = pd.read_csv("examples/data/tornado_250.csv").sort_values("swing", ascending=False).head(3)
        ans = ("Three numbers move the answer most: " + "; ".join(f"{r.input.lower()} ({r.who_can_answer})" for r in tor.itertuples()) + ". Give us those and the assumptions become measurements.")
    elif q == QS[5]:
        ans = "Open the 3D Twin tab at the top. Click a cell to fail it, click again to repair it, and flip between a plain string and cell-level control."
    if ans:
        st.html(f'<div class="rn-ans">{ans}</div>')
    pr0 = DM.proof()
    st.caption(f"Checked against {pr0['runs']} stress runs: never behind a balancer or a plain string by more than ${pr0['worst_regret']:.2f} a kWh. Simulation on assumed sodium-ion behaviour; not REON data. Inputs and limits are under Details and evidence.".replace("$", "\\$"))

with trend_tab:
    st.write("A snapshot ranks cells by where they are today. A trend asks how fast each one is falling, and whether it falls faster than the cells next to it. Real data: the Nature Energy 2026 packs (95 cells each, measured at 80,000 and 280,000 km). Not REON data.")

    @st.cache_data
    def trend_packs():
        return SLP.load_cells()

    tp = trend_packs()
    summ = SLP.snapshot_vs_trend(tp)
    pk = st.selectbox("Pack", list(tp), key="tr_pack")
    e_, l_ = tp[pk]
    f_ = SLP.fade_pp(e_, l_)
    flag_, lm_, sc_ = SLP.outliers(f_)
    wl_ = int(np.argmin(l_))
    row = summ["per_pack"][pk]
    tm = st.columns(4)
    tm[0].metric("Weakest cell at the end", f"cell {wl_}", f"{100*l_[wl_]:.0f}% of day 1", delta_color="off")
    tm[1].metric("Its rank at 80,000 km", f"{row['early_rank_of_final_weakest']} of {row['n']}", "1 = weakest then", delta_color="off")
    tm[2].metric("Steepest fader is that cell", "yes" if row["steepest_is_final_weakest"] else "no")
    tm[3].metric("Fading faster than neighbours", f"{int(flag_.sum())} cell(s)")
    st.altair_chart(VZ.slope_lines_chart(e_, l_, flag_, wl_), use_container_width=True)
    st.caption("Each line is one cell. Red ends weakest; amber fades faster than its neighbours. The lines fan out: where a cell starts says little about where it ends.")
    st.altair_chart(VZ.position_chart(e_, l_, flag_, wl_, lm_), use_container_width=True)
    st.caption("Left to right along the pack. The dashed line is the median of the eight nearest cells. Cells well above it are fading for their own reasons, not because the whole neighbourhood is hot.")
    n_ = summ["packs"]
    st.write(f"**Across all {n_} packs:** the cell that ended weakest was also the weakest at 80,000 km in only {summ['same_weakest']} of {n_}; its median rank then was {summ['median_early_rank']:.0f} of 95. The steepest fader was the final weakest in {summ['steepest_is_final_weakest']} of {n_}. The spread in how much cells fade was larger than the spread in where they started in {summ['fade_spread_larger']} of {n_}.")
    st.caption("What this is and is not: two ages give a slope, not a full curve, and we cannot test a forecast out of sample, so this shows what a snapshot misses and does not predict failures. REON's own per-cell history would give the curve. The grouping by neighbours uses the order the data give; in a real string it would be the wiring order.")

with eng_wrap:
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12 = st.tabs(["1 Is it worth it", "2 Where it flips", "3 Life of the string", "4 Storm", "5 Voltage limit", "6 Evidence and limits", "7 Which cell is hurting", "8 Where the money comes from", "9 System view", "10 Balancing and modules", "11 What to ask REON first", "12 Who buys and how it ships"])

with front:
    st.markdown("One application: a 60 kWh sodium-ion backup battery at a chain store or small commercial site. We add a decision layer on top of REON's per-cell sensing and switches. "
                "The same engine fits any stationary backup customer; only the load, the value of a kWh and the outage length change.")
    sd0 = pd.read_csv("examples/data/eia_reliability_by_state.csv", comment="#").set_index("state")
    ss0 = st.session_state
    ss0.setdefault("map_ver", 0)
    with st.expander("Pick your state on a map (and see where this matters most)"):
        mc = st.columns([3, 2])
        layer = mc[0].radio("Show", list(MP.LAYERS), key="m_layer", horizontal=True, help="Exposure: minutes without power. Coverage: backup hours against the typical outage. Where to pilot: load at risk in dollars.")
        mload = ss0.get("f_load", 5.0)
        voll = mc[1].slider("Value of lost load ($ per kWh)", 0.0, 100.0, MP.VOLL_TEXAS, key="m_voll", help="Only the Texas figure (about 35.7) is sourced; a store's own number can be far lower or higher.") if layer == "Where to pilot" else MP.VOLL_TEXAS

        @st.cache_data
        def eia_tbl():
            return pd.read_csv("examples/data/eia_reliability_by_state.csv", comment="#").set_index("state")

        @st.cache_data
        def backup_h(load):
            return SF.backup_hours(real_packs(), 60.0, load)[1]

        mf = MP.tile_frame(eia_tbl(), layer, backup_h(float(mload)), float(mload), float(voll))
        try:
            clicked = MP.clicked_state(ss0.get(f"mapchart{ss0.map_ver}").selection)
        except Exception:
            clicked = None
        if clicked:
            ss0["f_state"] = clicked
            ss0.map_ver += 1
        mtitle = {"Exposure": "Minutes without power, 2025", "Coverage": "Backup hours / typical outage", "Where to pilot": "$ of load at risk per store-year"}[layer]
        st.altair_chart(VZ.tile_map_chart(mf, ss0.get("f_state"), mtitle, ",.1f" if layer == "Coverage" else ",.0f"), on_select="rerun", key=f"mapchart{ss0.map_ver}", use_container_width=False)
        st.caption("Click a tile to set your state below. State averages from the utilities' reports (EIA-861), not a store's own outage record. "
                      + ("Coverage uses your load setting and the cell-level backup hours." if layer == "Coverage" else "")
                      + (" Load at risk = hours without power x your load x the value above; one sourced anchor (Texas), the rest is your call." if layer == "Where to pilot" else ""))
    ctrl, res = st.columns([1, 2.6], gap="large")
    with ctrl:
        st.markdown("**Your site**")
        state0 = st.selectbox("State", list(sd0.index), index=list(sd0.index).index("California"), key="f_state")
        load0 = st.slider("Critical load during an outage (kW)", 1.0, 10.0, 5.0, key="f_load")
        kind0 = st.radio("What is one position in the string?", ["One large cell", "4 cells in parallel", "16 cells in parallel"], key="f_kind", help="REON has not said which. The answer changes the result (see engineering tab 9).")
        hard0 = st.radio("How hard is the battery used?", ["Gentle (maker's 20,000-cycle claim)", "Typical", "Hot or hard"], index=1, key="f_hard")
        val0 = st.select_slider("What a kWh of battery earns per year ($)", [12, 22, 40, 80], 40, key="f_val", help="12 grid services, 22 EV, 40 to 80 sites that pay demand charges")
    p0 = {"One large cell": 1, "4 cells in parallel": 4, "16 cells in parallel": 16}[kind0]
    fade0 = {"Gentle (maker's 20,000-cycle claim)": 0.004, "Typical": 0.008, "Hot or hard": 0.02}[hard0]

    @st.cache_data(show_spinner="Not precomputed: simulating a 250-cell string (about 15 seconds)")
    def sf_run(p, fade, value):
        return SF.storefront(p, fade, float(value), 15.5, real_packs())

    r0 = dict(sf_run(p0, fade0, val0))
    r0["backup_plain_h"], r0["backup_managed_h"] = SF.backup_hours(real_packs(), 60.0, load0)
    r0["load_kw"] = load0
    ci = float(sd0.loc[state0, "caidi_major_2025"]) / 60.0
    pp, pm, ps = SF.backup_policies(real_packs(), 60.0, load0)
    with res:
        st.subheader({"BUY": "Worth it", "BALANCER": "A simple balancer is enough here"}.get(r0["verdict"], "Not worth it here"))
        (st.success if r0["verdict"] == "BUY" else st.warning)(SF.headline(r0, state0, ci).replace("$", "\\$"))
        m = st.columns(3)
        m[0].metric("Backup on a storm night", f"{r0['backup_managed_h']:.1f} h", f"{r0['backup_managed_h'] - r0['backup_plain_h']:+.1f} h vs a plain string")
        m[1].metric("Battery life", f"{r0['life_ours']:.0f} years" if r0["verdict"] == "BUY" else f"{r0['life_plain']:.0f} years", f"{r0['life_ours'] - r0['life_plain']:+.0f} years vs plain" if r0["verdict"] == "BUY" else None)
        m[2].metric("Worth over the first 12 years", f"${r0['dollars_total']:,.0f}" if r0["verdict"] == "BUY" else "$0", f"pessimistic ${r0['p10_total']:,.0f}; ${r0['vs_balancer_total']:,.0f} over a balancer alone" if r0["verdict"] == "BUY" else None)
        st.markdown("**Same battery, three ways to run it**")
        st.altair_chart(VZ.policies_chart(pp, pm, ps), use_container_width=True)
        if r0["verdict"] == "BUY" and r0["life_ours"] > r0["life_plain"]:
            st.markdown("**Environmental value**")
            H0 = st.select_slider("Years of service counted", [10, 15, 20, 25, 30], 20, key="f_h")
            e0 = EN.environmental(60.0, r0["life_plain"], r0["life_ours"], H0)
            k = st.columns(3)
            k[0].metric("Battery cells not manufactured", f"{e0['kwh_cells_avoided']:.0f} kWh", help="over the horizon, because the string lasts longer")
            k[1].metric("Battery material not made", f"about {e0['material_kg']:,.0f} kg", help="assumes 10 kg of battery per kWh of cells: a placeholder until REON gives pack mass")
            k[2].metric("Manufacturing carbon avoided, net", f"{e0['net_t']:.1f} t CO2e", f"range {round(e0['low_t'], 1) + 0.0:.1f} to {e0['high_t']:.1f} t")
        else:
            e0 = None
    with st.expander("How to read this page"):
        st.markdown(f"**Backup hours.** Median over 12 real car packs (Nature Energy 2026) at {load0:.0f} kW, cold-weather capacity 80%. Switching adds a modest amount of hours on day one; the payoff is life and money. "
                    "A plain string with one open cell delivers nothing; cell-level control bypasses it. In the third bar the site sheds half the load (it chooses which loads count as life-safety).")
        st.markdown(f"**Outages in {state0}.** A typical customer lost power {sd0.loc[state0, 'saidi_major_2025']:.0f} minutes in 2025 across {sd0.loc[state0, 'saifi_major_2025']:.1f} interruptions (EIA-861, utility-wide averages; one store can be far worse).")
        if e0:
            st.markdown("**Carbon.** Sodium-ion pack 56.8 kg CO2e/kWh (EIA Review study via ess-news.com); Fraunhofer/RWTH cell-level 75 to 87 for sodium-ion. Those figures ignore cycle life, which we supply. "
                        "Two inputs are assumed and shown as a range: how many avoided cells would really have been replaced (50 to 100%) and the carbon of REON's electronics (1 to 10 kg per kWh, counted in full). "
                        + ("The sign of the result does not flip inside these ranges." if not e0["sign_can_flip"] else "At the low end this is close to zero: the sign can flip, so treat the carbon claim as small here."))
        st.markdown("**Where the numbers are counted.** Energy and hours are measured at the battery string's DC terminals: usable kWh (cell capacities, 80% in the cold, a small switch loss) divided by the load you set. No inverter loss and no solar. Power capability in kW is not modelled; the only kW is your load.")
        st.markdown("**Voltage limit.** Every build in the dollar and life figures keeps at least 90% of the 250 cells in the string at all times (about 90% is the CTO's unclear remark; REON's real inverter minimum is not known), which caps bypassing at 25 cells. "
                    "An earlier version had no cap and read \\$1,635 for the typical case; with the cap, the switch loss below and the balancer comparison it reads about \\$1,500 over a plain string (60 kWh), of which about \\$190 is above what a simple balancer alone would earn. "
                    "Counting cells is only a first-order stand-in for volts: it ignores that cell voltage sags toward the end of a discharge. In our voltage check on 12 real packs, the median energy gain at a 90% floor fell from 4.3% (cell count) to 0.0% (with sag). Treat the dollar figures as an upper bound until REON gives the inverter's minimum voltage.")
        st.markdown("**Switch loss.** A plain string has no switches; a switched string pays a small loss on every kWh that passes through its closed switches. We charge 2% (assumed) on all energy of the switched string, not only on the extra energy it recovers, and both strings are measured at the same point, the string's DC terminals. Otherwise the switched string would look better for free.")
        st.markdown("**Where it comes from.** Every input is tagged in docs/SOURCES.md. Sodium-ion cell behaviour is assumed; there is no live REON data in this yet.")
    with st.expander("What would have to be true: gain against how fast the cells wear"):
        vsel = st.select_slider("Value of a kWh of backup per year ($)", [12, 22, 40, 80], 40, key="f_gv")
        grows = SF.gain_vs_fade(vsel)
        if grows:
            st.altair_chart(VZ.gain_fade_chart(grows), use_container_width=True)
            st.caption("The height is the EXTRA 12-year gain our recommended build earns over the better of a simple 5% balancer or doing nothing. Each line is one way of wiring cells in parallel. A cross on the zero line means a balancer is enough (or nothing pays) and we would not sell the switches. "
                       "Read it from the right: the faster the cells wear, the more cell-level control is worth beyond a balancer, and the more cells share a position, the more wear it takes before it pays. "
                       "The maker's claim is the far left, where a balancer is enough. Steps in the lines come from replacement dates. Simulated at 250 cells, switch cost 15.5 per kWh (the extra over a conventional BMS), at least 90% of cells kept in the string, 2% switch loss on all energy; not REON data.")
        else:
            st.info("No precomputed cases found for this value.")
    with st.expander("Against a simple balancer: how strong would it have to be?"):
        bc = st.columns(2)
        bp = bc[0].select_slider("Cells in parallel per position", [1, 4, 16], 1, key="f_bp")
        bf = bc[1].select_slider("Cell fade per year", [0.004, 0.008, 0.02], 0.008, key="f_bf", format_func=lambda v: f"{v:.3f}")
        brows = SF.balancer_rows(bp, bf)
        if brows:
            st.altair_chart(VZ.balancer_chart(brows), use_container_width=True)
            bx = SF.balancer_crossover(brows)
            if bx is None:
                bt = "REON switches alone beat a balancer of every strength we tried (up to 15% of a cell's capacity per cycle)."
            elif bx == 0.0:
                bt = "A balancer beats REON switches alone at every strength we tried, even 1%."
            else:
                bt = f"A balancer that can move about {bx * 100:.1f}% of a cell's capacity per cycle already matches REON switches alone. We assumed 5%, which is not sourced."
            st.markdown(bt.replace("$", "\\$"))
            st.caption("An active balancer moves charge between cells instead of switching a cell out. The black line is what we would recommend: our build only when it beats the better of the balancer and doing nothing by at least 1 per kWh on two independent random draws, otherwise the balancer itself, so it never sits below the balancer line. "
                       "Switches alone pay at fast wear or when a cell fails outright; at slow wear a balancer does most of the work. Our hybrid (a few switches on the weakest cells, or a switch on every cell, plus the balancer) keeps the balancer's gain and adds the tail the balancer cannot reach. "
                       "Simulated at 250 cells, value 40 per kWh-year, switch cost 15.5 and balancer cost 4 per kWh, 90% voltage window, 2% switch loss on all energy. REON's actual balancing strength is not known (top question for REON).")
        else:
            st.info("No precomputed balancer cases for this choice.")
    with st.expander("What we are not doing"):
        st.markdown("- We are not changing REON's hardware. We add the decision layer: which cell to switch out, when to bypass, when to call a crew. REON's hardware keeps safety authority.\n"
                    "- We are not claiming this for homes, EVs or scooters; the numbers are for a commercial backup battery.\n"
                    "- We are not claiming a grid-emissions saving. The carbon figure is manufacturing only.\n"
                    "- Everything here is a simulation or a replay on assumed sodium-ion behaviour; there is no live REON data in it yet. Cell fade, fault rates and switch cost are assumptions or REON statements, tagged in the evidence tab.\n"
                    "- We do not count benefits beyond the 12-year bankable horizon in the dollar figure. Life beyond that is a projection.")

with t1:
    c = st.columns(5)
    fade25 = c[4].slider("Cell fade per year at 25 C (20,000-cycle claim = 0.004 at one cycle a day; lithium EVs about 0.02)", 0.003, 0.04, 0.008, format="%.3f")
    temp = c[4].slider("Average cell temperature, C (ageing about doubles per 10 C, assumed)", 15, 45, 25)
    fade = fade25 * 2.0 ** ((temp - 25) / 10.0)
    value = c[0].slider("Value per kWh-year (12 grid, 22 EV, 30-90 demand-charge sites)", 5.0, 100.0, 40.0)
    fcv = c[1].slider("Spread of fade rates between cells (real cars 0.20-0.60)", 0.05, 0.8, 0.45)
    elec = c[2].slider("Switch cost per kWh nameplate (Tim Ren: 7-24)", 2.0, 40.0, 15.5)
    loss = c[3].slider("Usable-energy loss: switches + voltage floor", 0.0, 0.10, 0.04)
    st.caption("Tim Ren, 8 Nov: the 7 to 24 per kWh is already the cost over a conventional BMS (it depends on how many PCBs are made), so it is used as the extra cost, not reduced again.")
    g = st.columns(2)
    n1 = g[0].select_slider("Cells in series (Tim Ren: 200 to 300; 16 is the quick demo size)", [16, 250], 250, key="n1")
    p1 = g[1].select_slider("Cells in parallel per position (unknown: ask REON)", [1, 4, 16, 40], 1, key="p1")

    @st.cache_data(show_spinner="Running the engine (about 15 seconds at 250 cells)")
    def eng1(n, p, value, elec, fcv, loss, fade):
        rng = np.random.default_rng(3)
        start = 100.0 * (1.0 + 0.02 / np.sqrt(p) * rng.standard_normal(n))
        kw = dict(value_per_kwh_year=float(value), electronics_per_kwh=float(elec), fade_cv=fcv / np.sqrt(p), loss=loss, fade_mean=fade, ks=tuple(k for k in (1, 2, 4, 8, 16, 25) if k < n) or (1,), window=SF.WINDOW, closed_loss=SF.CLOSED_LOSS)
        if n >= 100:
            kw.update(trials=8, steps=60)
        rb = POL.robust_guarded(start, n, **kw)
        return rb, dict(table=rb["table"], build=rb["build"], ours_best=rb["build"], rival_best=rb["rival"], margin=rb["margin_vs_rival"])

    sig1 = (n1, p1, value, elec, fcv, loss, fade)
    if n1 <= 16 or st.button("Run the engine with these settings (about 15 seconds at 250 cells)", key="run1"):
        st.session_state["res1"] = (sig1,) + tuple(eng1(*sig1))
    res1 = st.session_state.get("res1")
    if res1 is None or res1[0] != sig1:
        st.info("Press the button to run the engine with these settings. The Customer view tab already shows precomputed results for the standard 250-cell cases.")
    if res1 is not None and res1[0] == sig1:
        rob, out = res1[1], res1[2]
        (st.success if rob["verdict"] == "BUY" else st.warning)(f"Verdict on a fresh seed: {rob['verdict']} ({rob['build']}). " + "; ".join(rob["reasons"]))
        for w in rob["warnings"]:
            st.caption(f"Note: {w}")
        t = out["table"]
        m = st.columns(4)
        m[0].metric("Recommended build", out["build"])
        m[1].metric("Net value vs plain string", f"{rob['mean_gain']:+.1f} per kWh", help=f"scored on an independent seed, the number the customer view uses. The table below is the seed the build was picked on and reads higher ({t[out['ours_best']]['mean']:+.1f}): picking the best of several always flatters it.")
        m[2].metric("Margin over best rival", f"{out['margin']:+.1f}", help=f"best rival: {out['rival_best']}")
        m[3].metric("Service life (30-year run)", f"{rob['life_ours']:.1f} y vs {rob['life_plain']:.1f} y plain")
        if out["margin"] <= 0:
            st.warning(f"No-go: at these inputs {out['rival_best']} is at least as good as switches, or the edge is under 1 per kWh. Do not buy switches here: use the {out['rival_best']}.")
        else:
            st.success(f"Go: our build beats the best alternative ({out['rival_best']}) by {out['margin']:.1f} per kWh at these inputs.")
        st.dataframe(pd.DataFrame({k: {"net value per kWh": v["mean"], "10th percentile": v["p10"], "service years": v["years"], "cost": v["cost"]} for k, v in t.items()}).T.round(1))
    st.caption("Plain string = the brief's baseline. Balancer rival: 5 % transfer, cost 4. Start spread 2 % (divided by the square root of cells in parallel), 12 years, retire at 70 %. The customer view uses the same engine. Stress tests: examples/reon_hero_stress_output.txt.")

with t2:
    st.subheader("Break-even switch cost against a typical balancer (per kWh nameplate)")
    st.dataframe(BE.fillna(">60 (never flips)").astype(str))
    st.caption("This table was computed before the voltage window was enforced in the engine (see docs/SOURCES.md); treat the break-even costs as the optimistic end.")
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
    st.write("In bypass mode the remaining cells carry n/(n-k) more current: wear x1.06 for 1 of 16 bypassed, x1.28 for 4 (DoD exponent 0.87). Storm days cost cents of pack life; leaving healthy cells bypassed all year does not.")
    sd = pd.read_csv("examples/data/eia_reliability_by_state.csv", comment="#").set_index("state")
    stt = st.selectbox("State (EIA-861 reliability, 2025 and 2024)", list(sd.index), index=list(sd.index).index("California"))
    r = sd.loc[stt]
    st.write(f"{stt}: a typical customer lost power {r.saidi_no_major_2025:.0f} min in 2025 without major events and {r.saidi_major_2025:.0f} min with them ({r.saidi_major_2024:.0f} in 2024), over {r.saifi_major_2025:.1f} interruptions; one interruption lasted about {r.caidi_major_2025/60:.1f} h on average ({r.caidi_major_2024/60:.1f} h in 2024). "
             f"The managed pack above lasts {tab['managed'].median():.1f} h at this load. Real data, tagged REAL in docs/SOURCES.md; they are utility-wide averages, a single store can be far worse.")

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

with t9:
    st.write("System level, the way Tim Ren frames it: how many charges does the whole string last, and how likely is it to survive? Life is cell-limited here (30-year horizon, retire at 70% of day-1); the bankable value in tab 1 stops at 12 years.")
    c = st.columns(5)
    n9 = c[0].select_slider("Cells in series per string", [16, 48, 112, 250], 250, key="n9")
    p9 = c[1].select_slider("Cells in parallel per series element (unknown: ask REON)", [1, 4, 16, 40], 1, key="p9")
    f9 = c[2].select_slider("Fade per year at 25 C", [0.004, 0.008, 0.012, 0.02], 0.008, key="f9")
    v9 = c[3].select_slider("Value per kWh-year", [12, 22, 40, 80], 40, key="v9")
    e9 = c[4].select_slider("Switch cost per kWh", [7.0, 11.0, 15.5, 24.0], 15.5, key="e9")

    @st.cache_data(show_spinner="Running the engine")
    def rec9(n, p, f, v, e):
        rng9 = np.random.default_rng(3)
        start = 100.0 * (1.0 + 0.02 / np.sqrt(p) * rng9.standard_normal(n))
        ks = tuple(k for k in (1, 2, 4, 8, 16, 25) if k < n) or (1,)
        out, _ = G.safe_recommend(start, n, value_per_kwh_year=float(v), electronics_per_kwh=float(e), fade_cv=0.45 / np.sqrt(p), fade_mean=float(f), loss=0.04, years=30.0, eol_frac=0.7, trials=8, steps=60, ks=ks, window=SF.WINDOW, closed_loss=SF.CLOSED_LOSS)
        return out

    sig9 = (n9, p9, f9, v9, e9)
    if st.button("Run the system view (about 12 seconds at 250 cells)", key="run9"):
        st.session_state["res9"] = (sig9, rec9(*sig9))
    res9 = st.session_state.get("res9")
    if res9 is None or res9[0] != sig9:
        st.info("Press the button to run the engine with these settings.")
    if res9 is not None and res9[0] == sig9:
        o9 = res9[1]
        sv = SYS.system_view(o9["table"])
        names = ["plain", o9["ours_best"], o9["rival_best"]]
        rows = [{"build": nm, "service life (y)": sv[nm]["years"], "system cycles": sv[nm]["system_cycles"], "share of the 20,000-cycle cell rating": sv[nm]["share_of_cell_rating"], "lifetime kWh per kWh nameplate": sv[nm]["lifetime_kwh_per_kwh_nameplate"],
                 "cost per kWh delivered": sv[nm]["cost_per_kwh_delivered"]} for nm in dict.fromkeys(names)]
        st.dataframe(pd.DataFrame(rows).round(2).set_index("build"))
        st.caption("System cycles at one cycle a day. Warranty standard 10 years / 8,000 cycles (Tim Ren). Cost per kWh delivered uses an assumed 98 per kWh cell cost plus the build's electronics. Life stops at 30 years in this view.")
    d = st.columns(3)
    lam9 = d[0].select_slider("Faults per cell-year (assumed; ask REON)", [0.0005, 0.001, 0.002, 0.005, 0.01], 0.002, key="lam9")
    yr9 = d[1].select_slider("Years", [5, 10, 15, 20], 10, key="yr9")
    vm9 = d[2].select_slider("Lowest string voltage the inverter accepts (share of full)", [0.7, 0.8, 0.9], 0.9, key="vm9")
    pc = RL.p_from_rate(lam9, yr9)
    kcap = RL.bypass_cap(n9, vm9)
    ks9 = list(range(0, max(kcap, 1) + 1))
    surv = pd.DataFrame({"chance the string survives": [RL.survival(n9, pc, k) for k in ks9]}, index=ks9)
    st.line_chart(surv)
    st.write(f"Each cell fails over {yr9} years with probability {100*pc:.1f}%. A plain string of {n9} cells survives {100*RL.survival(n9, pc, 0):.1f}% of the time. Tolerating {kcap} dead cells (the voltage limit) it survives {100*RL.survival(n9, pc, kcap):.2f}%. "
             f"Each cell would need {100*RL.required_cell_survival(n9, 0.99):.4f}% survival for a plain string to reach 99%. Independent failures assumed; bypass does not fix a short or a thermal event, and REON's hardware keeps safety authority.")

with t10:
    st.write("Why not just balance? Passive balancers move about 0.25 A and only waste energy as heat; active balancers move 0.5 to 6 A. Keeping one weak cell in step needs about load current x capacity gap. Loss goes as current squared (Tim Ren). Switches move no charge.")
    c = st.columns(3)
    ah = c[0].select_slider("Cell size (Ah)", [20, 50, 100], 50, key="ah10")
    cr = c[1].select_slider("Discharge rate (C)", [0.15, 0.3, 0.5], 0.3, key="cr10")
    gp = c[2].select_slider("Capacity gap of the weak cell", [0.03, 0.08, 0.15, 0.32], 0.15, key="gp10")
    a = BAL.assess(ah, cr, gp)
    st.write(f"Needed balancing current {a['needed_a']:.2f} A. Passive (0.25 A max): {'enough' if a['passive_ok'] else 'not enough'}. Active (6 A max): {'enough' if a['active_ok'] else 'NOT enough'}; efficiency {100*a['efficiency']:.0f}%, heat {a['heat_w']:.1f} W per channel, "
             f"energy lost {a['energy_lost_pct_of_throughput']:.1f}% of throughput. Passive balancing 20 Ah of imbalance at 1 A takes 20 h; at 0.25 A, 80 h. Path resistance is ASSUMED (90% efficient at 3 A).")
    rowsb = [{"gap": g, **{f"{cc} C needs (A)": BAL.assess(ah, cc, g)["needed_a"] for cc in (0.15, 0.3, 0.5)}, "active can": all(BAL.assess(ah, cc, g)["active_ok"] for cc in (0.15, 0.3, 0.5))} for g in (0.03, 0.08, 0.15, 0.32)]
    st.dataframe(pd.DataFrame(rowsb).round(2).set_index("gap"))
    st.write("Module-level versus cell-level switching (second life): gain over a plain string, 240 cells in modules of 24, 10% mean capacity loss. Cells inside a module age differently by position, so module-level keeps only part of the gain.")
    bs = st.select_slider("Share of the fade spread that is BETWEEN modules", [0.0, 0.3, 0.6, 0.9], 0.3, key="bs10")

    @st.cache_data(show_spinner=False)
    def lad(b):
        return LAD.ladder(between_share=b, trials=500)

    r10 = lad(bs)
    st.bar_chart(pd.DataFrame({"gain over plain, %": [100 * r10[g] for g in (1, 6, 12, 24, 48)]}, index=["each cell", "6 cells per switch", "12 per switch", "module of 24", "2 modules (48)"]))
    st.caption(f"Switching whole modules keeps {100*r10[24]/r10[1]:.0f}% of the cell-level gain here. Our own simulation, independent lognormal draws; ask REON for teardown data.")
    st.divider()
    st.subheader("Second life: one retired EV pack as a stationary string")
    st.write("Real late-life cells (Nature Energy 2026, 12 EVs at 280,000 km, 95 cells each) re-used as one fixed series string. How much more is usable if neighbouring cells switch as a module, or every cell switches, and how little can the electronics cost before it stops paying? Static first-order screen: no further ageing, testing and disassembly not priced.")
    q = st.columns(3)
    win2 = q[0].select_slider("Share of cells that must stay in the string (Tim Ren: about 90% in normal use)", [0.5, 0.7, 0.9], 0.9, key="win2")
    val2 = q[1].select_slider("Value per kWh-year", [12, 22, 40, 80], 40, key="val2")
    yrs2 = q[2].select_slider("Years of second life", [4, 8, 12], 8, key="yrs2")
    sl = SL.table(real_packs(), window=win2, value=float(val2), years=float(yrs2))
    sl_rows = [{"option": k.replace("upper bound", "upper bound (every cell may leave, no loss)"), "extra usable energy, median (range over 12 cars)": f"{100*v['gain_median']:.1f}% ({100*v['gain_min']:.1f} to {100*v['gain_max']:.1f})",
                "most the electronics can cost per kWh and still pay, median (range)": f"{v['flip_cost_median']:.0f} ({v['flip_cost_min']:.0f} to {v['flip_cost_max']:.0f})"} for k, v in sl.items()]
    st.dataframe(pd.DataFrame(sl_rows).set_index("option"))
    best = sl["cell level"]["flip_cost_median"]
    st.write("Reading it: " + ("cell-level control pays across REON's quoted 7 to 24 per kWh." if best >= 24 else "cell-level control pays only at the cheap end of REON's quoted 7 to 24 per kWh." if best >= 7 else "cell-level control does not pay at REON's quoted 7 to 24 per kWh here.")
             + " Negative numbers mean the option loses energy to switch loss. Real retired EV cells are fairly well matched, and sorting them into matched strings recovers most of the gain (hackkit/reon_sorting.py), so second life is a scenario with a flip point, not the headline.")

with t11:
    st.write("Which unanswered question moves the answer most? Net gain over a plain string, 12 years, per kWh nameplate, 250 cells, one input changed at a time from the base case (single cells, fade 0.008, value 40, switch cost 15.5). A HOLD counts as zero. Ask REON in this order.")
    tor = pd.read_csv("examples/data/tornado_250.csv")
    base_gain = float(tor["base_gain"].iloc[0])
    st.metric("Base case", f"{base_gain:+.1f} per kWh")
    st.bar_chart(tor.set_index("input")[["gain_low", "gain_high"]].rename(columns={"gain_low": "input at its low end", "gain_high": "input at its high end"}))
    st.dataframe(tor[["input", "low", "high", "gain_low", "gain_high", "swing", "tag", "who_can_answer"]].set_index("input"))
    st.caption("Source: examples/reon_tornado_250.py. Each input stays BUY at both ends of its range in this base case, so the question is how much, not whether (the parallel-group case alone approaches HOLD at 40 cells). Switch loss barely matters; the value of a kWh, how much cells differ, and fade matter most. Every run keeps at least 90% of cells in the string.")

with t12:
    st.write("Who buys, how it reaches a site, and what policy touches it. The tariff screen turns a demand charge into the value of a kWh and reruns the engine at 250 cells (single cells, typical wear).")
    c = st.columns(2)
    dem = c[0].select_slider("Demand charge ($ per kW-month)", [5, 10, 15, 20, 25], 15, key="dem12")
    hrs = c[1].select_slider("Hours of storage per kW (2 or 4)", [2, 4], 2, key="hrs12")
    v12 = dem * 12.0 / hrs
    c12 = SF.cached_core(1, 0.008, v12)
    rob12 = {"verdict": c12["verdict"], "mean_gain": c12["dollars_per_kwh"]} if c12 else eng1(250, 1, v12, 15.5, 0.45, 0.04, 0.008)[0]
    st.metric(f"Value of a kWh at this tariff", f"${v12:.0f} per year")
    (st.success if rob12["verdict"] == "BUY" else st.warning)(f"{rob12['verdict']}: net gain over a plain string {rob12['mean_gain']:+.1f} per kWh, about ${rob12['mean_gain'] * 60:,.0f} on a 60 kWh battery over 12 years.".replace("$", "\\$"))
    st.markdown("- **Buyers.** About 5 million US commercial customers can subscribe to demand charges above \\$15/kW, about 3 million above \\$20/kW (NREL survey). Only the top quarter reach the 40 to 90 per kWh-year range.\n"
                "- **Market.** Community, commercial and industrial storage was about 95.6 MW of 18.9 GW installed in 2025; Wood Mackenzie expects 39% growth from 2025 to 2030 with a dip in 2026 (via ESS News). Small today, growing.\n"
                "- **How it ships.** Software on REON modules, which can be added in series with an existing battery (REON CTO). Sealed EV packs are typically not retrofittable.\n"
                "- **Policy.** The storage investment tax credit (Sections 48 and 48E) outlasts the wind and solar sunset, but prohibited-foreign-entity material-assistance rules are stricter for storage; preliminary Treasury guidance came in February 2026. Whether a REON battery qualifies depends on where its cells are made: ask REON.\n"
                "- **Certification.** Commercial storage normally meets UL 9540, UL 1973 and NFPA 855. Our layer stays out of the safety loop; REON's hardware keeps final authority. REON's engineers should confirm.")
    st.markdown("**Next 90 days:** (1) REON answers the seven questions in tab 11; (2) run `examples/reon_bms_sample_check.py` on a small per-cell sample; (3) shadow mode at one site: the layer recommends and logs, the hardware acts; (4) pick a pilot from the tariff screen and rerun with its load, outage record and tariff.")
