"""System-level view (REON, 7 Nov): the business case is energy per charge and how many charges the SYSTEM lasts, not how long a cell lasts. A cell may be rated 20,000 cycles while the system guarantee is 8,000, because the weakest cell sets the system.
Works on the table that reon_wear.recommend_build returns (years = service life of each build, retire at eol_frac of day-1)."""
from hackkit.reon_guard import need

OURS_PREFIX = ("selective", "late", "level", "hybrid")


def incremental_share(bms_multiple):
    """REON: REON's electronics cost 3 to 4 times a conventional BMS. A customer buying a plain string buys a BMS anyway, so the extra cost is (k - 1) / k of the total."""
    need(bms_multiple >= 1.0, "system: BMS multiple must be at least 1")
    return (bms_multiple - 1.0) / bms_multiple


def incremental_cost(total_per_kwh, bms_multiple):
    return total_per_kwh * incremental_share(bms_multiple)


def system_view(table, cycles_per_day=1.0, duty=0.7, cell_rated_cycles=20000.0, capex_per_kwh=98.0):
    need(cycles_per_day > 0 and 0 < duty <= 1 and cell_rated_cycles > 0 and capex_per_kwh >= 0 and "plain" in table, "system: positive cycles, duty in (0, 1], a plain row in the table")
    rows = {}
    for name, v in table.items():
        cyc = v["years"] * 365.0 * cycles_per_day
        life_kwh = cyc * duty
        cost = capex_per_kwh + (v.get("cost", 0.0) if name.startswith(OURS_PREFIX) else 0.0)
        rows[name] = dict(years=v["years"], system_cycles=cyc, share_of_cell_rating=cyc / cell_rated_cycles, lifetime_kwh_per_kwh_nameplate=life_kwh, cost_per_kwh_delivered=cost / life_kwh if life_kwh > 0 else float("inf"))
    return rows
