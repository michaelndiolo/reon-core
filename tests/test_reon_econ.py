"""reon_econ: every function is checked against a case worked out by hand, plus the one claim that matters most for honesty
(the held-out score never tunes a rule on the window it is scoring)."""
import numpy as np
import pytest

from hackkit import flex as F
from hackkit import reon_econ as R
from hackkit.flex import Battery, FlexProblem


def mkp(price, base, **kw):
    T = len(price)
    return FlexProblem(times=[f"t{i}" for i in range(T)], price=np.asarray(price, float), carbon=np.zeros(T),
                       base_load=np.asarray(base, float), solar=np.zeros(T), **kw)


def hand_problem():
    # 4 hours, base load 1 MW, prices 10,10,100,100, perfect 1 MW battery that starts empty and must end empty.
    # No battery: 10+10+100+100 = 220.
    # 1 MWh: charge 1 MW in one cheap hour (+10), discharge in one dear hour (-100): saves 90.
    # 2 MWh: charge in both cheap hours (+20), discharge in both dear hours (-200): saves 180.
    return mkp([10.0, 10.0, 100.0, 100.0], [1.0] * 4, battery=Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.0))


def test_control_value_hand_calc():
    cv = R.control_value(hand_problem(), conv_mwh=1.0, ctrl_mwh=2.0)
    assert cv.conventional.money == pytest.approx(130.0)
    assert cv.control.money == pytest.approx(40.0)
    assert cv.saving_money == pytest.approx(90.0)
    assert cv.horizon_hours == 4.0 and cv.regulation is False
    # no demand charge, no regulation: the whole saving is energy, so its share is 100%
    assert cv.split["items"]["energy"] == pytest.approx(90.0)
    assert cv.split["share"]["energy"] == pytest.approx(1.0)
    assert cv.split["share"]["demand_charge"] == pytest.approx(0.0)


def test_equal_capacities_are_worth_nothing_and_bad_input_is_refused():
    p = hand_problem()
    cv = R.control_value(p, 1.5, 1.5)
    assert cv.saving_money == pytest.approx(0.0, abs=1e-9)
    assert cv.split["share"]["energy"] is None          # a share of a zero saving is not reported
    with pytest.raises(ValueError):
        R.control_value(p, 2.0, 1.0)
    with pytest.raises(ValueError):
        R.control_value(p, 0.0, 1.0)
    with pytest.raises(ValueError):
        R.control_value(p.copy(battery=None), 1.0, 2.0)


def test_regulation_is_off_unless_asked_for():
    p = hand_problem().copy(reg_price=np.array([50.0, 50.0, 50.0, 50.0]))
    off = R.control_value(p, 1.0, 2.0)
    on = R.control_value(p, 1.0, 2.0, use_regulation=True)
    assert off.conventional.components["regulation_revenue"] == 0.0
    assert on.conventional.components["regulation_revenue"] >= 0.0
    assert on.regulation is True


def test_value_split_mixed_signs_by_hand():
    base = {"energy": 100.0, "demand_charge": 50.0, "wear": 0.0, "comfort_cost": 0.0, "regulation_revenue": 0.0, "export_revenue": 0.0}
    plan = {"energy": 110.0, "demand_charge": 20.0, "wear": 0.0, "comfort_cost": 0.0, "regulation_revenue": 5.0, "export_revenue": 0.0}
    s = R.value_split(plan, base)
    assert s["items"]["energy"] == pytest.approx(-10.0)          # more energy bought: a cost, not a saving
    assert s["items"]["demand_charge"] == pytest.approx(30.0)
    assert s["items"]["regulation_revenue"] == pytest.approx(5.0)
    assert s["total"] == pytest.approx(25.0)
    assert s["share"]["energy"] == pytest.approx(-0.4)
    assert s["share"]["demand_charge"] == pytest.approx(1.2)      # above 100% of the net: energy cost eats part of it
    assert s["share"]["regulation_revenue"] == pytest.approx(0.2)
    assert sum(v for v in s["share"].values()) == pytest.approx(1.0)
    t = R.split_table(s)
    assert t.iloc[0]["source"] == "Demand charge"                  # biggest absolute contribution first


def test_annualize():
    assert R.annualize(100.0, 24.0) == pytest.approx(100.0 * 365)
    with pytest.raises(ValueError):
        R.annualize(1.0, 0.0)


