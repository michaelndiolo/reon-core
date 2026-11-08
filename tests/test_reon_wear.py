import numpy as np
import pytest

from hackkit import reon_design as D, reon_wear as W

KW = dict(fade_mean=0.04, fade_cv=0.2, loss=0.02, electronics_per_kwh=8.8, balancer_per_kwh=0.0, sort_cost_per_kwh=0.0, value_per_kwh_year=22.0, rate=0.07, years=7.0,
          eol_frac=0.7, trials=12, seed=5, steps=60, balancer_rs=(0.1,))


def caps(cv=0.05, n=24, seed=3):
    return np.maximum(np.random.default_rng(seed).normal(90, cv * 90, n), 20)


def test_reproduces_design_scan_without_wear_or_knees():
    c = caps()
    a = W.wear_scan(c, 24, test_sigma=0.02, **KW)
    recs = D.design_scan(c, 24, fade_mean=0.04, fade_cvs=[0.2], loss_cell=0.02, loss_exps=[0.0], cost_exps=[1.0], electronics_per_kwh_cell=8.8, sort_cost_per_kwh=0.0,
                         value_per_kwh_year=22.0, rate=0.07, years=7.0, eol_frac=0.7, test_sigma=0.02, trials=12, seed=5, steps=60, balancer_rs=[0.1], balancer_eta=0.9, balancer_per_kwh=0.0)
    ref = {r["design"]: r["mean"] for r in recs}
    assert a["late switches"]["mean"] == pytest.approx(ref["late-engaging switch on every cell, cells as found"], abs=1e-9)
    assert a["balancer 10%"]["mean"] == pytest.approx(ref["active balancer (moves up to 10% of a cell's capacity), cells as found"], abs=1e-9)


def test_knees_and_wear_change_the_outcome_but_plain_is_reference():
    c = caps(0.02, 24)
    base = W.wear_scan(c, 8, **KW)
    knee = W.wear_scan(c, 8, knee_share=0.65, **KW)
    wear = W.wear_scan(c, 8, dod_exp=0.9, duty=0.7, **KW)
    assert base["plain"]["mean"] == 0.0 and knee["plain"]["mean"] == 0.0
    assert knee["late switches"]["gross"] != base["late switches"]["gross"]
    assert wear["balancer 10%"]["gross"] > base["balancer 10%"]["gross"] - 1e-9   # wear-sharing never hurts a rival that moves charge
    assert all(v["years"] <= 7.0 + 1e-9 for v in knee.values())


def test_knee_draws_do_not_disturb_the_ageing_draws():
    c = caps(0.05, 24)
    a = W.wear_scan(c, 8, knee_share=0.0, **KW)
    b = W.wear_scan(c, 8, knee_share=0.0, knee_kappa=5.0, **KW)
    assert a == b


def test_bad_string_length():
    with pytest.raises(ValueError):
        W.wear_scan(caps(0.05, 24), 7, **KW)


def test_selective_bypass_limits():
    c = caps(0.05, 24)
    a = W.wear_scan(c, 8, select_counts=(0, 8), test_sigma=0.0, **KW)
    assert a["selective 0/8 cells"]["gross"] == pytest.approx(0.0, abs=1e-9)           # no switches = plain pack
    assert a["selective 8/8 cells"]["gross"] == pytest.approx(a["late switches"]["gross"], abs=1e-9)   # switches everywhere = late switches
    assert a["selective 8/8 cells"]["cost"] == pytest.approx(a["late switches"]["cost"])


def test_selective_catches_a_single_outlier_cheaply():
    c = np.full(24, 90.0); c[5] = 60.0
    kw = dict(KW); kw["fade_cv"] = 0.0
    kw.pop("fade_cv"); 
    a = W.wear_scan(c, 8, select_counts=(1,), test_sigma=0.0, fade_cv=0.0, **kw)
    assert a["selective 1/8 cells"]["gross"] == pytest.approx(a["late switches"]["gross"], rel=1e-6)
    assert a["selective 1/8 cells"]["cost"] == pytest.approx(a["late switches"]["cost"] / 8)


def test_recommend_build_picks_selective_for_one_outlier_and_a_rival_when_matched():
    kw = dict(fade_mean=0.02, fade_cv=0.2, loss=0.02, electronics_per_kwh=8.8, sort_cost_per_kwh=0.0, value_per_kwh_year=22.0, rate=0.07, years=7.0, eol_frac=0.7, trials=10, seed=5, steps=40)
    c = np.full(24, 90.0); c[5] = 60.0
    out = W.recommend_build(c, 8, balancer_r=0.05, balancer_per_kwh=4.0, **kw)
    assert out["build"].startswith("selective") and out["margin"] > 0
    flat = np.full(24, 90.0)
    out2 = W.recommend_build(flat, 8, balancer_r=0.05, balancer_per_kwh=4.0, **kw)
    assert not out2["build"].startswith(("selective", "late", "level")) or out2["margin"] > 0


