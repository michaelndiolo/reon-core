"""reon_unit: is cell-level control cheaper than the obvious alternative, adding more cells?

A conventional pack with weakest-cell limit delivers U. Control adds g x U of usable energy (g = the gain from the pack model). The nameplate is U x (1 + g),
because nameplate = sum of cells = N x mean and U = N x min. If the control electronics cost e per kWh of NAMEPLATE, the cost per extra usable kWh is
        e x (1 + g) / g
This is compared with c, what one extra kWh of capacity would cost another way (more retired cells, or new cells). Control is cheaper only when
        g > e / (c - e)        (never, if c <= e)
and the payback of the electronics in years is cost per extra kWh divided by the value of an extra kWh per year (from reon_econ / the price runs).
All of e, c and the value are inputs that must be sourced or flagged ASSUMED; nothing here is a default. Space, weight, voltage and balance limits of
adding cells, and cell supply limits, are NOT priced here: they are the reasons control can still win when this test says it should not.
Cost-bucket and levelizing idea (capital recovery plus operating cost per unit) follows the usual levelized-cost practice; credit for the framing prompt:
the Doshi post on reprocessing economics (secondary source; no numbers used from it).
"""
from __future__ import annotations

from typing import Optional

from .reon_econ import capital_recovery_factor


def cost_per_extra_kwh(electronics_per_kwh_nameplate: float, gain: float) -> float:
    """Cost of the control electronics per extra usable kWh it recovers: e x (1 + g) / g."""
    if electronics_per_kwh_nameplate < 0:
        raise ValueError("electronics cost cannot be negative")
    if gain <= 0:
        raise ValueError("gain must be positive (no gain: no extra kWh to pay for)")
    return electronics_per_kwh_nameplate * (1.0 + gain) / gain


def breakeven_gain(electronics_per_kwh_nameplate: float, alt_cost_per_kwh: float) -> Optional[float]:
    """Smallest gain at which control costs less per extra usable kWh than buying `alt_cost_per_kwh` of extra capacity. None if it never does."""
    e, c = electronics_per_kwh_nameplate, alt_cost_per_kwh
    if e < 0 or c <= 0:
        raise ValueError("need e >= 0 and c > 0")
    if c <= e:
        return None
    return e / (c - e)


def payback_years(cost_per_extra_kwh_: float, value_per_extra_kwh_year: float) -> float:
    """Years for the yearly value of an extra kWh to repay its cost (no discounting)."""
    if cost_per_extra_kwh_ < 0 or value_per_extra_kwh_year <= 0:
        raise ValueError("need cost >= 0 and value > 0")
    return cost_per_extra_kwh_ / value_per_extra_kwh_year


def levelized_cost_per_extra_kwh_year(cost_per_extra_kwh_: float, rate: float, years: float, om_per_kwh_year: float = 0.0) -> float:
    """Yearly cost of one extra usable kWh: cost x capital recovery factor(rate, years) + yearly operating cost. Compare with its yearly value."""
    if cost_per_extra_kwh_ < 0 or om_per_kwh_year < 0:
        raise ValueError("costs cannot be negative")
    return cost_per_extra_kwh_ * capital_recovery_factor(rate, years) + om_per_kwh_year


def repay_thresholds(gain: float, electronics_per_kwh_nameplate: float, value_per_kwh_year: float, rate: float, years: float) -> dict:
    """Where the 'does it repay?' verdict flips, one input at a time (decision-flip pattern from the hack kit notes).
    Repays when  e x (1 + g) / g x CRF  <=  value.  Returns the largest electronics cost, the smallest value, and the smallest gain at which it still repays
    (None if no gain is enough), and the extra loss the current gain can take before it stops repaying (None if it does not repay now)."""
    crf = capital_recovery_factor(rate, years)
    e, v, g = electronics_per_kwh_nameplate, value_per_kwh_year, gain
    out = {
        "max_electronics_per_kwh": v * g / ((1.0 + g) * crf) if g > 0 else 0.0,
        "min_value_per_kwh_year": (e * (1.0 + g) / g * crf) if g > 0 else None,
        "min_gain": (e * crf / (v - e * crf)) if v > e * crf else None,
    }
    mg = out["min_gain"]
    out["extra_loss_tolerated"] = (1.0 - (1.0 + mg) / (1.0 + g)) if (mg is not None and g > 0 and g >= mg) else None
    return out
