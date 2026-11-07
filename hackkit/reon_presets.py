"""Site presets for the string-life simulation. Every number is ASSUMED unless noted; docs/SOURCES.md has the tags. Fade is per year at about one cycle a day."""
PRESETS = {
    "C&I site, crew within reach": dict(visit_cost=500.0, lead=1.0, detect=0.0, down_cost=0.0, lam=0.01, fade=0.008, loss=0.02, slack=0.0),
    "Remote solar minigrid, no crew nearby": dict(visit_cost=3000.0, lead=3.0, detect=3.0, down_cost=20.0, lam=0.01, fade=0.008, loss=0.02, slack=0.0),
}
NOTES = {
    "visit_cost": "ASSUMED: cost of one crew visit; no public figure found (ESMAP, off-grid paper)",
    "lead": "ASSUMED: months from fault flagged to cell replaced (dispatch and repair)",
    "detect": "ASSUMED: months before a plain string notices a fault (REON sensing makes this zero)",
    "down_cost": "ASSUMED: cost per month the string is down, per kWh nameplate; energy value alone is about 3",
    "lam": "ASSUMED: faults per cell-year; EPRI gives 0.04 to 0.14 % a year for whole stationary systems",
    "fade": "ASSUMED: 0.004 to 0.012 follows from the 20,000-cycle claim (Tim Ren, unverified); lithium EVs measure about 0.02",
    "loss": "ASSUMED: switch conduction loss; Tim Ren says 'very minimum, not none'",
    "slack": "share of current the site can shed by stretching discharge; loss share falls in proportion (physics)",
}


def fade_per_year(cycles_per_day=1.0, temp_c=25.0, loss_per_1000_cycles=0.01, doubling_c=10.0):
    """Capacity fade per year implied by REON's cell claim and the site. 20,000 cycles to 80 % (Tim Ren, maker claim, unverified) = 0.01 of capacity per 1,000 cycles at 25 C.
    Temperature: the usual rule of thumb that ageing roughly doubles every 10 C (ASSUMED for sodium; not measured). Returns fraction of capacity per year."""
    if cycles_per_day < 0 or loss_per_1000_cycles < 0 or doubling_c <= 0:
        raise ValueError("fade_per_year: cycles, loss and doubling step must be positive")
    return loss_per_1000_cycles * cycles_per_day * 365.0 / 1000.0 * 2.0 ** ((temp_c - 25.0) / doubling_c)
