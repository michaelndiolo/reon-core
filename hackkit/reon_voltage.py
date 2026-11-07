"""Voltage floor: each engaged cell adds its own voltage, the system needs a minimum string voltage, so only so many cells can be bypassed, and fewer as the cells empty (their voltage falls).
Discharge a string at constant power with three ways of running it:
  plain     all cells in series; stops when the first cell reaches its cutoff (the weakest cell) or the string falls below v_min.
  ideal     every cell used until its own cutoff, no voltage floor (what usable = sum of cells assumes).
  floor     every cell used until its own cutoff, but the string must stay at or above v_min: cells that are empty are bypassed only while the rest can still hold v_min.
Cell curves are ASSUMED shapes inside the sourced voltage window (docs/SOURCES.md); the system minimum voltage is REON's inverter and is UNKNOWN, so it is a sweep (fraction of the nominal string voltage)."""
import numpy as np
from hackkit.reon_guard import caps_array, need

# (soc, open-circuit volts). Shapes ASSUMED; sodium-ion window 2.5 to 4.2 V, nominal 3.6 V from a commercial 18650 datasheet (Shenzhen Asia Technology INR18650-20EB).
CURVES = {
    "sodium-ion": ((0.0, 2.5), (0.1, 3.0), (0.5, 3.65), (0.9, 4.05), (1.0, 4.2)),
    "LFP": ((0.0, 2.8), (0.05, 3.15), (0.1, 3.2), (0.9, 3.35), (1.0, 3.6)),
    "NMC": ((0.0, 3.0), (0.1, 3.4), (0.5, 3.7), (0.9, 4.0), (1.0, 4.2)),
}


def ocv(curve, soc):
    xs, ys = zip(*CURVES[curve])
    return np.interp(soc, xs, ys)


def run(caps, curve="sodium-ion", mode="floor", v_min_frac=0.8, c_rate=0.3, r_cell=0.001, q0=100.0, v_cut=0.0, dt=30.0):
    """Hours delivered at constant power. caps: capacity of each cell relative to nominal (1 = q0 Ah). Returns (hours, bypassed_count_at_end)."""
    caps = caps_array(caps, positive=True)
    need(curve in CURVES and mode in ("plain", "ideal", "floor"), "voltage: unknown curve or mode")
    need(0.0 <= v_min_frac < 1.0 and c_rate > 0 and q0 > 0 and r_cell >= 0 and dt > 0, "voltage: 0 <= v_min < 1, c_rate, q0, dt above zero")
    n = len(caps)
    q = caps * q0
    soc = np.ones(n)
    v_nom = float(ocv(curve, 0.5))
    v_min = v_min_frac * n * v_nom
    power = c_rate * q0 * n * v_nom
    cut = float(ocv(curve, 0.02)) if v_cut == 0.0 else v_cut
    t = 0.0
    while t < 100 * 3600:
        v_oc = ocv(curve, soc)
        eng = np.ones(n, bool) if mode == "plain" else (v_oc > cut)
        if not eng.any():
            break
        if mode == "plain" and (v_oc <= cut).any():
            break
        i = power / max(v_oc[eng].sum(), 1e-9)
        for _ in range(3):
            i = power / max((v_oc[eng] - i * r_cell).sum(), 1e-9)
        v_str = (v_oc[eng] - i * r_cell).sum()
        if mode != "ideal" and v_str < v_min:
            break
        soc[eng] -= i * dt / 3600.0 / q[eng]
        soc = np.clip(soc, 0.0, 1.0)
        t += dt
    return t / 3600.0, int(n - eng.sum())


def bypass_room(n: int, soc: float, curve="sodium-ion", v_min_frac=0.8, i_r=0.0) -> int:
    """Most cells that can be bypassed at this SOC if every cell is at that SOC (a worst-case rule of thumb)."""
    need(n >= 1 and 0.0 <= soc <= 1.0 and curve in CURVES and 0 < v_min_frac < 1, "bypass_room: bad arguments")
    v_nom = float(ocv(curve, 0.5))
    v_cell = float(ocv(curve, soc)) - i_r
    return int(max(0, np.floor(n - v_min_frac * n * v_nom / v_cell)))
