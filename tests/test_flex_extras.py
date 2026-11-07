"""Tests for the export cap and the 'battery is used whenever the spread beats its cost' check.

Every number below is worked out by hand in the comment next to it. These tests do not touch the solver's internals: they ask
what a sensible schedule must look like and whether the independent checker agrees.
"""
import numpy as np
import pytest

from hackkit.flex import Battery, FlexProblem, solve_flex, evaluate, violations_flex


def mk(price, base, solar=None, **kw):
    T = len(price)
    return FlexProblem(times=[f"t{i}" for i in range(T)], price=price, carbon=np.zeros(T), base_load=base,
                       solar=np.zeros(T) if solar is None else solar, **kw)


# ---------------- export cap ----------------

def test_export_cap_limits_solar_export_hand_calc():
    # 4 hours, base 0.5 MW, solar 3 MW, price 100, paid 100% of price. Surplus 2.5 MW, cap 1 MW.
    # Exports 1 MW x 4 h = 4 MWh -> revenue 400, nothing bought -> money = -400. The other 1.5 MW of solar is curtailed.
    kw = dict(allow_export=True, export_price_factor=1.0)
    capped = solve_flex(mk([100.0] * 4, [0.5] * 4, [3.0] * 4, export_limit_mw=1.0, **kw))
    assert capped.table["export"].max() == pytest.approx(1.0)
    assert capped.money == pytest.approx(-400.0)
    free = solve_flex(mk([100.0] * 4, [0.5] * 4, [3.0] * 4, **kw))
    assert free.money == pytest.approx(-1000.0)          # 2.5 MW x 4 h x 100, no cap
    assert violations_flex(capped.problem, capped.table["charge"], capped.table["discharge"], capped.loads.to_numpy().T) == []


def test_export_cap_stops_battery_from_pushing_past_it():
    # base 1 MW, no solar, 2 MW battery full at start, price spike in hour 1, export allowed but capped at 0.5 MW.
    # Most the battery may deliver: base 1.0 + cap 0.5 = 1.5 MW, not its 2 MW rating.
    bat = Battery(4.0, 2.0, 1.0, 1.0, soc0_frac=1.0, soc_end_frac=0.0)
    p = mk([10.0, 500.0, 10.0], [1.0, 1.0, 1.0], battery=bat, allow_export=True, export_price_factor=1.0, export_limit_mw=0.5)
    plan = solve_flex(p)
    assert plan.table["discharge"].max() <= 1.5 + 1e-6
    assert plan.table["export"].max() <= 0.5 + 1e-6
    assert violations_flex(p, plan.table["charge"], plan.table["discharge"], plan.loads.to_numpy().T) == []


def test_checker_flags_an_export_the_solar_cannot_curtail_away():
    bat = Battery(4.0, 2.0, 1.0, 1.0, soc0_frac=1.0)
    p = mk([10.0, 10.0], [1.0, 1.0], battery=bat, allow_export=True, export_limit_mw=0.5)
    # Battery pushes 3 MW with base 1 MW: 2 MW would flow out, cap 0.5, no solar to curtail -> must be flagged.
    bad = violations_flex(p, [0.0, 0.0], [3.0, 3.0], np.zeros((0, 2)))
    assert any("export limit" in b for b in bad)
    # Same flow is fine when it is solar that is over the cap (solar can be curtailed).
    p2 = mk([10.0, 10.0], [1.0, 1.0], solar=[3.0, 3.0], allow_export=True, export_limit_mw=0.5)
    assert not any("export limit" in b for b in violations_flex(p2, [0.0, 0.0], [0.0, 0.0], np.zeros((0, 2))))


def test_evaluate_curtails_to_the_cap_and_pays_only_for_what_flows():
    p = mk([100.0] * 2, [0.0] * 2, [4.0] * 2, allow_export=True, export_price_factor=0.5, export_limit_mw=1.0)
    r = evaluate(p, [0.0, 0.0], [0.0, 0.0], np.zeros((0, 2)))
    assert r["export"].tolist() == pytest.approx([1.0, 1.0])
    assert r["money"] == pytest.approx(-(2 * 1.0 * 0.5 * 100.0))   # 2 MWh x half price = -100


def test_no_cap_leaves_old_behaviour_unchanged():
    kw = dict(allow_export=True, export_price_factor=0.8)
    a = solve_flex(mk([30.0, 90.0, 40.0], [0.5] * 3, [2.0] * 3, **kw))
    b = solve_flex(mk([30.0, 90.0, 40.0], [0.5] * 3, [2.0] * 3, export_limit_mw=None, **kw))
    assert a.money == pytest.approx(b.money)
    assert a.money == pytest.approx(-(0.8 * (30 + 90 + 40) * 1.5))


# ---------------- 'the battery is used whenever the spread beats its cost' ----------------

def breakeven_high(low, eff_c, eff_d, degr):
    """Lowest high price at which buying 1 MWh at `low`, storing and selling pays: eff_c x eff_d x (high - degr) = low."""
    return low / (eff_c * eff_d) + degr


def run_two_prices(low, high, eff=0.9, degr=2.0):
    bat = Battery(1.0, 1.0, eff, eff, soc0_frac=0.0, degr_cost=degr)
    plan = solve_flex(mk([low, high], [1.0, 1.0], battery=bat))
    return plan.table["charge"].sum(), plan.table["discharge"].sum()


def test_battery_idle_when_spread_is_below_break_even():
    # eff 0.9 each way, wear 2 per MWh: break-even high price = 20 / 0.81 + 2 = 26.69. At 25 it must not cycle.
    assert breakeven_high(20.0, 0.9, 0.9, 2.0) == pytest.approx(26.6914, abs=1e-3)
    c, d = run_two_prices(20.0, 25.0)
    assert c == pytest.approx(0.0, abs=1e-6) and d == pytest.approx(0.0, abs=1e-6)


def test_battery_cycles_when_spread_beats_break_even():
    c, d = run_two_prices(20.0, 28.0)           # 28 > 26.69, so it must charge and discharge
    assert c > 0.5 and d > 0.5


@pytest.mark.parametrize("seed", range(12))
def test_random_prices_battery_used_iff_a_profitable_pair_exists(seed):
    """Random 6-hour prices. A battery that starts and ends empty can only profit by charging in an earlier hour than it discharges.
    If some earlier/later pair beats break-even by 15%, it must be used; if no pair comes within 15% of break-even, it must be idle."""
    rng = np.random.default_rng(seed)
    price = rng.uniform(10, 60, 6) if seed % 2 == 0 else rng.uniform(30, 32, 6)   # odd seeds: prices too flat to pay for the losses
    eff, degr = 0.9, 1.0
    bat = Battery(2.0, 2.0, eff, eff, soc0_frac=0.0, degr_cost=degr)
    plan = solve_flex(mk(price, [3.0] * 6, battery=bat))
    used = plan.table["discharge"].sum() > 1e-6
    ratios = [(price[j] - degr) * eff * eff / price[i] for i in range(6) for j in range(i + 1, 6)]   # > 1 means that pair pays
    if max(ratios) > 1.15:
        assert used, "a clearly profitable pair existed but the battery stayed idle"
    if max(ratios) < 0.85:
        assert not used, "the battery cycled although no pair could pay for the losses and wear"
    # whatever it did, the independent checker must agree it broke nothing
    assert violations_flex(plan.problem, plan.table["charge"], plan.table["discharge"], plan.loads.to_numpy().T) == []
