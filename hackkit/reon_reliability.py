"""System reliability from architecture (REON, 7 Nov): in a series string every cell must work, so survival is r^n and gets worse as exponentially with cell count; making each cell better barely helps.
Tolerating k dead cells (bypass) turns it into 'at most k of n fail'. Independent failures assumed; bypass cannot fix a short or a thermal event (REON's hardware keeps safety authority)."""
import math
from hackkit.reon_guard import need


def p_from_rate(lam_per_cell_year, years):
    need(lam_per_cell_year >= 0 and years >= 0, "reliability: rate and years must be zero or more")
    return 1.0 - math.exp(-lam_per_cell_year * years)


def survival(n, p, k=0):
    """Probability that at most k of n cells fail, each with probability p over the period."""
    need(isinstance(n, int) and n >= 1 and 0.0 <= p <= 1.0 and isinstance(k, int) and k >= 0, "reliability: n >= 1, 0 <= p <= 1, k >= 0 integers")
    k = min(k, n)
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 1.0 if k >= n else 0.0
    pmf = (1.0 - p) ** n
    if pmf == 0.0:   # underflow at huge n: work in logs
        return sum(math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * math.log(p) + (n - j) * math.log1p(-p)) for j in range(k + 1))
    tot = pmf
    for j in range(k):
        pmf *= (n - j) / (j + 1) * p / (1.0 - p)
        tot += pmf
    return min(tot, 1.0)


def required_cell_survival(n, target):
    """What every single cell must achieve for a plain series string of n to survive with probability `target`."""
    need(n >= 1 and 0.0 < target < 1.0, "reliability: n >= 1 and 0 < target < 1")
    return target ** (1.0 / n)


def budget_for(n, p, target, kmax=None):
    """Smallest number of bypassable cells that gets survival to `target` (None if kmax is not enough)."""
    kmax = n if kmax is None else min(kmax, n)
    for k in range(kmax + 1):
        if survival(n, p, k) >= target:
            return k
    return None


def bypass_cap(n, v_min_frac):
    """Most cells that can be bypassed before the string voltage falls below v_min_frac of full (cells treated as equal voltage; sodium sloping curves cost more, see reon_voltage)."""
    need(n >= 1 and 0.0 < v_min_frac <= 1.0, "reliability: n >= 1 and 0 < v_min_frac <= 1")
    return int(math.floor(n * (1.0 - v_min_frac) + 1e-9))
