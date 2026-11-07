"""Energy-use scheduling: when to run a battery, flexible loads and building heating/cooling.

A linear program decides, hour by hour, how much to buy from the grid, charge or discharge a battery,
commit to frequency regulation, run each flexible load inside its window, and heat or cool a building
inside a comfort band. Terms in the bill and the physics:

    energy cost       price x energy bought (minus a share of the price for any export)
    demand charge     money per kW of the highest import in the billing period (optional)
    regulation        capacity paid per MW-hour for holding battery headroom up AND down (optional)
    ramp limits       how fast imports or battery output may change between steps (optional)
    export cap        most power that may be sent back to the grid (optional; surplus solar is curtailed, battery may not exceed it)
    building thermal  one-zone heat balance: envelope loss, internal gains, heat pump/chiller, comfort band
    carbon            kg CO2 per MWh bought, valued at a money-per-kg price (0 = money only)

Simplifications that matter (also in the README):
    * regulation is paid for capacity only; the energy it actually moves is not simulated
    * the building is ONE zone with ONE temperature; real buildings have many
    * a short horizon pays its share of a month's demand charge, as if its peak were the month's peak
Everything in synth_flex() is invented. Real series enter through hackkit/data_io.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

HOURS_PER_MONTH = 30.4 * 24


@dataclass
class Battery:
    energy_mwh: float
    power_mw: float
    eff_charge: float = 0.95
    eff_discharge: float = 0.95
    soc0_frac: float = 0.5
    soc_min_frac: float = 0.0
    soc_end_frac: Optional[float] = None   # default: finish where it started (ignored if terminal_value is set)
    degr_cost: float = 0.0                 # money per MWh discharged (wear)
    ramp_mw: Optional[float] = None        # most the net battery power may change between steps
    reg_hours: float = 0.25                # energy held back per MW of regulation, in hours of that power
    max_discharge_mwh_per_day: Optional[float] = None  # throughput cap, averaged over the horizon (e.g. one full cycle a day = energy_mwh * eff)


@dataclass
class Deferrable:
    """Energy that must be delivered inside [start, end) but may be delivered when it is cheapest."""
    name: str
    energy_mwh: float                      # most that can be delivered
    power_mw: float                        # charger or equipment limit
    start: int
    end: int                               # exclusive
    min_energy_mwh: Optional[float] = None  # must-deliver amount; default = energy_mwh

    @property
    def must(self) -> float:
        return self.energy_mwh if self.min_energy_mwh is None else self.min_energy_mwh


@dataclass
class DemandCharge:
    rate_per_kw_month: float
    mask: Optional[np.ndarray] = None      # bool per step; only imports inside the mask set the peak (None = all)
    billing_hours: Optional[float] = None  # None = the horizon; a short horizon pays its share of a month

    def factor(self, T: int, dt: float) -> float:
        hours = self.billing_hours if self.billing_hours is not None else T * dt
        return min(1.0, hours / HOURS_PER_MONTH)


@dataclass
class Thermal:
    """One-zone building. Electric power in, heat moved by a heat pump or chiller, envelope loss to outdoors."""
    t_out: np.ndarray                      # outdoor temperature per step, C
    ua_mw_per_c: float = 0.15              # heat loss per degree of indoor-outdoor difference
    cap_mwh_per_c: float = 1.8             # heat stored per degree of indoor temperature
    cop_cool: float = 3.0
    cop_heat: float = 2.8
    max_cool_mw: float = 1.5               # electric
    max_heat_mw: float = 1.5               # electric
    gains_mw: Optional[np.ndarray] = None  # internal heat from people, lights, equipment (MW of heat)
    occupied: Optional[np.ndarray] = None  # bool per step
    band_occ: Tuple[float, float] = (21.0, 24.0)
    band_unocc: Tuple[float, float] = (17.0, 28.0)
    t0: float = 22.5
    comfort_penalty: float = 300.0         # money per degree-hour outside the band
    margin: float = 0.0                    # planning only: aim this far inside each edge (a hedge against surprises)

    def arrays(self, T: int, margin: float = 0.0):
        t_out = np.asarray(self.t_out, float)
        gains = np.zeros(T) if self.gains_mw is None else np.asarray(self.gains_mw, float)
        occ = np.ones(T, bool) if self.occupied is None else np.asarray(self.occupied, bool)
        lo = np.where(occ, self.band_occ[0], self.band_unocc[0])
        hi = np.where(occ, self.band_occ[1], self.band_unocc[1])
        if margin > 0:
            m = np.minimum(margin, (hi - lo) / 2)
            lo, hi = lo + m, hi - m
        return t_out, gains, occ, lo, hi

    def step(self, dt: float, temp: float, t_out: float, gain: float, heat: float, cool: float) -> float:
        a = dt * self.ua_mw_per_c / self.cap_mwh_per_c
        return temp * (1 - a) + dt / self.cap_mwh_per_c * (self.ua_mw_per_c * t_out + gain
                                                          + self.cop_heat * heat - self.cop_cool * cool)


@dataclass
class FlexProblem:
    times: List[str]
    price: np.ndarray                      # money per MWh bought
    carbon: np.ndarray                     # kg CO2 per MWh bought
    base_load: np.ndarray                  # MW that cannot move (everything except HVAC and flexible loads)
    solar: np.ndarray                      # MW of free on-site generation available
    step_hours: float = 1.0
    battery: Optional[Battery] = None
    deferrables: List[Deferrable] = field(default_factory=list)
    thermal: Optional[Thermal] = None
    demand_charge: Optional[DemandCharge] = None
    reg_price: Optional[np.ndarray] = None  # money per MW-hour of regulation capacity (None = no market)
    import_limit_mw: Optional[float] = None
    import_ramp_mw: Optional[float] = None
    allow_export: bool = False
    export_price_factor: float = 0.8       # share of the market price paid for exported energy
    export_limit_mw: Optional[float] = None  # grid-congestion cap on exports (None = no cap); only matters when allow_export is True
    carbon_price: float = 0.0              # money per kg CO2 (50 per tonne = 0.05)
    terminal_value: Optional[float] = None  # money per MWh left in the battery at the end (rolling plans)
    thermal_terminal_value: Optional[float] = None  # money per degree of final indoor temperature (rolling plans)
    peak_floor_mw: float = 0.0             # highest billed import already seen in this billing period
    prev_import_mw: Optional[float] = None  # for the first ramp step of a rolling plan
    prev_batt_mw: Optional[float] = None
    synthetic: bool = True
    notes: str = ""

    def __post_init__(self):
        for k in ("price", "carbon", "base_load", "solar"):
            setattr(self, k, np.asarray(getattr(self, k), dtype=float))
        T = len(self.times)
        for k in ("price", "carbon", "base_load", "solar"):
            assert getattr(self, k).shape == (T,), f"{k} must have one value per time step"
        if self.reg_price is not None:
            self.reg_price = np.asarray(self.reg_price, dtype=float)
            assert self.reg_price.shape == (T,), "reg_price must have one value per time step"

    @property
    def T(self) -> int:
        return len(self.times)

    def copy(self, **changes) -> "FlexProblem":
        return replace(self, **changes)


@dataclass
class Schedule:
    """What a policy did, per step. Any policy's output is scored on the same yardstick by evaluate_s."""
    charge: np.ndarray
    discharge: np.ndarray
    loads: np.ndarray                      # deferrables x T
    reg: np.ndarray
    cool: np.ndarray
    heat: np.ndarray


