"""Carbon value of cell-level control: manufacturing carbon avoided, minus the carbon of the control electronics, plus any grid
emissions saved by running the pack more cleverly. One balance, a hotspot table, and a one-at-a-time sweep that shows which input
dominates and whether the answer can change sign inside the ranges given.

THERE ARE NO DEFAULT NUMBERS HERE. The embodied carbon of a new battery (kg CO2e per kWh) and the share of the extra capacity that
would really have been bought new are the two inputs that decide the answer, and both must come from a named source (CITED) or be
flagged ASSUMED. Use atstake.Lever for each input so its source tag travels with it.

Accounting choices to state in the pitch (all ASSUMED here until sourced):
    * a retired pack is taken to carry NO manufacturing burden in its second life (the "cut-off" convention); other conventions
      split the first-life burden, which would lower the credit for reusing it;
    * 'extra capacity' only avoids a new battery if someone would otherwise have bought one (the displaced share).

Added 2026-11-07, two patterns (no code taken from anywhere):
    * origin-dependent embodied carbon: embodied = non_electric + electricity_per_kwh x grid intensity of the factory, so the credit depends on WHERE the
      displaced new cells would have been made. Pattern from the topic of a public LinkedIn post by an IBM summer intern (author not identified; the post
      gave titles only, no method) about monitoring and modeling supplier emissions;
    * flip points: the value of one input at which the net carbon crosses zero, from the participants' "decision-flip threshold" pattern.

Method credit (pattern only): hotspot table plus sensitivity analysis, as in cradle-to-gate LCA practice
(for example the sugar-kelp bioplastic LCA co-authored by R. Colwell, ACS Sustainable Chem. Eng. 2026, noted from his public page).
"""
from __future__ import annotations

import itertools
from typing import Dict, List, Sequence

import pandas as pd

from .atstake import Lever

EMBODIED = "Embodied carbon of a new battery (kg CO2e/kWh)"
EXTRA_KWH = "Extra usable capacity from control (kWh)"
DISPLACED = "Share of the extra capacity that would otherwise be new-built (fraction)"
CONTROL_EMBODIED = "Embodied carbon of the control electronics (kg CO2e)"
GRID_SAVED = "Grid emissions saved by smarter operation (t CO2e per year)"
YEARS = "Years of operation (yr)"
NAMES = (EMBODIED, EXTRA_KWH, DISPLACED, CONTROL_EMBODIED, GRID_SAVED, YEARS)


def carbon_balance(values: Dict[str, float]) -> dict:
    """Net tonnes CO2e over the pack's second life. Positive = control avoids carbon.
        avoided manufacturing = extra kWh x displaced share x kg/kWh / 1000
        control electronics   = kg / 1000                      (a cost)
        operation             = t per year x years
    """
    missing = [n for n in NAMES if n not in values]
    if missing:
        raise ValueError(f"missing inputs: {missing}")
    if not 0.0 <= values[DISPLACED] <= 1.0:
        raise ValueError("displaced share must be between 0 and 1")
    for n in (EMBODIED, EXTRA_KWH, CONTROL_EMBODIED, GRID_SAVED, YEARS):
        if values[n] < 0:
            raise ValueError(f"{n} cannot be negative")
    avoided = values[EXTRA_KWH] * values[DISPLACED] * values[EMBODIED] / 1000.0
    control = values[CONTROL_EMBODIED] / 1000.0
    operation = values[GRID_SAVED] * values[YEARS]
    items = {"Avoided new-battery manufacturing": avoided, "Control electronics (cost)": -control, "Cleaner operation": operation}
    return {"items": items, "net_t": avoided - control + operation}


