import numpy as np
import pytest

from hackkit.flex import (Battery, Deferrable, DemandCharge, Thermal, FlexProblem, Rule, solve_flex, evaluate,
                          evaluate_s, violations_flex, baseline_asap, replay, adjusted_objective, hindsight,
                          synth_flex, flex_monte_carlo, flex_from_prices, noisy_forecast, simulate_temperature,
                          comfort_degree_hours, tune_rule, HOURS_PER_MONTH)

MONTH = HOURS_PER_MONTH


def mk(price, base, carbon=None, **kw):
    T = len(price)
    return FlexProblem(times=[f"t{i}" for i in range(T)], price=price, carbon=carbon if carbon is not None else np.zeros(T),
                       base_load=base, solar=np.zeros(T), **kw)


# ---------------- v1 behaviour (energy, battery, deferrable loads, carbon) ----------------

def test_battery_arbitrage_hand_calc():
    bat = Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.0)
    plan = solve_flex(mk([10.0, 100.0], [1.0, 1.0], battery=bat))
    assert plan.money == pytest.approx(20.0)
    assert plan.table["charge"].tolist() == pytest.approx([1.0, 0.0])
    assert plan.table["discharge"].tolist() == pytest.approx([0.0, 1.0])
    sized = solve_flex(mk([10.0, 100.0], [5.0, 5.0], battery=Battery(1.0, 5.0, 1.0, 1.0, soc0_frac=0.0)))
    assert sized.battery_energy_value == pytest.approx(90.0, rel=1e-3)
    powered = solve_flex(mk([10.0, 100.0], [5.0, 5.0], battery=Battery(50.0, 1.0, 1.0, 1.0, soc0_frac=0.0)))
    assert powered.battery_power_value > 0


def test_round_trip_losses_hand_calc():
    bat = Battery(10.0, 1.0, 0.9, 0.9, soc0_frac=0.0)
    plan = solve_flex(mk([10.0, 100.0], [1.0, 1.0], battery=bat))
    assert plan.table.loc[0, "charge"] == pytest.approx(1.0)
    assert plan.money < solve_flex(mk([10.0, 100.0], [1.0, 1.0])).money


def test_flexible_load_picks_cheapest_hours():
    job = Deferrable("ev", energy_mwh=2.0, power_mw=1.0, start=0, end=4)
    plan = solve_flex(mk([50.0, 10.0, 30.0, 80.0], [0, 0, 0, 0], deferrables=[job]))
    assert plan.loads["ev"].tolist() == pytest.approx([0, 1, 1, 0])
    assert plan.money == pytest.approx(40.0)


def test_deadline_is_respected_and_infeasible_is_explained():
    job = Deferrable("ev", 2.0, 1.0, start=0, end=2)
    plan = solve_flex(mk([50.0, 60.0, 1.0, 1.0], [0, 0, 0, 0], deferrables=[job]))
    assert plan.loads["ev"].tolist() == pytest.approx([1, 1, 0, 0])
    with pytest.raises(ValueError):
        solve_flex(mk([1.0, 1.0], [0, 0], deferrables=[Deferrable("big", 5.0, 1.0, 0, 2)]))


def test_import_limit_forces_spreading_and_has_a_price():
    job = Deferrable("ev", 2.0, 2.0, start=0, end=2)
    free = solve_flex(mk([10.0, 20.0], [0, 0], deferrables=[job]))
    capped = solve_flex(mk([10.0, 20.0], [0, 0], deferrables=[job], import_limit_mw=1.0))
    assert capped.loads["ev"].tolist() == pytest.approx([1, 1])
    assert capped.money > free.money
    assert capped.import_limit_value > 0


def test_carbon_price_moves_the_load_to_cleaner_hours():
    job = Deferrable("ev", 1.0, 1.0, start=0, end=2)
    cheap_dirty = mk([10.0, 11.0], [0, 0], carbon=np.array([500.0, 100.0]), deferrables=[job])
    assert solve_flex(cheap_dirty).loads["ev"].tolist() == pytest.approx([1, 0])
    assert solve_flex(cheap_dirty.copy(carbon_price=0.05)).loads["ev"].tolist() == pytest.approx([0, 1])


