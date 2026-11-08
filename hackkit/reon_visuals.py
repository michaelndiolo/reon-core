"""Charts for the dashboard (Altair, bundled with Streamlit: no extra package). Colour is never the only cue: failed cells carry a cross, early leavers a dash, and every state is in the legend."""
from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

STATES = ["Active", "Can leave early", "Failed, isolated"]
COLORS = ["#2a7f8e", "#d9922b", "#c0392b"]


def grid_frame(health, failed, early, cols: int = 25) -> pd.DataFrame:
    h = np.asarray(health, dtype=float)
    fs, es = set(failed), set(early)
    rows = []
    for i, v in enumerate(h):
        state = STATES[2] if i in fs else (STATES[1] if i in es else STATES[0])
        rows.append(dict(cell=i, row=i // cols, col=i % cols, health=float(v), state=state, mark="×" if i in fs else ("–" if i in es else "")))
    return pd.DataFrame(rows)


def grid_chart(health, failed, early, cols: int = 25):
    df = grid_frame(health, failed, early, cols)
    pick = alt.selection_point(name="pick", fields=["cell"], on="click", clear="dblclick")
    base = alt.Chart(df).encode(x=alt.X("col:O", axis=None), y=alt.Y("row:O", axis=None))
    rect = base.mark_rect(stroke="white", strokeWidth=1.5, cornerRadius=2).encode(
        color=alt.Color("state:N", scale=alt.Scale(domain=STATES, range=COLORS), legend=alt.Legend(title=None, orient="bottom")),
        opacity=alt.Opacity("health:Q", scale=alt.Scale(domain=[0.65, 1.0], range=[0.35, 1.0], clamp=True), legend=None),
        tooltip=[alt.Tooltip("cell:Q", title="Cell"), alt.Tooltip("health:Q", title="Health", format=".0%"), alt.Tooltip("state:N", title="State")]).add_params(pick)
    glyph = base.mark_text(color="white", fontSize=13, fontWeight="bold").encode(text="mark:N")
    return (rect + glyph).properties(height=400)


def voltage_chart(v_now: float, window: float):
    """One bar for the string voltage as a share of full, with the inverter floor as a rule. The axis starts at 40% so the gap to the floor is readable."""
    df = pd.DataFrame({"label": ["String voltage"], "v": [v_now], "floor": [window], "lo": [0.4]})
    ax = alt.Axis(format="%", title=None, values=[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], grid=False)
    bar = alt.Chart(df).mark_bar(cornerRadiusEnd=3, height=22, color=COLORS[0] if v_now >= window else COLORS[2]).encode(
        x=alt.X("lo:Q", scale=alt.Scale(domain=[0.4, 1.0]), axis=ax), x2="v:Q", y=alt.Y("label:N", axis=None))
    rule = alt.Chart(df).mark_rule(color="#444", strokeWidth=2, strokeDash=[4, 3]).encode(x="floor:Q")
    txt = alt.Chart(df).mark_text(align="right", dx=-4, dy=-18, fontSize=11, color="#444").encode(x="floor:Q", y=alt.Y("label:N", axis=None), text=alt.value("inverter floor"))
    return (bar + rule + txt).properties(height=100)


def policies_chart(plain_h: float, managed_h: float, shed_h: float):
    names = ["Plain string", "Cell-level", "Cell-level, half the load shed"]
    df = pd.DataFrame({"policy": names, "hours": [plain_h, managed_h, shed_h]})
    y = alt.Y("policy:N", sort=None, axis=alt.Axis(title=None, labelLimit=260))
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=3, size=26).encode(
        y=y, x=alt.X("hours:Q", axis=alt.Axis(title="Hours of backup at this load", grid=False, tickMinStep=2)),
        color=alt.Color("policy:N", scale=alt.Scale(domain=names, range=["#9aa3a8", COLORS[0], "#1f5f6b"]), legend=None))
    lab = alt.Chart(df).mark_text(align="left", dx=5, color="#444").encode(y=y, x="hours:Q", text=alt.Text("hours:Q", format=".1f"))
    return (bars + lab).properties(height=210)


TREND_CLASSES = ["Typical", "Fades faster than its neighbours", "Ends weakest"]
TREND_COLORS = ["#8aa9b0", "#d9922b", "#c0392b"]


def trend_frame(early, late, flagged, end_weakest: int) -> pd.DataFrame:
    e, l = np.asarray(early, float), np.asarray(late, float)
    rows = []
    for i in range(e.size):
        cls = TREND_CLASSES[2] if i == end_weakest else (TREND_CLASSES[1] if flagged[i] else TREND_CLASSES[0])
        rows.append(dict(cell=i, early=float(100 * e[i]), late=float(100 * l[i]), fade=float(100 * (e[i] - l[i])), cls=cls))
    return pd.DataFrame(rows)


def slope_lines_chart(early, late, flagged, end_weakest: int, km_early: int = 80, km_late: int = 280):
    """Each cell as a line from its early capacity to its late capacity; the cell that ends weakest and the fast faders are drawn heavier."""
    df = trend_frame(early, late, flagged, end_weakest)
    long = pd.concat([df.assign(age=f"{km_early},000 km", cap=df.early), df.assign(age=f"{km_late},000 km", cap=df.late)])
    long["order"] = long.cls.map({TREND_CLASSES[0]: 0, TREND_CLASSES[1]: 1, TREND_CLASSES[2]: 2})
    long = long.sort_values(["order", "cell"])
    return alt.Chart(long).mark_line(point=alt.OverlayMarkDef(size=18)).encode(
        x=alt.X("age:N", sort=[f"{km_early},000 km", f"{km_late},000 km"], axis=alt.Axis(title=None, labelAngle=0), scale=alt.Scale(padding=0.15)),
        y=alt.Y("cap:Q", scale=alt.Scale(zero=False), axis=alt.Axis(title="Capacity, % of day 1", grid=False)),
        detail="cell:N", color=alt.Color("cls:N", scale=alt.Scale(domain=TREND_CLASSES, range=TREND_COLORS), legend=alt.Legend(title=None, orient="bottom")),
        strokeWidth=alt.StrokeWidth("order:Q", scale=alt.Scale(domain=[0, 2], range=[1, 3.5]), legend=None), opacity=alt.Opacity("order:Q", scale=alt.Scale(domain=[0, 2], range=[0.4, 1.0]), legend=None),
        tooltip=[alt.Tooltip("cell:Q", title="Cell"), alt.Tooltip("early:Q", title="Early, %", format=".1f"), alt.Tooltip("late:Q", title="Late, %", format=".1f"), alt.Tooltip("fade:Q", title="Lost, points", format=".1f")]).properties(height=260)


def position_chart(early, late, flagged, end_weakest: int, local_median):
    """Left to right along the pack: each cell's fade against the median of its neighbours."""
    df = trend_frame(early, late, flagged, end_weakest)
    df["neighbours"] = np.asarray(local_median, float)
    base = alt.Chart(df).encode(x=alt.X("cell:Q", title="Position along the pack, left to right", axis=alt.Axis(grid=False)))
    pts = base.mark_circle(size=55, opacity=0.9).encode(
        y=alt.Y("fade:Q", title="Capacity lost, points of day 1", scale=alt.Scale(zero=True)),
        color=alt.Color("cls:N", scale=alt.Scale(domain=TREND_CLASSES, range=TREND_COLORS), legend=None),
        tooltip=[alt.Tooltip("cell:Q", title="Cell"), alt.Tooltip("fade:Q", title="Lost, points", format=".1f"), alt.Tooltip("neighbours:Q", title="Neighbours' median", format=".1f")])
    line = base.mark_line(color="#555", strokeWidth=1.5, strokeDash=[3, 2]).encode(y="neighbours:Q")
    return (line + pts).properties(height=220)


PAR_COLORS = ["#2a7f8e", "#5b8fc9", "#d9922b", "#8a6bbf"]


def gain_fade_chart(rows, claim_fade: float = 0.004):
    """12-year gain per kWh against cell fade per year, one line per cells-in-parallel. A cross marks HOLD (we would not recommend building it there); a dot marks Build.
    The vertical rule is the maker's own wear claim: left of the data is where it holds up. The y axis is a symmetric-log scale so the small wins and the big ones both show."""
    df = pd.DataFrame(rows)
    df["parallel_label"] = df.parallel.map(lambda p: "1 cell" if p == 1 else f"{p} in parallel")
    order = [("1 cell" if p == 1 else f"{p} in parallel") for p in sorted(df.parallel.unique())]
    df["Verdict"] = df.verdict.map({"BUY": "Build it", "BALANCER": "A balancer is enough", "HOLD": "Hold"})
    base = alt.Chart(df).encode(
        x=alt.X("fade:Q", title="Cell fade per year (share of capacity)", axis=alt.Axis(format=".3f", grid=False, values=sorted(df.fade.unique().tolist())), scale=alt.Scale(domain=[0.003, 0.021])),
        y=alt.Y("gain:Q", title="Extra 12-year gain over a balancer, $ per kWh", scale=alt.Scale(type="symlog", constant=2, domain=[-0.8, 260]), axis=alt.Axis(values=[0, 2, 5, 10, 25, 50, 100, 200], grid=True, gridOpacity=0.25)),
        color=alt.Color("parallel_label:N", scale=alt.Scale(domain=order, range=PAR_COLORS[:len(order)]), legend=alt.Legend(title=None, orient="bottom")))
    line = base.mark_line(strokeWidth=2)
    tip = [alt.Tooltip("parallel_label:N", title="Arrangement"), alt.Tooltip("fade:Q", title="Fade per year", format=".3f"), alt.Tooltip("gain:Q", title="Extra over a balancer, $/kWh", format=".1f"), alt.Tooltip("total:Q", title="Total over plain, $/kWh", format=".1f"), alt.Tooltip("p10:Q", title="Pessimistic total, $/kWh", format=".1f"), alt.Tooltip("Verdict:N")]
    built = base.transform_filter(alt.datum.Verdict == "Build it").mark_point(shape="circle", size=80, filled=True, opacity=1).encode(tooltip=tip)
    held = base.transform_filter(alt.datum.Verdict != "Build it").mark_point(shape="cross", size=150, filled=False, strokeWidth=3, opacity=1).encode(tooltip=tip)
    pts = built + held
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(color="#555", strokeDash=[4, 3]).encode(y="y:Q")
    claim = alt.Chart(pd.DataFrame({"x": [claim_fade], "t": ["maker's claim"]})).mark_rule(color="#999", strokeDash=[2, 3]).encode(x="x:Q")
    lab = alt.Chart(pd.DataFrame({"x": [claim_fade], "y": [150.0], "t": ["maker's claim"]})).mark_text(align="left", dx=5, color="#555", fontSize=11).encode(x="x:Q", y="y:Q", text="t:N")
    return (zero + claim + lab + line + pts).properties(height=420)


BAL_COLORS = {"Balancer alone": "#d9922b", "REON switches alone": "#2a7f8e", "Switches plus balancer": "#5b4b8a", "Our recommendation": "#1e2a2e"}


def balancer_chart(rows, assumed: float = 0.05):
    """12-year gain per kWh against balancer strength (share of a cell's capacity it can move per cycle), three lines. The vertical rule marks the strength we assumed (not sourced)."""
    df = pd.DataFrame(rows)
    df["pct"] = df.limit * 100
    order = list(BAL_COLORS)
    base = alt.Chart(df).encode(
        x=alt.X("pct:Q", title="Balancer strength: % of a cell's capacity it can move per cycle", axis=alt.Axis(values=sorted(df.pct.unique().tolist()), format=".3~g", grid=False)),
        y=alt.Y("gain:Q", title="12-year gain, $ per kWh", axis=alt.Axis(grid=True, gridOpacity=0.25)),
        color=alt.Color("series:N", scale=alt.Scale(domain=order, range=[BAL_COLORS[k] for k in order]), legend=alt.Legend(title=None, orient="bottom")))
    tip = [alt.Tooltip("series:N", title="Build"), alt.Tooltip("pct:Q", title="Balancer strength, %", format=".3~g"), alt.Tooltip("gain:Q", title="Gain, $/kWh", format=".1f"), alt.Tooltip("p10:Q", title="Pessimistic, $/kWh", format=".1f")]
    line = base.mark_line(strokeWidth=2.5)
    pts = base.mark_point(filled=True, size=70, opacity=1).encode(tooltip=tip)
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(color="#555", strokeDash=[4, 3]).encode(y="y:Q")
    rule = alt.Chart(pd.DataFrame({"x": [assumed * 100]})).mark_rule(color="#999", strokeDash=[2, 3]).encode(x="x:Q")
    top = float(df.gain.max())
    lab = alt.Chart(pd.DataFrame({"x": [assumed * 100], "y": [top], "t": ["assumed"]})).mark_text(align="left", dx=5, color="#555", fontSize=11).encode(x="x:Q", y="y:Q", text="t:N")
    return (zero + rule + lab + line + pts).properties(height=340)


def tile_map_chart(frame: pd.DataFrame, selected: str | None = None, title: str = "", fmt: str = ",.0f"):
    """US tile map: one square per state, one-hue ramp (light = little, dark = a lot), abbreviation in each tile, the selected state outlined. Click a tile to pick it (selection 'pick', field 'state').
    `frame` comes from hackkit.reon_map.tile_frame."""
    df = frame.copy()
    lo, hi = float(df.value.min()), float(df.value.max())
    df["dark"] = (df.value - lo) / ((hi - lo) or 1.0) > 0.55
    df["chosen"] = df.state == selected
    pick = alt.selection_point(name="pick", fields=["state"], on="click", clear=False)
    x = alt.X("col:O", axis=None, scale=alt.Scale(domain=list(range(12)), paddingInner=0.08))
    y = alt.Y("row:O", axis=None, scale=alt.Scale(domain=list(range(8)), paddingInner=0.08))
    tip = [alt.Tooltip("state:N", title="State"), alt.Tooltip("text:N", title=title or "Value"), alt.Tooltip("unit:N", title="Measure")]
    tiles = alt.Chart(df).mark_rect(cornerRadius=3).encode(
        x=x, y=y, color=alt.Color("value:Q", scale=alt.Scale(range=["#e3eef0", "#1f5e6b"]), legend=alt.Legend(title=title, orient="bottom", format=fmt, gradientLength=220, direction="horizontal")),
        stroke=alt.condition(alt.datum.chosen, alt.value("#c0392b"), alt.value("#ffffff")), strokeWidth=alt.condition(alt.datum.chosen, alt.value(3), alt.value(0.5)), tooltip=tip).add_params(pick)
    labels = alt.Chart(df).mark_text(fontSize=12, fontWeight="bold").encode(x=x, y=y, text="abbr:N", color=alt.condition(alt.datum.dark, alt.value("#ffffff"), alt.value("#1e2a2e")), tooltip=tip)
    return (tiles + labels).properties(height=440, width=720).configure_view(stroke=None)
