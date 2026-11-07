"""Shortcut checks: results that must NOT be possible if the engine is honest (pattern: watch the steps, not just the score)."""
import numpy as np
from hackkit import reon_wear as W

KW = dict(balancer_r=0.05, balancer_per_kwh=4.0, ks=(1, 2), fade_mean=0.02, loss=0.02, sort_cost_per_kwh=0.0, rate=0.07, years=12.0, eol_frac=0.7, duty=0.7, dod_exp=0.87, knee_share=0.65,
          start_soh=1.0, balancer_eta=0.9, closed_loss=0.0, test_sigma=0.02, trials=6, steps=30, seed=5)
START = 100.0 * (1.0 + 0.02 * np.random.default_rng(3).standard_normal(16))


def best(**over):
    a = dict(KW, fade_cv=0.45, electronics_per_kwh=15.0, value_per_kwh_year=40.0)
    a.update(over)
    o = W.recommend_build(over.pop("start", START), 16, **a)
    return o


def test_prohibitive_switch_cost_never_recommends_switches():
    o = best(electronics_per_kwh=500.0)
    assert o["margin"] <= 0


def test_worthless_energy_gives_no_net_gain():
    o = best(value_per_kwh_year=0.0)
    assert o["table"][o["ours_best"]]["mean"] <= 0.05


def test_identical_cells_identical_fade_nothing_to_gain():
    a = dict(KW, fade_cv=0.0, electronics_per_kwh=15.0, value_per_kwh_year=40.0)
    a.update(knee_share=0.0)        # the Iowa knee makes some cells fade 2.4x faster at random: that alone creates spread, so it is switched off for this check
    o = W.recommend_build(np.full(16, 100.0), 16, **a)
    assert o["table"][o["ours_best"]]["mean"] <= 0.05


def test_capacity_scale_does_not_change_the_answer():
    a = dict(KW, fade_cv=0.45, electronics_per_kwh=15.0, value_per_kwh_year=40.0)
    o1 = W.recommend_build(START, 16, **a)
    o2 = W.recommend_build(START * 3.7, 16, **a)
    assert abs(o1["margin"] - o2["margin"]) < 0.5 and o1["ours_best"] == o2["ours_best"]


def test_knees_alone_create_spread_and_a_gain():
    """The flip side of the check above: with identical cells and identical base fade rates, random knees (65 % of cells, 2.4x faster) still open a gap that control can use. Written down so nobody is surprised."""
    a = dict(KW, fade_cv=0.0, electronics_per_kwh=15.0, value_per_kwh_year=40.0)
    o = W.recommend_build(np.full(16, 100.0), 16, **a)
    assert o["table"][o["ours_best"]]["mean"] > 1.0
