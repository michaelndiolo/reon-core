"""One headline number per view: the three or four figures a person reads first, with the yardstick they are compared to.

Each metric is a plain object (label, value, unit, change against a named comparison, one sentence on what it means), so the same
numbers can be shown in the app, printed, or checked in a test. `render(st, metrics)` draws them with Streamlit's metric widget.

    flex_headline(plan)       energy scheduler: money saved vs doing nothing clever, peak import, battery cover, emissions
    split_headline(split)     where a saving comes from (demand charge, energy, regulation...), from reon_econ.value_split

Comparison baseline is the one already in the kit (baseline_asap for the scheduler), so the headline is never "a number alone".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from . import flex as F
from . import reon_econ as RE


@dataclass
class Metric:
    label: str
    value: float
    unit: str = ""
    decimals: int = 1
    delta: Optional[float] = None          # change against the comparison (value minus comparison, or saving, as stated in `vs`)
    delta_unit: str = ""
    vs: str = ""                           # what the delta is measured against, in words
    lower_is_better: bool = False
    help: str = ""
    delta_decimals: Optional[int] = None   # decimals for the change; defaults to the value's

    @property
    def value_text(self) -> str:
        return f"{self.value:,.{self.decimals}f}{self.unit}"

    @property
    def delta_text(self) -> Optional[str]:
        if self.delta is None:
            return None
        sign = "+" if self.delta >= 0 else "-"
        dd = self.decimals if self.delta_decimals is None else self.delta_decimals
        return f"{sign}{abs(self.delta):,.{dd}f}{self.delta_unit}" + (f" {self.vs}" if self.vs else "")


def flex_headline(plan: F.FlexPlan, baseline: Optional[dict] = None) -> List[Metric]:
    """baseline: the result of flex.evaluate_s for the do-nothing-clever schedule (computed here if not given)."""
    p = plan.problem
    if baseline is None:
        baseline = F.evaluate_s(p, F.baseline_asap(p))
    out: List[Metric] = []
    base_money = float(baseline["money"])
    saved = base_money - plan.money
    pct = 100.0 * saved / abs(base_money) if abs(base_money) > 1e-9 else 0.0
    out.append(Metric("Saved vs doing nothing clever", saved, "", 0, pct, "%", "of the baseline bill", False,
                      "Money saved over this horizon against running everything as soon as it is wanted, scored on the same bill. Comfort misses are shown separately.", 1))
    base_peak = float(baseline["peak_import_mw"])
    out.append(Metric("Highest import", plan.peak_mw, " MW", 2, plan.peak_mw - base_peak, " MW", "vs baseline", True,
                      "The largest power drawn from the grid in any step; this is what a demand charge bills."))
    if p.battery is not None:
        load = float(np.mean(p.base_load))
        usable = p.battery.energy_mwh * (1.0 - p.battery.soc_min_frac) * p.battery.eff_discharge
        out.append(Metric("Battery cover", usable / max(load, 1e-9), " h", 1, None, "", "", False,
                          "Hours the battery alone could carry the site's average fixed load, from full to its lowest allowed charge."))
    if np.any(p.carbon != 0):
        d = (plan.carbon_kg - float(baseline["carbon_kg"])) / 1000.0
        out.append(Metric("Emissions", plan.carbon_kg / 1000.0, " t", 2, d, " t", "vs baseline", True,
                          "Tonnes of CO2 from grid energy bought over the horizon, using the carbon series given (average mix, not marginal)."))
    return out


def split_headline(split: dict, top: int = 3, unit: str = "") -> List[Metric]:
    """Tiles for the net saving and its biggest sources, from reon_econ.value_split. A saving shown without its source invites the
    question 'which assumption is doing the work?', so the biggest contributors (by absolute size, sign kept) sit beside the total."""
    out: List[Metric] = [Metric("Net saving", split["total"], unit, 0, None, "", "", False,
                                "Total saving over the window: every line below added up, costs avoided plus revenue gained.")]
    ranked = sorted(split["items"].items(), key=lambda kv: abs(kv[1]), reverse=True)
    for k, v in ranked[:top]:
        if abs(v) < 1e-9:
            continue
        share = split["share"][k]
        out.append(Metric(RE.LABELS[k], v, unit, 0, None if share is None else 100.0 * share, "%", "of net saving", False,
                          "Share of the net saving from this line; a negative value means this line got worse while the others improved.", 0))
    return out


def render(st, metrics: List[Metric], columns: Optional[int] = None) -> None:
    """Draw the metrics in a row with Streamlit (st is the streamlit module or any object with columns() and metric())."""
    if not metrics:
        return
    cols = st.columns(columns or len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(m.label, m.value_text, m.delta_text, delta_color="inverse" if m.lower_is_better else "normal", help=m.help or None)
