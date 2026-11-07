import math, pytest
from hackkit import reon_reliability as RL, reon_balance as B, reon_ladder as L, reon_system as S

def test_survival_matches_tim_example():
    assert abs(RL.survival(500, 0.001, 0) - 0.999 ** 500) < 1e-9 and abs(RL.survival(500, 0.001, 0) - 0.6064) < 1e-3
    assert RL.survival(500, 0.001, 4) > 0.999
    assert RL.survival(10, 0.0, 0) == 1.0 and RL.survival(10, 1.0, 9) == 0.0 and RL.survival(3, 1.0, 3) == 1.0
    assert RL.survival(5000, 0.5, 10) < 1e-9
    with pytest.raises(ValueError):
        RL.survival(0, 0.1)

def test_budget_and_required_survival():
    assert RL.budget_for(112, 0.02, 0.99) == 6 or RL.budget_for(112, 0.02, 0.99) in range(5, 8)
    assert abs(RL.required_cell_survival(500, 0.999) - 0.9999980) < 1e-6
    assert RL.bypass_cap(250, 0.9) == 25
    assert abs(RL.p_from_rate(0.002, 10) - 0.0198) < 1e-4

def test_balance_physics():
    a = B.assess(50, 0.3, 0.15)
    assert abs(a["needed_a"] - 2.25) < 1e-9 and a["active_ok"] and not a["passive_ok"]
    assert not B.assess(100, 0.5, 0.15)["active_ok"]
    assert B.efficiency(3.0) == pytest.approx(0.9, abs=1e-9) and B.efficiency(1.0) > B.efficiency(6.0)
    assert B.hours_to_balance(20, 1.0) == 20
    with pytest.raises(ValueError):
        B.needed_current(-1, 0.1)

def test_ladder_orders_and_validates():
    r = L.ladder(trials=200)
    assert r[1] > r[24] > r[240] and abs(r[240]) < 1e-9
    with pytest.raises(ValueError):
        L.ladder(n=241)

def test_system_view_and_incremental():
    assert S.incremental_share(4) == 0.75 and abs(S.incremental_cost(24, 3) - 16) < 1e-9
    t = {"plain": dict(years=10.0, cost=0.0), "late switches": dict(years=20.0, cost=15.5)}
    v = S.system_view(t)
    assert v["late switches"]["system_cycles"] == 7300 and v["late switches"]["share_of_cell_rating"] == pytest.approx(0.365)
    assert v["late switches"]["cost_per_kwh_delivered"] < v["plain"]["cost_per_kwh_delivered"] * 1.0 + 1