@dataclass
class FlexPlan:
    problem: FlexProblem
    table: pd.DataFrame            # one row per step
    loads: pd.DataFrame            # deferrable loads, MW per step
    money: float                   # energy + demand charge + wear - export - regulation revenue
    carbon_kg: float
    objective: float               # money + carbon_price x carbon + comfort cost
    components: Dict[str, float]
    peak_mw: float
    comfort_degree_hours: float
    battery_energy_value: float    # objective saved per extra MWh of battery size over this horizon
    battery_power_value: float     # objective saved per extra MW of battery power over this horizon
    import_limit_value: float      # objective saved per extra MW of import headroom over this horizon
    status: str

    def schedule(self) -> Schedule:
        T = self.problem.T
        t = self.table
        loads = self.loads.to_numpy().T if self.loads.shape[1] else np.zeros((0, T))
        return Schedule(t["charge"].to_numpy(), t["discharge"].to_numpy(), loads,
                        t["reg"].to_numpy(), t["cool"].to_numpy(), t["heat"].to_numpy())


class _Rows:
    def __init__(self):
        self.r, self.c, self.v, self.rhs, self.n = [], [], [], [], 0

    def add(self, coeffs, rhs):
        for col, val in coeffs:
            self.r.append(self.n)
            self.c.append(col)
            self.v.append(val)
        self.rhs.append(rhs)
        self.n += 1

    def matrix(self, ncols):
        if self.n == 0:
            return None, None
        return coo_matrix((self.v, (self.r, self.c)), shape=(self.n, ncols)).tocsr(), np.array(self.rhs, float)


def _mask(p: FlexProblem) -> np.ndarray:
    if p.demand_charge is None or p.demand_charge.mask is None:
        return np.ones(p.T, bool)
    return np.asarray(p.demand_charge.mask, bool)


