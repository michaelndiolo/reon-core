"""Plain project finance for a storage add-on: NPV, IRR, payback, tax with straight-line depreciation, and break-even capex.

Everything here is arithmetic on the cash flows you give it; it never invents an input. Year 0 is the investment; years 1..N are operating years.
Real terms (no inflation), unlevered (all equity) unless you pass your own discount rate for a levered case. Taxes and the discount rate are
inputs you must label ASSUMED or CITED in any pitch. No degradation is modelled here: pass a revenue path that already contains it.
"""
from typing import Optional, Sequence

import numpy as np
from scipy.optimize import brentq


def npv(rate: float, cashflows: Sequence[float]) -> float:
    """Net present value with cashflows[0] at time 0."""
    cf = np.asarray(cashflows, float)
    return float(np.sum(cf / (1.0 + rate) ** np.arange(len(cf))))


def irr(cashflows: Sequence[float]) -> Optional[float]:
    """Rate at which NPV is zero, or None if there is no sign change (always lose or always gain)."""
    cf = np.asarray(cashflows, float)
    if not ((cf > 0).any() and (cf < 0).any()):
        return None
    f = lambda r: npv(r, cf)
    lo, hi = -0.99, 10.0
    if f(lo) * f(hi) > 0:
        return None
    return float(brentq(f, lo, hi))


def payback_years(cashflows: Sequence[float]) -> Optional[float]:
    """Years until cumulative (undiscounted) cash turns non-negative, interpolated within the year; None if never."""
    cum = np.cumsum(np.asarray(cashflows, float))
    if cum[0] >= 0:
        return 0.0
    for i in range(1, len(cum)):
        if cum[i] >= 0:
            return float(i - 1 + (-cum[i - 1]) / (cum[i] - cum[i - 1]))
    return None


def _rates(tax_rate, n: int) -> np.ndarray:
    """A single rate, or one rate per operating year (a schedule such as a corporate tax cut); must have n entries then."""
    t = np.atleast_1d(np.asarray(tax_rate, float))
    if t.size == 1:
        return np.full(n, float(t[0]))
    if t.size != n:
        raise ValueError(f"tax schedule has {t.size} entries but there are {n} operating years")
    return t


def storage_cashflows(capex: float, revenue: Sequence[float], om: float, tax_rate=0.0, life: Optional[int] = None) -> np.ndarray:
    """Cash flows of a storage add-on. revenue[i] is the extra revenue in operating year i+1 (already net of any wear and degradation); om is the
    yearly fixed cost (including any augmentation); depreciation is straight line over `life` years (default: the number of revenue years); tax is
    paid on (revenue - om - depreciation) when that is positive, and a loss is simply not refunded (conservative). tax_rate is one number or one
    number per operating year."""
    rev = np.asarray(revenue, float)
    n = len(rev)
    life = n if life is None else life
    tax = _rates(tax_rate, n)
    dep = capex / life
    cf = np.zeros(n + 1)
    cf[0] = -capex
    for i in range(n):
        taxable = rev[i] - om - (dep if i < life else 0.0)
        cf[i + 1] = rev[i] - om - tax[i] * max(taxable, 0.0)
    return cf


def breakeven_capex(revenue: Sequence[float], om_share_of_capex: float, rate: float, tax_rate=0.0, om_fixed: float = 0.0) -> Optional[float]:
    """Capex at which NPV = 0 when the yearly fixed cost is `om_share_of_capex` x capex plus `om_fixed` (a currency amount that does not move with
    capex). None if revenue cannot cover even the fixed cost."""
    rev = np.asarray(revenue, float)

    def f(c):
        return npv(rate, storage_cashflows(c, rev, om_share_of_capex * c + om_fixed, tax_rate))

    if f(1e-6) <= 0:
        return None
    hi = 1.0
    while f(hi) > 0 and hi < 1e15:
        hi *= 2.0
    return float(brentq(f, 1e-6, hi))
