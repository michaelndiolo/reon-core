"""reon_claim: hand cases, monotonicity, round trips, and a brute-force check of the linear-fade life ratio."""
import numpy as np
import pytest

from hackkit import reon_claim as K


def test_hand_cases():
    assert K.life_ratio_linear([1, 1, 1, 1]) == pytest.approx(1.0)
    assert K.life_ratio_linear([3, 1, 1, 1]) == pytest.approx(3 / 1.5)          # max 3, mean 1.5
    assert K.expected_ratio(0.0, 8) == pytest.approx(1.0)                       # identical cells: no gain
    assert K.expected_life_ratio(0.0, 8) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        K.life_ratio_linear([1, 0])
    with pytest.raises(ValueError):
        K.required_cv(0.5, 8)
    with pytest.raises(ValueError):
        K.expected_ratio(0.1, 4, n_min=5)


def test_monotone_and_window_never_helps():
    prev = 1.0
    for cv in (0.02, 0.05, 0.1, 0.2, 0.4):
        r = K.expected_ratio(cv, 12)
        assert r > prev
        prev = r
        assert K.expected_ratio(cv, 12, n_min=10) <= r + 1e-12              # a limited window can only lose
    assert K.expected_ratio(0.2, 12, n_min=12) == pytest.approx(1.0)        # all cells must stay in: conventional
    assert K.expected_ratio(0.2, 12, n_min=1) == pytest.approx(K.expected_ratio(0.2, 12))


def test_round_trips():
    for target in (1.1, 1.5, 2.0):
        cv = K.required_cv(target, 12)
        assert cv is not None and K.expected_ratio(cv, 12) == pytest.approx(target, abs=0.01)
    cv = K.required_rate_cv(2.0, 12)
    assert cv is not None and K.expected_life_ratio(cv, 12) == pytest.approx(2.0, abs=0.01)
    assert K.required_cv(1.0, 12) == 0.0
    assert K.required_cv(50.0, 4, cv_max=0.3) is None                        # not reachable inside the allowed range


def test_linear_fade_life_ratio_by_simulation():
    rng = np.random.default_rng(2)
    for _ in range(10):
        rates = rng.uniform(0.01, 0.06, int(rng.integers(2, 10)))
        eol = 0.8
        dt, t = 1e-3, 0.0
        t_conv = t_ctrl = None
        while t_conv is None or t_ctrl is None:
            s = 1.0 - rates * t
            if t_conv is None and s.min() <= eol:
                t_conv = t
            if t_ctrl is None and s.mean() <= eol:
                t_ctrl = t
            t += dt
        assert t_ctrl / t_conv == pytest.approx(K.life_ratio_linear(rates), rel=0.01)
