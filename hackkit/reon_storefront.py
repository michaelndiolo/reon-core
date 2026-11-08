"""Customer view for a C&I site (Tim Ren: chain stores / small commercial, storm night, 60 kWh, 200-300 cells in series).
Turns the engine's numbers into three things a store owner reads: how many hours the backup lasts, how many years the battery lasts, and dollars.
One series element is either a single large cell (p = 1) or a parallel group of p cells (REON has not said which): the headline depends on it, so it is a switch.
Dollars are bankable-horizon (12 years, warranty is 10) per kWh nameplate x nameplate; life is cell-limited and capped at 30 years.
Everything is a simulation on assumed sodium-ion behaviour; sourced and assumed inputs are tagged in docs/SOURCES.md."""
from __future__ import annotations

import json
import os

import numpy as np

from hackkit import reon_guard as G
from hackkit import reon_storm as S
from hackkit import reon_enviro as EN

N_SERIES = 250
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
    """Rows for the 'what would have to be true' chart: 12-year gain per kWh against cell fade, one line per cells-in-parallel, at one value of a kWh-year.
    Only precomputed cases are used (nothing runs live); missing combinations are skipped. Each row: parallel, fade, gain, verdict."""
    cs = load_cases() if cases is None else cases
    rows = []
    for p in parallels:
        for f in fades:
            c = cs.get(case_key(p, f, value))
            if c:
                rows.append(dict(parallel=int(p), fade=float(f), gain=float(c["dollars_per_kwh"]), verdict=c["verdict"], p10=float(c["p10_per_kwh"])))
    return rows


KS = (1, 2, 4, 8, 16, 25)
OURS = ("selective", "late", "level", "hybrid")


def _kw(p, fade, value, elec, years, n):
    return dict(value_per_kwh_year=float(value), electronics_per_kwh=float(elec), fade_cv=0.45 / np.sqrt(p), fade_mean=float(fade), loss=0.04, years=float(years),
                eol_frac=0.7, trials=8, steps=60, ks=tuple(k for k in KS if k < n) or (1,), window=WINDOW)


def _start(p, n):
    return 100.0 * (1.0 + 0.02 / np.sqrt(p) * np.random.default_rng(3).standard_normal(n))


def backup_hours(packs, nameplate_kwh, load_kw, cold=0.8):
    """Median hours over real packs, plain vs managed, at a steady critical load (cold-weather capacity factor)."""
    plain = [S.hours(v, nameplate_kwh, load_kw, False, cold) for v in packs.values()]
    managed = [S.hours(v, nameplate_kwh, load_kw, True, cold) for v in packs.values()]
    return float(np.median(plain)), float(np.median(managed))


def backup_policies(packs, nameplate_kwh, load_kw, cold=0.8, keep=0.5):
    """Median hours at the same load for: plain string, cell-level control, cell-level control that also sheds the load to `keep` of its size (the site decides which loads are life-safety)."""
    plain = [S.hours(v, nameplate_kwh, load_kw, False, cold) for v in packs.values()]
    managed = [S.hours(v, nameplate_kwh, load_kw, True, cold) for v in packs.values()]
    shed = [S.hours(v, nameplate_kwh, load_kw, True, cold, None, power_fraction=keep) for v in packs.values()]
    return float(np.median(plain)), float(np.median(managed)), float(np.median(shed))


def core(p, fade, value, elec=ELEC, n=N_SERIES):
    """Run the engine (about 12 s at 250 cells): verdict on an independent seed, 12-year gain per kWh, and simulated lives over 30 years."""
    start = _start(p, n)
    rob = G.robust_recommend(start, n, **_kw(p, fade, value, elec, 12.0, n))
    out, _ = G.safe_recommend(start, n, seed=9, **_kw(p, fade, value, elec, 30.0, n))
    t = out["table"]
    nm = out["ours_best"]
    return dict(verdict=rob["verdict"], build=rob["build"], reasons=list(rob["reasons"]), dollars_per_kwh=float(rob["mean_gain"]), p10_per_kwh=float(rob["p10_gain"]),
                life_plain=float(t["plain"]["years"]), life_ours=float(t[nm]["years"]))


def storefront(p, fade, value, elec, packs, load_kw=5.0, nameplate_kwh=60.0, n=N_SERIES, horizon_env=20.0, use_cache=True):
    c = cached_core(p, fade, value) if (use_cache and n == N_SERIES and float(elec) == ELEC) else None
    c = c or core(p, fade, value, elec, n)
    bp, bm = backup_hours(packs, nameplate_kwh, load_kw)
    buy = c["verdict"] == "BUY"
    res = dict(verdict=c["verdict"], build=c["build"], reasons=c["reasons"], dollars_per_kwh=c["dollars_per_kwh"], dollars_total=c["dollars_per_kwh"] * nameplate_kwh,
               p10_total=c["p10_per_kwh"] * nameplate_kwh, life_plain=c["life_plain"], life_ours=c["life_ours"], backup_plain_h=bp, backup_managed_h=bm, nameplate_kwh=nameplate_kwh, load_kw=load_kw)
    res["env"] = EN.environmental(nameplate_kwh, c["life_plain"], c["life_ours"], horizon_env) if buy and c["life_ours"] > c["life_plain"] else None
    return res


def headline(r, state=None, state_hours=None):
    """One plain-language paragraph."""
    if r["verdict"] != "BUY":
        return (f"At these inputs we would not sell you the cell-level switches: a plain string, or a simpler fix, is as good ({'; '.join(r['reasons'])}). "
                f"That is a result, not a failure of the tool.")
    s = (f"On a storm night, a {r['nameplate_kwh']:.0f} kWh battery carrying {r['load_kw']:.0f} kW keeps the lights on about {r['backup_managed_h']:.1f} hours instead of {r['backup_plain_h']:.1f}. "
         f"The battery lasts about {r['life_ours']:.0f} years instead of {r['life_plain']:.0f} before it has to be replaced, and over the first 12 years it is worth about "
         f"${r['dollars_total']:,.0f} more (10th percentile ${r['p10_total']:,.0f}).")
    if state and state_hours:
        s += f" In {state} a typical outage lasts about {state_hours:.1f} hours."
    return s
