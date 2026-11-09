"""The five responses of the decision layer and when each fires. REON's hardware can sense every cell and switch every cell (REON slide, 7 Nov: Sense, Protect, Balance, then Decide, Isolate, Mix).
This module says WHICH response the policy recommends for a frame of cell states. It recommends; hardware limits stay with the certified BMS and are never overridden.

Responses, mildest first:
  NORMAL        every cell works until it reaches its own limit (the late-switch mode that recovers stranded energy)
  SWITCH_OUT    reversible: take a cell out of the string for now (it reached its own SOC cutoff, or it is hot) and let it back in when it can work
  BYPASS        permanent isolation of one cell (persistently weak, or a single fault sign), while the string keeps running on the rest
  REDUCE_POWER  limit string current for everyone (cold, hot, few bypasses left, or stretching runtime in an outage)
  KILL          open the string and call a crew (hard limit, several cells show fault signs, bypass budget used up, or the string is finished)

Every threshold is a field of Limits and carries a tag. weak_frac is calibrated on REAL cells (0 of 1,140 normal lithium NMC cells were below 0.85 x pack mean, examples/reon_threshold_check.py).
The rest are ASSUMED placeholders to be replaced by the cell maker's datasheet (REON: temperature limits are the cell manufacturer's spec)."""
from dataclasses import dataclass, field
from typing import List, Optional
import math
from hackkit.reon_guard import need

NORMAL, SWITCH_OUT, BYPASS, REDUCE_POWER, KILL = "normal", "switch_out", "bypass", "reduce_power", "kill"
RANK = {NORMAL: 0, SWITCH_OUT: 1, BYPASS: 2, REDUCE_POWER: 3, KILL: 4}


@dataclass
class Limits:
    weak_frac: float = 0.15          # REAL-calibrated (lithium): capacity this far below the median of the others = persistently weak
    persist_cycles: int = 3          # ASSUMED: cycles a cell must look weak before a permanent bypass (tune by injected faults)
    r_jump: float = 2.0              # ASSUMED: resistance this many times the median of the others = fault sign
    dT_dt_warn: float = 1.0          # ASSUMED: degC per minute rise = fault sign
    t_soft: float = 45.0             # ASSUMED: rest a cell above this (cell datasheet)
    t_hard: float = 60.0             # ASSUMED, loosely matches the 'safe below 60 C' regime line of arXiv 2607.18860 (lithium, mechanical abuse); cell datasheet decides; the BMS acts first
    v_hard_lo: float = 1.5           # ASSUMED sodium-ion style window, cell datasheet
    v_hard_hi: float = 4.2
    t_cold: float = 0.0              # ASSUMED lithium charge limit; a sodium vendor claims -20 (to verify)
    soc_lo: float = 0.05
    soc_hi: float = 0.98
    fault_cells_to_kill: int = 2     # ASSUMED: this many cells with fault signs at once = open the string
    hot_share_to_derate: float = 0.3  # ASSUMED: share of cells above t_soft that makes it a string-level problem (cooling)


@dataclass
class Cell:
    i: int
    v: float = 3.2
    t: float = 25.0
    soc: float = 0.5
    cap_rel: float = 1.0             # capacity / median capacity of the other cells
    r_rel: float = 1.0               # resistance / median resistance of the other cells
    dT_dt: float = 0.0               # degC per minute
    bad_cycles: int = 0              # consecutive cycles with cap_rel below the weak line
    discharging: bool = True


@dataclass
class Context:
    n_engaged: int = 16
    n_min: int = 12                  # fewest cells the inverter voltage window allows
    bypass_left: int = 4             # how many more permanent bypasses the string can take
    cooling_ok: bool = True
    islanded: bool = False           # grid down, battery carrying the site
    runtime_needed_h: Optional[float] = None
    runtime_available_h: Optional[float] = None
    capacity_frac: float = 1.0       # string capacity / beginning of life
    retire_frac: float = 0.7         # brief: 70 % stationary (80 % EV)


