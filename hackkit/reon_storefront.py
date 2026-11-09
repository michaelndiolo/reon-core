"""Customer view for a C&I site (REON: chain stores / small commercial, storm night, 60 kWh, 200-300 cells in series).
Turns the engine's numbers into three things a store owner reads: how many hours the backup lasts, how many years the battery lasts, and dollars.
One series element is either a single large cell (p = 1) or a parallel group of p cells (REON has not said which): the headline depends on it, so it is a switch.
Dollars are bankable-horizon (12 years, warranty is 10) per kWh nameplate x nameplate; life is cell-limited and capped at 30 years.
Everything is a simulation on assumed sodium-ion behaviour; sourced and assumed inputs are tagged in docs/SOURCES.md."""
from __future__ import annotations

import json
import os

import numpy as np

from hackkit import reon_guard as G
from hackkit import reon_policy as POL
from hackkit import reon_storm as S
from hackkit import reon_enviro as EN

N_SERIES = 250
CLOSED_LOSS = 0.02   # ASSUMED: conduction loss of the always-closed series switches, charged on ALL energy of a switched string (REON: overhead 'very minimum, but not none'); the plain string has no switches. Same 2% the backup-hours calculation uses.
WINDOW = 0.9   # share of the 250 cells that must stay in the string (REON CTO: about 90%, unclear); every build respects it. None would mean no voltage limit.
ELEC = 15.5
CASES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "data", "storefront_cases.json")


def case_key(p, fade, value):
    return f"{int(p)}|{float(fade):.4f}|{float(value):g}"


def load_cases(path=CASES_PATH):
    """Precomputed engine results (examples/reon_precompute_cases.py), so the demo is instant. Empty dict if the file is missing."""
    try:
        with open(path) as f:
            return json.load(f).get("cases", {})
    except (OSError, ValueError):
        return {}


def cached_core(p, fade, value, cases=None):
    """The precomputed result for this (p, fade, value) at 250 cells and switch cost 15.5, or None. Fields: verdict, build, reasons, dollars_per_kwh, p10_per_kwh, life_plain, life_ours."""
    return (load_cases() if cases is None else cases).get(case_key(p, fade, value))


GAIN_FADES = (0.004, 0.006, 0.008, 0.012, 0.02)
GAIN_PARALLEL = (1, 4, 16, 40)


def gain_vs_fade(value, cases=None, fades=GAIN_FADES, parallels=GAIN_PARALLEL):
    """Rows for the 'what would have to be true' chart: the EXTRA 12-year gain per kWh our recommended build earns over the better of a simple balancer or a plain string, against cell fade, one line per cells-in-parallel,
    at one value of a kWh-year. It is 0 when the verdict is BALANCER (a balancer is enough) or HOLD. Only precomputed cases are used (nothing runs live); missing combinations are skipped.
    Each row: parallel, fade, gain (extra over the better rival), total (gain over a plain string), verdict, p10 (pessimistic total)."""
    cs = load_cases() if cases is None else cases
    rows = []
    for p in parallels:
        for f in fades:
            c = cs.get(case_key(p, f, value))
            if c:
                extra = float(c.get("vs_balancer_per_kwh", 0.0)) if c["verdict"] == "BUY" else 0.0
                rows.append(dict(parallel=int(p), fade=float(f), gain=extra, total=float(c["dollars_per_kwh"]), verdict=c["verdict"], p10=float(c["p10_per_kwh"])))
    return rows


BAL_PATH = os.path.join(os.path.dirname(CASES_PATH), "balancer_sweep.json")
BAL_LIMITS = (0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15)
BAL_SERIES = (("balancer", "Balancer alone"), ("reon", "REON switches alone"), ("both", "Switches plus balancer"), ("recommended", "Our recommendation"))


def balancer_rows(p, fade, path=BAL_PATH):
    """Rows for the balancer-strength chart: 12-year gain per kWh (value 40) against how much of a cell's capacity a balancer can move per cycle, for three builds.
    Precomputed by examples/reon_balancer_sweep.py; empty list if the case is missing. Each row: limit, series, gain, p10."""
    try:
        with open(path) as f:
            cs = json.load(f).get("cases", {})
    except (OSError, ValueError):
        return []
    rows = []
    for r in BAL_LIMITS:
        c = cs.get(f"{int(p)}|{float(fade):.4f}|{r:.3f}")
        if not c:
            continue
        for key, label in BAL_SERIES:
            rows.append(dict(limit=float(r), series=label, gain=float(c[key]["gain"]), p10=float(c[key]["p10"]), build=c[key]["build"]))
    return rows


def balancer_crossover(rows):
    """Balancer strength (share of a cell's capacity per cycle) above which a balancer alone beats REON switches alone, linearly interpolated; None if switches win at every limit tried, 0.0 if the balancer wins at all of them."""
    bal = sorted((r["limit"], r["gain"]) for r in rows if r["series"] == "Balancer alone")
    sw = {r["limit"]: r["gain"] for r in rows if r["series"] == "REON switches alone"}
    if not bal:
        return None
    d = [(x, g - sw[x]) for x, g in bal]
    if d[0][1] >= 0:
        return 0.0
    for (x0, d0), (x1, d1) in zip(d, d[1:]):
        if d1 >= 0:
            return x0 + (x1 - x0) * (-d0) / (d1 - d0)
    return None


KS = (1, 2, 4, 8, 16, 25)
OURS = ("selective", "late", "level", "hybrid")


