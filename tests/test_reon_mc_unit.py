"""reon_mc (triangular Latin hypercube Monte Carlo) and reon_unit (cost per extra kWh, break-even gain, payback), by hand and by property."""
import numpy as np
import pytest

from hackkit import reon_carbon as C
from hackkit import reon_mc as M
from hackkit import reon_unit as U
from hackkit.atstake import Lever


def test_triangular_by_hand():
    assert M.triangular_ppf(0.0, 0, 1, 4) == pytest.approx(0)
    assert M.triangular_ppf(1.0, 0, 1, 4) == pytest.approx(4)
    assert M.triangular_ppf(0.25, 0, 1, 4) == pytest.approx(1.0)       # F(mode) = (1-0)/(4-0) = 0.25
    assert M.triangular_ppf(0.5, 0, 2, 4) == pytest.approx(2.0)        # symmetric
    assert M.triangular_ppf(0.3, 5, 5, 5) == pytest.approx(5)          # degenerate
    with pytest.raises(ValueError):
        M.triangular_ppf(0.5, 1, 0, 2)


def test_lhs_one_per_stratum_and_moments():
    rng = np.random.default_rng(1)
    u = M.lhs_unit(1000, rng)
    assert sorted((u * 1000).astype(int).tolist()) == list(range(1000))
    lv = [Lever("x", 1.0, 0.0, 4.0)]
    x = M.sample_levers(lv, 20000, seed=2)["x"]
    assert x.mean() == pytest.approx((0 + 1 + 4) / 3, abs=0.01)         # triangular mean
    assert x.min() >= 0 and x.max() <= 4
    assert M.sample_levers(lv, 200, seed=7)["x"] == pytest.approx(M.sample_levers(lv, 200, seed=7)["x"])   # reproducible
    with pytest.raises(ValueError):
        M.sample_levers(lv, 10)


def test_monte_carlo_known_answers():
    lv = [Lever("x", 0.5, 0.0, 1.0)]
    r = M.monte_carlo(lv, lambda v: v["x"] - 0.5, n=20000)
    assert r["prob_negative"] == pytest.approx(0.5, abs=0.01)           # symmetric around the mode
    assert r["p50"] == pytest.approx(0.0, abs=0.01)
    lv2 = [Lever("a", 1.0, 0.0, 2.0), Lever("b", 2.0, 1.0, 3.0)]
    r2 = M.monte_carlo(lv2, lambda v: v["a"] + v["b"], n=20000)
    assert r2["mean"] == pytest.approx(3.0, abs=0.02)


def test_monte_carlo_on_carbon_balance():
    levers = [Lever(C.EMBODIED, 84.0, 61.0, 106.0), Lever(C.EXTRA_KWH, 134.0, 24.0, 314.0), Lever(C.DISPLACED, 0.5, 0.0, 1.0),
              Lever(C.CONTROL_EMBODIED, 800.0, 200.0, 2000.0), Lever(C.GRID_SAVED, 0.0, 0.0, 0.2), Lever(C.YEARS, 7.0, 3.0, 10.0)]
    r = M.monte_carlo(levers, lambda v: C.carbon_balance(v)["net_t"], n=4000)
    s = C.sensitivity(levers)
    assert s["min_net_t"] <= r["p5"] <= r["p95"] <= s["max_net_t"]      # draws stay inside the corners
    assert 0.0 <= r["prob_negative"] < 0.5                              # the sign can flip, but is unlikely on these ranges


def test_unit_by_hand():
    assert U.cost_per_extra_kwh(8.0, 0.25) == pytest.approx(40.0)
    assert U.breakeven_gain(8.0, 40.0) == pytest.approx(0.25)
    assert U.breakeven_gain(8.0, 8.0) is None and U.breakeven_gain(8.0, 5.0) is None
    assert U.payback_years(40.0, 20.0) == pytest.approx(2.0)
    assert U.levelized_cost_per_extra_kwh_year(40.0, 0.0, 5.0) == pytest.approx(8.0)
    assert U.levelized_cost_per_extra_kwh_year(40.0, 0.0, 5.0, om_per_kwh_year=1.5) == pytest.approx(9.5)
    for bad in (lambda: U.cost_per_extra_kwh(8, 0), lambda: U.payback_years(10, 0), lambda: U.breakeven_gain(8, 0)):
        with pytest.raises(ValueError):
            bad()


def test_breakeven_is_the_tie_point():
    rng = np.random.default_rng(4)
    for _ in range(50):
        e, c = float(rng.uniform(1, 20)), float(rng.uniform(21, 150))
        g = U.breakeven_gain(e, c)
        assert U.cost_per_extra_kwh(e, g) == pytest.approx(c)
        assert U.cost_per_extra_kwh(e, g * 1.2) < c < U.cost_per_extra_kwh(e, g * 0.8)


def test_repay_thresholds_flip_exactly_at_the_boundary():
    from hackkit import reon_unit as U
    g, e, v, r, y = 0.186, 8.8, 22.0, 0.07, 7.0
    t = U.repay_thresholds(g, e, v, r, y)
    lev = lambda ee, gg: U.levelized_cost_per_extra_kwh_year(U.cost_per_extra_kwh(ee, gg), r, y)
    assert lev(t["max_electronics_per_kwh"], g) == pytest.approx(v)
    assert lev(e, t["min_gain"]) == pytest.approx(v)
    assert t["min_value_per_kwh_year"] == pytest.approx(lev(e, g))
    assert U.repay_thresholds(g, e, 3.0, r, y)["min_gain"] is None or U.repay_thresholds(g, e, 3.0, r, y)["extra_loss_tolerated"] is None