def solve_flex(p: FlexProblem, with_values: bool = True) -> FlexPlan:
    T, dt = p.T, p.step_hours
    J = len(p.deferrables)
    bat, th, dc = p.battery, p.thermal, p.demand_charge
    layout = [("g", T), ("e", T), ("c", T), ("d", T), ("soc", T), ("s", T), ("x", J * T), ("peak", 1),
              ("reg", T), ("cool", T), ("heat", T), ("temp", T), ("slo", T), ("shi", T)]
    off, n = {}, 0
    for k, size in layout:
        off[k] = n
        n += size
    G, E, C, D, SOC, S, X, PK, R, CL, HT, TP, SLO, SHI = (off[k] for k, _ in layout)

    cost = np.zeros(n)
    cost[G:G + T] = dt * (p.price + p.carbon_price * p.carbon)
    if p.allow_export:
        cost[E:E + T] = dt * (-p.export_price_factor * p.price - p.carbon_price * p.carbon)
    if bat is not None:
        cost[C:C + T] = 1e-7 * dt
        cost[D:D + T] = dt * bat.degr_cost + 1e-7 * dt
        if p.terminal_value is not None:
            cost[SOC + T - 1] = -p.terminal_value
        if p.reg_price is not None:
            cost[R:R + T] = -dt * p.reg_price
    if dc is not None:
        cost[PK] = dc.rate_per_kw_month * 1000.0 * dc.factor(T, dt)
    if th is not None:
        cost[SLO:SLO + T] = th.comfort_penalty * dt
        cost[SHI:SHI + T] = th.comfort_penalty * dt
        cost[CL:CL + T] = 1e-7 * dt
        cost[HT:HT + T] = 1e-7 * dt
        if p.thermal_terminal_value is not None:
            cost[TP + T - 1] = p.thermal_terminal_value

    lo = np.zeros(n)
    hi = np.full(n, np.inf)
    hi[G:G + T] = np.inf if p.import_limit_mw is None else p.import_limit_mw
    hi[E:E + T] = (np.inf if p.export_limit_mw is None else p.export_limit_mw) if p.allow_export else 0.0
    hi[S:S + T] = p.solar                      # S = solar curtailed
    if bat is not None:
        hi[C:C + T] = bat.power_mw
        hi[D:D + T] = bat.power_mw
        lo[SOC:SOC + T] = bat.soc_min_frac * bat.energy_mwh
        hi[SOC:SOC + T] = bat.energy_mwh
        if p.terminal_value is None:
            end = bat.soc0_frac if bat.soc_end_frac is None else bat.soc_end_frac
            lo[SOC + T - 1] = max(lo[SOC + T - 1], end * bat.energy_mwh)
        hi[R:R + T] = bat.power_mw if p.reg_price is not None else 0.0
    else:
        hi[C:C + T] = hi[D:D + T] = hi[SOC:SOC + T] = hi[R:R + T] = 0.0
    for j, d in enumerate(p.deferrables):
        for t in range(T):
            hi[X + j * T + t] = d.power_mw if d.start <= t < d.end else 0.0
    if dc is not None:
        lo[PK] = p.peak_floor_mw
    else:
        hi[PK] = 0.0
    if th is not None:
        hi[CL:CL + T] = th.max_cool_mw
        hi[HT:HT + T] = th.max_heat_mw
        lo[TP:TP + T], hi[TP:TP + T] = -100.0, 100.0
    else:
        for a in (CL, HT, TP, SLO, SHI):
            hi[a:a + T] = 0.0

    eq, ub = _Rows(), _Rows()
    soc0 = 0.0 if bat is None else bat.soc0_frac * bat.energy_mwh
    for t in range(T):
        co = [(G + t, 1.0), (S + t, -1.0), (D + t, 1.0), (E + t, -1.0), (C + t, -1.0),
              (CL + t, -1.0), (HT + t, -1.0)] + [(X + j * T + t, -1.0) for j in range(J)]
        eq.add(co, p.base_load[t] - p.solar[t])
    for t in range(T):
        co = [(SOC + t, 1.0)]
        rhs = 0.0
        if t > 0:
            co.append((SOC + t - 1, -1.0))
        else:
            rhs = soc0
        if bat is not None:
            co += [(C + t, -dt * bat.eff_charge), (D + t, dt / bat.eff_discharge)]
        eq.add(co, rhs)
    if th is not None:
        t_out, gains, occ, blo, bhi = th.arrays(T, margin=th.margin)
        a = dt * th.ua_mw_per_c / th.cap_mwh_per_c
        for t in range(T):
            co = [(TP + t, 1.0), (HT + t, -dt / th.cap_mwh_per_c * th.cop_heat),
                  (CL + t, dt / th.cap_mwh_per_c * th.cop_cool)]
            rhs = dt / th.cap_mwh_per_c * (th.ua_mw_per_c * t_out[t] + gains[t])
            if t > 0:
                co.append((TP + t - 1, -(1.0 - a)))
            else:
                rhs += (1.0 - a) * th.t0
            eq.add(co, rhs)
            ub.add([(TP + t, -1.0), (SLO + t, -1.0)], -blo[t])      # temperature + slack >= lower edge
            ub.add([(TP + t, 1.0), (SHI + t, -1.0)], bhi[t])        # temperature - slack <= upper edge
    for j, d in enumerate(p.deferrables):
        cap = d.power_mw * dt * max(0, min(d.end, T) - max(d.start, 0))
        if d.must > cap + 1e-9:
            raise ValueError(f"'{d.name}' needs {d.must:.2f} MWh but its window can only deliver {cap:.2f} MWh "
                             "(raise the power limit or widen the window)")
        ub.add([(X + j * T + t, dt) for t in range(T)], d.energy_mwh)
        ub.add([(X + j * T + t, -dt) for t in range(T)], -d.must)
    if dc is not None:
        mk = _mask(p)
        for t in range(T):
            if mk[t]:
                ub.add([(G + t, 1.0), (PK, -1.0)], 0.0)
    if bat is not None and bat.max_discharge_mwh_per_day is not None:
        ub.add([(D + t, dt) for t in range(T)], bat.max_discharge_mwh_per_day * T * dt / 24.0)
    if bat is not None and p.reg_price is not None:
        for t in range(T):
            ub.add([(D + t, 1.0), (R + t, 1.0)], bat.power_mw)
            ub.add([(C + t, 1.0), (R + t, 1.0)], bat.power_mw)
            ub.add([(SOC + t, -1.0), (R + t, bat.reg_hours / bat.eff_discharge)], -bat.soc_min_frac * bat.energy_mwh)
            ub.add([(SOC + t, 1.0), (R + t, bat.reg_hours * bat.eff_charge)], bat.energy_mwh)
    if p.import_ramp_mw is not None:
        for t in range(T):
            if t > 0:
                ub.add([(G + t, 1.0), (G + t - 1, -1.0)], p.import_ramp_mw)
                ub.add([(G + t, -1.0), (G + t - 1, 1.0)], p.import_ramp_mw)
            elif p.prev_import_mw is not None:
                ub.add([(G + t, 1.0)], p.import_ramp_mw + p.prev_import_mw)
                ub.add([(G + t, -1.0)], p.import_ramp_mw - p.prev_import_mw)
    if bat is not None and bat.ramp_mw is not None:
        for t in range(T):
            if t > 0:
                ub.add([(D + t, 1.0), (C + t, -1.0), (D + t - 1, -1.0), (C + t - 1, 1.0)], bat.ramp_mw)
                ub.add([(D + t, -1.0), (C + t, 1.0), (D + t - 1, 1.0), (C + t - 1, -1.0)], bat.ramp_mw)
            elif p.prev_batt_mw is not None:
                ub.add([(D + t, 1.0), (C + t, -1.0)], bat.ramp_mw + p.prev_batt_mw)
                ub.add([(D + t, -1.0), (C + t, 1.0)], bat.ramp_mw - p.prev_batt_mw)

    A_eq, b_eq = eq.matrix(n)
    A_ub, b_ub = ub.matrix(n)
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=list(zip(lo, hi)), method="highs")
    if res.status != 0:
        raise RuntimeError(f"Flex solve did not finish cleanly: {res.message}")
    x = res.x
    g, e, c, d_, soc, s = (x[G:G + T], x[E:E + T], x[C:C + T], x[D:D + T], x[SOC:SOC + T], x[S:S + T])
    reg, cool, heat, temp = x[R:R + T], x[CL:CL + T], x[HT:HT + T], x[TP:TP + T]
    slack = x[SLO:SLO + T] + x[SHI:SHI + T]
    loads = np.array([x[X + j * T:X + (j + 1) * T] for j in range(J)]) if J else np.zeros((0, T))

    comp = {
        "energy": float(np.sum(dt * p.price * g)),
        "export_revenue": float(np.sum(dt * p.export_price_factor * p.price * e)) if p.allow_export else 0.0,
        "wear": float(np.sum(dt * bat.degr_cost * d_)) if bat is not None else 0.0,
        "demand_charge": float(dc.rate_per_kw_month * 1000.0 * dc.factor(T, dt) * x[PK]) if dc is not None else 0.0,
        "regulation_revenue": float(np.sum(dt * p.reg_price * reg)) if (bat is not None and p.reg_price is not None) else 0.0,
    }
    money = comp["energy"] - comp["export_revenue"] + comp["wear"] + comp["demand_charge"] - comp["regulation_revenue"]
    carbon = float(np.sum(dt * p.carbon * (g - (e if p.allow_export else 0.0))))
    comfort = float(dt * slack.sum())
    comp["comfort_cost"] = comfort * (th.comfort_penalty if th is not None else 0.0)
    objective = money + p.carbon_price * carbon + comp["comfort_cost"]
    table = pd.DataFrame({"time": p.times, "price": p.price, "carbon": p.carbon, "base_load": p.base_load,
                          "solar_used": p.solar - s, "import": g, "export": e, "charge": c, "discharge": d_,
                          "soc": soc, "flex_load": loads.sum(axis=0) if J else np.zeros(T), "reg": reg,
                          "cool": cool, "heat": heat, "hvac": cool + heat,
                          "temp": temp if th is not None else np.full(T, np.nan)})
    ld = pd.DataFrame(loads.T, columns=[d.name for d in p.deferrables]) if J else pd.DataFrame(index=range(T))

    e_val = p_val = i_val = 0.0
    if with_values:
        # Marginal values by re-solving with a slightly larger asset (this includes the regulation and thermal links).
        if bat is not None:
            de = max(0.05 * bat.energy_mwh, 0.05)
            up = solve_flex(p.copy(battery=replace(bat, energy_mwh=bat.energy_mwh + de)), with_values=False)
            e_val = (objective - up.objective) / de
            dpw = max(0.05 * bat.power_mw, 0.05)
            up = solve_flex(p.copy(battery=replace(bat, power_mw=bat.power_mw + dpw)), with_values=False)
            p_val = (objective - up.objective) / dpw
        if p.import_limit_mw is not None:
            di = 0.1
            up = solve_flex(p.copy(import_limit_mw=p.import_limit_mw + di), with_values=False)
            i_val = (objective - up.objective) / di
    return FlexPlan(problem=p, table=table, loads=ld, money=money, carbon_kg=carbon, objective=objective,
                    components=comp, peak_mw=float(x[PK]) if dc is not None else float(g.max(initial=0.0)),
                    comfort_degree_hours=comfort, battery_energy_value=e_val, battery_power_value=p_val,
                    import_limit_value=i_val, status=res.message)


# ---------- building temperature, simulated outside the solver ----------