def test_hybrid_select_limits():
    c = np.full(24, 90.0); c[5] = 60.0
    kw = dict(KW); kw.pop("fade_cv"); kw["balancer_rs"] = (0.0, 0.5)
    a = W.wear_scan(c, 8, hybrid_counts=(1,), select_counts=(1,), test_sigma=0.0, fade_cv=0.0, **kw)
    # a balancer that moves nothing (r = 0) leaves the selective bypass alone
    assert a["hybrid 1/8 + balancer 0%"]["gross"] == pytest.approx(a["selective 1/8 cells"]["gross"], rel=1e-9)
    # never worse than the selective bypass in gross value
    assert a["hybrid 1/8 + balancer 50%"]["gross"] >= a["selective 1/8 cells"]["gross"] - 1e-9


def test_hybrid_cost_is_switches_plus_balancer():
    c = np.full(24, 90.0); c[5] = 60.0
    kw = dict(KW); kw.pop("fade_cv"); kw["balancer_per_kwh"] = 4.0
    a = W.wear_scan(c, 8, hybrid_counts=(1,), test_sigma=0.0, fade_cv=0.0, **kw)
    assert a["hybrid 1/8 + balancer 10%"]["cost"] == pytest.approx(8.8 / 8 + 4.0)


def test_closed_loss_scales_with_the_share_of_switched_cells():
    c = np.full(24, 90.0); c[5] = 60.0
    kw = dict(KW); kw.pop("fade_cv")
    a = W.wear_scan(c, 8, select_counts=(1, 8), test_sigma=0.0, fade_cv=0.0, closed_loss=0.04, **kw)
    b = W.wear_scan(c, 8, select_counts=(1, 8), test_sigma=0.0, fade_cv=0.0, closed_loss=0.0, **kw)
    drop1 = b["selective 1/8 cells"]["gross"] - a["selective 1/8 cells"]["gross"]
    drop8 = b["selective 8/8 cells"]["gross"] - a["selective 8/8 cells"]["gross"]
    assert 0 < drop1 < drop8


def test_global_selective_puts_the_switch_on_the_outlier_wherever_it_is():
    c = np.full(24, 90.0); c[13] = 60.0           # outlier in the second string
    kw = dict(KW); kw.pop("fade_cv")
    a = W.wear_scan(c, 8, global_counts=(1,), select_counts=(1,), test_sigma=0.0, fade_cv=0.0, **kw)
    assert a["selective: only the 1 weakest cell of the pack"]["gross"] == pytest.approx(a["selective 1/8 cells"]["gross"], rel=1e-9)
    assert a["selective: only the 1 weakest cell of the pack"]["cost"] == pytest.approx(8.8 / 24)   # one switch in the whole pack


def test_window_none_is_unchanged_and_window_one_means_no_bypass_gain():
    import numpy as np
    caps = 100.0 * (1.0 + 0.05 * np.random.default_rng(1).standard_normal(40))
    kw = dict(fade_mean=0.01, fade_cv=0.45, loss=0.04, electronics_per_kwh=15.5, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0, rate=0.07, years=12.0, eol_frac=0.7, trials=3, steps=20, seed=2)
    free = W.wear_scan(caps, 40, **kw)
    none = W.wear_scan(caps, 40, window=None, **kw)
    assert free["late switches"]["mean"] == none["late switches"]["mean"]
    tight = W.wear_scan(caps, 40, window=1.0, **kw)
    assert abs(tight["late switches"]["gross"]) < 1e-9          # no cell may leave: late switches behave like the plain string
    mid = W.wear_scan(caps, 40, window=0.9, **kw)
    assert mid["late switches"]["gross"] <= free["late switches"]["gross"] + 1e-9   # a window can only remove value
    assert mid["late switches"]["gross"] >= tight["late switches"]["gross"] - 1e-9
    assert all(not k.startswith("selective 8/") for k in W.wear_scan(caps, 40, window=0.9, select_counts=(2, 8), **kw))   # 8 > floor(40 x 0.1) = 4 switches are not allowed


def test_hybrid_wear_sharing_is_off_by_default_and_never_hurts():
    import numpy as np
    caps = 100.0 * (1.0 + 0.05 * np.random.default_rng(4).standard_normal(40))
    kw = dict(fade_mean=0.012, fade_cv=0.45, loss=0.04, electronics_per_kwh=15.5, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0, rate=0.07, years=12.0, eol_frac=0.7, trials=3, steps=20, seed=2,
              hybrid_counts=(1,), balancer_rs=(0.05,), dod_exp=0.87)
    base = W.wear_scan(caps, 40, **kw)
    off = W.wear_scan(caps, 40, hybrid_shares_wear=False, **kw)
    on = W.wear_scan(caps, 40, hybrid_shares_wear=True, **kw)
    h = [k for k in base if k.startswith("hybrid")][0]
    assert base[h]["mean"] == off[h]["mean"]
    assert on[h]["mean"] >= off[h]["mean"] - 1e-9
    assert on["balancer 5%"]["mean"] == off["balancer 5%"]["mean"]