@dataclass
class Action:
    kind: str
    cells: List[int] = field(default_factory=list)
    reason: str = ""
    power_limit: Optional[float] = None   # fraction of rated current, for REDUCE_POWER


def fault_sign(c: Cell, lim: Limits) -> bool:
    return c.r_rel >= lim.r_jump or c.dT_dt >= lim.dT_dt_warn


def decide(cells: List[Cell], ctx: Context, lim: Limits = Limits()) -> List[Action]:
    """Actions for this frame, most severe first. An empty-handed frame returns [Action(NORMAL)]."""
    need(len(cells) >= 1, "decide: no cells given")
    bad = [c.i for c in cells if not all(math.isfinite(x) for x in (c.v, c.t, c.soc, c.cap_rel, c.r_rel, c.dT_dt))]
    if bad:   # never bypass or kill on a reading we cannot trust: slow down, and ask for a sensor check
        cells = [c for c in cells if c.i not in bad]
        if not cells:
            return [Action(REDUCE_POWER, bad, "no valid cell readings: sensor check needed", 0.5)]
    acts: List[Action] = []
    hard = [c.i for c in cells if c.t >= lim.t_hard or c.v >= lim.v_hard_hi or c.v <= lim.v_hard_lo]
    faulty = [c.i for c in cells if fault_sign(c, lim)]
    if hard:
        return [Action(KILL, hard, "hard limit (temperature or voltage) crossed")]
    if len(faulty) >= lim.fault_cells_to_kill:
        return [Action(KILL, faulty, "several cells show fault signs at once")]
    if ctx.capacity_frac < ctx.retire_frac:
        return [Action(KILL, [], "string capacity below the retirement level: finished, call a crew")]
    weak = [c.i for c in cells if c.cap_rel < 1.0 - lim.weak_frac and c.bad_cycles >= lim.persist_cycles and c.i not in faulty]
    to_bypass = faulty + weak
    if len(to_bypass) > ctx.bypass_left or ctx.n_engaged - len(to_bypass) < ctx.n_min:
        return [Action(KILL, to_bypass, "no bypass budget or voltage margin left: call a crew")]
    if to_bypass:
        acts.append(Action(BYPASS, to_bypass, "single fault sign" if faulty else "persistently weak against the other cells"))
    cold = min(c.t for c in cells) < lim.t_cold
    hot = [c.i for c in cells if lim.t_soft <= c.t < lim.t_hard and c.i not in to_bypass]
    if cold:
        acts.append(Action(REDUCE_POWER, [], "cells below the charge temperature limit", 0.5))
    if hot:
        if len(hot) / len(cells) >= lim.hot_share_to_derate or not ctx.cooling_ok:
            acts.append(Action(REDUCE_POWER, [], "many cells hot or cooling failed", 0.5))
        acts.append(Action(SWITCH_OUT, hot, "cell hot: rest it until it cools"))
    if ctx.bypass_left - len(to_bypass) <= 1 and (to_bypass or ctx.bypass_left <= 1):
        acts.append(Action(REDUCE_POWER, [], "almost no bypass budget left: protect the remaining cells", 0.7))
    if ctx.islanded and ctx.runtime_needed_h and ctx.runtime_available_h is not None and ctx.runtime_available_h < ctx.runtime_needed_h:
        acts.append(Action(REDUCE_POWER, [], "outage: stretch runtime by shedding load", max(0.2, ctx.runtime_available_h / ctx.runtime_needed_h)))
    done = [c.i for c in cells if c.i not in to_bypass and c.i not in hot and ((c.discharging and c.soc <= lim.soc_lo) or (not c.discharging and c.soc >= lim.soc_hi))]
    if done:
        acts.append(Action(SWITCH_OUT, done, "cell reached its own SOC limit: skip it this half-cycle, string keeps running"))
    if bad:
        acts.append(Action(REDUCE_POWER, bad, "invalid sensor reading on these cells: not judged, check the sensors", 0.7))
    return sorted(acts, key=lambda a: -RANK[a.kind]) or [Action(NORMAL, [], "all cells inside their limits")]
