"""Backup energy through an outage: plain fixed string vs cell-level control (energy balance, no solar = conservative; Maine winter storm).
Plain string: usable = n x weakest cell. A cell that fails open (or hits a hard limit) takes the whole plain string offline: nothing without a crew.
Managed: usable = sum of cells x (1 - switch loss); a failed cell is bypassed and the rest keep going at (n-1)/n of the voltage, losing only that cell's remaining share.
Reduce power: shedding load to a fraction f stretches the same energy over 1/f the time.
Wear price of bypass: with fewer cells in the string, constant power means MORE CURRENT (x n/(n-k)) and a deeper discharge per remaining cell (x n/(n-k)); wear goes as (DoD)^g (g = DoD exponent, Iowa State fit 0.87 in this repo), heat as current squared."""
import numpy as np
from hackkit.reon_guard import caps_array, need


def usable_kwh(caps, nameplate_kwh: float, managed: bool, cold: float = 1.0, switch_loss: float = 0.02) -> float:
    c = caps_array(caps)
    need(nameplate_kwh > 0 and 0 < cold <= 1.5 and 0 <= switch_loss < 1, "storm: nameplate > 0, 0 < cold factor <= 1.5, 0 <= switch loss < 1")
    base = c.mean() * (1.0 - switch_loss) if managed else c.min()
    return nameplate_kwh * base * cold


def hours(caps, nameplate_kwh: float, load_kw: float, managed: bool, cold: float = 1.0, fail_at_h=None, power_fraction: float = 1.0, switch_loss: float = 0.02) -> float:
    """Hours of supply at load_kw x power_fraction. fail_at_h: one cell fails open at that hour (None = no failure)."""
    caps = caps_array(caps)
    n = len(caps)
    e = usable_kwh(caps, nameplate_kwh, managed, cold, switch_loss)
    need(load_kw > 0 and 0 < power_fraction <= 1, "storm: load must be above zero and the power fraction between 0 and 1")
    need(fail_at_h is None or fail_at_h >= 0, "storm: failure hour must be zero or more")
    p = load_kw * power_fraction
    t = e / p
    if fail_at_h is None or t <= fail_at_h:
        return t
    if not managed:
        return float(fail_at_h)
    left = (e - p * fail_at_h) * (n - 1) / n
    return float(fail_at_h + left / p)


def stress_factors(n: int, k: int, g: float = 0.87) -> dict:
    """Extra stress on each remaining cell when k of n are bypassed for good at constant power."""
    need(0 <= k < n, "stress_factors: need 0 <= k < n")
    r = n / (n - k)
    return {"current_and_dod_x": r, "wear_rate_x": r ** g, "heat_x": r ** 2}
