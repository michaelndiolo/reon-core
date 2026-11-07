import numpy as np
from hackkit import reon_storm as S

CAPS = np.array([0.9, 0.85, 0.8, 0.9, 0.88, 0.9, 0.9, 0.86])


def test_managed_beats_plain_without_failure():
    assert S.hours(CAPS, 60, 1.0, True) > S.hours(CAPS, 60, 1.0, False)


def test_plain_stops_when_a_cell_fails_managed_continues():
    assert S.hours(CAPS, 60, 1.0, False, fail_at_h=10) == 10
    assert S.hours(CAPS, 60, 1.0, True, fail_at_h=10) > 30


def test_failure_after_plain_already_empty_changes_nothing():
    t = S.hours(CAPS, 60, 2.0, False)
    assert S.hours(CAPS, 60, 2.0, False, fail_at_h=t + 5) == t


def test_load_shedding_stretches_hours_inversely():
    assert abs(S.hours(CAPS, 60, 2.0, True, power_fraction=0.5) - 2 * S.hours(CAPS, 60, 2.0, True)) < 1e-9


def test_stress_factors():
    f = S.stress_factors(16, 1)
    assert abs(f["current_and_dod_x"] - 16 / 15) < 1e-12 and f["wear_rate_x"] < f["current_and_dod_x"] < f["heat_x"]
    assert S.stress_factors(16, 0)["wear_rate_x"] == 1.0
