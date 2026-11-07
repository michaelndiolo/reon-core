import numpy as np
from hackkit import reon_wear as W
from examples import reon_hero_stress as H

KW = dict(loss=0.02, electronics_per_kwh=15.0, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, rate=0.07, trials=6, steps=30, seed=5, balancer_rs=(), global_counts=(1, 2), years=12.0, eol_frac=0.7, fade_mean=0.02, start_soh=1.0)


def best(fcv, value, start=None):
    start = np.full(16, 100.0) if start is None else start
    r = W.wear_scan(start, 16, fade_cv=fcv, value_per_kwh_year=value, **KW)
    return max(v["mean"] for k, v in r.items() if k.startswith(("late", "selective", "level")))


def test_no_spread_no_gain():
    # identical cells and identical fade rates: a plain string already uses every cell, so control cannot pay for itself
    assert best(0.0, 40.0) <= 0.05


def test_more_fade_spread_helps():
    assert best(0.6, 40.0) > best(0.2, 40.0) > 0.0


def test_higher_value_helps():
    assert best(0.45, 80.0) > best(0.45, 22.0) > best(0.45, 12.0)


def test_sourced_draw_stays_in_range():
    rng = np.random.default_rng(0)
    cvs = H.real_fade_cvs()
    assert len(cvs) == 12 and all(0.1 < c <= 0.6 for c in cvs)
    for _ in range(200):
        p = H.draw(rng, "sourced", cvs)
        assert 7.0 <= p["elec"] <= 24.0 and 10 <= p["value"] <= 90 and 0.0 < p["r"] <= 1.0 and p["fcv"] in cvs
