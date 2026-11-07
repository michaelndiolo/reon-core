"""Small Streamlit helpers shared by the app pages: headline tiles, the data-contract line, and 'what changed since the last plan'."""
from __future__ import annotations

from typing import Callable, List, Optional

import streamlit as st

from . import contract as K
from . import headline as H


def show_headline(metrics: List[H.Metric], only: Optional[List[str]] = None) -> None:
    """Draw metric tiles; `only` keeps just those labels (so a page can add the tiles it does not already show)."""
    ms = [m for m in metrics if only is None or m.label in only or any(m.label.startswith(o) for o in only)]
    H.render(st, ms)


def show_contract(findings: List[K.Finding], title: str = "Data contract") -> None:
    """One line when clean; a table (stop findings as an error) when not."""
    if not findings:
        st.caption(K.summary_line(findings))
        return
    box = st.error if K.has_stop(findings) else st.warning
    box(K.summary_line(findings) + (" Do not trust the plan until the 'stop' lines are explained." if K.has_stop(findings) else ""))
    with st.expander(title + ": what was found"):
        st.dataframe(K.report(findings), hide_index=True, use_container_width=True)


def show_last_change(key: str, plan, differ: Callable, title: str = "What changed since the last plan") -> None:
    """Keep the last plan that was shown under `key`; when a new plan differs, remember the plain-words diff and keep showing it
    (a Streamlit page reruns on every click, so a one-off message would vanish at once)."""
    ss = st.session_state
    ref = ss.get(key + "_ref")
    if ref is None:
        ss[key + "_ref"] = plan
    elif ref is not plan:
        try:
            d = differ(ref, plan)
        except ValueError:
            ss[key + "_ref"] = plan
            d = None
        if d is not None and not d.empty:
            ss[key + "_diff"] = d
            ss[key + "_ref"] = plan
    d = ss.get(key + "_diff")
    if d is not None:
        with st.expander(title):
            st.write(d.headline)
            for line in d.lines:
                st.write("- " + line)


def show_at_stake(res, money_unit: str = "") -> None:
    """The sentence for each baseline, which input matters most, and the full scenario table. Every input carries REAL or ASSUMED."""
    from . import atstake as A
    for b in res.baselines:
        (st.success if res.range(b)[0] > 0 else st.warning)(res.sentence(b, money_unit))
    st.caption(res.note)
    st.markdown("**Inputs varied**")
    st.dataframe(res.lever_table(), hide_index=True, use_container_width=True)
    st.markdown("**Which input moves the saving most** (one input changed at a time, the others at base)")
    st.dataframe(res.one_at_a_time.round(1), hide_index=True, use_container_width=True)
    with st.expander("Every combination tried"):
        st.dataframe(res.scenarios.round(2), hide_index=True, use_container_width=True)


def at_stake_panel(key: str, defaults, run: Callable, ctx: str, money_unit: str = "",
                   title: str = "Value at stake: how much does the plan save, and how sure are we?") -> None:
    """An expander with a low/high box and a REAL/ASSUMED choice for each input, a Compute button (it re-solves up to 15 times, so it only
    runs on a click) and the result. `ctx` identifies the current plan's inputs: a result computed for other inputs is not shown."""
    from . import atstake as A
    ss = st.session_state
    with st.expander(title):
        st.caption("Re-solves the plan with each uncertain input at its low, base and high value, so the saving is a range, not one number. "
                   "Mark an input REAL only if the range comes from a file, a filing or the sponsor.")
        levers = []
        for d in defaults:
            c1, c2, c3 = st.columns(3)
            lo = c1.number_input(f"{d.name}: low", value=float(d.low), key=f"{key}_{d.name}_lo")
            hi = c2.number_input(f"{d.name}: high", value=float(d.high), key=f"{key}_{d.name}_hi")
            src = c3.selectbox(f"{d.name}: source", A.SOURCES, index=A.SOURCES.index(d.source), key=f"{key}_{d.name}_src")
            levers.append(A.Lever(d.name, d.base, min(lo, d.base), max(hi, d.base), src, d.unit, d.note))
        if st.button("Compute value at stake", key=f"{key}_go"):
            try:
                with st.spinner("Re-solving the plan for each combination..."):
                    ss[key + "_res"] = (ctx, run(levers))
            except (ValueError, RuntimeError) as err:
                st.error(f"Could not compute it: {err}")
        got = ss.get(key + "_res")
        if got is not None:
            if got[0] == ctx:
                show_at_stake(got[1], money_unit)
            else:
                st.info("The plan's inputs changed since this was computed. Click Compute again.")
