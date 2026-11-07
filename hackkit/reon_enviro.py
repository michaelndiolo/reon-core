"""Environmental number: battery cells NOT replaced because the string lasts longer, and the manufacturing carbon that avoids.

Wired through hackkit.reon_carbon (carbon_balance, sensitivity) so every input keeps its source tag.

    kWh of cells not bought = nameplate x horizon x (1 / life_plain - 1 / life_ours)      (replacement-equivalents over the horizon)
    carbon avoided          = that x share that would really have been replaced x embodied kg CO2e/kWh
    carbon spent            = embodied carbon of REON's control electronics (whole electronics, not only the extra over a BMS: conservative)

Sourced inputs (tags in docs/SOURCES.md):
    * Sodium-ion pack, cradle to gate, China, 56.8 kg CO2e/kWh; LFP pack 75.5 (about 25 % lower). Environmental Impact Assessment Review study,
      reported by ess-news.com. The study does not account for cycle life (we do that here). CITED.
    * Fraunhofer / RWTH 2025, cell level: sodium-ion 75-87 vs LFP 59-70 kg CO2e/kWh (the opposite ranking). Not strictly comparable (cell vs pack). CITED.
    * Embodied-carbon range used here: low 56.8, high 87.0, base = midpoint of the two sodium-ion figures (56.8 and the middle of 75-87 = 81) = 68.9. DERIVED.
ASSUMED (no source yet; wide on purpose): share of avoided cells that would really have been replaced (0.5 / 0.8 / 1.0), embodied carbon of the control
electronics (1 / 4 / 10 kg CO2e per kWh nameplate).
Nothing here claims a grid-emissions saving (set to zero)."""
from __future__ import annotations

from hackkit import reon_carbon as C
from hackkit.atstake import Lever

EMBODIED_LOW, EMBODIED_BASE, EMBODIED_HIGH = 56.8, 68.9, 87.0
DISPLACED_LOW, DISPLACED_BASE, DISPLACED_HIGH = 0.5, 0.8, 1.0
CONTROL_LOW, CONTROL_BASE, CONTROL_HIGH = 1.0, 4.0, 10.0   # kg CO2e per kWh nameplate


def cells_not_replaced(nameplate_kwh, life_plain, life_ours, horizon):
    """kWh of cells that do not have to be bought over `horizon` years (never negative). Lives in years; both capped at the horizon by the caller."""
    if nameplate_kwh <= 0 or life_plain <= 0 or life_ours <= 0 or horizon <= 0:
        raise ValueError("enviro: nameplate, lives and horizon must be positive")
    return max(0.0, nameplate_kwh * horizon * (1.0 / life_plain - 1.0 / life_ours))


def levers(nameplate_kwh, life_plain, life_ours, horizon):
    extra = cells_not_replaced(nameplate_kwh, life_plain, life_ours, horizon)
    return [
        Lever(C.EMBODIED, EMBODIED_BASE, EMBODIED_LOW, EMBODIED_HIGH, "CITED", "kg CO2e/kWh", "sodium-ion pack 56.8, Fraunhofer cell 75-87; base DERIVED midpoint"),
        Lever(C.EXTRA_KWH, extra, extra, extra, "CITED", "kWh", "from the engine's simulated service lives"),
        Lever(C.DISPLACED, DISPLACED_BASE, DISPLACED_LOW, DISPLACED_HIGH, "ASSUMED", "fraction", "share of avoided cells that would really have been replaced"),
        Lever(C.CONTROL_EMBODIED, CONTROL_BASE * nameplate_kwh, CONTROL_LOW * nameplate_kwh, CONTROL_HIGH * nameplate_kwh, "ASSUMED", "kg CO2e", "REON electronics, whole not incremental"),
        Lever(C.GRID_SAVED, 0.0, 0.0, 0.0, "ASSUMED", "t CO2e/yr", "no grid-emission saving claimed"),
        Lever(C.YEARS, float(horizon), float(horizon), float(horizon), "ASSUMED", "yr", "service horizon"),
    ]


def environmental(nameplate_kwh, life_plain, life_ours, horizon):
    """Dict: kwh_cells_avoided, net_t (base), low_t, high_t (all corners), sign_can_flip, avoided_t_base, control_t_base, table (one at a time)."""
    lv = levers(nameplate_kwh, life_plain, life_ours, horizon)
    s = C.sensitivity(lv)
    b = C.carbon_balance({l.name: l.base for l in lv})
    return {"kwh_cells_avoided": lv[1].base, "net_t": s["base_net_t"], "low_t": s["min_net_t"], "high_t": s["max_net_t"], "sign_can_flip": s["min_net_t"] < -1e-9,
            "avoided_t_base": b["items"]["Avoided new-battery manufacturing"], "control_t_base": -b["items"]["Control electronics (cost)"],
            "assumed": s["assumed_inputs"], "table": s["table"]}