def simulate_temperature(p: FlexProblem, cool, heat, t_out=None, disturbance=None, t0=None) -> np.ndarray:
    th = p.thermal
    T, dt = p.T, p.step_hours
    t_arr, gains, _, _, _ = th.arrays(T)
    t_out = t_arr if t_out is None else np.asarray(t_out, float)
    temp = np.zeros(T)
    prev = th.t0 if t0 is None else t0
    for t in range(T):
        prev = th.step(dt, prev, t_out[t], gains[t], heat[t], cool[t])
        if disturbance is not None:
            prev += disturbance[t]
        temp[t] = prev
    return temp


def comfort_degree_hours(p: FlexProblem, temp) -> float:
    """Degree-hours outside the real comfort band, however the schedule was produced."""
    _, _, _, lo, hi = p.thermal.arrays(p.T)
    return float(p.step_hours * (np.maximum(lo - temp, 0) + np.maximum(temp - hi, 0)).sum())


# ---------- scoring any schedule on one yardstick ----------

def evaluate(p: FlexProblem, charge, discharge, loads, price=None, solar=None, reg=None, hvac=None,
             comfort_cost: float = 0.0, reg_price=None) -> dict:
    """Cost and emissions of ANY schedule. Solar is used first; surplus is exported if allowed, else curtailed.
    Pass actual price/solar to score a plan on what really happened."""
    dt = p.step_hours
    price = p.price if price is None else np.asarray(price, float)
    solar = p.solar if solar is None else np.asarray(solar, float)
    rp = p.reg_price if reg_price is None else np.asarray(reg_price, float)
    charge, discharge = np.asarray(charge, float), np.asarray(discharge, float)
    loads = np.asarray(loads, float).reshape(-1, p.T)
    hv = np.zeros(p.T) if hvac is None else np.asarray(hvac, float)
    need = p.base_load + charge + loads.sum(axis=0) + hv - discharge - solar
    g = np.maximum(need, 0.0)
    e = np.maximum(-need, 0.0) if p.allow_export else np.zeros(p.T)
    if p.allow_export and p.export_limit_mw is not None:
        e = np.minimum(e, p.export_limit_mw)       # surplus beyond the cap is curtailed (see violations_flex for when that is not possible)
    wear = p.battery.degr_cost if p.battery is not None else 0.0
    energy = float(np.sum(dt * price * g))
    export = float(np.sum(dt * p.export_price_factor * price * e))
    wear_c = float(np.sum(dt * wear * discharge))
    peak = float(g[_mask(p)].max(initial=0.0))
    demand = 0.0
    if p.demand_charge is not None:
        demand = p.demand_charge.rate_per_kw_month * 1000.0 * p.demand_charge.factor(p.T, dt) * max(peak, p.peak_floor_mw)
    regrev = 0.0
    if reg is not None and rp is not None:
        regrev = float(np.sum(dt * rp * np.asarray(reg, float)))
    money = energy - export + wear_c + demand - regrev
    carbon = float(np.sum(dt * p.carbon * (g - e)))
    return {"money": money, "carbon_kg": carbon, "objective": money + p.carbon_price * carbon + comfort_cost,
            "peak_import_mw": float(g.max(initial=0.0)), "billed_peak_mw": max(peak, p.peak_floor_mw) if p.demand_charge else peak,
            "import": g, "export": e,
            "components": {"energy": energy, "export_revenue": export, "wear": wear_c, "demand_charge": demand,
                           "regulation_revenue": regrev, "comfort_cost": comfort_cost}}


def evaluate_s(p: FlexProblem, s: Schedule, price=None, solar=None, t_out=None, disturbance=None, reg_price=None) -> dict:
    """Score a Schedule, including the comfort cost of whatever the building temperature really did."""
    comfort_c, temp = 0.0, None
    if p.thermal is not None:
        temp = simulate_temperature(p, s.cool, s.heat, t_out=t_out, disturbance=disturbance)
        comfort_c = comfort_degree_hours(p, temp) * p.thermal.comfort_penalty
    out = evaluate(p, s.charge, s.discharge, s.loads, price=price, solar=solar, reg=s.reg, hvac=s.cool + s.heat,
                   comfort_cost=comfort_c, reg_price=reg_price)
    out["temp"] = temp
    out["comfort_cost"] = comfort_c
    return out


def violations_flex(p: FlexProblem, charge, discharge, loads, reg=None, hvac=None, cool=None, heat=None,
                    tol: float = 1e-6) -> List[str]:
    """Independent check of the physical limits, no solver involved. Comfort is soft and scored separately."""
    dt = p.step_hours
    charge, discharge = np.asarray(charge, float), np.asarray(discharge, float)
    loads = np.asarray(loads, float).reshape(-1, p.T)
    r = np.zeros(p.T) if reg is None else np.asarray(reg, float)
    bad = []
    bat = p.battery
    if bat is None:
        if charge.max(initial=0) > tol or discharge.max(initial=0) > tol or r.max(initial=0) > tol:
            bad.append("battery used but none exists")
    else:
        if charge.min(initial=0) < -tol or discharge.min(initial=0) < -tol or r.min(initial=0) < -tol:
            bad.append("negative battery flow")
        if max(charge.max(initial=0), discharge.max(initial=0)) > bat.power_mw + tol:
            bad.append("battery power limit exceeded")
        soc = bat.soc0_frac * bat.energy_mwh
        for t in range(p.T):
            soc += dt * (bat.eff_charge * charge[t] - discharge[t] / bat.eff_discharge)
            if soc > bat.energy_mwh + 1e-5 or soc < bat.soc_min_frac * bat.energy_mwh - 1e-5:
                bad.append(f"battery state of charge out of range at step {t}")
                break
            if r[t] > tol and (soc - bat.reg_hours * r[t] / bat.eff_discharge < bat.soc_min_frac * bat.energy_mwh - 1e-5
                               or soc + bat.reg_hours * bat.eff_charge * r[t] > bat.energy_mwh + 1e-5):
                bad.append(f"regulation commitment not backed by stored energy at step {t}")
                break
        if (discharge + r).max(initial=0) > bat.power_mw + 1e-5 or (charge + r).max(initial=0) > bat.power_mw + 1e-5:
            bad.append("regulation headroom exceeds battery power")
        if bat.ramp_mw is not None:
            net = discharge - charge
            if p.prev_batt_mw is not None:
                net = np.concatenate([[p.prev_batt_mw], net])
            if np.abs(np.diff(net)).max(initial=0) > bat.ramp_mw + 1e-5:
                bad.append("battery ramp limit exceeded")
    for j, d in enumerate(p.deferrables):
        row = loads[j]
        if row.min(initial=0) < -tol or row.max(initial=0) > d.power_mw + tol:
            bad.append(f"{d.name}: power limit")
        outside = np.concatenate([row[:max(0, d.start)], row[min(d.end, p.T):]])
        if outside.size and outside.max() > tol:
            bad.append(f"{d.name}: ran outside its window")
        delivered = dt * row.sum()
        if delivered > d.energy_mwh + 1e-5 or delivered < d.must - 1e-5:
            bad.append(f"{d.name}: delivered {delivered:.3f} MWh outside [{d.must:.3f}, {d.energy_mwh:.3f}]")
    if p.thermal is not None and cool is not None and heat is not None:
        if (np.asarray(cool).max(initial=0) > p.thermal.max_cool_mw + 1e-5
                or np.asarray(heat).max(initial=0) > p.thermal.max_heat_mw + 1e-5
                or np.asarray(cool).min(initial=0) < -tol or np.asarray(heat).min(initial=0) < -tol):
            bad.append("heating or cooling equipment limit exceeded")
    ev = evaluate(p, charge, discharge, loads, hvac=hvac)
    g = ev["import"]
    if p.allow_export and p.export_limit_mw is not None:
        hv = np.zeros(p.T) if hvac is None else np.asarray(hvac, float)
        surplus = -(p.base_load + charge + loads.sum(axis=0) + hv - discharge - p.solar)       # MW that would flow out if nothing is curtailed
        if (surplus - p.export_limit_mw - p.solar).max(initial=-1.0) > 1e-5:
            bad.append("export limit exceeded (more than the free solar can be curtailed to fix)")
    if p.import_limit_mw is not None and g.max(initial=0) > p.import_limit_mw + 1e-5:
        bad.append("import limit exceeded")
    if p.import_ramp_mw is not None:
        gg = g if p.prev_import_mw is None else np.concatenate([[p.prev_import_mw], g])
        if np.abs(np.diff(gg)).max(initial=0) > p.import_ramp_mw + 1e-5:
            bad.append("import ramp limit exceeded")
    return bad


