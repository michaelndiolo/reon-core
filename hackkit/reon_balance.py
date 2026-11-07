"""Why not just balance? Passive and active balancers versus per-cell switching (Tim Ren, 7 Nov: power electronics loss goes as I squared R, so cost, copper and heat grow with current).
Passive: burns charge as heat, about 0.25 A at most, charge only. Active: moves charge, about 0.5 to 6 A, efficiency 0.89 to 0.91 at 3 A (Monolithic Power, https://www.monolithicpower.com/learning/resources/active-balancing-how-it-works-and-its-advantages).
To keep ONE weak cell in step the balancer must supply about load current x capacity gap (our approximation). Path resistance is ASSUMED so that efficiency is 0.90 at 3 A. Switches move no charge, so they have no such current limit (they pay a conduction loss instead)."""
from hackkit.reon_guard import need

PASSIVE_MAX_A = 0.25
ACTIVE_MAX_A = 6.0
V_CELL = 3.2
R_PATH = 0.10 * V_CELL / 3.0   # ohm, ASSUMED: efficiency 0.90 at 3 A


def needed_current(i_load_a, gap_frac, weak_cells=1):
    need(i_load_a >= 0 and 0 <= gap_frac < 1 and weak_cells >= 1, "balance: load >= 0, 0 <= gap < 1, weak cells >= 1")
    return i_load_a * gap_frac * weak_cells


def efficiency(i_b, r_path=R_PATH, v=V_CELL):
    need(i_b >= 0 and r_path >= 0 and v > 0, "balance: current, resistance >= 0 and v > 0")
    return max(0.0, 1.0 - i_b * r_path / v)


def hours_to_balance(imbalance_ah, i_b):
    need(imbalance_ah >= 0 and i_b > 0, "balance: imbalance >= 0 and current above zero")
    return imbalance_ah / i_b


def assess(cell_ah, c_rate, gap_frac, weak_cells=1):
    i_load = cell_ah * c_rate
    ib = needed_current(i_load, gap_frac, weak_cells)
    eff = efficiency(ib)
    return dict(load_a=i_load, needed_a=ib, passive_ok=ib <= PASSIVE_MAX_A, active_ok=ib <= ACTIVE_MAX_A, efficiency=eff, heat_w=ib * ib * R_PATH,
                energy_lost_pct_of_throughput=100.0 * gap_frac * (1.0 - eff), hours_passive_per_ah=1.0 / PASSIVE_MAX_A)