def hotspots(values: Dict[str, float]) -> pd.DataFrame:
    """Each line of the balance, largest absolute size first, with its share of the total of the absolute sizes."""
    b = carbon_balance(values)
    mag = sum(abs(v) for v in b["items"].values())
    rows = [{"line": k, "tonnes_co2e": v, "share_of_absolute_total": (abs(v) / mag if mag > 0 else None)} for k, v in b["items"].items()]
    return pd.DataFrame(rows).sort_values("tonnes_co2e", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def _values(levers: Sequence[Lever], pick: str = "base") -> Dict[str, float]:
    return {l.name: getattr(l, pick) for l in levers}


def sensitivity(levers: Sequence[Lever]) -> dict:
    """One input at a time at its low and high (others at base), plus the lowest and highest net over EVERY combination of lows and
    highs (the balance is a sum of products, so its extremes sit at those corners). `sign_can_flip` is True if the net is negative
    somewhere in the ranges: then the sign of the carbon claim depends on guesses and the pitch must say so."""
    names = [l.name for l in levers]
    if sorted(names) != sorted(NAMES):
        raise ValueError(f"need exactly one lever for each of {list(NAMES)}")
    base = carbon_balance(_values(levers))["net_t"]
    rows = []
    for l in levers:
        v = _values(levers)
        v[l.name] = l.low
        lo = carbon_balance(v)["net_t"]
        v[l.name] = l.high
        hi = carbon_balance(v)["net_t"]
        rows.append({"input": l.name, "source": l.source, "net_at_low": lo, "net_at_high": hi, "swing": abs(hi - lo)})
    table = pd.DataFrame(rows).sort_values("swing", ascending=False).reset_index(drop=True)
    corners = [carbon_balance({l.name: pick for l, pick in zip(levers, combo)})["net_t"]
               for combo in itertools.product(*[(l.low, l.high) for l in levers])]
    return {"base_net_t": base, "table": table, "min_net_t": min(corners), "max_net_t": max(corners),
            "sign_can_flip": min(corners) < 0.0,
            "assumed_inputs": [l.name for l in levers if l.source == "ASSUMED"],
            "biggest_driver": table.iloc[0]["input"]}


# ---------------------------------------------------------------------------------------------------------------------------------
# Origin-dependent embodied carbon
# ---------------------------------------------------------------------------------------------------------------------------------

def embodied_at(grid_g_per_kwh: float, non_electric_kg_per_kwh: float, el_kwh_per_kwh: float) -> float:
    """kg CO2e per kWh of new battery made where the electricity emits `grid_g_per_kwh` g CO2e/kWh:
        embodied = non_electric + electricity used per kWh of battery x grid / 1000.
    All three inputs must be sourced or flagged ASSUMED by the caller; nothing is defaulted here."""
    for n, v in (("grid", grid_g_per_kwh), ("non_electric", non_electric_kg_per_kwh), ("el_kwh_per_kwh", el_kwh_per_kwh)):
        if v < 0:
            raise ValueError(f"{n} cannot be negative")
    return non_electric_kg_per_kwh + el_kwh_per_kwh * grid_g_per_kwh / 1000.0


def embodied_by_origin(shares: Dict[str, float], grid: Dict[str, float], non_electric_kg_per_kwh: float, el_kwh_per_kwh: float) -> dict:
    """Embodied carbon per region and for a mix. `shares` = fraction of displaced new cells made in each region (must sum to 1);
    `grid` = g CO2e/kWh for each region named in `shares`. Returns {'by_region', 'mix', 'cleanest', 'dirtiest'} in kg CO2e/kWh."""
    if not shares:
        raise ValueError("need at least one region")
    missing = [r for r in shares if r not in grid]
    if missing:
        raise ValueError(f"no grid intensity for: {missing}")
    if any(v < 0 for v in shares.values()) or abs(sum(shares.values()) - 1.0) > 1e-9:
        raise ValueError("shares must be nonnegative and sum to 1")
    by = {r: embodied_at(grid[r], non_electric_kg_per_kwh, el_kwh_per_kwh) for r in shares}
    mix = sum(shares[r] * by[r] for r in shares)
    return {"by_region": by, "mix": mix, "cleanest": min(by.values()), "dirtiest": max(by.values())}


def origin_lever(shares: Dict[str, float], grid: Dict[str, float], non_electric_kg_per_kwh: float, el_kwh_per_kwh: float,
                 source: str = "ASSUMED", note: str = "") -> Lever:
    """A Lever for `EMBODIED`: base = the mix, low = the cleanest listed region, high = the dirtiest. Use source='CITED' only if the shares
    and every other input are cited; a guessed mix makes the lever ASSUMED."""
    r = embodied_by_origin(shares, grid, non_electric_kg_per_kwh, el_kwh_per_kwh)
    return Lever(EMBODIED, r["mix"], r["cleanest"], r["dirtiest"], source, "kg CO2e/kWh", note)


# ---------------------------------------------------------------------------------------------------------------------------------
# Flip points
# ---------------------------------------------------------------------------------------------------------------------------------

def flip_point(levers: Sequence[Lever], name: str) -> dict:
    """Value of one input at which the net carbon is zero with every other input at base. The balance is linear in any single input, so
    two evaluations give it exactly. Returns {'input','base','flip_value','inside_range','net_at_base'}; flip_value is None when the net
    does not depend on that input. 'inside_range' = the flip value lies between that input's low and high, i.e. the sign claim really
    depends on a guess. Values outside the lever's own range are never fed to the balance."""
    names = [l.name for l in levers]
    if sorted(names) != sorted(NAMES):
        raise ValueError(f"need exactly one lever for each of {list(NAMES)}")
    lev = next(l for l in levers if l.name == name)
    vals = _values(levers)
    f0 = carbon_balance(vals)["net_t"]
    probe = lev.high if lev.high != lev.base else lev.low
    if probe == lev.base:
        return {"input": name, "base": lev.base, "flip_value": None, "inside_range": False, "net_at_base": f0}
    v1 = dict(vals)
    v1[name] = probe
    f1 = carbon_balance(v1)["net_t"]
    if f1 == f0:
        return {"input": name, "base": lev.base, "flip_value": None, "inside_range": False, "net_at_base": f0}
    x = lev.base - f0 * (probe - lev.base) / (f1 - f0)
    return {"input": name, "base": lev.base, "flip_value": x, "inside_range": min(lev.low, lev.high) <= x <= max(lev.low, lev.high), "net_at_base": f0}


def flip_table(levers: Sequence[Lever]) -> pd.DataFrame:
    """flip_point for every input, those whose flip value lies inside their own range first. (A missing flip value shows as NaN in the table.)"""
    rows = [flip_point(levers, l.name) for l in levers]
    df = pd.DataFrame(rows)
    return df.sort_values("inside_range", ascending=False, kind="stable").reset_index(drop=True)

