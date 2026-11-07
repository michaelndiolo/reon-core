"""Learning from data: the unknowns that decide switches-vs-balancer (failure rate, fade-rate spread) are updated as observations arrive.
Not a neural network: with a handful of packs a black-box model would only memorise noise. Instead two small Bayesian updates, then the design engine is re-run on draws from what we believe.
- failure rate per cell-year: Gamma(a, b) prior, updated by (failures seen, cell-years watched). Exact (conjugate), so it also learns from zero failures.
- fade-rate spread (CV): prior pseudo-observations centred on the calibrated fleet value, updated by per-cell fade rates measured from capacity snapshots.
prob_ours_wins() draws (failure rate, CV) from those beliefs, runs reon_design.design_scan for each draw and reports how often late-engaging switches beat the best balancer, and by how much.
Priors are ASSUMED (weakly informative); the update rule is exact. Run examples/reon_learn_example.py to watch it converge."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence
import numpy as np
from hackkit import reon_design as D


@dataclass
class FailureBelief:
    a: float = 0.5      # prior shape: half a failure ...
    b: float = 100.0    # ... in 100 cell-years (prior mean 0.5%/cell-year, wide). ASSUMED.

    def update(self, failures: int, cell_years: float) -> "FailureBelief":
        if failures < 0 or cell_years < 0:
            raise ValueError("counts must be non-negative")
        return FailureBelief(self.a + failures, self.b + cell_years)

    @property
    def mean(self) -> float:
        return self.a / self.b

    def interval(self, p: float = 0.9) -> tuple:
        x = np.random.default_rng(0).gamma(self.a, 1.0 / self.b, 20000)
        return float(np.quantile(x, (1 - p) / 2)), float(np.quantile(x, 1 - (1 - p) / 2))

    def sample(self, n: int, rng) -> np.ndarray:
        return rng.gamma(self.a, 1.0 / self.b, n)


@dataclass
class FadeBelief:
    """Belief about the fade-rate spread (CV). prior_cv from the fleet calibration, prior_n pseudo-cells of confidence."""
    prior_cv: float = 0.10
    prior_n: float = 6.0
    n: int = 0
    ss_rel: float = 0.0   # sum of squared relative deviations of observed fade rates from their mean

    def update(self, fade_rates: Sequence[float]) -> "FadeBelief":
        f = np.asarray(fade_rates, float)
        if len(f) < 2 or f.mean() <= 0:
            return self
        rel = f / f.mean() - 1.0
        return FadeBelief(self.prior_cv, self.prior_n, self.n + len(f) - 1, self.ss_rel + float((rel ** 2).sum()))

    @property
    def cv(self) -> float:
        return float(np.sqrt((self.prior_n * self.prior_cv ** 2 + self.ss_rel) / (self.prior_n + self.n)))

    def sample(self, n: int, rng) -> np.ndarray:
        df = self.prior_n + self.n
        var = (self.prior_n * self.prior_cv ** 2 + self.ss_rel) / rng.chisquare(df, n)  # scaled-inverse-chi-square draw: sigma^2 = SS / chi2(df), SS = df * s^2
        return np.sqrt(var)


def prob_ours_wins(caps: Sequence[float], m: int, fail: FailureBelief, fade: FadeBelief, *, draws: int = 10, trials: int = 30, seed: int = 0,
                   fade_mean: float = 0.04, electronics_per_kwh_cell: float = 8.8, balancer_per_kwh: float = 0.0, value_per_kwh_year: float = 22.0,
                   rate: float = 0.07, years: float = 7.0, eol_frac: float = 0.7, closed_loss: float = 0.0, repair_years: Optional[float] = None,
                   balancer_r: float = 1e9, rivals: str = "all") -> dict:
    """Share of belief draws in which late-engaging switches beat every rival, and the mean advantage (switch minus best rival, net value per kWh nameplate)."""
    rng = np.random.default_rng(seed)
    lams, cvs = fail.sample(draws, rng), np.clip(fade.sample(draws, rng), 0.02, 0.6)
    adv = []
    for lam, cv in zip(lams, cvs):
        adv.append(_advantage(caps, m, float(lam), float(cv), trials=trials, seed=int(rng.integers(1 << 30)), fade_mean=fade_mean,
                              electronics_per_kwh_cell=electronics_per_kwh_cell, value_per_kwh_year=value_per_kwh_year, rate=rate, years=years, eol_frac=eol_frac,
                              closed_loss=closed_loss, repair_years=repair_years, balancer_r=balancer_r, balancer_per_kwh=balancer_per_kwh, rivals=rivals))
    adv = np.array(adv)
    return {"p_win": float((adv > 0).mean()), "mean_advantage": float(adv.mean()), "draws": draws,
            "fail_mean": fail.mean, "fail_interval": fail.interval(), "cv": fade.cv}


def _advantage(caps, m, lam, cv, *, trials, seed, **kw) -> float:
    """Net value of the best late-engaging switch design minus the best of every rival (balancer, converter, sort-only, plain pack) at one failure rate and one fade spread.
    kw rivals="balancer" restores the older switches-versus-balancer-only comparison."""
    kw = dict(kw)
    recs = D.design_scan(caps, m, fade_mean=kw.get("fade_mean", 0.04), fade_cvs=[cv], loss_cell=0.02, loss_exps=[1.0], cost_exps=[1.0],
                         electronics_per_kwh_cell=kw.get("electronics_per_kwh_cell", 8.8), sort_cost_per_kwh=0.0, value_per_kwh_year=kw.get("value_per_kwh_year", 22.0),
                         rate=kw.get("rate", 0.07), years=kw.get("years", 7.0), eol_frac=kw.get("eol_frac", 0.7), test_sigma=0.02, trials=trials, seed=seed,
                         balancer_rs=[kw.get("balancer_r", 1e9)], balancer_eta=0.9, balancer_per_kwh=kw.get("balancer_per_kwh", 0.0),
                         closed_loss=kw.get("closed_loss", 0.0), fail_rate_per_cell_year=lam, repair_years=kw.get("repair_years"))
    best = lambda k: max(r["mean"] for r in recs if r["kind"] == k)
    ours = best("late")
    if kw.get("rivals", "all") == "balancer":
        return ours - best("balancer")
    # every other way to build the pack: balancer, DC-DC converters, sort-only (cells regrouped, no switches), and the plain pack (value 0 by construction)
    sort_only = [r["mean"] for r in recs if r["kind"] == "switch" and r["order"] == "sorted" and "sort only" in r["design"]]
    rivals = [best("balancer"), 0.0]
    if any(r["kind"] == "converter" for r in recs):
        rivals.append(best("converter"))
    if sort_only:
        rivals.append(max(sort_only))
    return ours - max(rivals)


def flip_failure_rate(caps: Sequence[float], m: int, *, cv: float = 0.10, hi: float = 0.2, steps: int = 9, trials: int = 40, seed: int = 3, **kw) -> Optional[float]:
    """Failure rate per cell-year above which late-engaging switches beat the balancer, by bisection on the design engine. 0.0 = they win even with no failures;
    None = they do not win even at `hi`. Same keyword inputs as prob_ours_wins. The advantage rises with the rate, so bisection is valid."""
    if _advantage(caps, m, 0.0, cv, trials=trials, seed=seed, **kw) > 0:
        return 0.0
    if _advantage(caps, m, hi, cv, trials=trials, seed=seed, **kw) <= 0:
        return None
    lo_, hi_ = 1e-4, hi                       # bisect on a log scale: the flip can be 0.1% or 3%, a linear grid of 7 steps over [0, 0.2] was only good to +-0.08%
    if _advantage(caps, m, lo_, cv, trials=trials, seed=seed, **kw) > 0:
        return lo_
    for _ in range(steps):
        mid = (lo_ * hi_) ** 0.5
        if _advantage(caps, m, mid, cv, trials=trials, seed=seed, **kw) > 0:
            hi_ = mid
        else:
            lo_ = mid
    return (lo_ * hi_) ** 0.5


def p_above(fail: FailureBelief, flip: float, n: int = 40000, seed: int = 0) -> float:
    """Belief that the true failure rate is above the flip value (instant: no simulation)."""
    return float((fail.sample(n, np.random.default_rng(seed)) > flip).mean())


def decide(fail: FailureBelief, flip: float, confidence: float = 0.9, n: int = 40000) -> str:
    p = p_above(fail, flip, n)
    return "switches" if p >= confidence else "balancer" if p <= 1 - confidence else "undecided"


def decision_accuracy(true_rate: float, flip: float, cell_years: float, *, fleets: int = 300, confidence: float = 0.9, seed: int = 0,
                      prior: Optional[FailureBelief] = None) -> dict:
    """TEST-RETEST on SIMULATED fleets (never fed to the app's real belief): watch `cell_years` of a fleet whose true rate is known, decide, repeat `fleets` times.
    Returns the share of repeats that decide correctly, wrongly, or stay undecided."""
    rng = np.random.default_rng(seed)
    prior = prior or FailureBelief()
    right = "switches" if true_rate > flip else "balancer"
    out = {"switches": 0, "balancer": 0, "undecided": 0}
    for _ in range(fleets):
        out[decide(prior.update(int(rng.poisson(true_rate * cell_years)), cell_years), flip, confidence, 4000)] += 1
    return {"correct": out[right] / fleets, "wrong": out["switches" if right == "balancer" else "balancer"] / fleets, "undecided": out["undecided"] / fleets}


def cell_years_needed(true_rate: float, flip: float, *, target: float = 0.9, confidence: float = 0.9, fleets: int = 200, seed: int = 0,
                      grid: Sequence[float] = (50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000)) -> Optional[float]:
    """Smallest watched cell-years at which at least `target` of simulated fleets reach the right decision (None if the grid is not enough)."""
    for cy in grid:
        if decision_accuracy(true_rate, flip, cy, fleets=fleets, confidence=confidence, seed=seed)["correct"] >= target:
            return float(cy)
    return None


def interval_coverage(cell_years: float, *, p: float = 0.9, fleets: int = 1000, seed: int = 0, prior: Optional[FailureBelief] = None) -> float:
    """Calibration check: draw true rates from the prior, simulate the failures seen, and count how often the p-interval holds the truth (should be near p)."""
    rng = np.random.default_rng(seed)
    prior = prior or FailureBelief()
    hit = 0
    for _ in range(fleets):
        true = float(prior.sample(1, rng)[0])
        lo, hi = prior.update(int(rng.poisson(true * cell_years)), cell_years).interval(p)
        hit += lo <= true <= hi
    return hit / fleets
