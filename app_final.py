"""REON decision layer: dashboard v1 (replays and simulations only; no live hardware link). Run: streamlit run app_final.py
Front page: customer view (storm night, years, dollars, environmental value). Engineering and evidence tabs sit behind it.
Tabs: 1 Is it worth it (live engine + go/no-go), 2 Where it flips (break-even map), 3 Life of the string (automatic bypass vs crew), 4 Storm (backup hours), 5 Voltage limit, 6 Evidence and limits."""
import csv
import altair as alt
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

st.set_page_config(page_title="JaiDio · REON decision layer", layout="wide", initial_sidebar_state="collapsed")
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
.rn-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; flex-wrap: wrap; }
.rn-logo { width: 190px; height: auto; margin-top: -4px; }
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
[data-testid="stElementToolbar"], .vega-actions, details.vega-actions { display: none !important; }
.st-key-nav button { font-size: 18px !important; font-weight: 700 !important; padding: 14px 22px !important; min-height: 56px; }
.st-key-nav [data-testid="stSegmentedControl"], .st-key-nav > div { width: 100%; }
.rn-hint { font-size: 17px; color: #5b6472; margin: 6px 0 18px; line-height: 1.45; }
.rn-hint b { color: #12161c; }
.rn-step { font-size: 20px; font-weight: 800; letter-spacing: -0.01em; margin: 22px 0 4px; color: #12161c; }
.rn-step span { display: inline-block; width: 28px; height: 28px; line-height: 28px; text-align: center; border-radius: 14px; background: #17324f; color: #fff; font-size: 15px; margin-right: 10px; }
.rn-read { background: #e8eff8; border: 1px solid #d3e0f1; border-radius: 14px; padding: 12px 18px; font-size: 17px; color: #17324f; margin: 4px 0 8px; }
.st-key-nextrow button { font-size: 17px !important; font-weight: 700 !important; padding: 12px 22px !important; }

@keyframes rn-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes rn-pop { from { opacity: 0; transform: translateY(8px) scale(.96); } to { opacity: 1; transform: none; } }
@keyframes rn-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes rn-glow { 0%, 100% { text-shadow: 0 0 0 rgba(255,200,87,0); } 50% { text-shadow: 0 0 22px rgba(255,200,87,.55); } }
.rn-verdict { animation: rn-rise .55s cubic-bezier(.2,.8,.2,1) both; }
.rn-buy .rn-vt { animation: rn-glow 2.6s ease-in-out 1s 2; }
.rn-nums > div { animation: rn-pop .6s cubic-bezier(.2,.8,.2,1) both; }
.rn-nums > div:nth-child(1) { animation-delay: .15s; } .rn-nums > div:nth-child(2) { animation-delay: .27s; } .rn-nums > div:nth-child(3) { animation-delay: .39s; } .rn-nums > div:nth-child(4) { animation-delay: .51s; }
.rn-ans { animation: rn-rise .4s ease both; }
.rn-read { animation: rn-rise .4s ease both; }
.rn-bars { margin: 8px 0 4px; }
.rn-brow { display: grid; grid-template-columns: 260px 1fr 70px; align-items: center; gap: 14px; margin: 9px 0; }
.rn-blab { font-size: 15px; font-weight: 600; color: #12161c; text-align: right; line-height: 1.2; }
.rn-btrack { position: relative; height: 34px; background: #17324f; border-radius: 17px; overflow: hidden; }
.rn-bfill { position: absolute; left: 0; top: 0; bottom: 0; background: #ffc857; border-radius: 17px; transform-origin: left center; animation: rn-grow 1.2s cubic-bezier(.2,.8,.2,1) both; }
.rn-bval { font-size: 16px; font-weight: 800; color: #17324f; }
.rn-bfail { position: absolute; top: -4px; bottom: -4px; width: 0; border-left: 3px dashed #e0573a; z-index: 3; }
.rn-baxis { display: grid; grid-template-columns: 260px 1fr 70px; gap: 14px; }
.rn-baxis > div:nth-child(2) { display: flex; justify-content: space-between; font-size: 13px; color: #5b6472; font-weight: 600; }
.rn-key { display: flex; gap: 20px; font-size: 14px; color: #5b6472; margin: 4px 0 0 274px; }
.rn-key i { display: inline-block; width: 12px; height: 12px; border-radius: 6px; margin-right: 6px; vertical-align: -1px; }
.rn-grid { display: grid; grid-template-columns: 150px repeat(4, 1fr); gap: 6px; margin: 10px 0 4px; }
.rn-gh { font-size: 13px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: #5b6472; padding: 4px 6px; display: flex; align-items: flex-end; }
.rn-gl { font-size: 15px; font-weight: 700; color: #12161c; display: flex; align-items: center; }
.rn-gc { border-radius: 12px; padding: 12px 10px; text-align: center; font-size: 17px; font-weight: 800; animation: rn-pop .5s ease both; transition: transform .15s; }
.rn-gc small { display: block; font-size: 12px; font-weight: 600; opacity: .75; margin-top: 2px; }
.rn-gc:hover { transform: translateY(-2px); }
.rn-gb { background: #17324f; color: #ffc857; }
.rn-gk { background: #e8eff8; color: #17324f; }
.rn-gn { background: #f4f6fa; color: #5b6472; }
.rn-gsel { outline: 3px solid #e0573a; outline-offset: 2px; }
.rn-range { font-size: 16px; margin: 10px 0 0; opacity: .92; line-height: 1.45; }
[data-testid="stSlider"] label p { font-size: 15px !important; font-weight: 700 !important; }
[data-testid="stSlider"] [role="slider"] { width: 28px !important; height: 28px !important; background: #2f5fa3 !important; box-shadow: 0 0 0 5px rgba(47,95,163,.18) !important; border: 3px solid #fff !important; }
[data-testid="stSlider"] [data-baseweb="slider"] > div:first-child > div { height: 10px !important; border-radius: 6px !important; }
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { font-size: 15px !important; font-weight: 700 !important; }
[data-testid="stSlider"] { padding-top: 6px; padding-bottom: 10px; }
@media (max-width: 820px) { .rn-brow, .rn-baxis { grid-template-columns: 120px 1fr 56px; } .rn-key { margin-left: 0; } .rn-grid { grid-template-columns: 90px repeat(4, 1fr); } .rn-h1 { font-size: 32px; } }
.rn-ct { font-size: 20px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; color: #12161c; margin: 0 0 6px; }
.rn-cb { font-size: 15px; line-height: 1.45; color: #5b6472; margin: 0 0 4px; min-height: 66px; }
[class*="st-key-evcard"] { border-radius: 20px !important; background: #f4f6fa; border: 1px solid #e3e7ee !important; transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease; padding: 6px 8px; }
[class*="st-key-evcard"]:hover { transform: translateY(-3px); box-shadow: 0 10px 26px rgba(23,50,79,.12); border-color: #2f5fa3 !important; }
[class*="st-key-evcard"] button { background: #17324f; color: #fff; border: none; border-radius: 12px; font-weight: 700; }
[class*="st-key-evcard"] button:hover { background: #2f5fa3; color: #fff; }
.rn-h2 { font-size: 34px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.08; margin: 10px 0 4px; color: #12161c; }
.rn-bigq { font-size: 30px; font-weight: 800; letter-spacing: -0.025em; line-height: 1.15; margin: 4px 0 6px; color: #12161c; }
.rn-prog { height: 8px; background: #e3e7ee; border-radius: 4px; overflow: hidden; margin: 10px 0 8px; }
.rn-prog > div { height: 100%; background: #2f5fa3; border-radius: 4px; animation: rn-grow .7s ease both; transform-origin: left; }
.rn-asks { display: flex; flex-direction: column; gap: 10px; margin: 6px 0 12px; }
.rn-ask { display: flex; gap: 16px; align-items: flex-start; background: #f4f6fa; border: 1px solid #e3e7ee; border-radius: 16px; padding: 14px 18px; animation: rn-rise .4s ease both; }
.rn-ask-n { flex: none; width: 34px; height: 34px; line-height: 34px; text-align: center; border-radius: 17px; background: #17324f; color: #ffc857; font-weight: 800; }
.rn-ask-b b { display: block; font-size: 17px; color: #12161c; }
.rn-ask-b span { display: block; font-size: 14px; color: #5b6472; margin-top: 2px; }
.rn-ask-b em { display: block; font-style: normal; font-size: 15px; color: #2f5fa3; font-weight: 700; margin-top: 4px; }
[data-testid="stSegmentedControl"] button { font-size: 16px !important; padding: 10px 16px !important; font-weight: 600 !important; }
[data-testid="stColumn"] [data-testid="stSegmentedControl"] button { padding: 8px 10px !important; font-size: 15px !important; }
[data-testid="stButtonGroup"] [role="radiogroup"] { flex-wrap: wrap !important; overflow: visible !important; row-gap: 6px; }
[data-testid="stSegmentedControl"] label p { font-size: 15px !important; font-weight: 700 !important; color: #12161c; }
</style>""", unsafe_allow_html=True)
import base64


@st.cache_data
def _logo_uri():
    try:
        with open("assets/jaidio_logo.png", "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except OSError:
        return ""


_lg = _logo_uri()
st.html('<div class="rn-head"><div><p class="rn-eyebrow">Team JaiDio · REON decision layer · MIT Energy &amp; Climate Hack 2026</p><h1 class="rn-h1">Should this store get cell-level switches?</h1>'
        '<p class="rn-sub">Answer three questions. We give a recommendation, then test it on a storm night. Everything is a simulation on assumed sodium-ion behaviour, not REON data.</p></div>'
        + (f'<img class="rn-logo" src="{_lg}" alt="JaiDio">' if _lg else "") + '</div>')


@st.cache_data
def real_packs():
    rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
    car = {}
    for p, _, _, late in rows:
        car.setdefault(p, []).append(float(late))
    return {k: np.array(v) for k, v in car.items()}


BE = pd.DataFrame({"fade spread 0.20": [16.2, 27.3, 45.7, None], "0.45": [25.4, 42.9, None, None], "0.60": [29.1, 49.4, None, None]}, index=["value 12", "value 22", "value 40", "value 80"])
@st.cache_data
def storm_demo(fail_h):
    return DM.storm(real_packs(), fail_h)


def _bars(rows, fail_h=None, horizon=24.0):
    """Animated storm bars: amber = lights on, navy = dark, red dashed line = the hour a cell opens."""
    out = ['<div class="rn-bars">']
    for label, until in rows:
        u = max(0.0, min(float(until), horizon))
        fail = f'<div class="rn-bfail" style="left:{100 * fail_h / horizon:.2f}%"></div>' if fail_h is not None else ""
        out.append(f'<div class="rn-brow"><div class="rn-blab">{label}</div><div class="rn-btrack">{fail}<div class="rn-bfill" style="width:{100 * u / horizon:.2f}%"></div></div><div class="rn-bval">{u:.1f} h</div></div>')
    ticks = "".join(f"<span>{t}</span>" for t in range(0, int(horizon) + 1, 4))
    out.append(f'<div class="rn-baxis"><div></div><div>{ticks}</div><div></div></div>')
    out.append('<div class="rn-key"><span><i style="background:#ffc857"></i>Lights on</span><span><i style="background:#17324f"></i>Dark</span>' + ('<span><i style="background:#e0573a"></i>A cell opens</span>' if fail_h is not None else "") + "</div></div>")
    return "".join(out)


def _verdict_grid(wire_i, wear_i, val_i):
    """How the call changes if wear or the value of backup is a step away from what was picked. Rows: wear. Columns: value."""
    cells = ['<div class="rn-grid"><div></div>' + "".join(f'<div class="rn-gh">{v[1].split(" ")[0]} / kWh-yr</div>' for v in DM.VALUES)]
    for wi, w in enumerate(DM.WEAR):
        cells.append(f'<div class="rn-gl">{w[0]} · {w[1] * 100:.1f}%</div>')
        for vi, v in enumerate(DM.VALUES):
            c = DM.verdict_card(SF.cached_core(DM.WIRING[wire_i][1], w[1], v[0]))
            sel = " rn-gsel" if (wi == wear_i and vi == val_i) else ""
            if c is None:
                cells.append(f'<div class="rn-gc rn-gn{sel}">n/a</div>')
            elif c["kind"] == "BUY":
                cells.append(f'<div class="rn-gc rn-gb{sel}" style="animation-delay:{(wi * 4 + vi) * 0.03:.2f}s">${c["dollars"]:,.0f}<small>build</small></div>')
            elif c["kind"] == "BALANCER":
                cells.append(f'<div class="rn-gc rn-gk{sel}" style="animation-delay:{(wi * 4 + vi) * 0.03:.2f}s">balancer<small>is enough</small></div>')
            else:
                cells.append(f'<div class="rn-gc rn-gn{sel}">hold</div>')
    cells.append("</div>")
    return "".join(cells)


def _neighbours(wire_i, wear_i, val_i):
    """Verdict cards for the picked case and the cases one step away in wear or value (including diagonals)."""
    out = []
    for dw in (-1, 0, 1):
        for dv in (-1, 0, 1):
            w, v = wear_i + dw, val_i + dv
            if 0 <= w < len(DM.WEAR) and 0 <= v < len(DM.VALUES):
                c = DM.verdict_card(SF.cached_core(DM.WIRING[wire_i][1], DM.WEAR[w][1], DM.VALUES[v][0]))
                if c:
                    out.append(c)
    return out


def _fmt_val(v, fmt):
    if fmt:
        try:
            return fmt % v
        except (TypeError, ValueError):
            pass
    return f"{v:g}" if isinstance(v, float) else str(v)


def _chip_slider(host, label, min_value=None, max_value=None, value=None, step=None, format=None, key=None, help=None, **kw):
    """Stand-in for st.slider: a row of four preset buttons (low, between, default, between, high). No dragging; the default is always one of them."""
    lo, hi = min_value, max_value
    isint = all(isinstance(x, int) for x in (lo, hi, value if value is not None else lo))
    d = lo if value is None else value
    mids = [lo + (d - lo) / 2.0] if (d - lo) >= (hi - d) else [d + (hi - d) / 2.0]   # four presets: the low end, the default, the high end, and one midpoint on the longer side
    opts = [lo] + mids + [d, hi]
    if isint:
        opts = sorted({int(round(o)) for o in opts})
    else:
        dec = 3 if (step and step < 0.01) or hi <= 1 else 2 if hi <= 20 else 1
        opts = sorted({round(float(o), dec) for o in opts} | {float(d)})
    v = host.pills(label, opts, selection_mode="single", default=d if d in opts else opts[0], format_func=lambda o: _fmt_val(o, format), key=key, help=help, disabled=kw.get("disabled", False))
    return d if v is None else v


def _chip_select(host, label, options=(), value=None, format_func=str, key=None, help=None, **kw):
    opts = list(options)
    d = value if value in opts else opts[0]
    v = host.pills(label, opts, selection_mode="single", default=d, format_func=format_func, key=key, help=help, disabled=kw.get("disabled", False))
    return d if v is None else v


from streamlit.delta_generator import DeltaGenerator as _DG
_DG.slider = lambda self, *a, **k: _chip_slider(self, *a, **k)
_DG.select_slider = lambda self, *a, **k: _chip_select(self, *a, **k)
st.slider = lambda *a, **k: _chip_slider(st, *a, **k)
st.select_slider = lambda *a, **k: _chip_select(st, *a, **k)

PAGES = ["1 · Ask us", "2 · See it in 3D", "3 · Your state and site", "4 · The evidence"]
HINTS = ["Start here. Answer three questions and we tell you whether the switches are worth it, then test it on a storm night.",
         "Break the battery yourself. Click a cell to fail it and watch what a plain string and cell-level control do.",
         "Pick your state on the map, describe the site, and read what it means in dollars, battery life and carbon.",
         "Every claim above, checked. Pick a question below; each answer shows its method, inputs and limits."]
st.session_state.setdefault("nav", PAGES[0])
st.segmented_control("Go to", PAGES, key="nav", label_visibility="collapsed")
if st.session_state.get("nav") not in PAGES:
    st.session_state["nav"] = st.session_state.get("_nav_last", PAGES[0])
st.session_state["_nav_last"] = st.session_state["nav"]
pidx = PAGES.index(st.session_state["nav"])
st.html(f'<p class="rn-hint"><b>{PAGES[pidx]}.</b> {HINTS[pidx]}</p>')
EV = {1: "Try your own numbers", 2: "Where does it flip?", 3: "How the string ages", 4: "Storm night in detail", 5: "The voltage limit", 6: "Sources and stress tests", 7: "Which cell is hurting?", 8: "Where the money comes from",
      9: "System view", 10: "Balancing and modules", 11: "What to ask REON first", 12: "Who buys and how it ships", 13: "Cell trends"}
EVB = {1: "Answer seven short questions about a store and run the full 250-cell engine on your own numbers.",
       2: "How cheap switches must be, and how narrow the cell spread, before a balancer beats them.",
       3: "Years of faults, crew visits and bypasses: replace-on-failure against automatic bypass.",
       4: "A storm night in hours on 12 real car packs: plain, switched, and shedding half the load.",
       5: "How many cells can be bypassed before the string drops below the inverter minimum.",
       6: "The source for every input, and every stress test we ran, including the hostile cases.",
       7: "For each cell: what bypassing it is worth per year, and what the response layer would do.",
       8: "Where the extra dollars come from, and the fault rate where bypass starts to pay.",
       9: "The whole string over 30 years: how many charges it lasts and how likely it is to survive.",
       10: "Why not just balance? The current a balancer needs, and what module-level switching keeps.",
       11: "Ten unknowns ranked by how much they move the answer, and who can answer each.",
       12: "Who buys, how it reaches a site, and the next 90 days.",
       13: "Spot a failing cell early from how fast it falls compared with its neighbours."}
EVG = [("Is it worth it?", [1, 2, 3, 8, 10]), ("Does it hold up?", [4, 5, 6, 7, 13, 9]), ("What we still need", [11, 12])]
EV_ORDER = [n for _, ids in EVG for n in ids]


def _open_ev(n):
    st.session_state["ev"] = n


ev = None
if pidx == 3:
    ev = st.session_state.get("ev")
    if ev not in EV:
        ev = None
    if ev is None:
        for gname, ids in EVG:
            st.html(f'<p class="rn-sec" style="margin-top:22px">{gname}</p>')
            cols = st.columns(3, gap="medium")
            for j, n in enumerate(ids):
                with cols[j % 3]:
                    with st.container(border=True, key=f"evcard{n}"):
                        st.html(f'<p class="rn-ct">{EV[n]}</p><p class="rn-cb">{EVB[n]}</p>')
                        st.button("Open →", key=f"evopen{n}", on_click=_open_ev, args=(n,))
    else:
        tb = st.columns([1, 4])
        tb[0].button("← All evidence", key="ev_back", on_click=_open_ev, args=(None,))
        st.html(f'<p class="rn-h2">{EV[ev]}</p><p class="rn-note" style="margin-bottom:14px">{EVB[ev]}</p>')

if pidx == 0:
    def _pick(label, n, fmt, default, key, num):
        st.html(f'<p class="rn-q"><span>{"ABC"[num - 1]}</span>{label}</p>')
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
        nb = _neighbours(wire_i, wear_i, val_i)
        same = sum(1 for c in nb if c["kind"] == kind)
        rng = ""
        if kind == "BUY":
            dl = [c["dollars"] for c in nb if c["kind"] == "BUY"]
            rng = (f'<p class="rn-range"><b>Not exact, so here is the range.</b> Pessimistic case: about ${case_d["p10_per_kwh"] * 60:,.0f} (the 10th percentile of our random runs). '
                   f'If wear or backup value is one step off, the call stays "{head.rstrip(".").lower()}" in {same} of {len(nb)} nearby cases, worth ${min(dl):,.0f} to ${max(dl):,.0f}.</p>')
        else:
            rng = f'<p class="rn-range"><b>Not exact, so here is the range.</b> If wear or backup value is one step off, the call stays the same in {same} of {len(nb)} nearby cases. The grid below shows where it flips.</p>'
        st.html(f'<div class="rn-verdict {cls}"><p class="rn-eyebrow">Our answer for this store</p><p class="rn-vt">{head}</p><p class="rn-vl">{card["line"]}</p>'
                + ('<div class="rn-nums">' + "".join(f"<div><b>{a}</b><i>{b}</i></div>" for a, b in nums) + "</div>" if nums else "") + rng + "</div>")
        st.html('<p class="rn-sec">What if the numbers are off?</p><p class="rn-note">Rows are how fast cells wear, columns are what backup is worth, for the wiring you picked. Dollars are the 12-year value of the switches per 60 kWh store. Your pick is outlined in red.</p>')
        st.html(_verdict_grid(wire_i, wear_i, val_i))

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
        st.html(_bars(rows, fail_h if failed else None))
        m = st.columns(3)
        m[0].metric("Plain string", f"{plain_h:.1f} h of lights")
        m[1].metric("Cell-level control", f"{ours_h:.1f} h of lights", f"{ours_h - plain_h:+.1f} h", delta_color="normal")
        m[2].metric("Control, shedding half the load", f"{shed_h:.1f} h of lights", f"{shed_h - plain_h:+.1f} h", delta_color="normal")

    st.html('<p class="rn-sec">Ask us</p><p class="rn-note">Tap a question. Every answer is computed from the model, not written by a chatbot.</p>')
    QS = ["What happens if a cell dies mid-storm?", "When is a simple balancer enough?", "How do we know the policy is safe?", "How hostile a case did we test?", "What do we need from REON?", "Can I see it in 3D?"]
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
        av = DM.adversary_summary()
        ran = (f"We ran {av['runs']} hostile packs ({len(av['cases'])} kinds, at 1, 4 and 16 cells in parallel, 6 random draws each): clustered weak cells, outliers, dead cells, three cold cases, slow and fast wear, and fade that hits neighbouring cells together. "
               f"The policy was behind a balancer or a plain string in only 2 of them, by at most ${av['worst_regret']:.2f} a kWh (our tolerance is 0.50), and said \"a balancer is enough\" where that was true. ") if av else ""
        ans = (ran + "What is still weak: cold is one vendor's published capacity at minus 20 and minus 40 C plus an assumed loss, not temperature physics. Slow recovery is an energy budget between two outages, not rest-voltage rebound. "
               "Dead cells are frozen from day 1 in the dollar run; failures arriving over the years are tested separately and the per-site chooser left at most about 30 dollars a kWh on the table in 300 hostile sites. "
               "There is no REON data in the model: sodium-ion behaviour is assumed, and backup hours use 12 real car packs.").replace("$", "&#36;")
    elif q == QS[4]:
        tor = pd.read_csv("examples/data/tornado_250.csv").sort_values("swing", ascending=False).head(3)
        ans = ("Three numbers move the answer most: " + "; ".join(f"{r.input.lower()} ({r.who_can_answer})" for r in tor.itertuples()) + ". Give us those and the assumptions become measurements.")
    elif q == QS[5]:
        ans = "Open step 2, See it in 3D. Click a cell to fail it, click again to repair it, and flip between a plain string and cell-level control."
    if ans:
        st.html(f'<div class="rn-ans">{ans}</div>')
    pr0 = DM.proof()
    st.caption(f"Checked against {pr0['runs']} stress runs: never behind a balancer or a plain string by more than ${pr0['worst_regret']:.2f} a kWh. Simulation on assumed sodium-ion behaviour; not REON data. Inputs and limits are in step 4, The evidence.".replace("$", "\\$"))

if pidx == 3 and ev == 13:
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


if pidx == 2:
    st.html('<p class="rn-step"><span>A</span>Pick your state</p>')
    sd0 = pd.read_csv("examples/data/eia_reliability_by_state.csv", comment="#").set_index("state")
    ss0 = st.session_state
    ss0.setdefault("map_ver", 0)
    if True:
        mc = st.columns([3, 2])
        layer = mc[0].radio("What to colour the map by", list(MP.LAYERS), key="m_layer", horizontal=True, format_func=lambda v: {"Exposure": "Outage minutes", "Coverage": "Backup coverage", "Where to pilot": "Where to pilot first"}[v], help="Outage minutes: how long the average customer was without power in 2025. Backup coverage: hours of backup against a typical outage. Where to pilot first: load at risk in dollars per store-year.")
        mc[0].caption({"Exposure": "Darker = more minutes without power in 2025 (utility reports). Click a state to use it below.", "Coverage": "Darker = our battery covers more of a typical outage there. Click a state to use it below.", "Where to pilot": "Darker = more dollars of load at risk per store-year. A good place to pilot. Click a state to use it below."}[layer])
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
        _s = ss0.get("f_state", "California")
        if _s in sd0.index:
            st.html(f'<div class="rn-read"><b>{_s}.</b> A typical customer lost power {sd0.loc[_s, "saidi_major_2025"]:.0f} minutes in 2025 across {sd0.loc[_s, "saifi_major_2025"]:.1f} interruptions, and each lasted about {sd0.loc[_s, "caidi_major_2025"]:.0f} minutes. Click another tile to change it.</div>')
        st.caption("Click a tile to set your state below. State averages from the utilities' reports (EIA-861), not a store's own outage record. "
                      + ("Coverage uses your load setting and the cell-level backup hours." if layer == "Coverage" else "")
                      + (" Load at risk = hours without power x your load x the value above; one sourced anchor (Texas), the rest is your call." if layer == "Where to pilot" else ""))
    st.html('<p class="rn-step"><span>B</span>Describe the site, then read the result</p>')
    ctrl, res = st.columns([1, 2.6], gap="large")
    with ctrl:
        st.markdown("**Your site**")
        state0 = st.selectbox("State", list(sd0.index), index=list(sd0.index).index("California"), key="f_state")
        load0 = st.slider("Critical load during an outage (kW)", 1.0, 10.0, 5.0, key="f_load")
        kind0 = st.radio("What is one position in the string?", ["One large cell", "4 cells in parallel", "16 cells in parallel"], key="f_kind", help="REON has not said which. The answer changes the result (see \"System view\" in step 4).")
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
    with st.expander("Go deeper: how to read this page"):
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
    with st.expander("Go deeper: what would have to be true (gain against how fast cells wear)"):
        vsel = st.select_slider("Value of a kWh of backup per year ($)", [12, 22, 40, 80], 40, key="f_gv")
        grows = SF.gain_vs_fade(vsel)
        if grows:
            st.altair_chart(VZ.gain_fade_chart(grows), use_container_width=True)
            st.caption("The height is the EXTRA 12-year gain our recommended build earns over the better of a simple 5% balancer or doing nothing. Each line is one way of wiring cells in parallel. A cross on the zero line means a balancer is enough (or nothing pays) and we would not sell the switches. "
                       "Read it from the right: the faster the cells wear, the more cell-level control is worth beyond a balancer, and the more cells share a position, the more wear it takes before it pays. "
                       "The maker's claim is the far left, where a balancer is enough. Steps in the lines come from replacement dates. Simulated at 250 cells, switch cost 15.5 per kWh (the extra over a conventional BMS), at least 90% of cells kept in the string, 2% switch loss on all energy; not REON data.")
        else:
            st.info("No precomputed cases found for this value.")
    with st.expander("Go deeper: how strong would a simple balancer have to be?"):
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
    with st.expander("Go deeper: what we are not claiming"):
        st.markdown("- We are not changing REON's hardware. We add the decision layer: which cell to switch out, when to bypass, when to call a crew. REON's hardware keeps safety authority.\n"
                    "- We are not claiming this for homes, EVs or scooters; the numbers are for a commercial backup battery.\n"
                    "- We are not claiming a grid-emissions saving. The carbon figure is manufacturing only.\n"
                    "- Everything here is a simulation or a replay on assumed sodium-ion behaviour; there is no live REON data in it yet. Cell fade, fault rates and switch cost are assumptions or REON statements, tagged in the evidence tab.\n"
                    "- We do not count benefits beyond the 12-year bankable horizon in the dollar figure. Life beyond that is a projection.")

if pidx == 3 and ev == 1:
    WZ = [("fade25", "How fast do the cells wear?", [0.004, 0.008, 0.012, 0.02], 0.008, lambda v: {0.004: "Gentle", 0.008: "Typical", 0.012: "Hard", 0.02: "EV-like"}[v] + f" · {v * 100:.1f}% a year", "The maker's 20,000-cycle claim is 0.4% a year at one cycle a day. Lithium EVs lose about 2%."),
          ("temp", "How hot does the battery run?", [15, 25, 35, 45], 25, lambda v: f"{v} °C", "Ageing about doubles per 10 °C (an assumed rule of thumb)."),
          ("fcv", "How different are the cells from each other?", [0.2, 0.45, 0.6], 0.45, lambda v: {0.2: "Tight", 0.45: "Typical", 0.6: "Wide"}[v] + f" · {v:.2f}", "Spread of wear rates between cells. Real car packs run 0.20 to 0.60."),
          ("value", "What is backup worth to the owner, per kWh per year?", [12, 22, 40, 80], 40, lambda v: f"${v}", "$12 grid services, $22 EV charging, $40 to $80 for sites that pay demand charges."),
          ("elec", "What do the switches cost, per kWh of battery?", [7, 15.5, 24], 15.5, lambda v: f"${v:g}", "Tim Ren: $7 to $24 per kWh over a conventional BMS. $15.5 is the middle."),
          ("p1", "How many cells sit side by side at each position?", [1, 4, 16, 40], 1, lambda v: "One cell" if v == 1 else f"{v} in parallel", "REON has not said. More cells in parallel average out wear, so the case for switches shrinks."),
          ("n1", "How many cells are in series?", [200, 250, 300], 250, lambda v: f"{v} cells", "Tim Ren: 200 to 300 in series. The engine takes about 15 seconds at 250.")]
    ss1 = st.session_state
    ss1.setdefault("wz_step", 0)
    ss1.setdefault("wz_ans", {})

    def _wz_go(delta, key=None, default=None):
        if key is not None:
            v = ss1.get(f"wzw_{key}")
            ss1["wz_ans"][key] = default if v is None else v
        ss1["wz_step"] = max(0, min(len(WZ), ss1["wz_step"] + delta))

    def _wz_reset():
        ss1["wz_step"], ss1["wz_ans"] = 0, {}

    step = ss1["wz_step"]
    if step < len(WZ):
        key, q, opts, dflt, fmt, why = WZ[step]
        st.html(f'<div class="rn-prog"><div style="width:{100 * (step + 1) / (len(WZ) + 1):.0f}%"></div></div><p class="rn-note">Question {step + 1} of {len(WZ)}</p><p class="rn-bigq">{q}</p><p class="rn-note">{why}</p>')
        st.segmented_control(q, opts, default=ss1["wz_ans"].get(key, dflt), format_func=fmt, key=f"wzw_{key}", label_visibility="collapsed")
        nb = st.columns([1, 1, 3])
        if step > 0:
            nb[0].button("← Back", key="wz_back", on_click=_wz_go, args=(-1, key, dflt))
        nb[1].button("Next →" if step < len(WZ) - 1 else "See my answer →", key="wz_next", type="primary", on_click=_wz_go, args=(1, key, dflt))
    else:
        A1 = {k: ss1["wz_ans"].get(k, d) for k, _, _, d, _, _ in WZ}
        fade = A1["fade25"] * 2.0 ** ((A1["temp"] - 25) / 10.0)
        value, fcv, elec, loss, p1, n1 = A1["value"], A1["fcv"], A1["elec"], 0.04, A1["p1"], A1["n1"]

        @st.cache_data(show_spinner="Running the engine on your numbers (about 15 seconds)")
        def eng1(n, p, value, elec, fcv, loss, fade):
            rng = np.random.default_rng(3)
            start = 100.0 * (1.0 + 0.02 / np.sqrt(p) * rng.standard_normal(n))
            kw = dict(value_per_kwh_year=float(value), electronics_per_kwh=float(elec), fade_cv=fcv / np.sqrt(p), loss=loss, fade_mean=fade, ks=tuple(k for k in (1, 2, 4, 8, 16, 25) if k < n) or (1,), window=SF.WINDOW, closed_loss=SF.CLOSED_LOSS)
            if n >= 100:
                kw.update(trials=8, steps=60)
            rb = POL.robust_guarded(start, n, **kw)
            return rb, dict(table=rb["table"], build=rb["build"], ours_best=rb["build"], rival_best=rb["rival"], margin=rb["margin_vs_rival"])

        rob, out = eng1(n1, p1, value, elec, fcv, loss, fade)
        t = out["table"]
        go = rob["verdict"] == "BUY" and out["margin"] > 0
        cls, head = ("rn-buy", "Build the switches.") if go else ("rn-bal", f"Use the {out['rival_best']}.") if rob["verdict"] != "BUY" else ("rn-bal", "Too close to call.")
        line = ("; ".join(rob["reasons"])).replace("<", "&lt;")
        nums = [(f"{rob['mean_gain']:+.1f}", "net value per kWh vs plain"), (f"{out['margin']:+.1f}", f"margin over {out['rival_best']}"), (f"{rob['life_ours']:.0f} → {rob['life_plain']:.0f} y" if False else f"{rob['life_ours']:.0f} years", f"service life (plain: {rob['life_plain']:.0f})"), (out["build"], "recommended build")]
        st.html(f'<div class="rn-verdict {cls}"><p class="rn-eyebrow">Your numbers, run through the full engine</p><p class="rn-vt">{head}</p><p class="rn-vl">{line}</p>'
                '<div class="rn-nums">' + "".join(f"<div><b>{a}</b><i>{b}</i></div>" for a, b in nums) + "</div></div>")
        for w in rob["warnings"]:
            st.caption(f"Note: {w}")
        tt = pd.DataFrame({k: {"net": v["mean"], "p10": v["p10"], "cost": v["cost"]} for k, v in t.items()}).T.reset_index(names="build").sort_values("net", ascending=False).head(8)
        st.html('<p class="rn-step"><span>A</span>How the builds compare</p><p class="rn-note">Net 12-year value per kWh against a plain string. The bar is the average; the thin line runs from the pessimistic 10th percentile to the average.</p>')
        base = alt.Chart(tt).encode(y=alt.Y("build:N", sort=None, title=None, axis=alt.Axis(labelLimit=420, labelFontSize=13, ticks=False, domain=False)))
        bars = base.mark_bar(cornerRadius=6, height=20, color="#2f5fa3").encode(x=alt.X("net:Q", title="$ per kWh", axis=alt.Axis(grid=False)), tooltip=[alt.Tooltip("build:N", title="Build"), alt.Tooltip("net:Q", title="Net value", format=".1f"), alt.Tooltip("p10:Q", title="Pessimistic (p10)", format=".1f"), alt.Tooltip("cost:Q", title="Cost per kWh", format=".1f")])
        rng_ = base.mark_rule(color="#17324f", strokeWidth=2).encode(x="p10:Q", x2="net:Q")
        st.altair_chart((rng_ + bars).properties(height=34 * len(tt) + 30), use_container_width=True)
        rb_ = st.columns([1, 1, 3])
        rb_[0].button("← Change answers", key="wz_chg", on_click=lambda: ss1.__setitem__("wz_step", 0))
        rb_[1].button("Start over", key="wz_reset", on_click=_wz_reset)
    st.caption("Plain string is the brief's baseline. Balancer rival: 5% transfer, cost $4 per kWh. Start spread 2% (divided by the square root of cells in parallel), 12 years, retire at 70%, 4% usable-energy loss. The Ask page uses the same engine on precomputed cases.")

if pidx == 3 and ev == 2:
    st.subheader("Break-even switch cost against a typical balancer (per kWh nameplate)")
    st.dataframe(BE.fillna(">60 (never flips)").astype(str))
    st.caption("This table was computed before the voltage window was enforced in the engine (see docs/SOURCES.md); treat the break-even costs as the optimistic end.")
    st.write("Above the number in a cell, a typical balancer is better than switches. Tim Ren's overhead range is 7 to 24. Only the lowest-value, narrowest-spread corner puts that range partly in the losing zone. Source: examples/reon_losing_regimes_output.txt.")
    st.write("A logistic go/no-go screen on all inputs, tested on held-out draws, is right 88.5 % of the time against 82.7 % for always saying go, and catches about half the cases we lose: use it as a screen, not a verdict.")

if pidx == 3 and ev == 3:
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

if pidx == 3 and ev == 4:
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

if pidx == 3 and ev == 5:
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

if pidx == 3 and ev == 6:
    av6 = DM.adversary_summary()
    if av6:
        st.html(f'<div class="rn-verdict rn-buy"><p class="rn-eyebrow">Hostile-pack run</p><p class="rn-vt">{av6["runs"]} hostile packs, {"never behind" if av6["worst_regret"] <= 0.01 else "worst shortfall $" + format(av6["worst_regret"], ".2f") + " a kWh"}.</p>'
                f'<p class="rn-vl">{len(av6["cases"])} kinds of bad pack, at 1, 4 and 16 cells in parallel, 6 random draws each. Measured against the better of a plain string or a balancer, only two were behind, by at most ${av6["worst_regret"]:.2f} a kWh; the other 196 never were.</p></div>'.replace("$", "&#36;"))
    tabs6 = st.tabs(["Hostile packs", "All stress tests", "Where each number comes from"])
    with tabs6[0]:
        st.markdown(open("docs/stress/adversary_results.md").read())
        st.markdown(open("docs/stress/adversary_assumptions.md").read())
    with tabs6[1]:
        st.markdown(open("docs/STRESS.md").read())
    with tabs6[2]:
        st.markdown(open("docs/SOURCES.md").read())

if pidx == 3 and ev == 7:
    st.write("Rule, then money, then rank: for each cell of a plain string, what bypassing it would be worth per year, and what the response layer would do with it.")
    packs = real_packs()
    car = st.selectbox("Real car pack (Nature Energy 2026, 95 cells; first 16 shown as one string)", list(packs))
    v7 = st.slider("Value per kWh-year", 5.0, 100.0, 40.0, key="v7")
    rows = RK.rank_cells(packs[car][:16], 60.0, v7)
    st.dataframe(pd.DataFrame(rows).round(2).set_index("cell"))
    st.caption("Negative dollars: bypassing a healthy cell loses more than it gains. Responses come from reon_response.decide; hardware keeps safety authority.")

if pidx == 3 and ev == 8:
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

if pidx == 3 and ev == 9:
    st.write("System level, the way Tim Ren frames it: how many charges does the whole string last, and how likely is it to survive? Life is cell-limited here (30-year horizon, retire at 70% of day-1); the bankable value in \"Is it worth it?\" stops at 12 years.")
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

if pidx == 3 and ev == 10:
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

if pidx == 3 and ev == 11:
    tor = pd.read_csv("examples/data/tornado_250.csv")
    base_gain = float(tor["base_gain"].iloc[0])
    st.html(f'<p class="rn-note">Net gain over a plain string, 12 years, per kWh of battery, 250 cells. One input changed at a time from the base case (single cells, fade 0.008, value 40, switch cost 15.5); a HOLD counts as zero. The base case is <b>{base_gain:+.1f} per kWh</b> (amber line). Ask REON in this order.</p>')
    tt = tor.assign(lo=tor[["gain_low", "gain_high"]].min(axis=1), hi=tor[["gain_low", "gain_high"]].max(axis=1)).sort_values("swing", ascending=False)
    tt["short"] = tt["input"].str.replace(r"\s*\(.*\)", "", regex=True)
    _b = alt.Chart(tt).mark_bar(cornerRadius=6, height=20, color="#2f5fa3").encode(
        y=alt.Y("short:N", sort=None, title=None, axis=alt.Axis(labelLimit=420, labelFontSize=14, ticks=False, domain=False)),
        x=alt.X("lo:Q", title="12-year gain over a plain string, $ per kWh", axis=alt.Axis(grid=False)), x2="hi:Q",
        tooltip=[alt.Tooltip("input:N", title="Input"), alt.Tooltip("low:Q", title="Low end"), alt.Tooltip("high:Q", title="High end"), alt.Tooltip("lo:Q", title="Gain at worst", format=".1f"), alt.Tooltip("hi:Q", title="Gain at best", format=".1f")])
    _r = alt.Chart(pd.DataFrame({"x": [base_gain]})).mark_rule(color="#f2b134", strokeWidth=3).encode(x="x:Q")
    st.altair_chart((_b + _r).properties(height=380), use_container_width=True)
    st.html('<p class="rn-step"><span>A</span>Who can answer each</p>')
    rows = []
    for i, r in enumerate(tt.itertuples(), 1):
        tag = str(r.tag).replace("<", "&lt;")
        rows.append(f'<div class="rn-ask"><div class="rn-ask-n">{i}</div><div class="rn-ask-b"><b>{r.input}</b><span>{r.low:g} to {r.high:g} · moves the gain by {r.swing:.1f} per kWh · {tag}</span>'
                    f'<em>{str(r.who_can_answer)}</em></div></div>')
    st.html('<div class="rn-asks">' + "".join(rows) + "</div>")
    st.caption("Source: examples/reon_tornado_250.py. Each input stays BUY at both ends of its range in this base case, so the question is how much, not whether (the parallel-group case alone approaches HOLD at 40 cells). Switch loss barely matters; the value of a kWh, how much cells differ, and fade matter most. Every run keeps at least 90% of cells in the string.")

if pidx == 3 and ev == 12:
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
    st.markdown("**Next 90 days:** (1) REON answers the seven questions in step 4 (\"What to ask REON first\"); (2) run `examples/reon_bms_sample_check.py` on a small per-cell sample; (3) shadow mode at one site: the layer recommends and logs, the hardware acts; (4) pick a pilot from the tariff screen and rerun with its load, outage record and tariff.")


def _go(p):
    st.session_state["nav"] = PAGES[p]


with st.container(key="nextrow"):
    st.html('<hr style="border:none;border-top:1px solid #e3e7ee;margin:28px 0 12px">')
    fb = st.columns([1, 1, 1])
    if pidx > 0:
        fb[0].button(f"← Back to {PAGES[pidx - 1].split(' · ')[1]}", key="nav_back", on_click=_go, args=(pidx - 1,))
    if pidx < len(PAGES) - 1:
        fb[1].button(f"Next: {PAGES[pidx + 1].split(' · ')[1]} →", key="nav_next", type="primary", on_click=_go, args=(pidx + 1,))