# ---------------- demand charge ----------------

def test_demand_charge_hand_calc():
    # base 1 and 3 MW, price 10, battery 2 MWh / 1 MW starting half full. Best peak = 3 - 1 = 2 MW.
    bat = Battery(2.0, 1.0, 1.0, 1.0, soc0_frac=0.5)
    dc = DemandCharge(10.0, billing_hours=MONTH)           # $10 per kW-month, full month => $10,000 per MW
    p = mk([10.0, 10.0], [1.0, 3.0], battery=bat, demand_charge=dc)
    plan = solve_flex(p)
    assert plan.peak_mw == pytest.approx(2.0)
    assert plan.components["demand_charge"] == pytest.approx(20000.0)
    assert plan.money == pytest.approx(40.0 + 20000.0)     # 2 MWh in each hour at $10
    nobat = solve_flex(mk([10.0, 10.0], [1.0, 3.0], demand_charge=dc))
    assert nobat.components["demand_charge"] == pytest.approx(30000.0)


def test_demand_charge_floor_mask_and_proration():
    bat = Battery(2.0, 1.0, 1.0, 1.0, soc0_frac=0.5)
    dc = DemandCharge(10.0, billing_hours=MONTH)
    floor = solve_flex(mk([10.0, 10.0], [1.0, 3.0], battery=bat, demand_charge=dc, peak_floor_mw=2.5))
    assert floor.components["demand_charge"] == pytest.approx(25000.0)      # already billed at 2.5, no point shaving to 2
    masked = solve_flex(mk([10.0, 10.0], [1.0, 3.0], demand_charge=DemandCharge(10.0, mask=np.array([True, False]),
                                                                              billing_hours=MONTH)))
    assert masked.components["demand_charge"] == pytest.approx(10000.0)      # only hour 1 counts
    assert DemandCharge(10.0).factor(2, 1.0) == pytest.approx(2 / MONTH)


# ---------------- regulation ----------------

def test_regulation_revenue_hand_calc():
    bat = Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.5)
    plan = solve_flex(mk([10.0, 10.0], [0.0, 0.0], battery=bat, reg_price=np.array([8.0, 8.0])))
    assert plan.table["reg"].tolist() == pytest.approx([1.0, 1.0])
    assert plan.components["regulation_revenue"] == pytest.approx(16.0)
    assert plan.money == pytest.approx(-16.0)


def test_regulation_is_limited_by_stored_energy():
    # 0.2 MWh battery holding 0.1 MWh: 0.25 h of headroom per MW => at most 0.4 MW both up and down
    bat = Battery(0.2, 1.0, 1.0, 1.0, soc0_frac=0.5)
    plan = solve_flex(mk([10.0, 10.0], [0.0, 0.0], battery=bat, reg_price=np.array([8.0, 8.0])))
    assert plan.table["reg"].tolist() == pytest.approx([0.4, 0.4])
    assert plan.components["regulation_revenue"] == pytest.approx(6.4)
    p = mk([10.0, 10.0], [0.0, 0.0], battery=bat)
    assert violations_flex(p, [0, 0], [0, 0], np.zeros((0, 2)), reg=[0.4, 0.4]) == []
    assert violations_flex(p, [0, 0], [0, 0], np.zeros((0, 2)), reg=[0.6, 0.0])      # not backed by stored energy


def test_regulation_competes_with_arbitrage():
    bat = Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.0)
    arb_only = solve_flex(mk([10.0, 100.0], [1.0, 1.0], battery=bat))
    both = solve_flex(mk([10.0, 100.0], [1.0, 1.0], battery=bat, reg_price=np.array([1.0, 1.0])))
    assert both.objective <= arb_only.objective + 1e-6
    big = solve_flex(mk([10.0, 100.0], [1.0, 1.0], battery=bat, reg_price=np.array([500.0, 500.0])))
    assert big.table["reg"].sum() > 0 and big.table["discharge"].sum() == pytest.approx(0.0)   # paid more to stand by


# ---------------- ramp limits ----------------

