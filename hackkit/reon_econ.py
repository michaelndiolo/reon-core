"""Economics of cell-level control for a battery pack, built on the scheduler (flex.py) and plain finance (finance.py).

The question Reon asks is: what is the extra usable capacity of a pack under cell-level control worth, against a conventional BMS?
This module turns a pair of capacities (from the pack model in recheck/SPEC.md; reon_loss.py, reon_report.py or the app's pack.py can supply them) into money, and keeps every claim honest:

    control_value        run the scheduler with the conventional capacity and with the control capacity on the same site and prices;
                         the difference in bill is what control is worth over that window. Regulation is OFF unless asked for.
    value_split          where a saving comes from (demand charge, energy arbitrage, regulation, wear, comfort), so a headline never
                         hides that one assumed tariff line is doing all the work.
    size_vs_peak         saving as a function of battery power relative to the site's own peak load (a 1 MW battery means little
                         at a 33 MW site and a lot at a 3 MW one).
    heldout_scores       planner vs a rule tuned WITHOUT the window being scored (leave-one-window-out), win count and a bootstrap
                         range. Never score a policy on the data its rule was tuned on.
    life_extension_value the yearly value of a longer pack life (equivalent annual cost, capital recovery factor).
    control_npv          NPV, payback and break-even cost of the control electronics, via finance.py.

Nothing here knows a number the caller did not give it. Label every input REAL (sponsor/public data), CITED (a named source) or ASSUMED.

Method credit (patterns only, no code copied): scoring on held-out months rather than resamples, and reporting the cost-regime split
(demand charge vs regulation vs energy), follow Gardner & Taylor, "Stochastic Model Predictive Control for Commercial Battery Systems"
(BU EC701 course project, April 2026 - a student paper, not peer reviewed), which replicates Kumar et al., IEEE Trans. Power Systems 2018.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import finance as FIN
from . import flex as F

COST_ITEMS = ("energy", "demand_charge", "wear", "comfort_cost")          # a lower number is a saving
REVENUE_ITEMS = ("export_revenue", "regulation_revenue")                  # a higher number is a saving
LABELS = {"energy": "Energy bought", "demand_charge": "Demand charge", "wear": "Battery wear", "comfort_cost": "Comfort",
          "export_revenue": "Export revenue", "regulation_revenue": "Regulation revenue"}


# ---------- where a saving comes from ----------

def value_split(plan_components: Dict[str, float], baseline_components: Dict[str, float]) -> dict:
    """Saving by source: baseline minus plan for every cost line, plan minus baseline for every revenue line.
    `share` is each line's part of the NET saving (it can be negative or above 100%, e.g. extra energy bought to cover losses
    while the demand charge falls by more). Share is None when the net saving is about zero (a share of nothing means nothing)."""
    items: Dict[str, float] = {}
    for k in COST_ITEMS:
        items[k] = float(baseline_components.get(k, 0.0)) - float(plan_components.get(k, 0.0))
    for k in REVENUE_ITEMS:
        items[k] = float(plan_components.get(k, 0.0)) - float(baseline_components.get(k, 0.0))
    total = float(sum(items.values()))
    scale = max(1.0, max(abs(float(baseline_components.get(k, 0.0))) for k in list(COST_ITEMS) + list(REVENUE_ITEMS)))
    share = {k: (v / total if abs(total) > 1e-9 * scale else None) for k, v in items.items()}
    return {"items": items, "total": total, "share": share}


def split_table(split: dict) -> pd.DataFrame:
    """The split as a small table, biggest absolute contribution first."""
    rows = [{"source": LABELS[k], "saving": v, "share of net": split["share"][k]} for k, v in split["items"].items()]
    return pd.DataFrame(rows).sort_values("saving", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


# ---------- what control is worth ----------

@dataclass
class ControlValue:
    saving_money: float            # conventional bill minus control bill over the window (positive = control is worth it)
    saving_objective: float        # same, on the scheduler's objective (includes any carbon price and comfort cost)
    conventional: F.FlexPlan
    control: F.FlexPlan
    split: dict                    # value_split(control, conventional)
    horizon_hours: float
    regulation: bool


def control_value(p: F.FlexProblem, conv_mwh: float, ctrl_mwh: float, power_mw: Optional[float] = None,
                  use_regulation: bool = False, **battery_kw) -> ControlValue:
    """Same site, same prices, same power rating; only the usable energy differs (conventional vs control).
    conv_mwh and ctrl_mwh come from the pack model. Regulation is OFF by default: the scheduler plans it with no commitment
    notice, which flatters it, and it was a small share of the saving on real windows. battery_kw replaces other Battery fields
    (for example soc_min_frac for a reserve, eff_charge/eff_discharge)."""
    if p.battery is None:
        raise ValueError("the problem needs a battery to start from (its power rating and efficiencies are used)")
    if conv_mwh <= 0 or ctrl_mwh <= 0:
        raise ValueError("capacities must be positive")
    if ctrl_mwh < conv_mwh - 1e-12:
        raise ValueError("control capacity is below the conventional capacity; check the pack model")
    q = p if use_regulation else p.copy(reg_price=None)
    pw = p.battery.power_mw if power_mw is None else power_mw
    conv = F.solve_flex(q.copy(battery=replace(p.battery, energy_mwh=conv_mwh, power_mw=pw, **battery_kw)), with_values=False)
    ctrl = F.solve_flex(q.copy(battery=replace(p.battery, energy_mwh=ctrl_mwh, power_mw=pw, **battery_kw)), with_values=False)
    return ControlValue(saving_money=conv.money - ctrl.money, saving_objective=conv.objective - ctrl.objective,
                        conventional=conv, control=ctrl, split=value_split(ctrl.components, conv.components),
                        horizon_hours=p.T * p.step_hours, regulation=use_regulation)


def annualize(saving: float, horizon_hours: float, hours_per_year: float = 8760.0) -> float:
    """Scale a saving over a window to a year. Only honest if the window is typical of the year; say so (ASSUMED) when you use it."""
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    return saving * hours_per_year / horizon_hours


# ---------- size relative to the site ----------

def size_vs_peak(p: F.FlexProblem, power_fractions: Sequence[float], duration_h: float = 2.0, peak_mw: Optional[float] = None,
                 use_regulation: bool = False, **battery_kw) -> pd.DataFrame:
    """Saving against doing nothing as battery power grows relative to the site's own peak load. Energy = power x duration_h.
    peak_mw defaults to the highest grid import with the battery idle. Returns one row per fraction."""
    if p.battery is None:
        raise ValueError("the problem needs a battery to start from")
    q = p if use_regulation else p.copy(reg_price=None)
    base = F.evaluate_s(q, F.baseline_asap(q))
    peak = float(base["peak_import_mw"]) if peak_mw is None else float(peak_mw)
    if peak <= 0:
        raise ValueError("the site peak is zero; nothing to size against")
    rows = []
    for f in power_fractions:
        if f <= 0:
            raise ValueError("power fractions must be positive")
        pw = f * peak
        plan = F.solve_flex(q.copy(battery=replace(q.battery, power_mw=pw, energy_mwh=pw * duration_h, **battery_kw)), with_values=False)
        saved = float(base["money"]) - plan.money
        rows.append({"power_fraction_of_peak": f, "power_mw": pw, "energy_mwh": pw * duration_h, "saving": saved,
                     "saving_pct": 100.0 * saved / abs(base["money"]) if abs(base["money"]) > 1e-9 else 0.0,
                     "peak_after_mw": plan.peak_mw})
    return pd.DataFrame(rows)


# ---------- never score a policy on the data its rule was tuned on ----------

def heldout_scores(windows: List[F.FlexProblem], price_forecasts: Optional[List[np.ndarray]] = None, horizon: int = 24,
                   grid: int = 3, n_boot: int = 2000, seed: int = 0) -> dict:
    """Leave-one-window-out. For each window the price-level rule is tuned on the OTHER windows only, then the rolling planner and
    the rule are both run on the held-out window and scored on the scheduler's adjusted objective (lower is better).
    price_forecasts: what the planner is allowed to see for each window (default = the true prices, i.e. a perfect forecast, which
    makes the planner's edge an upper bound; pass day-ahead prices to be fair). Returns per-window rows, the win count, the mean
    improvement over the rule (% of the rule's cost) and a 90% bootstrap range over windows."""
    n = len(windows)
    if n < 3:
        raise ValueError("need at least 3 windows to hold one out and still tune on two")
    if price_forecasts is not None and len(price_forecasts) != n:
        raise ValueError("one price forecast per window")
    rows = []
    for i, w in enumerate(windows):
        rule = F.tune_rule([q for j, q in enumerate(windows) if j != i], grid=grid)
        pf = w.price if price_forecasts is None else np.asarray(price_forecasts[i], float)
        r_rule = F.replay(w, pf, policy="rule", rule=rule)
        r_plan = F.replay(w, pf, policy="planner", horizon=horizon)
        rule_obj, plan_obj = F.adjusted_objective(w, r_rule), F.adjusted_objective(w, r_plan)
        rows.append({"window": i, "rule_cost": rule_obj, "planner_cost": plan_obj,
                     "improvement_pct": 100.0 * (rule_obj - plan_obj) / abs(rule_obj) if abs(rule_obj) > 1e-9 else 0.0})
    df = pd.DataFrame(rows)
    imp = df["improvement_pct"].to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([imp[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.quantile(boots, [0.05, 0.95])
    return {"windows": df, "planner_wins": int((imp > 0).sum()), "n_windows": n, "mean_improvement_pct": float(imp.mean()),
            "range_pct_90": (float(lo), float(hi)),
            "note": ("Planner saw the TRUE prices (perfect forecast): its edge is an upper bound." if price_forecasts is None
                     else "Planner saw only the supplied forecasts.")}


# ---------- a longer life, and the control electronics as an investment ----------

def capital_recovery_factor(rate: float, years: float) -> float:
    """Yearly payment that repays 1 of capital over `years` at `rate` (rate 0 = straight line)."""
    if years <= 0:
        raise ValueError("years must be positive")
    if abs(rate) < 1e-12:
        return 1.0 / years
    g = (1.0 + rate) ** years
    return rate * g / (g - 1.0)


def life_extension_value(pack_cost: float, rate: float, life_conv_years: float, life_ctrl_years: float) -> dict:
    """Value per year of a longer life, as equivalent annual cost: cost x CRF(rate, life). Use the cost of the pack as bought
    (second-life packs: the price paid for the retired pack), and lives from the aging model (cycles to end of life / cycles a year).
    Do not add a wear $/MWh on top of this for the same degradation, or it is counted twice."""
    if pack_cost < 0:
        raise ValueError("pack cost cannot be negative")
    eac_conv = pack_cost * capital_recovery_factor(rate, life_conv_years)
    eac_ctrl = pack_cost * capital_recovery_factor(rate, life_ctrl_years)
    return {"annual_cost_conventional": eac_conv, "annual_cost_control": eac_ctrl, "annual_saving": eac_conv - eac_ctrl}


def control_npv(annual_value: float, control_capex: float, years: int, rate: float, om: float = 0.0, tax_rate: float = 0.0) -> dict:
    """The control electronics as an investment: NPV, payback and the most it could cost for NPV = 0, from finance.py.
    annual_value is the yearly saving from control (energy value and/or life extension), already net of any wear it avoids."""
    if years < 1:
        raise ValueError("years must be at least 1")
    rev = np.full(int(years), float(annual_value))
    cf = FIN.storage_cashflows(control_capex, rev, om, tax_rate)
    return {"npv": FIN.npv(rate, cf), "payback_years": FIN.payback_years(cf),
            "breakeven_capex": FIN.breakeven_capex(rev, 0.0, rate, tax_rate, om_fixed=om), "cashflows": cf}
