"""Data-contract watch: look at a data series BEFORE it reaches a plan, and say in plain words what looks wrong.

A plan built on a series whose units flipped (kW read as MW), whose timestamps went stale, or whose zeros really mean "missing"
looks fine and is wrong. These checks catch the common ways that happens. They never fix anything and never change the data:
they return findings with a severity.

    stop   the plan should not be trusted until this is explained
    warn   probably fine, but say so out loud when presenting
    info   worth knowing

Checks (each is a pure function of the numbers, no model involved):
    empty or all missing; share missing; timestamps out of order or duplicated; gaps much longer than the usual step;
    stale (last point older than allowed); values outside a stated plausible range; negatives where none are possible;
    a 1000x unit flip (whole series, or one block of it, e.g. kW in some months and MW in others);
    a stuck sensor (the same value repeated); zeros that look like "missing" (long runs of exact zeros in a series that is positive).

The 'zeros as missing' check comes from the CARE wind data, where some sensors read exactly 0 when they were not recording.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

SEVERITIES = ("stop", "warn", "info")


@dataclass
class Finding:
    series: str
    severity: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.series}: {self.message}"


def _runs(mask: np.ndarray):
    """(start, length) of each run of True."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def check_series(name: str, values, times: Optional[Sequence] = None, *, lo: Optional[float] = None, hi: Optional[float] = None,
                 nonneg: bool = False, unit: str = "", max_age_days: Optional[float] = None, now: Optional[datetime] = None,
                 flat_run: int = 12, zero_run: int = 6, block: int = 24, kind: str = "series", zero_ok: bool = False) -> List[Finding]:
    """Findings for one series. lo/hi = the plausible range in the stated unit (not hard limits: a warning, not a rejection).

    kind: "series" (default) = a measured series where a long flat run or a run of zeros is suspicious (prices, demand, carbon);
          "daily_cycle" = a series that is flat or zero every night or weekend by nature (solar, an office's fixed load, fans):
                          the stuck-value check is skipped, and zeros count as 'maybe missing' only if the series is positive
                          at least 90% of the time (a fixed load, yes; solar, no); all others still run;
          "records" = a table of separate items in no time order (turbine list, past slips): the time, gap, stuck and zero checks are skipped.
    zero_ok: True when exact zeros are normal for this series (solar), so they are never read as 'not recording'.
    Found on real data (EIA-930 solar, DOE reference building, USWTDB, LBNL slips): those checks fired on every one of them, falsely."""
    if kind not in ("series", "daily_cycle", "records"):
        raise ValueError("kind must be 'series', 'daily_cycle' or 'records'")
    if kind == "records":
        times = None
    f: List[Finding] = []
    v = np.asarray(values, dtype=float)
    u = f" {unit}" if unit else ""
    if v.size == 0:
        return [Finding(name, "stop", "empty", "no values at all")]
    miss = np.isnan(v)
    if miss.all():
        return [Finding(name, "stop", "all_missing", "every value is missing")]
    share = float(miss.mean())
    if share > 0.20:
        f.append(Finding(name, "stop", "missing", f"{100 * share:.0f}% of values are missing"))
    elif share > 0.05:
        f.append(Finding(name, "warn", "missing", f"{100 * share:.0f}% of values are missing"))
    ok = v[~miss]
    med = float(np.median(ok))

    if times is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = pd.to_datetime(pd.Series(list(times)), utc=True, errors="raise")
        except Exception:
            t = None
            f.append(Finding(name, "info", "times_unreadable", "timestamps could not be read as dates; time checks skipped"))
        if t is not None:
            if len(t) != len(v):
                f.append(Finding(name, "stop", "length_mismatch", f"{len(t)} timestamps but {len(v)} values"))
            else:
                d = t.diff().dropna().dt.total_seconds().to_numpy()
                if (d < 0).any():
                    f.append(Finding(name, "stop", "out_of_order", f"timestamps go backwards at {int((d < 0).sum())} places"))
                if (d == 0).any():
                    f.append(Finding(name, "warn", "duplicates", f"{int((d == 0).sum())} repeated timestamps"))
                pos = d[d > 0]
                if pos.size:
                    step = float(np.median(pos))
                    big = np.where(d > 3 * step)[0]
                    if big.size:
                        i = int(big[0])
                        f.append(Finding(name, "warn", "gap", f"{big.size} gap(s) longer than 3x the usual step "
                                         f"({step / 3600:.2g} h); first after {t.iloc[i].isoformat()} lasting {d[i] / 3600:.3g} h"))
                if max_age_days is not None:
                    ref = pd.Timestamp(now if now is not None else datetime.utcnow())
                    ref = ref.tz_localize("UTC") if ref.tzinfo is None else ref.tz_convert("UTC")
                    age = (ref - t.max()).total_seconds() / 86400
                    if age > max_age_days:
                        f.append(Finding(name, "warn", "stale", f"last data point is {age:.1f} days old (allowed {max_age_days:g})"))

    if nonneg and (ok < 0).any():
        n = int((ok < 0).sum())
        f.append(Finding(name, "stop" if n > 0.05 * ok.size else "warn", "negative", f"{n} negative values in a series that cannot be negative"))
    if lo is not None or hi is not None:
        out = np.zeros(ok.size, bool)
        if lo is not None:
            out |= ok < lo
        if hi is not None:
            out |= ok > hi
        if out.any():
            n = int(out.sum())
            f.append(Finding(name, "stop" if n > 0.05 * ok.size else "warn", "out_of_range",
                             f"{n} values outside the plausible range [{lo}, {hi}]{u}"))
        # whole-series unit guess: the median is 1000x off but would be plausible after a 1000x change
        if lo is not None and hi is not None and med != 0 and not (lo <= med <= hi):
            if lo <= med * 1000 <= hi:
                f.append(Finding(name, "stop", "unit_flip", f"median {med:.4g} is about 1000x too small for this series{u}: kW given where MW expected, "
                                 "or MWh where kWh expected?"))
            elif lo <= med / 1000 <= hi:
                f.append(Finding(name, "stop", "unit_flip", f"median {med:.4g} is about 1000x too big for this series{u}: MW given where kW expected?"))

    # a series that legitimately goes negative (at least 0.5% of its values): exact zeros and near-zero stretches are real prices there
    crosses_zero = bool((ok < 0).mean() >= 0.005) if ok.size else False

    # a block-wise flip: one stretch of the series sits ~1000x away from the rest
    if ok.size >= 3 * block and med != 0:
        nb = ok.size // block
        meds = np.array([np.median(ok[i * block:(i + 1) * block]) for i in range(nb)])
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.abs(meds) / max(abs(med), 1e-12)
        # A series that really goes negative (day-ahead electricity prices) also has real near-zero days (sunny Sundays, holidays), and a
        # near-zero stretch there is a price level, not a unit change. For such series only the 'too big' side is a block flip.
        small = (ratio < 1 / 300) & (np.abs(meds) > 0) & (not crosses_zero)
        flip = np.where((ratio > 300) | small)[0]
        if flip.size and flip.size < nb / 2:
            f.append(Finding(name, "stop", "unit_flip_block", f"{flip.size} block(s) of {block} values sit about 1000x away from the rest "
                             f"(first block starts at position {int(flip[0]) * block}): units may change partway through"))

    if kind == "series" and ok.size > flat_run:
        same = np.concatenate([[False], np.diff(ok) == 0])
        runs = [r for r in _runs(same) if r[1] + 1 >= flat_run and not (ok[r[0]] == 0)]
        if runs:
            s0, ln = max(runs, key=lambda r: r[1])
            f.append(Finding(name, "warn", "stuck", f"the same value ({ok[s0]:.4g}) repeats {ln + 1} times in a row starting at position {s0 - 1}: stuck sensor or a filled-in gap?"))

    # zeros-as-missing: a plain series must be mostly positive; a daily-cycle series only if it is almost never zero by nature
    # (a building's fixed load, yes; solar, which is zero every night, no)
    if kind != "records" and not zero_ok and not crosses_zero and ok.size > zero_run and (ok > 0).mean() > (0.5 if kind == "series" else 0.9):
        zr = [r for r in _runs(ok == 0) if r[1] >= zero_run]
        if zr:
            s0, ln = max(zr, key=lambda r: r[1])
            f.append(Finding(name, "warn", "zeros_as_missing", f"{len(zr)} run(s) of exact zeros, longest {ln} values (position {s0}), in a series that is "
                             "otherwise positive: zeros may mean 'not recording' rather than a real zero"))
    return f