def test_import_ramp_hand_calc():
    job = Deferrable("ev", 2.0, 2.0, start=0, end=2)
    free = solve_flex(mk([10.0, 50.0], [0, 0], deferrables=[job]))
    assert free.money == pytest.approx(20.0)
    ramped = solve_flex(mk([10.0, 50.0], [0, 0], deferrables=[job], import_ramp_mw=1.0))
    assert ramped.table["import"].tolist() == pytest.approx([1.5, 0.5])
    assert ramped.money == pytest.approx(40.0)
    start_low = solve_flex(mk([10.0, 50.0], [0, 0], deferrables=[job], import_ramp_mw=1.0, prev_import_mw=0.0))
    assert start_low.table["import"].tolist() == pytest.approx([1.0, 1.0])
    assert start_low.money == pytest.approx(60.0)


def test_battery_ramp_hand_calc():
    bat = Battery(2.0, 2.0, 1.0, 1.0, soc0_frac=0.0, ramp_mw=1.0)
    plan = solve_flex(mk([10.0, 100.0], [2.0, 2.0], battery=bat))
    assert plan.table["charge"].tolist() == pytest.approx([0.5, 0.0])
    assert plan.table["discharge"].tolist() == pytest.approx([0.0, 0.5])
    assert plan.money == pytest.approx(175.0)
    p = mk([10.0, 100.0], [2.0, 2.0], battery=bat)
    assert violations_flex(p, [2.0, 0.0], [0.0, 2.0], np.zeros((0, 2)))       # swings 4 MW in one step


# ---------------- building heating and cooling ----------------

def _room(**kw):
    return Thermal(t_out=np.full(3, 30.0), ua_mw_per_c=0.2, cap_mwh_per_c=1.0, cop_cool=2.0, cop_heat=2.0,
                   max_cool_mw=2.0, max_heat_mw=2.0, band_occ=(24.0, 24.0), band_unocc=(24.0, 24.0), t0=24.0, **kw)


def test_steady_state_cooling_hand_calc():
    # holding 24 C against 30 C outside: loss = 0.2 x 6 = 1.2 MW of heat; a COP of 2 needs 0.6 MW of power
    plan = solve_flex(mk([10.0, 10.0, 10.0], [0, 0, 0], thermal=_room()))
    assert plan.table["cool"].tolist() == pytest.approx([0.6, 0.6, 0.6])
    assert plan.money == pytest.approx(18.0)
    assert plan.comfort_degree_hours == pytest.approx(0.0, abs=1e-6)


def test_lp_temperature_matches_independent_simulation():
    p = mk([30.0, 10.0, 80.0], [0, 0, 0], thermal=Thermal(t_out=np.array([30.0, 33.0, 36.0]), t0=22.5, occupied=np.array([False, True, True])))
    plan = solve_flex(p)
    sim = simulate_temperature(p, plan.table["cool"].to_numpy(), plan.table["heat"].to_numpy())
    assert sim == pytest.approx(plan.table["temp"].to_numpy(), abs=1e-6)
    s = plan.schedule()
    assert evaluate_s(p, s)["objective"] == pytest.approx(plan.objective, rel=1e-6, abs=1e-6)


def test_comfort_is_soft_and_priced():
    hot = Thermal(t_out=np.full(3, 45.0), ua_mw_per_c=0.2, cap_mwh_per_c=1.0, cop_cool=2.0, max_cool_mw=0.1,
                  band_occ=(24.0, 24.0), band_unocc=(24.0, 24.0), t0=24.0, comfort_penalty=100.0)
    plan = solve_flex(mk([10.0, 10.0, 10.0], [0, 0, 0], thermal=hot))
    assert plan.comfort_degree_hours > 0
    p = mk([10.0, 10.0, 10.0], [0, 0, 0], thermal=hot)
    assert plan.comfort_degree_hours == pytest.approx(comfort_degree_hours(p, plan.table["temp"].to_numpy()), rel=1e-6)
    assert plan.components["comfort_cost"] == pytest.approx(100.0 * plan.comfort_degree_hours)