# ---------- the comparison rules (what a careful operator would do without an optimizer) ----------

@dataclass
class Rule:
    """Fixed-price-level operating rule, tuned on training weeks.
    cheap/dear: absolute price levels. peak_cap: shave imports above this MW (None = ignore demand charge).
    reg_level: offer regulation when its price is at least this (None = never)."""
    cheap: float
    dear: float
    peak_cap: Optional[float] = None
    reg_level: Optional[float] = None
    daily: bool = False   # cheap/dear are then shares (0-1) of THAT day's price range, not absolute levels


def _is_cooling(p: FlexProblem) -> bool:
    return bool(np.mean(np.asarray(p.thermal.t_out, float)) > sum(p.thermal.band_occ) / 2)


def _hvac_control(p: FlexProblem, t: int, temp: float, target_occ: Optional[float], cooling: Optional[bool]):
    """Move toward a target with limited equipment. cooling=None lets it heat or cool as needed (plain thermostat)."""
    th, dt = p.thermal, p.step_hours
    t_out, gains, occ, _, _ = th.arrays(p.T)
    free = th.step(dt, temp, t_out[t], gains[t], 0.0, 0.0)
    occ_now = bool(occ[t] or occ[min(t + 1, p.T - 1)])        # start conditioning one step before people arrive
    lo_b, hi_b = th.band_occ if occ_now else th.band_unocc
    target = target_occ if (occ_now and target_occ is not None) else (sum(th.band_occ) / 2 if occ_now else min(max(free, lo_b), hi_b))
    gap = target - free
    k = th.cap_mwh_per_c / dt
    if gap < 0 and (cooling is None or cooling or free > hi_b):
        return min(th.max_cool_mw, -gap * k / th.cop_cool), 0.0
    if gap > 0 and (cooling is None or not cooling or free < lo_b):
        return 0.0, min(th.max_heat_mw, gap * k / th.cop_heat)
    return 0.0, 0.0