def test_size_vs_peak_hand_and_monotone():
    p = mkp([10.0, 100.0], [1.0, 1.0], battery=Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.0))
    df = R.size_vs_peak(p, [1.0], duration_h=1.0)                  # site peak 1 MW with the battery idle; 1 MW x 1 h battery
    row = df.iloc[0]
    assert row["power_mw"] == pytest.approx(1.0) and row["energy_mwh"] == pytest.approx(1.0)
    assert row["saving"] == pytest.approx(90.0)                    # 110 do-nothing minus 20
    assert row["saving_pct"] == pytest.approx(100 * 90 / 110)
    assert row["peak_after_mw"] == pytest.approx(2.0)              # 2 MW while charging
    q = F.synth_flex(days=2, seed=3, hvac=False, ev=False)
    d2 = R.size_vs_peak(q, [0.05, 0.1, 0.2, 0.4])
    s = d2["saving"].to_numpy()
    assert np.all(np.diff(s) >= -1e-6)                             # a bigger battery can always copy a smaller one's schedule
    with pytest.raises(ValueError):
        R.size_vs_peak(q, [0.0])


def test_heldout_never_tunes_on_the_window_it_scores(monkeypatch):
    wins = [F.synth_flex(days=2, seed=s, hvac=False, ev=False) for s in range(4)]
    seen = []
    real = F.tune_rule

    def spy(train, *a, **k):
        seen.append(list(train))
        return real(train, *a, **k)

    monkeypatch.setattr(F, "tune_rule", spy)
    out = R.heldout_scores(wins, grid=2, n_boot=200)
    assert len(seen) == 4
    for i, train in enumerate(seen):
        assert len(train) == 3
        assert all(q is not wins[i] for q in train)                # the held-out window is never in its own training set
    assert out["n_windows"] == 4 and 0 <= out["planner_wins"] <= 4
    lo, hi = out["range_pct_90"]
    assert lo <= hi
    assert "perfect forecast" in out["note"]
    assert list(out["windows"].columns) == ["window", "rule_cost", "planner_cost", "improvement_pct"]


def test_heldout_input_checks():
    wins = [F.synth_flex(days=1, seed=s, hvac=False, ev=False) for s in range(2)]
    with pytest.raises(ValueError):
        R.heldout_scores(wins)
    wins3 = [F.synth_flex(days=1, seed=s, hvac=False, ev=False) for s in range(3)]
    with pytest.raises(ValueError):
        R.heldout_scores(wins3, price_forecasts=[w.price for w in wins3[:2]])


def test_capital_recovery_and_life_extension_by_hand():
    assert R.capital_recovery_factor(0.0, 10) == pytest.approx(0.1)
    assert R.capital_recovery_factor(0.1, 1) == pytest.approx(1.1)             # one year: repay capital plus one year's interest
    assert R.capital_recovery_factor(0.05, 20) == pytest.approx(0.0802426, abs=1e-6)   # standard annuity table value
    v = R.life_extension_value(1000.0, 0.0, 10.0, 12.0)
    assert v["annual_cost_conventional"] == pytest.approx(100.0)
    assert v["annual_cost_control"] == pytest.approx(1000 / 12)
    assert v["annual_saving"] == pytest.approx(100 - 1000 / 12)
    assert R.life_extension_value(1000.0, 0.07, 10.0, 10.0)["annual_saving"] == pytest.approx(0.0)
    with pytest.raises(ValueError):
        R.life_extension_value(-1.0, 0.05, 10, 12)
    with pytest.raises(ValueError):
        R.capital_recovery_factor(0.05, 0)


def test_control_npv_by_hand():
    r = R.control_npv(annual_value=100.0, control_capex=300.0, years=5, rate=0.0)
    assert r["npv"] == pytest.approx(200.0)                         # 5 x 100 - 300
    assert r["payback_years"] == pytest.approx(3.0)
    assert r["breakeven_capex"] == pytest.approx(500.0)             # cost at which NPV = 0
    bad = R.control_npv(annual_value=10.0, control_capex=300.0, years=5, rate=0.0)
    assert bad["npv"] == pytest.approx(-250.0) and bad["payback_years"] is None
    with pytest.raises(ValueError):
        R.control_npv(100.0, 300.0, 0, 0.05)