def test_precooling_beats_a_plain_thermostat_when_prices_differ():
    T = 24
    h = np.arange(T)
    price = np.where((h >= 15) & (h <= 19), 160.0, 30.0)
    th = Thermal(t_out=27 + 6 * np.sin((h - 9) / 24 * 2 * np.pi), occupied=(h >= 7) & (h <= 19),
                 gains_mw=np.where((h >= 7) & (h <= 19), 0.45, 0.1), t0=22.5)
    p = mk(price, np.full(T, 1.0), thermal=th)
    smart = solve_flex(p)
    plain = evaluate_s(p, baseline_asap(p))
    assert smart.comfort_degree_hours < 1e-6
    assert smart.objective < plain["objective"]


# ---------------- whole-model consistency ----------------

def test_planner_output_passes_the_independent_checker_and_matches_evaluate():
    for seed in range(5):
        for season in ("summer", "winter"):
            p = synth_flex(days=2, seed=seed, season=season)
            plan = solve_flex(p, with_values=False)
            s = plan.schedule()
            assert violations_flex(p, s.charge, s.discharge, s.loads, reg=s.reg, hvac=s.cool + s.heat,
                                   cool=s.cool, heat=s.heat) == [], (seed, season)
            ev = evaluate_s(p, s)
            assert ev["money"] == pytest.approx(plan.money, rel=1e-4, abs=1e-2)
            assert ev["objective"] == pytest.approx(plan.objective, rel=1e-4, abs=1e-2)


def test_ramps_also_hold_in_the_full_model():
    p = synth_flex(days=2, seed=2)
    p = p.copy(import_ramp_mw=1.2, battery=Battery(6.0, 2.0, degr_cost=6.0, ramp_mw=1.5))
    plan = solve_flex(p, with_values=False)
    s = plan.schedule()
    assert violations_flex(p, s.charge, s.discharge, s.loads, reg=s.reg, hvac=s.cool + s.heat, cool=s.cool, heat=s.heat) == []


def test_checker_catches_a_bad_schedule():
    bat = Battery(1.0, 1.0, soc0_frac=0.0)
    p = mk([10.0, 20.0], [1.0, 1.0], battery=bat)
    assert violations_flex(p, [2.0, 0.0], [0.0, 0.0], np.zeros((0, 2)))
    assert violations_flex(p, [0.0, 0.0], [1.0, 0.0], np.zeros((0, 2)))


def test_planner_never_costs_more_than_doing_nothing_and_each_term_has_value():
    for seed in range(4):
        p = synth_flex(days=2, seed=seed)
        a = evaluate_s(p, baseline_asap(p))["objective"]
        opt = solve_flex(p, with_values=False).objective
        assert opt <= a + 1e-6
        assert opt <= solve_flex(p.copy(battery=None, reg_price=None), with_values=False).objective + 1e-6


def test_rolling_replay_obeys_limits_and_perfect_forecast_is_near_hindsight():
    p = synth_flex(days=2, seed=3)
    r = replay(p, p.price, p.solar, policy="planner", horizon=24)
    assert r["violations"] == []
    h = hindsight(p)
    assert adjusted_objective(p, r) >= h.objective - 1e-6
    assert adjusted_objective(p, r) <= h.objective * 1.25 + 50.0


def test_rule_and_asap_replays_are_valid_and_the_rule_can_be_tuned():
    train = [synth_flex(days=2, seed=100 + i) for i in range(2)]
    rule = tune_rule(train, grid=3)
    assert isinstance(rule, Rule) and rule.cheap < rule.dear
    p = synth_flex(days=2, seed=7)
    for pol, kw in (("rule", dict(rule=rule)), ("asap", {})):
        r = replay(p, p.price, policy=pol, **kw)
        assert r["violations"] == [], pol


def test_monte_carlo_runs_without_violations():
    df = flex_monte_carlo(n=2, days=2, sigma=0.3, seed=1, n_train=2)
    assert int(df.filter(like="violations").sum().sum()) == 0
    assert (df.hindsight_obj <= df.planner_obj + 1e-6).all()


def test_real_price_hook_and_forecast_noise():
    p = flex_from_prices([20, 50, 30, 80], battery=Battery(2, 1))
    assert p.T == 4 and solve_flex(p).money > 0
    f = noisy_forecast(np.full(200, 50.0), np.random.default_rng(0), 0.3)
    assert f.std() > 1 and (f > 0).all()
    assert np.allclose(noisy_forecast(np.full(5, 50.0), np.random.default_rng(0), 0.0), 50.0)
