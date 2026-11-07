"""Value at stake: how much the plan saves against a named baseline, as a RANGE over the inputs we are not sure of.

A single saving number built on guessed inputs does not survive a sponsor's first question. This module re-solves the plan with each
uncertain input at its low, base and high value, and reports:

    - the saving in the base case, and the lowest and highest saving over all the combinations of low/high;
    - which input moves the saving most (one input changed at a time);
    - every input marked REAL (from a file or filing) or ASSUMED (a guess), so nobody mistakes a guess for a fact.

It never invents a number: the ranges are the ones the user types in. A range of "x0.5 to x2" on an assumed cost is a statement
about what we do not know, not a forecast.

    levers = [Lever("Lateness cost", 1.0, 0.5, 2.0, "ASSUMED", unit="x current")]
    res = campaign_at_stake(campaign, levers)            # plan vs the simple build-what-is-owed rule
    print(res.sentence("rule", "EUR k"))

At most 3 levers (2 per side makes 1 + 8 corners + 6 one-at-a-time = 15 re-solves at most).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

MAX_LEVERS = 3
SOURCES = ("REAL", "CITED", "ASSUMED")


@dataclass
class Lever:
    name: str
    base: float
    low: float
    high: float
    source: str = "ASSUMED"          # "REAL" = a file, filing or the sponsor; "CITED" = a named published source; "ASSUMED" = a guess
    unit: str = ""
    note: str = ""

    def __post_init__(self):
        if self.source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        if not (self.low <= self.base <= self.high):
            raise ValueError(f"{self.name}: need low <= base <= high, got {self.low}, {self.base}, {self.high}")


@dataclass
class AtStake:
    levers: List[Lever]
    baselines: List[str]
    scenarios: pd.DataFrame            # one row per scenario: lever values, plan cost, cost of each baseline, saving per baseline
    one_at_a_time: pd.DataFrame        # per baseline and lever: saving at low and at high, others at base
    note: str = ""

    def base_row(self) -> pd.Series:
        return self.scenarios[self.scenarios["scenario"] == "base"].iloc[0]

    def range(self, baseline: str):
        s = self.scenarios[f"saving vs {baseline}"]
        return float(s.min()), float(self.base_row()[f"saving vs {baseline}"]), float(s.max())

    def all_real(self) -> bool:
        return all(l.source == "REAL" for l in self.levers)

    def sentence(self, baseline: str, money_unit: str = "") -> str:
        lo, base, hi = self.range(baseline)
        u = f" {money_unit}" if money_unit else ""
        base_cost = float(self.base_row()[f"cost of {baseline}"])
        pct = f" ({100 * base / abs(base_cost):.0f}% of that baseline's cost)" if abs(base_cost) > 1e-9 else ""
        if lo > 0:
            span = f"and stays positive across every combination tried: from {lo:,.0f}{u} to {hi:,.0f}{u}"
        elif hi < 0:
            span = f"but it is negative in every combination tried: {lo:,.0f}{u} to {hi:,.0f}{u}"
        else:
            span = f"but the sign is not settled: from {lo:,.0f}{u} (plan worse than the baseline) to {hi:,.0f}{u}"
        assumed = [l.name for l in self.levers if l.source == "ASSUMED"]
        tail = ("All inputs varied are REAL." if not assumed else
                f"ASSUMED inputs: {', '.join(assumed)}. This is the size of the prize if those guesses are right, not a forecast.")
        return f"Against {baseline}, the plan saves {base:,.0f}{u}{pct} in the base case, {span}. {tail}"

    def lever_table(self) -> pd.DataFrame:
        return pd.DataFrame([{"input": l.name, "low": l.low, "base": l.base, "high": l.high, "unit": l.unit,
                              "REAL or ASSUMED": l.source, "note": l.note} for l in self.levers])


def value_at_stake(levers: Sequence[Lever], evaluate: Callable[[Dict[str, float]], Dict[str, float]],
                   baselines: Sequence[str], note: str = "") -> AtStake:
    """evaluate(values) -> {"plan": cost of the plan, <baseline>: cost of that baseline} with every lever set to values[lever.name].
    Costs are what the user pays (lower is better), so saving = baseline cost - plan cost."""
    levers = list(levers)
    if not 1 <= len(levers) <= MAX_LEVERS:
        raise ValueError(f"give 1 to {MAX_LEVERS} inputs to vary")
    if len({l.name for l in levers}) != len(levers):
        raise ValueError("input names must be unique")
    base = {l.name: l.base for l in levers}
    cache: Dict[tuple, Dict[str, float]] = {}

    def run(vals: Dict[str, float]):
        key = tuple(round(vals[l.name], 12) for l in levers)
        if key not in cache:
            cache[key] = evaluate(dict(vals))
        return cache[key]

    rows = []

    def add(tag: str, vals: Dict[str, float]):
        r = run(vals)
        row = {"scenario": tag, **{l.name: vals[l.name] for l in levers}, "plan cost": r["plan"]}
        for b in baselines:
            row[f"cost of {b}"] = r[b]
            row[f"saving vs {b}"] = r[b] - r["plan"]
        rows.append(row)

    add("base", base)
    for combo in itertools.product(*[(l.low, l.high) for l in levers]):
        vals = {l.name: v for l, v in zip(levers, combo)}
        if vals != base:
            add("corner: " + ", ".join(f"{l.name}={'low' if v == l.low else 'high'}" for l, v in zip(levers, combo)), vals)
    oat = []
    for l in levers:
        for side, v in (("low", l.low), ("high", l.high)):
            vals = dict(base); vals[l.name] = v
            r = run(vals)
            for b in baselines:
                oat.append({"baseline": b, "input": l.name, "side": side, "value": v, "saving": r[b] - r["plan"]})
    oat_df = pd.DataFrame(oat)
    wide = []
    for (b, name), g in oat_df.groupby(["baseline", "input"], sort=False):
        lo_s = float(g[g.side == "low"].saving.iloc[0]); hi_s = float(g[g.side == "high"].saving.iloc[0])
        wide.append({"baseline": b, "input": name, "saving at low": lo_s, "saving at high": hi_s, "swing": abs(hi_s - lo_s)})
    one = pd.DataFrame(wide).sort_values(["baseline", "swing"], ascending=[True, False]).reset_index(drop=True)
    return AtStake(levers, list(baselines), pd.DataFrame(rows), one, note)


# ---------------------------------------------------------------- campaign (delivery planner, install sequencing)

CAMPAIGN_LEVERS = ("Lateness cost", "Holding cost")


def _scaled(c, late_x: float, hold_x: float):
    from . import campaign as C
    fams = [replace(f, late_penalty=C.late_penalty(f) * late_x, hold_cost=f.hold_cost * hold_x) for f in c.families]
    return c.copy(families=fams)


def _avoidable(c, produce, ship, bridge=None, expired=None) -> float:
    """Cost the user actually bears: value forgone against the full profit of what was shipped (lateness, holding, material holding, spot buys)."""
    from . import campaign as C
    s = C.score(c, produce, ship, bridge, expired)
    gross = sum(f.profit * ship[i].sum() for i, f in enumerate(c.families))
    return float(gross - s["value"])


def campaign_at_stake(c, levers: Sequence[Lever], reference=None, with_keep_plan: bool = False, setup: bool = False,
                      time_limit: float = 20.0) -> AtStake:
    """Plan vs (a) the simple rule 'build only what is owed, oldest first' and, if with_keep_plan, (b) the plan made for `reference`
    (e.g. before a grid date slipped) kept as it was. Lever names: 'Lateness cost' and 'Holding cost' are multipliers on every family's
    current number. Costs are avoidable cost (lateness + holding + spot buys), so the saving is the same difference the plan diff shows."""
    from . import campaign as C
    unknown = [l.name for l in levers if l.name not in CAMPAIGN_LEVERS]
    if unknown:
        raise ValueError(f"campaign levers must be named {CAMPAIGN_LEVERS}, got {unknown}")
    has_spot = any(m.spot_cap > 0 for m in c.materials)
    kept = None
    if with_keep_plan:
        ref = reference if reference is not None else c
        kept = C.solve_campaign(ref, setup=setup, time_limit=time_limit).produce.to_numpy()

    def evaluate(v):
        cs = _scaled(c, v.get("Lateness cost", 1.0), v.get("Holding cost", 1.0))
        plan = C.solve_campaign(cs, setup=setup, time_limit=time_limit)
        br = None if plan.bridge is None else plan.bridge.to_numpy()
        ex = None if plan.expired is None else plan.expired.to_numpy()
        out = {"plan": _avoidable(cs, plan.produce.to_numpy(), plan.ship.to_numpy(), br, ex)}
        rp, rs, rbr = C.edd_rule(cs, use_bridge=has_spot, return_bridge=True)
        out["simple rule"] = _avoidable(cs, rp, rs, rbr if has_spot else None)
        if kept is not None:
            out["old plan kept"] = _avoidable(cs, kept, C.execute(cs, kept))
        return out
    names = ["simple rule"] + (["old plan kept"] if kept is not None else [])
    return value_at_stake(levers, evaluate, names,
                          note="Avoidable cost = lateness + holding + spot buys, in the campaign's own money units. The 'simple rule' builds only what is owed.")


# ---------------------------------------------------------------- energy scheduler

FLEX_LEVERS = ("Demand charge ($/kW-month)", "Energy price (x)")


def flex_at_stake(p, levers: Sequence[Lever], with_rule: bool = True) -> AtStake:
    """Plan vs 'doing nothing clever' (and a price-level rule tuned on the base case, if with_rule). Lever names:
    'Demand charge ($/kW-month)' sets the demand rate; 'Energy price (x)' multiplies every price in the window."""
    from . import flex as F
    unknown = [l.name for l in levers if l.name not in FLEX_LEVERS]
    if unknown:
        raise ValueError(f"flex levers must be named {FLEX_LEVERS}, got {unknown}")
    if any(l.name == "Demand charge ($/kW-month)" for l in levers) and p.demand_charge is None:
        raise ValueError("this problem has no demand charge, so that input cannot be varied")
    rule = F.tune_rule([p], grid=4) if with_rule else None

    def evaluate(v):
        q = p
        if "Energy price (x)" in v:
            q = replace(q, price=np.asarray(p.price, float) * v["Energy price (x)"])
        if "Demand charge ($/kW-month)" in v and p.demand_charge is not None:
            q = replace(q, demand_charge=replace(p.demand_charge, rate_per_kw_month=v["Demand charge ($/kW-month)"]))
        plan = F.solve_flex(q, with_values=False)
        out = {"plan": float(plan.money), "doing nothing clever": float(F.evaluate_s(q, F.baseline_asap(q))["money"])}
        if rule is not None:
            out["tuned rule"] = float(F.replay(q, q.price, policy="rule", rule=rule)["money"])
        return out
    names = ["doing nothing clever"] + (["tuned rule"] if rule is not None else [])
    return value_at_stake(levers, evaluate, names,
                          note="Costs are the bill over the window. The tuned rule is tuned on the base case, which flatters it.")