def _kw(p, fade, value, elec, years, n):
    return dict(value_per_kwh_year=float(value), electronics_per_kwh=float(elec), fade_cv=0.45 / np.sqrt(p), fade_mean=float(fade), loss=0.04, years=float(years),
                eol_frac=0.7, trials=8, steps=60, ks=tuple(k for k in KS if k < n) or (1,), window=WINDOW, closed_loss=CLOSED_LOSS)


def _start(p, n):
    return 100.0 * (1.0 + 0.02 / np.sqrt(p) * np.random.default_rng(3).standard_normal(n))


def backup_hours(packs, nameplate_kwh, load_kw, cold=0.8):
    """Median hours over real packs, plain vs managed, at a steady critical load (cold-weather capacity factor)."""
    plain = [S.hours(v, nameplate_kwh, load_kw, False, cold) for v in packs.values()]
    managed = [S.hours(v, nameplate_kwh, load_kw, True, cold, window=WINDOW) for v in packs.values()]
    return float(np.median(plain)), float(np.median(managed))


def backup_policies(packs, nameplate_kwh, load_kw, cold=0.8, keep=0.5):
    """Median hours at the same load for: plain string, cell-level control, cell-level control that also sheds the load to `keep` of its size (the site decides which loads are life-safety)."""
    plain = [S.hours(v, nameplate_kwh, load_kw, False, cold) for v in packs.values()]
    managed = [S.hours(v, nameplate_kwh, load_kw, True, cold, window=WINDOW) for v in packs.values()]
    shed = [S.hours(v, nameplate_kwh, load_kw, True, cold, None, power_fraction=keep, window=WINDOW) for v in packs.values()]
    return float(np.median(plain)), float(np.median(managed)), float(np.median(shed))


def core(p, fade, value, elec=ELEC, n=N_SERIES):
    """Run the engine (about 30 s at 250 cells): the guarded policy (reon_policy.robust_guarded) picks on one seed and re-checks on an independent one; it only says BUY when one of our builds beats the better of
    'balancer alone' and 'plain' on both, otherwise BALANCER (a simple balancer is enough: we tie it) or HOLD (tie with plain). Gains are per kWh nameplate vs a plain string; lives are simulated over 30 years."""
    start = _start(p, n)
    rob = POL.robust_guarded(start, n, **_kw(p, fade, value, elec, 12.0, n))
    return dict(verdict=rob["verdict"], build=rob["build"], reasons=list(rob["reasons"]), dollars_per_kwh=float(rob["mean_gain"]), p10_per_kwh=float(rob["p10_gain"]),
                balancer_per_kwh=float(rob["balancer_gain"]), vs_balancer_per_kwh=float(rob["margin_vs_rival"]), life_plain=float(rob["life_plain"]), life_ours=float(rob["life_ours"]))


def storefront(p, fade, value, elec, packs, load_kw=5.0, nameplate_kwh=60.0, n=N_SERIES, horizon_env=20.0, use_cache=True):
    c = cached_core(p, fade, value) if (use_cache and n == N_SERIES and float(elec) == ELEC) else None
    c = c or core(p, fade, value, elec, n)
    bp, bm = backup_hours(packs, nameplate_kwh, load_kw)
    buy = c["verdict"] == "BUY"
    res = dict(verdict=c["verdict"], build=c["build"], reasons=c["reasons"], dollars_per_kwh=c["dollars_per_kwh"], dollars_total=c["dollars_per_kwh"] * nameplate_kwh,
               p10_total=c["p10_per_kwh"] * nameplate_kwh, balancer_total=c.get("balancer_per_kwh", 0.0) * nameplate_kwh, vs_balancer_total=c.get("vs_balancer_per_kwh", 0.0) * nameplate_kwh, life_plain=c["life_plain"], life_ours=c["life_ours"], backup_plain_h=bp, backup_managed_h=bm, nameplate_kwh=nameplate_kwh, load_kw=load_kw)
    res["env"] = EN.environmental(nameplate_kwh, c["life_plain"], c["life_ours"], horizon_env) if buy and c["life_ours"] > c["life_plain"] else None
    return res


def headline(r, state=None, state_hours=None):
    """One plain-language paragraph."""
    if r["verdict"] == "BALANCER":
        return (f"At these inputs a simple balancer already does what our switches would, so we would not sell you cell-level switches here ({'; '.join(r['reasons'])}). "
                f"A balancer is worth about ${r.get('balancer_total', 0):,.0f} over 12 years on a {r['nameplate_kwh']:.0f} kWh battery; we tie that fix, we do not beat it. That is a result, not a failure of the tool.")
    if r["verdict"] != "BUY":
        return (f"At these inputs we would not sell you the cell-level switches: a plain string, or a simpler fix, is as good ({'; '.join(r['reasons'])}). "
                f"That is a result, not a failure of the tool.")
    s = (f"On a storm night, a {r['nameplate_kwh']:.0f} kWh battery carrying {r['load_kw']:.0f} kW keeps the lights on about {r['backup_managed_h']:.1f} hours instead of {r['backup_plain_h']:.1f}. "
         f"The battery lasts about {r['life_ours']:.0f} years instead of {r['life_plain']:.0f} before it has to be replaced, and over the first 12 years it is worth about "
         f"${r['dollars_total']:,.0f} more (10th percentile ${r['p10_total']:,.0f}).")
    if r.get("vs_balancer_total", 0) > 0:
        s += f" That is about ${r['vs_balancer_total']:,.0f} more than a simple balancer alone would give."
    if state and state_hours:
        s += f" In {state} a typical outage lasts about {state_hours:.1f} hours."
    return s