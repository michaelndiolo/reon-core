"""Backup energy through an outage: plain fixed string vs cell-level control (energy balance, no solar = conservative; Maine winter storm).
Plain string: usable = n x weakest cell. A cell that fails open (or hits a hard limit) takes the whole plain string offline: nothing without a crew.
Managed: usable = sum of cells x (1 - switch loss); a failed cell is bypassed and the rest keep going at (n-1)/n of the voltage, losing only that cell's remaining share.
Reduce power: shedding load to a fraction f stretches the same energy over 1/f the time.
Wear price of bypass: with fewer cells in the string, constant power means MORE CURRENT (x n/(n-k)) and a deeper discharge per remaining cell (x n/(n-k)); wear goes as (DoD)^g (g = DoD exponent, Iowa State fit 0.87 in this repo), heat as current squared."""
import numpy as np
from hackkit.reon_guard import caps_array, need
from hackkit.reon_window import window_usable


def usable_kwh(caps, nameplate_kwh: float, managed: bool, cold: float = 1.0, switch_loss: float = 0.02, window: float = None) -> float:
    c = caps_array(caps)
    need(nameplate_kwh > 0 and 0 < cold <= 1.5 and 0 <= switch_loss < 1, "storm: nameplate > 0, 0 < cold factor <= 1.5, 0 <= switch loss < 1")
    if managed and window is not None:   # inverter voltage window: at least window x n cells stay in the string, so at most floor(n (1 - window)) can be bypassed (cells treated as equal in voltage)
        need(0.0 < window <= 1.0, "storm: window must be above 0 and at most 1")
        n_min = len(c) - int(np.floor(len(c) * (1.0 - window) + 1e-9))
        base = window_usable(np.maximum(c, 1e-9), n_min) / len(c) * (1.0 - switch_loss)   # switch loss charged on ALL managed energy; the plain string has no switches
    else:
        base = c.mean() * (1.0 - switch_loss) if managed else c.min()
    return nameplate_kwh * base * cold


def hours(caps, nameplate_kwh: float, load_kw: float, managed: bool, cold: float = 1.0, fail_at_h=None, power_fraction: float = 1.0, switch_loss: float = 0.02, window: float = None) -> float:
    """Hours of supply at load_kw x power_fraction. fail_at_h: one cell fails open at that hour (None = no failure)."""
    caps = caps_array(caps)
    n = len(caps)
    e = usable_kwh(caps, nameplate_kwh, managed, cold, switch_loss, window)
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


def second_outage_hours(caps, nameplate_kwh: float, load_kw: float, recharge_kw: float, recharge_h: float, managed: bool, cold: float = 1.0, switch_loss: float = 0.02, window: float = None,
                        power_fraction: float = 1.0, failed: int = 0) -> float:
    """Back-to-back outages with a slow recovery in between. The first outage has emptied the string to its usable floor; the grid comes back for recharge_h hours and the charger puts in recharge_kw.
    Energy stored = the smaller of what the charger delivered (managed strings pay the switch loss on it) and what the string can hold (usable_kwh: the weakest cell for a plain string, the
    window rule for a managed one; failed = cells left open by the first outage). Hours of the second outage = stored / load. A plain energy budget: no rest-voltage rebound and no charge-rate limit on individual cells, and energy left in strong
    cells of a plain string after the first outage is ignored (conservative for plain)."""
    need(recharge_kw > 0 and recharge_h >= 0, "storm: recharge power must be above zero and recharge time not negative")
    need(load_kw > 0 and 0 < power_fraction <= 1, "storm: load must be above zero and the power fraction between 0 and 1")
    need(failed >= 0, "storm: failed cells must not be negative")
    cap_e = usable_kwh(caps, nameplate_kwh, managed, cold, switch_loss, window)
    if failed:   # a cell left open by the first outage: a plain string delivers nothing; a managed string bypasses it and loses that cell's share
        cap_e = 0.0 if not managed else cap_e * (len(caps_array(caps)) - failed) / len(caps_array(caps))
    put_in = recharge_kw * recharge_h * ((1.0 - switch_loss) if managed else 1.0)
    return float(min(put_in, cap_e) / (load_kw * power_fraction))


def stress_factors(n: int, k: int, g: float = 0.87) -> dict:
    """Extra stress on each remaining cell when k of n are bypassed for good at constant power."""
    need(0 <= k < n, "stress_factors: need 0 <= k < n")
    r = n / (n - k)
    return {"current_and_dod_x": r, "wear_rate_x": r ** g, "heat_x": r ** 2}
