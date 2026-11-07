import numpy as np
from hackkit import reon_events as E


def mean_net(policy, **kw):
    return float(np.mean([E.simulate(policy, s, **kw)["net"] for s in range(30)]))


def test_same_seed_same_result():
    assert E.simulate("ours", 3) == E.simulate("ours", 3)


def test_no_faults_no_spread_control_only_costs_money():
    kw = dict(lam=0.0, fcv=0.0, start_cv=0.0)
    assert mean_net("replace", **kw) > mean_net("ours", **kw)


def test_expensive_remote_visits_favor_automatic_bypass():
    kw = dict(lam=0.01, visit_cost=3000.0)
    assert mean_net("ours+crew", **kw) > mean_net("replace", **kw)


def test_dead_cell_takes_plain_string_down_but_not_bypassing_one():
    kw = dict(lam=0.03, lead=2.0)
    assert np.mean([E.simulate("replace", s, **kw)["down_months"] for s in range(30)]) > 0
    assert np.mean([E.simulate("ours", s, **kw)["down_months"] for s in range(30)]) == 0


def test_choose_policy_cheap_visits_prefers_replace_or_threshold_and_remote_prefers_auto():
    cheap = E.choose_policy(visit_cost=60.0, lam=0.008, loss=0.09, seeds_pick=range(0, 4), seeds_check=range(100, 104))
    remote = E.choose_policy(visit_cost=6000.0, lam=0.02, seeds_pick=range(0, 4), seeds_check=range(100, 104))
    assert remote["auto_wins"] and set(cheap["finalists"]) <= set(E.POLICIES)
