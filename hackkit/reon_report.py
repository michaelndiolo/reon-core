"""reon_report: one call from per-cell capacities to the whole REON story, every number with its assumptions named.

    from hackkit.reon_report import analyze_pack, render_markdown, load_caps_csv
    res = analyze_pack(load_caps_csv("cells.csv")["caps"], electronics_per_kwh=8.8, value_per_kwh_year=22.0, alt_costs=[98.4, 40])
    print(render_markdown(res))

What it combines (each piece has its own module and tests):
    pack model      usable = N x weakest cell without control, sum of cells with it (the model on REON's own slide)        recheck/SPEC.md
    loss            gain left after a switching/conversion loss, and the loss at which the gain disappears                    reon_loss
    window          gain left if the converter needs a minimum number of cells in circuit                                      reon_window
    fragility/noise how much of the gain is one cell, and how much measurement error alone could add                           reon_spread
    checks          weak-cell / data-quality findings                                                                          contract.check_cells
    economics       cost per extra usable kWh, payback, break-even gain against adding cells (only if you give e and value)    reon_unit
    life            service-life ratio if you give per-cell fade rates (linear fade)                                           reon_claim

NO DEFAULT NUMBERS for efficiency, cost, value or fade. Anything you pass is echoed with a source tag (REAL / CITED / ASSUMED; ASSUMED unless you say
otherwise in `sources`). The capacity data are yours to tag too. Limits are listed in the output's 'notes'.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import contract, reon_loss, reon_spread, reon_unit, reon_window
from .atstake import SOURCES
from .reon_claim import life_ratio_linear

NOTES = [
    "Usable energy uses the ideal sum of cells; real packs also have a converter window, switching losses, spare cells and parallel columns (see the loss and window sections).",
    "Gain = mean / min - 1 depends on the weakest cell; see fragility and noise before quoting it.",
    "Economics compare control with a conventional BMS on the same cells, and (if alternative costs are given) with simply adding capacity. Space, weight, voltage and supply limits of adding cells are not priced.",
    "Life ratio assumes cells fade linearly at their own rates and a pack is retired when its fastest cell (conventional) or its average cell (control) reaches end of life.",
]


def parse_caps_text(text: str) -> dict:
    """Cell capacities (Ah) from pasted text or a CSV's contents. Lines starting with # are comments. Accepts one capacity per line, one comma- or space-separated
    line, or a CSV with an optional header (the capacity column is the one named capacity / cap_ah / ah / capacity_ah, else the first column) and an optional
    'fade_rate' column of per-cell fade rates."""
    rows = [r for r in csv.reader(io.StringIO(text)) if r and not r[0].lstrip().startswith("#")]
    rows = [[x.strip() for x in r if x.strip() != ""] for r in rows]
    rows = [r for r in rows if r]
    if not rows:
        raise ValueError("no data rows")
    header = None
    try:
        float(rows[0][0].split()[0])
    except ValueError:
        header = [h.lower() for h in rows[0]]
        rows = rows[1:]
        if not rows:
            raise ValueError("no data rows")
    if header is None and len(rows) == 1:
        rows = [[x] for x in re.split(r"[,\s;]+", " ".join(rows[0])) if x]            # one line holding the whole list
    elif header is None and any(len(r) == 1 and " " in r[0] for r in rows):
        rows = [[x] for r in rows for x in re.split(r"[\s;]+", r[0]) if x]
    col, fade_col = 0, None
    for i, h in enumerate(header or []):
        if h in ("capacity", "cap_ah", "ah", "capacity_ah"):
            col = i
        if h == "fade_rate":
            fade_col = i
    out = {"caps": [float(r[col]) for r in rows], "fade_rates": None}
    if fade_col is not None:
        out["fade_rates"] = [float(r[fade_col]) for r in rows]
    return out


def load_caps_csv(path: str) -> dict:
    """parse_caps_text on a file."""
    with open(path, newline="") as fh:
        return parse_caps_text(fh.read())


def gain_after(caps: Sequence[float], loss: float = 0.0, window_frac: Optional[float] = None) -> float:
    """The gain once both practical haircuts are applied: control usable = window usable x (1 - loss); conventional = N x weakest.
    window_frac = share of the N cells that must stay in circuit (None = the ideal sum, 1.0 = no better than conventional)."""
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size == 0 or not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("caps must be a non-empty list of positive capacities")
    if not (0.0 <= loss < 1.0):
        raise ValueError("loss must be in [0, 1)")
    n = int(c.size)
    if window_frac is None:
        k = 1
    elif 0.0 < window_frac <= 1.0:
        k = max(1, int(np.ceil(window_frac * n)))
    else:
        raise ValueError("window_frac must be in (0, 1]")
    return float(reon_window.window_usable(c, k) * (1.0 - loss) / (n * c.min()) - 1.0)


def _tag(sources: Dict[str, str], key: str) -> str:
    t = sources.get(key, "ASSUMED")
    if t not in SOURCES:
        raise ValueError(f"source for {key} must be one of {SOURCES}")
    return t


def analyze_pack(caps: Sequence[float], *, name: str = "pack", volts: Optional[float] = None, losses: Sequence[float] = (0.02, 0.05),
                 window_fracs: Sequence[float] = (0.9, 0.8, 0.5), noise_sigmas: Sequence[float] = (0.01, 0.02, 0.03), weak_frac: float = 0.05,
                 electronics_per_kwh: Optional[float] = None, alt_costs: Optional[Sequence[float]] = None, value_per_kwh_year: Optional[float] = None,
                 rate: Optional[float] = None, years: Optional[float] = None, fade_rates: Optional[Sequence[float]] = None,
                 sources: Optional[Dict[str, str]] = None) -> dict:
    sources = dict(sources or {})
    c = np.asarray(caps, dtype=float)
    if c.ndim != 1 or c.size == 0 or not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("caps must be a non-empty list of positive capacities")
    n = int(c.size)
    gain = reon_loss.net_gain(c, 1.0)
    res: dict = {"name": name, "tags": {}}
    cells = {"n": n, "min_ah": float(c.min()), "mean_ah": float(c.mean()), "max_ah": float(c.max()), "cv": float(c.std(ddof=1) / c.mean()) if n > 1 else 0.0,
             "conventional_ah": float(n * c.min()), "ideal_ah": float(c.sum()), "gain_ideal": gain, "tag": _tag(sources, "capacities")}
    if volts is not None:
        cells["conventional_kwh"] = cells["conventional_ah"] * volts / 1000.0
        cells["ideal_kwh"] = cells["ideal_ah"] * volts / 1000.0
        cells["extra_kwh"] = cells["ideal_kwh"] - cells["conventional_kwh"]
        res["tags"]["volts"] = _tag(sources, "volts")
    res["cells"] = cells
    res["loss"] = reon_loss.loss_table(c, losses)
    res["loss"]["tag"] = _tag(sources, "losses")
    win = []
    for f in window_fracs:
        k = max(1, int(np.ceil(f * n)))
        r = [x for x in reon_window.window_curve(c) if x["n_min"] == k][0]
        win.append({"fraction": f, "n_min": k, "share_of_ideal_gain": r["share_of_ideal_gain"], "gain": r["gain"]})
    res["window"] = {"rows": win, "tag": _tag(sources, "window_fracs")}
    if n >= 2:
        res["fragility"] = reon_spread.fragility(c)
        res["noise"] = {"rows": [{"sigma": s, "apparent_gain": reon_spread.noise_bias(c, s)["apparent_mean"]} for s in noise_sigmas], "tag": _tag(sources, "noise_sigmas")}
    res["checks"] = [str(f) for f in contract.check_cells(list(c), weak_frac=weak_frac)]
    if electronics_per_kwh is not None and value_per_kwh_year is not None:
        eco = {"electronics_per_kwh": electronics_per_kwh, "value_per_kwh_year": value_per_kwh_year,
               "tags": {"electronics": _tag(sources, "electronics_per_kwh"), "value": _tag(sources, "value_per_kwh_year")}}
        if gain > 0:
            cpk = reon_unit.cost_per_extra_kwh(electronics_per_kwh, gain)
            eco["cost_per_extra_kwh"] = cpk
            eco["payback_years"] = reon_unit.payback_years(cpk, value_per_kwh_year)
            if rate is not None and years is not None:
                eco["levelized_cost_per_extra_kwh_year"] = reon_unit.levelized_cost_per_extra_kwh_year(cpk, rate, years)
        else:
            eco["cost_per_extra_kwh"] = None
            eco["payback_years"] = None
        eco["breakeven_gain"] = {float(a): reon_unit.breakeven_gain(electronics_per_kwh, a) for a in (alt_costs or [])}
        if alt_costs:
            eco["tags"]["alt_costs"] = _tag(sources, "alt_costs")
        if "extra_kwh" in cells:
            eco["value_per_year_total"] = cells["extra_kwh"] * value_per_kwh_year
        res["economics"] = eco
    if fade_rates is not None:
        if len(fade_rates) != n:
            raise ValueError("fade_rates must have one value per cell")
        res["life"] = {"ratio": life_ratio_linear(fade_rates), "tag": _tag(sources, "fade_rates")}
    res["notes"] = list(NOTES)
    return res


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def render_markdown(res: dict) -> str:
    c = res["cells"]
    L: List[str] = [f"# {res['name']}: cell-level control report", ""]
    L.append(f"**Cells:** {c['n']}; capacity min {c['min_ah']:.2f} / mean {c['mean_ah']:.2f} / max {c['max_ah']:.2f} Ah; spread (CV) {c['cv']:.1%} [{c['tag']}]")
    L.append(f"**Usable without control:** {c['conventional_ah']:.1f} Ah (N x weakest). **With ideal control:** {c['ideal_ah']:.1f} Ah (sum). **Gain:** {c['gain_ideal']:.1%}")
    if "extra_kwh" in c:
        L.append(f"**In energy:** {c['conventional_kwh']:.2f} kWh to {c['ideal_kwh']:.2f} kWh (+{c['extra_kwh']:.2f} kWh) at the given cell voltage [{res['tags']['volts']}]")
    L += ["", "## If switching losses take a share [" + res["loss"]["tag"] + "]", f"- Break-even loss: {_pct(res['loss']['break_even_loss'])} (above this, control delivers less than the conventional pack)"]
    for k, v in res["loss"]["net_gain"].items():
        L.append(f"- Net gain at {k:.0%} loss: {_pct(v)}")
    L += ["", "## If the converter needs a minimum share of cells in circuit [" + res["window"]["tag"] + "]"]
    for r in res["window"]["rows"]:
        L.append(f"- Needs {r['fraction']:.0%} of cells ({r['n_min']} of {c['n']}): keeps {_pct(r['share_of_ideal_gain'])} of the ideal gain, net gain {_pct(r['gain'])}")
    if "fragility" in res:
        f = res["fragility"]
        rest = (f"{_pct(f['share_lost'])} of the gain rests on that one cell" if f["share_lost"] >= 0
                else "removing it would RAISE the gain, so the result does not hang on one cell")
        L += ["", "## How solid is the gain", f"- Without the single weakest cell the gain would be {_pct(f['gain_without_weakest'])} ({rest})"]
        for r in res["noise"]["rows"]:
            L.append(f"- If capacities carry {r['sigma']:.0%} measurement error, noise alone shows an apparent gain of {_pct(r['apparent_gain'])} [{res['noise']['tag']}]")
    L += ["", "## Data checks"] + ([f"- {x}" for x in res["checks"]] or ["- no cell flagged at the weak-cell cut-off used"])
    if "economics" in res:
        e = res["economics"]
        L += ["", f"## Economics (electronics {e['electronics_per_kwh']} per kWh of nameplate [{e['tags']['electronics']}]; value {e['value_per_kwh_year']} per extra kWh per year [{e['tags']['value']}])"]
        if e["cost_per_extra_kwh"] is None:
            L.append("- No gain, so nothing to pay for.")
        else:
            L.append(f"- Cost per extra usable kWh: {e['cost_per_extra_kwh']:.1f}; payback {e['payback_years']:.1f} years (no discounting)")
            if "levelized_cost_per_extra_kwh_year" in e:
                L.append(f"- Levelized yearly cost per extra kWh: {e['levelized_cost_per_extra_kwh_year']:.1f} against a yearly value of {e['value_per_kwh_year']}")
        if "value_per_year_total" in e:
            v = e["value_per_year_total"]
            L.append(f"- Value of the extra energy in this pack: {v:.2f} per year" if abs(v) < 100 else f"- Value of the extra energy in this pack: {v:.0f} per year")
        for a, g in e["breakeven_gain"].items():
            L.append(f"- Against adding capacity at {a:g} per kWh: control is cheaper only above a gain of {_pct(g) if g is not None else 'never'} (this pack: {_pct(c['gain_ideal'])})")
    if "life" in res:
        L += ["", f"## Service life (linear fade) [{res['life']['tag']}]", f"- Life ratio, control / conventional: {res['life']['ratio']:.2f}"]
    L += ["", "## Limits"] + [f"- {x}" for x in res["notes"] if "Life ratio" not in x or "life" in res]
    return "\n".join(L) + "\n"