# ---------- checks on the objects the kit plans with ----------

def _dates_or_none(times):
    """The times if they read as real dates, else None (labels like 'D1 00:00' in the invented examples are not dates)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pd.to_datetime(pd.Series(list(times)), utc=True, errors="raise")
        return times
    except Exception:
        return None


def check_flex_problem(p, max_age_days: Optional[float] = None, now: Optional[datetime] = None) -> List[Finding]:
    """Run the series checks on a FlexProblem's price, carbon, base load and solar.
    max_age_days: set it when the data is meant to be live (a feed); the price series is then checked for staleness.
    A historical replay leaves it None."""
    out: List[Finding] = []
    t = _dates_or_none(p.times)
    out += check_series("price", p.price, t, lo=-500, hi=5000, unit="$/MWh", max_age_days=max_age_days, now=now)
    pv = np.asarray(p.price, float)
    nz = int((pv == 0).sum())
    if nz and float(np.nanmedian(np.abs(pv))) > 10 and nz <= 0.05 * pv.size:
        out.append(Finding("price", "warn", "isolated_zero", f"{nz} step(s) priced at exactly 0.00 while the typical price is {float(np.nanmedian(pv)):.3g}: "
                           "a dropped feed often shows up as zeros (a real price is almost never exactly zero)"))
    out += check_series("carbon", p.carbon, t, nonneg=True, lo=0, hi=1500, unit="kg/MWh")
    pm = float(np.nanmedian(np.abs(p.price)))
    if 0 < pm < 1.0:
        out.append(Finding("price", "stop", "unit_flip", f"median price is {pm:.3g}: that looks like $/kWh, but this field is $/MWh (1000x apart)"))
    cm = float(np.nanmedian(p.carbon))
    if 0 < cm < 2.0:
        out.append(Finding("carbon", "stop", "unit_flip", f"median carbon intensity is {cm:.3g}: that looks like tonnes/MWh, but this field is kg/MWh (1000x apart)"))
    out += check_series("base_load", p.base_load, t, nonneg=True, unit="MW", kind="daily_cycle")
    out += check_series("solar", p.solar, t, nonneg=True, unit="MW", kind="daily_cycle", zero_ok=True)
    # cross-series scale check: everything on one site is in MW, so the biggest and smallest characteristic sizes should be within
    # a couple of orders of magnitude. A whole series in kW (1000x) breaks that even when each series alone looks plausible.
    sizes = {"median fixed load": float(np.nanmedian(p.base_load))}
    if p.battery is not None:
        sizes["battery power"] = float(p.battery.power_mw)
    if np.nanmax(p.solar) > 0:
        sizes["solar peak"] = float(np.nanmax(p.solar))
    for d in p.deferrables:
        sizes[f"{d.name} charger power"] = float(d.power_mw)
    if p.import_limit_mw:
        sizes["import limit"] = float(p.import_limit_mw)
    pos = {k: v for k, v in sizes.items() if v > 0}
    if len(pos) >= 2:
        hi_k, lo_k = max(pos, key=pos.get), min(pos, key=pos.get)
        if pos[hi_k] / pos[lo_k] > 300:
            out.append(Finding("scale", "stop", "scale", f"{hi_k} ({pos[hi_k]:.4g} MW) is {pos[hi_k] / pos[lo_k]:.0f}x {lo_k} ({pos[lo_k]:.4g} MW): "
                               "one of these is probably in kW (or kWh) while the rest are in MW (MWh)"))
    return out


def check_cells(cap_ah, volts=None, pack_v=None, *, v_lo: float = 2.5, v_hi: float = 4.3, weak_frac: float = 0.15,
                flat_run: int = 12, tol_rel: float = 0.02, name: str = "cell") -> List[Finding]:
    """Cell-level data for one series string: tell a WEAK CELL (the thing cell-level control exploits) from a BAD SENSOR (which must
    not be read as a weak cell, and must not be switched around).

    cap_ah: one capacity estimate per cell (Ah).    volts: optional (time x cells) voltage readings.    pack_v: optional pack voltage per step.
    A cell is 'weak' when its capacity is more than weak_frac below the median of the others (weak_frac is an ASSUMED cut-off: say so).
    A cell's sensor is suspect when its voltage is missing, outside [v_lo, v_hi], stuck while the other cells move (flat_run steps), or when
    the cell voltages no longer add up to the pack voltage (tol_rel) and swapping that one column for the median of the others restores
    the sum. A weak-looking cell with a suspect sensor is reported as 'weak_or_sensor': we cannot tell which, so do not act on it.
    Checks that cross-check one measurement against another (sum of cells vs pack) follow the cross-sensor idea of separating sensor
    faults from equipment faults; the thesis that motivated it was not read, so this is the idea only."""
    cap = np.asarray(cap_ah, dtype=float)
    if cap.ndim != 1 or cap.size < 2:
        raise ValueError("cap_ah must be one capacity per cell, at least two cells")
    n = cap.size
    f: List[Finding] = []
    bad_cap = ~np.isfinite(cap) | (cap <= 0)
    for j in np.flatnonzero(bad_cap):
        f.append(Finding(f"{name} {j}", "stop", "bad_capacity", "capacity is missing, zero or negative"))
    suspect = {}
    if volts is not None:
        V = np.asarray(volts, dtype=float)
        if V.ndim != 2 or V.shape[1] != n:
            raise ValueError(f"volts must be (time x {n} cells)")
        if V.shape[0] >= 2:
            same = np.diff(V, axis=0) == 0
        else:
            same = np.zeros((0, n), bool)
        for j in range(n):
            col = V[:, j]
            if np.isnan(col).any():
                suspect[j] = "missing readings"
                f.append(Finding(f"{name} {j}", "warn", "sensor_missing", f"{int(np.isnan(col).sum())} voltage readings are missing"))
                continue
            out = int(((col < v_lo) | (col > v_hi)).sum())
            if out:
                suspect[j] = "voltage outside the plausible range"
                f.append(Finding(f"{name} {j}", "warn", "sensor_range", f"{out} voltage readings are outside {v_lo}-{v_hi} V (a cell does not do that; a sensor does)"))
                continue
            others = np.delete(np.arange(n), j)
            for start, length in _runs(same[:, j]):
                if length + 1 >= flat_run and (~same[start:start + length][:, others]).any(axis=1).mean() > 0.5:
                    suspect[j] = "stuck reading"
                    f.append(Finding(f"{name} {j}", "warn", "sensor_stuck",
                                     f"voltage is frozen for {length + 1} steps while the other cells keep moving"))
                    break
        if pack_v is not None:
            pv = np.asarray(pack_v, dtype=float)
            if pv.shape != (V.shape[0],):
                raise ValueError("pack_v must have one value per time step")
            gap = np.nanmedian(np.abs(V.sum(axis=1) - pv) / np.abs(pv))
            if gap > tol_rel:
                f.append(Finding("pack voltage", "warn", "pack_voltage_mismatch",
                                 f"the cell voltages add up {100 * gap:.1f}% away from the pack voltage (limit {100 * tol_rel:.0f}%)"))
                for j in range(n):
                    if j in suspect:
                        continue
                    W = V.copy()
                    W[:, j] = np.nanmedian(np.delete(V, j, axis=1), axis=1)
                    if np.nanmedian(np.abs(W.sum(axis=1) - pv) / np.abs(pv)) < tol_rel / 2:
                        suspect[j] = "cell voltages only add up to the pack voltage without it"
                        f.append(Finding(f"{name} {j}", "warn", "sensor_suspect_by_sum",
                                         "replacing this cell's voltage with its neighbours' restores the pack voltage: suspect its sensor"))
    ok = ~bad_cap
    if ok.sum() >= 2:
        med = float(np.median(cap[ok]))
        for j in np.flatnonzero(ok & (cap < med * (1.0 - weak_frac))):
            pct = 100.0 * (1.0 - cap[j] / med)
            if int(j) in suspect:
                f.append(Finding(f"{name} {j}", "warn", "weak_or_sensor",
                                 f"capacity is {pct:.0f}% below the median but its voltage sensor is suspect ({suspect[int(j)]}): cannot tell a weak cell from a bad sensor, do not act on it"))
            else:
                f.append(Finding(f"{name} {j}", "info", "weak_cell", f"capacity is {pct:.0f}% below the median ({med:.1f} Ah): a weak cell"))
    return f


def report(findings: List[Finding]) -> pd.DataFrame:
    order = {s: i for i, s in enumerate(SEVERITIES)}
    rows = sorted(findings, key=lambda x: order[x.severity])
    return pd.DataFrame([{"severity": x.severity, "series": x.series, "code": x.code, "what we saw": x.message} for x in rows],
                        columns=["severity", "series", "code", "what we saw"])


def has_stop(findings: List[Finding]) -> bool:
    return any(x.severity == "stop" for x in findings)


def summary_line(findings: List[Finding]) -> str:
    n = {s: sum(1 for x in findings if x.severity == s) for s in SEVERITIES}
    if not findings:
        return "Data contract: no problems found."
    return f"Data contract: {n['stop']} stop, {n['warn']} warning, {n['info']} note."
