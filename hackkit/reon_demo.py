"""reon_demo: the numbers behind the one-screen demo (no Streamlit here, so it can be tested).

Pick a case (cell wear, how cells are wired, what a kWh is worth) and a midnight failure hour; get back what we would tell a store owner: the verdict, backup hours with and without the failure,
battery life, and 12-year dollars against a plain string and against a simple balancer. Dollars and lives come from the precomputed cases (reon_storefront, guarded policy); backup hours are
computed live on the 12 real packs (reon_storm). Everything is a simulation on assumed sodium-ion behaviour, not REON data."""
from __future__ import annotations

import json
import os

import numpy as np

from hackkit import reon_enviro as EN
from hackkit import reon_storefront as SF
from hackkit import reon_storm as S

WEAR = (("Maker's claim", 0.004, "0.4% a year (20,000-cycle claim)"), ("Typical", 0.008, "0.8% a year"), ("Hard", 0.012, "1.2% a year"), ("EV-like", 0.02, "2% a year"))
WIRING = (("One cell per position", 1), ("4 in parallel", 4), ("16 in parallel", 16))
VALUES = ((12, "$12 (grid)"), (22, "$22"), (40, "$40 (demand charge)"), (80, "$80"))
NAMEPLATE_KWH = 60.0
LOAD_KW = 5.0
COLD = 0.8
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def storm(packs, fail_h, load_kw=LOAD_KW, nameplate_kwh=NAMEPLATE_KWH, cold=COLD, keep=0.5):
    """Median backup hours over the real packs: plain, cell-level control, and cell-level control shedding to `keep` of the load; each without a failure and with one cell failing open at hour fail_h."""
    def med(managed, ff, frac=1.0):
        return float(np.median([S.hours(v, nameplate_kwh, load_kw, managed, cold, ff, power_fraction=frac, window=SF.WINDOW if managed else None) for v in packs.values()]))
    return dict(plain=med(False, None), ours=med(True, None), shed=med(True, None, keep),
                plain_fail=med(False, float(fail_h)), ours_fail=med(True, float(fail_h)), shed_fail=med(True, float(fail_h), keep), fail_h=float(fail_h))


def verdict_card(case, nameplate_kwh=NAMEPLATE_KWH):
    """Plain-language card for one cached case. Returns dict(kind BUY|BALANCER|HOLD, title, line, dollars, vs_balancer, balancer, life_plain, life_ours, carbon_t) or None if the case is missing."""
    if not case:
        return None
    k = case["verdict"]
    d = case["dollars_per_kwh"] * nameplate_kwh
    b = case.get("balancer_per_kwh", 0.0) * nameplate_kwh
    vs = case.get("vs_balancer_per_kwh", 0.0) * nameplate_kwh
    carbon = None
    if k == "BUY" and case["life_ours"] > case["life_plain"]:
        carbon = EN.environmental(nameplate_kwh, case["life_plain"], case["life_ours"], 20)["net_t"]
    if k == "BUY":
        title = "Worth it"
        line = f"Cell-level control earns about ${d:,.0f} over 12 years against a plain string, ${vs:,.0f} of it beyond what a simple balancer would give."
    elif k == "BALANCER":
        title = "A simple balancer is enough here"
        line = f"We would tell the owner not to buy cell-level switches: a balancer earns about ${b:,.0f} over 12 years and ours would add under $1 a kWh. We tie it, we do not beat it."
    else:
        title = "Nothing pays here"
        line = "Keep the plain string: neither switches nor a balancer earn their cost at these inputs."
    return dict(kind=k, title=title, line=line, dollars=d, vs_balancer=vs, balancer=b, life_plain=case["life_plain"], life_ours=case["life_ours"], carbon_t=carbon, reasons=list(case.get("reasons", [])))


def proof():
    """How hard the policy has been tested, read from the saved result files: number of runs and the worst shortfall against the better of a balancer or plain (dollars per kWh, 0 = never behind)."""
    runs, worst = 0, 0.0
    def load(name):
        try:
            with open(os.path.join(HERE, "examples", "data", name)) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    for v in load("policy_fuzz.json").get("cases", {}).values():
        runs += 1
        worst = max(worst, float(v.get("regret", 0.0)))
    for v in load("policy_eval.json").get("cases", {}).values():
        if "guarded" in v:
            runs += 1
            worst = max(worst, float(v["guarded"].get("regret", 0.0)))
    for v in load("adversary_vs_guard.json").values():
        for key, x in v.items():
            if key.startswith("balancer") and "error" not in x:
                runs += 1
                worst = max(worst, float(x.get("regret", 0.0)))
    return dict(runs=runs, worst_regret=max(worst, 0.0))