def _rule_step(p: FlexProblem, rule: Optional[Rule], t: int, st: dict, asap: bool):
    dt = p.step_hours
    J = len(p.deferrables)
    cool = heat = 0.0
    cheap = dear = 0.0
    if rule is not None:
        if rule.daily:
            seg = p.price[(t // 24) * 24:(t // 24 + 1) * 24]
            cheap, dear = float(np.quantile(seg, rule.cheap)), float(np.quantile(seg, rule.dear))
        else:
            cheap, dear = rule.cheap, rule.dear
    if p.thermal is not None:
        if asap:
            cool, heat = _hvac_control(p, t, st["temp"], None, None)
        else:
            cooling = _is_cooling(p)
            lo_o, hi_o = p.thermal.band_occ
            if p.price[t] <= cheap:
                tgt = lo_o + 0.3 if cooling else hi_o - 0.3          # pre-cool / pre-heat when power is cheap
            elif p.price[t] >= dear:
                tgt = hi_o - 0.2 if cooling else lo_o + 0.2          # coast near the edge when power is dear
            else:
                tgt = (lo_o + hi_o) / 2
            cool, heat = _hvac_control(p, t, st["temp"], tgt, cooling)
    loads_t = np.zeros(J)
    cap = None if (asap or rule.peak_cap is None) else rule.peak_cap
    room = np.inf if cap is None else max(0.0, cap - max(p.base_load[t] + cool + heat - p.solar[t], 0.0))
    for j, d in enumerate(p.deferrables):
        left = st["remaining"][j]
        if not (d.start <= t < d.end) or left <= 1e-12:
            continue
        steps_after = max(0, min(d.end, p.T) - t - 1)
        must_now = min(d.power_mw, max(0.0, left - d.power_mw * dt * steps_after) / dt, left / dt)
        if asap:
            x = min(d.power_mw, left / dt)
        else:
            want = min(d.power_mw, left / dt) if p.price[t] <= cheap else must_now
            x = max(must_now, min(want, room))                      # respect the peak cap unless the deadline forces it
        loads_t[j] = x
        room = max(0.0, room - x)
    c = d_ = r = 0.0
    bat = p.battery
    if bat is not None and not asap:
        need0 = p.base_load[t] + loads_t.sum() + cool + heat - p.solar[t]
        soc = st["soc"]
        avail_d = min(bat.power_mw, max(0.0, soc - bat.soc_min_frac * bat.energy_mwh) * bat.eff_discharge / dt)
        if p.price[t] <= cheap:
            x = min(bat.power_mw, (bat.energy_mwh - soc) / (dt * bat.eff_charge))
            if cap is not None:
                x = min(x, max(0.0, cap - max(need0, 0.0)))
            c = max(0.0, x)
        elif p.price[t] >= dear:
            out_room = max(0.0, need0) if not p.allow_export else (np.inf if p.export_limit_mw is None else max(0.0, need0 + p.export_limit_mw))
            d_ = min(avail_d, out_room)                              # never push more out than the load plus the export cap
        elif cap is not None and need0 > cap:
            d_ = min(avail_d, need0 - cap)
        if cap is not None and need0 > cap and d_ < min(avail_d, need0 - cap):
            d_ = min(avail_d, need0 - cap)                           # shave a peak even at a "dear" price level
        if c == 0.0 and d_ == 0.0 and rule.reg_level is not None and p.reg_price is not None \
                and p.reg_price[t] >= rule.reg_level:
            r = 0.5 * bat.power_mw
            r = min(r, max(0.0, soc - bat.soc_min_frac * bat.energy_mwh) * bat.eff_discharge / bat.reg_hours,
                    max(0.0, bat.energy_mwh - soc) / (bat.reg_hours * bat.eff_charge))
    return c, d_, r, loads_t, cool, heat


def tune_rule(train: List[FlexProblem], grid: int = 5, seed_levels=None, daily: bool = True) -> Rule:
    """Pick the best operating rule on training horizons; then apply it unchanged to new ones.
    Two families compete: fixed price levels, and (daily=True) levels relative to each day's own price range
    (charge in the cheapest part of the day, discharge in the dearest). The rule is chosen by training cost only."""
    pooled = np.concatenate([q.price for q in train])
    regs = [q.reg_price for q in train if q.reg_price is not None]
    reg_level = float(np.quantile(np.concatenate(regs), 0.5)) if regs else None
    caps = [None]
    if any(q.demand_charge is not None for q in train):
        base = np.concatenate([evaluate_s(q, baseline_asap(q))["import"] for q in train])
        caps += [float(np.quantile(base, v)) for v in (0.3, 0.4, 0.5, 0.6, 0.75, 0.9)]
    best = (np.inf, None)
    for fam in ((False, True) if daily else (False,)):
        for a in np.linspace(0.1, 0.5, grid):
            for b in np.linspace(0.6, 0.95, grid):
                for cap in caps:
                    lv = (float(a), float(b)) if fam else (float(np.quantile(pooled, a)), float(np.quantile(pooled, b)))
                    rule = Rule(lv[0], lv[1], cap, reg_level, daily=fam)
                    v = sum(adjusted_objective(q, replay(q, q.price, policy="rule", rule=rule)) for q in train)
                    if v < best[0]:
                        best = (v, rule)
    return best[1]


def baseline_asap(p: FlexProblem) -> Schedule:
    """Do nothing clever: flexible loads as early as possible, battery idle, plain thermostat."""
    return replay(p, p.price, policy="asap")["schedule"]


# ---------- rolling replay: plan with forecasts, live with the truth ----------

def _window_problem(p: FlexProblem, t0: int, H: int, price_fc, solar_fc, reg_fc, tout_fc, st: dict,
                    known_now: bool = True) -> FlexProblem:
    T = p.T
    t1 = min(T, t0 + H)
    dt = p.step_hours
    price = np.array(price_fc[t0:t1], float)
    if known_now:
        price[0] = p.price[t0]                           # this step's price is known
    solar = np.array(solar_fc[t0:t1], float)
    if known_now:
        solar[0] = p.solar[t0]
    reg = None
    if p.reg_price is not None:
        reg = np.array(reg_fc[t0:t1], float)
        if known_now:
            reg[0] = p.reg_price[t0]
    jobs = []
    for j, d in enumerate(p.deferrables):
        r = st["remaining"][j]
        if r <= 1e-9 or d.end <= t0:
            continue
        s_ = max(d.start, t0) - t0
        e_ = min(d.end, t1) - t0
        if s_ >= t1 - t0:
            continue
        beyond = max(0, d.end - t1)
        must = max(0.0, r - d.power_mw * dt * beyond)
        cap = d.power_mw * dt * max(0, e_ - s_)
        jobs.append(Deferrable(d.name, r, d.power_mw, s_, e_, min_energy_mwh=min(must, cap, r)))
    bat = None
    tv = None
    if p.battery is not None:
        b = p.battery
        bat = replace(b, soc0_frac=st["soc"] / b.energy_mwh if b.energy_mwh > 0 else 0.0)
        tv = max(0.0, float(np.mean(price)) * bat.eff_discharge)
    th = None
    ttv = None
    if p.thermal is not None:
        t_out_full, gains, occ, _, _ = p.thermal.arrays(T)
        tout = np.array(tout_fc[t0:t1], float)
        tout[0] = t_out_full[t0]
        th = replace(p.thermal, t_out=tout, gains_mw=gains[t0:t1], occupied=occ[t0:t1], t0=st["temp"])
        cooling = _is_cooling(p)
        ttv = (1.0 if cooling else -1.0) * float(np.mean(price)) * p.thermal.cap_mwh_per_c / (
            p.thermal.cop_cool if cooling else p.thermal.cop_heat)
    dc = None
    if p.demand_charge is not None:
        mask = None if p.demand_charge.mask is None else np.asarray(p.demand_charge.mask, bool)[t0:t1]
        bh = p.demand_charge.billing_hours if p.demand_charge.billing_hours is not None else T * dt
        dc = replace(p.demand_charge, mask=mask, billing_hours=bh)
    return FlexProblem(times=p.times[t0:t1], price=price, carbon=p.carbon[t0:t1], base_load=p.base_load[t0:t1],
                       solar=solar, step_hours=dt, battery=bat, deferrables=jobs, thermal=th, demand_charge=dc,
                       reg_price=reg, import_limit_mw=p.import_limit_mw, import_ramp_mw=p.import_ramp_mw,
                       allow_export=p.allow_export, export_price_factor=p.export_price_factor, export_limit_mw=p.export_limit_mw,
                       carbon_price=p.carbon_price, terminal_value=tv, thermal_terminal_value=ttv,
                       peak_floor_mw=st["peak"], prev_import_mw=st["g_prev"], prev_batt_mw=st["b_prev"],
                       synthetic=p.synthetic)


def _blend_forecast(p: FlexProblem, series_fc, series_actual, t: int, horizon: int, w: float, period: int = 24):
    """Trust the forecast only by weight w; the rest is 'same hour on the latest day already observed'."""
    out = np.array(series_fc, float)
    if w >= 1.0:
        return out
    for k in range(t, min(p.T, t + horizon)):
        idx = k - period * ((k - t) // period + 1)
        if idx >= 0:
            out[k] = w * series_fc[k] + (1.0 - w) * series_actual[idx]
    return out


def replay(p: FlexProblem, price_fc, solar_fc=None, policy: str = "planner", horizon: int = 24,
           rule: Optional[Rule] = None, blend: float = 1.0, reg_fc=None, tout_fc=None, disturbance=None,
           margin: float = 0.0, known_now: bool = True) -> dict:
    """Live through the horizon step by step.
    'planner' re-plans every step from forecasts (the current step is known); 'rule' follows tuned price levels;
    'asap' runs loads early, battery idle, plain thermostat. The building follows its true physics plus a random
    disturbance the planner cannot see. known_now=False hides even the current step's price from the planner (it then
    acts on the forecast and is charged the actual price)."""
    T, dt = p.T, p.step_hours
    solar_fc = p.solar if solar_fc is None else solar_fc
    reg_fc = p.reg_price if reg_fc is None else reg_fc
    bat, th = p.battery, p.thermal
    t_out, gains = (th.arrays(T)[0], th.arrays(T)[1]) if th is not None else (None, None)
    tout_fc = t_out if tout_fc is None else tout_fc
    dist = np.zeros(T) if disturbance is None else np.asarray(disturbance, float)
    soc_start = 0.0 if bat is None else bat.soc0_frac * bat.energy_mwh
    temp_start = th.t0 if th is not None else 0.0
    st = {"remaining": [d.must for d in p.deferrables], "soc": soc_start, "temp": temp_start,
          "peak": p.peak_floor_mw, "g_prev": p.prev_import_mw, "b_prev": p.prev_batt_mw}
    c, dd, reg = np.zeros(T), np.zeros(T), np.zeros(T)
    loads = np.zeros((len(p.deferrables), T))
    cool, heat = np.zeros(T), np.zeros(T)
    mask = _mask(p)
    for t in range(T):
        if policy == "planner":
            pf = _blend_forecast(p, price_fc, p.price, t, horizon, blend)
            w = _window_problem(p, t, horizon, pf, solar_fc, reg_fc, tout_fc, st, known_now)
            if w.thermal is not None:
                w = w.copy(thermal=replace(w.thermal, margin=margin))
            plan = solve_flex(w, with_values=False)
            row = plan.table.iloc[0]
            c[t], dd[t], reg[t], cool[t], heat[t] = row["charge"], row["discharge"], row["reg"], row["cool"], row["heat"]
            names = [d.name for d in w.deferrables]
            for j, d in enumerate(p.deferrables):
                if d.name in names:
                    loads[j, t] = float(plan.loads[d.name].iloc[0])
        else:
            c[t], dd[t], reg[t], loads[:, t], cool[t], heat[t] = _rule_step(p, rule, t, st, asap=(policy == "asap"))
        for j in range(len(p.deferrables)):
            st["remaining"][j] -= loads[j, t] * dt
        if bat is not None:
            st["soc"] = min(max(st["soc"] + dt * (bat.eff_charge * c[t] - dd[t] / bat.eff_discharge),
                                bat.soc_min_frac * bat.energy_mwh), bat.energy_mwh)
            st["b_prev"] = dd[t] - c[t]
        if th is not None:
            st["temp"] = th.step(dt, st["temp"], t_out[t], gains[t], heat[t], cool[t]) + dist[t]
        g_t = max(p.base_load[t] + c[t] + loads[:, t].sum() + cool[t] + heat[t] - dd[t] - p.solar[t], 0.0)
        st["g_prev"] = g_t
        if mask[t]:
            st["peak"] = max(st["peak"], g_t)
    sched = Schedule(c, dd, loads, reg, cool, heat)
    ev = evaluate_s(p, sched, disturbance=dist)
    bad = violations_flex(p, c, dd, loads, reg=reg, hvac=cool + heat, cool=cool, heat=heat)
    return {"money": ev["money"], "carbon_kg": ev["carbon_kg"], "objective": ev["objective"],
            "soc_end": st["soc"], "soc_start": soc_start, "temp_end": st["temp"], "temp_start": temp_start,
            "violations": bad, "comfort_cost": ev["comfort_cost"], "peak_mw": ev["billed_peak_mw"],
            "schedule": sched, "components": ev["components"], "temp": ev["temp"], "import": ev["import"]}


def adjusted_objective(p: FlexProblem, r: dict) -> float:
    """Credit energy left in the battery and the building relative to where each started, at the average price."""
    out = r["objective"]
    avg = float(np.mean(p.price))
    if p.battery is not None:
        out -= (r["soc_end"] - r["soc_start"]) * avg * p.battery.eff_discharge
    if p.thermal is not None:
        th = p.thermal
        cooling = _is_cooling(p)
        stored = (r["temp_start"] - r["temp_end"]) if cooling else (r["temp_end"] - r["temp_start"])
        out -= stored * th.cap_mwh_per_c / (th.cop_cool if cooling else th.cop_heat) * avg
    return out


def plan_as_result(plan: FlexPlan) -> dict:
    p = plan.problem
    t = plan.table
    return {"objective": plan.objective, "money": plan.money, "carbon_kg": plan.carbon_kg,
            "soc_start": 0.0 if p.battery is None else p.battery.soc0_frac * p.battery.energy_mwh,
            "soc_end": 0.0 if p.battery is None else float(t["soc"].iloc[-1]),
            "temp_start": 0.0 if p.thermal is None else p.thermal.t0,
            "temp_end": 0.0 if p.thermal is None else float(t["temp"].iloc[-1])}


def hindsight(p: FlexProblem) -> FlexPlan:
    """Perfect foresight, battery finishes where it started. No real schedule can beat this (after adjustment)."""
    return solve_flex(p.copy(terminal_value=None, thermal_terminal_value=None, peak_floor_mw=0.0), with_values=False)


# ---------- invented data, and a way to bring real prices ----------

def synth_flex(days: int = 3, seed: int = 0, battery: bool = True, solar_mw: float = 3.0, ev: bool = True,
               carbon_price: float = 0.0, hvac: bool = True, season: str = "summer", demand_rate: float = 14.0,
               regulation: bool = True) -> FlexProblem:
    """A small building or campus site with a battery, rooftop solar, an EV fleet and heating/cooling. All invented."""
    rng = np.random.default_rng(seed)
    T = 24 * days
    h = np.arange(T) % 24
    day = np.arange(T) // 24
    shape = (np.where((h >= 7) & (h <= 9), 22.0, 0.0) + np.where((h >= 17) & (h <= 20), 38.0, 0.0)
             + np.where((h >= 11) & (h <= 15), -12.0, 0.0) + np.where((h <= 5), -14.0, 0.0))
    level = np.exp(rng.normal(0, 0.18, size=days))[day]
    price = np.maximum(5.0, (52.0 + shape) * level + rng.normal(0, 4.0, size=T)
                       + (rng.random(T) < 0.02) * rng.uniform(60, 140, size=T))
    carbon = np.maximum(80.0, 390.0 + np.where((h >= 17) & (h <= 21), 70.0, 0.0)
                        + np.where((h >= 10) & (h <= 15), -90.0, 0.0) + 0.9 * (price - price.mean())
                        + rng.normal(0, 12.0, size=T))
    base = 1.5 + 0.8 * np.sin((h - 6) / 24 * 2 * np.pi).clip(0) + 0.3 * (h >= 8) * (h <= 18) + rng.normal(0, 0.07, size=T)
    cloud = rng.uniform(0.45, 1.0, size=days)[day]
    sun = np.where((h >= 7) & (h <= 17), np.sin((h - 7) / 10 * np.pi).clip(0), 0.0)
    solar = solar_mw * sun * cloud
    labels = [f"D{int(d) + 1} {int(x):02d}:00" for d, x in zip(day, h)]
    bat = Battery(energy_mwh=6.0, power_mw=2.0, degr_cost=6.0) if battery else None
    jobs = []
    if ev:
        for d in range(max(1, days - 1)):
            jobs.append(Deferrable(f"EV fleet night {d + 1}", energy_mwh=5.0, power_mw=2.5,
                                   start=24 * d + 18, end=min(T, 24 * (d + 1) + 7)))
    th = None
    if hvac:
        mean_t, amp = {"summer": (27.0, 6.0), "winter": (-1.0, 5.0), "shoulder": (14.0, 5.0)}[season]
        day_shift = rng.normal(0, 2.0, size=days)[day]
        t_out = mean_t + day_shift + amp * np.sin((h - 9) / 24 * 2 * np.pi)
        occupied = (h >= 7) & (h <= 19)
        th = Thermal(t_out=t_out, occupied=occupied, gains_mw=np.where(occupied, 0.45, 0.1), t0=22.5)
    dc = DemandCharge(demand_rate) if demand_rate else None
    reg = None
    if regulation and battery:
        reg = np.maximum(0.5, 6.0 + 3.0 * (h >= 16) * (h <= 21) + rng.normal(0, 1.5, size=T)
                         + (rng.random(T) < 0.03) * rng.uniform(10, 40, size=T))
    return FlexProblem(times=labels, price=price, carbon=carbon, base_load=base, solar=solar, battery=bat,
                       deferrables=jobs, thermal=th, demand_charge=dc, reg_price=reg, carbon_price=carbon_price,
                       allow_export=False, synthetic=True,
                       notes="invented hourly profiles; demand rate and regulation price are illustrative")


def flex_from_prices(prices, carbon=None, base_load_mw: float = 2.5, battery: Optional[Battery] = None,
                     deferrables: Optional[List[Deferrable]] = None, **kw) -> FlexProblem:
    """Build a problem from a real hourly price list (for example a CSV column from the grid operator).
    Set synthetic=False only if the load, solar and carbon series are also real."""
    prices = np.asarray(prices, float)
    T = len(prices)
    carbon = np.full(T, 400.0) if carbon is None else np.asarray(carbon, float)
    return FlexProblem(times=[f"h{t}" for t in range(T)], price=prices, carbon=carbon,
                       base_load=np.full(T, base_load_mw), solar=np.zeros(T), battery=battery,
                       deferrables=deferrables or [], **kw)


def noisy_forecast(actual, rng, sigma: float, phi: float = 0.8, floor: float = 0.0):
    """Forecast = truth x lognormal error that persists from hour to hour (AR(1)). sigma 0 is a perfect forecast."""
    actual = np.asarray(actual, float)
    if sigma <= 0:
        return actual.copy()
    eps = np.zeros(len(actual))
    for t in range(len(actual)):
        prev = eps[t - 1] if t else 0.0
        eps[t] = phi * prev + np.sqrt(1 - phi ** 2) * rng.normal(0, sigma)
    return np.maximum(floor, actual * np.exp(eps))


BLEND_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)


def make_forecasts(p: FlexProblem, rng, sigma: float, solar_sigma: float = 0.2, temp_sigma: float = 1.5):
    """Noisy forecasts of price, solar, regulation price and outdoor temperature (any may be None)."""
    pf = noisy_forecast(p.price, rng, sigma, floor=1.0)
    sf = np.clip(noisy_forecast(p.solar + 1e-9, rng, solar_sigma), 0, None)
    rf = noisy_forecast(p.reg_price, rng, sigma, floor=0.0) if p.reg_price is not None else None
    tf = None
    if p.thermal is not None:
        err = np.zeros(p.T)
        for t in range(p.T):
            err[t] = 0.8 * (err[t - 1] if t else 0.0) + 0.6 * rng.normal(0, temp_sigma)
        tf = p.thermal.arrays(p.T)[0] + err
    return pf, sf, rf, tf


MARGIN_GRID = (0.0, 0.3, 0.6, 0.9)


def tune_hedges(train: List[FlexProblem], rng, sigma: float, solar_sigma: float, horizon: int = 24,
                blend_grid=BLEND_GRID, margin_grid=MARGIN_GRID, disturbance_sigma: float = 0.3) -> Tuple[float, float]:
    """(blend, margin) chosen on training horizons only: how much to trust the price forecast, and how far inside
    the comfort band to aim. Margin first (blend 1), then blend."""
    prepared = [(make_forecasts(q, rng, sigma, solar_sigma),
                 rng.normal(0, disturbance_sigma, size=q.T) if q.thermal else None) for q in train]

    def total(w, m):
        return sum(adjusted_objective(q, replay(q, f[0], f[1], "planner", horizon, blend=w, reg_fc=f[2], tout_fc=f[3],
                                                disturbance=dist, margin=m)) for q, (f, dist) in zip(train, prepared))
    has_th = any(q.thermal is not None for q in train)
    margin = min(margin_grid, key=lambda m: total(1.0, m)) if has_th else 0.0
    blend = min(blend_grid, key=lambda w: total(w, margin))
    return float(blend), float(margin)


def tune_blend(train, rng, sigma, solar_sigma, horizon: int = 24, grid=BLEND_GRID) -> float:
    return tune_hedges(train, rng, sigma, solar_sigma, horizon, blend_grid=grid, margin_grid=(0.0,))[0]


def flex_monte_carlo(n: int = 12, days: int = 3, sigma: float = 0.25, seed: int = 0, solar_sigma: float = 0.2,
                     horizon: int = 24, carbon_price: float = 0.0, battery: Optional[Battery] = None,
                     n_train: int = 6, blend="tune", disturbance_sigma: float = 0.3, **synth_kw) -> pd.DataFrame:
    """n independent invented horizons. The rule's levels are tuned on separate training horizons.
    Each row: money, carbon, comfort cost, peak and the adjusted objective for planner / rule / asap / hindsight."""
    rng = np.random.default_rng(seed)
    train = [synth_flex(days, seed=10_000 + seed * 100 + i, carbon_price=carbon_price, **synth_kw) for i in range(n_train)]
    if battery is not None:
        train = [q.copy(battery=battery) for q in train]
    rule = tune_rule(train)
    if blend == "tune":
        w_blend, margin = tune_hedges(train, rng, sigma, solar_sigma, horizon, disturbance_sigma=disturbance_sigma)
    else:
        w_blend, margin = float(blend), 0.0
    rows = []
    for i in range(n):
        p = synth_flex(days, seed=seed * 1000 + i, carbon_price=carbon_price, **synth_kw)
        if battery is not None:
            p = p.copy(battery=battery)
        pf, sf, rf, tf = make_forecasts(p, rng, sigma, solar_sigma)
        dist = rng.normal(0, disturbance_sigma, size=p.T) if p.thermal is not None else None
        out = {"scenario": i, "blend": w_blend, "margin": margin}
        for name, kw in (("planner", dict(policy="planner", horizon=horizon, blend=w_blend, margin=margin)),
                         ("planner_raw", dict(policy="planner", horizon=horizon)),
                         ("threshold", dict(policy="rule", rule=rule)),
                         ("asap", dict(policy="asap"))):
            r = replay(p, pf, sf, reg_fc=rf, tout_fc=tf, disturbance=dist, **kw)
            out[f"{name}_money"] = r["money"]
            out[f"{name}_carbon"] = r["carbon_kg"]
            out[f"{name}_obj"] = adjusted_objective(p, r)
            out[f"{name}_comfort"] = r["comfort_cost"]
            out[f"{name}_peak"] = r["peak_mw"]
            out[f"{name}_violations"] = len(r["violations"])
        h = hindsight(p)
        out["hindsight_money"], out["hindsight_carbon"] = h.money, h.carbon_kg
        out["hindsight_obj"] = adjusted_objective(p, plan_as_result(h))
        out["hindsight_peak"] = h.peak_mw
        rows.append(out)
    return pd.DataFrame(rows)
